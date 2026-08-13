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
# 🔴 判準本體（M2／M5／M7／M10 ＋ R86 三缺陷）住 `tools/lib/quota_criteria.py`，本檔只留
# 「呼叫判準 ＋ 斷言」。理由兩條同時成立，見該檔檔頭：① 它們不依賴 unittest，是對源碼／
# 讀數的純判定；② `tools/tests/*.py` 受護欄層行數棘輪管，判準留在這裡會逼別包去砍別的
# 東西來抵。**鑑別力不得下降**：搬家後全部合成注入自證已重跑，結果與搬家前逐字相同。
import pace_contract as PC  # noqa: E402
import quota_criteria as QC  # noqa: E402
import quota_meter as M  # noqa: E402
import quota_pace as W  # noqa: E402
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
                cap = min(QC.cap_num(r.cap) for r in readings)
                base = min(Q._base_rec(r.band, P) for r in readings)
                rec = Q._bound(Q._clamp(int(base * Q._pace_of(readings, P)), P),
                               None if cap == _INF else int(cap))
                self.assertEqual(cap, QC.cap_num(want_cap), f"{label}: cap")
                self.assertEqual(rec, want_rec, f"{label}: rec")

    def test_every_axis_recommendation_stays_under_its_own_cap(self) -> None:
        """逐軸也必須 `rec <= cap`——否則跨軸那一層是在替單軸的矛盾擦屁股。"""
        for _label, st, *_ in _TABLE:
            for r in Q.axes_of(st, NOW, P):
                with self.subTest(kind=r.axis.kind, band=r.band):
                    self.assertLessEqual(float(r.recommended), QC.cap_num(r.cap))


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
    a, b = QC.cap_num(cap_of(_A)), QC.cap_num(cap_of(_B))
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
                            float(d.recommended_fanout), QC.cap_num(d.cap))

    def test_an_axis_with_no_horizon_but_a_real_cap_blocks_acceleration(self) -> None:
        """fail-closed 那一半**原封不動**：期程不明且**真的在煞車**的軸仍一票否決。

        🔴 R84／SA-01 訂正本測試此前的形狀（原版拿 `spend 0%`＝free 帶當否決者，斷言
        `rec == 8`）。那個斷言把「一個 cap=None、零煞車力的軸有完整否決權」釘成了契約，
        於是掌舵者錨點①（低水位＋近 reset ⇒ 多派）在 production **任何**水位下都拿不到
        ×2：live 快取 7 軸有 3 軸 `resets_at=null` 且全是 0% ⇒ 否決永遠成立。
        現在的不變式是「**不參與 cap 的軸不得參與 pace**」，兩個方向各自被下面兩支釘住。
        """
        braking = Q.decide(state(("session", 75, 3), ("spend", 55, None)), NOW, P)
        self.assertEqual(braking.recommended_fanout, 2, "期程不明的煞車軸必須仍能否決加速")
        self.assertEqual(braking.cap, 4, "它的 cap 也必須真的在（否則它不是煞車軸）")

    def test_red_dropping_the_conjunct_lets_a_braking_null_axis_be_overtaken(self) -> None:
        """🔴 合成注入：拿掉 `r.cap is not None` 的**對偶**——把否決整條移除 ⇒ 上一支的
        情境從 2 變 4 ⇒ fail-closed 那一半有牙齒，不是恆綠。"""
        readings = Q.axes_of(state(("session", 75, 3), ("spend", 55, None)), NOW, P)
        no_veto = max(Q._mult(r.horizon, P) for r in readings)      # ＝拿掉整個 if
        base = min(Q._base_rec(r.band, P) for r in readings)
        cap = min(QC.cap_num(r.cap) for r in readings)
        self.assertEqual(Q._pace_of(readings, P), 1.0)
        self.assertEqual(no_veto, 2.0)
        self.assertEqual(Q._bound(Q._clamp(int(base * no_veto), P), int(cap)), 4)

    def test_a_toothless_null_axis_no_longer_vetoes_acceleration(self) -> None:
        """治本那一半：`cap is None`（free 帶）的無期程軸**不得**否決加速。

        數字是 live 快取的形狀（3 軸 `resets_at=null` 且 0%）：修前 8、修後 16。
        """
        with_none = Q.decide(state(("session", 0, 5), ("spend", 0, None)), NOW, P)
        without = Q.decide(state(("session", 0, 5), ("spend", 0, 8640)), NOW, P)
        self.assertEqual(with_none.recommended_fanout, 16, "零煞車力的軸仍在從後門煞車")
        self.assertEqual(without.recommended_fanout, 16, "對照組：沒有 null 軸時本來就 16")

    def test_red_the_old_any_none_predicate_halves_the_recommendation(self) -> None:
        """🔴 合成注入：把判準退回舊形態（`any(horizon == NONE)`）⇒ 上一支必紅（8 != 16）。"""
        readings = Q.axes_of(state(("session", 0, 5), ("spend", 0, None)), NOW, P)
        fastest = max(Q._mult(r.horizon, P) for r in readings)
        old_pace = (min(1.0, fastest)
                    if any(r.horizon == Q.AXIS_NONE for r in readings) else fastest)
        base = min(Q._base_rec(r.band, P) for r in readings)
        self.assertEqual(Q._clamp(int(base * old_pace), P), 8)
        self.assertEqual(Q._clamp(int(base * Q._pace_of(readings, P)), P), 16)

    def test_the_binding_axis_is_never_the_toothless_one(self) -> None:
        """SA-06：cap 平手時 binding 必須落在**真的在消耗**的軸上，不是零消耗那一軸。

        live 快取實測（修前）`binding=nimbus_quill`＝0%、reset 不明、cap=None：指著一個
        完全不消耗的軸說它是最緊的一條，正是「裸百分比誤讀」的下一代形態。
        """
        d = Q.decide(state(("weekly_all", 35, 5976), ("nimbus_quill", 0, None),
                           ("spend", 0, None)), NOW, P)
        self.assertEqual(d.binding.kind, "weekly_all")
        # 🔴 反向：halt／節流帶的無期程軸**必須**保留原優先權——否則 `reset_branch()` 會從
        # `escalate`（只有人去提額）翻成 `arm`（排一支等 reset 的工作）＝R59 事故同形。
        halting = Q.decide(state(("weekly_all", 96, 5976), ("spend", 96, None)), NOW, P)
        self.assertEqual(halting.binding.kind, "spend")
        self.assertIsNone(halting.binding.resets_at)


# ═══════════════════════════════════════════════════════════════════════════
# M2 reset 距離必須真的影響輸出（6b 的存在性證明）
# ═══════════════════════════════════════════════════════════════════════════
class TestM2HorizonActuallyMoves(unittest.TestCase):
    def test_green_the_real_implementation_passes(self) -> None:
        self.assertEqual(
            QC.m2_problems(lambda pct, m: Q.axis_cap(pct, m, P),
                        lambda pct, m: Q.axis_recommended(pct, m, P)), [])

    def test_the_three_horizons_are_three_different_caps(self) -> None:
        """規格 M2 的定點：8 / 4 / 2。今天實測三者皆 `tier=normal cap=None`。"""
        self.assertEqual(
            [Q.axis_cap(79, 3, P), Q.axis_cap(79, 240, P), Q.axis_cap(79, 8640, P)],
            [8, 4, 2])

    def test_red_when_the_minutes_parameter_is_ignored(self) -> None:
        """注入：`axis_cap` 無視 `minutes`（＝今天 shipped 的形態）⇒ 必紅。"""
        problems = QC.m2_problems(lambda pct, _m: Q.axis_cap(pct, 240, P),
                               lambda pct, _m: Q.axis_recommended(pct, 240, P))
        self.assertTrue(problems, "無視 minutes 卻沒轉紅＝零鑑別力")

    def test_red_when_the_direction_is_inverted(self) -> None:
        """注入：方向寫反（reset 愈遠愈寬）⇒ 方向掃描必紅。"""
        inverted = {Q.AXIS_NEAR: 0.5, Q.AXIS_MID: 1.0,
                    Q.AXIS_FAR: 2.0, Q.AXIS_NONE: 2.0}
        self.assertTrue(
            QC.m2_problems(lambda pct, m: _mult_cap(pct, m, inverted),
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
        before = QC.cap_num(aggregate(state(*base)))
        after = QC.cap_num(aggregate(state(*base, extra)))
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
    return Q._clamp(int(override * Q._mult(Q.horizon_band(minutes, P), P)), P)


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
                * Q._mult(Q.horizon_band(m, policy), policy)), policy)
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
        caps = [QC.cap_num(Q.axis_cap(pct / 2.0, minutes, policy)) for pct in range(0, 201)]
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
class TestM5NoSingleScalarDrivesDecisions(unittest.TestCase):
    def test_green_the_module_itself_is_clean(self) -> None:
        self.assertEqual(QC.scalar_decision_defs(_MODULE_SRC), [])
        self.assertEqual(QC.worst_mentions(_MODULE_SRC), [])

    def test_red_the_shipped_signatures_are_caught(self) -> None:
        """注入：貼回 `fanout_cap(pct)` 與 `quota_tier_of(pct)` ⇒ 兩支都必須被抓。"""
        injected = (
            "def fanout_cap(pct: float | None) -> int | None:\n    return 2\n"
            "def quota_tier_of(pct: float) -> str:\n    return 'normal'\n")
        self.assertEqual(sorted(QC.scalar_decision_defs(injected)),
                         ["fanout_cap", "quota_tier_of"])

    def test_green_a_display_helper_is_not_caught(self) -> None:
        """鑑別力反證：顯示用的 `format_pct` 必須放行，否則只是在抓 `pct` 這個字。"""
        harmless = ("def format_pct(pct: float) -> str:\n    return f'{pct}%'\n"
                    "def pct_band(pct: float, p: object) -> str:\n    return 'free'\n")
        self.assertEqual(QC.scalar_decision_defs(harmless), [])

    def test_green_the_two_axis_signature_is_not_caught(self) -> None:
        """規格自己的 `axis_cap(pct, minutes, p)` 必須綠——否則判準把正解判成違規。"""
        good = ("def axis_cap(pct: float, minutes: float | None, p: object):\n"
                "    return 1\n")
        self.assertEqual(QC.scalar_decision_defs(good), [])

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
                self.assertEqual(QC.scalar_decision_defs(injected), ["fanout_cap"])

    def test_green_a_real_state_consumer_has_no_scalar_parameter(self) -> None:
        """鑑別力反證：真的吃狀態的函式**不會**有 `pct` 參數 ⇒ 一開始就不在射程內。"""
        real = ("def decide(state: object, now: object, p: object) -> object:\n"
                "    return state\n")
        self.assertEqual(QC.scalar_decision_defs(real), [])

    def test_the_tombstone_catches_call_sites_not_only_definitions(self) -> None:
        """判準自證：只認 `def worst` 會漏掉「別處定義、這裡呼叫」的版本。"""
        call_only = "top = worst(readings)\npct = top['pct']\n"
        self.assertEqual(QC.worst_mentions(call_only), ["call worst()"])
        self.assertEqual(QC.worst_mentions("def worst(rs):\n    return rs[0]\n"),
                         ["def worst"])

    def test_axis_has_no_scalar_escape_hatch(self) -> None:
        self.assertEqual(QC.scalar_escape_problems(Q.Axis), [])
        with self.assertRaises(TypeError):
            float(axis("session", 61, 13.5))
        with self.assertRaises(TypeError):
            _ = axis("session", 61, 13.5) < axis("weekly_all", 57, 8233)

    def test_red_a_subclass_that_adds_float_is_caught(self) -> None:
        """注入：在 `Axis` 上加 `__float__` ⇒ 執行期半必紅。"""
        class Leaky(Q.Axis):
            def __float__(self) -> float:
                return self.pct

        self.assertTrue(QC.scalar_escape_problems(Leaky))

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
                            QC.scalar_decision_defs(path.read_text(encoding="utf-8")),
                            list, f"{path} 掃不動＝這一面實際上沒有被掃")

    def test_the_owned_surface_is_gated_hard(self) -> None:
        """本包擁有的那一面是硬 gate；其餘兩面見 `TestM5EveryScanSurfaceIsGatedHard`。"""
        self.assertEqual(QC.scalar_decision_defs(_MODULE_SRC), [])
        self.assertEqual(QC.worst_mentions(_MODULE_SRC), [])
        self.assertIn(_REPO / "tools" / "lib" / "quota_policy.py",
                      _M5_SCAN_SURFACES["tools/lib/quota_*.py"])


# 🔴 R82／C4：把「三個掃描面」從**列舉**升成**硬 gate**。
#
# 病（複審鏡以沙箱注入實測，每次跑全套）：`QC.worst_mentions`／`QC.scalar_decision_defs` 兩個
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
# `QC.scalar_decision_defs == []` 且 `QC.worst_mentions == []`。今天全部為空（落地當回合實測），
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
                    QC.scalar_decision_defs(path.read_text(encoding="utf-8")), [],
                    f"{path} 出現「只吃一個純量水位就做決策」的函式 ⇒ "
                    "(pct, 距 reset 幾分鐘) 的後半在簽章層就不存在了")

    def test_the_worst_tombstone_holds_on_every_file(self) -> None:
        for path in self._files():
            with self.subTest(file=path.name):
                self.assertEqual(
                    QC.worst_mentions(path.read_text(encoding="utf-8")), [],
                    f"{path} 又出現 worst()（定義或呼叫）⇒ 那是 R82 的墓碑")

    def test_red_all_five_injections_from_the_review_turn_red(self) -> None:
        """🔴 判準自證：複審鏡那五組注入，逐組必須被抓到。

        沒有這一條，上面兩支就只是「今天恰好是空的」——與「判準看不見任何東西」
        在 rc 上完全相同。這裡直接把注入文字餵給判準本體（不動磁碟）。
        """
        cases = {
            "worst 回到 quota_gate": ("def worst(readings):\n    return readings[0]\n",
                                      QC.worst_mentions),
            "worst 回到 quota_meter": ("top = worst(bucket_readings(payload))\n",
                                       QC.worst_mentions),
            "fanout_cap 回到 quota_gate": (
                "def fanout_cap(pct: float | None) -> int | None:\n    return 2\n",
                QC.scalar_decision_defs),
            "quota_tier_of 回到 hook": (
                "def quota_tier_of(pct: float) -> str:\n    return 'normal'\n",
                QC.scalar_decision_defs),
            "fanout_cap 進 AutoClaude adapter": (
                "class A:\n    def fanout_cap(self, pct: float) -> int:\n        return 2\n",
                QC.scalar_decision_defs),
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
                self.assertEqual(QC.scalar_decision_defs(polluted), ["fanout_cap"])


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
class TestM7EveryPercentNamesItsBucket(unittest.TestCase):
    def test_green_describe_passes_for_every_table_row(self) -> None:
        for label, st, *_ in _TABLE:
            with self.subTest(row=label):
                self.assertEqual(QC.m7_problems(Q.describe(Q.decide(st, NOW, P))), [])

    def test_red_a_bare_percentage_is_caught(self) -> None:
        """注入＝掌舵者當場誤讀的**那個**形狀。"""
        self.assertTrue(QC.m7_problems("額度 54% 了，要收斂"))

    def test_red_naming_the_bucket_but_not_the_horizon(self) -> None:
        """只補桶名不補分鐘 ⇒ 仍必紅（兩個都是 6b 的輸入）。"""
        problems = QC.m7_problems("kind=weekly_all 54% 了，要收斂")
        self.assertEqual(len(problems), 1, problems)

    def test_both_axes_are_named_when_both_halt(self) -> None:
        """兩軸同時 halt 時訊息必須**兩軸都說**；今天只渲染 `worst()` 那一格。"""
        text = Q.describe(Q.decide(
            state(("session", 96, 20), ("weekly_all", 97, 8640)), NOW, P))
        self.assertIn("kind=session", text)
        self.assertIn("kind=weekly_all", text)
        self.assertEqual(QC.m7_problems(text), [])

    def test_red_removing_the_separators_no_longer_launders_a_bare_percentage(
            self) -> None:
        """🔴 ⑦ 的紅綠自證：舊的 chunk 級判準被「拿掉分隔符」整段矇混過關。

        下面這一則裡第二個百分比既沒有自己的 `kind=`、也沒有自己的分鐘，只是坐在
        第一個桶的名牌與分鐘旁邊。chunk 級判準把它切成**一段**、看到段內有 `kind=`
        也有「分鐘」⇒ 放行；百分比級判準逐個問 ⇒ 抓到兩筆。
        """
        laundered = "kind=session 61% 剩 13 分鐘 57% 剩 8233 分鐘"
        self.assertEqual(QC.chunk_level_m7_problems(laundered), [],
                         "控制組：舊判準本來就該放行這一則（那正是它的病）")
        problems = QC.m7_problems(laundered)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("沒說是哪一桶", problems[0])

    def test_the_separator_is_not_part_of_the_criterion(self) -> None:
        """把 `describe()` 的分隔符全換掉，判準的答案必須一個字都不變。"""
        text = Q.describe(Q.decide(
            state(("session", 61, 13.5), ("weekly_all", 57, 8233)), NOW, P))
        for old, new in (("；", " / "), ("　", " ")):
            text = text.replace(old, new)
        self.assertEqual(QC.m7_problems(text), [])
        self.assertEqual(len(QC.PCT_RE.findall(text)), 2)

    def test_the_unmeasurable_message_carries_no_bare_percentage(self) -> None:
        d = Q.decide(Q.QuotaState(axes=(), measured_at=NOW.isoformat(),
                                  source="cache", reason="http-401"), NOW, P)
        text = Q.describe(d)
        self.assertEqual(QC.PCT_RE.findall(text), [])
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
# M8-b 檔案契約的**路徑**那一半（R83／F2-①：此前只有 SCHEMA 被鎖住）
# ═══════════════════════════════════════════════════════════════════════════
# 🔴 立案。檔案契約有兩個欄位（**路徑** ＋ schema），而 R82 只把 schema 綁起來。路徑那一半
# 今天各自寫在兩支檔裡：meter 是 `cache_path()`、adapter 是 `__init__` 的預設值，兩者都
# 自己算 `tempfile.gettempdir() / "autosdd_quota.json"`。adapter **不能** import meter
# （importlinter contract #9「autoclaude must not import monorepo harness modules」），
# 所以複本是設計上必要的——正因為必要，它才需要一道鎖。
#
# 為什麼這一格值得一道鎖，而不是「今天兩邊相符就算了」：R83 本輪的 F2-① 任務書提出的修法
# 正是「把快取搬到不吃 TMPDIR 的固定家」。那個動作只改 meter 的話，adapter 會**靜默**讀不到
# 任何檔 ⇒ `_pick()` 回 `None` ⇒ `resume_wait_seconds` 回落寫死延遲、`TokenGuardPlugin`
# 的額度軸恆「量不到」，而 `None` 這個回傳值被 adapter 自己的測試釘成正確行為（同 SCHEMA
# 那一格的判例：「失效全綠、完全靜默」）。⇒ 搬家是可以做的，但它必須是**同一次** commit
# 動兩支檔，而這道鎖就是那個「同一次」的機械保證。
#
# 判準取「兩邊算路徑用的 token 序列相等」而不是「必須是 gettempdir」：後者會把家釘死在
# 今天這個選擇上，於是將來真的要搬家時，這道鎖自己會變成阻力（本 repo 對「鎖住了實作而
# 不是性質」有判例）。搬到 `~/.cache/autosdd/` 一樣綠——只要兩邊一起搬。
#: 「家」只可能來自這幾個地方。刻意是白名單而不是「抓所有識別字」：後者會把
#: `self._path`／`Path`／`if`／`else` 這種**寫法差異**也算進去，於是兩支檔明明用同一個
#: 算法卻判紅（實測：第一版判準就是這樣假紅的）。假紅的鎖活不過一輪。
_HOME_SOURCE_RE = re.compile(
    r"tempfile\.gettempdir|Path\.home|os\.path\.expanduser|expanduser|"
    r"os\.environ|os\.getenv")
#: 檔名那一段由 `QuotaCacheContractHomeTest` 另一側守（meter↔hook 的 `CACHE_NAME` 間接
#: 層）。本判準只問「**目錄**那一段是不是同一個算法」，所以在這兩個 token 處截斷。
_FILENAME_TOKENS = ("CACHE_NAME", '"autosdd_quota.json"')


def cache_home_tokens(source: str) -> list[str]:
    """把一支檔算「快取住哪裡」的那個運算式抽成可比對的 token 序列（家 ＋ 目錄字面）。"""
    tokens: list[str] = []
    for line in source.splitlines():
        text = line.strip()
        # 註解裡照抄契約是允許的（adapter 檔頭就有一行）——它不是第二個實作。
        if text.startswith("#") or not any(t in text for t in _FILENAME_TOKENS):
            continue
        head = text
        for token in _FILENAME_TOKENS:
            head = head.split(token)[0]
        tokens += _HOME_SOURCE_RE.findall(head)
        tokens += re.findall(r'"([^"]+)"', head)   # `.cache` / `autosdd` 這種目錄字面
    return tokens


def cache_home_sync_problems(meter_src: str, adapter_src: str) -> list[str]:
    """兩支檔算出來的快取**目錄**必須來自同一個算法（純文字判準，可注入）。"""
    a, b = cache_home_tokens(meter_src), cache_home_tokens(adapter_src)
    if not a or not b:
        return ["至少一側找不到快取路徑運算式 ⇒ 契約的路徑那一半沒有家"]
    if a != b:
        return [f"快取路徑算法不同步：meter={a} adapter={b}——adapter 對「檔不在」的反應是"
                "回 None（＝量不到），而 None 被它自己的測試釘成正確行為 ⇒ 失效全綠、"
                "完全靜默。搬家必須同一次 commit 動兩支檔"]
    return []


class TestM8bCacheHomeStaysInSync(unittest.TestCase):
    _METER_LIKE = "    return Path(tempfile.gettempdir()) / CACHE_NAME\n"
    _ADAPTER_LIKE = ('        self._path = Path(path) if path else '
                     'Path(tempfile.gettempdir()) / "autosdd_quota.json"\n')

    def test_green_two_matching_expressions(self) -> None:
        self.assertEqual(cache_home_sync_problems(
            self._METER_LIKE, self._ADAPTER_LIKE), [])

    def test_red_only_the_meter_moves_home(self) -> None:
        """注入①＝F2-① 提議的那個修法只做一半 ⇒ 必紅（這就是它存在的理由）。"""
        moved = '    return Path.home() / ".cache" / "autosdd" / CACHE_NAME\n'
        problems = cache_home_sync_problems(moved, self._ADAPTER_LIKE)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("完全靜默", problems[0])

    def test_green_when_both_move_together(self) -> None:
        """對稱的控制組：**一起**搬家必須放行，否則這道鎖鎖的是實作不是性質。"""
        self.assertEqual(cache_home_sync_problems(
            '    return Path.home() / ".cache" / "autosdd" / CACHE_NAME\n',
            '        self._path = Path(path) if path else '
            'Path.home() / ".cache" / "autosdd" / "autosdd_quota.json"\n'), [])

    def test_red_a_missing_expression(self) -> None:
        self.assertTrue(cache_home_sync_problems(self._METER_LIKE, "pass"))

    def test_the_two_real_files_agree_today(self) -> None:
        """對磁碟現況比對（adapter 不屬本包，故存在才判——同 M8 的體例）。"""
        if _METER.exists() and _ADAPTER.exists():
            self.assertEqual(cache_home_sync_problems(
                _METER.read_text(encoding="utf-8"),
                _ADAPTER.read_text(encoding="utf-8")), [])


# ═══════════════════════════════════════════════════════════════════════════
# M9 「量不到」不得等於「不設限」
# ═══════════════════════════════════════════════════════════════════════════
#: 規格 S7 的失效字面（`no-horizon` 那一列有桶，不在本表）。
#: 🔴 R83／F2-③ 新增 `keychain-timeout`：mac 的 Keychain 跳鎖定提示而沒有人按時，
#: `security` 會阻塞到逾時——那與「這台 mac 沒有條目」要做的事完全相反（解鎖 vs 重新登入），
#: 故取數層給了它自己的字面。本表**不是**這批字面的家（家在 `quota_meter.REASON_*`），
#: 而是「每一個字面都必須被 M9 那兩條不變量掃過」的登記處；兩者的同步由
#: `TestMeterReasonsAreAllRegistered` 機械守（漏登記即紅）。
_UNMEASURABLE_REASONS = (
    "no-credentials", "no-credentials-darwin", "keychain-timeout",
    "http-401", "http-5xx", "meter-unreachable", "no-buckets",
    "stale-cache", "expired-cache", "schema-mismatch", "no-cache",
)


# 🔴 立案（R83／F2-③，形狀與 `TestM8SchemaStaysInSync` 同構）：取數層新增一個失效字面
# 時，**沒有任何東西**會提醒你來這張表登記它。漏登記的後果不是崩潰而是失明——那個字面
# 從此不在 M9 的分母裡，於是「它會不會被錯判成不設限／被錯判成 halt」這兩條不變量對它
# 一次都沒有驗過，而 rc 與「正確地全部通過」一模一樣（分母少一項是看不見的）。
# 判準的分母是**現查** meter 的 `REASON_*` 宣告集合（會變的量測值），不是寫死清單。
_METER_REASON_RE = re.compile(r"^REASON_([A-Z0-9_]+)\s*=\s*\"([^\"]+)\"", re.MULTILINE)
#: `REASON_OK` 是「量到了」，語意上不屬本表——唯一的例外，且必須具名而不是靠註解。
_NOT_A_FAILURE = ("ok",)


def reason_registry_problems(meter_src: str, registered: tuple[str, ...]) -> list[str]:
    """meter 宣告的每一個失效字面都必須登記進 `_UNMEASURABLE_REASONS`（純文字判準）。"""
    declared = {value for _, value in _METER_REASON_RE.findall(meter_src)}
    missing = sorted(declared - set(registered) - set(_NOT_A_FAILURE))
    return [f"`{name}` 是 quota_meter 宣告的失效字面，卻沒有登記進 _UNMEASURABLE_REASONS"
            "⇒ M9 那兩條不變量對它零覆蓋，而分母少一項是靜默的" for name in missing]


class TestMeterReasonsAreAllRegistered(unittest.TestCase):
    def test_green_the_real_meter_is_fully_registered(self) -> None:
        if _METER.exists():
            self.assertEqual(reason_registry_problems(
                _METER.read_text(encoding="utf-8"), _UNMEASURABLE_REASONS), [])

    def test_red_a_newly_declared_reason_that_nobody_registered(self) -> None:
        """注入①：取數層長出一個新字面而本表沒動 ⇒ 必紅。"""
        problems = reason_registry_problems(
            'REASON_FOO = "brand-new-failure"\n', _UNMEASURABLE_REASONS)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("brand-new-failure", problems[0])

    def test_red_this_rounds_own_reason_would_have_been_caught(self) -> None:
        """注入②：拿掉本輪新增的那一個 ⇒ 必紅（證明它不是事後補記的裝飾）。"""
        without = tuple(r for r in _UNMEASURABLE_REASONS if r != "keychain-timeout")
        self.assertTrue(reason_registry_problems(
            'REASON_KEYCHAIN_TIMEOUT = "keychain-timeout"\n', without))

    def test_ok_is_the_only_exemption_and_it_is_named(self) -> None:
        """控制組：`REASON_OK` 不得因為這道鎖而被逼進失效表（它是「量到了」）。"""
        self.assertEqual(reason_registry_problems(
            'REASON_OK = "ok"\n', _UNMEASURABLE_REASONS), [])
        self.assertNotIn("ok", _UNMEASURABLE_REASONS)


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
class TestM10SingleDecisionEntry(unittest.TestCase):
    def test_green_only_decide_builds_a_decision(self) -> None:
        self.assertEqual(QC.decision_constructors(_MODULE_SRC), ["decide"])

    def test_red_a_second_derivation_path_is_caught(self) -> None:
        """注入：hook 裡再長出一條自己推導 band/cap 的路徑 ⇒ 必紅。"""
        injected = _MODULE_SRC + (
            "\n\ndef quota_gate(payload):\n"
            "    return Decision(2, 1, BAND_PREPARE, None, (), 'ok')\n")
        self.assertEqual(QC.decision_constructors(injected), ["decide", "quota_gate"])

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


# ═══════════════════════════════════════════════════════════════════════════
# R84／6b：pace 兩個係數必須可由 `.env` 調，而**方向**必須被機械守
# ═══════════════════════════════════════════════════════════════════════════
# 病：三檔乘數此前是模組層寫死的 dict（`_MULTIPLIER = {near: 2.0, …}`），而掌舵者訴求 6b
# 逐字要求「係數必須可由 env 參數化」——寫死的字面結構上不可能被參數化。
# 這一節同時守住開放之後**新長出來的**危害：兩個鍵各自合法（值域檢查看得到），但
# 「near < far」這種**關係**錯誤只有跨鍵判準看得到，而它會讓「近 reset 加速」變成減速。
class TestR84ThePaceCoefficientsAreTunableAndDirectional(unittest.TestCase):
    def test_the_two_knobs_are_declared_and_reach_the_policy(self) -> None:
        """`.env` 兩個鍵 → `Policy` 欄位 → 真的改變 rec（三段都要接上）。"""
        names = [s.name for s in Q.ENV_SPEC]
        self.assertIn("AUTOSDD_QUOTA_PACE_NEAR", names)
        self.assertIn("AUTOSDD_QUOTA_PACE_FAR", names)
        policy, problems = Q.load_policy({"AUTOSDD_QUOTA_PACE_NEAR": "4"})
        self.assertEqual(problems, [])
        self.assertEqual(policy.pace_near, 4.0)
        # 0%＋5 分鐘後 reset：預設 ×2 ⇒ 16（撞 max_fanout）；把 max_fanout 一起放大才看得到 ×4
        loose, _ = Q.load_policy({"AUTOSDD_QUOTA_PACE_NEAR": "4",
                                  "AUTOSDD_QUOTA_MAX_FANOUT": "64"})
        self.assertEqual(Q.decide(state(("session", 0, 5)), NOW, loose).recommended_fanout, 32)
        self.assertEqual(Q.decide(state(("session", 0, 5)), NOW, P).recommended_fanout, 16)

    def test_a_reversed_direction_is_reported_not_silently_applied(self) -> None:
        """🔴 near<1 或 far>1 ＝「近 reset 就減速」⇒ 必須進 problems 並整組退回預設。"""
        for env in ({"AUTOSDD_QUOTA_PACE_NEAR": "0.5"}, {"AUTOSDD_QUOTA_PACE_FAR": "2"}):
            with self.subTest(env=env):
                policy, problems = Q.load_policy(env)
                self.assertTrue(problems, f"{env} 被靜默接受＝方向鎖恆綠")
                self.assertEqual(policy, Q.DEFAULT_POLICY)

    def test_red_removing_the_direction_check_makes_the_reversal_silent(self) -> None:
        """🔴 合成注入：直接構造反向 `Policy`（繞過 env 值域）⇒ 方向判準必須自己抓到。

        沒有這一支，上一支可能只是被 `ENV_SPEC` 的 lo／hi 擋掉——那守不到程式內構造。
        """
        reversed_policy = Q.Policy(pace_near=0.5, pace_far=2.0)
        problems = Q.policy_monotonicity_problems(reversed_policy)
        self.assertTrue([p for p in problems if "[方向]" in p], f"實得 {problems}")
        self.assertEqual([p for p in Q.policy_monotonicity_problems(P) if "[方向]" in p], [])

    def test_the_multiplier_has_exactly_one_home(self) -> None:
        """乘數不得再有模組層寫死的第二個家（同 repo 判過的「同一份知識兩個家」）。"""
        self.assertFalse(hasattr(Q, "_MULTIPLIER"), "舊的寫死 dict 又長回來了")
        self.assertEqual(Q._mult(Q.AXIS_NEAR, P), P.pace_near)
        self.assertEqual(Q._mult(Q.AXIS_FAR, P), P.pace_far)
        self.assertEqual(Q._mult(Q.AXIS_NONE, P), P.pace_far)
        self.assertEqual(Q._mult(Q.AXIS_MID, P), 1.0)


# ═══════════════════════════════════════════════════════════════════════════
# R86 缺陷 A（門檻是絕對分鐘數）／B（瞬時 pct 無意義）／C（cap 保護錯的配額）
# ═══════════════════════════════════════════════════════════════════════════
# 判準本體、對照組（R85 版判讀的程式重建）、掃描網格與 CLI 校準基準全住
# `tools/lib/quota_criteria.py`；逐項實測數字與治法辯護住
# `docs/06_quality/CrossPlatform_R86_Pace_Calibration.md`。本節只做斷言。
class TestR86WindowRelativeHorizonAndCrossWindowAmortization(unittest.TestCase):
    def test_defect_a_the_same_distance_means_different_things_per_window(self) -> None:
        """同 pct、同 reset 距離、不同窗長 ⇒ 新版必須分歧；R85 版必須**逐格相同**。"""
        old, new = QC.defect_a_divergence(P, Q, NOW)
        self.assertEqual(old[0], old[1], "對照組：R85 版本來就看不到窗長（那正是缺陷 A）")
        self.assertEqual(new, (Q.AXIS_FAR, Q.AXIS_NEAR), f"新版仍然看不到窗長：{new}")

    def test_defect_b_the_same_pct_at_two_burn_rates_gets_two_caps(self) -> None:
        """74% ＋ 已過 20%／90% ⇒ 新版 cap 必須不同；R85 版必須相同。"""
        old, new = QC.defect_b_divergence(P, Q, NOW)
        self.assertEqual(old[0], old[1], "對照組：R85 版對燃燒率整片失明（那正是缺陷 B）")
        self.assertLess(new[0], new[1], f"超支的那一格必須比省的那一格緊：{new}")

    def test_defect_c_this_window_allowance_moves_with_the_long_window(self) -> None:
        """短窗讀數完全相同、長窗剩餘窗數不同 ⇒ 本窗餘裕與 cap 必須不同。"""
        old, caps, headrooms = QC.defect_c_divergence(P, Q, NOW)
        self.assertEqual(old[0], old[1], "對照組：R85 版沒有跨窗攤提這個概念")
        self.assertNotEqual(caps[0], caps[1], f"攤提沒有進到 cap：{caps}")
        self.assertGreater(headrooms[0], headrooms[1], "長窗剩餘窗數愈多 ⇒ 本窗配額愈小")

    def test_acceleration_never_happens_without_evidence_of_thrift(self) -> None:
        """🔴 方向鎖（本節最重要的一支）：新版**只准**在有節省證據時比 R85 版鬆。"""
        looser, unlicensed = QC.unlicensed_acceleration(P, Q, W, NOW)
        self.assertTrue(looser, "一格都沒有放寬 ⇒ 這支測試失去鑑別力（缺陷 A 沒被治）")
        self.assertEqual(unlicensed, [], f"無證據就放寬了：{unlicensed[:5]}")

    def test_amortization_only_tightens_and_never_triggers_halt(self) -> None:
        """攤提是 `max(原始 pct, 攤提後)` ⇒ 換算比被設成任何值都不可能放寬；且封頂在 halt-1。"""
        for ratio in (0.1, 1.0, 7.0, 1e6):
            shown = W.band_inputs((("five_hour", 40.0), ("seven_day", 75.0)),
                                  (100.0, 9000.0), (300.0, 10080.0), ratio, 95.0)[0]
            self.assertGreaterEqual(shown[0], 40.0, f"r={ratio} 讓攤提放寬了")
            self.assertEqual(shown[1], 75.0, "攤提不得動長窗那一軸的水位")
        hot = W.band_inputs((("five_hour", 90.0), ("seven_day", 99.0)),
                            (100.0, 9000.0), (300.0, 10080.0), 1.0, 95.0)[0]
        self.assertEqual(Q.pct_band(hot[0], P), Q.BAND_PREPARE, "推導值把短窗推進 halt 帶")
        self.assertEqual(W.band_inputs((("five_hour", 99.0),), (100.0,), (300.0,),
                                       1.0, 95.0)[0][0], 99.0, "真 halt 的軸被放寬了")

    def test_an_unresolvable_window_keeps_the_shipped_absolute_thresholds(self) -> None:
        """窗長解不出 ⇒ 逐格等於 R85 版（向後相容是**跑出來的**，不是宣稱的）。"""
        self.assertIsNone(W.window_minutes("session"))
        self.assertEqual(QC.backward_compat_problems(P, Q, NOW), [])

    def test_the_conversion_ratio_is_conservative_while_samples_are_thin(self) -> None:
        """樣本不足 ⇒ 取 min 並**說出來**；翻頁不得被讀成一次負燃燒的觀測。"""
        ratio, note = W.estimate_ratio(list(W.SEED_OBSERVATIONS))
        self.assertIn("保守", note)
        self.assertLess(ratio, 15.0, "點估 15 是上界；下界才是保守側")
        self.assertEqual(W.estimate_ratio([])[0], None)
        text = "".join(W.row_of(ts, (("five_hour", s), ("seven_day", lg)))
                       for ts, s, lg in W.SEED_OBSERVATIONS)
        self.assertEqual(len(W.rows_from_jsonl(text + text)), 2)
        self.assertEqual(W.rows_from_jsonl("not json\n{}\n{\"pct\": 3}\n"), [])
        rows = [("2026-08-12T01:00+08:00", 10.0, 70.0), ("2026-08-12T02:00+08:00", 40.0, 72.0),
                ("2026-08-12T07:00+08:00", 5.0, 73.0), ("2026-08-12T08:00+08:00", 35.0, 75.0)]
        self.assertEqual([len(s) for s in W.segments(rows)], [2, 2])
        self.assertIsNone(W.ratio_of(-30.0, 1.0), "翻頁的負差值不得產生換算比")

    def test_the_helm_cli_screen_reconciles_with_the_axes_snapshot(self) -> None:
        """🔴 外部校準憑證：CLI 畫面上的兩個數字 vs 程式從 `axes[]` 算出來的兩個數字。"""
        text, pct, resets_at, read_at, cli_minutes = QC.CLI_CALIBRATION
        self.assertIn(f"{pct:g}% used", text)
        when = datetime.fromisoformat(read_at)
        self.assertAlmostEqual(Q.minutes_to_reset(resets_at, when), cli_minutes,
                               delta=QC.CLI_TOLERANCE_MINUTES)
        reading = Q.axes_of(Q.QuotaState((Q.Axis("session", pct, resets_at),),
                                         read_at, "endpoint", "ok"), when, P)[0]
        self.assertEqual(reading.axis.pct, pct, "pct 必須逐字吻合，不吃容差")
        self.assertAlmostEqual(reading.minutes, cli_minutes,
                               delta=QC.CLI_TOLERANCE_MINUTES)


class TestR86ThePaceContractWriterMatchesTheEngineReader(unittest.TestCase):
    """引擎不准 import 根層（`no-harness-import`）⇒ 檔名與 schema 兩個字面必然有兩個家。"""

    def test_both_literals_are_identical_on_the_two_sides(self) -> None:
        engine = _REPO / "AutoClaude" / "autoclaude"
        self.assertEqual(QC.contract_literal_problems(
            PC, (engine / "infra" / "adapters" / "file_quota_meter.py").read_text(
                encoding="utf-8"),
            (engine / "core" / "ports" / "quota_meter.py").read_text(encoding="utf-8")), [])

    def test_the_payload_never_writes_a_null_cap_and_carries_provenance(self) -> None:
        """`cap=None`（不設限）必須映射成整數；`measured_at` 是**量測**時刻不是現在。"""
        st = state(("session", 0, 30))
        free = PC.payload(Q.decide(st, NOW, P), st, P.max_fanout, P.halt_pct)
        self.assertEqual((free["cap"], free["schema"]), (P.max_fanout, PC.CONTRACT_SCHEMA))
        self.assertEqual(free["measured_at"], NOW.isoformat())
        halted = PC.payload(Q.decide(state(("session", 96, 20)), NOW, P), st,
                            P.max_fanout, P.halt_pct)
        self.assertEqual((halted["cap"], halted["band"]), (0, Q.BAND_HALT))
        for key in ("headroom_pct", "headroom_pct_per_hour", "binding_kind", "source"):
            self.assertIn(key, free)


class TestR87TheMeterMayNotDropAThrottlingAxis(unittest.TestCase):
    """R87 事故鎖：**取數層不得把「已撞頂但自報 `enabled:false`」的軸丟掉。**

    🔴 立案（本輪真實事故，非假想）：13 個 subagent 全數撞
    `You've hit your monthly spend limit`，燒 **1,319,703 tokens**／331 tool_uses／634 秒、
    **零產出**。根因**不在判讀層**——`decide()` 的「halt 一票否決」不變式當時完好無損；
    舵手是從**取數層**把 `spend`／`extra_usage` 兩軸整個排除掉（誤讀
    `enabled:false` ＝「池子關著、不算節流軸」，真意是 `used 610 > limit 500` 已撞月度
    支出上限、購買功能因此被 org 層停用）。於是判讀層**拿不到輸入**，整道保護在
    **零判準觸發**的情況下失效，且失敗表徵與「一切正常」完全相同。

    ⇒ 這揭露的架構缺口是：判讀層的不變式只保證「**給定的軸**不會被放寬」，
    它**不保證「軸不會消失」**。本鎖補的就是那一格——把事故當下的真實 payload 釘成
    fixture，任何讓它**不再 halt** 的改動當場轉紅。

    🔴 本鎖的存在理由是「**由程式否決模型，不是由模型自律**」：掌舵者對本事故的裁決
    逐字為「不是要寫在程式架構控制嗎？怎麼變成你在控制？」。散文約束對當下的模型
    零攔阻力（repo 已多次實證），所以下一次有人再判定「這是假紅」時，必須有東西轉紅。
    """

    #: 事故當回合 http 200 回應的**真實**節錄（關鍵欄位逐字保留，時間欄改為相對本檔 NOW）。
    INCIDENT = {
        "limits": [{"kind": "session", "percent": 1, "resets_at": at(30),
                    "group": "session", "is_active": True}],
        "five_hour": {"utilization": 1.0, "resets_at": at(30),
                      "limit_dollars": None, "used_dollars": None},
        "extra_usage": {"is_enabled": False, "monthly_limit": 500,
                        "used_credits": 610.0, "utilization": 100.0,
                        "disabled_reason": "org_level_disabled_until",
                        "spend_limit_reached": True, "credits_ever_enabled": True},
        "spend": {"used": {"amount_minor": 610}, "limit": {"amount_minor": 500},
                  "percent": 100, "severity": "critical", "enabled": False,
                  "disabled_reason": "org_level_disabled_until",
                  "can_purchase_credits": False},
    }

    @staticmethod
    def _state_from(readings) -> Q.QuotaState:
        return Q.QuotaState(
            axes=tuple(Q.Axis(kind=r["kind"], pct=r["pct"], resets_at=r["resets_at"])
                       for r in readings),
            measured_at=NOW.isoformat(), source="endpoint", reason="ok")

    def test_the_throttling_axes_survive_the_meter(self) -> None:
        """`spend`／`extra_usage` 必須出現在取數層的輸出裡——這是被繞過的那一格。"""
        kinds = {r["kind"] for r in M.bucket_readings(self.INCIDENT)}
        self.assertIn("spend", kinds)
        self.assertIn("extra_usage", kinds)

    def test_the_incident_payload_still_halts(self) -> None:
        """端到端：這份 payload 餵完整條鏈，結論必須是 halt／cap=0。"""
        st = self._state_from(M.bucket_readings(self.INCIDENT))
        out = PC.payload(Q.decide(st, NOW, P), st, P.max_fanout, P.halt_pct)
        self.assertEqual(out["band"], Q.BAND_HALT)
        self.assertEqual(out["cap"], 0)

    def test_the_lock_discriminates(self) -> None:
        """合成注入自證：**重演** R87 那個錯誤實作，必須不再 halt。

        這一條證明前兩條守的就是那個差異——沒有它，前兩條可能只是在斷言一個
        恆真的東西（本 repo 對「結構上恆綠的假鎖」已有多次判例）。
        """
        dropped = [r for r in M.bucket_readings(self.INCIDENT)
                   if r["kind"] not in ("spend", "extra_usage")]
        self.assertTrue(dropped, "重演組不得為空，否則本自證無鑑別力")
        st = self._state_from(dropped)
        out = PC.payload(Q.decide(st, NOW, P), st, P.max_fanout, P.halt_pct)
        self.assertNotEqual(
            out["band"], Q.BAND_HALT,
            "把兩軸排除後若仍 halt，代表 halt 另有來源，本鎖並未守住那個缺口")

    def test_disabled_is_not_a_reason_to_drop_an_axis(self) -> None:
        """`enabled:false` 這個欄位本身**不得**成為排除依據。

        判準刻意寫成「同一份 payload、只把布林翻成 True」的對照：兩者收到的軸集合
        必須**逐字相同**。若哪天有人再以 `enabled`／`is_enabled` 當過濾條件，
        這一條會當場紅——而它是這次事故裡唯一被動過的那一行。
        """
        enabled = {k: (dict(v, **({"enabled": True} if "enabled" in v else {}),
                          **({"is_enabled": True} if "is_enabled" in v else {}))
                       if isinstance(v, dict) else v)
                   for k, v in self.INCIDENT.items()}
        self.assertEqual(
            {r["kind"] for r in M.bucket_readings(self.INCIDENT)},
            {r["kind"] for r in M.bucket_readings(enabled)})


class TestR87AccountPostureIsKnownBeforeDispatch(unittest.TestCase):
    """R87：**派工前**要先知道 Account Type 與有沒有可用 credits（掌舵者裁決）。

    立案逐字：「配置 Agents 前，要先知道 Account Type and Account 是否有 Usage
    credits 再進行配置！」。事故機制＝訂閱窗尚有 37% 餘裕、credits 池已爆且停用
    ⇒ 扇出全滅而主 session 照常 ⇒ **credits 是「還有沒有救」的布林，不是節流軸**。
    """

    INCIDENT = TestR87TheMeterMayNotDropAThrottlingAxis.INCIDENT

    def test_the_exhausted_and_disabled_pool_gives_no_fallback(self) -> None:
        """事故當下的真實 payload：兩池皆 `used>limit` 且 `enabled:false`。"""
        p = M.account_posture(self.INCIDENT)
        self.assertTrue(p["credits_present"])
        self.assertFalse(p["credits_enabled"])
        self.assertTrue(p["credits_exhausted"])
        self.assertFalse(p["fallback_available"])

    def test_an_account_without_credits_defaults_to_no_fallback(self) -> None:
        """掌舵者：「（通常沒有）」⇒ 沒有 credits 欄的帳號＝訂閱窗即硬牆。"""
        bare = {k: v for k, v in self.INCIDENT.items()
                if k not in M.CREDIT_POOL_KEYS}
        p = M.account_posture(bare)
        self.assertFalse(p["credits_present"])
        self.assertFalse(p["fallback_available"])

    def test_a_healthy_pool_does_give_fallback(self) -> None:
        """**鑑別力**：池若真的可用，必須回 `True`，否則本判準恆假＝假鎖。"""
        healthy = dict(self.INCIDENT)
        healthy["extra_usage"] = dict(self.INCIDENT["extra_usage"],
                                      is_enabled=True, used_credits=10.0)
        healthy["spend"] = dict(self.INCIDENT["spend"], enabled=True,
                                used={"amount_minor": 10})
        self.assertTrue(M.account_posture(healthy)["fallback_available"])

    def test_unreadable_payload_is_not_read_as_healthy(self) -> None:
        """「量不到 ≠ 量到零」：讀不出來一律**無 fallback**，不得樂觀。"""
        for bad in (None, [], "x", {}, {"spend": "not-a-dict"}):
            self.assertFalse(M.account_posture(bad)["fallback_available"], bad)

    def test_the_fingerprint_is_the_axis_set_not_a_plan_name(self) -> None:
        """指紋＝軸組合。payload 沒有方案名（實測 17 個頂層鍵無一為方案名），
        且它的用途是**偵測方案變更**，不是查一組寫死的參數。"""
        p = M.account_posture(self.INCIDENT)
        self.assertIn("spend", p["plan_fingerprint"])
        self.assertIn("session", p["plan_fingerprint"])
        self.assertEqual(p["plan_fingerprint"], tuple(sorted(p["plan_fingerprint"])))


if __name__ == "__main__":
    unittest.main(verbosity=2)
