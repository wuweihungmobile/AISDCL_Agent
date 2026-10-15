import { describe, expect, it } from "vitest";

import type { ReviewDecision, ReviewKind } from "@/lib/api/types";
import { isDestructiveDecision, reviewConsequence, reviewDoneMessage } from "./reviewHelp";

/** 契約 §3.6.3 的表：每個 kind 允許哪些決定（✗ 的格子不會有說明）。 */
const ALLOWED: Record<ReviewKind, ReviewDecision[]> = {
  TASK_CONFIRM: ["APPROVE", "REJECT"],
  GOAL_CONFIRM: ["APPROVE", "REJECT"],
  GOAL_COMPLETED: ["APPROVE", "REJECT", "RETRY"],
  ESCALATED: ["RETRY", "SKIP", "REJECT"],
};

describe("審核決定的後果說明（契約 §3.6.3）", () => {
  it("每個「允許的決定」都有專屬說明，且不是兜底句", () => {
    for (const [kind, decisions] of Object.entries(ALLOWED) as Array<[ReviewKind, ReviewDecision[]]>) {
      for (const d of decisions) expect(reviewConsequence(kind, d), `${kind}.${d}`).not.toBe("依後端規則處理。");
    }
  });

  it("不允許的組合（例如 ESCALATED 的通過）退回兜底句，不編造說明", () => {
    expect(reviewConsequence("ESCALATED", "APPROVE")).toBe("依後端規則處理。");
    expect(reviewConsequence("TASK_CONFIRM", "SKIP")).toBe("依後端規則處理。");
  });

  it("後果與契約一致：gate 類拒絕＝取消批次；GOAL_COMPLETED 拒絕另標目標失敗；ESCALATED 拒絕只關閉審核項、不呼叫引擎；ESCALATED 跳過＝另開後續批次", () => {
    expect(reviewConsequence("TASK_CONFIRM", "REJECT")).toContain("取消");
    expect(reviewConsequence("GOAL_COMPLETED", "REJECT")).toContain("標為失敗");
    expect(reviewConsequence("ESCALATED", "REJECT")).toContain("不會呼叫引擎");
    expect(reviewConsequence("ESCALATED", "SKIP")).toContain("後續批次");
    expect(reviewConsequence("ESCALATED", "RETRY")).toContain("沿用原批次的 playbook");
  });

  it("會改變批次的決定（取消批次、跳過）用醒目確認鈕；ESCALATED 的拒絕只關審核項、不算", () => {
    expect(isDestructiveDecision("TASK_CONFIRM", "REJECT")).toBe(true);
    expect(isDestructiveDecision("GOAL_COMPLETED", "REJECT")).toBe(true);
    expect(isDestructiveDecision("ESCALATED", "SKIP")).toBe(true);
    expect(isDestructiveDecision("ESCALATED", "REJECT")).toBe(false);
    expect(isDestructiveDecision("TASK_CONFIRM", "APPROVE")).toBe(false);
    expect(isDestructiveDecision("ESCALATED", "RETRY")).toBe(false);
  });

  it("完成後的 toast：四種決定；另開後續批次時補一句", () => {
    expect([...(["APPROVE", "REJECT", "RETRY", "SKIP"] as const)].map((d) => reviewDoneMessage(d, false))).toEqual(["已通過", "已拒絕", "已要求重試", "已跳過"]);
    expect(reviewDoneMessage("SKIP", true)).toBe("已跳過，已開啟後續批次並切換過去");
  });
});
