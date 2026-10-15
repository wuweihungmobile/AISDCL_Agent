import { describe, expect, it } from "vitest";

import type { ParsedResult } from "@/lib/api/types";
import { blankGoal, blankTask, countTasks, isTreeDirty, toParsedResult, toTree, treeReducer, treeSignature, uniqueGoalKey, type Tree } from "./tree";

/** 契約 E2E-01 的 S-OK 解析結果（g1 兩個任務、g2 一個任務且依賴 g1），再加上伺服器擁有的欄位。 */
const SERVER_TREE: ParsedResult = {
  project: {
    name: "E2E 匯入專案",
    executionPath: "/e2e/proj-import",
    passCriteria: "三個目標全部完成",
    description: "由 BRD 匯入",
    autonomyLevel: 3,
  },
  goals: [
    {
      key: "g1",
      name: "基礎",
      passCriteria: "基礎任務完成",
      sortOrder: 0,
      dependsOn: [],
      tasks: [
        { name: "初始化", description: "請輸出 [T1_DONE]", passCriteria: "輸出含 [T1_DONE]", sortOrder: 0 },
        { name: "設定", description: "請輸出 [T2_DONE]", passCriteria: "輸出含 [T2_DONE]", sortOrder: 1 },
      ],
    },
    {
      key: "g2",
      name: "核心",
      passCriteria: "核心任務完成",
      sortOrder: 1,
      dependsOn: ["g1"],
      tasks: [{ name: "實作", description: "請輸出 [T3_DONE]", passCriteria: "輸出含 [T3_DONE]", sortOrder: 0 }],
    },
  ],
  path: "LLM",
  aiModel: "e2e-model",
  tokenUsed: 1152,
  reasoning: "（伺服器欄位）",
  draftIds: ["d1"],
  specDigest: "abc",
};

const fresh = (): Tree => toTree(SERVER_TREE);
const names = (t: Tree) => t.goals.map((g) => g.name);
const taskNames = (t: Tree, goal: number) => t.goals[goal].tasks.map((x) => x.name);

describe("契約 ⇄ 編輯樹", () => {
  it("來回轉換不丟資料：三層結構、依賴與順序原樣保留", () => {
    const out = toParsedResult(fresh());
    expect(out.project).toEqual({
      name: "E2E 匯入專案",
      executionPath: "/e2e/proj-import",
      passCriteria: "三個目標全部完成",
      description: "由 BRD 匯入",
      autonomyLevel: 3,
    });
    expect(out.goals.map((g) => [g.key, g.name, g.dependsOn])).toEqual([
      ["g1", "基礎", []],
      ["g2", "核心", ["g1"]],
    ]);
    expect(out.goals[0].tasks.map((t) => t.name)).toEqual(["初始化", "設定"]);
  });

  it("伺服器擁有的欄位（path／aiModel／tokenUsed／reasoning／draftIds／specDigest）不會送回去", () => {
    const out = toParsedResult(fresh());
    for (const key of ["path", "aiModel", "tokenUsed", "reasoning", "draftIds", "specDigest"]) {
      expect(out, key).not.toHaveProperty(key);
    }
  });

  it("sortOrder 依陣列順序重編成 0 起連續整數（不信任來源值）", () => {
    const messy = { ...SERVER_TREE, goals: SERVER_TREE.goals.map((g, i) => ({ ...g, sortOrder: 90 - i })) };
    const out = toParsedResult(toTree(messy));
    expect(out.goals.map((g) => g.sortOrder)).toEqual([0, 1]);
    expect(out.goals[0].tasks.map((t) => t.sortOrder)).toEqual([0, 1]);
  });

  it("選填欄位只在有值時才送：空的 evaluatorCommand／expectedOutputRegex 不出現；有值的與不編輯的欄位原樣帶回", () => {
    const tree = fresh();
    const withOptional = treeReducer(tree, {
      type: "editTask",
      goalKey: "g1",
      uid: tree.goals[0].tasks[0].uid,
      patch: { evaluatorCommand: "pytest -q", expectedOutputRegex: "\\[T1_DONE\\]", maxRetries: 2, estimatedTokens: 900, passCriteriaSpec: { source: "sdd" } },
    });
    const [first, second] = toParsedResult(withOptional).goals[0].tasks;
    expect(first).toMatchObject({ evaluatorCommand: "pytest -q", expectedOutputRegex: "\\[T1_DONE\\]", maxRetries: 2, estimatedTokens: 900, passCriteriaSpec: { source: "sdd" } });
    for (const key of ["evaluatorCommand", "expectedOutputRegex", "maxRetries", "estimatedTokens", "passCriteriaSpec"]) {
      expect(second, key).not.toHaveProperty(key);
    }
  });

  it("DEF-AC-001：真後端對 AI 解析的任務回 maxRetries: null（契約 §0.2：與缺席等價）——不當成「有值」送回，也不讓樹被誤判成未儲存編輯", () => {
    // 型別宣告只有 number | undefined，但真後端實際回 null：用斷言模擬線上資料，才測得到執行期行為
    const nullRetries = null as unknown as number;
    const fromServer: ParsedResult = {
      ...SERVER_TREE,
      goals: SERVER_TREE.goals.map((g) => ({ ...g, tasks: g.tasks.map((t) => ({ ...t, maxRetries: nullRetries })) })),
    };
    const tree = toTree(fromServer);
    const baseline = treeSignature(tree);
    for (const goal of toParsedResult(tree).goals) for (const t of goal.tasks) expect(t, "null 不送").not.toHaveProperty("maxRetries");
    // 對話框不改欄位就按確定：patch.maxRetries 為 undefined（欄位空白）→ 與伺服器版本一致，不算未儲存編輯
    const uid = tree.goals[0].tasks[0].uid;
    const same = treeReducer(tree, { type: "editTask", goalKey: "g1", uid, patch: { maxRetries: undefined } });
    expect(isTreeDirty(same, baseline)).toBe(false);
  });

  it("autonomyLevel 缺席時預設 3（契約 §1.1.6：parsedResult.project.autonomyLevel ?? 3）；目標缺 key 時補不衝突的 g<n>", () => {
    const sparse = toTree({
      project: { name: "p", executionPath: "/x", passCriteria: "c" },
      goals: [
        { key: "", name: "A", passCriteria: "c", tasks: [] },
        { key: "g1", name: "B", passCriteria: "c", tasks: [] },
      ],
    });
    expect(sparse.project.autonomyLevel).toBe(3);
    expect(sparse.goals.map((g) => g.key)).toEqual(["g2", "g1"]);
  });
});

describe("未儲存編輯偵測", () => {
  it("載入後與伺服器版本相同；改一個任務名就髒；改回原值又乾淨", () => {
    const baseline = treeSignature(fresh());
    let tree = fresh();
    expect(isTreeDirty(tree, baseline)).toBe(false);
    const uid = tree.goals[0].tasks[0].uid;
    tree = treeReducer(tree, { type: "editTask", goalKey: "g1", uid, patch: { name: "初始化（改）" } });
    expect(isTreeDirty(tree, baseline)).toBe(true);
    tree = treeReducer(tree, { type: "editTask", goalKey: "g1", uid, patch: { name: "初始化" } });
    expect(isTreeDirty(tree, baseline)).toBe(false);
  });

  it("只是改順序也算未儲存編輯", () => {
    const baseline = treeSignature(fresh());
    const moved = treeReducer(fresh(), { type: "moveGoal", activeKey: "g2", overKey: "g1" });
    expect(isTreeDirty(moved, baseline)).toBe(true);
  });
});

describe("編輯操作（reducer）", () => {
  it("改名：只動被指到的那個任務，其他不變", () => {
    const tree = fresh();
    const next = treeReducer(tree, { type: "editTask", goalKey: "g1", uid: tree.goals[0].tasks[1].uid, patch: { name: "設定環境" } });
    expect(taskNames(next, 0)).toEqual(["初始化", "設定環境"]);
    expect(taskNames(next, 1)).toEqual(["實作"]);
    expect(taskNames(tree, 0)).toEqual(["初始化", "設定"]); // 原樹不被改（不可變）
  });

  it("新增目標：附一個空白任務；key 重複時拒絕", () => {
    const tree = fresh();
    const goal = blankGoal("g-new", "t-new-0");
    const next = treeReducer(tree, { type: "addGoal", goal });
    expect(next.goals.map((g) => g.key)).toEqual(["g1", "g2", "g-new"]);
    expect(next.goals[2].tasks).toHaveLength(1);
    expect(treeReducer(next, { type: "addGoal", goal: blankGoal("g-new", "t-x") }).goals).toHaveLength(3);
  });

  it("新增任務：加到指定目標的最後；uid 重複時拒絕", () => {
    const tree = fresh();
    const next = treeReducer(tree, { type: "addTask", goalKey: "g2", task: { ...blankTask("t-n"), name: "收尾" } });
    expect(taskNames(next, 1)).toEqual(["實作", "收尾"]);
    expect(taskNames(treeReducer(next, { type: "addTask", goalKey: "g2", task: blankTask("t-n") }), 1)).toEqual(["實作", "收尾"]);
  });

  it("刪除任務：只拿掉該任務", () => {
    const tree = fresh();
    const next = treeReducer(tree, { type: "deleteTask", goalKey: "g1", uid: tree.goals[0].tasks[0].uid });
    expect(taskNames(next, 0)).toEqual(["設定"]);
  });

  it("刪除目標：其他目標對它的依賴一併清掉（不留指向不存在 key 的依賴）", () => {
    const next = treeReducer(fresh(), { type: "deleteGoal", key: "g1" });
    expect(names(next)).toEqual(["核心"]);
    expect(next.goals[0].dependsOn).toEqual([]);
  });

  it("目標拖曳排序：依賴用 key 引用，所以換位後依賴不會錯位；序列化的 sortOrder 隨之重編", () => {
    const next = treeReducer(fresh(), { type: "moveGoal", activeKey: "g2", overKey: "g1" });
    expect(names(next)).toEqual(["核心", "基礎"]);
    const out = toParsedResult(next);
    expect(out.goals.map((g) => [g.key, g.sortOrder])).toEqual([
      ["g2", 0],
      ["g1", 1],
    ]);
    expect(out.goals[0].dependsOn).toEqual(["g1"]);
  });

  it("任務拖曳排序只在同一個目標內換位", () => {
    const tree = fresh();
    const [a, b] = tree.goals[0].tasks.map((t) => t.uid);
    const next = treeReducer(tree, { type: "moveTask", goalKey: "g1", activeUid: b, overUid: a });
    expect(taskNames(next, 0)).toEqual(["設定", "初始化"]);
    expect(toParsedResult(next).goals[0].tasks.map((t) => t.sortOrder)).toEqual([0, 1]);
    // 指到別的目標的任務 uid：不動
    const cross = treeReducer(tree, { type: "moveTask", goalKey: "g1", activeUid: a, overUid: tree.goals[1].tasks[0].uid });
    expect(taskNames(cross, 0)).toEqual(["初始化", "設定"]);
  });

  it("編輯目標依賴：自依賴與不存在的 key 被濾掉", () => {
    const next = treeReducer(fresh(), { type: "editGoal", key: "g2", patch: { dependsOn: ["g2", "ghost", "g1"] } });
    expect(next.goals[1].dependsOn).toEqual(["g1"]);
  });

  it("指到不存在的目標或任務：樹原樣不變", () => {
    const tree = fresh();
    const sig = treeSignature(tree);
    expect(treeSignature(treeReducer(tree, { type: "editGoal", key: "nope", patch: { name: "x" } }))).toBe(sig);
    expect(treeSignature(treeReducer(tree, { type: "deleteGoal", key: "nope" }))).toBe(sig);
    expect(treeSignature(treeReducer(tree, { type: "addTask", goalKey: "nope", task: blankTask("t") }))).toBe(sig);
    expect(treeSignature(treeReducer(tree, { type: "editTask", goalKey: "g1", uid: "nope", patch: { name: "x" } }))).toBe(sig);
    expect(treeSignature(treeReducer(tree, { type: "moveGoal", activeKey: "g1", overKey: "nope" }))).toBe(sig);
  });

  it("改專案：名稱、路徑、說明、通過標準、自治等級", () => {
    const next = treeReducer(fresh(), { type: "editProject", patch: { name: "新名稱", autonomyLevel: 5 } });
    expect(next.project).toMatchObject({ name: "新名稱", autonomyLevel: 5, executionPath: "/e2e/proj-import" });
  });

  it("有界閘不在前端執行：25 個任務、空白描述都原樣保留並送出（不截斷、不修剪，由伺服器 422 完整列出）", () => {
    let tree = fresh();
    for (let i = 0; i < 23; i += 1) tree = treeReducer(tree, { type: "addTask", goalKey: "g2", task: blankTask(`t-extra-${i}`) });
    expect(tree.goals[1].tasks).toHaveLength(24);
    tree = treeReducer(tree, { type: "addTask", goalKey: "g2", task: blankTask("t-25") });
    const out = toParsedResult(tree);
    expect(out.goals[1].tasks).toHaveLength(25);
    expect(out.goals[1].tasks.at(-1)).toMatchObject({ name: "", description: "" });
    expect(countTasks(tree)).toBe(27);
  });

  it("load 整棵換掉（儲存成功或重新解析後以伺服器版本為準）", () => {
    const loaded = treeReducer(treeReducer(fresh(), { type: "deleteGoal", key: "g1" }), { type: "load", tree: fresh() });
    expect(names(loaded)).toEqual(["基礎", "核心"]);
  });
});

describe("uniqueGoalKey", () => {
  it("回傳 g-<片段>，並避開已存在的 key", () => {
    const seq = ["aaa", "aaa", "bbb"];
    let i = 0;
    expect(uniqueGoalKey([], () => "xyz")).toBe("g-xyz");
    expect(uniqueGoalKey(["g-aaa"], () => seq[i++])).toBe("g-bbb");
  });

  it("連續撞 50 次就丟錯，不無窮迴圈", () => {
    expect(() => uniqueGoalKey(["g-same"], () => "same")).toThrow();
  });
});
