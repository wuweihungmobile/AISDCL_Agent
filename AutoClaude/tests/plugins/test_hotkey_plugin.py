"""HotkeyPlugin 單元測試（Phase 3 / W5 #2，≥ 10 cases）。"""
from __future__ import annotations

from unittest.mock import MagicMock

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase, VetoResult
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import HotkeyPlugin


def _pb() -> Playbook:
    return Playbook(version="1.0", project="P",
                    global_invariants=GlobalInvariants(), tasks=[])


def _task() -> PlaybookTask:
    return PlaybookTask(step_id="T01", name="n", prompt="p")


class TestHotkeyPluginBasics:
    def test_name(self):
        hk = MagicMock(); hk.triggered = False
        assert HotkeyPlugin(hk).name() == "hotkey"

    def test_priority_is_10(self):
        hk = MagicMock(); hk.triggered = False
        assert HotkeyPlugin(hk).priority() == 10

    def test_subscribed_phases(self):
        hk = MagicMock(); hk.triggered = False
        phases = HotkeyPlugin(hk).subscribed_phases()
        assert KernelPhase.PRE_STEP in phases
        assert KernelPhase.PRE_ATTEMPT in phases
        assert len(phases) == 2


class TestHotkeyPluginNotTriggered:
    def test_returns_none_when_not_triggered(self):
        hk = MagicMock(); hk.triggered = False
        plugin = HotkeyPlugin(hk)
        ctx = HookContext(phase=KernelPhase.PRE_STEP, playbook=_pb(), task=_task())
        assert plugin.on_event(ctx) is None

    def test_returns_none_on_pre_attempt_when_not_triggered(self):
        hk = MagicMock(); hk.triggered = False
        plugin = HotkeyPlugin(hk)
        ctx = HookContext(phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(),
                          task=_task(), attempt=0)
        assert plugin.on_event(ctx) is None


class TestHotkeyPluginTriggered:
    def test_returns_veto_when_triggered_pre_step(self):
        hk = MagicMock(); hk.triggered = True
        plugin = HotkeyPlugin(hk)
        ctx = HookContext(phase=KernelPhase.PRE_STEP, playbook=_pb(), task=_task())
        result = plugin.on_event(ctx)
        assert isinstance(result, VetoResult)
        assert result.contributor == "hotkey"
        assert "ESC+F12" in result.reason

    def test_returns_veto_when_triggered_pre_attempt(self):
        hk = MagicMock(); hk.triggered = True
        plugin = HotkeyPlugin(hk)
        ctx = HookContext(phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(),
                          task=_task(), attempt=2)
        result = plugin.on_event(ctx)
        assert isinstance(result, VetoResult)
        assert "T01" in result.reason

    def test_veto_reason_includes_step_id(self):
        hk = MagicMock(); hk.triggered = True
        plugin = HotkeyPlugin(hk)
        task = PlaybookTask(step_id="T_CUSTOM", name="n", prompt="p")
        ctx = HookContext(phase=KernelPhase.PRE_STEP, playbook=_pb(), task=task)
        result = plugin.on_event(ctx)
        assert "T_CUSTOM" in result.reason


class TestHotkeyPluginEventBusIntegration:
    def test_via_event_bus_pre_step_vetos(self):
        hk = MagicMock(); hk.triggered = True
        bus = EventBus()
        bus.register(HotkeyPlugin(hk))
        merged = bus.emit(HookContext(
            phase=KernelPhase.PRE_STEP, playbook=_pb(), task=_task(),
        ))
        assert merged.veto is True
        assert any("hotkey" in r for r in merged.veto_reasons)

    def test_via_event_bus_pre_attempt_vetos(self):
        hk = MagicMock(); hk.triggered = True
        bus = EventBus()
        bus.register(HotkeyPlugin(hk))
        merged = bus.emit(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(), task=_task(), attempt=0,
        ))
        assert merged.veto is True


class TestHotkeyPluginContextWithoutTask:
    def test_no_task_still_returns_veto(self):
        hk = MagicMock(); hk.triggered = True
        plugin = HotkeyPlugin(hk)
        ctx = HookContext(phase=KernelPhase.PRE_STEP, playbook=_pb(), task=None)
        result = plugin.on_event(ctx)
        assert isinstance(result, VetoResult)
        assert "N/A" in result.reason
