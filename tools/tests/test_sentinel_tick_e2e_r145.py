#!/usr/bin/env python3
"""D23（DEF-200-275 第六輪，SD-08）：構造合法 relay 狀態塊＋halt marker fixture，只
mock 排程/告警副作用（`_register_and_record`／`_resume_tick`），直接呼叫
`_sentinel_tick(args)`，證明 halt 標記到 decision 這段是真的跑過的端到端程式碼，
不是分別驗證兩段純函式後靠推論黏起來（既有測試皆止於純函式邊界，見 DEF200278
證據檔第二輪 §8）。詳見 docs/06_quality/
CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第六輪〉。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import context_budget_guard as guard  # noqa: E402
import quota_gate as qg  # noqa: E402
import sentinel_lifecycle as SL  # noqa: E402

import session_resume_planner as planner  # noqa: E402

_MODULE_FENCES: list[dict] = []  # DEF-200-446：模組級圍籬 handle 堆疊（後進先出）


def setUpModule() -> None:  # DEF-200-446：單模組直跑也不得碰真實 TEMP／快取／痕跡目錄
    _MODULE_FENCES.append(SL.fence_enter())


def tearDownModule() -> None:
    SL.fence_exit(_MODULE_FENCES.pop())

os.environ[guard.SENTINEL_OFF_ENV] = "1"  # 本檔全程不准碰真排程器（同既有測試慣例）


class SentinelTickConsumesHaltMarkerE2ETest(unittest.TestCase):
    """真的呼叫 `_sentinel_tick(args)`（不 mock 判定層），只 mock 排程/告警副作用。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="d23_sentinel_e2e_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        old_trace = os.environ.get("AUTOSDD_TRACE_DIR")
        os.environ["AUTOSDD_TRACE_DIR"] = str(self.tmp / "traces")
        self.addCleanup(lambda: (os.environ.__setitem__("AUTOSDD_TRACE_DIR", old_trace)
                                 if old_trace is not None
                                 else os.environ.pop("AUTOSDD_TRACE_DIR", None)))
        self.gettempdir_patch = unittest.mock.patch(
            "tempfile.gettempdir", return_value=str(self.tmp))
        self.gettempdir_patch.start()
        self.addCleanup(self.gettempdir_patch.stop)

    def _transcript(self, sid: str, mtime: float | None = None) -> Path:
        """`mtime`＝None 用現在；給定值模擬最後活動時刻，供 `halt_verdict()` 判過期。"""
        ts = self.tmp / f"{sid}.jsonl"
        ts.write_text('{"type":"assistant","message":{"model":"claude-opus-5",'
                      '"usage":{"input_tokens":10}}}\n', encoding="utf-8")
        if mtime is not None:
            os.utime(ts, (mtime, mtime))
        return ts

    def _write_plan(self, sid: str, transcript: Path, task: str) -> Path:
        """合法 relay 狀態塊（`relay_problems()` 必須回空清單，否則測到自癒分支）。"""
        plan = self.tmp / f"plan-{sid}.md"
        state = {
            "schema": planner.RELAY_SCHEMA, "session_id": sid, "plan_path": str(plan),
            "state": "patrolling", "kind": "sentinel", "reset_at": "",
            "reset_source": "operator", "attempts": 0,
            "max_attempts": planner.MAX_PROBE_ATTEMPTS, "allow_resume": True,
            "task_name": task, "carrier": "test",
            "log_path": str(planner.endurance_log_path(plan)),
            "transcript": str(transcript),
        }
        self.assertEqual(planner.relay_problems(state), [], "fixture 本身必須是健康的狀態塊")
        plan.write_text("# D23 e2e 任務書\n\n" + planner.render_relay(state), encoding="utf-8")
        return plan

    def _args(self, plan: Path, task: str):
        return planner.build_parser().parse_args(
            ["--sentinel-tick", "--plan", str(plan), "--task-name", task])

    def test_unexpired_halt_marker_drives_arm_reset_and_reaches_register(self) -> None:
        """reset_at 尚未到 ⇒ decision=arm_reset ⇒ 必須真的走到 `_register_and_record()`。"""
        sid = "sid-d23-e2e-armreset"
        transcript = self._transcript(sid, mtime=datetime.now(UTC).timestamp() - 5)  # 活動早於 at
        plan = self._write_plan(sid, transcript, "T-r145-armreset")
        now = datetime.now(UTC).astimezone()
        reset_at = now + timedelta(seconds=600)
        qg.write_halt_marker(sid, {"sid": sid, "band": "halt", "binding": "session",
                                   "reset_at": reset_at.isoformat(),
                                   "at": now.isoformat(), "transcript": str(transcript),
                                   "resolved_source": "payload"})
        self.assertIsNotNone(qg.read_halt_marker(sid), "fixture 本身必須先確認標記寫得進去")

        calls: list[tuple] = []

        def _fake_register(plan_arg, state_arg, at_arg, tick_arg):
            calls.append((plan_arg, state_arg.get("session_id"), at_arg, tick_arg))
            return 0, "cred-e2e-stub"

        with unittest.mock.patch.object(planner, "_register_and_record", _fake_register):
            rc = planner._sentinel_tick(self._args(plan, "T-r145-armreset"))

        self.assertEqual(rc, 0, "patch 過的 register 回 0，rc 必須原樣傳回")
        self.assertEqual(len(calls), 1,
                         "halt 標記被讀到但沒有真的走到 _register_and_record ⇒ 標記沒被消費")
        called_plan, called_sid, called_at, called_tick = calls[0]
        self.assertEqual(called_plan, plan)
        self.assertEqual(called_sid, sid)
        self.assertEqual(called_tick, planner.SENTINEL_TICK)
        # fire_at = reset_at + HALT_RESET_SKEW_SECONDS（quota_messages 與 planner 兩檔
        # 各自具名同值，DEF-200-278／INV-H2 parity）。
        self.assertAlmostEqual(
            (called_at - reset_at).total_seconds(), qg.HALT_RESET_SKEW_SECONDS, delta=1)

    def test_expired_halt_marker_drives_probe_and_delegates_to_resume_tick(self) -> None:
        """reset_at 已過 ⇒ decision=probe ⇒ 必須交棒給既有的 `_resume_tick()`。"""
        sid = "sid-d23-e2e-probe"
        now = datetime.now(UTC).astimezone()
        marker_at = now - timedelta(seconds=700)
        # 活動落在 marker_at 之前＝halt 後未續跑過，否則會判成已自行續跑。
        transcript = self._transcript(sid, mtime=(marker_at - timedelta(seconds=60)).timestamp())
        plan = self._write_plan(sid, transcript, "T-r145-probe")
        reset_at = now - timedelta(seconds=qg.HALT_RESET_SKEW_SECONDS + 60)
        qg.write_halt_marker(sid, {"sid": sid, "band": "halt", "binding": "session",
                                   "reset_at": reset_at.isoformat(),
                                   "at": marker_at.isoformat(),
                                   "transcript": str(transcript),
                                   "resolved_source": "payload"})

        calls: list = []

        def _fake_resume_tick(args_arg):
            calls.append(args_arg)
            return 7  # 一個既有分支都不會回的哨兵值，證明真的是這支被叫到

        with unittest.mock.patch.object(planner, "_resume_tick", _fake_resume_tick):
            rc = planner._sentinel_tick(self._args(plan, "T-r145-probe"))

        self.assertEqual(rc, 7, "decision=probe 必須交棒給 _resume_tick 且原樣回傳其 rc")
        self.assertEqual(len(calls), 1,
                         "halt 標記已過期卻沒有交棒給 _resume_tick ⇒ 標記沒被消費")


_AT = "'2099-01-01 00:00:00'"  # 顯式 --at：避開額度快取（全程不碰網路）


class _FakeBackend:
    """只記錄、不碰排程器的後端替身：`arm`／`disarm` 的呼叫都進 `calls`。"""

    name, credential_key = "fake", "next_run_time"

    def __init__(self, jobs: list[str] | None = None) -> None:
        self.jobs, self.calls = list(jobs or []), []

    def list_jobs(self, prefix: str) -> list[str]:
        return [job for job in self.jobs if job.startswith(prefix)]

    def arm(self, plan_path, task_name, at_expr, tick, at=None):  # noqa: ARG002
        self.calls.append(("arm", task_name, at_expr, at))
        return 0, "FAKE-CRED"

    def disarm(self, task_name: str) -> int:
        self.calls.append(("disarm", task_name))
        return 0

    def credential_line(self, moment: str) -> str:
        return f"credential={moment}"

    def armed(self) -> list[tuple]:
        return [call for call in self.calls if call[0] == "arm"]


class ManualRegisterThenWakeE2ETest(unittest.TestCase):
    """DEF-200-456：手動 `--register-schtasks` 註冊的排程，醒來必須有狀態塊可讀。
    修前它不寫任何狀態塊 ⇒ 醒來 `_resume_tick` 一律「沒有狀態塊 ⇒ 拒絕動作」並自我解除，
    使用者卻只看到「✅ 憑證」。只替身排程器（`select`）與付費探針，其餘全走真碼。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="def456_manual_e2e_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        env = {"AUTOSDD_TRACE_DIR": str(self.tmp / "traces"),
               "AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp)}
        for patcher in (unittest.mock.patch.dict(os.environ, env),
                        unittest.mock.patch("tempfile.gettempdir", return_value=str(self.tmp))):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.backend = _FakeBackend()
        select = unittest.mock.patch.object(
            planner.schedule_backend, "select", return_value=self.backend)
        select.start()
        self.addCleanup(select.stop)
        # DEF-200-480：本 e2e 驗的是 `--allow-resume` 的**程式預設**（開）。`planner.main()`
        # 先把 repo 根 `.env` 的逃生口填進環境，機器本地若設 AUTOSDD_RESUME_OFF=1，預設就翻成
        # 關 ⇒ 把 `.env` 根指到沒有 `.env` 的臨時目錄，讓測試對機器設定密封（語意不變：真環境
        # 變數仍優先）。上面的 patch.dict 已快照環境，這裡順手清掉行程繼承的同名鍵。
        os.environ.pop(planner.RESUME_OFF_ENV, None)
        real_defaults = planner.quota_gate.apply_env_defaults
        dotenv = unittest.mock.patch.object(
            planner.quota_gate, "apply_env_defaults",
            lambda env, root=None: real_defaults(env, root=self.tmp))
        dotenv.start()
        self.addCleanup(dotenv.stop)
        self.sid = "sidManualE2E"
        self.transcript = self.tmp / f"{self.sid}.jsonl"
        self.transcript.write_text('{"type":"assistant","message":{"model":"claude-opus-5",'
                                   '"usage":{"input_tokens":10}}}\n', encoding="utf-8")
        self.plan = self.tmp / "plan.md"
        self.task = planner.resume_task_name(self.sid, planner.DEFAULT_TASK_NAME)

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        full = ["--transcript", str(self.transcript), "--out", str(self.plan), *argv]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = planner.main(full)
        return rc, out.getvalue(), err.getvalue()

    def _block(self) -> dict | None:
        return planner.parse_relay(self.plan.read_text(encoding="utf-8"))

    def test_manual_register_leaves_a_healthy_relay_block(self) -> None:
        rc, out, err = self._run("--register-schtasks", "--at", _AT)
        self.assertEqual(rc, 0, err)
        self.assertIn("會自動續跑", out, "醒來預設會真的續跑，註冊當下必須讓人看見")
        state = self._block()
        self.assertIsNotNone(state, "手動註冊後任務書沒有狀態塊 ⇒ 醒來必拒絕動作（DEF-200-456）")
        self.assertEqual(planner.relay_problems(state), [])
        self.assertEqual(
            (state["session_id"], state["task_name"], state["plan_path"], state["state"]),
            (self.sid, self.task, str(self.plan), "armed"))
        self.assertEqual(state[self.backend.credential_key], "FAKE-CRED")

    def test_the_woken_job_acts_instead_of_aborting(self) -> None:
        """接著跑真的 `_resume_tick`（探針替身＝額度已回來）。醒來那一跑讀的是狀態塊裡的
        `allow_resume`（武裝當下寫入）⇒ 以 `--no-allow-resume` 武裝才不會真 spawn `claude`；
        另以炸彈替身擋住 `_run_resume`，萬一該旗標漏寫，測試紅而不是真續跑。"""
        rc, out, err = self._run("--register-schtasks", "--at", _AT, "--no-allow-resume")
        self.assertEqual(rc, 0, err)
        self.assertIn("只探測＋留痕", out)
        args = planner.build_parser().parse_args(
            ["--resume-tick", "--plan", str(self.plan), "--task-name", self.task])
        verdict = {"open": True, "kind": guard.LIMIT_NONE, "rc": 0, "text": "", "source": "stub"}
        woke_err = io.StringIO()
        bomb = AssertionError("測試不得真的續跑（會 spawn 真的 claude）")
        with unittest.mock.patch.object(planner, "probe_quota", return_value=verdict), \
                unittest.mock.patch.object(planner, "_run_resume", side_effect=bomb), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(woke_err):
            woke_rc = planner._resume_tick(args)
        log = planner.endurance_log_path(self.plan).read_text(encoding="utf-8")
        events = [json.loads(line)["event"] for line in log.splitlines()]
        self.assertEqual(woke_rc, 0, woke_err.getvalue())
        self.assertNotIn("aborted", events)
        self.assertIn("probed", events)
        self.assertIn("quota_back_no_resume", events)
        self.assertNotIn("沒有狀態塊", woke_err.getvalue())

    def test_explicit_and_observed_at_write_distinct_honest_sources(self) -> None:
        """L0（操作者宣稱）與 L1（端點實測）各用自己的字面，不借 `operator`／
        `transcript-verbatim`（ADR-XPLAT-014 約束 2／3）。"""
        self._run("--register-schtasks", "--at", _AT)
        explicit = self._block()
        self.assertEqual((explicit["reset_source"], explicit["reset_at"]),
                         ("operator-asserted", ""))
        fire = datetime.now(UTC).astimezone() + timedelta(hours=2)
        trigger = (f"'{fire:%Y-%m-%d %H:%M:%S}'", fire, "")
        with unittest.mock.patch.object(planner.session_brief, "schtasks_trigger",
                                        return_value=trigger):
            rc, _out, err = self._run("--register-schtasks")
        self.assertEqual(rc, 0, err)
        observed = self._block()
        self.assertEqual(observed["reset_source"], "endpoint-authoritative")
        self.assertEqual(observed["reset_at"],
                         (fire - timedelta(seconds=planner.RESET_SKEW_SECONDS)).isoformat())

    def test_inv5_conflict_returns_0_and_writes_no_block(self) -> None:
        self.backend.jobs.append("AutoSDD_Sentinel_" + self.sid)
        rc, _out, err = self._run("--register-schtasks", "--at", _AT)
        self.assertEqual(rc, 0, err)
        self.assertEqual(self.backend.armed(), [])
        self.assertIsNone(self._block())

    def test_print_only_never_writes_a_relay_block(self) -> None:
        """對照組：只印不註冊的路徑零修改——不得寫「armed」狀態塊、不得碰排程器。"""
        rc, out, err = self._run("--print-schtasks-command", "--at", _AT)
        self.assertEqual(rc, 0, err)
        self.assertIn("Register-ScheduledTask", out, "沒印出腳本 ⇒ 本測試沒走到 print 路徑")
        self.assertIsNone(self._block())
        self.assertEqual(self.backend.calls, [])

    def test_an_empty_at_is_refused(self) -> None:
        """`--at ""` 不是時刻：照單全收會把它記成「操作者宣稱的 reset」，而宣稱的是空的。"""
        rc, _out, err = self._run("--register-schtasks", "--at", "")
        self.assertEqual(rc, 1, err)
        self.assertEqual(self.backend.armed(), [])
        self.assertIn("--at", err)


if __name__ == "__main__":
    unittest.main()
