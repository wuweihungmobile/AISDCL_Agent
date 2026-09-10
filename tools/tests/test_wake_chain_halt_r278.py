#!/usr/bin/env python3
"""DEF-200-278（喚醒鏈缺口第四輪）：halt 交棒 ＋ 哨兵認得自願停機的回歸鎖。

事故：額度守衛判 `band=halt` 後，`quota_halt_actions()` 只認 `payload["transcript_path"]`
——缺席（或雖有路徑但暫時讀不到檔）就整段放棄，任務書寫不出來、喚醒訊息卻只印一句
籠統的「拿不到逐字稿路徑」，不管真正的成因是什麼（見 §RC1）。而哨兵（`sentinel_decide`）
只認逐字稿裡的未復原撞線（429），自願停機沒有那一筆 ⇒ 永遠 `patrol` 到 6 小時後靜默
解除。兩層合起來＝reset 到了也不會有人喚醒續跑（本輪 2026-09-10 19:1x～23:11 損失
≈3h50m 的直接成因）。

本檔釘住的兩件事（各自紅→綠）：
  INV-H1：`quota_gate.resolve_halt_transcript()` 在 payload 缺席時以
          `CLAUDE_CODE_SESSION_ID`＋`project_transcript_dir()` 還原；
          `quota_gate.quota_halt_actions()` 落一份持久 halt 標記，且「未武裝」訊息
          不再對所有成因都印同一句話。
  INV-H2：`session_resume_planner.sentinel_decide()` 認得 halt 標記，未過期時
          `arm_reset`／已過期時 `probe`；標記過期（session 已自行續跑）不再誤觸。
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

import importlib.util as _ilu  # noqa: E402

import context_budget_guard as guard  # noqa: E402
import quota_gate as qg  # noqa: E402
import quota_policy  # noqa: E402

import session_resume_planner as planner  # noqa: E402


def _load_claim_guard():
    """同 `test_claim_provenance_r86.py` 的既有慣例：以檔案路徑載入，不經 import 機制。"""
    hook = _REPO_ROOT / ".claude" / "hooks" / "check_claim_provenance.py"
    spec = _ilu.spec_from_file_location("_claim_guard_r278", hook)
    module = _ilu.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

os.environ[guard.SENTINEL_OFF_ENV] = "1"  # 本檔全程不准碰真排程器（同既有測試慣例）


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
        """RC-1 的直接修復：這是紅端本身——修前 `quota_gate` 沒有這支函式。"""
        root = self.tmp / "repo"
        root.mkdir()
        import re
        slug = re.sub(r"[^A-Za-z0-9]", "-", str(root))
        proj = Path.home() / ".claude" / "projects" / slug
        proj.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: __import__("shutil").rmtree(proj, ignore_errors=True))
        (proj / "sid-def278.jsonl").write_text("{}\n", encoding="utf-8")
        old_env = dict(os.environ)
        os.environ["CLAUDE_CODE_SESSION_ID"] = "sid-def278"
        os.environ["CLAUDE_PROJECT_DIR"] = str(root)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old_env)))
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


if __name__ == "__main__":
    unittest.main()
