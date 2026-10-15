import { describe, expect, it } from "vitest";

import type { Dag, DagNode } from "@/lib/api/types";
import { TONE_LABEL, deriveGoalStatus, layoutDag, nodeCode, nodeTone, overlayDag } from "./dag";

const goal = (id: string, sequence: number, status = "PENDING", label = `目標 ${sequence}`): DagNode => ({ id, kind: "GOAL", label, status, sequence });
const task = (id: string, goalId: string, sequence: number, status = "PENDING", stepId = `${goalId}-T${sequence}`): DagNode => ({
  id,
  kind: "TASK",
  label: `任務 ${id}`,
  status,
  goalId,
  sequence,
  stepId,
});

const DAG: Dag = {
  runId: "run1",
  statusAsOf: "2026-10-15T08:30:00Z",
  nodes: [
    task("t3", "g2", 3, "PENDING"), // 故意亂序：版面必須依 sequence 排
    goal("g2", 2, "PENDING", "核心"),
    task("t1", "g1", 1, "COMPLETED"),
    goal("g1", 1, "IN_PROGRESS", "基礎"),
    task("t2", "g1", 2, "RUNNING"),
    goal("g3", 3, "PENDING", "測試"),
  ],
  edges: [
    { from: "g1", to: "g2", kind: "DEPENDENCY" },
    { from: "g1", to: "t1", kind: "CONTAINS" },
    { from: "g1", to: "t2", kind: "CONTAINS" },
    { from: "g2", to: "t3", kind: "CONTAINS" },
  ],
};

describe("DAG 節點版面（目標橫向排列 G1 ─── G2 ─── G3，各目標下方列任務）", () => {
  it("目標與任務各依 sequence 排序；任務歸到自己的目標底下", () => {
    const cols = layoutDag(DAG);
    expect(cols.map((c) => c.goal.id)).toEqual(["g1", "g2", "g3"]);
    expect(cols.map((c) => c.tasks.map((t) => t.id))).toEqual([["t1", "t2"], ["t3"], []]);
  });

  it("連線：有依賴邊的相鄰目標＝實線（dependency）；只是排序相鄰＝虛線（sequence）；第一個沒有", () => {
    expect(layoutDag(DAG).map((c) => c.connector)).toEqual(["none", "dependency", "sequence"]);
  });

  it("每個目標列出它的前置目標（DEPENDENCY 邊的 from）；非相鄰的依賴也看得到", () => {
    const dag: Dag = { ...DAG, edges: [...DAG.edges, { from: "g1", to: "g3", kind: "DEPENDENCY" }, { from: "g2", to: "g3", kind: "DEPENDENCY" }] };
    const cols = layoutDag(dag);
    expect(cols[2].dependsOn.sort()).toEqual(["g1", "g2"]);
    expect(cols[2].connector).toBe("dependency"); // 與前一個（g2）有依賴
    expect(cols[0].dependsOn).toEqual([]);
  });

  it("沒有目標節點：空版面（不丟例外）", () => {
    expect(layoutDag({ nodes: [], edges: [] })).toEqual([]);
  });

  it("節點代號：目標 G<序>；任務取 playbook 的 step_id，沒有就用名稱", () => {
    expect(nodeCode(goal("g1", 1), 0)).toBe("G1");
    expect(nodeCode(task("t1", "g1", 1), 0)).toBe("g1-T1");
    expect(nodeCode({ ...task("t9", "g1", 9), stepId: undefined }, 0)).toBe("任務 t9");
  });
});

describe("狀態色調（設計稿：完成＝主色實底、進行中＝tertiary 底主色邊、待處理＝灰底）", () => {
  it.each([
    ["COMPLETED", "done"],
    ["IN_PROGRESS", "active"],
    ["RUNNING", "active"],
    ["VALIDATING", "active"],
    ["FAILED", "failed"],
    ["ESCALATED", "failed"],
    ["SKIPPED", "skipped"],
    ["CANCELLED", "skipped"],
    ["PENDING", "pending"],
    ["QUEUED", "pending"],
    ["BLOCKED", "pending"],
    ["PAUSED", "pending"],
    ["SOMETHING_NEW", "pending"],
  ] as const)("%s → %s", (status, tone) => {
    expect(nodeTone(status)).toBe(tone);
  });

  it("每種色調都有中文標籤", () => {
    expect(Object.values(TONE_LABEL).every((l) => /\S/.test(l))).toBe(true);
  });
});

describe("即時狀態疊加（REST 的節點狀態是讀取當下的現況，SSE 讓它即時）", () => {
  it("沒有即時資料：原樣回傳（同一個物件）", () => {
    expect(overlayDag(DAG, {})).toBe(DAG);
  });

  it("被疊加的任務換成串流看到的狀態；目標依 R-goal 重算（有任務完成／進行中＝進行中；全完成＝完成；有失敗＝失敗）", () => {
    const live = { t1: { status: "COMPLETED" as const, seq: 5 }, t2: { status: "COMPLETED" as const, seq: 8 } };
    const out = overlayDag(DAG, live);
    expect(out.nodes.find((n) => n.id === "t2")?.status).toBe("COMPLETED");
    expect(out.nodes.find((n) => n.id === "g1")?.status).toBe("COMPLETED");
    // 沒被疊加到任務的目標保留伺服器給的狀態
    expect(out.nodes.find((n) => n.id === "g2")?.status).toBe("PENDING");
    expect(out.nodes.find((n) => n.id === "g3")?.status).toBe("PENDING");

    const failed = overlayDag(DAG, { t2: { status: "FAILED", seq: 9 } });
    expect(failed.nodes.find((n) => n.id === "g1")?.status).toBe("FAILED");
    const started = overlayDag(DAG, { t3: { status: "RUNNING", seq: 10 } });
    expect(started.nodes.find((n) => n.id === "g2")?.status).toBe("IN_PROGRESS");
  });

  it("輸入的 DAG 不被修改", () => {
    const snapshot = JSON.stringify(DAG);
    overlayDag(DAG, { t1: { status: "FAILED", seq: 1 } });
    expect(JSON.stringify(DAG)).toBe(snapshot);
  });

  it("deriveGoalStatus（R-goal）：全完成／全跳過／有失敗／有進度／沒進度", () => {
    expect(deriveGoalStatus(["COMPLETED", "SKIPPED"])).toBe("COMPLETED");
    expect(deriveGoalStatus(["SKIPPED", "SKIPPED"])).toBe("SKIPPED");
    expect(deriveGoalStatus(["COMPLETED", "FAILED"])).toBe("FAILED");
    expect(deriveGoalStatus(["QUEUED", "ESCALATED"])).toBe("FAILED");
    expect(deriveGoalStatus(["QUEUED", "RUNNING"])).toBe("IN_PROGRESS");
    expect(deriveGoalStatus(["QUEUED", "COMPLETED"])).toBe("IN_PROGRESS");
    expect(deriveGoalStatus(["QUEUED", "PENDING"])).toBe("PENDING");
    expect(deriveGoalStatus([])).toBe("PENDING");
  });
});
