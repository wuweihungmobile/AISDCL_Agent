# enforces (governance rules): R-9.15
"""Phase G M2 / ACT-035/036: TrajectoryPredictor + FSMRuntime predictive halt tests.

Acceptance per planning §M2:
  - 4 信號 (S1~S4) 獨立可被觸發
  - 0~1 信號 → continue ; ≥2 → switch_to_audit ; ≥3 + conf≥0.8 → abort_early
  - Rule 9.15.1 retry_count == 0 → predictor disabled
  - Rule 9.15.2 abort_early 須 confidence ≥ 0.8（caller validates；exit hook enforces）
  - Rule 9.15.3 false-positive 寫 PREDICTOR-MISS YAML
  - Rule 9.15.4 同 stage switch_to_audit ≤ 1 次
  - 30 mixed fixtures: false-positive rate < 15% (≥ 26/30 correct)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import trajectory_predictor as tp  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state, save_state  # noqa: E402
from tools.fsm_runtime.transition_rules import (  # noqa: E402
    TransitionError, OBSERVATION_STATES, _HAPPY_PATH,
)


def _make_state(td: Path, name: str, current: str = "PR_REVIEW"):
    path = td / f"FSM-STATE-{name}.yaml"
    state = load_state(name, path=path, create_if_missing=True)
    state.root["current_state"] = current
    save_state(state)
    return state


def _seed_retry(state, gate: str, *, count: int, same_pattern: int = 0):
    entry = state.retry(gate)
    entry["current_count"] = count
    entry["same_pattern_count"] = same_pattern
    save_state(state)


def _seed_decision_trace(state, *, reasons):
    for r in reasons:
        state.append_decision_trace(
            from_state="PR_REVIEW",
            to_state="PR_REVIEW",
            reason=r,
            trigger="test_seed",
        )
    save_state(state)


def _write_ledger(td: Path, *, drift_pct: float) -> Path:
    p = td / "conv-ledger.yaml"
    p.write_text(
        yaml.safe_dump({"rolling_avg_drift_pct_last10": drift_pct}, sort_keys=False),
        encoding="utf-8",
    )
    return p


# ----------------------------------------------------------------------
# Signal-level tests
# ----------------------------------------------------------------------

class SignalEvaluatorTests(unittest.TestCase):
    def test_s1_same_pattern_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "s1")
            _seed_retry(state, "PR_REVIEW", count=2, same_pattern=2)
            self.assertTrue(tp._signal_s1_same_pattern(state, "PR_REVIEW"))
            _seed_retry(state, "PR_REVIEW", count=2, same_pattern=1)
            self.assertFalse(tp._signal_s1_same_pattern(state, "PR_REVIEW"))

    def test_s2_retry_near_limit_requires_pattern(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "s2")
            # PR_REVIEW limit=5, 60% threshold = 3/5
            _seed_retry(state, "PR_REVIEW", count=3, same_pattern=2)
            self.assertTrue(tp._signal_s2_retry_near_limit(state, "PR_REVIEW"))
            # high count but unstable pattern → S2 false (avoid noise FP)
            _seed_retry(state, "PR_REVIEW", count=3, same_pattern=0)
            self.assertFalse(tp._signal_s2_retry_near_limit(state, "PR_REVIEW"))

    def test_s3_spec_in_trace(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "s3")
            _seed_decision_trace(state, reasons=[
                "SLV-005 FAIL", "AC-015 conflict with INV-002", "ok", "ok", "ok",
            ])
            self.assertTrue(tp._signal_s3_spec_in_trace(state))
            # only 1 spec hit in last 5 → False
            state2 = _make_state(Path(td), "s3b")
            _seed_decision_trace(state2, reasons=["SLV-001", "ok", "ok", "ok", "ok"])
            self.assertFalse(tp._signal_s3_spec_in_trace(state2))

    def test_s4_drift_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            ok = _write_ledger(Path(td), drift_pct=10.0)
            self.assertFalse(tp._signal_s4_drift_anomaly(ok))
            high = _write_ledger(Path(td), drift_pct=45.0)
            self.assertTrue(tp._signal_s4_drift_anomaly(high))
            # missing path → False (defensive)
            self.assertFalse(tp._signal_s4_drift_anomaly(Path(td) / "missing.yaml"))


# ----------------------------------------------------------------------
# Decision matrix
# ----------------------------------------------------------------------

class PredictDecisionTests(unittest.TestCase):
    def test_rule_9151_retry_zero_disabled(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "r9151")
            _seed_retry(state, "PR_REVIEW", count=0, same_pattern=0)
            action = tp.predict(state, gate="PR_REVIEW")
            self.assertEqual(action.decision, "continue")
            self.assertEqual(action.confidence, 0.0)
            self.assertIn("9.15.1", action.rationale)

    def test_zero_signals_continue(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "zero")
            _seed_retry(state, "PR_REVIEW", count=1, same_pattern=0)
            action = tp.predict(state, gate="PR_REVIEW")
            self.assertEqual(action.decision, "continue")
            self.assertEqual(action.signals_triggered, [])

    def test_one_signal_continue(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "one")
            _seed_retry(state, "PR_REVIEW", count=2, same_pattern=2)  # S1
            action = tp.predict(state, gate="PR_REVIEW")
            self.assertEqual(action.decision, "continue")
            self.assertEqual(action.signals_triggered, ["S1"])
            self.assertEqual(action.confidence, 0.25)

    def test_two_signals_switch_to_audit(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "two")
            _seed_retry(state, "PR_REVIEW", count=3, same_pattern=2)  # S1+S2
            action = tp.predict(state, gate="PR_REVIEW")
            self.assertEqual(action.decision, "switch_to_audit")
            self.assertEqual(set(action.signals_triggered), {"S1", "S2"})
            self.assertEqual(action.next_state_hint, "SPEC_AUDIT")

    def test_three_signals_abort_early_meets_confidence(self):
        with tempfile.TemporaryDirectory() as td:
            state = _make_state(Path(td), "three")
            ledger = _write_ledger(Path(td), drift_pct=50.0)
            _seed_retry(state, "PR_REVIEW", count=3, same_pattern=2)  # S1+S2
            _seed_decision_trace(state, reasons=[
                "SLV-005 FAIL", "AC vs INV conflict", "ok", "ok", "ok",
            ])
            action = tp.predict(state, gate="PR_REVIEW", ledger_path=ledger)
            self.assertEqual(set(action.signals_triggered), {"S1", "S2", "S3", "S4"})
            self.assertEqual(action.decision, "abort_early")
            self.assertEqual(action.next_state_hint, "ESCALATION")
            self.assertGreaterEqual(action.confidence, tp.ABORT_CONFIDENCE_FLOOR)


# ----------------------------------------------------------------------
# FSMRuntime integration
# ----------------------------------------------------------------------

class FSMRuntimePredictiveTests(unittest.TestCase):
    def _runtime(self, td: Path, current: str = "PR_REVIEW") -> FSMRuntime:
        state = _make_state(td, "rt", current=current)
        rt = FSMRuntime(state=state)
        return rt

    def test_enter_blocked_from_non_predictor_gate(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._runtime(Path(td), current="SPEC_DRAFTING")
            with self.assertRaises(TransitionError):
                rt.enter_trajectory_predicted(
                    predicted_action={"decision": "switch_to_audit", "confidence": 0.5,
                                      "signals_triggered": ["S1", "S2"], "rationale": "x",
                                      "next_state_hint": "SPEC_AUDIT", "gate": "PR_REVIEW"},
                    gate="PR_REVIEW",
                )

    def test_exit_continue_resumes_gate(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._runtime(Path(td), current="PR_REVIEW")
            rt.enter_trajectory_predicted(
                predicted_action={"decision": "continue", "confidence": 0.0,
                                  "signals_triggered": [], "rationale": "x",
                                  "next_state_hint": None, "gate": "PR_REVIEW"},
                gate="PR_REVIEW",
            )
            self.assertEqual(rt.state.current, "TRAJECTORY_PREDICTED")
            rt.exit_trajectory_predicted("continue")
            self.assertEqual(rt.state.current, "PR_REVIEW")

    def test_exit_switch_to_audit_transitions(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._runtime(Path(td), current="PR_REVIEW")
            rt.enter_trajectory_predicted(
                predicted_action={"decision": "switch_to_audit", "confidence": 0.5,
                                  "signals_triggered": ["S1", "S2"], "rationale": "x",
                                  "next_state_hint": "SPEC_AUDIT", "gate": "PR_REVIEW"},
                gate="PR_REVIEW",
            )
            rt.exit_trajectory_predicted("switch_to_audit")
            self.assertEqual(rt.state.current, "SPEC_AUDIT")

    def test_rule_9152_abort_requires_confidence(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._runtime(Path(td), current="PR_REVIEW")
            rt.enter_trajectory_predicted(
                predicted_action={"decision": "abort_early", "confidence": 0.5,
                                  "signals_triggered": ["S1", "S2"], "rationale": "x",
                                  "next_state_hint": "ESCALATION", "gate": "PR_REVIEW"},
                gate="PR_REVIEW",
            )
            with self.assertRaises(TransitionError) as ctx:
                rt.exit_trajectory_predicted("abort_early")
            self.assertIn("9.15.2", str(ctx.exception))

    def test_rule_9154_switch_capped_per_stage(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._runtime(Path(td), current="PR_REVIEW")
            # first switch ok
            rt.enter_trajectory_predicted(
                predicted_action={"decision": "switch_to_audit", "confidence": 0.5,
                                  "signals_triggered": ["S1", "S2"], "rationale": "x",
                                  "next_state_hint": "SPEC_AUDIT", "gate": "PR_REVIEW"},
                gate="PR_REVIEW",
            )
            rt.exit_trajectory_predicted("switch_to_audit")
            # SPEC_AUDIT → PR_REVIEW (happy)
            rt.transition("PR_REVIEW", reason="audit done", trigger="test")
            # second switch in same stage → refuse
            rt.enter_trajectory_predicted(
                predicted_action={"decision": "switch_to_audit", "confidence": 0.5,
                                  "signals_triggered": ["S1", "S2"], "rationale": "x",
                                  "next_state_hint": "SPEC_AUDIT", "gate": "PR_REVIEW"},
                gate="PR_REVIEW",
            )
            with self.assertRaises(TransitionError) as ctx:
                rt.exit_trajectory_predicted("switch_to_audit")
            self.assertIn("9.15.4", str(ctx.exception))

    def test_consult_predictor_continue_noop(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._runtime(Path(td), current="PR_REVIEW")
            _seed_retry(rt.state, "PR_REVIEW", count=1, same_pattern=0)
            r = rt.consult_predictor(gate="PR_REVIEW")
            self.assertEqual(r["decision"], "continue")
            self.assertFalse(r["executed"])
            self.assertEqual(rt.state.current, "PR_REVIEW")

    def test_consult_predictor_switch_executes(self):
        with tempfile.TemporaryDirectory() as td:
            rt = self._runtime(Path(td), current="PR_REVIEW")
            _seed_retry(rt.state, "PR_REVIEW", count=3, same_pattern=2)  # S1+S2
            r = rt.consult_predictor(gate="PR_REVIEW")
            self.assertEqual(r["decision"], "switch_to_audit")
            self.assertTrue(r["executed"])
            self.assertEqual(rt.state.current, "SPEC_AUDIT")


# ----------------------------------------------------------------------
# False-positive log
# ----------------------------------------------------------------------

class PredictorMissLogTests(unittest.TestCase):
    def test_record_miss_writes_yaml(self):
        with tempfile.TemporaryDirectory() as td:
            action = tp.PredictedAction(
                decision="switch_to_audit", confidence=0.5,
                signals_triggered=["S1", "S2"], rationale="x",
                next_state_hint="SPEC_AUDIT", gate="PR_REVIEW",
            )
            path = tp.record_miss(
                action=action,
                actual_outcome="would_have_succeeded",
                miss_dir=Path(td),
                state_name="TRAJECTORY_PREDICTED",
            )
            self.assertTrue(path.exists())
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(len(doc), 1)
            self.assertEqual(doc[0]["actual_outcome"], "would_have_succeeded")
            # second call appends
            tp.record_miss(action=action, actual_outcome="x", miss_dir=Path(td))
            doc2 = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(len(doc2), 2)


# ----------------------------------------------------------------------
# Mixed fixtures — false-positive < 15%
# ----------------------------------------------------------------------

# 30 fixtures: (signals_setup, expected_decision)
# signals_setup is a tuple (current_count, same_pattern, spec_traces, drift_pct)
# spec_traces: list of decision trace reasons
FIXTURES = [
    # ---- 10 真正該 switch (≥2 信號) ----
    ((3, 2, [], 10.0), "switch_to_audit"),  # S1+S2
    ((4, 2, [], 10.0), "switch_to_audit"),  # S1+S2
    ((2, 2, ["SLV-001 FAIL", "AC-002 conflict INV-003", "x", "x", "x"], 10.0), "switch_to_audit"),  # S1+S3
    ((1, 0, [], 50.0), "continue"),  # S4 only — 1 signal
    ((2, 2, [], 60.0), "switch_to_audit"),  # S1+S4
    ((3, 2, ["SLV-001", "INV-002", "x", "x", "x"], 10.0), "switch_to_audit"),  # S1+S2+S3 (3 signals but conf=0.75)
    ((1, 0, ["SLV-001 FAIL", "INV-002 conflict", "x", "x", "x"], 60.0), "switch_to_audit"),  # S3+S4
    ((2, 2, ["SLV-001", "AC-002 conflict INV-003", "x", "x", "x"], 60.0), "abort_early"),  # 4 signals
    ((4, 2, ["SLV-001 FAIL", "INV-003 contradiction", "x", "x", "x"], 60.0), "abort_early"),  # 4 signals
    ((3, 2, ["SLV-005", "AC vs INV", "x", "x", "x"], 60.0), "abort_early"),  # 4 signals
    # ---- 10 真正該 continue (0~1 信號) ----
    ((1, 0, [], 10.0), "continue"),
    ((2, 0, [], 10.0), "continue"),
    ((1, 1, [], 10.0), "continue"),  # same_pattern=1 < 2 → no S1
    ((2, 1, [], 10.0), "continue"),
    ((1, 0, ["x", "x", "x", "x", "x"], 10.0), "continue"),
    ((2, 2, [], 10.0), "continue"),  # only S1
    ((1, 0, [], 20.0), "continue"),  # drift below threshold
    ((1, 0, ["SLV-001 FAIL", "x", "x", "x", "x"], 10.0), "continue"),  # only 1 spec hit
    ((4, 0, [], 10.0), "continue"),  # high count but unstable
    ((5, 0, [], 10.0), "continue"),
    # ---- 10 邊界 / 噪音 (期望保守) ----
    ((1, 2, [], 10.0), "continue"),  # only S1
    ((2, 0, ["SLV-001 FAIL", "INV-002", "x", "x", "x"], 10.0), "continue"),  # only S3
    ((1, 0, [], 35.0), "continue"),  # only S4
    ((2, 2, ["x", "x", "x", "x", "x"], 10.0), "continue"),  # only S1
    ((3, 2, ["x", "x", "x", "x", "x"], 10.0), "switch_to_audit"),  # S1+S2 — true positive
    ((1, 0, ["SLV", "INV-001 conflict", "AC", "x", "x"], 10.0), "continue"),  # S3 alone
    ((1, 0, [], 10.0), "continue"),
    ((0, 0, [], 10.0), "continue"),  # retry_count == 0 disabled
    ((0, 5, [], 50.0), "continue"),  # retry_count == 0 disabled (overrides everything)
    ((2, 2, ["SLV-001 FAIL", "INV-002", "x", "x", "x"], 60.0), "abort_early"),  # 4 signals
]


class FixturePrecisionTests(unittest.TestCase):
    def test_fixture_false_positive_below_15pct(self):
        wrong = []
        with tempfile.TemporaryDirectory() as td:
            for i, ((count, same_pattern, traces, drift), expected) in enumerate(FIXTURES):
                state = _make_state(Path(td), f"fx{i}", current="PR_REVIEW")
                _seed_retry(state, "PR_REVIEW", count=count, same_pattern=same_pattern)
                if traces:
                    _seed_decision_trace(state, reasons=traces)
                ledger = None
                if drift > 0:
                    ledger = Path(td) / f"l{i}.yaml"
                    ledger.write_text(
                        yaml.safe_dump({"rolling_avg_drift_pct_last10": drift}),
                        encoding="utf-8",
                    )
                action = tp.predict(state, gate="PR_REVIEW", ledger_path=ledger)
                if action.decision != expected:
                    wrong.append(f"fx{i}: {action.decision} expected={expected} signals={action.signals_triggered}")
        precision = (len(FIXTURES) - len(wrong)) / len(FIXTURES)
        # Acceptance: precision ≥ 0.85 (i.e. FP rate < 15%)
        self.assertGreaterEqual(
            precision, 0.85,
            f"precision={precision:.2%}; misses={len(wrong)}:\n  " + "\n  ".join(wrong),
        )


# ----------------------------------------------------------------------
# Constants sanity
# ----------------------------------------------------------------------

class ConstantsTests(unittest.TestCase):
    def test_observation_state_registered(self):
        self.assertIn("TRAJECTORY_PREDICTED", OBSERVATION_STATES)
        self.assertIn("TRAJECTORY_PREDICTED", _HAPPY_PATH)

    def test_thresholds_consistent(self):
        self.assertGreater(tp.ABORT_THRESHOLD, tp.SWITCH_THRESHOLD)
        self.assertGreaterEqual(tp.ABORT_CONFIDENCE_FLOOR, 0.7)


if __name__ == "__main__":
    unittest.main()
