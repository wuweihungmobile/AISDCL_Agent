#!/usr/bin/env python3
"""`sched_isolation.py`＋`session_resume_planner` 站點接線的驗收（DES S2：哨兵／續航排程）。

規格：DES RealVerify_SideEffect_Isolation §3.4（tick／register／headless 站點）、§4（job 環境）、
§5.4（OS 自毀）。
WHY（Rule 9）：A6f 鑑定——RV-SK1／SK2 的沙盒哨兵 `AutoSDD_Sentinel_<沙盒 sid>` 是真前綴，排程 tick
吃機器環境，痕跡進真 `~/.autosdd`、SK2 會發真 `claude -p -r`。每條斷言對應「拿掉那個接點就會重演」：
  · 登記首判拿掉 ⇒ 沒有租約的沙盒也能登記哨兵；
  · `--job-env` 搬運拿掉 ⇒ tick 回到真居所；
  · 到點首判拿掉 ⇒ 主人已死／租約過期的沙盒哨兵照樣醒來探測；
  · 執行檔判準拿掉 ⇒ 沙盒目標用真 `claude`；
  · 自毀拿掉 ⇒ 沙盒排程（哨兵每 15 分重排）靠人清。
E2E 類走真子行程＋真 schtasks（Windows），沙盒前綴 `AutoSDD_RV_sbx_`，環境不帶任何 AUTOSDD_*
（等同排程器的真環境）。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

import endurance_env  # noqa: E402
import sandbox_scope as ss  # noqa: E402
import sched_isolation as si  # noqa: E402

import session_resume_planner as planner  # noqa: E402

NOW = datetime.now().astimezone().replace(microsecond=0)
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _sandbox(parent: Path, lease_min: int | None = 20, *, owner_pid: int | None = None) -> Path:
    home = parent / f"AutoSDD_RV_sbx_{uuid.uuid4().hex[:8]}"
    (home / ".git").mkdir(parents=True)
    ss.write_identity(home, run_id="r1", sid="s1", owner_pid=owner_pid or os.getpid(), now=NOW)
    if lease_min is not None:
        ss.grant(home, until=NOW + timedelta(minutes=lease_min), now=NOW)
    return home


def _fire_expr(fire: datetime) -> str:
    return f"'{fire:%Y-%m-%d %H:%M:%S}'"


class _Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.traces: list[tuple[str, dict]] = []

    def trace(self, event: str, **fields) -> None:
        self.traces.append((event, fields))


class CarriageTest(_Tmp):
    def test_official_target_without_explicit_env_carries_nothing(self) -> None:
        """正式目標＋無顯式 env ⇒ 三段全空（註冊腳本與 Action 引數逐字不變）。"""
        got = si.carriage(self.tmp, {}, NOW, "'2026-11-21 18:00:00'")
        self.assertEqual(got, si.Carriage())

    def test_official_target_forwards_only_explicit_valid_keys(self) -> None:
        env = {"AUTOSDD_SESSION_SWITCH_MODE": "notify", "AUTOSDD_DESKTOP_NOTIFY": "1"}
        got = si.carriage(self.tmp, env, NOW)  # 後者不合法：靜默不轉送
        self.assertEqual(got.argument, ' --job-env "AUTOSDD_SESSION_SWITCH_MODE=notify"')
        self.assertEqual((got.trigger_ps, got.settings_ps), ("", ""))

    def test_sandbox_with_lease_forwards_residences_and_self_destructs(self) -> None:
        home = _sandbox(self.tmp)
        env = {"AUTOSDD_TRACE_DIR": str(home / "traces"), "AUTOSDD_SENTINEL_OFF": "1"}
        got = si.carriage(home, env, NOW, _fire_expr(NOW + timedelta(minutes=15)))
        self.assertIn(f' --job-env "AUTOSDD_TRACE_DIR={home / "traces"}"', got.argument)
        self.assertIn(' --job-env "AUTOSDD_SENTINEL_OFF=1"', got.argument)
        until = ss.job_expiry(home, NOW)
        self.assertIn(f"$trigger.EndBoundary = '{until:%Y-%m-%dT%H:%M:%S}'", got.trigger_ps)
        self.assertIn("DeleteExpiredTaskAfter = 'PT0S'", got.settings_ps)

    def test_sandbox_lease_not_after_fire_makes_the_script_throw(self) -> None:
        home = _sandbox(self.tmp, lease_min=5)
        got = si.carriage(home, {}, NOW, _fire_expr(NOW + timedelta(minutes=15)))
        self.assertTrue(got.trigger_ps.startswith("throw '拒絕註冊"), got.trigger_ps)
        self.assertNotIn("$trigger.EndBoundary", got.trigger_ps)

    def test_sandbox_with_a_forbidden_value_raises_instead_of_dropping(self) -> None:
        home = _sandbox(self.tmp)
        with self.assertRaises(endurance_env.JobEnvValueError):
            si.carriage(home, {"AUTOSDD_SENTINEL_OFF": "0"}, NOW)


class RegisterGateTest(_Tmp):
    def _gate(self, root: Path, env=None, fire=None) -> int:
        return si.register_gate(root, env or {}, fire, self.trace, "_register_and_record")

    def test_official_target_passes_without_a_trace(self) -> None:
        self.assertEqual(self._gate(self.tmp), 0)
        self.assertEqual(self.traces, [])

    def test_sandbox_without_lease_is_refused_rc4_with_reason_and_trace(self) -> None:
        home = _sandbox(self.tmp, lease_min=None)
        with mock.patch("sys.stderr"):
            self.assertEqual(self._gate(home), si.RC_REGISTER_REFUSED)
        event, fields = self.traces[0]
        self.assertEqual(event, "sideeffect_refused")
        self.assertEqual((fields["reason"], fields["site"]),
                         ("sandbox_no_lease", "_register_and_record"))

    def test_lease_shorter_than_fire_is_refused(self) -> None:
        home = _sandbox(self.tmp, lease_min=5)
        with mock.patch("sys.stderr"):
            rc = self._gate(home, fire=NOW + timedelta(minutes=15))
        self.assertEqual((rc, self.traces[0][1]["reason"]), (4, "lease_shorter_than_fire"))

    def test_sandbox_with_valid_lease_passes(self) -> None:
        home = _sandbox(self.tmp)
        self.assertEqual(self._gate(home, fire=NOW + timedelta(minutes=15)), 0)

    def test_job_env_with_a_forbidden_value_in_a_sandbox_is_rc2(self) -> None:
        home = _sandbox(self.tmp)
        with mock.patch("sys.stderr"):
            rc = self._gate(home, {"AUTOSDD_DESKTOP_NOTIFY": "1"})
        self.assertEqual(rc, endurance_env.JobEnvValueError.rc)
        self.assertTrue(self.traces[0][1]["reason"].startswith("job_env:"))

    def test_codes_are_distinct_from_the_other_isolation_codes(self) -> None:
        codes = {si.RC_REGISTER_REFUSED, ss.RC_SIDEEFFECT_REFUSED,
                 endurance_env.RC_RESIDENCE_MISSING, endurance_env.JobEnvValueError.rc}
        self.assertEqual(len(codes), 4)


class TickGateTest(_Tmp):
    def _gate(self, root: Path, **kw):
        with mock.patch("sys.stderr"):
            return si.tick_gate(root, "_sentinel_tick", "AutoSDD_Sentinel_x", self.trace, **kw)

    def test_official_target_is_released(self) -> None:
        self.assertIsNone(self._gate(self.tmp))
        self.assertEqual(self.traces, [])

    def test_each_dead_sandbox_shape_is_refused_rc10_with_its_reason(self) -> None:
        dead = subprocess.Popen([sys.executable, "-c", "pass"], creationflags=_NOWIN)
        dead.wait()
        gone = _sandbox(self.tmp)
        shutil.rmtree(gone)
        cases = {
            "sandbox_no_lease": _sandbox(self.tmp, lease_min=None),
            "sandbox_owner_dead": _sandbox(self.tmp, owner_pid=dead.pid),
            "target_missing": gone,
        }
        for reason, home in cases.items():
            with self.subTest(reason):
                self.traces.clear()
                self.assertEqual(self._gate(home), ss.RC_SIDEEFFECT_REFUSED)
                self.assertEqual(self.traces[0][1]["reason"], reason)

    def test_expired_lease_is_refused(self) -> None:
        home = _sandbox(self.tmp, lease_min=1)
        with mock.patch.object(si, "datetime") as clock, mock.patch("sys.stderr"):
            clock.now.return_value = NOW + timedelta(hours=1)
            rc = si.tick_gate(home, "_sentinel_tick", None, self.trace)
        self.assertEqual(rc, ss.RC_SIDEEFFECT_REFUSED)
        self.assertEqual(self.traces[0][1]["reason"], "sandbox_lease_expired")

    def test_a_real_claude_is_refused_but_an_in_home_exe_passes(self) -> None:
        home = _sandbox(self.tmp)
        self.assertEqual(self._gate(home, exe="claude"), ss.RC_SIDEEFFECT_REFUSED)
        self.assertEqual(self.traces[0][1]["reason"], "sandbox_real_exe")
        fake = home / "bin" / "claude.exe"
        fake.parent.mkdir()
        fake.write_bytes(b"")
        self.assertIsNone(self._gate(home, exe=str(fake)))
        self.assertIsNone(self._gate(home, exe=None), "純巡邏讀檔的首判不傳 exe")

    def test_a_sandbox_transcript_slug_flags_an_official_checkout(self) -> None:
        """真 tools＋沙盒逐字稿：cwd 正式、逐字稿 slug 含沙盒片段、無可讀身分檔 ⇒ 拒絕。"""
        transcript = self.tmp / "C--x-AutoSDD-RV-sbx-abc12345" / "s.jsonl"
        transcript.parent.mkdir()
        transcript.write_text("{}", encoding="utf-8")
        self.assertEqual(self._gate(self.tmp, transcript=str(transcript)),
                         ss.RC_SIDEEFFECT_REFUSED)
        self.assertEqual(self.traces[0][1]["reason"], "sandbox_unreadable")


class PlannerWiringTest(_Tmp):
    """planner 的接點真的呼叫判準（不是只有 `sched_isolation` 自己會動）。"""

    def _args(self, home: Path, task: str) -> Namespace:
        return Namespace(plan=str(home / "plan.md"), task_name=task, probe_command="claude")

    def test_sites_are_registered_in_sandbox_scope(self) -> None:
        mine = {(s.function, s.kind) for s in ss.SITES if s.module == "session_resume_planner"}
        self.assertEqual(mine, {("_register_and_record", "register"), ("_sentinel_tick", "tick"),
                                ("_resume_tick", "tick"), ("main", "headless")})

    def test_script_for_the_official_target_has_no_isolation_residue(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            for key in endurance_env.JOB_ENV_KEYS:
                os.environ.pop(key, None)
            script = planner.endurance_schtasks_script(
                str(self.tmp / "p.md"), "T", "'2026-11-21 18:00:00'")
        for needle in ("--job-env", "EndBoundary", "DeleteExpired"):
            self.assertNotIn(needle, script)

    def test_script_for_a_sandbox_carries_env_and_self_destruct(self) -> None:
        home = _sandbox(self.tmp)
        fire = NOW + timedelta(minutes=15)
        with (
            mock.patch.object(planner, "_REPO_ROOT", home),
            mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(home / "traces")}),
        ):
            script = planner.endurance_schtasks_script(
                str(home / "p.md"), "T", _fire_expr(fire))
        self.assertIn(f"--job-env \"AUTOSDD_TRACE_DIR={home / 'traces'}\"", script)
        self.assertLess(script.index("-Once -At"), script.index("$trigger.EndBoundary"))
        self.assertIn("DeleteExpiredTaskAfter", script)

    def test_register_and_record_refuses_a_leaseless_sandbox_before_the_scheduler(self) -> None:
        home = _sandbox(self.tmp, lease_min=None)
        plan = home / "plan.md"
        plan.write_text("# p\n", encoding="utf-8")
        state = {"session_id": "s", "task_name": "AutoSDD_Sentinel_s", "plan_path": str(plan)}
        backend = mock.Mock()
        with (
            mock.patch.object(planner, "_REPO_ROOT", home),
            mock.patch.object(planner.schedule_backend, "select", return_value=backend),
            mock.patch.object(planner.relay_machine, "single_owner_conflict", return_value=False),
            mock.patch.object(planner.switch, "trace") as trace,
            mock.patch("sys.stderr"),
        ):
            got = planner._register_and_record(
                plan, state, NOW + timedelta(minutes=15), planner.SENTINEL_TICK)
        self.assertEqual(got, (si.RC_REGISTER_REFUSED, ""))
        backend.arm.assert_not_called()
        self.assertNotIn("RELAY", plan.read_text(encoding="utf-8"), "拒絕時不寫狀態塊")
        self.assertEqual(trace.call_args.args[0], "sideeffect_refused")

    def test_sentinel_tick_in_a_dead_sandbox_refuses_before_any_log_or_probe(self) -> None:
        home = _sandbox(self.tmp, lease_min=None)
        removed: list[str] = []
        with (
            mock.patch.object(planner, "_REPO_ROOT", home),
            mock.patch.object(planner, "_schtasks_remove", side_effect=removed.append),
            mock.patch.object(planner, "append_log") as append,
            mock.patch.object(planner, "probe_quota") as probe,
            mock.patch.object(planner.switch, "trace"),
            mock.patch("sys.stderr"),
        ):
            rc = planner._sentinel_tick(self._args(home, "AutoSDD_Sentinel_s"))
        self.assertEqual(rc, ss.RC_SIDEEFFECT_REFUSED)
        self.assertEqual(removed, ["AutoSDD_Sentinel_s"], "自拆排程")
        append.assert_not_called()  # 連 `sentinel_woken` 都不寫（不洩進系統暫存）
        probe.assert_not_called()

    def test_resume_tick_refuses_and_the_probe_verb_refuses_a_real_claude(self) -> None:
        home = _sandbox(self.tmp, lease_min=None)
        removed: list[str] = []
        with (
            mock.patch.object(planner, "_REPO_ROOT", home),
            mock.patch.object(planner, "_schtasks_remove", side_effect=removed.append),
            mock.patch.object(planner, "probe_quota") as probe,
            mock.patch.object(planner.switch, "trace"),
            mock.patch("sys.stderr"),
        ):
            self.assertEqual(planner._resume_tick(self._args(home, "AutoSDD_RM_s")),
                             ss.RC_SIDEEFFECT_REFUSED)
            self.assertEqual(planner.main(["--probe-quota"]), ss.RC_SIDEEFFECT_REFUSED)
        self.assertEqual(removed, ["AutoSDD_RM_s"], "verb 沒有排程可拆")
        probe.assert_not_called()

    def test_main_strips_job_env_into_the_environment_first(self) -> None:
        res = self.tmp / "res"
        res.mkdir()
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AUTOSDD_TRACE_DIR", None)
            rc = planner.main(["--check-autocompact", "--job-env", f"AUTOSDD_TRACE_DIR={res}"])
            self.assertIn(rc, (0, 1), "argparse 不得因未知旗標 --job-env 而 rc 2")
            self.assertEqual(os.environ["AUTOSDD_TRACE_DIR"], str(res))

    def test_main_rejects_a_job_env_outside_the_allow_table_with_rc2(self) -> None:
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit) as caught:
            planner.main(["--check-autocompact", "--job-env", "AUTOSDD_UNATTENDED=1"])
        self.assertEqual(caught.exception.code, 2)


_WIN = sys.platform == "win32"
_PY = sys.executable
_COPY_IGNORE = shutil.ignore_patterns("tests", "__pycache__", "*.pyc", ".git")
_PS = "powershell.exe"  # 只在 Windows 限定的 E2E 類（skipUnless win32）內使用


def _ps(script: str, timeout: int = 60) -> str:
    argv = [_PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script]
    out = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                         errors="replace", timeout=timeout, creationflags=_NOWIN, check=False)
    return out.stdout.strip()


@unittest.skipUnless(_WIN, "真 schtasks（Windows）；launchd 無 EndBoundary，job env 不過其邊界")
class SentinelSandboxE2ETest(unittest.TestCase):
    """E2E-S2：真子行程＋真 schtasks。沙盒＝`%TEMP%\\AutoSDD_RV_sbx_*` 的工具副本；排程環境＝
    不帶任何 AUTOSDD_*。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sid = str(uuid.uuid4())
        cls.task = f"AutoSDD_Sentinel_{cls.sid}"
        cls.home = Path(tempfile.gettempdir()) / f"AutoSDD_RV_sbx_s2e2e{uuid.uuid4().hex[:6]}"
        (cls.home / ".git").mkdir(parents=True)
        cls.addClassCleanup(cls._cleanup)
        # 來源唯讀、目的在 %TEMP%：不是樹內寫入
        shutil.copytree(_REPO_ROOT / "tools", cls.home / "tools",  # tmpdir-ok: 目的在 %TEMP%
                        ignore=_COPY_IGNORE)
        shutil.copytree(_REPO_ROOT / ".claude" / "hooks",  # tmpdir-ok: 目的在 %TEMP%
                        cls.home / ".claude" / "hooks", ignore=_COPY_IGNORE)
        shutil.copy2(_REPO_ROOT / ".claude" / "settings.unattended.json",
                     cls.home / ".claude" / "settings.unattended.json")
        cls.res = {k: cls.home / "res" / k.removeprefix("AUTOSDD_").removesuffix("_DIR").lower()
                   for k in endurance_env.RESIDENCE_KEYS}
        for path in cls.res.values():
            path.mkdir(parents=True)
        cls.transcript = cls.home / "tx" / f"{cls.sid}.jsonl"
        cls.transcript.parent.mkdir()
        usage = {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 0,
                 "cache_creation_input_tokens": 0}
        rec = {"type": "assistant", "sessionId": cls.sid, "cwd": str(cls.home),
               "timestamp": datetime.now().astimezone().isoformat(),
               "message": {"model": "claude-haiku-4-5", "role": "assistant", "usage": usage,
                           "content": [{"type": "text", "text": "ok"}]}}
        cls.transcript.write_text(json.dumps(rec) + "\n", encoding="utf-8")
        cls.plan = cls.res["AUTOSDD_PLAN_DIR"] / f"autosdd_resume_plan_{cls.sid}.md"

    @classmethod
    def _cleanup(cls) -> None:
        _ps(f"Unregister-ScheduledTask -TaskName '{cls.task}' -Confirm:$false "
            "-ErrorAction SilentlyContinue")
        shutil.rmtree(cls.home, ignore_errors=True)

    @staticmethod
    def _machine_env() -> dict:
        """排程器給 job 的環境：沒有任何 AUTOSDD_*／CLAUDE*。"""
        return {k: v for k, v in os.environ.items() if not k.startswith(("AUTOSDD_", "CLAUDE"))}

    def _case_env(self) -> dict:
        env = self._machine_env()
        env.update({k: str(v) for k, v in self.res.items()})
        env.update({"AUTOSDD_SENTINEL_OFF": "1", "PYTHONDONTWRITEBYTECODE": "1"})
        return env

    def _run(self, argv, env: dict, shell_line: str | None = None):
        return subprocess.run(shell_line or argv, cwd=self.home, env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=180,
                              creationflags=_NOWIN, check=False, stdin=subprocess.DEVNULL)

    def _planner(self, *args: str):
        script = str(self.home / "tools" / "session_resume_planner.py")
        return self._run([_PY, script, *args], self._case_env())

    def _arm(self):
        return self._planner("--arm-sentinel", "--session-id", self.sid, "--transcript",
                             str(self.transcript), "--out", str(self.plan))

    def _lease(self, minutes: int | None, owner_pid: int | None = None) -> None:
        now = datetime.now().astimezone()
        ss.write_identity(self.home, run_id="e2e", sid=self.sid,
                          owner_pid=owner_pid or os.getpid(), now=now)
        if minutes is not None:
            ss.grant(self.home, until=now + timedelta(minutes=minutes), now=now)

    def _task_exists(self) -> bool:
        name = _ps(f"(Get-ScheduledTask -TaskName '{self.task}' "
                   "-ErrorAction SilentlyContinue).TaskName")
        return bool(name)

    def _trace_rows(self) -> list[dict]:
        path = self.res["AUTOSDD_TRACE_DIR"] / "autosdd_session_switch.jsonl"
        if not path.is_file():
            return []
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]

    def test_e2e_s2_01_leaseless_sandbox_cannot_register_a_sentinel(self) -> None:
        self._lease(None)
        res = self._arm()
        self.assertEqual(res.returncode, si.RC_REGISTER_REFUSED, res.stdout[-400:] + res.stderr)
        self.assertIn("sandbox_no_lease", res.stderr)
        self.assertFalse(self._task_exists(), "拒絕登記 ⇒ 排程器裡不得有這支工作")
        self.assertTrue(any(r["event"] == "sideeffect_refused" and r["reason"] == "sandbox_no_lease"
                            for r in self._trace_rows()))

    def test_e2e_s2_02_to_04_register_with_job_env_and_expiry_then_dead_owner_refuses(
        self,
    ) -> None:
        self._lease(20)
        res = self._arm()
        self.assertEqual(res.returncode, 0, res.stdout[-600:] + res.stderr[-600:])
        self.assertIn("NextRunTime", res.stdout)
        # (02) 真排程器的 Action 與 XML：居所＋行為開關、EndBoundary＝租約到期、自刪設定
        action = _ps(f"(Get-ScheduledTask -TaskName '{self.task}').Actions[0].Arguments")
        for key in endurance_env.RESIDENCE_KEYS:
            self.assertIn(f'--job-env "{key}={self.res[key]}"', action, key)
        self.assertIn('--job-env "AUTOSDD_SENTINEL_OFF=1"', action)
        xml = _ps(f"Export-ScheduledTask -TaskName '{self.task}'")
        until = ss.job_expiry(self.home, datetime.now().astimezone())
        self.assertIn(f"<EndBoundary>{until:%Y-%m-%dT%H:%M:%S}", xml)
        self.assertIn("<DeleteExpiredTaskAfter>PT0S</DeleteExpiredTaskAfter>", xml)
        # (03) 到點（排程器登記的真 Action 引數、機器環境不帶 AUTOSDD_*）而主人已死 ⇒ rc 10、自拆
        dead = subprocess.Popen([_PY, "-c", "pass"], creationflags=_NOWIN)
        dead.wait()
        self._lease(20, owner_pid=dead.pid)
        real = Path.home().joinpath(*endurance_env.TRACE_HOME_PARTS)  # 真痕跡目錄（只讀比對）
        before = {p: p.stat().st_size for p in real.glob("*.jsonl")} if real.is_dir() else {}
        tick = self._run(None, self._machine_env(), shell_line=f'"{_PY}" {action}')
        self.assertEqual(tick.returncode, ss.RC_SIDEEFFECT_REFUSED, tick.stdout + tick.stderr)
        self.assertFalse(self._task_exists(), "到點首判拒絕 ⇒ 自拆（既有 disarm 路）")
        rows = [r for r in self._trace_rows() if r["event"] == "sideeffect_refused"]
        self.assertEqual((rows[-1]["reason"], rows[-1]["site"]),
                         ("sandbox_owner_dead", "_sentinel_tick"))
        # (04) 沙盒 sid 沒有洩進真 ~/.autosdd/traces
        after = {p: p.stat().st_size for p in real.glob("*.jsonl")} if real.is_dir() else {}
        leaked = [p.name for p, size in after.items() if size != before.get(p)
                  and self.sid in p.read_text(encoding="utf-8", errors="replace")]
        self.assertEqual(leaked, [], "job 環境轉送生效：沙盒 sid 不得出現在真痕跡")

    def test_e2e_s2_05_probe_verb_refuses_a_real_claude_but_not_an_in_home_fake(self) -> None:
        self._lease(20)
        res = self._planner("--probe-quota")  # `--probe-command` 預設裸名 "claude"
        self.assertEqual(res.returncode, ss.RC_SIDEEFFECT_REFUSED, res.stdout + res.stderr)
        self.assertIn("sandbox_real_exe", res.stderr)
        fake = self.home / "bin" / "fakeclaude.cmd"
        fake.parent.mkdir(exist_ok=True)
        fake.write_text("@echo off\r\necho Hi\r\n", encoding="utf-8")
        res = self._planner("--probe-quota", "--probe-command", str(fake))
        self.assertNotEqual(res.returncode, ss.RC_SIDEEFFECT_REFUSED, res.stdout + res.stderr)
        self.assertIn("quota_open=", res.stdout, "通過首判後進到探測（零成本端點可能先答）")
        refused = [r for r in self._trace_rows()
                   if r["event"] == "sideeffect_refused" and r["site"] == "main:probe_quota"]
        self.assertEqual(len(refused), 1, "只有第一次（裸名 claude）被拒；家內替身不被拒")


if __name__ == "__main__":
    unittest.main()
