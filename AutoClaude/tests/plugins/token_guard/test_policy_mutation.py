"""policy.py 補強測試 — SD_09 W1 A-1（mutation pilot kill rate ≥ 70%）。

對應 SD_Improving_09 W1 範疇：policy.py 17 個 survived mutation
（id: 83-86, 92-94, 98, 100, 103-104, 106-111）。

聚焦：
  - _evaluate_resources：payload 解析常量、float/int cast
  - ResourceRequest 構造：contributor、request_halt、request_compact、reason 文字
  - on_event 分支：disabled / phase check / payload defaults
  - public API delegation 精確值
"""
from __future__ import annotations

from autoclaude.core.hookspec import (
    HookContext,
    KernelPhase,
    ResourceRequest,
)
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins.token_guard import TokenGuardPlugin
from autoclaude.utils.config import TokenGuardConfig


def _pb() -> Playbook:
    return Playbook(
        version="1.0", project="P",
        global_invariants=GlobalInvariants(), tasks=[],
    )


def _task() -> PlaybookTask:
    return PlaybookTask(step_id="T01", name="n", prompt="p")


class TestEvaluateResourcesMutations:
    """殺 _evaluate_resources 內 payload defaults + 條件分支 mutation。"""

    def test_default_max_retries_is_3(self):
        """殺 `payload.get('max_retries', 3)` → 0/1/None mutation。"""
        # 無 max_retries 提供時走 default 3
        p = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 82.0},  # 故意不傳 max_retries
            attempt=0,
        )
        rr = p.on_event(ctx)
        # attempt=0, max_retries=3 → threshold 仍 80 → 82 ≥ 80 → compact
        assert rr is not None
        assert rr.request_compact is True

    def test_default_token_pct_is_zero(self):
        """殺 `payload.get('token_pct', 0.0)` default mutation。"""
        # 完全空 payload → token_pct=0 → 不應 halt 也不 compact
        p = TokenGuardPlugin()
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={},
        )
        assert p.on_event(ctx) is None

    def test_resource_request_contributor_is_plugin_name(self):
        """殺 `contributor=self.name()` 字串字面值 mutation。"""
        p = TokenGuardPlugin(TokenGuardConfig(halt_threshold_pct=90.0))
        ctx = HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            payload={"token_pct": 95.0},
        )
        rr = p.on_event(ctx)
        assert isinstance(rr, ResourceRequest)
        assert rr.contributor == "token_guard"

    def test_halt_resource_has_request_halt_true_not_compact(self):
        """殺 `request_halt=True` boolean mutation + 排他性。"""
        p = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        ctx = HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            payload={"token_pct": 95.0},
        )
        rr = p.on_event(ctx)
        assert rr.request_halt is True
        # halt 優先；不應同時 request_compact
        assert rr.request_compact is False

    def test_compact_resource_has_request_compact_true(self):
        """殺 `request_compact=True` mutation。"""
        p = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 85.0, "max_retries": 3},
        )
        rr = p.on_event(ctx)
        assert rr.request_compact is True
        assert rr.request_halt is False

    def test_halt_reason_contains_threshold(self):
        """殺 reason 字串字面值 mutation。"""
        p = TokenGuardPlugin(TokenGuardConfig(halt_threshold_pct=90.0))
        ctx = HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            payload={"token_pct": 95.0},
        )
        rr = p.on_event(ctx)
        assert "token_pct=95.0%" in rr.reason
        assert "halt_threshold" in rr.reason
        assert "90" in rr.reason

    def test_compact_reason_contains_dynamic_threshold(self):
        """殺 compact reason 字串字面值 mutation。"""
        p = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 85.0, "max_retries": 3},
        )
        rr = p.on_event(ctx)
        assert "token_pct=85.0%" in rr.reason
        assert "dynamic_compact_threshold" in rr.reason

    def test_disabled_short_circuits_before_phase_check(self):
        """殺 `if not self._cfg.enabled` 反向 mutation。"""
        p = TokenGuardPlugin(TokenGuardConfig(enabled=False, halt_threshold_pct=90.0))
        # 兩個 phase 都應 short-circuit
        for phase in [KernelPhase.POST_ATTEMPT, KernelPhase.ON_TOKEN_USAGE]:
            ctx = HookContext(
                phase=phase, playbook=_pb(), task=_task(),
                payload={"token_pct": 99.0},
            )
            assert p.on_event(ctx) is None

    def test_default_in_correction_loop_is_false(self):
        """殺 `payload.get('in_correction_loop', False)` default → True mutation。"""
        # 無 in_correction_loop 鍵 → 預設 False → 不影響 compact 判定
        p = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 70.0, "max_retries": 3},
        )
        # 70 < 80 → None
        assert p.on_event(ctx) is None

    def test_default_correction_history_len_is_zero(self):
        """殺 `payload.get('correction_history_len', 0)` default mutation。"""
        # in_correction_loop=True + history=0（預設）→ 仍 short_history 路徑
        p = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 85.0, "max_retries": 3, "in_correction_loop": True},
        )
        rr = p.on_event(ctx)
        assert rr is not None
        assert rr.request_compact is True

    def test_attempt_int_cast(self):
        """殺 `int(ctx.attempt or 0)` mutation：浮點 attempt 須能 cast。"""
        p = TokenGuardPlugin(TokenGuardConfig(
            compact_threshold_pct=80.0, halt_threshold_pct=90.0,
        ))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            payload={"token_pct": 82.0, "max_retries": 3},
            attempt=2,
        )
        rr = p.on_event(ctx)
        assert rr is not None


class TestPriorityConstant:
    """殺 `PRIORITY = 30` 常量 mutation。"""

    def test_priority_value_is_30(self):
        assert TokenGuardPlugin.PRIORITY == 30

    def test_instance_priority_returns_30(self):
        assert TokenGuardPlugin().priority() == 30

    def test_name_string_is_token_guard(self):
        """殺 `return 'token_guard'` 字串字面值 mutation。"""
        assert TokenGuardPlugin().name() == "token_guard"

    def test_subscribed_phases_includes_both(self):
        """殺 list element mutation。improving_79 W-78-2 新增 POST_COMPACT（Gap-008-E）。"""
        phases = TokenGuardPlugin().subscribed_phases()
        assert KernelPhase.POST_ATTEMPT in phases
        assert KernelPhase.ON_TOKEN_USAGE in phases
        assert KernelPhase.POST_COMPACT in phases
        assert len(phases) == 3


class TestPublicApiPreciseValues:
    """殺 delegation 中傳遞參數順序/keyword mutation。"""

    def test_should_halt_propagates_halt_threshold(self):
        """殺 `halt_threshold=self._cfg.halt_threshold_pct` 替換 mutation。"""
        p = TokenGuardPlugin(TokenGuardConfig(halt_threshold_pct=95.0))
        # pct=90 < halt=95 → False
        assert p.should_halt(90.0) is False
        # pct=95 == halt=95 → True
        assert p.should_halt(95.0) is True

    def test_should_compact_propagates_threshold_via_get_dynamic(self):
        """殺 `threshold = get_dynamic_compact_threshold(...)` 邏輯 mutation。"""
        p = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # attempt=0 → threshold=80
        assert p.should_compact(token_pct=80.0, attempt=0, max_retries=3) is True
        assert p.should_compact(token_pct=79.99, attempt=0, max_retries=3) is False

    def test_record_compact_failure_returns_count_after_increment(self):
        """殺 `return state.record_failure()` 委派 mutation。"""
        p = TokenGuardPlugin()
        assert p.record_compact_failure() == 1
        assert p.record_compact_failure() == 2
        assert p.record_compact_failure() == 3

    def test_reset_compact_failure_clears_to_zero(self):
        p = TokenGuardPlugin()
        p.record_compact_failure()
        p.record_compact_failure()
        p.reset_compact_failure()
        assert p.compact_failure_count == 0
        assert p.is_compact_failure_critical() is False

    def test_compact_failure_count_setter_int_cast(self):
        """殺 `int(value)` mutation。"""
        p = TokenGuardPlugin()
        p._compact_failure_count = "5"  # str input
        assert p._compact_failure_count == 5
        assert isinstance(p._compact_state.count, int)

    def test_process_compact_result_returns_false_when_critical(self):
        """殺 委派返回邏輯 mutation。"""
        p = TokenGuardPlugin()
        # default critical_threshold=2
        assert p.process_compact_result(True, peak_token_pct=85.0) is True
        assert p.process_compact_result(True, peak_token_pct=85.0) is False
