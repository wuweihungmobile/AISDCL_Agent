#!/usr/bin/env python3
"""WP-SW REQ-CTL-52（TCS-Control §8；AT-CTL-109～114）：同專案另一 session 在動 ⇒ 不 spawn。

WHY（暴露證據）：掌舵者真機回報「為何還有另一個視窗……多頭馬車」；前置情境在真實逐字稿已發生 2 次。
判準＝`transcript_activity.driver_after` 迴圈推進 since 直到回 assistant 或 None（單次呼叫只回窗口內最早一筆，
真實活躍 session 常是人類提示在前，會把正在動的 session 判成沒人在動＝雙駕駛）；只認 AI 回合，真人／`/login` 不算。
縫：FS（tmp 專案目錄）、NOW（真時鐘）、`oldwin_park._rearm`（假重排，絕不登記真排程）。
"""
from __future__ import annotations

import ast
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import test_sessionctl_park as P  # noqa: E402  # 模組引用：避免把對方的 TestCase 帶進本檔重跑

import transcript_activity as ta  # noqa: E402
from lib.sessionctl import othersession, park, park_announce  # noqa: E402

OWN = "11111111-2222-4333-8444-555555555555"
OTHER = "4290bf58-a5e9-4e64-b118-e9db87ca2af4"


def _rec(kind: str, at: datetime, **over) -> dict:
    stamp = at.astimezone().isoformat()
    if kind == "assistant":
        return {"type": "assistant", "timestamp": stamp, "message": {"model": "claude-fable-5", "content": []}, **over}
    if kind == "synthetic":
        return {"type": "assistant", "timestamp": stamp, "message": {"model": "<synthetic>"}, **over}
    if kind == "login":
        return {"type": "user", "timestamp": stamp, "origin": {"kind": "human"},
                "message": {"content": "<command-name>/login</command-name>"}, **over}
    return {"type": "user", "timestamp": stamp, "origin": {"kind": kind}, "message": {"content": "hi"}, **over}


class _Dir(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="wpsw-os-")
        self.addCleanup(holder.cleanup)
        self.proj = Path(holder.name)
        self.now = datetime.now().astimezone()
        patch = mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": str(self.proj / "_traces"),
                                             "AUTOSDD_QUOTA_CACHE_DIR": str(self.proj / "_q")})
        patch.start()
        self.addCleanup(patch.stop)

    def put(self, sid: str, *recs: dict, sub: str | None = None) -> Path:
        path = self.proj / f"{sid}.jsonl"
        target = path
        if sub:
            target = self.proj / sid / "subagents" / sub
            target.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text("", encoding="utf-8")
        target.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
        return path

    def ago(self, minutes: float) -> datetime:
        return self.now - timedelta(minutes=minutes)

    def calls(self, **kw):
        n = {"n": 0}

        def probe(path, since, now):
            n["n"] += 1
            return ta.driver_after(path, since, now)

        got = othersession.active(self.proj, OWN, self.now, driver_after=probe, **kw)
        return got, n["n"]


class ActiveTest(_Dir):
    def test_at_ctl_109_human_before_assistant_is_found_by_advancing_since(self) -> None:
        """AT-CTL-109：窗口內 human(t1)→assistant(t2)：單次 driver_after 只回 human，迴圈推進才命中；
        呼叫次數 human→assistant＝2、human→human→assistant＝3、human 單獨＝2（回 None）。"""
        self.put(OTHER, _rec("human", self.ago(5)), _rec("assistant", self.ago(4)))
        got, n = self.calls()
        self.assertEqual((got["sid"], n), (OTHER, 2))
        self.assertEqual(ta.driver_after(self.proj / f"{OTHER}.jsonl", self.now.timestamp() - 900,
                                         self.now)["kind"], "human", "夾具真的重現單次呼叫會漏判的形狀")
        self.put(OTHER, _rec("human", self.ago(6)), _rec("human", self.ago(5)), _rec("assistant", self.ago(4)))
        self.assertEqual(self.calls()[1], 3)
        self.put(OTHER, _rec("human", self.ago(5)))
        got, n = self.calls()
        self.assertEqual((got, n), (None, 2))

    def test_at_ctl_109_excludes_self_synthetic_and_finds_subagent_only_activity(self) -> None:
        """自己排除；`<synthetic>` 限額記錄不算；活只在 subagent 檔也算（主檔舊）。"""
        self.put(OWN, _rec("assistant", self.ago(1)))
        self.put("aaaaaaaa-0000-4000-8000-000000000001", _rec("synthetic", self.ago(1)))
        self.assertIsNone(self.calls()[0])
        self.put(OTHER, _rec("assistant", self.ago(60)), sub="agent-x.jsonl")
        (self.proj / OTHER / "subagents" / "agent-x.jsonl").write_text(
            json.dumps(_rec("assistant", self.ago(2))) + "\n", encoding="utf-8")
        got, _n = self.calls()
        self.assertEqual(got["sid"], OTHER)

    def test_at_ctl_110_not_a_driver_cases(self) -> None:
        """AT-CTL-110：①僅 mtime 新、無對話記錄 ②最後記錄早於 now−N ③human-only（含 /login 本機指令）
        ④加一筆晚於 human 的 assistant ⇒ 命中 ④′三筆連續 human 無 assistant ⇒ None 且有限呼叫
        ⑤auto-continuation 單獨 ⇒ None；目錄讀不動 ⇒ None。"""
        self.put(OTHER, {"type": "system", "subtype": "away_summary", "timestamp": self.ago(1).isoformat()})
        self.assertIsNone(self.calls()[0])  # ① mtime 新（剛寫）但無對話記錄
        self.put(OTHER, _rec("assistant", self.ago(40)))
        self.assertIsNone(self.calls()[0])  # ②
        self.put(OTHER, _rec("human", self.ago(5)), _rec("login", self.ago(4)),
                 {"type": "user", "timestamp": self.ago(3).isoformat(), "origin": {"kind": "human"},
                  "message": {"content": "<local-command-stdout>Login successful</local-command-stdout>"}})
        self.assertIsNone(self.calls()[0])  # ③
        self.put(OTHER, _rec("human", self.ago(5)), _rec("login", self.ago(4)), _rec("assistant", self.ago(3)))
        self.assertEqual(self.calls()[0]["sid"], OTHER)  # ④ 證 human 記錄不是被別的原因擋掉
        self.put(OTHER, _rec("human", self.ago(5)), _rec("human", self.ago(4)), _rec("human", self.ago(3)))
        got, n = self.calls()
        self.assertEqual((got, n), (None, 4))  # ④′ 推進到底、不死循環
        self.put(OTHER, _rec("auto-continuation", self.ago(2)))
        self.assertIsNone(self.calls()[0])  # ⑤
        self.assertIsNone(othersession.active(self.proj / "no-such-dir", OWN, self.now))
        self.assertIsNone(othersession.active(None, OWN, self.now))

    def test_at_ctl_110_scan_cap_stops_at_200_and_leaves_a_trace(self) -> None:
        """AT-CTL-110 ④″：driver_after 假實作恆回 human、時戳逐次 +1 秒 ⇒ 恰 200 次、None、痕跡 scan_cap。"""
        self.put(OTHER, _rec("human", self.ago(5)))
        calls = []

        def endless(_path, since, _now):
            calls.append(since)
            return {"timestamp": datetime.fromtimestamp(since + 1).astimezone().isoformat(), "kind": "human"}

        got = othersession.active(self.proj, OWN, self.now, driver_after=endless)
        self.assertIsNone(got)
        self.assertEqual(len(calls), othersession.OTHER_SESSION_SCAN_MAX_STEPS)
        rows = [json.loads(x) for x in (self.proj / "_traces" / "autosdd_session_switch.jsonl")
                .read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["action"] for r in rows if r["event"] == "park_other_session"], ["scan_cap"])

    def test_p3_same_stamp_human_and_assistant_does_not_skip_the_assistant(self) -> None:
        """QA P3②：human 與 assistant 恰同一戳（human 在檔案序先）⇒ 推進 since 不得跳過同戳 assistant。"""
        at = self.ago(3)
        self.put(OTHER, _rec("human", at), _rec("assistant", at))
        self.assertEqual(self.calls()[0]["sid"], OTHER)
        self.put(OTHER, _rec("human", at), _rec("human", at))
        self.assertIsNone(self.calls()[0], "同戳只有 human ⇒ 仍是沒人在動")

    def test_at_ctl_114_single_ruler_loop_and_no_mtime_decision(self) -> None:
        """AT-CTL-114：判活只經 driver_after（迴圈、有上限、只收 assistant）；不用 newest_conversation_at；
        不以 mtime 判活（只有預篩）；不新寫詞表；不被 quota_policy／transcript_activity 頂層 import。"""
        src = (_REPO_ROOT / "tools" / "lib" / "sessionctl" / "othersession.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        self.assertNotIn("newest_conversation_at", src.replace("`newest_conversation_at`", ""))
        loops = [n for n in ast.walk(tree) if isinstance(n, ast.While)]
        self.assertTrue(any("probe" in ast.dump(n) and "since" in ast.dump(n) for n in loops),
                        "driver_after 必須在迴圈內被呼叫且 since 在迴圈體內推進")
        self.assertIn("OTHER_SESSION_SCAN_MAX_STEPS", src)
        self.assertIn('rec["kind"] == "assistant"', src)
        code = "\n".join(ln.split("#")[0] for ln in src.split('"""')[2::2])  # 去掉 docstring 後的程式碼
        for banned in ("synthetic", "origin", "away_summary", "<local-command"):
            self.assertNotIn(banned, code, f"不得另寫詞表：{banned}")
        decide_uses_mtime = [ln for ln in src.splitlines() if "st_mtime" in ln and "max(" not in ln]
        self.assertEqual(decide_uses_mtime, [])
        for rel in ("quota_policy.py", "transcript_activity.py"):
            body = (_REPO_ROOT / "tools" / "lib" / rel).read_text(encoding="utf-8")
            top = [n for n in ast.parse(body).body if isinstance(n, (ast.Import, ast.ImportFrom))]
            self.assertFalse(any("othersession" in ast.dump(n) for n in top), rel)
        self.assertEqual(othersession.SENTINEL_INTERVAL_SECONDS, _planner_interval())


def _planner_interval() -> int:
    text = (_REPO_ROOT / "tools" / "session_resume_planner.py").read_text(encoding="utf-8")
    return int(next(ln for ln in text.splitlines() if ln.startswith("SENTINEL_INTERVAL_SECONDS")).split("=")[1])


class ParkFireOtherSessionTest(P.JobTest):
    """AT-CTL-111／112：`park_fire.run` 前置——另一 session 在動 ⇒ 延後，用盡終局 skip 且出聲。"""

    def setUp(self) -> None:
        super().setUp()
        patch = mock.patch.object(tempfile, "tempdir", str(self.tmp))  # alert 的 note 檔不得落真暫存
        patch.start()
        self.addCleanup(patch.stop)
        self.rearms: list = []

        def fake_rearm(sid, pkg, when, env, now, S, extra=None):
            self.rearms.append((when, extra))
            marker = park.read_marker(sid)
            park.write_marker(dict(marker, **(extra or {})))
            return "ok"

        patch = mock.patch("lib.sessionctl.oldwin_park._rearm", side_effect=fake_rearm)
        patch.start()
        self.addCleanup(patch.stop)
        self.records()

    def other(self, *recs) -> None:
        path = self.tmp / f"{OTHER}.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")

    def _assistant(self, minutes_ago: float = 3):
        return _rec("assistant", self.LATE - timedelta(minutes=minutes_ago))

    def test_at_ctl_111_active_other_session_defers_instead_of_spawning(self) -> None:
        self.other(_rec("human", self.LATE - timedelta(minutes=4)), self._assistant())
        self.assertEqual(self.fire(), 0)
        self.assertEqual((self.spawned, self.resumed), ([], []))
        marker = park.read_marker(P.SID)
        self.assertEqual((marker["status"], marker[othersession.DEFERS_KEY]), ("armed", 1))
        self.assertAlmostEqual(self.rearms[0][0], self.LATE.timestamp() + 900, delta=1)
        rows = [t for t in self.traces() if t["event"] == "park_other_session"]
        self.assertEqual((rows[0]["action"], rows[0]["other_sid"]), ("defer", OTHER))

    def test_at_ctl_111_no_other_session_keeps_the_golden_sequence(self) -> None:
        self.assertEqual(self.fire(), 0)
        self.assertEqual(self.spawned, [self.pkg])
        self.assertEqual([t for t in self.traces() if t["event"] == "park_other_session"], [])

    def test_at_ctl_112_exhausted_defers_skip_terminally_and_announce_once(self) -> None:
        park.write_marker(dict(park.read_marker(P.SID),
                               **{othersession.DEFERS_KEY: othersession.OTHER_SESSION_MAX_DEFERS}))
        self.other(self._assistant())
        with mock.patch("lib.sessionctl.park_announce.announce") as announce:
            self.assertEqual(self.fire(), 0)
        marker = park.read_marker(P.SID)
        self.assertEqual((marker["status"], marker["outcome"]["event"]), ("skipped", "other_session"))
        announce.assert_called_once()
        kw = announce.call_args.kwargs
        self.assertIn("他 session 在動", kw["title"])
        self.assertIn(OTHER[:8], kw["body"])
        self.assertIn(str(self.pkg), kw["body"])
        self.assertEqual(self.spawned, [])
        self.assertEqual(self.rearms, [], "用盡後不再重排")
        actions = [t["action"] for t in self.traces() if t["event"] == "park_other_session"]
        self.assertEqual(actions, ["skip"])

    def test_at_ctl_112_midway_defer_does_not_announce(self) -> None:
        self.other(self._assistant())
        with mock.patch("lib.sessionctl.park_announce.announce") as announce:
            self.fire()
        announce.assert_not_called()

    def test_at_ctl_112_real_announce_writes_handback_and_queue_and_status_line_until_ack(self) -> None:
        import quota_escalation  # noqa: PLC0415

        park.write_marker(dict(park.read_marker(P.SID), desktop_notify="1",
                               **{othersession.DEFERS_KEY: othersession.OTHER_SESSION_MAX_DEFERS}))
        self.other(self._assistant())
        with mock.patch.dict(os.environ, {"AUTOSDD_DESKTOP_NOTIFY": "1"}), \
                mock.patch.object(quota_escalation, "notify", return_value=0) as toast:
            self.assertEqual(self.fire(env={"AUTOSDD_DESKTOP_NOTIFY": "1"}), 0)
        text = (self.bdir / f"{P.SID}_park_other_session.md").read_text(encoding="utf-8")
        for head in ("## 做了什麼", "## 驗了什麼", "## 卡在哪", "## 下一步指令"):
            self.assertIn(head, text)
        queue = quota_escalation._load_queue(quota_escalation.notify_queue_path())  # noqa: SLF001
        self.assertLessEqual(len(queue), 1)
        self.assertLessEqual(toast.call_count, 1)
        (line,) = othersession.status_lines()
        self.assertIn("park 因他 session 在動而終局 skip：", line)
        self.assertIn(str(self.pkg), line)
        from lib.sessionctl import briefline, roster  # noqa: PLC0415

        snap = {"agents": [], "windows": [], "schedules": [], "stale_sentinels": [], "handoffs": []}
        self.assertIn("終局 skip", roster.render_snapshot(snap))
        self.assertIn("終局 skip", briefline.lines(None, os.environ))
        self.pkg.with_suffix(".ack").write_text("acked", encoding="utf-8")
        self.assertEqual(othersession.status_lines(), [])

    def test_at_ctl_112_zero_max_defers_goes_straight_to_terminal_skip(self) -> None:
        self.other(self._assistant())
        with mock.patch.object(othersession, "OTHER_SESSION_MAX_DEFERS", 0), \
                mock.patch("lib.sessionctl.park_announce.announce") as announce:
            self.fire()
        self.assertEqual(park.read_marker(P.SID)["status"], "skipped")
        announce.assert_called_once()

    def test_at_ctl_112_announce_defaults_are_unchanged_for_the_failure_chain(self) -> None:
        with mock.patch("lib.sessionctl.park_announce._enqueue") as enq, \
                mock.patch("lib.sessionctl.park_announce._handback") as hb, \
                mock.patch("lib.sessionctl.park_announce.se_gate.check", return_value=None):
            park_announce.announce(P.SID, self.pkg, park.read_marker(P.SID), [], repo=P._REPO_ROOT
                                   if hasattr(P, "_REPO_ROOT") else None)
        self.assertEqual(enq.call_args.args[0], "park 到點續航失敗")
        self.assertEqual(hb.call_args.args[3:], ("park_failed", None))


for _name in dir(P.JobTest):  # 只留本類自己的測試
    if _name.startswith("test_") and _name not in ParkFireOtherSessionTest.__dict__:
        setattr(ParkFireOtherSessionTest, _name, None)


class ParkEarlyHoldTest(unittest.TestCase):
    """AT-CTL-113：`parkearly._precheck` 回 `other_session`（不提前）。"""

    def test_at_ctl_113_precheck_returns_other_session_and_traces_hold(self) -> None:
        from lib.sessionctl import parkearly  # noqa: PLC0415

        now = datetime.now().astimezone()
        with tempfile.TemporaryDirectory() as td, \
                mock.patch.dict(os.environ, {"AUTOSDD_TRACE_DIR": td}):
            proj = Path(td)
            (proj / f"{OTHER}.jsonl").write_text(json.dumps(_rec("assistant", now - timedelta(minutes=2))) + "\n",
                                                 encoding="utf-8")
            S = {"transcript": lambda _s: proj / f"{OWN}.jsonl"}
            self.assertEqual(parkearly._other_session({"sid": OWN}, {}, now, S), "other_session")  # noqa: SLF001
            rows = [json.loads(x) for x in (proj / "autosdd_session_switch.jsonl").read_text("utf-8").splitlines()]
            self.assertEqual(rows[-1]["action"], "hold")
            (proj / f"{OTHER}.jsonl").write_text(json.dumps(_rec("assistant", now - timedelta(hours=2))) + "\n",
                                                 encoding="utf-8")
            self.assertEqual(parkearly._other_session({"sid": OWN}, {}, now, S), "")  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
