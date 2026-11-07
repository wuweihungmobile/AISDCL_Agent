"""/research/projects/{id}:route-preview、:route、:route-compensated（分流；IFACE §1.1～§1.7）。

與 `routers/research.py` 同一套檢查序（先中者定案）：`X-Bridge-Token`（未設 503、缺或錯 403）→
資料庫（無 DSN 503，不降級）→ 專案存在（404）→ 請求本文（422：同一個
`route.validate_request`，預演與確認共用）→ 部署支援（422 `route_unsupported_in_deployment`）→
Gate 0 現態（409）→ 分流衝突（409 `route_conflict`）→ 目標衝突（`branch_exists` 409、
`target_not_empty` 422）。**預演零副作用**：前面的每一關都是唯讀；確認才會寫表與動檔，而且只在
全部前置通過之後。

`:route` 是同步 HTTP（D-105）：回 200（全部成功）或 502 `route_step_failed`（該分流列已是 `FAILED`，
游標 `route／ROUTING／FAILED`）。GitHub token 只在軌道 B 且 `create_github` 時由請求本文帶入、只留在
記憶體與 gh 子行程環境，不入 argv、檔案、日誌、DB 與任何回應（`gitops` 的脫敏是最後一道牆）。
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends

from ..errors import ApiError, unprocessable
from ..research import fsm_ops, gitops, route, scaffold
from ..research.db import ResearchGuardError
from ..research.outbox import Op
from ..settings import Settings
from .research import (
    ResearchContext,
    _flow_out,
    _fsm_ctx,
    _project,
    _research_id,
    _violation,
    operation,
    write_gate,
)

router = APIRouter(prefix="/research", tags=["research"])
_MAX_TOKEN_CHARS = 255


def _caps(cfg: Settings, row: dict[str, Any], *, with_templates: bool) -> route.RouteCaps:
    return route.RouteCaps(
        templates=tuple(scaffold.list_templates()) if with_templates else (),
        worktree_root=cfg.worktree_root, scaffold_root=cfg.research_scaffold_root,
        repo_root=cfg.repo_root, rp_no=str(row["rp_no"]), slug=str(row["slug"]),
        sdd_subdir=route.sdd_subdir_of(cfg.repo_root))


def _research_info(row: dict[str, Any]) -> dict[str, Any]:
    return {"target_scope": row["target_scope"],
            "default_target_module": route.default_target_module(Path(row["workspace_path"]))}


class Prepared:
    """前置全部通過之後的結果（預演與確認共用）。"""

    def __init__(self, row: dict[str, Any], req: route.RouteRequest, caps: route.RouteCaps,
                 git: gitops.Gitops, info: dict[str, Any]) -> None:
        self.row, self.req, self.caps, self.git, self.info = row, req, caps, git, info
        self.retry_route: dict[str, Any] | None = None

    @property
    def derived(self) -> route.Derived:
        """推導路徑（部署不支援時 scaffold 根可能未設，所以在部署檢查通過後才推導）。"""
        return route.derive(self.req, self.caps)


def _token_of(body: dict[str, Any], req: route.RouteRequest) -> str | None:
    """GitHub token：只在軌道 B 且 `create_github` 時才讀（其餘一律忽略）。"""
    token = body.get("github_token")
    if req.track != "B" or not req.create_github or not isinstance(token, str) or not token:
        return None
    if len(token) > _MAX_TOKEN_CHARS or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise ApiError(422, "invalid_request", violations=[
            _violation("github_token", "invalid_token", "github_token 格式不合（內容不予回顯）")])
    return token


def _prepare(ctx: ResearchContext, rid: str, body: dict[str, Any], *, confirm: bool
             ) -> Prepared:
    assert ctx.db is not None
    row = _project(ctx, rid)
    info = _research_info(row)
    caps = _caps(ctx.cfg, row, with_templates=True)
    violations: list[dict[str, str]] = []
    req: route.RouteRequest | None = None
    try:             # 驗證只有一個入口：normalize_request 內的 validate_request
        req = route.normalize_request(body, caps, info)
    except route.RouteViolation as exc:
        violations = list(exc.violations)
    if confirm:
        violations += _binding_violations(body)
    if violations or req is None:
        raise ApiError(422, route.violation_reason(violations), violations=violations)
    token = _token_of(body, req) if confirm else None
    git = gitops.Gitops(scaffold_root=ctx.cfg.research_scaffold_root,
                        worktree_root=ctx.cfg.worktree_root, secrets=(token,) if token else (),
                        token=token)
    prepared = Prepared(row, req, caps, git, info)
    missing = route.deployment_missing(ctx.cfg, req, git, caps)
    if missing:
        raise ApiError(422, "route_unsupported_in_deployment", details={"missing": missing})
    _check_gate0(ctx, row)
    return prepared


def _binding_violations(body: dict[str, Any]) -> list[dict[str, str]]:
    """確認階段另需 `console_project_id`（console-api 先建好的專案列；軌道 A 與 B 皆必填）。"""
    value = body.get("console_project_id")
    if value is None or value == "":
        return [_violation("console_project_id", "required", "console_project_id 必填")]
    try:
        uuid.UUID(str(value))
    except ValueError:
        return [_violation("console_project_id", "invalid_uuid", "console_project_id 須為 UUID")]
    return []


def _check_gate0(ctx: ResearchContext, row: dict[str, Any]) -> None:
    """外環鍵須在 SPEC_FROZEN（Gate 0 已過）；ESCALATION 類給恢復指令。"""
    fctx = _fsm_ctx(ctx, row)
    state = fsm_ops.read_current(fctx)
    if fsm_ops.is_escalated(state):
        raise fsm_ops.escalated_error(fctx, state)
    if state.get("current_state") != "SPEC_FROZEN":
        raise fsm_ops.conflict("fsm_state_conflict", current_state=state.get("current_state"),
                               expected_state="SPEC_FROZEN")


def _check_conflicts(ctx: ResearchContext, rid: str, prep: Prepared, *, retry: bool,
                     preview: bool = False) -> None:
    """分流衝突與目標衝突（全部唯讀）。回 `prep.retry_route`（要續跑的 FAILED 列）。"""
    assert ctx.db is not None
    active = ctx.db.active_route(rid)
    if active is not None:
        raise ApiError(409, "route_conflict", details={
            "route_id": str(active["id"]), "status": active["status"]})
    latest = ctx.db.latest_route(rid)
    failed = latest if latest is not None and latest["status"] == "FAILED" else None
    if retry:
        if failed is None:
            raise ApiError(409, "route_conflict", details={"reason": "nothing_to_retry"})
        if route.stored_inputs_hash(ctx.db, str(failed["id"])) != prep.req.inputs_sha256():
            raise ApiError(409, "route_conflict", details={
                "reason": "inputs_changed", "route_id": str(failed["id"])})
        prep.retry_route = failed
        return
    if failed is not None and preview:
        return                       # 預演一個待重試的專案：分支與目標目錄本來就已存在，不再檢查
    if failed is not None:
        raise ApiError(409, "route_conflict", details={
            "reason": "retry_required", "route_id": str(failed["id"]), "status": "FAILED"})
    req, d = prep.req, prep.derived
    if req.track == "A":
        assert req.branch_name
        listed = prep.git.git(["branch", "--list", req.branch_name], cwd=ctx.cfg.repo_root)
        if listed.returncode == 0 and listed.stdout.strip():
            raise ApiError(409, "branch_exists", details={"branch": req.branch_name})
    else:
        assert ctx.cfg.research_scaffold_root is not None and d.new_root is not None
        target = d.new_root
        if target.exists() and (not target.is_dir() or any(target.iterdir())):
            rel = target.relative_to(ctx.cfg.research_scaffold_root).as_posix()
            raise ApiError(422, "target_not_empty", details={"path": rel})


def _prd_block(ctx: ResearchContext, rid: str, prep: Prepared) -> dict[str, Any]:
    assert ctx.db is not None
    head = ctx.db.head_prd(rid) or {}
    digests = ctx.db.gate0_digests(rid) or {}
    differs = route.scope_differs(prep.req.track, prep.info)
    return {"version_no": head.get("version_no"), "semver": head.get("semver"),
            "sha256": digests.get(route.BASELINE_REL, head.get("sha256")),
            "target_scope": prep.info["target_scope"], "scope_differs": differs}


# ── :route-preview ───────────────────────────────────────────────────────────────────────────
@router.post("/projects/{research_id}:route-preview")
def route_preview(research_id: str, body: dict[str, Any] = Body(...),
                  ctx: ResearchContext = Depends(write_gate("route-preview"))) -> dict[str, Any]:
    """預演（零副作用）：回與執行共用的動作清單；不寫任何表、不建任何目錄。"""
    assert ctx.db is not None
    rid = _research_id(research_id)
    with operation(ctx, "route-preview", rid, None):
        prep = _prepare(ctx, rid, body, confirm=False)
        _check_conflicts(ctx, rid, prep, retry=False, preview=True)
        plan = route.build_plan(prep.req, prep.caps)
        prd = _prd_block(ctx, rid, prep)
        out: dict[str, Any] = {
            "research_id": rid, "track": prep.req.track, "prd": prd,
            "scope_differs": prd["scope_differs"], "prd_target_scope": prep.info["target_scope"],
            "route_track": prep.req.track, "overridden_default": prep.req.overridden_default,
            "targets": route.placement_list(prep.info["default_target_module"]),
            "impl_fsm_project": prep.derived.impl_key,
            "impl_state_dir": str(prep.derived.state_dir),
            "execution_path": str(prep.derived.execution_path),
            "actions": plan, "warnings": route.warnings_for(prep.req)}
        if prep.req.track == "B":
            out["expected_tracked_files"] = route.expected_tracked(
                prep.req, prep.caps, Path(prep.row["workspace_path"]))
    return out


# ── :route ───────────────────────────────────────────────────────────────────────────────────
@router.post("/projects/{research_id}:route")
def route_execute(research_id: str, body: dict[str, Any] = Body(...),
                  ctx: ResearchContext = Depends(write_gate("route"))) -> dict[str, Any]:
    """確認並同步執行分流：200 `SUCCEEDED`，或 502 `route_step_failed`。"""
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    approver_raw = body.get("approver")
    with operation(ctx, "route", rid, approver_raw if isinstance(approver_raw, str) else None):
        approver = route.check_approver(approver_raw)
        retry = body.get("retry") is True
        with ctx.writer.project_lock(rid):
            prep = _prepare(ctx, rid, body, confirm=True)
            _check_conflicts(ctx, rid, prep, retry=retry)
            if prep.retry_route is not None:
                route_id = str(prep.retry_route["id"])
            else:
                route_id = route.new_route_id()
                d, req = prep.derived, prep.req
                ctx.writer.persist(Op("route.create", rid, {
                    "research_id": rid, "route_id": route_id, "track": req.track,
                    "target_kind": "MODULE" if req.track == "A" else "STANDALONE",
                    "target_module": req.target_module,
                    "target_path": str(d.execution_path)[:500], "git_branch": req.branch_name,
                    "base_ref": req.base_ref,
                    "repo_visibility": req.visibility if req.track == "B" else None,
                    "stack_template": req.stack_template,
                    "console_project_id": req.console_project_id,
                    "scope_differs_reason": req.scope_differs_reason, "decided_by": approver,
                    "created_at": route.now_iso(), "actor": approver}))
        run = route.RouteRun(cfg=ctx.cfg, db=ctx.db, writer=ctx.writer, git=prep.git,
                             req=prep.req, caps=prep.caps, project=prep.row, route_id=route_id,
                             approver=approver, audit=ctx.audit)
        result = route.execute(run)
        if result.status != "SUCCEEDED":
            raise ApiError(502, "route_step_failed", details={
                "route_id": route_id, "failure_step": result.failure_step,
                "reason": result.reason, "steps": result.steps,
                "cleanup_hint": "失敗不自動清理；需要時請人工以 git worktree remove 處置"})
        fresh = _project(ctx, rid)
        if ctx.orchestrator is not None:
            # 分流時點的自動對帳（AC-961-20）由 PKG-BR-D2 在此接線並更新 P0 的呼叫點鎖
            ctx.orchestrator.project_state(rid)
    return {"route_id": route_id, "status": "SUCCEEDED", "steps": result.steps,
            "impl_fsm_project": prep.derived.impl_key,
            "impl_state_dir": str(prep.derived.state_dir),
            "published_docs": result.published_docs, "flow": _flow_out(fresh)}


# ── :route-compensated ───────────────────────────────────────────────────────────────────────
@router.post("/projects/{research_id}:route-compensated")
def route_compensated(research_id: str, body: dict[str, Any] = Body(...),
                      ctx: ResearchContext = Depends(write_gate("route-compensated"))
                      ) -> dict[str, Any]:
    """console-api 補償完 Console 專案列後的通知（D-112）：只有 `FAILED` 的列才改 `COMPENSATED`。
    零 FSM 呼叫、零檔案動作（不 git clean、stash、刪目錄）。"""
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    requested_by = body.get("requested_by")
    with operation(ctx, "route-compensated", rid,
                   requested_by if isinstance(requested_by, str) else None):
        actor = route.check_approver(requested_by)
        reason = body.get("reason")
        violations = []
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= (
                route.COMPENSATE_REASON_MAX) or len(reason) > route.COMPENSATE_REASON_MAX:
            violations.append(_violation(
                "reason", "invalid_length",
                f"reason 須為 1～{route.COMPENSATE_REASON_MAX} 字"))
        try:
            route_id = str(uuid.UUID(str(body.get("route_id"))))
        except ValueError:
            violations.append(_violation("route_id", "invalid_uuid", "route_id 須為 UUID"))
            route_id = ""
        if violations:
            raise unprocessable(violations, "invalid_request")
        _project(ctx, rid)
        found = ctx.db.get_route(route_id)
        if found is None or str(found["research_id"]) != rid:
            raise ApiError(404, "research_not_found", route_id=route_id)
        with ctx.writer.project_lock(rid):
            try:
                ctx.writer.persist(Op("route.compensate", rid, {
                    "research_id": rid, "route_id": route_id, "reason": reason,
                    "actor": actor, "occurred_at": route.now_iso()}))
            except ResearchGuardError as exc:
                if exc.rule == "route_not_found":
                    raise ApiError(404, "research_not_found", route_id=route_id) from exc
                raise
    return {"route_id": route_id, "status": "COMPENSATED"}

