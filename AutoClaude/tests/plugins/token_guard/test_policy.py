"""policy.py / TokenGuardPlugin 組合層單元測試（SD_07 W3-T3-10）。

對應子模組：autoclaude/plugins/token_guard/policy.py
測試重點：組合層委派 + on_event ResourceRequest 構造 + 公開 API 等價性

目標：≥ 5 case
"""
from __future__ import annotations

from autoclaude.core.hookspec import (
    HookContext,
    KernelPhase,
    ResourceRequest,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins.token_guard import TokenGuardPlugin
from autoclaude.plugins.token_guard.compactor import CompactFailureState
from autoclaude.utils.config import TokenGuardConfig


def _pb() -> Playbook:
    return Playbook(
        version="1.0", project="P",
        global_invariants=GlobalInvariants(), tasks=[],
    )


def _task() -> PlaybookTask:
    return PlaybookTask(step_id="T01", name="n", prompt="p")


class TestPluginIdentity:
    def test_name_priority_phases(self):
        p = TokenGuardPlugin()
        assert p.name() == "token_guard"
        assert p.priority() == 30
        phases = p.subscribed_phases()
        assert KernelPhase.POST_ATTEMPT in phases
        assert KernelPhase.ON_TOKEN_USAGE in phases


class TestOnEventResourceRequest:
    def test_halt_yields_resource_request_halt(self):
        p = TokenGuardPlugin(TokenGuardConfig(halt_threshold_pct=90.0))
        ctx = HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            payload={"token_pct": 95.0, "max_retries": 3},
        )
        rr = p.on_event(ctx)
        assert isinstance(rr, ResourceRequest)
        assert rr.request_halt is True
        assert "halt_threshold" in rr.reason

    def test_compact_yields_resource_request_compact(self):
        p = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 85.0, "max_retries": 3},
        )
        rr = p.on_event(ctx)
        assert isinstance(rr, ResourceRequest)
        assert rr.request_compact is True

    def test_below_thresholds_returns_none(self):
        p = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 50.0, "max_retries": 3},
        )
        assert p.on_event(ctx) is None

    def test_disabled_plugin_returns_none(self):
        p = TokenGuardPlugin(TokenGuardConfig(enabled=False))
        ctx = HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            payload={"token_pct": 95.0},
        )
        assert p.on_event(ctx) is None

    def test_unsubscribed_phase_returns_none(self):
        """非 POST_ATTEMPT / ON_TOKEN_USAGE phase 返回 None（保險）。"""
        p = TokenGuardPlugin()
        ctx = HookContext(
            phase=KernelPhase.PRE_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 95.0},
        )
        assert p.on_event(ctx) is None


class TestPublicApiDelegation:
    """公開 API 與原 token_guard_plugin.py 等價（SSOT 委派）。"""

    def test_get_dynamic_compact_threshold_delegates(self):
        p = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # 對齊 thresholds.get_dynamic_compact_threshold
        assert p.get_dynamic_compact_threshold(0, 3) == 80.0
        assert p.get_dynamic_compact_threshold(3, 3) == 65.0

    def test_should_compact_with_dynamic_threshold(self):
        p = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # attempt=0 → threshold=80
        assert p.should_compact(token_pct=82.0, attempt=0, max_retries=3) is True
        # attempt=3 → threshold=65
        assert p.should_compact(token_pct=66.0, attempt=3, max_retries=3) is True

    def test_record_and_reset_compact_failure(self):
        p = TokenGuardPlugin()
        assert p.compact_failure_count == 0
        p.record_compact_failure()
        p.record_compact_failure()
        assert p.compact_failure_count == 2
        assert p.is_compact_failure_critical() is True
        p.reset_compact_failure()
        assert p.compact_failure_count == 0
        assert p.is_compact_failure_critical() is False

    def test_backward_compat_setter_for_underscore_count(self):
        """SD_05 W2 SD-M1：_compact_failure_count setter backward compat。"""
        p = TokenGuardPlugin()
        p._compact_failure_count = 5
        assert p.compact_failure_count == 5
        assert p._compact_failure_count == 5

    def test_observe_token_line_delegates(self):
        p = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        peak, c, h = p.observe_token_line(
            pct=85.0, peak_pct=50.0,
            triggered_compact=False, triggered_halt=False,
        )
        assert peak == 85.0
        assert c is True
        assert h is False

    def test_build_compact_prompt_delegates(self):
        p = TokenGuardPlugin()
        task = PlaybookTask(step_id="T01", name="n", prompt="p")
        prompt = p.build_compact_prompt(task=task, attempt=0)
        assert "/compact" in prompt
        assert "[ACTIVE_TASK] T01" in prompt

    def test_process_compact_result_delegates(self):
        p = TokenGuardPlugin()
        assert p.process_compact_result(triggered_compact=True, peak_token_pct=85.0) is True
        assert p.compact_failure_count == 1

    def test_verify_correction_applied_attempt_zero(self):
        p = TokenGuardPlugin()
        assert p.verify_correction_applied(0) is None

    def test_resolve_per_step_cfg_returns_global_when_no_task(self):
        p = TokenGuardPlugin()
        cfg = p.resolve_per_step_cfg(None)
        assert isinstance(cfg, TokenGuardConfig)


class TestCompactFailureStateIntegration:
    """確認 plugin 與 CompactFailureState SSOT 一致。"""

    def test_internal_state_uses_dataclass(self):
        p = TokenGuardPlugin()
        assert isinstance(p._compact_state, CompactFailureState)
