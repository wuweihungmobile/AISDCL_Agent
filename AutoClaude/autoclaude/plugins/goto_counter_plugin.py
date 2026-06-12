"""GotoCounterPlugin — v1.1 新增 Plugin，承接 Gap-042/048/049 跨 Session 計數器。

對應：
  - SD_Improving_01.md v1.1 §3.5 表格第 3 列（priority=85）
  - SD_Improving_02.md v1.1 §2.5 W6 #6（v1.1 新增遷移項）

職責：
  1. 維護 4 個計數器（goto_counter / inject_before_counter / skip_to_counter /
     step_evolution_counter）
  2. 提供查詢介面（is_over_limit）供 Kernel / EvolutionPlugin 在處理 mutation 前檢查
  3. POST_ATTEMPT / ON_INTERRUPT 時將計數器快照供 CheckpointPlugin 持久化
  4. PRE_RUN 時從 CheckpointPlugin 還原跨 Session 計數器

對應 Gap：
  - Gap-042：goto / inject_before / skip_to 計數器跨 TOKEN_HALT 持久化
  - Gap-048：per-step step_evolution_counter 跨 ESC+F12 持久化
  - Gap-049：max_goto_per_step 可配置（讀 PlaybookConfig）
"""
from __future__ import annotations

from typing import Any, Optional

from ..core.hookspec import CounterSnapshotResult, HookContext, KernelPhase
from ..models.counter_snapshot import CounterSnapshot  # noqa: F401 (re-exported)
from ..utils.config import PlaybookConfig


class GotoCounterPlugin:
    """跨 Session 計數器 Plugin（Gap-042 / Gap-048 / Gap-049）。"""

    PRIORITY = 85

    def __init__(self, playbook_cfg: Optional[PlaybookConfig] = None):
        self._cfg = playbook_cfg or PlaybookConfig()
        self._snapshot = CounterSnapshot()

    def name(self) -> str:
        return "goto_counter"

    def priority(self) -> int:
        return self.PRIORITY

    def subscribed_phases(self) -> list[KernelPhase]:
        return [
            KernelPhase.PRE_RUN,                     # 從 checkpoint 還原計數器（舊路徑）
            KernelPhase.POST_ATTEMPT,                # 觀察 mutation 是否被套用
            KernelPhase.ON_INTERRUPT,                # 中斷前快照供持久化
            KernelPhase.ON_TOKEN_USAGE,              # token halt 前快照供持久化
            # W4-T17 / M-11：解耦 CheckpointPlugin
            KernelPhase.ON_CHECKPOINT_RESTORE,       # 訂閱 checkpoint 還原事件
            KernelPhase.ON_CHECKPOINT_SAVE_REQUEST,  # 訂閱 checkpoint 取 snapshot 事件
        ]

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        if ctx.phase == KernelPhase.PRE_RUN:
            self._on_pre_run(ctx)
        elif ctx.phase == KernelPhase.POST_ATTEMPT:
            self._on_post_attempt(ctx)
        elif ctx.phase == KernelPhase.ON_CHECKPOINT_RESTORE:
            self._on_checkpoint_restore(ctx)
        elif ctx.phase == KernelPhase.ON_CHECKPOINT_SAVE_REQUEST:
            # SD_05 W1 Step-2：回傳 CounterSnapshotResult IHookResult（取代 M-4
            # anti-pattern 的 payload[mutable_container] 寫法）。同步保留 container
            # 寫入作 backward compat（W6 完整下沉後拔除）。
            return self._on_checkpoint_save_request(ctx)
        # ON_INTERRUPT / ON_TOKEN_USAGE：純觀察者
        return None

    # ──────────────────────────────────────────────
    # 公開 API（供 Kernel / EvolutionPlugin / CheckpointPlugin 查詢）
    # ──────────────────────────────────────────────
    def increment_goto(self, step_id: str) -> int:
        self._snapshot.goto_counter[step_id] = self._snapshot.goto_counter.get(step_id, 0) + 1
        return self._snapshot.goto_counter[step_id]

    def increment_inject_before(self, step_id: str) -> int:
        c = self._snapshot.inject_before_counter
        c[step_id] = c.get(step_id, 0) + 1
        return c[step_id]

    def increment_skip_to(self, step_id: str) -> int:
        c = self._snapshot.skip_to_counter
        c[step_id] = c.get(step_id, 0) + 1
        return c[step_id]

    def increment_step_evolution(self, step_id: str) -> int:
        c = self._snapshot.step_evolution_counter
        c[step_id] = c.get(step_id, 0) + 1
        return c[step_id]

    def is_goto_over_limit(self, step_id: str) -> bool:
        """Gap-049：依 max_goto_per_step 配置判斷是否超限。"""
        limit = self._cfg.max_goto_per_step
        return self._snapshot.goto_counter.get(step_id, 0) >= limit

    def is_step_evolution_over_limit(self, step_id: str) -> bool:
        """Gap-048：依 max_evolutions 配置判斷 per-step 演化次數是否超限。"""
        limit = self._cfg.max_evolutions
        return self._snapshot.step_evolution_counter.get(step_id, 0) >= limit

    def snapshot(self) -> CounterSnapshot:
        """供 CheckpointPlugin 取得當前快照進行持久化（deep copy 防併發）。"""
        return CounterSnapshot(
            goto_counter=dict(self._snapshot.goto_counter),
            inject_before_counter=dict(self._snapshot.inject_before_counter),
            skip_to_counter=dict(self._snapshot.skip_to_counter),
            step_evolution_counter=dict(self._snapshot.step_evolution_counter),
        )

    # ──────────────────────────────────────────────
    # SD_Improving_05 W1 Step-1：SSOT 橋接 API
    # ──────────────────────────────────────────────
    @property
    def goto_counter(self) -> dict[str, int]:
        """SD_05 W1 Step-1：暴露 goto_counter live reference 供 PlaybookRunner._run_steps 使用。

        提供 SSOT：local 變數 `_goto_counter` 將指向此 dict（同一物件），所有讀寫
        皆作用於 plugin 內部資料；CheckpointPlugin 透過 `snapshot()` 取 deep copy
        進行持久化，避免併發 race。

        W6 完整下沉至 EventBus phase 後將移除此 property（屆時不再需要 mixin 路徑）。
        """
        return self._snapshot.goto_counter

    @property
    def inject_before_counter(self) -> dict[str, int]:
        """SD_05 W1 Step-1：暴露 inject_before_counter live reference。"""
        return self._snapshot.inject_before_counter

    @property
    def skip_to_counter(self) -> dict[str, int]:
        """SD_05 W1 Step-1：暴露 skip_to_counter live reference。"""
        return self._snapshot.skip_to_counter

    @property
    def step_evolution_counter(self) -> dict[str, int]:
        """SD_05 W1 Step-1：暴露 step_evolution_counter live reference。"""
        return self._snapshot.step_evolution_counter

    def restore(self, snap: CounterSnapshot) -> None:
        """供 CheckpointPlugin 從持久化資料還原計數器。

        SD_05 W1 三方審查 Arch-M2：改為**就地 clear + update** 而非物件替換，
        確保 PlaybookRunner._run_steps 中已取得的 local alias（plugin.goto_counter
        等 property 回傳的 dict reference）在 restore 後仍指向正確資料。

        舊實作 `self._snapshot = CounterSnapshot(...)` 會把 _snapshot 換成新物件，
        導致先前取的 alias 指向廢棄 dict（靜默漂移）；改為就地操作後，dict 物件
        identity 不變，任何持有 alias 的位置自動看到新資料，杜絕「restore 後二次
        restore 致 alias 失效」的 W6 拔除前隱性 bug。
        """
        self._snapshot.goto_counter.clear()
        self._snapshot.goto_counter.update(snap.goto_counter)
        self._snapshot.inject_before_counter.clear()
        self._snapshot.inject_before_counter.update(snap.inject_before_counter)
        self._snapshot.skip_to_counter.clear()
        self._snapshot.skip_to_counter.update(snap.skip_to_counter)
        self._snapshot.step_evolution_counter.clear()
        self._snapshot.step_evolution_counter.update(snap.step_evolution_counter)

    # ──────────────────────────────────────────────
    # 內部 handler
    # ──────────────────────────────────────────────
    def _on_pre_run(self, ctx: HookContext) -> None:
        """PRE_RUN 時從 ctx.payload 取得 checkpoint 快照（若有）並還原。"""
        payload = ctx.payload or {}
        cp_snapshot = payload.get("counter_snapshot")
        if isinstance(cp_snapshot, CounterSnapshot):
            self.restore(cp_snapshot)
        elif isinstance(cp_snapshot, dict):
            self.restore(CounterSnapshot(
                goto_counter=dict(cp_snapshot.get("goto_counter", {})),
                inject_before_counter=dict(cp_snapshot.get("inject_before_counter", {})),
                skip_to_counter=dict(cp_snapshot.get("skip_to_counter", {})),
                step_evolution_counter=dict(cp_snapshot.get("step_evolution_counter", {})),
            ))

    def _on_checkpoint_restore(self, ctx: HookContext) -> None:
        """W4-T17 / M-11：訂閱 CheckpointPlugin 廣播的 RESTORE 事件，還原計數器。"""
        payload = ctx.payload or {}
        snap = payload.get("counter_snapshot")
        if isinstance(snap, CounterSnapshot):
            self.restore(snap)
        elif isinstance(snap, dict):
            self.restore(CounterSnapshot(
                goto_counter=dict(snap.get("goto_counter", {})),
                inject_before_counter=dict(snap.get("inject_before_counter", {})),
                skip_to_counter=dict(snap.get("skip_to_counter", {})),
                step_evolution_counter=dict(snap.get("step_evolution_counter", {})),
            ))

    def _on_checkpoint_save_request(self, ctx: HookContext) -> CounterSnapshotResult:
        """W4-T17 / M-11 + SD_05 W1 Step-2：訂閱 CheckpointPlugin 廣播的
        SAVE_REQUEST 事件，回傳 CounterSnapshotResult IHookResult。

        SD_06 W6（T6-8）：mutable container backward compat 路徑已物理拔除；
        所有呼叫端必須改從 MergedResult.counter_diff 讀取 SSOT 結果。
        """
        snap = self.snapshot()
        return CounterSnapshotResult(
            contributor=self.name(),
            snapshot={
                "goto_counter": dict(snap.goto_counter),
                "inject_before_counter": dict(snap.inject_before_counter),
                "skip_to_counter": dict(snap.skip_to_counter),
                "step_evolution_counter": dict(snap.step_evolution_counter),
            },
        )

    def _on_post_attempt(self, ctx: HookContext) -> None:
        """POST_ATTEMPT 觀察 payload.applied_mutation_kind 並遞增對應計數器。"""
        payload = ctx.payload or {}
        kind = payload.get("applied_mutation_kind")
        if not kind or ctx.task is None:
            return
        step_id = ctx.task.step_id
        if kind == "GOTO_STEP":
            self.increment_goto(step_id)
        elif kind == "INJECT_BEFORE":
            self.increment_inject_before(step_id)
        elif kind == "SKIP_TO":
            self.increment_skip_to(step_id)
        elif kind in ("REVISE_CURRENT", "INJECT_AFTER", "DELETE_STEP"):
            # 演化型突變 → step_evolution
            self.increment_step_evolution(step_id)
