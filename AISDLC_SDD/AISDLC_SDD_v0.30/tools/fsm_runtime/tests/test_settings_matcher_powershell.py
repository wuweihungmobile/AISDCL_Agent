# enforces (governance rules): R-9.6
"""ADR-XPLAT-016 §12（SD-10／體檢 S-02 的 LATEST 半）：版本目錄 `.claude/settings.json` 的兩個 matcher 必須含
`PowerShell`，**且**同批改好三個「Bash 才特殊處理」的站點，否則單純加 matcher 會引入死鎖。

背景：根層鐵律一在 Windows 禁用 Bash 工具，Windows 唯一的 shell 載具是 PowerShell。matcher 沒列它 ⇒
FSM 進 ESCALATION 後模型仍可用 PowerShell 跑任意指令（`R-9.6-phase-d-hooks.yaml` 宣稱 ESCALATION 拒
所有工具，實作靠 hook 被呼叫才生效），PostToolUse 記帳也不含它。但只加 matcher 會讓三個站點出事：

  站點                                                       只加 matcher 的後果
  `fsm_runtime._assert_allowed_under_auto_compact`           AUTO_COMPACT_PENDING 期間 PowerShell 被拒 ⇒ Windows 上
                                                             連 `complete-auto-compact` 都跑不了 ⇒ **死鎖**
  `conversation_ledger.estimate_tool_tokens`                 PowerShell 估 0，帳本漏記
  `context_ledger_pre._estimate_tokens`（備援）              同上

四組斷言（ADR §12-3）：(a) 兩個 matcher 的 token 集合含 `Bash` 與 `PowerShell`；(b) `estimate_tool_tokens` 對
PowerShell 與 Bash 同輸入同值；(c) AUTO_COMPACT_PENDING 下 `assert_tool_allowed("PowerShell", None)` 不拋、與 Bash
對稱；(d) ESCALATION 下 `context_ledger_pre.main()` 對 `tool_name=PowerShell` 回 `deny`。
反向對照：還原 `fsm_runtime.py` 的 `{"Bash", "PowerShell"}` ⇒ (c) 紅；還原 matcher ⇒ (a) 紅。

夾具（`_load_hook_module`／`_isolated_env`／`_write_transcript`／`_MainRunner`／`_isolate_fsm`）依
`test_settings_matcher_r145.py` 的「抄而非共用」慣例複製——該檔 docstring 綁定那一輪的 Agent／Workflow 議題，不併入。
"""
from __future__ import annotations

import datetime as _dt
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import yaml

_V_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_V_ROOT))

SETTINGS_PATH = _V_ROOT / ".claude" / "settings.json"
HOOK_MODULE_PATH = _V_ROOT / ".claude" / "hooks" / "context_ledger_pre.py"
_POLLUTING_ENVS = ("SDD_MAX_CONTEXT", "AUTOSDD_CONTEXT_WINDOW", "CLAUDE_CODE_AUTO_COMPACT_WINDOW")


# ───────────────────────── (a) matcher 內容 ─────────────────────────
class MatcherContentTests(unittest.TestCase):
    def _matcher_tokens(self, event: str, script: str) -> set[str]:
        self.assertTrue(SETTINGS_PATH.is_file(), f"找不到 {SETTINGS_PATH}")
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
        for entry in settings.get("hooks", {}).get(event, []) or []:
            for hook in entry.get("hooks", []) or []:
                haystack = " ".join([str(hook.get("command", ""))] + [str(a) for a in hook.get("args", [])])
                if script in haystack:
                    return {t for t in str(entry.get("matcher", "")).split("|") if t}
        self.fail(f"settings.json 的 {event} 底下找不到承載 {script} 的條目——註冊佈局已變，請重寫本案而不是放寬斷言")
        return set()  # pragma: no cover

    def test_pre_tool_use_matcher_covers_bash_and_powershell(self) -> None:
        tokens = self._matcher_tokens("PreToolUse", "context_ledger_pre.py")
        for tool in ("Bash", "PowerShell"):
            self.assertIn(tool, tokens, f"PreToolUse matcher 缺 {tool}：該載具的呼叫繞過 FSM guardrail（S-02）")

    def test_post_tool_use_matcher_covers_bash_and_powershell(self) -> None:
        tokens = self._matcher_tokens("PostToolUse", "context_ledger_post.py")
        for tool in ("Bash", "PowerShell"):
            self.assertIn(tool, tokens, f"PostToolUse matcher 缺 {tool}：該載具的呼叫不進記帳（S-02）")

    def test_post_matcher_stays_asymmetric_on_subagents(self) -> None:
        """既有設計（context_ledger_post.py 檔頭 A6-02）：子代理在自己的 context window 內執行，其結果不得記到
        主 session 的帳——加 PowerShell 不得順手把 Task／Agent／Workflow 也帶進 PostToolUse。"""
        tokens = self._matcher_tokens("PostToolUse", "context_ledger_post.py")
        self.assertFalse(tokens & {"Task", "Agent", "Workflow"}, tokens)


# ───────────────────────── (b) 記帳估算 ─────────────────────────
class EstimateTests(unittest.TestCase):
    def test_powershell_estimates_exactly_like_bash(self) -> None:
        from tools.fsm_runtime.conversation_ledger import estimate_tool_tokens

        for command in ("Get-ChildItem -Recurse", "x" * 400, "中文" * 50, ""):
            with self.subTest(command=command[:20]):
                self.assertEqual(
                    estimate_tool_tokens("PowerShell", {"command": command}),
                    estimate_tool_tokens("Bash", {"command": command}),
                )
        self.assertGreater(estimate_tool_tokens("PowerShell", {"command": "x" * 400}), 0, "非空指令不得估成 0")

    def test_powershell_without_a_command_key_estimates_zero_like_bash(self) -> None:
        from tools.fsm_runtime.conversation_ledger import estimate_tool_tokens

        self.assertEqual(estimate_tool_tokens("PowerShell", {}), estimate_tool_tokens("Bash", {}))

    def test_the_hooks_legacy_fallback_treats_powershell_like_bash(self) -> None:
        """hook 的 `_estimate_tokens` 在 conversation_ledger 匯入失敗時走備援（size/4）——備援也不得漏 PowerShell。"""
        mod = _load_hook_module(Path(tempfile.gettempdir()))
        with patch.dict(sys.modules, {"tools.fsm_runtime.conversation_ledger": None}):  # 匯入即 ImportError
            self.assertEqual(mod._estimate_tokens("PowerShell", {"command": "x" * 40}), 10)
            self.assertEqual(mod._estimate_tokens("Bash", {"command": "x" * 40}), 10)
            self.assertEqual(mod._estimate_tokens("PowerShell", {}), 0)


# ───────────────────────── 共用夾具（抄自 test_settings_matcher_r145.py） ─────────────────────────
def _load_hook_module(tmp_root: Path):
    spec = importlib.util.spec_from_file_location("context_ledger_pre_settings_matcher_powershell", str(HOOK_MODULE_PATH))
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
        "SDD_HOOKS_DISABLE": "", "SDD_HOOKS_DRY_RUN": "", "SDD_SUBAGENT_CONTRACT": "0",
        "HOME": str(home), "USERPROFILE": str(home), "CLAUDE_PROJECT_DIR": str(proj),
    })
    if extra:
        env.update(extra)
    return patch.dict(os.environ, env, clear=True)


def _write_transcript(tmp: Path, used: int, *, model: str = "claude-fable-5-1", name: str = "session-ps.jsonl") -> str:
    def rec(m: str, n: int) -> str:
        return json.dumps({"type": "assistant", "message": {
            "model": m, "usage": {"input_tokens": n, "cache_creation_input_tokens": 0,
                                  "cache_read_input_tokens": 0, "output_tokens": 7}}})
    lines = [json.dumps({"type": "user", "message": {"content": "hi"}}), rec(model, used)]
    path = tmp / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


class _MainRunner:
    def __init__(self, mod):
        self.mod = mod

    def run(self, payload) -> dict:
        buf_out = StringIO()

        class _FakeStdin(StringIO):
            def isatty(self) -> bool:  # noqa: D401
                return False

        with patch.object(sys, "stdin", _FakeStdin(json.dumps(payload))), patch.object(sys, "stdout", buf_out):
            rc = self.mod.main()
        assert rc == 0
        raw = buf_out.getvalue().strip()
        return json.loads(raw) if raw else {}


class _IsolatedFsmBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._patches: list = []
        self._env = _isolated_env(self.root)
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def isolate_fsm(self, current: str = "SPEC_DRAFTING"):
        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        import tools.fsm_runtime.snapshot as snap_mod
        import tools.fsm_runtime.state_loader as sl_mod
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state

        state = load_state("powershell-matcher-proj", path=self.root / "FSM-STATE-ps.yaml")
        state.current = current
        self.rt = FSMRuntime(state)
        self._patches = [
            patch.object(fsm_rt_mod.FSMRuntime, "bootstrap", classmethod(lambda cls, project=None: self.rt)),
            patch.object(snap_mod, "SNAPSHOT_DIR", self.root / "abort"),
            patch.object(sl_mod, "REPO_ROOT", self.root / "repo"),
            patch.object(sl_mod, "DEFAULT_STATE_DIR", self.root / "repo" / "build" / "reports" / "fsm"),
        ]
        for p in self._patches:
            p.start()
        return self.rt


# ───────────────────────── (c) AUTO_COMPACT_PENDING 不得把 Windows 鎖死 ─────────────────────────
class AutoCompactAllowListTests(_IsolatedFsmBase):
    def _enter_pending(self) -> None:
        self.isolate_fsm("IMPLEMENTATION")
        result = self.rt.trigger_auto_compact(184_000, 0.92, details={"session_id": "owner-session"})
        self.assertFalse(result.get("already_pending"), result)
        self.assertEqual(self.rt.state.current, "AUTO_COMPACT_PENDING")

    def test_powershell_is_allowed_exactly_like_bash_under_pending(self) -> None:
        """死鎖防線：PENDING 期間唯一能跑 `complete-auto-compact` 的 shell 工具就是 PowerShell（Windows）。"""
        self._enter_pending()
        self.rt.assert_tool_allowed("Bash", None)
        self.rt.assert_tool_allowed("PowerShell", None)
        self.rt.assert_tool_allowed("PowerShell", None, session_id="owner-session")

    def test_the_allowance_is_specific_to_shells_not_a_blanket_opening(self) -> None:
        """對照組：放行 PowerShell 不得連帶放行別的寫入工具（PENDING 只准 compact 相關操作）。"""
        from tools.fsm_runtime.transition_rules import TransitionError

        self._enter_pending()
        with self.assertRaises(TransitionError):
            self.rt.assert_tool_allowed("Write", "src/app.py", session_id="owner-session")
        with self.assertRaises(TransitionError):
            self.rt.assert_tool_allowed("NotebookEdit", None, session_id="owner-session")


# ───────────────────────── (d) ESCALATION 下 hook 真的擋 PowerShell ─────────────────────────
class HookGatingTests(_IsolatedFsmBase):
    def setUp(self) -> None:
        super().setUp()
        self.isolate_fsm()
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def test_escalation_denies_a_powershell_call(self) -> None:
        """matcher 修好之後 hook 真的被呼叫，其 gating 又與 tool_name 無關——本案證明 PowerShell 這個名字走得進
        同一條 deny 路徑（反向對照：`tool_name` 若被當成未知工具而略過 FSM guardrail，這裡會放行 ⇒ 紅）。"""
        self.rt.state.record_escalation("R-9.1: retry budget exceeded", details={"session_id": "old-escalator"})
        out = self.runner.run({
            "tool_name": "PowerShell", "tool_input": {"command": "Get-ChildItem"},
            "transcript_path": _write_transcript(self.root, 5_000), "session_id": "new-window",
        }).get("hookSpecificOutput", {})
        self.assertEqual(out.get("permissionDecision"), "deny", msg=out)

    def test_powershell_passes_at_low_water_mark_and_is_recorded_with_tokens(self) -> None:
        command = "Get-ChildItem -Recurse -Filter *.py | Select-Object -ExpandProperty FullName  # " + "x" * 300
        out = self.runner.run({
            "tool_name": "PowerShell", "tool_input": {"command": command},
            "transcript_path": _write_transcript(self.root, 1_000), "session_id": "new-window",
        }).get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", out, msg=out)
        ledger = yaml.safe_load(
            (self.root / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml").read_text(encoding="utf-8")
        )
        entry = next(e for e in reversed(ledger["entries"]) if e.get("tool") == "PowerShell")
        self.assertEqual(entry["phase"], "pre")
        self.assertGreaterEqual(entry["tokens"], len(command) // 4, "PowerShell 呼叫不得在帳本裡估成 0（S-02）")


if __name__ == "__main__":
    unittest.main()
