# enforces (governance rules): R-9.2, R-9.6
"""Unit tests for QA patches on `.claude/hooks/context_ledger_post.py`.

Covers:
- DEF-CLDREV-002: SDD_MAX_CONTEXT=0 / negative must NOT crash the :140 ratio
  calculation (cumulative / MAX_CONTEXT) with ZeroDivisionError — symmetric with
  the floor guard already present in context_ledger_pre.py:31-35.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

HOOK_MODULE_PATH = (
    Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "context_ledger_post.py"
)


def _load_hook_module(tmp_root: Path):
    """Import the post hook fresh so module-level MAX_CONTEXT reflects the env
    set by the caller (it is read at import time, like the pre hook)."""
    spec = importlib.util.spec_from_file_location("context_ledger_post_test", str(HOOK_MODULE_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.LEDGER_DIR = tmp_root
    return mod


class _MainRunner:
    def __init__(self, mod):
        self.mod = mod

    def run(self, payload: dict) -> dict:
        buf_out = StringIO()

        class _FakeStdin(StringIO):
            def isatty(self) -> bool:
                return False

        fake_stdin = _FakeStdin(json.dumps(payload))
        with patch.object(sys, "stdin", fake_stdin), patch.object(sys, "stdout", buf_out):
            rc = self.mod.main()
        assert rc == 0
        raw = buf_out.getvalue().strip()
        return json.loads(raw) if raw else {}


class MaxContextFloorTests(unittest.TestCase):
    """DEF-CLDREV-002: zero / negative SDD_MAX_CONTEXT must degrade gracefully."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run_with_env(self, max_ctx: str) -> dict:
        # A non-empty tool_response → _estimate_result_tokens > 0 → cumulative > 0
        # → the :140 `ratio = cumulative / MAX_CONTEXT` line is exercised.
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/x"},
            "tool_response": "x" * 4000,
        }
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": max_ctx}, clear=False):
            mod = _load_hook_module(self.root)
            return _MainRunner(mod).run(payload)

    def test_zero_max_context_does_not_crash(self) -> None:
        """Pre-fix: MAX_CONTEXT=0 → ZeroDivisionError at :140 → hook crashes.
        Post-fix: floored to 200000, ratio computed, hook returns cleanly."""
        out = self._run_with_env("0")
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")

    def test_negative_max_context_does_not_crash(self) -> None:
        out = self._run_with_env("-5")
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")

    def test_floor_applied_value(self) -> None:
        """Intent (Rule 9): the floor must land on 200000, matching the pre hook,
        so a misconfigured operator gets the same graceful budget — not an
        arbitrary value or a crash."""
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "0"}, clear=False):
            mod = _load_hook_module(self.root)
            self.assertEqual(mod.MAX_CONTEXT, 200000)
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "50000"}, clear=False):
            mod = _load_hook_module(self.root)
            self.assertEqual(mod.MAX_CONTEXT, 50000)  # valid value preserved

    def test_non_numeric_max_context_does_not_crash(self) -> None:
        """DEF-CLDREV-012: a non-numeric SDD_MAX_CONTEXT (operator typo) must NOT
        raise ValueError at import time. Pre-fix: `int("abc")` crashes the whole
        hook → the context-budget gate is silently disabled. Post-fix: falls back
        to the 200000 default and the hook runs cleanly."""
        out = self._run_with_env("abc")
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")
        out = self._run_with_env("1.5")
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")

    def test_non_numeric_falls_back_to_default(self) -> None:
        """Intent (Rule 9): a non-numeric value must land on the same 200000 floor
        as 0/negative, so the gate keeps a sane budget rather than vanishing."""
        with patch.dict(os.environ, {"SDD_MAX_CONTEXT": "abc"}, clear=False):
            mod = _load_hook_module(self.root)
            self.assertEqual(mod.MAX_CONTEXT, 200000)


class MalformedPayloadTests(unittest.TestCase):
    """DEF-CLDREV-025: symmetric with the pre hook — a JSON-valid but non-dict
    top-level payload (`[1,2,3]`) or non-dict tool_input must NOT crash the post
    hook with AttributeError at `inp.get(...)` / `tool_input.get(...)`. Both must
    normalize to {}."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.mod = _load_hook_module(self.root)
        self.runner = _MainRunner(self.mod)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_top_level_list_does_not_crash(self) -> None:
        out = self.runner.run([1, 2, 3])  # type: ignore[arg-type]
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")

    def test_list_tool_input_does_not_crash(self) -> None:
        out = self.runner.run(
            {"tool_name": "Read", "tool_input": [1, 2, 3], "tool_response": "x"}  # type: ignore[dict-item]
        )
        self.assertEqual(out.get("hookSpecificOutput", {}).get("hookEventName"), "PostToolUse")


if __name__ == "__main__":
    unittest.main()
