"""sessionctl hook 面（TCS-SessionCtl AT-SC-61～65、74～76；ADR-XPLAT-004 §2.13.6 D6／D7a）。

兩層：函式層（`roster.resume_gate`／`roster.stop_message`）一律能跑；子行程層把 payload 餵給
**最終路徑** `.claude/hooks/sessionctl_guard.py`——`.claude/` 是受保護路徑，成品先 staged 在
scratchpad 由主控套用（2026-11-14 已套用）；`GuardRegistrationTest` 釘註冊面（AT-SC-85）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TOOLS = _REPO_ROOT / "tools"
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

from lib.sessionctl import roster  # noqa: E402

ROOT = _TOOLS.parent
#: hook 與 settings 的所在根。缺省＝本 repo；`SESSIONCTL_APPLIED_ROOT` 指向「套用後佈局」的鏡像根
#: （hook、settings、`tools` 連結）時，套用前也能驗成品。
GUARD_ROOT = Path(os.environ.get("SESSIONCTL_APPLIED_ROOT") or ROOT)
HOOK = GUARD_ROOT / ".claude" / "hooks" / "sessionctl_guard.py"
SID = "d4ed2654-9181-4df1-a6e6-2d712956e23b"
LIMIT = 150_000  # 出廠門檻（`quota_policy_env.ENV_SPEC` 現查；本檔只在函式層用，env 另行釘死）


def _project(case: unittest.TestCase) -> Path:
    holder = tempfile.TemporaryDirectory(prefix="sc-hook-")
    case.addCleanup(holder.cleanup)
    slug = Path(holder.name) / "slug"
    slug.mkdir()
    return slug


def _agent(slug: Path, aid: str, ctx: int, minutes_ago: float = 1.0, ts_now=None) -> None:
    """`<slug>/<SID>/subagents/agent-<aid>.jsonl`：最後一筆 assistant usage 合計 `ctx`。"""
    folder = slug / SID / "subagents"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = (ts_now or datetime.now(UTC)) - timedelta(minutes=minutes_ago)
    usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
             "cache_creation_input_tokens": 0, "output_tokens": 7}
    rec = {"type": "assistant", "timestamp": stamp.isoformat(),
           "message": {"id": f"m-{aid}", "usage": usage}}
    (folder / f"agent-{aid}.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
    (folder / f"agent-{aid}.meta.json").write_text(
        json.dumps({"description": f"任務-{aid}", "model": "sonnet"}), encoding="utf-8")


def _send(slug: Path, to: str | None, field: str = "to") -> dict:
    payload: dict = {"hook_event_name": "PreToolUse", "tool_name": "SendMessage",
                     "session_id": SID, "transcript_path": str(slug / f"{SID}.jsonl")}
    if to is not None:
        payload["tool_input"] = {field: to, "message": "續做"}
    return payload


def _stop(slug: Path, **extra) -> dict:
    return {"hook_event_name": "Stop", "session_id": SID,
            "transcript_path": str(slug / f"{SID}.jsonl"), **extra}


class ResumeGateFunctionTest(unittest.TestCase):
    """AT-SC-61～65 的函式層。"""

    INTERACTIVE: dict = {}
    UNATTENDED = {"AUTOSDD_UNATTENDED": "1"}

    def test_at_sc_61_interactive_warm_agent_at_threshold_passes_silently(self) -> None:
        """AT-SC-61／AT-TW-19（改寫）：目標代理上下文 150,000、互動、**熱**（1 分鐘前）⇒ `(0, "")`。
        原「互動只出聲」被快取冷熱判準取代（熱續棒只付讀價）；「出聲含改派新代理」的語意移到冷代理
        的 AT-TW-09（`test_sessionctl_cachegate.py`）。"""
        slug = _project(self)
        _agent(slug, "a1", LIMIT)
        self.assertEqual(roster.resume_gate(_send(slug, "a1"), self.INTERACTIVE), (0, ""))

    def test_at_sc_61_interactive_cold_agent_at_threshold_is_blocked(self) -> None:
        """AT-SC-61 的原斷言（改派新代理）保留在冷代理上：互動、150,000、10 分鐘前 ⇒ rc 2。"""
        slug = _project(self)
        _agent(slug, "a1", LIMIT, minutes_ago=10)
        rc, text = roster.resume_gate(_send(slug, "a1"), self.INTERACTIVE)
        self.assertEqual(rc, 2)
        self.assertIn("改派新代理", text)

    def test_at_sc_62_unattended_at_threshold_blocks_with_the_fresh_agent_advice(self) -> None:
        """AT-SC-62：同上、`AUTOSDD_UNATTENDED=1` ⇒ rc 2、訊息含「改派新代理＋短任務書」。"""
        slug = _project(self)
        _agent(slug, "a1", LIMIT)
        rc, text = roster.resume_gate(_send(slug, "a1"), self.UNATTENDED)
        self.assertEqual(rc, 2)
        self.assertIn("改派新代理＋短任務書", text)

    def test_at_sc_63_just_below_threshold_passes_silently_even_unattended(self) -> None:
        """AT-SC-63：上下文 149,999、無人 ⇒ rc 0、無輸出（邊界：恰低於門檻 1 token）。"""
        slug = _project(self)
        _agent(slug, "a1", LIMIT - 1)
        self.assertEqual(roster.resume_gate(_send(slug, "a1"), self.UNATTENDED), (0, ""))

    def test_at_sc_64_unresolvable_targets_fail_open(self) -> None:
        """AT-SC-64：目標解析不到／逐字稿壞／payload 無 `tool_input`／`to` 非字串 ⇒ rc 0 放行。"""
        slug = _project(self)
        _agent(slug, "a1", LIMIT * 3)
        (slug / SID / "subagents" / "agent-bad.jsonl").write_text("{{壞 JSON\n", encoding="utf-8")
        cases = {"目標不存在": _send(slug, "ghost"), "逐字稿壞": _send(slug, "bad"),
                 "無 tool_input": _send(slug, None), "to 非字串": _send(slug, "x"),
                 "路徑穿越": _send(slug, "../../etc/passwd"), "萬用字元": _send(slug, "*")}
        cases["to 非字串"]["tool_input"]["to"] = 123
        for label, payload in cases.items():
            with self.subTest(label):
                self.assertEqual(roster.resume_gate(payload, self.UNATTENDED), (0, ""))
        self.assertEqual(roster.resume_gate({}, self.UNATTENDED), (0, ""))

    def test_recipient_is_the_fallback_target_field(self) -> None:
        """目標欄＝`to`，缺則 `recipient`（沙盒 V-S2：兩者值皆為代理 id）。"""
        slug = _project(self)
        _agent(slug, "a1", LIMIT)
        self.assertEqual(roster.resume_gate(_send(slug, "a1", field="recipient"),
                                            self.UNATTENDED)[0], 2)

    def test_at_sc_65_e1_replay_450k_context_is_blocked_unattended(self) -> None:
        """AT-SC-65（E1 重放）：無人、目標代理最後 usage 合計 450,000 ⇒ rc 2，訊息帶實際數字。"""
        slug = _project(self)
        _agent(slug, "old", 450_000, minutes_ago=600)
        rc, text = roster.resume_gate(_send(slug, "old"), self.UNATTENDED)
        self.assertEqual(rc, 2)
        self.assertIn("450,000", text)

    def test_threshold_override_only_lowers_it(self) -> None:
        """門檻走 `AUTOSDD_RESUME_AGENT_TOKENS`：調低生效；調高（放寬）被方向鎖退回出廠值。"""
        slug = _project(self)
        _agent(slug, "a1", 100_000)
        low = {**self.UNATTENDED, "AUTOSDD_RESUME_AGENT_TOKENS": "50000"}
        high = {**self.UNATTENDED, "AUTOSDD_RESUME_AGENT_TOKENS": "900000"}
        self.assertEqual(roster.resume_gate(_send(slug, "a1"), low)[0], 2)
        _agent(slug, "a2", LIMIT)
        self.assertEqual(roster.resume_gate(_send(slug, "a2"), high)[0], 2, "放寬值必須退回出廠值")


class StopMessageFunctionTest(unittest.TestCase):
    """AT-SC-74～76 的函式層。"""

    def test_at_sc_74_two_running_agents_are_announced_with_count_and_description(self) -> None:
        """AT-SC-74：讀檔路徑（payload 無 `background_tasks`）2 支執行中 ⇒ 含「2 支」與描述。"""
        slug = _project(self)
        _agent(slug, "a1", 1000)
        _agent(slug, "a2", 2000)
        text = roster.stop_message(_stop(slug))
        self.assertIn("2 支", text)
        self.assertIn("任務-a1", text)
        self.assertIn("任務-a2", text)

    def test_payload_background_tasks_has_priority_over_the_file_roster(self) -> None:
        """優先讀 payload 的 `background_tasks`（V-S7）：單元素為物件非陣列也認；shell 附帶一提。"""
        slug = _project(self)
        task = {"id": "a9", "type": "subagent", "status": "running", "description": "長跑審查",
                "agent_type": "general-purpose"}
        text = roster.stop_message(_stop(slug, background_tasks=task))
        self.assertIn("1 支", text)
        self.assertIn("長跑審查", text)
        mixed = roster.stop_message(_stop(slug, background_tasks=[
            task, {"id": "b1", "type": "shell", "status": "running", "command": "sleep 240"}]))
        self.assertIn("1 支", mixed)
        self.assertIn("1 個背景 shell", mixed)

    def test_finished_background_tasks_are_never_reported_as_running(self) -> None:
        """`status` 不是 running 的子代理與 shell 一律不計入（已結束的被報成在跑＝Stop 誤報）。"""
        slug = _project(self)
        done = [{"id": "a1", "type": "subagent", "status": "completed",
                 "description": "已完成審查"},
                {"id": "b1", "type": "shell", "status": "completed", "command": "sleep 1"}]
        self.assertEqual(roster.stop_message(_stop(slug, background_tasks=done)), "")
        live = {"id": "a2", "type": "subagent", "status": "running", "description": "還在跑"}
        text = roster.stop_message(_stop(slug, background_tasks=[*done, live]))
        self.assertIn("1 支", text)
        self.assertNotIn("已完成審查", text)
        self.assertNotIn("背景 shell", text)

    def test_at_sc_75_nothing_running_or_unreadable_roster_is_silent(self) -> None:
        """AT-SC-75：無執行中（含 `background_tasks: []`、檔案名冊讀不動）⇒ 空字串。"""
        slug = _project(self)
        self.assertEqual(roster.stop_message(_stop(slug)), "")
        self.assertEqual(roster.stop_message(_stop(slug, background_tasks=[])), "")
        self.assertEqual(roster.stop_message({}), "")
        _agent(slug, "old", 1000, minutes_ago=90)  # 安靜（>10 分鐘）不算執行中
        self.assertEqual(roster.stop_message(_stop(slug)), "")

    def test_empty_background_tasks_wins_over_a_running_looking_file(self) -> None:
        """payload 明說 `[]`（harness 的權威答案）時不得再退回讀檔——否則已結束的會被報成在跑。"""
        slug = _project(self)
        _agent(slug, "a1", 1000, minutes_ago=0.5)
        self.assertEqual(roster.stop_message(_stop(slug, background_tasks=[])), "")

    def test_at_sc_76_stop_hook_active_does_not_change_the_text_function(self) -> None:
        """AT-SC-76 的函式層：`stop_hook_active` 為真照樣只回文字（永不阻斷由 hook 層斷言）。"""
        slug = _project(self)
        _agent(slug, "a1", 1000)
        self.assertIn("1 支", roster.stop_message(_stop(slug, stop_hook_active=True)))


def _run_hook(payload: dict, **env_extra: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items()
           if k not in ("AUTOSDD_UNATTENDED", "AUTOSDD_RESUME_AGENT_TOKENS",
                        "AUTOSDD_SESSIONCTL_GUARD_OFF", "AUTOSDD_ROSTER_QUIET_MINUTES",
                        "AUTOSDD_SWITCH_HARD_CTX_TOKENS", "AUTOSDD_SESSION_SWITCH_MODE",
                        "AUTOSDD_HANDOFF_DIR", "AUTOSDD_TRACE_DIR")}
    env.update(PYTHONUTF8="1", **env_extra)
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                          capture_output=True, encoding="utf-8", errors="replace", timeout=60,
                          check=False, cwd=str(ROOT), env=env)


class HookSubprocessTest(unittest.TestCase):
    """把 payload 餵給最終路徑的 hook。🔴 hook 套用前整組紅（檔案不存在）是預期，見檔頭。"""

    def test_hook_file_exists_at_the_final_path(self) -> None:
        """成品必須落在最終路徑（主控套用後轉綠）。"""
        self.assertTrue(HOOK.is_file(), f"尚未套用：{HOOK}")

    def test_at_sc_61_hook_pretooluse_interactive_warm_is_silent_rc0(self) -> None:
        """AT-TW-36（hook 層）：互動、150,000、熱 ⇒ rc 0、stdout／stderr 皆空。"""
        slug = _project(self)
        _agent(slug, "a1", LIMIT)
        proc = _run_hook(_send(slug, "a1"))
        self.assertEqual((proc.returncode, proc.stdout.strip(), proc.stderr.strip()), (0, "", ""))

    def test_at_tw_35_hook_pretooluse_interactive_cold_blocks_rc2(self) -> None:
        """AT-TW-35（hook 層）：互動、150,000、冷 ⇒ rc 2、stderr 含「續棒成本閘」，stdout 空。"""
        slug = _project(self)
        _agent(slug, "a1", LIMIT, minutes_ago=10)
        proc = _run_hook(_send(slug, "a1"))
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("續棒成本閘", proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_at_sc_62_hook_pretooluse_unattended_blocks_rc2(self) -> None:
        """AT-SC-62（hook 層）：無人、150,000 ⇒ rc 2、stderr 含「改派新代理＋短任務書」。"""
        slug = _project(self)
        _agent(slug, "a1", LIMIT)
        proc = _run_hook(_send(slug, "a1"), AUTOSDD_UNATTENDED="1")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("改派新代理＋短任務書", proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_at_sc_63_hook_just_below_threshold_is_silent_rc0(self) -> None:
        """AT-SC-63（hook 層）：149,999、無人 ⇒ rc 0、stdout／stderr 皆空。"""
        slug = _project(self)
        _agent(slug, "a1", LIMIT - 1)
        proc = _run_hook(_send(slug, "a1"), AUTOSDD_UNATTENDED="1")
        self.assertEqual((proc.returncode, proc.stdout.strip(), proc.stderr.strip()), (0, "", ""))

    def test_at_sc_64_hook_unresolvable_target_and_degenerate_payloads_pass(self) -> None:
        """AT-SC-64（hook 層）：目標不存在／無 `tool_input`／空 payload／壞 JSON ⇒ rc 0。"""
        slug = _project(self)
        for label, payload in (("目標不存在", _send(slug, "ghost")),
                               ("無 tool_input", _send(slug, None)), ("空 payload", {})):
            with self.subTest(label):
                proc = _run_hook(payload, AUTOSDD_UNATTENDED="1")
                self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ""), proc.stderr)
        env = {**os.environ, "AUTOSDD_UNATTENDED": "1", "PYTHONUTF8": "1"}
        broken = subprocess.run([sys.executable, str(HOOK)], input="{{not json", env=env,
                                capture_output=True, encoding="utf-8", errors="replace",
                                timeout=60, check=False, cwd=str(ROOT))
        self.assertEqual(broken.returncode, 0, broken.stderr)

    def test_at_sc_65_hook_e1_replay_450k_unattended_is_rc2(self) -> None:
        """AT-SC-65（hook 層，E1 重放）：450,000 ⇒ rc 2。"""
        slug = _project(self)
        _agent(slug, "old", 450_000, minutes_ago=600)
        self.assertEqual(_run_hook(_send(slug, "old"), AUTOSDD_UNATTENDED="1").returncode, 2)

    def test_at_sc_74_hook_stop_announces_running_agents_as_system_message(self) -> None:
        """AT-SC-74：Stop、名冊 2 支執行中 ⇒ rc 0、stdout JSON `systemMessage` 含「2 支」與描述。"""
        slug = _project(self)
        _agent(slug, "a1", 1000)
        _agent(slug, "a2", 2000)
        proc = _run_hook(_stop(slug))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        message = json.loads(proc.stdout)["systemMessage"]
        self.assertIn("2 支", message)
        self.assertIn("任務-a1", message)

    def test_at_sc_75_hook_stop_without_running_agents_is_silent(self) -> None:
        """AT-SC-75：Stop、無執行中 ⇒ rc 0、無輸出。"""
        proc = _run_hook(_stop(_project(self)))
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ""), proc.stderr)

    def test_at_sc_76_hook_stop_never_blocks_even_when_stop_hook_active(self) -> None:
        """AT-SC-76：`stop_hook_active` 為真仍 rc 0、輸出不含 `decision`（永不 block）。"""
        slug = _project(self)
        _agent(slug, "a1", 1000)
        proc = _run_hook(_stop(slug, stop_hook_active=True))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("decision", json.loads(proc.stdout))

    def test_escape_hatch_silences_both_events(self) -> None:
        """`AUTOSDD_SESSIONCTL_GUARD_OFF` ⇒ 兩個事件一律 no-op（無人阻斷也放行）。"""
        slug = _project(self)
        _agent(slug, "a1", 450_000)
        for payload in (_send(slug, "a1"), _stop(slug)):
            proc = _run_hook(payload, AUTOSDD_SESSIONCTL_GUARD_OFF="1", AUTOSDD_UNATTENDED="1")
            self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ""), proc.stderr)

    def test_other_events_and_other_tools_are_ignored(self) -> None:
        """只認 Stop 與 PreToolUse(SendMessage／Agent／Task／Workflow)：其他事件／工具名一律 rc 0
        無輸出（matcher 被改寬時的第二道限縮）；`Agent` 不再被忽略見 `HookConvergeTest`。"""
        slug = _project(self)
        _agent(slug, "a1", 450_000)
        wide = {**_send(slug, "a1"), "tool_name": "Bash"}
        post = {**_send(slug, "a1"), "hook_event_name": "PostToolUse"}
        for payload in (wide, post):
            proc = _run_hook(payload, AUTOSDD_UNATTENDED="1")
            self.assertEqual((proc.returncode, proc.stdout.strip()), (0, ""), proc.stderr)


def _advised_session(case: unittest.TestCase, ctx: int) -> tuple[Path, dict]:
    """tmp 圍籬：主控逐字稿（最後 usage 合計 `ctx`）＋已出聲閂鎖；回 `(slug, 子行程 env 覆寫)`。"""
    slug = _project(case)
    handoff_dir = slug.parent / "handoff"
    handoff_dir.mkdir()
    (handoff_dir / f"{SID}.advised").write_text("x", encoding="utf-8")
    usage = {"input_tokens": 1, "cache_read_input_tokens": ctx - 1,
             "cache_creation_input_tokens": 0, "output_tokens": 7}
    rec = {"type": "assistant", "timestamp": datetime.now(UTC).isoformat(),
           "message": {"id": "m", "usage": usage}}
    (slug / f"{SID}.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
    return slug, {"AUTOSDD_HANDOFF_DIR": str(handoff_dir),
                  "AUTOSDD_TRACE_DIR": str(slug.parent)}


def _tool(slug: Path, tool: str, **extra) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "session_id": SID,
            "transcript_path": str(slug / f"{SID}.jsonl"), **extra}


class HookConvergeTest(unittest.TestCase):
    """AT-TW-33、34、37 與 Stop 推回的 hook 層：`.claude/hooks/sessionctl_guard.py` 接線
    （判準在 `tools/lib/sessionctl/converge.py`）。🔴 hook 套用前整組紅屬預期，見檔頭。"""

    def test_at_tw_33_agent_task_workflow_are_blocked_after_the_voice(self) -> None:
        """AT-TW-33：已出聲、ctx 400,000、三個展開型工具 ⇒ rc 2、stderr 含「收斂閘」、stdout 空。"""
        slug, env = _advised_session(self, 400_000)
        for tool in ("Agent", "Task", "Workflow"):
            with self.subTest(tool):
                proc = _run_hook(_tool(slug, tool), **env)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("收斂閘", proc.stderr)
                self.assertEqual(proc.stdout.strip(), "")

    def test_at_tw_34_other_tools_pass_even_when_the_gate_would_trip(self) -> None:
        """AT-TW-34：Bash／Read／Edit／PowerShell 同條件仍 rc 0 無輸出（收斂本身需要它們）。"""
        slug, env = _advised_session(self, 400_000)
        for tool in ("Bash", "Read", "Edit", "PowerShell"):
            with self.subTest(tool):
                proc = _run_hook(_tool(slug, tool), **env)
                self.assertEqual((proc.returncode, proc.stdout.strip(), proc.stderr.strip()),
                                 (0, "", ""))

    def test_at_tw_37_degenerate_payloads_and_the_escape_hatch_stay_open(self) -> None:
        """AT-TW-37：空 payload／無人／notify／逃生口 ⇒ rc 0；擴射程沒破壞既有 fail-open。"""
        slug, env = _advised_session(self, 400_000)
        self.assertEqual(_run_hook({}, **env).returncode, 0)
        got = _run_hook(_tool(slug, "Agent"), AUTOSDD_UNATTENDED="1", **env)
        self.assertEqual(got.returncode, 0)
        self.assertEqual(_run_hook(_tool(slug, "Agent"), AUTOSDD_SESSION_SWITCH_MODE="notify",
                                   **env).returncode, 0)
        off = _run_hook(_tool(slug, "Agent"), AUTOSDD_SESSIONCTL_GUARD_OFF="1", **env)
        self.assertEqual((off.returncode, off.stdout.strip(), off.stderr.strip()), (0, "", ""))

    def test_at_tw_70_hook_stop_pushes_back_once_with_a_block_decision(self) -> None:
        """AT-TW-70／71（hook 層）：Stop、已出聲、ctx 300,000、無代理 ⇒ rc 0＋`decision:block`；
        `stop_hook_active` 為真 ⇒ 無輸出。"""
        slug, env = _advised_session(self, 300_000)
        first = _run_hook(_stop(slug), **env)
        self.assertEqual(first.returncode, 0, first.stderr)
        doc = json.loads(first.stdout)
        self.assertEqual(doc["decision"], "block")
        self.assertIn("handoff --finalize", doc["reason"])
        second = _run_hook(_stop(slug, stop_hook_active=True), **env)
        self.assertEqual((second.returncode, second.stdout.strip()), (0, ""), second.stderr)

    def test_at_tw_72_hook_stop_with_running_agents_only_announces(self) -> None:
        """AT-TW-72（hook 層）：仍有背景代理在跑 ⇒ 只出 systemMessage、不 block（既有出聲照舊）。"""
        slug, env = _advised_session(self, 300_000)
        agent = {"id": "a1", "type": "subagent", "status": "running", "description": "跑著"}
        proc = _run_hook(_stop(slug, background_tasks=[agent]), **env)
        doc = json.loads(proc.stdout)
        self.assertIn("systemMessage", doc)
        self.assertNotIn("decision", doc)

    def test_at_tw_78_stacked_with_check_pending_handoff_there_is_no_deadlock(self) -> None:
        """AT-TW-78：兩支 Stop 守衛同回合都推回（最壞一個額外回合），第二次 Stop
        （`stop_hook_active`）兩者皆放行——疊加不死鎖。"""
        slug, env = _advised_session(self, 300_000)
        real = ROOT / ".claude" / "hooks" / "check_pending_handoff.py"
        self.assertTrue(real.is_file(), real)
        claim = {"last_assistant_message": "這件事待掌舵者決定。"}

        def both(extra: dict) -> list[dict]:
            outs = []
            for hook in (HOOK, real):
                cmd_env = {k: v for k, v in os.environ.items() if k != "AUTOSDD_UNATTENDED"}
                cmd_env.update(PYTHONUTF8="1", **env)
                proc = subprocess.run([sys.executable, str(hook)], capture_output=True,
                                      input=json.dumps(_stop(slug, **claim, **extra)),
                                      encoding="utf-8", errors="replace", timeout=60, check=False,
                                      cwd=str(ROOT), env=cmd_env)
                outs.append(json.loads(proc.stdout) if proc.stdout.strip() else {})
            return outs

        first = both({})
        self.assertEqual([d.get("decision") for d in first], ["block", "block"])
        self.assertEqual(both({"stop_hook_active": True}), [{}, {}])


class GuardRegistrationTest(unittest.TestCase):
    """AT-SC-85：新 hook 以 exec form 註冊於兩個事件，且在機械守衛總表點名。

    WHY：註冊面是 fail-open 的——少註冊一個事件，守衛就靜默失效而表徵與「修好了」相同。
    受測對象＝`.claude/settings.json` 的註冊與 `tools/lib/sessionctl/roster.py` 的 hook 跳板。
    """

    def _entries(self, event: str) -> list[dict]:
        path = GUARD_ROOT / ".claude" / "settings.json"
        settings = json.loads(path.read_text(encoding="utf-8"))
        return [e for e in settings["hooks"][event]
                if any("sessionctl_guard.py" in (h.get("args") or [""])[-1] for h in e["hooks"])]

    def test_registered_exec_form_on_send_message_expansion_tools_and_stop(self) -> None:
        """AT-TW-38：恰一條 PreToolUse 條目、matcher 含四個工具名；Stop 條目不變。"""
        pre, stop = self._entries("PreToolUse"), self._entries("Stop")
        self.assertEqual([e.get("matcher") for e in pre], ["SendMessage|Agent|Task|Workflow"])
        self.assertEqual(len(stop), 1)
        self.assertNotIn("matcher", stop[0])
        for entry in (*pre, *stop):
            args = entry["hooks"][0]["args"]
            self.assertTrue(args[0].endswith("_hook_launcher.py"), args)

    def test_named_in_the_root_claude_md_guard_table_with_its_escape_hatch(self) -> None:
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("sessionctl_guard.py", text)
        self.assertIn("AUTOSDD_SESSIONCTL_GUARD_OFF", text)


if __name__ == "__main__":
    unittest.main()
