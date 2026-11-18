#!/usr/bin/env python3
"""`tools/lib/sessionctl/costmodel.py` 的驗收測試（TCS-SessionSwitch-CostModel-20261118
REQ-SS-01／02／17、AT-SS-01／06／07、MU-01～03／20）。

守的判準（WHY 全文＝docs/02_architecture/SessionSwitch_CostModel_Design.md §3／§4.4／§11）：
- 掌舵者 2026-11-18「專注在不要讓 Cache 過期」：換 session 只剩兩條路——快取**已冷**之後按帳選路
  （F4）、上下文到硬線。本檔釘 F4 的不等式與邊界、參數壞值退出廠值、硬線小於 autocompact 點；
- 依裁決（D-1＝不設軟線、D-2＝hold 不實作）軟線 `T_soft`、`B`、`N_lo`、hold 一律不存在——
  有人把它們加回來，本檔的反向斷言會紅。
縫：ENV mapping 參數；不讀真實 ~/.claude、不起排程。
"""
from __future__ import annotations

import contextlib
import io
import math
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

import quota_policy_env  # noqa: E402

from lib.sessionctl import costmodel, keepwarm, switch  # noqa: E402

F, Q = costmodel.FRESH_COST_KEY, costmodel.VALUE_Q_KEY


class FactoryTest(unittest.TestCase):
    def test_factory_values_and_sources(self) -> None:
        """AT-SS-01：出廠 F＝480,000（實測中位 480,734 取整）、q＝1.0；臨界上下文＝480,000。
        WHY：F4 的邊界數字是整個換窗政策的核心，漂移一格就改變誰被換新。"""
        self.assertEqual(costmodel.fresh_cost({}), 480_000)
        self.assertEqual(costmodel.value_q({}), 1.0)
        self.assertEqual(costmodel.fresh_total({}), 960_000)
        self.assertEqual(costmodel.fresh_ctx_threshold({}), 480_000)

    def test_weights_agree_with_keepwarm_and_the_census_units(self) -> None:
        """加權單位在 keepwarm 與本檔各一份（keepwarm 本棒不動）：兩處必須相等，否則 F1（保溫）與
        F4（換窗）用兩套價目表、同一個上下文的帳對不上。MU-01：把主控重寫誤寫成 5m 層 1.25 必紅。"""
        self.assertEqual((costmodel.W_CR, costmodel.W_CC1), (keepwarm.W_CR, keepwarm.W_CC1))
        self.assertEqual((costmodel.W_CR, costmodel.W_CC1, costmodel.W_CC5), (0.1, 2.0, 1.25))

    def test_env_spec_declares_the_keys_with_the_same_defaults(self) -> None:
        """出廠值只有 ENV_SPEC 一個家：本檔讀它、不寫第二份數字。"""
        got = {s.name: s.default for s in quota_policy_env.ENV_SPEC}
        self.assertEqual(got[F], 480_000)
        self.assertEqual(got[Q], 1.0)

    def test_no_soft_line_and_no_hold_exist(self) -> None:
        """依裁決（D-1＝③、D-2）：沒有軟線函式、沒有 `B`／`N_lo` 參數、sessionctl 沒有 hold 模組。
        WHY：掌舵者「Context 的容量本來就很大，25 萬就切換是自我閹割」——軟線被悄悄加回來，
        人在 25～85 萬之間又會被推著換窗。"""
        for name in ("t_soft", "soft_line", "n_lo", "B"):
            self.assertFalse(hasattr(costmodel, name), name)
        self.assertFalse((_REPO / "tools" / "lib" / "sessionctl" / "hold.py").exists())
        names = {s.name for s in quota_policy_env.ENV_SPEC}
        for key in ("AUTOSDD_SWITCH_FRESH_CTX_TOKENS", "AUTOSDD_SWITCH_MIN_REMAINING_TURNS"):
            self.assertNotIn(key, names, key)


class F4Test(unittest.TestCase):
    def test_boundary_equal_does_not_switch_one_more_does(self) -> None:
        """AT-SS-01／MU-03：冷、c=480,000 ⇒ 不換（相等）；480,001 ⇒ 換。WHY：嚴格大於——相等時兩邊
        一樣貴，保留上下文較有價值。寫成 `>=` 或把 `(1+q)` 漏乘（臨界腰斬成 240,000）都必紅。"""
        self.assertFalse(costmodel.fresh_is_cheaper(480_000, cold=True, env={}))
        self.assertTrue(costmodel.fresh_is_cheaper(480_001, cold=True, env={}))
        self.assertFalse(costmodel.fresh_is_cheaper(240_001, cold=True, env={}),
                         "漏乘 (1+q) 的突變")

    def test_a_warm_cache_never_switches_however_big(self) -> None:
        """MU-20：快取仍熱 ⇒ 一律不換（讀價 0.1c 必小於 F；F4 只在『已經冷了』之後才有意義）。"""
        for c in (1, 480_001, 5_000_000):
            self.assertFalse(costmodel.fresh_is_cheaper(c, cold=False, env={}), c)

    def test_unmeasured_context_never_switches(self) -> None:
        """量不到（None／0／負）⇒ 不換：FRESH 的代價是丟上下文，量不到不該單方面造成資訊損失。"""
        for c in (None, 0, -5):
            self.assertFalse(costmodel.fresh_is_cheaper(c, cold=True, env={}), c)

    def test_value_q_moves_the_threshold_as_designed(self) -> None:
        """AT-SS-06：q=0／1／2 ⇒ 臨界 240,000／480,000／720,000。q=0＝只看 token 成本（換得更勤）、
        q 越大越重視上下文（換得更少）；方向反了就是把掌舵者的偏好倒過來。"""
        for q, expect in ((0, 240_000), (1, 480_000), (2, 720_000)):
            with self.subTest(q=q):
                env = {Q: str(q)}
                self.assertEqual(costmodel.fresh_ctx_threshold(env), expect)
                self.assertFalse(costmodel.fresh_is_cheaper(expect, cold=True, env=env))
                self.assertTrue(costmodel.fresh_is_cheaper(expect + 1, cold=True, env=env))

    def test_fresh_cost_override_scales_the_threshold(self) -> None:
        """F 加倍 ⇒ 臨界加倍（接手越貴越不該換）；F 腰斬 ⇒ 臨界腰斬。"""
        self.assertEqual(costmodel.fresh_ctx_threshold({F: "960000"}), 960_000)
        self.assertEqual(costmodel.fresh_ctx_threshold({F: "240000"}), 240_000)

    def test_f4_applies_strictly_below_the_hard_line(self) -> None:
        """F4 臨界（480,000）必須低於硬線（850,000）：否則快取冷了之後 F4 永遠輪不到、硬線搶先，
        『按帳選路』就成了空話。"""
        hard = int(switch._factory(switch.HARD_CTX_KEY))
        self.assertLess(costmodel.fresh_ctx_threshold({}), hard)

    def test_reason_text_carries_the_numbers(self) -> None:
        """命中理由要讓人看懂為什麼：續跑重寫單位、換新單位、臨界各一個數字。"""
        text = costmodel.f4_reason(600_000, {})
        for needle in ("F4", "1,200,000", "960,000", "600,000", "480,000"):
            self.assertIn(needle, text)


class BadValueTest(unittest.TestCase):
    def test_pathological_values_fall_back_and_say_so_never_raise(self) -> None:
        """AT-SS-07：負數、非數字、NaN、inf、空字串 ⇒ 退出廠值；有給值的壞值 stderr 出聲一次，
        空字串＝未設，靜默。WHY：這些參數在 hook 與無人續跑路徑上，沒有人看 stderr、不能拋。"""
        cases = ((F, "-5", 480_000, True), (F, "abc", 480_000, True), (F, "0", 480_000, True),
                 (F, "nan", 480_000, True), (F, "inf", 480_000, True), (F, "", 480_000, False),
                 (Q, "-1", 1.0, True), (Q, "abc", 1.0, True), (Q, "nan", 1.0, True),
                 (Q, "inf", 1.0, True), (Q, "", 1.0, False))
        for key, raw, expect, loud in cases:
            with self.subTest(key=key, raw=raw), contextlib.redirect_stderr(io.StringIO()) as err:
                got = (costmodel.fresh_cost if key == F else costmodel.value_q)({key: raw})
                self.assertEqual(got, expect)
                self.assertEqual(bool(err.getvalue()), loud, err.getvalue())

    def test_zero_q_is_valid_but_zero_cost_is_not(self) -> None:
        """q=0 是合法值（純 token 成本）；F=0 不合法（會讓任何非零上下文都『換新較便宜』）。"""
        self.assertEqual(costmodel.value_q({Q: "0"}), 0.0)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(costmodel.fresh_cost({F: "0"}), 480_000)

    def test_returned_values_are_always_finite(self) -> None:
        for raw in ("nan", "inf", "-inf", "1e999"):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertTrue(math.isfinite(costmodel.value_q({Q: raw})), raw)
                self.assertTrue(math.isfinite(costmodel.fresh_cost({F: raw})), raw)


class HardLineInvariantTest(unittest.TestCase):
    def test_hard_line_is_850k_and_strictly_below_the_observed_autocompact_point(self) -> None:
        """設計 §4.4 不變式：HARD < 觀測到的流程內 autocompact 最小點（881,938）。WHY：autocompact
        一次把上下文砍到 1～2 萬，比交接包更失真；硬線若不在它之前，『主動交棒』就來不及。
        量測值重量後若 autocompact 點下降，本測試先紅，逼人下修硬線而不是放著。"""
        hard = int(switch._factory(switch.HARD_CTX_KEY))
        self.assertEqual(hard, 850_000)
        self.assertLess(hard, costmodel.OBSERVED_AUTOCOMPACT_MIN)
        self.assertEqual(costmodel.OBSERVED_AUTOCOMPACT_MIN, 881_938)

    def test_hard_line_cannot_be_raised_past_the_autocompact_point_by_env(self) -> None:
        """方向鎖：env 只准下修；設成 autocompact 點以上一律退出廠值並出聲。"""
        for raw in ("881938", "900000", "5000000"):
            with self.subTest(raw), contextlib.redirect_stderr(io.StringIO()):
                got = switch.threshold(switch.HARD_CTX_KEY, {switch.HARD_CTX_KEY: raw})[0]
                self.assertEqual(got, 850_000)


if __name__ == "__main__":
    unittest.main()
