"""PreRunValidatorPlugin 單元測試（Phase 3 / W5 #3，≥ 10 cases）。"""
from __future__ import annotations

from unittest.mock import MagicMock

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase, VetoResult
from autoclaude.execution.pre_run_validator import PreRunIssue
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import PreRunValidatorPlugin


def _pb() -> Playbook:
    return Playbook(version="1.0", project="P",
                    global_invariants=GlobalInvariants(), tasks=[])


def _task(evaluator_command=None) -> PlaybookTask:
    return PlaybookTask(step_id="T01", name="n", prompt="p",
                        evaluator_command=evaluator_command)


class TestPreRunValidatorPluginBasics:
    def test_name(self):
        assert PreRunValidatorPlugin().name() == "pre_run_validator"

    def test_priority_is_5(self):
        assert PreRunValidatorPlugin().priority() == 5

    def test_subscribed_phases(self):
        phases = PreRunValidatorPlugin().subscribed_phases()
        assert KernelPhase.PRE_RUN in phases
        assert KernelPhase.PRE_ATTEMPT in phases


class TestPreRunValidatorPluginPreRunNoOp:
    def test_pre_run_returns_none_currently(self):
        plugin = PreRunValidatorPlugin()
        ctx = HookContext(phase=KernelPhase.PRE_RUN, playbook=_pb())
        assert plugin.on_event(ctx) is None


class TestPreRunValidatorPluginPreAttempt:
    def test_returns_none_when_no_task(self):
        plugin = PreRunValidatorPlugin()
        ctx = HookContext(phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(),
                          task=None, attempt=0)
        assert plugin.on_event(ctx) is None

    def test_returns_none_on_retry(self):
        # attempt > 0 → 不再驗證（首次已驗）
        validator = MagicMock()
        plugin = PreRunValidatorPlugin(validator=validator)
        ctx = HookContext(phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(),
                          task=_task("nonexistent_cmd"), attempt=1)
        assert plugin.on_event(ctx) is None
        validator.validate_step.assert_not_called()

    def test_returns_none_when_no_issues(self):
        validator = MagicMock()
        validator.validate_step.return_value = []
        plugin = PreRunValidatorPlugin(validator=validator)
        ctx = HookContext(phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(),
                          task=_task("echo ok"), attempt=0)
        assert plugin.on_event(ctx) is None

    def test_returns_none_when_only_warn_issues(self):
        validator = MagicMock()
        validator.validate_step.return_value = [
            PreRunIssue(severity="warn", category="X", message="m", strategy_hint="h"),
        ]
        plugin = PreRunValidatorPlugin(validator=validator)
        ctx = HookContext(phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(),
                          task=_task("echo ok"), attempt=0)
        assert plugin.on_event(ctx) is None

    def test_returns_veto_when_block_issue_present(self):
        validator = MagicMock()
        validator.validate_step.return_value = [
            PreRunIssue(
                severity="block", category="evaluator_missing",
                message="cmd not found",
                strategy_hint="install it",
            ),
        ]
        plugin = PreRunValidatorPlugin(validator=validator)
        ctx = HookContext(phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(),
                          task=_task("missing_cmd"), attempt=0)
        result = plugin.on_event(ctx)
        assert isinstance(result, VetoResult)
        assert result.contributor == "pre_run_validator"
        assert "evaluator_missing" in result.reason
        assert "cmd not found" in result.reason
        assert "install it" in result.reason


class TestPreRunValidatorPluginEventBusIntegration:
    def test_block_issue_through_event_bus(self):
        validator = MagicMock()
        validator.validate_step.return_value = [
            PreRunIssue(severity="block", category="evaluator_missing",
                        message="m", strategy_hint=""),
        ]
        bus = EventBus()
        bus.register(PreRunValidatorPlugin(validator=validator))
        merged = bus.emit(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(),
            task=_task("missing"), attempt=0,
        ))
        assert merged.veto is True

    def test_no_issues_through_event_bus(self):
        validator = MagicMock()
        validator.validate_step.return_value = []
        bus = EventBus()
        bus.register(PreRunValidatorPlugin(validator=validator))
        merged = bus.emit(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(),
            task=_task("echo ok"), attempt=0,
        ))
        assert merged.veto is False


class TestPreRunValidatorPluginDefaultValidator:
    def test_default_validator_used_when_none_passed(self):
        plugin = PreRunValidatorPlugin()
        from autoclaude.execution.pre_run_validator import PreRunValidator
        assert isinstance(plugin._validator, PreRunValidator)

    def test_real_validator_block_on_missing_command(self):
        # 整合測試：使用真實 validator，傳入肯定不存在的命令
        plugin = PreRunValidatorPlugin()
        ctx = HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(),
            task=_task("zzz_definitely_not_a_real_cmd_xyzqv"),
            attempt=0,
        )
        result = plugin.on_event(ctx)
        # 應該 block（command 不在 PATH）
        assert isinstance(result, VetoResult)
