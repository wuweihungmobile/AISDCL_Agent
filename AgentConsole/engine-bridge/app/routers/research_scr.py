"""/research/projects/{id}:scr、:scr-apply、:decompose、:decomposition-signoff（P1 BR-D2）。

依據 IFACE §1.4～§1.8；D-94、D-103、D-104、D-113。檢查序與 `routers/research.py` 相同（先中者
定案）：權杖→資料庫→專案存在（404）→請求本文（422）→業務前置（409）。本檔由 `routers/research.py`
檔尾掛進同一個 router（前綴 `/research`、`write_gate`／`operation` 共用，不複製貼上），所以必須
經 `app.routers.research`（或 `app.main`）載入，不可單獨先 import 本檔。

  · `:scr`（202；HEALING_FAILED 為 200）：輸入閘、OPEN 檢查、現態矩陣預檢、`scr_limit`，再走三路
    （`research/scr.py`）；console-api 已先停進行中的 run（D-103），這裡不停 run；
  · `:scr-apply`（ADMIN 重試）：只對 `APPROVED` 的 MINOR SCR；已 `APPLIED` 回 200（冪等）；
  · `:decompose`（同步、非 stage run）：逐 US 呼叫既有 `DecomposeService`，確定性綁定 AC；
  · `:decomposition-signoff`：console-api 先走既有 import／signoff 取得 `import_record_id`，
    Bridge 再一次寫 `SIGNED_OFF`（D-113）。
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from ..errors import ApiError, unprocessable
from ..research import decompose_plan, export, fsm_ops, layout, scr
from ..research.db import utc_now
from .research import (
    ResearchContext,
    _flow_out,
    _fsm_init_step,
    _init_files,
    _project,
    _research_id,
    _set_cursor,
    _subject,
    _violation,
    operation,
    write_gate,
)

router = APIRouter(tags=["research"])


def _env(ctx: ResearchContext) -> scr.ScrEnv:
    assert ctx.db is not None and ctx.writer is not None
    return scr.ScrEnv(cfg=ctx.cfg, db=ctx.db, writer=ctx.writer, audit=ctx.audit)


def _frozen_model(ctx: ResearchContext, row: dict[str, Any]) -> scr.FrozenPrd:
    assert ctx.db is not None
    ref = decompose_plan.frozen_prd(ctx.db, str(row["id"]))
    if ref is None:
        return scr.FrozenPrd(frozenset(), frozenset())
    try:
        text = layout.safe_join(Path(row["workspace_path"]), ref.rel).read_text(encoding="utf-8")
    except OSError:
        return scr.FrozenPrd(frozenset(), frozenset())
    return scr.parse_frozen_prd(text)


# ── :scr ─────────────────────────────────────────────────────────────────────────────────────
def _successor_factory(ctx: ResearchContext, requested_by: str
                       ) -> Callable[[dict[str, Any], int], dict[str, Any]]:
    """MAJOR 的新研究專案（slug `<舊 slug>-scr<N>`、`parent_research_id`；同 `create_project`）。"""

    def make(old: dict[str, Any], scr_no: int) -> dict[str, Any]:
        assert ctx.db is not None and ctx.writer is not None
        # D-136：確定性截斷（舊 slug 截到 30－len(後綴) 字、去尾端 `-`），不回 422；撞名走 409
        suffix = f"-scr{scr_no}"
        slug = f"{str(old['slug'])[:30 - len(suffix)].rstrip('-')}{suffix}"
        if ctx.db.find_active_project(slug) is not None:
            raise ApiError(409, "slug_in_use", details={"slug": slug})
        new_id = str(uuid.uuid4())
        workspace = layout.resolve_workspace(ctx.cfg.research_root, slug,
                                             ctx.cfg.allowed_path_roots)
        rp_no = ctx.db.allocate_rp_no()["rp_no"]
        created_at = utc_now().replace(microsecond=0)
        scope = dict(old["scope"] or {})
        issue = export.render_issue_scope({
            "research_id": new_id, "rp_no": rp_no, "slug": slug, "scope_rev": 1,
            "title": old["title"], "topic": old["topic"], "scope": scope,
            "depth_level": old["depth_level"], "created_by": requested_by,
            "created_at": created_at})
        payload: dict[str, Any] = dict(
            research_id=new_id, rp_no=rp_no, slug=slug, title=old["title"], topic=old["topic"],
            scope=scope, depth_level=old["depth_level"], target_scope=old["target_scope"],
            workspace_path=str(workspace), fsm_project=f"research-{slug}",
            fsm_state_dir=str(layout.fsm_state_dir(workspace)), created_by=requested_by,
            created_at=created_at.isoformat(), parent_research_id=str(old["id"]),
            flow={"step": "topic", "phase": "INGESTED", "status": "IDLE", "detail": ""})
        failed = _init_files(ctx, workspace, issue, payload, new_id)
        row = _project(ctx, new_id)
        if failed is None:
            failed = _fsm_init_step(ctx, row, actor=requested_by)
            if failed is not None:
                _set_cursor(ctx, new_id, {"step": row["flow_step"], "phase": row["flow_phase"],
                                          "status": "FAILED", "detail": f"init_failed:{failed}"},
                            "bridge")
        if failed is not None:
            raise ApiError(502, "init_failed", details={"step": failed, "successor": new_id})
        return {"research_id": new_id, "rp_no": row["rp_no"]}

    return make


@router.post("/projects/{research_id}:scr", status_code=202)
def open_scr(research_id: str, body: dict[str, Any] = Body(...),
             ctx: ResearchContext = Depends(write_gate("scr.open"))) -> Any:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    raw_by = body.get("requested_by")
    with operation(ctx, "scr.open", rid, raw_by if isinstance(raw_by, str) else None):
        requested_by = _subject(raw_by, "requested_by")
        row = _project(ctx, rid)
        violations = scr.validate_request(body, _frozen_model(ctx, row))
        if violations:
            raise unprocessable(violations, "invalid_request")
        with ctx.writer.project_lock(rid):
            env = _env(ctx)
            kind, source = str(body["kind"]), str(body["source_kind"])
            route = scr.check_open_preconditions(env, row, kind, source)
            if kind == "MAJOR":
                return scr.open_major(env, row, body, requested_by,
                                      _successor_factory(ctx, requested_by))
            if source == "HEALING_FAILED":
                assert route is not None
                return JSONResponse(status_code=200, content=scr.open_healing_failed(
                    env, row, body, route, requested_by))
            return scr.open_minor(env, row, body, requested_by)
    raise AssertionError("unreachable")


# ── :scr-apply ───────────────────────────────────────────────────────────────────────────────
@router.post("/projects/{research_id}:scr-apply")
def apply_scr(research_id: str, body: dict[str, Any] = Body(...),
              ctx: ResearchContext = Depends(write_gate("scr.apply"))) -> dict[str, Any]:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    raw = body.get("approver")
    with operation(ctx, "scr.apply", rid, raw if isinstance(raw, str) else None):
        approver = scr.check_approver(raw)
        scr_no = body.get("scr_no")
        if isinstance(scr_no, bool) or not isinstance(scr_no, int) or scr_no < 1:
            raise unprocessable([_violation("scr_no", "invalid_scr_no", "scr_no 須為正整數")],
                                "invalid_request")
        row = _project(ctx, rid)
        with ctx.writer.project_lock(rid):
            found = ctx.db.get_scr(rid, scr_no)
            if found is None:
                raise ApiError(404, "research_not_found", scr_no=scr_no)
            if found["status"] == "APPLIED":       # 冪等：零 FSM 寫入
                return {"scr_no": scr_no, "status": "APPLIED",
                        "impl_fsm_actions": found["impl_fsm_actions"],
                        "flow": _flow_out(_project(ctx, rid))}
            scr.check_applicable(found)
            env = _env(ctx)
            base = scr.baseline_from_db(env, row, found)
            result = scr.apply_and_record(env, row, found, approver=approver, base=base)
            fresh = ctx.db.get_scr(rid, scr_no) or found
            if ctx.orchestrator is not None:
                ctx.orchestrator.project_state(rid)
            out: dict[str, Any] = {"scr_no": scr_no, "status": result.status,
                                   "impl_fsm_actions": fresh["impl_fsm_actions"],
                                   "flow": _flow_out(_project(ctx, rid))}
            if result.status != "APPLIED":
                out["detail"] = result.detail
            return out
    raise AssertionError("unreachable")


# ── :decompose ───────────────────────────────────────────────────────────────────────────────
def _decompose_env(ctx: ResearchContext, request: Request) -> decompose_plan.DecomposeEnv:
    assert ctx.db is not None and ctx.writer is not None
    return decompose_plan.DecomposeEnv(db=ctx.db, writer=ctx.writer,
                                       service=request.app.state.decompose)


@router.post("/projects/{research_id}:decompose")
def decompose(research_id: str, request: Request, body: dict[str, Any] = Body(...),
              ctx: ResearchContext = Depends(write_gate("decompose"))) -> dict[str, Any]:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    raw_by = body.get("requested_by")
    with operation(ctx, "decompose", rid, raw_by if isinstance(raw_by, str) else None):
        requested_by = _subject(raw_by, "requested_by")
        scope = body.get("scope") or {}
        by = scope.get("by", "us") if isinstance(scope, dict) else "us"
        us_ids = scope.get("us_ids") if isinstance(scope, dict) else None
        if by not in decompose_plan.BY_MODES or (us_ids is not None and not (
                isinstance(us_ids, list) and all(isinstance(u, str) for u in us_ids))):
            raise unprocessable([_violation("scope", "invalid_scope",
                                            "scope.by 須為 us｜goal｜all、us_ids 須為字串清單")],
                                "invalid_request")
        row = _project(ctx, rid)
        with ctx.writer.project_lock(rid):
            scr.guard_inner_start(ctx.db, rid)
            route = ctx.db.active_route(rid)
            if route is None or route["status"] != "SUCCEEDED":
                raise ApiError(409, "fsm_state_conflict", details={"cause": "route_not_succeeded"})
            state = fsm_ops.read_current(fsm_ops.FsmCtx(
                sdd_root=ctx.cfg.sdd_root, state_dir=Path(row["fsm_state_dir"]),
                key=str(row["fsm_project"])))
            if state.get("current_state") != "SPEC_FROZEN":
                raise ApiError(409, "fsm_state_conflict", details={
                    "current_state": state.get("current_state"), "expected_state": "SPEC_FROZEN"})
            active = ctx.db.active_stage_run(rid)
            if active is not None:
                raise ApiError(409, "stage_conflict", details={
                    "activeStageRunId": str(active["id"]), "activeStage": active["stage"]})
            result = decompose_plan.decompose(_decompose_env(ctx, request), row,
                                              requested_by=requested_by, by=by, us_ids=us_ids)
            if ctx.orchestrator is not None:
                ctx.orchestrator.project_state(rid)
            return result
    raise AssertionError("unreachable")


# ── :decomposition-signoff ───────────────────────────────────────────────────────────────────
@router.post("/projects/{research_id}:decomposition-signoff")
def decomposition_signoff(research_id: str, request: Request, body: dict[str, Any] = Body(...),
                          ctx: ResearchContext = Depends(write_gate("decomposition.signoff"))
                          ) -> dict[str, Any]:
    assert ctx.db is not None and ctx.writer is not None
    rid = _research_id(research_id)
    raw = body.get("approver")
    with operation(ctx, "decomposition.signoff", rid, raw if isinstance(raw, str) else None):
        row = _project(ctx, rid)
        with ctx.writer.project_lock(rid):
            return decompose_plan.signoff(_decompose_env(ctx, request), row, body)
    raise AssertionError("unreachable")
