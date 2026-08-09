"""`tools/lib/quota_policy.py` 的機械物（R82 HELM-04 規格 M1~M10）。

每一支都帶**合成注入紅綠自證**：注入錯誤形態必須被判準抓到（紅），正確形態必須
放行（綠）。只斷言「今天的實作是綠的」不算機械物——本 repo 分群實測「鎖存在但沒有
鑑別力」曾是最大的一桶。

🔴 **本檔的射程只到判讀層本身**（接線是第二步，由持有 hook／meter／adapter 的包做）。
以下四個半條在本包**結構上驗不到**，已逐條標明，不得被讀成「已驗證」：
  · M8 的「adapter 讀得到 /2 快取」——adapter 與 meter 兩支檔本包一行都不准動；
    本檔只交付**純文字判準** ＋ 對現存兩支檔的「兩邊 SCHEMA 必須相等」比對。
  · M9 的端到端半（`quota_gate` 連呼 21 次）——`quota_gate` 住 hook，本包不動 hook。
  · M10 的 spy 半（`quota_gate` 必須恰好呼叫 `decide` 一次）——同上。
  · ✅ **M5 靜態半的三個掃描面已於 R82／C4 全數轉成硬 gate**（見
    `TestM5EveryScanSurfaceIsGatedHard`）。此處原本記載「本包只 gate 得動第一個、
    其餘兩面留待下一階段」——那段劃界在當時是誠實的，但它被留在原地整整一輪，
    期間複審鏡以沙箱注入實測**五組全綠**（worst() 放回 gate／meter、fanout_cap(pct)
    放回 gate 與 AutoClaude adapter、quota_tier_of(pct) 放回 hook）。
    現在四個面逐檔硬判，並附「注入真檔內容後必須翻紅」的端到端自證。
本檔另外釘住**本層**可釘的那一半：`Decision` 的建構點必須唯一（＝`decide`），
讓「hook 裡再長出第二條自己推導 band/cap 的路徑」在接線時就沒有可抄的樣板。

執行：python -m unittest test_quota_policy -v   （cwd＝tools/tests）
"""
from __future__ import annotations

import ast
import random
import re
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "tools" / "lib"))
import quota_policy as Q  # noqa: E402

_MODULE_SRC = (_REPO / "tools" / "lib" / "quota_policy.py").read_text(encoding="utf-8")

#: 固定時刻（aware）。刻意不用 `datetime.now()`——判準不得隨掛鐘漂移。
NOW = datetime(2026, 8, 9, 5, 15, 3, tzinfo=UTC)
P = Q.DEFAULT_POLICY

_INF = float("inf")


def at(minutes: float | None) -> str | None:
    """把「幾分鐘後 reset」寫成**伺服器形態的原字串**（帶 offset，不轉本地）。"""
    if minutes is None:
        return None
    return (NOW + timedelta(minutes=minutes)).isoformat()


def axis(kind: str, pct: float, minutes: float | None, **kw) -> Q.Axis:
    return Q.Axis(kind=kind, pct=pct, resets_at=at(minutes), **kw)


def state(*specs, reason: str = "ok", source: str = "endpoint") -> Q.QuotaState:
    axes = tuple(axis(k, p, m) for k, p, m in specs)
    return Q.QuotaState(axes=axes, measured_at=NOW.isoformat(),
                        source=source, reason=reason)


def cap_num(cap: int | None) -> float:
    """`None`（不設限）視為 +∞，才能與整數 cap 比大小。"""
    return _INF if cap is None else float(cap)


# ═══════════════════════════════════════════════════════════════════════════
# 決策表：規格 S4 的 15 列，直接當參數表用
# ═══════════════════════════════════════════════════════════════════════════
#: `(標籤, state, 期望 cap, 期望 rec, 期望 binding.kind, 語意)`
_TABLE = [
    ("S4-1 不緊的長期程軸不得吃掉加速",
     state(("session", 0, 30), ("weekly_all", 20, 8640)), None, 16, "weekly_all"),
    ("S4-2 加速真的看得到（單軸）",
     state(("session", 0, 30)), None, 16, "session"),
    ("S4-3 今天的實測活值",
     state(("session", 61, 13.5), ("weekly_all", 57, 8233)), 4, 4, "weekly_all"),
    ("S4-4 79%@3min",
     state(("session", 79, 3)), 8, 4, "session"),
    ("S4-5 79%@240min",
     state(("session", 79, 240)), 4, 2, "session"),
    ("S4-6 79%@6d",
     state(("session", 79, 8640)), 2, 1, "session"),
    ("S4-7 A：短期程高水位",
     state(("session", 90, 34), ("weekly_all", 20, 8640)), 2, 1, "session"),
    ("S4-8 B：長期程高水位",
     state(("session", 10, 34), ("weekly_all", 90, 8640)), 1, 1, "weekly_all"),
    ("S4-9 55%@6d（50 錨點生效）",
     state(("session", 55, 8640)), 4, 2, "session"),
    ("S4-10 75%@6d（70 錨點生效）",
     state(("session", 75, 8640)), 2, 1, "session"),
    ("S4-11 96% halt 絕對",
     state(("session", 96, 20), ("weekly_all", 20, 8640)), 0, 0, "session"),
    ("S4-12 任一軸 halt 即全域 halt",
     state(("session", 10, 20), ("weekly_all", 96, 8640)), 0, 0, "weekly_all"),
    ("S4-13 spend 88%（無 reset）",
     state(("spend", 88, None)), 1, 1, "spend"),
    ("S4-14 時鐘偏移（強制不加速）",
     state(("session", 0, -5)), None, 8, "session"),
    ("S4-15 量不到＝degraded，不是不設限",
     Q.QuotaState(axes=(), measured_at=NOW.isoformat(), source="cache",
                  reason="stale-cache"), 4, 4, None),
]


class TestDecisionTable(unittest.TestCase):
    """規格 S4 的 15 列逐列釘住（parametrized；一列一個 subTest）。"""

    def test_every_row_of_the_spec_table(self) -> None:
        for label, st, want_cap, want_rec, want_binding in _TABLE:
            with self.subTest(row=label):
                d = Q.decide(st, NOW, P)
                got_binding = d.binding.kind if d.binding else None
                self.assertEqual(d.cap, want_cap, f"{label}: cap")
                self.assertEqual(d.recommended_fanout, want_rec, f"{label}: rec")
                self.assertEqual(got_binding, want_binding, f"{label}: binding")

    def test_the_two_anchors_the_helm_asked_for_now_exist(self) -> None:
        """實測坐實今天 `pct=55` 與 `pct=75` 都回 `normal/None` ⇒ 兩錨點不存在。"""
        self.assertEqual(Q.pct_band(55, P), Q.BAND_NOTICE)
        self.assertEqual(Q.pct_band(75, P), Q.BAND_CONVERGE)
        self.assertNotEqual(Q.axis_cap(55, 8640, P), Q.axis_cap(75, 8640, P))

    def test_band_boundaries_on_both_sides_of_every_anchor(self) -> None:
        """0/50/70/85/95 各自的上下鄰域（`>=` 與 `>` 差一個 pp 就是整帶錯位）。"""
        cases = [
            (0.0, Q.BAND_FREE), (49.9, Q.BAND_FREE),
            (50.0, Q.BAND_NOTICE), (50.1, Q.BAND_NOTICE), (69.9, Q.BAND_NOTICE),
            (70.0, Q.BAND_CONVERGE), (84.9, Q.BAND_CONVERGE),
            (85.0, Q.BAND_PREPARE), (94.9, Q.BAND_PREPARE),
            (95.0, Q.BAND_HALT), (100.0, Q.BAND_HALT),
        ]
        for pct, want in cases:
            with self.subTest(pct=pct):
                self.assertEqual(Q.pct_band(pct, P), want)

    def test_horizon_boundaries_on_both_sides(self) -> None:
        """30／360 兩條線的鄰域；`None` 自成一檔。"""
        cases = [
            (0.0, Q.AXIS_NEAR), (30.0, Q.AXIS_NEAR), (30.1, Q.AXIS_MID),
            (360.0, Q.AXIS_MID), (360.1, Q.AXIS_FAR), (None, Q.AXIS_NONE),
        ]
        for minutes, want in cases:
            with self.subTest(minutes=minutes):
                self.assertEqual(Q.horizon_band(minutes, P), want)


class TestTheTableIsProducedByTheRuleNotByHand(unittest.TestCase):
    """🔴 上表每一列都必須從**寫下來的聚合規則**重算得到，而不是手挑的數字。

    規則（見 `quota_policy` 檔頭「兩個角色分開聚合」）：
      cap = min(逐軸 cap)                                    ← 煞車
      rec = min( clamp(min(逐軸 base_rec) × pace) , cap )     ← 加速，pace 取最短期程
    本測試**不呼叫 `decide()`**，而是照上式獨立重算一次——同一顆星有兩條互不相干的
    算法對得上，才排除得掉「表是照著實作抄的」。

    🔴 聚合規則改寫後，規格 S4 參數表有**兩列**與交件時的判定不同，照實記：
      · 第 3 列：表寫 rec=4。舊的 `min(逐軸 rec)` 算出 2 ⇒ 當時被判成「抄寫失誤」；
        新規則算出 **4** ⇒ **表原本就是對的**，那筆失誤是舊聚合造成的假象。
      · 第 1 列：表寫 8、它自己的語意欄寫「被 weekly 的 8×0.5=4 壓下來」、舊式子算
        出 4——三個數字互不相同。新規則算出 **16**：weekly 20% 落在 free 帶、根本
        不是約束，而 session 30 分鐘後就 reset ⇒ 這正是使用者原句要的「多派」。
      其餘 13 列（cap／rec／binding 三欄）與規格表逐字相同。
    """

    def test_every_row_follows_from_the_documented_rule(self) -> None:
        for label, st, want_cap, want_rec, _ in _TABLE:
            if not st.axes:
                continue
            with self.subTest(row=label):
                readings = Q.axes_of(st, NOW, P)
                cap = min(cap_num(r.cap) for r in readings)
                base = min(Q._base_rec(r.band, P) for r in readings)
                rec = Q._bound(Q._clamp(int(base * Q._pace_of(readings)), P),
                               None if cap == _INF else int(cap))
                self.assertEqual(cap, cap_num(want_cap), f"{label}: cap")
                self.assertEqual(rec, want_rec, f"{label}: rec")

    def test_every_axis_recommendation_stays_under_its_own_cap(self) -> None:
        """逐軸也必須 `rec <= cap`——否則跨軸那一層是在替單軸的矛盾擦屁股。"""
        for _label, st, *_ in _TABLE:
            for r in Q.axes_of(st, NOW, P):
                with self.subTest(kind=r.axis.kind, band=r.band):
                    self.assertLessEqual(float(r.recommended), cap_num(r.cap))


# ═══════════════════════════════════════════════════════════════════════════
# M1 兩個相反情境必須得到不同且**方向正確**的 cap（本案頭號鎖）
# ═══════════════════════════════════════════════════════════════════════════
_A = state(("session", 90, 34), ("weekly_all", 20, 8640))   # 短期程高水位
_B = state(("session", 10, 34), ("weekly_all", 90, 8640))   # 長期程高水位


def m1_problems(cap_of) -> list[str]:
    """判準本體：`cap(A)` 必須**嚴格大於** `cap(B)`。

    🔴 刻意**不**斷言「binding 不同／reset 分支不同／訊息不同」——規格實測那三條
    今天就是綠的（A→kind=session branch=arm、B→kind=weekly_all branch=notify），
    寫進去就是零鑑別力的鎖。
    """
    a, b = cap_num(cap_of(_A)), cap_num(cap_of(_B))
    if a <= b:
        return [f"cap(A)={a} 未嚴格大於 cap(B)={b}：短期程與長期程被壓成同一件事"]
    return []


def _worst_cap(st: Q.QuotaState) -> int | None:
    """注入形態＝shipped 的 `worst()`：只看 max(pct)，horizon 一律當 mid。"""
    worst = max(a.pct for a in st.axes)
    return Q._cap_for(Q.pct_band(worst, P), Q.AXIS_MID, P)


class TestM1OppositeScenariosDiverge(unittest.TestCase):
    def test_green_the_real_implementation_passes(self) -> None:
        self.assertEqual(m1_problems(lambda s: Q.decide(s, NOW, P).cap), [])

    def test_red_the_shipped_scalar_version_fails(self) -> None:
        """注入：換回 `max(pct)` 單軸版 ⇒ A 與 B 皆 cap=2 ⇒ 判準必紅。"""
        self.assertEqual(_worst_cap(_A), _worst_cap(_B))
        self.assertTrue(m1_problems(_worst_cap), "注入了缺陷卻沒轉紅＝零鑑別力")

    def test_regression_pin_todays_live_reading(self) -> None:
        """迴歸釘（**非鑑別力來源**）：今天的實測活值 ＋ session 那一列必須在。"""
        d = Q.decide(state(("session", 61, 13.5), ("weekly_all", 57, 8233)), NOW, P)
        self.assertEqual(d.cap, 4)
        self.assertEqual(d.binding.kind, "weekly_all")
        kinds = [r.axis.kind for r in d.per_axis]
        self.assertIn("session", kinds, "session 那一列在消費端不得結構性缺席")

    def test_is_active_is_never_used_to_pick_a_bucket(self) -> None:
        """五次觀測 `is_active` 都等於 argmax，但五次一致不構成契約。

        把 `is_active` 掛到**低水位**那一軸上，決策必須一個位元都不變——否則
        就是把 `worst()` 換個寫法再犯一次。
        """
        plain = state(("session", 10, 34), ("weekly_all", 90, 8640))
        flagged = Q.QuotaState(
            axes=(axis("session", 10, 34, is_active=True),
                  axis("weekly_all", 90, 8640, is_active=False)),
            measured_at=NOW.isoformat(), source="endpoint")
        d1, d2 = Q.decide(plain, NOW, P), Q.decide(flagged, NOW, P)
        self.assertEqual((d1.cap, d1.recommended_fanout, d1.binding.kind),
                         (d2.cap, d2.recommended_fanout, d2.binding.kind))

    def test_group_is_never_used_to_classify(self) -> None:
        """四個 top-level 桶實測**一個 `group` 欄都沒有** ⇒ group 只能當標籤。"""
        without = Q.decide(state(("five_hour", 79, 3)), NOW, P)
        with_group = Q.decide(Q.QuotaState(
            axes=(axis("five_hour", 79, 3, group="weekly"),),
            measured_at=NOW.isoformat(), source="endpoint"), NOW, P)
        self.assertEqual(without.cap, with_group.cap)
        self.assertEqual(without.band, with_group.band)


# ═══════════════════════════════════════════════════════════════════════════
# M1b 加速訊號必須**穿過 `decide()`**，不是只穿 `axis_cap()`（R82 複驗鏡 ①）
# ═══════════════════════════════════════════════════════════════════════════
# 🔴 這一節的存在理由是一個被鎖結構性放行的缺口：M2 的每一條判準都只穿 `axis_cap()`，
# 而 S4 表第 4/5/6 列全是**單軸** fixture ⇒ 「跨軸聚合把加速吃掉」在整份機械物裡
# 一次都沒有被觀測到。複驗鏡實測：固定 weekly_all 57%@8233min、把 session 的 reset
# 從 1 分鐘掃到 6 天（**差 8640 倍**），`decide()` 的 cap/rec/band **逐格相同**
# （4/2/notice）；使用者錨點①「0%+30m ⇒ 多派」在多軸下相異 rec 只有一個值，而且
# 比中性基準（8）更小 ⇒ 方向相反。
#: 掃描點刻意跨過 30／360 兩條 horizon 線的兩側（1 分鐘 ~ 6 天）。
_SWEEP_MINUTES = (1, 5, 15, 30, 31, 120, 360, 361, 1000, 8640)


def m1b_problems(decide_fn, other: tuple, pct: float = 0.0) -> list[str]:
    """固定一條長期程軸，掃短期程軸的 reset 距離：`rec` 必須**動**且方向正確。"""
    recs = [decide_fn(state(("session", pct, m), other)).recommended_fanout
            for m in _SWEEP_MINUTES]
    problems = []
    if len(set(recs)) < 2:
        problems.append(
            f"8640 倍的期程掃描下 rec 只有一個值 {sorted(set(recs))}"
            "：多軸下加速結構上不可觀測（＝本案要治的病原封不動）")
    if any(b > a for a, b in zip(recs, recs[1:], strict=False)):
        problems.append(f"方向錯：reset 愈遠 rec 反而愈大 {recs}")
    if recs[0] <= recs[-1]:
        problems.append(f"最近端 {recs[0]} 未嚴格大於最遠端 {recs[-1]}")
    return problems


#: 今天的實測活值（binding 恆為 weekly）／一條不緊的長期程軸（binding 會換手）。
_TIGHT_WEEKLY = ("weekly_all", 57, 8233)
_LOOSE_WEEKLY = ("weekly_all", 20, 8640)


def _min_min_decide(st: Q.QuotaState) -> Q.Decision:
    """注入形態＝**舊聚合**：cap 與 rec 都取 `min(逐軸)`。這就是被抓到的那個實作。"""
    readings = Q.axes_of(st, NOW, P)
    binding = min(readings, key=Q._binding_key)
    return Q.Decision(binding.cap, min(r.recommended for r in readings),
                      binding.band, binding.axis, readings, "injected")


class TestM1bAccelerationSurvivesAggregation(unittest.TestCase):
    def test_green_the_real_decide_passes_on_both_weeklies(self) -> None:
        for label, other in (("tight", _TIGHT_WEEKLY), ("loose", _LOOSE_WEEKLY)):
            with self.subTest(weekly=label):
                self.assertEqual(
                    m1b_problems(lambda s: Q.decide(s, NOW, P), other), [])

    def test_red_the_min_min_aggregation_swallows_the_signal(self) -> None:
        """注入：舊聚合 ⇒ 兩組掃描都只剩一個 rec 值 ⇒ 判準必紅。"""
        for label, other in (("tight", _TIGHT_WEEKLY), ("loose", _LOOSE_WEEKLY)):
            with self.subTest(weekly=label):
                problems = m1b_problems(_min_min_decide, other)
                self.assertTrue(problems, "注入舊聚合卻沒轉紅＝零鑑別力")
                self.assertIn("只有一個值", problems[0])

    def test_the_helm_anchor_survives_a_second_axis(self) -> None:
        """使用者原句「Token 剩 30Min 就 Reset、還有 100% 沒用 ⇒ 加速」。

        加一條**不緊**的長期程軸之後必須仍然成立，而且不得低於中性基準（8）——
        複驗鏡量到的正是「多軸下 rec=4，方向與中性基準相反」。
        """
        solo = Q.decide(state(("session", 0, 30)), NOW, P)
        paired = Q.decide(state(("session", 0, 30), _LOOSE_WEEKLY), NOW, P)
        self.assertEqual((solo.recommended_fanout, paired.recommended_fanout),
                         (16, 16))
        self.assertGreater(paired.recommended_fanout, P.cap_notice)
        self.assertEqual(_min_min_decide(
            state(("session", 0, 30), _LOOSE_WEEKLY)).recommended_fanout, 4)

    def test_the_hard_cap_still_moves_with_the_short_axis(self) -> None:
        """cap 那一半也要看得見期程：session 90% 在 near/mid/far 三檔 ⇒ 4/2/1。"""
        caps = [Q.decide(state(("session", 90, m), _TIGHT_WEEKLY), NOW, P).cap
                for m in (3, 240, 8640)]
        self.assertEqual(caps, [4, 2, 1])

    def test_a_tighter_axis_still_wins_the_hard_cap(self) -> None:
        """反向鑑別力：加速**不得**穿過煞車。weekly 撞線 ⇒ 兩者皆 0，掃描全平。"""
        halting = ("weekly_all", 96, 8640)
        for m in _SWEEP_MINUTES:
            with self.subTest(minutes=m):
                d = Q.decide(state(("session", 0, m), halting), NOW, P)
                self.assertEqual((d.cap, d.recommended_fanout), (0, 0))

    def test_the_pace_never_exceeds_the_binding_cap(self) -> None:
        """`rec <= cap` 是加速那一半的安全條件，掃描全域都必須成立。"""
        for pct in (0, 20, 55, 79, 90, 96):
            for m in _SWEEP_MINUTES:
                for other in (_TIGHT_WEEKLY, _LOOSE_WEEKLY):
                    d = Q.decide(state(("session", pct, m), other), NOW, P)
                    with self.subTest(pct=pct, minutes=m, other=other[1]):
                        self.assertLessEqual(
                            float(d.recommended_fanout), cap_num(d.cap))

    def test_an_axis_with_no_horizon_blocks_acceleration(self) -> None:
        """fail-closed：任一軸不知道何時 reset ⇒ pace 夾在 1.0，不得加速。"""
        with_none = Q.decide(
            state(("session", 0, 5), ("spend", 0, None)), NOW, P)
        without = Q.decide(state(("session", 0, 5), ("spend", 0, 8640)), NOW, P)
        self.assertEqual(with_none.recommended_fanout, 8)
        self.assertEqual(without.recommended_fanout, 16)


# ═══════════════════════════════════════════════════════════════════════════
# M2 reset 距離必須真的影響輸出（6b 的存在性證明）
# ═══════════════════════════════════════════════════════════════════════════
def m2_problems(cap_fn, rec_fn) -> list[str]:
    """固定 pct=79，cap 必須隨 reset 變遠而**非遞增**，且近端嚴格大於中段。"""
    problems = []
    near, mid, far = cap_fn(79, 3), cap_fn(79, 240), cap_fn(79, 8640)
    if not (cap_num(near) > cap_num(mid) > cap_num(far)):
        problems.append(f"79% 的 cap 未隨期程遞減：{near}/{mid}/{far}")
    seq = [cap_num(cap_fn(79, m)) for m in range(1, 20000, 37)]
    if any(b > a for a, b in zip(seq, seq[1:], strict=False)):
        problems.append("cap 隨 minutes 增大而變寬（方向掃描失敗）")
    # 反向鑑別力：free 帶的 cap 恆為 None，差別只出現在建議值上
    if cap_fn(20, 3) is not None or cap_fn(20, 240) is not None:
        problems.append("free 帶的 cap 不該被設限")
    if rec_fn(20, 3) <= rec_fn(20, 240):
        problems.append("free 帶的『加速』沒有出口（rec 必須隨 reset 逼近而變大）")
    return problems


class TestM2HorizonActuallyMoves(unittest.TestCase):
    def test_green_the_real_implementation_passes(self) -> None:
        self.assertEqual(
            m2_problems(lambda pct, m: Q.axis_cap(pct, m, P),
                        lambda pct, m: Q.axis_recommended(pct, m, P)), [])

    def test_the_three_horizons_are_three_different_caps(self) -> None:
        """規格 M2 的定點：8 / 4 / 2。今天實測三者皆 `tier=normal cap=None`。"""
        self.assertEqual(
            [Q.axis_cap(79, 3, P), Q.axis_cap(79, 240, P), Q.axis_cap(79, 8640, P)],
            [8, 4, 2])

    def test_red_when_the_minutes_parameter_is_ignored(self) -> None:
        """注入：`axis_cap` 無視 `minutes`（＝今天 shipped 的形態）⇒ 必紅。"""
        problems = m2_problems(lambda pct, _m: Q.axis_cap(pct, 240, P),
                               lambda pct, _m: Q.axis_recommended(pct, 240, P))
        self.assertTrue(problems, "無視 minutes 卻沒轉紅＝零鑑別力")

    def test_red_when_the_direction_is_inverted(self) -> None:
        """注入：方向寫反（reset 愈遠愈寬）⇒ 方向掃描必紅。"""
        inverted = {Q.AXIS_NEAR: 0.5, Q.AXIS_MID: 1.0,
                    Q.AXIS_FAR: 2.0, Q.AXIS_NONE: 2.0}
        self.assertTrue(
            m2_problems(lambda pct, m: _mult_cap(pct, m, inverted),
                        lambda pct, m: Q.axis_recommended(pct, m, P)))


def _mult_cap(pct: float, minutes: float | None, table: dict) -> int | None:
    """以自訂乘數表重算 cap（只給注入用；不進 production 路徑）。"""
    band = Q.pct_band(pct, P)
    if band == Q.BAND_HALT:
        return 0
    base = Q._base_cap(band, P)
    if base is None:
        return None
    return Q._clamp(int(base * table[Q.horizon_band(minutes, P)]), P)


# ═══════════════════════════════════════════════════════════════════════════
# M3 加入更緊的軸永不放寬（`min` 而非 `max`）＋ halt 絕對
# ═══════════════════════════════════════════════════════════════════════════
def m3_problems(aggregate) -> list[str]:
    """property：對任意軸集合 A 與任一新軸 x，`cap(A+[x]) <= cap(A)`。"""
    problems = []
    rng = random.Random(20260809)

    def rand_axis(name: str) -> tuple[str, float, float | None]:
        return (name, rng.uniform(0, 100),
                rng.choice([None, rng.uniform(0, 20000)]))

    for _ in range(400):
        base = [rand_axis(f"k{i}") for i in range(rng.randint(1, 4))]
        extra = rand_axis("x")
        before = cap_num(aggregate(state(*base)))
        after = cap_num(aggregate(state(*base, extra)))
        if after > before:
            problems.append(f"加入 {extra} 後 cap 由 {before} 放寬為 {after}")
            break
    return problems


def _min_aggregate(st: Q.QuotaState) -> int | None:
    return Q.decide(st, NOW, P).cap


def _max_aggregate(st: Q.QuotaState) -> int | None:
    """注入形態：跨軸取**最寬**的那一格。"""
    readings = Q.axes_of(st, NOW, P)
    return max(readings, key=Q._binding_key).cap


class TestM3TighterAxisNeverLoosens(unittest.TestCase):
    def test_green_min_aggregation_passes(self) -> None:
        self.assertEqual(m3_problems(_min_aggregate), [])

    def test_red_max_aggregation_fails(self) -> None:
        self.assertTrue(m3_problems(_max_aggregate), "聚合寫成 max 卻沒轉紅")

    def test_a_halt_axis_swallows_an_accelerating_one(self) -> None:
        """定點：`[session 0%@30min]`（cap None、rec 16）＋ `[weekly 96%@6d]` ⇒ 0。"""
        solo = Q.decide(state(("session", 0, 30)), NOW, P)
        self.assertEqual((solo.cap, solo.recommended_fanout), (None, 16))
        both = Q.decide(state(("session", 0, 30), ("weekly_all", 96, 8640)), NOW, P)
        self.assertEqual((both.cap, both.recommended_fanout), (0, 0))

    def test_halt_does_not_eat_the_env_override(self) -> None:
        """`AUTOSDD_QUOTA_FANOUT_CAP=99` 之下，96% 那一軸仍必須 `cap==0`。"""
        policy, problems = Q.load_policy({"AUTOSDD_QUOTA_FANOUT_CAP": "99"})
        self.assertEqual(problems, [])
        self.assertEqual(policy.fanout_cap_override, 99)
        d = Q.decide(state(("session", 96, 20)), NOW, policy)
        self.assertEqual(d.cap, 0)
        self.assertEqual(d.recommended_fanout, 0)

    def test_the_override_does_reach_the_throttle_bands(self) -> None:
        """鑑別力反證：覆寫必須對**節流帶**真的有效（否則是「設了沒生效」）。"""
        policy, _ = Q.load_policy({"AUTOSDD_QUOTA_FANOUT_CAP": "1"})
        self.assertEqual(Q.decide(state(("session", 79, 240)), NOW, policy).cap, 1)
        self.assertEqual(Q.decide(state(("session", 79, 240)), NOW, P).cap, 4)


# ═══════════════════════════════════════════════════════════════════════════
# M3b 三個純實作缺陷（R82 複驗鏡 ②）：覆寫被放大／rec > cap／負值防線是死碼
# ═══════════════════════════════════════════════════════════════════════════
def _override_as_multiplicand(pct: float, minutes: float | None,
                              override: int) -> int | None:
    """注入形態＝舊寫法：把覆寫值當成 base 丟進 horizon 乘法。"""
    band = Q.pct_band(pct, P)
    if band == Q.BAND_HALT:
        return 0
    if Q._base_cap(band, P) is None:
        return None
    return Q._clamp(int(override * Q._MULTIPLIER[Q.horizon_band(minutes, P)]), P)


def rec_over_cap_problems(cap_fn, rec_fn) -> list[str]:
    """`rec > cap` ＝自相矛盾的建議（「建議派 4 個」而「上限只准 2 個」）。"""
    problems = []
    for pct in (0, 20, 55, 61, 79, 88, 90, 96):
        for minutes in (1, 30, 240, 8640, None):
            cap, rec = cap_fn(pct, minutes), rec_fn(pct, minutes)
            if cap is not None and rec > cap:
                problems.append(f"pct={pct} minutes={minutes}: rec={rec} > cap={cap}")
    return problems


def _horizon_without_negative_guard(minutes: float | None, p: Q.Policy) -> str:
    """注入形態＝把 `horizon_band` 的負值分支當死碼刪掉。"""
    if minutes is None:
        return Q.AXIS_NONE
    if minutes <= p.accel_window_minutes:
        return Q.AXIS_NEAR
    if minutes <= p.far_horizon_minutes:
        return Q.AXIS_MID
    return Q.AXIS_FAR


class TestM3bImplementationDefects(unittest.TestCase):
    def test_the_override_is_a_ceiling_not_a_multiplicand(self) -> None:
        """`AUTOSDD_QUOTA_FANOUT_CAP=8` 在任何 horizon 下都不得產出 >8 的 cap。

        舊寫法把覆寫值當 base 丟進乘法 ⇒ near 檔實得 **16**：一個名字叫 CAP 的旋鈕
        給出比使用者要求**更鬆**的值，而且不出聲。
        """
        policy, problems = Q.load_policy({"AUTOSDD_QUOTA_FANOUT_CAP": "8"})
        self.assertEqual(problems, [])
        for pct in (55, 79, 90):
            for minutes in (3, 240, 8640, None):
                with self.subTest(pct=pct, minutes=minutes):
                    self.assertLessEqual(Q.axis_cap(pct, minutes, policy), 8)
        self.assertEqual(_override_as_multiplicand(79, 3, 8), 16)  # 注入版必紅

    def test_the_override_only_tightens_never_loosens(self) -> None:
        """把覆寫調大不得放寬（它是上限）；調小必須真的生效。"""
        loose, _ = Q.load_policy({"AUTOSDD_QUOTA_FANOUT_CAP": "99"})
        tight, _ = Q.load_policy({"AUTOSDD_QUOTA_FANOUT_CAP": "1"})
        self.assertEqual(Q.axis_cap(79, 3, loose), Q.axis_cap(79, 3, P))
        self.assertEqual(Q.axis_cap(79, 3, tight), 1)

    def test_green_recommendation_never_exceeds_the_cap(self) -> None:
        for label, env in (("預設", {}), ("覆寫 1", {"AUTOSDD_QUOTA_FANOUT_CAP": "1"}),
                           ("覆寫 3", {"AUTOSDD_QUOTA_FANOUT_CAP": "3"})):
            policy, _ = Q.load_policy(env)
            with self.subTest(policy=label):
                self.assertEqual(rec_over_cap_problems(
                    lambda pct, m: Q.axis_cap(pct, m, policy),
                    lambda pct, m: Q.axis_recommended(pct, m, policy)), [])

    def test_red_an_unbounded_recommendation_is_caught(self) -> None:
        """注入＝舊實作（rec 不看 cap）＋覆寫 1 ⇒ 79%@3min 得 rec=4 > cap=1。"""
        policy, _ = Q.load_policy({"AUTOSDD_QUOTA_FANOUT_CAP": "1"})
        unbounded = lambda pct, m: Q._clamp(  # noqa: E731
            int(Q._base_rec(Q.pct_band(pct, policy), policy)
                * Q._MULTIPLIER[Q.horizon_band(m, policy)]), policy)
        problems = rec_over_cap_problems(
            lambda pct, m: Q.axis_cap(pct, m, policy), unbounded)
        self.assertTrue(problems, "rec 超過 cap 卻沒轉紅＝零鑑別力")

    def test_the_negative_horizon_guard_is_live_not_dead_code(self) -> None:
        """時鐘偏移的負號必須**真的走進** `horizon_band`，那道防線才不是死碼。

        舊實作在 `_delta_minutes` 就把負值夾成 0、另在 `axes_of` 用一個 if 強制
        mid ⇒ `horizon_band` 的負值分支任何生產路徑都到不了（刪掉它零測試會紅），
        而「偏移不得加速」變成同一份知識的第二個家。
        """
        past = (NOW - timedelta(minutes=5)).isoformat()
        raw, note = Q._delta_minutes(past, NOW)
        self.assertLess(raw, 0.0, "負號沒有傳到 horizon_band ⇒ 那道防線是死碼")
        self.assertEqual(note, Q.NOTE_SKEW)
        self.assertEqual(Q.horizon_band(raw, P), Q.AXIS_MID)
        self.assertEqual(_horizon_without_negative_guard(raw, P), Q.AXIS_NEAR)
        st = Q.QuotaState(axes=(Q.Axis(kind="session", pct=0.0, resets_at=past),),
                          measured_at=NOW.isoformat(), source="endpoint")
        self.assertEqual(Q.axes_of(st, NOW, P)[0].horizon, Q.AXIS_MID)


# ═══════════════════════════════════════════════════════════════════════════
# M3c 單調性不變式：任何合法設定下，pct 愈高 cap 必須單調不增（R82 複驗鏡 ③）
# ═══════════════════════════════════════════════════════════════════════════
def cap_monotonicity_problems(policy: Q.Policy) -> list[str]:
    """獨立於實作的判準：直接掃 pct 0~100，逐 horizon 檢查 cap／rec 非遞增。

    刻意**不呼叫** `Q.policy_monotonicity_problems`（那是被判的對象；用它來判自己
    等於沒判）。這一支掃的是連續水位，模組那一支只取樣帶邊界——兩者對得上才排除
    「取樣點剛好避開違規」。
    """
    problems = []
    for minutes in (3, 240, 8640, None):
        caps = [cap_num(Q.axis_cap(pct / 2.0, minutes, policy)) for pct in range(0, 201)]
        recs = [float(Q.axis_recommended(pct / 2.0, minutes, policy))
                for pct in range(0, 201)]
        for label, seq in (("cap", caps), ("rec", recs)):
            problems += [
                f"minutes={minutes} 的 {label}：pct={i / 2.0} 得 {a}，"
                f"pct={(i + 1) / 2.0} 反而得 {b}（水位愈高愈鬆）"
                for i, (a, b) in enumerate(zip(seq, seq[1:], strict=False)) if b > a]
    return problems


class TestM3cHigherUsageNeverLoosensTheCap(unittest.TestCase):
    def test_green_the_shipped_defaults_are_monotone(self) -> None:
        self.assertEqual(cap_monotonicity_problems(P), [])
        self.assertEqual(Q.policy_monotonicity_problems(P), [])

    def test_red_a_bumped_prepare_cap_is_caught_by_both_criteria(self) -> None:
        """複驗鏡實測可走的那條路：`CAP_PREPARE=16` ⇒ 90% 得 16、60% 得 8。"""
        broken = Q.Policy(cap_prepare=16)
        self.assertEqual(Q.axis_cap(90, 240, broken), 16)
        self.assertEqual(Q.axis_cap(60, 240, broken), 8)
        self.assertTrue(cap_monotonicity_problems(broken))
        self.assertTrue(Q.policy_monotonicity_problems(broken))

    def test_load_policy_refuses_the_setting_instead_of_taking_it_silently(self) -> None:
        """🔴 舊行為：`problems=[]`（每個值都在自己區間內，區間檢查看不到關係）。"""
        policy, problems = Q.load_policy({"AUTOSDD_QUOTA_CAP_PREPARE": "16"})
        self.assertTrue(problems, "水位愈高愈鬆的設定被靜默接受")
        self.assertTrue(any("非單調" in x for x in problems), problems)
        self.assertEqual(policy, Q.DEFAULT_POLICY, "壞設定必須整組退回預設")
        self.assertEqual(Q.axis_cap(90, 240, policy), 2)

    def test_a_legal_tightening_of_the_same_knob_still_works(self) -> None:
        """鑑別力反證：合法的收緊（prepare 1 < converge 4）必須放行。"""
        policy, problems = Q.load_policy({"AUTOSDD_QUOTA_CAP_PREPARE": "1"})
        self.assertEqual(problems, [])
        self.assertEqual(policy.cap_prepare, 1)
        self.assertEqual(cap_monotonicity_problems(policy), [])

    def test_a_broken_percentage_falls_closed_not_open(self) -> None:
        """`pct=NaN` 舊行為＝`band=free／cap=None／rec=16`＝全場最寬鬆的一格。"""
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(pct=bad):
                self.assertEqual(Q.pct_band(bad, P), Q.BAND_PREPARE)
                self.assertEqual(Q.axis_cap(bad, 240, P), 2)
        st = Q.QuotaState(
            axes=(Q.Axis(kind="session", pct=float("nan"), resets_at=at(240)),),
            measured_at=NOW.isoformat(), source="endpoint")
        d = Q.decide(st, NOW, P)
        self.assertEqual((d.band, d.cap, d.recommended_fanout),
                         (Q.BAND_PREPARE, 2, 1))
        self.assertIn(Q.NOTE_BAD_PCT, d.reason, "壞水位不得靜默")
        self.assertIn(Q.NOTE_BAD_PCT, Q.describe(d))

    def test_an_out_of_range_percentage_is_clamped_and_reported(self) -> None:
        """越界水位夾回 [0,100] 並出聲；150% 仍必須落 halt（不得因夾而放寬）。"""
        self.assertEqual(Q.pct_band(150, P), Q.BAND_HALT)
        self.assertEqual(Q.pct_band(-5, P), Q.BAND_FREE)
        self.assertEqual(Q._sane_pct(150)[1], Q.NOTE_BAD_PCT)
        self.assertEqual(Q._sane_pct(61.0), (61.0, Q.NOTE_OK))


# ═══════════════════════════════════════════════════════════════════════════
# M4 加速的三道 fail-closed（`None` / 猜出來的時刻 / 時鐘偏移）
# ═══════════════════════════════════════════════════════════════════════════
def m4_problems(resolve_horizon) -> list[str]:
    """`resolve_horizon(axis) -> horizon`。三種輸入都**不得**落進 near。"""
    problems = []
    if resolve_horizon(axis("spend", 88, None)) != Q.AXIS_NONE:
        problems.append("`resets_at` 缺席時沒有落進 none 檔")
    skewed = Q.Axis(kind="session", pct=0.0,
                    resets_at=(NOW - timedelta(minutes=5)).isoformat())
    if resolve_horizon(skewed) == Q.AXIS_NEAR:
        problems.append("時鐘偏移被當成『reset 就在眼前』⇒ 偏移可以把預算調高")
    if resolve_horizon(Q.Axis(kind="x", pct=0.0, resets_at="not-a-time")) == Q.AXIS_NEAR:
        problems.append("解不出的 `resets_at` 被當成可加速的證據")
    return problems


def _real_horizon(a: Q.Axis) -> str:
    st = Q.QuotaState(axes=(a,), measured_at=NOW.isoformat(), source="endpoint")
    return Q.axes_of(st, NOW, P)[0].horizon


def _naive_horizon(a: Q.Axis) -> str:
    """注入形態：把負值 `max(0, …)` 夾完就直接餵 `horizon_band`。"""
    minutes, _note = Q._delta_minutes(a.resets_at, NOW)
    return Q.horizon_band(max(0.0, minutes) if minutes is not None else 0.0, P)


class TestM4AccelerationFailsClosed(unittest.TestCase):
    def test_green_the_real_resolver_passes(self) -> None:
        self.assertEqual(m4_problems(_real_horizon), [])

    def test_red_the_naive_clamp_falls_into_near(self) -> None:
        """`max(0, …)` 之後餵 `horizon_band` ⇒ 偏移與缺席都會落 near ⇒ 必紅。"""
        problems = m4_problems(_naive_horizon)
        self.assertTrue(problems)
        self.assertGreaterEqual(len(problems), 2, problems)

    def test_missing_horizon_only_slows_down(self) -> None:
        """M4-①：`axis_cap(88, None) == 1`（＝2×0.5），**不是** 2×2。"""
        self.assertEqual(Q.horizon_band(None, P), Q.AXIS_NONE)
        self.assertEqual(Q.axis_cap(88, None, P), 1)

    def test_minutes_cannot_be_injected_from_outside_the_contract(self) -> None:
        """M4-②：`resets_at=None` 的軸，走正規路徑必定落 none 檔。

        呼叫端就算自己算出一個 `minutes=5`，`axes_of` 也只認 `axis.resets_at`。
        """
        st = Q.QuotaState(axes=(axis("spend", 88, None),),
                          measured_at=NOW.isoformat(), source="endpoint")
        reading = Q.axes_of(st, NOW, P)[0]
        self.assertIsNone(reading.minutes)
        self.assertEqual(reading.horizon, Q.AXIS_NONE)
        self.assertEqual(reading.note, Q.NOTE_MISSING)
        self.assertEqual(Q.axis_cap(88, 5, P), 4)   # 硬塞 5 分鐘會得到完全不同的答案

    def test_clock_skew_is_zero_minutes_but_forced_mid(self) -> None:
        """M4-③：偏移 ⇒ `minutes==0.0`、`note=clock-skew`、檔位**強制 mid**。"""
        past = (NOW - timedelta(minutes=5)).isoformat()
        self.assertEqual(Q.minutes_to_reset(past, NOW), 0.0)
        st = Q.QuotaState(axes=(Q.Axis(kind="session", pct=0.0, resets_at=past),),
                          measured_at=NOW.isoformat(), source="endpoint")
        reading = Q.axes_of(st, NOW, P)[0]
        self.assertEqual((reading.minutes, reading.note, reading.horizon),
                         (0.0, Q.NOTE_SKEW, Q.AXIS_MID))

    def test_missing_and_unparseable_are_different_notes(self) -> None:
        """缺席（正常）與格式變了（伺服器改了）**必須分得開**；今天共用 `None`。"""
        self.assertEqual(Q._delta_minutes(None, NOW), (None, Q.NOTE_MISSING))
        self.assertEqual(Q._delta_minutes("", NOW), (None, Q.NOTE_MISSING))
        self.assertEqual(Q._delta_minutes("2026-13-99", NOW)[1], Q.NOTE_BAD)
        self.assertEqual(Q._delta_minutes("2026-08-09T05:20:00", NOW)[1], Q.NOTE_BAD)

    def test_a_naive_now_is_refused_loudly(self) -> None:
        """naive `now` 相減跨 DST 實測差 3600 秒且完全靜默 ⇒ 一律拒收。"""
        with self.assertRaises(ValueError):
            Q._delta_minutes(at(30), datetime(2026, 8, 9, 5, 15, 3))

    def test_resets_at_is_persisted_verbatim(self) -> None:
        """伺服器原字串原封不動：不轉本地、不重新格式化。"""
        raw = "2026-08-14T22:00:00.249193+00:00"
        a = Q.Axis(kind="weekly_all", pct=58.0, resets_at=raw)
        self.assertEqual(a.resets_at, raw)
        self.assertEqual(Q.decide(
            Q.QuotaState(axes=(a,), measured_at=NOW.isoformat(), source="endpoint"),
            NOW, P).binding.resets_at, raw)


# ═══════════════════════════════════════════════════════════════════════════
# M5 決策不得由任何單一純量驅動（`worst()` 的墓碑 ＋ 純量簽章禁令）
# ═══════════════════════════════════════════════════════════════════════════
#: 決策詞。🔴 規格原表另有 `band`／`budget`——**刻意移除**：規格自己的 `pct_band(pct, p)`
#: 是二元決策合法的前半，把它判紅就是 15 筆假紅裡的第一筆，而那種鎖活不過一輪。
_DECISION_WORDS = ("cap", "tier", "fanout", "throttle", "halt", "gate", "decide")
_SCALAR_PARAMS = ("pct", "percent", "utilization")
#: 🔴 第二軸的證據。規格原文只寫「參數名含 pct 且註記為 float/int」——照抄會把
#: 規格自己宣告的 `axis_cap(pct: float, minutes: float | None, p: Policy)` 判紅。
#: 真正要禁的是「**只**由一個純量決策」，所以判準多一個合取項：沒有任何期程輸入。
#:
#: 🔴 R82 複驗鏡實測的**三條洗白路徑**（此前 `now`／`state` 也在這張表裡）：
#:   · 加一個 `now: datetime` ⇒ 判準放行。但 `now` 不帶任何 reset 時刻，
#:     「現在幾點」單獨存在時對 horizon 零資訊 ⇒ 它從來就不是第二軸的證據。
#:   · 加一個 `state` ⇒ 判準放行。吃 `QuotaState` 的函式根本不需要 `pct` 參數，
#:     兩者同時出現正是「表面上收了狀態、實際上還是照純量決策」的形狀。
#:   · 寫成 `async def` ⇒ `ast.FunctionDef` 比對整片失明（見下方 walk 的型別）。
#: 三條都不是假想：M5-④ 要埋的 `fanout_cap(pct)` 就住在下一階段要接線的
#: `tools/lib/quota_gate.py`，任何一條都能讓它靜默逃出射程。
_HORIZON_PARAMS = ("minutes", "horizon", "resets", "deadline", "remaining", "until")
_FUNC_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def _is_number_annotation(node) -> bool:
    return node is not None and any(
        tok in ast.unparse(node) for tok in ("float", "int"))


def scalar_decision_defs(source: str) -> list[str]:
    """列出「只吃一個純量水位就做決策」的函式（M5 靜態半 ④）。"""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, _FUNC_NODES):
            continue
        if not any(w in node.name.lower() for w in _DECISION_WORDS):
            continue
        args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
        names = [a.arg.lower() for a in args]
        if any(h in n for n in names for h in _HORIZON_PARAMS):
            continue
        if any(any(s in a.arg.lower() for s in _SCALAR_PARAMS)
               and _is_number_annotation(a.annotation) for a in args):
            found.append(node.name)
    return found


def worst_mentions(source: str) -> list[str]:
    """`worst()` 的墓碑：**定義與呼叫兩邊都算**（只認 `def worst` 會漏掉呼叫端）。"""
    hits = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, _FUNC_NODES) and node.name == "worst":
            hits.append("def worst")
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "")
            if name == "worst":
                hits.append("call worst()")
    return hits


def scalar_escape_problems(cls) -> list[str]:
    """執行期半：型別上**不得**存在任何無參數的取值出口。

    🔴 判準必須走 `__mro__` 的 `__dict__`，**不能**用 `getattr`：`object` 自己就帶
    `__lt__`／`__gt__`（回 `NotImplemented` 的預設實作），`getattr` 版對**任何**
    類別都回非 None ⇒ 那是一支恆紅、因而必然被刪掉的鎖。本註解是實測得來的：
    第一版正是 `getattr`，跑出來 `Axis` 自己就被判了兩筆違規。
    """
    problems = []
    owners = [k for k in cls.__mro__ if k is not object]
    for dunder in ("__float__", "__int__", "__index__", "__lt__", "__gt__"):
        if any(dunder in k.__dict__ for k in owners):
            problems.append(f"{cls.__name__} 定義了 {dunder} ⇒ 不指名軸別就拿得到數字")
    return problems


class TestM5NoSingleScalarDrivesDecisions(unittest.TestCase):
    def test_green_the_module_itself_is_clean(self) -> None:
        self.assertEqual(scalar_decision_defs(_MODULE_SRC), [])
        self.assertEqual(worst_mentions(_MODULE_SRC), [])

    def test_red_the_shipped_signatures_are_caught(self) -> None:
        """注入：貼回 `fanout_cap(pct)` 與 `quota_tier_of(pct)` ⇒ 兩支都必須被抓。"""
        injected = (
            "def fanout_cap(pct: float | None) -> int | None:\n    return 2\n"
            "def quota_tier_of(pct: float) -> str:\n    return 'normal'\n")
        self.assertEqual(sorted(scalar_decision_defs(injected)),
                         ["fanout_cap", "quota_tier_of"])

    def test_green_a_display_helper_is_not_caught(self) -> None:
        """鑑別力反證：顯示用的 `format_pct` 必須放行，否則只是在抓 `pct` 這個字。"""
        harmless = ("def format_pct(pct: float) -> str:\n    return f'{pct}%'\n"
                    "def pct_band(pct: float, p: object) -> str:\n    return 'free'\n")
        self.assertEqual(scalar_decision_defs(harmless), [])

    def test_green_the_two_axis_signature_is_not_caught(self) -> None:
        """規格自己的 `axis_cap(pct, minutes, p)` 必須綠——否則判準把正解判成違規。"""
        good = ("def axis_cap(pct: float, minutes: float | None, p: object):\n"
                "    return 1\n")
        self.assertEqual(scalar_decision_defs(good), [])

    def test_red_none_of_the_three_whitewash_paths_works(self) -> None:
        """🔴 三條洗白路徑逐條注入：加 `now`／加 `state`／寫成 `async def`。

        每一條都是「換個寫法就出射程」，而失明的表徵是**恆綠**——掃描器照跑、
        照回報 0 命中，只是那一族從此不在分母裡。
        """
        for label, injected in (
            ("加 now", "def fanout_cap(pct: float | None, now: datetime) -> int:\n"
                       "    return 2\n"),
            ("加 state", "def fanout_cap(pct: float | None, state: object) -> int:\n"
                        "    return 2\n"),
            ("async def", "async def fanout_cap(pct: float | None) -> int:\n"
                          "    return 2\n"),
            ("三條一起", "async def fanout_cap(pct: float, now: object,\n"
                          "                    state: object) -> int:\n"
                          "    return 2\n"),
        ):
            with self.subTest(whitewash=label):
                self.assertEqual(scalar_decision_defs(injected), ["fanout_cap"])

    def test_green_a_real_state_consumer_has_no_scalar_parameter(self) -> None:
        """鑑別力反證：真的吃狀態的函式**不會**有 `pct` 參數 ⇒ 一開始就不在射程內。"""
        real = ("def decide(state: object, now: object, p: object) -> object:\n"
                "    return state\n")
        self.assertEqual(scalar_decision_defs(real), [])

    def test_the_tombstone_catches_call_sites_not_only_definitions(self) -> None:
        """判準自證：只認 `def worst` 會漏掉「別處定義、這裡呼叫」的版本。"""
        call_only = "top = worst(readings)\npct = top['pct']\n"
        self.assertEqual(worst_mentions(call_only), ["call worst()"])
        self.assertEqual(worst_mentions("def worst(rs):\n    return rs[0]\n"),
                         ["def worst"])

    def test_axis_has_no_scalar_escape_hatch(self) -> None:
        self.assertEqual(scalar_escape_problems(Q.Axis), [])
        with self.assertRaises(TypeError):
            float(axis("session", 61, 13.5))
        with self.assertRaises(TypeError):
            _ = axis("session", 61, 13.5) < axis("weekly_all", 57, 8233)

    def test_red_a_subclass_that_adds_float_is_caught(self) -> None:
        """注入：在 `Axis` 上加 `__float__` ⇒ 執行期半必紅。"""
        class Leaky(Q.Axis):
            def __float__(self) -> float:
                return self.pct

        self.assertTrue(scalar_escape_problems(Leaky))

    def test_quota_state_has_no_pct(self) -> None:
        st = state(("session", 61, 13.5), ("weekly_all", 57, 8233))
        self.assertIsNone(getattr(st, "pct", None))
        with self.assertRaises(AttributeError):
            _ = st.pct   # type: ignore[attr-defined]
        self.assertTrue(st.usable())


# ── M5 靜態半的**掃描面**（規格點名三個；本包只 gate 得動第一個，見檔頭誠實劃界）──
_M5_SCAN_SURFACES: dict[str, list[Path]] = {
    "tools/lib/quota_*.py": sorted((_REPO / "tools" / "lib").glob("quota_*.py")),
    ".claude/hooks/context_budget_guard.py":
        [_REPO / ".claude" / "hooks" / "context_budget_guard.py"],
    "AutoClaude/autoclaude/**": sorted(
        (_REPO / "AutoClaude" / "autoclaude").rglob("*quota*.py")),
}
#: 🔴 R82／C4：規格 M5-④ 點名的「活標的」常數（名字刻意不用反引號寫出來——它已經不存在，
#: 而 `TestR78GhostSymbolClaims` 會把「反引號指名一個不存在的符號」判成幽靈引用，
#: 那正是本輪 C4 在治的同一種病）已刪除。它服務的那條測試是
#: `if 定義還在: assertIn(...)`——定義被拆掉之後整條靜默沉默，**結構上不可能失敗**。
#: 取代它的是下方 `TestM5EveryScanSurfaceIsGatedHard`：逐檔硬判 ＋ 五組注入自證。


class TestM5ScanSurfaceScope(unittest.TestCase):
    """射程本身要可查：掃描面解析成空集合＝鎖靜默歸零，而那與全綠無法區分。"""

    def test_all_three_surfaces_from_the_spec_are_enumerated_and_parseable(self) -> None:
        self.assertEqual(len(_M5_SCAN_SURFACES), 3)
        for label, files in _M5_SCAN_SURFACES.items():
            with self.subTest(surface=label):
                self.assertTrue(files, f"{label} 解析成空集合＝射程靜默歸零")
                for path in files:
                    if path.is_file():   # in-flight 的包可能還沒把檔放上來
                        self.assertIsInstance(
                            scalar_decision_defs(path.read_text(encoding="utf-8")),
                            list, f"{path} 掃不動＝這一面實際上沒有被掃")

    def test_the_owned_surface_is_gated_hard(self) -> None:
        """本包擁有的那一面是硬 gate；其餘兩面見 `TestM5EveryScanSurfaceIsGatedHard`。"""
        self.assertEqual(scalar_decision_defs(_MODULE_SRC), [])
        self.assertEqual(worst_mentions(_MODULE_SRC), [])
        self.assertIn(_REPO / "tools" / "lib" / "quota_policy.py",
                      _M5_SCAN_SURFACES["tools/lib/quota_*.py"])


# 🔴 R82／C4：把「三個掃描面」從**列舉**升成**硬 gate**。
#
# 病（複審鏡以沙箱注入實測，每次跑全套）：`worst_mentions`／`scalar_decision_defs` 兩個
# 判準只對 `_MODULE_SRC`（＝`quota_policy.py` 自己）斷言，於是
#   worst() 放回 quota_gate.py → rc=0 GREEN；放回 quota_meter.py → rc=0 GREEN；
#   fanout_cap(pct) 放回 quota_gate.py → GREEN；quota_tier_of(pct) 放回 hook → GREEN；
#   fanout_cap(pct) 放進 AutoClaude adapter → GREEN。
# 五組注入全綠。`_M5_SCAN_SURFACES` 當時**列了**三個面，但那一條只 `assertIsInstance(...,
# list)`＝「解析得動」，不是「乾淨」；而那支「確認掃描器擋得住活標的」的測試（同輪一併
# 刪除，名字刻意不用反引號寫出來——它已不存在，寫成反引號就是新的幽靈引用）
# 用的是 `if 定義還在: assertIn(...)` ⇒ 定義不在就整條沉默，**結構上不可能失敗**。
# 「掃描面列出來了」與「掃描面被判了」是兩件事，前者讀起來很像後者。
#
# 現在的判準：三個面（＋ AutoClaude adapter 那一面）**每一支檔**都必須同時
# `scalar_decision_defs == []` 且 `worst_mentions == []`。今天全部為空（落地當回合實測），
# 所以這不是「登記存量」而是「不准有人放回去」。
class TestM5EveryScanSurfaceIsGatedHard(unittest.TestCase):
    def _files(self) -> list[Path]:
        return [p for files in _M5_SCAN_SURFACES.values() for p in files if p.is_file()]

    def test_the_surface_is_not_empty(self) -> None:
        """分母自證：掃到 0 支檔時「全部乾淨」與「什麼都沒掃」rc 完全相同。"""
        self.assertGreaterEqual(len(self._files()), 4, "掃描面塌成 <4 支檔＝射程靜默歸零")

    def test_no_scalar_driven_decision_anywhere_on_the_surface(self) -> None:
        for path in self._files():
            with self.subTest(file=path.name):
                self.assertEqual(
                    scalar_decision_defs(path.read_text(encoding="utf-8")), [],
                    f"{path} 出現「只吃一個純量水位就做決策」的函式 ⇒ "
                    "(pct, 距 reset 幾分鐘) 的後半在簽章層就不存在了")

    def test_the_worst_tombstone_holds_on_every_file(self) -> None:
        for path in self._files():
            with self.subTest(file=path.name):
                self.assertEqual(
                    worst_mentions(path.read_text(encoding="utf-8")), [],
                    f"{path} 又出現 worst()（定義或呼叫）⇒ 那是 R82 的墓碑")

    def test_red_all_five_injections_from_the_review_turn_red(self) -> None:
        """🔴 判準自證：複審鏡那五組注入，逐組必須被抓到。

        沒有這一條，上面兩支就只是「今天恰好是空的」——與「判準看不見任何東西」
        在 rc 上完全相同。這裡直接把注入文字餵給判準本體（不動磁碟）。
        """
        cases = {
            "worst 回到 quota_gate": ("def worst(readings):\n    return readings[0]\n",
                                      worst_mentions),
            "worst 回到 quota_meter": ("top = worst(bucket_readings(payload))\n",
                                       worst_mentions),
            "fanout_cap 回到 quota_gate": (
                "def fanout_cap(pct: float | None) -> int | None:\n    return 2\n",
                scalar_decision_defs),
            "quota_tier_of 回到 hook": (
                "def quota_tier_of(pct: float) -> str:\n    return 'normal'\n",
                scalar_decision_defs),
            "fanout_cap 進 AutoClaude adapter": (
                "class A:\n    def fanout_cap(self, pct: float) -> int:\n        return 2\n",
                scalar_decision_defs),
        }
        for label, (injected, judge) in cases.items():
            with self.subTest(injection=label):
                self.assertTrue(judge(injected), f"注入「{label}」沒有被判準抓到")

    def test_red_the_gate_really_fails_when_a_real_file_is_polluted(self) -> None:
        """端到端半：把注入**接在真檔內容後面**，本 gate 的斷言必須翻紅。

        上一條驗的是判準，這一條驗的是「判準真的套在這些檔上」——兩者是不同的失效。
        """
        for path in self._files():
            with self.subTest(file=path.name):
                polluted = path.read_text(encoding="utf-8") + (
                    "\n\ndef fanout_cap(pct: float) -> int:\n    return 2\n")
                self.assertEqual(scalar_decision_defs(polluted), ["fanout_cap"])


# ═══════════════════════════════════════════════════════════════════════════
# M6 `.env.example` ↔ 讀取點 雙向鎖
# ═══════════════════════════════════════════════════════════════════════════
class TestM6EnvExampleBidirectionalLock(unittest.TestCase):
    def test_green_the_generated_text_is_self_consistent(self) -> None:
        self.assertEqual(Q.env_example_problems(Q.render_env_example()), [])

    def test_red_a_ghost_key_is_caught(self) -> None:
        """注入①：手工加一行 `AUTOSDD_QUOTA_FOO=1` ⇒ 必紅。"""
        problems = Q.env_example_problems(
            Q.render_env_example() + "AUTOSDD_QUOTA_FOO=1\n")
        self.assertTrue(any("幽靈鍵" in x for x in problems), problems)

    def test_red_a_dropped_key_is_caught(self) -> None:
        """注入②：`ENV_SPEC` 有、範例檔沒有 ⇒ 必紅（防「讀了但沒寫進範例」）。"""
        lines = [x for x in Q.render_env_example().splitlines()
                 if not x.startswith("AUTOSDD_QUOTA_HALT_PCT=")]
        problems = Q.env_example_problems("\n".join(lines) + "\n")
        self.assertTrue(any("漏鍵" in x for x in problems), problems)

    def test_red_handwritten_drift_is_caught(self) -> None:
        """注入③：鍵集合對、但內容被手改 ⇒ 相等斷言必紅。"""
        problems = Q.env_example_problems(
            Q.render_env_example().replace("# 開始收斂", "# 隨手改的說明"))
        self.assertTrue(any("不同步" in x for x in problems), problems)

    def test_the_four_anchors_really_are_tunable(self) -> None:
        """M6-③：現存測試逐字宣告「這兩個數字是規格，不是可調參數」，與 6c 矛盾。"""
        policy, problems = Q.load_policy({"AUTOSDD_QUOTA_HALT_PCT": "88"})
        self.assertEqual(problems, [])
        self.assertEqual(policy.halt_pct, 88.0)
        self.assertEqual(Q.pct_band(89, policy), Q.BAND_HALT)
        self.assertEqual(Q.pct_band(89, P), Q.BAND_PREPARE)

    def test_non_monotonic_thresholds_fall_back_loudly(self) -> None:
        """M6-④：非單調 ⇒ problems 非空 ＋ 回傳的 Policy **等於預設**（不靜默夾）。"""
        policy, problems = Q.load_policy({"AUTOSDD_QUOTA_NOTICE_PCT": "90",
                                          "AUTOSDD_QUOTA_CONVERGE_PCT": "50"})
        self.assertTrue(problems)
        self.assertEqual(policy, Q.DEFAULT_POLICY)

    def test_an_inverted_horizon_pair_also_falls_back(self) -> None:
        """`accel >= far` 會讓 mid 檔變成空集合——同一類的靜默失效。"""
        policy, problems = Q.load_policy({"AUTOSDD_QUOTA_ACCEL_WINDOW_MINUTES": "600"})
        self.assertTrue(problems)
        self.assertEqual(policy, Q.DEFAULT_POLICY)


# ═══════════════════════════════════════════════════════════════════════════
# R82／C1：產生器 ↔ **消費者** 的 round-trip（此前整條不存在）
# ═══════════════════════════════════════════════════════════════════════════
#
# 病：`env_example_problems()` 拿 `render_env_example()` **跟自己比**，從不呼叫消費者的
# 解析器 ⇒ 兩個家互相一致、都沒對消費者測。而消費者 `quota_gate.policy_env()` 當時做的是
# `partition("=")` + `strip()`，產生器產出的卻是 `KEY=值<補白>#說明`（同一行）。
# 複審鏡實測：把 `.env.example` 原封不動複製成 `.env`，**12 個帶值的鍵全部解析失敗**、
# 全部靜默退回預設；把 `AUTOSDD_QUOTA_HALT_PCT` 改成 99.5、額度 99% ⇒ **仍 rc=2 被擋**
# （生效的是預設 95）。而使用者的標準流程就是 copy 一份再改幾個值 ⇒ 這不是邊角案例。
class TestM6TheGeneratedFileSurvivesItsOwnConsumer(unittest.TestCase):
    #: 帶值且真的會進 `Policy` 的鍵數（機械導出，不寫死——ENV_SPEC 長大時自己跟著走）。
    def _valued(self) -> list[Q.EnvVar]:
        return [s for s in Q.ENV_SPEC if s.attr is not None]

    def test_round_trip_render_parse_load_is_clean(self) -> None:
        """`load_policy(parse(render()))` 必須 `problems == []` 且等於 `DEFAULT_POLICY`。"""
        policy, problems = Q.load_policy(Q.parse_env_text(Q.render_env_example()))
        self.assertEqual(problems, [])
        self.assertEqual(policy, Q.DEFAULT_POLICY)

    def test_red_the_old_consumer_fails_on_every_valued_key(self) -> None:
        """🔴 合成注入：把「不剝行內註解」的舊消費者貼回來 ⇒ 每個帶值的鍵都必須報錯。

        這一條同時是上一條的鑑別力證明：沒有它，round-trip 在「產生器與消費者一起
        壞掉」時也會綠。
        """
        naive = {k.strip(): v.strip() for k, _, v in
                 (ln.strip().partition("=") for ln in Q.render_env_example().splitlines()
                  if ln.strip() and not ln.strip().startswith("#") and "=" in ln)}
        # (b) 半落地之後產生器已經不產行內註解 ⇒ 直接手工造一份「使用者手寫加註解」的檔。
        handwritten = "\n".join(
            f"{s.name}={Q._fmt_default(s.default)}    # 我自己的註記" for s in Q.ENV_SPEC)
        naive.update({k.strip(): v.strip() for k, _, v in
                      (ln.partition("=") for ln in handwritten.splitlines())})
        _policy, problems = Q.load_policy(naive)
        self.assertEqual(len(problems), len(self._valued()),
                         f"舊消費者應該讓 {len(self._valued())} 個帶值鍵全部失敗，實得 {problems}")

    def test_green_the_new_parser_handles_handwritten_inline_comments(self) -> None:
        """(a) 半：使用者手寫時加行內註解，值仍然解得出來、且真的生效。"""
        parsed = Q.parse_env_text(
            "AUTOSDD_QUOTA_HALT_PCT=88   # 我的帳號方案比較小\n"
            "# 整行註解不算鍵\n"
            "AUTOSDD_QUOTA_GUARD_OFF=    # 空值＝沒設\n")
        self.assertEqual(parsed["AUTOSDD_QUOTA_HALT_PCT"], "88")
        self.assertEqual(parsed["AUTOSDD_QUOTA_GUARD_OFF"], "")
        policy, problems = Q.load_policy(parsed)
        self.assertEqual(problems, [])
        self.assertEqual(policy.halt_pct, 88.0)

    def test_a_value_that_contains_a_hash_is_not_truncated(self) -> None:
        """鑑別力反證：只認「行首或空白之後的 #」⇒ 值本身帶 # 不得被剝掉。"""
        self.assertEqual(Q.parse_env_text("K=a#b\n")["K"], "a#b")
        self.assertEqual(Q.parse_env_text("K=a #b\n")["K"], "a")

    def test_the_generated_file_no_longer_carries_inline_comments(self) -> None:
        """(b) 半：鍵那一行只剩 `KEY=value`，說明在自己的一行上。"""
        for line in Q.render_env_example().splitlines():
            if line and not line.startswith("#"):
                self.assertNotIn("#", line, f"生成物又出現行內註解：{line!r}")

    def test_the_disk_copy_is_in_sync(self) -> None:
        """磁碟上那一份（進 repo 的範本）必須等於生成物——手寫＝第二個家。"""
        path = _REPO / ".env.example"
        self.assertTrue(path.is_file(), "根層 .env.example 不見了")
        self.assertEqual(Q.env_example_problems(path.read_text(encoding="utf-8")), [])

    def test_bad_values_are_reported_not_silently_clamped(self) -> None:
        """M6-⑤：`abc` ／ `-5` ／ `150` 三種壞值各一筆皆須進 problems。"""
        for raw in ("abc", "-5", "150"):
            with self.subTest(raw=raw):
                policy, problems = Q.load_policy({"AUTOSDD_QUOTA_HALT_PCT": raw})
                self.assertTrue(problems, f"{raw} 被靜默接受")
                self.assertEqual(policy.halt_pct, P.halt_pct, "壞值必須採用預設")

    def test_escape_hatches_are_listed_for_humans(self) -> None:
        """四個逃生口此前只散落在 hook 註解裡，零使用者可讀清單。"""
        names = [spec.name for spec in Q.ENV_SPEC]
        for key in ("AUTOSDD_QUOTA_GUARD_OFF", "AUTOSDD_QUOTA_FANOUT_CAP",
                    "AUTOSDD_SENTINEL_OFF", "AUTOSDD_CONTEXT_GUARD_OFF"):
            self.assertIn(key, names)

    def test_the_disk_file_matches_the_generator_once_it_lands(self) -> None:
        """接線後 `.env.example` 必須逐字等於生成物。

        🔴 誠實劃界：該檔的建立屬**第二步**（本包只准動兩支檔），今天磁碟上還沒有
        它。這裡刻意不寫 skip（skip 會被當成通過），而是「存在才判」——判準本身的
        紅綠已由上面三支注入測試自證，這一支只負責在接線落地那一刻自動長出牙齒。
        """
        path = _REPO / ".env.example"
        if path.exists():
            self.assertEqual(
                Q.env_example_problems(path.read_text(encoding="utf-8")), [])


# ═══════════════════════════════════════════════════════════════════════════
# M7 每一個印出去的百分比都必須指名桶名與剩餘分鐘
# ═══════════════════════════════════════════════════════════════════════════
_PCT_RE = re.compile(r"\d+(?:\.\d+)?%")


def m7_problems(text: str) -> list[str]:
    """**逐一個百分比**判：每個 `%` 自己前面要有 `kind=`、後面要有剩餘分鐘。

    🔴 判準由「chunk 級」改成「百分比級」（R82 複驗鏡 ⑦）。舊版先用
    `re.split(r"[；\\n　]", text)` 切段、再問「這一段裡有沒有 kind= 和 分鐘」——
    於是**只要改 `describe()` 的分隔符**（或乾脆不放分隔符），兩個桶就會落進同一段，
    第一個桶的 `kind=`／「分鐘」替第二個裸百分比背書，整段矇混過關。判準去問文字
    怎麼被切，而不是去問每個百分比自己有沒有被指名——那是把鑑別力寄放在被判者手上。

    現在的切法只依**百分比自己的位置**：一個 `%` 的「名牌區」是它與**前一個** `%`
    之間、「期程區」是它與**後一個** `%` 之間。分隔符換成什麼都不影響。
    """
    problems = []
    marks = list(_PCT_RE.finditer(text))
    for i, mark in enumerate(marks):
        before = text[marks[i - 1].end() if i else 0: mark.start()]
        after = text[mark.end(): marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        shown = text[max(0, mark.start() - 20): mark.end() + 20]
        if "kind=" not in before:
            problems.append(f"裸的百分比，沒說是哪一桶：…{shown}…")
        if "分鐘" not in after and "reset 距離不明" not in after:
            problems.append(f"沒說還剩幾分鐘：…{shown}…")
    return problems


def _chunk_level_m7_problems(text: str) -> list[str]:
    """注入形態＝**舊的 chunk 級判準**（只留作對照組，不是現行判準）。"""
    problems = []
    for chunk in re.split(r"[；\n　]", text):
        if not _PCT_RE.search(chunk):
            continue
        if "kind=" not in chunk:
            problems.append(f"裸的百分比：{chunk!r}")
        if "分鐘" not in chunk and "reset 距離不明" not in chunk:
            problems.append(f"沒說還剩幾分鐘：{chunk!r}")
    return problems


class TestM7EveryPercentNamesItsBucket(unittest.TestCase):
    def test_green_describe_passes_for_every_table_row(self) -> None:
        for label, st, *_ in _TABLE:
            with self.subTest(row=label):
                self.assertEqual(m7_problems(Q.describe(Q.decide(st, NOW, P))), [])

    def test_red_a_bare_percentage_is_caught(self) -> None:
        """注入＝掌舵者當場誤讀的**那個**形狀。"""
        self.assertTrue(m7_problems("額度 54% 了，要收斂"))

    def test_red_naming_the_bucket_but_not_the_horizon(self) -> None:
        """只補桶名不補分鐘 ⇒ 仍必紅（兩個都是 6b 的輸入）。"""
        problems = m7_problems("kind=weekly_all 54% 了，要收斂")
        self.assertEqual(len(problems), 1, problems)

    def test_both_axes_are_named_when_both_halt(self) -> None:
        """兩軸同時 halt 時訊息必須**兩軸都說**；今天只渲染 `worst()` 那一格。"""
        text = Q.describe(Q.decide(
            state(("session", 96, 20), ("weekly_all", 97, 8640)), NOW, P))
        self.assertIn("kind=session", text)
        self.assertIn("kind=weekly_all", text)
        self.assertEqual(m7_problems(text), [])

    def test_red_removing_the_separators_no_longer_launders_a_bare_percentage(
            self) -> None:
        """🔴 ⑦ 的紅綠自證：舊的 chunk 級判準被「拿掉分隔符」整段矇混過關。

        下面這一則裡第二個百分比既沒有自己的 `kind=`、也沒有自己的分鐘，只是坐在
        第一個桶的名牌與分鐘旁邊。chunk 級判準把它切成**一段**、看到段內有 `kind=`
        也有「分鐘」⇒ 放行；百分比級判準逐個問 ⇒ 抓到兩筆。
        """
        laundered = "kind=session 61% 剩 13 分鐘 57% 剩 8233 分鐘"
        self.assertEqual(_chunk_level_m7_problems(laundered), [],
                         "控制組：舊判準本來就該放行這一則（那正是它的病）")
        problems = m7_problems(laundered)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("沒說是哪一桶", problems[0])

    def test_the_separator_is_not_part_of_the_criterion(self) -> None:
        """把 `describe()` 的分隔符全換掉，判準的答案必須一個字都不變。"""
        text = Q.describe(Q.decide(
            state(("session", 61, 13.5), ("weekly_all", 57, 8233)), NOW, P))
        for old, new in (("；", " / "), ("　", " ")):
            text = text.replace(old, new)
        self.assertEqual(m7_problems(text), [])
        self.assertEqual(len(_PCT_RE.findall(text)), 2)

    def test_the_unmeasurable_message_carries_no_bare_percentage(self) -> None:
        d = Q.decide(Q.QuotaState(axes=(), measured_at=NOW.isoformat(),
                                  source="cache", reason="http-401"), NOW, P)
        text = Q.describe(d)
        self.assertEqual(_PCT_RE.findall(text), [])
        self.assertIn("http-401", text)


# ═══════════════════════════════════════════════════════════════════════════
# M8 檔案契約的兩個消費者必須同步（本包只交付判準 ＋ 比對，不動那兩支檔）
# ═══════════════════════════════════════════════════════════════════════════
_METER = _REPO / "tools" / "lib" / "quota_meter.py"
_ADAPTER = (_REPO / "AutoClaude" / "autoclaude" / "infra" / "adapters"
            / "file_quota_meter.py")
_SCHEMA_RE = re.compile(r'SCHEMA\s*[:=]\s*(?:str\s*=\s*)?"([^"]+)"')


def schema_sync_problems(meter_src: str, adapter_src: str) -> list[str]:
    """兩支檔宣告的 `SCHEMA` 字串必須相等（純文字判準，可注入）。"""
    a = _SCHEMA_RE.search(meter_src)
    b = _SCHEMA_RE.search(adapter_src)
    if a is None or b is None:
        return ["至少一側找不到 SCHEMA 宣告"]
    if a.group(1) != b.group(1):
        return [f"SCHEMA 不同步：meter={a.group(1)} adapter={b.group(1)}——"
                "adapter 對 schema 不符的反應是回 None，而 None 被它自己的測試"
                "釘成正確行為 ⇒ 失效全綠、完全靜默"]
    return []


class TestM8SchemaStaysInSync(unittest.TestCase):
    def test_green_two_matching_declarations(self) -> None:
        self.assertEqual(schema_sync_problems(
            'SCHEMA = "autosdd.quota/2"', 'SCHEMA: str = "autosdd.quota/2"'), [])

    def test_red_only_one_side_bumped(self) -> None:
        """注入①：meter 升到 /2、adapter 留 /1 ⇒ 必紅。"""
        self.assertTrue(schema_sync_problems(
            'SCHEMA = "autosdd.quota/2"', 'SCHEMA: str = "autosdd.quota/1"'))

    def test_red_a_missing_declaration(self) -> None:
        self.assertTrue(schema_sync_problems('SCHEMA = "autosdd.quota/2"', "pass"))

    def test_the_two_real_files_agree_today(self) -> None:
        """對磁碟現況比對。🔴 兩支檔皆**不屬本包**（in-flight），故存在才判。

        誠實劃界：M8-②③（餵一份合法 /2 快取給 adapter、`resume_wait_seconds`
        必須約 360 秒）本包**驗不到**——那要動 adapter，而 adapter 一行都不准動。
        """
        if _METER.exists() and _ADAPTER.exists():
            self.assertEqual(schema_sync_problems(
                _METER.read_text(encoding="utf-8"),
                _ADAPTER.read_text(encoding="utf-8")), [])


# ═══════════════════════════════════════════════════════════════════════════
# M9 「量不到」不得等於「不設限」
# ═══════════════════════════════════════════════════════════════════════════
#: 規格 S7 的十種失效字面（`no-horizon` 那一列有桶，不在本表）。
_UNMEASURABLE_REASONS = (
    "no-credentials", "no-credentials-darwin", "http-401", "http-5xx",
    "meter-unreachable", "no-buckets", "stale-cache", "expired-cache",
    "schema-mismatch", "no-cache",
)


def m9_problems(decide_fn) -> list[str]:
    """兩條不變量：量不到時 `0 < cap <= degraded_cap`，且**永不** halt。"""
    problems = []
    for reason in _UNMEASURABLE_REASONS:
        st = Q.QuotaState(axes=(), measured_at=NOW.isoformat(),
                          source="cache", reason=reason)
        cap = decide_fn(st).cap
        if cap is None:
            problems.append(f"{reason}: cap 是 None ⇒ 量不到等於不設限")
        elif cap == 0:
            problems.append(f"{reason}: cap 是 0 ⇒ 對一個沒量到的值開火")
        elif cap > P.degraded_cap:
            problems.append(f"{reason}: cap={cap} 超過 degraded_cap")
    return problems


class TestM9UnmeasurableIsNotUnlimited(unittest.TestCase):
    def test_green_the_real_decide_passes(self) -> None:
        self.assertEqual(m9_problems(lambda st: Q.decide(st, NOW, P)), [])

    def test_red_when_unmeasurable_falls_back_to_none(self) -> None:
        """注入＝今天 shipped 的行為（`fanout_cap(None) is None`）⇒ 必紅。"""
        broken = lambda st: Q.Decision(None, 0, Q.BAND_FREE, None, (), st.reason)  # noqa: E731
        self.assertEqual(len(m9_problems(broken)), len(_UNMEASURABLE_REASONS))

    def test_red_when_unmeasurable_is_escalated_to_halt(self) -> None:
        """反向：把量不到升級成 halt 也必紅（絕不對未量到的值開火）。"""
        broken = lambda st: Q.Decision(0, 0, Q.BAND_HALT, None, (), st.reason)  # noqa: E731
        self.assertEqual(len(m9_problems(broken)), len(_UNMEASURABLE_REASONS))

    def test_no_horizon_only_slows_down_it_does_not_degrade(self) -> None:
        """S7「200、有桶、無任何 `resets_at`」那一列：走 ×0.5，不是 degraded。"""
        d = Q.decide(Q.QuotaState(
            axes=(axis("spend", 88, None), axis("nimbus_quill", 0, None)),
            measured_at=NOW.isoformat(), source="endpoint",
            reason="no-horizon"), NOW, P)
        self.assertEqual([r.horizon for r in d.per_axis],
                         [Q.AXIS_NONE, Q.AXIS_NONE])
        self.assertEqual(d.cap, 1)

    def test_the_degraded_band_is_not_a_measured_band(self) -> None:
        """band 不得填成 `converge`——那是一句沒量到卻宣稱量到的假話。"""
        d = Q.decide(Q.QuotaState(axes=(), measured_at=NOW.isoformat(),
                                  source="cache", reason="http-401"), NOW, P)
        self.assertEqual(d.band, Q.BAND_UNMEASURED)
        self.assertNotIn(d.band, (Q.BAND_FREE, Q.BAND_NOTICE, Q.BAND_CONVERGE,
                                  Q.BAND_PREPARE, Q.BAND_HALT))

    def test_a_zero_degraded_cap_still_never_locks_solid(self) -> None:
        """設定把 degraded_cap 逼到 0 時仍必須 `>=1`（禁止靜默鎖死）。"""
        weird = Q.Policy(degraded_cap=0)
        d = Q.decide(Q.QuotaState(axes=(), measured_at=NOW.isoformat(),
                                  source="cache", reason="no-cache"), NOW, weird)
        self.assertEqual(d.cap, 1)


# ═══════════════════════════════════════════════════════════════════════════
# M10 決策入口唯一化（本層可釘的那一半）
# ═══════════════════════════════════════════════════════════════════════════
def decision_constructors(source: str) -> list[str]:
    """列出「自己組出一個 `Decision`」的函式——正解是**恰好一個**（`decide`）。"""
    owners = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef):
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                    and inner.func.id == "Decision"):
                owners.append(node.name)
                break
    return sorted(set(owners))


class TestM10SingleDecisionEntry(unittest.TestCase):
    def test_green_only_decide_builds_a_decision(self) -> None:
        self.assertEqual(decision_constructors(_MODULE_SRC), ["decide"])

    def test_red_a_second_derivation_path_is_caught(self) -> None:
        """注入：hook 裡再長出一條自己推導 band/cap 的路徑 ⇒ 必紅。"""
        injected = _MODULE_SRC + (
            "\n\ndef quota_gate(payload):\n"
            "    return Decision(2, 1, BAND_PREPARE, None, (), 'ok')\n")
        self.assertEqual(decision_constructors(injected), ["decide", "quota_gate"])

    def test_decide_is_patchable_so_a_spy_can_be_installed(self) -> None:
        """接線時 M10 要用 `mock.patch` 裝 spy；`decide` 必須是模組層可替換的名字。"""
        self.assertTrue(callable(Q.decide))
        self.assertIs(getattr(Q, "decide"), Q.decide)
        self.assertEqual(Q.decide.__module__, "quota_policy")

    def test_the_module_is_pure_no_io_no_network(self) -> None:
        """純函式層：不得 import 網路／檔案系統／os.environ 那一族。"""
        banned = {"urllib", "requests", "socket", "http", "subprocess", "os"}
        imported = set()
        for node in ast.walk(ast.parse(_MODULE_SRC)):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(imported & banned, set(), f"實得 {sorted(imported)}")
        self.assertNotIn("open(", _MODULE_SRC.replace("path.open(", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
