"""_phase_handlers — CheckpointPlugin 內 EventBus phase handler 集合。

從 plugin.py 抽出（避免 plugin.py 超 250 行 LOC 預算）。

包含：
  - on_pre_run                     PRE_RUN 載入 checkpoint + 廣播 ON_CHECKPOINT_RESTORE
  - save_interrupt                 ON_INTERRUPT phase handler
  - save_token_halt                ON_TOKEN_USAGE phase handler
  - save_evolution                 ON_EVOLUTION phase handler
  - on_persistence_request         ON_PERSISTENCE_REQUEST 通用持久化請求
  - on_escalation_dump_request     ON_ESCALATION_DUMP_REQUEST escalation dump
"""
from __future__ import annotations

import logging
from typing import Optional

from ...core.hookspec import (
    EscalationDumpedResult,
    HookContext,
    KernelPhase,
    PersistenceResult,
)
from ...models.counter_snapshot import CounterSnapshot

from ._builder import build_checkpoint_from_ctx

logger = logging.getLogger("autoclaude.plugins.checkpoint")


def on_pre_run(plugin, ctx: HookContext) -> None:
    payload = ctx.payload or {}
    playbook_path = payload.get("playbook_path")
    if not playbook_path:
        return
    cp = plugin._mgr.load(playbook_path)
    if cp is None:
        return
    snap = CounterSnapshot(
        goto_counter=dict(cp.goto_counter),
        inject_before_counter=dict(cp.inject_before_counter),
        skip_to_counter=dict(cp.skip_to_counter),
        step_evolution_counter=dict(cp.step_evolution_counter),
    )
    if plugin._bus is not None:
        plugin._bus.emit(HookContext(
            phase=KernelPhase.ON_CHECKPOINT_RESTORE,
            playbook=ctx.playbook,
            payload={
                "checkpoint": cp,
                "counter_snapshot": snap,
                "playbook_path": playbook_path,
            },
        ))


def save_interrupt(plugin, ctx: HookContext) -> Optional[PersistenceResult]:
    payload = ctx.payload or {}
    cp = build_checkpoint_from_ctx(plugin, ctx, payload)
    if cp is None:
        return None
    playbook_path = payload.get("playbook_path", "")
    try:
        plugin._mgr.save(cp, playbook_path)
        return PersistenceResult(
            contributor=plugin.name(), path=playbook_path,
            succeeded=True, kind="interrupt",
        )
    except Exception as exc:
        logger.error("CheckpointPlugin save_interrupt 失敗: %s", exc)
        return PersistenceResult(
            contributor=plugin.name(), path=playbook_path,
            succeeded=False, kind="interrupt",
        )


def save_token_halt(plugin, ctx: HookContext) -> Optional[PersistenceResult]:
    payload = ctx.payload or {}
    if not payload.get("request_halt", False):
        return None
    cp = build_checkpoint_from_ctx(plugin, ctx, payload)
    if cp is None:
        return None
    delay_minutes = int(payload.get("resume_delay_minutes", 30))
    if delay_minutes > 0:
        plugin._mgr.schedule_resume(cp, delay_minutes)
    playbook_path = payload.get("playbook_path", "")
    try:
        plugin._mgr.save(cp, playbook_path)
        return PersistenceResult(
            contributor=plugin.name(), path=playbook_path,
            succeeded=True, kind="interrupt",
        )
    except Exception as exc:
        logger.error("CheckpointPlugin save_token_halt 失敗: %s", exc)
        return PersistenceResult(
            contributor=plugin.name(), path=playbook_path,
            succeeded=False, kind="interrupt",
        )


def save_evolution(plugin, ctx: HookContext) -> Optional[PersistenceResult]:
    payload = ctx.payload or {}
    cp = build_checkpoint_from_ctx(plugin, ctx, payload)
    if cp is None:
        return None
    playbook_path = payload.get("playbook_path", "")
    try:
        plugin._mgr.save(cp, playbook_path)
        return PersistenceResult(
            contributor=plugin.name(), path=playbook_path,
            succeeded=True, kind="checkpoint",
        )
    except Exception as exc:
        logger.error("CheckpointPlugin save_evolution 失敗: %s", exc)
        return PersistenceResult(
            contributor=plugin.name(), path=playbook_path,
            succeeded=False, kind="checkpoint",
        )


def on_persistence_request(plugin, ctx: HookContext) -> Optional[PersistenceResult]:
    """W3：通用持久化請求入口（替代 imperative 方法的 EventBus 路徑）。

    payload schema:
      kind: "evolution_resume" | "interrupt"
      + 對應 kind 所需的參數
    """
    payload = ctx.payload or {}
    kind = payload.get("kind", "")
    if kind == "evolution_resume":
        evolved_path = payload.get("evolved_path", "")
        ok = plugin.save_evolution_resume_checkpoint(
            evolved_path=evolved_path,
            playbook=ctx.playbook,
            step_log=payload.get("step_log", []),
            completed_step_ids=payload.get("completed_step_ids", set()),
            step_evolution_counter=payload.get("step_evolution_counter"),
        )
        return PersistenceResult(
            contributor=plugin.name(), path=evolved_path,
            succeeded=ok, kind="checkpoint",
        )
    if kind == "interrupt":
        plugin.save_interrupt_checkpoint(
            playbook=ctx.playbook,
            playbook_path=payload.get("playbook_path", ""),
            task=ctx.task,
            step_idx=int(payload.get("step_idx", ctx.step_idx or 0)),
            step_log=payload.get("step_log", []),
            total=int(payload.get("total", len(ctx.playbook.tasks))),
            tracker=payload.get("tracker"),
            attempt=int(payload.get("attempt", 0)),
            goto_counter=payload.get("goto_counter"),
            inject_before_counter=payload.get("inject_before_counter"),
            skip_to_counter=payload.get("skip_to_counter"),
            completed_step_ids=payload.get("completed_step_ids"),
            step_evolution_counter=payload.get("step_evolution_counter"),
        )
        return PersistenceResult(
            contributor=plugin.name(),
            path=payload.get("playbook_path", ""),
            succeeded=True, kind="interrupt",
        )
    return None


def on_escalation_dump_request(
    plugin, ctx: HookContext,
) -> Optional[EscalationDumpedResult]:
    """W3：ESCALATION dump 持久化請求入口。

    SD_05 W3 三方審查 Arch-C1 / SD-C1 修：dump_path 改為從 plugin._last_dump_path
    取真實寫入路徑（含 timestamp + .md 副檔名），避免手構字串與真實檔名失真。
    """
    payload = ctx.payload or {}
    tracker = payload.get("tracker")
    if tracker is None or ctx.task is None:
        logger.warning(
            "ON_ESCALATION_DUMP_REQUEST 缺 tracker/task，已忽略"
            "（step_id=%s）",
            ctx.task.step_id if ctx.task else "<no-task>",
        )
        return None
    plugin.save_escalation_dump(
        tracker=tracker,
        task=ctx.task,
        playbook_path=payload.get("playbook_path", ""),
        final_eval_output=str(payload.get("final_eval_output", "")),
        checkpoint_dir=str(payload.get("checkpoint_dir", "")),
        log_dir=str(payload.get("log_dir", "")),
        human_hint=str(payload.get("human_hint", "")),
        notify_callback=payload.get("notify_callback"),
    )
    return EscalationDumpedResult(
        contributor=plugin.name(),
        dump_path=plugin._last_dump_path,
    )
