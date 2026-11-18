"""R3 WP-4B：監督憑證／Stop 監督閘／派工附註／status 一行／crons 記錄（AT-W11～W14、FR-S4）。

WHY：主控派完背景子代理就結束回合、沒人叫醒它（21 天 655 區間）。這裡釘「沒掛 watch 就推回一次、
掛了就放行並改字樣」，以及每條 fail-open 方向。時鐘、心跳讀取、pid 探測皆參數注入；
`AUTOSDD_TRACE_DIR`／`AUTOSDD_HANDOFF_DIR`／`AUTOSDD_QUOTA_CACHE_DIR` 圍到暫存，
不碰真實 `~/.autosdd`。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "tools"))
sys.path.insert(0, str(_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_ROOT / "tools" / "tests"))

from test_sessionctl_converge import SID  # noqa: E402
from test_sessionctl_converge import _Fence as _ConvFenceTestCase  # noqa: E402

from lib.sessionctl import converge, roster, supervise, watch  # noqa: E402
from lib.wastecensus import supervision  # noqa: E402

NOW = 1_800_000_000.0


def _iso(epoch: float) -> str:
    from datetime import datetime  # noqa: PLC0415

    return datetime.fromtimestamp(epoch).astimezone().isoformat(timespec="seconds")


def _beat(age: float = 10.0, pid: int = 4242) -> dict:
    return {"pid": pid, "heartbeat_at": _iso(NOW - age), "started_at": _iso(NOW - 600),
            "keepwarm_at": _iso(NOW + 1800), "stall_min": 15}


AGENT = {"type": "subagent", "id": "a1", "status": "running", "description": "工人"}
WATCH_SHELL = {"type": "shell", "id": "s1", "status": "running",
               "command": "python tools/sessionctl.py watch > w.txt"}


def _payload(*tasks, **extra) -> dict:
    return {"hook_event_name": "Stop", "session_id": SID, "background_tasks": list(tasks), **extra}


def _kw(beat=None, *, alive=True, boom=False):
    def reader(_sid):
        if boom:
            raise OSError("讀不動")
        return beat
    return {"heartbeat_reader": reader, "alive": lambda _pid: alive}


class _Env(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="wp4b-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        patcher = mock.patch.dict(os.environ, {
            "AUTOSDD_TRACE_DIR": str(self.tmp / "trace"),
            "AUTOSDD_HANDOFF_DIR": str(self.tmp / "handoff"),
            "AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp / "quota")})
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.tmp / "trace").mkdir()
        self.env: dict = {}


class CredentialTests(_Env):
    """AT-W11：憑證四態＋fail-open。"""

    def test_main_proof_with_fresh_or_missing_heartbeat_is_valid(self):
        """WHY：watch 活著且心跳新鮮（或剛啟動還沒寫心跳）＝結束時會叫醒主控，不該被推回。"""
        for beat in (_beat(5), None):
            with self.subTest(beat=beat):
                self.assertEqual(supervise.credential(_payload(AGENT, WATCH_SHELL), SID, NOW,
                                                      **_kw(beat)), "valid")

    def test_main_proof_recognises_quoted_script_path(self):
        """WHY：PowerShell／含空白路徑的真機命令是「& 'py' '<repo>\\sessionctl.py' watch」，
        字面子字串比不到會把有效 watch 誤判成沒掛（RV-S2 真機實證）；反向變體＝別的子命令仍不算。"""
        for cmd in ("& 'py.exe' 'C:\\r\\tools\\sessionctl.py' watch --sid x",  # platform-ok: 命令串
                    "python \"C:/r/tools/sessionctl.py\" watch"):  # platform-ok: 命令字串形態
            shell = {"type": "shell", "id": "s2", "status": "running", "command": cmd}
            with self.subTest(cmd=cmd):
                self.assertEqual(supervise.credential(_payload(AGENT, shell), SID, NOW,
                                                      **_kw(None)), "valid")
        for cmd in ("python tools/sessionctl.py watcher", "python tools/sessionctl.py status",
                    "python tools/sessionctl.py' park"):
            shell = {"type": "shell", "id": "s3", "status": "running", "command": cmd}
            with self.subTest(cmd=cmd):
                self.assertEqual(supervise.credential(_payload(AGENT, shell), SID, NOW,
                                                      **_kw(None)), "none")

    def test_main_proof_with_stale_heartbeat_is_stuck(self):
        """WHY：shell 還在但心跳停了＝watch 卡死，掛著等於沒掛；要先 TaskStop 再重掛。"""
        got = supervise.credential(_payload(AGENT, WATCH_SHELL), SID, NOW, **_kw(_beat(999)))
        self.assertEqual(got, "stuck")

    def test_no_main_proof_is_none_even_with_fresh_heartbeat(self):
        """WHY：別的終端手跑的 watch 結束不會叫醒本 session，心跳新鮮也不算憑證。"""
        self.assertEqual(supervise.credential(_payload(AGENT), SID, NOW, **_kw(_beat(5))), "none")

    def test_finished_or_other_shell_is_not_proof(self):
        """WHY：已結束的 watch、或不是 watch 的 shell 都不是看管。"""
        done = {**WATCH_SHELL, "status": "completed"}
        other = {"type": "shell", "status": "running", "command": "pytest -q"}
        for tasks in ((done,), (other,)):
            with self.subTest(tasks=tasks):
                self.assertEqual(supervise.credential(_payload(*tasks), SID, NOW, **_kw(_beat(5))),
                                 "none")

    def test_old_harness_without_field_needs_fresh_heartbeat_and_live_pid(self):
        """WHY：舊 harness 沒有 background_tasks 欄，只剩副證；pid 死了的新鮮心跳是殘檔。"""
        legacy = {"session_id": SID}
        self.assertEqual(supervise.credential(legacy, SID, NOW, **_kw(_beat(5))), "valid")
        self.assertEqual(supervise.credential(legacy, SID, NOW, **_kw(_beat(5), alive=False)),
        "none")
        self.assertEqual(supervise.credential(legacy, SID, NOW, **_kw(_beat(999))), "none")
        self.assertEqual(supervise.credential(legacy, SID, NOW, **_kw(None)), "none")

    def test_any_exception_fails_open_to_valid(self):
        """WHY：讀不動心跳不可擋死回合結束（寧可漏推）。"""
        self.assertEqual(supervise.credential(_payload(AGENT, WATCH_SHELL), SID, NOW,
                                              **_kw(boom=True)), "valid")

    def test_freshness_threshold_is_six_poll_intervals(self):
        """WHY（方向鎖）：180 秒＝6 個輪詢間隔；調小會因單次抖動誤判卡死、調大讓卡死放太久。"""
        self.assertEqual(supervise.HEARTBEAT_FRESH_SECONDS, 6 * watch.POLL_SECONDS)
        edge = supervise.credential(_payload(WATCH_SHELL), SID, NOW, **_kw(_beat(180)))
        over = supervise.credential(_payload(WATCH_SHELL), SID, NOW, **_kw(_beat(181)))
        self.assertEqual((edge, over), ("valid", "stuck"))


class StopGateTests(_Env):
    """AT-W12：監督閘。"""

    def verdict(self, payload, env=None, beat=None, **kw):
        return supervise.stop_verdict(payload, self.env if env is None else env, NOW,
                                      **_kw(beat), **kw)

    def traces(self) -> list[dict]:
        path = self.tmp / "trace" / "autosdd_session_switch.jsonl"
        return ([json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
                if path.exists() else [])

    def test_no_credential_blocks_with_exact_command_and_traces(self):
        """WHY：沒人看管就結束回合＝子代理卡死也沒人知道；reason 要給確切指令，並落痕跡供量測。"""
        why = self.verdict(_payload(AGENT))
        for needle in ("python tools/sessionctl.py watch", "run_in_background", "第二次 Stop 放行"):
            self.assertIn(needle, why)
        row = [r for r in self.traces() if r["event"] == supervise.EV_SUPERVISE_STOP_BLOCK][0]
        self.assertEqual((row["sid"], row["n_agents"], row["credential"]), (SID, 1, "none"))

    def test_stuck_reason_says_taskstop_first(self):
        """WHY：卡死的 watch 還佔著 shell，直接再掛會有兩支；要先 TaskStop。"""
        why = self.verdict(_payload(AGENT, WATCH_SHELL), beat=_beat(999))
        self.assertIn("TaskStop", why)
        self.assertEqual(self.traces()[-1]["credential"], "stuck")

    def test_valid_credential_does_not_block_and_message_says_watched(self):
        """WHY：有效看管就放行；Stop 出聲改成「看管中」字樣，且帶下次叫醒時刻與停滯門檻。"""
        payload = _payload(AGENT, WATCH_SHELL)
        self.assertEqual(self.verdict(payload, beat=_beat(5)), "")
        text = supervise.watching_text(payload, SID, 1, NOW, **_kw(_beat(5)))
        for needle in ("1 支背景代理由監督程序看管中", "下次叫醒最晚", "停滯門檻 15 分"):
            self.assertIn(needle, text)

    def test_loop_brake_unattended_and_modes(self):
        """WHY：stop_hook_active＝第二次 Stop 必放行；無人窗口不推；off 不做事；notify 只出聲不推。
        """
        base = _payload(AGENT)
        self.assertEqual(self.verdict({**base, "stop_hook_active": True}), "")
        self.assertEqual(self.verdict(base, {"AUTOSDD_UNATTENDED": "1"}), "")
        self.assertEqual(self.verdict(base, {"AUTOSDD_SESSION_SWITCH_MODE": "off"}), "")
        self.assertEqual(self.verdict(base, {"AUTOSDD_SESSION_SWITCH_MODE": "notify"}), "")
        self.assertEqual(self.traces(), [])

    def test_only_subagents_trigger(self):
        """WHY：背景 shell／monitor 不是「會自己卡死的工人」，只有 running 子代理才需要看管。"""
        for tasks in ((WATCH_SHELL,), ({"type": "shell", "status": "running", "command": "x"},),
                      ({**AGENT, "status": "completed"},), ()):
            with self.subTest(tasks=tasks):
                self.assertEqual(self.verdict(_payload(*tasks)), "")

    def test_roster_stop_message_keeps_legacy_head_without_credential(self):
        """WHY：量測判準認「本回合結束時仍有」開頭；沒憑證時字樣不得改。"""
        with mock.patch.object(supervise, "read_heartbeat", return_value=None):
            self.assertTrue(roster.stop_message(_payload(AGENT)).startswith("本回合結束時仍有"))

    def test_roster_stop_message_says_watched_with_credential(self):
        """WHY：roster 薄呼叫 supervise；有效憑證時出「看管中」。"""
        with mock.patch.object(supervise, "read_heartbeat", return_value=_beat(5)):
            self.assertIn("看管中", roster.stop_message(_payload(AGENT, WATCH_SHELL)))

    def test_event_name_matches_the_measurement_side(self):
        """WHY（A-8）：sessionctl 不得 import wastecensus；兩邊的事件名只能靠測試核對相等。"""
        self.assertEqual(supervise.EV_SUPERVISE_STOP_BLOCK, supervision.EV_SUPERVISE_STOP_BLOCK)


class ColdWakeVsSuperviseTests(_ConvFenceTestCase):
    """AT-W13：冷叫醒閘與監督閘同時成立 ⇒ 只出冷叫醒 reason。"""

    def test_finalized_package_wins_over_supervise(self):
        """WHY：已交棒的 session 該 TaskStop 而不是再掛 watch——掛了反而多一個會叫醒它的背景任務。"""
        self.main(100_000)
        # E-CW-1：冷叫醒閘的前提是「已封存」（`--finalize` 寫 `.sealed`），不是主控層寫完
        self.package(finalized=True).with_suffix(".sealed").write_text(
            "2026-11-17T09:00:00+08:00\n", encoding="utf-8")
        why = converge.stop_verdict(self.stop(background_tasks=[AGENT, WATCH_SHELL]), self.env)
        self.assertIn("冷叫醒閘", why)
        self.assertNotIn("監督閘", why)

    def test_unfinalized_falls_to_supervise_gate(self):
        """WHY：沒交棒的在飛代理沒憑證 ⇒ 走監督閘；Stop 路徑同時記 crons，不影響判決。"""
        self.main(100_000)
        why = converge.stop_verdict(self.stop(background_tasks=[AGENT], session_crons=[]), self.env)
        self.assertIn("監督閘", why)
        self.assertIs(supervise.crons_state(SID), False)


class DispatchNoteTests(_Env):
    """AT-W14：派工附註三格。"""

    def pre(self, **extra) -> dict:
        return {"hook_event_name": "PreToolUse", "tool_name": "Agent", "session_id": SID, **extra}

    def test_note_when_no_fresh_heartbeat(self):
        """WHY：派工瞬間就提醒「同一回合掛監督」，比等 Stop 才推回早一步。"""
        text = supervise.dispatch_note(self.pre(), self.env, NOW,
        **{"heartbeat_reader": lambda _s: None})
        for needle in ("python tools/sessionctl.py watch", "8.4 萬"):
            self.assertIn(needle, text)
        self.assertTrue(supervise.dispatch_note({**self.pre(), "tool_name": "Task"}, self.env, NOW,
                                                heartbeat_reader=lambda _s: None))

    def test_silent_with_fresh_heartbeat_subagent_call_unattended_or_other_tool(self):
        """WHY：已有看管不囉嗦；子代理自己的呼叫、無人窗口、非派工工具都不出聲。"""
        fresh = {"heartbeat_reader": lambda _s: _beat(5)}
        self.assertEqual(supervise.dispatch_note(self.pre(), self.env, NOW, **fresh), "")
        quiet = {"heartbeat_reader": lambda _s: None}
        self.assertEqual(supervise.dispatch_note(self.pre(agent_id="a9"), self.env, NOW, **quiet),
        "")
        self.assertEqual(supervise.dispatch_note(self.pre(), {"AUTOSDD_UNATTENDED": "1"}, NOW,
        **quiet), "")
        self.assertEqual(supervise.dispatch_note({**self.pre(), "tool_name": "Read"}, self.env, NOW,
                                                 **quiet), "")

    def test_converge_verdict_carries_the_note_when_the_gate_passes(self):
        """WHY：函式層接線——hook 跳板對 rc 0 的文字會轉成 additionalContext，不必改 hook。"""
        rc, text = converge.converge_verdict(self.pre(), {})
        self.assertEqual(rc, 0)
        self.assertIn("watch", text)


class StatusAndCronsTests(_Env):
    def test_status_line_three_states(self):
        """WHY：status 沒有 payload，只能依心跳檔；字樣標明依據，避免被當成確證。"""
        none = supervise.status_line(SID, NOW, **_kw(None))
        ok = supervise.status_line(SID, NOW, **_kw(_beat(5)))
        stuck = supervise.status_line(SID, NOW, **_kw(_beat(999)))
        self.assertTrue(all("依心跳檔" in s for s in (none, ok, stuck)))
        self.assertTrue(none.startswith("監督：無"))
        self.assertIn("有效", ok)
        self.assertIn("卡死", stuck)
        self.assertIn("量不到", supervise.status_line(SID, NOW, **_kw(boom=True)))

    def test_status_verb_prints_the_line(self):
        """WHY：入口接線——status 結尾多一行監督（取 CLAUDE_CODE_SESSION_ID）。"""
        import importlib.util  # noqa: PLC0415 — `sessionctl` 與 lib 套件同名，按路徑載入入口檔

        spec = importlib.util.spec_from_file_location("sessionctl_entry",
                                                      _ROOT / "tools" / "sessionctl.py")
        sessionctl_cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sessionctl_cli)
        out = mock.MagicMock()
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": SID}), \
                mock.patch.object(roster, "cli", return_value=0), \
                mock.patch.object(sys, "stdout", out):
            self.assertEqual(sessionctl_cli.main(["status"]), 0)
        self.assertIn("監督：", "".join(c.args[0] for c in out.write.call_args_list))

    def test_crons_three_states(self):
        """WHY：WP-5 要知道排程是否存在；沒有該欄不寫（讀回 None），不把「不知道」寫成 False。"""
        self.assertIsNone(supervise.crons_state(SID))
        supervise.record_crons({"session_id": SID}, SID)
        self.assertIsNone(supervise.crons_state(SID))
        supervise.record_crons({"session_crons": [{"id": 1}]}, SID)
        self.assertIs(supervise.crons_state(SID), True)
        supervise.record_crons({"session_crons": []}, SID)
        self.assertIs(supervise.crons_state(SID), False)


if __name__ == "__main__":
    unittest.main()
