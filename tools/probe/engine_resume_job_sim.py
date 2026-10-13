#!/usr/bin/env python3
"""ARCH-01 引擎續跑工作（tools/lib/engine_resume_job.py）的模擬世界自證：假 launchd／schtasks。"""
# WHY 放 tools/probe 而不是 tools/tests：護欄層測試行數棘輪（R213 起淨額必須 <= 0）已無足量純史料可
# 搬（全庫僅約 400 行候選、且多為判準 WHY），而本檔是「模擬世界自證」——與 pacing_simulator／
# two_project_fanout_probe 同型（用生產碼、假世界），由 `SimulationProbeSelftestTest` 以
# `--selftest` 逐次閘門化（根層全套會跑它，rc!=0 即紅）。真機掛／拆未驗證。
# 鎖：一次性（job 本體跑完自拆）、取證（回讀不符不發憑證）、機密不落 plist、取代舊工作但不殺自己。
#
# 用法：python tools/probe/engine_resume_job_sim.py --selftest
from __future__ import annotations

import argparse
import io
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

import endurance_env  # noqa: E402
import engine_resume_job as erj  # noqa: E402
import relay_machine  # noqa: E402
import schedule_backend as sb  # noqa: E402
import sentinel_lifecycle  # noqa: E402

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）
import session_resume_planner as planner  # noqa: E402

_FENCES: list[dict] = []
_JOB = "AutoSDD_EngineResume_x_1"


def _print_output(argv: list[str], path: str, calendar: dict) -> str:
    """合成 `launchctl print`（欄位與真機同形，同 test_mac_endurance_r83；只有 calendar）。"""
    lines = ["gui/501/L = {", f"\tpath = {path}", "\tstate = not running", "\targuments = {"]
    lines += [f"\t\t{a}" for a in argv] + ["\t}", "\tevent triggers = {", "\t\tj => {",
                                          "\t\t\tstream = com.apple.launchd.calendarinterval",
                                          "\t\t\tdescriptor = {"]
    lines += [f'\t\t\t\t"{k}" => {v}' for k, v in calendar.items()]
    return "\n".join(lines + ["\t\t\t}", "\t\t}", "\t}", "}"]) + "\n"


def setUpModule() -> None:  # 單模組直跑也不得碰真實 TEMP／痕跡目錄（DEF-200-446）
    _FENCES.append(sentinel_lifecycle.fence_enter())


def tearDownModule() -> None:
    sentinel_lifecycle.fence_exit(_FENCES.pop())


class _Stub:
    """後端替身：記 disarm、回預設 list_jobs 序列（用到最後一個值後一律重複它）。"""

    def __init__(self, name: str = "launchd", lists=((),)) -> None:
        self.name, self.disarmed, self._lists = name, [], list(lists)

    def list_jobs(self, prefix: str):
        return self._lists.pop(0) if len(self._lists) > 1 else self._lists[0]

    def disarm(self, task_name: str) -> int:
        self.disarmed.append(task_name)
        return 0


class _Case(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="erj_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.pb, self.cwd = self.tmp / "play book.yaml", self.tmp / "cwd"
        self.pb.write_text("version: '1.0'\n", encoding="utf-8")
        self.cwd.mkdir()
        self.seen: list[list[str]] = []
        for target, name, value in ((sb, "LAUNCH_AGENTS_DIR", self.tmp / "LA"),
                                    (erj, "_engine_importable", lambda: True)):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.at = datetime.now().astimezone() + timedelta(hours=3)

    def echo_launchd(self, print_rc: int = 0, drift: bool = False):
        """忠實 launchd 替身：`print` 回讀的是 plist 檔裡真正寫的內容（可注入漂移）。"""
        def _run(argv, timeout: int = 60):
            self.seen.append(list(argv))
            if argv[1] != "print":
                return 0, ""
            plist = sb.LAUNCH_AGENTS_DIR / f"{argv[2].rsplit('/', 1)[-1]}.plist"
            if print_rc or not plist.is_file():
                return print_rc or sb.LAUNCHCTL_ENOENT_RC, ""
            body = plistlib.loads(plist.read_bytes())
            cal = dict(body["StartCalendarInterval"])
            cal["Minute"] = (cal["Minute"] + 1) % 60 if drift else cal["Minute"]
            return 0, _print_output(body["ProgramArguments"], str(plist), cal)
        return _run

    def arm(self, backend=None, **kw):
        with mock.patch.object(sb, "select", return_value=backend or sb.LaunchdBackend()), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return erj.arm(str(self.pb), self.at, cwd=str(self.cwd), **kw)


class TestFireTimeAndNaming(_Case):
    def test_fire_is_at_plus_the_planner_skew_rounded_up_never_in_the_past(self) -> None:
        now, skew = datetime.now().astimezone().replace(second=7), planner.RESET_SKEW_SECONDS
        got = erj.fire_time(now + timedelta(hours=3), skew, now)
        self.assertEqual(got.second, 0)
        self.assertTrue(timedelta(hours=3, seconds=skew) <= got - now
                        < timedelta(hours=3, seconds=skew + 60))
        past = erj.fire_time(now - timedelta(days=2), skew, now)
        self.assertGreaterEqual((past - now).total_seconds(), erj.MIN_LEAD_SECONDS)

    def test_the_job_family_is_per_playbook_and_visible_to_the_leak_fence(self) -> None:
        a, b = erj.job_prefix(str(self.pb)), erj.job_prefix(str(self.pb) + "2")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith(erj.JOB_PREFIX) and not sb._unsafe_name(a))
        self.assertTrue(erj.JOB_PREFIX.startswith(sentinel_lifecycle.LEAK_FENCE_JOB_PREFIX))
        self.assertIn(erj.JOB_PREFIX, relay_machine._JOB_PREFIXES)

    def test_the_env_literal_equals_the_engines_constant(self) -> None:
        engine = _REPO_ROOT / "AutoClaude/autoclaude/core/services/external_resume.py"
        found = re.search(r'EXTERNAL_RESUME_CMD_ENV = "([A-Z_]+)"', engine.read_text("utf-8"))
        self.assertEqual(found and found.group(1), erj.EXTERNAL_RESUME_CMD_ENV)


class TestLaunchdArming(_Case):
    def test_a_matching_readback_yields_a_credential_and_a_one_shot_plist(self) -> None:
        path, config = os.pathsep.join(["px", "py"]), str(self.tmp / "config.yaml")
        with mock.patch.dict(os.environ, {"MINIMAX_API_KEY": "sk-secret", "PATH": path}), \
                mock.patch.object(sb, "_run", self.echo_launchd()):
            rc, cred = self.arm(config=config)
        self.assertEqual(rc, 0, cred)
        plist = next(sb.LAUNCH_AGENTS_DIR.glob(f"{erj.job_prefix(str(self.pb))}*.plist"))
        body = plistlib.loads(plist.read_bytes())
        self.assertIn(plist.stem, cred)
        self.assertEqual(body["Label"], plist.stem)
        self.assertEqual(sorted(body["StartCalendarInterval"]), ["Day", "Hour", "Minute", "Month"])
        self.assertFalse(body["RunAtLoad"] or {"StartInterval", "KeepAlive"} & set(body))
        self.assertEqual(body["WorkingDirectory"], str(self.cwd))
        args = body["ProgramArguments"]
        self.assertEqual(args[2:9], ["--run", "--job", plist.stem, "--playbook", str(self.pb),
                                     "--cwd", str(self.cwd)])
        self.assertEqual(args[-2:], ["--config", config])
        self.assertEqual(body["EnvironmentVariables"].get("PATH"), path)
        self.assertNotIn("MINIMAX_API_KEY", body["EnvironmentVariables"], "機密不得落進 plist")
        boots = [c for c in self.seen if c[:2] == ["launchctl", "bootstrap"]]
        self.assertEqual([c[3] for c in boots], [str(plist)], "bootstrap 載的必須是剛寫的 plist")
        trace = (endurance_env.trace_dir() / erj.TRACE_NAME).read_text("utf-8").splitlines()
        self.assertEqual(json.loads(trace[-1])["schema"], erj.SCHEMA)
        self.assertEqual(json.loads(trace[-1])["event"], "armed")

    def test_no_readback_or_a_drifted_one_is_not_a_credential_and_leaves_no_plist(self) -> None:
        for label, runner in (("absent", self.echo_launchd(print_rc=113)),
                              ("drift", self.echo_launchd(drift=True))):
            with self.subTest(label), mock.patch.object(sb, "_run", runner):
                self.assertEqual(self.arm(), (1, ""))
                self.assertEqual(list(sb.LAUNCH_AGENTS_DIR.glob("*.plist")), [], "殘留 plist")

    def test_an_unrunnable_request_is_refused_before_any_scheduler_call(self) -> None:
        with mock.patch.object(sb, "_run", self.echo_launchd()):
            with mock.patch.object(erj, "_engine_importable", return_value=False):
                self.assertEqual(self.arm()[0], 1)          # 這個直譯器 import 不到 autoclaude
            self.pb.unlink()
            self.assertEqual(self.arm()[0], 1)              # playbook 不存在
        self.assertEqual(self.seen, [], "拒絕發生在碰排程器之前")


class TestSchtasksArming(_Case):
    def _arm(self, stdout: str, rc: int = 0):
        shot = {}

        def _ps(script: str):
            shot["script"] = script
            return subprocess.CompletedProcess([], rc, stdout, "")
        with mock.patch.object(planner, "run_powershell", _ps):
            return self.arm(backend=sb.SchtasksBackend()), shot.get("script", "")

    def test_the_script_reuses_the_planner_pieces_and_next_run_time_is_the_credential(self) -> None:
        (rc, cred), script = self._arm("NextRunTime : 2099/1/1 09:02:00\n")
        self.assertEqual(rc, 0)
        self.assertIn("2099/1/1 09:02:00", cred)
        for needle in ("Register-ScheduledTask", "-Once -At", planner._SCHTASKS_SETTINGS,
                       "--run", f"-WorkingDirectory '{self.cwd}'", erj.JOB_PREFIX):
            self.assertIn(needle, script)

    def test_without_a_next_run_time_nothing_is_claimed(self) -> None:
        self.assertEqual(self._arm("registered\n")[0], (1, ""))
        self.assertEqual(self._arm("NextRunTime : 2099/1/1\n", rc=1)[0], (1, ""))


class TestSupersedeRemoveAndTheJobBody(_Case):
    def test_arm_supersedes_older_jobs_but_never_the_job_it_is_running_inside(self) -> None:
        pre = erj.job_prefix(str(self.pb))
        stub = _Stub(lists=([f"{pre}old", f"{pre}running", "AutoSDD_Sentinel_x"],))
        with mock.patch.object(erj, "_arm_launchd", return_value=(0, "cred")), \
                mock.patch.dict(os.environ, {erj.JOB_ENV: f"{pre}running"}):
            self.assertEqual(self.arm(backend=stub), (0, "cred"))
        self.assertEqual(stub.disarmed, [f"{pre}old"], "只取代同 playbook 的舊工作")

    def test_remove_confirms_by_reading_back_and_never_claims_unmeasured(self) -> None:
        pre = erj.job_prefix(str(self.pb))
        for lists, want in ((([f"{pre}a", f"{pre}b"], []), 0), (([f"{pre}a"], [f"{pre}a"]), 1),
                            ((None,), 1), (([f"{pre}a"], None), 1)):
            stub = _Stub(lists=lists)
            with self.subTest(lists), mock.patch.object(sb, "select", return_value=stub), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(erj.remove(str(self.pb)), want)

    def _run_job(self, fire: datetime, stub: _Stub, engine) -> int:
        with mock.patch.object(sb, "select", return_value=stub), \
                mock.patch.object(erj.subprocess, "run", engine):
            return erj.run_job(_JOB, str(self.pb), str(self.cwd), None,
                               fire.isoformat(timespec="seconds"))

    def test_the_job_body_runs_the_engine_then_disarms_itself_and_marks_its_children(self) -> None:
        order, stub = [], _Stub()
        stub.disarm = lambda name: order.append(("disarm", name)) or 0
        rc = self._run_job(datetime.now().astimezone() - timedelta(minutes=5), stub,
                           lambda argv, **kw: order.append(("engine", argv, kw)) or
                           subprocess.CompletedProcess(argv, 5))
        self.assertEqual(rc, 5, "引擎的 rc 必須原樣成為 job 的 rc")
        self.assertEqual([step[0] for step in order], ["engine", "disarm"], "必須跑完才自拆")
        argv, kw = order[0][1], order[0][2]
        self.assertEqual(argv[1:], ["-m", "autoclaude", str(self.pb)])
        self.assertEqual((kw["cwd"], kw["env"][erj.JOB_ENV]), (str(self.cwd), _JOB))

    def test_a_stale_fire_never_reruns_the_playbook_but_still_disarms(self) -> None:
        ran, stub = [], _Stub()
        stale = datetime.now().astimezone() - timedelta(seconds=erj.STALE_FIRE_SECONDS + 3600)
        rc = self._run_job(stale, stub, lambda *a, **k: ran.append(a))
        self.assertNotEqual(rc, 0)
        self.assertEqual((ran, stub.disarmed), ([], [_JOB]))


class TestCli(_Case):
    def test_unknown_flags_are_rejected_and_at_is_required(self) -> None:
        with redirect_stderr(io.StringIO()):
            self.assertEqual(erj.main(["--bogus"]), 2)
            with self.assertRaises(SystemExit) as caught:
                erj.main(["--playbook", str(self.pb)])
            self.assertEqual(caught.exception.code, 2)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--selftest", action="store_true", required=True)
    parser.parse_args(argv)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    bad = len(result.failures) + len(result.errors)
    print(f"自證：{result.testsRun - bad}/{result.testsRun}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
