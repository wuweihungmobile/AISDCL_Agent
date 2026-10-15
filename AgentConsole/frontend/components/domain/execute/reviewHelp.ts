/**
 * 審核動作的說明文字（契約 §3.6.3 的「每個 kind 允許的決定與動作」資料化）：審核對話框在送出前告訴人「按下去會發生什麼」。
 * 允許與否以後端給的 allowedDecisions 為準（按鈕是否可按），這裡只負責說明後果。
 */
import type { ReviewDecision, ReviewKind } from "@/lib/api/types";

const TEXT: Record<ReviewKind, Partial<Record<ReviewDecision, string>>> = {
  TASK_CONFIRM: {
    APPROVE: "批次會恢復執行，開始下一個任務。",
    REJECT: "批次會被取消（狀態變為已取消），尚未開始的任務一併取消。",
  },
  GOAL_CONFIRM: {
    APPROVE: "批次會恢復執行，開始下一個目標。",
    REJECT: "批次會被取消（狀態變為已取消），尚未開始的任務一併取消。",
  },
  GOAL_COMPLETED: {
    APPROVE: "批次會恢復執行，接著做下一個目標。",
    REJECT: "批次會被取消，且這個目標會被標為失敗（人工判定，不會被後續事件蓋回）。",
    RETRY: "從這個目標開始之前的斷點還原，重跑這個目標；找不到斷點時改開後續批次。",
  },
  ESCALATED: {
    RETRY: "從失敗步驟之前的斷點還原後重跑（沿用原批次的 playbook，任務內容的修改不會生效）；找不到斷點時改開後續批次。",
    SKIP: "把失敗的任務標為跳過，並以其餘未完成的任務另開一個後續批次。",
    REJECT: "只關閉這個審核項；批次與任務維持失敗，不會呼叫引擎。",
  },
};

export function reviewConsequence(kind: ReviewKind, decision: ReviewDecision): string {
  return TEXT[kind]?.[decision] ?? "依後端規則處理。";
}

/** 這個決定會不會改變批次（取消、還原、另開批次）：對話框據此用較醒目的確認鈕。 */
export function isDestructiveDecision(kind: ReviewKind, decision: ReviewDecision): boolean {
  if (decision === "REJECT") return kind !== "ESCALATED";
  return decision === "SKIP";
}

/** 決定完成後的 toast 文字。followUp＝回應標頭帶了 X-Follow-Up-Run-Id（另開了後續批次，畫面會切過去）。 */
export function reviewDoneMessage(decision: ReviewDecision, followUp: boolean): string {
  const base = { APPROVE: "已通過", REJECT: "已拒絕", RETRY: "已要求重試", SKIP: "已跳過" }[decision];
  return followUp ? `${base}，已開啟後續批次並切換過去` : base;
}
