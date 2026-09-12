#!/usr/bin/env python3
"""D23（DEF-200-275 第六輪，SD-08）：構造合法 relay 狀態塊＋halt marker fixture，只
mock 排程/告警副作用（`_register_and_record`／`_resume_tick`），直接呼叫
`_sentinel_tick(args)`，證明 halt 標記到 decision 這段是真的跑過的端到端程式碼，
不是分別驗證兩段純函式後靠推論黏起來（既有測試皆止於純函式邊界，見 DEF200278
證據檔第二輪 §8）。詳見 docs/06_quality/
CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第六輪〉。
"""
from __future__ import annotations

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

import session_resume_planner as planner  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
