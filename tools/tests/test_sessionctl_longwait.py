"""tools/lib/sessionctl/longwait.py：子代理長等待 runlong／waitfor＋長前景閘（R216 WP-D；
TCS-SessionSwitch-CostModel REQ-SS-10～12、AT-SS-30～36、MU-13～16）。

目標（掌舵者 2026-11-18「專注在不要讓Cache過期!」）：子代理快取壽命 5 分鐘，前景等超過它下一回合整份
上下文重寫；本檔守「分段等待」與「擋長前景」兩條路。縫：真子行程（runlong／waitfor 都以 CLI 真跑）、
假時鐘、`env` mapping、`AUTOSDD_TRACE_DIR` 圍到暫存；不開測試用環境變數、不 monkeypatch 被測模組。
payload 形狀取自 2026-11-19 真 `claude -p` 的 PreToolUse 傾印（子代理的 PowerShell 呼叫帶
`agent_id`／
`agent_type`；`tool_input` 鍵＝command／timeout／description，`run_in_background` 只在設了才出現）。
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

from lib.sessionctl import longwait  # noqa: E402

SESSIONCTL = _REPO_ROOT / "tools" / "sessionctl.py"
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _payload(tool="PowerShell", *, agent="ae69f50e699e37cc2", timeout=300_000,
             command="Write-Output hi", **extra) -> dict:
    tin = {"command": command, "description": "d", **extra}
    if timeout is not None:
        tin["timeout"] = timeout
    pl = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tin,
          "session_id": "s", "tool_use_id": "t"}
    if agent:
        pl.update(agent_id=agent, agent_type="general-purpose")
    return pl


def _cli(*argv: str, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SESSIONCTL), *argv], capture_output=True, text=True,
                          encoding="utf-8", timeout=timeout, creationflags=NOWIN,
                          env={**os.environ, "PYTHONUTF8": "1"}, check=False)


class LongForegroundGateTest(unittest.TestCase):
    """AT-SS-33～36、MU-13～15：只擋「子代理＋前景＋timeout > 270000」。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.env = {"AUTOSDD_TRACE_DIR": self._tmp.name}
        self._old = os.environ.get("AUTOSDD_TRACE_DIR")
        os.environ["AUTOSDD_TRACE_DIR"] = self._tmp.name
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self._old is None:
            os.environ.pop("AUTOSDD_TRACE_DIR", None)
        else:
            os.environ["AUTOSDD_TRACE_DIR"] = self._old

    def test_subagent_foreground_long_timeout_is_blocked_with_both_commands(self) -> None:
        """AT-SS-33：擋得住，且訊息指路 runlong 與 waitfor（否則子代理被擋了不知道改什麼）。"""
        for tool in ("PowerShell", "Bash"):
            rc, text = longwait.pretool_verdict(_payload(tool), self.env)
            self.assertEqual(rc, 2, tool)
            self.assertIn("runlong", text)
            self.assertIn("waitfor", text)
            self.assertIn("keepwarm-ok", text)

    def test_boundary_270000_passes_and_270001_blocks(self) -> None:
        """MU-13：`>` 改 `>=` 或 270000 改 300000 ⇒ 這裡紅（邊界值是設計的核心常數）。"""
        self.assertEqual(longwait.pretool_verdict(_payload(timeout=270_000), self.env), (0, ""))
        self.assertEqual(longwait.pretool_verdict(_payload(timeout=270_001), self.env)[0], 2)
        self.assertEqual(longwait.LONG_FG_MS, 270_000)

    def test_waitfor_own_recommended_timeout_is_never_blocked(self) -> None:
        """waitfor 的建議前景 timeout 必須在閘之下，否則「指路」的指令自己被自己擋。"""
        self.assertLessEqual(longwait.WAIT_FG_TIMEOUT_MS, longwait.LONG_FG_MS)
        self.assertGreater(longwait.WAIT_FG_TIMEOUT_MS / 1000, longwait.WAIT_CEIL_SEC)
        payload = _payload(timeout=longwait.WAIT_FG_TIMEOUT_MS)
        self.assertEqual(longwait.pretool_verdict(payload, self.env), (0, ""))

    def test_main_agent_is_not_judged(self) -> None:
        """MU-14：主控（無 agent_id）快取 1 小時，等 5 分鐘以上不是洞；對主控也判會擋掉正常工作。"""
        self.assertEqual(longwait.pretool_verdict(_payload(agent=None), self.env), (0, ""))
        self.assertEqual(longwait.pretool_verdict(_payload(agent=""), self.env), (0, ""))

    def test_background_calls_and_other_tools_pass(self) -> None:
        """AT-SS-34：背景呼叫（runlong 本體）與非 shell 工具不擋——擋了 runlong 自己就沒路可走。"""
        self.assertEqual(longwait.pretool_verdict(_payload(run_in_background=True), self.env),
                         (0, ""))
        self.assertEqual(longwait.pretool_verdict(_payload("Read"), self.env), (0, ""))
        self.assertEqual(longwait.pretool_verdict(_payload("Agent"), self.env), (0, ""))
        verdict = longwait.pretool_verdict(_payload(run_in_background=False), self.env)
        self.assertEqual(verdict[0], 2, "run_in_background=False 是前景，仍擋")

    def test_default_and_short_timeouts_pass(self) -> None:
        """沒設 timeout（預設 120 秒）或短 timeout 不擋：要超過 5 分鐘必須顯式設大，判準才精確。"""
        self.assertEqual(longwait.pretool_verdict(_payload(timeout=None), self.env), (0, ""))
        self.assertEqual(longwait.pretool_verdict(_payload(timeout=120_000), self.env), (0, ""))

    def test_inline_exemption_needs_a_reason_and_dies_when_unattended(self) -> None:
        """AT-SS-35、MU-15：`# keepwarm-ok: <WHY>` 放行；理由空白不放行；
        無人窗口豁免無效（無人回合自己
        寫得出豁免，同其他守衛）。"""
        cmd = "Invoke-WebRequest https://x/big.iso   # keepwarm-ok: 一次性下載大檔無法分段"
        self.assertEqual(longwait.pretool_verdict(_payload(command=cmd), self.env), (0, ""))
        self.assertEqual(longwait.pretool_verdict(
            _payload(command=cmd), {**self.env, "AUTOSDD_UNATTENDED": "1"})[0], 2)
        for empty in ("x # keepwarm-ok:", "x # keepwarm-ok:  "):
            self.assertEqual(
                longwait.pretool_verdict(_payload(command=empty), self.env)[0], 2)
        self.assertEqual(longwait.pretool_verdict(_payload(command="echo keepwarm-ok: 一次性下載"),
                                                  self.env)[0], 2, "沒有 # 不是註解")

    def test_broken_payloads_fail_open(self) -> None:
        """AT-SS-36：解析不到一律放行（fail-open 是 P0：hook 崩潰不得演變成阻斷）。"""
        bad = [None, [], "x", {}, {"tool_name": "PowerShell", "agent_id": "a"},
               {"tool_name": "PowerShell", "agent_id": "a", "tool_input": "oops"},
               _payload(timeout="abc"), _payload(timeout=True), _payload(timeout=[1]),
               _payload(timeout=float("nan"))]
        for pl in bad:
            self.assertEqual(longwait.pretool_verdict(pl, self.env), (0, ""), repr(pl))

    def test_numeric_string_timeout_is_still_judged(self) -> None:
        """工具參數可能以字串送來（"300000"）；數字字串仍要判，否則換型別就繞過閘。"""
        self.assertEqual(longwait.pretool_verdict(_payload(timeout="300000"), self.env)[0], 2)

    def test_block_leaves_a_trace_row(self) -> None:
        """REQ-SS-21：擋下要落 `longwait_block` 痕跡（量測端靠它數擋了幾次）。"""
        longwait.pretool_verdict(_payload(), self.env)
        trace = Path(self._tmp.name) / "autosdd_session_switch.jsonl"
        rows = [json.loads(x) for x in trace.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([r["event"] for r in rows], [longwait.EV_BLOCK])
        self.assertEqual(rows[0]["timeout_ms"], 300_000)


class RunlongTest(unittest.TestCase):
    """AT-SS-30、MU-16：輸出落檔（UTF-8），`.done` 在輸出寫完**之後**才出現。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = Path(self._tmp.name) / "o.txt"

    def test_output_is_utf8_and_done_records_child_rc(self) -> None:
        got = _cli("runlong", "--out", str(self.out), "--", sys.executable, "-c",
                   "import sys;print('中');sys.exit(3)")
        self.assertEqual(got.returncode, 3, got.stderr)
        self.assertIn("中", self.out.read_text(encoding="utf-8"))
        row = json.loads(longwait.done_path(self.out).read_text(encoding="utf-8"))
        self.assertEqual((row["rc"], row["schema"]), (3, longwait.SCHEMA))
        self.assertIn("ended", row)

    def test_done_does_not_exist_until_the_child_finished_and_output_is_complete(self) -> None:
        """MU-16：先寫 `.done` 再收輸出 ⇒ 讀者看到 `.done` 時輸出不全。子行程睡 2 秒期間
        `.done` 必不存在，
        出現時最後一行必在。"""
        code = "import time,sys;print('first',flush=True);time.sleep(2);print('LAST-LINE')"
        proc = subprocess.Popen([sys.executable, str(SESSIONCTL), "runlong",
                                 "--out", str(self.out), "--",
                                 sys.executable, "-c", code], creationflags=NOWIN,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(proc.kill)
        done, seen_early = longwait.done_path(self.out), False
        deadline = time.monotonic() + 30
        while not done.exists() and time.monotonic() < deadline:
            seen_early = seen_early or (proc.poll() is None and done.exists())
            time.sleep(0.05)
        self.assertTrue(done.exists())
        self.assertFalse(seen_early)
        self.assertIn("LAST-LINE", self.out.read_text(encoding="utf-8"))
        proc.wait(timeout=10)

    def test_stale_done_from_a_previous_run_is_cleared_at_start(self) -> None:
        """舊 `.done` 殘留會讓 waitfor 在新一輪剛開始就誤報完成。"""
        longwait.done_path(self.out).write_text('{"rc": 0}', encoding="utf-8")
        proc = subprocess.Popen([sys.executable, str(SESSIONCTL), "runlong",
                                 "--out", str(self.out), "--",
                                 sys.executable, "-c", "import time;time.sleep(3)"],
                                creationflags=NOWIN,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(proc.kill)
        deadline = time.monotonic() + 15
        while self.out.exists() is False and time.monotonic() < deadline:
            time.sleep(0.05)
        time.sleep(0.5)
        self.assertFalse(longwait.done_path(self.out).exists())
        proc.wait(timeout=15)

    def test_unlaunchable_command_still_leaves_done_with_127(self) -> None:
        """起不來也要留 `.done`（否則 waitfor 永遠 pending、子代理空轉到分段上限）。"""
        got = _cli("runlong", "--out", str(self.out), "--", "definitely-not-a-command-r216")
        self.assertEqual(got.returncode, 127)
        done = json.loads(longwait.done_path(self.out).read_text(encoding="utf-8"))
        self.assertEqual(done["rc"], 127)
        self.assertIn("起不來", self.out.read_text(encoding="utf-8"))

    def test_missing_command_is_a_usage_error(self) -> None:
        self.assertEqual(_cli("runlong", "--out", str(self.out)).returncode, 2)
        self.assertEqual(_cli("runlong", "--out", str(self.out), "--").returncode, 2)


class _Clock:
    def __init__(self) -> None:
        self.t, self.sleeps = 0.0, []

    def now(self) -> float:
        return self.t

    def sleep(self, sec: float) -> None:
        self.sleeps.append(sec)
        self.t += sec


class WaitforTest(unittest.TestCase):
    """AT-SS-31／32：完成 rc 0＋尾端＋判決；未完成 rc 3；參數錯 rc 2；`--max-sec` 夾到上限。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = Path(self._tmp.name) / "o.txt"
        self.done = longwait.done_path(self.out)

    def _run(self, max_sec: float = 5, clock: _Clock | None = None) -> tuple[int, str]:
        clock, buf = clock or _Clock(), io.StringIO()
        rc = longwait.waitfor(self.done, max_sec, now_fn=clock.now, sleep_fn=clock.sleep, out=buf)
        return rc, buf.getvalue()

    def test_pending_returns_3_with_verdict_last_line_and_waits_the_whole_budget(self) -> None:
        clock = _Clock()
        rc, text = self._run(5, clock)
        self.assertEqual(rc, longwait.RC_PENDING)
        self.assertEqual(text.splitlines()[-1], "WAITFOR_VERDICT=pending seg=1/12")
        self.assertAlmostEqual(clock.t, 5.0, places=6,
                               msg="要把 max-sec 等滿才回（每段都續命快取）")

    def test_done_returns_0_with_child_rc_and_the_last_40_lines(self) -> None:
        self.out.write_text("\n".join(f"L{i}" for i in range(100)) + "\n", encoding="utf-8")
        self.done.write_text('{"schema": "x", "rc": 3, "ended": "t"}', encoding="utf-8")
        rc, text = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(text.splitlines()[-1], "WAITFOR_VERDICT=done rc=3")
        body = text.splitlines()
        self.assertIn("L99", body)
        self.assertIn("L60", body)
        self.assertNotIn("L59", body, "只印尾端 40 行")

    def test_done_appearing_mid_wait_ends_the_wait_early(self) -> None:
        clock = _Clock()
        orig = clock.sleep

        def sleep(sec: float) -> None:
            orig(sec)
            if clock.t >= 2:
                self.done.write_text('{"rc": 0}', encoding="utf-8")
        buf = io.StringIO()
        rc = longwait.waitfor(self.done, 100, now_fn=clock.now, sleep_fn=sleep, out=buf)
        self.assertEqual(rc, 0)
        self.assertLess(clock.t, 5, "完成就該立刻回，不能等滿 max-sec")
        self.assertIn("WAITFOR_VERDICT=done rc=0", buf.getvalue())

    def test_half_written_done_counts_as_pending_not_a_crash(self) -> None:
        """`.done` 不用 rename：讀到寫一半的內容當未完成，下一輪再讀。"""
        for junk in ("", "{", '{"rc": "3"}', "[]"):
            self.done.write_text(junk, encoding="utf-8")
            self.assertEqual(self._run(1)[0], longwait.RC_PENDING, repr(junk))

    def test_segment_counter_climbs_and_the_cap_message_stops_further_splitting(self) -> None:
        seen = [self._run(1)[1].splitlines()[-1] for _ in range(longwait.N_S_STAR)]
        n = longwait.N_S_STAR
        self.assertEqual(seen[-1], f"WAITFOR_VERDICT=pending seg={n}/{n}")
        last = self._run(1)[1]
        self.assertIn("不再分段", last)
        self.assertIn("向主控回報", last, "上限之後的出路必須是回報主控，不能叫子代理無限輪詢")
        self.assertNotIn("keepwarm-ok", last, "waitfor 上限 < 閘線，沒有任何理由叫子代理去繞閘")

    def test_cli_exit_codes_and_clamp(self) -> None:
        """AT-SS-31／32 的 CLI 面：done 不存在＋max-sec 1 ⇒ rc 3；缺參數／非 .done／非正數 ⇒ rc 2；
        `--max-sec 600` 夾到上限並出聲（此處只驗出聲，不真等 270 秒：done 已存在即刻回）。"""
        got = _cli("waitfor", "--done", str(self.done), "--max-sec", "1")
        self.assertEqual((got.returncode, got.stdout.splitlines()[-1].split(" seg")[0]),
                         (3, "WAITFOR_VERDICT=pending"), got.stderr)
        self.assertEqual(_cli("waitfor").returncode, 2)
        self.assertEqual(_cli("waitfor", "--done", str(self.out)).returncode, 2)
        self.assertEqual(_cli("waitfor", "--done", str(self.done), "--max-sec", "0").returncode, 2)
        self.done.write_text('{"rc": 0}', encoding="utf-8")
        clamped = _cli("waitfor", "--done", str(self.done), "--max-sec", "600")
        self.assertEqual(clamped.returncode, 0)
        self.assertIn(f"夾到 {longwait.WAIT_CEIL_SEC:g}", clamped.stderr)

    def test_ceiling_and_default_are_below_the_five_minute_cache_life(self) -> None:
        """常數方向鎖：預設 ≤ 上限、上限 < 300（5 分鐘快取壽命）；放寬就等不到下一個 5
        分鐘內的回合。"""
        self.assertLessEqual(longwait.WAIT_DEFAULT_SEC, longwait.WAIT_CEIL_SEC)
        self.assertLess(longwait.WAIT_CEIL_SEC, 300)
        self.assertEqual(longwait.TAIL_LINES, 40)

    def test_main_dispatch_rejects_unknown_verb_but_knows_the_new_ones(self) -> None:
        err = io.StringIO()
        sys.path.insert(0, str(_REPO_ROOT / "tools"))
        import sessionctl  # noqa: PLC0415

        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            self.assertEqual(sessionctl.main(["nope"]), 3)
        self.assertIn("runlong／waitfor", err.getvalue())


if __name__ == "__main__":
    unittest.main()
