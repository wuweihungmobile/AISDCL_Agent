"""CrossStepValidatorPlugin 單元測試（Phase 3 / W6 #4，≥ 10 cases）。"""
from __future__ import annotations

from unittest.mock import MagicMock

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase, PromptInjectionResult
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import CrossStepValidatorPlugin


def _pb(*tasks) -> Playbook:
    return Playbook(version="1.0", project="P",
                    global_invariants=GlobalInvariants(), tasks=list(tasks))


def _t(step_id: str) -> PlaybookTask:
    return PlaybookTask(step_id=step_id, name=step_id, prompt="p")


class TestCrossStepValidatorPluginBasics:
    def test_name(self):
        assert CrossStepValidatorPlugin().name() == "cross_step_validator"

    def test_priority_is_15(self):
        assert CrossStepValidatorPlugin().priority() == 15

    def test_subscribed_phases(self):
        phases = CrossStepValidatorPlugin().subscribed_phases()
        assert KernelPhase.PRE_STEP in phases
        assert KernelPhase.PRE_ATTEMPT in phases


class TestCrossStepValidatorPluginPreStep:
    def test_pre_step_caches_warning(self):
        v = MagicMock()
        v.validate_before_step.return_value = "⚠️ 5 modified files"
        plugin = CrossStepValidatorPlugin(validator=v)
        ctx = HookContext(
            phase=KernelPhase.PRE_STEP,
            playbook=_pb(_t("T01"), _t("T02")),
            task=_t("T02"), step_idx=1,
        )
        result = plugin.on_event(ctx)
        assert result is None  # PRE_STEP 不回傳
        assert plugin._cached_warning == "⚠️ 5 modified files"

    def test_pre_step_no_pollution_no_cache(self):
        v = MagicMock()
        v.validate_before_step.return_value = None
        plugin = CrossStepValidatorPlugin(validator=v)
        ctx = HookContext(
            phase=KernelPhase.PRE_STEP,
            playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0,
        )
        plugin.on_event(ctx)
        assert plugin._cached_warning is None

    def test_pre_step_passes_prev_step_correctly(self):
        v = MagicMock()
        v.validate_before_step.return_value = None
        plugin = CrossStepValidatorPlugin(validator=v)
        pb = _pb(_t("T01"), _t("T02"))
        ctx = HookContext(
            phase=KernelPhase.PRE_STEP, playbook=pb, task=pb.tasks[1], step_idx=1,
        )
        plugin.on_event(ctx)
        kwargs = v.validate_before_step.call_args.kwargs
        assert kwargs["prev_step"].step_id == "T01"
        assert kwargs["current_step"].step_id == "T02"

    def test_pre_step_first_step_prev_is_none(self):
        v = MagicMock()
        v.validate_before_step.return_value = None
        plugin = CrossStepValidatorPlugin(validator=v)
        pb = _pb(_t("T01"))
        ctx = HookContext(
            phase=KernelPhase.PRE_STEP, playbook=pb, task=pb.tasks[0], step_idx=0,
        )
        plugin.on_event(ctx)
        assert v.validate_before_step.call_args.kwargs["prev_step"] is None


class TestCrossStepValidatorPluginPreAttempt:
    def test_pre_attempt_injects_cached_warning(self):
        v = MagicMock()
        v.validate_before_step.return_value = "⚠️ pollution"
        plugin = CrossStepValidatorPlugin(validator=v)
        # 先觸發 PRE_STEP 快取
        plugin.on_event(HookContext(
            phase=KernelPhase.PRE_STEP, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0,
        ))
        # 再觸發 PRE_ATTEMPT
        result = plugin.on_event(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0, attempt=0,
        ))
        assert isinstance(result, PromptInjectionResult)
        assert "pollution" in result.prefix

    def test_pre_attempt_no_warning_returns_none(self):
        v = MagicMock()
        v.validate_before_step.return_value = None
        plugin = CrossStepValidatorPlugin(validator=v)
        plugin.on_event(HookContext(
            phase=KernelPhase.PRE_STEP, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0,
        ))
        result = plugin.on_event(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0, attempt=0,
        ))
        assert result is None

    def test_pre_attempt_attempt_gt_zero_no_inject(self):
        v = MagicMock()
        v.validate_before_step.return_value = "⚠️ x"
        plugin = CrossStepValidatorPlugin(validator=v)
        plugin.on_event(HookContext(
            phase=KernelPhase.PRE_STEP, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0,
        ))
        result = plugin.on_event(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0, attempt=1,  # 重試 → 不再注入
        ))
        assert result is None

    def test_cache_cleared_after_inject(self):
        v = MagicMock()
        v.validate_before_step.return_value = "⚠️ once"
        plugin = CrossStepValidatorPlugin(validator=v)
        plugin.on_event(HookContext(
            phase=KernelPhase.PRE_STEP, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0,
        ))
        plugin.on_event(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0, attempt=0,
        ))
        # 第二次注入應為 None（cache 已 cleared）
        result = plugin.on_event(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0, attempt=0,
        ))
        assert result is None


class TestCrossStepValidatorPluginEventBusIntegration:
    def test_pre_attempt_via_bus_accumulates_prefix(self):
        v = MagicMock()
        v.validate_before_step.return_value = "⚠️ git dirty"
        bus = EventBus()
        bus.register(CrossStepValidatorPlugin(validator=v))
        # PRE_STEP 觸發 cache
        bus.emit(HookContext(
            phase=KernelPhase.PRE_STEP, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0,
        ))
        # PRE_ATTEMPT 取得 prefix
        merged = bus.emit(HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(_t("T01")),
            task=_t("T01"), step_idx=0, attempt=0,
        ))
        assert "git dirty" in merged.accumulated_prefix
