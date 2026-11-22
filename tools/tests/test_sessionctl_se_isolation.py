#!/usr/bin/env python3
"""sessionctl 站點的 L1 副作用隔離驗收（RealVerify SideEffect Isolation，S2；TCS §3
AT-SE-10／11／12／
15／28／31／36／37／43／44／49／50 的 sessionctl 半邊）。

受測模組：`tools/lib/sessionctl/se_gate.py`（共用接點）、`park_cli.py`（`_cmd_fire`／`_cmd_park`／
`spawn_resume`）、`handoff.py`（`spawn`／`announce`）、`oldwin_sched.py`（`schedule_retry`）、
`oldwin_park.py`（`_rearm`）、`park.py`（`STATUSES`＝含 `refused`）、`rv_orphans.py`、
`tools/sessionctl.py`。

WHY（幽靈 session 57d0ccad）：驗證案例的 park 排程在沙盒外到點，開了真視窗跑 `claude -r`。判準是
「目標自帶的身分檔＋租約」，不是環境變數——所以這裡的沙盒全是 tmp 下 `AutoSDD_RV_sbx_*`
目錄＋真身分檔，
痕跡／handback／交接包居所全指向 tmp，從不碰真排程器、真 `~/.autosdd`、真 `~/.claude`。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parents[2]
for _p in (_ROOT / "tools", _ROOT / "tools" / "lib"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import sandbox_scope  # noqa: E402
from test_sessionctl_handoff import FakeRoster, FakeRunner  # noqa: E402

from lib.sessionctl import (  # noqa: E402
    handoff,
    oldwin_park,
    oldwin_sched,
    park,
    park_cli,
    rv_orphans,
    se_gate,
    switch,
)

SID = "57d0ccad-1111-4222-8333-444455556666"
RC10 = sandbox_scope.RC_SIDEEFFECT_REFUSED
_MAIN = "\n\n".join(f"{h}\n內容 {i}" for i, h in enumerate(handoff.SECTIONS))


def _now() -> datetime:
    return datetime.now().astimezone()


def _secs(moment: datetime) -> datetime:
    """身分檔把 allow_until 存到秒；比對時把期望值也截到秒。"""
    return datetime.fromisoformat(moment.isoformat(timespec="seconds"))


class _FakeBackend:
    name = "schtasks"

    def __init__(self) -> None:
        self.jobs: set[str] = set()
        self.disarmed: list[str] = []

    def disarm(self, label: str) -> int:
        self.disarmed.append(label)
        self.jobs.discard(label)
        return 0

    def list_jobs(self, prefix: str):
        return [j for j in self.jobs if j.startswith(prefix)]


class _SeFence(unittest.TestCase):
    """tmp 圍籬：痕跡／handback／交接包居所、沙盒家（真身分檔）與正式 repo 替身。"""

    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="tw-se-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.tdir, self.bdir = self.tmp / "traces", self.tmp / "handback"
        self.hdir = self.tmp / "handoff"
        for folder in (self.tdir, self.bdir, self.hdir):
            folder.mkdir()
        self.home = self.tmp / "AutoSDD_RV_sbx_t1"
        self.prod = self.tmp / "prodrepo"
        for folder in (self.home, self.prod):
            folder.mkdir()
        sandbox_scope.write_identity(self.home, run_id="t1", sid="sbx", owner_pid=os.getpid(),
                                     now=_now())
        self.env = {"AUTOSDD_HANDOFF_DIR": str(self.hdir)}
        patch = mock.patch.dict(os.environ, {
            "AUTOSDD_TRACE_DIR": str(self.tdir), "AUTOSDD_HANDOFF_DIR": str(self.hdir),
            "AUTOSDD_HANDBACK_DIR": str(self.bdir)})
        patch.start()
        self.addCleanup(patch.stop)
        self.backend = _FakeBackend()
        self.label = f"AutoSDD_HandoffSpawn_{SID[:8]}_202611222000"

    def lease(self, minutes: int = 30) -> datetime:
        now = _now()
        return sandbox_scope.grant(self.home, until=now + timedelta(minutes=minutes), now=now)

    def package(self, repo: Path) -> Path:
        path = self.hdir / f"{SID}_20261122T000000Z.md"
        path.write_text(f"# 交接包 <!-- sessionctl-handoff sid={SID} at=x -->\n\n## 機械層\n\n"
                        f"- repo 根：{repo}\n\n{handoff.MAIN_MARK}\n\n{_MAIN}\n", encoding="utf-8")
        return path

    def events(self) -> list[dict]:
        target = self.tdir / "autosdd_session_switch.jsonl"
        return ([json.loads(x) for x in target.read_text(encoding="utf-8").splitlines()]
                if target.exists() else [])

    def names(self) -> list[str]:
        return [e["event"] for e in self.events()]

    def marker(self, pkg: Path, status: str = "armed", label: str | None = None) -> dict:
        fire = _now() + timedelta(minutes=5)
        job = {"label": label or self.label, "role": "primary", "fire_at": fire.isoformat(),
               "credential": "NextRunTime = x"}
        marker = {"schema": park.SCHEMA, "sid": SID, "route": "H", "status": status,
                  "parked_at": _now().isoformat(), "reset_at": fire.isoformat(),
                  "fire_at": fire.isoformat(), "axis": None, "pkg": str(pkg), "why": None,
                  "valid_until": (fire + timedelta(hours=1)).isoformat(), "jobs": [job],
                  "reason": "測試", "outcome": None}
        ok, msg = park.write_marker(marker)
        self.assertTrue(ok, msg)
        return marker


class FireSiteTest(_SeFence):
    """tools/lib/sessionctl/park_cli.py::_cmd_fire：L1 首判的位置、終局語意與 `--claude` 傳遞
    （AT-SE-10、31、38、44、50）。"""

    def setUp(self) -> None:
        super().setUp()
        self.spawn_calls: list[dict] = []
        self.resume_calls: list[dict] = []
        self.spawn_rc = self.resume_rc = 0
        self.transcript = self.tmp / f"{SID}.jsonl"
        stale = (_now() - timedelta(hours=5)).isoformat()
        self.transcript.write_text(json.dumps({"type": "assistant", "timestamp": stale,
                                               "message": {"model": "claude-fable-5"}}) + "\n",
                                   encoding="utf-8")

    def fire(self, repo: Path, pkg: Path, *argv: str):
        def spawn(path, **kw):
            self.spawn_calls.append(kw)
            return self.spawn_rc

        def resume(sid, path, **kw):
            self.resume_calls.append(kw)
            return self.resume_rc
        seams = {"backend": self.backend, "spawn": spawn, "resume": resume,
                 "transcript": lambda _s: self.transcript}
        err = io.StringIO()
        with mock.patch.object(park_cli, "_REPO", repo), contextlib.redirect_stderr(err), \
                contextlib.redirect_stdout(io.StringIO()):
            rc = park_cli.run(["--session-id", SID, "--fire", "--job", self.label, "--pkg",
                               str(pkg), "--fire-at", _now().isoformat(), *argv],
                              env=dict(self.env), seams=seams)
        return rc, err.getvalue()

    def test_at_se_10_38_no_lease_refuses_right_after_job_start_and_is_terminal(self) -> None:
        """park_cli.py::_cmd_fire：沙盒無租約 ⇒ 痕跡只有 park_job_start→sideeffect_refused；
        標記讀取晚於拒絕痕跡；list_handoffs／live_driver／oldwin gate 一次都沒呼叫；標記 refused、
        自拆 1 次、rc 0；沒有讓路／嘗試／失敗鏈痕跡、沒有 handback、沒有任何 spawn。"""
        pkg = self.package(self.home)
        self.marker(pkg)
        order: list[str] = []
        real_trace, real_read = switch.trace, park.read_marker

        def trace(event, **kw):
            order.append(event)
            return real_trace(event, **kw)

        def read(sid, **kw):
            order.append("read_marker")
            return real_read(sid, **kw)
        boom = AssertionError("L1 拒絕後不得再走到這裡")
        with mock.patch.object(switch, "trace", trace), \
                mock.patch.object(park, "read_marker", read), \
                mock.patch.object(handoff, "list_handoffs", side_effect=boom), \
                mock.patch.object(oldwin_park, "resume_gate", side_effect=boom), \
                mock.patch("transcript_activity.live_driver", side_effect=boom):
            rc, err = self.fire(self.home, pkg)
        self.assertEqual(rc, 0)
        self.assertEqual(self.names(), ["park_job_start", "sideeffect_refused"])
        self.assertLess(order.index("sideeffect_refused"), order.index("read_marker"))
        refused = self.events()[1]
        self.assertEqual((refused["site"], refused["reason"]),
                         ("park_cli._cmd_fire", "sandbox_no_lease"))
        self.assertIn("sandbox_no_lease", err)
        read_back = park.read_marker(SID)
        self.assertEqual(read_back["status"], "refused")
        self.assertIn("sandbox_no_lease", read_back["outcome"]["detail"])
        self.assertEqual(self.backend.disarmed, [self.label])
        self.assertEqual((self.spawn_calls, self.resume_calls), ([], []))
        self.assertEqual(list(self.bdir.iterdir()), [])

    def test_a_marker_of_another_job_is_left_alone(self) -> None:
        """park_cli.py::_cmd_fire：拒絕時標記不屬本 job（label 不在 jobs）⇒ 標記原樣、仍自拆本
        job。"""
        pkg = self.package(self.home)
        self.marker(pkg, label="AutoSDD_HandoffSpawn_other_202611222100")
        rc, _err = self.fire(self.home, pkg)
        self.assertEqual(rc, 0)
        self.assertEqual(park.read_marker(SID)["status"], "armed")
        self.assertEqual(self.backend.disarmed, [self.label])

    def test_real_exe_outside_the_sandbox_home_is_refused_at_the_gate(self) -> None:
        """park_cli.py::_cmd_fire：有租約但沒給 --claude（⇒ 真 claude）⇒ sandbox_real_exe 終局；
        給家目錄內的替身 ⇒ 放行並真的走到 spawn。"""
        self.lease()
        pkg = self.package(self.home)
        self.marker(pkg)
        rc, err = self.fire(self.home, pkg)
        self.assertEqual((rc, park.read_marker(SID)["status"]), (0, "refused"))
        self.assertIn("sandbox_real_exe", err)
        self.assertEqual(self.spawn_calls, [])
        exe = str(self.home / "bin" / "claude.exe")
        self.backend.jobs.add(self.label)
        self.marker(pkg)
        rc, _err = self.fire(self.home, pkg, "--claude", exe)
        self.assertEqual((rc, park.read_marker(SID)["status"]), (0, "fired"))
        self.assertEqual(self.spawn_calls, [{"claude": exe}])

    def test_at_se_44_every_spawn_attempt_uses_the_same_claude(self) -> None:
        """park_cli.py::_cmd_fire：FRESH 路（handoff.spawn）與 RESUME 路（spawn_resume）都收到同一個
        --claude；沒給時兩路都不帶 claude 參數（呼叫形態與修改前逐字相同）。"""
        self.lease()
        pkg = self.package(self.home)
        exe = str(self.home / "bin" / "claude.exe")
        for route in ("FRESH", "RESUME"):
            for argv, expect in (((), {}), (("--claude", exe), {"claude": exe})):
                with self.subTest(route=route, argv=argv):
                    self.spawn_calls.clear()
                    self.resume_calls.clear()
                    self.package(self.home)  # 改回沙盒目標（前一個子案例可能寫了正式 repo 的包）
                    self.marker(pkg)
                    self.backend.jobs.add(self.label)
                    chosen = (park.FIRE_RESUME, "t", 1) if route == "RESUME" else (
                        park.FIRE_FRESH, "t", None)
                    with mock.patch.object(park_cli, "_fire_route", return_value=chosen), \
                            mock.patch.object(oldwin_park, "resume_gate",
                                              return_value={"act": "go", "reason": ""}):
                        if not argv:  # 無 --claude 時沙盒會被 sandbox_real_exe 拒絕：改測正式目標
                            rc, _e = self.fire(self.prod, self.package(self.prod))
                        else:
                            rc, _e = self.fire(self.home, pkg, *argv)
                    self.assertEqual(rc, 0)
                    calls = self.resume_calls if route == "RESUME" else self.spawn_calls
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(calls[0].get("claude"), expect.get("claude"))
                    self.assertEqual("claude" in calls[0], bool(expect))

    def test_at_se_50_spawn_site_refusal_is_terminal_not_a_failure(self) -> None:
        """park_cli.py::_cmd_fire：spawn／resume 回 RC_SIDEEFFECT_REFUSED ⇒ 標記 refused、各只呼叫
        1 次
        （不走另一路）、無 handback、無 park_*_failed、自拆、rc 0；對照組 rc 1 ⇒
        failed＋handback。"""
        self.lease()
        pkg = self.package(self.home)
        exe = str(self.home / "bin" / "claude.exe")
        for route in ("FRESH", "RESUME"):
            with self.subTest(route=route):
                self.marker(pkg)
                self.backend.jobs.add(self.label)
                self.spawn_calls.clear()
                self.resume_calls.clear()
                self.spawn_rc = self.resume_rc = RC10
                chosen = (park.FIRE_RESUME, "t", 1) if route == "RESUME" else (
                    park.FIRE_FRESH, "t", None)
                with mock.patch.object(park_cli, "_fire_route", return_value=chosen), \
                        mock.patch.object(oldwin_park, "resume_gate",
                                          return_value={"act": "go", "reason": ""}):
                    rc, _e = self.fire(self.home, pkg, "--claude", exe)
                self.assertEqual(rc, 0)
                self.assertEqual(park.read_marker(SID)["status"], "refused")
                self.assertEqual((len(self.spawn_calls), len(self.resume_calls)),
                                 (1, 0) if route == "FRESH" else (0, 1))
                self.assertEqual(list(self.bdir.iterdir()), [])
                self.assertFalse({"park_spawn_failed", "park_resume_failed"} & set(self.names()))
        self.marker(pkg)
        self.spawn_rc = 1
        with mock.patch.object(park_cli, "_fire_route", return_value=(park.FIRE_FRESH, "t", None)):
            rc, _e = self.fire(self.home, pkg, "--claude", exe)
        self.assertEqual((rc, park.read_marker(SID)["status"]), (1, "failed"))
        self.assertEqual(len(list(self.bdir.iterdir())), 1)

    def test_at_se_31_production_target_sequence_is_unchanged(self) -> None:
        """park_cli.py::_cmd_fire：正式目標（tmp 正式 repo、pkg 同根）＋spawn 成功 ⇒ 痕跡序列＝
        park_job_start→park_route→park_spawned，無任何 sideeffect_*；標記 fired（QW Q3
        前的黃金序列；
        Q3 改 `_cmd_fire` 後由 Q3 同一個 commit 重釘，DES §10.2-9）。"""
        pkg = self.package(self.prod)
        self.marker(pkg)
        rc, err = self.fire(self.prod, pkg)
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(self.names(), ["park_job_start", "park_route", "park_spawned"])
        self.assertEqual(park.read_marker(SID)["status"], "fired")
        self.assertEqual(self.spawn_calls, [{}])


class SpawnSiteTest(_SeFence):
    """tools/lib/sessionctl/handoff.py::spawn 與 park_cli.py::spawn_resume：runner 前的 L1（
    AT-SE-12）。"""

    def spawn_env(self) -> dict:
        return {**self.env, "AUTOSDD_SESSION_SWITCH_MODE": "auto"}

    def test_at_se_12_no_lease_never_reaches_the_runner(self) -> None:
        """handoff.spawn／park_cli.spawn_resume：沙盒無租約 ⇒ rc＝RC_SIDEEFFECT_REFUSED、stderr 帶
        reason、痕跡 sideeffect_refused、runner 0 次、無 .spawned／.resumed。"""
        pkg = self.package(self.home)
        for name, call in (
                ("handoff.spawn", lambda runner: handoff.spawn(
                    pkg, runner=runner, platform_name="win32", env=self.spawn_env(),
                    repo=self.home)),
                ("park_cli.spawn_resume", lambda runner: park_cli.spawn_resume(
                    SID, pkg, runner=runner, platform_name="win32", env=self.spawn_env(),
                    repo=self.home, projects_dir=self.tmp / "proj"))):
            with self.subTest(site=name):
                runner = mock.Mock(side_effect=AssertionError("runner 不得被呼叫"))
                err = io.StringIO()
                with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                    rc = call(runner)
                self.assertEqual(rc, RC10)
                self.assertIn("sandbox_no_lease", err.getvalue())
                runner.assert_not_called()
                self.assertEqual([p.suffix for p in self.hdir.iterdir() if p.suffix in
                                  (".spawned", ".resumed")], [])
        refused = [e for e in self.events() if e["event"] == "sideeffect_refused"]
        self.assertEqual([e["site"] for e in refused], ["handoff.spawn", "park_cli.spawn_resume"])

    def test_bare_claude_is_refused_even_with_a_valid_lease_but_a_home_exe_passes(self) -> None:
        """park_cli.spawn_resume：租約有效、未給 --claude ⇒ sandbox_real_exe；給家目錄內的執行檔 ⇒
        L1 放行，runner 的 argv[0] 就是那個替身。"""
        self.lease()
        pkg = self.package(self.home)
        base = {"platform_name": "win32", "env": self.spawn_env(), "repo": self.home,
                "projects_dir": self.tmp / "proj", "alive": lambda _p: False,
                "sleep": lambda _s: None, "wait_seconds": 0}
        runner = mock.Mock(return_value=(0, "", 4242))
        with contextlib.redirect_stderr(io.StringIO()) as err, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(park_cli.spawn_resume(SID, pkg, runner=runner, **base), RC10)
        self.assertIn("sandbox_real_exe", err.getvalue())
        runner.assert_not_called()
        exe = str(self.home / "bin" / "claude.exe")
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            rc = park_cli.spawn_resume(SID, pkg, runner=runner, claude=exe, **base)
        self.assertEqual(rc, 1)  # 行程「已不在」＝一般失敗，不是 L1 拒絕
        self.assertEqual(runner.call_args.args[0][0], exe)

    def test_unattended_fence_and_l1_are_independent(self) -> None:
        """handoff.spawn：無人旗標先拒絕（rc 1，舊行為不變）；L1 不依賴它（無旗標時才由 L1 拒絕 rc
        10）。"""
        pkg = self.package(self.home)
        runner = mock.Mock()
        with contextlib.redirect_stderr(io.StringIO()):
            rc = handoff.spawn(pkg, runner=runner, platform_name="win32", repo=self.home,
                               env={**self.spawn_env(), "AUTOSDD_UNATTENDED": "1"})
        self.assertEqual(rc, 1)
        self.assertNotIn("sideeffect_refused", self.names())

    def test_handoff_cli_accepts_claude_and_passes_it_through(self) -> None:
        """handoff.py::cli：`--spawn <包> --claude <path>` 把 path 交給 spawn（驗證用執行檔）。"""
        exe = str(self.tmp / "fake" / "claude.exe")
        with mock.patch.object(handoff, "spawn", return_value=0) as spawned:
            self.assertEqual(handoff.cli(["--spawn", "x.md", "--claude", exe]), 0)
        spawned.assert_called_once_with("x.md", claude=exe)


class RegisterSiteTest(_SeFence):
    """park_cli.py::_cmd_park、oldwin_sched.py::schedule_retry、oldwin_park.py::_rearm：登記前 L1、
    job 環境轉送與沙盒自毀（AT-SE-11、15、49）。"""

    def setUp(self) -> None:
        super().setUp()
        self.armed: list[dict] = []

    def arm(self, label, argv, cwd, fire, *, interactive=False, expire_at=None):
        self.armed.append({"label": label, "argv": argv, "fire": fire, "expire_at": expire_at})
        self.backend.jobs.add(label)
        return 0, "NextRunTime = 2026-11-22 20:00:00（排程器自報）"

    def park(self, repo: Path, pkg: Path, *argv: str, env: dict | None = None):
        at = (_now() + timedelta(minutes=10)).isoformat()
        seams = {"backend": self.backend, "arm": self.arm, "runner": FakeRunner(),
                 "roster": FakeRoster()}
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(park_cli, "_REPO", repo), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            rc = park_cli.run(["--session-id", SID, "--at", at, "--why", "測試用的原因說明",
                               "--pkg", str(pkg), *argv], env=dict(env or {}), seams=seams)
        return rc, err.getvalue()

    def test_at_se_11_park_refusals_never_arm(self) -> None:
        """park_cli.py::_cmd_park：沙盒無租約⇒rc 4／租約短於觸發時刻⇒rc 4 lease_shorter_than_fire；
        arm 0 次、stderr 帶 reason、痕跡 sideeffect_refused site＝park_cli._cmd_park、不寫標記。"""
        pkg = self.package(self.home)
        rc, err = self.park(self.home, pkg)
        self.assertEqual(rc, 4)
        self.assertIn("sandbox_no_lease", err)
        self.lease(minutes=2)
        rc, err = self.park(self.home, pkg)
        self.assertEqual(rc, 4)
        self.assertIn("lease_shorter_than_fire", err)
        self.assertEqual((self.armed, park.read_marker(SID)), ([], None))
        refused = [e for e in self.events() if e["event"] == "sideeffect_refused"]
        self.assertEqual([(e["site"], e["reason"]) for e in refused],
                         [("park_cli._cmd_park", "sandbox_no_lease"),
                          ("park_cli._cmd_park", "lease_shorter_than_fire")])

    def test_sandbox_registration_carries_expiry_job_env_and_claude(self) -> None:
        """park_cli.py::_cmd_park：沙盒有租約 ⇒ arm 帶 expire_at＝allow_until、job argv 帶
        `--job-env`（顯式空通知＝關閉值）與 `--claude`；標記 claude 欄＝同一值。"""
        until = self.lease()
        pkg = self.package(self.home)
        exe = str(self.home / "bin" / "claude.exe")
        rc, err = self.park(self.home, pkg, "--claude", exe, env={"AUTOSDD_DESKTOP_NOTIFY": ""})
        self.assertEqual((rc, err), (0, ""))
        got = self.armed[0]
        self.assertEqual(got["expire_at"], _secs(until))
        argv = got["argv"]
        self.assertIn("--claude", argv)
        self.assertEqual(argv[argv.index("--claude") + 1], exe)
        self.assertEqual(argv[argv.index("--job-env") + 1], "AUTOSDD_DESKTOP_NOTIFY=")
        self.assertEqual(park.read_marker(SID)["claude"], exe)

    def test_at_se_49_job_env_value_rules_differ_by_target(self) -> None:
        """park_cli.py::_cmd_park：通知＝1（不在允許值）：沙盒 ⇒ rc 2、arm 0 次、stderr 點名鍵與值；
        正式目標 ⇒ 登記成功、argv 不含 --job-env、arm 不帶 expire_at、標記無 claude 欄、無
        sideeffect_*。"""
        self.lease()
        rc, err = self.park(self.home, self.package(self.home), env={"AUTOSDD_DESKTOP_NOTIFY": "1"})
        self.assertEqual(rc, 2)
        self.assertIn("AUTOSDD_DESKTOP_NOTIFY", err)
        self.assertEqual(self.armed, [])
        rc, err = self.park(self.prod, self.package(self.prod), env={"AUTOSDD_DESKTOP_NOTIFY": "1"})
        self.assertEqual((rc, err), (0, ""))
        self.assertNotIn("--job-env", self.armed[0]["argv"])
        self.assertIsNone(self.armed[0]["expire_at"])
        self.assertNotIn("claude", park.read_marker(SID))
        self.assertEqual([n for n in self.names() if n.startswith("sideeffect_")],
                         ["sideeffect_refused"])  # 只有上面沙盒那一筆

    def test_production_argv_is_byte_identical_to_the_pre_change_builder(self) -> None:
        """park_cli.py::job_argv：沒有顯式 job 環境值、沒給 --claude ⇒ argv
        與修改前的建構逐字相同。"""
        label, fire, pkg = "L", _now(), Path("p.md")
        import win_spawn
        legacy = [win_spawn.quiet_python(), str(park_cli._REPO / "tools" / "sessionctl.py"), "park",
                  "--fire", "--job", "L", "--session-id", SID, "--pkg", "p.md", "--fire-at",
                  fire.isoformat(timespec="seconds")]
        self.assertEqual(park_cli.job_argv(label, SID, pkg, fire), legacy)
        self.assertEqual(park_cli.job_argv(label, SID, pkg, fire, []), legacy)

    def test_at_se_15_oldwin_retry_registration(self) -> None:
        """oldwin_sched.py::schedule_retry：沙盒無租約 ⇒ (4, "")、arm 0 次、不動既有工作；有租約 ⇒
        arm 帶 expire_at 且 argv 帶 --job-env（居所）；正式目標 ⇒ 無 expire_at、argv 與舊式相同。"""
        pkg = self.package(self.home)
        when = (_now() + timedelta(minutes=5)).timestamp()
        calls: list[dict] = []

        def arm(label, argv, cwd, fire, **kw):
            calls.append({"argv": argv, **kw})
            return 0, "NextRunTime = x"
        be = mock.Mock(list_jobs=mock.Mock(return_value=[]), disarm=mock.Mock())
        env = {"AUTOSDD_TRACE_DIR": str(self.tdir)}

        def retry(repo, package):
            with mock.patch.object(oldwin_sched, "_REPO", repo), \
                    contextlib.redirect_stderr(io.StringIO()):
                return oldwin_sched.schedule_retry("oldsid12345", "newsid", package, when, env=env,
                                                   arm=arm, backend=be)
        self.assertEqual(retry(self.home, pkg), (4, ""))
        self.assertEqual((calls, be.list_jobs.call_count, be.disarm.call_count), ([], 0, 0))
        until = self.lease()
        self.assertEqual(retry(self.home, pkg)[0], 0)
        self.assertEqual(calls[0]["expire_at"], _secs(until))
        self.assertIn("--job-env", calls[0]["argv"])
        prod_pkg = self.package(self.prod)
        self.assertEqual(retry(self.prod, prod_pkg)[0], 0)
        self.assertNotIn("expire_at", calls[1])

    def test_rearm_inside_a_job_is_gated_and_keeps_the_fence(self) -> None:
        """oldwin_park.py::_rearm：沙盒無租約 ⇒ False、不 arm、舊標記不動；有租約 ⇒ 重排並把 job
        環境與
        自毀時刻帶過去（否則重試 job 會掉出沙盒圍籬）。"""
        pkg = self.package(self.home)
        self.marker(pkg)
        env = {"AUTOSDD_TRACE_DIR": str(self.tdir)}
        when = (_now() + timedelta(minutes=5)).timestamp()
        S = {"arm": self.arm}
        with mock.patch.object(park_cli, "_REPO", self.home), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(oldwin_park._rearm(SID, pkg, when, env, _now(), S))
            self.assertEqual(self.armed, [])
            self.lease()
            self.assertTrue(oldwin_park._rearm(SID, pkg, when, env, _now(), S))
        self.assertIsNotNone(self.armed[0]["expire_at"])
        self.assertIn("--job-env", self.armed[0]["argv"])


class RefusedReadEndTest(_SeFence):
    """park.py／park_cli.py／handoff.py：`refused` 標記的讀取端（AT-SE-43）。"""

    def test_at_se_43_refused_is_a_valid_terminal_marker_and_never_a_credential(self) -> None:
        """park.STATUSES 含 refused；read_marker 回標記、`park --status` 印 refused 與 reason、
        yields
        False、stop_verdict 推回（不當續航憑證）、SessionStart
        公告一行含「產品面拒絕」且不含失敗字樣。"""
        import quota_policy
        import quota_policy_env
        self.assertIn("refused", park.STATUSES)
        pkg = self.package(self.home)
        marker = self.marker(pkg)
        park_cli._settle(marker, "refused", "sideeffect_refused", reason="sandbox_no_lease")
        got = park.read_marker(SID)
        self.assertEqual(got["status"], "refused")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            park_cli.run(["--session-id", SID, "--status"], env={})
        self.assertIn("status=refused", out.getvalue())
        self.assertIn("sandbox_no_lease", out.getvalue())
        now = _now()
        self.assertFalse(park.yields(got, now))
        reset = (now + timedelta(minutes=40)).isoformat()
        state = quota_policy.QuotaState((quota_policy.Axis("five_hour", 98.0, reset),),
                                        now.isoformat(), "test")
        policy = quota_policy_env.load_policy({"AUTOSDD_QUOTA_PREPARE_PCT": "85"})[0]
        verdict = park.stop_verdict({"session_id": SID}, {"AUTOSDD_SESSION_SWITCH_MODE": "auto"},
                                    now=now, read_quota=lambda _n: state, policy_fn=lambda: policy,
                                    carrier_fn=lambda: True, spawned_fn=lambda _s, _e: False)
        self.assertIn("沒有任何續航憑證", verdict)
        notes = se_gate.refused_notes(SID)
        self.assertEqual(len(notes), 1)
        self.assertIn("產品面拒絕", notes[0])
        for word in ("失敗", "failed", "FAIL"):
            self.assertNotIn(word, notes[0])
        emitted: list[str] = []
        text = handoff.announce(lambda m: emitted.append(m) or True, base=self.hdir, sid=SID)
        self.assertIn("產品面拒絕", text)
        self.assertEqual(se_gate.refused_notes("other-sid"), [])


class RvOrphanLineTest(unittest.TestCase):
    """tools/lib/sessionctl/rv_orphans.py：`sessionctl status` 的孤兒行只讀帳檔（AT-SE-28）。"""

    def test_at_se_28_counts_only_pending_rows_with_a_dead_owner_and_changes_nothing(self) -> None:
        """一份 made＋主人已死、一份 revoked（結清）、一份 made＋主人存活 ⇒ n=1；帳檔位元組與 mtime
        不變；sessionctl 套件沒有任何 realverify import（單向相依）。"""
        with tempfile.TemporaryDirectory(prefix="tw-orph-") as tmp:
            folder = Path(tmp)

            def row(ident, state, pid):
                return json.dumps({"at": "x", "kind": "sched_job", "ident": ident, "undo": "",
                                   "owner_pid": pid, "owner_started": None, "expires_at": None,
                                   "state": state}) + "\n"
            gone = 99999999
            for name, body in (
                    ("a", row("A", "intent", gone) + row("A", "made", gone)),
                    ("b", row("B", "made", gone) + row("B", "revoked", gone)),
                    ("c", row("C", "made", os.getpid()) + "壞列\n")):
                (folder / f"{name}.jsonl").write_text(body, encoding="utf-8")
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
            with mock.patch.object(rv_orphans, "lease_dir", return_value=folder):
                # 主人存活但驗不到建立時間時改看 expires_at（null＝不判孤兒）
                with mock.patch.object(sandbox_scope, "proc_probe",
                                       side_effect=lambda pid: (pid == os.getpid(), None)):
                    line = rv_orphans.status_line()
            self.assertEqual(line, "realverify 孤兒 n=1")
            self.assertEqual({p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                              for p in folder.iterdir()}, before)
            with mock.patch.object(rv_orphans, "lease_dir", return_value=folder / "none"):
                self.assertEqual(rv_orphans.status_line(), "realverify 孤兒 n=0")

    def test_format_constants_equal_the_writer_and_there_is_no_realverify_import(self) -> None:
        """rv_orphans.py 的帳格式常數與寫端 `realverify/leases.py` 逐一相等；sessionctl 套件無
        import。"""
        from lib.realverify import leases
        self.assertEqual((rv_orphans.SCHED_KIND,), leases.KINDS)
        self.assertEqual(rv_orphans.PENDING, leases._PENDING)
        self.assertEqual(rv_orphans.lease_dir(), leases.LEASE_DIR)
        for path in (_ROOT / "tools" / "lib" / "sessionctl").glob("*.py"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("#", 1)[0]
                if "import" in code and "realverify" in code:
                    self.fail(f"{path.name}:{number} 不得 import realverify：{line.strip()}")


class PackageHeaderContractTest(unittest.TestCase):
    """tools/lib/sessionctl/handoff_build.py：交接包檔頭「repo 根：」行的寫端與讀端（`sandbox_scope.
    pkg_root`）共用同一個常數——兩處各寫一份字串，改一邊另一邊就讀不到（L1 會因此 fail-closed）。"""

    def test_the_writer_output_is_readable_by_the_l1_reader(self) -> None:
        """handoff_build 產出的機械層，經 `sandbox_scope.pkg_root` 讀回的路徑＝寫入的 repo 根。"""
        from lib.sessionctl import handoff_build
        with tempfile.TemporaryDirectory(prefix="tw-hdr-") as tmp:
            repo = Path(tmp) / "some repo"
            repo.mkdir()
            self.assertIs(handoff_build.sandbox_scope, sandbox_scope)
            mech = handoff_build.build_mechanical(
                SID, None, repo=repo, now=_now(), runner=FakeRunner(), roster_mod=FakeRoster())
            pkg = Path(tmp) / "pkg.md"
            pkg.write_text(mech, encoding="utf-8")
            self.assertEqual(sandbox_scope.pkg_root(pkg), repo)


class EntryAndRegistryTest(unittest.TestCase):
    """tools/sessionctl.py：入口最先套用 job 環境（AT-SE-37 的 sessionctl 半邊）；
    `sandbox_scope.SITES`
    的 sessionctl 列與原始碼的對帳。"""

    def run_entry(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(_ROOT / "tools" / "sessionctl.py"), *argv],
                              capture_output=True, text=True, encoding="utf-8", cwd=str(_ROOT),
                              check=False, timeout=120)

    def test_at_se_37_gone_sandbox_residence_exits_9_and_creates_nothing(self) -> None:
        """tools/sessionctl.py：居所值指向已刪的沙盒家 ⇒ 真行程 rc 9、stderr 一行、目錄不被建立；
        不在允許表的鍵 ⇒ rc 2。"""
        with tempfile.TemporaryDirectory(prefix="tw-entry-") as tmp:
            gone = Path(tmp) / "AutoSDD_RV_sbx_gone" / "traces"
            before = sorted(p.name for p in Path(tmp).iterdir())
            done = self.run_entry("--job-env", f"AUTOSDD_TRACE_DIR={gone}", "oldwin", "--status")
            self.assertEqual(done.returncode, 9, done.stderr)
            self.assertEqual(len(done.stderr.strip().splitlines()), 1)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), before)
            bad = self.run_entry("--job-env", "FOO_DIR=x", "oldwin", "--status")
            self.assertEqual(bad.returncode, 2)

    def test_sites_registry_matches_source(self) -> None:
        """sandbox_scope.py::SITES 的 sessionctl 列：函式真的存在，且函式本體呼叫
        se_gate.check／register
        （漏接線或漏登記皆紅；登記的類別與實際呼叫的接點一致）。"""
        import ast
        rows = [s for s in sandbox_scope.SITES if s.module.startswith("lib.sessionctl.")]
        self.assertEqual(len(rows), 6)
        for site in rows:
            path = _ROOT / "tools" / (site.module.replace(".", "/") + ".py")
            tree = ast.parse(path.read_text(encoding="utf-8"))
            func = next(n for n in ast.walk(tree)
                        if isinstance(n, ast.FunctionDef) and n.name == site.function)
            calls = {n.func.attr for n in ast.walk(func)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                     and isinstance(n.func.value, ast.Name) and n.func.value.id == "se_gate"}
            expect = "register" if site.kind == "register" else "check"
            self.assertIn(expect, calls, f"{site}")


if __name__ == "__main__":
    unittest.main()
