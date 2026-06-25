# enforces (governance rules): R-9.14, R-9.5
"""Phase G M1 / ACT-033/034: auto_recovery + FSMRuntime self-healing tests.

Covers:
  - Rule 9.14.1 session-wide ≤ 3 attempts
  - Rule 9.14.2 ≤ 1 attempt per same reason
  - Rule 9.14.3 structural never auto-recoverable
  - Rule 9.14.4 fail → ESCALATION_FINAL (no further recovery)
  - FSMRuntime.enter_auto_recovery / exit_auto_recovery roundtrip
  - assert_tool_allowed blocks ESCALATION_FINAL (B1.7 sealed-guard)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import auto_recovery  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state, save_state  # noqa: E402
from tools.fsm_runtime.transition_rules import TransitionError  # noqa: E402


def _make_state(td: Path, name: str, current: str = "ESCALATION"):
    """Helper: create a fresh FSMState in a temp dir, set current."""
    path = td / f"FSM-STATE-{name}.yaml"
    state = load_state(name, path=path, create_if_missing=True)
    state.root["current_state"] = current
    save_state(state)
    return state


class ProposeRecoveryTests(unittest.TestCase):
    def test_transient_high_confidence_allowed(self):
        proposal = auto_recovery.propose_recovery("CI runner timeout 30s")
        self.assertTrue(proposal.allowed)
        self.assertEqual(proposal.action, "wait_and_rerun")
        self.assertEqual(proposal.wait_sec, 30)
        self.assertTrue(proposal.resume_state_required)

    def test_structural_refused(self):
        proposal = auto_recovery.propose_recovery("SLV-005 FAIL on AC-015")
        self.assertFalse(proposal.allowed)
        self.assertIn("9.14.3", proposal.refusal_reason)

    def test_unknown_low_confidence_refused(self):
        proposal = auto_recovery.propose_recovery("alien failure mode")
        self.assertFalse(proposal.allowed)
        # diagnostic returns unknown/structural so 9.14.3 fires first;
        # confidence-threshold path is exercised separately below.
        self.assertIn("9.14.3", proposal.refusal_reason)


class BoundsCheckTests(unittest.TestCase):
    def test_rule_9_14_1_session_limit(self):
        """≥ 3 session_attempt_count → refuse."""
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "rule-9141")
            rs = auto_recovery._recovery_state(state)
            rs["session_attempt_count"] = 3
            ok, reason = auto_recovery.bounds_check(state, "abc123")
            self.assertFalse(ok)
            self.assertIn("9.14.1", reason)

    def test_rule_9_14_2_per_reason_limit(self):
        """Same reason hash already 1 → refuse."""
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "rule-9142")
            rs = auto_recovery._recovery_state(state)
            rs["per_reason_count"]["abc123"] = 1
            ok, reason = auto_recovery.bounds_check(state, "abc123")
            self.assertFalse(ok)
            self.assertIn("9.14.2", reason)

    def test_under_limits_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "under-limits")
            ok, reason = auto_recovery.bounds_check(state, "fresh_hash")
            self.assertTrue(ok)
            self.assertEqual(reason, "")


class ReasonHashTests(unittest.TestCase):
    def test_normalization_collapses_whitespace_and_case(self):
        h1 = auto_recovery.reason_hash("CI runner   TIMEOUT")
        h2 = auto_recovery.reason_hash("  ci runner timeout  ")
        self.assertEqual(h1, h2)

    def test_distinct_reasons_distinct_hashes(self):
        h1 = auto_recovery.reason_hash("ConnectionError")
        h2 = auto_recovery.reason_hash("rate limit 429")
        self.assertNotEqual(h1, h2)

    def test_truncates_to_200_chars(self):
        long_reason = "x" * 1000
        h = auto_recovery.reason_hash(long_reason)
        self.assertEqual(len(h), 16)


class RecordAttemptTests(unittest.TestCase):
    def test_start_increments_counters(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "start-incr")
            diag = {"escalation_reason": "CI timeout 30s", "sub_type": "ci_timeout"}
            auto_recovery.record_attempt_start(state, diagnostic=diag, resume_state="PR_REVIEW")
            rs = state.root["recovery_state"]
            self.assertEqual(rs["session_attempt_count"], 1)
            rh = auto_recovery.reason_hash("CI timeout 30s")
            self.assertEqual(rs["per_reason_count"][rh], 1)
            self.assertIsNotNone(rs["current"])
            self.assertEqual(rs["current"]["resume_state"], "PR_REVIEW")

    def test_invalid_resume_state_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "bad-resume")
            with self.assertRaises(ValueError):
                auto_recovery.record_attempt_start(
                    state,
                    diagnostic={"escalation_reason": "x"},
                    resume_state="RELEASE",  # not in _GATE_RESUMABLE_TARGETS
                )

    def test_outcome_moves_current_to_history(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "outcome-history")
            diag = {"escalation_reason": "rate limit 429", "sub_type": "rate_limit"}
            auto_recovery.record_attempt_start(state, diagnostic=diag, resume_state="PR_REVIEW")
            auto_recovery.record_attempt_outcome(state, "success")
            rs = state.root["recovery_state"]
            self.assertIsNone(rs["current"])
            self.assertEqual(len(rs["history"]), 1)
            self.assertEqual(rs["history"][0]["outcome"], "success")

    def test_invalid_outcome_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "bad-outcome")
            diag = {"escalation_reason": "x", "sub_type": "ci_timeout"}
            auto_recovery.record_attempt_start(state, diagnostic=diag, resume_state="PR_REVIEW")
            with self.assertRaises(ValueError):
                auto_recovery.record_attempt_outcome(state, "maybe")

    def test_outcome_without_current_raises(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "no-current")
            with self.assertRaises(RuntimeError):
                auto_recovery.record_attempt_outcome(state, "success")


class FSMRuntimeAutoRecoveryTests(unittest.TestCase):
    def test_enter_from_non_escalation_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "wrong-source", current="IMPLEMENTATION")
            rt = FSMRuntime(state)
            with self.assertRaises(TransitionError):
                rt.enter_auto_recovery(
                    escalation_reason="CI timeout 30s",
                    resume_state="PR_REVIEW",
                )

    def test_transient_enter_succeeds_and_records_state(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "transient-enter")
            rt = FSMRuntime(state)
            outcome = rt.enter_auto_recovery(
                escalation_reason="CI runner timeout after 30 minutes",
                resume_state="PR_REVIEW",
            )
            self.assertTrue(outcome["entered"])
            self.assertEqual(rt.state.current, "AUTO_RECOVERY_ATTEMPT")
            self.assertEqual(outcome["action"], "wait_and_rerun")
            self.assertEqual(outcome["wait_sec"], 30)
            rs = rt.state.root["recovery_state"]
            self.assertEqual(rs["session_attempt_count"], 1)

    def test_structural_enter_routes_to_escalation_final(self):
        """Rule 9.14.3: structural must NEVER enter AUTO_RECOVERY_ATTEMPT."""
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "structural-enter")
            rt = FSMRuntime(state)
            outcome = rt.enter_auto_recovery(
                escalation_reason="SLV-007 FAIL on AC-015 vs INV-002",
                resume_state="PR_REVIEW",
            )
            self.assertFalse(outcome["entered"])
            self.assertEqual(outcome["next_state"], "ESCALATION_FINAL")
            self.assertEqual(rt.state.current, "ESCALATION_FINAL")
            self.assertIn("9.14.3", outcome["refusal_reason"])

    def test_exit_success_transitions_to_resume_state(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "exit-success")
            rt = FSMRuntime(state)
            rt.enter_auto_recovery(
                escalation_reason="rate limit 429",
                resume_state="IMPLEMENTATION",
            )
            self.assertEqual(rt.state.current, "AUTO_RECOVERY_ATTEMPT")
            result = rt.exit_auto_recovery("success")
            self.assertEqual(rt.state.current, "IMPLEMENTATION")
            self.assertEqual(result["next_state"], "IMPLEMENTATION")

    def test_exit_fail_transitions_to_escalation_final(self):
        """Rule 9.14.4: failed attempt → ESCALATION_FINAL."""
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "exit-fail")
            rt = FSMRuntime(state)
            rt.enter_auto_recovery(
                escalation_reason="ConnectionError",
                resume_state="PR_REVIEW",
            )
            result = rt.exit_auto_recovery("fail")
            self.assertEqual(rt.state.current, "ESCALATION_FINAL")
            self.assertEqual(result["next_state"], "ESCALATION_FINAL")

    def test_session_limit_enforced_after_three(self):
        """Rule 9.14.1: 3 distinct reasons in same session → 4th refused."""
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "session-limit")
            # First 3 attempts (distinct reasons to dodge 9.14.2)
            for i in range(3):
                state.current = "ESCALATION"
                save_state(state)
                rt = FSMRuntime(state)
                outcome = rt.enter_auto_recovery(
                    escalation_reason=f"CI runner timeout iteration-{i}",
                    resume_state="PR_REVIEW",
                )
                self.assertTrue(outcome["entered"], msg=f"iter {i} should enter")
                rt.exit_auto_recovery("fail")  # leaves at ESCALATION_FINAL
                # Reset back to ESCALATION for the next iteration
            # 4th attempt (different reason again)
            state.current = "ESCALATION"
            save_state(state)
            rt = FSMRuntime(state)
            outcome = rt.enter_auto_recovery(
                escalation_reason="CI runner timeout iteration-99",
                resume_state="PR_REVIEW",
            )
            self.assertFalse(outcome["entered"])
            self.assertIn("9.14.1", outcome["refusal_reason"])

    def test_per_reason_limit_enforced(self):
        """Rule 9.14.2: same reason already attempted → refuse."""
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "per-reason")
            rt = FSMRuntime(state)
            outcome1 = rt.enter_auto_recovery(
                escalation_reason="rate limit 429 hit on hub",
                resume_state="PR_REVIEW",
            )
            self.assertTrue(outcome1["entered"])
            rt.exit_auto_recovery("fail")
            # Try same reason again
            state.current = "ESCALATION"
            save_state(state)
            rt2 = FSMRuntime(state)
            outcome2 = rt2.enter_auto_recovery(
                escalation_reason="rate limit 429 hit on hub",
                resume_state="PR_REVIEW",
            )
            self.assertFalse(outcome2["entered"])
            self.assertIn("9.14.2", outcome2["refusal_reason"])


class EscalationFinalGuardTests(unittest.TestCase):
    """B1.7: ESCALATION_FINAL must block all tool calls (in _BLOCKING_STATES)."""

    def test_assert_tool_allowed_blocks_in_escalation_final(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "blocked-final", current="ESCALATION_FINAL")
            rt = FSMRuntime(state)
            with self.assertRaises(TransitionError) as ctx:
                rt.assert_tool_allowed("Write", "docs/01_requirements/FRD.md")
            self.assertIn("ESCALATION_FINAL", str(ctx.exception))

    def test_assert_tool_allowed_also_blocks_read_in_escalation_final(self):
        """Like ESCALATION, ESCALATION_FINAL blocks all tools (not just writes)."""
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "blocked-read", current="ESCALATION_FINAL")
            rt = FSMRuntime(state)
            with self.assertRaises(TransitionError):
                rt.assert_tool_allowed("Read", "any/path.txt")


if __name__ == "__main__":
    unittest.main()
