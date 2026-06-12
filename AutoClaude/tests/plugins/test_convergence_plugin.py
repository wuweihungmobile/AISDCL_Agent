"""ConvergencePlugin 單元測試（Phase 3 / W9 #10，≥ 12 cases）。"""
from __future__ import annotations

from unittest.mock import MagicMock

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase, ResourceRequest
from autoclaude.execution.convergence_monitor import ConvergenceReport
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import ConvergencePlugin


def _pb() -> Playbook:
    return Playbook(version="1.0", project="P",
                    global_invariants=GlobalInvariants(), tasks=[])


def _task() -> PlaybookTask:
    return PlaybookTask(step_id="T01", name="n", prompt="p")


class TestConvergencePluginBasics:
    def test_name(self):
        assert ConvergencePlugin().name() == "convergence"

    def test_priority_is_65(self):
        assert ConvergencePlugin().priority() == 65

    def test_subscribed_phases(self):
        phases = ConvergencePlugin().subscribed_phases()
        assert KernelPhase.POST_ATTEMPT in phases
        assert len(phases) == 1


class TestConvergencePluginRecommendationMode:
    """Mode A：payload 直接帶 convergence_recommendation。"""

    def test_continue_returns_none(self):
        plugin = ConvergencePlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"convergence_recommendation": "continue"},
        )
        assert plugin.on_event(ctx) is None

    def test_change_strategy_returns_none(self):
        plugin = ConvergencePlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"convergence_recommendation": "change_strategy"},
        )
        assert plugin.on_event(ctx) is None

    def test_escalate_returns_resource_request(self):
        plugin = ConvergencePlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={
                "convergence_recommendation": "escalate",
                "convergence_reasoning": "stuck on regex",
            },
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, ResourceRequest)
        assert result.request_escalation is True
        assert "stuck on regex" in result.reason

    def test_escalate_with_no_reasoning_uses_default(self):
        plugin = ConvergencePlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"convergence_recommendation": "escalate"},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, ResourceRequest)
        assert "ConvergenceMonitor" in result.reason


class TestConvergencePluginTrackerMode:
    """Mode B：payload 帶 failure_tracker，由 Plugin 執行 evaluate。"""

    def test_tracker_evaluate_escalate(self):
        monitor = MagicMock()
        monitor.evaluate.return_value = ConvergenceReport(
            score=0.0, trend="diverging", recommendation="escalate",
            reasoning="diverging trend",
        )
        plugin = ConvergencePlugin(monitor=monitor)
        tracker = MagicMock()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"failure_tracker": tracker},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, ResourceRequest)
        assert result.request_escalation is True
        assert "diverging trend" in result.reason
        monitor.evaluate.assert_called_once_with(tracker)

    def test_tracker_evaluate_continue(self):
        monitor = MagicMock()
        monitor.evaluate.return_value = ConvergenceReport(
            score=0.6, trend="improving", recommendation="continue",
        )
        plugin = ConvergencePlugin(monitor=monitor)
        tracker = MagicMock()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"failure_tracker": tracker},
        )
        assert plugin.on_event(ctx) is None


class TestConvergencePluginNoPayload:
    def test_empty_payload_returns_none(self):
        plugin = ConvergencePlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
        )
        assert plugin.on_event(ctx) is None


class TestConvergencePluginPublicEvaluate:
    def test_evaluate_delegates_to_monitor(self):
        monitor = MagicMock()
        report = ConvergenceReport(score=0.5, trend="stuck", recommendation="continue")
        monitor.evaluate.return_value = report
        plugin = ConvergencePlugin(monitor=monitor)
        tracker = MagicMock()
        result = plugin.evaluate(tracker)
        assert result is report
        monitor.evaluate.assert_called_once_with(tracker)


class TestConvergencePluginEventBusIntegration:
    def test_via_bus_escalate(self):
        bus = EventBus()
        bus.register(ConvergencePlugin())
        merged = bus.emit(HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={
                "convergence_recommendation": "escalate",
                "convergence_reasoning": "stuck",
            },
        ))
        assert merged.request_escalation is True

    def test_via_bus_continue_no_escalation(self):
        bus = EventBus()
        bus.register(ConvergencePlugin())
        merged = bus.emit(HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"convergence_recommendation": "continue"},
        ))
        assert merged.request_escalation is False
