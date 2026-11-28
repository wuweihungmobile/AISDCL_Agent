#!/usr/bin/env python3
"""`tools/lib/sessionctl/parkprobe.py`／`parkearly.py` 的驗收測試（Control_Handover W6；TCS-Control
AT-CTL-56～69、MU-CTL-30～37）。

WHY（2026-11-22 真事件）：`65389f03` 週額度 100% ⇒ `park --at` 到 11/24 19:03；掌舵者換帳號後
讀數已回 0%，但等待期間沒有任何元件重讀額度，只能靠人手開窗。所以：
- 判準＝「相對登記當下的下降」＋「低於準備門檻」，絕對值低不觸發（`park --why` 的 80%→80%
  不誤觸發）；
- 提前到點走 Q3 的同一條 fire 路（讓路、失敗鏈、出聲照常），只停用「主載具活著且未到 ⇒ 重排」；
- 任何前置不成立、量不到讀數、已觸發過，一律不觸發；探針本身的例外不得讓哨兵巡邏死掉。

縫：S["quota"]（假額度）、S["policy"]、S["transcript"]（假逐字稿）、S["backend"]／spawn／
resume（假排程與假 spawn）。不碰真排程器、真 `~/.claude`、真 `~/.autosdd`。
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_escalation  # noqa: E402
import quota_policy  # noqa: E402
import quota_ruling as QR  # noqa: E402
from test_sessionctl_park import (  # noqa: E402
    NOW,
    SID,
    _CliFence,
    _Fence,
    _line,
    _marker,
    _policy,
    _state,
)

from lib.sessionctl import (  # noqa: E402
    briefline,
    park,
    park_cli,
    park_status,
    park_yield,
    parkearly,
    parkprobe,
    qw_schema,
)

FIRE_AT = NOW + timedelta(hours=3)  # 剩餘等待 3 小時，遠大於 EARLY_MIN_WAIT_MIN
LABEL = "AutoSDD_HandoffSpawn_798a7bf1_202611152002"


def _early_marker(pkg=None, **over) -> dict:
    """一份「等 3 小時、登記時讀數 100%、帳號 acct-A」的 armed park 標記。"""
    marker = dict(_marker("H"), pkg=str(pkg) if pkg else None, parked_pct=100.0,
                  parked_account="acct-A", fire_at=FIRE_AT.isoformat(),
                  valid_until=(FIRE_AT + timedelta(seconds=park.YIELD_GRACE_SECONDS)).isoformat(),
                  **qw_schema.marker_extra(FIRE_AT.timestamp(), "at", FIRE_AT.timestamp(),
                                           False, None))
    marker["jobs"][0].update(label=LABEL, fire_at=FIRE_AT.isoformat())
    marker.update(over)
    return marker


def _ruling(state, prepare: float = 85.0):
    """QVD C21（WP-QV）：提前恢復的准許只看**判決**；以同一份讀數＋政策組真判決（純函式）。"""
    pol = _policy(prepare)
    return QR.ruling(state, quota_policy.decide(state, NOW, pol), model=None, policy=pol, now=NOW)


def _keyed(state, key: str | None):
    return dataclasses.replace(state, account_key=key)


class EvaluateTest(_Fence, unittest.TestCase):
    """tools/lib/sessionctl/parkprobe.py::evaluate、park.py::recovered：提前恢復判準
    （AT-CTL-56／57；REQ-CTL-32／37；MU-CTL-30／31）。"""

    def test_at_ctl_56_recovered_truth_table(self) -> None:
        for parked, cur, prepare, want in (
                (100, 0, 85, True), (100, 96, 85, False), (90, 86, 85, False), (90, 84, 85, True),
                (80, 79, 85, False), (80, 80, 85, False)):
            with self.subTest(parked=parked, cur=cur, prepare=prepare):
                marker = dict(_marker("H"), parked_pct=float(parked))
                state = _state(five=cur, week=cur)
                got = park.recovered(marker, state, _ruling(state, prepare), NOW)
                self.assertIs(got, want)

    def test_at_ctl_56_missing_baseline_never_recovers(self) -> None:
        state = _state(five=0, week=0)
        self.assertFalse(park.recovered(_marker("H"), state, _ruling(state), NOW))

    def test_the_drop_threshold_is_exactly_five_pp(self) -> None:
        marker = dict(_marker("H"), parked_pct=90.0)
        hit, miss = _state(five=85.0 - 0.1, week=0), _state(five=85.1, week=0)
        self.assertTrue(park.recovered(marker, hit, _ruling(hit, 86), NOW))
        self.assertFalse(park.recovered(marker, miss, _ruling(miss, 99), NOW))

    def test_reading_ignores_model_scoped_and_fallback_axes(self) -> None:
        resets = (NOW + timedelta(hours=1)).isoformat()
        axes = (quota_policy.Axis("five_hour", 3.0, resets),
                quota_policy.Axis("seven_day", 2.0, resets),
                quota_policy.Axis("weekly_scoped", 99.0, resets, scope_model="Fable"))
        self.assertEqual(parkprobe.reading(_state(axes=axes)), 3.0)
        self.assertIsNone(parkprobe.reading(_state(axes=())))

    def test_at_ctl_57_old_marker_without_baseline_says_so_and_is_not_judged(self) -> None:
        verdict = parkprobe.evaluate(_marker("H"), None, None, NOW)
        self.assertEqual((verdict["reason"], verdict["recovered"]),
                         (parkprobe.REASON_NO_BASELINE, False))
        self.assertEqual(parkprobe.status_row(_marker("H")), "early_probe: absent(no_baseline)")

    def test_an_empty_axis_set_is_unmeasured_not_recovered(self) -> None:
        empty = _state(axes=())
        verdict = parkprobe.evaluate(_early_marker(), empty, _ruling(empty), NOW)
        self.assertEqual((verdict["reason"], verdict["recovered"]),
                         (parkprobe.REASON_UNMEASURED, False))

    def test_account_changed_needs_both_sides_and_a_difference(self) -> None:
        marker = _early_marker()
        self.assertTrue(parkprobe.account_changed(marker, "acct-B"))
        for then, now in (("acct-A", "acct-A"), ("acct-A", None), (None, "acct-B"), ("", "acct-B")):
            with self.subTest(then=then, now=now):
                self.assertFalse(parkprobe.account_changed(
                    dict(marker, **{parkprobe.MK_PARKED_ACCOUNT: then}), now))
        self.assertFalse(parkprobe.account_changed(None, "acct-B"))

    def test_at_ctl_87_an_old_marker_without_parked_account_can_still_recover_by_drop(self) -> None:
        marker = {k: v for k, v in _early_marker().items() if k != parkprobe.MK_PARKED_ACCOUNT}
        state = _keyed(_state(five=0, week=0), "acct-B")
        verdict = parkprobe.evaluate(marker, state, _ruling(state), NOW)
        self.assertEqual((verdict["recovered"], verdict["account_changed"]), (True, False))


class BaselineAndMarkerTest(_CliFence, unittest.TestCase):
    """tools/lib/sessionctl/park_cli.py::_cmd_park＋parkprobe.baseline：基準欄寫入與往返
    （AT-CTL-58／68；REQ-CTL-32／36）。"""

    def test_at_ctl_58_park_registration_writes_the_two_baseline_fields(self) -> None:
        self.quota = lambda _n: _keyed(_state(five=98.0, week=78.0), "acct-A")
        rc, _out, err = self.run_cli()
        self.assertEqual(rc, 0, err)
        marker = park.read_marker(SID)
        self.assertEqual((marker[parkprobe.MK_PARKED_PCT], marker[parkprobe.MK_PARKED_ACCOUNT]),
                         (98.0, "acct-A"))

    def test_baseline_takes_the_max_over_short_and_weekly_axes_excluding_scoped(self) -> None:
        state = _keyed(_state(five=10.0, week=70.0), "acct-A")
        self.assertEqual(parkprobe.baseline({"quota": lambda _n: state}, NOW),
                         {"parked_pct": 70.0, "parked_account": "acct-A"})

    def test_an_unmeasurable_baseline_is_omitted_and_never_breaks_registration(self) -> None:
        def boom(_n):
            raise OSError("端點 500")
        self.assertEqual(parkprobe.baseline({"quota": boom}, NOW), {})
        self.assertEqual(parkprobe.baseline({"quota": lambda _n: _state(axes=())}, NOW), {})
        # WP-QV：登記須判決 PARK｜HALT_WEEKLY（QVD C6）⇒ 判決用預設讀數；只讓「基準讀數」量不到
        with mock.patch.object(parkprobe, "reading", return_value=None):
            rc, _out, _err = self.run_cli("--at", (NOW + timedelta(minutes=30)).isoformat(),
                                          "--note", "週額度停工到時間再接手")
        self.assertEqual(rc, 0)
        self.assertNotIn(parkprobe.MK_PARKED_PCT, park.read_marker(SID))

    def test_an_unkeyed_account_is_recorded_as_null_not_dropped(self) -> None:
        self.assertEqual(parkprobe.baseline({"quota": lambda _n: _state()}, NOW)["parked_account"],
                         None)

    def test_baseline_fields_survive_write_read_and_settling(self) -> None:
        marker = _early_marker()
        self.assertTrue(park.write_marker(marker)[0])
        self.assertEqual(park.read_marker(SID), marker)
        self.cli._settle(marker, "cancelled", "cancel")  # noqa: SLF001
        after = park.read_marker(SID)
        self.assertEqual((after["status"], after["parked_pct"], after["parked_account"]),
                         ("cancelled", 100.0, "acct-A"))

    def test_at_ctl_68_the_last_line_gains_exactly_one_token(self) -> None:
        import sentinel_lifecycle
        listed: list = []

        def arm(sid, *_a):
            listed.append(f"{sentinel_lifecycle.TASK_PREFIX}{sid}")
            return 0
        _rc, out, _err = self.run_cli(arm_sentinel=arm, jobs=lambda _p: list(listed))
        last = out.strip().splitlines()[-1]
        self.assertIn("sentinel=armed", last)
        self.assertTrue(last.endswith(" early_probe=armed"), last)
        _rc, out, _err = self.run_cli(env={"AUTOSDD_SENTINEL_OFF": "1"})
        self.assertTrue(out.strip().splitlines()[-1].endswith(" early_probe=absent(sentinel_off)"))
        _rc, out, _err = self.run_cli(arm_sentinel=lambda *a: 5, jobs=lambda _p: [])
        self.assertTrue(out.strip().splitlines()[-1].endswith(" early_probe=absent(arm_rc_5)"))

    def test_at_ctl_68_an_old_baseline_free_marker_reports_no_baseline_not_armed(self) -> None:
        line = parkprobe.with_token(["hint", "PARK_VERDICT=armed"], _marker("H"), ("armed", ""))[-1]
        self.assertTrue(line.endswith(" early_probe=absent(no_baseline)"), line)

    def test_at_ctl_67_status_prints_the_early_probe_row_and_refused_markers_keep_all_rows(
            self) -> None:
        park.write_marker(_early_marker(self.pkg))
        rc, out, _err = self.run_cli("--status")
        self.assertEqual(rc, 0)
        self.assertRegex(out, r"early_probe: next_probe=\? last=never reading=\? baseline=100\.0")
        park.write_marker(dict(_early_marker(self.pkg), status="refused",
                               outcome={"at": NOW.isoformat(), "event": "x", "detail": "y"}))
        _rc, out, _err = self.run_cli("--status")
        for key in ("primary:", "backup:", "sentinel:", "early_probe:"):
            self.assertIn(key, out)

    def test_status_row_reads_the_last_probe_trace_and_the_scheduler_seam(self) -> None:
        marker = _early_marker()
        with mock.patch.object(parkprobe, "probe_rows", return_value=[
                {"at": "t1", "reading": 5.0}, {"at": "t2", "reading": 0.0}]):
            row = parkprobe.status_row(marker, {"next_probe": lambda _sid: "2026-11-15T20:00"})
        self.assertEqual(row, "early_probe: next_probe=2026-11-15T20:00 last=t2 reading=0.0 "
                              "baseline=100.0")


class ImportDirectionAndScanTest(unittest.TestCase):
    """tools/lib/sessionctl/parkprobe.py／parkearly.py／park_cli.py：匯入方向、欄名住處、
    單一額度讀取點（AT-CTL-58／65／69／90；REQ-CTL-38／46）。逐行掃描，不做整檔缺席斷言。"""

    SESSIONCTL = _REPO_ROOT / "tools" / "lib" / "sessionctl"

    def lines(self, name: str) -> list[str]:
        return (self.SESSIONCTL / name).read_text(encoding="utf-8").splitlines()

    def imports(self, name: str) -> list[str]:
        heads = ("from ", "import ")
        return [ln.strip() for ln in self.lines(name) if ln.lstrip().startswith(heads)]

    def test_at_ctl_58_import_direction_is_one_way(self) -> None:
        bad = [ln for ln in self.lines("parkprobe.py")
               if ln.lstrip().startswith(("from . import", "import ")) and
               ("park_cli" in ln or "parkearly" in ln)]
        self.assertEqual(bad, [], "parkprobe 不得 import park_cli／parkearly")
        self.assertTrue(any("parkprobe" in ln for ln in self.imports("parkearly.py")))
        self.assertTrue(any("park_cli" in ln for ln in self.lines("parkearly.py")
                            if ln.strip().startswith("from . import park_cli")))
        self.assertEqual([ln for ln in self.imports("park_cli.py") if "parkearly" in ln], [])
        self.assertEqual([ln for ln in self.lines("park_cli.py") if "fire_early" in ln], [])

    def test_at_ctl_58_baseline_constants_do_not_live_in_qw_schema(self) -> None:
        for name in ("parked_pct", "parked_account"):
            self.assertEqual([ln for ln in self.lines("qw_schema.py") if name in ln], [])
        self.assertTrue(any("parked_pct" in ln for ln in self.lines("parkprobe.py")))

    def test_at_ctl_65_69_the_only_quota_read_is_park_pace_state(self) -> None:
        reads = [ln for ln in self.lines("parkprobe.py") + self.lines("parkearly.py")
                 if "quota_meter" in ln or "quota_gate" in ln or "urllib" in ln or "requests" in ln]
        self.assertEqual([ln for ln in reads if not ln.lstrip().startswith(("#", '"""'))
                          and "import" in ln], [], "探針路徑不得自己 import 額度讀取點")
        self.assertTrue(any("_pace_state" in ln for ln in self.lines("parkearly.py")))

    def test_at_ctl_59_the_planner_calls_parkearly_in_one_line_and_yields_stays_in_decide(
            self) -> None:
        planner = (_REPO_ROOT / "tools" / "session_resume_planner.py").read_text(
            encoding="utf-8").splitlines()
        calls = [ln for ln in planner if "parkearly.tick(" in ln]
        self.assertEqual(len(calls), 1)
        uses = [ln for ln in planner if "yields(" in ln and "def " not in ln]
        self.assertEqual(len(uses), 1, "park.yields 仍只在 sentinel_decide 內呼叫一次")
        tick_at = next(i for i, ln in enumerate(planner) if "sched_isolation.tick_gate(" in ln)
        probe_at = next(i for i, ln in enumerate(planner) if "parkearly.tick(" in ln)
        decide_at = next(i for i, ln in enumerate(planner)
                         if i > tick_at and "sentinel_decide(" in ln and "def " not in ln)
        self.assertLess(tick_at, probe_at)
        self.assertLess(probe_at, decide_at)


class _EarlyFence(_CliFence):
    """提前到點共同夾具：armed 標記（等 3 小時）、備援 job 在假排程器、假 spawn／resume。"""

    def setUp(self) -> None:
        super().setUp()
        self.backend.jobs.add(LABEL)
        self.marker = _early_marker(self.pkg)
        park.write_marker(self.marker)
        self.transcript = self.tmp / f"{SID}.jsonl"
        stale = (NOW - timedelta(hours=5)).isoformat()
        self.transcript.write_text(_line(type="assistant", timestamp=stale,
                                         message={"model": "claude-fable-5"}) + "\n",
                                   encoding="utf-8")
        os.utime(self.transcript, ((NOW - timedelta(hours=5)).timestamp(),) * 2)
        self.spawned: list[Path] = []
        self.resumed: list[dict] = []
        self.quota_reads: list = []
        self.jobs: list = []
        self.state = _keyed(_state(five=0.0, week=0.0), "acct-A")
        self.args = argparse.Namespace(
            plan=str(self.tmp / f"{quota_escalation.guard.PLAN_PREFIX}{SID}.md"))

    def seams(self, **extra) -> dict:
        def spawn(path, **_kw):
            self.spawned.append(path)
            return 0

        def resume(*_a, **kw):
            self.resumed.append(kw)
            return 0

        def quota(now):
            self.quota_reads.append(now)
            state = self.state
            if isinstance(state, Exception):
                raise state
            return state

        def run_job(argv, env):
            """真子行程的行程內替身：解回排程同 argv（`… park --fire …`）呼叫 CLI。"""
            self.jobs.append((list(argv), dict(env)))
            return park_cli.run(argv[2:], env=env, now=NOW, seams=base)

        base = {"quota": quota, "policy": _policy, "backend": self.backend, "spawn": spawn,
                "resume": resume, "platform": "win32", "preflight": lambda *_a, **_k: [],
                "transcript": lambda _s: self.transcript, "notify": lambda *_a: 0,
                "sessions_dir": self.tmp / "sessions"}
        return {**base, "run_job": run_job, **extra}

    def tick(self, now=NOW, env=None, **extra):
        return parkearly.tick(self.args, now, self.seams(**extra), env={**self.env, **(env or {})})

    def probes(self) -> list[dict]:
        return [t for t in self.traces() if t["event"] == parkprobe.EV_PROBE]

    def recovered_events(self) -> list[dict]:
        return [t for t in self.traces() if t["event"] == parkprobe.EV_RECOVERED]


class TickFiresThroughTheQ3PathTest(_EarlyFence, unittest.TestCase):
    """tools/lib/sessionctl/parkearly.py::tick／fire_early：讀數降到門檻下 ⇒ 走既有 `_cmd_fire`
    （AT-CTL-59／61／62／63／64；REQ-CTL-31／33／34／37；MU-CTL-32～36）。"""

    def test_recovered_reading_fires_once_and_tears_down_the_backup_job(self) -> None:
        verdict = self.tick()
        self.assertTrue(verdict["recovered"])
        self.assertEqual(verdict["fired"], "fired")
        self.assertEqual(park.read_marker(SID)["status"], "fired")
        self.assertNotIn(LABEL, self.backend.jobs, "備援排程隨 fire 自拆（QW 原規則）")
        self.assertEqual(self.spawned, [self.pkg], "上下文量不到 ⇒ FRESH 帶交接包")
        events = self.recovered_events()
        self.assertEqual(len(events), 1)
        self.assertAlmostEqual(events[0]["saved_min"], 180.0, places=1)
        self.assertIs(events[0]["account_changed"], False)

    def test_at_ctl_63_at_most_once_the_next_patrol_skips(self) -> None:
        self.tick()
        reads = len(self.quota_reads)
        self.assertIsNone(self.tick())
        self.assertEqual((len(self.recovered_events()), len(self.quota_reads)), (1, reads))

    def test_at_ctl_62_an_account_change_forces_cold_and_marks_the_route_reason(self) -> None:
        self.state = _keyed(_state(five=0.0, week=0.0), "acct-B")
        verdict = self.tick()
        self.assertTrue(verdict["account_changed"])
        routes = [t for t in self.traces() if t["event"] == "park_route"]
        self.assertTrue(routes[0]["why"].startswith("account_changed"), routes)
        self.assertIs(self.recovered_events()[0]["account_changed"], True)

    def test_at_ctl_62_force_cold_makes_a_mid_sized_context_pick_fresh(self) -> None:
        small, big = 20_000, 900_000
        self.assertEqual(park.fire_route(small, False)[0], park.FIRE_RESUME)
        forced = {park.FORCE_COLD_ENV: "1"}
        self.assertEqual(park.fire_route(small, False, forced)[0], park.FIRE_RESUME)
        route, why = park.fire_route(big, False, forced)
        self.assertEqual(route, park.FIRE_FRESH)
        self.assertTrue(why.startswith("account_changed"))
        self.assertEqual(park.fire_route(big, False, {})[0], park.FIRE_RESUME)
        self.assertEqual(park.fire_route(big, False)[0], park.FIRE_RESUME, "快取仍熱 ⇒ 續跑")
        self.assertFalse(park.fire_route(small, False)[1].startswith("account_changed"))

    def test_at_ctl_61_early_disables_only_the_reschedule_branch(self) -> None:
        row = {"pid": 4242, "sid": SID, **qw_schema.holder_extra(
            (NOW + timedelta(minutes=5)).timestamp(), "chain", "reset")}
        S = {"holder": lambda _s: row, "holder_live": lambda _r: True}
        env = {parkprobe.EARLY_ENV: "1"}
        normal = park_yield.decide(SID, self.marker, {}, S, lambda: NOW, lambda _s: None)
        self.assertEqual(normal["act"], "rearm", "非 early：主載具活著且未到 ⇒ 重排（舊行為）")
        early = park_yield.decide(SID, parkprobe.early_view(self.marker, env), {}, S,
                                  lambda: NOW, lambda _s: None)
        self.assertEqual((early["act"], early["reason"]), ("go", "yield_exhausted"))
        self.assertIs(parkprobe.early_view(self.marker, {}), self.marker)
        self.assertNotIn(park_yield.RESCHEDULES_KEY, self.marker, "early_view 只改記憶體副本")

    def test_the_reschedule_counter_on_disk_is_restored_after_an_early_fire(self) -> None:
        for before in (None, 2):
            with self.subTest(before=before):
                marker = _early_marker(self.pkg)
                if before is not None:
                    marker[park_yield.RESCHEDULES_KEY] = before
                park.write_marker(marker)
                self.backend.jobs.add(LABEL)
                self.assertEqual(self.tick()["fired"], "fired")
                self.assertEqual(park.read_marker(SID).get(park_yield.RESCHEDULES_KEY), before)

    def test_at_ctl_64_a_live_reset_primary_handles_it_but_an_at_primary_does_not(self) -> None:
        row = {"pid": 4242, "sid": SID,
               **qw_schema.holder_extra(NOW.timestamp() - 600, "chain", "reset")}
        with mock.patch.object(parkearly.holder, "read", return_value=row), \
                mock.patch.object(parkearly.holder, "is_live", return_value=True):
            park.write_marker(dict(self.marker, **{qw_schema.MK_PRIMARY_SOURCE: "reset"}))
            self.assertIsNone(self.tick(), "reset 型主載具活著 ⇒ 由 early_reset 處理，不重判")
            self.assertEqual(self.recovered_events(), [])
        with mock.patch.object(parkearly.holder, "read", return_value=row), \
                mock.patch.object(parkearly.holder, "is_live", return_value=False):
            park.write_marker(self.marker)  # primary_source=at：early_reset 不適用 ⇒ 本分支判
            self.assertTrue(self.tick()["recovered"])

    def test_at_ctl_59_unmeasured_returns_a_verdict_without_firing_and_traces_it(self) -> None:
        self.state = OSError("端點 500")
        verdict = self.tick()
        self.assertIsNone(verdict, "例外一律吞掉：探針不得讓哨兵巡邏死掉")
        self.assertEqual(park.read_marker(SID)["status"], "armed")
        self.assertIn(parkearly.EV_ERROR, [t["event"] for t in self.traces()])

    def test_at_ctl_66_an_empty_reading_is_traced_unmeasured_and_not_fired(self) -> None:
        self.state = _state(axes=())
        verdict = self.tick()
        self.assertEqual((verdict["reason"], verdict["recovered"]), ("unmeasured", False))
        self.assertEqual([p["reason"] for p in self.probes()], ["unmeasured"])
        self.assertEqual((self.spawned, self.recovered_events()), ([], []))

    def test_at_ctl_65_the_reading_goes_through_the_single_pace_state_seam(self) -> None:
        self.tick()
        self.assertEqual(len(self.quota_reads), 1)

    def test_the_probe_trace_carries_reading_baseline_and_reason(self) -> None:
        self.state = _keyed(_state(five=95.0, week=95.0), "acct-A")
        self.tick()
        probe = self.probes()[0]
        got = (probe["reason"], probe["reading"], probe["parked_pct"], probe["recovered"])
        self.assertEqual(got, ("hold", 95.0, 100.0, False))


class ChildProcessContractTest(_EarlyFence, unittest.TestCase):
    """tools/lib/sessionctl/parkearly.py::fire_early／_run_job：到點子行程的 argv 與環境契約。
    WHY：planner 對 `--sentinel-tick` 強制 `AUTOSDD_UNATTENDED=1`（DEF-200-272），行程內呼叫會被
    `park_fire`／`handoff.spawn` 的無人旗標擋下；所以必須是「排程同 argv、乾淨環境」的子行程。"""

    def test_a_forced_unattended_flag_in_the_tick_does_not_block_the_probe_nor_reach_the_child(
            self) -> None:
        verdict = self.tick(env={park.UNATTENDED_ENV: "1"})
        self.assertEqual(verdict["fired"], "fired")
        argv, child_env = self.jobs[0]
        self.assertNotIn(park.UNATTENDED_ENV, child_env)
        self.assertEqual(self.spawned, [self.pkg])

    def test_the_child_argv_is_the_scheduled_job_argv_plus_the_registered_claude(self) -> None:
        park.write_marker(dict(self.marker, claude=str(Path("x") / "fake-claude")))
        self.tick()
        argv, _env = self.jobs[0]
        fake = str(Path("x") / "fake-claude")
        want = park_cli.job_argv(LABEL, SID, self.pkg, FIRE_AT, ["--claude", fake])
        self.assertEqual(argv, want)
        self.assertEqual(argv[2:4], ["park", "--fire"])

    def test_the_child_env_carries_early_and_force_cold_only_for_an_account_change(self) -> None:
        self.tick()
        _argv, env = self.jobs[0]
        self.assertEqual((env.get(parkprobe.EARLY_ENV), park.FORCE_COLD_ENV in env), ("1", False))
        park.write_marker(self.marker)
        self.backend.jobs.add(LABEL)
        self.state = _keyed(_state(five=0.0, week=0.0), "acct-B")
        self.tick()
        _argv, env = self.jobs[1]
        self.assertEqual((env.get(parkprobe.EARLY_ENV), env.get(park.FORCE_COLD_ENV)), ("1", "1"))

    def test_a_child_that_cannot_start_leaves_the_marker_armed_and_is_traced(self) -> None:
        with mock.patch.object(parkearly.subprocess, "run", side_effect=OSError("找不到")):
            verdict = self.tick(run_job=parkearly._run_job)  # noqa: SLF001
        self.assertEqual(verdict["fired"], "armed")
        self.assertEqual(park.read_marker(SID)["status"], "armed")
        errs = [t for t in self.traces() if t["event"] == parkearly.EV_ERROR]
        self.assertEqual((errs[0]["error"], errs[0]["rc"]), ("child_rc", 127))
        self.assertEqual(self.recovered_events(), [])

    def test_the_real_runner_is_windowless_bounded_and_closes_stdin(self) -> None:
        import win_spawn
        with mock.patch.object(parkearly.subprocess, "run") as run:
            run.return_value.returncode = 0
            self.assertEqual(parkearly._run_job(["x"], {"A": "1"}), 0)  # noqa: SLF001
        kw = run.call_args.kwargs
        self.assertEqual((kw["creationflags"], kw["timeout"], kw["env"], kw["check"]),
                         (win_spawn.NO_WINDOW, parkearly.CHILD_TIMEOUT_SECONDS, {"A": "1"}, False))
        self.assertIs(kw["stdin"], parkearly.subprocess.DEVNULL)


class NegativeControlsTest(_EarlyFence, unittest.TestCase):
    """tools/lib/sessionctl/parkearly.py::tick：不誤觸發（AT-CTL-60；REQ-CTL-37；MU-CTL-30／34）。
    每例只改一個條件、替身 spawn 必須 0 次。"""

    def assert_silent(self, **kw) -> None:
        self.assertIsNone(self.tick(**kw) if kw else self.tick())
        self.assertEqual((self.spawned, self.resumed, self.recovered_events()), ([], [], []))
        self.assertEqual(park.read_marker(SID)["status"], "armed")

    def test_wait_shorter_than_sixty_minutes(self) -> None:
        late = NOW + timedelta(minutes=59)
        park.write_marker(dict(self.marker, fire_at=late.isoformat()))
        self.assert_silent()
        park.write_marker(dict(self.marker, fire_at=(NOW + timedelta(minutes=61)).isoformat()))
        self.assertIsNotNone(self.tick(), "61 分鐘 ⇒ 探")

    def test_acked_package(self) -> None:
        self.pkg.with_suffix(".ack").write_text("acked t sid=other", encoding="utf-8")
        self.assert_silent()

    def test_handed_over_or_spawning_intent(self) -> None:
        with mock.patch.object(parkearly.seal, "_spawned", return_value=True):
            self.assert_silent()
        with mock.patch.object(parkearly.handoff, "_duplicate_refusals", return_value=["剛 spawn"]):
            self.assert_silent()

    def test_live_driver(self) -> None:
        fresh = (NOW - timedelta(minutes=1)).isoformat()
        row = _line(type="assistant", timestamp=fresh, message={"model": "claude-fable-5"})
        self.transcript.write_text(row + "\n", encoding="utf-8")
        self.assert_silent()

    def test_non_auto_mode(self) -> None:
        self.assert_silent(env={"AUTOSDD_SESSION_SWITCH_MODE": "notify"})
        self.assert_silent(env={"AUTOSDD_SESSION_SWITCH_MODE": "off"})

    def test_reading_not_lower_or_barely_lower_or_still_above_prepare(self) -> None:
        for five in (100.0, 96.0, 90.0):  # 持平／降 4pp／降 10pp 但仍 ≥ 準備門檻 85
            with self.subTest(five=five):
                self.state = _keyed(_state(five=five, week=five), "acct-A")
                self.assertFalse(self.tick()["recovered"])
        self.assertEqual((self.spawned, self.recovered_events()), ([], []))

    def test_park_why_registration_does_not_fire_on_a_low_absolute_reading(self) -> None:
        park.write_marker(dict(self.marker, parked_pct=80.0))
        self.state = _keyed(_state(five=80.0, week=80.0), "acct-A")
        self.assertFalse(self.tick()["recovered"])
        self.assertEqual(self.spawned, [])

    def test_old_marker_without_baseline_traces_no_baseline_and_never_fires(self) -> None:
        old = {k: v for k, v in self.marker.items() if k not in ("parked_pct", "parked_account")}
        park.write_marker(old)
        verdict = self.tick()
        self.assertEqual((verdict["reason"], verdict["recovered"]), ("no_baseline", False))
        self.assertEqual(self.quota_reads, [], "無基準就不必量額度")
        self.assertEqual(self.spawned, [])

    def test_armed_but_expired_or_cancelled_markers_are_not_probed(self) -> None:
        park.write_marker(dict(self.marker, status="cancelled"))
        self.assertIsNone(self.tick())
        park.write_marker(dict(self.marker, status="armed",
                               valid_until=(NOW - timedelta(seconds=1)).isoformat()))
        self.assertIsNone(self.tick())
        self.assertEqual(self.quota_reads, [])

    def test_a_missing_marker_or_a_non_sid_plan_is_silent(self) -> None:
        park.marker_path(SID).unlink()
        self.assertIsNone(self.tick())
        self.args = argparse.Namespace(plan=str(self.tmp / "unknown.md"))
        self.assertIsNone(self.tick())
        self.assertIsNone(parkearly.tick(argparse.Namespace(), NOW, {}, env={}))


class BriefLineTest(_Fence, unittest.TestCase):
    """tools/lib/sessionctl/parkprobe.py::brief_line／briefline.py：連續 3 次量不到 ⇒ SessionStart
    出聲（AT-CTL-66；REQ-CTL-35）。"""

    def row(self, reason: str, n: int) -> dict:
        return {"event": parkprobe.EV_PROBE, "sid": SID, "reason": reason,
                "at": (NOW + timedelta(minutes=15 * n)).isoformat()}

    def write_rows(self, *rows: dict) -> None:
        with (self.tdir / park._SPAWNED_LOG).open("a", encoding="utf-8") as fh:  # noqa: SLF001
            fh.writelines(json.dumps(r) + "\n" for r in rows)

    def test_three_consecutive_unmeasured_probes_say_so(self) -> None:
        marker = _early_marker(None, valid_until=(NOW + timedelta(days=9)).isoformat())
        park.write_marker(marker)
        with mock.patch.object(parkprobe, "datetime", wraps=parkprobe.datetime) as dt:
            dt.now.return_value = NOW
            self.write_rows(self.row("unmeasured", 0), self.row("unmeasured", 1))
            self.assertEqual(parkprobe.brief_line({}), "")
            self.write_rows(self.row("unmeasured", 2))
            text = parkprobe.brief_line({})
            self.assertIn("連續 3 次量不到", text)
            self.assertIn("park --status", text)
            self.assertEqual(briefline.park_probe_line({}), text)
            self.write_rows(self.row("hold", 3))
            self.assertEqual(parkprobe.brief_line({}), "", "中間有一次量得到就重新累計")

    def test_no_armed_marker_or_any_exception_gives_an_empty_line(self) -> None:
        self.assertEqual(parkprobe.brief_line({}), "")
        with mock.patch.object(parkprobe.park, "read_marker", side_effect=RuntimeError("x")):
            park.write_marker(_early_marker(None))
            self.assertEqual(parkprobe.brief_line({}), "")

    def test_briefline_lines_joins_both_notes_and_stays_empty_when_both_are_empty(self) -> None:
        with mock.patch.object(briefline, "orphan_line", return_value=""), \
                mock.patch.object(briefline, "park_probe_line", return_value=""):
            self.assertEqual(briefline.lines(SID, {}), "")
        with mock.patch.object(briefline, "orphan_line", return_value=" A"), \
                mock.patch.object(briefline, "park_probe_line", return_value=" B"):
            self.assertEqual(briefline.lines(SID, {}), " A B")


class PlannerWiringTest(_Fence, unittest.TestCase):
    """tools/session_resume_planner.py::_sentinel_tick：探針接線（AT-CTL-59；REQ-CTL-31）。
    任務書檔名帶 `PLAN_PREFIX`，park 標記以裸 sid 為鍵——兩個哨兵分支都必須去前綴。"""

    def setUp(self) -> None:
        super().setUp()
        import session_resume_planner as planner
        self.planner = planner
        plan = self.tmp / f"{planner.PLAN_PREFIX}{SID}.md"
        self.args = planner.build_parser().parse_args(
            ["--sentinel-tick", "--plan", str(plan), "--task-name", "T-w6"])

    def test_both_probes_receive_the_bare_sid_after_the_gate_passes(self) -> None:
        planner, seen = self.planner, {}
        with mock.patch.object(planner.sched_isolation, "tick_gate", return_value=None), \
                mock.patch.object(planner.sessionctl_takeover, "on_patrol",
                                  side_effect=lambda sid, _log: seen.setdefault("takeover", sid)), \
                mock.patch.object(parkearly.park, "read_marker",
                                  side_effect=lambda sid: seen.setdefault("probe", sid) and None), \
                mock.patch.object(planner, "append_log", side_effect=RuntimeError("stop")):
            with self.assertRaises(RuntimeError):
                planner._sentinel_tick(self.args)  # noqa: SLF001
        self.assertEqual(seen, {"probe": SID, "takeover": SID})

    def test_a_refused_gate_returns_before_the_probe_runs(self) -> None:
        planner = self.planner
        with mock.patch.object(planner.sched_isolation, "tick_gate", return_value=7), \
                mock.patch.object(planner, "_schtasks_remove", return_value=0), \
                mock.patch.object(planner.parkearly, "tick") as probe:
            self.assertEqual(planner._sentinel_tick(self.args), 7)  # noqa: SLF001
        probe.assert_not_called()

    def test_a_probe_exception_never_kills_the_patrol(self) -> None:
        park.write_marker(_early_marker(self.package()))
        # WP-QV：提前恢復的取數改走判決（`park_reset.ruling_for`）；讓它拋例外
        with mock.patch("lib.sessionctl.park_reset.ruling_for", side_effect=RuntimeError("x")):
            self.assertIsNone(parkearly.tick(
                self.args, NOW, {"transcript": lambda _s: self.tmp / "none.jsonl"}, env=self.env))
        self.assertIn(parkearly.EV_ERROR, [t["event"] for t in self.traces()])


class StatusLineCompatTest(unittest.TestCase):
    """tools/lib/sessionctl/park_status.py：本包不改 SE／QW 既有三列（SE X-22：兩稿各自加列）。"""

    def test_park_status_lines_still_three_rows_and_early_row_is_separate(self) -> None:
        seams = {"backend": mock.Mock(name="b", list_jobs=lambda _p: [])}
        rows = park_status.lines(SID, None, seams)
        self.assertEqual([r.split(":")[0] for r in rows], ["primary", "backup", "sentinel"])


class WpSwUnmeasuredWhyTest(_EarlyFence, unittest.TestCase):
    """WP-SW REQ-CTL-51（AT-CTL-104～108）：提前探針量不到必帶具名原因（封閉值域）；fail-closed
    不變。
    WHY：痕跡第 1379、1381 行 `unmeasured reading=null` 無原因，根因只能靠推理。"""

    def whys(self) -> list:
        return [p.get("why") for p in self.probes() if p.get("reading") is None]

    def test_at_ctl_104_measure_exception_is_named_and_never_recovers(self) -> None:
        from lib.sessionctl import parkwhy  # noqa: PLC0415

        self.state = OSError("端點炸了")
        self.assertIsNone(self.tick(), "例外照舊吞掉、EV_ERROR 照舊落")
        self.assertIn(parkearly.EV_ERROR, [t["event"] for t in self.traces()])
        self.assertEqual(self.whys(), ["measure_exception:OSError"])
        self.assertEqual(self.recovered_events(), [])
        for why in self.whys():
            self.assertTrue(parkwhy.valid(why), why)
        self.assertFalse(parkwhy.valid(None), "負控：缺 why 即違規")
        self.assertFalse(parkwhy.valid("random_reason"))

    def test_at_ctl_105_each_closed_domain_value_has_a_fixture(self) -> None:
        import quota_gate  # noqa: PLC0415

        from lib.sessionctl import parkwhy  # noqa: PLC0415

        usable = _keyed(_state(five=0.0, week=0.0), "acct-A")
        empty = _state(axes=())
        cases = [
            ({"state": empty, "note": {"won": True, "reason": "no-credentials"}}, "no_credential"),
            ({"state": empty, "note": {"won": True, "reason": "no-credentials-darwin"}},
                "no_credential"),
            ({"state": empty, "note": {"won": False, "reason": ""}}, "claim_lost"),
            ({"state": empty, "note": {"won": True, "reason": "http-429-unmeasured"}},
                "http_error:429"),
            ({"state": empty, "note": {"won": True, "reason": "http-503"}}, "http_error:503"),
            ({"state": empty, "note": {"won": True, "reason": "meter-unreachable"}}, "timeout"),
            ({"state": empty, "note": {}}, "stale_cache"),
            ({"state": _keyed(usable, None), "expected_account": "acct-A"}, "account_unreadable"),
            ({"state": usable, "expected_account": "acct-A"}, ""),
        ]
        for kwargs, want in cases:
            with self.subTest(want=want, note=kwargs.get("note")):
                got = parkwhy.classify(**kwargs)
                self.assertEqual(got, want)
                self.assertTrue(not got or parkwhy.valid(got))
        with mock.patch.object(sys, "stderr", None):
            self.assertEqual(parkwhy.classify(exc=AttributeError("write")), "stdio_none")
        self.assertEqual(parkwhy.classify(exc=AttributeError("write")),
            "measure_exception:AttributeError")
        # tick 層：no_credential 取自 `pace_state` 補量旁記（MEASURE_NOTE），tick 先清再讀

        def fake_pace(_now):
            quota_gate.MEASURE_NOTE.update(won=True, reason="no-credentials")
            return empty

        with mock.patch.object(quota_gate, "pace_state", fake_pace):
            self.tick(quota=None)
        self.assertEqual(self.whys(), ["no_credential"])

    def test_at_ctl_106_account_switch_timeline_recovers_within_two_patrols(self) -> None:
        """tick1：舊帳號、讀數仍高 ⇒ hold；tick2：新帳號 weekly 0% ⇒ 提前接手。"""
        self.state = _keyed(_state(five=95.0, week=95.0), "acct-A")
        self.assertFalse(self.tick()["recovered"])
        self.state = _keyed(_state(five=0.0, week=0.0), "acct-B")
        verdict = self.tick(now=NOW + timedelta(minutes=15))
        self.assertTrue(verdict["recovered"] and verdict["account_changed"])
        self.assertEqual(verdict["fired"], "fired")
        self.assertEqual(len(self.recovered_events()), 1)
        self.assertLessEqual(15 * 60, 2 * 900 + parkearly.CHILD_TIMEOUT_SECONDS)

    def test_at_ctl_107_fail_closed_is_unchanged(self) -> None:
        self.state = _state(axes=())
        verdict = self.tick()
        self.assertFalse(verdict["recovered"])
        self.assertTrue(self.whys() and self.whys()[0], "量不到必有 why")
        self.assertEqual((self.spawned, self.recovered_events()), ([], []))

    def test_at_ctl_108_pythonw_root_cause_note(self) -> None:
        """AT-CTL-108：根因探針的程式面證據——補量旁記 `MEASURE_NOTE` 由 `pace_state`
        寫（won／reason），
        量測路徑在 `STDIO` 縫（stderr 為 None、SSOT 已綁 devnull）下不拋；真 pythonw 重放見
        E2E-CTL-25。"""
        import quota_gate  # noqa: PLC0415

        import _stdio_utf8  # noqa: PLC0415

        with mock.patch.object(sys, "stderr", None), mock.patch.object(sys, "stdout", None):
            _stdio_utf8.reconfigure_stdio_utf8()
            quota_gate.MEASURE_NOTE.clear()
            with mock.patch.object(quota_gate, "read_quota", return_value=_state(axes=())), \
                    mock.patch.object(quota_gate, "claim_refresh_slot", return_value=True), \
                    mock.patch.object(quota_gate, "settled_quota", return_value=_state(axes=())), \
                    mock.patch.object(quota_gate.quota_meter, "measure_detail",
                                      return_value=(None, "no-credentials")):
                quota_gate.pace_state(NOW)
            self.assertEqual(quota_gate.MEASURE_NOTE, {"won": True, "reason": "no-credentials"})


if __name__ == "__main__":
    unittest.main()
