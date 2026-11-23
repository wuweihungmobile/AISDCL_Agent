"""tools/lib/openitems/{fold,liveness,driver_run,drive}.py 的「驅動器死亡偵測」（W5-FIX1；
TCS-WorkProgress REQ-WP-03／08 追加註記 r4、AT-WP-50 (e)(f)、E2E-WP-46 修訂）。

WHY：2026-11-22 14:46 整機重開機殺掉正在跑的 OIR 驅動器，帳本只留 `start`；舊判準只認
`start.ts＋budget_minutes`（195 分），死掉的驅動器佔住 driven 憑證約 4 小時，完成閘看不到。
這裡測會讓它說謊的方向：①行程已死或 pid 被復用卻仍算 driven；②量不到開機時間／身分卻把活驅動器判死
（反向，fail-safe）；③驅動器行內任何例外離開卻不留 attempt；④逾時只砍直接子行程、孫行程殘留。
縫：fold 的 `run_alive` 注入（單元）、真子行程＋真 `taskkill /T /F`＋真 CLI `list`（E2E）。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_openitems_drive import (  # noqa: E402
    OK_PACE,
    RV_CHECK,
    SRC,
    T0,
    Clock,
    FakeBackend,
    FakeRun,
    make_root,
)

from lib import sandbox_scope  # noqa: E402
from lib.openitems import drive, driver_run, gate, liveness, throttle  # noqa: E402
from lib.openitems import ledger as oi_ledger  # noqa: E402
from lib.openitems import params as oi_params  # noqa: E402
from lib.openitems.fold import fold  # noqa: E402
from lib.realverify.sandbox import kill_tree  # noqa: E402

ITEM = "OI-20261119-001"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _ev(seq: int, name: str, minutes: float, **kw) -> dict:
    out = {"seq": seq, "ev": name, "id": ITEM, "by": "t",
           "ts": (T0 + timedelta(minutes=minutes)).isoformat(timespec="seconds")}
    out.update(kw)
    return out


def _events(start_extra: dict | None = None) -> list[dict]:
    return [
        _ev(1, "open", 0, title="t", source=SRC, scope="s", kind="auto", check=RV_CHECK),
        _ev(2, "drive", 1, task="T", credential="c", at=(T0 + timedelta(minutes=10)).isoformat()),
        _ev(3, "start", 10, drive_seq=2, pid=4242, proc_start="2026-11-20T04:00:00.1234567Z",
            budget_minutes=195, **(start_extra or {})),
    ]


class RunDiedFoldTest(unittest.TestCase):
    """tools/lib/openitems/fold.py：`run_alive` 注入後的 `run_died` 判準與 fail-safe。"""

    P: dict = {}

    @classmethod
    def setUpClass(cls) -> None:
        cls.P = json.loads((_REPO / oi_params.PARAMS_REL).read_text(encoding="utf-8"))

    def state(self, events, now_min, run_alive=None) -> dict:
        got = fold(events, self.P, T0 + timedelta(minutes=now_min), None, run_alive)
        return got.items[ITEM]

    def test_dead_runner_is_undriven_immediately_not_after_the_budget(self):
        item = self.state(_events(), 11, lambda _s: False)  # start 後 1 分，預算 195 分遠未到
        self.assertTrue(item["undriven"])
        self.assertEqual(item["undriven_reason"], "run_died")

    def test_without_the_probe_the_old_budget_bound_still_holds(self):
        # 反向變體：沒有注入（或量不到 None）＝ 舊行為，預算內仍 driven——證明判準真的靠探針
        for probe in (None, lambda _s: None):
            with self.subTest(probe=probe):
                self.assertFalse(self.state(_events(), 11, probe)["undriven"])
        self.assertEqual(self.state(_events(), 10 + 196, None)["undriven_reason"],
                         "run_budget_exceeded")

    def test_live_runner_stays_driven(self):
        self.assertFalse(self.state(_events(), 11, lambda _s: True)["undriven"])

    def test_probe_is_not_consulted_once_an_attempt_exists(self):
        # attempt 之後行程本來就會結束：判準只看 followup_grace，不得因「行程已不在」判死
        attempt = _ev(4, "attempt", 20, n=1, result="fail", drive_seq=2)
        item = self.state([*_events(), attempt], 21, lambda _s: False)
        self.assertFalse(item["undriven"])

    def test_a_dead_run_is_redrivable_and_costs_no_attempt(self):
        # REQ-WP-27 語意：沒寫 attempt ⇒ attempts／deferrals 不變；重掛（drive）接得上
        root = make_root()
        self.addCleanup(shutil.rmtree, root, True)
        params = oi_params.load(root)
        clock = Clock()
        backend = FakeBackend()
        events = {"ev": "open", "id": "OI-20261120-001", "by": "human", "title": "t",
                  "source": SRC, "scope": "r217", "kind": "auto", "check": RV_CHECK,
                  "ts": (T0 - timedelta(minutes=60)).isoformat(timespec="seconds")}
        oi_ledger.append(root, lambda _e: [events])
        drive.drive_item(root, params, "OI-20261120-001", backend=backend, now=clock(), by="human")
        rows, _bad = oi_ledger.read_events(oi_params.ledger_path(root))
        seq = fold(rows, params, clock()).items["OI-20261120-001"]["drive"]["seq"]
        oi_ledger.append(root, lambda _e: [{
            "ev": "start", "id": "OI-20261120-001", "by": "driver:t", "ts": clock().isoformat(
                timespec="seconds"), "drive_seq": seq, "pid": 1, "proc_start": "",
            "budget_minutes": 195}])
        rows, _bad = oi_ledger.read_events(oi_params.ledger_path(root))
        died = fold(rows, params, clock.t + timedelta(minutes=1), None, lambda _s: False)
        self.assertEqual(died.items["OI-20261120-001"]["undriven_reason"], "run_died")
        again = drive.drive_item(root, params, "OI-20261120-001", backend=backend,
                                 now=clock.t + timedelta(minutes=1), by="human")
        rows, _bad = oi_ledger.read_events(oi_params.ledger_path(root))
        after = fold(rows, params, clock.t + timedelta(minutes=1), None, lambda _s: False)
        item = after.items["OI-20261120-001"]
        self.assertEqual((item["attempts"], item["deferrals"], item["undriven"]), (0, 0, False))
        self.assertEqual(item["drive"]["task"], again["task"])
        self.assertIsNone(item["start"])


class StartAliveTest(unittest.TestCase):
    """tools/lib/openitems/liveness.py：start 事件→執行者是否活著（三條判死、量不到不判死）。"""

    BOOT = T0 - timedelta(hours=3)

    def probe(self, alive: bool, created: str | None):
        return lambda _pid: (alive, created)

    def start(self, **kw) -> dict:
        base = {"ts": T0.isoformat(), "pid": 4242, "proc_start": "2026-11-20T04:00:00.1234567Z"}
        base.update(kw)
        return base

    def test_pid_gone_is_dead(self):
        self.assertIs(liveness.start_alive(self.start(), self.BOOT, self.probe(False, None)),
                      False)

    def test_reused_pid_with_a_different_creation_time_is_dead(self):
        other = "2026-11-20T09:30:00+08:00"  # 與 proc_start（04:00Z＝12:00+08:00）差 2.5 小時
        self.assertIs(liveness.start_alive(self.start(), self.BOOT, self.probe(True, other)),
                      False)

    def test_same_process_is_alive_across_the_two_time_formats(self):
        # 真格式：proc_start＝.NET `ToString('o')`（7 位小數、Z）；探針＝秒精度＋本地 offset
        same = "2026-11-20T12:00:00+08:00"
        self.assertIs(liveness.start_alive(self.start(), self.BOOT, self.probe(True, same)), True)

    def test_start_older_than_this_boot_is_dead_even_if_the_pid_is_taken_again(self):
        # 重開機後新行程剛好撿到同一個 pid、建立時間也量不到：只剩「start 早於開機」能判死
        late_boot = T0 + timedelta(minutes=30)
        self.assertIs(liveness.start_alive(self.start(), late_boot, self.probe(True, None)),
                      False)

    def test_unmeasurable_never_condemns_a_live_driver(self):
        # fail-safe：開機時間量不到、建立時間量不到、proc_start 空字串、pid 欄位缺——都不得判死
        for start, created in ((self.start(), None), (self.start(proc_start=""), "x"),
                               (self.start(proc_start="garbage"), "2026-11-20T12:00:00+08:00")):
            with self.subTest(start=start):
                self.assertIs(liveness.start_alive(start, None, self.probe(True, created)), True)
        self.assertIsNone(liveness.start_alive(self.start(pid=None), None, self.probe(True, None)))
        self.assertIsNone(liveness.start_alive(self.start(pid=-3), None, self.probe(True, None)))

    def test_real_process_identity_round_trips(self):
        # 真行程：自己的 pid＋throttle.proc_identity（寫入端真值）⇒ 活；不存在的 pid ⇒ 死
        now = datetime.now().astimezone()
        mine = {"ts": now.isoformat(), "pid": os.getpid(),
                "proc_start": throttle.proc_identity(os.getpid()) or ""}
        self.assertIs(liveness.start_alive(mine, liveness.boot_time(now)), True)
        self.assertIs(liveness.start_alive({**mine, "pid": 2**30}, None), False)

    def test_boot_time_is_measurable_and_in_the_past_here(self):
        now = datetime.now().astimezone()
        boot = liveness.boot_time(now)
        if boot is None:
            self.skipTest("這個平台量不到開機時間（fail-safe 路徑，已由上面的案例覆蓋）")
        self.assertLess(boot, now)


class _Raising(FakeBackend):
    def list_tasks(self, prefix):
        raise RuntimeError("scheduler enumeration blew up")


class DriverSealsAnAttemptTest(unittest.TestCase):
    """tools/lib/openitems/driver_run.py：start 之後任何例外離開，帳本末列必為 attempt。"""

    def setUp(self) -> None:
        self.root = make_root()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.params = oi_params.load(self.root)
        self.clock = Clock()
        self.trace = self.root / "_trace"
        old = os.environ.get("AUTOSDD_TRACE_DIR")
        os.environ["AUTOSDD_TRACE_DIR"] = str(self.trace)
        self.addCleanup(lambda: os.environ.__setitem__("AUTOSDD_TRACE_DIR", old) if old is not None
                        else os.environ.pop("AUTOSDD_TRACE_DIR", None))

    def deps(self, backend=None, **kw) -> driver_run.Deps:
        base = {"backend": backend or FakeBackend(), "now": self.clock,
                "pace": lambda _n: OK_PACE, "interactive": lambda _r, _n: False,
                "identity": lambda _p: "T0", "run": FakeRun(self.root, self.clock),
                "coverage": lambda _r: "ok", "pid": 4242,
                "case_info": lambda _c: drive.CaseInfo(wall_minutes=60)}
        base.update(kw)
        return driver_run.Deps(**base)

    def armed(self, backend) -> tuple[str, dict]:
        def make(events):
            return [{"ev": "open", "id": oi_ledger.next_id(events, T0), "by": "human",
                     "title": "t", "source": SRC, "scope": "r217", "kind": "auto",
                     "check": RV_CHECK,
                     "ts": (T0 - timedelta(minutes=60)).isoformat(timespec="seconds")}]
        item_id = oi_ledger.append(self.root, make)[0]["id"]
        d = drive.drive_item(self.root, self.params, item_id, backend=backend, now=self.clock(),
                             by="human")
        self.clock.t = oi_ledger.parse_ts(d["at"]) + timedelta(minutes=1)
        return item_id, d

    def rows(self, item_id: str) -> list[dict]:
        evs = oi_ledger.read_events(oi_params.ledger_path(self.root))[0]
        return [e for e in evs if e["id"] == item_id]

    def assertSealed(self, item_id: str, result: str, reason: str) -> dict:
        names = [e["ev"] for e in self.rows(item_id)]
        self.assertEqual(names[-1] if result != "deferred" else names[-2], "attempt", names)
        last = [e for e in self.rows(item_id) if e["ev"] == "attempt"][-1]
        self.assertEqual((last["result"], last["reason"]), (result, reason))
        self.assertFalse((throttle.oi_dir() / "driver.lock").exists(), "鎖沒有釋放")
        return last

    def test_every_pointed_out_throw_site_leaves_an_attempt(self):
        # INV1 點名的拋點：schedcache.refresh、throttle.acquire、deps.pace、record_run
        calls = {"n": 0}

        def second_identity_call_blows(_pid):
            calls["n"] += 1
            if calls["n"] >= 2:
                raise RuntimeError("identity blew up")
            return "T0"

        def pace_blows(_n):
            raise RuntimeError("pace blew up")

        def block_record_run() -> None:
            (throttle.oi_dir() / "window_runs.jsonl").mkdir(parents=True, exist_ok=True)

        sites = {
            "refresh": (_Raising(), {}, lambda: None, "RuntimeError"),
            "acquire": (None, {"identity": second_identity_call_blows}, lambda: None,
                        "RuntimeError"),
            "pace": (None, {"pace": pace_blows}, lambda: None, "RuntimeError"),
            # 以目錄佔住檔名：以附加模式開啟，Windows 丟 PermissionError、POSIX 丟 IsADirectoryError
            # （同為 OSError 子類；封存記錄依實際例外類名，故期望值依平台）
            "record_run": (None, {}, block_record_run,
                           "PermissionError" if sys.platform == "win32" else "IsADirectoryError"),
        }
        for name, (backend, kw, prep, cls) in sites.items():
            with self.subTest(site=name):
                calls["n"] = 0
                shutil.rmtree(self.trace, ignore_errors=True)
                backend = backend or FakeBackend()
                item_id, d = self.armed(FakeBackend())
                prep()
                with self.assertRaises(RuntimeError if cls == "RuntimeError" else OSError):
                    driver_run.run_driver(self.root, self.params, item_id, d["task"],
                                          self.deps(backend, **kw))
                last = self.assertSealed(item_id, "fail", f"error:{cls}")
                self.assertIn(cls, last["evidence"])

    def test_interrupt_defers_without_spending_attempts_and_redrives(self):
        for exc in (KeyboardInterrupt, SystemExit):
            with self.subTest(exc=exc.__name__):
                shutil.rmtree(self.trace, ignore_errors=True)
                backend = FakeBackend()
                item_id, d = self.armed(backend)

                def boom(*_a, _exc=exc):
                    raise _exc()

                with self.assertRaises(exc):
                    driver_run.run_driver(self.root, self.params, item_id, d["task"],
                                          self.deps(backend, run=boom))
                last = [e for e in self.rows(item_id) if e["ev"] == "attempt"][-1]
                self.assertEqual((last["result"], last["reason"]), ("deferred", "interrupted"))
                drives = [e for e in self.rows(item_id) if e["ev"] == "drive"]
                self.assertEqual(len(drives), 2, "中斷後必須重掛新的 drive")
                now = self.clock.t
                item = fold(self.rows_all(), self.params, now).items[item_id]
                self.assertEqual((item["attempts"], item["deferrals"]), (0, 0))
                self.assertFalse((throttle.oi_dir() / "driver.lock").exists())

    def rows_all(self) -> list[dict]:
        return oi_ledger.read_events(oi_params.ledger_path(self.root))[0]

    def test_exception_after_the_normal_attempt_does_not_write_a_second_one(self):
        backend = FakeBackend()
        item_id, d = self.armed(backend)

        def coverage_blows(_root):
            raise RuntimeError("coverage blew up")

        with self.assertRaises(RuntimeError):
            driver_run.run_driver(self.root, self.params, item_id, d["task"],
                                  self.deps(backend, coverage=coverage_blows))
        attempts = [e for e in self.rows(item_id) if e["ev"] == "attempt"]
        self.assertEqual([a["result"] for a in attempts], ["pass"])

    def test_an_error_on_the_last_allowed_attempt_escalates(self):
        self.root2 = make_root(max_attempts=1)
        self.addCleanup(shutil.rmtree, self.root2, True)
        params = oi_params.load(self.root2)
        backend = FakeBackend()
        item_id = oi_ledger.append(self.root2, lambda ev: [{
            "ev": "open", "id": oi_ledger.next_id(ev, T0), "by": "human", "title": "t",
            "source": SRC, "scope": "r217", "kind": "auto", "check": RV_CHECK,
            "ts": (T0 - timedelta(minutes=60)).isoformat(timespec="seconds")}])[0]["id"]
        d = drive.drive_item(self.root2, params, item_id, backend=backend, now=self.clock(),
                             by="human")
        self.clock.t = oi_ledger.parse_ts(d["at"]) + timedelta(minutes=1)
        with self.assertRaises(RuntimeError):
            driver_run.run_driver(self.root2, params, item_id, d["task"],
                                  self.deps(_Raising()))
        rows = [e for e in oi_ledger.read_events(oi_params.ledger_path(self.root2))[0]
                if e["id"] == item_id]
        self.assertEqual([e["ev"] for e in rows][-2:], ["attempt", "escalate"])


class ConsoleRunKillsTheWholeTreeTest(unittest.TestCase):
    """tools/lib/openitems/drive.py::console_run：逾時砍整棵樹，孫行程不殘留。"""

    def test_timeout_reaps_the_grandchild_too(self):
        import tempfile  # noqa: PLC0415

        tmp = Path(tempfile.mkdtemp(prefix="oi_cr_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        pidfile = tmp / "grandchild.pid"
        code = textwrap.dedent(f"""
            import subprocess, sys, time
            kid = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
            open(r"{pidfile}", "w").write(str(kid.pid))
            time.sleep(300)
        """)
        rc, out = drive.console_run(["python", "-c", code], 4, dict(os.environ), tmp)
        self.assertEqual((rc, out), (124, "timeout"))
        grand = int(pidfile.read_text(encoding="utf-8"))
        deadline = time.monotonic() + 8
        alive = True
        while time.monotonic() < deadline:
            alive, _made = sandbox_scope.proc_probe(grand)
            if not alive:
                break
            time.sleep(0.2)
        self.assertFalse(alive, "逾時後孫行程仍活著（只砍了直接子行程）")

    def test_normal_run_still_returns_rc_and_stdout(self):
        rc, out = drive.console_run(["python", "-c", "print('hi'); raise SystemExit(3)"], 60,
                                    dict(os.environ), Path.cwd())
        self.assertEqual(rc, 3)
        self.assertIn("hi", out)


_LAUNCHER = """
import sys
from datetime import datetime
from pathlib import Path
repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / "tools")); sys.path.insert(0, str(repo / "tools" / "lib"))
from lib.openitems import drive, driver_run, throttle
from lib.openitems import params as oi_params
root = Path(sys.argv[2]); item_id = sys.argv[3]; task = sys.argv[4]
free = {{k: "free" for k in ("session", "five_hour", "weekly_all", "seven_day")}}
deps = driver_run.Deps(backend=None, pace=lambda _n: throttle.Pace(True, 2, free, 120.0),
                       interactive=lambda _r, _n: False, coverage=lambda _r: "ok",
                       case_info=lambda _c: drive.CaseInfo(wall_minutes=60))
print(driver_run.run_driver(root, oi_params.load(root), item_id, task, deps), flush=True)
"""


class RealRunnerDeathE2ETest(unittest.TestCase):
    """E2E-WP-46 修訂：真驅動器子行程被 `taskkill /T /F`（等同關機）⇒ 帳本停在 start，
    真 CLI `list`／完成閘立即判 `run_died`，不等預算。載具＝真子行程＋真 kill＋真 CLI；
    驅動器用注入 Deps 的啟動器（不碰真排程器、不碰互動讓路與真額度——那兩個會讓測試依賴本機狀態）。
    """

    def test_killed_driver_is_undriven_run_died_right_away(self):
        import tempfile  # noqa: PLC0415

        root = Path(tempfile.mkdtemp(prefix="oi_died_"))
        self.addCleanup(shutil.rmtree, root, True)
        dest = root / oi_params.PARAMS_REL
        dest.parent.mkdir(parents=True)
        shutil.copyfile(_REPO / oi_params.PARAMS_REL, dest)
        params = oi_params.load(root)
        now = datetime.now().astimezone()
        check = {"argv": [sys.executable, "-c", "import time; time.sleep(300)"], "pass": "rc0"}
        item_id = oi_ledger.append(root, lambda ev: [{
            "ev": "open", "id": oi_ledger.next_id(ev, now), "by": "human", "title": "t",
            "source": SRC, "scope": "r217", "kind": "auto", "check": check,
            "ts": (now - timedelta(minutes=60)).isoformat(timespec="seconds")}])[0]["id"]
        task = "AutoSDD_RV_sbx_oi_died_task"
        oi_ledger.append(root, lambda _e: [{
            "ev": "drive", "id": item_id, "by": "human", "task": task, "credential": "c",
            "ts": (now - timedelta(minutes=3)).isoformat(timespec="seconds"),
            "at": (now - timedelta(minutes=1)).isoformat(timespec="seconds")}])
        launcher = root / "launch.py"
        launcher.write_text(_LAUNCHER.format(), encoding="utf-8", newline="\n")
        env = {**os.environ, "AUTOSDD_TRACE_DIR": str(root / "_trace"), "PYTHONUTF8": "1"}
        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, str(launcher), str(_REPO), str(root), item_id, task], env=env,
            cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=_NO_WINDOW, start_new_session=os.name != "nt")
        self.addCleanup(lambda: (kill_tree(proc), proc.communicate()))
        path = oi_params.ledger_path(root)
        deadline = time.monotonic() + 60
        started = None
        while time.monotonic() < deadline and started is None:
            started = next((e for e in oi_ledger.read_events(path)[0] if e["ev"] == "start"), None)
            time.sleep(0.2)
        self.assertIsNotNone(started, "驅動器沒有在 60 秒內寫出 start")
        time.sleep(1.5)  # 讓它真的進到睡眠的案例子行程
        kill_tree(proc)
        proc.wait(timeout=30)
        rows = oi_ledger.read_events(path)[0]
        self.assertEqual(rows[-1]["ev"], "start", "缺陷重現：被殺後帳本停在 start、沒有 attempt")
        later = datetime.now().astimezone()
        old = fold(rows, params, later).items[item_id]
        self.assertFalse(old["undriven"], "對照組：沒有存活探針時仍在預算界內（舊行為）")
        cli = subprocess.run(  # noqa: S603
            [sys.executable, str(_REPO / "tools" / "openitems.py"), "--root", str(root), "list"],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=120,
            creationflags=_NO_WINDOW, check=False)
        self.assertIn("undriven(run_died)", cli.stdout, cli.stdout + cli.stderr)
        self.assertIn("undriven=1", cli.stdout)
        state = gate.load_state(root, later)
        self.assertEqual([i["undriven_reason"] for i in state.undriven], ["run_died"])


if __name__ == "__main__":
    unittest.main()
