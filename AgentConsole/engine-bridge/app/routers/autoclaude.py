"""/autoclaude/*：run 生命週期、SSE、checkpoint、目標拆解（契約逐字，見 API 契約文件）。"""
from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Body, Header, Query, Request
from fastapi.responses import StreamingResponse

from .. import security
from ..errors import not_found, unprocessable
from ..events import to_sse_data
from ..models import (
    TERMINAL_STATUSES,
    ApproveIn,
    CheckpointOut,
    ControlIn,
    DecomposeIn,
    RestoreIn,
    RunCreatedOut,
    RunCreateIn,
    RunStateOut,
    RunStatus,
    StatusAckOut,
)
from ..runner import RunHandle, RunManager

router = APIRouter(prefix="/autoclaude", tags=["autoclaude"])

SSE_HEARTBEAT_SECONDS = 15.0
SSE_BATCH = 200


def _mgr(request: Request) -> RunManager:
    return request.app.state.runs


def _control_env(request: Request, env: dict[str, str]) -> dict[str, str] | None:
    if not env:
        return None
    violations = security.validate_env(
        env, request.app.state.settings.outbound_allowlist, audit=request.app.state.audit)
    if violations:
        raise unprocessable(violations)
    return env


@router.post("/runs", status_code=201, response_model=RunCreatedOut)
def create_run(body: RunCreateIn, request: Request) -> dict[str, Any]:
    handle = _mgr(request).create(body)
    rec = handle.rec
    return {"run_id": rec.run_id, "status": RunStatus.RUNNING.value, "pid": rec.pid,
            "workspace": str(handle.paths.run_dir), "bridge_instance": rec.bridge_instance}


@router.post("/runs/{run_id}:pause", status_code=202, response_model=StatusAckOut)
def pause_run(run_id: str, request: Request) -> dict[str, str]:
    return {"status": _mgr(request).require(run_id).pause()}


@router.post("/runs/{run_id}:resume", status_code=202, response_model=StatusAckOut)
def resume_run(run_id: str, request: Request,
               body: ControlIn | None = Body(default=None)) -> dict[str, str]:
    handle = _mgr(request).require(run_id)
    return {"status": handle.resume(_control_env(request, body.env if body else {}))}


@router.post("/runs/{run_id}:stop", status_code=202, response_model=StatusAckOut)
def stop_run(run_id: str, request: Request) -> dict[str, str]:
    return {"status": _mgr(request).require(run_id).stop()}


@router.get("/runs/{run_id}", response_model=RunStateOut)
def get_run(run_id: str, request: Request) -> dict[str, Any]:
    return _mgr(request).require(run_id).snapshot()


@router.get("/runs/{run_id}/events")
def get_events(run_id: str, request: Request, after: int = Query(0, ge=0),
               limit: int = Query(500, ge=1, le=5000)) -> list[dict[str, Any]]:
    handle = _mgr(request).require(run_id)
    return handle.store.replay(after, limit)


@router.get("/runs/{run_id}/checkpoints", response_model=list[CheckpointOut])
def list_checkpoints(run_id: str, request: Request) -> list[dict[str, Any]]:
    return _mgr(request).require(run_id).history.list_meta()


@router.post("/runs/{run_id}/restore", status_code=202, response_model=StatusAckOut)
def restore_run(run_id: str, body: RestoreIn, request: Request) -> dict[str, str]:
    handle = _mgr(request).require(run_id)
    handle.restore(body.checkpoint_id, _control_env(request, body.env))
    return {"status": RunStatus.RUNNING.value}


# ── SSE ──────────────────────────────────────────────────────────────────────
def _frame(event: dict[str, Any]) -> str:
    data = json.dumps(to_sse_data(event), ensure_ascii=False, separators=(",", ":"))
    return f"id: {event['seq']}\nevent: {event['event']}\ndata: {data}\n\n"


def _parse_cursor(after: int, last_event_id: str | None) -> int:
    try:
        header = int(last_event_id) if last_event_id else 0
    except ValueError:
        header = 0
    return max(after, header, 0)


async def _sse(request: Request, handle: RunHandle, cursor: int) -> AsyncIterator[str]:
    """先重播 cursor 之後的事件，再 tail；run 進入終態且游標追上時結束（PAUSED 不結束）。"""
    store = handle.store
    loop = asyncio.get_running_loop()
    wakeup = asyncio.Event()
    token = store.add_waiter(loop, wakeup)
    last_sent = time.monotonic()
    try:
        yield "retry: 3000\n\n"
        while True:
            wakeup.clear()                       # 先清再查，避免「查完到等待之間」漏掉喚醒
            batch = await asyncio.to_thread(store.replay, cursor, SSE_BATCH)
            if batch:
                for event in batch:
                    yield _frame(event)
                cursor = batch[-1]["seq"]
                last_sent = time.monotonic()
                continue
            if handle.rec.status in {s.value for s in TERMINAL_STATUSES}:
                tail = await asyncio.to_thread(store.replay, cursor, SSE_BATCH)
                if not tail:
                    return                       # 終態事件一定先於狀態欄位寫入，這裡已全數送出
                continue
            if await request.is_disconnected():
                return
            try:
                await asyncio.wait_for(wakeup.wait(), timeout=1.0)
            except TimeoutError:
                if time.monotonic() - last_sent >= SSE_HEARTBEAT_SECONDS:
                    yield ": keep-alive\n\n"
                    last_sent = time.monotonic()
    finally:
        store.remove_waiter(token)


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str, request: Request, after: int = Query(0, ge=0),
                     last_event_id: str | None = Header(default=None, alias="Last-Event-ID")):
    handle = _mgr(request).get(run_id)
    if handle is None:
        raise not_found("run_not_found", run_id=run_id)
    return StreamingResponse(
        _sse(request, handle, _parse_cursor(after, last_event_id)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── 目標拆解 ─────────────────────────────────────────────────────────────────
@router.post("/decompose")
def decompose(body: DecomposeIn, request: Request) -> dict[str, Any]:
    return request.app.state.decompose.decompose(body)


@router.post("/decompose/{draft_id}:approve")
def approve_draft(draft_id: str, body: ApproveIn, request: Request) -> dict[str, Any]:
    return request.app.state.decompose.approve(draft_id, body)
