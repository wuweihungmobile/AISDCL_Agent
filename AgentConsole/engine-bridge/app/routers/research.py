"""/research/*：研究寫入面（ResearchToPRD；ADR-003、ADR-XPLAT-017；API 契約 §2）。

僅 console-api 呼叫（不對瀏覽器開放）。每個寫入端點的檢查序（先中者定案）：
`X-Bridge-Token`（未設 503 `research_write_disabled`、缺或錯 403 `research_write_forbidden`）
→ 資料庫（無 `BRIDGE_DB_DSN` 503 `research_requires_db`，不降級）→ 請求本文（422）→
業務前置（404／409）。前兩關是 dependency（先於本文驗證，所以連空本文也被擋在同一個 503）。
唯一例外：`GET /research/capabilities` 一律 200（無 DSN 時 `db` 為假）。

寫入走 outbox 協定（`DurableWriter`：檔→outbox→DB 交易→標完成）；FSM 只經 `fsm_ops`（CLI 子
行程）。成功與被拒都記 `bridge.audit` 的
`research_write{verb,research_id,approver,result,trace_id}`，不含權杖。

四類處理函式（`stages/{stage}:start` 的啟動、`:approve-baseline`、`:return`、`:reconcile`）的
前置條件與驗證都在這裡（含 stage 啟動的並行上限：同專案互斥與全站
`BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS`，達上限一律 409 `stage_conflict`）；通過後的動作交
`research/orchestrator.py`（啟動、對帳、投影）與 `fsm_ops`（Gate 0、人工退回）。唯一仍回 501
`not_implemented` 的是 P1 的 `tcs-draft`（絕不是 2xx）。`:approve-baseline` 是唯一可呼叫
`fsm_ops.approve_baseline` 的地方（AST 鎖）。
"""
from __future__ import annotations

import asyncio
import hmac
import json
import logging
import re
import threading
import time
import uuid
from collections.abc import AsyncIterator, Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import sdd_cli
from ..errors import ApiError, unprocessable
from ..research import export, fsm_ops, layout
from ..research import route as route_mod
from ..research import scr as scr_mod
from ..research.db import (
    ResearchConflict,
    ResearchDb,
    ResearchDbError,
    ResearchGuardError,
    jsonable,
    utc_now,
)
from ..research.fetch.allowlist import DEFAULT_ENV_MIN_INTERVAL, ENV_MIN_INTERVALS
from ..research.gates.reconcile import prd_save_cursor
from ..research.orchestrator import (
    APPROVE_DOCS,
    BASELINE_REL,
    Orchestrator,
    approve_input_violations,
    derive_flow_status,
    digest_problems,
    human_reason,
)
from ..research.outbox import DbBlocked, DurableWriter, FileRef, FileWrite, Op, Outbox
from ..research.registry import (
    RegistryTooLarge,
    build_registry,
    host_of,
    utc_text,
    watch_violations,
)
from ..research.settings import research_capabilities
from ..sdd_state import ESCALATION_STATES
from ..security import AuditLog, is_within
from ..settings import Settings
from ..tracing import trace_id_var

logger = logging.getLogger("bridge.research")
router = APIRouter(prefix="/research", tags=["research"])

STAGES: tuple[str, ...] = ("research", "draft", "review", "revise", "iterate", "tcs-draft")
#: P0 的 stage；`tcs-draft` 自 P1 起可啟動（不再回 501；`not_implemented` 保留供 P2，D-111）。
P0_STAGES: tuple[str, ...] = STAGES[:5]
TCS_STAGE = "tcs-draft"
#: `tcs-draft` 啟動時內環鍵可在的現態（SPEC_FROZEN＝首次；其餘兩個＝驗證失敗後重試）。
TCS_INNER_STATES: tuple[str, ...] = ("SPEC_FROZEN", "SPEC_DRAFTING", "SCG_VALIDATION")
#: 全站「啟動 stage」臨界區的鎖名（並行上限檢查與 stage run 建列之間不得被別的啟動插入）。
SITE_STAGE_LOCK = "site:stage-start"
PRD_MAX_BYTES = 1_048_576
EVENTS_MAX_LIMIT = 500
STREAM_BATCH = 200
#: SSE：輪詢事件表的間隔與心跳間隔（秒）；測試以 monkeypatch 縮短。
STREAM_POLL_SECONDS = 1.0
STREAM_HEARTBEAT_SECONDS = 15.0
_HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$")
_LIST_KINDS = ("FETCH", "WEB")
_LAYERS = ("ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY")
_FROZEN_STEPS = ("route", "build", "deliver")


# ── 執行脈絡（延遲建立，掛在 app.state；main.py 只多一行 include_router）──────────────────────────
@dataclass
class ResearchContext:
    cfg: Settings
    audit: AuditLog
    db: ResearchDb | None
    writer: DurableWriter | None
    #: PKG-BR-C 注入：停止進行中 stage run 的行程（None＝只在資料庫標記取消）。
    stopper: Callable[[str], None] | None = None
    #: PKG-BR-C 注入：啟動與驅動 stage run 的 orchestrator（測試可換成注入假抓取層的實例）。
    orchestrator: Orchestrator | None = None


_build_lock = threading.Lock()


def _build_context(state: Any) -> ResearchContext:
    cfg: Settings = state.settings
    audit = getattr(state, "audit", None) or AuditLog(None)
    db = ResearchDb(cfg.db_dsn, cfg.db_schema) if cfg.db_dsn else None
    writer = None
    if db is not None:
        writer = DurableWriter(db, Outbox(cfg.research_root / ".outbox" / "outbox.jsonl"))
        try:
            writer.replay()                  # 重啟重放：DB 不可用時記錄留在 outbox、這裡不拋
        except Exception:                    # noqa: BLE001 — 重放失敗不得擋住整個 API；留記錄
            logger.exception("研究 outbox 啟動重放失敗（記錄仍在 outbox，之後的寫入會再重放）")
    ctx = ResearchContext(cfg=cfg, audit=audit, db=db, writer=writer)
    if db is not None and writer is not None:
        ctx.orchestrator = Orchestrator(cfg, audit, db, writer)
        ctx.stopper = ctx.orchestrator.stop
        try:
            ctx.orchestrator.reap_orphans()      # 上一個 Bridge 行程留下的 stage run＝orphaned
        except Exception:                    # noqa: BLE001 — 回收失敗不得擋住整個 API
            logger.exception("研究 stage run 孤兒回收失敗")
        try:                                 # P1：卡在 PENDING／RUNNING 的分流列（BR-D1 提供）
            route_mod.reap_route_orphans(db, writer)
        except Exception:                    # noqa: BLE001 — 回收失敗不得擋住整個 API
            logger.exception("研究分流列孤兒回收失敗")
    return ctx


def get_context(request: Request) -> ResearchContext:
    state = request.app.state
    ctx = getattr(state, "research", None)
    if ctx is None:
        with _build_lock:
            ctx = getattr(state, "research", None)
            if ctx is None:
                ctx = _build_context(state)
                state.research = ctx
    return ctx


def _audit(ctx: ResearchContext, verb: str, research_id: str | None, approver: str | None,
           result: str) -> None:
    ctx.audit.record("research_write", verb=verb, research_id=research_id,
                     approver=(approver or "")[:100] or None, result=result,
                     trace_id=trace_id_var.get())


def write_gate(verb: str) -> Callable[..., ResearchContext]:
    """寫入端點的前兩關（權杖、資料庫）；被拒也記稽核（不含任何權杖值）。"""

    def dependency(request: Request,
                   x_bridge_token: str | None = Header(default=None)) -> ResearchContext:
        ctx = get_context(request)
        rid = request.path_params.get("research_id")

        def reject(error: ApiError) -> ApiError:
            _audit(ctx, verb, rid, None, f"rejected:{error.body['reason']}")
            return error

        token = ctx.cfg.research_write_token
        if not token:
            raise reject(ApiError(
                503, "research_write_disabled",
                detail="Bridge 未設定 BRIDGE_RESEARCH_WRITE_TOKEN：研究寫入面停用"))
        if x_bridge_token is None or not hmac.compare_digest(
                x_bridge_token.encode("utf-8"), token.encode("utf-8")):
            raise reject(ApiError(403, "research_write_forbidden"))
        if ctx.db is None or ctx.writer is None:
            raise reject(ApiError(503, "research_requires_db",
                                  detail="研究寫入面需要 BRIDGE_DB_DSN；不降級成純檔案模式"))
        return ctx

    return dependency


def read_gate(request: Request) -> ResearchContext:
    ctx = get_context(request)
    if ctx.db is None or ctx.writer is None:
        raise ApiError(503, "research_requires_db",
                       detail="研究端點需要 BRIDGE_DB_DSN；不降級成純檔案模式")
    return ctx


@contextmanager
def operation(ctx: ResearchContext, verb: str, research_id: str | None,
              approver: str | None) -> Iterator[None]:
    """一個寫入操作的稽核與錯誤對映：寫入器的衝突／守衛／DB 錯誤一律轉成 `ApiError`，成功與被拒
    都記稽核。"""
    try:
        try:
            yield
        except ResearchConflict as exc:
            raise ApiError(409, exc.reason, details=exc.details) from exc
        except ResearchGuardError as exc:
            raise _guard_error(exc) from exc
        except (DbBlocked, ResearchDbError) as exc:
            raise ApiError(503, "db_blocked", detail=str(exc)[:300]) from exc
    except ApiError as err:
        _audit(ctx, verb, research_id, approver, f"rejected:{err.body['reason']}")
        raise
    _audit(ctx, verb, research_id, approver, "ok")


def _guard_error(exc: ResearchGuardError) -> ApiError:
    if exc.rule == "project_not_found":
        return ApiError(404, "research_not_found")
    if exc.rule == "terms_ack_required":
        return ApiError(422, "terms_ack_required", detail="Reddit 須先確認條款")
    return ApiError(422, "invalid_request", violations=[
        {"field": exc.rule, "rule": exc.rule, "message": str(exc)[:300]}])


def _violation(field: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field, "rule": rule, "message": message}


def _subject(value: object, field: str) -> str:
    """JWT subject 一類的人名欄位：1～100 字、非空白、無控制字元。"""
    text = value if isinstance(value, str) else ""
    if not text.strip() or len(text) > 100 or any(ord(c) < 32 for c in text):
        raise unprocessable([_violation(field, "invalid_subject", f"{field} 須為 1～100 字")],
                            "invalid_request")
    return text


def _research_id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise ApiError(404, "research_not_found", research_id=value) from exc


def _project(ctx: ResearchContext, research_id: str) -> dict[str, Any]:
    assert ctx.db is not None
    row = ctx.db.get_project(research_id)
    if row is None:
        raise ApiError(404, "research_not_found", research_id=research_id)
    return row


def _flow_out(row: dict[str, Any]) -> dict[str, Any]:
    return {"step": row["flow_step"], "phase": row["flow_phase"], "status": row["flow_status"],
            "detail": row["flow_detail"]}


def _fsm_ctx(ctx: ResearchContext, row: dict[str, Any], *, actor: str | None = None,
             key: str | None = None) -> fsm_ops.FsmCtx:
    return fsm_ops.FsmCtx(sdd_root=ctx.cfg.sdd_root, state_dir=Path(row["fsm_state_dir"]),
                          key=key or row["fsm_project"], audit=ctx.audit, actor=actor)


def _fsm_state_or_none(ctx: ResearchContext, row: dict[str, Any]) -> str | None:
    """外環 FSM 現態（唯讀、不起子行程）；狀態檔缺席或讀不動＝None（呼叫端據此保守處理）。"""
    try:
        return fsm_ops.current_state(_fsm_ctx(ctx, row))
    except ApiError:
        return None


def _not_implemented(endpoint: str, **extra: Any) -> ApiError:
    return ApiError(501, "not_implemented", endpoint=endpoint,
                    detail="尚未實作：這是 P1 功能，P0 不提供（前置條件與驗證已在這裡）", **extra)


# ── 外環 FSM 鍵：唯一的建檔呼叫點（AST 鎖：呼叫者只有初始化流程與換世代）──────────────────────────
def _ensure_fsm_key(ctx: ResearchContext, row: dict[str, Any], *, key: str,
                    actor: str | None) -> None:
    """鍵的狀態檔不存在就以共用 helper 建出（INIT），再走到 AGENT_LOAD；已存在只補走前置（冪等）。
    失敗拋 `ApiError`（呼叫端標 `init_failed:fsm`）。"""
    fctx = _fsm_ctx(ctx, row, actor=actor, key=key)
    if sdd_state_file_missing(fctx):
        fsm_ops.create_key(fctx, allowed_roots=ctx.cfg.allowed_path_roots)
    fsm_ops.bring_to_agent_load(fctx)


def sdd_state_file_missing(fctx: fsm_ops.FsmCtx) -> bool:
    return not (fctx.state_dir / f"FSM-STATE-{fctx.key}.yaml").is_file()


def _fsm_init_step(ctx: ResearchContext, row: dict[str, Any], *, actor: str | None) -> str | None:
    """初始化流程的 FSM 步驟（建立專案與重試初始化共用）：成功回 None，失敗回步驟名 `fsm`。"""
    try:
        _ensure_fsm_key(ctx, row, key=row["fsm_project"], actor=actor)
    except ApiError as exc:
        logger.warning("研究專案 %s 的 FSM 初始化失敗：%s", row.get("id"), exc.body.get("reason"))
        return "fsm"
    return None


def _set_cursor(ctx: ResearchContext, research_id: str, flow: dict[str, Any],
                actor: str) -> dict[str, Any]:
    assert ctx.writer is not None
    return ctx.writer.persist(Op("project.cursor", research_id, {
        "research_id": research_id, "actor": actor, "flow": flow}))


def _failed_flow(row: dict[str, Any], step: str) -> dict[str, Any]:
    return {"step": row["flow_step"], "phase": row["flow_phase"], "status": "FAILED",
            "detail": f"init_failed:{step}"}


# ── 建立專案 ─────────────────────────────────────────────────────────────────────────────────
class ProjectIn(BaseModel):
    research_id: uuid.UUID
    slug: str
    title: str
    topic: str
    scope: dict[str, Any] = {}
    depth_level: str = "STANDARD"
    created_by: str


def _project_violations(body: ProjectIn, cfg: Settings) -> dict[str, Any]:
    scope, violations = export.normalize_scope(body.scope)
    violations += export.field_violations(title=body.title, topic=body.topic,
                                          depth_level=body.depth_level)
    if violations:
        raise unprocessable(violations, "invalid_request")
    if scope["layers"]["industry"] and not cfg.research_web_allowlist:
        raise ApiError(422, "layer_unavailable", violations=[_violation(
            "scope.layers.industry", "web_layer_disabled",
            "產業層需要 Web 層（BRIDGE_RESEARCH_WEB_ALLOWLIST 為空＝未啟用）")])
    return scope


@router.post("/projects", status_code=201)
def create_project(body: ProjectIn, ctx: ResearchContext = Depends(write_gate("project.create"))
                   ) -> dict[str, Any]:
    assert ctx.db is not None and ctx.writer is not None
    rid, actor = str(body.research_id), body.created_by
    with operation(ctx, "project.create", rid, actor):
        _subject(actor, "created_by")
        scope = _project_violations(body, ctx.cfg)
        workspace = layout.resolve_workspace(ctx.cfg.research_root, body.slug,
                                             ctx.cfg.allowed_path_roots)
        key = f"research-{body.slug}"
        with ctx.writer.project_lock(f"slug:{body.slug}"):
            if ctx.db.find_active_project(body.slug) is not None:
                raise ApiError(409, "slug_in_use", details={"slug": body.slug})
            rp_no = ctx.db.allocate_rp_no()["rp_no"]
            created_at = utc_now().replace(microsecond=0)
            issue = export.render_issue_scope({
                "research_id": rid, "rp_no": rp_no, "slug": body.slug, "scope_rev": 1,
                "title": body.title, "topic": body.topic, "scope": scope,
                "depth_level": body.depth_level, "created_by": actor, "created_at": created_at})
            payload: dict[str, Any] = dict(
                research_id=rid, rp_no=rp_no, slug=body.slug, title=body.title, topic=body.topic,
                scope=scope, depth_level=body.depth_level, target_scope=scope["target_scope_hint"],
                workspace_path=str(workspace), fsm_project=key,
                fsm_state_dir=str(layout.fsm_state_dir(workspace)), created_by=actor,
                created_at=created_at.isoformat(), flow={
                    "step": "topic", "phase": "INGESTED", "status": "IDLE", "detail": ""})
            failed = _init_files(ctx, workspace, issue, payload, rid)
        row = _project(ctx, rid)
        if failed is None:
            failed = _fsm_init_step(ctx, row, actor=actor)
            if failed is not None:
                _set_cursor(ctx, rid, _failed_flow(row, failed), "bridge")
                row = _project(ctx, rid)
        elif row["flow_status"] != "FAILED":
            _set_cursor(ctx, rid, _failed_flow(row, failed), "bridge")
            row = _project(ctx, rid)
    return {"research_id": rid, "rp_no": row["rp_no"], "workspace_path": row["workspace_path"],
            "fsm_project": row["fsm_project"], "flow": _flow_out(row)}


def _init_files(ctx: ResearchContext, workspace: Path, issue: str, payload: dict[str, Any],
                rid: str) -> str | None:
    """建四目錄、寫 `issue_scope.json` 並建列（檔→outbox→DB）。失敗＝專案列照建但標 FAILED
    `init_failed:<步驟>`（只有成功寫出的檔才登記）。回失敗步驟名或 None。"""
    assert ctx.writer is not None
    step = "workspace"
    try:
        layout.ensure_dirs(workspace)
        step = "files"
        digest = layout.sha256_text(issue)
        payload["issue_scope"] = {"rel_path": layout.ISSUE_SCOPE_REL, "sha256": digest,
                                  "bytes": len(issue.encode("utf-8"))}
        op = Op("project.create", rid, payload, files=(FileRef(
            str(workspace), layout.ISSUE_SCOPE_REL, digest),))
        ctx.writer.persist(op, writes=[FileWrite(workspace, layout.ISSUE_SCOPE_REL, issue)])
    except OSError as exc:
        logger.warning("研究工作區初始化失敗（%s）：%s", step, type(exc).__name__)
        payload.pop("issue_scope", None)
        payload["flow"] = {"step": "topic", "phase": "INGESTED", "status": "FAILED",
                           "detail": f"init_failed:{step}"}
        ctx.writer.persist(Op("project.create", rid, payload))
        return step
    return None


# ── 重試初始化與換世代 ───────────────────────────────────────────────────────────────────────
class ReinitIn(BaseModel):
    generation: str | None = None
    reason: str | None = None
    decided_by: str | None = None


@router.post("/projects/{research_id}:reinit")
def reinit_project(research_id: str, body: ReinitIn | None = None,
                   ctx: ResearchContext = Depends(write_gate("reinit"))) -> dict[str, Any]:
    rid = _research_id(research_id)
    body = body or ReinitIn()
    actor = body.decided_by
    with operation(ctx, "reinit", rid, actor):
        row = _project(ctx, rid)
        if body.generation is None:
            return _retry_init(ctx, row)
        if body.generation != "next":
            raise unprocessable([_violation("generation", "invalid_value", "generation 只准 next")],
                                "invalid_request")
        reason = (body.reason or "").strip()
        if not 1 <= len(reason) <= 500:
            raise unprocessable([_violation("reason", "invalid_length", "reason 須為 1～500 字")],
                                "invalid_request")
        return _abandon_and_reinit(ctx, row, reason, _subject(body.decided_by, "decided_by"))


def _retry_init(ctx: ResearchContext, row: dict[str, Any]) -> dict[str, Any]:
    """重試（冪等）：只在 `flow_status=FAILED` 時可用——初始化失敗（`init_failed:<步驟>`）補齊缺的
    目錄、`issue_scope.json` 與其登記列、FSM 鍵（不覆寫已存在檔案、不重複配號與建鍵）；stage run
    失敗或取消（D-77；`flow_detail` 為 exit_reason）沒有缺的東西，只是清掉失敗標記、讓游標回到
    衍生狀態。其餘狀態 409 `stage_conflict`、零寫入。"""
    assert ctx.writer is not None and ctx.db is not None
    if row["flow_status"] != "FAILED":
        raise ApiError(409, "stage_conflict", details={
            "flowStatus": row["flow_status"], "flowDetail": row["flow_detail"]})
    rid, workspace = str(row["id"]), Path(row["workspace_path"])
    if not any(is_within(workspace, root) for root in ctx.cfg.allowed_path_roots):
        raise ApiError(422, "sanitization_failed", violations=[_violation(
            "workspace_path", "outside_allowed_roots", "工作區不在允許的根目錄之下")])
    step = "workspace"
    try:
        layout.ensure_dirs(workspace)
        step = "files"
        _ensure_issue_scope(ctx, row, workspace)
    except OSError as exc:
        logger.warning("研究工作區補建失敗（%s）：%s", step, type(exc).__name__)
        failed = _failed_flow(row, step)
        if _flow_out(row) != failed:
            _set_cursor(ctx, rid, failed, "bridge")
        raise ApiError(502, "init_failed", details={"step": step}) from exc
    failed_step = _fsm_init_step(ctx, row, actor=row["created_by"])
    if failed_step is not None:
        failed = _failed_flow(row, failed_step)
        if _flow_out(row) != failed:
            _set_cursor(ctx, rid, failed, "bridge")
        raise ApiError(502, "init_failed", details={"step": failed_step})
    # 初始化後恆為 IDLE；stage 失敗（D-77）則依 FSM 現態衍生
    status = derive_flow_status([], _fsm_state_or_none(ctx, row))
    _set_cursor(ctx, rid, {**_flow_out(row), "status": status, "detail": ""}, "bridge")
    return {"flow": _flow_out(_project(ctx, rid))}


def _ensure_issue_scope(ctx: ResearchContext, row: dict[str, Any], workspace: Path) -> None:
    """`issue_scope.json` 不存在就由資料列重新渲染寫出；登記列不存在就補（已存在的檔案不動）。"""
    assert ctx.writer is not None
    rid = str(row["id"])
    existing = layout.file_digest(workspace, layout.ISSUE_SCOPE_REL)
    writes: list[FileWrite] = []
    if existing is None:
        text = export.render_issue_scope({**row, "research_id": rid})
        writes.append(FileWrite(workspace, layout.ISSUE_SCOPE_REL, text, overwrite=False))
        existing = (layout.sha256_text(text), len(text.encode("utf-8")))
    op = Op("artifact.insert", rid, dict(
        research_id=rid, kind="ISSUE_SCOPE", version=1, rel_path=layout.ISSUE_SCOPE_REL,
        sha256=existing[0], bytes=existing[1], origin="BRIDGE", created_by=row["created_by"]),
        files=(FileRef(str(workspace), layout.ISSUE_SCOPE_REL, existing[0]),))
    ctx.writer.persist(op, writes=writes)


def _abandon_and_reinit(ctx: ResearchContext, row: dict[str, Any], reason: str,
                        decided_by: str) -> dict[str, Any]:
    """換世代（D-60、D-64）：外環 FSM 現態須在 ESCALATION*；單一交易放棄舊鍵、改指新世代鍵（DB 先於
    FSM）；提交後才以共用 helper 建新鍵並走到 AGENT_LOAD（失敗＝游標 FAILED `init_failed:fsm`，
    以重試初始化補建）。舊鍵狀態檔不動、不呼叫任何寫入類動詞。"""
    assert ctx.writer is not None
    rid = str(row["id"])
    state = fsm_ops.read_current(_fsm_ctx(ctx, row))
    current = state.get("current_state")
    if current not in ESCALATION_STATES:
        raise fsm_ops.conflict("fsm_state_conflict", current_state=current)
    generation = int(row["fsm_generation"]) + 1
    new_key = f"research-{row['slug']}-g{generation}"
    decision_id = str(uuid.uuid4())
    ctx.writer.persist(Op("project.abandon_key", rid, dict(
        research_id=rid, decision_id=decision_id, decided_by=decided_by, reason=reason,
        old_fsm_project=row["fsm_project"], new_fsm_project=new_key, new_generation=generation,
        fsm_state_after=current, audit_trace_id=trace_id_var.get(),
        # 進得了 ESCALATION 的專案一定在規格工作室；寫死 studio，游標對映才與新鍵（AGENT_LOAD）一致
        flow={"step": "studio", "phase": "REVISING", "status": "IDLE", "detail": ""})))
    row = _project(ctx, rid)                       # 提交之後 `fsm_project` 已指向新世代鍵
    failed = _fsm_init_step(ctx, row, actor=decided_by)
    if failed is not None:
        _set_cursor(ctx, rid, _failed_flow(row, failed), "bridge")
        row = _project(ctx, rid)
    return {"flow": _flow_out(row), "fsm_project": row["fsm_project"],
            "fsm_generation": row["fsm_generation"], "gate_decision_id": decision_id}


# ── 存 PRD 新版（人工編輯；樂觀鎖）─────────────────────────────────────────────────────────────
class PrdIn(BaseModel):
    base_version: int
    content: str
    change_summary: str = ""
    author: str


@router.put("/projects/{research_id}/prd", status_code=201)
def save_prd(research_id: str, body: PrdIn,
             ctx: ResearchContext = Depends(write_gate("prd.save"))) -> dict[str, Any]:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    with operation(ctx, "prd.save", rid, body.author):
        author = _subject(body.author, "author")
        size = _prd_violations(body)
        with ctx.writer.project_lock(rid):
            row = _project(ctx, rid)
            if row["flow_phase"] == "FROZEN" or row["flow_step"] in _FROZEN_STEPS:
                raise ApiError(409, "spec_frozen", details={
                    "flowStep": row["flow_step"], "flowPhase": row["flow_phase"]})
            head = ctx.db.head_prd(rid)
            head_no = int(head["version_no"]) if head else 0
            if body.base_version != head_no:
                raise ApiError(409, "prd_version_conflict", details={"headVersion": head_no})
            version_no = head_no + 1
            semver = f"v0.{version_no}.0-draft"
            rel = f"01_specs/PRD-{semver}.md"
            digest = layout.sha256_text(body.content)
            workspace = Path(row["workspace_path"])
            # 游標：FSM 現態的合法對映（不固定寫 DRAFTING；INT-05）、狀態依 stage run 與 FSM 衍生
            # （D-56）
            fsm_state = _fsm_state_or_none(ctx, row)
            step, phase = prd_save_cursor(fsm_state, row["flow_step"], row["flow_phase"])
            active = ctx.db.active_stage_run(rid)
            status = derive_flow_status([] if active is None else [active["status"]], fsm_state)
            op = Op("prd.save", rid, dict(
                research_id=rid, version_no=version_no, semver=semver, kind="DRAFT",
                author_kind="HUMAN", author=author, content=body.content, rel_path=rel,
                sha256=digest, bytes=size, change_summary=body.change_summary[:500],
                flow={"step": step, "phase": phase, "status": status, "detail": ""}),
                files=(FileRef(str(workspace), rel, digest),))
            ctx.writer.persist(op, writes=[FileWrite(workspace, rel, body.content)])
    return {"version_no": version_no, "semver": semver, "sha256": digest, "bytes": size}


def _prd_violations(body: PrdIn) -> int:
    """PRD 本文輸入閘：非空、無 NUL、可編成 UTF-8、≤ 1 MiB 位元組；回位元組數。"""
    if not body.content.strip() or "\x00" in body.content:
        raise unprocessable([_violation("content", "invalid_content", "content 不可為空或含 NUL")],
                            "invalid_request")
    try:
        size = len(body.content.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise unprocessable([_violation("content", "not_utf8", "content 須為合法 UTF-8")],
                            "invalid_request") from exc
    if size > PRD_MAX_BYTES:
        raise unprocessable([_violation("content", "too_large",
                                        f"content 超過 {PRD_MAX_BYTES} 位元組")], "invalid_request")
    return size


# ── 啟動 stage（前置條件在這裡；本體在 research/orchestrator.py）─────────────────────────────────
class StageStartIn(BaseModel):
    auto: bool = False
    note: str | None = None
    requested_by: str
    after_escalation: bool = False


def stage_unmet(stage: str, row: dict[str, Any], head_prd: dict[str, Any] | None,
                last_round: dict[str, Any] | None) -> list[dict[str, Any]]:
    """各 stage 的前置條件表（純函式）：回未滿足項（`rule`、`expected`、`current`）。"""
    phase = row["flow_phase"]
    unmet: list[dict[str, Any]] = []
    if stage == "research" and phase not in ("INGESTED", "EVIDENCE_READY"):
        unmet.append({"rule": "phase", "expected": ["INGESTED", "EVIDENCE_READY"],
                      "current": phase})
    if stage == "draft" and phase != "EVIDENCE_READY":
        unmet.append({"rule": "phase", "expected": ["EVIDENCE_READY"], "current": phase})
    if stage == "review" and head_prd is None:
        unmet.append({"rule": "head_prd", "expected": "exists", "current": None})
    if stage in ("revise", "iterate") and (last_round is None or last_round["passed"]):
        unmet.append({"rule": "last_round_failed", "expected": "FAIL",
                      "current": None if last_round is None else last_round["verdict"]})
    return unmet


@router.post("/projects/{research_id}/stages/{stage}:start", status_code=202)
def start_stage(research_id: str, stage: str, body: StageStartIn,
                ctx: ResearchContext = Depends(write_gate("stage.start"))) -> dict[str, Any]:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    with operation(ctx, "stage.start", rid, body.requested_by):
        if stage not in STAGES:
            raise unprocessable([_violation("stage", "invalid_value",
                                            f"stage 須為 {'｜'.join(STAGES)}")], "invalid_request")
        _subject(body.requested_by, "requested_by")
        row = _project(ctx, rid)
        # P1：Stage-2 發生在 Gate 0 凍結之後（游標在 route／build），所以不套 spec_frozen 檢查
        tcs = stage == TCS_STAGE
        if not tcs and (row["flow_phase"] == "FROZEN" or row["flow_step"] in _FROZEN_STEPS):
            raise ApiError(409, "spec_frozen", details={
                "flowStep": row["flow_step"], "flowPhase": row["flow_phase"]})
        if tcs:
            outer = fsm_ops.read_current(_fsm_ctx(ctx, row))
            if fsm_ops.is_escalated(outer):
                raise fsm_ops.escalated_error(_fsm_ctx(ctx, row), outer)
        active = ctx.db.active_stage_run(rid)
        if active is not None:
            raise ApiError(409, "stage_conflict", details={
                "activeStageRunId": str(active["id"]), "activeStage": active["stage"]})
        if tcs:
            scr_mod.guard_inner_start(ctx.db, rid)
            unmet = tcs_unmet(ctx, row)
            if unmet:
                raise ApiError(409, "fsm_state_conflict", details={"unmet": unmet})
        if stage in ("review", "revise", "iterate"):
            _escalation_gate(ctx, row, stage, body.after_escalation)
        unmet = stage_unmet(stage, row, ctx.db.head_prd(rid), ctx.db.review_state(rid)["last"])
        if unmet:
            raise ApiError(409, "stage_conflict", details={"unmet": unmet})
        with ctx.writer.project_lock(SITE_STAGE_LOCK):      # 上限檢查與 stage run 建列之間不被插入
            _check_concurrency_cap(ctx)
            return _run_stage(ctx, row, stage, body)
    raise AssertionError("unreachable")


def tcs_unmet(ctx: ResearchContext, row: dict[str, Any]) -> list[dict[str, Any]]:
    """`tcs-draft` 的前置（D-110／D-118 ⚖P1-11；體例沿 AC-R2P-01-3 的 `details.unmet[]`）：分流
    `SUCCEEDED`、內環鍵已採納（現態在 SPEC_FROZEN／重試的 SPEC_DRAFTING 或 SCG_VALIDATION，且
    `frozen_stages` 恰一筆 Stage-1）、已有拆解列。純唯讀。"""
    assert ctx.db is not None
    rid = str(row["id"])
    unmet: list[dict[str, Any]] = []
    route = ctx.db.active_route(rid)
    ok_route = route is not None and route["status"] == "SUCCEEDED" and bool(
        route.get("impl_fsm_project"))
    if not ok_route:
        unmet.append({"rule": "route_not_succeeded", "expected": "SUCCEEDED",
                      "current": None if route is None else route["status"]})
    else:
        assert route is not None
        snap = fsm_ops.snapshot(fsm_ops.FsmCtx(
            sdd_root=ctx.cfg.sdd_root, state_dir=Path(route["impl_state_dir"]),
            key=str(route["impl_fsm_project"])))
        stages = [s.get("stage") for s in snap["frozen_stages"] if isinstance(s, dict)]
        if snap["state"] not in TCS_INNER_STATES or stages != ["Stage-1"]:
            unmet.append({"rule": "inner_key_not_adopted", "expected": {
                "states": list(TCS_INNER_STATES), "frozen_stages": ["Stage-1"]},
                "current": {"state": snap["state"], "frozen_stages": stages}})
    found = ctx.db.query("SELECT 1 AS hit FROM {s}.research_decompositions WHERE research_id = "
                         "%s AND status <> 'REJECTED' LIMIT 1", (rid,))
    if not found:
        unmet.append({"rule": "decomposition_missing", "expected": "exists", "current": None})
    return unmet


def _check_concurrency_cap(ctx: ResearchContext) -> None:
    """全站進行中的 stage run 數達 `BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS` 時，新的啟動一律 409
    `stage_conflict`（PRD AC-R2P-04-10「第二個 stage 排隊或 409」：本 Bridge 取 409，不排隊）；
    同專案的互斥在上面已判（`activeStageRunId`），這裡數的是全站。"""
    assert ctx.db is not None
    limit = ctx.cfg.research_max_concurrent_runs
    active = ctx.db.count_active_stage_runs()
    if active >= limit:
        raise ApiError(409, "stage_conflict", details={
            "cause": "max_concurrent_runs", "limit": limit, "active": active})


def _escalation_gate(ctx: ResearchContext, row: dict[str, Any], stage: str,
                     after_escalation: bool) -> None:
    """外環 FSM 在 ESCALATION* 時：自動修訂與新審查一律 409 `escalated`（帶恢復指令）；唯一的
    例外是 `revise` 帶 `afterEscalation`——只唯讀驗證 FSM 已離開 ESCALATION*（否則 409
    `fsm_state_conflict`），不呼叫任何 FSM 寫入動詞（D-30、D-60）。"""
    fctx = _fsm_ctx(ctx, row)
    state = fsm_ops.read_current(fctx)
    current = state.get("current_state")
    in_escalation = isinstance(current, str) and current in ESCALATION_STATES
    if stage == "revise" and after_escalation:
        if in_escalation:
            raise fsm_ops.conflict("fsm_state_conflict", current_state=current)
        return
    if in_escalation:
        raise fsm_ops.escalated_error(fctx, state)


def _run_stage(ctx: ResearchContext, row: dict[str, Any], stage: str,
               body: StageStartIn) -> dict[str, Any]:
    """啟動 stage run（本體在 `Orchestrator.start`）。

    契約：呼叫端持有全站啟動鎖（`SITE_STAGE_LOCK`），已通過前置條件與並行上限；本體必須在回傳前
    建好 stage run 列（QUEUED 或 RUNNING，下一個啟動請求的上限檢查才看得到它），且不得長時間阻塞
    （起行程後即回 202）。"""
    assert ctx.orchestrator is not None
    return ctx.orchestrator.start(row, stage, requested_by=body.requested_by,
                                  after_escalation=body.after_escalation, auto=body.auto)


# ── Gate 0、人工退回、對帳 ───────────────────────────────────────────────────────────────────
class ApproveIn(BaseModel):
    prd_version: int
    expected_digests: dict[str, str] = {}
    approver: str
    reason: str | None = None
    #: 僅 SCR（open MINOR）核准時有效：`MAJOR`＝新基線 `v2.0.0`，省略＝`v1.<n>.0`（PRD §5.1.9）
    version_bump: str | None = None


def _regression_reason(ctx: ResearchContext, rid: str) -> str:
    """進 SPEC_REGRESSION_CHECK 的理由：已處理缺陷數與人工要求數（取自資料庫）。"""
    assert ctx.db is not None
    fixed = ctx.db.query(
        "SELECT count(*) AS n FROM {s}.research_review_defects d "
        "JOIN {s}.research_review_rounds r ON r.id = d.round_id "
        "WHERE r.research_id = %s AND d.status IN ('FIXED', 'WAIVED')", (rid,))
    human = ctx.db.query("SELECT count(*) AS n FROM {s}.research_gate_decisions WHERE "
                         "research_id = %s AND decision = 'CHANGES'", (rid,))
    return (f"gate 0 regression check: {fixed[0]['n']} defects handled, "
            f"{human[0]['n']} human requests")


@router.post("/projects/{research_id}:approve-baseline")
def approve_baseline(research_id: str, body: ApproveIn,
                     ctx: ResearchContext = Depends(write_gate("approve_baseline"))
                     ) -> dict[str, Any]:
    """Gate 0（ADR-XPLAT-017 §D3 的檢查序：權杖→審查→摘要→FSM 現態→回歸態→凍結）。先中者定案；
    前五關都是唯讀，任何一關不過都零寫入。`approve_baseline` 的唯一呼叫點（AST 鎖 C2）。

    摘要（D-72）：只比對前端送來的 `expected_digests` 鍵——不符 422 `digest_mismatch`、一個鍵都沒送
    422 `missing_digests`、缺鍵不算錯；四份文件的摘要一律由 `spec-frozen --digest --root` 在凍結當下
    自工作區計算並記入凍結記錄（回應的 `spec_doc_digests` 與 R6 列的 `frozen_digests` 取自它）。"""
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    with operation(ctx, "approve_baseline", rid, body.approver):
        approver = sdd_cli.validate_research_approver(body.approver)
        violations = approve_input_violations(body.expected_digests, body.reason)
        if violations:
            raise unprocessable(violations, "invalid_request")
        with ctx.writer.project_lock(rid):
            row = _project(ctx, rid)
            workspace = Path(row["workspace_path"])
            open_scr = scr_mod.scr_awaiting_approval(ctx.db, rid)    # D-103：OPEN 的 MINOR SCR
            if body.version_bump is not None and (
                    open_scr is None or body.version_bump not in export.VERSION_BUMPS):
                raise unprocessable([_violation(
                    "version_bump", "invalid_version_bump",
                    "version_bump 只在有 OPEN 的 MINOR SCR 時可用，且須為 MAJOR 或 MINOR")],
                    "invalid_request")
            semver = (export.baseline_semver(int(open_scr["scr_no"]), body.version_bump)
                      if open_scr else "v1.0.0")
            baseline_rel = export.baseline_rel(semver) if open_scr else BASELINE_REL
            drafts = ctx.db.query(
                "SELECT version_no, rel_path, sha256 FROM {s}.research_prd_versions WHERE "
                "research_id = %s AND kind = 'DRAFT' ORDER BY version_no DESC LIMIT 1", (rid,))
            head = drafts[0] if drafts else None
            last = ctx.db.review_state(rid)["last"]
            if (head is None or last is None or not last["passed"]
                    or int(last["prd_version_no"]) != int(head["version_no"])
                    or body.prd_version != int(head["version_no"])):
                raise ApiError(409, "review_not_passed", details={
                    "headVersion": None if head is None else int(head["version_no"]),
                    "requested": body.prd_version})
            docs = (baseline_rel, *APPROVE_DOCS[1:])
            raw = (workspace / head["rel_path"]).read_bytes()
            actual = {BASELINE_REL: layout.sha256_bytes(raw)}      # digest_problems 以此為 PRD 鍵
            for doc in docs[1:]:
                found = layout.file_digest(workspace, doc)
                if found is not None:
                    actual[doc] = found[0]
            problem = digest_problems(body.expected_digests, actual, str(head["rel_path"]))
            if problem is not None:
                raise ApiError(422, problem[0], details=problem[1])
            fctx = _fsm_ctx(ctx, row, actor=approver)
            state = fsm_ops.read_current(fctx)
            if fsm_ops.is_escalated(state):
                raise fsm_ops.escalated_error(fctx, state)
            if state.get("current_state") != "HUMAN_PENDING":
                raise fsm_ops.conflict("fsm_state_conflict", current_state=state.get(
                    "current_state"), expected_state="HUMAN_PENDING")
            shown = fsm_ops.show(fctx)
            count = int(((shown.get("retry_history") or {}).get("SCG_VALIDATION") or {}).get(
                "current_count", 0) or 0)
            if count > 0:               # 只取決於 show 讀到的計數（不看 DB 輪數、不自建計數變數）
                fsm_ops.transition(fctx, to="SPEC_REGRESSION_CHECK",
                                   reason=_regression_reason(ctx, rid))
            layout.write_workspace_file(workspace, docs[0], raw.decode("utf-8"))
            reason_text = (body.reason or "Gate 0 approved")[:500]
            if open_scr is None:
                frozen = fsm_ops.approve_baseline(
                    fctx, docs=list(docs), root=str(workspace), approver=approver,
                    reason=reason_text)
            else:                       # D-103：Stage 名 `Gate-0-SCR<k>`（`OUTER_FREEZE_STAGE_RE`）
                frozen = fsm_ops.spec_frozen(
                    fctx, stage=f"{scr_mod.SCR_STAGE_PREFIX}{open_scr['scr_no']}",
                    docs=list(docs), root=str(workspace), approver=approver, reason=reason_text)
            digests = dict(frozen["spec_doc_digests"])
            version_no = int(head["version_no"])
            decision_id = str(uuid.uuid4())
            top = ctx.db.head_prd(rid)
            digest = layout.sha256_bytes(raw)
            new_no = (int(top["version_no"]) if top else 0) + 1
            ctx.writer.persist(Op("prd.save", rid, dict(
                research_id=rid, version_no=new_no, semver=semver,
                kind="BASELINE", author_kind="HUMAN", author=approver,
                content=raw.decode("utf-8"), rel_path=docs[0], sha256=digest, bytes=len(raw),
                change_summary="SCR 核准新基線" if open_scr else "Gate 0 核准基線"),
                files=(FileRef(str(workspace), docs[0], digest),)))
            # SCR：核准之後外環鍵回到 SPEC_FROZEN、內環套用成功前游標仍在 studio／SCR_OPEN
            flow = ({"step": "studio", "phase": "SCR_OPEN", "status": "IDLE", "detail": ""}
                    if open_scr else
                    {"step": "route", "phase": "FROZEN", "status": "IDLE", "detail": ""})
            ctx.writer.persist(Op("gate.decision", rid, dict(
                research_id=rid, decision_id=decision_id, gate="GATE0", decision="APPROVED",
                decided_by=approver, decided_at=utc_now().isoformat(), prd_version_no=version_no,
                review_round_no=int(last["round_no"]), fsm_project=row["fsm_project"],
                fsm_stage=frozen.get("stage", "Gate-0"), fsm_state_after="SPEC_FROZEN",
                frozen_digests=digests, reason=body.reason or "", audit_trace_id=trace_id_var.get(),
                flow=flow)))
            scr_apply: dict[str, Any] | None = None
            if open_scr is not None:
                scr_apply = scr_mod.approve_and_apply(
                    scr_mod.ScrEnv(cfg=ctx.cfg, db=ctx.db, writer=ctx.writer, audit=ctx.audit),
                    row, open_scr, approver=approver, text=raw.decode("utf-8"), sha256=digest,
                    to_version_no=new_no, semver=semver, rel=docs[0], decision_id=decision_id)
            fresh = _project(ctx, rid)
            assert ctx.orchestrator is not None
            ctx.orchestrator.reconcile(fresh, actor="bridge")       # Gate 0 時點的自動對帳
            ctx.orchestrator.project_state(rid)
    out = {"gate_decision_id": decision_id, "stage": frozen.get("stage", "Gate-0"),
           "spec_doc_digests": digests, "fsm_state": "SPEC_FROZEN"}
    if scr_apply is not None:
        out["scr_apply"] = scr_apply
    return out


class ReturnIn(BaseModel):
    approver: str
    reason: str


@router.post("/projects/{research_id}:return")
def return_for_changes(research_id: str, body: ReturnIn,
                       ctx: ResearchContext = Depends(write_gate("return"))) -> dict[str, Any]:
    """人工退回（框架 SOP 第 5 列）：FSM 維持 HUMAN_PENDING、以**靜態 FAIL** 的 `gate` 帶人工理由使
    計數加一（與自動審查共用同一份三次預算）、PRD 回到可編輯（游標 REVISING）。"""
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    with operation(ctx, "return", rid, body.approver):
        approver = sdd_cli.validate_research_approver(body.approver)
        reason = human_reason(body.reason)
        if not 1 <= len(body.reason.strip()) <= 500 or len(reason) > 500:
            raise unprocessable([_violation("reason", "invalid_length", "reason 須為 1～500 字")],
                                "invalid_request")
        with ctx.writer.project_lock(rid):
            row = _project(ctx, rid)
            if row["flow_phase"] == "FROZEN" or row["flow_step"] in _FROZEN_STEPS:
                raise ApiError(409, "spec_frozen", details={
                    "flowStep": row["flow_step"], "flowPhase": row["flow_phase"]})
            fctx = _fsm_ctx(ctx, row, actor=approver)
            state = fsm_ops.read_current(fctx)
            if fsm_ops.is_escalated(state):
                raise fsm_ops.escalated_error(fctx, state)
            if state.get("current_state") != "HUMAN_PENDING":
                raise fsm_ops.conflict("fsm_state_conflict", current_state=state.get(
                    "current_state"), expected_state="HUMAN_PENDING")
            result = fsm_ops.gate(fctx, gate="SCG_VALIDATION", result="FAIL", reason=reason)
            head, last = ctx.db.head_prd(rid), ctx.db.review_state(rid)["last"]
            decision_id = str(uuid.uuid4())
            ctx.writer.persist(Op("gate.decision", rid, dict(
                research_id=rid, decision_id=decision_id, gate="GATE0", decision="CHANGES",
                decided_by=approver, decided_at=utc_now().isoformat(),
                prd_version_no=None if head is None else int(head["version_no"]),
                review_round_no=None if last is None else int(last["round_no"]),
                fsm_project=row["fsm_project"], fsm_stage=None,
                fsm_state_after=result["next_state"], frozen_digests={}, reason=reason,
                audit_trace_id=trace_id_var.get(),
                flow={"step": "studio", "phase": "REVISING", "detail": "",
                      "status": derive_flow_status([], result["next_state"])})))
            assert ctx.orchestrator is not None
            ctx.orchestrator.project_state(rid)
    return {"gate_decision_id": decision_id, "fsm_retry_count": result.get("retry_count"),
            "escalated": bool(result.get("escalated"))}


@router.post("/projects/{research_id}:reconcile")
def reconcile(research_id: str,
              ctx: ResearchContext = Depends(write_gate("reconcile"))) -> dict[str, Any]:
    """對帳（只報告、不修復）：結果追加一筆 `research.reconcile` 事件。"""
    rid = _research_id(research_id)
    with operation(ctx, "reconcile", rid, None):
        row = _project(ctx, rid)
        assert ctx.orchestrator is not None
        result = ctx.orchestrator.reconcile(row, actor="bridge")
        research_deliver.sync_best_effort(ctx, row)     # 順帶補寫自癒日誌（best-effort）
        return result


# ── 取消、封存、復原 ─────────────────────────────────────────────────────────────────────────
class ActorIn(BaseModel):
    actor: str = "bridge"


@router.post("/projects/{research_id}:cancel")
def cancel_stage(research_id: str, body: ActorIn | None = None,
                 ctx: ResearchContext = Depends(write_gate("cancel"))) -> dict[str, Any]:
    """停止進行中的 stage run：有注入 `stopper`（PKG-BR-C）就先停行程；資料庫一律標 CANCELLED 並
    發 `research.run`。沒有進行中的 stage＝冪等（`stopped_run_id` 為 null）。

    游標收尾與失敗同一條路（D-77）：`flow_status=FAILED`、`flow_detail=cancelled`、相態退回該
    run 開始前的穩定相態（研究 run 的 RESEARCHING 不留在游標上），所以取消之後
    `stages/research` 與 `:reinit`（重試）都能再走。"""
    assert ctx.db is not None and ctx.writer is not None and ctx.orchestrator is not None
    rid, actor = _research_id(research_id), (body or ActorIn()).actor
    with operation(ctx, "cancel", rid, actor):
        row = _project(ctx, rid)
        active = ctx.db.active_stage_run(rid)
        if active is None:
            return {"stopped_run_id": None, "flow": _flow_out(row)}
        run_id = str(active["id"])
        if ctx.stopper is not None:
            ctx.stopper(run_id)
        ctx.writer.persist(Op("stage_run.update", rid, {
            "stage_run_id": run_id, "status": "CANCELLED", "exit_reason": "cancelled",
            "finished_at": utc_now().isoformat(), "actor": actor}))
        ctx.orchestrator.settle_failed(rid, "cancelled", run_ids=(run_id,), actor=actor)
        return {"stopped_run_id": run_id, "flow": _flow_out(_project(ctx, rid))}


def _archive(ctx: ResearchContext, verb: str, research_id: str, actor: str,
             *, archive: bool) -> dict[str, Any]:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    with operation(ctx, verb, rid, actor):
        row = _project(ctx, rid)
        if archive and ctx.db.active_stage_run(rid) is not None:
            raise ApiError(409, "stage_conflict", details={"reason": "stage_running"})
        ctx.writer.persist(Op("project.archive" if archive else "project.restore", rid, {
            "research_id": rid, "actor": actor}))
        return {"flow": _flow_out(row), "archived": archive}


@router.post("/projects/{research_id}:archive")
def archive_project(research_id: str, body: ActorIn | None = None,
                    ctx: ResearchContext = Depends(write_gate("archive"))) -> dict[str, Any]:
    return _archive(ctx, "archive", research_id, (body or ActorIn()).actor, archive=True)


@router.post("/projects/{research_id}:restore")
def restore_project(research_id: str, body: ActorIn | None = None,
                    ctx: ResearchContext = Depends(write_gate("restore"))) -> dict[str, Any]:
    return _archive(ctx, "restore", research_id, (body or ActorIn()).actor, archive=False)


# ── 事件帳（REST 與 SSE；兩者逐列相等）────────────────────────────────────────────────────────
def _event_out(row: dict[str, Any]) -> dict[str, Any]:
    return jsonable(row)


@router.get("/projects/{research_id}/events")
def list_events(research_id: str, after: int = Query(0, ge=0), limit: int = Query(100, ge=1),
                ctx: ResearchContext = Depends(read_gate)) -> dict[str, Any]:
    assert ctx.db is not None
    rid = _research_id(research_id)
    limit = min(limit, EVENTS_MAX_LIMIT)
    try:
        _project(ctx, rid)
        rows = ctx.db.list_events(rid, after_seq=after, limit=limit + 1)
    except ResearchDbError as exc:
        raise ApiError(503, "db_blocked", detail=str(exc)[:300]) from exc
    items = [_event_out(r) for r in rows[:limit]]
    return {"items": items, "next_seq": items[-1]["seq"] if items else after,
            "truncated": len(rows) > limit}


def _frame(event: dict[str, Any]) -> str:
    data = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    return f"id: {event['seq']}\nevent: {event['event_type']}\ndata: {data}\n\n"


async def _event_stream(request: Request, db: ResearchDb, research_id: str,
                        cursor: int) -> AsyncIterator[str]:
    """先重播游標之後的事件，再輪詢新事件；閒置時依間隔送心跳（`event: heartbeat`、不帶 id）。"""
    yield "retry: 3000\n\n"
    last_sent = time.monotonic()
    while True:
        batch = await asyncio.to_thread(db.list_events, research_id, after_seq=cursor,
                                        limit=STREAM_BATCH)
        if batch:
            for row in batch:
                yield _frame(_event_out(row))
            cursor = int(batch[-1]["seq"])
            last_sent = time.monotonic()
            continue
        if await request.is_disconnected():
            return
        if time.monotonic() - last_sent >= STREAM_HEARTBEAT_SECONDS:
            yield "event: heartbeat\ndata: {}\n\n"
            last_sent = time.monotonic()
        await asyncio.sleep(STREAM_POLL_SECONDS)


@router.get("/projects/{research_id}/stream")
async def stream_events(research_id: str, request: Request, after: int = Query(0, ge=0),
                        last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
                        ctx: ResearchContext = Depends(read_gate)) -> StreamingResponse:
    assert ctx.db is not None
    rid = _research_id(research_id)
    await asyncio.to_thread(_project, ctx, rid)
    try:
        header = int(last_event_id) if last_event_id else 0
    except ValueError:
        header = 0
    return StreamingResponse(_event_stream(request, ctx.db, rid, max(after, header, 0)),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── allowlist（D-17：產業網域由 ADMIN 逐一加入；全域資源、不寫 research_events）────────────────
def _entry_out(row: dict[str, Any]) -> dict[str, Any]:
    return {**jsonable(row), "source": "ADMIN"}


def _env_entries(cfg: Settings) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    lists = (("FETCH", cfg.research_fetch_allowlist), ("WEB", cfg.research_web_allowlist))
    for kind, hosts in lists:
        for host in hosts:
            entries.append({
                "id": None, "list_kind": kind, "host": host, "layer": None, "purpose": "",
                "tos_note": "", "min_interval_seconds": ENV_MIN_INTERVALS.get(
                    host, DEFAULT_ENV_MIN_INTERVAL), "enabled": True, "tos_acknowledged": False,
                "added_by": None, "added_at": None, "disabled_by": None, "disabled_at": None,
                "source": "ENV"})
    return entries


def effective_allowlist(cfg: Settings, entries: list[dict[str, Any]]) -> dict[str, list[str]]:
    """有效清單＝部署基底 ∪ 啟用中的 ADMIN 條目（D-17）；Reddit 預設不在任何清單。"""
    result: dict[str, list[str]] = {"FETCH": list(cfg.research_fetch_allowlist),
                                    "WEB": list(cfg.research_web_allowlist)}
    for e in entries:
        if e["enabled"] and e["host"] not in result[e["list_kind"]]:
            result[e["list_kind"]].append(e["host"])
    return result


@router.get("/allowlist")
def get_allowlist(ctx: ResearchContext = Depends(read_gate)) -> dict[str, Any]:
    assert ctx.db is not None
    try:
        rows = ctx.db.list_allowlist()
    except ResearchDbError as exc:
        raise ApiError(503, "db_blocked", detail=str(exc)[:300]) from exc
    return {"items": [*_env_entries(ctx.cfg), *[_entry_out(r) for r in rows]],
            "effective": effective_allowlist(ctx.cfg, rows)}


class AllowlistIn(BaseModel):
    list_kind: str
    host: str
    layer: str
    purpose: str = ""
    tos_note: str = ""
    min_interval_seconds: int = 3
    tos_acknowledged: bool = False
    added_by: str


@router.post("/allowlist", status_code=201)
def add_allowlist(body: AllowlistIn,
                  ctx: ResearchContext = Depends(write_gate("allowlist.add"))) -> dict[str, Any]:
    assert ctx.db is not None
    with operation(ctx, "allowlist.add", None, body.added_by):
        host = body.host.strip().lower().rstrip(".")
        problems = []
        if body.list_kind not in _LIST_KINDS:
            problems.append(_violation("list_kind", "invalid_value", "list_kind 須為 FETCH 或 WEB"))
        if body.layer not in _LAYERS:
            problems.append(_violation("layer", "invalid_value",
                                       f"layer 須為 {'｜'.join(_LAYERS)}"))
        if not _HOST_RE.match(host):
            problems.append(_violation("host", "invalid_host",
                                       "host 須是不含 scheme、埠與路徑的主機名"))
        if not 1 <= body.min_interval_seconds <= 3600:
            problems.append(_violation("min_interval_seconds", "out_of_range", "須為 1～3600"))
        if problems:
            raise unprocessable(problems, "invalid_request")
        result = ctx.db.add_allowlist_entry(
            list_kind=body.list_kind, host=host, layer=body.layer, purpose=body.purpose,
            tos_note=body.tos_note, min_interval_seconds=body.min_interval_seconds,
            tos_acknowledged=body.tos_acknowledged, added_by=_subject(body.added_by, "added_by"))
        entry = next(r for r in ctx.db.list_allowlist() if str(r["id"]) == result["entry_id"])
    return _entry_out(entry)


class AllowlistPatchIn(BaseModel):
    model_config = {"extra": "forbid"}

    enabled: bool
    disabled_by: str | None = None


@router.patch("/allowlist/{entry_id}")
def patch_allowlist(entry_id: str, body: AllowlistPatchIn,
                    ctx: ResearchContext = Depends(write_gate("allowlist.patch"))
                    ) -> dict[str, Any]:
    """只准改 `enabled`（停用時一併記 `disabled_by`／`disabled_at`）；條目不可刪、其餘
    欄位建立後不可改。"""
    assert ctx.db is not None
    with operation(ctx, "allowlist.patch", None, body.disabled_by):
        try:
            entry_uuid = str(uuid.UUID(entry_id))
        except ValueError as exc:
            raise ApiError(404, "research_not_found", entry_id=entry_id) from exc
        if not body.enabled:
            _subject(body.disabled_by, "disabled_by")
        try:
            ctx.db.set_allowlist_enabled(entry_id=entry_uuid, enabled=body.enabled,
                                         disabled_by=body.disabled_by)
        except ResearchGuardError as exc:
            if exc.rule == "allowlist_not_found":
                raise ApiError(404, "research_not_found", entry_id=entry_id) from exc
            raise
        entry = next(r for r in ctx.db.list_allowlist() if str(r["id"]) == entry_uuid)
    return _entry_out(entry)


# ── 追蹤來源（研究來源單一化；API 契約 §5A.2、§5A.3；全域資源、不寫 research_events）──────────────
_WATCH_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")


def _valid_hosts(ctx: ResearchContext) -> set[str]:
    """當前有效網域清單（FETCH ∪ WEB；部署基底 ∪ 啟用中的 ADMIN 條目）。"""
    assert ctx.db is not None
    effective = effective_allowlist(ctx.cfg, ctx.db.list_allowlist())
    return {*effective["FETCH"], *effective["WEB"]}


def _watch_out(row: dict[str, Any], hosts: set[str]) -> dict[str, Any]:
    host = host_of(row["url"])
    expand = None
    if row["expand_mode"] is not None:
        expand = {"mode": row["expand_mode"], "prefix": row["expand_prefix"],
                  "max": int(row["expand_max"])}
    return {"slug": row["slug"], "url": row["url"], "host": host, "kind": row["kind"],
            "extract": row["extract"], "layer": row["layer"], "expand": expand,
            "enabled": bool(row["enabled"]), "host_allowed": host in hosts,
            "added_by": row["added_by"], "added_at": utc_text(row["added_at"]),
            "disabled_by": row["disabled_by"], "disabled_at": utc_text(row["disabled_at"])}


def _too_large(exc: RegistryTooLarge) -> ApiError:
    return ApiError(422, "registry_too_large",
                    details={"what": "registry_text", "limit": exc.limit, "size": exc.size})


def _host_not_allowed(host: str) -> ApiError:
    return ApiError(422, "host_not_allowed", details={"host": host},
                    detail="這個網域還沒開放：請先在網域清單新增")


@router.get("/watch-sources")
def list_watch_sources(ctx: ResearchContext = Depends(read_gate)) -> dict[str, Any]:
    assert ctx.db is not None
    try:
        rows, hosts = ctx.db.list_watch_sources(), _valid_hosts(ctx)
    except ResearchDbError as exc:
        raise ApiError(503, "db_blocked", detail=str(exc)[:300]) from exc
    return {"items": [_watch_out(r, hosts) for r in rows]}


@router.post("/watch-sources", status_code=201)
def add_watch_source(body: dict[str, Any],
                     ctx: ResearchContext = Depends(write_gate("watch.add"))) -> dict[str, Any]:
    """檢查序（先中者定案）：輸入閘（六條規則一次全列，422 `invalid_request`）→ 單一閘（host 須在
    有效網域清單，422 `host_not_allowed`）→ slug 重複（409 `watch_source_exists`）→ 大小閘（假設
    寫入成功後的快照超過上限，422 `registry_too_large`）→ 寫入。任一關被拒＝零寫入。"""
    assert ctx.db is not None
    approver = body.get("added_by")
    with operation(ctx, "watch.add", None, approver if isinstance(approver, str) else None):
        problems = watch_violations({k: v for k, v in body.items() if k != "added_by"})
        if not isinstance(approver, str) or not approver.strip() or len(approver) > 100 \
                or any(ord(c) < 32 for c in approver):
            problems.append(_violation("added_by", "invalid_subject", "added_by 須為 1～100 字"))
        if problems:
            raise unprocessable(problems, "invalid_request")
        host = host_of(body["url"])
        allow_rows, rows = ctx.db.list_allowlist(), ctx.db.list_watch_sources()
        effective = effective_allowlist(ctx.cfg, allow_rows)
        if host not in {*effective["FETCH"], *effective["WEB"]}:
            raise _host_not_allowed(host)
        if any(r["slug"] == body["slug"] for r in rows):
            raise ApiError(409, "watch_source_exists", details={"slug": body["slug"]})
        expand = body.get("expand")
        candidate = {
            "slug": body["slug"], "url": body["url"], "kind": body["kind"],
            "extract": body["extract"], "layer": body["layer"],
            "expand_mode": expand["mode"] if expand else None,
            "expand_prefix": expand["prefix"] if expand else None,
            "expand_max": expand["max"] if expand else None, "enabled": True,
            "added_by": approver, "added_at": utc_now(), "disabled_by": None,
            "disabled_at": None}
        try:
            build_registry(ctx.cfg.research_fetch_allowlist, ctx.cfg.research_web_allowlist,
                           allow_rows, [*rows, candidate])
        except RegistryTooLarge as exc:
            raise _too_large(exc) from exc
        ctx.db.apply("watch.add", {
            "slug": body["slug"], "url": body["url"], "kind": body["kind"],
            "extract": body["extract"], "layer": body["layer"], "expand": expand,
            "added_by": approver})
        row = next(r for r in ctx.db.list_watch_sources() if r["slug"] == body["slug"])
    return _watch_out(row, _valid_hosts(ctx))


class WatchPatchIn(BaseModel):
    model_config = {"extra": "forbid"}

    enabled: bool
    disabled_by: str | None = None


@router.patch("/watch-sources/{slug}")
def patch_watch_source(slug: str, body: WatchPatchIn,
                       ctx: ResearchContext = Depends(write_gate("watch.patch"))
                       ) -> dict[str, Any]:
    """只准改 `enabled`（停用須帶 `disabled_by`；重新啟用清空停用欄並檢 host 仍在有效清單）。"""
    assert ctx.db is not None
    with operation(ctx, "watch.patch", None, body.disabled_by):
        not_found = ApiError(404, "research_not_found", details={"slug": slug})
        if not _WATCH_SLUG_RE.fullmatch(slug):
            raise not_found
        if not body.enabled:
            _subject(body.disabled_by, "disabled_by")
        row = next((r for r in ctx.db.list_watch_sources() if r["slug"] == slug), None)
        if row is None:
            raise not_found
        if body.enabled:
            host = host_of(row["url"])
            if host not in _valid_hosts(ctx):
                raise _host_not_allowed(host)
        try:
            ctx.db.apply("watch.set_enabled", {
                "slug": slug, "enabled": body.enabled, "disabled_by": body.disabled_by})
        except ResearchGuardError as exc:
            if exc.rule == "watch_source_not_found":
                raise not_found from exc
            raise
        row = next(r for r in ctx.db.list_watch_sources() if r["slug"] == slug)
    return _watch_out(row, _valid_hosts(ctx))


@router.get("/registry")
def get_registry(ctx: ResearchContext = Depends(read_gate)) -> dict[str, str]:
    """登記快照：Bridge 唯一產生者；不讀時鐘、不回部分內容。"""
    assert ctx.db is not None
    try:
        text, sha = build_registry(ctx.cfg.research_fetch_allowlist, ctx.cfg.research_web_allowlist,
                                   ctx.db.list_allowlist(), ctx.db.list_watch_sources())
    except RegistryTooLarge as exc:
        raise _too_large(exc) from exc
    except ResearchDbError as exc:
        raise ApiError(503, "db_blocked", detail=str(exc)[:300]) from exc
    return {"registry_text": text, "registry_sha256": sha}


# ── 能力探針（無 DSN 仍 200；D-49）──────────────────────────────────────────────────────────
@router.get("/capabilities")
def capabilities(request: Request) -> dict[str, Any]:
    """八個資訊欄（同 `/health/deep` 的 `research`）加契約 §2.1 的五個（D-76(1)）。
    `fetch_hosts`＝有效 FETCH 清單（部署基底 ∪ 啟用中的 ADMIN 條目）；無資料庫或資料庫暫時
    不可用時回部署基底——探針一律 200。"""
    ctx = get_context(request)
    hosts: Sequence[str] = ctx.cfg.research_fetch_allowlist
    if ctx.db is not None:
        try:
            hosts = effective_allowlist(ctx.cfg, ctx.db.list_allowlist())["FETCH"]
        except ResearchDbError:
            logger.warning("capabilities：讀不到 ADMIN allowlist，fetch_hosts 先回部署基底")
    return research_capabilities(ctx.cfg, fetch_hosts=hosts)


def reconcile_at_route(ctx: ResearchContext, research_id: str) -> dict[str, Any]:
    """分流時點的自動對帳（AC-961-20／AC-R2P-23-4）：分流成功路徑恰呼叫一次、失敗路徑不呼叫。呼叫點
    住 `routers/research_route.py` 的 `route_execute` 成功之後（P0 的 AST 鎖只認 `orchestrator.
    reconcile` 的實際呼叫點＝本檔；這支助手是它的 P1 增列呼叫點）。"""
    assert ctx.orchestrator is not None
    return ctx.orchestrator.reconcile(_project(ctx, research_id), actor="bridge")


def reconcile_at_delivery(ctx: ResearchContext, research_id: str) -> dict[str, Any]:
    """交付時點的自動對帳（AC-962-23／AC-R2P-23-4）：`:tag` 成功後恰呼叫一次。呼叫點住本檔（同
    `reconcile_at_route`；P0 的呼叫點鎖由 3 處增為 4 處）。"""
    assert ctx.orchestrator is not None
    return ctx.orchestrator.reconcile(_project(ctx, research_id), actor="bridge")


# P1 BR-D2：`:scr`、`:scr-apply`、`:decompose`、`:decomposition-signoff` 住 `research_scr.py`；
# P2 BR-P2：`:gates`、`:tag`、`:pr`、`:traceability-preview`、`:healing-sync`
# 住 `research_deliver.py`。
# 兩支子模組**各自在檔尾把自己的 router 掛回本檔的 router**（`app/main.py` 已 include 本 router；
# 不必再多一行）。本處只 import 它們以觸發註冊、**不存取 `.router`**：放檔尾是因為它們從本檔 import
# 共用助手；不存取 `.router` 是因為單獨 `import app.routers.research_deliver` 的入口會讓本檔在
# 子模組半初始化時執行到這裡，存取屬性會拋 AttributeError（SCG-4 一審 F-17 D-3，循環匯入）。
from . import research_deliver, research_scr  # noqa: E402, F401
