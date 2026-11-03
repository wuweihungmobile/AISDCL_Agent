"""研究 stage 的確定性 orchestrator（ADR-003 D1／D2；ADR-XPLAT-017 D3／D6；TCS AC-960-7／12）。

一個 stage run＝一份短 playbook（`compile/`），由專用的 `ResearchRunManager` 以 AutoClaude
引擎執行（研究 run 不進 `execution_runs`，只記 `research_stage_runs` 與事件）。引擎只負責
「叫 claude 做事、用 `gate_cli` 驗收」；**所有判定都在這裡的確定性碼**：解析輸出、再驗一次
schema、聚合評分、寫資料庫、呼叫 FSM。LLM 從不決定迴圈與停止（12-Rule Rule 5）。

兩條持久化紀律：
  · 寫入一律「檔→outbox→DB 交易」（`DurableWriter`）；FSM 一律經 `fsm_ops`（CLI 子行程）。
  · 審查結果（D-58）：`gate` 呼叫**之前**，輪結果先落 `<outbox>/review-pending/` 的 journal；`gate`
    回傳後才在同一交易寫輪列、分數、缺陷與事件。崩潰後重放以 FSM `show` 的 `decision_trace` 與
    `retry_history` 找 gate 理由內的 stage run 記號，判斷該輪的 `gate` 是否已呼叫（已呼叫＝只補 DB、
    不重呼叫；未呼叫＝先呼叫再寫）；POST_HUMAN 通過輪依設計不呼叫 `gate`（D-50），重放只補 DB。

`gate SCG_VALIDATION` 的呼叫點只在 `_call_gate`：非靜態 FAIL 的那一處位於「現態不為 HUMAN_PENDING」
的守衛分支內（AST 鎖 C7）；人工退回與 POST_HUMAN 未通過走靜態 FAIL。核准（Gate 0）只在 HTTP 處理函式
內（C2），本模組不引用。
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import fsutil
from ..errors import ApiError
from ..locks import AdvisoryLock
from ..models import PlaybookIn, RunCreateIn
from ..runner import RunHandle, RunManager
from ..sdd_state import ESCALATION_STATES
from ..security import AuditLog
from ..settings import Settings
from . import export, fsm_ops, layout
from .compile import CompiledStage, CompileError, StageRequest, compile_stage, defects_rel
from .compile.playbooks import EVIDENCE_INDEX_REL, PREFETCH_INDEX_REL, PREVIOUS_EVIDENCE_REL
from .db import ResearchDb, utc_now
from .fetch import (
    FetchBatch,
    FetchClient,
    build_effective_allowlist,
    effective_limits,
    run_prefetch,
    task_for,
)
from .gates import aggregate
from .gates.evidence import EvidenceContext, validate_evidence_items
from .gates.ingest import plan_ingest
from .gates.prd_schema import count_acs, precheck_draft, precheck_p1, precheck_passed
from .gates.reconcile import (
    absent_check,
    derive_flow_status,
    file_check,
    flow_fsm_mapping_ok,
    mapping_check,
    reconcile_result,
)
from .gates.review_card import (
    plan_defect_transitions,
    precheck_to_detail,
    validate_review_card,
    validate_review_dimension,
)
from .gates.schemas import DIMENSIONS, RUBRIC_REGISTRY, SCG_RETRY_LIMIT, violation_lines
from .offline import OfflineFixtureError, fixture_file, load_batch, offline_reason
from .outbox import DbBlocked, DurableWriter, FileRef, FileWrite, Op

logger = logging.getLogger("bridge.research.orchestrator")

GATE = "SCG_VALIDATION"
TERMINAL_ENGINE = frozenset({"COMPLETED", "FAILED", "CANCELLED"})
ESCALATED_STATES = ESCALATION_STATES | {"AUTO_RECOVERY_ATTEMPT"}
CHAIN_MAX_ROUNDS = 6
AUTHOR_AGENT = "spec-engineer"
RESEARCH_AGENT = "research-analyst"
REVIEW_CARD_REL = "02_governance/review_card.json"
MATRIX_REL = "00_research/evidence_matrix.md"
PRD_DRAFT_REL = "01_specs/PRD_draft.md"
ADR_DRAFT_REL = "01_specs/adr_draft.md"
LICENSE_PENDING_REL = "00_research/license_pending.json"
DEFAULT_CLAUDE = "claude"
#: 研究 run 的引擎子行程環境不帶的名稱前綴：Bridge 自己的設定（`BRIDGE_*`）、SDD 寫入面（`SDD_*`）、
#: Brain 的金鑰與端點（`MINIMAX_*`；D-79：引擎在 ESCALATION 時依金鑰是否存在決定要不要同步呼叫
#: MiniMax——資料出口，且多耗約 11 秒；研究 run 不用 Brain，所以一律不給）。
_STRIPPED_PREFIXES = ("BRIDGE_", "SDD_", "MINIMAX_")
_STRIPPED_NAMES = frozenset({"PYTHONPATH", "GITHUB_TOKEN", "GH_TOKEN", "GH_ENTERPRISE_TOKEN"})
_JSON_PATH_SAFE = re.compile(r"[^A-Za-z0-9_.\[\]-]")


# ── 子行程環境（AT-960-7-E-2）──────────────────────────────────────────────────────────────────
class ResearchRunHandle(RunHandle):
    """研究 stage 的引擎 run：子行程環境再剝掉 Bridge 的設定與機密（`BRIDGE_*`、`SDD_*`、
    `MINIMAX_*`、`PYTHONPATH`、GitHub 權杖）。父類只剝 SDD 寫入面的三個名字，所以哨兵值會一路走到
    假 claude。"""

    def _child_env(self) -> dict[str, str]:
        env = super()._child_env()
        return {k: v for k, v in env.items()
                if not k.upper().startswith(_STRIPPED_PREFIXES)
                and k.upper() not in _STRIPPED_NAMES}


class ResearchRunManager(RunManager):
    """`db=None`（不鏡射 `execution_runs`／`execution_steps`）的 RunManager；handle 換成
    `ResearchRunHandle`。不改 `runner.py`。"""

    def _materialize(self, req: RunCreateIn, run_id: str, exec_path: Path, info: Any,
                     plan: Any = None) -> RunHandle:
        handle = super()._materialize(req, run_id, exec_path, info, plan)
        handle.__class__ = ResearchRunHandle
        return handle


# ── 值物件 ───────────────────────────────────────────────────────────────────────────────────
class StageFailed(Exception):
    """一個 stage run 以確定的理由失敗（`exit_reason` 進 `research_stage_runs`）。"""

    def __init__(self, exit_reason: str, detail: str = "") -> None:
        super().__init__(f"{exit_reason}: {detail}" if detail else exit_reason)
        self.exit_reason = exit_reason
        self.detail = detail


class StageCancelled(Exception):
    """cancel 端點已標記取消：資料庫由路由處理函式寫，這裡只停手。"""


@dataclass
class StagePlan:
    """一個已編譯、已建列的 stage run。"""

    stage: str                      # research｜draft｜review｜revise（小寫）
    run_id: str
    round_no: int
    attempt: int
    compiled: CompiledStage
    trigger_kind: str | None = None
    iterate: bool = False


@dataclass
class Outcome:
    status: str                     # SUCCEEDED｜FAILED｜CANCELLED
    exit_reason: str = ""
    verdict: str | None = None      # 審查輪的 PASS｜REVISE｜ESCALATE
    detail: str = ""


def derive_exit_reason(reason: str, log_tail: str = "") -> str:
    """引擎 run 失敗理由 → 本模組的 `exit_reason`（`step_timeout`｜`token_guard_halt`｜`quota`｜
    `evaluator_failed`｜`engine_failed`）。依 `RunHandle.rec.reason` 與引擎日誌尾段的固定字樣
    判斷。"""
    text = f"{reason}\n{log_tail}".lower()
    if "[quota_limit]" in text or "usage limit" in text or "rate_limit" in text:
        return "quota"
    if "停機（halted）" in reason or "halted=true" in text or "token_halt" in text:
        return "token_guard_halt"
    if "timeout" in text or "timed out" in text or "逾時" in text or "超時" in text:
        return "step_timeout"
    if "評估指令失敗" in reason or "escalation" in text:
        return "evaluator_failed"
    return "engine_failed"


def _safe_path(path: str) -> str:
    return _JSON_PATH_SAFE.sub("_", path)[:40]


def _sha(data: bytes) -> str:
    return layout.sha256_bytes(data)


# ── 審查結果的 pre-gate journal（D-58）──────────────────────────────────────────────────────────
class ReviewJournal:
    """`<outbox>/review-pending/r-<research_id>-<round>.json`：gate 呼叫前先落地的輪結果。
    「標完成」以原子覆寫 `done: true` 表達（不 rename、不 unlink：不新增目錄項原語站點）。"""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _path(self, research_id: str, round_no: int) -> Path:
        return self.directory / f"r-{research_id}-{round_no}.json"

    def write(self, entry: Mapping[str, Any]) -> None:
        text = json.dumps(dict(entry), ensure_ascii=False, indent=1, default=str) + "\n"
        fsutil.write_text_atomic(self._path(entry["research_id"], entry["round_no"]), text)

    def mark_done(self, entry: Mapping[str, Any]) -> None:
        self.write({**entry, "done": True})

    def pending(self) -> list[dict[str, Any]]:
        out = []
        for path in sorted(self.directory.glob("r-*.json")) if self.directory.is_dir() else []:
            try:
                entry = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(entry, dict) and not entry.get("done"):
                out.append(entry)
        return out


# ── Orchestrator ─────────────────────────────────────────────────────────────────────────────
FetchClientFactory = Callable[[Settings, Any], FetchClient]


def default_client_factory(cfg: Settings, allowlist: Any) -> FetchClient:
    return FetchClient.from_settings(cfg, allowlist=allowlist,
                                     github_token=os.environ.get("GITHUB_TOKEN") or None)


@dataclass
class _Ctx:
    """一個 stage run 執行期間用到的專案脈絡。"""

    row: dict[str, Any]
    workspace: Path
    fctx: fsm_ops.FsmCtx
    extra: dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    """啟動與驅動研究 stage run 的唯一處。`start` 建好 QUEUED 列、起執行緒後立即回傳。"""

    def __init__(self, cfg: Settings, audit: AuditLog, db: ResearchDb, writer: DurableWriter, *,
                 fetch_client_factory: FetchClientFactory | None = None,
                 run_manager: RunManager | None = None, poll_seconds: float = 0.05) -> None:
        self.cfg, self.audit, self.db, self.writer = cfg, audit, db, writer
        self.mgr = run_manager or ResearchRunManager(
            cfg, locks=AdvisoryLock(None), audit=audit, db=None)
        self._client_factory = fetch_client_factory or default_client_factory
        self._poll = poll_seconds
        self._threads: dict[str, threading.Thread] = {}
        self._cancelled: set[str] = set()
        #: stage run id → 該 run 開始前的游標相態（失敗、取消、回收時游標退回它；D-77）。
        #: 記憶體內：重啟後查不到時改由事件帳推回（`_stable_phase`）。被取消的 run 的條目由
        #: `settle_failed`（取消端點）取走，執行緒收到取消後不碰它。
        self._prior_phase: dict[str, str] = {}
        self._guard = threading.RLock()
        self.journal = ReviewJournal(Path(writer.outbox.path).parent / "review-pending")

    # ── 對外 ─────────────────────────────────────────────────────────────────────────────────
    def start(self, row: dict[str, Any], stage: str, *, requested_by: str,
              after_escalation: bool = False, auto: bool = False) -> dict[str, Any]:
        """建好第一個 stage run 列（QUEUED）、起執行緒、立即回傳（202 的本文）。"""
        rid = str(row["id"])
        self._check_layers(row, stage)
        first = "revise" if stage == "iterate" else stage
        plan = self._new_plan(row, first, requested_by=requested_by, iterate=stage == "iterate",
                              auto=auto)
        self._insert_run(rid, plan, requested_by)
        thread = threading.Thread(
            target=self._chain, args=(rid, plan, stage, after_escalation, requested_by),
            name=f"research-{rid[:8]}", daemon=True)
        with self._guard:
            self._threads[rid] = thread
        thread.start()
        fresh = self.db.get_project(rid) or row
        return {"stage_run_id": plan.run_id, "engine_run_id": plan.run_id,
                "flow": {"step": fresh["flow_step"], "phase": fresh["flow_phase"],
                         "status": fresh["flow_status"], "detail": fresh["flow_detail"]}}

    def stop(self, run_id: str) -> None:
        """cancel 端點的 `stopper`：標記取消並停引擎行程樹；資料庫由路由處理函式標 CANCELLED。"""
        self._cancelled.add(run_id)
        handle = self.mgr.get(run_id)
        if handle is not None:
            try:
                handle.stop()
            except ApiError:
                logger.info("stage run %s 已不在可停止的狀態", run_id)

    def shutdown(self) -> None:
        """Bridge 關閉時停掉仍在跑的引擎 run（行程樹）並關閉引擎端的儲存；`main.py` 的 lifespan
        結束段呼叫它（尚未接線時，遺留的 RUNNING 列由下次啟動的 `reap_orphans` 收斂為
        `orphaned`）。"""
        self.mgr.shutdown()

    def join(self, research_id: str | None = None, timeout: float = 120.0) -> bool:
        """等執行緒結束（測試與優雅關閉用）；回是否全部結束。"""
        with self._guard:
            threads = [t for rid, t in self._threads.items() if research_id in (None, rid)]
        deadline = time.monotonic() + timeout
        for thread in threads:
            thread.join(max(0.0, deadline - time.monotonic()))
        return not any(t.is_alive() for t in threads)

    def reap_orphans(self) -> list[str]:
        """啟動時：上一個 Bridge 行程留下的 QUEUED／RUNNING stage run 一律 FAILED（`orphaned`；
        不寫輪列、不耗預算）；游標退回該 run 開始前的穩定相態、`flow_status` 為 FAILED 並寫明原因
        （D-77）；未收尾的審查 journal 依 D-58 補完。"""
        reaped: list[str] = []
        rows = self.db.query(
            "SELECT id, research_id FROM {s}.research_stage_runs "
            "WHERE status IN ('QUEUED', 'RUNNING')")
        for run in rows:
            rid, run_id = str(run["research_id"]), str(run["id"])
            self.writer.persist(Op("stage_run.update", rid, {
                "stage_run_id": run_id, "status": "FAILED", "exit_reason": "orphaned",
                "finished_at": utc_now().isoformat(), "actor": "bridge"}))
            self.settle_failed(rid, "orphaned", run_ids=(run_id,))
            reaped.append(run_id)
        for entry in self.journal.pending():
            try:
                self._finish_review(self._project(str(entry["research_id"])), entry)
            except Exception:                                   # noqa: BLE001
                logger.exception("審查 journal 重放失敗：%s", entry.get("research_id"))
        return reaped

    # ── 專案脈絡 ─────────────────────────────────────────────────────────────────────────────
    def _project(self, rid: str) -> dict[str, Any]:
        row = self.db.get_project(rid)
        if row is None:
            raise ApiError(404, "research_not_found", research_id=rid)
        return row

    def _fsm(self, row: Mapping[str, Any]) -> fsm_ops.FsmCtx:
        return fsm_ops.FsmCtx(sdd_root=self.cfg.sdd_root, state_dir=Path(row["fsm_state_dir"]),
                              key=row["fsm_project"], audit=self.audit, actor="bridge")

    def _fsm_state(self, row: Mapping[str, Any]) -> str | None:
        try:
            return fsm_ops.current_state(self._fsm(row))
        except ApiError:
            return None

    def _one(self, sql: str, params: Sequence[Any]) -> dict[str, Any] | None:
        rows = self.db.query(sql, params)
        return rows[0] if rows else None

    # ── 游標（flow_status 一律衍生）───────────────────────────────────────────────────────────
    def _sync_flow(self, rid: str, *, step: str | None = None, phase: str | None = None,
                   detail: str | None = None, failed: bool = False, actor: str = "bridge") -> None:
        """寫游標：`flow_status` 一律由 `derive_flow_status` 衍生（`failed`＝這次收尾是 stage run
        失敗、取消或回收，D-77）；與現值相同就不寫。"""
        row = self._project(rid)
        runs = self.db.query("SELECT status FROM {s}.research_stage_runs WHERE research_id = %s "
                             "AND status IN ('QUEUED', 'RUNNING')", (rid,))
        status = derive_flow_status([r["status"] for r in runs], self._fsm_state(row),
                                    last_run_failed=failed)
        flow = {"step": step or row["flow_step"], "phase": phase or row["flow_phase"],
                "status": status, "detail": row["flow_detail"] if detail is None else detail}
        if flow != {"step": row["flow_step"], "phase": row["flow_phase"],
                    "status": row["flow_status"], "detail": row["flow_detail"]}:
            self.writer.persist(Op("project.cursor", rid, {
                "research_id": rid, "actor": actor, "flow": flow}))
        self.project_state(rid)

    def settle_failed(self, rid: str, exit_reason: str, *, run_ids: Sequence[str] = (),
                      actor: str = "bridge") -> None:
        """stage run 失敗、取消或被回收之後的游標收尾（D-77；三者同一條路）：相態退回該 run
        開始前的穩定相態（RESEARCHING 這類只在 run 進行中才成立的相態不留在游標上，否則
        `stages/research` 的前置相態永遠不滿足）、`flow_status` 為 FAILED（FSM 在 ESCALATION 類時
        仍是 ESCALATED）、`flow_detail` 寫 `exit_reason`。`run_ids`＝剛結束的 run（取記憶體內的
        開始前相態；查不到由 `_stable_phase` 從事件帳推回）。"""
        with self._guard:
            known = [self._prior_phase.pop(run_id, None) for run_id in run_ids]
        prior = next((phase for phase in known if phase), None)
        row = self._project(rid)
        phase = prior or self._stable_phase(rid, str(row["flow_phase"]))
        self._sync_flow(rid, phase=phase, detail=exit_reason, failed=True, actor=actor)

    def _stable_phase(self, rid: str, current: str) -> str:
        """查不到 run 開始前相態時（Bridge 重啟後的孤兒回收、直接建列的 run）的穩定相態：
        `RESEARCHING` 只在研究 run 進行中成立，退回事件帳（`research.step`，append-only）裡最近
        一次記錄的研究步驟穩定相態（INGESTED 或 EVIDENCE_READY；沒有記錄＝INGESTED，建立專案時的
        相態）；其餘相態原樣。"""
        if current != "RESEARCHING":
            return current
        last = self._one(
            "SELECT payload->>'flowPhase' AS phase FROM {s}.research_events WHERE research_id = %s "
            "AND event_type = 'research.step' AND payload->>'flowStep' = 'topic' "
            "AND payload->>'flowPhase' IN ('INGESTED', 'EVIDENCE_READY') ORDER BY seq DESC LIMIT 1",
            (rid,))
        return str(last["phase"]) if last else "INGESTED"

    def project_state(self, rid: str) -> None:
        """`02_governance/state.json` 匯出（只寫、從不讀回）；失敗不拖垮流程。"""
        try:
            row = self._project(rid)
            runs = self.db.query(
                "SELECT stage, round_no, attempt, status, exit_reason FROM "
                "{s}.research_stage_runs WHERE research_id = %s ORDER BY created_at", (rid,))
            fsm = fsm_ops.snapshot(self._fsm(row))
            projection = export.build_state_projection(
                research_id=rid, flow={"step": row["flow_step"], "phase": row["flow_phase"],
                                       "status": row["flow_status"]},
                fsm=fsm, runs=runs, projected_at=utc_now())
            layout.write_workspace_file(Path(row["workspace_path"]), layout.STATE_JSON_REL,
                                        export.render_state_json(projection))
        except (OSError, ApiError):
            logger.warning("state.json 投影失敗（研究 %s）", rid)

    # ── 啟動前檢查與編譯 ─────────────────────────────────────────────────────────────────────
    def _effective_web(self) -> tuple[list[str], list[dict[str, Any]]]:
        rows = self.db.list_allowlist()
        hosts = list(self.cfg.research_web_allowlist)
        hosts += [r["host"] for r in rows if r["list_kind"] == "WEB" and r["enabled"]
                  and r["host"] not in hosts]
        return hosts, rows

    def _check_layers(self, row: Mapping[str, Any], stage: str) -> None:
        scope = row.get("scope") or {}
        if stage == "research" and (scope.get("layers") or {}).get("industry") and not (
                self._effective_web()[0]):
            raise ApiError(422, "layer_unavailable", violations=[{
                "field": "scope.layers.industry", "rule": "web_layer_disabled",
                "message": "產業層需要 Web 層（有效 Web 清單為空）"}])

    def _allowlist_snapshot(self) -> list[dict[str, Any]]:
        web, rows = self._effective_web()
        fetch = build_effective_allowlist(self.cfg.research_fetch_allowlist, rows).snapshot()
        admin = {r["host"]: r for r in rows if r["list_kind"] == "WEB" and r["enabled"]}
        snap = [{"host": h, "list_kind": "WEB", "source": "ADMIN" if h in admin else "ENV",
                 "layer": (admin.get(h) or {}).get("layer"),
                 "min_interval_seconds": int((admin.get(h) or {}).get("min_interval_seconds", 3))}
                for h in web]
        return [*fetch, *snap]

    def _new_plan(self, row: dict[str, Any], stage: str, *, requested_by: str, iterate: bool,
                  auto: bool) -> StagePlan:
        rid, ws = str(row["id"]), Path(row["workspace_path"])
        state = self.db.review_state(rid)
        completed = int(state["completed"])
        round_no = {"review": completed + 1, "revise": completed}.get(stage, 0)
        prev = self._one("SELECT COALESCE(MAX(attempt), 0) AS n FROM {s}.research_stage_runs "
                         "WHERE research_id = %s AND stage = %s AND round_no = %s",
                         (rid, stage.upper(), round_no))
        attempt = int(prev["n"]) + 1 if prev else 1
        head = self.db.head_prd(rid)
        values: dict[str, Any] = {}
        trigger = None
        if stage == "research":
            scope_file = ws / layout.ISSUE_SCOPE_REL
            values["issue_scope_sha256"] = _sha(scope_file.read_bytes())
            values["supplement"] = (ws / "00_research" / "evidence_items.json").is_file()
            values["budget_note"] = self._budget_note(row)
            values["accept_template_sentinel"] = bool(
                os.environ.get("MOCK_CLAUDE_RESEARCH_SCRIPT", "").strip())  # 空字串＝未設
        elif stage in ("review", "revise") and head is not None:
            values["prd_rel"] = str(head["rel_path"])
            if stage == "review":
                text = (ws / head["rel_path"]).read_bytes()
                if _sha(text) != head["sha256"]:
                    raise ApiError(409, "stage_conflict", details={"cause": "prd_file_changed"})
                values.update(prd_sha256=head["sha256"],
                              ac_total=count_acs(text.decode("utf-8")))
                trigger = self._trigger_kind(row, iterate=iterate, auto=auto)
            else:
                self._write_defects(rid, ws, completed)
        if values.get("supplement"):
            layout.write_workspace_file(ws, PREVIOUS_EVIDENCE_REL, (
                ws / "00_research" / "evidence_items.json").read_text(encoding="utf-8"))
        run_id = str(uuid.uuid4())
        # Web 工具只給「專案的產業層有開」的 RESEARCH（AT-960-8-E-2；最小授權：有效 Web 清單非空
        # 還不夠，沒開產業層的專案不需要、也不得拿到 WebSearch／WebFetch）。
        industry = bool(((row.get("scope") or {}).get("layers") or {}).get("industry"))
        web = self._effective_web()[0] if stage == "research" and industry else ()
        try:
            if self.cfg.sdd_root is None:
                raise CompileError("framework_unavailable", "找不到框架樹（SDD_ROOT）")
            compiled = compile_stage(StageRequest(
                stage=stage, slug=row["slug"], workspace=ws.resolve(),
                framework_root=self.cfg.sdd_root,
                step_timeout_seconds=self.cfg.research_step_timeout_seconds,
                claude_command=self.cfg.research_claude_command or DEFAULT_CLAUDE,
                web_hosts=tuple(web), round_no=round_no, scope_rev=int(row["scope_rev"]),
                **values))
            for rel, text in compiled.prompt_files.items():
                layout.write_workspace_file(ws, rel, text)
        except CompileError as exc:
            raise ApiError(503, "compile_failed", detail=str(exc), cause=exc.reason) from exc
        return StagePlan(stage, run_id, round_no, attempt, compiled, trigger, iterate)

    def _budget_note(self, row: Mapping[str, Any]) -> str:
        limits = effective_limits(str(row["depth_level"]))
        return (f"預算：每層來源上限 {limits.per_layer}、抓取上限 {limits.total}、"
                f"牆鐘 {self.cfg.research_step_timeout_seconds} 秒；"
                "用盡即停，未完成面寫進 honest_bounds。")

    def _trigger_kind(self, row: Mapping[str, Any], *, iterate: bool, auto: bool) -> str:
        if self._fsm_state(row) == "HUMAN_PENDING":
            return "POST_HUMAN"
        return "AUTO" if iterate or auto else "MANUAL"

    def _write_defects(self, rid: str, ws: Path, round_no: int) -> None:
        """修訂的輸入：未結缺陷（OPEN／REGRESSED）＋人工退回意見；不含分數、權重與門檻。"""
        rows = self.db.query(
            "SELECT d.defect_no, d.severity, d.prd_anchor, d.description, d.suggestion "
            "FROM {s}.research_review_defects d JOIN {s}.research_review_rounds r "
            "ON r.id = d.round_id WHERE r.research_id = %s AND d.status IN ('OPEN', 'REGRESSED') "
            "ORDER BY r.round_no, d.defect_no", (rid,))
        human = self.db.query(
            "SELECT reason FROM {s}.research_gate_decisions WHERE research_id = %s "
            "AND gate = 'GATE0' AND decision = 'CHANGES' ORDER BY decided_at", (rid,))
        defects = [{"id": r["defect_no"], "severity": r["severity"], "anchor": r["prd_anchor"],
                    "finding": r["description"], "suggestion": r["suggestion"]} for r in rows]
        defects += [{"id": f"H-{i}", "severity": "P2", "anchor": "§0", "finding": h["reason"],
                     "suggestion": "依人工審查意見修訂"} for i, h in enumerate(human, 1)]
        text = json.dumps({"round": round_no, "defects": defects}, ensure_ascii=False,
                          indent=2) + "\n"
        layout.write_workspace_file(ws, defects_rel(round_no), text)

    def _insert_run(self, rid: str, plan: StagePlan, requested_by: str) -> None:
        compiled = plan.compiled
        self.writer.persist(Op("stage_run.insert", rid, {
            "research_id": rid, "stage_run_id": plan.run_id, "stage": plan.stage.upper(),
            "round_no": plan.round_no, "attempt": plan.attempt,
            "scope_rev": int(self._project(rid)["scope_rev"]), "status": "QUEUED",
            "playbook_sha256": compiled.playbook_sha256, "config_sha256": compiled.config_sha256,
            "prompt_manifest": list(compiled.prompt_manifest),
            "allowlist_snapshot": self._allowlist_snapshot(), "requested_by": requested_by,
            "occurred_at": utc_now().isoformat()}))

    # ── 鏈驅動 ───────────────────────────────────────────────────────────────────────────────
    def _chain(self, rid: str, plan: StagePlan, mode: str, after_escalation: bool,
               requested_by: str) -> None:
        try:
            for _ in range(CHAIN_MAX_ROUNDS * 2 + 2):
                outcome = self._run_one(rid, plan)
                nxt = self._next_plan(rid, plan, outcome, mode, after_escalation, requested_by)
                if nxt is None:
                    break
                plan = nxt
        except StageCancelled:
            logger.info("研究 %s 的 stage 鏈已取消", rid)
        except DbBlocked:
            # 資料庫不可用：寫入器已把 stage run 的 BLOCKED_DB 與 research.alert 暫存在 outbox，
            # 復原後重放即可見（AT-960-2-5）。這裡不再排 FAILED：那會在重放時蓋掉 BLOCKED_DB 終態。
            logger.warning("研究 %s 的 stage 鏈因資料庫不可用而阻塞；outbox 重放後可見", rid)
        except Exception:                                      # noqa: BLE001
            logger.exception("研究 %s 的 stage 鏈崩潰", rid)
            try:
                self._fail_active(rid, "internal_error")
            except Exception:                                  # noqa: BLE001 — 資料庫不可用
                logger.exception("研究 %s 的 stage run 無法標記失敗；重啟時由孤兒回收收斂", rid)
        finally:
            with self._guard:
                self._threads.pop(rid, None)

    def _next_plan(self, rid: str, plan: StagePlan, outcome: Outcome, mode: str,
                   after_escalation: bool, requested_by: str) -> StagePlan | None:
        if outcome.status != "SUCCEEDED":
            return None
        chained = mode == "iterate" or (mode == "revise" and after_escalation)
        if plan.stage == "revise" and chained:
            nxt = "review"
        elif plan.stage == "review" and mode == "iterate" and outcome.verdict == "REVISE":
            nxt = "revise"
        else:
            return None
        row = self._project(rid)
        new = self._new_plan(row, nxt, requested_by=requested_by, iterate=mode == "iterate",
                             auto=True)
        self._insert_run(rid, new, requested_by)
        return new

    def _fail_active(self, rid: str, reason: str) -> None:
        ids: list[str] = []
        for run in self.db.query("SELECT id FROM {s}.research_stage_runs WHERE research_id = %s "
                                 "AND status IN ('QUEUED', 'RUNNING')", (rid,)):
            ids.append(str(run["id"]))
            self.writer.persist(Op("stage_run.update", rid, {
                "stage_run_id": str(run["id"]), "status": "FAILED", "exit_reason": reason,
                "finished_at": utc_now().isoformat(), "actor": "bridge"}))
        self.settle_failed(rid, reason, run_ids=ids)

    def _run_one(self, rid: str, plan: StagePlan) -> Outcome:
        run_id = plan.run_id
        started = utc_now()
        self.writer.persist(Op("stage_run.update", rid, {
            "stage_run_id": run_id, "status": "RUNNING", "started_at": started.isoformat(),
            "actor": "bridge"}))
        row = self._project(rid)
        with self._guard:               # 失敗、取消、回收時游標退回這個相態（D-77）
            self._prior_phase[run_id] = str(row["flow_phase"])
        phase = {"research": "RESEARCHING", "revise": "REVISING"}.get(plan.stage)
        if plan.stage == "review" and plan.trigger_kind != "POST_HUMAN":
            phase = "REVIEWING"
        self._sync_flow(rid, phase=phase)
        outcome = Outcome("FAILED", "engine_failed")
        tokens = 0
        try:
            ctx = _Ctx(row, Path(row["workspace_path"]), self._fsm(row))
            tokens = self._execute(ctx, plan, started)
            outcome = Outcome("SUCCEEDED", verdict=ctx.extra.get("verdict"))
        except StageCancelled:
            raise
        except StageFailed as exc:
            outcome = Outcome("FAILED", exc.exit_reason, detail=exc.detail)
            self._on_failure(rid, plan, exc)
        except ApiError as exc:
            outcome = Outcome("FAILED", "fsm_error" if exc.status_code >= 500 else exc.body.get(
                "reason", "rejected"), detail=str(exc.body)[:300])
        if run_id in self._cancelled:
            raise StageCancelled
        self.writer.persist(Op("stage_run.update", rid, {
            "stage_run_id": run_id, "status": outcome.status, "exit_reason": outcome.exit_reason,
            "tokens_used": tokens, "finished_at": utc_now().isoformat(), "actor": "bridge"}))
        final = not plan.iterate or outcome.status != "SUCCEEDED" or (
            plan.stage == "review" and outcome.verdict != "REVISE")
        if outcome.status != "SUCCEEDED":
            # 失敗不使游標顯示為完成（D-77）：相態退回 stage 開始前的穩定相態、`flow_status` 為
            # FAILED、原因寫進 `flow_detail`——與取消、孤兒回收同一條收尾路徑
            self.settle_failed(rid, outcome.exit_reason, run_ids=(run_id,))
            return outcome
        with self._guard:
            self._prior_phase.pop(run_id, None)
        if final or plan.stage == "review":
            self._sync_flow(rid, detail="")
        return outcome

    def _on_failure(self, rid: str, plan: StagePlan, exc: StageFailed) -> None:
        """失敗的善後：REVIEW_INVALID 發事件（不寫輪列、不佔輪號、不耗預算）；游標寫明原因。"""
        if exc.exit_reason == "review_invalid":
            self.writer.persist(Op("event.append", rid, {
                "research_id": rid, "event_type": "research.review_invalid", "actor": "bridge",
                "payload": {"stageRunId": plan.run_id, "roundNo": plan.round_no,
                            "attempt": plan.attempt, "reason": exc.detail[:300]},
                "ref_kind": "stage_run", "ref_id": plan.run_id}))

    # ── 執行一個 stage run ───────────────────────────────────────────────────────────────────
    def _check_cancel(self, run_id: str) -> None:
        if run_id in self._cancelled:
            raise StageCancelled

    def _execute(self, ctx: _Ctx, plan: StagePlan, started: datetime) -> int:
        if plan.stage == "research":
            return self._research(ctx, plan)
        if plan.stage == "draft":
            return self._author(ctx, plan, revise=False)
        if plan.stage == "revise":
            return self._author(ctx, plan, revise=True)
        return self._review(ctx, plan, started)

    def _engine(self, ctx: _Ctx, plan: StagePlan) -> int:
        """起引擎 run 並等它終止；回 token 用量。失敗＝`StageFailed`（依引擎理由分類）。"""
        self._check_cancel(plan.run_id)
        compiled = plan.compiled
        req = RunCreateIn(
            run_id=uuid.UUID(plan.run_id), project=f"research-{ctx.row['slug']}",
            execution_path=str(ctx.workspace),
            playbook=PlaybookIn.model_validate(compiled.playbook),
            config_overrides=compiled.config_overrides, env=compiled.env, fresh=True)
        try:
            handle = self.mgr.create(req)
        except ApiError as exc:
            raise StageFailed("engine_rejected", str(exc.body)[:300]) from exc
        limit = self.cfg.research_step_timeout_seconds
        steps = len(compiled.steps)
        budget = steps * (compiled.playbook["global_invariants"]["max_retries_per_step"] + 1) * (
            limit + 30) + 60
        deadline = time.monotonic() + budget
        seen: tuple[Any, Any] = (None, None)
        since = time.monotonic()
        while handle.rec.status not in TERMINAL_ENGINE:
            if plan.run_id in self._cancelled:
                raise StageCancelled
            now = time.monotonic()
            key = (handle.rec.current_step, handle.rec.attempt)
            if key != seen:                          # 換步驟或換 attempt：重新計這一步的牆鐘
                seen, since = key, now
            elif key[0] is not None and now - since > limit:
                # 引擎的 Kernel 路徑固定以 600 秒為步驟逾時（`playbook.global_invariants` 沒有
                # `step_timeout_seconds` 欄位，`config.playbook.step_timeout_seconds` 只有
                # 舊路徑讀）：`BRIDGE_RESEARCH_STEP_TIMEOUT_SECONDS` 由這裡的看門狗負責執行。
                handle.stop()
                raise StageFailed("step_timeout", f"步驟 {key[0]} 超過牆鐘 {limit} 秒")
            if now > deadline:
                handle.stop()
                raise StageFailed("step_timeout", "stage 牆鐘用盡")
            time.sleep(self._poll)
        tokens = int(getattr(handle.rec, "tokens_used", 0) or 0)
        self._check_cancel(plan.run_id)
        if handle.rec.status != "COMPLETED":
            reason, tail = str(handle.rec.reason or ""), self._log_tail(handle)
            logger.warning("stage run %s 的引擎 run 以 %s 結束：%s", plan.run_id,
                           handle.rec.status, reason[:300] + "｜" + tail[-600:])
            raise StageFailed(derive_exit_reason(reason, tail), reason[:300])
        return tokens

    @staticmethod
    def _log_tail(handle: RunHandle) -> str:
        try:
            logs = sorted(handle.paths.logs.glob("*.log"))
            return "".join(p.read_text(encoding="utf-8", errors="replace")[-1500:] for p in logs)
        except OSError:
            return ""

    # ── RESEARCH ─────────────────────────────────────────────────────────────────────────────
    def _research(self, ctx: _Ctx, plan: StagePlan) -> int:
        self._prefetch(ctx, plan)
        tokens = self._engine(ctx, plan)
        self._ingest_evidence(ctx, plan)
        return tokens

    def _research_tasks(self, row: Mapping[str, Any], per_layer: int) -> list[Any]:
        scope = row.get("scope") or {}
        layers = scope.get("layers") or {}
        query = str(row["topic"])[:200]
        kinds = [k for flag, ks in (("academic", ("arxiv", "semantic_scholar")),
                                    ("oss", ("github",)), ("community", ("stackexchange",)))
                 if layers.get(flag) for k in ks]
        tasks = []
        for kind in kinds:
            try:
                tasks.append(task_for(kind, query, limit=per_layer))
            except ValueError:               # 例：議題沒有 ASCII 詞，arXiv 查詢組不出來——略過該來源
                logger.info("議題無法組成 %s 的查詢，略過", kind)
        return tasks

    def _offline_reason(self) -> str | None:
        """前置抓取是否不得連網（D-78）：連線層是正式預設（`default_client_factory`）時，遇到劇本模式或
        mock-only 一律離線；換了抓取層（測試注入假連線層）的呼叫端自備連線層，照原路徑走。"""
        if self._client_factory is not default_client_factory:
            return None
        return offline_reason(self.cfg)

    def _fetch_batch(self, ctx: _Ctx, plan: StagePlan) -> FetchBatch | None:
        """前置抓取的結果批次：離線＝夾具（沒有夾具＝空批次，`no_sources` 但不外呼）；本機模式＝
        真抓取（議題組不出任何查詢＝None，沒有批次）。兩條路產出同形的 `FetchBatch`，入庫共用
        `_prefetch`。"""
        reason = self._offline_reason()
        if reason is not None:
            logger.info("研究 %s 的前置抓取走離線夾具（%s）：不連網", ctx.row["id"], reason)
            try:
                return load_batch(fixture_file())
            except OfflineFixtureError as exc:
                raise StageFailed("prefetch_fixture_invalid", str(exc)[:300]) from exc
        limits = effective_limits(str(ctx.row["depth_level"]))
        tasks = self._research_tasks(ctx.row, limits.per_layer)
        if not tasks:
            return None
        self._check_cancel(plan.run_id)
        allow = build_effective_allowlist(self.cfg.research_fetch_allowlist,
                                          self.db.list_allowlist())
        return run_prefetch(self._client_factory(self.cfg, allow), tasks,
                            depth_level=str(ctx.row["depth_level"]), now=utc_now())

    def _prefetch(self, ctx: _Ctx, plan: StagePlan) -> None:
        """前置抓取（API 層）：落地原文、逐筆入庫（含被拒者）、寫 `prefetch_index.json`。批次來自
        `_fetch_batch`（本機模式＝Bridge 原生抓取；劇本模式與 mock-only＝離線夾具），入庫路徑
        只有一條。"""
        rid, ws = str(ctx.row["id"]), ctx.workspace
        index: dict[str, Any] = {"fetches": {}, "candidates": []}
        batch = self._fetch_batch(ctx, plan)
        if batch is not None:
            numbers: dict[int, str] = {}
            for record in batch.records:
                body = {**record.to_db(), "source_id": None, "stage_run_id": plan.run_id}
                files, writes = (), ()
                if record.raw_text is not None and record.raw_rel_path:
                    files = (FileRef(str(ws), record.raw_rel_path, record.raw_sha256 or ""),)
                    writes = (FileWrite(ws, record.raw_rel_path, record.raw_text, overwrite=False),)
                result = self.writer.persist(Op("fetch.insert", rid, {
                    "research_id": rid, "fetch": body}, files=files), writes=writes)
                numbers[id(record)] = str(result.get("fetch_no"))
                index["fetches"][numbers[id(record)]] = {
                    "observed_by": record.observed_by, "outcome": record.outcome, "url": record.url,
                    "layer": record.layer, "raw_rel_path": record.raw_rel_path,
                    "raw_sha256": record.raw_sha256}
            for bundle in batch.sources:
                refs = [numbers[id(r)] for r in bundle.records if id(r) in numbers]
                index["candidates"].append({**bundle.source, "fetch_refs": refs})
            if batch.skipped:
                self.writer.persist(Op("event.append", rid, {
                    "research_id": rid, "event_type": "research.alert", "actor": "bridge",
                    "payload": {"kind": "FETCH_SKIPPED_OVER_LIMIT", "detail": json.dumps(
                        [s.to_payload() for s in batch.skipped],
                        ensure_ascii=False)[:4000]},
                    "ref_kind": "alert", "ref_id": str(uuid.uuid4())}))
        layout.write_workspace_file(ws, PREFETCH_INDEX_REL,
                                    json.dumps(index, ensure_ascii=False, indent=1) + "\n")
        web = bool(self._effective_web()[0]) and bool((ctx.row.get("scope") or {}).get(
            "layers", {}).get("industry"))
        if batch is not None and batch.exit_reason == "no_evidence" and not web:
            raise StageFailed("no_evidence", "所有抓取失敗或沒有可用來源")

    def _evidence_context(self, ctx: _Ctx, plan: StagePlan) -> EvidenceContext:
        ws = ctx.workspace
        scope = json.loads((ws / layout.ISSUE_SCOPE_REL).read_text(encoding="utf-8"))
        index = json.loads((ws / PREFETCH_INDEX_REL).read_text(encoding="utf-8"))
        prev = ws / PREVIOUS_EVIDENCE_REL
        return EvidenceContext(
            issue_scope=scope, issue_scope_sha256=_sha((ws / layout.ISSUE_SCOPE_REL).read_bytes()),
            accept_template_sentinel=bool(
                os.environ.get("MOCK_CLAUDE_RESEARCH_SCRIPT", "").strip()),
            fetch_index=index.get("fetches") or {},
            previous=json.loads(prev.read_text(encoding="utf-8")) if plan.compiled.steps[0].inputs
            .get("previous") and prev.is_file() else None)

    def _ingest_evidence(self, ctx: _Ctx, plan: StagePlan) -> None:
        """檔→驗→DB：行程內再驗一次（與 evaluator 同一批純函式）、算 UNANCHORED、渲染矩陣、入庫。"""
        rid, ws = str(ctx.row["id"]), ctx.workspace
        path = ws / "00_research" / "evidence_items.json"
        raw = path.read_bytes()
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise StageFailed("evidence_invalid", "evidence_items.json 不是合法 JSON") from exc
        problems = validate_evidence_items(doc, self._evidence_context(ctx, plan))
        if problems:
            raise StageFailed("evidence_invalid", "; ".join(violation_lines(problems))[:300])
        index = json.loads((ws / PREFETCH_INDEX_REL).read_text(encoding="utf-8"))["fetches"]

        def raw_text_of(ref: str) -> str | None:
            rel = (index.get(ref) or {}).get("raw_rel_path")
            try:
                return (ws / rel).read_text(encoding="utf-8") if rel else None
            except OSError:
                return None

        known = [int(r["search_no"]) for r in self.db.query(
            "SELECT search_no FROM {s}.research_fetches WHERE research_id = %s "
            "AND search_no IS NOT NULL", (rid,))]
        last = self._one("SELECT COALESCE(MAX(version), 0) AS n FROM {s}.research_artifacts "
                         "WHERE research_id = %s AND kind = 'EVIDENCE_ITEMS'", (rid,))
        version = int(last["n"]) + 1 if last else 1
        plan_in = plan_ingest(doc, matrix_version=version, raw_text_of=raw_text_of,
                              known_search_nos=known)
        scope = json.loads((ws / layout.ISSUE_SCOPE_REL).read_text(encoding="utf-8"))
        rendered = export.render_evidence_matrix(
            version=version, scope_rev=int(doc["scope_rev"]),
            axes_labels=scope.get("applicability_axes") or [], sources=doc["sources"],
            items=plan_in.items_rendered, counters=doc["counter_evidence"],
            bounds=doc["honest_bounds"],
            fetch_info={k: {"raw_sha256": v.get("raw_sha256")} for k, v in index.items()})
        sha = _sha(raw)
        self.writer.persist(Op("evidence.record", rid, {
            "research_id": rid, "matrix_version": version, "scope_rev": plan_in.scope_rev,
            "stage_run_id": plan.run_id, "actor": RESEARCH_AGENT,
            "artifact": {"rel_path": "00_research/evidence_items.json", "sha256": sha,
                         "bytes": len(raw), "origin": "AGENT", "created_by": RESEARCH_AGENT,
                         "content": raw.decode("utf-8")},
            "sources": plan_in.sources, "items": plan_in.items},
            files=(FileRef(str(ws), "00_research/evidence_items.json", sha),)))
        for search in plan_in.searches:
            self.writer.persist(Op("fetch.insert", rid, {
                "research_id": rid, "fetch": {**search, "stage_run_id": plan.run_id}}))
        writes = [FileWrite(ws, MATRIX_REL, rendered.text),
                  FileWrite(ws, EVIDENCE_INDEX_REL, json.dumps(plan_in.index, ensure_ascii=False,
                                                              indent=1) + "\n"),
                  FileWrite(ws, LICENSE_PENDING_REL, json.dumps(
                      {"license_pending": plan_in.license_pending}, ensure_ascii=False) + "\n"),
                  *[FileWrite(ws, rel, text) for rel, text in rendered.notes.items()]]
        matrix_sha = layout.sha256_text(rendered.text)
        self.writer.persist(Op("artifact.insert", rid, {
            "research_id": rid, "kind": "EVIDENCE_MATRIX", "version": version,
            "rel_path": MATRIX_REL, "sha256": matrix_sha, "bytes": len(rendered.text.encode()),
            "origin": "BRIDGE", "stage_run_id": plan.run_id, "created_by": "bridge"},
            files=(FileRef(str(ws), MATRIX_REL, matrix_sha),)), writes=writes)
        if plan_in.enough:
            self._sync_flow(rid, step="topic", phase="EVIDENCE_READY", detail="")
        else:
            self._sync_flow(rid, step="topic", phase="INGESTED", detail=(
                f"insufficient_evidence:{plan_in.qualifying}/3"))

    # ── DRAFT／REVISE ────────────────────────────────────────────────────────────────────────
    def _author(self, ctx: _Ctx, plan: StagePlan, *, revise: bool) -> int:
        rid, ws = str(ctx.row["id"]), ctx.workspace
        tokens = self._engine(ctx, plan)
        raw = (ws / PRD_DRAFT_REL).read_bytes()
        text = raw.decode("utf-8")
        index = json.loads((ws / EVIDENCE_INDEX_REL).read_text(encoding="utf-8")).get("rows")
        problems = precheck_draft(text, evidence_rows=index)
        if problems:
            raise StageFailed("draft_precheck_failed", "; ".join(violation_lines(problems))[:300])
        if not revise:
            self._advance(ctx.fctx, "SPEC_DRAFTING")
        head = self.db.head_prd(rid)
        version = (int(head["version_no"]) if head else 0) + 1
        sha = _sha(raw)
        summary = f"修訂：回應第 {plan.round_no} 輪缺陷" if revise else "起草"
        self.writer.persist(Op("prd.save", rid, {
            "research_id": rid, "version_no": version, "kind": "DRAFT", "author_kind": "AGENT",
            "author": AUTHOR_AGENT, "content": text, "rel_path": PRD_DRAFT_REL, "sha256": sha,
            "bytes": len(raw), "change_summary": summary, "stage_run_id": plan.run_id,
            "flow": {"step": "studio", "phase": "REVISING" if revise else "DRAFTING",
                     "status": "RUNNING", "detail": ""}},
            files=(FileRef(str(ws), PRD_DRAFT_REL, sha),)))
        adr = (ws / ADR_DRAFT_REL)
        if adr.is_file():
            adr_raw = adr.read_bytes()
            self.writer.persist(Op("artifact.insert", rid, {
                "research_id": rid, "kind": "ADR_DRAFT", "version": version,
                "rel_path": ADR_DRAFT_REL, "sha256": _sha(adr_raw), "bytes": len(adr_raw),
                "origin": "AGENT", "stage_run_id": plan.run_id, "created_by": AUTHOR_AGENT},
                files=(FileRef(str(ws), ADR_DRAFT_REL, _sha(adr_raw)),)))
        return tokens

    def _advance(self, fctx: fsm_ops.FsmCtx, target: str) -> str:
        """把外環鍵推進到 `target`（只走研究面的鏡像邊；已在或超過就不動）。"""
        state = fsm_ops.current_state(fctx)
        order = ("AGENT_LOAD", "SPEC_DRAFTING", "SCG_VALIDATION")
        if state in order and target in order and order.index(state) < order.index(target):
            for nxt in order[order.index(state) + 1: order.index(target) + 1]:
                state = fsm_ops.transition(fctx, to=nxt, reason=f"research stage requires {nxt}")
        return state

    # ── REVIEW ───────────────────────────────────────────────────────────────────────────────
    def _review(self, ctx: _Ctx, plan: StagePlan, started: datetime) -> int:
        rid, ws = str(ctx.row["id"]), ctx.workspace
        head = self.db.head_prd(rid)
        assert head is not None
        text = (ws / head["rel_path"]).read_text(encoding="utf-8")
        checks = precheck_p1(text)
        if precheck_passed(checks):
            if plan.trigger_kind != "POST_HUMAN":
                self._advance(ctx.fctx, "SCG_VALIDATION")
            try:
                tokens = self._engine(ctx, plan)
            except StageFailed as exc:
                if exc.exit_reason in ("evaluator_failed", "engine_failed"):
                    self._read_dimensions(ctx, plan, head, text)     # 檔案不合＝REVIEW_INVALID
                raise
            dims = self._read_dimensions(ctx, plan, head, text)
        else:
            tokens, dims = 0, None
        self._check_cancel(plan.run_id)
        entry = self._journal_entry(ctx, plan, head, checks, dims, started)
        self.journal.write(entry)
        ctx.extra["verdict"] = self._finish_review(ctx.row, entry)["verdict"]
        return tokens

    def _read_dimensions(self, ctx: _Ctx, plan: StagePlan, head: Mapping[str, Any],
                         text: str) -> dict[str, dict[str, Any]]:
        """四維單維度 JSON：行程內再驗一次；任一不合＝REVIEW_INVALID（原因只含維度與規則）。"""
        ws, k = ctx.workspace, plan.round_no
        index = json.loads((ws / EVIDENCE_INDEX_REL).read_text(encoding="utf-8")).get("rows") or {}
        out: dict[str, dict[str, Any]] = {}
        reasons: list[str] = []
        for dimension in DIMENSIONS:
            rel = f"02_governance/reviews/round-{k}/{dimension.lower()}.json"
            try:
                raw = (ws / rel).read_bytes()
                doc = json.loads(raw.decode("utf-8"))
            except (OSError, UnicodeDecodeError, ValueError):
                reasons.append(f"{dimension} R1 file")
                continue
            problems = validate_review_dimension(
                doc, dimension=dimension, round_no=k, prd_sha256=str(head["sha256"]),
                ac_total=count_acs(text), evidence_numbers=index.keys())
            if problems:
                reasons += [f"{dimension} {v.rule} {_safe_path(v.path)}" for v in problems[:3]]
                continue
            out[dimension] = {"doc": doc, "raw_sha256": _sha(raw), "rel": rel}
        if reasons:
            raise StageFailed("review_invalid", "; ".join(reasons))
        return out

    def _journal_entry(self, ctx: _Ctx, plan: StagePlan, head: Mapping[str, Any],
                       checks: Sequence[Any], dims: dict[str, dict[str, Any]] | None,
                       started: datetime) -> dict[str, Any]:
        """gate 之前就要落地的輪結果（聚合分數、四維分數、缺陷、`prd_version_no`、`trigger_kind`）；
        尚無 `fsm_gate_result`、`fsm_retry_count`、`verdict`。"""
        k, rid = plan.round_no, str(ctx.row["id"])
        personas = {p.role: p for p in plan.compiled.personas}
        scores, defects, p1 = [], [], 0
        if dims is not None:
            for dimension in DIMENSIONS:
                doc = dims[dimension]["doc"]
                persona = personas[f"review-{dimension.lower()}"]
                scores.append({
                    "dimension": dimension, "score": int(doc["score"]),
                    "agent_id": RUBRIC_REGISTRY[dimension]["agent_id"],
                    "assist_agent_id": persona.assist_agent_id,
                    "assist_agent_yaml_sha256": persona.assist_yaml_sha256,
                    "agent_yaml_path": persona.agent_yaml, "agent_yaml_sha256": persona.yaml_sha256,
                    "persona_sha256": persona.persona_sha256, "summary": str(doc["summary"])[:600],
                    "raw_rel_path": dims[dimension]["rel"],
                    "raw_sha256": dims[dimension]["raw_sha256"], "stage_run_id": plan.run_id})
                for item in doc["defects"]:
                    defects.append({
                        "defect_no": f"D-{k}-{len(defects) + 1:03d}", "dimension": dimension,
                        "severity": item["severity"], "code": item["code"],
                        "prd_anchor": item["prd_anchor"], "description": item["description"],
                        "suggestion": item.get("suggestion", ""),
                        "evidence_refs": list(item.get("evidence_refs") or [])})
                    p1 += item["severity"] == "P1"
        inputs = aggregate.RoundInputs(dims is not None, {s["dimension"]: s["score"] for s in
                                                          scores} if dims is not None else None, p1)
        judgement = aggregate.judge(inputs)
        post_human = plan.trigger_kind == "POST_HUMAN"
        intent = None if judgement.passed and post_human else (
            "PASS" if judgement.passed else "FAIL")
        return {
            "v": 1, "research_id": rid, "round_no": k, "stage_run_id": plan.run_id, "done": False,
            "trigger_kind": plan.trigger_kind, "prd_version_no": int(head["version_no"]),
            "prd_text_sha256": head["sha256"], "precheck": precheck_to_detail(checks),
            "precheck_passed": dims is not None, "scores": scores, "defects": defects,
            "open_p1_count": p1, "weighted_score": aggregate.format_weighted(
                judgement.weighted_total), "min_dimension_score": judgement.min_dimension_score,
            "passed": judgement.passed, "gate_intent": intent,
            "gate_reason": (f"R2P review round {k} {'pass' if judgement.passed else 'fail'} "
                            f"(stage_run {plan.run_id})"),
            "fsm_generation": int(ctx.row["fsm_generation"]),
            "started_at": started.isoformat(), "finished_at": utc_now().isoformat()}

    # ── gate 與輪列（D-58）───────────────────────────────────────────────────────────────────
    def _call_gate(self, fctx: fsm_ops.FsmCtx, state: str, intent: str,
                   reason: str) -> dict[str, Any] | None:
        """`gate SCG_VALIDATION` 的唯一呼叫處。靜態 FAIL 任何現態皆可（人工退回與 POST_HUMAN 未通過
        走這裡）；PASS 只在現態不為 HUMAN_PENDING 時才呼叫（D-50：那裡 PASS 是非法轉態）。"""
        if intent == "FAIL":
            return fsm_ops.gate(fctx, gate="SCG_VALIDATION", result="FAIL", reason=reason)
        if state != "HUMAN_PENDING":
            return fsm_ops.gate(fctx, gate="SCG_VALIDATION", result=intent, reason=reason)
        return None

    def _gate_history(self, fctx: fsm_ops.FsmCtx, token: str) -> dict[str, Any] | None:
        """以 FSM `show` 判斷帶這個記號的 gate 是否已呼叫；已呼叫回「等同 gate 回傳」的資料。"""
        shown = fsm_ops.show(fctx)
        trace = [t for t in shown.get("decision_trace") or [] if token in str(t.get("reason", ""))]
        entries = [h for h in ((shown.get("retry_history") or {}).get(GATE) or {}).get(
            "history") or [] if token in str(h.get("failure_reason", ""))]
        if not trace and not entries:
            return None
        if entries:
            count = int(entries[-1]["attempt"])
            nxt = str(trace[-1].get("to")) if trace else str(shown.get("current_state"))
            return {"retry_count": count, "escalated": nxt in ESCALATED_STATES or (
                count >= SCG_RETRY_LIMIT), "next_state": nxt, "result": "FAIL"}
        return {"retry_count": 0, "escalated": False, "result": "PASS",
                "next_state": str(trace[-1].get("to"))}

    def _resolve_gate(self, row: Mapping[str, Any],
                      entry: Mapping[str, Any]) -> dict[str, Any] | None:
        intent = entry["gate_intent"]
        if intent is None:
            return None                                 # POST_HUMAN 通過輪：從不補呼叫 gate PASS
        fctx = self._fsm(row)
        token = f"stage_run {entry['stage_run_id']}"
        done = self._gate_history(fctx, token)
        if done is not None:
            return done
        state = fsm_ops.current_state(fctx)             # 呼叫前即時讀，不看 DB 游標
        if state != "HUMAN_PENDING":
            state = self._advance(fctx, "SCG_VALIDATION")
        return self._call_gate(fctx, state, intent, str(entry["gate_reason"]))

    def _finish_review(self, row: Mapping[str, Any], entry: Mapping[str, Any]) -> dict[str, Any]:
        """gate 回傳後的同交易寫入（輪列、四維分數、缺陷、`research.review`）與善後。"""
        rid, ws, k = str(row["id"]), Path(row["workspace_path"]), int(entry["round_no"])
        existing = self._one("SELECT id, verdict, passed, escalated FROM "
                             "{s}.research_review_rounds WHERE research_id = %s AND round_no = %s",
                             (rid, k))
        if existing is not None:                         # 重放：輪列早已寫入
            self.journal.mark_done(entry)
            return {"verdict": existing["verdict"], "passed": existing["passed"]}
        gate_result = self._resolve_gate(row, entry)
        post_human = entry["trigger_kind"] == "POST_HUMAN"
        inputs = aggregate.RoundInputs(
            bool(entry["precheck_passed"]),
            {s["dimension"]: int(s["score"]) for s in entry["scores"]} or None,
            int(entry["open_p1_count"]))
        decision = aggregate.decide(inputs, gate_result, post_human=post_human)
        round_row = {
            "id": str(uuid.uuid4()), "round_no": k, "fsm_generation": entry["fsm_generation"],
            "prd_version_no": entry["prd_version_no"], "trigger_kind": entry["trigger_kind"],
            "precheck_passed": bool(entry["precheck_passed"]),
            "precheck_detail": entry["precheck"], "weighted_score": entry["weighted_score"],
            "min_dimension_score": entry["min_dimension_score"],
            "open_p1_count": entry["open_p1_count"], "passed": decision.judgement.passed,
            "verdict": decision.verdict,
            "fsm_gate_result": None if gate_result is None else (
                "PASS" if decision.judgement.passed else "FAIL"),
            "fsm_retry_count": None if gate_result is None else (
                0 if decision.judgement.passed else int(gate_result["retry_count"])),
            "escalated": decision.escalated, "stage_run_id": entry["stage_run_id"],
            "started_at": entry["started_at"], "finished_at": entry["finished_at"]}
        previous = self.db.query(
            "SELECT d.id, d.defect_no, d.code, d.prd_anchor AS anchor, d.status FROM "
            "{s}.research_review_defects d JOIN {s}.research_review_rounds r ON r.id = d.round_id "
            "WHERE r.research_id = %s", (rid,))
        prd_text = (ws / PRD_DRAFT_REL).read_text(encoding="utf-8") if (
            ws / PRD_DRAFT_REL).is_file() else None
        transitions = plan_defect_transitions(
            previous, [(d["code"], d["prd_anchor"]) for d in entry["defects"]],
            prd_version_no=int(entry["prd_version_no"]), prd_text=prd_text)
        self.writer.persist(Op("review.round", rid, {
            "research_id": rid, "round": round_row, "scores": entry["scores"],
            "defects": entry["defects"], "actor": "bridge"}))
        for change in transitions:
            self.writer.persist(Op("defect.update", rid, {
                "defect_id": change.defect_id, "status": change.new_status,
                "fixed_in_version_no": change.fixed_in_version_no, "actor": "bridge"}))
        self.journal.mark_done(entry)
        self._render_card(row, k, gate_result, decision)
        self._sync_flow(
            rid, step="studio",
            phase="GATE0_PENDING" if decision.judgement.passed else (
                "REVIEWING" if decision.escalated else "REVISING"), detail="")
        return {"verdict": decision.verdict, "passed": decision.judgement.passed}

    def _render_card(self, row: Mapping[str, Any], round_no: int,
                     gate_result: Mapping[str, Any] | None, decision: aggregate.Decision) -> None:
        """`review_card.json`（DB→渲染→檔）：每輪重新彙整並登記一個 REVIEW_CARD 版本。"""
        rid, ws = str(row["id"]), Path(row["workspace_path"])
        rounds = self.db.query("SELECT * FROM {s}.research_review_rounds WHERE research_id = %s "
                               "ORDER BY round_no", (rid,))
        scores = self.db.query(
            "SELECT s.*, r.round_no FROM {s}.research_review_scores s JOIN "
            "{s}.research_review_rounds r ON r.id = s.round_id WHERE r.research_id = %s", (rid,))
        defects = self.db.query(
            "SELECT d.*, r.round_no FROM {s}.research_review_defects d JOIN "
            "{s}.research_review_rounds r ON r.id = d.round_id WHERE r.research_id = %s "
            "ORDER BY d.defect_no", (rid,))
        versions = self.db.query("SELECT version_no, semver, sha256 FROM "
                                 "{s}.research_prd_versions WHERE research_id = %s", (rid,))
        semver = {int(v["version_no"]): v["semver"] for v in versions}
        shas = {int(v["version_no"]): v["sha256"] for v in versions}
        order = {d: i for i, d in enumerate(DIMENSIONS)}
        card_rounds = [export.card_round(
            r, sorted((s for s in scores if s["round_no"] == r["round_no"]),
                      key=lambda s: order[s["dimension"]]),
            [d for d in defects if d["round_no"] == r["round_no"]],
            semver_by_no=semver, sha_by_no=shas) for r in rounds]
        last = rounds[-1]
        final = "PASS" if last["passed"] else ("ESCALATED" if last["escalated"] else "IN_PROGRESS")
        card = export.build_review_card(
            rid, card_rounds, final_verdict=final,
            retry_count=None if gate_result is None else int(gate_result.get("retry_count", 0)))
        text = export.render_review_card(card)
        if validate_review_card(json.loads(text)):
            logger.warning("review_card.json 未通過模板驗證（研究 %s 第 %s 輪）", rid, round_no)
        sha = layout.sha256_text(text)
        self.writer.persist(Op("artifact.insert", rid, {
            "research_id": rid, "kind": "REVIEW_CARD", "version": round_no,
            "rel_path": REVIEW_CARD_REL, "sha256": sha, "bytes": len(text.encode("utf-8")),
            "origin": "BRIDGE", "created_by": "bridge"},
            files=(FileRef(str(ws), REVIEW_CARD_REL, sha),)),
            writes=[FileWrite(ws, REVIEW_CARD_REL, text)])

    # ── 對帳（只報告、不修復）────────────────────────────────────────────────────────────────
    def reconcile(self, row: Mapping[str, Any], *, actor: str = "bridge") -> dict[str, Any]:
        """六項對帳：游標與 FSM 對映、PRD、審查卡、證據矩陣的檔案↔資料庫 sha256，以及 P0 沒有的
        拆解與分流。結果追加一筆 `research.reconcile` 事件；檔案與資料列（事件除外）一律不動。"""
        rid, ws = str(row["id"]), Path(row["workspace_path"])
        try:
            state: str | None = fsm_ops.current_state(self._fsm(row))
            readable = True
        except ApiError:
            state, readable = None, False
        approved = self._one(
            "SELECT frozen_digests FROM {s}.research_gate_decisions WHERE research_id = %s "
            "AND gate = 'GATE0' AND decision = 'APPROVED' ORDER BY decided_at DESC LIMIT 1", (rid,))

        def latest(kind: str) -> dict[str, Any] | None:
            return self._one(
                "SELECT rel_path AS path, sha256 FROM {s}.research_artifacts "
                "WHERE research_id = %s AND kind = %s ORDER BY version DESC LIMIT 1", (rid, kind))

        def digests(*paths: str) -> dict[str, str | None]:
            return {p: (d[0] if (d := layout.file_digest(ws, p)) else None) for p in paths}

        # `prd_sha256` 項（INT-10）：核准後＝Gate 0 凍結的每份文件各一個漂移列、kind 依檔
        # （`FROZEN_DOC_KINDS`）；證據矩陣另有自己的對帳項（`evidence_matrix`，比對最新矩陣版本
        # 登記的 sha256），凍結集合裡的那一份由它負責，這裡不重複計入（同一個檔案漂移只算一次）。
        prd: list[dict[str, Any]] = []
        if approved is not None:
            frozen = approved["frozen_digests"] or {}
            prd = [{"path": p, "sha256": str(v).removeprefix("sha256:"),
                    "kind": FROZEN_DOC_KINDS.get(p, "PRD")}
                   for p, v in frozen.items() if p != MATRIX_REL]
        else:
            head = self.db.head_prd(rid)
            prd = [] if head is None else [{"path": head["rel_path"], "sha256": head["sha256"],
                                            "kind": "PRD"}]
        prd_check = file_check("prd_sha256", "PRD", None, None)
        if prd:
            drifts = [file_check("prd_sha256", item["kind"], item, digests(item["path"]))
                      for item in prd]
            bad = [d for c in drifts for d in c["drift"]]
            prd_check = {"id": "prd_sha256", "status": "drift" if bad else "ok", "present": True,
                         "detail": "", "drift": bad}
        checks = [
            mapping_check(state, row["flow_step"], row["flow_phase"], readable=readable,
                          flow_status=row["flow_status"]),
            prd_check]
        for check_id, kind, label in (("review_card", "REVIEW_CARD", "REVIEW_CARD"),
                                      ("evidence_matrix", "EVIDENCE_MATRIX", "EVIDENCE_MATRIX")):
            expected = latest(kind)
            checks.append(file_check(check_id, label, expected, digests(expected["path"])
                                     if expected else None))
        checks += [absent_check("task_decomposition"), absent_check("route_decision")]
        result = reconcile_result(checks)
        self.writer.persist(Op("event.append", rid, {
            "research_id": rid, "event_type": "research.reconcile", "actor": actor[:100],
            "payload": {"consistent": result["consistent"], "driftCount": result["driftCount"]},
            "ref_kind": "reconcile", "ref_id": str(uuid.uuid4())}))
        return result


# ── Gate 0／人工退回的純函式（路由處理函式使用；輸入驗證與理由格式）────────────────────────────
BASELINE_REL = "01_specs/PRD-v1.0.0.md"
#: Gate 0 凍結的四份文件（相對工作區的 POSIX 路徑；第一份是 PRD 基線；不要求 TCS）。
APPROVE_DOCS: tuple[str, ...] = (BASELINE_REL, MATRIX_REL, layout.ISSUE_SCOPE_REL, ADR_DRAFT_REL)
#: 凍結文件各自的對帳 kind（與 `research_artifacts.kind` 同名；INT-10：漂移列的 kind 依檔，
#: 不一律標 PRD）。
FROZEN_DOC_KINDS: Mapping[str, str] = {
    BASELINE_REL: "PRD", MATRIX_REL: "EVIDENCE_MATRIX", layout.ISSUE_SCOPE_REL: "ISSUE_SCOPE",
    ADR_DRAFT_REL: "ADR_DRAFT"}
HUMAN_REASON_PREFIX = "人工審查："
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def human_reason(reason: str) -> str:
    """人工退回送給 `gate FAIL --reason` 的理由：一律以 `人工審查：` 起頭（已帶就不重複）。"""
    text = reason.strip()
    return text if text.startswith(HUMAN_REASON_PREFIX) else f"{HUMAN_REASON_PREFIX}{text}"


def approve_input_violations(expected: Mapping[str, str], reason: str | None
                             ) -> list[dict[str, str]]:
    """核准輸入驗證（純函式；形狀，不看工作區）：`expected_digests` 的鍵是不含 `..` 的相對 POSIX
    路徑、值是 `sha256:` 加 64 位小寫十六進位；`reason` 選填、至多 500 字元。缺鍵不算錯（D-72：
    只比對前端送來的鍵）；一個鍵都沒送由 `digest_problems` 回報（防止盲核）。"""
    out: list[dict[str, str]] = []

    def bad(field: str, rule: str, message: str) -> None:
        out.append({"field": field, "rule": rule, "message": message})

    if reason is not None and len(reason) > 500:
        bad("reason", "invalid_length", "reason 至多 500 字元")
    for key, value in expected.items():
        text = key.replace("\\", "/")
        if text.startswith("/") or re.match(r"^[A-Za-z]:", text) or ".." in text.split("/"):
            bad("expected_digests", "invalid_path", f"鍵須是不含 .. 的相對路徑：{key}")
        if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
            bad("expected_digests", "invalid_digest", f"{key} 的值須為 sha256:<64 位十六進位>")
    return out


def digest_problems(expected: Mapping[str, str], actual: Mapping[str, str],
                    head_rel: str) -> tuple[str, dict[str, Any]] | None:
    """核准當下的摘要比對（D-72；純函式）。`actual`＝`APPROVE_DOCS` 內**存在**之檔案現在的 sha256
    （十六進位；PRD 以基線路徑為鍵；不存在的檔案不列）。只比對前端送來的鍵（缺鍵不算錯；其餘檔案由
    `spec-frozen --digest` 在凍結當下計算並記入凍結記錄）：PRD 可用基線路徑或 head 草稿路徑表示；
    送了不在四檔內（或檔案不存在）的鍵視為不符。回 `None`＝全部相符；否則 `(reason, details)`：
    一個鍵都沒送＝`missing_digests`（防止盲核；details 列出可送的鍵）、有鍵不符＝`digest_mismatch`
    （details.files 逐鍵列出送來的值與現值，現值為 None＝檔案不存在或不在四檔內）。"""
    if not expected:
        return "missing_digests", {"accepted_keys": list(APPROVE_DOCS)}
    wrong = []
    for key, value in expected.items():
        now = actual.get(BASELINE_REL if key == head_rel else key)
        if now is None or value != f"sha256:{now}":
            wrong.append({"key": key, "expected": value,
                          "current": None if now is None else f"sha256:{now}"})
    return ("digest_mismatch", {"files": wrong}) if wrong else None


__all__ = ["APPROVE_DOCS", "BASELINE_REL", "FROZEN_DOC_KINDS", "HUMAN_REASON_PREFIX",
           "Orchestrator", "ResearchRunHandle", "ResearchRunManager", "ReviewJournal",
           "StageFailed", "approve_input_violations", "derive_exit_reason", "derive_flow_status",
           "digest_problems", "flow_fsm_mapping_ok", "human_reason"]
