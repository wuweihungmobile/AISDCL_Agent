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
  · ✅ **M5 靜態半的四個掃描面已於 R82／C4 全數轉成硬 gate**（見
    `TestM5EveryScanSurfaceIsGatedHard`；立案史料＝R89 收尾證據檔）。
本檔另外釘住**本層**可釘的那一半：`Decision` 的建構點必須唯一（＝`decide`），
讓「hook 裡再長出第二條自己推導 band/cap 的路徑」在接線時就沒有可抄的樣板。

🔴 **本檔各鎖的立案史料原文一律住 `docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`**
（R89 起的搬遷體例：判準與判準的理由留在本檔，事故數字／裁決逐字／舊版形態進證據檔）。
下文以「R89 收尾證據檔」指稱它——**指標的家只有這一處**，逐處複寫完整路徑會讓同一份
知識住十幾個家，而其中只有一個會被人改（本 repo 對 `Find-GitBash` 已下過同型判決）。

執行：python -m unittest test_quota_policy -v   （cwd＝tools/tests）
"""
from __future__ import annotations

import ast
import dataclasses
import json
import random
import re
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "tools" / "lib"))
# 🔴 判準本體（M2／M5／M7／M10 ＋ R86 三缺陷）住 `tools/lib/quota_criteria.py`，本檔只留
# 「呼叫判準 ＋ 斷言」；理由見該檔檔頭。**鑑別力不得下降**（搬家後注入自證全數重跑）。
import pace_contract as PC  # noqa: E402
import quota_criteria as QC  # noqa: E402
import quota_gate as QG  # noqa: E402  # R95 修4：halt 動作接線面（waker 注入驗證）
import quota_messages as QM  # noqa: E402  # R95 修4：halt 多軸 reset 裁決的家
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
    """🔴 上表每一列都必須從**寫下來的聚合規則**重算得到（本測試不呼叫 `decide()`，
    照 `quota_policy` 檔頭的 cap／rec 兩式獨立重算——兩條互不相干的算法對得上，才排除
    「表是照著實作抄的」）。S4 表兩列與交件時判定不同的歸因＝R95 Pace 證據檔 §7.4；
    規則原文與重算取捨全文＝同檔 §7-R95-L1。
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
    """判準本體：`cap(A)` 必須**嚴格大於** `cap(B)`。刻意不斷言「binding／reset 分支
    ／訊息不同」——那三條今天就是綠的，寫進去就是零鑑別力的鎖。"""
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
        """五次觀測 `is_active` 都等於 argmax，但五次一致不構成契約：把它掛到低水位
        那一軸，決策必須一個位元都不變（否則＝`worst()` 換個寫法再犯一次）。"""
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


# ── R89 `is_active`／`severity`：接好卻沒有電的線（通電不得改判）────────────────
# 🔴 判準的**立案史料原文**（為何交付條件的字面不可滿足、抹回聲欄的判準為何更強、
#    反向判準為何必要）＝`tools/lib/quota_meter.py` 的〈R89 觀測欄〉段，本節不複寫。
#: 新帳號（Team）payload 形狀，2026-08-15 真機節錄（時間欄改為相對 NOW）。與舊帳號的
#: 形狀差異即本節要驗的兩點：`extra_usage` 各欄皆 `None`（⇒ 不成一個軸）、多 `weekly_scoped`。
_R89_TEAM = {
    "five_hour": {"utilization": 6.0, "resets_at": at(264), "limit_dollars": None},
    "seven_day": {"utilization": 1.0, "resets_at": at(9624)},
    "nimbus_quill": {"utilization": 0.0, "resets_at": None},
    "extra_usage": {"is_enabled": False, "monthly_limit": None, "used_credits": None},
    "limits": [{"kind": "session", "group": "session", "percent": 6,
                "severity": "normal", "resets_at": at(264), "is_active": True},
               {"kind": "weekly_all", "group": "weekly", "percent": 1,
                "severity": "normal", "resets_at": at(9624), "is_active": False},
               {"kind": "weekly_scoped", "group": "weekly", "percent": 0,
                "severity": "normal", "resets_at": None, "is_active": False}],
    "spend": {"used": {"amount_minor": 0}, "limit": None, "percent": 0,
              "severity": "normal", "enabled": False},
}


def _r89_state(rows, carry: bool) -> Q.QuotaState:
    """建 `QuotaState`；`carry=False`＝重演通電前。欄序同 `quota_gate.read_quota()`。"""
    return Q.QuotaState(tuple(
        Q.Axis(str(r["kind"]), float(r["pct"]), r.get("resets_at"), r.get("group"),
               r.get("is_active") if carry else None,
               r.get("severity") if carry else None, str(r.get("via") or ""))
        for r in rows), NOW.isoformat(), "cache", "ok")


def r89_decision_drift_problems(decide_fn, rows, ratio=None) -> list[str]:
    """判準本體：同一批讀數餵兩次（不帶／帶新欄），**抹掉回聲欄後**決策須逐位元相同。"""
    def strip(a):
        return a and dataclasses.replace(a, is_active=None, severity=None)

    def blank(d):
        return dataclasses.replace(d, binding=strip(d.binding), per_axis=tuple(
            r._replace(axis=strip(r.axis)) for r in d.per_axis))
    old = decide_fn(_r89_state(rows, False), ratio)
    new = decide_fn(_r89_state(rows, True), ratio)
    return [] if blank(new) == old else [f"通電改判：舊={old}／新={blank(new)}"]


def _r89_decide(st: Q.QuotaState, ratio) -> Q.Decision:
    return Q.decide(st, NOW, P, ratio, "r89-fixture")


class TestR89ObservationFieldsAreWiredButInert(unittest.TestCase):
    """兩個新欄位必須**真的送達**，且**一格都不得參與**分類／選桶／band／cap／rec。"""

    def test_green_neither_account_shape_moves_a_single_decision_bit(self) -> None:
        """兩種帳號形狀 ×「攤提分支開不開」。`ratio` 那一組不是湊數：不帶它時
        `Decision.amort` 恆為 `None`＝那個欄位從未真的被比對過。"""
        legacy = TestR87TheMeterMayNotDropAThrottlingAxis.INCIDENT
        self.assertIn("critical", [r.get("severity") for r in M.bucket_readings(legacy)],
                      "舊帳號 fixture 沒有 critical ⇒ severity 那一半沒被測到")
        for label, payload in (("team", _R89_TEAM), ("legacy", legacy)):
            for ratio in (None, 7.5):
                with self.subTest(shape=label, ratio=ratio):
                    self.assertEqual(r89_decision_drift_problems(
                        _r89_decide, M.bucket_readings(payload), ratio), [])
        self.assertIsNotNone(
            _r89_decide(_r89_state(M.bucket_readings(_R89_TEAM), True), 7.5).amort,
            "fixture 沒觸發攤提 ⇒ 上面那組 ratio 沒有在多守什麼")

    def test_red_an_aggregator_that_reads_either_field_is_caught(self) -> None:
        """合成注入：把新欄位接進 cap／binding ⇒ 必紅（那是 `worst()` 換個寫法再犯）。"""
        def by_severity(st, ratio):
            d = _r89_decide(st, ratio)
            return dataclasses.replace(d, cap=0) if any(a.severity for a in st.axes) else d

        def by_is_active(st, ratio):
            d, hot = _r89_decide(st, ratio), [a for a in st.axes if a.is_active]
            return dataclasses.replace(d, binding=hot[0]) if hot else d
        for name, fn in (("severity→cap", by_severity), ("is_active→binding", by_is_active)):
            with self.subTest(injection=name):
                self.assertTrue(r89_decision_drift_problems(
                    fn, M.bucket_readings(_R89_TEAM)), "注入了缺陷卻沒轉紅＝零鑑別力")

    def test_severity_is_never_used_to_pick_a_bucket(self) -> None:
        """`test_is_active_is_never_used_to_pick_a_bucket` 的雙生子：`critical` 至今只
        出現在已被判為**保險軸**的池子上 ⇒ 拿它當節流訊號＝把 R89 剛拿掉的否決權從後門
        還回去。把它掛到**低水位**那一軸，決策必須一個位元都不變。"""
        plain = state(("session", 10, 34), ("weekly_all", 90, 8640))
        flagged = Q.QuotaState(
            axes=(axis("session", 10, 34, severity="critical"),
                  axis("weekly_all", 90, 8640, severity="normal")),
            measured_at=NOW.isoformat(), source="endpoint")
        d1, d2 = Q.decide(plain, NOW, P), Q.decide(flagged, NOW, P)
        self.assertEqual((d1.cap, d1.recommended_fanout, d1.binding.kind, d1.band),
                         (d2.cap, d2.recommended_fanout, d2.binding.kind, d2.band))

    def test_the_meter_really_energises_both_fields_end_to_end(self) -> None:
        """**反向判準**（史料見 meter 檔頭）：端到端走到 `read_quota()`，只驗
        `bucket_readings()` 的回傳值等於只驗了半條線。順帶釘住交付座標那句括號註記為假
        ——頂層桶**不是**「一律 `None`」，`spend` 自帶 `severity`。"""
        import tempfile  # noqa: PLC0415 — 與本檔既有的延後 import 同形態

        import quota_gate as G  # noqa: PLC0415
        rows = M.bucket_readings(_R89_TEAM)
        by = {r["kind"]: r for r in rows}
        self.assertIs(by["weekly_all"]["is_active"], False,
                      "`False` 被壓成 `None` ⇒ 「沒給」與「給了 false」分不開")
        self.assertIsNone(by["five_hour"]["is_active"], "頂層真的沒有它，不得偽造")
        path = Path(tempfile.mkdtemp()) / M.CACHE_NAME
        self.assertTrue(M.write_cache({"schema": M.SCHEMA, "axes": rows,
                                       "source": "endpoint", "measured_at":
                                       datetime.now(UTC).astimezone().isoformat()}, path))
        got = {a.kind: (a.is_active, a.severity)
               for a in G.read_quota(datetime.now(UTC), path).axes}
        self.assertEqual((got["session"], got["spend"]),
                         ((True, "normal"), (None, "normal")))

    def test_backward_compatibility_holds_in_both_directions(self) -> None:
        """① `SCHEMA` 不得升版（純追加鍵；升版會把 AutoClaude adapter 拉進同一次 commit
        ＝另一個持有面）；② 通電前寫下的舊快取沒有這兩鍵，`_report()` 不得 KeyError。"""
        self.assertEqual(M.SCHEMA, "autosdd.quota/2")
        old = {"schema": M.SCHEMA, "measured_at": NOW.isoformat(),
               "denominator": {"kind": "undisclosed", "text": "t", "cross_check": None},
               "axes": [{"kind": "session", "pct": 6.0, "resets_at": at(264),
                         "group": "session", "via": "limits[].percent"}]}
        self.assertIn("is_active=None", M._report(old))

# ═══════════════════════════════════════════════════════════════════════════
# M1b 加速訊號必須**穿過 `decide()`**，不是只穿 `axis_cap()`（R82 複驗鏡 ①；
# 立案與複驗鏡實測數字原文＝Pace 證據檔 §7，R89 搬遷體例）。
# ═══════════════════════════════════════════════════════════════════════════
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
        """使用者原句「剩 30Min 就 Reset、還有 100% 沒用 ⇒ 加速」：加一條不緊的長期程
        軸後必須仍成立且不低於中性基準 8（複驗鏡量到 rec=4，方向相反）。"""
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
        """fail-closed 那一半原封不動：期程不明且真的在煞車的軸仍一票否決（不變式＝
        不參與 cap 的軸不得參與 pace；R84／SA-01 史料＝R89 收尾證據檔）。"""
        # 🔴 R89：fixture 由 `spend` 換成 `nimbus_quill`——`spend` 是保險軸、不進 gate，
        # 拿它當煞車軸的例子，測的就不再是本測試宣稱的性質。
        braking = Q.decide(state(("session", 75, 3), ("nimbus_quill", 55, None)), NOW, P)
        self.assertEqual(braking.recommended_fanout, 2, "期程不明的煞車軸必須仍能否決加速")
        self.assertEqual(braking.cap, 4, "它的 cap 也必須真的在（否則它不是煞車軸）")

    def test_red_dropping_the_conjunct_lets_a_braking_null_axis_be_overtaken(self) -> None:
        """🔴 合成注入：拿掉 `r.cap is not None` 的**對偶**——把否決整條移除 ⇒ 上一支的
        情境從 2 變 4 ⇒ fail-closed 那一半有牙齒，不是恆綠。"""
        readings = Q.axes_of(state(("session", 75, 3), ("nimbus_quill", 55, None)), NOW, P)
        no_veto = max(Q._mult(r.horizon, P) for r in readings)      # ＝拿掉整個 if
        base = min(Q._base_rec(r.band, P) for r in readings)
        cap = min(QC.cap_num(r.cap) for r in readings)
        self.assertEqual(Q._pace_of(readings, P), 1.0)
        self.assertEqual(no_veto, 2.0)
        self.assertEqual(Q._bound(Q._clamp(int(base * no_veto), P), int(cap)), 4)

    def test_a_toothless_null_axis_no_longer_vetoes_acceleration(self) -> None:
        """治本那一半：`cap is None`（free 帶）的無期程軸**不得**否決加速（live 形狀
        實測修前 8、修後 16）。R89／QA B-3：fixture 換 `nimbus_quill`（保險軸到不了
        `_pace_of()` ⇒ `spend` 對它零鑑別力），紅端自證同步換軸。"""
        with_none = Q.decide(state(("session", 0, 5), ("nimbus_quill", 0, None)), NOW, P)
        without = Q.decide(state(("session", 0, 5), ("nimbus_quill", 0, 8640)), NOW, P)
        self.assertEqual(with_none.recommended_fanout, 16, "零煞車力的軸仍在從後門煞車")
        self.assertEqual(without.recommended_fanout, 16, "對照組：沒有 null 軸時本來就 16")

    def test_red_the_old_any_none_predicate_halves_the_recommendation(self) -> None:
        """🔴 合成注入：把判準退回舊形態（`any(horizon == NONE)`）⇒ 上一支必紅（8 != 16）。"""
        readings = Q.axes_of(state(("session", 0, 5), ("nimbus_quill", 0, None)), NOW, P)
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
        # 🔴 R89：同上，fixture 由 `spend` 換成 `nimbus_quill`（`spend` 已是保險軸）。
        halting = Q.decide(state(("weekly_all", 96, 5976), ("nimbus_quill", 96, None)),
                           NOW, P)
        self.assertEqual(halting.binding.kind, "nimbus_quill")
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
        """時鐘偏移的負號必須**真的走進** `horizon_band`，那道防線才不是死碼（舊實作
        提前夾 0 ⇒ 負值分支任何生產路徑都到不了＝同一份知識的第二個家）。"""
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
    """獨立於實作的判準：直接掃 pct 0~100，逐 horizon 檢查 cap／rec 非遞增。刻意不
    呼叫 `Q.policy_monotonicity_problems`（被判的對象不能判自己）；這一支掃連續水位、
    模組那一支只取樣帶邊界——兩者對得上才排除「取樣點剛好避開違規」。"""
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


# 🔴 R82／C4：「三個掃描面」從列舉升成硬 gate——四個面每一支檔都必須同時
# `QC.scalar_decision_defs == []` 且 `QC.worst_mentions == []`（不准有人放回去）。
# 立案史料原文＝R89 收尾證據檔；五組注入全綠的病灶全文＝R95 Pace 證據檔 §7-R95-L2。
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
# 病：判準拿生成物跟自己比、從不呼叫消費者的解析器 ⇒ 兩個家互相一致、都沒對消費者測。
# 複審鏡實測（12 個帶值鍵全部解析失敗、照抄範例檔會關掉整條節流）原文＝R95 Pace 證據檔 §7.5。
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
        """逃生口此前只散落在 hook 註解裡，零使用者可讀清單。"""
        names = [spec.name for spec in Q.ENV_SPEC]
        for key in ("AUTOSDD_QUOTA_GUARD_OFF", "AUTOSDD_QUOTA_FANOUT_CAP",
                    "AUTOSDD_SENTINEL_OFF", "AUTOSDD_CONTEXT_GUARD_OFF",
                    "AUTOSDD_RESUME_OFF"):
            self.assertIn(key, names)

    def test_the_resume_off_hatch_reaches_the_process_env_from_dot_env(self) -> None:
        """🔴 R97（round-label-ok：非帳本追蹤的正式輪，僅沿用便於追蹤的標籤）：`AUTOSDD_RESUME_OFF` 此前只讀 `os.environ`，`.env` 設了也關不掉——

        `session_resume_planner.py` 要 Windows `[Environment]::SetEnvironmentVariable`
        寫登錄檔＋整個重啟 Claude Code 才吃得到。補進白名單後，同一份前置填充機制
        （`quota_gate.apply_env_defaults`）必須也能把它從 `.env` 帶進 `os.environ`。
        """
        spec = next(s for s in Q.ENV_SPEC if s.name == "AUTOSDD_RESUME_OFF")
        self.assertEqual(spec.kind, "flag")
        self.assertIsNone(spec.attr, "逃生口不得誤植進 Policy 欄位")
        self.assertEqual(spec.section, "escape")

    def test_the_disk_file_matches_the_generator_once_it_lands(self) -> None:
        """接線後 `.env.example` 必須逐字等於生成物。誠實劃界：刻意不寫 skip（skip 會
        被當成通過）而是「存在才判」——紅綠已由上面三支注入自證，這一支只負責在接線
        落地那一刻自動長出牙齒。"""
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
        """🔴 ⑦ 的紅綠自證：chunk 級判準被「拿掉分隔符」矇混（第二個百分比坐在第一個
        桶的名牌旁即放行）；百分比級判準逐個問 ⇒ 抓到兩筆。"""
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
# M8-b 檔案契約的**路徑**那一半（R83／F2-①）：判準＝兩邊算路徑的「家」token 序列相等
# ——搬家可以，但必須同一次 commit 動兩支檔。立案與取捨原文＝R95 Pace 證據檔 §7。
# ═══════════════════════════════════════════════════════════════════════════
#: 「家」只可能來自這幾個地方——刻意白名單（抓所有識別字會把寫法差異也算進去＝假紅，
#: 第一版實測如此；假紅的鎖活不過一輪）。
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
#: 規格 S7 的失效字面（`no-horizon` 那一列有桶，不在本表）。本表是「每個字面都必須
#: 被 M9 兩條不變量掃過」的登記處（家在 `quota_meter.REASON_*`；同步由
#: `TestMeterReasonsAreAllRegistered` 機械守）。keychain-timeout 立案全文＝Pace 證據檔 §7-R95-L3。
_UNMEASURABLE_REASONS = (
    "no-credentials", "no-credentials-darwin", "keychain-timeout",
    "http-401", "http-5xx", "meter-unreachable", "no-buckets",
    "stale-cache", "expired-cache", "schema-mismatch", "no-cache",
)


# 🔴 立案（R83／F2-③，同 `TestM8SchemaStaysInSync` 形狀）：漏登記＝失明而 rc 全綠。
# 分母是**現查** meter 的 `REASON_*` 宣告集合，不是寫死清單。全文＝Pace 證據檔 §7-R95-L5。
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
            # 🔴 R89：`spend` → `weekly_all`（保險軸不進 cap 聚合，拿它測 cap 會失準）。
            axes=(axis("weekly_all", 88, None), axis("nimbus_quill", 0, None)),
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
# 病＝乘數寫死的 dict 結構上不可能被參數化；開放後的新危害＝「near < far」這種跨鍵
# 關係錯誤會讓加速變減速。立案全文＝R95 Pace 證據檔 §7-R95-L4。
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
                       for ts, s, lg, _fp in W.SEED_OBSERVATIONS)
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


class TestR93PlanChangeAdaptiveAmortization(unittest.TestCase):
    """R93／DEF-200-122：換方案/換帳號的分區過濾（`filter_by_signature`）。分區優於
    偵測——過濾發生在 `segments()`／`estimate_ratio()` 之前，兩者零改動。
    """

    def test_row_of_round_trips_the_signature(self) -> None:
        text = W.row_of("2026-08-16T00:00:00+08:00",
                        (("five_hour", 10.0), ("seven_day", 20.0)),
                        fp=("five_hour", "session"))
        rows = W.rows_from_jsonl(text)
        self.assertEqual(rows[0][3], ("five_hour", "session"))

    def test_legacy_rows_without_fp_key_parse_to_none(self) -> None:
        """本輪落地之前寫下的舊落款沒有 `fp` 鍵 ⇒ 必須解成 `None`，不是 `()`。"""
        line = json.dumps({"ts": "2026-08-16T00:00:00+08:00",
                           "pct": {"five_hour": 10.0, "seven_day": 20.0}})
        rows = W.rows_from_jsonl(line + "\n")
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0][3])

    def test_filter_by_signature_excludes_none_even_when_signature_is_empty(self) -> None:
        rows = [("t1", 1.0, 2.0, None)]
        self.assertEqual(W.filter_by_signature(rows, ()), [])

    def test_filter_by_signature_is_symmetric_for_shrink_and_grow(self) -> None:
        """🔴 SA 條件②，本規格最重要的一支：雙向都要驗，不能只驗其一。"""
        sig_a = ("extra_usage", "five_hour", "session")   # 大→小：extra_usage 之後消失
        sig_b = ("five_hour", "session", "weekly_scoped")  # 小→大：weekly_scoped 新增
        rows_a = [("2026-08-01T00:00:00+08:00", 1.0, 70.0, sig_a),
                 ("2026-08-01T01:00:00+08:00", 10.0, 71.0, sig_a)]
        rows_b = [("2026-08-02T00:00:00+08:00", 2.0, 60.0, sig_b),
                 ("2026-08-02T01:00:00+08:00", 12.0, 61.0, sig_b)]
        mixed = rows_a + rows_b
        only_a = W.filter_by_signature(mixed, sig_a)
        only_b = W.filter_by_signature(mixed, sig_b)
        self.assertEqual(only_a, [(r[0], r[1], r[2]) for r in rows_a])
        self.assertEqual(only_b, [(r[0], r[1], r[2]) for r in rows_b])
        self.assertTrue(all(row not in only_b for row in only_a), "大→小的樣本混進了另一池")
        self.assertTrue(all(row not in only_a for row in only_b), "小→大的樣本混進了另一池")

    def test_seed_observations_never_enter_any_pool(self) -> None:
        for signature in ((), ("five_hour",), ("five_hour", "seven_day")):
            with self.subTest(signature=signature):
                self.assertEqual(
                    W.filter_by_signature(list(W.SEED_OBSERVATIONS), signature), [])

    def test_estimate_ratio_on_a_fresh_signature_falls_back_safely(self) -> None:
        rows = [("2026-08-01T00:00:00+08:00", 1.0, 70.0, ("five_hour", "seven_day")),
               ("2026-08-01T01:00:00+08:00", 10.0, 71.0, ("five_hour", "seven_day"))]
        pool = W.filter_by_signature(rows, ("session", "weekly_all"))
        self.assertEqual(pool, [])
        ratio, note = W.estimate_ratio(pool)
        self.assertIsNone(ratio)
        self.assertIn("無可用區段", note)
        self.assertIsNone(W.amortize((("five_hour", 40.0),), (100.0,), (300.0,), ratio, note))

    def test_the_amortization_floor_survives_arbitrary_ratio_sourced_from_a_filtered_pool(
            self) -> None:
        """🔴 SA 條件④，最關鍵的不變式：`shown_pct >= raw_pct` 不因換算比的來源改變而破。"""
        sig = ("five_hour", "seven_day")
        rows = [("2026-08-01T00:00:00+08:00", 1.0, 70.0, sig),
               ("2026-08-01T01:00:00+08:00", 10.0, 71.0, sig),
               ("2026-08-01T02:00:00+08:00", 20.0, 72.0, sig),
               ("2026-08-01T03:00:00+08:00", 30.0, 73.0, sig)]
        for signature in (sig, ("session",)):   # 同指紋（有樣本）／陌生指紋（無樣本）
            with self.subTest(signature=signature):
                pool = W.filter_by_signature(rows, signature)
                ratio, note = W.estimate_ratio(pool)
                shown = W.band_inputs((("five_hour", 40.0), ("seven_day", 75.0)),
                                     (100.0, 9000.0), (300.0, 10080.0), ratio, 95.0, note)[0]
                self.assertGreaterEqual(shown[0], 40.0, f"ratio={ratio} 讓攤提放寬了")

    def test_cross_signature_isolation_end_to_end(self) -> None:
        sig_x, sig_y, sig_z = (("five_hour", "session"), ("five_hour", "weekly_all"),
                               ("seven_day", "session"))
        rows = [("2026-08-01T00:00:00+08:00", 1.0, 61.0, sig_x),
               ("2026-08-01T01:00:00+08:00", 2.0, 62.0, sig_x),
               ("2026-08-02T00:00:00+08:00", 5.0, 65.0, sig_y),
               ("2026-08-02T01:00:00+08:00", 6.0, 66.0, sig_y),
               ("2026-08-03T00:00:00+08:00", 10.0, 70.0, sig_z),
               ("2026-08-03T01:00:00+08:00", 11.0, 71.0, sig_z)]
        for target in (sig_x, sig_y, sig_z):
            with self.subTest(target=target):
                filtered = W.filter_by_signature(rows, target)
                self.assertEqual(len(filtered), 2)
                others = [r for r in rows if r[3] != target]
                self.assertTrue(all((r[0], r[1], r[2]) not in filtered for r in others),
                                f"{target} 的過濾結果混進了別的指紋")


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
    """R87 事故鎖：**取數層不得把「已撞頂但自報 `enabled:false`」的軸丟掉**（判讀層
    只保證給定的軸不被放寬，不保證軸不消失）。立案史料原文＝R89 收尾證據檔
    〈護欄層史料搬遷（R89 收尾批）〉節（路徑見檔頭）。
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

    def test_the_incident_payload_still_carries_both_axes_end_to_end(self) -> None:
        """端到端：逐軸讀數原封不動，只有 cap 聚合不吃它們。判準刻意不守「結論必須是
        halt」（正確與 R87 錯誤實作四欄逐字相同＝假鎖）。史料＝R89 證據檔。"""
        d = Q.decide(self._state_from(M.bucket_readings(self.INCIDENT)), NOW, P)
        seen = {r.axis.kind: r for r in d.per_axis}
        for kind in ("spend", "extra_usage"):
            self.assertIn(kind, seen, f"{kind} 從 per_axis 消失＝R87 原樣復發")
            self.assertEqual(seen[kind].axis.pct, 100.0, "水位被改寫")
            self.assertEqual(seen[kind].band, Q.BAND_HALT, "逐軸帶別被放寬")
            self.assertEqual(seen[kind].cap, 0, "逐軸 cap 被放寬")
            self.assertIn(f"kind={kind} 100%", Q.describe(d), "人看的那一面少一軸")
        # 🔴 R89 收尾：舊斷言 `assertEqual(d.cap, 1)`＝那道地板的契約，地板已拆（三條理由
        # ＝`quota_policy.decide()` 的墓碑段）。改守它拆掉才回來的**不變式**：cap 由 binding
        # 解釋，否則取 binding `resets_at` 的人機訊息會講另一條軸的 reset＝假話。
        self.assertEqual(d.cap, seen[d.binding.kind].cap, "cap 不再由 binding 解釋")
        self.assertNotIn(d.binding.kind, Q.FALLBACK_KINDS, "binding 落在保險軸")

    def test_the_lock_discriminates(self) -> None:
        """合成注入自證：**重演** R87 那個錯誤實作，必須被抓到。判準指向 R87 真正的
        差異＝**軸在不在**（舊版「重演組必須不再 halt」已恆真＝假鎖）。"""
        dropped = [r for r in M.bucket_readings(self.INCIDENT)
                   if r["kind"] not in ("spend", "extra_usage")]
        self.assertTrue(dropped, "重演組不得為空，否則本自證無鑑別力")
        d_broken = Q.decide(self._state_from(dropped), NOW, P)
        kinds = {r.axis.kind for r in d_broken.per_axis}
        self.assertNotIn("spend", kinds, "重演組沒把軸拿掉＝這個自證沒有在重演 R87")
        self.assertNotIn("extra_usage", kinds)
        # 🔴 R89 收尾：舊斷言 `assertNotEqual(d_broken.cap, 1)` 隨地板作廢；反向判準改指
        # 第二個出口（`per_axis` 與 `describe()` 各自會失明，R87 是兩條同時失明）。
        self.assertNotIn("kind=spend ", Q.describe(d_broken), "掉軸之後人看的那一面仍印得出它")

    def test_disabled_is_not_a_reason_to_drop_an_axis(self) -> None:
        """`enabled:false` 本身**不得**成為排除依據：同一份 payload 只把布林翻成 True，
        兩者收到的軸集合必須逐字相同（那是這次事故裡唯一被動過的那一行）。"""
        enabled = {k: (dict(v, **({"enabled": True} if "enabled" in v else {}),
                          **({"is_enabled": True} if "is_enabled" in v else {}))
                       if isinstance(v, dict) else v)
                   for k, v in self.INCIDENT.items()}
        self.assertEqual(
            {r["kind"] for r in M.bucket_readings(self.INCIDENT)},
            {r["kind"] for r in M.bucket_readings(enabled)})


class TestR87AccountPostureIsKnownBeforeDispatch(unittest.TestCase):
    """R87：**派工前**要先知道 Account Type 與有沒有可用 credits（掌舵者裁決）。

    立案逐字與事故機制史料＝R89 收尾證據檔（路徑見檔頭）。
    結論：**credits 是「還有沒有救」的布林，不是節流軸**。"""

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
        """指紋＝軸組合（payload 沒有方案名），不是拿去查一組寫死的參數。"""
        p = M.account_posture(self.INCIDENT)
        self.assertIn("spend", p["plan_fingerprint"])
        self.assertIn("session", p["plan_fingerprint"])
        self.assertEqual(p["plan_fingerprint"], tuple(sorted(p["plan_fingerprint"])))


class TestR93AccountKeyIsDerivedFromExistingResponseHeaders(unittest.TestCase):
    """R93／DEF-200-114（Architect REJECT 承接）：帳號身分訊號＝
    `sha256(org-id:workspace-id)[:12]`，取自 `fetch_usage()` 已在發的回應標頭；純函式
    測試（零網路）。立案史料與真實對照組＝`docs/06_quality/
    Quota_R90_CrossAccount_Experiment.md` §2.5。
    """

    ORG_A, WS_A = "8b63e143-0d4a-4c6a-a0fc-53229d07b7f5", "wrkspc_01RVxG93ofY2Rq2SQyNhqHm5"
    ORG_B, WS_B = "c7716c3e-4510-4d6e-9473-6c639f6c77d6", "wrkspc_01AaQ7rxzXCosJbx4LkJXQnn"

    def _headers(self, org: str, ws: str) -> dict:
        return {M.ORG_HEADER: org, M.WORKSPACE_HEADER: ws}

    def test_both_headers_present_yields_a_deterministic_short_hash(self) -> None:
        """R90 §2.5 一手實測值：兩個真實帳號的標頭 → 兩個相異、穩定的 12-hex 摘要。"""
        key = M.account_key_of(self._headers(self.ORG_B, self.WS_B))
        self.assertEqual(key, "34cd3507237f", "與 R90 §2.5 的一手實測值不符")
        self.assertEqual(key, M.account_key_of(self._headers(self.ORG_B, self.WS_B)),
                         "同輸入兩次呼叫必須逐字相同")

    def test_two_real_accounts_from_r90_give_different_keys(self) -> None:
        """這正是要解的盲區：同方案換帳號時，兩個帳號的 key 必須不同。"""
        self.assertNotEqual(M.account_key_of(self._headers(self.ORG_A, self.WS_A)),
                            M.account_key_of(self._headers(self.ORG_B, self.WS_B)))

    def test_either_header_missing_or_blank_is_unmeasurable(self) -> None:
        """量不到 ≠ 量到零：缺席／空字串／非字串一律回 `None`，不得猜。"""
        for headers in ({}, {M.ORG_HEADER: self.ORG_A}, {M.WORKSPACE_HEADER: self.WS_A},
                        {M.ORG_HEADER: "", M.WORKSPACE_HEADER: self.WS_A},
                        {M.ORG_HEADER: "  ", M.WORKSPACE_HEADER: self.WS_A},
                        {M.ORG_HEADER: 123, M.WORKSPACE_HEADER: self.WS_A}, None, []):
            with self.subTest(headers=headers):
                self.assertIsNone(M.account_key_of(headers))

    def test_the_headers_are_not_credentials_and_never_appear_in_the_key(self) -> None:
        """R90 §2.5／§3.2：標頭不是憑證。雜湊後的輸出不得逐字含任一原始標頭值。"""
        key = M.account_key_of(self._headers(self.ORG_B, self.WS_B))
        self.assertNotIn(self.ORG_B, key)
        self.assertNotIn(self.WS_B, key)


class TestR89TheFallbackSetMayNotSwallowASubscriptionAxis(unittest.TestCase):
    """🔴 R89／Architect 複審②：`FALLBACK_KINDS` 是新開的繞過面，本鎖是它唯一的觀測者。
    立案實測與 R89 收尾的判準翻面（黑名單 → 白名單）史料＝R89 收尾證據檔。"""

    #: 🔴 R89 收尾／QA 複審 N1：判準由「黑名單四個訂閱軸」翻成**白名單以外一律紅**（舊黑
    #: 名單只罩 7 個活體軸中的 4 個，注入 `weekly_scoped` 紅 0 支＝對它完全失明）。前三個
    #: 成員的出處＝PRD `:78`；`spend` PRD 未列，是端點頂層鍵，由 payload 實測補入。
    ALLOWED_FALLBACK = frozenset({"extra_usage", "overage", "spend",
                                  "seven_day_overage_included"})
    #: 舊黑名單，只留給下一支注入自證當對照組（不再是任何生效判準）。
    OLD_BLACKLIST = frozenset({"session", "five_hour", "seven_day", "weekly_all"})

    def test_no_subscription_axis_is_ever_a_fallback_axis(self) -> None:
        """四條一起：白名單以外一律不得是保險軸／兩家是**包含**不是相等／PRD 明列的
        overage 類必須在／訂閱軸撞線仍然 halt。"""
        self.assertEqual(Q.FALLBACK_KINDS - self.ALLOWED_FALLBACK, set(),
                         "保險集吞了一個沒有出處的 kind＝主節流可能被整條關掉")
        # 🔴 SA 複審 B-3：由 `==` 改為**子集**——兩者命名空間不同（頂層美元池 vs bucket
        # kind），今天恰好同值卻被焊死 ⇒「補齊保險軸」這件事本身會轉紅（本輪實測到）。
        self.assertLessEqual(frozenset(M.CREDIT_POOL_KEYS), Q.FALLBACK_KINDS,
                             "美元計價池不是保險軸 ⇒ 它會進 cap 聚合＝憲法裁決被繞過")
        # PRD `:78` 的 overage 類：取數層原樣帶出 kind ⇒ 漏列＝本輪剛治好的病原樣復發。
        self.assertLessEqual({"overage", "seven_day_overage_included"}, Q.FALLBACK_KINDS)
        # 排除「這道放寬只准作用在保險軸上」：訂閱軸自己撞線必須仍然 cap=0。
        self.assertEqual(
            Q.decide(state(("five_hour", 96, 30), ("spend", 0, None)), NOW, P).cap, 0,
            "訂閱軸撞停止水位卻沒 halt ⇒ 這道改動放寬到了不該放寬的地方")

    def test_red_the_old_blacklist_was_blind_to_the_axes_it_did_not_name(self) -> None:
        """🔴 合成注入：`weekly_scoped` 被吞——舊黑名單全綠，新白名單必紅。"""
        injected = Q.FALLBACK_KINDS | {"weekly_scoped"}
        self.assertEqual(injected & self.OLD_BLACKLIST, frozenset(), "舊判準對它全綠")
        self.assertNotEqual(injected - self.ALLOWED_FALLBACK, set(), "新判準必須紅")


class TestR89UnknownKindsAreLoudButNeverReclassified(unittest.TestCase):
    """🔴 R89 收尾／SA 複審 B-3 末項：未知 kind（live 實測 `nimbus_quill`）的**預設分類**
    ＝維持訂閱軸／保守側，但必須出聲。兩個方向缺一即假鎖：①`note` 與 `reason` 兩個出口都
    要看得到；②`KNOWN_KINDS` 的成員資格對 `band`／`cap`／`rec` 必須**零影響**，否則它就
    變成檔頭紀律「禁止寫死桶名清單」真正要禁的那種東西（過期即靜默答錯）。
    史料＝R89 收尾證據檔（路徑見檔頭）。"""

    KNOWN_PAIR = (("session", 10, 60), ("seven_day", 88, 30))

    def test_an_unknown_kind_says_so_in_both_outlets(self) -> None:
        d = Q.decide(state(("session", 10, 60), ("nimbus_quill", 0, None)), NOW, P)
        seen = {r.axis.kind: r for r in d.per_axis}
        self.assertIn(Q.NOTE_UNKNOWN, seen["nimbus_quill"].note, "note 出口沒說")
        self.assertIn(Q.NOTE_UNKNOWN, d.reason, "reason 出口沒說")
        self.assertNotIn(Q.NOTE_UNKNOWN, seen["session"].note, "已知軸被誤標")

    def test_membership_changes_nothing_but_the_note(self) -> None:
        """②：同一組讀數換一個「已知」的軸名，三個決策欄必須逐字相同。"""
        unknown = Q.decide(state(("session", 10, 60), ("nimbus_quill", 88, 30)), NOW, P)
        known = Q.decide(state(*self.KNOWN_PAIR), NOW, P)
        self.assertEqual(
            (unknown.cap, unknown.recommended_fanout, unknown.band),
            (known.cap, known.recommended_fanout, known.band),
            "未知 kind 的成員資格改變了決策 ⇒ 它已經在分類，而過期的名單會靜默答錯")

    def test_red_a_stale_vocabulary_only_adds_noise(self) -> None:
        """🔴 合成注入（fail-safe 方向）：把一個**已知**軸從詞彙表拿掉 ⇒ 只多一句話、
        三個決策欄一格不動＝「名單過期只會多說、不會答錯」那句宣稱的證明。"""
        before = Q.decide(state(*self.KNOWN_PAIR), NOW, P)
        with mock.patch.object(Q, "KNOWN_KINDS", Q.KNOWN_KINDS - {"seven_day"}):
            after = Q.decide(state(*self.KNOWN_PAIR), NOW, P)
        self.assertEqual((before.cap, before.recommended_fanout, before.band),
                         (after.cap, after.recommended_fanout, after.band))
        self.assertNotIn(Q.NOTE_UNKNOWN, before.reason)
        self.assertIn(Q.NOTE_UNKNOWN, after.reason, "詞彙表少一項卻沒多說＝觀測者失效")


# ═══════════════════════════════════════════════════════════════════════════
# R95 配速致動器三合一：攤提窗尾修正／模型降級建議／PACE_INDEX 與可調配速上限
# 立案史料與設計辯護＝docs/06_quality/CrossPlatform_R95_Pace_Actuator_Evidence.md
# ═══════════════════════════════════════════════════════════════════════════
class TestR95AmortizationSpeaksButDoesNotTightenBelowConverge(unittest.TestCase):
    """掌舵者 2026-08-16 裁決：長窗自軸未達 converge 錨點 ⇒ 攤提**出聲不收緊**
    （窗尾額度 use-it-or-lose-it、weekly 同一消耗池 ⇒ 空等純浪費牆鐘）。
    立案實案數字全文＝Pace 證據檔 §2。
    """

    HELM = (("five_hour", 25.0, 33.0), ("seven_day", 46.0, 4000.0))
    ARGS = ((("five_hour", 25.0), ("seven_day", 46.0)), (33.0, 4000.0), (300.0, 10080.0))

    def test_the_helm_case_is_no_longer_pressed_by_amortization(self) -> None:
        """生產路徑（`decide` 帶 ratio）：長窗 free band ⇒ 短窗不再被推導水位壓制。"""
        d = Q.decide(state(*self.HELM), NOW, P, 1.0, "r95")
        self.assertIsNone(d.cap, f"長窗 free band 仍被攤提壓制：{Q.describe(d)}")
        self.assertIsNotNone(d.amort, "出聲那一半不見了（amort 必須照算照回）")
        self.assertNotIn(W.NOTE_AMORT, d.reason, "水位沒被調高就不該掛 amortized 註記")

    def test_red_the_unconditional_form_still_tightens_the_same_input(self) -> None:
        """合成注入自證：不帶 converge 錨點（＝R94 版行為）同一組輸入**必被**壓制。"""
        old = W.band_inputs(*self.ARGS, 1.0, 95.0)[0]
        new = W.band_inputs(*self.ARGS, 1.0, 95.0, converge_pct=70.0)[0]
        self.assertGreater(old[0], 25.0, "對照組失去鑑別力：R94 版本來就會壓制這一格")
        self.assertEqual(new[0], 25.0, "出聲不收緊：餵 pct_band 的水位必須是原值")
        self.assertIsNotNone(W.band_inputs(*self.ARGS, 1.0, 95.0, converge_pct=70.0)[1])

    def test_at_or_above_the_converge_anchor_nothing_relaxes(self) -> None:
        """方向鎖：長窗自軸 ≥ converge（含錨點本身＝fail-safe 側）⇒ 逐格等於 R94 版。"""
        for long_pct in (70.0, 75.0, 99.0):
            pcts = (("five_hour", 40.0), ("seven_day", long_pct))
            with self.subTest(long_pct=long_pct):
                self.assertEqual(
                    W.band_inputs(pcts, (100.0, 9000.0), (300.0, 10080.0), 1.0, 95.0,
                                  converge_pct=70.0)[0],
                    W.band_inputs(pcts, (100.0, 9000.0), (300.0, 10080.0), 1.0, 95.0)[0])

    def test_the_feed_never_drops_below_the_raw_pct_for_any_anchor(self) -> None:
        """不變式 `shown >= raw`（SA 條件④）對任何 converge 值仍成立，含 `None`。"""
        for converge in (None, 0.0, 50.0, 70.0, 100.0):
            shown = W.band_inputs((("five_hour", 40.0), ("seven_day", 46.0)),
                                  (100.0, 9000.0), (300.0, 10080.0), 7.0, 95.0,
                                  converge_pct=converge)[0]
            with self.subTest(converge=converge):
                self.assertGreaterEqual(shown[0], 40.0)
                self.assertEqual(shown[1], 46.0, "攤提不得動長窗那一軸的水位")

    def test_explain_says_out_loud_that_it_did_not_tighten(self) -> None:
        cool = W.amortize(*self.ARGS, 1.0, "n=1")
        hot = W.amortize((("five_hour", 40.0), ("seven_day", 75.0)),
                         (100.0, 9000.0), (300.0, 10080.0), 1.0, "n=1")
        self.assertIn("出聲不收緊", W.explain(cool, converge_pct=70.0))
        self.assertIn("攤提", W.explain(cool, converge_pct=70.0), "免除不得吃掉整行說明")
        self.assertNotIn("出聲不收緊", W.explain(cool), "錨點不明＝維持 R94 字面")
        self.assertNotIn("出聲不收緊", W.explain(hot, converge_pct=70.0))


class TestR95ModelHintOnlyInTighteningBands(unittest.TestCase):
    """PRD §4.2.3 第 7 步／致動器表：模型降級**建議**。方向鎖兩條：
    ① hint 只在收緊帶出現（converge 帶起；模型分軌 kind 為 notice 帶起＝PRD
    `MODEL_DOWNGRADE_PERCENT=50` 出廠值逐格對齊）；② cap 完全不受 hint 影響
    （建構順序保證：`decide()` 先算完 cap／rec 才產生 hint）。"""

    def test_no_hint_below_the_tightening_bands(self) -> None:
        for kind, pct in (("session", 0), ("session", 55), ("session", 69),
                          ("weekly_scoped", 0), ("weekly_scoped", 49)):
            with self.subTest(kind=kind, pct=pct):
                self.assertEqual(
                    Q.decide(state((kind, pct, 8640)), NOW, P).model_hint, "")

    def test_a_model_scoped_axis_hints_from_the_notice_band(self) -> None:
        """模型分軌（weekly_scoped）在 notice 帶（≥50）就建議＝PRD 第 7 步的水位。"""
        d = Q.decide(state(("weekly_scoped", 55, 8640)), NOW, P)
        self.assertIn("weekly_scoped", d.model_hint)
        self.assertEqual(Q.decide(state(("session", 55, 8640)), NOW, P).model_hint,
                         "", "非模型分軌的 notice 帶不該觸發（那是 converge 的事）")

    def test_any_tight_axis_hints_from_the_converge_band(self) -> None:
        for pct in (70, 85, 96):
            with self.subTest(pct=pct):
                self.assertIn("session",
                              Q.decide(state(("session", pct, 8640)), NOW, P).model_hint)

    def test_the_hint_never_moves_a_single_decision_bit(self) -> None:
        """S4-10 的釘值（cap 2／rec 1）在 hint 出現時逐格不變。"""
        d = Q.decide(state(("session", 75, 8640)), NOW, P)
        self.assertEqual((d.cap, d.recommended_fanout), (2, 1))
        self.assertTrue(d.model_hint)

    def test_a_healthy_subscription_is_not_hinted_by_the_fallback_pool(self) -> None:
        """R89 同判：保險軸不進 cap 聚合，也不由它觸發降級建議。"""
        d = Q.decide(state(("spend", 88, None), ("session", 20, 30)), NOW, P)
        self.assertEqual(d.model_hint, "")

    def test_unmeasured_never_hints(self) -> None:
        st = Q.QuotaState(axes=(), measured_at=NOW.isoformat(), source="cache",
                          reason="stale-cache")
        self.assertEqual(Q.decide(st, NOW, P).model_hint, "")

    def test_the_screen_line_appears_only_with_a_hint(self) -> None:
        import quota_messages as QM  # noqa: PLC0415 — 與本檔既有的延後 import 同形態
        tight = Q.decide(state(("weekly_scoped", 75, 8640)), NOW, P)
        free = Q.decide(state(("weekly_scoped", 20, 8640)), NOW, P)
        self.assertIn("sonnet/haiku", QM.model_hint_line(tight))
        self.assertIn("weekly_scoped", QM.model_hint_line(tight))
        self.assertEqual(QM.model_hint_line(free), "", "free 帶印降級建議＝一句假話")


class TestR95PaceIndexAndTunableCeiling(unittest.TestCase):
    """PRD §4.2.8：`pace_index` 比值形式（供人讀與校準）與 `lead_pp` 差值形式（供決策）
    並存；`AUTOSDD_QUOTA_PACE_CEILING` 預設 1.0＝逐位元維持現行「任何超前即減速」。"""

    def test_the_ratio_form_matches_the_prd_formula(self) -> None:
        self.assertAlmostEqual(W.pace_index(74.0, 8064.0, 10080.0), 3.7)
        self.assertAlmostEqual(W.pace_index(74.0, 1008.0, 10080.0), 74.0 / 90.0)
        for bad in ((74.0, None, 10080.0), (74.0, -5.0, 10080.0), (74.0, 100.0, None)):
            with self.subTest(bad=bad):
                self.assertIsNone(W.pace_index(*bad))

    def test_the_denominator_floor_prevents_blowup_at_window_start(self) -> None:
        self.assertEqual(W.pace_index(5.0, 300.0, 300.0), 5.0)

    def test_the_default_ceiling_keeps_the_shipped_burn_step_verbatim(self) -> None:
        """預設 1.0 ⇒ 超前判定逐位元等於既有 `lead > 0`（含省與中性兩側）。"""
        for pct in (0.0, 5.0, 40.0, 74.0, 96.0):
            for minutes in (33.0, 100.0, 1008.0, 8064.0, 10080.0):
                lead = W.lead_pp(pct, minutes, 10080.0)
                want = (1 if lead > 0 else
                        (-1 if lead <= -W.anchor_margin_pp(10080.0) else 0))
                with self.subTest(pct=pct, minutes=minutes):
                    self.assertEqual(W.burn_step(pct, minutes, 10080.0)[0], want)

    def test_a_raised_ceiling_releases_the_brake_but_never_grants_speed(self) -> None:
        """方向鎖：調高上限只把「超前⇒強制 far」放回中性，絕不越過絕對門檻版。"""
        eased = dataclasses.replace(P, pace_ceiling=1e9)
        _looser, unlicensed = QC.unlicensed_acceleration(eased, Q, W, NOW)
        self.assertEqual(unlicensed, [], "調高配速上限造出了無節省證據的放寬")
        self.assertEqual(W.burn_step(74.0, 100.0, 300.0, 1e9), (0, ""))
        self.assertEqual(W.burn_step(74.0, 100.0, 300.0), (1, W.NOTE_AHEAD))

    def test_the_ceiling_reaches_the_production_path(self) -> None:
        """five_hour 74%@100min（pace_index≈1.11）：預設判超前（far、cap 2）；
        上限調高後回中性（mid、cap 4）——仍逐格等於 R85 絕對門檻版的 cap 4。"""
        tight = QC.new_axis(P, Q, NOW, "five_hour", 74.0, 100.0)
        eased = QC.new_axis(dataclasses.replace(P, pace_ceiling=1e9), Q, NOW,
                            "five_hour", 74.0, 100.0)
        self.assertEqual((tight.horizon, tight.cap), (Q.AXIS_FAR, 2))
        self.assertEqual((eased.horizon, eased.cap), (Q.AXIS_MID, 4))
        self.assertEqual(QC.r85_axis(P, Q, 74.0, 100.0)[1], 4, "中性不得越過對照組")

    def test_the_ceiling_is_declared_bounded_and_reaches_the_policy(self) -> None:
        policy, problems = Q.load_policy({"AUTOSDD_QUOTA_PACE_CEILING": "1.5"})
        self.assertEqual(problems, [])
        self.assertEqual(policy.pace_ceiling, 1.5)
        bad, problems = Q.load_policy({"AUTOSDD_QUOTA_PACE_CEILING": "0.5"})
        self.assertTrue(problems, "低於 1 的上限被靜默接受（會反轉節儉判定）")
        self.assertEqual(bad.pace_ceiling, 1.0, "壞值必須採用預設")
        self.assertIn("AUTOSDD_QUOTA_PACE_CEILING", Q.render_env_example())

    def test_explain_carries_the_pace_index(self) -> None:
        amort = W.amortize((("five_hour", 16.0), ("seven_day", 75.0)),
                           (2520.0, 4320.0), (300.0, 10080.0), 7.0, "n")
        self.assertIn("pace_index=", W.explain(amort))


# ═══════════════════════════════════════════════════════════════════════════
# R95 修4（PRD R-4.5.6-5／A3；ADR §2.9）：halt 武裝分支不得只看 binding 單軸；方向鎖＝
# 只准更早喚醒、絕不把可等的 reset 判成 escalate。事故立案全文＝Pace 證據檔 §7-R95-修4。
# ═══════════════════════════════════════════════════════════════════════════
class TestR95HaltArmsOffTheEarliestResettableAxis(unittest.TestCase):
    def test_the_incident_shape_now_arms_instead_of_escalating(self) -> None:
        """A3 前半＝事故重演（紅面：修前 binding 單軸判 escalate，本測試必紅）。
        binding 軸無 reset 的訂閱側重現：halt 帶兩軸 cap 同為 0（優先權判例只管平手時
        的 cap），`-remaining=-INF` 的那一軸依 `_binding_key` 勝出。"""
        d = Q.decide(state(("session", 96, None), ("five_hour", 96, 188)), NOW, P)
        self.assertIsNone(d.binding.resets_at,
                          "前提破了：binding 必須是無期程那一軸才有鑑別力")
        self.assertEqual(QM.halt_resets_at(d), at(188), "沒取到 ≥halt 中最早可 reset 軸")
        self.assertEqual(QM.reset_branch(QM.halt_resets_at(d), NOW), QM.QUOTA_BRANCH_ARM)
        # 事故原形自證：對照組（binding 單軸）確實是 escalate——修的正是這一格。
        self.assertEqual(QM.reset_branch(QM.binding_resets_at(d), NOW),
                         QM.QUOTA_BRANCH_ESCALATE)

    def test_the_literal_incident_binding_shape_is_also_covered(self) -> None:
        """事故閂鎖逐字 `halt@extra_usage@None`＝binding 落在保險軸（R89 起保險軸不進
        gate，這只在全軸皆保險的 `or readings` fail-safe 路上成立）——這一格也要 arm：
        錯付的代價是一次探測，漏喚醒的代價是空轉八小時。"""
        d = Q.decide(state(("extra_usage", 100, None),
                           ("seven_day_overage_included", 96, 188)), NOW, P)
        self.assertEqual(d.binding.kind, "extra_usage", "前提：重現事故閂鎖的 binding")
        self.assertEqual(QM.reset_branch(QM.halt_resets_at(d), NOW), QM.QUOTA_BRANCH_ARM)

    def test_no_resettable_axis_anywhere_still_escalates(self) -> None:
        """A3 後半：全軸皆無 reset ⇒ 仍 escalate（提額是唯一的路，排程等於白等）。"""
        d = Q.decide(state(("extra_usage", 100, None), ("spend", 96, None)), NOW, P)
        self.assertIsNone(QM.halt_resets_at(d))
        self.assertEqual(QM.reset_branch(QM.halt_resets_at(d), NOW),
                         QM.QUOTA_BRANCH_ESCALATE)

    def test_the_choice_is_directionally_locked(self) -> None:
        """方向鎖三格：①只會更早不會更晚（候選含 binding 自己 ⇒ min 不可能更晚）；
        ②未到 halt 的軸不得進候選（醒在它的 reset 上是白醒——那一刻 halt 軸仍滿）；
        ③遠 reset 走 notify 而非 arm（R59 同形防護）、也絕非 escalate。"""
        self.assertEqual(QM.halt_resets_at(
            Q.decide(state(("session", 97, 300), ("five_hour", 96, 120)), NOW, P)), at(120))
        self.assertEqual(QM.halt_resets_at(
            Q.decide(state(("session", 96, 200), ("five_hour", 55, 10)), NOW, P)), at(200))
        far = Q.decide(state(("extra_usage", 100, None),
                             ("weekly_all", 96, 6 * 24 * 60)), NOW, P)
        self.assertEqual(QM.reset_branch(QM.halt_resets_at(far), NOW),
                         QM.QUOTA_BRANCH_NOTIFY)

    def test_the_halt_actions_and_message_follow_the_choice(self) -> None:
        """接線＋訊息面：事故形狀下 waker 真的被按下去（修前 branch=escalate ⇒ waker
        一次都不會被叫），且已武裝那一句印**被選中的** reset 而非 binding 的 None。"""
        d = Q.decide(state(("session", 96, None), ("five_hour", 96, 188)), NOW, P)
        woken: list[str] = []
        act = QG.quota_halt_actions({"transcript_path": ""}, d, NOW, plan_writer=lambda t: "",
                                    waker=lambda t, p: woken.append(p) or {"armed": True})
        self.assertEqual((act["branch"], act["armed"], len(woken)),
                         (QM.QUOTA_BRANCH_ARM, True, 1))
        self.assertIn(str(at(188)), QM.quota_halt_message(d, act),
                      "halt 訊息還在印 binding 軸的期程（None）")


if __name__ == "__main__":
    unittest.main(verbosity=2)
