#!/usr/bin/env python3
"""`.claude/hooks/sdd_hook_router.py` 的回歸鎖（R158 P4）。 round-label-ok

WHY：`_drift_advisory()`（DEF-43-004）此前只寫 router 自己的 `sys.stderr`，而
SessionStart 是 exit 0 路徑、stderr 不進模型 context（官方契約）⇒ 可能長期靜默
（CrossPlatform R158 分析 A1 路徑 6）。本輪改優先併進 child 的 round-label-ok
`hookSpecificOutput.additionalContext`（走 stdout），併不進去才退回 stderr。

只鎖三支純函式與一個端到端合成情境，不驗證真實 v0.30 內容；router 零相依契約
（stdlib-only），本檔呼叫同樣只用 stdlib。
"""
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "sdd_hook_router.py"

sys.path.insert(0, str(_HOOK.parent))
import sdd_hook_router as router  # noqa: E402

_LEGACY_LITERAL = "TOKEN_BUDGET_CRITICAL: cumulative="


class TargetWritesLegacyTokenBudgetCriticalTest(unittest.TestCase):
    """`_target_writes_legacy_token_budget_critical`：純字面比對，不 import 目標版模組。"""

    def test_true_when_target_context_ledger_pre_contains_legacy_literal(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            hooks_dir = root / "AISDLC_SDD" / "AISDLC_SDD_v9.8" / ".claude" / "hooks"
            hooks_dir.mkdir(parents=True)
            (hooks_dir / "context_ledger_pre.py").write_text(
                f'reason = f"{_LEGACY_LITERAL}{{existing_cum}}"\n', encoding="utf-8",
            )
            with mock.patch.object(router, "REPO_ROOT", root):
                self.assertTrue(router._target_writes_legacy_token_budget_critical("9.8"))

    def test_false_when_target_uses_session_level_semantics(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            hooks_dir = root / "AISDLC_SDD" / "AISDLC_SDD_v9.8" / ".claude" / "hooks"
            hooks_dir.mkdir(parents=True)
            (hooks_dir / "context_ledger_pre.py").write_text(
                "reason = 'session 級 deny，不寫專案級狀態'\n", encoding="utf-8",
            )
            with mock.patch.object(router, "REPO_ROOT", root):
                self.assertFalse(router._target_writes_legacy_token_budget_critical("9.8"))

    def test_false_when_target_file_missing(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(router, "REPO_ROOT", root):
                self.assertFalse(router._target_writes_legacy_token_budget_critical("9.8"))


class DriftAdvisoryTextTest(unittest.TestCase):
    """`_drift_advisory_text`：純文字組裝，不做 I/O。"""

    def test_none_when_no_drift(self) -> None:
        with mock.patch.object(router, "_disk_latest_version", return_value="9.8"):
            self.assertIsNone(router._drift_advisory_text("9.8"))

    def test_none_when_disk_scan_fails(self) -> None:
        with mock.patch.object(router, "_disk_latest_version", return_value=None):
            self.assertIsNone(router._drift_advisory_text("9.8"))

    def test_advisory_text_when_active_is_behind_latest(self) -> None:
        with mock.patch.object(router, "_disk_latest_version", return_value="9.9"), \
             mock.patch.object(
                 router, "_target_writes_legacy_token_budget_critical", return_value=False,
             ):
            text = router._drift_advisory_text("9.8")
        self.assertIsNotNone(text)
        self.assertIn("SDD_ACTIVE_VERSION=v9.8", text)
        self.assertIn("v9.9", text)
        self.assertNotIn("TOKEN_BUDGET_CRITICAL", text)

    def test_advisory_text_adds_legacy_semantics_warning(self) -> None:
        with mock.patch.object(router, "_disk_latest_version", return_value="9.9"), \
             mock.patch.object(
                 router, "_target_writes_legacy_token_budget_critical", return_value=True,
             ):
            text = router._drift_advisory_text("9.8")
        self.assertIn("仍寫專案級 TOKEN_BUDGET_CRITICAL", text)
        self.assertIn("SDD_ACTIVE_VERSION=9.9", text)


class MergeAdvisoryIntoStdoutTest(unittest.TestCase):
    """`_merge_advisory_into_stdout`：優先併進合法 JSON 的 additionalContext。"""

    def test_merges_into_valid_additional_context(self) -> None:
        original = json.dumps({
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "hello"},
        })
        merged_text, merged = router._merge_advisory_into_stdout(original, "ADVISORY-X")
        self.assertTrue(merged)
        doc = json.loads(merged_text)
        ctx = doc["hookSpecificOutput"]["additionalContext"]
        self.assertIn("hello", ctx)
        self.assertIn("ADVISORY-X", ctx)

    def test_leaves_invalid_json_untouched(self) -> None:
        original = "not json"
        merged_text, merged = router._merge_advisory_into_stdout(original, "ADVISORY-X")
        self.assertFalse(merged)
        self.assertEqual(merged_text, original)

    def test_leaves_missing_hook_specific_output_untouched(self) -> None:
        original = json.dumps({"somethingElse": True})
        merged_text, merged = router._merge_advisory_into_stdout(original, "ADVISORY-X")
        self.assertFalse(merged)
        self.assertEqual(merged_text, original)

    def test_leaves_non_string_additional_context_untouched(self) -> None:
        original = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart"}})
        merged_text, merged = router._merge_advisory_into_stdout(original, "ADVISORY-X")
        self.assertFalse(merged)
        self.assertEqual(merged_text, original)


class MainSessionStartDriftEndToEndTest(unittest.TestCase):
    """`main()` 對合成 tempdir 版本樹的端到端情境——advisory 是否真的送達 stdout JSON。"""

    def _synth_tree(self, tmp_root: Path, *, active: str, latest: str) -> Path:
        for ver in {active, latest}:
            hooks_dir = tmp_root / "AISDLC_SDD" / f"AISDLC_SDD_v{ver}" / ".claude" / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)
        active_hooks = tmp_root / "AISDLC_SDD" / f"AISDLC_SDD_v{active}" / ".claude" / "hooks"
        (active_hooks / "session_start.py").write_text(
            "import json, sys\n"
            "sys.stdout.write(json.dumps({'hookSpecificOutput': "
            "{'hookEventName': 'SessionStart', 'additionalContext': 'child says hi'}}))\n",
            encoding="utf-8",
        )
        (active_hooks / "context_ledger_pre.py").write_text(
            "reason = 'session 級 deny'\n", encoding="utf-8",
        )
        return tmp_root

    def test_advisory_merged_into_child_stdout_when_drifted(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._synth_tree(Path(td), active="9.8", latest="9.9")
            out = io.StringIO()
            err = io.StringIO()
            with mock.patch.object(router, "REPO_ROOT", root), \
                 mock.patch.dict(router.os.environ, {"SDD_ACTIVE_VERSION": "9.8"}, clear=False), \
                 mock.patch.object(sys, "stdin", io.StringIO("{}")), \
                 redirect_stdout(out), redirect_stderr(err):
                rc = router.main(["sdd_hook_router.py", "session_start"])
        self.assertEqual(rc, 0)
        doc = json.loads(out.getvalue())
        ctx = doc["hookSpecificOutput"]["additionalContext"]
        self.assertIn("child says hi", ctx)
        self.assertIn("[SDD-ROUTER][advisory]", ctx)
        self.assertIn("v9.9", ctx)
        # 併成功就不該再退回 stderr（不重複印同一件事）。
        self.assertNotIn("[SDD-ROUTER][advisory]", err.getvalue())

    def test_no_advisory_text_when_active_is_already_latest(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._synth_tree(Path(td), active="9.8", latest="9.8")
            out = io.StringIO()
            err = io.StringIO()
            with mock.patch.object(router, "REPO_ROOT", root), \
                 mock.patch.dict(router.os.environ, {"SDD_ACTIVE_VERSION": "9.8"}, clear=False), \
                 mock.patch.object(sys, "stdin", io.StringIO("{}")), \
                 redirect_stdout(out), redirect_stderr(err):
                rc = router.main(["sdd_hook_router.py", "session_start"])
        self.assertEqual(rc, 0)
        doc = json.loads(out.getvalue())
        ctx = doc["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(ctx, "child says hi")
        self.assertEqual(err.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
