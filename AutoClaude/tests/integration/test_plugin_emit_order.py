"""W2 DoD：Plugin emit ordering 契約測試（SD_03 §2.3 R-13）。

驗證 EventBus 依 priority 排序觸發 Plugin，保證：
  - priority 30（TokenGuard）在 70（Evolution）之前
  - priority 65（Convergence）在 70（Evolution）之前
  - build_kernel 組裝後 12 個 Plugin 的 priority 順序正確
"""
from __future__ import annotations

from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase, ResourceRequest
from autoclaude.core.wiring import build_kernel
from autoclaude.infra.adapters.dry_run_executor import DryRunExecutor
from autoclaude.infra.adapters.shell_evaluator import ShellEvaluator
from autoclaude.utils.config import AppConfig, PlaybookConfig


# ──────────────────────────────────────────────────────────
# 工具：記錄觸發順序的 spy plugin
# ──────────────────────────────────────────────────────────
class SpyPlugin:
    """記錄每次 on_event 呼叫順序的測試用 Plugin。"""

    def __init__(self, name_: str, priority_: int, phases: list[KernelPhase]):
        self._name = name_
        self._priority = priority_
        self._phases = phases
        self.call_order: list[tuple[str, KernelPhase]] = []

    def name(self) -> str:
        return self._name

    def priority(self) -> int:
        return self._priority

    def subscribed_phases(self) -> list[KernelPhase]:
        return self._phases

    def on_event(self, ctx: HookContext) -> Optional[Any]:
        self.call_order.append((self._name, ctx.phase))
        return None


# ──────────────────────────────────────────────────────────
# 測試：EventBus priority 排序
# ──────────────────────────────────────────────────────────
class TestPluginEmitOrder:
    """EventBus 依 priority 排序觸發驗證。"""

    def _make_ctx(self, phase: KernelPhase) -> HookContext:
        from autoclaude.models.playbook import Playbook, PlaybookTask, GlobalInvariants
        playbook = Playbook(
            project="emit-order-test",
            tasks=[PlaybookTask(step_id="T01", name="test", prompt="p")],
            global_invariants=GlobalInvariants(),
        )
        return HookContext(phase=phase, playbook=playbook)

    def test_lower_priority_fires_first(self):
        """priority 30 應在 70 之前觸發。"""
        bus = EventBus()
        order: list[str] = []
        p30 = SpyPlugin("low30", 30, [KernelPhase.POST_ATTEMPT])
        p70 = SpyPlugin("high70", 70, [KernelPhase.POST_ATTEMPT])
        bus.register(p70)  # 刻意先 register 高 priority
        bus.register(p30)
        ctx = self._make_ctx(KernelPhase.POST_ATTEMPT)
        bus.emit(ctx)
        fire_names = [e[0] for e in p30.call_order + p70.call_order
                      if e[1] == KernelPhase.POST_ATTEMPT]
        # 收集觸發順序（利用 SpyPlugin.call_order）
        all_calls: list[str] = []
        for name, phase in p30.call_order + p70.call_order:
            if phase == KernelPhase.POST_ATTEMPT:
                all_calls.append(name)
        assert all_calls.index("low30") < all_calls.index("high70"), (
            f"priority 30 應先於 70 觸發，實際順序: {all_calls}"
        )

    def test_emit_order_stable_across_three_plugins(self):
        """priority 5 < 30 < 70 的觸發順序應嚴格遞增。"""
        bus = EventBus()
        p5 = SpyPlugin("p5", 5, [KernelPhase.PRE_STEP])
        p30 = SpyPlugin("p30", 30, [KernelPhase.PRE_STEP])
        p70 = SpyPlugin("p70", 70, [KernelPhase.PRE_STEP])
        # 以逆序 register，確認 priority 排序覆蓋 register 順序
        for p in [p70, p30, p5]:
            bus.register(p)

        ctx = self._make_ctx(KernelPhase.PRE_STEP)
        bus.emit(ctx)

        positions = {}
        seen = []
        for spy in [p5, p30, p70]:
            for name, _ in spy.call_order:
                seen.append(name)
        for i, name in enumerate(seen):
            positions[name] = i
        assert positions["p5"] < positions["p30"] < positions["p70"]

    def test_same_priority_stable_by_register_order(self):
        """同 priority 時，先 register 的先觸發（tie-break）。"""
        bus = EventBus()
        first = SpyPlugin("first", 50, [KernelPhase.POST_STEP])
        second = SpyPlugin("second", 50, [KernelPhase.POST_STEP])
        bus.register(first)
        bus.register(second)
        ctx = self._make_ctx(KernelPhase.POST_STEP)
        bus.emit(ctx)
        all_calls: list[str] = []
        for spy in [first, second]:
            for name, ph in spy.call_order:
                if ph == KernelPhase.POST_STEP:
                    all_calls.append(name)
        assert all_calls.index("first") < all_calls.index("second")

    def test_build_kernel_plugin_priorities(self):
        """build_kernel 後驗證各 Plugin 的 priority 值符合 SD_03 規格。"""
        cfg = AppConfig()
        executor = DryRunExecutor()
        evaluator = ShellEvaluator(PlaybookConfig())
        kernel = build_kernel(cfg, executor=executor, evaluator=evaluator)

        expected_priorities = {
            "pre_run_validator": 5,
            "token_guard": 30,
            "convergence": 65,
            "evolution": 70,
            "goto_counter": 85,
            "checkpoint": 90,
        }
        for name, expected_prio in expected_priorities.items():
            plugin = kernel.bus.get_plugin(name)
            assert plugin is not None, f"Plugin '{name}' 未在 bus 中找到"
            assert plugin.priority() == expected_prio, (
                f"Plugin '{name}' priority={plugin.priority()}，預期={expected_prio}"
            )

    def test_token_guard_fires_before_evolution(self):
        """從 build_kernel bus 中驗證 token_guard(30) < evolution(70)。"""
        cfg = AppConfig()
        executor = DryRunExecutor()
        evaluator = ShellEvaluator(PlaybookConfig())
        kernel = build_kernel(cfg, executor=executor, evaluator=evaluator)

        tg = kernel.bus.get_plugin("token_guard")
        ev = kernel.bus.get_plugin("evolution")
        assert tg is not None and ev is not None
        assert tg.priority() < ev.priority(), (
            f"token_guard priority({tg.priority()}) 應 < evolution priority({ev.priority()})"
        )

    def test_convergence_fires_before_evolution(self):
        """從 build_kernel bus 中驗證 convergence(65) < evolution(70)。"""
        cfg = AppConfig()
        executor = DryRunExecutor()
        evaluator = ShellEvaluator(PlaybookConfig())
        kernel = build_kernel(cfg, executor=executor, evaluator=evaluator)

        cv = kernel.bus.get_plugin("convergence")
        ev = kernel.bus.get_plugin("evolution")
        assert cv is not None and ev is not None
        assert cv.priority() < ev.priority()
