/**
 * DAG 視覺化的資料層（契約 §1.2.8、§4.2 E-13；PRD US-E-09；設計稿畫面 7「DAG 依賴視覺化」）。純函式、不依賴 React。
 *  - layoutDag：目標節點橫向依序排列（G1 ─── G2 ─── G3），各目標下方列出它的任務節點。
 *  - nodeTone：節點狀態 → 視覺色調（完成＝主色實底、進行中＝tertiary 底主色邊、待處理＝灰底；失敗／跳過另有色調）。
 *  - overlayDag：把串流看到的任務即時狀態疊到 REST 的 DAG 上（REST 的節點狀態是讀取當下的現況，不是即時），
 *    目標節點在有任務被疊加時依 R-goal 規則重算（契約 §3.5.3）。
 */
import type { Dag, DagNode } from "@/lib/api/types";
import type { TaskLive } from "@/lib/domain/runLive";

export type DagTone = "done" | "active" | "pending" | "failed" | "skipped";

export function nodeTone(status: string): DagTone {
  switch (status) {
    case "COMPLETED":
      return "done";
    case "IN_PROGRESS":
    case "RUNNING":
    case "VALIDATING":
      return "active";
    case "FAILED":
    case "ESCALATED":
      return "failed";
    case "SKIPPED":
    case "CANCELLED":
      return "skipped";
    default:
      return "pending"; // PENDING／QUEUED／BLOCKED／PAUSED／未知
  }
}

export const TONE_LABEL: Record<DagTone, string> = {
  done: "完成",
  active: "進行中",
  pending: "待處理",
  failed: "失敗",
  skipped: "已略過",
};

export type DagColumn = {
  goal: DagNode;
  tasks: DagNode[];
  /** 這個目標的前置目標（DEPENDENCY 邊的 from） */
  dependsOn: string[];
  /** 與前一個目標之間的連線：有依賴邊＝實線；沒有（只是排序相鄰）＝虛線；第一個目標沒有 */
  connector: "dependency" | "sequence" | "none";
};

const bySequence = (a: DagNode, b: DagNode) => (a.sequence ?? 0) - (b.sequence ?? 0);

export function layoutDag(dag: Pick<Dag, "nodes" | "edges">): DagColumn[] {
  const goals = dag.nodes.filter((n) => n.kind === "GOAL").sort(bySequence);
  const depEdges = dag.edges.filter((e) => e.kind === "DEPENDENCY");
  return goals.map((goal, i) => {
    const dependsOn = depEdges.filter((e) => e.to === goal.id).map((e) => e.from);
    const prev = goals[i - 1];
    return {
      goal,
      tasks: dag.nodes.filter((n) => n.kind === "TASK" && n.goalId === goal.id).sort(bySequence),
      dependsOn,
      connector: !prev ? "none" : dependsOn.includes(prev.id) ? "dependency" : "sequence",
    };
  });
}

/** R-goal（契約 §3.5.3）：由任務狀態推導目標狀態。 */
export function deriveGoalStatus(taskStatuses: readonly string[]): string {
  if (taskStatuses.length > 0 && taskStatuses.every((s) => s === "COMPLETED" || s === "SKIPPED")) {
    return taskStatuses.every((s) => s === "SKIPPED") ? "SKIPPED" : "COMPLETED";
  }
  if (taskStatuses.some((s) => s === "FAILED" || s === "ESCALATED")) return "FAILED";
  if (taskStatuses.some((s) => s === "RUNNING" || s === "VALIDATING" || s === "COMPLETED")) return "IN_PROGRESS";
  return "PENDING";
}

/**
 * 把即時任務狀態（taskId → RUNNING／COMPLETED／FAILED）疊到 DAG：
 * 沒被疊加到任何任務的目標保留伺服器給的狀態（可能含人工判定，例如 REJECT 的目標被標 FAILED）。
 */
export function overlayDag(dag: Dag, live: Readonly<Record<string, TaskLive>>): Dag {
  if (Object.keys(live).length === 0) return dag;
  const nodes = dag.nodes.map((n) => (n.kind === "TASK" && live[n.id] ? { ...n, status: live[n.id].status } : n));
  const touchedGoals = new Set(nodes.filter((n) => n.kind === "TASK" && live[n.id]).map((n) => n.goalId));
  return {
    ...dag,
    nodes: nodes.map((n) => {
      if (n.kind !== "GOAL" || !touchedGoals.has(n.id)) return n;
      const statuses = nodes.filter((t) => t.kind === "TASK" && t.goalId === n.id).map((t) => t.status);
      return { ...n, status: deriveGoalStatus(statuses) };
    }),
  };
}

/** 節點的簡短代號：目標 G<序>；任務取 playbook 的 step_id（例 G1-T2），沒有就用名稱。 */
export function nodeCode(node: DagNode, index: number): string {
  if (node.kind === "GOAL") return `G${node.sequence ?? index + 1}`;
  return node.stepId ?? node.label;
}
