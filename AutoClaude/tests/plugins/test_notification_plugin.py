"""NotificationPlugin 單元測試（Phase 3 / W5 #1，≥ 10 cases）。"""
from __future__ import annotations

from unittest.mock import patch

from autoclaude.core.hookspec import HookContext, KernelPhase
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import NotificationPlugin


def _pb() -> Playbook:
    return Playbook(version="1.0", project="P",
                    global_invariants=GlobalInvariants(), tasks=[])


def _task(step_id="T01") -> PlaybookTask:
    return PlaybookTask(step_id=step_id, name="n", prompt="p")


class TestNotificationPluginBasics:
    def test_name(self):
        assert NotificationPlugin().name() == "notification"

    def test_priority_is_50(self):
        assert NotificationPlugin().priority() == 50

    def test_subscribed_phases(self):
        phases = NotificationPlugin().subscribed_phases()
        assert KernelPhase.ON_ESCALATION in phases
        assert KernelPhase.ON_EVOLUTION in phases
        assert KernelPhase.POST_RUN in phases

    def test_returns_none_when_disabled(self):
        plugin = NotificationPlugin(enabled=False)
        ctx = HookContext(phase=KernelPhase.POST_RUN, playbook=_pb())
        assert plugin.on_event(ctx) is None


class TestNotificationPluginOnEscalation:
    @patch("autoclaude.plugins.notification_plugin.notify")
    def test_escalation_calls_notify(self, mock_notify):
        plugin = NotificationPlugin(enabled=True)
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(), task=_task(),
            payload={"title": "T", "message": "M"},
        )
        plugin.on_event(ctx)
        assert mock_notify.called

    @patch("autoclaude.plugins.notification_plugin.notify_escalation")
    def test_escalation_with_dump_path_uses_notify_escalation(self, mock_ne):
        from autoclaude.utils.config import AppConfig
        plugin = NotificationPlugin(enabled=True, app_config=AppConfig())
        ctx = HookContext(
            phase=KernelPhase.ON_ESCALATION, playbook=_pb(), task=_task(),
            payload={"dump_path": "/tmp/dump.md", "title": "T", "message": "M"},
        )
        plugin.on_event(ctx)
        assert mock_ne.called


class TestNotificationPluginOnEvolution:
    @patch("autoclaude.plugins.notification_plugin.notify")
    def test_evolution_calls_notify(self, mock_notify):
        plugin = NotificationPlugin(enabled=True)
        ctx = HookContext(
            phase=KernelPhase.ON_EVOLUTION, playbook=_pb(),
            payload={"evolution_count": 2, "evolved_playbook_path": "/x.yaml"},
        )
        plugin.on_event(ctx)
        assert mock_notify.called
        title = mock_notify.call_args.args[0]
        assert "演化" in title or "第 2 次" in title


class TestNotificationPluginOnPostRun:
    @patch("autoclaude.plugins.notification_plugin.notify")
    def test_post_run_success_title(self, mock_notify):
        plugin = NotificationPlugin(enabled=True)
        ctx = HookContext(
            phase=KernelPhase.POST_RUN, playbook=_pb(),
            payload={"success": True},
        )
        plugin.on_event(ctx)
        title = mock_notify.call_args.args[0]
        assert "完成" in title

    @patch("autoclaude.plugins.notification_plugin.notify")
    def test_post_run_failure_title(self, mock_notify):
        plugin = NotificationPlugin(enabled=True)
        ctx = HookContext(
            phase=KernelPhase.POST_RUN, playbook=_pb(),
            payload={"success": False},
        )
        plugin.on_event(ctx)
        title = mock_notify.call_args.args[0]
        assert "失敗" in title

    @patch("autoclaude.plugins.notification_plugin.notify")
    def test_post_run_no_payload_uses_defaults(self, mock_notify):
        plugin = NotificationPlugin(enabled=True)
        ctx = HookContext(phase=KernelPhase.POST_RUN, playbook=_pb())
        plugin.on_event(ctx)
        assert mock_notify.called


class TestNotificationPluginObserverContract:
    def test_returns_none_for_observer_phases(self):
        """純觀察者 phase（ON_ESCALATION/ON_EVOLUTION/POST_RUN）不回傳 IHookResult。"""
        from autoclaude.core.hookspec import ScheduleResumeResult
        plugin = NotificationPlugin(enabled=True)
        observer_phases = [
            KernelPhase.ON_ESCALATION,
            KernelPhase.ON_EVOLUTION,
            KernelPhase.POST_RUN,
        ]
        for phase in observer_phases:
            with patch("autoclaude.plugins.notification_plugin.notify"):
                ctx = HookContext(phase=phase, playbook=_pb())
                assert plugin.on_event(ctx) is None

    def test_returns_schedule_resume_result_for_auto_resume_wake(self):
        """W5 / M-9 / SA-M3：ON_AUTO_RESUME_WAKE 回傳 ScheduleResumeResult 符合 PHASE_RESULT_CONTRACT。"""
        from autoclaude.core.hookspec import ScheduleResumeResult
        plugin = NotificationPlugin(enabled=True)
        with patch("autoclaude.plugins.notification_plugin.notify"):
            ctx = HookContext(
                phase=KernelPhase.ON_AUTO_RESUME_WAKE, playbook=_pb(),
                payload={"kind": "halt", "scheduled_at": "2026-01-01",
                         "wait_seconds": 30.0},
            )
            result = plugin.on_event(ctx)
            assert isinstance(result, ScheduleResumeResult)
            assert result.contributor == "notification"
            assert result.scheduled_at == "2026-01-01"

    def test_auto_resume_wake_disabled_returns_none(self):
        plugin = NotificationPlugin(enabled=False)
        ctx = HookContext(
            phase=KernelPhase.ON_AUTO_RESUME_WAKE, playbook=_pb(),
            payload={"kind": "halt"},
        )
        assert plugin.on_event(ctx) is None
