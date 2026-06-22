# enforces (governance rules): R-9.2, R-9.6
"""Unit tests for QA patches on `.claude/hooks/context_ledger_pre.py`.

Covers:
- P1-04: SDD_HOOKS_DISABLE=1 must NOT silence Subagent Contract injection.
- P1-05: Legacy Read fallback must include cat -n line overhead.
- P2-08: tokens==0 early-return must still run ESCALATION / AUTO_COMPACT checks.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

# Re-import the hook module with the repo root on sys.path. The module does
# its own path manipulation; we wrap it in a helper so each test gets a
# fresh module-level state (LEDGER_DIR, MAX_CONTEXT).
HOOK_MODULE_PATH = (
    Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "context_ledger_pre.py"
)


def _load_hook_module(tmp_root: Path):
    """Import the hook as a module, pointing LEDGER_DIR at tmp_root."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "context_ledger_pre_test", str(HOOK_MODULE_PATH),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.LEDGER_DIR = tmp_root
    return mod


class _MainRunner:
    """Capture stdout from mod.main() given a JSON stdin payload."""

    def __init__(self, mod):
        self.mod = mod

    def run(self, payload: dict) -> dict:
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


class HooksDisableSubagentContractTests(unittest.TestCase):
    """P1-04: HOOKS_DISABLE should keep Subagent Contract injection alive."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_hooks_disable_still_injects_subagent_hint(self) -> None:
        env = {
            "SDD_HOOKS_DISABLE": "1",
            "SDD_SUBAGENT_CONTRACT": "1",  # soft mode
        }
        payload = {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "dev-senior", "prompt": "demo"},
        }
        with patch.dict(os.environ, env, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertEqual(hook_out.get("hookEventName"), "PreToolUse")
        ctx = hook_out.get("additionalContext", "")
        self.assertIn("SDD-SUBAGENT-CONTRACT", ctx,
                      msg=f"expected subagent hint even with HOOKS_DISABLE=1, got: {ctx!r}")

    def test_hooks_disable_non_task_returns_plain_output(self) -> None:
        """Sanity check: HOOKS_DISABLE for non-Task tool still returns empty
        additionalContext (no false-positive injection)."""
        env = {"SDD_HOOKS_DISABLE": "1", "SDD_SUBAGENT_CONTRACT": "1"}
        payload = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}}
        with patch.dict(os.environ, env, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertNotIn("additionalContext", hook_out)

    def test_hooks_disable_with_contract_off_skips_injection(self) -> None:
        """If subagent contract is explicitly off, HOOKS_DISABLE path stays
        quiet — the fix only preserves injection when the contract is ON."""
        env = {"SDD_HOOKS_DISABLE": "1", "SDD_SUBAGENT_CONTRACT": "0"}
        payload = {
            "tool_name": "Task",
            "tool_input": {"subagent_type": "dev-senior"},
        }
        with patch.dict(os.environ, env, clear=False):
            out = self.runner.run(payload)
        self.assertNotIn(
            "additionalContext", out.get("hookSpecificOutput", {}),
        )


class LegacyReadFallbackTests(unittest.TestCase):
    """P1-05: legacy Read fallback must add cat -n line overhead."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_fallback_read_includes_line_overhead(self) -> None:
        src = self.root / "sample.txt"
        # Write 10 short lines so line-count overhead is material relative to size.
        src.write_text("\n".join(f"l{i}" for i in range(10)) + "\n", encoding="utf-8")
        size = src.stat().st_size

        # Force the legacy fallback path by making estimate_tool_tokens raise.
        from tools.fsm_runtime import conversation_ledger as cl

        def _boom(*_a, **_k):
            raise RuntimeError("simulated import failure")

        with patch.object(cl, "estimate_tool_tokens", _boom):
            legacy = self.mod._estimate_tokens("Read", {"file_path": str(src)})

        size_only = max(1, size // 4)
        self.assertGreater(
            legacy, size_only,
            msg=f"legacy fallback ignored line overhead: legacy={legacy} size_only={size_only}",
        )
        # Upper bound — should not exceed (size + 10*8)/4 + 1
        self.assertLessEqual(legacy, (size + 10 * 8) // 4 + 1)

    def test_fallback_read_missing_file_returns_zero(self) -> None:
        from tools.fsm_runtime import conversation_ledger as cl

        with patch.object(cl, "estimate_tool_tokens", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))):
            self.assertEqual(self.mod._estimate_tokens("Read", {"file_path": str(self.root / "nope.txt")}), 0)
            self.assertEqual(self.mod._estimate_tokens("Read", {"file_path": None}), 0)


class ZeroTokenEscalationTests(unittest.TestCase):
    """P2-08: zero-delta tool calls must still trigger TOKEN_BUDGET_CRITICAL
    / AUTO_COMPACT when cumulative ratio is already past threshold."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)
        # Small MAX_CONTEXT so we can cross thresholds easily
        self.mod.MAX_CONTEXT = 1000
        self.runner = _MainRunner(self.mod)

        # Isolate FSM state from the repo's real FSM-STATE-*.yaml so the hook
        # doesn't see a live ESCALATION / HUMAN_PENDING from another session.
        from tools.fsm_runtime.fsm_runtime import FSMRuntime
        from tools.fsm_runtime.state_loader import load_state
        self._fsm_state_path = self.root / "FSM-STATE-zerotoken.yaml"
        state = load_state("zerotoken-proj", path=self._fsm_state_path)
        state.current = "SPEC_DRAFTING"  # benign state; Bash is allowed
        self._isolated_rt = FSMRuntime(state)

        # Patch FSMRuntime.bootstrap used by the hook to return our isolated rt.
        import tools.fsm_runtime.fsm_runtime as fsm_rt_mod
        self._boot_patch = patch.object(
            fsm_rt_mod.FSMRuntime, "bootstrap",
            classmethod(lambda cls, project=None: self._isolated_rt),
        )
        self._boot_patch.start()

    def tearDown(self) -> None:
        self._boot_patch.stop()
        self._tmp.cleanup()

    def _seed_ledger(self, cumulative: int) -> None:
        """Write a minimal daily ledger with `cumulative` already spent."""
        import datetime as _dt
        import yaml  # noqa: WPS433

        path = self.root / f"CONTEXT-LEDGER-{_dt.date.today().isoformat()}.yaml"
        doc = {
            "date": _dt.date.today().isoformat(),
            "cumulative_tokens": cumulative,
            "entries": [{"tokens": cumulative, "phase": "pre", "tool": "Seed"}],
        }
        path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")

    def test_zero_token_tool_still_denies_at_crit_ratio(self) -> None:
        # Cumulative already 96% of 1000 = 960. A Bash with empty command
        # estimates to 0 tokens → should hit TOKEN_BUDGET_CRITICAL branch.
        self._seed_ledger(960)
        payload = {"tool_name": "Bash", "tool_input": {"command": ""}}
        with patch.dict(os.environ, {
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
        }, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertEqual(
            hook_out.get("permissionDecision"), "deny",
            msg=f"expected deny for tokens==0 at 96%, got: {hook_out}",
        )
        self.assertIn("TOKEN_BUDGET_CRITICAL", hook_out.get("permissionDecisionReason", ""))

    def test_zero_token_tool_triggers_auto_compact_at_90pct(self) -> None:
        """90-94% range with tokens==0 must trigger AUTO_COMPACT_PENDING
        via the new early-return branch (not silent pass-through)."""
        self._seed_ledger(920)  # 92%
        payload = {"tool_name": "Bash", "tool_input": {"command": ""}}
        with patch.dict(os.environ, {
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
        }, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        ctx = hook_out.get("additionalContext", "")
        self.assertIn("AUTO-COMPACT", ctx,
                      msg=f"expected AUTO-COMPACT notice at 92% with tokens==0, got: {hook_out}")

    def test_zero_token_tool_under_warn_passes_through(self) -> None:
        """Sanity: tokens==0 below WARN_RATIO must NOT raise a warning."""
        self._seed_ledger(300)  # 30%
        payload = {"tool_name": "Bash", "tool_input": {"command": ""}}
        with patch.dict(os.environ, {
            "SDD_HOOKS_DISABLE": "",
            "SDD_HOOKS_DRY_RUN": "",
            "SDD_SUBAGENT_CONTRACT": "0",
        }, clear=False):
            out = self.runner.run(payload)
        hook_out = out.get("hookSpecificOutput", {})
        self.assertNotIn("permissionDecision", hook_out)
        self.assertNotIn("AUTO-COMPACT", hook_out.get("additionalContext", ""))


class MaxContextGuardTests(unittest.TestCase):
    """DEF-CLDREV-002 (symmetric) + DEF-CLDREV-012: a misconfigured
    SDD_MAX_CONTEXT (zero / negative / non-numeric) must NOT crash the pre hook
    at import time. A crash here silently disables the entire context-budget gate
    (cumulative tokens stop recording, 85% warn / 95% deny / auto-compact never
    fire) — the opposite of the hook's purpose."""

    def test_zero_floors_to_default(self) -> None:
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "0"}, clear=False):
            mod = _load_hook_module(Path(tempfile.gettempdir()))
            self.assertEqual(mod.MAX_CONTEXT, 200000)

    def test_negative_floors_to_default(self) -> None:
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "-5"}, clear=False):
            mod = _load_hook_module(Path(tempfile.gettempdir()))
            self.assertEqual(mod.MAX_CONTEXT, 200000)

    def test_non_numeric_falls_back_to_default(self) -> None:
        """Pre-fix: `int("abc")` raises ValueError at import → hook crashes.
        Post-fix: falls back to 200000, matching the 0/negative floor."""
        for bad in ("abc", "1.5", "12k"):
            with patch.dict(os.environ, {"SDD_MAX_CONTEXT": bad}, clear=False):
                mod = _load_hook_module(Path(tempfile.gettempdir()))
                self.assertEqual(mod.MAX_CONTEXT, 200000, msg=f"value={bad!r}")

    def test_valid_value_preserved(self) -> None:
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "50000"}, clear=False):
            mod = _load_hook_module(Path(tempfile.gettempdir()))
            self.assertEqual(mod.MAX_CONTEXT, 50000)


if __name__ == "__main__":
    unittest.main()
