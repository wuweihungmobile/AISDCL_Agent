#!/usr/bin/env python3
"""D23（DEF-200-275 第六輪，SD-08）：構造合法 relay 狀態塊＋halt marker fixture，只 mock 排程/告警
副作用（`_register_and_record`／`_resume_tick`），直接呼叫 `_sentinel_tick(args)`，證明 halt 標記到
decision 這段是真的跑過的端到端程式碼，不是分別驗證兩段純函式後靠推論黏起來（既有測試皆止於純函式
邊界，見 DEF200278 證據檔第二輪 §8）。詳見
docs/06_quality/CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第六輪〉。"""
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
import quota_policy  # noqa: E402
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
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory(
            prefix="d23_sentinel_e2e_", ignore_cleanup_errors=True)))
        self.enterContext(unittest.mock.patch.dict(
            os.environ, {"AUTOSDD_TRACE_DIR": str(self.tmp / "traces")}))
        self.enterContext(unittest.mock.patch("tempfile.gettempdir", return_value=str(self.tmp)))
        self.enterContext(unittest.mock.patch.object(  # DEF-200-532：slug 退路隔離、故意≠self.tmp
            planner, "project_transcript_dir", lambda _root: self.tmp / "slug"))

    def _transcript(self, sid: str, mtime: float | None = None) -> Path:
        """`mtime`＝None 用現在；給定值模擬最後活動時刻，供 `halt_verdict()` 判過期。
        DEF-200-560：存活判準是對話記錄的 timestamp（非 mtime）⇒ 記錄 timestamp 與 mtime 同值。"""
        ts = self.tmp / f"{sid}.jsonl"
        at = datetime.fromtimestamp(mtime, UTC) if mtime is not None else datetime.now(UTC)
        ts.write_text(json.dumps({"type": "assistant", "timestamp": at.isoformat(), "message": {
            "model": "claude-opus-5", "usage": {"input_tokens": 10}}}) + "\n", encoding="utf-8")
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
        # 活動（5 秒前）早於標記 at（現在）：標記未過期
        rc, calls, _resumes, now, plan = self._tick(sid, marker_age=0, reset_in=600, idle=5)
        self.assertEqual(rc, 0, "patch 過的 register 回 0，rc 必須原樣傳回")
        self.assertEqual(len(calls), 1,
                         "halt 標記被讀到但沒有真的走到 _register_and_record ⇒ 標記沒被消費")
        called_plan, called_sid, called_at, called_tick = calls[0]
        self.assertEqual(called_plan, plan)
        self.assertEqual(called_sid, sid)
        self.assertEqual(called_tick, planner.SENTINEL_TICK)
        # fire_at = reset_at + HALT_RESET_SKEW_SECONDS（quota_messages 與 planner 兩檔
        # 各自具名同值，DEF-200-278／INV-H2 parity）。
        reset_at = now + timedelta(seconds=600)
        self.assertAlmostEqual(
            (called_at - reset_at).total_seconds(), qg.HALT_RESET_SKEW_SECONDS, delta=1)

    def test_expired_halt_marker_drives_probe_and_delegates_to_resume_tick(self) -> None:
        """reset_at 已過 ⇒ decision=probe ⇒ 必須交棒給既有的 `_resume_tick()`。"""
        # 活動早於兌現時刻、且已靜止 ≥ 一個巡邏間隔（HALT_QUIESCE_SECONDS）⇒ 才 probe。
        rc, _registers, calls, _now, _plan = self._tick(
            "sid-d23-e2e-probe", marker_age=1000, idle=1060,
            reset_in=-(qg.HALT_RESET_SKEW_SECONDS + 60))
        self.assertEqual(rc, 7, "decision=probe 必須交棒給 _resume_tick 且原樣回傳其 rc")
        self.assertEqual(len(calls), 1, "halt 標記已過期卻沒有交棒給 _resume_tick ⇒ 標記沒被消費")

    def _tick(self, sid: str, *, marker_age: int, reset_in: int, idle: int):
        """真 `_sentinel_tick`（只替身 `_register_and_record`／`_resume_tick`）；單位秒。
        回 `(rc, register 呼叫, resume 呼叫, now, plan)`。"""
        now = datetime.now(UTC).astimezone()
        transcript = self._transcript(sid, mtime=now.timestamp() - idle)
        plan = self._write_plan(sid, transcript, f"T-{sid}")
        qg.write_halt_marker(sid, {"sid": sid, "band": "halt", "binding": "session",
                                   "reset_at": (now + timedelta(seconds=reset_in)).isoformat(),
                                   "at": (now - timedelta(seconds=marker_age)).isoformat(),
                                   "transcript": str(transcript), "resolved_source": "payload"})
        self.assertIsNotNone(qg.read_halt_marker(sid), "fixture 本身必須先確認標記寫得進去")
        registers, resumes = [], []
        mock_patch = unittest.mock.patch.object
        with mock_patch(planner, "_register_and_record", lambda p, s, at, tick: (
                registers.append((p, s.get("session_id"), at, tick)), (0, "cred-e2e-stub"))[1]), \
                mock_patch(planner, "_resume_tick", lambda a: resumes.append(a) or 7):
            rc = planner._sentinel_tick(self._args(plan, f"T-{sid}"))
        return rc, registers, resumes, now, plan

    def test_halt_marker_semantics_hold_through_the_real_tick(self) -> None:
        """DEF-200-516（7-E）端到端：收斂活動不讓標記過期；兌現後已續跑或到點仍在動 ⇒ 不叫醒。"""
        interval = planner.SENTINEL_INTERVAL_SECONDS
        for sid, marker_age, reset_in, idle, want_after in (
                ("converged", 600, 600, 585, 600 + qg.HALT_RESET_SKEW_SECONDS),  # ⇒ arm_reset
                ("resumed", 5000, -1000, 100, interval),  # 兌現後仍有活動 ⇒ 照常巡邏
                ("busy", 5000, -500, 600, interval)):  # 到點但 10 分鐘前才動過 ⇒ 延後
            with self.subTest(sid):
                _rc, registers, resumes, now, _plan = self._tick(
                    f"sid-e-{sid}", marker_age=marker_age, reset_in=reset_in, idle=idle)
                self.assertEqual(resumes, [], "不該叫醒（spawn 第二個續跑窗）")
                (_plan, _sid, at, tick), = registers
                self.assertEqual(tick, planner.SENTINEL_TICK)
                self.assertAlmostEqual((at - now).total_seconds(), want_after, delta=2)

    def test_a_superseding_session_disarms_the_real_tick_and_clears_the_marker(self) -> None:
        """DEF-200-532：同專案他 session 標記後累積 ≥24 回合／≥600 s ⇒ 真 tick disarm＋清標記。"""
        sid, t0 = "sid-d532-old", datetime.now(UTC) - timedelta(seconds=4880)
        rows = [{"type": "assistant", "message": {"model": "m"},
                 "timestamp": (t0 + timedelta(seconds=30 * i)).isoformat()} for i in range(30)]
        (self.tmp / "peer-sid.jsonl").write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
        with unittest.mock.patch.object(planner, "_schtasks_remove", return_value=0) as remove:
            rc, regs, wakes, _now, plan = self._tick(sid, marker_age=5000, reset_in=600, idle=5)
        self.assertEqual((rc, regs, wakes, remove.call_args.args), (0, [], [], (f"T-{sid}",)))
        self.assertIsNone(qg.read_halt_marker(sid), "disarm 必須把 halt 標記一併清掉")
        log = planner.endurance_log_path(plan).read_text(encoding="utf-8")
        (done,) = [e for e in map(json.loads, log.splitlines()) if e["event"] == "sentinel_disarm"]
        self.assertTrue(done["cleared_halt"] and "接手" in done["why"], done)

    # ── DEF-200-564（RC-D，2026-10-21 14:02:01 事故）：另一駕駛仍在動 ⇒ 不 probe、不 spawn
    _HIT = "You've hit your session limit · resets 9am (Asia/Taipei)"

    @staticmethod
    def _ago(seconds: float) -> str:
        return (datetime.now(UTC) - timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")

    def _tick_with(self, sid: str, *tail: dict, plans: Path | None = None):
        """事件錨 2026-08-07（reset 早已過⇒原本 probe）＋ tail；回 (rc, 註冊, resume, 末筆決策)。"""
        head = [{"type": "assistant", "timestamp": "2026-08-07T00:30:00Z",
                 "message": {"model": "claude-opus-5", "usage": {"input_tokens": 5}}},
                {"type": "assistant", "timestamp": "2026-08-07T00:44:01.000Z",
                 "message": {"model": guard.SYNTHETIC_MODEL, "content": [{"text": self._HIT}]}}]
        transcript = self.tmp / f"{sid}.jsonl"
        transcript.write_text("\n".join(map(json.dumps, [*head, *tail])) + "\n", encoding="utf-8")
        plan, (registers, resumes) = self._write_plan(sid, transcript, f"T-{sid}"), ([], [])
        if plans is not None:
            plans.mkdir(parents=True, exist_ok=True)
            (plans / plan.name).write_text(plan.read_text(encoding="utf-8"), encoding="utf-8")
            plan = plans / plan.name  # 讀寫複本而非 Path.replace：不新增 Windows 目錄項原語站點
        mock_patch = unittest.mock.patch.object
        with mock_patch(planner, "_register_and_record", lambda p, s, at, tick: (
                registers.append(tick), (0, "cred-e2e-stub"))[1]), \
                mock_patch(planner, "_resume_tick", lambda a: resumes.append(a) or 7):
            rc = planner._sentinel_tick(self._args(plan, f"T-{sid}"))
        rows = [json.loads(ln) for ln in
                planner.endurance_log_path(plan).read_text(encoding="utf-8").splitlines()]
        return rc, registers, resumes, [r for r in rows if r["event"] == "sentinel_decided"][-1]

    def test_a_live_driver_makes_the_real_tick_patrol_and_the_trail_names_them(self) -> None:
        """事故重放：auto-continuation 剛寫、首則回應未落檔 ⇒ 事件已處理；人類剛打字 ⇒ 另一駕駛
        （痕跡記下是誰）。都 patrol 不 probe；DEF-200-566：任務書在暫存只在 `plan_in_temp` 出聲。"""
        auto = {"type": "user", "timestamp": self._ago(25), "isMeta": True,
                "origin": {"kind": "auto-continuation"}}
        human = {"type": "user", "timestamp": self._ago(60), "origin": {"kind": "human"}}
        for sid, rec, kind, plans in (("auto", auto, None, None), ("human", human, "human", None),
                                      ("plans", human, "human", self.tmp / "plans")):
            with self.subTest(sid):
                rc, registers, resumes, row = self._tick_with(f"sid-rcd-{sid}", rec, plans=plans)
                self.assertEqual((rc, resumes, registers), (0, [], [planner.SENTINEL_TICK]))
                self.assertEqual((row["action"], (row["driver_after"] or {}).get("kind"),
                                  row["plan_in_temp"], "另一駕駛" in row["reason"]),
                                 ("patrol", kind, plans is None, kind is not None), row)

    def test_no_live_driver_after_the_event_still_gets_the_old_probe(self) -> None:
        """負控：事件之後只有重試的限額記錄、或戳了死視窗就走（靜止逾一個巡邏間隔）⇒ 照舊 probe。"""
        again = {"type": "assistant", "timestamp": self._ago(30),
                 "message": {"model": guard.SYNTHETIC_MODEL, "content": [{"text": self._HIT}]}}
        stale = {"type": "user", "origin": {"kind": "human"},
                 "timestamp": self._ago(planner.SENTINEL_INTERVAL_SECONDS + 600)}
        for sid, rec in (("limit", again), ("stale", stale)):
            with self.subTest(sid):
                rc, _registers, resumes, row = self._tick_with(f"sid-rcd-{sid}", rec)
                self.assertEqual((rc, len(resumes), row["action"], row["driver_after"]),
                                 (7, 1, "probe", None))


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
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory(
            prefix="def456_manual_e2e_", ignore_cleanup_errors=True)))
        env = {"AUTOSDD_TRACE_DIR": str(self.tmp / "traces"),
               "AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp)}
        self.enterContext(unittest.mock.patch.dict(os.environ, env))
        self.enterContext(unittest.mock.patch("tempfile.gettempdir", return_value=str(self.tmp)))
        self.backend = _FakeBackend()
        self.enterContext(unittest.mock.patch.object(
            planner.schedule_backend, "select", return_value=self.backend))
        # DEF-200-480：本 e2e 驗的是 `--allow-resume` 的**程式預設**（開）。`planner.main()`
        # 先把 repo 根 `.env` 的逃生口填進環境，機器本地若設 AUTOSDD_RESUME_OFF=1，預設就翻成
        # 關 ⇒ 把 `.env` 根指到沒有 `.env` 的臨時目錄，讓測試對機器設定密封（語意不變：真環境
        # 變數仍優先）。上面的 patch.dict 已快照環境，這裡順手清掉行程繼承的同名鍵。
        os.environ.pop(planner.RESUME_OFF_ENV, None)
        real_defaults = planner.quota_gate.apply_env_defaults
        self.enterContext(unittest.mock.patch.object(
            planner.quota_gate, "apply_env_defaults",
            lambda env, root=None: real_defaults(env, root=self.tmp)))
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

    def _events(self) -> list[dict]:
        log = planner.endurance_log_path(self.plan)  # 第一筆痕跡之前檔案還不存在
        text = log.read_text(encoding="utf-8") if log.is_file() else ""
        return [json.loads(line) for line in text.splitlines()]

    def _wake(self, *, band: str, handback: Path | None = None, files_changed: int = 0,
              early_bombs: bool = False) -> tuple[int, str]:
        """真 `_resume_tick`（探針／spawn／band 為替身，其餘收尾與重掛皆真碼；任務書目錄入沙箱）；
        `early_bombs`：探針與 spawn 換成炸彈（早醒不得碰它們）。"""
        args = planner.build_parser().parse_args(
            ["--resume-tick", "--plan", str(self.plan), "--task-name", self.task])
        verdict = {"open": True, "kind": guard.LIMIT_NONE, "rc": 0, "text": "", "source": "stub"}
        bomb = AssertionError("早醒不得探測、不得 spawn")

        def _spawn(_args, state, _log):
            state.update(handback_verdict="written", handback_path=str(handback),
                         files_changed=files_changed, route_strategy=planner.STRATEGY_RESUME)
            return 0

        err = io.StringIO()
        with unittest.mock.patch.dict(os.environ, {"AUTOSDD_PLAN_DIR": str(self.tmp / "plans")}), \
                unittest.mock.patch.object(
                    planner, "probe_quota", side_effect=bomb if early_bombs else None,
                    return_value=verdict), \
                unittest.mock.patch.object(
                    planner, "_run_resume", side_effect=bomb if early_bombs else _spawn), \
                unittest.mock.patch.object(planner.relay_machine, "current_band",
                                           lambda *_a, **_k: band), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertTrue(planner.endurance_env.plan_dir().is_relative_to(self.tmp),
                            "任務書目錄沒有隔離 ⇒ 真 gc_plans 會掃到真家目錄")
            return planner._resume_tick(args), err.getvalue()

    def test_an_early_wake_waits_for_the_reset_instead_of_probing_or_spawning(self) -> None:
        """DEF-200-516 端到端：真註冊後立刻醒（reset 在 2 小時後）：不得探測／spawn，須重掛。"""
        fire = datetime.now(UTC).astimezone() + timedelta(hours=2)
        with unittest.mock.patch.object(
                planner.session_brief, "schtasks_trigger",
                return_value=(f"'{fire:%Y-%m-%d %H:%M:%S}'", fire, "")):
            rc, _out, err = self._run("--register-schtasks")
        self.assertEqual(rc, 0, err)
        registered = self._block()
        seen = len(self._events())
        woke_rc, woke_err = self._wake(band=quota_policy.BAND_FREE, early_bombs=True)
        self.assertEqual(woke_rc, 0, woke_err)
        self.assertEqual([e["event"] for e in self._events()[seen:]],
                         ["woken", "resume_tick_early"])
        armed = self.backend.armed()
        self.assertEqual(len(armed), 2, f"早醒沒有恰一次重掛：{armed}")
        _, task, at_expr, at = armed[1]
        self.assertEqual(task, self.task)
        self.assertEqual(at_expr, f"'{fire:%Y-%m-%d %H:%M:%S}'")
        self.assertLess(abs((at - fire).total_seconds()), 1, "重掛的時刻不是原本的 reset＋skew")
        after = self._block()
        self.assertEqual((after["state"], after["reset_at"]), ("armed", registered["reset_at"]))

    def _settle_stop(self, *, next_step: str, files_changed: int, band: str) -> list[dict]:
        """DEF-200-516 順帶發現 7-B 的共同前置：真註冊 → 真醒 → 真收尾（含真 alert 與真重掛）。"""
        rc, _out, err = self._run("--register-schtasks", "--at", _AT)
        self.assertEqual(rc, 0, err)
        hb = self.tmp / "handback.md"
        hb.write_text("## 做了什麼\n測試\n\n## 驗了什麼（附實測 rc）\nrc=0\n\n## 卡在哪\n無\n\n"
                      f"## 下一步指令\n{next_step}\n", encoding="utf-8", newline="\n")
        woke_rc, woke_err = self._wake(band=band, handback=hb, files_changed=files_changed)
        self.assertEqual(woke_rc, 0, woke_err)
        return self._events()

    def _assert_settled_cleanly(self, events: list[dict], stop_event: str) -> None:
        names = [e["event"] for e in events]
        self.assertNotIn("relay_settle_crashed", names, f"收尾假崩潰：{events}")
        self.assertIn(stop_event, names)
        self.assertFalse(planner.escalation.note_path().exists(),
                         "正常收尾竟然寫了『需要你動手』的紙條（假崩潰叫人）")
        self.assertTrue(self.plan.is_file(),
                        "任務書在重掛哨兵前就被收掉 ⇒ 哨兵沒有地板（`arm` 拒絕註冊不存在的任務書）")
        self.assertEqual([c[1] for c in self.backend.armed()],
                         [self.task, planner.sentinel_task_name(self.sid)],
                         "收尾後沒有把哨兵重掛起來")
        self.assertEqual([e["rc"] for e in events if e["event"] == "relay_rearmed"], [0])
        state = self._block()
        self.assertEqual((state["kind"], planner.relay_problems(state)), ("sentinel", []))

    def test_a_done_window_settles_without_crashing_and_keeps_the_plan_for_the_sentinel(
            self) -> None:
        """DEF-200-516 順帶發現 7-B（DONE 路）：非 loud 的 `alert(plan=plan)` 會 GC 任務書，隨後的
        `write_relay` ⇒ FileNotFoundError ⇒ 假崩潰叫人，哨兵也註冊不了。既有測試把 `alert` 換成
        不 GC 的替身所以看不見；這裡 alert 是真的。"""
        events = self._settle_stop(next_step="", files_changed=0, band=quota_policy.BAND_FREE)
        self._assert_settled_cleanly(events, "relay_done")

    def test_a_quota_stop_window_settles_without_crashing_and_keeps_the_plan_for_the_sentinel(
            self) -> None:
        """同上（QUOTA_STOP 路）：有未完項、有進度、band 收緊 ⇒ 交回哨兵巡邏——非 loud，同一個病。"""
        events = self._settle_stop(next_step="1. 還有第 4 步", files_changed=2,
                                   band=quota_policy.BAND_HALT)
        self._assert_settled_cleanly(events, "relay_stopped")
        self.assertEqual([e["why"] for e in events if e["event"] == "relay_stopped"], ["band"])

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
