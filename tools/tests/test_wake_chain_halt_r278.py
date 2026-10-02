#!/usr/bin/env python3
"""DEF-200-278（喚醒鏈缺口第四輪）：halt 交棒 ＋ 哨兵認得自願停機的回歸鎖。

事故沿革（2026-09-10 損失 ≈3h50m 的直接成因）全文搬至
CrossPlatform_R151_Guard_Prose_Migration.md〈test_wake_chain_halt_r278.py 模組 docstring〉節。

本檔釘住的兩件事（各自紅→綠）：
  INV-H1：`quota_gate.resolve_halt_transcript()` 在 payload 缺席時以
          `CLAUDE_CODE_SESSION_ID`＋`project_transcript_dir()` 還原；
          `quota_gate.quota_halt_actions()` 落一份持久 halt 標記，且「未武裝」訊息
          不再對所有成因都印同一句話。
  INV-H2：`session_resume_planner.sentinel_decide()` 認得 halt 標記，未過期時
          `arm_reset`／已過期時 `probe`；標記過期（session 已自行續跑）不再誤觸。
"""
from __future__ import annotations

import contextlib
import inspect
import io
import json
import os
import re
import sys
import unittest
import unittest.mock
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

import importlib.util as _ilu  # noqa: E402

import context_budget_guard as guard  # noqa: E402
import platform_utils  # noqa: E402
import quota_gate as qg  # noqa: E402
import quota_messages  # noqa: E402
import quota_policy  # noqa: E402
import schedule_backend as sb  # noqa: E402
import sentinel_lifecycle  # noqa: E402  # DEF-200-446：模組級圍籬原語
import session_brief  # noqa: E402  # DEF-200-231：觸發時刻解析／`--check` FSM 行

import session_resume_planner as planner  # noqa: E402


def _load_claim_guard():
    """同 `test_claim_provenance_r86.py` 的既有慣例：以檔案路徑載入，不經 import 機制。"""
    hook = _REPO_ROOT / ".claude" / "hooks" / "check_claim_provenance.py"
    spec = _ilu.spec_from_file_location("_claim_guard_r278", hook)
    module = _ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

os.environ[guard.SENTINEL_OFF_ENV] = "1"  # 本檔全程不准碰真排程器（同既有測試慣例）

#: `setUpModule` 進來之前 `ENV_SPEC` 各鍵（`SENTINEL_OFF_ENV` 除外）的值，只捕捉一次。
_ENV_SPEC_ORIGINALS: dict[str, str | None] = {}
_ENV_SPEC_CAPTURED = False
_MODULE_FENCES: list[dict] = []  # DEF-200-446：模組級圍籬 handle 堆疊（後進先出）


def _pin_env_spec_off() -> None:
    """摘掉 `quota_policy.ENV_SPEC` 除 `guard.SENTINEL_OFF_ENV` 外的每一鍵（冪等）。

    DEF-200-354：ENV_SPEC 洩漏會讓 `quota_gate()` 提前 `return 0`，四支 HaltLatch／
    PrepareLatch 斷言落空；同模式見 `test_context_budget_guard.py._pin_sentinel_off`
    （pin 從 ENV_SPEC 導出，不手抄）。
    """
    for spec in quota_policy.ENV_SPEC:
        if spec.name != guard.SENTINEL_OFF_ENV:
            os.environ.pop(spec.name, None)


def _unpin_env_spec_off() -> None:
    """還原成 `setUpModule` 進來前的值（冪等）。"""
    for name, original in _ENV_SPEC_ORIGINALS.items():
        os.environ.pop(name, None)
        if original is not None:
            os.environ[name] = original


def setUpModule() -> None:  # noqa: N802 — unittest 的固定名稱
    global _ENV_SPEC_ORIGINALS, _ENV_SPEC_CAPTURED
    if not _ENV_SPEC_CAPTURED:
        _ENV_SPEC_ORIGINALS = {spec.name: os.environ.get(spec.name)
                               for spec in quota_policy.ENV_SPEC
                               if spec.name != guard.SENTINEL_OFF_ENV}
        _ENV_SPEC_CAPTURED = True
    _pin_env_spec_off()
    unittest.addModuleCleanup(_unpin_env_spec_off)
    _MODULE_FENCES.append(sentinel_lifecycle.fence_enter())  # DEF-200-446：直跑也不碰真實 TEMP


def tearDownModule() -> None:
    sentinel_lifecycle.fence_exit(_MODULE_FENCES.pop())


def _decision(pct: float, resets_in: float | None) -> quota_policy.Decision:
    now = datetime.now(UTC).astimezone()
    reset = None if resets_in is None else (now + timedelta(seconds=resets_in)).isoformat()
    state = quota_policy.QuotaState((quota_policy.Axis("session", pct, reset),),
                                    now.isoformat(), "test")
    policy, problems = quota_policy.load_policy({})
    assert not problems, problems
    return quota_policy.decide(state, now, policy)


class ResolveHaltTranscriptTest(unittest.TestCase):
    """INV-H1a：payload 缺 `transcript_path` 時，用環境變數＋slug 還原。"""

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="def278_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def test_payload_present_and_readable_wins(self) -> None:
        ts = self.tmp / "a.jsonl"
        ts.write_text('{"type":"assistant"}\n', encoding="utf-8")
        cand, source = qg.resolve_halt_transcript({"transcript_path": str(ts)})
        self.assertEqual((cand, source), (ts, "payload"))

    def test_missing_payload_falls_back_to_env_derived_slug(self) -> None:
        """RC-1 直接修復（紅端：修前 `quota_gate` 沒有這支函式）。DEF-200-427：逐字稿目錄經
        `claude_home()` 解析且 `CLAUDE_CONFIG_DIR` 指到暫存樹，測試不碰真實家目錄。"""
        # root 只用來算 slug、不必存在；刻意取短——slug 取自 root 全路徑，若用 tmp 底下的路徑，
        # 目錄樹長度會是 TEMP 長度的兩倍，在長 TEMP 的 Windows 上撞 MAX_PATH。
        root = Path(os.sep) / "proj-def278"
        import re
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(root))
        patcher = unittest.mock.patch.dict(os.environ, {
            "CLAUDE_CONFIG_DIR": str(self.tmp / "cfg"),
            "CLAUDE_CODE_SESSION_ID": "sid-def278", "CLAUDE_PROJECT_DIR": str(root)})
        patcher.start()
        self.addCleanup(patcher.stop)
        proj = platform_utils.claude_home() / "projects" / slug
        self.assertTrue(proj.is_relative_to(self.tmp), f"{proj} 不在暫存樹內＝碰到真實家目錄")
        proj.mkdir(parents=True)
        (proj / "sid-def278.jsonl").write_text("{}\n", encoding="utf-8")
        cand, source = qg.resolve_halt_transcript({})
        self.assertEqual(source, "env-derived")
        self.assertEqual(cand, proj / "sid-def278.jsonl")

    def test_nothing_resolvable_says_so_honestly(self) -> None:
        old_env = dict(os.environ)
        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old_env)))
        cand, source = qg.resolve_halt_transcript({})
        self.assertEqual((cand, source), (None, "unavailable"))


class HaltMarkerRoundTripTest(unittest.TestCase):
    """INV-H1c：落盤標記走 `endurance_env.trace_dir()` 這個 SSOT，讀寫成對。"""

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="def278_trace_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        old = os.environ.get("AUTOSDD_TRACE_DIR")
        os.environ["AUTOSDD_TRACE_DIR"] = str(self.tmp)
        self.addCleanup(lambda: (os.environ.__setitem__("AUTOSDD_TRACE_DIR", old)
                                 if old is not None else os.environ.pop("AUTOSDD_TRACE_DIR", None)))

    def test_written_marker_reads_back_verbatim(self) -> None:
        qg.write_halt_marker("sid-x", {"sid": "sid-x", "band": "halt",
                                      "reset_at": "2099-01-01T00:00:00+00:00"})
        back = qg.read_halt_marker("sid-x")
        self.assertEqual(back["band"], "halt")
        self.assertTrue((self.tmp / "halt_sid-x.json").is_file())

    def test_unknown_sid_reads_back_none(self) -> None:
        self.assertIsNone(qg.read_halt_marker("no-such-sid"))


class QuotaHaltActionsWritesMarkerAndNamesTheRealReasonTest(unittest.TestCase):
    """INV-H1b/c/e：halt 副作用要真的留下標記，且「未武裝」訊息要區分成因。"""

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="def278_act_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        old = os.environ.get("AUTOSDD_TRACE_DIR")
        os.environ["AUTOSDD_TRACE_DIR"] = str(self.tmp)
        self.addCleanup(lambda: (os.environ.__setitem__("AUTOSDD_TRACE_DIR", old)
                                 if old is not None else os.environ.pop("AUTOSDD_TRACE_DIR", None)))

    def test_no_transcript_anywhere_writes_marker_and_names_the_cause(self) -> None:
        """紅端＝本場在未修碼上實跑重現的那個現場（見 repro_rc1.py）：
        修前 `act["plan"]==""`、訊息硬印「拿不到逐字稿路徑」，且**沒有任何持久標記**。
        修後：標記落盤，且 `not_armed_reason` 存在並提到「不可得」。
        """
        old_env = dict(os.environ)
        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old_env)))
        decision = _decision(96.0, 600.0)
        now = datetime.now(UTC).astimezone()
        act = qg.quota_halt_actions({"hook_event_name": "PostToolUse", "tool_name": "Read"},
                                    decision, now,
                                    plan_writer=guard.write_resume_plan,
                                    waker=guard.arm_quota_wakeup)
        self.assertFalse(act["armed"])
        self.assertIsNotNone(act.get("not_armed_reason"))
        self.assertIn("不可得", act["not_armed_reason"])
        markers = list(self.tmp.glob("halt_*.json"))
        self.assertTrue(markers, "halt 標記沒有落盤 ⇒ 哨兵下一輪巡邏無從得知該轉續航")
        data = json.loads(markers[0].read_text(encoding="utf-8"))
        self.assertEqual(data["band"], "halt")
        self.assertTrue(data["reset_at"])

    def test_plan_writer_failure_gets_its_own_reason_not_a_generic_one(self) -> None:
        """情境二（見 repro_rc1.py 的第二次重現）：逐字稿明明存在，是 `plan_writer`
        本身失敗——修前這裡也印「拿不到逐字稿路徑」（假話），修後訊息要點名真因。
        """
        ts = self.tmp / "real.jsonl"
        ts.write_text('{"type":"assistant"}\n', encoding="utf-8")
        decision = _decision(96.0, 600.0)
        now = datetime.now(UTC).astimezone()
        act = qg.quota_halt_actions(
            {"hook_event_name": "PostToolUse", "tool_name": "Read",
             "transcript_path": str(ts)},
            decision, now, plan_writer=lambda t: "", waker=guard.arm_quota_wakeup)
        self.assertIsNotNone(act.get("not_armed_reason"))
        self.assertNotIn("不可得", act["not_armed_reason"],
                         "逐字稿明明存在，訊息卻仍宣稱路徑不可得 ⇒ 成因被誤植")


class HaltVerdictTest(unittest.TestCase):
    """INV-H2 判讀本體：`quota_gate.halt_verdict()`，純函式、四分支。"""

    def _now(self) -> datetime:
        return datetime.now(UTC).astimezone()

    def test_no_marker_defers_to_caller(self) -> None:
        self.assertIsNone(qg.halt_verdict(None, 10.0, self._now()))

    def test_future_reset_arms_at_reset_plus_skew(self) -> None:
        now = self._now()
        reset_at = now + timedelta(seconds=600)
        marker = {"at": now.isoformat(), "reset_at": reset_at.isoformat()}
        verdict = qg.halt_verdict(marker, 10.0, now)
        self.assertEqual(verdict["action"], "arm_reset")
        self.assertEqual((verdict["at"] - reset_at).total_seconds(), qg.HALT_RESET_SKEW_SECONDS)

    def test_passed_reset_probes_instead_of_patrolling(self) -> None:
        """idle 與 marker 的 `at` 一致（無活動）——不是「已續跑」那一支。
        `reset_at` 必須比 `HALT_RESET_SKEW_SECONDS` 更早，否則 `reset_at+skew`
        仍落在未來，那是 `arm_reset` 的合法轄區，不是本測試要驗的分支。"""
        now = self._now()
        reset_at = now - timedelta(seconds=qg.HALT_RESET_SKEW_SECONDS + 60)
        marker = {"at": (now - timedelta(seconds=700)).isoformat(),
                  "reset_at": reset_at.isoformat()}
        verdict = qg.halt_verdict(marker, 700.0, now)
        self.assertEqual(verdict["action"], "probe")

    def test_unparseable_reset_escalates_rather_than_guessing(self) -> None:
        now = self._now()
        marker = {"at": now.isoformat(), "reset_at": "not-a-timestamp"}
        verdict = qg.halt_verdict(marker, 10.0, now)
        self.assertEqual(verdict["action"], "escalate")

    def test_activity_after_the_marker_means_it_is_stale(self) -> None:
        """關鍵防呆：session 自己續跑過（最新活動晚於標記時刻）⇒ 標記過期，
        不得讓哨兵永遠卡在 probe（那是本輪要修的無做工空轉的鏡像新形態）。"""
        now = self._now()
        marker_at = now - timedelta(seconds=1000)
        marker = {"at": marker_at.isoformat(),
                  "reset_at": (marker_at + timedelta(seconds=60)).isoformat()}
        idle_seconds = 5.0  # 最新活動＝now-5s，遠晚於 marker_at
        self.assertIsNone(qg.halt_verdict(marker, idle_seconds, now))

    def test_activity_within_the_skew_tolerance_still_arms(self) -> None:
        """DEF-200-274 第十輪／SA-04 回歸鎖：改前必紅（零容忍嚴格比較會把這個
        20ms 的時序雜訊誤判成「已續跑」而回 `None`），改後必綠。活動只比標記晚
        0.02 秒——遠小於 `HALT_MARKER_ACTIVITY_SKEW_SECONDS`——是 hook 落盤與
        逐字稿 append 之間天生會有的落差，不是真的續跑過。"""
        now = self._now()
        marker_at = now - timedelta(seconds=600)
        reset_at = now + timedelta(seconds=600)
        marker = {"at": marker_at.isoformat(), "reset_at": reset_at.isoformat()}
        idle_seconds = 600 - 0.02  # 最新活動＝marker_at 之後 0.02s
        verdict = qg.halt_verdict(marker, idle_seconds, now)
        self.assertIsNotNone(verdict, "20ms 時序雜訊不得被判成已續跑")
        self.assertEqual(verdict["action"], "arm_reset")

    def test_activity_beyond_the_skew_tolerance_is_still_stale(self) -> None:
        """容忍窗不是無限放大：活動晚於標記超過
        `HALT_MARKER_ACTIVITY_SKEW_SECONDS` 一秒，仍要判過期。"""
        now = self._now()
        marker_at = now - timedelta(seconds=600)
        marker = {"at": marker_at.isoformat(),
                  "reset_at": (marker_at + timedelta(seconds=700)).isoformat()}
        idle_seconds = 600 - (qg.HALT_MARKER_ACTIVITY_SKEW_SECONDS + 1)
        self.assertIsNone(qg.halt_verdict(marker, idle_seconds, now))

    def test_activity_exactly_at_the_skew_boundary_still_arms(self) -> None:
        """邊界值：活動恰好晚於標記 `HALT_MARKER_ACTIVITY_SKEW_SECONDS` 秒——比較符號
        用嚴格 `>`，故恰好等於容忍窗仍不算過期（與 `HALT_RESET_SKEW_SECONDS` 的既有
        `fire_at > now` 用法同一方向）。"""
        now = self._now()
        marker_at = now - timedelta(seconds=600)
        marker = {"at": marker_at.isoformat(),
                  "reset_at": (marker_at + timedelta(seconds=700)).isoformat()}
        idle_seconds = 600 - qg.HALT_MARKER_ACTIVITY_SKEW_SECONDS
        verdict = qg.halt_verdict(marker, idle_seconds, now)
        self.assertIsNotNone(verdict, "恰好等於容忍窗不應被判成已續跑")


class HaltMarkerProbePathDoesNotCreateDirectoriesTest(unittest.TestCase):
    """D23：`_halt_marker_probe_path()` 是 `--check` 唯讀探測入口，不得觸發
    `trace_dir()` 的 mkdir 副作用。詳見 docs/06_quality/
    CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第六輪〉。"""

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="d23_probe_nomkdir_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        old = os.environ.get("AUTOSDD_TRACE_DIR")
        self.trace_root = self.tmp / "never-created" / "traces"
        os.environ["AUTOSDD_TRACE_DIR"] = str(self.trace_root)
        self.addCleanup(lambda: (os.environ.__setitem__("AUTOSDD_TRACE_DIR", old)
                                 if old is not None
                                 else os.environ.pop("AUTOSDD_TRACE_DIR", None)))

    def test_probing_a_never_written_marker_creates_no_directory(self) -> None:
        path = planner._halt_marker_probe_path("sid-never-written-d23")
        self.assertFalse(path.is_file())
        self.assertFalse(self.trace_root.exists(),
                         "唯讀探測不得建目錄——`--check` 的『不寫檔』契約靠這個成立")

    def test_probing_an_existing_marker_finds_it(self) -> None:
        sid = "sid-does-exist-d23"
        qg.write_halt_marker(sid, {"sid": sid, "reset_at": "2099-01-01T00:00:00+00:00"})
        path = planner._halt_marker_probe_path(sid)
        self.assertTrue(path.is_file())
        self.assertEqual(qg.read_halt_marker(sid), {"sid": sid,
                         "reset_at": "2099-01-01T00:00:00+00:00"})


class HaltedBandLineTest(unittest.TestCase):
    """D23（SD-07）：`halted_band_line()` 純函式——未過期印 halted 行，過期或無標記回
    `None`。詳見 docs/06_quality/CrossPlatform_DEF200275_Context_Metering_Evidence.md
    〈第六輪〉。"""

    def _now(self) -> datetime:
        return datetime.now(UTC).astimezone()

    def test_no_marker_returns_none(self) -> None:
        self.assertIsNone(quota_messages.halted_band_line(None, self._now()))

    def test_unexpired_marker_yields_the_halted_line(self) -> None:
        now = self._now()
        reset_at = now + timedelta(seconds=600)
        line = quota_messages.halted_band_line({"reset_at": reset_at.isoformat()}, now)
        self.assertIsNotNone(line)
        self.assertIn("halted", line)
        self.assertIn(reset_at.isoformat(), line)

    def test_expired_marker_returns_none(self) -> None:
        now = self._now()
        reset_at = now - timedelta(seconds=1)
        self.assertIsNone(
            quota_messages.halted_band_line({"reset_at": reset_at.isoformat()}, now))

    def test_unparseable_reset_at_still_yields_a_line_not_a_crash(self) -> None:
        """解不出 reset_at 時 `_aware()` 回 `None` ⇒ 視同「尚未到」（fail-safe：寧可多印
        一次 halted，也不要在解析失敗時假裝一切正常）。"""
        line = quota_messages.halted_band_line({"reset_at": "not-a-timestamp"}, self._now())
        self.assertIsNotNone(line)


class PaceReportShortCircuitsDuringHaltTest(unittest.TestCase):
    """D23（SD-07；INV-H3）：`pace_report()` 於 halt 未過期時須短路回 halted 行，不得
    進 `pace_state()` 補打 API。詳見 docs/06_quality/
    CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第六輪〉。"""

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="d23_pace_halt_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        old_trace = os.environ.get("AUTOSDD_TRACE_DIR")
        os.environ["AUTOSDD_TRACE_DIR"] = str(self.tmp / "traces")
        self.addCleanup(lambda: (os.environ.__setitem__("AUTOSDD_TRACE_DIR", old_trace)
                                 if old_trace is not None
                                 else os.environ.pop("AUTOSDD_TRACE_DIR", None)))

    def test_pace_state_is_never_called_while_halted(self) -> None:
        now = datetime.now(UTC).astimezone()
        sid = "sid-d23-pace-halt"
        qg.write_halt_marker(sid, {
            "sid": sid, "reset_at": (now + timedelta(seconds=600)).isoformat(),
            "at": now.isoformat(), "band": "halt", "binding": "session"})

        def _boom(*_a, **_k):
            raise AssertionError("halt 期間不該呼叫 pace_state()——那條路可能補打一次 API")

        old_pace_state = qg.pace_state
        qg.pace_state = _boom
        self.addCleanup(setattr, qg, "pace_state", old_pace_state)
        report = qg.pace_report(now=now, sid=sid)
        self.assertIn("halted", report)

    def test_no_halt_marker_falls_through_to_normal_pace_report(self) -> None:
        """對照組：沒有 halt 標記時仍走既有路徑（不是永遠短路）。"""
        now = datetime.now(UTC).astimezone()
        cache = self.tmp / "autosdd_quota.json"
        cache.write_text(json.dumps({
            "schema": qg.quota_schema(),
            "axes": [{"kind": "session", "pct": 10.0,
                      "resets_at": (now + timedelta(seconds=600)).isoformat()}],
            "source": "endpoint", "measured_at": now.isoformat(timespec="seconds"),
        }), encoding="utf-8")
        old = qg.quota_cache_path
        qg.quota_cache_path = lambda: cache
        self.addCleanup(setattr, qg, "quota_cache_path", old)
        report = qg.pace_report(now=now, sid="sid-never-halted-d23")
        self.assertNotIn("halted", report)


class RelayProblemsCatchesEmptySessionIdTest(unittest.TestCase):
    """D23（SD-08）：`relay_problems()` 此前只查 session_id 存在、不查非空，空字串會
    讓 `read_halt_marker` 靜默降級。詳見 docs/06_quality/
    CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第六輪〉。"""

    def _valid_state(self, session_id: str = "sid-relayproblems-ok") -> dict:
        return {"schema": planner.RELAY_SCHEMA, "session_id": session_id,
                "plan_path": "x", "state": "patrolling", "kind": "sentinel",
                "reset_at": "", "reset_source": "operator", "attempts": 0,
                "max_attempts": 5, "allow_resume": True, "task_name": "t"}

    def test_a_fully_valid_state_has_no_problems(self) -> None:
        """對照組：本測試組的 fixture 本身必須是健康的，否則下一條測不出「單一原因」。"""
        self.assertEqual(planner.relay_problems(self._valid_state()), [])

    def test_empty_session_id_is_flagged(self) -> None:
        state = self._valid_state(session_id="")
        problems = planner.relay_problems(state)
        self.assertTrue(problems, "空字串 session_id 必須被判為需要自癒")
        self.assertTrue(any("session_id" in p for p in problems))

    def test_empty_session_id_degrades_read_halt_marker_to_none(self) -> None:
        """證明體檢面攔的正是這個真實降級路徑（不是憑空立案）。"""
        self.assertIsNone(qg.read_halt_marker(""))


class SentinelDecideRecognizesHaltMarkerTest(unittest.TestCase):
    """INV-H2 接線：`sentinel_decide()` 的 halt_marker 分支。"""

    def _now(self) -> datetime:
        return datetime.now(UTC).astimezone()

    def test_halt_marker_beats_the_idle_patrol_branch(self) -> None:
        """RC-2 的直接迴歸鎖：修前『沒有未處理撞線』就一路落到 idle<6h → patrol，
        halt 標記完全不影響判決。修後：即使 idle 很小，halt 標記存在且 reset 未到
        也要 `arm_reset`，不能繼續 patrol。
        """
        now = self._now()
        reset_at = now + timedelta(seconds=600)
        marker = {"at": now.isoformat(), "reset_at": reset_at.isoformat()}
        decision = planner.sentinel_decide(None, "", 30.0, now, halt=marker)
        self.assertEqual(decision["action"], "arm_reset",
                         "自願 halt 標記被忽略 ⇒ RC-2 復發")

    def test_real_unhandled_429_event_still_wins_over_halt_marker(self) -> None:
        """優先序：真的撞線事件（既有分支）必須贏過自願 halt 標記——兩者同時存在時
        429 那一支的判讀比較精確（它能分辨 spend／session 兩種 kind）。`now` 釘在
        事件訊息所指的 9am 前 15 分鐘（同 `test_context_budget_guard.py` 既有慣例），
        讓 429 分支落在 `arm_reset`，才驗得出「它沒有被 halt 標記蓋過」。"""
        taipei = timezone(timedelta(hours=8))
        now = datetime(2026, 8, 7, 0, 45, tzinfo=UTC).astimezone(taipei)
        event = {"kind": guard.LIMIT_SESSION,
                 "text": "You've hit your session limit · resets 9am (Asia/Taipei)",
                 "timestamp": "2026-08-07T00:44:01.000Z"}
        stale_marker = {"at": now.isoformat(),
                        "reset_at": (now + timedelta(seconds=99999)).isoformat()}
        decision = planner.sentinel_decide(event, "", 10.0, now, halt=stale_marker)
        self.assertEqual(decision["reset_source"], "transcript-verbatim",
                         "halt 標記蓋過了既有 429 判讀 ⇒ 優先序反了")

    def test_stale_halt_marker_falls_back_to_existing_idle_logic(self) -> None:
        """標記過期（session 已自行續跑）⇒ 不得卡住既有 idle 判定。"""
        now = self._now()
        marker_at = now - timedelta(seconds=1000)
        stale = {"at": marker_at.isoformat(),
                "reset_at": (marker_at + timedelta(seconds=60)).isoformat()}
        decision = planner.sentinel_decide(None, "", 5.0, now, halt=stale)
        self.assertEqual(decision["action"], "patrol")

    def test_no_halt_marker_is_fully_backward_compatible(self) -> None:
        """既有呼叫端（不帶 `halt`）行為必須逐字不變——回歸鎖。"""
        now = self._now()
        self.assertEqual(planner.sentinel_decide(None, "", 60.0, now)["action"], "patrol")
        self.assertEqual(planner.sentinel_decide(
            None, "", planner.SENTINEL_IDLE_SECONDS + 1, now)["action"], "disarm")

    def test_halt_marker_reset_source_passes_the_relay_credential_check(self) -> None:
        """DEF-200-281／F-4 端到端演練（真 launchd）揪出的整合缺口：`halt_verdict()` 的
        `arm_reset` 分支寫回 `reset_source="halt-marker"`，但 `relay_problems()` 修前
        的白名單只有 `transcript-verbatim`／`probe-verbatim`／`operator`——下一輪 tick 會把
        這個合法狀態塊判成「猜出來的 reset」而觸發不必要的 `_heal_relay()` 自癒，自癒又
        會把 `allow_resume` 靜默重置回預設值（見 `_heal_relay`／`_base_state`）。"""
        state = {"schema": planner.RELAY_SCHEMA, "session_id": "sid-halt-marker",
                 "plan_path": "p.md", "state": "waiting", "kind": "sentinel",
                 "reset_at": "2099-01-01T00:00:00+00:00", "reset_source": "halt-marker",
                 "attempts": 0, "max_attempts": 5, "allow_resume": False,
                 "task_name": "AutoSDD_Sentinel_sid-halt-marker",
                 sb.CRED_KEY_LAUNCHD: "launchd gui/501/…憑證…"}
        self.assertEqual(planner.relay_problems(state), [],
                         "halt-marker 是真實觀測值（寫入前已過 F-1 自檢），"
                         "不該被判成『猜出來的 reset』")


class HaltMarkerSelfCheckTest(unittest.TestCase):
    """DEF-200-281／F-1：`quota_halt_actions()` 落盤前的寫入自檢。

    立案鑑識沿革全文搬至 CrossPlatform_R151_Guard_Prose_Migration.md〈HaltMarkerSelfCheckTest〉節。
    """

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="def281_selfcheck_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        old = os.environ.get("AUTOSDD_TRACE_DIR")
        os.environ["AUTOSDD_TRACE_DIR"] = str(self.tmp)
        self.addCleanup(lambda: (os.environ.__setitem__("AUTOSDD_TRACE_DIR", old)
                                 if old is not None else os.environ.pop("AUTOSDD_TRACE_DIR", None)))
        ts = self.tmp / "real.jsonl"
        ts.write_text('{"type":"assistant"}\n', encoding="utf-8")
        self.transcript = ts

    def test_fresh_now_and_future_reset_is_accepted_and_written(self) -> None:
        """對照組：`now`＝真牆鐘、`reset_at` 在未來 ⇒ 照舊落盤（不得誤傷正常路徑）。"""
        decision = _decision(96.0, 600.0)
        now = datetime.now(UTC).astimezone()
        act = qg.quota_halt_actions(
            {"hook_event_name": "PostToolUse", "tool_name": "Read",
             "transcript_path": str(self.transcript)},
            decision, now, plan_writer=lambda t: "plan-path", waker=lambda t, p: {"armed": True})
        self.assertIsNone(act["marker_rejected"])
        markers = list(self.tmp.glob("halt_*.json"))
        self.assertTrue(markers, "正常路徑不該被自檢誤擋")

    def test_frozen_now_a_month_stale_is_rejected_and_not_written(self) -> None:
        """紅端＝本場事故的逐位元組重現：拿 `test_quota_policy.py` 那個凍結常數當 `now`，
        修前會落盤（且與現場三份標記逐位元組相同），修後必須拒寫、且訊息點名量級。
        """
        frozen_now = datetime(2026, 8, 9, 5, 15, 3, tzinfo=UTC)
        decision = _decision(96.0, 188 * 60.0)
        act = qg.quota_halt_actions(
            {"hook_event_name": "PostToolUse", "tool_name": "Read",
             "transcript_path": str(self.transcript)},
            decision, frozen_now, plan_writer=lambda t: "plan-path",
            waker=lambda t, p: {"armed": True})
        self.assertIsNotNone(act["marker_rejected"])
        self.assertIn("疑似測試夾具洩漏", act["marker_rejected"])
        markers = list(self.tmp.glob("halt_*.json"))
        self.assertFalse(markers, "凍結的 now 不該落盤——落盤就是本次事故復發")

    def test_reset_at_in_the_past_is_rejected_even_when_now_is_fresh(self) -> None:
        """`now` 本身與牆鐘偏移很小（不會撞到 skew 門檻），但算出來的 `reset_at`
        相對 `real_now` 已經是過去 ⇒ 同樣拒寫，不准落一份保證讓 `halt_verdict()`
        判過期的標記。偏移刻意選在「skew 門檻之內、但足夠讓 reset 翻頁」的區間。"""
        now = datetime.now(UTC).astimezone()
        decision = _decision(96.0, 60.0)  # reset ≈ now 之後 60 秒
        real_now_past_reset = now + timedelta(seconds=120)  # skew=120s<600s；reset 已過
        marker, rejected = qg.halt_marker_or_rejection(
            "sid-past-reset", decision, now, self.transcript, "payload",
            real_now=real_now_past_reset)
        self.assertIsNone(marker)
        self.assertIn("已在過去", rejected)

    def test_skew_boundary_is_exactly_the_documented_threshold(self) -> None:
        """門檻值本身要能現查、不是憑印象——10 分鐘剛好卡在
        `HALT_MARKER_MAX_CLOCK_SKEW_SECONDS`。"""
        self.assertEqual(quota_messages.HALT_MARKER_MAX_CLOCK_SKEW_SECONDS, 600)
        now = datetime.now(UTC).astimezone()
        decision = _decision(96.0, 600.0)
        just_inside, _ = qg.halt_marker_or_rejection(
            "sid-inside", decision, now - timedelta(seconds=599), self.transcript, "payload",
            real_now=now)
        self.assertIsNotNone(just_inside)
        just_outside, reason = qg.halt_marker_or_rejection(
            "sid-outside", decision, now - timedelta(seconds=601), self.transcript, "payload",
            real_now=now)
        self.assertIsNone(just_outside)
        self.assertIsNotNone(reason)

    def test_naive_now_is_rejected_not_crashed(self) -> None:
        """複審 naive-now 防呆（必修）：`now` 缺 tzinfo 時 `real_now - now` 會拋
        `TypeError` 崩掉整條 halt 武裝路徑——這比拒寫更糟，連拒寫理由都印不出來，
        呼叫端（`quota_halt_actions`）會整段連 `not_armed_reason` 都算不出來。
        方向＝naive 視為不可信任的輸入，拒寫而非猜時區（猜錯時區會落一份看似合法、
        實則 `at`/`reset_at` 全錯的標記，與 RC-1 同型：寧可漏一次武裝機會）。
        """
        decision = _decision(96.0, 600.0)
        naive_now = datetime(2026, 9, 11, 9, 0, 0)  # 蓄意缺 tzinfo
        marker, rejected = qg.halt_marker_or_rejection(
            "sid-naive-now", decision, naive_now, self.transcript, "payload")
        self.assertIsNone(marker)
        self.assertIsNotNone(rejected)
        self.assertIn("tzinfo", rejected)


class HaltLatchIsSessionScopedTest(unittest.TestCase):
    """DEF-200-281 第二輪／RC-3：`quota_gate()` halt 分支的閂鎖鍵此前不含 sid
    （`f"halt@{kind}@{reset[:16]}"`），而 `quota_latch_path()` 是 machine-wide 單一檔案。
    同一個 reset 視窗內，第二個撞 halt 的 session 會被第一個 session 的閂鎖擋下
    （`key in latch_read(latch)`），於是永遠不呼叫 `quota_halt_actions()`——不寫自己的
    halt 標記，也不重新嘗試 spawn。原始觀測（立案當時本機同時掛兩支哨兵）搬至
    CrossPlatform_R86_Guard_Repin_Evidence.md §G。
    """

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="def281_rc3_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        old_trace = os.environ.get("AUTOSDD_TRACE_DIR")
        os.environ["AUTOSDD_TRACE_DIR"] = str(self.tmp / "traces")
        self.addCleanup(lambda: (os.environ.__setitem__("AUTOSDD_TRACE_DIR", old_trace)
                                 if old_trace is not None
                                 else os.environ.pop("AUTOSDD_TRACE_DIR", None)))
        now = datetime.now(UTC).astimezone()
        cache = self.tmp / "autosdd_quota.json"
        body = {"schema": qg.quota_schema(),
                "axes": [{"kind": "session", "pct": 96.0,
                          "resets_at": (now + timedelta(seconds=600)).isoformat()}],
                "source": "endpoint", "measured_at": now.isoformat(timespec="seconds")}
        cache.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        # 同 `QuotaPrepareBandActuallyPreparesTest` 既有慣例：三個檔案契約全關進沙箱，
        # `quota_latch_path` 刻意只給**一份共用**路徑——生產上機器級單一檔案正是本場景
        # 要重現的前提（latch 的機器級範圍本身不是本輪要動的線，見任務書 D-b）。
        for name, value in (("quota_cache_path", lambda: cache),
                            ("fanout_ledger_path", lambda: self.tmp / "ledger.d"),
                            ("quota_latch_path", lambda: self.tmp / "latch.json")):
            old = getattr(qg, name)
            setattr(qg, name, value)
            self.addCleanup(setattr, qg, name, old)
        self.waker_calls: list[str] = []
        self.notices: list[bool] = []  # 每次 `_gate()` 有沒有向模型送出 halt 提醒

    def _transcript(self, sid: str) -> Path:
        ts = self.tmp / f"{sid}.jsonl"
        ts.write_text('{"type":"assistant"}\n', encoding="utf-8")
        return ts

    def _gate(self, sid: str) -> int:
        ts = self._transcript(sid)
        rc = qg.quota_gate(
            {"hook_event_name": "PostToolUse", "tool_name": "Read",
             "transcript_path": str(ts)},
            blocking=guard.BLOCKING_TOOLS, latch_read=guard.announced_latches,
            latch_write=guard.remember_latch, plan_writer=lambda t: "plan-path",
            waker=lambda t, p: (self.waker_calls.append(str(t)) or {"armed": True}),
            event="PostToolUse")
        # DEF-200-435：PostToolUse 的 halt 只經 `emit_to_model` 提醒一次（只累積、不輸出）⇒
        # 就地排進緩衝區並記下「這次有沒有說話」，也免得它在 atexit 印到真的 stdout。
        with contextlib.redirect_stdout(io.StringIO()) as out:
            platform_utils.flush_to_model()
        self.notices.append(bool(out.getvalue().strip()))
        return rc

    def test_two_sessions_in_the_same_window_both_get_their_own_marker(self) -> None:
        """紅端＝修前第二個 sid 的 `_gate()` 會撞進「已閂鎖」分支：`waker` 只被叫一次、
        `read_halt_marker("sidB-...")` 回 `None`——第二個 session 的喚醒鏈斷在這裡。
        """
        rc_a = self._gate("sidA-def281rc3")
        rc_b = self._gate("sidB-def281rc3")
        self.assertEqual((rc_a, rc_b), (0, 0), "PostToolUse 的 halt 只提醒、不是 hook 錯誤")
        self.assertEqual(self.notices, [True, True], "B 首見＝自己也該被提醒一次，不被 A 吞掉")
        self.assertEqual(len(self.waker_calls), 2,
                         "第二個 session 被第一個的機器級閂鎖誤擋 ⇒ RC-3 復發")
        self.assertIsNotNone(qg.read_halt_marker("sidA-def281rc3"),
                             "第一個 session 應有自己的 halt 標記")
        self.assertIsNotNone(qg.read_halt_marker("sidB-def281rc3"),
                             "第二個 session 沒有自己的 halt 標記 ⇒ 它的哨兵永遠 idle-patrol")

    def test_same_session_repeated_halt_does_not_rewrite_or_respawn(self) -> None:
        """同一 sid 在同一視窗連續撞 halt：既有 one-shot 語意必須保留——第二次不重新
        spawn（`waker` 只叫一次），這是本輪唯一要**保留**而非改動的既有行為。
        """
        rc1 = self._gate("sidC-def281rc3")
        rc2 = self._gate("sidC-def281rc3")
        self.assertEqual((rc1, rc2), (0, 0))
        self.assertEqual(self.notices, [True, False], "提醒只說一次，之後安靜")
        self.assertEqual(len(self.waker_calls), 1,
                         "同一 session 在同一視窗重複 halt 不該重新 spawn"
                         "（one-shot 語意被打破）")


class PrepareLatchIsSessionScopedTest(unittest.TestCase):
    """D22（SD-04）：`quota_prepare_actions()` 閂鎖鍵此前不含 sid，同視窗第二個 session
    會被第一個誤擋、拿不到任務書骨架（比照 HaltLatchIsSessionScopedTest 同型）。詳見
    docs/06_quality/CrossPlatform_DEF200275_Context_Metering_Evidence.md〈第六輪〉。"""

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="d22_prepare_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        old_trace = os.environ.get("AUTOSDD_TRACE_DIR")
        os.environ["AUTOSDD_TRACE_DIR"] = str(self.tmp / "traces")
        self.addCleanup(lambda: (os.environ.__setitem__("AUTOSDD_TRACE_DIR", old_trace)
                                 if old_trace is not None
                                 else os.environ.pop("AUTOSDD_TRACE_DIR", None)))
        now = datetime.now(UTC).astimezone()
        cache = self.tmp / "autosdd_quota.json"
        body = {"schema": qg.quota_schema(),
                "axes": [{"kind": "session", "pct": 90.0,
                          "resets_at": (now + timedelta(seconds=600)).isoformat()}],
                "source": "endpoint", "measured_at": now.isoformat(timespec="seconds")}
        cache.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
        for name, value in (("quota_cache_path", lambda: cache),
                            ("fanout_ledger_path", lambda: self.tmp / "ledger.d"),
                            ("quota_latch_path", lambda: self.tmp / "latch.json")):
            old = getattr(qg, name)
            setattr(qg, name, value)
            self.addCleanup(setattr, qg, name, old)
        self.plan_calls: list[str] = []

    def _transcript(self, sid: str) -> Path:
        ts = self.tmp / f"{sid}.jsonl"
        ts.write_text('{"type":"assistant"}\n', encoding="utf-8")
        return ts

    def _gate(self, sid: str) -> int:
        ts = self._transcript(sid)
        return qg.quota_gate(
            {"hook_event_name": "PostToolUse", "tool_name": "Read",
             "transcript_path": str(ts)},
            blocking=guard.BLOCKING_TOOLS, latch_read=guard.announced_latches,
            latch_write=guard.remember_latch,
            plan_writer=lambda t: (self.plan_calls.append(str(t)) or f"plan-for-{t}"),
            waker=lambda t, p: {"armed": True}, event="PostToolUse")

    def test_two_sessions_in_the_same_prepare_window_both_get_their_own_plan(self) -> None:
        """紅端：修前第二個 sid 撞「已閂鎖」分支，plan_writer 只被叫一次（DEF-200-278
        第二輪 §8 item 1）。"""
        self._gate("sidA-d22prepare")
        self._gate("sidB-d22prepare")
        self.assertEqual(len(self.plan_calls), 2,
                         "第二個 session 被第一個的機器級閂鎖誤擋 ⇒ D22 復發")
        self.assertIn("sidA-d22prepare", self.plan_calls[0])
        self.assertIn("sidB-d22prepare", self.plan_calls[1])

    def test_same_session_repeated_prepare_does_not_rewrite(self) -> None:
        """同一 sid 在同一視窗重複進 prepare 帶：既有 one-shot 語意必須保留。"""
        self._gate("sidC-d22prepare")
        self._gate("sidC-d22prepare")
        self.assertEqual(len(self.plan_calls), 1,
                         "同一 session 在同一視窗重複 prepare 不該重新寫任務書")


class EnvSpecLeakIsolationTest(unittest.TestCase):
    """巢狀鎖（DEF-200-354）：module pin 必須真的擋得住洩漏、且清單不是手抄。"""

    def test_pin_leaves_no_env_spec_key_leaked(self) -> None:
        """兩種鍵型各注入一次：旗標鍵（`QUOTA_OFF_ENV`）與數值鍵
        （`AUTOSDD_QUOTA_HALT_PCT`）洩漏時都要被 pin 拔掉。"""
        for name, leaked in ((qg.QUOTA_OFF_ENV, "1"), ("AUTOSDD_QUOTA_HALT_PCT", "1")):
            with self.subTest(name=name), unittest.mock.patch.dict(os.environ, {name: leaked}):
                _pin_env_spec_off()
                self.assertNotIn(name, os.environ, f"pin 沒有拔掉洩漏進來的 {name}")

    def test_pin_set_is_derived_from_env_spec_not_copied(self) -> None:
        """pin 集合須涵蓋 `ENV_SPEC` 全名稱集合——手抄清單在新增鍵時不會自動跟長。"""
        self.assertGreaterEqual(set(_ENV_SPEC_ORIGINALS) | {guard.SENTINEL_OFF_ENV},
                                {spec.name for spec in quota_policy.ENV_SPEC})


class ClaimGuardCatchesAutoContinueWithoutCredentialTest(unittest.TestCase):
    """INV-H4：CLAUDE.md〈反事後諸葛取證規則〉要求「宣稱已排程／會自動繼續」必須
    附排程器回報的憑證——本輪的直接誘因（RC-3）正是主控寫下「重置後會自動續跑」
    卻拿不出 `next_run_time`／launchd descriptor。詞表要收得到這兩句常見說法。
    """

    def setUp(self) -> None:
        self.g = _load_claim_guard()

    def test_wordlist_recognizes_auto_resume_phrases(self) -> None:
        for phrase in ("自動續跑", "會自動繼續"):
            with self.subTest(phrase=phrase):
                self.assertRegex(phrase, self.g.NAKED_VERDICT_RE.pattern,
                                 f"詞表沒收「{phrase}」⇒ RC-3 那句宣稱仍然檢查不到")

    def test_stacked_auto_resume_claim_without_evidence_is_flagged(self) -> None:
        """兩個詞疊在同一句、且本場 tool_output 是空字串（沒有任何工具輸出＝零佐證）
        ⇒ 既有機制要出聲（同檔既有 `NAKED_MIN_TOKENS=2` 判準，未改判準本身，只驗
        新詞真的接上它）。"""
        hits = self.g.naked_verdict_hits(
            "重置後會自動繼續、已排程並自動續跑，不需要人介入。", "")
        self.assertTrue(hits, "自動續跑類宣稱疊加後沒有被判準抓到")


def _usage_transcript(path: Path) -> Path:
    """最小可量測逐字稿：一筆帶 usage 的 assistant 記錄（`measure()` 吃得動）。"""
    usage = {"input_tokens": 2, "cache_creation_input_tokens": 3,
             "cache_read_input_tokens": 995, "output_tokens": 1}
    message = {"model": "claude-test-double-3", "usage": usage}
    record = json.dumps({"type": "assistant", "message": message})
    path.write_text(record + "\n", encoding="utf-8", newline="\n")
    return path


class RegisterSchtasksTimeIsObservedNotGuessedTest(unittest.TestCase):
    """DEF-200-231①（受測：`tools/session_resume_planner.py` 的 `--print-schtasks-command`／
    `--register-schtasks`）：缺 `--at` 時，觸發時刻只取**實測**的 resets_at（額度快取）＋緩衝；
    解不出就拒絕，不得退回 `(Get-Date).AddHours(5)`（根 CLAUDE.md：reset 時刻是滾動視窗，
    只能觀測不能算）。事故形狀（DEF-200-231）：快取明明寫著 14:00，這條手動路徑卻排在 now+5h。
    全程行程內＋假排程後端：不真註冊、不打 usage 端點（`read_quota` 零網路）。"""

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="def231_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        env = {"AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp),
               "AUTOSDD_TRACE_DIR": str(self.tmp / "trace")}
        patcher = unittest.mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.transcript = _usage_transcript(self.tmp / "sidDef231.jsonl")
        self.plan = self.tmp / "plan.md"

    def _cache(self, *axes: tuple[str, float, float | None],
               age: float = 0.0, tz: timezone | None = None,
               zulu: bool = False) -> datetime:
        """種一份合成快取，回傳它用的基準 now（期望值與快取共用同一個 now，
        才不會因跨秒邊界偶發不等）：`axes`＝`(kind, pct, 距 reset 秒數；None＝無 reset
        可等)`。"""
        now = datetime.now(UTC).astimezone()

        def iso(seconds: float | None) -> str | None:
            if seconds is None:
                return None
            text = (now + timedelta(seconds=seconds)).astimezone(tz).isoformat()
            return text.replace("+00:00", "Z") if zulu else text

        measured = (now - timedelta(seconds=age)).isoformat(timespec="seconds")
        rows = [{"kind": k, "pct": pct, "resets_at": iso(r)} for k, pct, r in axes]
        body = {"schema": qg.quota_schema(), "source": "endpoint",
                "measured_at": measured, "axes": rows}
        (self.tmp / "autosdd_quota.json").write_text(
            json.dumps(body), encoding="utf-8", newline="\n")
        return now

    def _main(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        args = ["--transcript", str(self.transcript), "--out", str(self.plan), *argv]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = planner.main(args)
        return rc, out.getvalue(), err.getvalue()

    def _register(self, *argv: str) -> tuple[int, str, list]:
        """跑 `--register-schtasks`，回 `(rc, stderr, 底層註冊呼叫的位置引數清單)`；
        後端與註冊皆替身。"""
        calls: list[tuple] = []

        class _Backend:
            name, credential_key = "fake", "next_run_time"

            def list_jobs(self, prefix):  # noqa: ARG002 — 同 M-13 既有替身
                return []

            def credential_line(self, moment):
                return f"credential={moment}"

        def _fake_register(*args, **_kwargs):
            calls.append(args)
            return 0, "NEXT"

        select = unittest.mock.patch.object(
            planner.schedule_backend, "select", return_value=_Backend())
        register = unittest.mock.patch.object(
            planner, "_register_at_expr", side_effect=_fake_register)
        with select, register:
            rc, _out, err = self._main("--register-schtasks", *argv)
        return rc, err, calls

    @staticmethod
    def _fire(resets_in: float, now: datetime) -> datetime:
        """期望的觸發時刻：實測 reset ＋ `RESET_SKEW_SECONDS`，換到本機時區。"""
        skew = planner.RESET_SKEW_SECONDS
        return (now + timedelta(seconds=resets_in + skew)).astimezone()

    def test_a_cached_reset_is_what_gets_printed_not_five_hours(self) -> None:
        """核心：快取說 90 分鐘後 reset ⇒ 印出的觸發時刻 ≈ now＋92 分鐘（reset＋緩衝），
        絕不是 now＋5h。獨立於實作公式再核一次：把字面解回本機時刻（帶 offset，跨 DST
        不偏一小時），與現在相減。"""
        self._cache(("session", 90.0, 5400.0))
        rc, out, err = self._main("--print-schtasks-command")
        self.assertEqual(rc, 0, err)
        self.assertNotIn("AddHours(5)", out, "仍印出『假設 5 小時』的猜測值")
        literal = re.search(r"-At '([^']+)'", out)
        self.assertIsNotNone(literal, f"輸出沒有單引號時間字面：{out[-600:]}")
        moment = datetime.strptime(literal.group(1), "%Y-%m-%d %H:%M:%S").astimezone()
        gap = (moment - datetime.now().astimezone()).total_seconds()
        self.assertAlmostEqual(gap, 5400 + planner.RESET_SKEW_SECONDS, delta=90,
                               msg="觸發時刻不是『實測 reset ＋緩衝』")

    def test_a_utc_reset_prints_in_the_machine_local_timezone(self) -> None:
        """時區收斂不下沉（`-At '<字串>'` 一律被當成**機器本地時區**）：真快取的
        `resets_at` 是伺服器給的 UTC 字串；少了 `.astimezone()`，排程照樣成立、
        NextRunTime 照樣拿得到，只是整個偏一個時區差，醒在錯的時刻而取證全綠。夾具刻意不
        用本機 offset 字串（那樣拿掉 `.astimezone()` 也過），並加兩個固定的非 UTC offset
        （+14／-12）：本機時區至多等於其中一個，所以不論跑在哪個時區（CI 多半是 UTC），
        變異都至少有一格會紅。"""
        zones = (("+00:00", UTC, False), ("Z", UTC, True),
                 ("+14:00", timezone(timedelta(hours=14)), False),
                 ("-12:00", timezone(timedelta(hours=-12)), False))
        for label, tz, zulu in zones:
            with self.subTest(offset=label):
                now = self._cache(("session", 90.0, 5400.0), tz=tz, zulu=zulu)
                rc, out, err = self._main("--print-schtasks-command")
                self.assertEqual(rc, 0, err)
                literal = re.search(r"-At '([^']+)'", out)
                self.assertIsNotNone(literal, out[-400:])
                self.assertEqual(
                    literal.group(1), f"{self._fire(5400.0, now):%Y-%m-%d %H:%M:%S}",
                    "UTC 字串沒有被換算成本機時區再印")

    def test_the_header_describes_the_branch_that_was_taken(self) -> None:
        """印出的標頭只能說**這次真的走的那條路**：省略 `--at` 才是「取額度快取實測
        reset」；顯式 `--at` 是操作者宣稱的時刻，印「省略 --at＝…」對它是假話。"""
        self._cache(("session", 90.0, 5400.0))
        _, observed, _ = self._main("--print-schtasks-command")
        _, explicit, _ = self._main(
            "--print-schtasks-command", "--at", "(Get-Date).AddMinutes(30)")
        self.assertIn("省略 --at＝額度快取", observed)
        self.assertNotIn("省略 --at", explicit)
        self.assertIn("--at 顯式指定", explicit)

    def test_the_halted_axis_reset_wins_over_a_far_binding_axis(self) -> None:
        """沿用 `halt_resets_at`（≥halt 各軸中最早可解析者）而不是另造一套挑軸：session
        96% 已停、一小時後 reset；weekly 99%（binding，最緊的一軸）兩天後才 reset ⇒
        要等的是 session 那一個。若改取 binding 的 reset，
        會排到兩天後（或被視界擋下而拒絕），而 5 小時窗一小時後就翻頁了。"""
        now = self._cache(("session", 96.0, 3600.0), ("weekly_all", 99.0, 172800.0))
        rc, out, err = self._main("--print-schtasks-command")
        self.assertEqual(rc, 0, err)
        self.assertIn(f"-At '{self._fire(3600.0, now):%Y-%m-%d %H:%M:%S}'", out)

    def test_an_unobservable_reset_refuses_before_printing_anything(self) -> None:
        """憲法：解不出時刻一律拒絕——rc≠0、stderr 出聲「拒絕退回假設 5 小時」、stdout
        不得已經印出可貼的註冊腳本（印了就是把猜測交到使用者手上）。三種解不出：沒快取；
        快取過 TTL（≠ resets_at 還活著，DEF-200-200，訊息要指路 `--pace`）；只有兩天後才
        reset 的週軸（超出 6 小時可等視界，七天後才響的排程＝痕跡全綠的空等）。"""
        old = qg.QUOTA_CACHE_TTL_SECONDS + 300.0
        cases = (
            ("沒有快取", None, 0.0, ()),
            ("快取過 TTL", ("session", 90.0, 5400.0), old, ("stale-cache", "--pace")),
            ("週軸過遠", ("weekly_all", 30.0, 172800.0), 0.0, ("遠超 6 小時",)),
        )
        for label, axis, age, expected in cases:
            with self.subTest(label):
                if axis is not None:
                    self._cache(axis, age=age)
                rc, out, err = self._main("--print-schtasks-command")
                self.assertNotEqual(rc, 0)
                for fragment in ("拒絕退回「假設 5 小時」", *expected):
                    self.assertIn(fragment, err)
                self.assertNotIn("Register-ScheduledTask", out)
                self.assertNotIn("AddHours(5)", out + err)

    def test_an_explicit_at_passes_through_untouched(self) -> None:
        """人顯式給的 `--at` 照舊（不讀快取、不拒絕）：操作者知道自己在宣稱什麼時刻——
        印出與真註冊兩條路都一樣，運算式原樣下傳、結構化 `at` 仍是 `None`。"""
        rc, out, err = self._main(
            "--print-schtasks-command", "--at", "(Get-Date).AddMinutes(30)")
        self.assertEqual(rc, 0, err)
        self.assertIn("-At (Get-Date).AddMinutes(30)", out)
        self.assertNotIn("AddHours(5)", out)
        rc, err, calls = self._register("--at", "'2099-01-01 00:00:00'")
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(calls), 1, calls)
        _plan, _task, at_expr, tick, *rest = calls[0]
        self.assertEqual((at_expr, tick, (rest or [None])[0]),
                         ("'2099-01-01 00:00:00'", planner.RESUME_TICK, None))

    def test_register_hands_the_observed_moment_and_a_structured_at_over(self) -> None:
        """真註冊那條路拿到的是同一份觀測值：字面給 schtasks、結構化的本機時區 `at` 給
        launchd（`at=None` ⇒ mac 後端只寫重複觸發、不寫時刻——
        印出來的與真註冊的會分岔）。"""
        now = self._cache(("session", 90.0, 5400.0))
        rc, err, calls = self._register()
        self.assertEqual(rc, 0, err)
        self.assertEqual(len(calls), 1, calls)
        _plan, _task, at_expr, tick, at = calls[0]
        self.assertEqual(at_expr, f"'{self._fire(5400.0, now):%Y-%m-%d %H:%M:%S}'")
        self.assertEqual(tick, planner.RESUME_TICK)
        self.assertIsNotNone(at.tzinfo, "結構化 at 必須帶 tzinfo")
        gap = (at - now).total_seconds()
        self.assertAlmostEqual(gap, 5400 + planner.RESET_SKEW_SECONDS, delta=90)

    def test_register_without_an_observation_never_reaches_the_scheduler(self) -> None:
        """「拒絕武裝」要在**註冊之前**：解不出時刻時底層註冊呼叫次數必須為 0（只看 rc
        會被『註冊了、只是回非零』的實作騙過）。"""
        rc, err, calls = self._register()
        self.assertNotEqual(rc, 0)
        self.assertIn("拒絕退回「假設 5 小時」", err)
        self.assertEqual(calls, [], "解不出時刻卻仍呼叫了底層註冊")

    def test_the_guess_is_not_a_default_anywhere(self) -> None:
        """結構面：`--at` 的 argparse 預設與 `schtasks_command(at_expr=)`
        都不得再帶預設值——任何忘了帶 `--at` 的呼叫端都不能靜默走猜測路（ADR-XPLAT-014
        約束 1）。「`--at` 缺席就固定加 5 小時」的常數已整支刪除（程式碼零引用）。"""
        self.assertIsNone(planner.build_parser().parse_args([]).at)
        param = inspect.signature(planner.schtasks_command).parameters["at_expr"]
        self.assertIs(param.default, inspect.Parameter.empty)

    def test_a_cache_read_failure_refuses_with_the_reason(self) -> None:
        """讀快取本身拋例外 ⇒ 走拒絕並把例外帶進訊息；不得吞掉後退回猜測，也不得往上拋成
        traceback。"""
        boom = OSError("合成：讀不到")
        with unittest.mock.patch.object(qg, "read_quota", side_effect=boom):
            at_expr, at, why = session_brief.schtasks_trigger(None, qg, skew_seconds=120)
        self.assertEqual((at_expr, at), (None, None))
        self.assertIn("拒絕退回「假設 5 小時」", why)
        self.assertIn("合成：讀不到", why)


class CheckPrintsTheSddFsmLineTest(unittest.TestCase):
    """`--check` 末行補印 SDD FSM 現況：模型在 Q1 說「被擋」時，
    要有一條可外驗的機器級證據。純展示——不判阻斷（判準在 SDD 側）、不寫檔（`--check`
    的既有契約）。"""

    def setUp(self) -> None:
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="def_fsm_check_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        env = {"AUTOSDD_TRACE_DIR": str(self.tmp / "trace"),
               "AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp),
               "AUTOSDD_CONTEXT_FEED_DIR": str(self.tmp / "feed")}
        patcher = unittest.mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.transcript = _usage_transcript(self.tmp / "sidFsm.jsonl")

    def _check_lines(self, version: str | None) -> list[str]:
        """跑 `--check`，回 stdout 的行；`version=None` ＝ `SDD_ACTIVE_VERSION` 未設。"""
        os.environ.pop("SDD_ACTIVE_VERSION", None)
        if version is not None:
            os.environ["SDD_ACTIVE_VERSION"] = version
        out = io.StringIO()
        no_liveness = unittest.mock.patch.object(
            planner.sentinel_lifecycle, "liveness_line", return_value="")
        with no_liveness, contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            rc = planner.main(["--check", "--transcript", str(self.transcript)])
        self.assertEqual(rc, 0)
        return out.getvalue().splitlines()

    def test_unset_prints_dormant_as_the_last_stdout_line(self) -> None:
        """未設 ⇒ 末行說「休眠」：沒有這行，模型只能靠猜判斷 SDD 守門有沒有在管這個
        session。"""
        lines = self._check_lines(None)
        self.assertEqual(lines[-1], "SDD FSM：休眠（SDD_ACTIVE_VERSION 未設）")

    def test_set_prints_the_state_report_as_the_last_stdout_line(self) -> None:
        """有設 ⇒ 末行是狀態報告（本測試指到不存在的版本，與開發機上真狀態檔無關）：
        「無狀態檔」。"""
        lines = self._check_lines("99.99")
        self.assertTrue(lines[-1].startswith("SDD FSM：無狀態檔"), lines[-1])
        self.assertIn("99.99", lines[-1])


if __name__ == "__main__":
    unittest.main()
