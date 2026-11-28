#!/usr/bin/env python3
"""WP-SW REQ-CTL-50（TCS-Control §8；AT-CTL-97～103）：排程入口崩潰護欄 `crashguard`。

WHY：2026-11-28 10:21:52 舊哨兵在 pythonw 下崩潰，排程器自報 `LastTaskResult=1`、
`NextRunTime` 空白，
崩潰沒有任何痕跡與告警。本檔鎖「未捕捉例外必留痕＋告警＋重排；連續 3 次停止並 loud；正常 tick
歸零」。
縫：FS（tmp 圍籬）、NOW、假告警／假重排；真告警行為（HELM-01：只寫紙＋入佇列、不敲桌面）另斷言。
"""
from __future__ import annotations

import ast
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

# 模組引用而非 from-import：避免把對方的 TestCase 帶進本檔重跑
import test_sessionctl_park as P  # noqa: E402

from lib.sessionctl import crashguard, park  # noqa: E402

SID = "406454ea-91fc-4481-9c11-b28ed7d9e95f"
NOW = datetime(2026, 11, 28, 10, 21, 52).astimezone()


class _Ref:
    """記憶體內的狀態塊（`read`／`write` 縫）。"""

    def __init__(self, state=None, *, plan=None):
        self.state, self.plan, self.sid, self.task = state, plan, SID, "AutoSDD_Sentinel_x"
        self.writes = 0

    def read(self):
        return None if self.state is None else dict(self.state)

    def write(self, state):
        self.writes += 1
        self.state = dict(state)


def _state(**over):
    return {"session_id": SID, "task_name": "AutoSDD_Sentinel_x", "state": "waiting",
            "plan_path": "p", "log_path": "l", **over}


class _Fence(P._Fence):
    def setUp(self) -> None:
        super().setUp()
        patch = mock.patch.dict(os.environ, {"AUTOSDD_DESKTOP_NOTIFY": "1"})
        patch.start()
        self.addCleanup(patch.stop)
        patch2 = mock.patch.object(tempfile, "tempdir", str(self.tmp))
        patch2.start()
        self.addCleanup(patch2.stop)
        self.alerts: list = []
        self.rearms: list = []

    def alert(self, reason, state, **kw):
        self.alerts.append((reason, kw))
        return {}

    def events(self, name):
        return [t for t in self.traces() if t["event"] == name]

    def crash(self, ref, body=None, *, on_crash="default", now=NOW):
        def boom():
            raise AttributeError("'NoneType' object has no attribute 'write'")

        def rearm(st, at, info):
            self.rearms.append((st, at, info))
            return 0

        return crashguard.run("sentinel-tick", body or boom, state_ref=ref, now=now,
            alert=self.alert,
                              on_crash=rearm if on_crash == "default" else on_crash)


class RunTest(_Fence, unittest.TestCase):
    def test_at_ctl_97_crash_leaves_trace_alerts_once_and_rearms_once(self) -> None:
        """AT-CTL-97：AttributeError ⇒ 痕跡欄位齊全、alert(loud) 恰一次、
        重排恰一次且時刻＝now＋900、rc 1。"""
        ref = _Ref(_state())
        rc = self.crash(ref)
        self.assertEqual(rc, 1)
        row = self.events("sentinel_crashed")[0]
        for key in ("exc_type", "file", "line", "tb", "sid", "task", "streak", "entry"):
            self.assertIn(key, row)
        self.assertEqual((row["exc_type"], row["streak"], row["sid"]), ("AttributeError", 1, SID))
        self.assertLessEqual(len(row["tb"]), crashguard.CRASH_TB_MAX_CHARS)
        self.assertEqual(len(self.alerts), 1)
        self.assertTrue(self.alerts[0][1]["loud"])
        self.assertIn("AttributeError", self.alerts[0][0])
        self.assertEqual(len(self.rearms), 1)
        self.assertEqual(self.rearms[0][1], NOW + timedelta(seconds=900))
        self.assertEqual(ref.state["crash_streak"], 1)

    def test_at_ctl_98_unreadable_state_alerts_only_and_guard_never_throws(self) -> None:
        """AT-CTL-98：狀態塊讀不出 ⇒ 只告警、不重排、不二次拋、痕跡仍落；on_crash 自身拋 ⇒ 不拋。"""
        self.assertEqual(self.crash(_Ref(None)), 1)
        self.assertEqual((len(self.alerts), len(self.rearms)), (1, 0))
        self.assertEqual(len(self.events("sentinel_crashed")), 1)

        def bad(*_a):
            raise RuntimeError("rearm exploded")

        self.assertEqual(self.crash(_Ref(_state()), on_crash=bad), 1)
        self.assertEqual(len(self.events("sentinel_crashed")), 2)

    def test_at_ctl_99_three_crashes_stop_rearm_loop_and_cleared_resets(self) -> None:
        """AT-CTL-99：連續三次崩潰第三次起不重排、落 crash_loop(rearmed=false)、alert 恰一次、
        handback 存在；
        中間正常 tick ⇒ streak 歸零並落 cleared；第四次崩潰重新計 1。"""
        ref = _Ref(_state())
        self.crash(ref)
        self.crash(ref)
        self.assertEqual((len(self.rearms), ref.state["crash_streak"]), (2, 2))
        n = len(self.alerts)
        self.crash(ref)
        self.assertEqual(len(self.rearms), 2, "第三次不得再重排")
        loop = self.events("sentinel_crash_loop")
        self.assertEqual((len(loop), loop[0]["rearmed"], loop[0]["streak"]), (1, False, 3))
        self.assertEqual(len(self.alerts) - n, 1)
        hand = (self.bdir / f"{SID}_sentinel_crash_loop.md").read_text(encoding="utf-8")
        self.assertIn("--arm-sentinel --session-id " + SID, hand)
        for head in ("## 做了什麼", "## 驗了什麼", "## 卡在哪", "## 下一步指令"):
            self.assertIn(head, hand)
        self.assertEqual(crashguard.run("sentinel-tick", lambda: 0, state_ref=ref,
            alert=self.alert), 0)
        self.assertEqual(ref.state["crash_streak"], 0)
        self.assertEqual(len(self.events("sentinel_crash_cleared")), 1)
        crashguard.run("sentinel-tick", lambda: 0, state_ref=ref, alert=self.alert)
        self.assertEqual(len(self.events("sentinel_crash_cleared")), 1, "streak 本來就 0 不再落")
        self.crash(ref)
        self.assertEqual(ref.state["crash_streak"], 1)

    def test_at_ctl_99_visibility_status_line_until_cleared_or_gc(self) -> None:
        """AT-CTL-99①③：最新為 crash_loop ⇒ 一行；其後 cleared 或 sentinel_gc ⇒ 不再顯示。"""
        ref = _Ref(_state(crash_streak=2))
        self.crash(ref)
        (line,) = crashguard.status_lines()
        for needle in ("哨兵因連續崩潰停止：", "AutoSDD_Sentinel_x", SID[:8], "AttributeError@"):
            self.assertIn(needle, line)
        for event in ("sentinel_crash_cleared", "sentinel_gc"):
            from lib.sessionctl import switch  # noqa: PLC0415

            self.crash(_Ref(_state(crash_streak=2)))
            self.assertEqual(len(crashguard.status_lines()), 1)
            switch.trace(event, sid=SID, task="x")
            self.assertEqual(crashguard.status_lines(), [], event)

    def test_at_ctl_99_visibility_status_and_briefline_show_then_hide_the_line(self) -> None:
        """AT-CTL-99②：`sessionctl status`（render_snapshot）與 SessionStart 簡報兩處都含該行；
        其後 cleared ⇒ 兩處皆不再顯示。"""
        from lib.sessionctl import briefline, roster, switch  # noqa: PLC0415

        snap = {"agents": [], "windows": [], "schedules": [], "stale_sentinels": [], "handoffs": []}
        self.assertNotIn("哨兵因連續崩潰停止", roster.render_snapshot(snap))
        self.crash(_Ref(_state(crash_streak=2)))
        self.assertIn("哨兵因連續崩潰停止：", roster.render_snapshot(snap))
        self.assertIn("哨兵因連續崩潰停止：", briefline.lines(None, os.environ))
        switch.trace("sentinel_crash_cleared", sid=SID, task="x")
        self.assertNotIn("哨兵因連續崩潰停止", roster.render_snapshot(snap))
        self.assertNotIn("哨兵因連續崩潰停止", briefline.lines(None, os.environ))

    def test_at_ctl_99_real_alert_writes_note_and_queue_but_never_a_toast(self) -> None:
        """AT-CTL-99④：真 alert（HELM-01）：dead_agents==0 ⇒ note 含例外型別、通知佇列恰新增一筆、
        桌面通知縫 0 次（不斷言 toast）。佇列需 AUTOSDD_DESKTOP_NOTIFY 已設（queue_notify
        的前置）。"""
        import quota_escalation  # noqa: PLC0415

        with mock.patch.object(quota_escalation, "notify") as toast:
            rc = crashguard.run("sentinel-tick", lambda: 1 / 0, state_ref=_Ref(_state()),
                                on_crash=lambda *_a: 0)
        self.assertEqual(rc, 1)
        self.assertIn("ZeroDivisionError", quota_escalation.note_path().read_text(encoding="utf-8"))
        queue = quota_escalation._load_queue(quota_escalation.notify_queue_path())  # noqa: SLF001
        self.assertEqual(len(queue), 1)
        toast.assert_not_called()

    def test_at_ctl_103_normal_return_value_passes_through(self) -> None:
        """AT-CTL-103：正常回傳值原樣回傳（rc 不被吞）；SystemExit 不攔。"""
        for rc in (0, 1, 7):
            self.assertEqual(crashguard.run("sentinel-tick", lambda rc=rc: rc, alert=self.alert),
                rc)
        with self.assertRaises(SystemExit):
            crashguard.run("sentinel-tick", lambda: sys.exit(5), alert=self.alert)
        self.assertEqual(self.traces(), [])


class ParkFireCrashTest(P.JobTest):
    """AT-CTL-100：`park --fire` 崩潰 ⇒ park_job_crashed＋標記走既有失敗鏈結算 failed。"""

    def setUp(self) -> None:
        super().setUp()
        # alert 的 note 檔不得落真暫存
        patch = mock.patch.object(tempfile, "tempdir", str(self.tmp))
        patch.start()
        self.addCleanup(patch.stop)
    def test_at_ctl_100_park_fire_crash_settles_failed_and_announces(self) -> None:
        self.records()
        argv = ["--session-id", P.SID, "--fire", "--job", self.label, "--pkg", str(self.pkg),
                "--fire-at", P.RESET.isoformat()]
        with mock.patch("lib.sessionctl.park_fire.run", side_effect=OSError("disk gone")), \
                mock.patch("lib.sessionctl.park_announce.announce") as announce:
            rc = crashguard.run_park(lambda a: self.cli.run(a, env=self.env, now=self.LATE, seams={
                "backend": self.backend}), argv)
        self.assertEqual(rc, 1)
        marker = park.read_marker(P.SID)
        self.assertEqual(marker["status"], "failed")
        self.assertEqual(marker["outcome"]["event"], "park_job_crashed")
        announce.assert_called_once()
        row = next(t for t in self.traces() if t["event"] == "park_job_crashed")
        self.assertEqual(row["exc_type"], "OSError")

    def test_at_ctl_100_refused_never_enters_the_crash_path(self) -> None:
        """AT-CTL-100：L1 拒絕（refused）是 `park_cli._cmd_fire` 內的終局、不拋 ⇒ 不進本路。"""
        self.assertEqual(crashguard.run_park(lambda _a: 0, ["--fire"]), 0)
        self.assertEqual([t for t in self.traces() if t["event"] == "park_job_crashed"], [])


for _name in dir(P.JobTest):  # 只留本類自己的測試；繼承來的 JobTest 案例不在這裡重跑
    if _name.startswith("test_") and _name not in ParkFireCrashTest.__dict__:
        setattr(ParkFireCrashTest, _name, None)


class StaticTest(unittest.TestCase):
    TOOLS = _REPO_ROOT / "tools"

    def test_at_ctl_101_every_scheduled_entry_is_listed_in_entries(self) -> None:
        """AT-CTL-101：三站點（park_cli.job_argv／oldwin_sched.job_argv／planner 註冊腳本）
        產生的入口旗標
        都列在 `crashguard.ENTRIES`；人為新增未入表入口 ⇒ 紅（負控）。"""
        listed = {flag for (_file, flag) in crashguard.ENTRIES.values()}
        park_cli = (self.TOOLS / "lib" / "sessionctl" / "park_cli.py").read_text(encoding="utf-8")
        oldwin = (self.TOOLS / "lib" / "sessionctl" / "oldwin_sched.py").read_text(encoding="utf-8")
        planner = (self.TOOLS / "session_resume_planner.py").read_text(encoding="utf-8")
        self.assertIn('"--fire"', park_cli)
        self.assertIn("--fire", listed)
        self.assertIn('"--retry"', oldwin)
        self.assertIn("--retry", listed)
        for tick in ("SENTINEL_TICK", "RESUME_TICK"):
            self.assertIn(tick, planner)
        self.assertLessEqual({"--sentinel-tick", "--resume-tick"}, listed)

        def entries_of(text: str) -> set[str]:  # 掃入口旗標字面（`--xxx-tick`）
            import re  # noqa: PLC0415

            return set(re.findall(r'"(--[a-z]+-tick)"', text))

        self.assertEqual(entries_of(planner) - listed, set())
        self.assertEqual(entries_of(planner + '\n"--ghost-tick"') - listed, {"--ghost-tick"},
            "負控")

    def test_at_ctl_102_planner_dispatch_goes_through_crashguard_within_loc_budget(self) -> None:
        """AT-CTL-102：兩個 tick 分派都經 crashguard，且 planner 沒有內聯判準（無 crash_streak
        字面）。"""
        text = (self.TOOLS / "session_resume_planner.py").read_text(encoding="utf-8")
        tree = ast.parse(text)
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        hits = [ln for ln in ast.get_source_segment(text, main).splitlines()
                if "planner_tick(" in ln]
        self.assertEqual(len(hits), 2)
        self.assertNotIn("crash_streak", text)
        self.assertNotIn("sentinel_crashed", text)


if __name__ == "__main__":
    unittest.main()
