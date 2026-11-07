"""/research/projects/{id}:gates、:tag、:pr、:traceability-preview、:healing-sync（P2 BR-P2）。

檢查序（先中者定案）：權杖→資料庫→專案存在（404）→請求本文（422）→〔部署支援（422）〕→凍結 digest
比對（422 `digest_mismatch`，僅 `:gates`、`:tag`；漂移先於現態與 RTM 前置，D-142 ⚖P2-9）→
FSM 與業務前置（409）→副作用。`:healing-sync` 是事後偵測、無可阻擋的動作＝只記錄與告警。

本檔由 `routers/research.py` 檔尾掛進同一個 router（前綴 `/research`），所以必須經
`app.routers.research`（或 `app.main`）載入。新 reason 只有 `tag_exists`（409）與
`delivery_step_failed`（502）；其餘一律重用既有。
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from .. import rtm as rtm_mod
from ..errors import ApiError, unprocessable
from ..research import delivery, fsm_ops, gitops, healing, inner_gates, scr
from ..research import settings as settings_mod
from ..research.db import jsonable
from .research import (
    ResearchContext,
    _flow_out,
    _project,
    _research_id,
    _set_cursor,
    _violation,
    operation,
    reconcile_at_delivery,
    write_gate,
)

router = APIRouter(tags=["research"])
_SYNC_KEYS = frozenset({"requested_by", "run_id"})
_TAG_MESSAGE_MAX = 200


def checkpoint_dir_for(request: Request, run_id: str) -> Path:
    """run 的引擎檢查點目錄（RTM 報告所在）；run 不存在＝`ApiError`（呼叫端視為 RTM 不可得）。
    測試縫：可 monkeypatch 成暫存目錄。"""
    return request.app.state.runs.require(run_id).paths.checkpoints


def _rtm_loader(request: Request) -> Any:
    def load(run_id: str) -> dict[str, Any]:
        return rtm_mod.read_run_rtm(checkpoint_dir_for(request, run_id), run_id)

    return load


def _gate_env(ctx: ResearchContext, request: Request) -> inner_gates.GateEnv:
    assert ctx.db is not None and ctx.writer is not None
    return inner_gates.GateEnv(
        cfg=ctx.cfg, db=ctx.db, writer=ctx.writer, audit=ctx.audit, rtm_report=_rtm_loader(request),
        project_state=ctx.orchestrator.project_state if ctx.orchestrator else None)


def _delivery_env(ctx: ResearchContext, request: Request, git: gitops.Gitops
                  ) -> delivery.DeliveryEnv:
    assert ctx.db is not None and ctx.writer is not None
    return delivery.DeliveryEnv(cfg=ctx.cfg, db=ctx.db, writer=ctx.writer, git=git,
                                rtm_report=_rtm_loader(request))


def _git(ctx: ResearchContext, token: str | None = None) -> gitops.Gitops:
    return gitops.Gitops(scaffold_root=ctx.cfg.research_scaffold_root,
                         worktree_root=ctx.cfg.worktree_root,
                         secrets=(token,) if token else (), token=token)


def _succeeded_route(ctx: ResearchContext, rid: str) -> dict[str, Any] | None:
    assert ctx.db is not None
    route = ctx.db.active_route(rid)
    if (route is None or route["status"] != "SUCCEEDED" or not route.get("impl_fsm_project")
            or not route.get("impl_state_dir")):
        return None
    return route


def _inner_digests(ctx: ResearchContext, rid: str) -> tuple[dict[str, str], Path | None]:
    """內環鍵已凍結階段的 digest 聯集與目標根；沒有內環鍵或讀不到＝`({}, None)`。"""
    route = _succeeded_route(ctx, rid)
    if route is None:
        return {}, None
    fctx = fsm_ops.FsmCtx(sdd_root=ctx.cfg.sdd_root, state_dir=Path(route["impl_state_dir"]),
                          key=str(route["impl_fsm_project"]), audit=ctx.audit)
    try:
        state = fsm_ops.read_current(fctx)
    except ApiError:
        return {}, None
    stages = [s for s in (state.get("frozen_stages") or []) if isinstance(s, dict)]
    return healing.union_digests(stages), Path(route["target_path"])


def check_drift(ctx: ResearchContext, rid: str) -> None:
    """`:gates`／`:tag` 前置：凍結 digest 與目標根不符＝422 `digest_mismatch`（阻擋；零寫入）。"""
    digests, root = _inner_digests(ctx, rid)
    if root is None:
        return
    drift = healing.detect_spec_change(digests, root)
    if drift:
        raise ApiError(422, "digest_mismatch", details={"drift": [
            {"path": d["path"], "expected_sha256": d["expected"], "actual_sha256": d["actual"]}
            for d in drift]})


def sync_best_effort(ctx: ResearchContext, row: dict[str, Any]) -> None:
    """`:reconcile` 尾端順帶補寫自癒日誌：失敗不影響對帳結果。"""
    try:
        digests, root = _inner_digests(ctx, str(row["id"]))
        assert ctx.db is not None and ctx.writer is not None
        healing.sync(healing.HealingEnv(ctx.db, ctx.writer), row, frozen_digests=digests,
                     root=root, actor="system")
    except Exception:                     # noqa: BLE001 — 對帳結果不受補寫失敗影響
        return


def _uuid_field(body: dict[str, Any], name: str) -> list[dict[str, str]]:
    try:
        uuid.UUID(str(body.get(name)))
    except ValueError:
        return [_violation(name, "invalid_uuid", f"{name} 須為 UUID")]
    return []


# ── :traceability-preview ────────────────────────────────────────────────────────────────────
@router.post("/projects/{research_id}:traceability-preview")
def traceability_preview(research_id: str, request: Request,
                         body: dict[str, Any] = Body(default_factory=dict),
                         ctx: ResearchContext = Depends(write_gate("traceability.preview"))
                         ) -> dict[str, Any]:
    rid = _research_id(research_id)
    with operation(ctx, "traceability.preview", rid, None):
        row = _project(ctx, rid)
        run_id = body.get("run_id")
        route = _succeeded_route(ctx, rid)
        return delivery.preview(_delivery_env(ctx, request, _git(ctx)), row,
                                impl_key=str((route or {}).get("impl_fsm_project") or ""),
                                run_id=run_id if isinstance(run_id, str) else None)
    raise AssertionError("unreachable")


# ── :healing-sync ────────────────────────────────────────────────────────────────────────────
@router.post("/projects/{research_id}:healing-sync")
def healing_sync(research_id: str, body: dict[str, Any] = Body(default_factory=dict),
                 ctx: ResearchContext = Depends(write_gate("healing.sync"))) -> dict[str, Any]:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    with operation(ctx, "healing.sync", rid, "system"):
        row = _project(ctx, rid)
        extra = sorted(set(body) - _SYNC_KEYS)
        violations = [_violation(k, "unknown_field", f"不認得的欄位 {k}") for k in extra]
        if body.get("requested_by", "system") != "system":
            violations.append(_violation("requested_by", "invalid_subject",
                                         "healing-sync 只准 requested_by=system"))
        if violations:
            raise unprocessable(violations, "invalid_request")
        digests, root = _inner_digests(ctx, rid)
        return healing.sync(healing.HealingEnv(ctx.db, ctx.writer), row, frozen_digests=digests,
                            root=root, actor="system")
    raise AssertionError("unreachable")


# ── :gates ───────────────────────────────────────────────────────────────────────────────────
@router.post("/projects/{research_id}:gates")
def register_gate(research_id: str, request: Request, body: dict[str, Any] = Body(...),
                  ctx: ResearchContext = Depends(write_gate("gates.register"))) -> dict[str, Any]:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    raw_by = body.get("approver")
    with operation(ctx, "gates.register", rid, raw_by if isinstance(raw_by, str) else None):
        row = _project(ctx, rid)
        violations = inner_gates.validate_request(body) + _uuid_field(body, "decision_id")
        if violations:
            raise unprocessable(violations, "invalid_request")
        scr.check_approver(raw_by)
        check_drift(ctx, rid)
        result = inner_gates.register(_gate_env(ctx, request), row, body)
        return {**result, "flow": _flow_out(_project(ctx, rid))}
    raise AssertionError("unreachable")


# ── :tag ─────────────────────────────────────────────────────────────────────────────────────
def _tag_violations(body: dict[str, Any]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if not gitops.valid_semver(body.get("tag_name")):
        found.append(_violation("tagName", "not_semver", "tagName 須為 semver（至多 64 字）"))
    message = body.get("message")
    if message is not None and (not isinstance(message, str) or len(message) > _TAG_MESSAGE_MAX):
        found.append(_violation("message", "message_too_long",
                                f"message 須為至多 {_TAG_MESSAGE_MAX} 字的字串"))
    if body.get("push", False) not in (True, False):
        found.append(_violation("push", "invalid_boolean", "push 須為布林"))
    if body.get("create_github_release", False) is not False:
        found.append(_violation("createGithubRelease", "release_not_supported",
                                "P2 不建立 GitHub Release"))
    return found


def _unsupported(ctx: ResearchContext, rid: str) -> None:
    """容器模式（軌道 A 而 monorepo 不可寫）＝422 `route_unsupported_in_deployment`，零副作用。"""
    route = _succeeded_route(ctx, rid)
    if route is not None and route["track"] == "A" and not settings_mod.repo_writable(ctx.cfg):
        raise ApiError(422, "route_unsupported_in_deployment", details={"missing": [{
            "item": "repo_writable",
            "reason": "此部署無法寫入 monorepo（容器模式請改用本機模式）"}]})


@router.post("/projects/{research_id}:tag", status_code=201)
def create_tag(research_id: str, request: Request, body: dict[str, Any] = Body(...),
               ctx: ResearchContext = Depends(write_gate("delivery.tag"))) -> dict[str, Any]:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    raw_by = body.get("approver")
    with operation(ctx, "delivery.tag", rid, raw_by if isinstance(raw_by, str) else None):
        row = _project(ctx, rid)
        violations = _tag_violations(body)
        if violations:
            raise unprocessable(violations, "invalid_request")
        approver = scr.check_approver(raw_by)
        _unsupported(ctx, rid)
        check_drift(ctx, rid)
        tag_name = str(body["tag_name"])
        genv, denv = _gate_env(ctx, request), _delivery_env(ctx, request, _git(ctx))
        with ctx.writer.project_lock(rid):
            scr.guard_inner_start(ctx.db, rid)
            route = inner_gates.inner_route(ctx.db, rid)
            state = fsm_ops.current_state(inner_gates.inner_fsm(genv, route, approver))
            resumed = any(d["kind"] == "RELEASE_TAG" and d["ref"] == tag_name
                          and d["status"] == "CREATED" for d in ctx.db.list_deliveries(rid))
            trace = delivery.load_trace(denv, row, str(route["impl_fsm_project"]))
            if resumed:
                unmet = [] if state in ("RELEASE_READY", "RELEASE") else ["not_release_ready"]
            else:
                unmet = delivery.tag_unmet(state, trace.trace)
            if unmet:
                raise ApiError(409, "fsm_state_conflict", details={
                    "unmet": unmet, "current_state": state})
            made = delivery.create_tag(
                denv, row, route, tag_name=tag_name, message=str(body.get("message") or ""),
                push=bool(body.get("push", False)), approver=approver, fsm_state=state,
                rtm_run_id=body.get("run_id") if isinstance(body.get("run_id"), str) else None,
                trace=trace)
            try:
                final = inner_gates.release_transition(genv, row, tag_name, approver)
            except ApiError as exc:
                raise delivery.fail(denv, rid, "RELEASE_TAG", "fsm_release", actor=approver,
                                    reason=str(exc.body.get("reason"))) from exc
            _set_cursor(ctx, rid, {"step": "deliver", "phase": "DELIVERED",
                                   "status": "COMPLETED", "detail": ""}, approver)
            if ctx.orchestrator is not None:
                ctx.orchestrator.project_state(rid)
            reconcile_at_delivery(ctx, rid)
            return jsonable({"delivery": made["delivery"], "snapshot": made["snapshot"],
                             "flow": _flow_out(_project(ctx, rid)), "fsmState": final})
    raise AssertionError("unreachable")


# ── :pr ──────────────────────────────────────────────────────────────────────────────────────
@router.post("/projects/{research_id}:pr", status_code=201)
def create_pr(research_id: str, request: Request, body: dict[str, Any] = Body(...),
              ctx: ResearchContext = Depends(write_gate("delivery.pr"))) -> Any:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    raw_by = body.get("approver")
    with operation(ctx, "delivery.pr", rid, raw_by if isinstance(raw_by, str) else None):
        row = _project(ctx, rid)
        token = body.get("github_token")
        token = token if isinstance(token, str) and token else None
        git = _git(ctx, token)
        denv = _delivery_env(ctx, request, git)
        route = _succeeded_route(ctx, rid)
        if route is None:
            raise ApiError(409, "fsm_state_conflict", details={"cause": "route_not_succeeded"})
        trace = delivery.load_trace(denv, row, str(route["impl_fsm_project"]))
        totals = trace.trace["totals"]
        expected = delivery.pr_title(str(row["rp_no"]), str(row["title"]),
                                     int(totals["frTotal"]), int(totals["acTotal"]))
        violations = delivery.pr_request_violations(body, expected)
        if violations:
            raise unprocessable(violations, "invalid_request")
        approver = scr.check_approver(raw_by)
        cwd = Path(route["target_path"])
        missing = delivery.pr_missing(denv, route, cwd)
        if missing:
            raise ApiError(422, "route_unsupported_in_deployment", details={"missing": missing})
        with ctx.writer.project_lock(rid):
            scr.guard_inner_start(ctx.db, rid)
            genv = _gate_env(ctx, request)
            state = fsm_ops.current_state(inner_gates.inner_fsm(genv, route, approver))
            made, created = delivery.create_pr(
                denv, row, route, branch=body.get("branch"), approver=approver, fsm_state=state,
                ctx=trace)
            payload = {"delivery": made, "created": created}
            return JSONResponse(status_code=201 if created else 200, content=jsonable(payload))
    raise AssertionError("unreachable")
