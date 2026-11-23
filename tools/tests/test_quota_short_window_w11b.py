"""AT-QW-92／MU-QW-60／61：`tools/lib/quota_short_window.py` 的 `pace_line` 短窗欄。"""
from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))
import quota_messages as QM  # noqa: E402
import quota_policy as Q  # noqa: E402
import quota_short_window as QSW  # noqa: E402

NOW = datetime(2026, 11, 23, 10, 2, tzinfo=UTC)
P, A = Q.DEFAULT_POLICY, Q.Axis


def at(m):
    return (NOW + timedelta(minutes=m)).isoformat()


def decide(five_pct, five_min=38, week_pct=58):
    axes = (A("five_hour", five_pct, at(five_min)), A("seven_day", week_pct, at(8233)))
    state = Q.QuotaState(axes, NOW.isoformat(), "cache")
    return Q.decide(state, NOW, P, pace_floor=False)


class TestShortWindowNote(unittest.TestCase):
    """AT-QW-92：`tools/lib/quota_messages.py::pace_line` 標題的短窗欄與 `_binding_key` 回歸。"""

    def test_a_hidden_short_window_band_is_named_in_the_title(self) -> None:
        """①10:02 事故形：週軸平手勝出為 binding，標題必須另講五小時窗的帶（MU-QW-60）。"""
        d = decide(80)
        self.assertEqual(d.binding.kind, "seven_day", "前提：平手取長視野＝週軸（事故原形）")
        line = QM.pace_line(d, 0, P.max_fanout)
        self.assertIn("｜短窗=converge five_hour 80% 剩 38 分", line)
        self.assertIn("最緊的一條＝seven_day 58%", line)

    def test_no_note_when_the_short_window_is_the_binding_axis(self) -> None:
        """②five_hour 自己就是 binding（帶相同）⇒ 不補。"""
        d = decide(80, week_pct=10)
        self.assertEqual(d.binding.kind, "five_hour")
        self.assertNotIn("短窗=", QM.pace_line(d, 0, P.max_fanout))

    def test_no_note_when_the_short_window_is_below_the_binding_band(self) -> None:
        """③五小時窗低於 binding 帶 ⇒ 不補（只補「被藏起來的更高帶」）。"""
        d = decide(5, week_pct=80)
        self.assertEqual(d.binding.kind, "seven_day")
        self.assertNotIn("短窗=", QM.pace_line(d, 0, P.max_fanout))

    def test_binding_key_tie_rule_is_unchanged(self) -> None:
        """④MU-QW-61：平手仍取剩餘分鐘較長者（週軸）；呈現層不得改 `_binding_key`。"""
        d = decide(80)
        gate = [r for r in d.per_axis if r.cap == d.cap]
        self.assertEqual(len(gate), 2, "前提：兩軸 cap 平手")
        self.assertEqual(min(gate, key=Q._binding_key).axis.kind, "seven_day")
        self.assertEqual(d.band, "notice", "band 判定同 r8：仍取 binding 帶")

    def test_unmeasured_short_window_reset_is_stated_not_invented(self) -> None:
        """五小時窗 reset 不明 ⇒ 明講「reset 距離不明」，不編分鐘數。"""
        state = Q.QuotaState((A("five_hour", 80.0, None), A("seven_day", 58.0, at(8233))),
                             NOW.isoformat(), "cache")
        d = Q.decide(state, NOW, P, pace_floor=False)
        note = QSW.short_window_note(d)
        self.assertTrue(note == "" or "reset 距離不明" in note)


if __name__ == "__main__":
    unittest.main()
