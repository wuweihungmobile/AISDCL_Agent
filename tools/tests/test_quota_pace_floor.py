"""`tools/lib/quota_pace_floor.py` 的機械物（TCS-TokenWaste-20261114 §10.4.1～10.4.3，AT-QP-01～24；
另含 AT-QP-66／67 的靜態判準）。

每條 AT 的 docstring 寫「為何會紅」：改錯邏輯時這條要能轉紅，不是只斷言今天的實作是綠的。
測試零 I/O、零時鐘：`now` 一律注入，環境一律用 `Policy`（本檔不讀真實 `~/.autosdd`）。

執行：python -m unittest discover -s tools/tests -p test_quota_pace_floor.py
"""
from __future__ import annotations

import ast
import dataclasses
import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools" / "lib"))
import quota_pace as W  # noqa: E402
import quota_pace_floor as PF  # noqa: E402
import quota_policy as Q  # noqa: E402

NOW = datetime(2026, 11, 15, 10, 0, 0, tzinfo=UTC)
P = Q.DEFAULT_POLICY
_INF = float("inf")


def _floor(pct, minutes, window=300.0, p=P, **kw):
    """以預設政策呼叫 `pace_floor`；`kw` 可覆寫 burst／step 等。"""
    q = dataclasses.replace(p, **kw) if kw else p
    return PF.pace_floor(pct, minutes, window, q.pace_burst_pp, q.pace_step_pp,
                         q.converge_pct, q.prepare_pct, q.halt_pct)


def _at(minutes):
    return None if minutes is None else (NOW + timedelta(minutes=minutes)).isoformat()


def _rows(*specs):
    """`[(kind, pct, minutes)]` → `quota_policy._rows` 形狀。"""
    return tuple((k, p, _at(m), "ok") for k, p, m in specs)


def _deltas(rows):
    return tuple(W.expiry_of(r[2], NOW) for r in rows)


def _resolved(rows, ratio=None):
    return W.resolve(rows, _deltas(rows), ratio, "" if ratio is None else "test",
                     P.accel_window_minutes, P.far_horizon_minutes, P.halt_pct,
                     P.pace_ceiling, P.converge_pct)


def _eval(specs, policy=P, **kw):
    rows = _rows(*specs)
    floors = PF.evaluate(rows, _deltas(rows), policy, NOW, **kw)
    return rows, floors


def _lvl(value):
    return -_INF if value is None else value


class PaceFloorFnTest(unittest.TestCase):
    """AT-QP-01～11：`pace_floor()` 純函式。"""

    def test_at_qp_01_three_real_incident_points_all_get_converge(self):
        """三個真實事故點（ADR 2.15.0）；少算 burst 或把允許線算錯，三點之一會偏離 70。"""
        for pct, minutes in ((38, 247), (43, 244), (48, 230)):
            with self.subTest(pct=pct, minutes=minutes):
                self.assertEqual(_floor(pct, minutes), 70.0)

    def test_at_qp_02_over_exactly_zero_is_not_braked(self):
        """`over <= 0` 寫成 `< 0` 會把「剛好在線上」也煞車，床變成嚴格線性。"""
        self.assertIsNone(_floor(50, 210))
        self.assertEqual(_floor(51, 210), 70.0)

    def test_at_qp_03_over_exactly_step_stays_in_converge(self):
        """`over > S` 寫成 `>= S` 會讓邊界點越級進 prepare，觸發任務書落盤副作用。"""
        self.assertEqual(_floor(60, 210), 70.0)
        self.assertEqual(_floor(61, 210), 85.0)

    def test_at_qp_04_window_tail_is_never_braked(self):
        """use-it-or-lose-it：burst=20 時第 240 分起允許線 >=100，床不得破壞窗尾用完（AC-2）。"""
        self.assertIsNone(_floor(99, 30))
        for minutes in range(0, 61, 5):
            for pct in range(0, 101):
                with self.subTest(minutes=minutes, pct=pct):
                    self.assertIsNone(_floor(pct, minutes))

    def test_at_qp_05_unknown_schedule_never_lifts(self):
        """期程不明不得抬水位（同 `lead_pp` 前置）；抬了就是無證據的新煞車。"""
        for minutes, window in ((None, 300.0), (-1.0, 300.0), (100.0, None), (100.0, 0.0)):
            with self.subTest(minutes=minutes, window=window):
                self.assertIsNone(_floor(99, minutes, window))

    def test_at_qp_06_derived_level_never_reaches_halt(self):
        """推導值永不觸發 halt（halt 只由伺服器真實水位開火）；去掉夾層即回 96。"""
        self.assertEqual(_floor(61, 210, prepare_pct=96.0, halt_pct=95.0, notice_pct=50.0), 94.0)

    def test_at_qp_07_grid_properties(self):
        """AC-3 網格性質：結果∈{None}∪[converge,halt-1]、pct 增則不遞減、時間流逝則不遞增；
        任何符號寫反或單位寫錯會在某一格破單調。"""
        grid = {(p, m): _floor(p, m) for p in range(0, 101) for m in range(0, 301, 5)}
        for (pct, minutes), got in grid.items():
            self.assertTrue(
                got is None or P.converge_pct <= got <= P.halt_pct - 1.0, (pct, minutes))
            if (pct + 1, minutes) in grid:
                self.assertGreaterEqual(_lvl(grid[(pct + 1, minutes)]), _lvl(got), (pct, minutes))
            if (pct, minutes - 5) in grid:  # 剩餘分鐘減少＝時間流逝
                self.assertLessEqual(_lvl(grid[(pct, minutes - 5)]), _lvl(got), (pct, minutes))

    def test_at_qp_08_shrinking_burst_or_step_never_loosens(self):
        """方向鎖：調小一定更緊；方向反了＝可調旋鈕成了放寬後門。"""
        chain = ((20.0, 10.0), (10.0, 5.0), (0.0, 1.0))
        for pct in range(0, 101, 3):
            for minutes in range(0, 301, 15):
                seen = [_lvl(_floor(pct, minutes, pace_burst_pp=b, pace_step_pp=s))
                        for b, s in chain]
                self.assertEqual(seen, sorted(seen), (pct, minutes))

    def test_at_qp_09_window_is_normalised_not_hardcoded(self):
        """窗長歸一化；若寫死 300，非五小時窗軸（如日窗）會錯。"""
        self.assertEqual(_floor(35, 540, 600.0), 70.0)
        self.assertEqual(_floor(35, 270, 300.0), 70.0)
        self.assertIsNone(_floor(35, 540, 3000.0))  # 同一組 pct／分鐘在更長窗上沒超線

    def test_at_qp_10_contradictory_data_takes_the_conservative_side(self):
        """minutes > window 時 elapsed 夾 0（lead＝pct）；用負 elapsed 會得到放寬的錯誤答案。"""
        self.assertEqual(_floor(25, 400), 70.0)

    def test_at_qp_11_pure_function_ignores_environment(self):
        """純函式不讀環境；環境只能經 `Policy` 進場。"""
        with mock.patch.dict(os.environ, {"AUTOSDD_QUOTA_PACE_BURST_PP": "0"}):
            a = _floor(38, 247)
        with mock.patch.dict(os.environ, {}, clear=True):
            b = _floor(38, 247)
        self.assertEqual(a, b)


class EvaluateApplyTest(unittest.TestCase):
    """AT-QP-12～21：`evaluate()`／`apply()`。"""

    FIVE = (("five_hour", 38, 247), ("session", 38, 247), ("weekly_all", 60, 8000))

    def test_at_qp_12_both_short_axes_lift_and_weekly_untouched(self):
        """AC-1 軸級形態；少了 `max` 或套錯軸會立刻現形。"""
        rows, floors = _eval(self.FIVE)
        self.assertEqual([f.state for f in floors], ["lifted", "lifted", "n/a"])
        self.assertEqual([f.level for f in floors[:2]], [70.0, 70.0])
        base = _resolved(rows)
        out = PF.apply(base, floors)
        self.assertEqual([o[0] for o in out[:2]], [70.0, 70.0])
        self.assertIn(PF.NOTE_PACE, out[0][3])
        self.assertEqual(out[2], base[2])

    def test_at_qp_13_rush_returns_the_exact_original(self):
        """免套用①：若趕工只「壓低」不「還原」，輸出會差一格；要求 tuple 逐位元相等。"""
        policy = dataclasses.replace(P, pace_rush_until=NOW.timestamp() + 3600)
        rows, floors = _eval(self.FIVE, policy)
        self.assertEqual([f.state for f in floors[:2]], [PF.STATE_RUSH, PF.STATE_RUSH])
        base = _resolved(rows)
        self.assertEqual(PF.apply(base, floors), base)

    def test_at_qp_14_weekly_reset_inside_this_window_exempts_strictly(self):
        """免套用②與嚴格小於的邊界；寫成 `<=` 會讓「週軸剛好同時結束」也免套用。"""
        for weekly_min, want in ((100, "exempt-weekly-reset"), (247, "lifted"), (248, "lifted")):
            with self.subTest(weekly_min=weekly_min):
                rows, floors = _eval((("five_hour", 38, 247), ("weekly_all", 60, weekly_min)))
                self.assertEqual(floors[0].state, want)
                if want != "lifted":
                    self.assertEqual(PF.apply(_resolved(rows), floors), _resolved(rows))

    def test_at_qp_15_malformed_input_is_unknown_and_never_raises(self):
        """免套用③＋畸形輸入 fail-open；拋例外會讓整條 gate 變故障源。"""
        for rows in ((("five_hour", 38, None, "ok"),), (("five_hour", "x", _at(247), "ok"),)):
            with self.subTest(rows=rows):
                floors = PF.evaluate(rows, _deltas(rows), P, NOW)
                self.assertEqual(floors[0].state, "unknown")
                base = ((38.0, "none", None, ""),)
                self.assertEqual(PF.apply(base, floors), base)

    def test_at_qp_16_burndown_hold_exempts(self):
        """免套用④：床不得與清倉授權相抗；少了它床會把使用者明示要用盡的額度又擋回去。"""
        rows, floors = _eval(self.FIVE, hold=(True, False, False))
        self.assertEqual(floors[0].state, "exempt-hold")
        self.assertEqual(floors[1].state, "lifted")  # 遮罩逐軸，不連坐
        base = _resolved(rows)
        self.assertEqual(PF.apply(base, floors)[0], base[0])

    def test_at_qp_17_only_the_shortest_window_axes_are_floored(self):
        """只作用最短窗軸（X24）；套到週軸會與週用滿目標直接衝突。"""
        _rows_, floors = _eval((("five_hour", 40, 200), ("weekly_all", 90, 8000),
                                ("seven_day", 90, 8000)))
        self.assertEqual([f.state for f in floors], ["within", "n/a", "n/a"])

    def test_at_qp_17b_weekly_only_state_has_no_short_window(self):
        """只剩週軸時（session 無鄰軸可繼承窗長）不得對週軸套床（SHORT_WINDOW_MAX_MINUTES）；
        拿掉上界，既有 S4-3（session 61@13.5＋weekly 57@8233）會被床抬到 prepare。"""
        _rows_, floors = _eval((("session", 61, 13.5), ("weekly_all", 57, 8233)))
        self.assertEqual({f.state for f in floors}, {"n/a"})

    def test_at_qp_17c_short_window_ceiling_includes_exactly_1440_minutes(self):
        """窗長恰 1440 分仍算短窗（套床）、1441 分起不算；上界取「含等號」，邊界不釘就能
        被偷偷改成 `>=` 而把整個日窗軸排除在床外。"""
        for kind, state in (("1440_minute", "lifted"), ("1441_minute", "n/a")):
            with self.subTest(kind=kind):
                _r, floors = _eval(((kind, 85, 1000),))
                self.assertEqual(floors[0].state, state)

    def test_at_qp_18_masked_axis_is_neither_short_nor_long(self):
        """遮罩軸不得影響本模型的床（與攤提同尺，DEF-200-438 的同型）。"""
        specs = (("five_hour", 38, 247), ("weekly_all", 60, 8000), ("weekly_scoped", 50, 100))
        _r, masked = _eval(specs, skip=(False, False, True))
        self.assertEqual(masked[0].state, "lifted")
        _r, unmasked = _eval(specs)
        self.assertEqual(unmasked[0].state, "exempt-weekly-reset")  # 對照：不遮就免套用

    def test_at_qp_19_same_window_axes_are_computed_separately(self):
        """同窗長的多軸要逐軸算；只算第一軸會漏另一軸。
        （TCS 原數字 40／60@200 算不出 70／85：40@200 在允許線內。改用 55／70@200，見交卷檔。）"""
        _r, floors = _eval((("session", 55, 200), ("five_hour", 70, 200)))
        self.assertEqual([(f.state, f.level) for f in floors],
                         [("lifted", 70.0), ("lifted", 85.0)])

    def test_at_qp_20_apply_is_max_not_overwrite(self):
        """`max` 不是覆寫：覆寫會把更高的攤提水位壓回 70，變成放寬。"""
        rows = _rows(("five_hour", 38, 247), ("weekly_all", 80, 8000))
        base = _resolved(rows, ratio=1.0)
        self.assertGreater(base[0][0], 90.0)  # 前提：攤提已把 five_hour 抬到 prepare 以上
        floors = PF.evaluate(rows, _deltas(rows), P, NOW)
        self.assertEqual(floors[0].level, 70.0)
        out = PF.apply(base, floors)
        self.assertEqual(out[0][0], base[0][0])
        self.assertNotIn(PF.NOTE_PACE, out[0][3])

    def test_at_qp_21_note_only_when_it_really_lifted(self):
        """note 只在「真的抬了」時出現；否則 M-P4 的「床擋過」近似會被稀釋。"""
        rows = _rows(("five_hour", 90, 230))
        floors = PF.evaluate(rows, _deltas(rows), P, NOW)
        self.assertEqual((floors[0].state, floors[0].level), ("lifted", 85.0))
        base = _resolved(rows)
        out = PF.apply(base, floors)
        self.assertEqual(out[0][0], 90.0)
        self.assertNotIn(PF.NOTE_PACE, out[0][3])

    def test_rush_validity_boundaries(self):
        """AT-QP-31 的純函式半：到期與上限皆嚴格不等式（`<=`／`<` 寫錯一格即紅）。"""
        ts = NOW.timestamp()
        for delta, want in ((18000, True), (18001, False), (0, False), (-1, False), (1, True)):
            with self.subTest(delta=delta):
                policy = dataclasses.replace(P, pace_rush_until=ts + delta)
                self.assertIs(PF.rush_active(policy, NOW), want)
        self.assertIs(PF.rush_active(P, NOW), False)


class LineTest(unittest.TestCase):
    """AT-QP-22～24：說明行。"""

    def _f(self, state, **kw):
        base = dict(kind="five_hour", pct=38.0, minutes=247.0, window=300.0, allowed_pp=37.7,
                    over_pp=0.3, level=None, state=state)
        base.update(kw)
        return PF.PaceFloor(**base)

    def test_at_qp_22_every_state_names_its_reason_and_has_no_percent_sign(self):
        """畫面必須一行內回答「為什麼空著也不能衝」與「為什麼這次放行」（M7）。"""
        want = {"lifted": ("允許線", "超線", "水位至少抬到"), "within": ("未超線",),
                "exempt-rush": ("趕工戳記",), "exempt-weekly-reset": ("先 reset",),
                "exempt-hold": ("清倉",), "unknown": ("不明",)}
        for state, parts in want.items():
            with self.subTest(state=state):
                text = PF.line((self._f(state, level=70.0 if state == "lifted" else None),))
                self.assertTrue(text.startswith("  配速床："), text)
                self.assertIn("kind=five_hour", text)
                self.assertIn("247 分鐘", text)
                self.assertIn("pp", text)
                self.assertNotIn("%", text)
                for part in parts:
                    self.assertIn(part, text)

    def test_at_qp_23_no_shortest_axis_prints_nothing(self):
        """沒有最短窗軸時不得印一句空話（訊息混一句假話比少一欄更難看見）。"""
        self.assertEqual(PF.line(()), "")
        self.assertEqual(PF.line((self._f("n/a"),)), "")
        self.assertEqual(PF.line(None), "")

    def test_at_qp_24_one_line_per_shortest_axis(self):
        """逐軸說明；合併成一行會把不同水位說成同一個數。"""
        text = PF.line((self._f("within", kind="session"), self._f("within")))
        lines = text.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("kind=session", lines[0])
        self.assertIn("kind=five_hour", lines[1])


class StaticShapeTest(unittest.TestCase):
    """AT-QP-66／67：Python 3.9 相容與零 I/O。"""

    SRC = (_REPO / "tools" / "lib" / "quota_pace_floor.py").read_text(encoding="utf-8")

    def test_at_qp_66_python39_loadable_constructs_only(self):
        """POSIX hook 載具常是 3.9：`match`、執行期 `A|B`、`slots=`、`zip(strict=)` 一出現，
        `quota_gate` 的 hard import 就炸、整條額度軸零訊息短路。"""
        tree = ast.parse(self.SRC)
        in_annotation = set()  # `from __future__ import annotations` 下標註不在執行期求值
        for node in ast.walk(tree):
            for field in ("annotation", "returns"):
                ann = getattr(node, field, None)
                if ann is not None:
                    in_annotation.update(id(n) for n in ast.walk(ann))
        for node in ast.walk(tree):
            self.assertNotIsInstance(node, ast.Match)
            if isinstance(node, ast.Call):
                names = {kw.arg for kw in node.keywords}
                self.assertFalse({"slots", "kw_only", "strict"} & names, ast.dump(node)[:80])
            if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr)
                    and id(node) not in in_annotation):
                self.fail("執行期 A|B（3.10+）")

    def test_at_qp_67_no_io_no_clock_no_environment(self):
        """零 I/O、零時鐘：寫戳記與痕跡的呼叫只准出現在 `quota_rush.py`。"""
        tree = ast.parse(self.SRC)
        banned_attr = {"write_text", "read_text", "environ", "getenv", "now", "utcnow", "open"}
        seen = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "open":
                seen.add("open")
            elif isinstance(node, ast.Attribute):
                seen.add(node.attr)
        self.assertEqual(banned_attr & seen, set())


if __name__ == "__main__":
    unittest.main()
