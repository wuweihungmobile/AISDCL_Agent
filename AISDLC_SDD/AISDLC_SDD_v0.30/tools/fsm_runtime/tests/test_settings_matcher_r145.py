# enforces (governance rules): R-9.6
"""D20（DEF-200-275 第六輪；DEF-200-280／F-ARCH-02／SD-03）settings.json PreToolUse
matcher 必須含 Agent／Workflow，且 context_ledger_pre.py 的 gating 邏輯本就與 tool_name 無關。

背景（見任務書 r6_decisions.md D20）：四方複審（SD-03／F-ARCH-02）實測本檔 v0.30 版與根層
`.claude/settings.json` 的 sdd_hook_router→context_ledger_pre PreToolUse matcher 皆缺
`Agent`／`Workflow`——子代理（Agent）呼叫與批次編排（Workflow）呼叫因此完全繞過 SDD FSM
guardrail，等於 DEF-200-279（不該擋卻擋）的鏡像問題（該擋卻沒擋）。

本檔兩組斷言：
1. `MatcherContentTests`：直接讀取本版 `.claude/settings.json`，斷言 PreToolUse matcher
   含 Agent 與 Workflow（正面斷言，先紅後綠——修 matcher 前必失敗）。
2. `AgentWorkflowGatingTests`：讀碼確認 `FSMRuntime.assert_tool_allowed()` 對
   `_BLOCKING_STATES`（ESCALATION 等）的判斷完全由 `self.state.current` 決定、與傳入的
   `tool` 名稱無關（`tools/fsm_runtime/fsm_runtime.py` L562-567）；`_is_blocked_spec_write()`
   只在 `tool in {"Write", "Edit"}` 時才生效，對 Agent/Workflow 天然不觸發（不應觸發——子
   代理呼叫不是規格檔寫入）。故 `context_ledger_pre.py` 本身**不需要**為 Agent/Workflow
   改碼：只要 matcher 修好讓 hook 真的被呼叫，既有邏輯即可正確 gating。本組測試直接呼叫
   `context_ledger_pre.main()`（隔離 env，抄 `test_context_ledger_pre_hook.py` 的
   `_isolated_env`／`_isolate_fsm`／`_write_transcript`／`_MainRunner` 夾具形態，非 import
   ——`tools/fsm_runtime/tests/` 目錄無 `__init__.py`，跨測試檔案 import 不可靠，且複審任務書
   明文要求「抄」而非「共用」），驗證：
   - ESCALATION 狀態下 tool_name=Agent → deny（且 tool_name=Workflow 亦同）。
   - SPEC_DRAFTING 低水位（used 遠低於任何門檻）下 tool_name=Workflow → 放行
     （無 permissionDecision）。
   這兩案在 matcher 修復前後皆為綠——它們驗證的是「hook 邏輯本就 tool-name-agnostic」，
   不是本輪新改的行為；D20 派工矩陣要求「若 context_ledger_pre.py 需要改碼則不得改」，
   本檔讀碼＋以下兩個綠測試即是「不需要改碼」這個結論的證據，而非繞過驗證。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

_V_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_V_ROOT))

SETTINGS_PATH = _V_ROOT / ".claude" / "settings.json"
HOOK_MODULE_PATH = _V_ROOT / ".claude" / "hooks" / "context_ledger_pre.py"
_POLLUTING_ENVS = ("SDD_MAX_CONTEXT", "AUTOSDD_CONTEXT_WINDOW", "CLAUDE_CODE_AUTO_COMPACT_WINDOW")


class MatcherContentTests(unittest.TestCase):
    """先紅後綠本體：修 matcher 前必敗（AssertionError: 'Agent' not in {...}）。"""

    def _pretooluse_entries(self) -> list[dict]:
        self.assertTrue(SETTINGS_PATH.is_file(), f"找不到 {SETTINGS_PATH}")
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
        return settings.get("hooks", {}).get("PreToolUse", []) or []

    def _context_ledger_pre_matcher_tokens(self) -> set[str]:
        for entry in self._pretooluse_entries():
            for hook in entry.get("hooks", []) or []:
                haystack = " ".join(
                    [str(hook.get("command", ""))] + [str(a) for a in hook.get("args", [])]
                )
                if "context_ledger_pre.py" in haystack:
                    matcher = str(entry.get("matcher", ""))
                    return {t for t in matcher.split("|") if t}
        self.fail(
            "settings.json 的 PreToolUse 底下找不到承載 context_ledger_pre.py 的條目"
            "——註冊佈局已變，請重寫本案而不是放寬斷言"
        )
        return set()  # pragma: no cover — self.fail 已拋例外，此行僅安撫型別檢查

    def test_matcher_includes_agent_and_workflow(self) -> None:
        tokens = self._context_ledger_pre_matcher_tokens()
        for tool in ("Agent", "Workflow"):
            self.assertIn(
                tool, tokens,
                f"v0.30 settings.json 的 context_ledger_pre PreToolUse matcher 缺 {tool}"
                "（DEF-200-280／SD-03：Agent/Workflow 呼叫會繞過 SDD FSM guardrail）",
            )


# ── 下方為 AgentWorkflowGatingTests 的隔離夾具（抄自 test_context_ledger_pre_hook.py，
#    任務書 D20 明文要求「抄」——tests/ 目錄無 __init__.py，跨檔 import 不可靠）────────

def _load_hook_module(tmp_root: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "context_ledger_pre_settings_matcher_r145", str(HOOK_MODULE_PATH),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.LEDGER_DIR = tmp_root
    return mod


def _isolated_env(tmp: Path, extra: dict | None = None):
    env = dict(os.environ)
    for key in _POLLUTING_ENVS:
        env.pop(key, None)
    home = tmp / "home"
    proj = tmp / "proj"
    home.mkdir(exist_ok=True)
    proj.mkdir(exist_ok=True)
    env.update({
        "SDD_HOOKS_DISABLE": "",
        "SDD_HOOKS_DRY_RUN": "",
        "SDD_SUBAGENT_CONTRACT": "0",
        "HOME": str(home),
        "USERPROFILE": str(home),
        "CLAUDE_PROJECT_DIR": str(proj),
    })
    if extra:
        env.update(extra)
    return patch.dict(os.environ, env, clear=True)


def _write_transcript(tmp: Path, used: int, *, model: str = "claude-fable-5-1",
                       name: str = "session-abc.jsonl") -> str:
    def rec(m: str, n: int) -> str:
        return json.dumps({"type": "assistant", "message": {
            "model": m, "usage": {"input_tokens": n, "cache_creation_input_tokens": 0,
                                  "cache_read_input_tokens": 0, "output_tokens": 7}}})
    lines = [json.dumps({"type": "user", "message": {"content": "hi"}}), rec(model, used)]
    p = tmp / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


class _MainRunner:
    def __init__(self, mod):
        self.mod = mod

    def run(self, payload) -> dict:
        buf_out = StringIO()

        class _FakeStdin(StringIO):
            def isatty(self) -> bool:  # noqa: D401
                return False

        fake_stdin = _FakeStdin(json.dumps(payload))
        with patch.object(sys, "stdin", fake_stdin), patch.object(sys, "stdout", buf_out):
            rc = self.mod.main()
        assert rc == 0
        raw = buf_out.getvalue().strip()
        if not raw:
            return {}
        return json.loads(raw)


class AgentWorkflowGatingTests(unittest.TestCase):
    """既綠迴歸鎖：Agent／Workflow tool_name 下 hook 的 gating 行為與其它工具一致。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._isolate_fsm()
        self._env = _isolated_env(self.root)
        self._env.start()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._env.stop()
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def _isolate_fsm(self, current: str = "SPEC_DRAFTING"):
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state
        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        import tools.fsm_runtime.snapshot as snap_mod
        import tools.fsm_runtime.state_loader as sl_mod

        state = load_state("r145-matcher-proj", path=self.root / "FSM-STATE-r145.yaml")
        state.current = current
        self._rt = FSMRuntime(state)
        self._patches = [
            patch.object(fsm_rt_mod.FSMRuntime, "bootstrap",
                         classmethod(lambda cls, project=None: self._rt)),
            patch.object(snap_mod, "SNAPSHOT_DIR", self.root / "abort"),
            patch.object(sl_mod, "REPO_ROOT", self.root / "repo"),
        ]
        for p in self._patches:
            p.start()
        return self._rt

    def test_agent_tool_name_denied_in_escalation(self) -> None:
        self._rt.state.record_escalation("R-9.1: retry budget exceeded",
                                          details={"session_id": "old-escalator"})
        transcript = _write_transcript(self.root, 5_000)
        out = self.runner.run({
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "dev-senior", "prompt": "demo"},
            "transcript_path": transcript,
            "session_id": "new-window",
        }).get("hookSpecificOutput", {})
        self.assertEqual(
            out.get("permissionDecision"), "deny", msg=out,
        )

    def test_workflow_tool_name_denied_in_escalation(self) -> None:
        self._rt.state.record_escalation("R-9.1: retry budget exceeded",
                                          details={"session_id": "old-escalator"})
        transcript = _write_transcript(self.root, 5_000)
        out = self.runner.run({
            "tool_name": "Workflow",
            "tool_input": {"workflow": "batch-orchestration"},
            "transcript_path": transcript,
            "session_id": "new-window",
        }).get("hookSpecificOutput", {})
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)

    def test_workflow_tool_name_allowed_at_low_water_mark(self) -> None:
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")
        transcript = _write_transcript(self.root, 1_000)
        out = self.runner.run({
            "tool_name": "Workflow",
            "tool_input": {"workflow": "batch-orchestration"},
            "transcript_path": transcript,
            "session_id": "new-window",
        }).get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", out, msg=out)
        self.assertEqual(self._rt.state.current, "SPEC_DRAFTING")


if __name__ == "__main__":
    unittest.main()
