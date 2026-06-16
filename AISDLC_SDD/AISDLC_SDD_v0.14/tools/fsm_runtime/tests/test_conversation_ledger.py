"""Unit tests for ACT-024 Ledger Precision Upgrade (Phase E M2)."""
from __future__ import annotations

import datetime as _dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import yaml  # noqa: E402

from tools.fsm_runtime.conversation_ledger import (  # noqa: E402
    estimate_bash_command_tokens,
    estimate_conversation_overhead,
    estimate_read_tokens,
    estimate_tool_tokens,
    merge_conversation_overhead_into_ledger,
    record_calibration_sample,
)


class LedgerPrecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_ledger(self, entries: list) -> Path:
        date = _dt.date.today().isoformat()
        path = self.root / f"CONTEXT-LEDGER-{date}.yaml"
        doc = {
            "date": date,
            "cumulative_tokens": sum(int(e.get("tokens", 0)) for e in entries),
            "entries": entries,
        }
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def test_read_tokens_include_line_prefix_overhead(self) -> None:
        src = self.root / "sample.txt"
        content = "line1\nline2\nline3\nline4\nline5\n"
        src.write_text(content, encoding="utf-8")
        size_only_estimate = max(1, src.stat().st_size // 4)
        precise = estimate_read_tokens(str(src))
        # Precise estimate should be >= size-only due to cat -n prefix overhead
        self.assertGreater(precise, size_only_estimate - 1)
        # And bounded — should not exceed size + 5*8 chars worth of tokens
        upper = (src.stat().st_size + 5 * 8) // 4 + 1
        self.assertLessEqual(precise, upper)

    def test_read_tokens_returns_zero_for_missing_file(self) -> None:
        self.assertEqual(estimate_read_tokens(str(self.root / "nope.txt")), 0)
        self.assertEqual(estimate_read_tokens(None), 0)
        self.assertEqual(estimate_read_tokens(""), 0)

    def test_bash_command_estimate(self) -> None:
        self.assertEqual(estimate_bash_command_tokens(None), 0)
        self.assertEqual(estimate_bash_command_tokens(""), 0)
        self.assertEqual(estimate_bash_command_tokens("ls -la"), max(1, len("ls -la") // 4))

    def test_conversation_overhead_scales_linearly(self) -> None:
        self.assertEqual(estimate_conversation_overhead(0), 0)
        self.assertEqual(estimate_conversation_overhead(1), 300)
        self.assertEqual(estimate_conversation_overhead(10), 3000)

    def test_estimate_tool_tokens_dispatches(self) -> None:
        # Task estimate must include conversation overhead (300 tokens / turn)
        # on top of the prompt tokens — see Rule 9.8.2 / ACT-024 P1-06 fix.
        prompt = "abcd" * 40
        prompt_tokens = max(1, len(prompt) // 4)
        self.assertEqual(
            estimate_tool_tokens("Task", {"prompt": prompt}),
            prompt_tokens + estimate_conversation_overhead(1),
        )
        self.assertEqual(estimate_tool_tokens("Unknown", {}), 0)

    def test_task_estimate_includes_conversation_overhead(self) -> None:
        """Pure regression for P1-06: Task without prompt still pays subagent
        overhead because the subagent system-prompt is non-trivial."""
        zero_prompt = estimate_tool_tokens("Task", {"prompt": ""})
        self.assertGreaterEqual(zero_prompt, estimate_conversation_overhead(1))
        big_prompt = estimate_tool_tokens("Task", {"prompt": "x" * 4000})
        self.assertGreaterEqual(
            big_prompt - zero_prompt, 1000 - 1,
            "prompt-driven delta should match len(prompt)//4",
        )

    def test_merge_below_threshold_noop(self) -> None:
        # 10 entries = 5 tool calls (pre+post each writes an entry).
        # Under the new entries_per_call=2 semantics this must NOT trigger
        # when merge_every=10 tool calls.
        self._write_ledger([{"tokens": 100} for _ in range(10)])
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res["merged"])
        self.assertEqual(res["added_tokens"], 0)

    def test_merge_at_threshold_appends_conv_overhead_entry(self) -> None:
        # P1-06 fix: merge_every=10 now means 10 tool calls = 20 entries.
        path = self._write_ledger([{"tokens": 100} for _ in range(20)])
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(res["added_tokens"], 3000)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["cumulative_tokens"], 2000 + 3000)
        self.assertEqual(doc["entries"][-1]["phase"], "conv-overhead")
        self.assertEqual(doc["entries"][-1]["messages_counted"], 10)
        self.assertEqual(doc["entries"][-1]["entries_counted"], 20)
        # A second immediate call should not double-count
        res2 = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res2["merged"])

    def test_merge_pre_post_pairs_equal_one_tool_call(self) -> None:
        """P1-06 regression: 20 entries from pre+post pairs = 10 tool calls,
        and only ONE conv-overhead entry of 3000 tokens is appended — not two
        as would happen under the old "every 10 entries" semantics."""
        path = self._write_ledger([
            {"tokens": 50, "phase": "pre" if i % 2 == 0 else "post"}
            for i in range(20)
        ])
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(res["added_tokens"], 3000)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        conv_entries = [e for e in doc["entries"] if e.get("phase") == "conv-overhead"]
        self.assertEqual(len(conv_entries), 1, "10 tool calls must emit exactly ONE merge")
        self.assertEqual(conv_entries[0]["messages_counted"], 10)

    def test_merge_entries_per_call_override(self) -> None:
        """Allow callers (tests / future hook changes) to count entries-per-call
        explicitly. With entries_per_call=1 the historical 'every 10 entries'
        semantics is preserved for backward-compat callers."""
        path = self._write_ledger([{"tokens": 100} for _ in range(10)])
        res = merge_conversation_overhead_into_ledger(
            self.root, merge_every=10, entries_per_call=1,
        )
        self.assertTrue(res["merged"])
        self.assertEqual(res["added_tokens"], 3000)
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["entries"][-1]["messages_counted"], 10)

    def test_merge_with_no_ledger_is_safe(self) -> None:
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res["merged"])

    def test_sidecar_merges_into_primary_at_tick(self) -> None:
        """QA Round-3 P2-07 — when file_lock contention routes entries to a
        `.append` sidecar, the next merge tick must fold them back into the
        primary ledger so delta_entries is accurate and sidecars don't leak.
        """
        date = _dt.date.today().isoformat()
        path = self.root / f"CONTEXT-LEDGER-{date}.yaml"
        # 10 entries in primary; 10 more staged in sidecar. Total 20 = 10 tool
        # calls at entries_per_call=2 — exactly the merge threshold.
        self._write_ledger([{"tokens": 100, "phase": "pre"} for _ in range(10)])
        sidecar = path.with_suffix(path.suffix + ".append")
        sidecar_entries = [{"tokens": 100, "phase": "post"} for _ in range(10)]
        with sidecar.open("w", encoding="utf-8") as f:
            yaml.safe_dump(sidecar_entries, f, allow_unicode=True, sort_keys=False)

        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(res["sidecar_merged"], 10)
        self.assertFalse(sidecar.exists(), "sidecar must be consumed after merge")
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        # Original 1000 + sidecar 1000 + conv overhead 3000 = 5000.
        self.assertEqual(doc["cumulative_tokens"], 5000)
        # 20 real entries + 1 conv-overhead entry = 21 entries total.
        self.assertEqual(len(doc["entries"]), 21)
        # A follow-up merge should not double count (sidecar already consumed).
        res2 = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertFalse(res2["merged"])

    def test_sidecar_absent_does_not_report_merge(self) -> None:
        """Regression: sidecar_merged must be 0 when sidecar file is absent."""
        self._write_ledger([{"tokens": 100} for _ in range(20)])
        res = merge_conversation_overhead_into_ledger(self.root, merge_every=10)
        self.assertTrue(res["merged"])
        self.assertEqual(res.get("sidecar_merged", 0), 0)

    def test_calibration_sample_tracks_drift(self) -> None:
        out = record_calibration_sample(self.root, estimated=100, observed=110, source="unit")
        self.assertTrue(out.exists())
        doc = yaml.safe_load(out.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["samples"]), 1)
        self.assertAlmostEqual(doc["latest_drift_pct"], (10 / 110) * 100, places=2)
        record_calibration_sample(self.root, estimated=200, observed=180, source="unit")
        doc = yaml.safe_load(out.read_text(encoding="utf-8"))
        self.assertEqual(len(doc["samples"]), 2)
        self.assertIn("rolling_avg_drift_pct_last10", doc)


if __name__ == "__main__":
    unittest.main()
