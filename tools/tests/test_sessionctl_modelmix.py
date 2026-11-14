"""sessionctl 模型平衡建議（TCS-SessionCtl AT-SC-81～84；ADR-XPLAT-004 §2.13.7 D8）。只出聲。"""
from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLS = _REPO_ROOT / "tools"
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

from lib.sessionctl import modelmix  # noqa: E402

NOW = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)
HALF = (NOW + timedelta(days=3.5)).isoformat()  # 週剩 3.5 天 ⇒ elapsed 0.5


class _Axis:
    def __init__(self, kind: str, pct: float, resets_at, scope_model=None) -> None:
        self.kind, self.pct, self.resets_at, self.scope_model = kind, pct, resets_at, scope_model


def _axes(all_pct: float, scoped_pct: float, resets=HALF, scoped_resets=HALF):
    return (_Axis("weekly_all", all_pct, resets),
            _Axis("weekly_scoped", scoped_pct, scoped_resets, "Fable"))


class AdviceTest(unittest.TestCase):
    def test_at_sc_81_scoped_axis_ahead_says_fable_ahead(self) -> None:
        """AT-SC-81：週剩 3.5 天（elapsed .5）：all 40%、Fable 70% ⇒ 「Fable 超前：多外派」。"""
        line = modelmix.advice_line(_axes(40, 70), now=NOW)
        self.assertIn("Fable 超前：多外派", line)

    def test_at_sc_82_all_model_axis_ahead_says_downgrade_subagents(self) -> None:
        """AT-SC-82：all 70%、Fable 30% ⇒ 「全模型超前：子代理降級」且提到禁續棒。"""
        line = modelmix.advice_line(_axes(70, 30), now=NOW)
        self.assertIn("全模型超前：子代理降級", line)
        self.assertIn("禁續棒", line)

    def test_at_sc_83_both_axes_wide_allows_opus_review(self) -> None:
        """AT-SC-83：all 20%、Fable 20%、elapsed .5 ⇒ 「兩軸皆寬：深度審查可用 Opus」。"""
        self.assertIn("兩軸皆寬：深度審查可用 Opus", modelmix.advice_line(_axes(20, 20), now=NOW))

    def test_balanced_when_neither_ahead_nor_wide(self) -> None:
        """第四種情境：兩軸相近且至少一軸 ratio ≥ 0.8（all 45／Fable 50 ⇒ 0.9／1.0）⇒ 「平衡」。"""
        self.assertTrue(modelmix.advice_line(_axes(45, 50), now=NOW).endswith("平衡"))

    def test_gap_boundary_is_inclusive_at_015(self) -> None:
        """ratio 差恰為 0.15 即判超前（`>=`）：all 40（.8）、Fable 47.5（.95）⇒ 差 .15。"""
        self.assertIn("Fable 超前", modelmix.advice_line(_axes(40, 47.5), now=NOW))
        self.assertTrue(modelmix.advice_line(_axes(40, 47.0), now=NOW).endswith("平衡"))

    def test_at_sc_84_missing_resets_at_skips_that_axis_and_says_cannot_measure(self) -> None:
        """AT-SC-84：`resets_at` 缺 ⇒ 該軸不判、印「量不到」、不拋，且不憑單軸下建議。"""
        line = modelmix.advice_line(_axes(40, 70, scoped_resets=None), now=NOW)
        self.assertIn("量不到", line)
        self.assertIn("缺 resets_at", line)
        self.assertNotIn("超前", line)
        self.assertIn("量不到", modelmix.advice_line((), now=NOW))

    def test_scoped_axis_of_another_model_is_ignored(self) -> None:
        """專屬軸的 `scope_model` 不是主控家族（如 Opus 軸）⇒ 不拿來比（不猜）。"""
        axes = (_Axis("weekly_all", 40, HALF), _Axis("weekly_scoped", 90, HALF, "Opus"))
        self.assertIn("量不到", modelmix.advice_line(axes, now=NOW, family="fable"))
        self.assertIn("Opus 超前", modelmix.advice_line(axes, now=NOW, family="opus"))

    def test_elapsed_is_clamped_so_a_fresh_week_does_not_divide_by_zero(self) -> None:
        """剛 reset（剩 7 天）⇒ elapsed 夾在 0.05：5% 用量＝ratio 1.0，不除以零、不爆。"""
        fresh = (NOW + timedelta(days=7)).isoformat()
        line = modelmix.advice_line(_axes(5, 5, fresh, fresh), now=NOW)
        self.assertTrue(line.endswith("平衡"), line)


class PaceLineTest(unittest.TestCase):
    def _gate(self, axes, reason="ok"):
        state = type("S", (), {"axes": axes, "reason": reason})()
        return type("G", (), {"read_quota": staticmethod(lambda now: state)})

    def test_pace_line_ends_with_newline_for_planner_print(self) -> None:
        """`--pace` 接線：回傳含換行，planner 以 `print(..., end="")` 接。"""
        line = modelmix.pace_line(self._gate(_axes(40, 70)), "fable", NOW)
        self.assertTrue(line.startswith("模型建議：") and line.endswith("\n"))

    def test_cache_unavailable_or_gate_failure_degrades_to_cannot_measure(self) -> None:
        """額度快取不可用 ⇒ 「量不到」並帶原因；gate 本身例外 ⇒ 也收成一行，不得擋 --pace。"""
        self.assertIn("量不到", modelmix.pace_line(self._gate((), "stale-cache")))
        self.assertIn("stale-cache", modelmix.pace_line(self._gate((), "stale-cache")))
        self.assertIn("量不到", modelmix.pace_line(object()))


if __name__ == "__main__":
    unittest.main()
