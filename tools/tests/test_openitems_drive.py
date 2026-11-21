"""tools/lib/openitems 的驅動器（A2；TCS-WorkProgress
REQ-WP-05／08／10／11／12／13／17／19／26／27／28／97、
AT-WP-04／06／07／10～16／19／29／50／51／52～57／66／67～69／95）。

WHY：驅動器是「還有什麼沒做完」真的被做完的唯一手腳，它說謊的方向有四個：憑證空也宣稱已排程、
同時燒多支 `claude -p`、讓路／額度失效時照跑、重排失敗卻讓項目永遠算 driven。
縫（TCS §3）：`SCH`＝假排程後端、`RUN`＝假 runner、`Q`＝假 `--pace`、
`TR`＝真檔案系統上的合成逐字稿、`NOW`＝可撥時鐘；鎖與帳本走真檔案、
行程身分走真行程。不 monkeypatch 被測物，外部效應一律從 `Deps` 參數注入。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

from lib.openitems import drive, driver_run, evidence, schedcache, throttle  # noqa: E402
from lib.openitems import ledger as oi_ledger  # noqa: E402
from lib.openitems import params as oi_params  # noqa: E402
from lib.openitems.fold import fold  # noqa: E402

TZ = timezone(timedelta(hours=8))
T0 = datetime(2026, 11, 20, 12, 0, tzinfo=TZ)
SRC = "docs/03_testing/contracts/TCS-WorkProgress-20261119.md:277"
RV_CHECK = {"realverify": "RV-L1"}
OK_PACE = throttle.Pace(True, 2, {"session": "free", "five_hour": "free", "weekly_all": "free",
                                  "seven_day": "free"}, 120.0)
REAL_PACE_TEXT = (
    "現在可派 0 個 agent（硬上限 cap=1，本視窗已用 1 次）｜band=prepare｜"
    "最緊的一條＝seven_day 95% 剩 6874 分鐘\n"
    "  kind=session 7% 剩 294 分鐘 band=converge horizon=far cap=1 note=x；"
    "kind=weekly_all 95% 剩 6874 分鐘 "
    "band=prepare horizon=far cap=1；kind=five_hour 7% 剩 294 分鐘 band=free horizon=far cap=1；"
    "kind=seven_day 95% 剩 6874 分鐘 band=prepare；kind=extra_usage 0% reset 距離不明 band=free "
    "horizon=none cap=None note=missing\n")


class Clock:
    def __init__(self, at: datetime = T0) -> None:
        self.t = at

    def __call__(self) -> datetime:
        return self.t


class FakeBackend:
    """`SCH`：假排程後端。`credential` 空字串＝回讀不到憑證；`fail_after`＝第 N 次註冊後回空。"""

    name = "fake"

    def __init__(self, credential: str = "2026/11/20 12:02:00",
                 fail_after: int | None = None) -> None:
        self.credential, self.fail_after = credential, fail_after
        self.tasks: dict[str, datetime] = {}
        self.unregistered: list[str] = []
        self.registered = 0
        self.listed = 0

    def register(self, task, at, argv, cwd):
        self.registered += 1
        self.tasks[task] = at
        return "" if self.fail_after is not None and self.registered > self.fail_after \
            else self.credential

    def unregister(self, task):
        self.unregistered.append(task)
        self.tasks.pop(task, None)
        return True

    def list_tasks(self, prefix):
        self.listed += 1
        return {t: "" for t in self.tasks if t.startswith(prefix)}


class FakeRun:
    """`RUN`：假 runner。`script` 逐次回 `(rc, stdout)`；pass 時照真 realverify 往帳本追加一列。"""

    def __init__(self, root: Path, clock: Clock, script=None,
                 default=(0, "REALVERIFY_VERDICT=pass")):
        self.root, self.clock, self.script, self.default = root, clock, list(script or []), default
        self.calls: list[list[str]] = []

    def __call__(self, argv, timeout_s, env, cwd):
        self.calls.append(list(argv))
        rc, out = self.script.pop(0) if self.script else self.default
        if rc == 0 and "REALVERIFY_VERDICT=pass" in out:
            path = Path(self.root) / evidence.RV_LEDGER_REL
            path.parent.mkdir(parents=True, exist_ok=True)
            stamp = self.clock().astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(f"| {stamp} | RV-L1 | pass | 1 | - | - | 5 |\n")
        return rc, out


def make_root(**overrides) -> Path:
    root = Path(tempfile.mkdtemp(prefix="oi_drv_"))
    data = json.loads((_REPO / oi_params.PARAMS_REL).read_text(encoding="utf-8"))
    data.update(overrides)
    dest = root / oi_params.PARAMS_REL
    dest.parent.mkdir(parents=True)
    dest.write_text(json.dumps(data), encoding="utf-8")
    return root


class DriverCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = make_root()
        self.params = oi_params.load(self.root)
        self.clock = Clock()
        self.backend = FakeBackend()
        self.trace = self.root / "_trace"
        patcher = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.trace)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.root, True)

    def deps(self, **kw) -> driver_run.Deps:
        base = {"backend": self.backend, "now": self.clock, "pace": lambda _n: OK_PACE,
                "interactive": lambda _r, _n: False, "identity": lambda _p: "T0",
                "run": FakeRun(self.root, self.clock), "coverage": lambda _r: "ok",
                "case_info": lambda _c: drive.CaseInfo(wall_minutes=60), "pid": 4242}
        base.update(kw)
        return driver_run.Deps(**base)

    def open_item(self, kind="auto", check=None, minutes=0.0, **kw) -> str:
        def make(events):
            ev = {"ev": "open", "id": oi_ledger.next_id(events, T0), "by": "human", "title": "t",
                  "source": SRC, "scope": "r217", "kind": kind,
                  "ts": (T0 + timedelta(minutes=minutes - 60)).isoformat(timespec="seconds"),
                  "check": check or RV_CHECK}
            ev.update(kw)
            return [ev]
        return oi_ledger.append(self.root, make)[0]["id"]

    def drive_item(self, item_id: str, at: datetime | None = None) -> dict:
        return drive.drive_item(self.root, self.params, item_id, backend=self.backend,
                                now=self.clock(), by="human", at=at)

    def events(self, item_id: str | None = None) -> list[dict]:
        evs = oi_ledger.read_events(oi_params.ledger_path(self.root))[0]
        return [e for e in evs if item_id is None or e["id"] == item_id]

    def item(self, item_id: str) -> dict:
        return fold(self.events(), self.params, self.clock()).items[item_id]

    def advance(self, item_id: str) -> dict:
        """把時鐘撥到該列 `d.at` 之後 1 分鐘（不倒退）並回該列的 `drive` 事件。"""
        d = self.item(item_id)["drive"]
        self.clock.t = max(self.clock.t, oi_ledger.parse_ts(d["at"]) + timedelta(minutes=1))
        return d

    def fire(self, item_id: str, deps: driver_run.Deps | None = None) -> str:
        """以該列的排程工作名觸發一次 run-driver。"""
        d = self.advance(item_id)
        run = deps or self.deps()
        return driver_run.run_driver(self.root, self.params, item_id, d["task"], run)

    def evs(self, item_id: str, name: str) -> list[dict]:
        return [e for e in self.events(item_id) if e["ev"] == name]


class DriveVerbTest(DriverCase):
    def test_empty_credential_means_no_drive_event_and_task_revoked(self):  # AT-WP-10／MU-WP-05
        self.backend.credential = ""
        item_id = self.open_item()
        with self.assertRaises(drive.DriveFailed):
            self.drive_item(item_id)
        self.assertEqual(self.evs(item_id, "drive"), [])
        self.assertEqual(len(self.backend.unregistered), 1)
        self.assertEqual(self.backend.tasks, {})

    def test_success_records_raw_credential_and_task_name(self):  # REQ-WP-10
        item_id = self.open_item()
        ev = self.drive_item(item_id)
        self.assertEqual(ev["credential"], self.backend.credential)
        self.assertTrue(ev["task"].startswith(self.params["task_prefix"] + item_id + "_"))
        self.assertGreaterEqual(oi_ledger.parse_ts(ev["at"]), T0 + timedelta(minutes=2))

    def test_redrive_unregisters_the_previous_task(self):
        item_id = self.open_item()
        first = self.drive_item(item_id)
        self.clock.t = T0 + timedelta(minutes=30)
        second = self.drive_item(item_id)
        self.assertNotEqual(first["task"], second["task"])
        self.assertIn(first["task"], self.backend.unregistered)

    def test_terminal_human_and_escalated_items_are_rejected(self):
        human = self.open_item("human", why_not_auto="只能由掌舵者目視畫面", check=None)
        with self.assertRaises(oi_ledger.Reject):
            self.drive_item(human)
        self.assertEqual(self.backend.registered, 0)

    def test_thirty_drives_are_staggered(self):  # AT-WP-55／MU-WP-14
        ids = [self.open_item(minutes=i / 60) for i in range(30)]
        ats = sorted(oi_ledger.parse_ts(self.drive_item(i)["at"]) for i in ids)
        gaps = [(b - a).total_seconds() / 60 for a, b in zip(ats, ats[1:], strict=False)]
        self.assertGreaterEqual(min(gaps), self.params["stagger_minutes"])

    def test_observe_is_driven_at_its_due_time(self):
        due = (T0 + timedelta(hours=5)).isoformat(timespec="seconds")
        check = {"argv": ["python", "-c", "1"], "pass": "rc0"}
        item_id = self.open_item("observe", check=check, due=due)
        at = oi_ledger.parse_ts(self.drive_item(item_id)["at"])
        self.assertEqual(at, T0 + timedelta(hours=5))

    def test_pick_slot_is_bounded_and_finds_first_gap(self):
        taken = [T0 + timedelta(minutes=m) for m in (0, 10, 20)]
        self.assertEqual(throttle.pick_slot(T0, taken, 10), T0 + timedelta(minutes=30))
        self.assertEqual(throttle.pick_slot(T0 + timedelta(minutes=45), taken, 10),
                         T0 + timedelta(minutes=45))


class SchedCacheTest(DriverCase):
    def test_cache_gives_exists_missing_and_unknown_when_stale(self):  # AT-WP-04
        item_id = self.open_item()
        ev = self.drive_item(item_id, at=T0 + timedelta(minutes=60))
        before = T0 + timedelta(minutes=1)
        schedcache.refresh(self.params, self.backend, before)
        fresh = fold(self.events(), self.params, before, schedcache.exists_fn(self.params, before))
        self.assertFalse(fresh.items[item_id]["undriven"])
        self.backend.tasks.pop(ev["task"])
        schedcache.refresh(self.params, self.backend, before)
        gone = fold(self.events(), self.params, before, schedcache.exists_fn(self.params, before))
        self.assertEqual(gone.items[item_id]["undriven_reason"], "scheduled_task_missing")
        stale_at = before + timedelta(seconds=self.params["sched_cache_ttl_seconds"] + 5)
        lookup = schedcache.exists_fn(self.params, stale_at)
        unknown = fold(self.events(), self.params, stale_at, lookup)
        self.assertFalse(unknown.items[item_id]["undriven"])  # 快取過期＝量不到＝依帳本視為有效

    def test_failed_enumeration_keeps_the_old_cache(self):
        schedcache.refresh(self.params, self.backend, T0)
        blind = types.SimpleNamespace(name="x", list_tasks=lambda _p: None)
        self.assertIsNone(schedcache.refresh(self.params, blind, T0 + timedelta(minutes=1)))
        self.assertEqual(schedcache.read(self.params, T0 + timedelta(minutes=2)), {})

    def test_after_trigger_empty_next_run_time_does_not_change_the_verdict(self):  # AT-WP-50／51
        item_id = self.open_item()
        ev = self.drive_item(item_id)
        at = oi_ledger.parse_ts(ev["at"])
        cache = {"at": (at + timedelta(minutes=14)).isoformat(), "platform": "x",
                 "prefix": self.params["task_prefix"], "tasks": {ev["task"]: ""}}
        path = schedcache.cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache), encoding="utf-8")
        for minutes, undriven in ((14, False), (16, True)):
            now = at + timedelta(minutes=minutes)
            cache["at"] = now.isoformat()
            path.write_text(json.dumps(cache), encoding="utf-8")
            got = fold(self.events(), self.params, now, schedcache.exists_fn(self.params, now))
            self.assertEqual(got.items[item_id]["undriven"], undriven)

    def test_list_verify_enumerates_exactly_once_for_any_row_count(self):  # AT-WP-57（列舉面）
        for _ in range(5):
            self.drive_item(self.open_item())
        schedcache.refresh(self.params, self.backend, T0)
        self.assertEqual(self.backend.listed, 1)


class RunDriverTest(DriverCase):
    def test_start_event_precedes_everything_with_budget(self):  # AT-WP-29／REQ-WP-08
        item_id = self.open_item()
        d = self.drive_item(item_id)
        deps = self.deps(case_info=lambda _c: drive.CaseInfo(long=True, wall_minutes=180))
        self.fire(item_id, deps)
        start = self.evs(item_id, "start")[0]
        self.assertEqual(start["budget_minutes"], 195)
        self.assertEqual(start["drive_seq"], self.item(item_id)["drive"]["seq"])
        self.assertEqual(d["task"], self.item(item_id)["drive"]["task"])
        self.assertEqual([e["ev"] for e in self.events(item_id)][:3], ["open", "drive", "start"])

    def test_observe_budget_is_the_observe_timeout(self):
        item_id = self.open_item("observe", check={"argv": ["python", "-c", "1"], "pass": "rc0"},
                                 due=T0.isoformat(timespec="seconds"))
        self.drive_item(item_id)
        self.fire(item_id)
        self.assertEqual(self.evs(item_id, "start")[0]["budget_minutes"],
                         self.params["observe_timeout_minutes"])

    def test_pass_writes_attempt_and_close_with_ledger_coordinate(self):  # AT-WP-12
        item_id = self.open_item()
        task = self.drive_item(item_id)["task"]
        line = self.fire(item_id)
        self.assertTrue(line.startswith(f"OPENITEMS_DRIVER=pass id={item_id} n=1"))
        self.assertEqual(self.item(item_id)["state"], "closed")
        self.assertIn("RealVerify_Result_Ledger.md", self.evs(item_id, "close")[0]["evidence"])
        self.assertIn(task, self.backend.unregistered)

    def test_closed_item_is_a_noop_that_deletes_its_task(self):  # AT-WP-11
        item_id = self.open_item()
        task = self.drive_item(item_id)["task"]
        self.fire(item_id)
        self.backend.unregistered.clear()
        line = driver_run.run_driver(self.root, self.params, item_id, task, self.deps())
        self.assertTrue(line.startswith(f"OPENITEMS_DRIVER=noop id={item_id}"))
        self.assertEqual(self.backend.unregistered, [task])

    def test_fail_redrives_after_retry_backoff_then_escalates(self):  # AT-WP-13／06
        item_id = self.open_item()
        self.drive_item(item_id)
        fail = (1, "REALVERIFY_VERDICT=fail")
        deps = self.deps(run=FakeRun(self.root, self.clock, [fail, fail]))
        first = self.fire(item_id, deps)
        self.assertIn("OPENITEMS_DRIVER=fail", first)
        redrive = self.item(item_id)["drive"]
        self.assertGreaterEqual(oi_ledger.parse_ts(redrive["at"]) - self.clock(),
                                timedelta(minutes=self.params["retry_backoff_minutes"] - 1))
        second = self.fire(item_id, deps)
        self.assertIn("OPENITEMS_DRIVER=escalated", second)
        self.assertEqual(self.item(item_id)["state"], "escalated")
        self.assertEqual(len(self.evs(item_id, "drive")), 2)  # 第 2 次後不再寫 drive

    def test_redrive_failure_says_so_and_item_turns_undriven(self):  # AT-WP-66(c)／MU-WP-17
        item_id = self.open_item()
        self.backend.fail_after = 1
        self.drive_item(item_id)
        deps = self.deps(run=FakeRun(self.root, self.clock, [(1, "REALVERIFY_VERDICT=fail")]))
        line = self.fire(item_id, deps)
        self.assertIn("redrive=failed", line)
        self.assertEqual(len(self.evs(item_id, "drive")), 1)
        later = self.clock() + timedelta(minutes=self.params["followup_grace_minutes"] + 1)
        self.assertTrue(fold(self.events(), self.params, later).items[item_id]["undriven"])

    def test_coverage_failure_is_loud_but_does_not_change_the_verdict(self):  # AT-WP-95(d)
        item_id = self.open_item()
        self.drive_item(item_id)
        line = self.fire(item_id, self.deps(coverage=lambda _r: "failed"))
        self.assertIn("OPENITEMS_DRIVER=pass", line)
        self.assertIn("coverage=failed", line)
        self.assertEqual(self.item(item_id)["state"], "closed")

    def test_observe_argv_rule_match_closes_and_mismatch_fails(self):  # AT-WP-16
        for rule, run, state in (("regex:HELLO", (0, "say HELLO"), "closed"),
                                 ("regex:HELLO", (0, "nope"), "driven")):
            item_id = self.open_item("observe", check={"argv": ["python", "-c", "1"], "pass": rule},
                                     due=self.clock().isoformat(timespec="seconds"))
            self.drive_item(item_id)
            self.fire(item_id, self.deps(run=FakeRun(self.root, self.clock, [run])))
            self.assertEqual(self.item(item_id)["state"], state)

    def test_realverify_pass_without_ledger_row_in_the_real_repo_root_is_not_a_pass(self):
        item_id = self.open_item()
        self.drive_item(item_id)
        # 帳本不在本根、本根又不是真 repo：退認 stdout 末行，證據字串誠實標出「本根帳本未更新」
        silent = lambda argv, t, e, c: (0, "REALVERIFY_VERDICT=pass")  # noqa: E731
        self.fire(item_id, self.deps(run=silent))
        self.assertIn("本根帳本未更新", self.evs(item_id, "close")[0]["evidence"])

    def test_item_driven_by_a_newer_task_makes_the_old_task_a_stale_noop(self):
        item_id = self.open_item()
        old = self.drive_item(item_id)["task"]
        self.clock.t += timedelta(minutes=30)
        self.drive_item(item_id)
        line = driver_run.run_driver(self.root, self.params, item_id, old, self.deps())
        self.assertIn("OPENITEMS_DRIVER=noop", line)
        self.assertEqual(self.evs(item_id, "start"), [])

    def test_stale_pass_failure_does_not_swallow_the_drive(self):
        item_id = self.open_item()
        self.drive_item(item_id)

        def boom(*_a):
            raise RuntimeError("scan down")
        self.assertIn("OPENITEMS_DRIVER=pass", self.fire(item_id, self.deps(stale=boom)))


class YieldAndQuotaTest(DriverCase):
    def test_interactive_three_minutes_ago_defers_without_an_attempt(self):  # AT-WP-14
        projects = self.root / "projects"
        projects.mkdir()
        item_id = self.open_item()
        self.drive_item(item_id)
        d = self.advance(item_id)
        seen = self.clock().astimezone(UTC) - timedelta(minutes=3)
        transcript = projects / "s1.jsonl"
        record = {"type": "assistant", "timestamp": seen.isoformat().replace("+00:00", "Z")}
        transcript.write_text(json.dumps(record) + "\n", encoding="utf-8")
        os.utime(transcript, (seen.timestamp(), seen.timestamp()))  # 假時鐘下 mtime 預篩也要對得上
        deps = self.deps(interactive=lambda r, n: throttle.interactive_active(r, n, projects))
        line = driver_run.run_driver(self.root, self.params, item_id, d["task"], deps)
        att = self.evs(item_id, "attempt")[0]
        self.assertEqual((att["result"], att["reason"]), ("deferred", "interactive"))
        self.assertIn("reason=interactive", line)
        self.assertEqual(self.item(item_id)["attempts"], 0)

    def test_old_interactive_activity_does_not_yield(self):
        projects = self.root / "projects"
        projects.mkdir()
        stamp = self.clock().astimezone(UTC) - timedelta(minutes=40)
        transcript = projects / "s1.jsonl"
        record = {"type": "assistant", "timestamp": stamp.isoformat().replace("+00:00", "Z")}
        transcript.write_text(json.dumps(record) + "\n", encoding="utf-8")
        now_ts = self.clock().timestamp()
        os.utime(transcript, (now_ts, now_ts))  # mtime 新、記錄舊
        self.assertFalse(throttle.interactive_active(self.root, self.clock(), projects))

    def test_six_interactive_deferrals_escalate_with_zero_attempts(self):  # AT-WP-07／AT-WP-69 後半
        item_id = self.open_item()
        self.drive_item(item_id)
        deps = self.deps(interactive=lambda _r, _n: True)
        for _ in range(self.params["max_deferrals"]):
            self.fire(item_id, deps)
        self.assertEqual(self.item(item_id)["state"], "escalated")
        self.assertEqual(self.item(item_id)["attempts"], 0)

    def test_converge_band_defers_quota_and_redrives_after_reset(self):  # AT-WP-15
        item_id = self.open_item()
        self.drive_item(item_id)
        hot = throttle.Pace(True, 2, {**OK_PACE.bands, "session": "converge"}, 40.0)
        self.fire(item_id, self.deps(pace=lambda _n: hot))
        self.assertEqual(self.evs(item_id, "attempt")[0]["reason"], "quota")
        self.assertGreaterEqual(oi_ledger.parse_ts(self.item(item_id)["drive"]["at"]),
                                self.clock() + timedelta(minutes=40))
        self.assertEqual(self.item(item_id)["deferrals"], 0)

    def test_three_quota_failure_shapes_all_defer_and_never_run(self):  # AT-WP-56
        shapes = (throttle.Pace(True, 2, {**OK_PACE.bands, "weekly_all": "converge"}, 120.0),
                  throttle.Pace(True, 0, OK_PACE.bands, 120.0),
                  throttle.Pace(False, reason="pace_rc"))
        for pace in shapes:
            item_id = self.open_item()
            self.drive_item(item_id)
            runner = FakeRun(self.root, self.clock)
            self.fire(item_id, self.deps(pace=lambda _n, p=pace: p, run=runner))
            self.assertEqual(runner.calls, [])
            self.assertEqual(self.evs(item_id, "attempt")[0]["reason"], "quota")

    def test_unreadable_pace_redrives_after_retry_backoff(self):
        item_id = self.open_item()
        self.drive_item(item_id)
        self.fire(item_id, self.deps(pace=lambda _n: throttle.Pace(False, reason="pace_rc")))
        gap = oi_ledger.parse_ts(self.item(item_id)["drive"]["at"]) - self.clock()
        self.assertGreaterEqual(gap, timedelta(minutes=self.params["retry_backoff_minutes"] - 1))

    def test_parse_pace_reads_the_real_report_shape(self):
        pace = throttle.parse_pace(REAL_PACE_TEXT, T0)
        self.assertTrue(pace.ok)
        self.assertEqual((pace.dispatchable, pace.short_reset_min), (0, 294.0))
        self.assertEqual(pace.bands["session"], "converge")
        self.assertNotIn("extra_usage", pace.bands)
        self.assertTrue(pace.deferral())
        self.assertFalse(throttle.parse_pace("亂碼", T0).ok)


class LockTest(DriverCase):
    def hold(self, pid: int, budget: int = 60, started: datetime | None = None,
             lane="normal") -> None:
        path = throttle.oi_dir() / throttle.LOCK_FILES[lane]
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {"pid": pid, "proc_start": "T0", "id": "OI-X", "budget_minutes": budget,
                "started_at": (started or self.clock()).isoformat()}
        path.write_text(json.dumps(body), encoding="utf-8")

    def test_alive_holder_blocks_dead_or_overbudget_holder_is_taken_over(self):  # AT-WP-53
        alive = lambda _p: "T0"  # noqa: E731
        dead = lambda _p: None  # noqa: E731
        self.hold(999)
        got = throttle.acquire("normal", "OI-A", 60, self.clock(), identity=alive, pid=1)
        self.assertFalse(got)
        self.assertTrue(throttle.acquire("normal", "OI-A", 60, self.clock(), identity=dead, pid=1))
        throttle.release("normal", 1)
        self.hold(999, budget=30)
        later = self.clock() + timedelta(minutes=31)
        self.assertTrue(throttle.acquire("normal", "OI-A", 60, later, identity=alive, pid=1))
        throttle.release("normal", 1)
        throttle.release("normal", 1)
        self.hold(999)  # pid 被別的行程重用：建立時間對不上 ⇒ 不是原持有者 ⇒ 接手
        self.assertTrue(throttle.acquire("normal", "OI-A", 60, self.clock(),
                                         identity=lambda p: "T0" if p == 1 else "reused", pid=1))

    def test_busy_defers_without_touching_attempts_or_deferrals(self):  # AT-WP-53
        item_id = self.open_item()
        self.drive_item(item_id)
        self.hold(999)
        self.fire(item_id)
        att = self.evs(item_id, "attempt")[0]
        self.assertEqual(att["reason"], "busy")
        got = self.item(item_id)
        self.assertEqual((got["attempts"], got["deferrals"]), (0, 0))

    def test_soak_lane_does_not_take_the_normal_lock_or_a_window_slot(self):  # REQ-WP-97
        item_id = self.open_item()
        self.drive_item(item_id)
        self.hold(999)  # 一般鎖被別人持有
        for _ in range(3):
            throttle.record_run(self.clock(), "OI-other")  # 本窗名額也滿了
        deps = self.deps(case_info=lambda _c: drive.CaseInfo(kind="soak", wall_minutes=600))
        self.assertIn("OPENITEMS_DRIVER=pass", self.fire(item_id, deps))
        self.assertEqual(throttle.runs_in_window(T0 - timedelta(days=1)), 3)  # soak 不記每窗次數

    def test_lock_is_released_after_the_run_even_on_defer(self):
        item_id = self.open_item()
        self.drive_item(item_id)
        self.fire(item_id, self.deps(pace=lambda _n: throttle.Pace(False, reason="pace_rc")))
        self.assertFalse((throttle.oi_dir() / "driver.lock").exists())

    def test_real_processes_exclude_each_other_and_a_killed_holder_is_taken_over(self):
        sleeper = [sys.executable, "-c", "import time; time.sleep(60)"]
        child = subprocess.Popen(sleeper,  # noqa: S603
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.addCleanup(child.kill)
        self.assertIsNotNone(throttle.proc_identity(os.getpid()))
        self.assertIsNone(throttle.proc_identity(2**30))
        now = datetime.now().astimezone()
        self.assertTrue(throttle.acquire("normal", "OI-A", 60, now, pid=child.pid))
        self.assertFalse(throttle.acquire("normal", "OI-B", 60, now))
        child.kill()
        child.wait(timeout=30)
        self.assertTrue(throttle.acquire("normal", "OI-B", 60, now))
        throttle.release("normal")


class WindowCapTest(DriverCase):
    def test_full_window_defers_window_cap_after_observed_reset(self):  # AT-WP-54
        item_id = self.open_item()
        self.drive_item(item_id)
        d = self.item(item_id)["drive"]
        self.clock.t = oi_ledger.parse_ts(d["at"]) + timedelta(minutes=1)
        for _ in range(2):
            throttle.record_run(self.clock() - timedelta(minutes=10), "OI-other")
        pace = throttle.Pace(True, 2, OK_PACE.bands, 50.0)
        deps = self.deps(pace=lambda _n: pace)
        driver_run.run_driver(self.root, self.params, item_id, d["task"], deps)
        self.assertEqual(self.evs(item_id, "attempt")[0]["reason"], "window_cap")
        self.assertGreaterEqual(oi_ledger.parse_ts(self.item(item_id)["drive"]["at"]),
                                self.clock() + timedelta(minutes=50))

    def test_unobserved_reset_uses_rolling_window_and_retry_backoff(self):  # AT-WP-54
        item_id = self.open_item()
        self.drive_item(item_id)
        d = self.item(item_id)["drive"]
        self.clock.t = oi_ledger.parse_ts(d["at"]) + timedelta(minutes=1)
        for _ in range(2):
            throttle.record_run(self.clock() - timedelta(minutes=10), "OI-other")
        blind = throttle.Pace(False, reason="pace_rc")
        deps = self.deps(pace=lambda _n: blind)
        driver_run.run_driver(self.root, self.params, item_id, d["task"], deps)
        self.assertEqual(self.evs(item_id, "attempt")[0]["reason"], "window_cap")
        gap = oi_ledger.parse_ts(self.item(item_id)["drive"]["at"]) - self.clock()
        self.assertGreaterEqual(gap, timedelta(minutes=self.params["retry_backoff_minutes"] - 1))
        start, end = throttle.window(self.clock(), None, self.params)
        span = timedelta(minutes=self.params["cap_window_minutes"])
        self.assertEqual((self.clock() - start, end), (span, None))

    def test_older_queued_item_keeps_the_last_slot_over_a_newer_one(self):  # AT-WP-68／MU-WP-19
        old = self.open_item(minutes=0)
        new = self.open_item(minutes=1)
        self.drive_item(old, at=T0 + timedelta(minutes=60))
        self.drive_item(new, at=T0 + timedelta(minutes=30))
        throttle.record_run(T0 + timedelta(minutes=5), "OI-other")  # 本窗已用 1、名額剩 1
        self.clock.t = T0 + timedelta(minutes=31)
        self.fire(new)
        self.assertEqual(self.evs(new, "attempt")[0]["reason"], "window_cap")
        self.clock.t = T0 + timedelta(minutes=61)
        self.fire(old)
        self.assertEqual(self.evs(old, "attempt")[0]["result"], "pass")

    def test_only_interactive_deferrals_are_spent(self):  # AT-WP-69／MU-WP-18
        item_id = self.open_item()
        self.drive_item(item_id)
        hot = throttle.Pace(False, reason="pace_rc")
        for _ in range(10):  # quota
            self.fire(item_id, self.deps(pace=lambda _n: hot))
        for _ in range(10):  # window_cap（滾動窗內塞滿 2 次；先撥時鐘再記，名額才落在當窗）
            self.advance(item_id)
            for _i in range(2):
                throttle.record_run(self.clock(), "OI-other")
            self.fire(item_id, self.deps(pace=lambda _n: hot))
        throttle_lock = throttle.oi_dir() / "driver.lock"
        for _ in range(10):  # busy
            body = {"pid": 999, "proc_start": "T0", "id": "OI-X", "budget_minutes": 99999,
                    "started_at": self.clock().isoformat()}
            throttle_lock.write_text(json.dumps(body), encoding="utf-8")
            self.fire(item_id)
        throttle_lock.unlink()
        got = self.item(item_id)
        self.assertEqual((got["state"], got["deferrals"], got["attempts"]), ("driven", 0, 0))
        reasons = [e["reason"] for e in self.evs(item_id, "attempt")]
        tally = tuple(reasons.count(r) for r in ("quota", "window_cap", "busy"))
        self.assertEqual(tally, (10, 10, 10))
        interactive = self.deps(interactive=lambda _r, _n: True)
        last = self.params["max_deferrals"] - 1
        for i in range(last):
            self.assertNotEqual(self.item(item_id)["state"], "escalated", f"第 {i} 次不該已升級")
            self.fire(item_id, interactive)
        self.fire(item_id, self.deps(pace=lambda _n: hot))  # deferrals 已是上限−1：quota 不得升級
        got = self.item(item_id)
        self.assertEqual((got["state"], got["deferrals"]), ("driven", last))
        self.fire(item_id, interactive)
        self.assertEqual(self.item(item_id)["state"], "escalated")


class FifoSimulationTest(DriverCase):
    def test_thirty_rows_over_fifteen_windows_run_two_per_window_oldest_first(self):  # AT-WP-67
        ids = [self.open_item(minutes=i / 60) for i in range(30)]
        for item_id in ids:
            self.drive_item(item_id)
        span = self.params["cap_window_minutes"]
        run_log: list[tuple[int, str]] = []

        def pace_now(now: datetime) -> throttle.Pace:
            into = (now - T0).total_seconds() / 60 % span
            return throttle.Pace(True, 2, OK_PACE.bands, span - into)
        for _ in range(400):
            folded = fold(self.events(), self.params, self.clock())
            live = [i for i in folded.items.values() if i["state"] == "driven"]
            if not live:
                break
            nxt = min(live, key=lambda i: oi_ledger.parse_ts(i["drive"]["at"]))
            self.clock.t = max(self.clock(), oi_ledger.parse_ts(nxt["drive"]["at"]))
            window_no = int((self.clock() - T0).total_seconds() // 60 // span)
            deps = self.deps(pace=pace_now)
            task = nxt["drive"]["task"]
            line = driver_run.run_driver(self.root, self.params, nxt["id"], task, deps)
            if "OPENITEMS_DRIVER=pass" in line:
                run_log.append((window_no, nxt["id"]))
        final = fold(self.events(), self.params, self.clock()).items
        self.assertTrue(all(i["state"] == "closed" for i in final.values()))
        self.assertEqual(sum(1 for i in final.values() if i["state"] == "escalated"), 0)
        self.assertTrue(all(i["deferrals"] == 0 for i in final.values()))
        by_window: dict[int, list[str]] = {}
        for window_no, item_id in run_log:
            by_window.setdefault(window_no, []).append(item_id)
        self.assertEqual(sorted(by_window), list(range(15)))
        self.assertTrue(all(len(v) == 2 for v in by_window.values()))
        self.assertEqual([i for w in sorted(by_window) for i in by_window[w]], ids)  # 排隊鍵順序


class StalePassTest(DriverCase):
    def registry(self, sources=("tools/x.py",)):
        mod = types.ModuleType("oi_fake_family")
        mod.SOURCES = sources
        sys.modules["oi_fake_family"] = mod
        self.addCleanup(sys.modules.pop, "oi_fake_family", None)

        def fn(_ctx):
            return None
        fn.__module__ = "oi_fake_family"
        return {"RV-F1": types.SimpleNamespace(family="fam", fn=fn, long=False)}

    def write_pass(self, when: datetime) -> None:
        path = self.root / evidence.RV_LEDGER_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        path.write_text(f"| {stamp} | family=fam | pass | 1 | - | - | 5 |\n", encoding="utf-8")

    def scan(self, src_time: datetime) -> list[str]:
        return drive.stale_pass(self.root, self.params, self.clock(), registry=self.registry(),
                                git_time=lambda _r, _s: src_time)

    def test_newer_source_than_last_pass_opens_one_row_and_never_reopens(self):  # AT-WP-19／52(d)
        self.write_pass(T0 - timedelta(days=1))
        self.assertEqual(len(self.scan(T0 - timedelta(hours=1))), 1)
        for _ in range(3):
            self.assertEqual(self.scan(T0 - timedelta(hours=1)), [])
        self.assertEqual(len([e for e in self.events() if e["ev"] == "open"]), 1)

    def test_source_older_than_last_pass_opens_nothing(self):
        self.write_pass(T0)
        self.assertEqual(self.scan(T0 - timedelta(hours=1)), [])

    def test_escalated_family_reopens_only_after_a_newer_commit(self):  # AT-WP-52(a)(b)
        self.write_pass(T0 - timedelta(days=2))
        (first,) = self.scan(T0 - timedelta(days=1))
        self.drive_item(first)
        # 升級戳必須晚於該列既有事件（drive 事件的 ts 取牆鐘）：寫死 T0 會在牆鐘超過 T0 後讓 fold 把
        # 升級排到 drive 之前，列又回到 driven（時間炸彈；2026-11-21 牆鐘過 T0 後首次轉紅）
        esc_at = max(oi_ledger.parse_ts(e["ts"]) for e in self.events(first)) + timedelta(seconds=1)
        stamp = esc_at.isoformat(timespec="seconds")
        oi_ledger.append(self.root, lambda _e: [{"ev": "escalate", "id": first, "by": "human",
                                                "reason": "x", "ts": stamp}])
        self.assertEqual(self.scan(esc_at - timedelta(hours=1)), [])
        self.assertEqual(len(self.scan(esc_at + timedelta(hours=1))), 1)

    def test_human_listed_family_stays_quiet_without_new_commit(self):  # AT-WP-52(c)
        self.write_pass(T0 - timedelta(days=2))
        (first,) = self.scan(T0 - timedelta(days=1))
        oi_ledger.append(self.root, lambda _e: [{"ev": "convert", "id": first, "by": "human",
                                                "kind": "human", "why": "只能掌舵者目視畫面",
                                                "ts": T0.isoformat(timespec="seconds")}])
        self.assertEqual(self.scan(T0 - timedelta(hours=1)), [])

    def test_family_without_declared_sources_is_never_opened(self):
        self.write_pass(T0 - timedelta(days=1))
        got = drive.stale_pass(self.root, self.params, T0, registry=self.registry(sources=()),
                               git_time=lambda _r, _s: T0)
        self.assertEqual(got, [])


class CaseInfoTest(unittest.TestCase):
    def test_declared_wall_wins_and_long_default_is_180(self):
        mod = types.ModuleType("oi_fake_case")
        mod.KIND, mod.MIN_WALL_SECONDS, mod.SOURCES = "soak", 21600, ("a.py",)
        sys.modules["oi_fake_case"] = mod
        self.addCleanup(sys.modules.pop, "oi_fake_case", None)

        def fn(_c):
            return None
        fn.__module__ = "oi_fake_case"
        reg = {"RV-S": types.SimpleNamespace(family="f", fn=fn, long=True),
               "RV-L": types.SimpleNamespace(family="f", fn=lambda _c: None, long=True)}
        info = drive.case_info("RV-S", reg)
        self.assertEqual((info.kind, info.wall_minutes, info.sources), ("soak", 360, ("a.py",)))
        self.assertEqual(drive.case_info("RV-L", reg).wall_minutes, 180)
        self.assertEqual(drive.case_info("RV-nope", reg), drive.CaseInfo())


if __name__ == "__main__":
    unittest.main()
