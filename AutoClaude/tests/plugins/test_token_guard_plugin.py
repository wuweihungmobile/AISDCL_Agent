"""TokenGuardPlugin 單元測試（Phase 3 / W7 #8，≥ 10 cases）。"""
from __future__ import annotations

from autoclaude.core.event_bus import EventBus
from autoclaude.core.hookspec import HookContext, KernelPhase, ResourceRequest
from autoclaude.models.playbook import GlobalInvariants, Playbook, PlaybookTask
from autoclaude.plugins import TokenGuardPlugin
from autoclaude.utils.config import TokenGuardConfig


def _pb() -> Playbook:
    return Playbook(version="1.0", project="P",
                    global_invariants=GlobalInvariants(), tasks=[])


def _task() -> PlaybookTask:
    return PlaybookTask(step_id="T01", name="n", prompt="p")


class TestTokenGuardPluginBasics:
    def test_name(self):
        assert TokenGuardPlugin().name() == "token_guard"

    def test_priority_is_30(self):
        assert TokenGuardPlugin().priority() == 30

    def test_subscribed_phases(self):
        phases = TokenGuardPlugin().subscribed_phases()
        assert KernelPhase.POST_ATTEMPT in phases
        assert KernelPhase.ON_TOKEN_USAGE in phases
        # improving_79 W-78-2：新增 POST_COMPACT（Gap-008-E 連續失敗判定）
        assert KernelPhase.POST_COMPACT in phases

    def test_disabled_returns_none(self):
        plugin = TokenGuardPlugin(token_guard_cfg=TokenGuardConfig(enabled=False))
        ctx = HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            payload={"token_pct": 95.0},
        )
        assert plugin.on_event(ctx) is None


class TestTokenGuardPluginThresholds:
    def test_should_halt_above_halt_threshold(self):
        plugin = TokenGuardPlugin(TokenGuardConfig(halt_threshold_pct=90.0))
        assert plugin.should_halt(95.0) is True
        assert plugin.should_halt(89.0) is False

    def test_should_compact_above_threshold(self):
        plugin = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        assert plugin.should_compact(82.0) is True
        assert plugin.should_compact(75.0) is False

    def test_dynamic_threshold_decreases_with_attempts(self):
        """Gap-009-F：高重試時提前 compact。"""
        plugin = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # attempt=0 → 80% 不變
        assert plugin.get_dynamic_compact_threshold(0, 5) == 80.0
        # attempt=3, max=5 → 80 - 9 = 71
        assert plugin.get_dynamic_compact_threshold(3, 5) == 71.0
        # 下限 65%
        assert plugin.get_dynamic_compact_threshold(10, 1) == 65.0

    def test_dynamic_threshold_max_retries_zero(self):
        plugin = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        assert plugin.get_dynamic_compact_threshold(0, 0) == 80.0


class TestTokenGuardPluginResourceRequests:
    def test_halt_when_above_halt_threshold(self):
        plugin = TokenGuardPlugin(
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0))
        ctx = HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            payload={"token_pct": 95.0},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, ResourceRequest)
        assert result.request_halt is True
        assert result.request_compact is False

    def test_compact_when_above_compact_threshold(self):
        plugin = TokenGuardPlugin(
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            attempt=0,
            payload={"token_pct": 85.0, "max_retries": 3},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, ResourceRequest)
        assert result.request_compact is True
        assert result.request_halt is False

    def test_no_action_below_compact_threshold(self):
        plugin = TokenGuardPlugin(
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            attempt=0,
            payload={"token_pct": 50.0},
        )
        assert plugin.on_event(ctx) is None


class TestTokenGuardPluginCompactFailures:
    def test_record_compact_failure_increments(self):
        plugin = TokenGuardPlugin()
        assert plugin.record_compact_failure() == 1
        assert plugin.record_compact_failure() == 2

    def test_is_compact_failure_critical_at_2(self):
        plugin = TokenGuardPlugin()
        assert plugin.is_compact_failure_critical() is False
        plugin.record_compact_failure()
        assert plugin.is_compact_failure_critical() is False
        plugin.record_compact_failure()
        assert plugin.is_compact_failure_critical() is True   # 連續 2 次 → 升級 HALT

    def test_reset_clears_count(self):
        plugin = TokenGuardPlugin()
        plugin.record_compact_failure()
        plugin.record_compact_failure()
        plugin.reset_compact_failure()
        assert plugin._compact_failure_count == 0
        assert plugin.is_compact_failure_critical() is False


class TestTokenGuardPluginEventBusIntegration:
    def test_halt_via_bus(self):
        bus = EventBus()
        bus.register(TokenGuardPlugin(TokenGuardConfig(halt_threshold_pct=90.0)))
        merged = bus.emit(HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            payload={"token_pct": 92.0},
        ))
        assert merged.request_halt is True

    def test_compact_via_bus(self):
        bus = EventBus()
        bus.register(TokenGuardPlugin(
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0)))
        merged = bus.emit(HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            attempt=0,
            payload={"token_pct": 82.0, "max_retries": 3},
        ))
        assert merged.request_compact is True


class TestTokenGuardPluginCorrectionLoop:
    def test_compact_in_correction_loop_with_history_le_1(self):
        """LOW-8：在 correction 迴圈中（history <= 1）只在 dynamic_threshold 達標時 compact。"""
        plugin = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # attempt=2, max=5 → dynamic = 80 - 6 = 74
        # token_pct=70 < 74 → 不 compact
        assert plugin.should_compact(
            token_pct=70, attempt=2, max_retries=5,
            in_correction_loop=True, correction_history_len=1,
        ) is False
        # token_pct=78 >= 74 → compact
        assert plugin.should_compact(
            token_pct=78, attempt=2, max_retries=5,
            in_correction_loop=True, correction_history_len=1,
        ) is True


# ──────────────────────────────────────────────────────────
# W2 T11 補測（SD_Improving_04 §4 T11）：補強 ≥ 90% coverage
# 既有測試已涵蓋大部分情境；本區針對缺漏分支補足
# ──────────────────────────────────────────────────────────
class TestTokenGuardPluginW2Coverage:
    """W2 T11：補強既有測試遺漏的細項分支以達 ≥ 90% coverage。"""

    def test_priority_constant_is_30(self):
        """PRIORITY 常數驗證（class-level constant）。"""
        assert TokenGuardPlugin.PRIORITY == 30
        # instance method 一致
        assert TokenGuardPlugin().priority() == TokenGuardPlugin.PRIORITY

    def test_subscribed_phases_contains_both(self):
        """subscribed_phases 必須同時包含 POST_ATTEMPT 與 ON_TOKEN_USAGE。"""
        phases = TokenGuardPlugin().subscribed_phases()
        assert KernelPhase.POST_ATTEMPT in phases
        assert KernelPhase.ON_TOKEN_USAGE in phases
        # 不訂閱其他 phase（防止過度耦合）
        assert KernelPhase.PRE_RUN not in phases

    def test_disabled_config_returns_none_for_post_attempt(self):
        """cfg.enabled=False + POST_ATTEMPT → on_event 回 None（短路）。"""
        plugin = TokenGuardPlugin(token_guard_cfg=TokenGuardConfig(enabled=False))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            attempt=0, payload={"token_pct": 95.0, "max_retries": 3},
        )
        assert plugin.on_event(ctx) is None


class TestPostCompactGap008E:
    """improving_79 W-78-2（DEF-78-001 / RTM-79-4）：POST_COMPACT 連續 compact 失敗判定。

    驗證意圖（Rule 9）：compact 後若 context 仍壓不下來（仍達 compact 門檻），須累計失敗；
    連續達上限（預設 2）必須升級為 request_halt——否則 token 失控時無安全網（Gap-008-E）。
    CompactFailureState 為 SSOT、留在 plugin，不外洩 Kernel。
    """

    def _ctx(self, post_pct: float, attempt: int = 0) -> HookContext:
        return HookContext(
            phase=KernelPhase.POST_COMPACT, playbook=_pb(), task=_task(),
            attempt=attempt, payload={"token_pct": post_pct, "max_retries": 3},
        )

    def test_compact_success_resets_and_returns_none(self):
        """compact 後降到門檻下（50%）→ 回 None、計數器重設。"""
        plugin = TokenGuardPlugin()
        assert plugin.on_event(self._ctx(50.0)) is None
        assert plugin.compact_failure_count == 0

    def test_single_failure_no_halt_yet(self):
        """compact 後仍高（85%）一次 → 記 1 次失敗，未達上限 → 尚不 halt。"""
        plugin = TokenGuardPlugin()
        assert plugin.on_event(self._ctx(85.0)) is None
        assert plugin.compact_failure_count == 1

    def test_consecutive_failures_trigger_halt(self):
        """連續兩次 compact 後仍高 → 第 2 次達上限 → request_halt（Gap-008-E）。"""
        plugin = TokenGuardPlugin()
        assert plugin.on_event(self._ctx(85.0)) is None  # 1st failure
        result = plugin.on_event(self._ctx(88.0))         # 2nd → critical
        assert isinstance(result, ResourceRequest)
        assert result.request_halt is True
        assert "Gap-008-E" in result.reason

    def test_success_between_failures_resets_counter(self):
        """失敗後一次成功 compact → 計數器歸零，不會誤升級 halt。"""
        plugin = TokenGuardPlugin()
        plugin.on_event(self._ctx(85.0))   # failure 1
        plugin.on_event(self._ctx(40.0))   # success → reset
        assert plugin.compact_failure_count == 0
        assert plugin.on_event(self._ctx(85.0)) is None  # 又 1 次，仍未達上限

    def test_disabled_returns_none_for_post_compact(self):
        """cfg.enabled=False → POST_COMPACT 短路回 None。"""
        plugin = TokenGuardPlugin(token_guard_cfg=TokenGuardConfig(enabled=False))
        assert plugin.on_event(self._ctx(95.0)) is None

    def test_should_halt_at_exact_threshold(self):
        """token_pct == halt_threshold → True（>= 邊界包含）。"""
        plugin = TokenGuardPlugin(TokenGuardConfig(halt_threshold_pct=90.0))
        assert plugin.should_halt(90.0) is True
        assert plugin.should_halt(89.99) is False

    def test_dynamic_threshold_lower_bound_65(self):
        """attempt 極高時 dynamic threshold 下限為 65。"""
        plugin = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # attempt 遠超 max → ratio 被夾至 1.0 → 80 - 15 = 65
        assert plugin.get_dynamic_compact_threshold(100, 1) == 65.0
        # 即便傳入更高也不再下降
        assert plugin.get_dynamic_compact_threshold(9999, 3) == 65.0

    def test_dynamic_threshold_max_retries_zero_returns_base(self):
        """max_retries=0 → 直接回 base（避免除以零）。"""
        plugin = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=78.5))
        assert plugin.get_dynamic_compact_threshold(0, 0) == 78.5
        assert plugin.get_dynamic_compact_threshold(5, 0) == 78.5

    def test_should_compact_in_correction_loop_with_single_history(self):
        """in_correction_loop=True + history_len=1 + 達 dynamic_threshold → True。"""
        plugin = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # attempt=0 → dynamic = base = 80
        assert plugin.should_compact(
            token_pct=82, attempt=0, max_retries=3,
            in_correction_loop=True, correction_history_len=1,
        ) is True

    def test_should_compact_in_correction_loop_with_zero_history(self):
        """SD_04 W2 Dev-W2-Min-4：in_correction_loop=True + history_len=0
        + 達 dynamic_threshold → True（驗證 should_compact L80-82 `<=1` 涵蓋 0 邊界）。
        """
        plugin = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        # history_len=0 也應觸發 compact（<= 1 包含 0）
        assert plugin.should_compact(
            token_pct=82, attempt=0, max_retries=3,
            in_correction_loop=True, correction_history_len=0,
        ) is True
        # 反證：token_pct < threshold 時不應 compact（即使 history_len=0）
        assert plugin.should_compact(
            token_pct=70, attempt=0, max_retries=3,
            in_correction_loop=True, correction_history_len=0,
        ) is False

    def test_should_compact_normal_flow_above_threshold(self):
        """非 correction loop + token >= threshold → True（基本路徑）。"""
        plugin = TokenGuardPlugin(TokenGuardConfig(compact_threshold_pct=80.0))
        assert plugin.should_compact(
            token_pct=85, attempt=0, max_retries=3,
            in_correction_loop=False, correction_history_len=0,
        ) is True

    def test_record_compact_failure_and_reset_round_trip(self):
        """record 後 reset → 計數歸零、is_compact_failure_critical 回 False。"""
        plugin = TokenGuardPlugin()
        plugin.record_compact_failure()
        plugin.record_compact_failure()
        assert plugin.is_compact_failure_critical() is True
        plugin.reset_compact_failure()
        assert plugin.is_compact_failure_critical() is False
        assert plugin._compact_failure_count == 0

    def test_is_compact_failure_critical_at_two_consecutive(self):
        """連續 2 次失敗 → critical（>= 2 邊界）。"""
        plugin = TokenGuardPlugin()
        assert plugin.is_compact_failure_critical() is False
        assert plugin.record_compact_failure() == 1
        assert plugin.is_compact_failure_critical() is False
        assert plugin.record_compact_failure() == 2
        assert plugin.is_compact_failure_critical() is True
        # 第 3 次仍為 critical
        plugin.record_compact_failure()
        assert plugin.is_compact_failure_critical() is True

    def test_evaluate_resources_emits_halt_request_via_post_attempt(self):
        """POST_ATTEMPT + token_pct >= halt_threshold → ResourceRequest(request_halt=True)。"""
        plugin = TokenGuardPlugin(
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            attempt=1, payload={"token_pct": 95.0, "max_retries": 3},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, ResourceRequest)
        assert result.request_halt is True
        assert result.request_compact is False
        assert result.contributor == "token_guard"
        assert "95.0%" in result.reason

    def test_evaluate_resources_emits_compact_request(self):
        """POST_ATTEMPT + compact <= token_pct < halt → ResourceRequest(request_compact=True)。"""
        plugin = TokenGuardPlugin(
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            attempt=0, payload={"token_pct": 85.0, "max_retries": 3},
        )
        result = plugin.on_event(ctx)
        assert isinstance(result, ResourceRequest)
        assert result.request_compact is True
        assert result.request_halt is False
        assert result.contributor == "token_guard"

    def test_evaluate_resources_below_compact_threshold_returns_none(self):
        """token_pct=50% < compact_threshold=80% → on_event 回 None（不觸發任何 request）。"""
        plugin = TokenGuardPlugin(
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            attempt=0, payload={"token_pct": 50.0, "max_retries": 3},
        )
        assert plugin.on_event(ctx) is None

    def test_on_token_usage_phase_handled_same_as_post_attempt(self):
        """ON_TOKEN_USAGE 與 POST_ATTEMPT 對相同 payload 應產生等價結果。"""
        plugin = TokenGuardPlugin(
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0))
        payload = {"token_pct": 92.0, "max_retries": 3}
        ctx_post = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            attempt=0, payload=payload,
        )
        ctx_tok = HookContext(
            phase=KernelPhase.ON_TOKEN_USAGE, playbook=_pb(), task=_task(),
            attempt=0, payload=payload,
        )
        r_post = plugin.on_event(ctx_post)
        r_tok = plugin.on_event(ctx_tok)
        assert isinstance(r_post, ResourceRequest)
        assert isinstance(r_tok, ResourceRequest)
        # 兩者皆為 halt request
        assert r_post.request_halt is True
        assert r_tok.request_halt is True

    def test_payload_missing_token_pct_defaults_to_zero(self):
        """payload 缺 token_pct → 預設 0.0、不觸發任何 request。"""
        plugin = TokenGuardPlugin(
            TokenGuardConfig(compact_threshold_pct=80.0, halt_threshold_pct=90.0))
        ctx = HookContext(
            phase=KernelPhase.POST_ATTEMPT, playbook=_pb(), task=_task(),
            attempt=0, payload={},   # 無 token_pct
        )
        assert plugin.on_event(ctx) is None

    def test_on_event_with_unknown_phase_returns_none(self):
        """非訂閱的 phase（PRE_RUN）→ on_event 回 None（防禦性路徑）。"""
        plugin = TokenGuardPlugin()
        ctx = HookContext(
            phase=KernelPhase.PRE_RUN, playbook=_pb(), task=_task(),
            payload={"token_pct": 95.0},
        )
        # enabled=True 但 phase 不在 POST_ATTEMPT / ON_TOKEN_USAGE 分支內
        assert plugin.on_event(ctx) is None
