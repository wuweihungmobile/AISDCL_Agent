"""_builder — CheckpointPlugin 內部組裝 PlaybookCheckpoint 的 helper。

由 W4-T17 / M-11 解耦邏輯抽出：透過 EventBus emit ON_CHECKPOINT_SAVE_REQUEST
取得 GotoCounterPlugin 的 counter snapshot，組合成 PlaybookCheckpoint。

W3 不再修改本檔語意；僅由 plugin.py 委派呼叫。
AutoSDD_improving_01 W5/W6（2026-06-12）：additive 擴增讀取
merged.counter_diff['sdd_governance']（GotoCounter 先例之消費端，
計畫 §7 清單外之必要修改，詳 Audit §7.3 D-2）。
"""
from __future__ import annotations

from ...core.hookspec import HookContext, KernelPhase
from ...utils.checkpoint_manager import PlaybookCheckpoint


def build_checkpoint_from_ctx(
    plugin, ctx: HookContext, payload: dict,
) -> PlaybookCheckpoint | None:
    """從 ctx + payload 組裝 PlaybookCheckpoint（plugin 注入避免循環依賴）。

    SD_05 W1 Step-2：優先從 MergedResult.counter_diff（CounterSnapshotResult
    IHookResult 合併視圖）取得計數器。
    SD_05 W6：拔除 self._goto_counter 直接查詢的 backward compat 路徑，
    counter 統一透過 EventBus emit ON_CHECKPOINT_SAVE_REQUEST 取得。
    """
    playbook_path = payload.get("playbook_path", "")
    if not playbook_path:
        return None

    goto_c, inject_c, skip_c, evo_c = {}, {}, {}, {}
    sdd_gov: dict = {}
    # SD_06 W6（T6-8）：拔除 mutable container backward compat path（M-4 anti-pattern）。
    # 計數器統一透過 MergedResult.counter_diff（CounterSnapshotResult IHookResult）取得。
    if plugin._bus is not None:
        merged = plugin._bus.emit(HookContext(
            phase=KernelPhase.ON_CHECKPOINT_SAVE_REQUEST,
            playbook=ctx.playbook,
            task=ctx.task,
            step_idx=ctx.step_idx,
            attempt=ctx.attempt,
            payload={"playbook_path": playbook_path},
        ))
        if merged.counter_diff:
            goto_c = dict(merged.counter_diff.get("goto_counter", {}))
            inject_c = dict(merged.counter_diff.get("inject_before_counter", {}))
            skip_c = dict(merged.counter_diff.get("skip_to_counter", {}))
            evo_c = dict(merged.counter_diff.get("step_evolution_counter", {}))
            # AutoSDD_improving_01 §4.1（W6）：SddGovernancePlugin 以
            # CounterSnapshotResult 同款管道掛入 sdd_governance（additive）
            sdd_gov = dict(merged.counter_diff.get("sdd_governance", {}))

    return PlaybookCheckpoint(
        playbook_path=playbook_path,
        step_idx=int(payload.get("step_idx", ctx.step_idx or 0)),
        step_id=payload.get("step_id", ctx.task.step_id if ctx.task else ""),
        total_steps=int(payload.get("total_steps", len(ctx.playbook.tasks))),
        project=ctx.playbook.project,
        completed_step_log=list(payload.get("completed_step_log", [])),
        peak_token_pct=float(payload.get("peak_token_pct", 0.0)),
        failure_history=list(payload.get("failure_history", [])),
        active_step_attempt=int(payload.get("active_step_attempt", ctx.attempt or 0)),
        last_correction_prompt=str(payload.get("last_correction_prompt", "")),
        completed_step_ids=list(payload.get("completed_step_ids", [])),
        goto_counter=goto_c,
        inject_before_counter=inject_c,
        skip_to_counter=skip_c,
        step_evolution_counter=evo_c,
        sdd_governance=sdd_gov,
    )
