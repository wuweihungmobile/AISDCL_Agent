"""流程游標與 FSM 的對映、flow_status 衍生與對帳的判準（純函式；PRD §5.1.1；D-56）。

三件事、都是表驅動或確定性比較，沒有第二套狀態機：
  · `FLOW_FSM_MAPPING`／`flow_fsm_mapping_ok`：外環 FSM 現態與游標 `(step, phase)` 的合法對映表。
    `flow_status` 不是輸入也不是判準——它由 stage run 與 FSM 現態衍生（`derive_flow_status`）。
  · `derive_flow_status`：優先序 ESCALATED > RUNNING > WAITING_HUMAN > IDLE；stage run 失敗或取消
    屬「其餘」（游標回 IDLE、原因寫在 `flow_detail`；FAILED 只用於初始化失敗）。
  · 對帳結果的組裝（`file_check`、`mapping_check`、`absent_check`、`reconcile_result`）：
    只報告、不修復。
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType
from typing import Any

#: FSM 現態 → 合法的 `{flow_step: {flow_phase…}}`（PRD §5.1.1 與補充 M1；ESCALATION 類不限 phase）。
FLOW_FSM_MAPPING: Mapping[str, Mapping[str, frozenset[str]]] = MappingProxyType({
    "INIT": MappingProxyType({"topic": frozenset({"INGESTED"})}),
    "SCENARIO_DETECT": MappingProxyType({"topic": frozenset({"INGESTED"})}),
    "AGENT_LOAD": MappingProxyType({"topic": frozenset({
        "INGESTED", "RESEARCHING", "EVIDENCE_READY"})}),
    "SPEC_DRAFTING": MappingProxyType({"studio": frozenset({"DRAFTING", "REVISING"})}),
    "SCG_VALIDATION": MappingProxyType({"studio": frozenset({"REVIEWING"})}),
    "HUMAN_PENDING": MappingProxyType({"studio": frozenset({"GATE0_PENDING", "REVISING"})}),
    "SPEC_REGRESSION_CHECK": MappingProxyType({"studio": frozenset({
        "GATE0_PENDING", "REVISING"})}),
    "ESCALATION": MappingProxyType({"studio": frozenset({"REVIEWING", "REVISING"})}),
    "ESCALATION_FINAL": MappingProxyType({"studio": frozenset({"REVIEWING", "REVISING"})}),
    "SPEC_FROZEN": MappingProxyType({"route": frozenset({"FROZEN"})}),
})
#: 衍生 `flow_status` 時視為「ESCALATED」的 FSM 現態（外環鍵關閉自動恢復，正常只會是前兩者）。
ESCALATED_FSM_STATES = frozenset({"ESCALATION", "ESCALATION_FINAL", "AUTO_RECOVERY_ATTEMPT"})
ACTIVE_RUN_STATUSES = frozenset({"QUEUED", "RUNNING"})
CHECK_IDS: tuple[str, ...] = ("fsm_flow_mapping", "prd_sha256", "review_card", "evidence_matrix",
                              "task_decomposition", "route_decision")
#: 對帳項 `status` 的「量不到」值——拼法取 API 契約 `ReconcileResult`（底線）；能力資訊與
#: `state.json` 投影另用連字號的 `settings.NOT_EVALUABLE`，兩處是不同介面、各依各的契約。
NOT_EVALUABLE_STATUS = "NOT_EVALUABLE"


def flow_fsm_mapping_ok(fsm_state: str | None, flow_step: str, flow_phase: str) -> bool:
    """游標 `(step, phase)` 與 FSM 現態的對映是否合法；查無該現態的列＝不合法（不假設一致）。"""
    phases = FLOW_FSM_MAPPING.get(str(fsm_state), {}).get(flow_step)
    return phases is not None and flow_phase in phases


def derive_flow_status(stage_run_statuses: Iterable[str], fsm_state: str | None) -> str:
    """`flow_status` 的唯一衍生處：ESCALATED（FSM 在 ESCALATION 類）＞RUNNING（有 QUEUED 或 RUNNING
    的 stage run）＞WAITING_HUMAN（FSM 在 HUMAN_PENDING）＞IDLE（含 stage run 失敗、取消
    與無 run）。"""
    if fsm_state in ESCALATED_FSM_STATES:
        return "ESCALATED"
    if any(status in ACTIVE_RUN_STATUSES for status in stage_run_statuses):
        return "RUNNING"
    if fsm_state == "HUMAN_PENDING":
        return "WAITING_HUMAN"
    return "IDLE"


# ── 對帳結果的組裝 ───────────────────────────────────────────────────────────────────────────
def _drift(kind: str, path: str, expected: str | None, actual: str | None) -> dict[str, Any]:
    return {"kind": kind, "path": path, "expectedSha256": expected, "actualSha256": actual}


def file_check(check_id: str, kind: str, expected: Mapping[str, Any] | None,
               actual: Mapping[str, str | None] | None) -> dict[str, Any]:
    """一個檔案對帳項。`expected`＝`{path, sha256}`（資料庫那側）、`actual`＝`{path: sha256｜None}`
    （檔案那側；缺檔為 None）。兩側皆缺席＝ok 且 `present: false`；DB 有列而檔缺席或位元組不同
    ＝drift。"""
    if expected is None:
        return {"id": check_id, "status": "ok", "present": False, "detail": "", "drift": []}
    path, sha = str(expected["path"]), str(expected["sha256"])
    found = (actual or {}).get(path)
    drift = [] if found == sha else [_drift(kind, path, sha, found)]
    return {"id": check_id, "status": "drift" if drift else "ok", "present": True,
            "detail": "file_missing" if drift and found is None else "", "drift": drift}


def mapping_check(fsm_state: str | None, flow_step: str, flow_phase: str, *,
                  readable: bool) -> dict[str, Any]:
    """FSM 與游標對映項；狀態檔讀不動＝NOT_EVALUABLE（量不到不得 false-green）。"""
    if not readable:
        return {"id": "fsm_flow_mapping", "status": NOT_EVALUABLE_STATUS, "present": True,
                "detail": "fsm_state_unreadable", "drift": []}
    if flow_fsm_mapping_ok(fsm_state, flow_step, flow_phase):
        return {"id": "fsm_flow_mapping", "status": "ok", "present": True, "detail": "",
                "drift": []}
    return {"id": "fsm_flow_mapping", "status": "drift", "present": True,
            "detail": f"fsm={fsm_state} flow={flow_step}/{flow_phase}",
            "drift": [{"kind": "FSM_FLOW", "path": "flow", "expectedSha256": None,
                       "actualSha256": None}]}


def absent_check(check_id: str) -> dict[str, Any]:
    """P0 沒有的產物（拆解、分流）：兩側皆缺席＝ok，標 `present: false`。"""
    return {"id": check_id, "status": "ok", "present": False, "detail": "", "drift": []}


def reconcile_result(checks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """`consistent` 僅在全部 ok 時為真；`driftCount`＝非 ok 項的漂移列總數（NOT_EVALUABLE
    計 1）。"""
    drift_count = sum(len(c["drift"]) or (0 if c["status"] == "ok" else 1) for c in checks)
    return {"consistent": all(c["status"] == "ok" for c in checks),
            "driftCount": drift_count, "checks": [dict(c) for c in checks]}
