/**
 * 匯入步驟 2 的三層樹編輯模型（專案 → 目標 → 任務；契約 §1.1.4、§3.3.6；US-I-03／I-04）。
 *
 * 設計取捨：
 *  - 編輯用的樹（Tree）與契約的 ParsedResult 分開：前者帶前端專用的穩定 id（任務 uid、目標 key），
 *    拖曳排序與 React key 不依賴陣列索引；toParsedResult 負責序列化回契約形狀。
 *  - 全部是純函式／reducer，不碰 React、不碰網路，方便逐一測試。
 *  - 序列化時 sortOrder 依陣列順序重編成 0 起連續整數（契約也由伺服器重編，兩邊一致）；
 *    伺服器擁有的欄位（path／aiModel／tokenUsed／reasoning／draftIds／specDigest）不送（請求帶了也會被忽略）。
 *  - 有界閘（步驟 ≤24、無環、prompt 非空）由伺服器把關，這裡**不截斷、不修剪**：
 *    編輯器可以暫時放著 25 個任務，儲存時由 422 把違規完整列出（US-I-10）。
 */
import type { ParsedGoal, ParsedProject, ParsedResult, ParsedTask } from "@/lib/api/types";

export type TaskNode = {
  /** 前端專用的穩定 id（契約的 ParsedTask 沒有 id）；不會送到後端 */
  uid: string;
  name: string;
  description: string;
  passCriteria: string;
  /** 空字串＝沒有 */
  evaluatorCommand: string;
  /** 空字串＝沒有 */
  expectedOutputRegex: string;
  /** 契約 §0.2：null 與缺席等價（真後端對 AI 解析的任務回 null，DEF-AC-001），一律以 `== null` 判空 */
  maxRetries?: number | null;
  /** 以下兩欄畫面不編輯，原樣帶回（路徑 A／C 會放來源資訊） */
  estimatedTokens?: number;
  passCriteriaSpec?: Record<string, unknown>;
};

export type GoalNode = {
  /** 樹內唯一的穩定鍵；dependsOn 引用它，所以排序與刪除不會讓依賴錯位 */
  key: string;
  name: string;
  description: string;
  passCriteria: string;
  dependsOn: string[];
  tasks: TaskNode[];
};

export type ProjectNode = {
  name: string;
  executionPath: string;
  description: string;
  passCriteria: string;
  autonomyLevel: number;
};

export type Tree = { project: ProjectNode; goals: GoalNode[] };

export const DEFAULT_AUTONOMY = 3;

// ── 契約 ⇄ 編輯樹 ────────────────────────────────────────────────────────

function taskFrom(t: ParsedTask, uid: string): TaskNode {
  return {
    uid,
    name: t.name ?? "",
    description: t.description ?? "",
    passCriteria: t.passCriteria ?? "",
    evaluatorCommand: t.evaluatorCommand ?? "",
    expectedOutputRegex: t.expectedOutputRegex ?? "",
    maxRetries: t.maxRetries,
    estimatedTokens: t.estimatedTokens,
    passCriteriaSpec: t.passCriteriaSpec,
  };
}

/** 契約形狀 → 編輯樹。目標缺 key 時依序補 g1、g2…（伺服器解析時一定有，這裡只是防禦）。 */
export function toTree(parsed: ParsedResult): Tree {
  const used = new Set(parsed.goals.map((g) => g.key).filter(Boolean));
  let next = 1;
  const nextFreeKey = (): string => {
    while (used.has(`g${next}`)) next += 1;
    const key = `g${next}`;
    used.add(key);
    return key;
  };
  const goals = parsed.goals.map((g: ParsedGoal, gi): GoalNode => ({
    key: g.key || nextFreeKey(),
    name: g.name ?? "",
    description: g.description ?? "",
    passCriteria: g.passCriteria ?? "",
    dependsOn: [...(g.dependsOn ?? [])],
    tasks: (g.tasks ?? []).map((t, ti) => taskFrom(t, `t-${gi}-${ti}`)),
  }));
  const p: ParsedProject = parsed.project;
  return {
    project: {
      name: p.name ?? "",
      executionPath: p.executionPath ?? "",
      description: p.description ?? "",
      passCriteria: p.passCriteria ?? "",
      autonomyLevel: p.autonomyLevel ?? DEFAULT_AUTONOMY,
    },
    goals,
  };
}

/** 編輯樹 → 契約形狀（PUT /import/{id}/result 的 parsedResult）。 */
export function toParsedResult(tree: Tree): ParsedResult {
  return {
    project: {
      name: tree.project.name,
      executionPath: tree.project.executionPath,
      passCriteria: tree.project.passCriteria,
      description: tree.project.description,
      autonomyLevel: tree.project.autonomyLevel,
    },
    goals: tree.goals.map((g, gi): ParsedGoal => ({
      key: g.key,
      name: g.name,
      description: g.description,
      passCriteria: g.passCriteria,
      sortOrder: gi,
      dependsOn: [...g.dependsOn],
      tasks: g.tasks.map((t, ti): ParsedTask => {
        const out: ParsedTask = {
          name: t.name,
          description: t.description,
          passCriteria: t.passCriteria,
          sortOrder: ti,
        };
        if (t.evaluatorCommand.trim()) out.evaluatorCommand = t.evaluatorCommand;
        if (t.expectedOutputRegex.trim()) out.expectedOutputRegex = t.expectedOutputRegex;
        if (t.maxRetries != null) out.maxRetries = t.maxRetries;
        if (t.estimatedTokens !== undefined) out.estimatedTokens = t.estimatedTokens;
        if (t.passCriteriaSpec) out.passCriteriaSpec = t.passCriteriaSpec;
        return out;
      }),
    })),
  };
}

/** 序列化成穩定字串，用來判斷「和伺服器上的版本有沒有差異」（未儲存編輯）。 */
export function treeSignature(tree: Tree): string {
  return JSON.stringify(toParsedResult(tree));
}

export function isTreeDirty(tree: Tree, baseline: string): boolean {
  return treeSignature(tree) !== baseline;
}

export function countTasks(tree: Tree): number {
  return tree.goals.reduce((n, g) => n + g.tasks.length, 0);
}

// ── 新節點工廠（id 由呼叫端產生，reducer 保持純函式）──────────────────────────

export function blankTask(uid: string): TaskNode {
  return { uid, name: "", description: "", passCriteria: "", evaluatorCommand: "", expectedOutputRegex: "" };
}

/** 新目標一律帶一個空白任務：契約要求每個目標至少 1 個任務（空陣列 → 400）。 */
export function blankGoal(key: string, firstTaskUid: string): GoalNode {
  return { key, name: "", description: "", passCriteria: "", dependsOn: [], tasks: [blankTask(firstTaskUid)] };
}

/** 8 碼隨機片段（瀏覽器與 Node 22 皆有 crypto.randomUUID；缺席時退回時間＋亂數）。 */
export function randomId(): string {
  const c = globalThis.crypto;
  const raw = c?.randomUUID ? c.randomUUID() : `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
  return raw.replace(/-/g, "").slice(0, 8);
}

/** 產生樹內不重複的目標 key（g-<隨機片段>）；rand 可注入，測試用。 */
export function uniqueGoalKey(existing: readonly string[], rand: () => string): string {
  const taken = new Set(existing);
  for (let i = 0; i < 50; i += 1) {
    const key = `g-${rand()}`;
    if (!taken.has(key)) return key;
  }
  throw new Error("無法產生不重複的目標 key");
}

// ── reducer ─────────────────────────────────────────────────────────────

export type TreeAction =
  | { type: "load"; tree: Tree }
  | { type: "editProject"; patch: Partial<ProjectNode> }
  | { type: "addGoal"; goal: GoalNode }
  | { type: "editGoal"; key: string; patch: Partial<Pick<GoalNode, "name" | "description" | "passCriteria" | "dependsOn">> }
  | { type: "deleteGoal"; key: string }
  | { type: "moveGoal"; activeKey: string; overKey: string }
  | { type: "addTask"; goalKey: string; task: TaskNode }
  | { type: "editTask"; goalKey: string; uid: string; patch: Partial<Omit<TaskNode, "uid">> }
  | { type: "deleteTask"; goalKey: string; uid: string }
  | { type: "moveTask"; goalKey: string; activeUid: string; overUid: string };

function moveItem<T>(list: readonly T[], from: number, to: number): T[] {
  const copy = [...list];
  const [item] = copy.splice(from, 1);
  copy.splice(to, 0, item);
  return copy;
}

function mapGoal(state: Tree, key: string, fn: (g: GoalNode) => GoalNode): Tree {
  if (!state.goals.some((g) => g.key === key)) return state;
  return { ...state, goals: state.goals.map((g) => (g.key === key ? fn(g) : g)) };
}

export function treeReducer(state: Tree, action: TreeAction): Tree {
  switch (action.type) {
    case "load":
      return action.tree;

    case "editProject":
      return { ...state, project: { ...state.project, ...action.patch } };

    case "addGoal":
      if (state.goals.some((g) => g.key === action.goal.key)) return state;
      return { ...state, goals: [...state.goals, action.goal] };

    case "editGoal": {
      const others = new Set(state.goals.filter((g) => g.key !== action.key).map((g) => g.key));
      return mapGoal(state, action.key, (g) => ({
        ...g,
        ...action.patch,
        // 依賴只能指向「其他仍存在的目標」；自依賴與已刪除的 key 一律濾掉
        dependsOn: action.patch.dependsOn ? action.patch.dependsOn.filter((k) => others.has(k)) : g.dependsOn,
      }));
    }

    case "deleteGoal": {
      if (!state.goals.some((g) => g.key === action.key)) return state;
      return {
        ...state,
        // 其他目標對它的依賴一併清掉，避免留下指向不存在 key 的依賴（伺服器會把它判成 cycle 閘）
        goals: state.goals.filter((g) => g.key !== action.key).map((g) => (g.dependsOn.includes(action.key) ? { ...g, dependsOn: g.dependsOn.filter((k) => k !== action.key) } : g)),
      };
    }

    case "moveGoal": {
      const from = state.goals.findIndex((g) => g.key === action.activeKey);
      const to = state.goals.findIndex((g) => g.key === action.overKey);
      if (from < 0 || to < 0 || from === to) return state;
      return { ...state, goals: moveItem(state.goals, from, to) };
    }

    case "addTask":
      return mapGoal(state, action.goalKey, (g) => (g.tasks.some((t) => t.uid === action.task.uid) ? g : { ...g, tasks: [...g.tasks, action.task] }));

    case "editTask":
      return mapGoal(state, action.goalKey, (g) => ({
        ...g,
        tasks: g.tasks.map((t) => (t.uid === action.uid ? { ...t, ...action.patch } : t)),
      }));

    case "deleteTask":
      return mapGoal(state, action.goalKey, (g) => ({ ...g, tasks: g.tasks.filter((t) => t.uid !== action.uid) }));

    case "moveTask":
      return mapGoal(state, action.goalKey, (g) => {
        const from = g.tasks.findIndex((t) => t.uid === action.activeUid);
        const to = g.tasks.findIndex((t) => t.uid === action.overUid);
        if (from < 0 || to < 0 || from === to) return g;
        return { ...g, tasks: moveItem(g.tasks, from, to) };
      });

    default:
      return state;
  }
}
