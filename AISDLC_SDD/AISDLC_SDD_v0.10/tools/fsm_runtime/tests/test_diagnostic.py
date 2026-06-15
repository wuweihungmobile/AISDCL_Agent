"""Phase G M1 / ACT-032: DiagnosticAgent classification tests.

30 fixture samples covering all 6 sub_types + unknown + structural priority +
boundary cases. Acceptance per planning doc B1.8: precision ≥ 0.93 (≥28/30).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.diagnostic import (  # noqa: E402
    diagnose,
    is_auto_recoverable,
    DiagnosticResult,
    SUB_TYPES,
)


# (escalation_reason, expected_category, expected_sub_type, expected_auto_recover)
FIXTURES = [
    # ----- ci_timeout × 5 -----
    ("CI runner timeout after 30 minutes", "transient", "ci_timeout", True),
    ("actions/runner-images returned 502 Bad Gateway", "transient", "ci_timeout", True),
    ("CI job timed out waiting for resource", "transient", "ci_timeout", True),
    ("workflow cancelled by GitHub Actions", "transient", "ci_timeout", True),
    ("runner offline; rerun pending", "transient", "ci_timeout", True),
    # ----- network_flap × 5 -----
    ("ConnectionError when calling external API", "transient", "network_flap", True),
    ("NetworkTimeout during git clone", "transient", "network_flap", True),
    ("EAI_AGAIN: DNS lookup failed", "transient", "network_flap", True),
    ("socket timeout on hub.example.com:443", "transient", "network_flap", True),
    ("ETIMEDOUT trying to reach upstream", "transient", "network_flap", True),
    # ----- rate_limit × 5 -----
    ("GitHub API returned 429 too many requests", "transient", "rate_limit", True),
    ("Rate limit exceeded; Retry-After: 60", "transient", "rate_limit", True),
    ("Hugging Face API: too many requests, please wait", "transient", "rate_limit", True),
    ("OpenAI API throttled to 3 req/min", "transient", "rate_limit", True),
    ("AWS quota exceeded for region us-east-1", "transient", "rate_limit", True),
    # ----- spec_conflict × 4 -----
    ("SLV-007 FAIL: AC-015 conflict with INV-002", "structural", "spec_conflict", False),
    ("SPEC_AUDIT cannot find resolution for the contradiction", "structural", "spec_conflict", False),
    ("INV-003 contradict AC-021 on idempotency requirement", "structural", "spec_conflict", False),
    ("SLV-005 FAIL on FRD section 3.2", "structural", "spec_conflict", False),
    # ----- data_corruption × 4 -----
    ("yaml_error in primary, fallback to .bak succeeded", "structural", "data_corruption", False),
    ("schema violation on FSM-STATE root key", "structural", "data_corruption", False),
    ("non_dict YAML doc; primary=read_error, bak=absent", "structural", "data_corruption", False),
    ("missing_root in CONTEXT-LEDGER YAML", "structural", "data_corruption", False),
    # ----- retry_exhausted × 4 -----
    ("PR_REVIEW retry_count >= 5 (limit reached)", "structural", "retry_exhausted", False),
    ("max_iterations exceeded for IMPLEMENTATION sub-FSM", "structural", "retry_exhausted", False),
    ("consecutive_compile_fail = 3, escalate per IMPL_MAX", "structural", "retry_exhausted", False),
    ("budget exceeded after 5 dispatch attempts", "structural", "retry_exhausted", False),
    # ----- unknown / edge × 3 -----
    ("", "structural", "unknown", False),
    ("kernel panic: PFN_LIST_CORRUPT", "structural", "unknown", False),
    ("Some entirely novel failure mode that has never been seen", "structural", "unknown", False),
]


class DiagnosticTests(unittest.TestCase):
    def test_fixture_precision_at_least_93pct(self) -> None:
        """B1.8 acceptance: ≥ 28/30 fixture samples classified correctly."""
        wrong: list[str] = []
        for reason, exp_cat, exp_sub, exp_recover in FIXTURES:
            result = diagnose(reason)
            ok = (
                result.category == exp_cat
                and result.sub_type == exp_sub
                and result.auto_recoverable == exp_recover
            )
            if not ok:
                wrong.append(
                    f"{reason!r} -> {result.category}/{result.sub_type} "
                    f"(expected {exp_cat}/{exp_sub})"
                )
        precision = (len(FIXTURES) - len(wrong)) / len(FIXTURES)
        self.assertGreaterEqual(
            precision,
            0.93,
            f"precision={precision:.2%} < 93%; misses={len(wrong)}:\n  "
            + "\n  ".join(wrong),
        )

    def test_structural_priority_on_overlap(self) -> None:
        """When both structural + transient match, structural must win."""
        result = diagnose("SLV-005 FAIL due to ConnectionError in test runner")
        self.assertEqual(result.category, "structural")
        self.assertEqual(result.sub_type, "spec_conflict")
        self.assertFalse(result.auto_recoverable)
        # Multi-match penalty applied: confidence reduced from 0.85 to 0.70
        self.assertAlmostEqual(result.confidence, 0.70, places=2)

    def test_unknown_default_is_conservative(self) -> None:
        """No-match → structural/unknown/0.5 (safety default)."""
        result = diagnose("alien failure no rule covers this")
        self.assertEqual(result.category, "structural")
        self.assertEqual(result.sub_type, "unknown")
        self.assertFalse(result.auto_recoverable)
        self.assertEqual(result.confidence, 0.5)

    def test_transient_carries_recovery_action(self) -> None:
        """All transient diagnoses must populate recovery_action + wait_sec."""
        for reason, cat, _, _ in FIXTURES:
            if cat != "transient":
                continue
            result = diagnose(reason)
            self.assertIsNotNone(result.recovery_action, msg=f"reason={reason}")
            self.assertIsNotNone(result.recovery_max_wait_sec, msg=f"reason={reason}")
            self.assertGreater(result.recovery_max_wait_sec, 0)

    def test_structural_never_carries_recovery_action(self) -> None:
        """All structural diagnoses must have recovery_action=None."""
        for reason, cat, _, _ in FIXTURES:
            if cat != "structural":
                continue
            result = diagnose(reason)
            self.assertIsNone(result.recovery_action, msg=f"reason={reason}")
            self.assertIsNone(result.recovery_max_wait_sec, msg=f"reason={reason}")

    def test_is_auto_recoverable_threshold(self) -> None:
        """Convenience wrapper requires confidence ≥ 0.7 in addition to flag."""
        # high-confidence transient → True
        self.assertTrue(is_auto_recoverable("CI runner timeout after 30 minutes"))
        # structural → False
        self.assertFalse(is_auto_recoverable("SLV-007 FAIL"))
        # unknown (0.5) → False (below threshold)
        self.assertFalse(is_auto_recoverable("totally novel weird thing"))

    def test_to_dict_round_trip(self) -> None:
        """DiagnosticResult.to_dict() must serialize all fields."""
        result = diagnose("CI runner timeout 30s")
        d = result.to_dict()
        for key in (
            "category", "sub_type", "auto_recoverable", "confidence",
            "recovery_action", "recovery_max_wait_sec",
            "rationale", "spec_refs", "escalation_reason",
        ):
            self.assertIn(key, d)

    def test_spec_refs_passthrough(self) -> None:
        """spec_refs argument must be preserved verbatim."""
        refs = ["AC-015", "INV-002", "SLV-007"]
        result = diagnose("SLV-007 FAIL", spec_refs=refs)
        self.assertEqual(result.spec_refs, refs)

    def test_sub_types_constant_complete(self) -> None:
        """SUB_TYPES tuple 必須涵蓋所有分類 sub_type + 'unknown'。

        每個 _RULES 內的 sub_type 都必須在 SUB_TYPES 宣告（含 Phase I
        sandbox_policy_violation 與 Phase J adversarial_*）。"""
        expected = {
            "ci_timeout", "network_flap", "rate_limit",
            "spec_conflict", "data_corruption", "retry_exhausted",
            "sandbox_policy_violation",       # Phase I / ACT-061
            "adversarial_counterexample",     # Phase J / ACT-074
            "adversarial_spec_gap",           # Phase J / ACT-074
            "unknown",
        }
        self.assertSetEqual(set(SUB_TYPES), expected)
        # 防回歸：_RULES 內每個 sub_type 都必須在 SUB_TYPES
        from tools.fsm_runtime.diagnostic import _RULES
        rule_sub_types = {st for st, _cat, _pats in _RULES}
        self.assertTrue(rule_sub_types.issubset(set(SUB_TYPES)))


if __name__ == "__main__":
    unittest.main()
