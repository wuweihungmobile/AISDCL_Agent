"""流程游標與 FSM 的對映、flow_status 衍生與對帳的判準（純函式；PRD §5.1.1；D-56、D-77）。

三件事、都是表驅動或確定性比較，沒有第二套狀態機：
  · `FLOW_FSM_MAPPING`／`flow_fsm_mapping_ok`：外環 FSM 現態與游標 `(step, phase)` 的合法對映表。
    `flow_status` 不參與表的判準——唯一的例外是 D-77：stage run 失敗或取消的游標
    （`flow_status=FAILED`）對表內每個 FSM 現態都合法（失敗時相態退回 stage 開始前的穩定相態，
    不必與 FSM 現態對得上）。
  · `derive_flow_status`：優先序 ESCALATED > RUNNING > FAILED（最近一次 stage run 失敗或取消，
    D-77）> WAITING_HUMAN > IDLE；初始化失敗也是 FAILED（`flow_detail` 以 `init_failed:` 起頭）。
  · 對帳結果的組裝（`file_check`、`mapping_check`、`absent_check`、`reconcile_result`）：
    只報告、不修復。
另有 `prd_save_cursor`：人工存 PRD 之後游標該落在哪個合法相態（API-RP-09、INT-05）。
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from types import MappingProxyType
from typing import Any

#: FSM 現態 → 合法的 `{flow_step: {flow_phase…}}`（PRD §5.1.1 與補充 M1；ESCALATION 類不限 phase）。
#: `AGENT_LOAD` 的 `studio／REVISING` 是換世代（D-60）之後的合法態：新鍵回到 AGENT_LOAD、PRD 與
#: 審查輪都保留，使用者留在規格工作室繼續修訂（INT-05）。
FLOW_FSM_MAPPING: Mapping[str, Mapping[str, frozenset[str]]] = MappingProxyType({
    "INIT": MappingProxyType({"topic": frozenset({"INGESTED"})}),
    "SCENARIO_DETECT": MappingProxyType({"topic": frozenset({"INGESTED"})}),
    "AGENT_LOAD": MappingProxyType({
        "topic": frozenset({"INGESTED", "RESEARCHING", "EVIDENCE_READY"}),
        "studio": frozenset({"REVISING"})}),
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
#: 失敗游標的 `flow_status`：stage run 失敗、取消或被回收（D-77），以及初始化失敗。
FAILED_STATUS = "FAILED"
CHECK_IDS: tuple[str, ...] = ("fsm_flow_mapping", "prd_sha256", "review_card", "evidence_matrix",
                              "task_decomposition", "route_decision")
#: 對帳項 `status` 的「量不到」值——拼法取 API 契約 `ReconcileResult`（底線）；能力資訊與
#: `state.json` 投影另用連字號的 `settings.NOT_EVALUABLE`，兩處是不同介面、各依各的契約。
NOT_EVALUABLE_STATUS = "NOT_EVALUABLE"


def flow_fsm_mapping_ok(fsm_state: str | None, flow_step: str, flow_phase: str,
                        flow_status: str | None = None) -> bool:
    """游標 `(step, phase)` 與 FSM 現態的對映是否合法；查無該現態的列＝不合法（不假設一致）。

    D-77：`flow_status` 為 `FAILED`（stage run 失敗或取消後的游標）時，表內的每個 FSM 現態都算合法——
    失敗時相態退回「上一個可重入的穩定相態」，而 FSM 可能已被該 run 推進（例：審查 run 已把外環
    鍵推到 SCG_VALIDATION），兩者本來就不必對得上；表外的現態（含讀不到）照舊不合法。其餘一律
    只看表。"""
    if flow_status == FAILED_STATUS and str(fsm_state) in FLOW_FSM_MAPPING:
        return True
    phases = FLOW_FSM_MAPPING.get(str(fsm_state), {}).get(flow_step)
    return phases is not None and flow_phase in phases


def derive_flow_status(stage_run_statuses: Iterable[str], fsm_state: str | None, *,
                       last_run_failed: bool = False) -> str:
    """`flow_status` 的唯一衍生處：ESCALATED（FSM 在 ESCALATION 類）＞RUNNING（有 QUEUED 或 RUNNING
    的 stage run）＞FAILED（`last_run_failed`：呼叫端剛讓 stage run 失敗、取消或回收，D-77）＞
    WAITING_HUMAN（FSM 在 HUMAN_PENDING）＞IDLE。`stage_run_statuses` 只放仍在進行的 run；失敗與否
    由呼叫端以 `last_run_failed` 明說（它才知道這次收尾是不是失敗），所以後續任何一次成功的
    收尾都會把 FAILED 自然衍生掉。"""
    if fsm_state in ESCALATED_FSM_STATES:
        return "ESCALATED"
    if any(status in ACTIVE_RUN_STATUSES for status in stage_run_statuses):
        return "RUNNING"
    if last_run_failed:
        return FAILED_STATUS
    if fsm_state == "HUMAN_PENDING":
        return "WAITING_HUMAN"
    return "IDLE"


def prd_save_cursor(fsm_state: str | None, flow_step: str, flow_phase: str) -> tuple[str, str]:
    """人工存 PRD 新版之後的游標 `(step, phase)`（API-RP-09、PRD M1；INT-05）：一律是 FSM 現態的
    合法對映，不固定寫 DRAFTING。
      · `GATE0_PENDING` 表示「head 版本通過審查、等 Gate 0」；人改過之後 head 是尚未審查的新版，
        所以先降成 `REVISING`（PRD 修訂中，HUMAN_PENDING 的 M1 列）；
      · 現在的 `(step, phase)` 若已是該現態的合法對映就保持（AGENT_LOAD 下的研究步驟、換世代後的
        `studio／REVISING`、審查中的 `REVIEWING`…）；
      · 不合法時改取該現態規格工作室的合法相態：DRAFTING 優先、其次 REVISING、再其次（例：
        SCG_VALIDATION 只有 REVIEWING）依字母序第一個；
      · FSM 讀不到（`None`）或查無該現態：沒有合法相態可挑，游標步驟與相態維持原樣（只有第一條的
        GATE0_PENDING 降級照做，因為那是「head 已變」的事實、與 FSM 無關）。"""
    if flow_phase == "GATE0_PENDING":
        flow_phase = "REVISING"
    if flow_fsm_mapping_ok(fsm_state, flow_step, flow_phase):
        return flow_step, flow_phase
    legal = FLOW_FSM_MAPPING.get(str(fsm_state), {}).get("studio", frozenset())
    for candidate in ("DRAFTING", "REVISING"):
        if candidate in legal:
            return "studio", candidate
    if legal:
        return "studio", sorted(legal)[0]
    return flow_step, flow_phase


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
                  readable: bool, flow_status: str | None = None) -> dict[str, Any]:
    """FSM 與游標對映項；狀態檔讀不動＝NOT_EVALUABLE（量不到不得 false-green）。`flow_status`
    只有一個用途：FAILED 游標對表內的每個 FSM 現態都合法（D-77，見 `flow_fsm_mapping_ok`）。"""
    if not readable:
        return {"id": "fsm_flow_mapping", "status": NOT_EVALUABLE_STATUS, "present": True,
                "detail": "fsm_state_unreadable", "drift": []}
    if flow_fsm_mapping_ok(fsm_state, flow_step, flow_phase, flow_status):
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
