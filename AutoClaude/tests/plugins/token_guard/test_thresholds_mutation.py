"""thresholds.py 補強測試 — SD_09 W1 A-1（mutation pilot kill rate ≥ 70%）。

對應 SD_Improving_09 W1 範疇：thresholds.py 7 個 survived mutation
（id: 117, 119, 123, 125-128）。

聚焦：
  - 算術 mutation：`-` ↔ `+`, `*` ↔ `/`, `attempt / max_retries` ↔ `attempt * max_retries`
  - 邊界 mutation：`max_retries <= 0` 邊界值
  - 常量 mutation：default floor=65.0、decay_factor=15.0、min(ratio, 1.0)
  - 返回值 mutation：`max(...)` clamp 邏輯
"""
from __future__ import annotations

import pytest

from autoclaude.plugins.token_guard.thresholds import (
    get_dynamic_compact_threshold,
    should_compact_decision,
    should_halt_decision,
)


class TestDynamicThresholdArithmetic:
    """殺算術 mutation：公式 base - (attempt/max_retries) * decay_factor。"""

    def test_subtraction_not_addition(self):
        """殺 `base - ratio*decay` → `base + ratio*decay` mutation。"""
        result = get_dynamic_compact_threshold(
            base_threshold=80.0, attempt=1, max_retries=3,
        )
        # 80 - (1/3)*15 = 75
        assert result == pytest.approx(75.0)
        # 若改成加法 → 85，會更高
        assert result < 80.0

    def test_division_not_multiplication(self):
        """殺 `attempt/max_retries` → `attempt*max_retries` mutation。"""
        # attempt=1, max_retries=3 → ratio = 1/3 ≈ 0.333
        # 若改乘法 → 1*3=3 (clamped to 1) → 65（撞 floor）
        result = get_dynamic_compact_threshold(
            base_threshold=80.0, attempt=1, max_retries=3,
        )
        # 正確：80 - 5 = 75；若是乘法 → 65（floor）
        assert result == pytest.approx(75.0)
        assert result != 65.0

    def test_multiplication_with_decay_factor_not_division(self):
        """殺 `ratio * decay_factor` → `ratio / decay_factor` mutation。"""
        result = get_dynamic_compact_threshold(
            base_threshold=80.0, attempt=3, max_retries=3, decay_factor=15.0,
        )
        # ratio=1, 1*15=15 → 80-15=65
        # 若是除法：1/15≈0.067 → 80-0.067≈79.93
        assert result == pytest.approx(65.0)
        assert result < 70.0

    def test_max_retries_zero_uses_le_not_lt(self):
        """殺 `max_retries <= 0` → `< 0` boundary mutation。"""
        # max_retries=0 → 防呆走 base
        assert get_dynamic_compact_threshold(
            base_threshold=88.0, attempt=5, max_retries=0,
        ) == pytest.approx(88.0)

    def test_max_retries_negative_uses_le_branch(self):
        """殺 `<= 0` → `< 1` 邊界判定 mutation。"""
        assert get_dynamic_compact_threshold(
            base_threshold=88.0, attempt=5, max_retries=-1,
        ) == pytest.approx(88.0)

    def test_ratio_min_clamps_to_1_not_0(self):
        """殺 `min(attempt/max_retries, 1.0)` 中 1.0 → 0.0 mutation。"""
        # attempt > max_retries → ratio 應 clamp 到 1，但若 clamp 到 0 → 結果=base 不下降
        result = get_dynamic_compact_threshold(
            base_threshold=80.0, attempt=10, max_retries=3, floor=50.0,
        )
        # clamp=1 → 80 - 15 = 65；若 clamp=0 → 80（不下降）
        assert result == pytest.approx(65.0)
        assert result < 80.0

    def test_default_floor_is_65(self):
        """殺 `floor: float = 65.0` default value mutation。"""
        # 大 attempt → 應撞預設 floor=65
        result = get_dynamic_compact_threshold(
            base_threshold=100.0, attempt=100, max_retries=1,
        )
        # 100 - 1*15 = 85；不撞 floor
        assert result == pytest.approx(85.0)
        # 改用更大 decay 強制撞 floor
        result_floor = get_dynamic_compact_threshold(
            base_threshold=70.0, attempt=10, max_retries=1, decay_factor=100.0,
        )
        assert result_floor == pytest.approx(65.0)  # floor 預設 65

    def test_default_decay_factor_is_15(self):
        """殺 `decay_factor: float = 15.0` default value mutation。"""
        result = get_dynamic_compact_threshold(
            base_threshold=80.0, attempt=3, max_retries=3,
        )
        # 預設 decay=15 → ratio=1 → 80-15 = 65
        assert result == pytest.approx(65.0)

    def test_floor_clamps_via_max_not_min(self):
        """殺 `max(base-decay, floor)` → `min(...)` mutation。"""
        # base-decay 低於 floor 時應取 floor（用 max）
        result = get_dynamic_compact_threshold(
            base_threshold=70.0, attempt=10, max_retries=1,
            decay_factor=100.0, floor=60.0,
        )
        # 70 - 100 = -30；max(-30, 60) = 60；若是 min(-30, 60) = -30
        assert result == pytest.approx(60.0)
        assert result > 0


class TestShouldCompactDecisionBoundaries:
    """殺 should_compact_decision 中 `<`, `>=`, `<=` 邊界 mutation。"""

    def test_exactly_at_threshold_returns_true(self):
        """殺 `token_pct < threshold` → `<= threshold` mutation。"""
        # pct == threshold → 應 compact（>= threshold）
        assert should_compact_decision(
            token_pct=80.0, threshold=80.0,
            in_correction_loop=False, correction_history_len=0,
        ) is True

    def test_below_threshold_returns_false(self):
        assert should_compact_decision(
            token_pct=79.99, threshold=80.0,
            in_correction_loop=False, correction_history_len=0,
        ) is False

    def test_correction_loop_exactly_one_history_compacts_when_at_threshold(self):
        """殺 `correction_history_len <= 1` 中 1 → 0 / 2 mutation。"""
        assert should_compact_decision(
            token_pct=80.0, threshold=80.0,
            in_correction_loop=True, correction_history_len=1,
        ) is True

    def test_correction_loop_zero_history_compacts(self):
        assert should_compact_decision(
            token_pct=80.0, threshold=80.0,
            in_correction_loop=True, correction_history_len=0,
        ) is True

    def test_correction_loop_two_history_compacts_at_threshold(self):
        """history > 1 也應走第二條 return True（pct >= threshold）。"""
        assert should_compact_decision(
            token_pct=80.0, threshold=80.0,
            in_correction_loop=True, correction_history_len=2,
        ) is True


class TestShouldHaltDecisionBoundaries:
    """殺 should_halt_decision 的 `>=` boundary mutation（id 132,137,140 在 watcher 內也用到）。"""

    def test_exactly_at_halt_threshold_returns_true(self):
        """殺 `>= halt` → `> halt` mutation。"""
        assert should_halt_decision(token_pct=90.0, halt_threshold=90.0) is True

    def test_below_halt_returns_false(self):
        assert should_halt_decision(token_pct=89.99, halt_threshold=90.0) is False

    def test_well_above_halt_returns_true(self):
        assert should_halt_decision(token_pct=100.0, halt_threshold=90.0) is True

    def test_zero_token_pct_below_threshold(self):
        """殺常量 mutation：halt_threshold > 0 時，pct=0 必 False。"""
        assert should_halt_decision(token_pct=0.0, halt_threshold=90.0) is False
