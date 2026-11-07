import type { ResearchFsmView } from "@/lib/api/types";
import { T0, T1 } from "./ids";

/**
 * 外環 FSM 視圖夾具（API-RP-13）：既有 `SddFsmState` 原樣加 `retryHistory.gates` 與 `humanReturnCount`（D-59(4)）。
 * `currentCount` 是審查預算的唯一來源（剩餘預算＝max(0, 3 − currentCount)）；`entries` 是各閘 history 筆數。
 */
export function fsmView(currentState: string, patch: Partial<ResearchFsmView> = {}, scgCount = 0): ResearchFsmView {
  return {
    project: "research-vector-db",
    currentState,
    currentSprint: 1,
    sessionId: "sess-1",
    updatedAt: T1,
    frozenStages: [],
    decisionTrace: [{ ts: T0, from: "SCG_VALIDATION", to: currentState, reason: "夾具", spec_refs: [], agents_consulted: [], trigger: "gate" }],
    source: "FSM-STATE-research-vector-db.yaml",
    humanPending: { count: currentState === "HUMAN_PENDING" ? 1 : 0, items: [] },
    retryHistory: {
      count: scgCount,
      last: null,
      gates: { SCG_VALIDATION: { currentCount: scgCount, entries: scgCount }, PR_REVIEW: { currentCount: 0, entries: 0 }, RTM_VERIFY: { currentCount: 0, entries: 0 } },
    },
    rtmCoverage: null,
    phase: { name: currentState === "HUMAN_PENDING" ? "HUMAN_GATE" : "SPECIFICATION", order: currentState === "HUMAN_PENDING" ? 3 : 2, blocking: false, observation: false },
    escalationHistory: [],
    escalationProvenance: null,
    fsmProject: "research-vector-db",
    humanReturnCount: 0,
    stage2Frozen: false,
    ...patch,
  };
}

/** 等待人工核准：審查通過、FSM 在 HUMAN_PENDING。 */
export const FSM_HUMAN_PENDING = fsmView("HUMAN_PENDING");

/** 三輪審查都沒過：FSM 在 ESCALATION，附 Bridge 組好的恢復指令（Console 只顯示、不執行）。 */
export const FSM_ESCALATION = fsmView(
  "ESCALATION",
  {
    phase: { name: "BLOCKED", order: 0, blocking: true, observation: false },
    escalationHistory: [{ triggered_at: T1, trigger_reason: "SCG_VALIDATION 第 3 次未通過", resolved_at: null, resolution: null, source: "gate" }],
    recovery: {
      target: "SPEC_DRAFTING",
      powershell: "Push-Location '<工作區>'; python -m tools.fsm_runtime resume-from-escalation --to SPEC_DRAFTING --reason '<人工原因>'; Pop-Location",
      posix: "(cd '<工作區>' && python -m tools.fsm_runtime resume-from-escalation --to SPEC_DRAFTING --reason '<人工原因>')",
    },
  },
  3,
);

/** 人工恢復後：FSM 已回 SPEC_DRAFTING，但重試計數仍為 3（`resume-from-escalation` 不歸零；D-60）。 */
export const FSM_AFTER_RECOVERY = fsmView("SPEC_DRAFTING", {}, 3);
