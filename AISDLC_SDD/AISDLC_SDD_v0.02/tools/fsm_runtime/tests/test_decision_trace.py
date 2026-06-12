# enforces (governance rules): R-9.8
"""Unit tests for ACT-025 Decision Trace Capture (Phase E M2)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state  # noqa: E402


class DecisionTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-trace.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _boot(self, start: str = "SPEC_DRAFTING") -> FSMRuntime:
        state = load_state("trace-proj", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = start
        return rt

    def test_transition_appends_trace_with_reason_and_refs(self) -> None:
        rt = self._boot()
        rt.transition(
            "SCG_VALIDATION",
            reason="explicit advance for test",
            spec_refs=["docs/01_requirements/FRD-Demo.md"],
            trigger="manual",
        )
        trace = rt.state.root.get("decision_trace") or []
        self.assertEqual(len(trace), 1)
        e = trace[-1]
        self.assertEqual(e["from"], "SPEC_DRAFTING")
        self.assertEqual(e["to"], "SCG_VALIDATION")
        self.assertEqual(e["trigger"], "manual")
        self.assertIn("explicit advance", e["reason"])
        self.assertEqual(e["spec_refs"], ["docs/01_requirements/FRD-Demo.md"])
        self.assertTrue(e["ts"])

    def test_gate_pass_records_trace(self) -> None:
        rt = self._boot(start="SCG_VALIDATION")
        rt.record_gate_result("SCG_VALIDATION", "PASS")
        trace = rt.state.root.get("decision_trace") or []
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[-1]["trigger"], "gate_pass")
        self.assertEqual(trace[-1]["to"], "HUMAN_PENDING")

    def test_gate_fail_records_trace_with_reason(self) -> None:
        rt = self._boot(start="SCG_VALIDATION")
        rt.record_gate_result("SCG_VALIDATION", "FAIL", reason="NFR missing")
        trace = rt.state.root.get("decision_trace") or []
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[-1]["trigger"], "gate_fail")
        self.assertIn("NFR missing", trace[-1]["reason"])

    def test_auto_compact_trigger_and_complete_recorded(self) -> None:
        rt = self._boot(start="IMPLEMENTATION")
        result = rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.9)
        self.assertFalse(result.get("escalated", False))
        rt.complete_auto_compact(reset_ledger=False)
        trace = rt.state.root.get("decision_trace") or []
        triggers = [e["trigger"] for e in trace]
        self.assertIn("auto_compact_trigger", triggers)
        self.assertIn("auto_compact_complete", triggers)

    def test_spec_frozen_records_spec_refs(self) -> None:
        rt = self._boot(start="HUMAN_PENDING")
        docs = ["docs/01_requirements/FRD-A.md", "docs/02_architecture/SRD-A.md"]
        rt.record_spec_frozen("Stage-1", docs)
        trace = rt.state.root.get("decision_trace") or []
        self.assertEqual(trace[-1]["trigger"], "spec_frozen")
        self.assertEqual(trace[-1]["spec_refs"], docs)

    def test_flush_old_trace_beyond_max_keep(self) -> None:
        rt = self._boot()
        # Append 55 entries directly via state helper
        for i in range(55):
            rt.state.append_decision_trace(
                from_state="A", to_state="B", reason=f"n{i}", trigger="manual"
            )
        self.assertEqual(len(rt.state.root["decision_trace"]), 50)
        self.assertEqual(len(rt.state.root["decision_trace_flushed"]), 5)

    def test_repeated_flush_beyond_max_keep_no_drift(self) -> None:
        """QA Round-4 P2: verify bounded flush under sustained load.

        Appending 210 entries in stages (reaching 51, 100, 150, 210) must:
          - keep `decision_trace` length at exactly max_keep (50) once saturated
          - accumulate flushed entries monotonically (reason n0..n159 preserved)
          - keep the tail window (reason n160..n209) in the active list
        Off-by-one in `trace[overflow:]` would surface as the active list
        drifting away from 50 entries or as missing reasons in the flushed set.
        """
        rt = self._boot()
        # Stage 1: first 51 — active caps at 50, flushed gets 1.
        for i in range(51):
            rt.state.append_decision_trace(
                from_state="A", to_state="B", reason=f"n{i}", trigger="manual"
            )
        self.assertEqual(len(rt.state.root["decision_trace"]), 50)
        self.assertEqual(len(rt.state.root["decision_trace_flushed"]), 1)
        # Stage 2..4: continue appending, each checkpoint verifies invariants.
        for checkpoint in (100, 150, 210):
            while (
                sum(
                    (
                        len(rt.state.root.get("decision_trace") or []),
                        len(rt.state.root.get("decision_trace_flushed") or []),
                    )
                )
                < checkpoint
            ):
                idx = len(rt.state.root.get("decision_trace") or []) + len(
                    rt.state.root.get("decision_trace_flushed") or []
                )
                rt.state.append_decision_trace(
                    from_state="A", to_state="B", reason=f"n{idx}", trigger="manual"
                )
            self.assertEqual(
                len(rt.state.root["decision_trace"]), 50,
                msg=f"active list drifted at checkpoint {checkpoint}",
            )
            self.assertEqual(
                len(rt.state.root["decision_trace_flushed"]), checkpoint - 50,
                msg=f"flushed count drifted at checkpoint {checkpoint}",
            )
        # Tail window assertion: the newest 50 reasons are n160..n209.
        active_reasons = [e["reason"] for e in rt.state.root["decision_trace"]]
        self.assertEqual(active_reasons[0], "n160")
        self.assertEqual(active_reasons[-1], "n209")
        # Flushed invariant: reasons n0..n159 all present, exactly once.
        flushed_reasons = [e["reason"] for e in rt.state.root["decision_trace_flushed"]]
        self.assertEqual(len(flushed_reasons), 160)
        self.assertEqual(flushed_reasons[0], "n0")
        self.assertEqual(flushed_reasons[-1], "n159")
        self.assertEqual(len(set(flushed_reasons)), 160, "duplicate flush detected")

    def test_cli_transition_records_trigger_and_reason(self) -> None:
        """P0-01 regression: CLI-driven transitions must carry reason+trigger
        so the decision trace cannot be polluted with empty entries."""
        rt = self._boot()
        # Simulate the CLI call site: transition() with explicit cli_manual
        # trigger and a reason auto-derived from --to.
        rt.transition(
            "SCG_VALIDATION",
            reason="cli transition to SCG_VALIDATION",
            trigger="cli_manual",
        )
        trace = rt.state.root.get("decision_trace") or []
        self.assertTrue(trace)
        last = trace[-1]
        self.assertEqual(last["trigger"], "cli_manual")
        self.assertIn("cli transition", last["reason"])


if __name__ == "__main__":
    unittest.main()
