/**
 * SDD 治理（整合輪 115；契約 §1.10）元件測試的共用夾具：FSM 狀態、`GET /engines/sdd` 的回應、追溯報告、execute 的警告。
 * 形狀取自 schema-p3-6.d.ts；巢狀內容（escalationHistory、frozenStages…）保留 FSM 檔的 snake_case 鍵（原樣）。
 */
import type { ExecutionRtm, SddEngineStatus, SddFsmState } from "@/lib/api/types";

export const PROJECT_ID = "0b8c5d1e-6a47-4d3f-8f2a-9c1e7b3a5d02";
export const CHECKED_AT = "2026-10-17T03:21:45Z";
/** 本機時區建構，顯示成 2026-10-17 09:02:03，不依賴執行機器的時區 */
export const LOCAL_ISO = new Date(2026, 9, 17, 9, 2, 3).toISOString();

export const POWERSHELL_RECOVERY =
  'Push-Location "C:\\sdd\\AISDLC_SDD_v9.99" -ErrorAction Stop; $env:SDD_STATE_DIR = "C:\\work\\core\\build\\reports\\fsm"; & "python" -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project "core-fsm" --to IMPLEMENTATION --reason "<人工原因>"; Remove-Item Env:SDD_STATE_DIR; Pop-Location';
export const POSIX_RECOVERY =
  'cd "/sdd/AISDLC_SDD_v9.99" && SDD_STATE_DIR="/work/core/build/reports/fsm" "python" -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project "core-fsm" --to IMPLEMENTATION --reason "<人工原因>"';

export function fsmState(patch: Partial<SddFsmState> = {}): SddFsmState {
  return {
    project: "core-fsm",
    fsmProject: "core-fsm",
    currentState: "HUMAN_PENDING",
    currentSprint: 1,
    sessionId: "sid-core",
    updatedAt: LOCAL_ISO,
    frozenStages: [],
    decisionTrace: [],
    source: "FSM-STATE-core-fsm.yaml",
    humanPending: { count: 1, items: [{ entered_at: LOCAL_ISO, reminder_hours: 72 }] },
    retryHistory: { count: 0, last: null },
    rtmCoverage: null,
    phase: { name: "HUMAN_GATE", order: 3, blocking: false, observation: false },
    escalationHistory: [],
    escalationProvenance: null,
    recovery: null,
    ...patch,
  };
}

/** ESCALATION 的 FSM：委派失敗（provenance.source=autoclaude_delegated_failed），帶 Bridge 組好的恢復指令。 */
export function escalatedFsm(patch: Partial<SddFsmState> = {}): SddFsmState {
  return fsmState({
    currentState: "ESCALATION",
    humanPending: { count: 0, items: [] },
    phase: { name: "BLOCKED", order: 0, blocking: true, observation: false },
    escalationHistory: [{ triggered_at: LOCAL_ISO, trigger_reason: "AutoClaude 委派失敗：評估未通過", resolved_at: null, resolution: null, source: "autoclaude_delegated" }],
    escalationProvenance: { rule_id: "R-9.20.2", source: "autoclaude_delegated_failed", reason: "ENGINE-ESCALATION step=sdd-greenfield-at-001-1" },
    recovery: { target: "IMPLEMENTATION", powershell: POWERSHELL_RECOVERY, posix: POSIX_RECOVERY },
    ...patch,
  });
}

export function engineStatus(fsm: SddFsmState | null, patch: Partial<SddEngineStatus> = {}): SddEngineStatus {
  return {
    available: true,
    reason: null,
    version: { latest: "AISDLC_SDD_v9.99", root: "/sdd/AISDLC_SDD_v9.99" },
    projects: fsm ? [{ project: fsm.fsmProject ?? fsm.project, source: fsm.source, currentState: fsm.currentState ?? null, updatedAt: fsm.updatedAt ?? null }] : [],
    fsm,
    checkedAt: CHECKED_AT,
    ...patch,
  };
}

/** 契約 §1.10.3 的範例：4 個 AT 全過、2 個 AC 全覆蓋、沒有無法歸屬者。 */
export function rtmReport(patch: Partial<ExecutionRtm> = {}): ExecutionRtm {
  return {
    scenario: "greenfield",
    specDigest: "sha256:1f0e2b7a9c4d8e3f6a1b5c7d9e0f2a4b6c8d0e1f3a5b7c9d1e3f5a7b9c0d2e4f",
    at: { passed: 4, total: 4, unmapped: 0, pct: 100 },
    ac: { covered: 2, total: 2, pct: 100 },
    failedAtIds: [],
    weakRegexAtIds: [],
    unmappedAtIds: [],
    fullyCovered: true,
    advisory: true,
    ...patch,
  };
}
