"""thresholds.py 純函式單元測試（SD_07 W3-T3-10）。

對應子模組：autoclaude/plugins/token_guard/thresholds.py
測試 API：
  - get_dynamic_compact_threshold (Gap-009-F)
  - should_compact_decision
  - should_halt_decision

目標：≥ 5 case + coverage 100%
"""
from __future__ import annotations

import pytest

from autoclaude.plugins.token_guard.thresholds import (
    get_dynamic_compact_threshold,
    should_compact_decision,
    should_halt_decision,
    verify_act_first_ordering,
)


class TestGetDynamicCompactThreshold:
    """Gap-009-F：依重試進度動態降低 compact 門檻。"""

    def test_attempt_zero_returns_base(self):
        assert get_dynamic_compact_threshold(
            base_threshold=80.0, attempt=0, max_retries=3,
        ) == pytest.approx(80.0)

    def test_attempt_increases_lowers_threshold(self):
        result = get_dynamic_compact_threshold(
            base_threshold=80.0, attempt=2, max_retries=3,
        )
        # 80 - (2/3)*15 = 80 - 10 = 70
        assert result == pytest.approx(70.0)

    def test_floor_clamps_lower_bound(self):
        # 大幅 decay 應撞下限 65
        result = get_dynamic_compact_threshold(
            base_threshold=80.0, attempt=10, max_retries=3, floor=65.0,
        )
        assert result == pytest.approx(65.0)

    def test_max_retries_zero_returns_base(self):
        # divisor 防呆
        assert get_dynamic_compact_threshold(
            base_threshold=80.0, attempt=5, max_retries=0,
        ) == pytest.approx(80.0)

    def test_attempt_equal_max_retries_clamps_ratio_to_1(self):
        result = get_dynamic_compact_threshold(
            base_threshold=80.0, attempt=3, max_retries=3,
        )
        # ratio min(1,1)=1 → 80 - 15 = 65
        assert result == pytest.approx(65.0)

    def test_custom_decay_factor(self):
        result = get_dynamic_compact_threshold(
            base_threshold=90.0, attempt=1, max_retries=2,
            floor=60.0, decay_factor=20.0,
        )
        # 90 - 0.5*20 = 80
        assert result == pytest.approx(80.0)


class TestShouldCompactDecision:
    def test_below_threshold_returns_false(self):
        assert should_compact_decision(
            token_pct=70.0, threshold=80.0,
            in_correction_loop=False, correction_history_len=0,
        ) is False

    def test_above_threshold_returns_true(self):
        assert should_compact_decision(
            token_pct=85.0, threshold=80.0,
            in_correction_loop=False, correction_history_len=0,
        ) is True

    def test_correction_loop_short_history_still_compacts(self):
        # in_correction_loop + history <= 1 仍 compact
        assert should_compact_decision(
            token_pct=85.0, threshold=80.0,
            in_correction_loop=True, correction_history_len=1,
        ) is True

    def test_correction_loop_long_history_compacts(self):
        assert should_compact_decision(
            token_pct=85.0, threshold=80.0,
            in_correction_loop=True, correction_history_len=5,
        ) is True


class TestShouldHaltDecision:
    def test_below_halt_threshold(self):
        assert should_halt_decision(token_pct=85.0, halt_threshold=90.0) is False

    def test_at_halt_threshold(self):
        assert should_halt_decision(token_pct=90.0, halt_threshold=90.0) is True

    def test_above_halt_threshold(self):
        assert should_halt_decision(token_pct=95.0, halt_threshold=90.0) is True


class TestVerifyActFirstOrdering:
    """improving_68 W-68-1 / R-68-1：act-first 排序保 Token Guard 形式化門檻權威。

    Rule 9：編碼「為何」——SDK autocompact 若搶在 AutoClaude halt 之前壓縮，會撞掉
    80%/90% 形式化門檻。本函式必須在「halt 換算 token < SDK autocompact 門檻」時才判安全；
    任何無法判定（門檻非正）必 fail-closed 回 False（寧可保守擋下）。
    """

    def test_safe_when_halt_tokens_below_autocompact(self):
        # 200k 上限、halt 90% = 180k tokens；SDK autocompact 在 190k → AutoClaude 先發 → 安全
        assert verify_act_first_ordering(
            autocompact_threshold_tokens=190_000, max_tokens=200_000, halt_pct=90.0,
        ) is True

    def test_unsafe_when_autocompact_fires_first(self):
        # SDK autocompact 在 150k，但 halt 90% = 180k → SDK 搶先壓縮 → 不安全（撞形式化門檻）
        assert verify_act_first_ordering(
            autocompact_threshold_tokens=150_000, max_tokens=200_000, halt_pct=90.0,
        ) is False

    def test_boundary_equal_is_unsafe(self):
        # 相等不算先發（須嚴格小於）→ 保守判不安全
        assert verify_act_first_ordering(
            autocompact_threshold_tokens=180_000, max_tokens=200_000, halt_pct=90.0,
        ) is False

    def test_fail_closed_on_nonpositive_max_tokens(self):
        assert verify_act_first_ordering(
            autocompact_threshold_tokens=190_000, max_tokens=0, halt_pct=90.0,
        ) is False

    def test_fail_closed_on_nonpositive_autocompact(self):
        assert verify_act_first_ordering(
            autocompact_threshold_tokens=0, max_tokens=200_000, halt_pct=90.0,
        ) is False
