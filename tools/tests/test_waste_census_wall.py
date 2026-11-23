"""`tools/lib/wastecensus/sections_wall.py`（＋`keep_load.scan_walls`、`sections_keep`
的 M-K1 扣除）的驗收測試（R218 QuotaWall Q5；TCS-QuotaWall REQ-QW-50／51／52／53／55、AT-QW-56／
57／58／61 的
量測面、MU-QW-11、E2E-QW-19／20 的 CI 形態）。

守的是「額度牆續航有沒有被量到」：牆後冷重寫要單獨算且不再混進 M-K1、保溫有沒有保住快取與省下
多少、park 到點結局（含舊資料沒有終態痕跡的失敗）、三鍵建議值不足就誠實印「未校準」，且量測絕不
改設定檔。縫＝造出來的小型母體、痕跡與逐字稿（隔離 tmp 目錄），不讀真實 ~/.claude、~/.autosdd；
時間一律 epoch 秒。真實資料的實跑證據在 R218 Q5 交卷報告（E2E-QW-19／20 本機形態，正式案例由
Q6 的 realverify 家族 `quotawall` 負責）。
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

from lib.sessionctl import keepwarm, kw_wake, qw_calc, qw_schema, qw_wall  # noqa: E402
from lib.wastecensus import keep_load  # noqa: E402
from lib.wastecensus import sections_keep as sk  # noqa: E402
from lib.wastecensus import sections_wall as sw  # noqa: E402
from lib.wastecensus.reader import W_CC1  # noqa: E402

_T0 = 1_800_000_000.0
_MIN = 60.0
_PROBE = _REPO / "tools" / "probe" / "waste_census.py"
_DOC = _REPO / "docs" / "02_architecture" / "QuotaWall_CacheContinuity_Design.md"
_PARK_CLI = _REPO / "tools" / "lib" / "sessionctl" / "park_cli.py"


def _turn(at_min, *, cc=0, cr=0, inp=1, out=5, cause="human", tools=()):
    return {"ts_first": _T0 + at_min * _MIN, "ts_last": _T0 + at_min * _MIN + 5, "inp": inp,
            "cc": cc, "cr": cr, "out": out, "cc5": 0, "cc1": cc, "cause": cause,
            "tools": list(tools)}


def _main(sid, turns, walls=()):
    return {"sid": sid, "handoff_start": False, "turns": list(turns), "compactions": [],
            "kw_calls": [], "walls": [{"ts": _T0 + m * _MIN, "kind": k} for m, k in walls]}


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).isoformat()


def _row(event, at_min, **fields):
    return {"event": event, "at": _iso(_T0 + at_min * _MIN), **fields}


def _pop(mains=(), subs=()):
    return {"main": list(mains), "sub": list(subs)}


# ───────────────────────────────────────────────────────────────────────────── M-K7
class WallColdRewriteTest(unittest.TestCase):
    """`sections_wall.m_k7` 與 `sections_keep.m_k1` 的分工（REQ-QW-50、AT-QW-56、MU-QW-11）。"""

    def _session(self):
        """四段間隔：牆後重寫×2（一個 cut、一個 synthetic）＋牆外一般閒置重寫×1。"""
        turns = [_turn(0, cr=300_000), _turn(80, cc=300_000),            # 牆 ①（cut）後重寫
                 _turn(90, cr=300_000), _turn(160, cc=200_000, cr=100_000),  # 牆 ②（synthetic）
                 _turn(170, cr=300_000), _turn(240, cc=300_000)]         # 沒有牆的閒置重寫
        return _main("wallsess-0000", turns, walls=[(10, "cut"), (100, "synthetic")])

    def test_wall_rewrites_are_counted_once_in_mk7_and_not_in_mk1(self) -> None:
        """WHY：同一次冷重寫若 M-K1 與 M-K7 各算一次，保溫成效（省下的重寫量）被灌水。"""
        pop = _pop([self._session()])
        k7, k1 = sw.m_k7(pop["main"]), sk.m_k1(pop["main"])
        self.assertEqual((k7["count"], k7["tokens"]), (2, 500_000))
        self.assertEqual(k7["units"], W_CC1 * 500_000)
        self.assertEqual((k1["count"], k1["tokens"]), (1, 300_000))

    def test_without_wall_marks_all_three_gaps_fall_back_into_mk1(self) -> None:
        """MU-QW-11：把牆標記拿掉，同一份逐字稿三件全回 M-K1、M-K7 為 0——證明扣除靠牆標記。"""
        main = self._session()
        bare = {**main, "walls": []}
        self.assertEqual(sk.m_k1([bare])["count"], 3)
        self.assertEqual(sw.m_k7([bare])["count"], 0)
        # 舊快照沒有 walls 欄也不得炸（相容）
        legacy = {k: v for k, v in main.items() if k != "walls"}
        self.assertEqual(sk.m_k1([legacy])["count"], 3)

    def test_half_context_is_the_rewrite_boundary(self) -> None:
        """WHY：只有 cache_creation ≥ 前一筆上下文的一半才算「整份重寫」；只多寫增量不算。"""
        for cc, expect in ((149_999, 0), (150_000, 1)):
            prev = _turn(0, cr=299_999)  # 上下文＝30 萬
            main = _main("b", [prev, _turn(80, cc=cc, cr=300_000 - cc)], walls=[(10, "cut")])
            self.assertEqual(sw.m_k7([main])["count"], expect, cc)

    def test_a_wall_outside_the_gap_does_not_count(self) -> None:
        """WHY：牆要落在兩筆真 usage 之間；之前或之後的牆與這次重寫無關。"""
        turns = [_turn(0, cr=300_000), _turn(80, cc=300_000)]
        for at in (-5, 85):
            self.assertEqual(sw.m_k7([_main("c", turns, walls=[(at, "cut")])])["count"], 0, at)

    def test_wall_events_merge_records_ten_minutes_apart(self) -> None:
        """WHY：切斷通知與 synthetic 限額記錄常同時出現；一面牆只能算一次（牆前無觸發的分母）。"""
        main = _main("d", [], walls=[(0, "cut"), (3, "synthetic"), (9, "synthetic"),
                                     (60, "cut")])
        self.assertEqual(len(sw.wall_events(main)), 2)


class WallScanTest(unittest.TestCase):
    """`tools/lib/wastecensus/keep_load.py::scan_walls`：只認 ①切斷通知 ②限額 synthetic。"""

    def _write(self, lines) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return keep_load.scan_walls(path)

    @staticmethod
    def _synthetic(text, ts="2027-01-15T08:00:00Z", side=False):
        return json.dumps({"type": "assistant", "timestamp": ts, "isSidechain": side,
                           "message": {"model": "<synthetic>",
                                       "content": [{"type": "text", "text": text}]}})

    def test_cut_notice_and_limit_synthetic_are_walls_other_synthetic_is_not(self) -> None:
        cut = json.dumps({"type": "system", "timestamp": "2027-01-15T07:00:00Z",
                          "content": "Usage limit reached · continuing automatically at 12:10am"})
        got = self._write([
            cut,
            self._synthetic("You've hit your session limit · resets 6:50am"),
            self._synthetic("Request interrupted by user", "2027-01-15T09:00:00Z"),
            self._synthetic("usage limit reached", "2027-01-15T10:00:00Z", side=True),
            "{壞行 continuing automatically at",
        ])
        self.assertEqual([w["kind"] for w in got], ["cut", "synthetic"])
        self.assertLess(got[0]["ts"], got[1]["ts"])

    def test_the_wall_text_and_cut_mark_equal_the_guard_side(self) -> None:
        """REQ-SS-21 同款：wastecensus 不 import 守衛判準，兩邊字樣相等由這裡釘住。"""
        self.assertEqual(sw.WALL_TEXT_RE.pattern, qw_wall._WALL_TEXT_RE.pattern)
        import transcript_activity  # noqa: PLC0415

        self.assertEqual(sw.CUT_MARK, transcript_activity._CUTOFF_MARK)


# ───────────────────────────────────────────────────────────────────────────── M-K8
class KeepwarmEffectivenessTest(unittest.TestCase):
    """`sections_wall.m_k8`（REQ-QW-51、AT-QW-57）。"""

    CTX = 300_000

    def _traces(self):
        def ping(sid, at, k):
            return _row("keepwarm_verdict", at, sid=sid, verdict="ping", k=k, ctx=self.CTX)

        def end(sid, at, verdict, **kw):
            return _row("keepwarm_verdict", at, sid=sid, verdict=verdict, **kw)

        return [
            ping("aaaaaaaa", 100, 1), ping("aaaaaaaa", 145, 2), end("aaaaaaaa", 600, "resume"),
            ping("bbbbbbbb", 100, 1), end("bbbbbbbb", 600, "resume"),            # chain，沒保住
            end("cccccccc", 600, "resume"),                                      # single
            _row("keepwarm_verdict", 50, sid="dddddddd", verdict="skip", reason="small_ctx"),
            ping("eeeeeeee", 10, 1), end("eeeeeeee", 55, "cap", k=1),            # periodic
            end("eeeeeeee", 56, "cap", k=1),                                # 重複 cap：不算 run
            # 備援：一次到點被讓路（yield）＋一次真的觸發
            _row("park_job_start", 700, sid="aaaaaaaa", job="j1"),
            _row("park_yield_primary", 701, sid="aaaaaaaa"),
            _row("park_job_start", 800, sid="ffffffff", job="j2"),
            _row("quotawall_stop_muted", 10, sid="aaaaaaaa"),
            _row("quotawall_stop_muted", 11, sid="aaaaaaaa"),
        ]

    def _mains(self):
        a = _main("aaaaaaaa", [_turn(90, cr=self.CTX), _turn(601, cc=10_000, cr=290_000)],
                  walls=[(150, "cut")])
        b = _main("bbbbbbbb", [_turn(90, cr=self.CTX), _turn(601, cc=280_000, cr=20_000)])
        w = _main("gggggggg", [], walls=[(2000, "cut")])  # 牆前 6 小時內沒有任何觸發
        return [a, b, w]

    def test_counts_by_mode_and_cache_survival(self) -> None:
        got = sw.m_k8(self._mains(), self._traces())
        self.assertEqual((got["chain"], got["single"], got["periodic"]), (2, 1, 1))
        self.assertEqual((got["cross_ok"], got["cross_fail"], got["cross_unknown"]), (1, 1, 1))
        self.assertEqual(got["open"], 0)
        self.assertEqual(len(got["runs"]), 4)  # dddddddd 的 skip 與重複 cap 都不是 run

    def test_saved_units_is_two_c_minus_pings(self) -> None:
        """WHY：省下＝「若放冷會重寫的 2c」減「保溫實際付的 Σp」；只對真的保住快取的 run 計。"""
        got = sw.m_k8(self._mains(), self._traces())
        p = 2 * keepwarm.W_CR * self.CTX + keepwarm.P_FIX
        self.assertAlmostEqual(got["saved_units"], W_CC1 * (self.CTX + 1) - 2 * p, places=3)

    def test_backup_fired_yield_muted_and_walls_without_trigger(self) -> None:
        got = sw.m_k8(self._mains(), self._traces())
        self.assertEqual((got["fired"], got["yield"], got["stop_muted"]), (1, 1, 2))
        self.assertEqual((got["walls"], got["no_trigger_walls"]), (2, 1))

    def test_reset_jitter_of_one_second_is_one_window(self) -> None:
        """WHY：伺服器在 :59:59.9／:00:00.1 之間抖動，不取整會把同一窗拆成兩組（AT-QP-58 同款）。"""
        rows = [_row("keepwarm_verdict", 10, sid="s1", verdict="resume",
                     reset="2027-01-15T10:59:59.900000+00:00"),
                _row("keepwarm_verdict", 20, sid="s1", verdict="resume",
                     reset="2027-01-15T11:00:00.100000+00:00")]
        got = sw.m_k8([], rows)
        self.assertEqual((len(got["runs"]), got["windows"]), (2, 1))

    def test_an_explicit_mode_field_wins_over_the_inference(self) -> None:
        """WHY：Q2／Q3 之後若在痕跡補 `mode`，量測要直接採用而不是再推。"""
        rows = [_row("keepwarm_verdict", 10, sid="s2", verdict="resume", mode="chain")]
        self.assertEqual(sw.m_k8([], rows)["chain"], 1)

    def test_run_still_pinging_is_reported_open(self) -> None:
        rows = [_row("keepwarm_verdict", 10, sid="s3", verdict="ping", k=1, ctx=self.CTX)]
        self.assertEqual(sw.m_k8([], rows)["open"], 1)


# ───────────────────────────────────────────────────────────────────────────── M-K9
class ParkOutcomeTest(unittest.TestCase):
    """`sections_wall.m_k9`（REQ-QW-53、AT-QW-58；22:42 事件的形狀）。"""

    NOW = _T0 + 10_000 * _MIN

    def _armed(self, sid, at, reset_min):
        return _row("park_armed", at, sid=sid, route="H", reset_at=_iso(_T0 + reset_min * _MIN),
                    fire_at=_iso(_T0 + reset_min * _MIN))

    def _traces(self):
        return [
            # X：22:42 形狀——armed → job_start → route（RESUME）→ 沒有任何終態；同秒 oldwin 拒絕
            self._armed("xxxxxxxx", 10, 200),
            _row("park_job_start", 200, sid="xxxxxxxx", job="jx"),
            _row("park_route", 200.01, sid="xxxxxxxx", job="jx", route="RESUME"),
            # F：fired
            _row("park_job_start", 300, sid="ffffffff", job="jf"),
            _row("park_route", 300.01, sid="ffffffff", route="FRESH"),
            _row("park_spawned", 300.1, sid="ffffffff", job="jf", rc=0, route="FRESH"),
            # S：skipped（live_driver）
            _row("park_job_start", 400, sid="ssssssss", job="js"),
            _row("handoff_spawn_skipped", 400.01, sid="ssssssss", job="js", reason="live_driver"),
            # C：失敗鏈（兩次嘗試各有原因）
            _row("park_job_start", 500, sid="cccccccc", job="jc"),
            _row("park_chain_failed", 500.2, sid="cccccccc", attempts=[
                {"route": "RESUME", "attempted": True, "rc": 1, "reason": "image_not_allowed"},
                {"route": "FRESH", "attempted": False, "reason": "dirty_tree"}]),
            # R：舊格式失敗（只有 park_resume_failed＋rc），沒有 oldwin 痕跡
            _row("park_job_start", 600, sid="rrrrrrrr", job="jr"),
            _row("park_resume_failed", 600.1, sid="rrrrrrrr", rc=1, route="RESUME"),
            # U：開始後什麼都沒有（沒到過選路）
            _row("park_job_start", 700, sid="uuuuuuuu", job="ju"),
        ]

    def _oldwin(self):
        return [{"event": "oldwin_close_refused",
                 "at": _iso(_T0 + 200 * _MIN - 1),  # oldwin 時間戳只到秒：可能早於同一秒的 job 開始
                 "old": "xxxxxxxx", "new": "xxxxxxxx", "reason": "image_not_allowed"},
                {"event": "oldwin_close_degraded", "at": _iso(_T0 + 600 * _MIN),
                 "old": "rrrrrrrr", "new": "rrrrrrrr", "reason": "open_failed"}]

    def _mains(self):
        # X 在 reset（200 分）後 30 分內沒有任何回合；F 的 sid 本身不在母體（不判）
        return [_main("xxxxxxxx", [_turn(100, cr=1), _turn(300, cr=1)])]

    def test_every_job_lands_in_exactly_one_bucket(self) -> None:
        got = sw.m_k9(self._traces(), self._oldwin(), self._mains(), self.NOW)
        self.assertEqual(got["jobs"], 6)
        self.assertEqual(got["fired"], 1)
        self.assertEqual(got["skipped"], {"live_driver": 1})
        self.assertEqual(got["unresolved"], 1)
        self.assertEqual(got["failed"]["count"], 3)

    def test_the_2242_shape_is_failed_with_the_oldwin_reason(self) -> None:
        """WHY：真實 22:42 事件沒有 park 終態痕跡；只能由「到過選路＋同 sid 的 oldwin 拒絕」認出，
        原因要寫 image_not_allowed 而不是籠統的 no_terminal。"""
        got = sw.m_k9(self._traces(), self._oldwin(), self._mains(), self.NOW)
        items = {i["sid"]: i["reasons"] for i in got["failed"]["items"]}
        self.assertEqual(items["xxxxxxxx"], ["image_not_allowed"])
        without = sw.m_k9(self._traces(), [], self._mains(), self.NOW)
        self.assertEqual({i["sid"]: i["reasons"] for i in without["failed"]["items"]}["xxxxxxxx"],
                         ["no_terminal"])

    def test_chain_failure_reasons_come_from_attempts_and_degraded_is_no_reason(self) -> None:
        got = sw.m_k9(self._traces(), self._oldwin(), self._mains(), self.NOW)
        items = {i["sid"]: i["reasons"] for i in got["failed"]["items"]}
        self.assertEqual(items["cccccccc"], ["dirty_tree", "image_not_allowed"])
        self.assertEqual(items["rrrrrrrr"], ["rc=1"])  # close_degraded 會繼續，不當失敗原因
        self.assertEqual(got["failed"]["reasons"],
                         {"dirty_tree": 1, "image_not_allowed": 2, "rc=1": 1})

    def test_claimed_but_not_resumed_needs_no_assistant_record_in_30_minutes(self) -> None:
        got = sw.m_k9(self._traces(), self._oldwin(), self._mains(), self.NOW)
        lost = got["not_resumed"]
        self.assertEqual((lost["count"], lost["judged"], lost["pending"]), (1, 1, 0))
        self.assertEqual(lost["items"][0]["sid"], "xxxxxxxx")
        # reset＋30 分內有該 sid 的回合 ⇒ 不算；回合落在 31 分鐘後 ⇒ 仍算
        for at, expect in ((215, 0), (231, 1)):
            mains = [_main("xxxxxxxx", [_turn(100, cr=1), _turn(at, cr=1)])]
            self.assertEqual(sw.m_k9(self._traces(), [], mains, self.NOW)["not_resumed"]["count"],
                             expect, at)

    def test_a_fresh_spawned_session_counts_as_resumed(self) -> None:
        """WHY：FRESH 路是開新 session 接手，新 sid 的回合就是「續上了」。"""
        traces = [*self._traces(),
                  _row("session_switch_spawned", 200.5, sid="xxxxxxxx", ok=True,
                       new_transcripts=["nnnnnnnn.jsonl"])]
        mains = [*self._mains(), _main("nnnnnnnn", [_turn(205, cr=1), _turn(250, cr=1)])]
        self.assertEqual(sw.m_k9(traces, [], mains, self.NOW)["not_resumed"]["count"], 0)

    def test_cancelled_pending_and_unjudgeable_claims_are_not_counted(self) -> None:
        mains = self._mains()
        cancelled = [*self._traces(), _row("park_cancelled", 100, sid="xxxxxxxx")]
        self.assertEqual(sw.m_k9(cancelled, [], mains, self.NOW)["not_resumed"]["count"], 0)
        early = _T0 + 210 * _MIN  # reset＋30 分尚未到：待判而非未續上
        got = sw.m_k9(self._traces(), [], mains, early)["not_resumed"]
        self.assertEqual((got["count"], got["pending"]), (0, 1))
        unknown = [self._armed("zzzzzzzz", 10, 200)]  # 該 sid 不在逐字稿母體：不判
        got = sw.m_k9(unknown, [], mains, self.NOW)["not_resumed"]
        self.assertEqual((got["count"], got["judged"], got["pending"]), (0, 0, 0))

    def test_the_verdict_does_not_depend_on_trace_order(self) -> None:
        rows = self._traces()
        a = sw.m_k9(rows, self._oldwin(), self._mains(), self.NOW)
        b = sw.m_k9(list(reversed(rows)), self._oldwin(), self._mains(), self.NOW)
        self.assertEqual(a, b)


# ───────────────────────────────────────────────────────────────────────────── 校準
class CalibrateQuotawallTest(unittest.TestCase):
    """`sections_wall.calibrate_quotawall`（REQ-QW-52、S-3／S-4／S-15）。"""

    CTX = 300_000

    def _ping_rows(self, n):
        rows = []
        for i in range(n):
            at = 100 + 45 * i
            rows += [_row("keepwarm_verdict", at, sid="pppppppp", verdict="ping", k=i + 1,
                          ctx=self.CTX),
                     _row("keepwarm_ping_cost", at + 0.01, sid="pppppppp", delta=1, pct=90 + i)]
        return rows

    def _burn(self, n):
        reset = "2027-01-15T12:00:00+00:00"
        rows, pct = [], 10.0
        for i in range(n + 1):
            rows.append({"ts": _iso(_T0 + 5 * _MIN * i), "pct": {"five_hour": pct},
                         "resets_at": {"five_hour": reset}})
            pct += 1 + i % 2  # 每 5 分鐘交錯 +1、+2
        return rows

    def _subs(self, n):
        return [{"sid": f"s{i}", "turns": [_turn(j, cc=20_000, cr=60_000 + i) for j in range(6)]}
                for i in range(n)]

    def test_fewer_than_eight_intervals_is_uncalibrated_for_every_key(self) -> None:
        """WHY：區間太少的「建議值」是雜訊；寧可印未校準，由 S-3 縮放預設運作（REQ-QW-52）。"""
        got = sw.calibrate_quotawall(_pop(subs=self._subs(7)), self._ping_rows(7), self._burn(7))
        for key in ("pp", "burn", "agent"):
            self.assertIsNone(got[key]["rec"], key)
        self.assertEqual((got["pp"]["n"], got["burn"]["n"]), (7, 7))

    def test_pp_is_the_ratio_of_summed_delta_to_summed_kunits(self) -> None:
        got = sw.calibrate_quotawall(_pop(), self._ping_rows(8), [])
        kunits = 8 * (2 * keepwarm.W_CR * self.CTX + keepwarm.P_FIX) / 1000.0
        self.assertAlmostEqual(got["pp"]["rec"], 8 / kunits, places=9)
        self.assertEqual(got["pp"]["sources"], {"ping_cost": 8, "legacy_readings": 0})

    def test_legacy_readings_pair_consecutive_pings_inside_one_window(self) -> None:
        """WHY：真實舊資料沒有 ping_cost 事件，只有「ping 判決」與其後第一筆 Stop 讀數；
        跨 reset 的相鄰兩次不能配對（讀數從 98 掉回 0 不是成本）。"""
        reset = _iso(_T0 + 400 * _MIN)
        rows = []
        for i, pct in enumerate((91, 92, 93, 93, 94, 95, 96, 96, 97, 5)):
            at = 100 + 45 * i
            r = reset if i < 9 else _iso(_T0 + 900 * _MIN)
            rows += [_row("keepwarm_verdict", at, sid="lllllll1", verdict="ping", k=i + 1,
                          ctx=self.CTX),
                     _row("park_stop_block", at + 0.3, sid="lllllll1", kind="session",
                          pct=float(pct), reset_at=r)]
        got = sw.calibrate_quotawall(_pop(), rows, [])
        self.assertEqual(got["pp"]["sources"], {"ping_cost": 0, "legacy_readings": 8})
        self.assertEqual(got["pp"]["sum_delta"], 6.0)  # 91→97 的合計；97→5 跨視窗不配
        self.assertIsNotNone(got["pp"]["rec"])

    def test_new_and_legacy_sources_are_not_double_counted(self) -> None:
        rows = self._ping_rows(8)
        for i in range(8):  # 同一批 ping 之後都有 Stop 讀數：新資料已覆蓋，不得再算一次
            rows.append(_row("park_stop_block", 100 + 45 * i + 0.3, sid="pppppppp",
                             kind="session", pct=90.0 + i, reset_at=_iso(_T0 + 900 * _MIN)))
        got = sw.calibrate_quotawall(_pop(), rows, [])
        self.assertEqual(got["pp"]["sources"], {"ping_cost": 8, "legacy_readings": 0})

    def test_burn_is_the_p75_of_active_rates_and_agent_needs_pp_first(self) -> None:
        got = sw.calibrate_quotawall(_pop(subs=self._subs(8)), self._ping_rows(8), self._burn(8))
        rates = sorted((1 + i % 2) / 5.0 for i in range(8))  # 每 5 分鐘 +1 或 +2（pct 交錯）
        self.assertEqual(got["burn"]["n"], 8)
        self.assertAlmostEqual(got["burn"]["rec"], rates[5], places=9)  # nearest-rank p75
        self.assertEqual(got["agent"]["n"], 8)
        self.assertGreater(got["agent"]["rec"], 0)
        no_pp = sw.calibrate_quotawall(_pop(subs=self._subs(8)), [], self._burn(8))
        self.assertIsNone(no_pp["agent"]["rec"])
        self.assertIn("PP_PER_KUNIT", no_pp["agent"]["reason"])

    def test_calibration_is_a_pure_function_of_its_input(self) -> None:
        args = (_pop(subs=self._subs(9)), self._ping_rows(9), self._burn(9))
        self.assertEqual(sw.calibrate_quotawall(*args), sw.calibrate_quotawall(*args))


# ───────────────────────────────────────────────────────────────────────────── 契約與紀律
class SchemaDisciplineTest(unittest.TestCase):
    """AT-QW-61 的量測面條款與事件名兩邊相等（REQ-QW-63、REQ-SS-21 同款）。"""

    def test_sections_wall_takes_field_names_from_qw_schema_not_its_own_literals(self) -> None:
        """WHY：十一個跨包欄名只住 qw_schema；量測模組若自己寫一份，改名就靜默不一致。"""
        eleven = {getattr(qw_schema, n) for n in (
            "MK_PRIMARY_WAKE_AT", "MK_PRIMARY_SOURCE", "MK_BACKUP_FIRE_AT",
            "MK_CLOSE_STUCK_WINDOW", "MK_DESKTOP_NOTIFY", "HOLDER_WAKE_AT",
            "HOLDER_TARGET_SOURCE", "EV_SPAWNING", "LEDGER_LAST_PING_PCT",
            "LEDGER_LAST_PING_AT", "LEDGER_PING_COSTS")}
        self.assertEqual(len(eleven), 11)
        tree = ast.parse(Path(sw.__file__).read_text(encoding="utf-8"))
        literals = {n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertEqual(literals & eleven, set())
        self.assertIs(sw.qw_schema, qw_schema)

    def test_event_names_equal_the_producer_side(self) -> None:
        self.assertEqual(sw.EV_KW_VERDICT, keepwarm.EV_VERDICT)
        self.assertEqual(sw.EV_KW_PING_COST, kw_wake.EV_PING_COST)
        self.assertEqual(sw.EV_KW_EARLY_RESET, kw_wake.EV_EARLY_RESET)
        self.assertEqual((sw.KEY_PP, sw.KEY_BURN, sw.KEY_AGENT),
                         (qw_calc.KEY_PP, qw_calc.KEY_BURN, qw_calc.KEY_AGENT))

    def test_park_events_exist_in_park_cli_and_the_rest_in_the_design(self) -> None:
        """WHY：park_cli 已產出的事件名逐字在原始碼；Q3／Q4 尚未落地的（讓路、失敗鏈、靜音）
        至少逐字在設計稿的痕跡清單，量測與設計不能各說各話。"""
        # Q3 把到點流程拆進 park_fire／park_chain／park_yield：事件名住它們，不再全在 park_cli
        src = [line for name in ("park_cli", "park_fire", "park_chain", "park_yield")
               for line in _PARK_CLI.with_name(f"{name}.py").read_text(
                   encoding="utf-8").splitlines()]
        for name in (sw.EV_JOB_START, sw.EV_ROUTE, sw.EV_RESUMED, sw.EV_SPAWNED,
                     sw.EV_SKIPPED, sw.EV_ARMED, sw.EV_CANCELLED, sw.EV_DONE):
            self.assertTrue(any(f'"{name}"' in line for line in src), name)
        # Q3 起失敗不再各記一個事件名，改 `park_attempt`＋`park_chain_failed`；
        # 舊事件名只留在歷史列的
        # 判讀（見本檔「舊格式失敗」案例），不再要求原始碼產出
        for name in (sw.EV_YIELD, sw.EV_CHAIN_FAILED):
            self.assertTrue(any(f'"{name}"' in line for line in src), name)
        doc = _DOC.read_text(encoding="utf-8").splitlines()
        for name in (sw.EV_STOP_MUTED,):
            self.assertTrue(any(f"`{name}`" in line for line in doc), name)


# ───────────────────────────────────────────────────────────────────────────── 入口
class WallProbeEntryTest(unittest.TestCase):
    """`tools/probe/waste_census.py` 的 `--switch-metrics`／`--calibrate-quotawall`
    （E2E-QW-19／20 的 CI 形態）。"""

    def _transcripts(self, base: Path) -> None:
        def assistant(ts, mid, cc, cr):
            return json.dumps({"type": "assistant", "timestamp": ts, "message": {
                "id": mid, "model": "claude-x", "content": [], "usage": {
                    "input_tokens": 1, "cache_creation_input_tokens": cc,
                    "cache_read_input_tokens": cr, "output_tokens": 5,
                    "cache_creation": {"ephemeral_1h_input_tokens": cc}}}})
        cut = json.dumps({"type": "system", "timestamp": "2027-01-15T09:00:00Z",
                          "content": "Usage limit reached · continuing automatically at 2pm"})
        human = json.dumps({"type": "user", "timestamp": "2027-01-15T10:59:50Z",
                            "origin": {"kind": "human"}, "message": {"content": "回來了"}})
        lines = [assistant("2027-01-15T08:00:00Z", "m0", 1, 300_000), cut, human,
                 assistant("2027-01-15T11:00:00Z", "m1", 300_000, 0)]
        (base / "11111111-aaaa.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _probe(self, cwd, *args):
        argv = [sys.executable, str(_PROBE), *args]
        proc = subprocess.run(argv, capture_output=True, cwd=cwd,  # noqa: S603
                              encoding="utf-8", errors="replace", timeout=120)
        return proc.returncode, proc.stdout, proc.stderr

    def test_switch_metrics_prints_the_wall_section_from_a_real_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "proj"
            base.mkdir()
            self._transcripts(base)
            rc, out, err = self._probe(tmp, "--base", str(base), "--since-days", "3650",
                                       "--switch-metrics", "--trace-file",
                                       str(Path(tmp) / "no-trace.jsonl"))
        self.assertEqual(rc, 0, err)
        self.assertIn("M-K7 額度牆冷重寫：1 件／300,000 tok", out)
        self.assertIn("M-K1 主控可保溫閒置後重寫：0 件", out)
        self.assertRegex(out, re.compile(r"M-K8 保溫成效：run 0"))
        self.assertIn("M-K9 park 到點結局：job 0", out)

    def test_calibrate_twice_is_byte_identical_and_writes_nothing(self) -> None:
        """E2E-QW-20 前半：同輸入兩次逐位元組相同；不改任何設定檔（env.shared 位元組不變、目錄
        內容不變）。輸入只有 1 個區間 ⇒ 三鍵皆印未校準。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "proj"
            base.mkdir()
            self._transcripts(base)
            env_shared = root / "env.shared"
            env_shared.write_bytes(b"AUTOSDD_QUOTAWALL_PP_PER_KUNIT=\n")
            before = sorted(p.name for p in root.iterdir())
            flags = ["--base", str(base), "--since-days", "3650", "--calibrate-quotawall",
                     "--trace-file", str(root / "no-trace.jsonl"),
                     "--burn-file", str(root / "no-burn.jsonl")]
            rc1, one, err1 = self._probe(tmp, *flags)
            rc2, two, _ = self._probe(tmp, *flags)
            after = sorted(p.name for p in root.iterdir())
            kept = env_shared.read_bytes()
        self.assertEqual((rc1, rc2), (0, 0), err1)
        self.assertEqual(one.encode("utf-8"), two.encode("utf-8"))
        self.assertEqual((after, kept), (before, b"AUTOSDD_QUOTAWALL_PP_PER_KUNIT=\n"))
        for key in (sw.KEY_PP, sw.KEY_BURN, sw.KEY_AGENT):
            self.assertIn(f"{key}：未校準", one)


if __name__ == "__main__":
    unittest.main()
