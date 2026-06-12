# enforces (governance rules): R-9.1
"""Unit tests for FSM transitions (Phase D ACT-010 M1)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import transition_rules as tr  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state  # noqa: E402


class HappyPathTests(unittest.TestCase):
    def test_linear_path(self) -> None:
        path = [
            "INIT", "SCENARIO_DETECT", "AGENT_LOAD", "SPEC_DRAFTING",
            "SCG_VALIDATION", "HUMAN_PENDING", "SPEC_REGRESSION_CHECK",
            "SPEC_FROZEN", "IMPLEMENTATION", "PR_REVIEW", "RTM_VERIFY",
            "RELEASE_READY", "RELEASE",
        ]
        for src, dst in zip(path, path[1:]):
            self.assertTrue(tr.is_transition_allowed(src, dst), f"{src} → {dst} should be allowed")


class ErrorPathTests(unittest.TestCase):
    def test_scg_fail_under_limit_goes_back_to_drafting(self) -> None:
        nxt, esc = tr.next_state_on_gate_fail("SCG_VALIDATION", current_count=2)
        self.assertEqual(nxt, "SPEC_DRAFTING")
        self.assertFalse(esc)

    def test_scg_fail_at_limit_escalates(self) -> None:
        nxt, esc = tr.next_state_on_gate_fail("SCG_VALIDATION", current_count=3)
        self.assertEqual(nxt, "ESCALATION")
        self.assertTrue(esc)

    def test_pr_review_same_pattern_goes_to_audit(self) -> None:
        nxt, esc = tr.next_state_on_gate_fail("PR_REVIEW", current_count=2, same_pattern_count=3)
        self.assertEqual(nxt, "SPEC_AUDIT")
        self.assertFalse(esc)

    def test_emergency_targets_always_allowed(self) -> None:
        for emergency in ("ESCALATION", "TOKEN_BUDGET_CRITICAL", "TERMINATED"):
            self.assertTrue(tr.is_transition_allowed("IMPLEMENTATION", emergency))

    def test_gate_fail_blocked_transition_appends_trace(self) -> None:
        """M2 QA Round-2 P1-2 — when gate_fail's target is rejected by
        happy-path rules, record_gate_result must still leave an audit trail
        so retry_count and decision_trace stay consistent."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            state = load_state("gate-blocked-proj", path=Path(tmp) / "FSM-STATE.yaml")
            rt = FSMRuntime(state)
            # Arrange: place FSM in AGENT_LOAD so the gate_fail target
            # (IMPLEMENTATION for RTM_VERIFY fail) is not a legal transition
            # from AGENT_LOAD → TransitionError path.
            rt.state.current = "AGENT_LOAD"
            payload = rt.record_gate_result("RTM_VERIFY", "FAIL", reason="blocked-xition")
            # retry_count must still have incremented.
            self.assertEqual(payload["retry_count"], 1)
            # State must remain AGENT_LOAD (transition rejected).
            self.assertEqual(rt.state.current, "AGENT_LOAD")
            trace = rt.state.decision_trace()
            self.assertTrue(trace, "decision_trace should not be empty")
            last = trace[-1]
            self.assertEqual(last["trigger"], "gate_fail_blocked")
            self.assertIn("gate_fail transition rejected", last["reason"])


class RuntimeBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["SDD_PROJECT"] = f"test-{os.getpid()}"
        self.state_path = Path(self._tmp.name) / "FSM-STATE-test.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_bootstrap_creates_state_file(self) -> None:
        state = load_state("unit-test-proj", path=self.state_path)
        self.assertTrue(self.state_path.exists())
        self.assertEqual(state.current, "INIT")

    def test_record_gate_fail_increments_retry(self) -> None:
        state = load_state("unit-test-proj", path=self.state_path)
        rt = FSMRuntime(state)
        rt.state.current = "SCG_VALIDATION"
        payload = rt.record_gate_result("SCG_VALIDATION", "FAIL", reason="test")
        self.assertEqual(payload["retry_count"], 1)
        self.assertFalse(payload.get("escalated", False))

    def test_scg_fail_three_times_escalates(self) -> None:
        state = load_state("unit-test-proj", path=self.state_path)
        rt = FSMRuntime(state)
        rt.state.current = "SCG_VALIDATION"
        for _ in range(3):
            rt.record_gate_result("SCG_VALIDATION", "FAIL", reason="test")
            rt.state.current = "SCG_VALIDATION"
        rt.record_gate_result("SCG_VALIDATION", "FAIL", reason="test")
        self.assertEqual(rt.state.current, "ESCALATION")


class TamperedRetryCountTests(unittest.TestCase):
    """ACT-029 P1-01 — tamper defence for `increment_retry`.

    Attackers (or corrupted YAML) may poison `current_count` to earn free
    retries (negative) or skip retries entirely (above limit). Both cases
    must result in immediate escalation at the next FAIL, not silent retries.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-tamper.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_tampered_negative_retry_count_still_escalates_at_limit(self) -> None:
        """Prior count -5 must not buy free retries — SCG limit is 3, so
        after 3 FAILs the FSM MUST be in ESCALATION (not still drafting)."""
        state = load_state("tamper-neg", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "SCG_VALIDATION"
        # Poison the retry counter as an attacker would.
        rt.state.retry("SCG_VALIDATION")["current_count"] = -5
        # First FAIL → tamper detected → sanitized & snapped to limit.
        rt.record_gate_result("SCG_VALIDATION", "FAIL", reason="poisoned")
        self.assertEqual(
            rt.state.current, "ESCALATION",
            "tampered negative prior_count must escalate immediately, not earn retries"
        )
        # Audit trail must record tamper detection.
        history = rt.state.retry("SCG_VALIDATION").get("history", [])
        self.assertTrue(history, "history must record the tamper attempt")
        self.assertIn("tamper detected", history[-1]["failure_reason"])

    def test_tampered_oversized_retry_count_normalises(self) -> None:
        """Prior count 9999 is above any legal limit — next FAIL must
        escalate (snap to limit) rather than increment to 10000."""
        state = load_state("tamper-big", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "SCG_VALIDATION"
        rt.state.retry("SCG_VALIDATION")["current_count"] = 9999
        rt.record_gate_result("SCG_VALIDATION", "FAIL", reason="poisoned-big")
        self.assertEqual(rt.state.current, "ESCALATION")
        # Sanity: sanitized count must equal the gate's legal limit, not 10000.
        final_count = rt.state.retry("SCG_VALIDATION").get("current_count")
        self.assertEqual(final_count, tr.RETRY_LIMITS["SCG_VALIDATION"])

    def test_normal_retry_path_unaffected_by_defence(self) -> None:
        """Regression — defence must not break normal retries."""
        state = load_state("tamper-normal", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "SCG_VALIDATION"
        # Legal retry (count 0) — should increment to 1, not escalate.
        payload = rt.record_gate_result("SCG_VALIDATION", "FAIL", reason="normal")
        self.assertEqual(payload["retry_count"], 1)
        self.assertNotEqual(rt.state.current, "ESCALATION")


class ImplementationBudgetTests(unittest.TestCase):
    """QA Round-3 P1-01 — ensure test_fail_threshold actually triggers SPEC_AUDIT.

    Prior to the fix, should_escalate_for_implementation returned
    (False, "test_fail_threshold → SPEC_AUDIT") but check_implementation_budget
    only acted on escalate=True, leaving the SPEC_AUDIT sentinel as a no-op.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-impl-budget.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_test_fail_threshold_triggers_spec_audit(self) -> None:
        state = load_state("impl-budget", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "IMPLEMENTATION"
        budget = rt.state.implementation_budget()
        budget["test_fail_without_spec_change"] = tr.IMPL_MAX_TEST_FAIL_WITHOUT_SPEC_CHANGE
        payload = rt.check_implementation_budget()
        self.assertIn("SPEC_AUDIT", payload.get("reason", ""))
        self.assertEqual(rt.state.current, "SPEC_AUDIT",
                         "FSM must actually transition to SPEC_AUDIT, not just return the hint")
        self.assertIn("spec_audit", payload)
        pr_entry = rt.state.retry("PR_REVIEW")
        self.assertGreaterEqual(pr_entry.get("spec_audit_count", 0), 1)

    def test_budget_under_threshold_stays_in_implementation(self) -> None:
        state = load_state("impl-budget", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "IMPLEMENTATION"
        budget = rt.state.implementation_budget()
        budget["test_fail_without_spec_change"] = tr.IMPL_MAX_TEST_FAIL_WITHOUT_SPEC_CHANGE - 1
        payload = rt.check_implementation_budget()
        self.assertFalse(payload["escalated"])
        self.assertEqual(rt.state.current, "IMPLEMENTATION")
        self.assertNotIn("spec_audit", payload)

    def test_spec_audit_exhaustion_escalates(self) -> None:
        state = load_state("impl-budget", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "IMPLEMENTATION"
        # Simulate audit already run SPEC_AUDIT_MAX_PER_STAGE times — next call
        # must escalate rather than silently no-op.
        pr_entry = rt.state.retry("PR_REVIEW")
        pr_entry["spec_audit_count"] = tr.SPEC_AUDIT_MAX_PER_STAGE
        budget = rt.state.implementation_budget()
        budget["test_fail_without_spec_change"] = tr.IMPL_MAX_TEST_FAIL_WITHOUT_SPEC_CHANGE
        payload = rt.check_implementation_budget()
        self.assertTrue(payload["escalated"])
        self.assertEqual(rt.state.current, "ESCALATION")


class AutoCompactEntryGuardTests(unittest.TestCase):
    """QA Round-3 P2-06 — only legitimate sources may enter AUTO_COMPACT_PENDING.

    Previously `_EMERGENCY_TARGETS` included AUTO_COMPACT_PENDING, which made
    ``RELEASE → AUTO_COMPACT_PENDING`` / ``TERMINATED → AUTO_COMPACT_PENDING``
    legal at the transition-rule level. Terminal / critical / release states
    must refuse auto-compact entry.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-acp.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_auto_compact_pending_rejected_from_release(self) -> None:
        self.assertFalse(tr.is_transition_allowed("RELEASE", "AUTO_COMPACT_PENDING"))
        self.assertFalse(tr.is_transition_allowed("TERMINATED", "AUTO_COMPACT_PENDING"))
        self.assertFalse(tr.is_transition_allowed("ESCALATION", "AUTO_COMPACT_PENDING"))
        self.assertFalse(tr.is_transition_allowed("TOKEN_BUDGET_CRITICAL", "AUTO_COMPACT_PENDING"))

    def test_auto_compact_pending_allowed_from_normal_sources(self) -> None:
        for src in ("SPEC_DRAFTING", "IMPLEMENTATION", "PR_REVIEW", "SCG_VALIDATION"):
            self.assertTrue(
                tr.is_transition_allowed(src, "AUTO_COMPACT_PENDING"),
                f"{src} → AUTO_COMPACT_PENDING must be allowed",
            )

    def test_runtime_trigger_auto_compact_noop_from_release(self) -> None:
        state = load_state("acp-proj", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "RELEASE"
        result = rt.trigger_auto_compact(cumulative_tokens=200_000, ratio=0.9)
        self.assertTrue(result.get("noop"))
        self.assertEqual(rt.state.current, "RELEASE")

    def test_runtime_trigger_auto_compact_noop_from_token_critical(self) -> None:
        state = load_state("acp-proj", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "TOKEN_BUDGET_CRITICAL"
        result = rt.trigger_auto_compact(cumulative_tokens=200_000, ratio=0.96)
        self.assertTrue(result.get("escalated"))
        self.assertEqual(rt.state.current, "TOKEN_BUDGET_CRITICAL")


class GuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-guard.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_spec_write_blocked_in_implementation(self) -> None:
        state = load_state("guard-proj", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "IMPLEMENTATION"
        with self.assertRaises(tr.TransitionError):
            rt.assert_tool_allowed("Write", "docs/01_requirements/FRD-X.md")

    def test_spec_write_allowed_in_drafting(self) -> None:
        state = load_state("guard-proj", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "SPEC_DRAFTING"
        rt.assert_tool_allowed("Write", "docs/01_requirements/FRD-X.md")

    def test_all_tools_blocked_in_escalation(self) -> None:
        state = load_state("guard-proj", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "ESCALATION"
        with self.assertRaises(tr.TransitionError):
            rt.assert_tool_allowed("Bash", None)


class Act014019Tests(unittest.TestCase):
    def test_human_pending_to_spec_regression_check_then_frozen(self) -> None:
        self.assertTrue(tr.is_transition_allowed("HUMAN_PENDING", "SPEC_REGRESSION_CHECK"))
        self.assertTrue(tr.is_transition_allowed("SPEC_REGRESSION_CHECK", "SPEC_FROZEN"))
        self.assertEqual(tr.next_state_on_gate_pass("SPEC_REGRESSION_CHECK"), "SPEC_FROZEN")

    def test_spec_regression_check_fail_returns_to_human_pending(self) -> None:
        nxt, esc = tr.next_state_on_gate_fail("SPEC_REGRESSION_CHECK", current_count=1)
        self.assertEqual(nxt, "HUMAN_PENDING")
        self.assertFalse(esc)

    def test_spec_regression_check_fail_at_limit_escalates(self) -> None:
        nxt, esc = tr.next_state_on_gate_fail("SPEC_REGRESSION_CHECK", current_count=2)
        self.assertEqual(nxt, "ESCALATION")
        self.assertTrue(esc)

    def test_escalation_can_only_reach_resume_or_terminated(self) -> None:
        self.assertFalse(tr.is_transition_allowed("ESCALATION", "SPEC_DRAFTING"))
        self.assertFalse(tr.is_transition_allowed("ESCALATION", "IMPLEMENTATION"))
        self.assertTrue(tr.is_transition_allowed("ESCALATION", "RESUME_VERIFICATION"))
        self.assertTrue(tr.is_transition_allowed("ESCALATION", "TERMINATED"))

    def test_resume_verification_targets(self) -> None:
        self.assertTrue(tr.is_transition_allowed("RESUME_VERIFICATION", "SPEC_DRAFTING"))
        self.assertTrue(tr.is_transition_allowed("RESUME_VERIFICATION", "IMPLEMENTATION"))
        self.assertTrue(tr.is_transition_allowed("RESUME_VERIFICATION", "PR_REVIEW"))
        self.assertTrue(tr.is_transition_allowed("RESUME_VERIFICATION", "ESCALATION"))


if __name__ == "__main__":
    unittest.main()
