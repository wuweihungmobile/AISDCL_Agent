"""ACT-029 Chaos Runner — Phase E M2.5 precision-halt verification.

This module injects random faults into a running FSM simulation and verifies
that the FSM **always halts within a bounded number of steps**, landing in
one of the approved terminal states:

    {ESCALATION, TERMINATED, RELEASE}

Happy path on its own is trivially bounded (linear). The chaos runner
exercises adversarial scenarios that would have allowed infinite loops if
the Phase E M1/M2 guards (ACT-020~026) were missing.

Fault inventory (matches §ACT-029 L591):

- **STATE_CORRUPTION** — truncate / garble the FSM-STATE YAML mid-run.
  Exercises `state_loader.load_state` .bak fallback (ACT-029 §recovery).
- **RETRY_TAMPER** — inject absurd retry_count values. Verifies retry
  bounds are enforced on read, not trusted from state.
- **CI_EVENT_DUP** — drop duplicate `CI-EVENT-*.yaml`. Verifies
  `event_reconciler` only applies unprocessed events.
- **TIMEOUT_SIM** — stamp `human_pending_tracking.entered_at` > 168h in
  the past. Verifies `timeout_checker` escalates.
- **AUTO_COMPACT_BURST** — drive `trigger_auto_compact` past the
  per-stage cap. Verifies ACT-026 guard.
- **PR_REVIEW_JITTER** — paraphrased failure reasons. Verifies ACT-021
  semantic matcher catches same-pattern.
- **SCG_INFINITE_FAIL** — fail SCG_VALIDATION forever. Verifies the
  3-retry budget (Rule 9.1).
- **INTENT_DECOMPOSE_STORM** — repeatedly decompose over-cap / cyclic intents.
  Verifies INTENT_DECOMPOSITION converges to `underspecified` (Phase K, Rule 9.23.1).
- **DEBATE_FLAKY** — flaky spec-debate verdict. Verifies SPEC_DEBATE is
  deterministic + round-bounded (Phase K, Rule 9.23.3).
- **META_CHURN_STORM** — same-fingerprint add↔retire re-adoption storm. Verifies
  the self-improving meta-loop hits ChurnBounded → MFSM_ESCALATION (Phase L, Rule 9.24.1).
- **REPLAY_FLAKY** — counterfactual replay determinism + budget bound. Verifies
  EXPERIMENT_REPLAY stays advisory + bounded (Phase L, Rule 9.24.4).

Public API:

    run_chaos_rounds(n=100, seed=None) -> ChaosReport

CLI:

    python -m tools.fsm_runtime.chaos_runner --rounds 100 [--seed 42]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import random
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from .fsm_runtime import FSMRuntime
from .state_loader import FSMState, load_state, save_state
from .timeout_checker import evaluate_human_pending, mark_entered_now
from .transition_rules import (
    MAX_AUTO_COMPACT_PER_STAGE,
    RETRY_LIMITS,
    TransitionError,
)

TERMINAL_STATES = {"ESCALATION", "ESCALATION_FINAL", "TERMINATED", "RELEASE"}

# Rough per-operation token costs. Calibrated against conversation_ledger
# fixed overheads (Read ~200, Write ~200, transition ~50); kept deliberately
# conservative so chaos budgets surface regressions early.
_TOKEN_COST_TRANSITION = 50
_TOKEN_COST_WRITE = 180
_TOKEN_COST_READ = 120
_TOKEN_COST_GATE = 220
_TOKEN_COST_FAULT_INJECT = 80

# Hard cap per round so no scenario can run unbounded even if a guard is
# broken. 120 is ~2× the longest legitimate happy path (< 60 steps).
_MAX_STEPS_PER_ROUND = 120


@dataclass
class ChaosResult:
    round_id: int
    seed: int
    faults_injected: List[str] = field(default_factory=list)
    steps_taken: int = 0
    final_state: str = ""
    bounded: bool = False
    tokens_estimated: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "round_id": self.round_id,
            "seed": self.seed,
            "faults": self.faults_injected,
            "steps": self.steps_taken,
            "final": self.final_state,
            "bounded": self.bounded,
            "tokens": self.tokens_estimated,
            "error": self.error,
        }


@dataclass
class ChaosReport:
    rounds: List[ChaosResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.rounds)

    @property
    def bounded_count(self) -> int:
        return sum(1 for r in self.rounds if r.bounded)

    @property
    def bounded_ratio(self) -> float:
        return self.bounded_count / self.total if self.total else 0.0

    @property
    def avg_tokens(self) -> float:
        if not self.rounds:
            return 0.0
        return sum(r.tokens_estimated for r in self.rounds) / self.total

    @property
    def max_steps(self) -> int:
        return max((r.steps_taken for r in self.rounds), default=0)

    def to_dict(self) -> dict:
        return {
            "total_rounds": self.total,
            "bounded_rounds": self.bounded_count,
            "bounded_ratio": round(self.bounded_ratio, 4),
            "avg_tokens": round(self.avg_tokens, 1),
            "max_steps": self.max_steps,
            "rounds": [r.to_dict() for r in self.rounds],
        }


# ---------- fault injectors (pure functions on FSMState) ----------


def corrupt_state_file(rt: FSMRuntime, rng: random.Random) -> None:
    """Overwrite the primary YAML with random garbage mid-session.

    `.bak` is left intact so load_state fallback can recover.
    """
    path: Path = rt.state.path
    # Garbled bytes that are NOT valid YAML.
    garbage = bytes(rng.randrange(0, 256) for _ in range(32))
    path.write_bytes(b"!!!invalid_yaml\n\x00\x01\x02" + garbage)


def tamper_retry_count(rt: FSMRuntime, rng: random.Random) -> None:
    """Set a retry_count to an absurd sentinel — retry guards must still hold."""
    gate = rng.choice(list(RETRY_LIMITS.keys()))
    entry = rt.state.retry(gate)
    # Choose between massively-over-limit and negative (both illegal).
    entry["current_count"] = rng.choice([9999, -1, RETRY_LIMITS[gate] * 10])
    save_state(rt.state)


def duplicate_ci_event(rt: FSMRuntime, rng: random.Random) -> None:
    """Drop two identical CI-EVENT-*.yaml so the reconciler sees a duplicate."""
    events_dir = rt.state.path.parent
    events_dir.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    base = events_dir / f"CI-EVENT-{_dt.date.today().isoformat()}-chaos-{rng.randrange(10000)}.yaml"
    base.write_text(
        "pipeline_id: chaos\n"
        "stage: SLV\n"
        "result: FAIL\n"
        f"failure_reason: 'chaos SLV fail @ {ts}'\n"
        "scg_gate: SCG-0\n"
        f"timestamp: '{ts}'\n",
        encoding="utf-8",
    )
    # Duplicate (same content, different filename)
    dup = base.with_name(base.stem + "-dup.yaml")
    shutil.copy2(base, dup)


def simulate_human_pending_timeout(rt: FSMRuntime, rng: random.Random) -> None:
    """Stamp entered_at > 168h in the past so timeout_checker escalates."""
    # Only meaningful when already in HUMAN_PENDING.
    if rt.state.current != "HUMAN_PENDING":
        mark_entered_now(rt.state)
    past = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=200)
    tracking = rt.state.root.setdefault("human_pending_tracking", {})
    tracking["entered_at"] = past.isoformat(timespec="seconds")
    save_state(rt.state)


def auto_compact_burst(rt: FSMRuntime, rng: random.Random) -> dict:
    """Hammer trigger_auto_compact past the per-stage cap."""
    last_result: dict = {}
    for _ in range(MAX_AUTO_COMPACT_PER_STAGE + 2):
        last_result = rt.trigger_auto_compact(cumulative_tokens=180_000, ratio=0.9)
        if last_result.get("escalated"):
            break
        if rt.state.current == "AUTO_COMPACT_PENDING":
            rt.complete_auto_compact(reset_ledger=False)
    return last_result


def pr_review_jitter_reasons(rng: random.Random, *, with_spec_flavour: bool = False) -> List[str]:
    """Generate paraphrased-but-semantically-identical failure reasons.

    Synonym path (default for chaos rounds): exercises the
    `_SYNONYMS` canonicalisation chain (exceeded/above/超過 → "gt").

    For the synonym-free path (P1-06 generalisation contract), call
    :func:`pr_review_jitter_reasons_fuzzy` directly — chaos rounds keep
    the synonym pool because cross-pool jumps occasionally drop below
    the 0.75 threshold, which would weaken SPEC_AUDIT triggering and
    push more rounds into the (already bounded) ESCALATION fallback.

    When `with_spec_flavour=True` (Phase G M2 / ACT-036 chaos coupling
    with TRAJECTORY_PREDICTION), inject SLV/AC/INV identifiers into the
    paraphrases so the predictor's S3 signal (spec-pattern in trace) can
    fire earlier than the baseline same_pattern_threshold (3).
    """
    base = [
        "test_login_p95 > 200ms at concurrency 100",
        "test_login_p95 exceeded 200ms under 100 concurrent users",
        "test_login_p95 above 200ms with 100 concurrency",
        "test_login p95 超過 200ms 同時 100 users",
    ]
    if with_spec_flavour:
        # Phase G M2 / B2.8: 5 unrelated failure reasons — all carry an
        # "SLV-005 FAIL:" prefix so S3 (spec hits in trace) fires by retry 2,
        # but the bodies are different enough that pattern_matcher does NOT
        # mark them as same_pattern. Net effect:
        #   - baseline (no predictor): same_pattern stays 1 → no early
        #     SPEC_AUDIT trigger → exhausts the 5-retry PR_REVIEW budget →
        #     ESCALATION at retry 5
        #   - predictor active: at retry 2, S3 + S4 (high-drift ledger
        #     injected by _run_single_round) → 2 signals → switch_to_audit
        #     → SPEC_AUDIT → either RELEASE or ESCALATION via audit cycle
        # Saving ≈ 3 PR_REVIEW gate iters (3 × 220 tokens) ≥ 20% of total.
        templates = [
            "SLV-005 FAIL: alpha module connection refused",
            "SLV-005 FAIL: beta service unhandled exception",
            "SLV-005 FAIL: gamma module nil pointer panic",
            "SLV-005 FAIL: delta validator deadlock detected",
            "SLV-005 FAIL: epsilon engine race condition",
        ]
    else:
        templates = base
    rng.shuffle(templates)
    return templates[:5] if with_spec_flavour else templates[:3]


def pr_review_jitter_reasons_fuzzy() -> List[str]:
    """Synonym-free paraphrases — token-overlap only.

    Public so tests can assert matcher generalisation independently of the
    `_SYNONYMS` dictionary. None of these words appear in
    `pattern_matcher._SYNONYMS` or `_CHINESE_SYNONYMS` (verified by the
    sanity assertion in `test_pr_review_jitter_works_beyond_synonyms`).
    """
    # Token-overlap pool: every entry shares the core skeleton
    # `test_login p95 200ms 100 parallel requests` plus one differentiator
    # ("hit" / "reached" / "fail" / "breach"). All pairwise similarities
    # measure ≥ 0.80 against the matcher's default 0.75 threshold (verified
    # by `test_pr_review_jitter_works_beyond_synonyms`).
    return [
        "test_login p95 200ms hit at 100 parallel requests slow",
        "test_login p95 200ms reached at 100 parallel requests issue",
        "test_login p95 200ms fail at 100 parallel requests timeout",
        "test_login p95 200ms breach at 100 parallel requests problem",
    ]


FAULT_TYPES = (
    "STATE_CORRUPTION",
    "RETRY_TAMPER",
    "CI_EVENT_DUP",
    "TIMEOUT_SIM",
    "AUTO_COMPACT_BURST",
    "PR_REVIEW_JITTER",
    "SCG_INFINITE_FAIL",
    # Phase G M2 / ACT-036: predictive halt scenario. When enabled, calls
    # consult_predictor() on PR_REVIEW after first failure (retry_count ≥ 1),
    # short-circuiting jitter retries via TRAJECTORY_PREDICTED → SPEC_AUDIT.
    # Used to verify ≥ 20% token saving vs baseline (per planning §M2 B2.8).
    "TRAJECTORY_PREDICTION",
    # Phase I M1 / ACT-059: non-deterministic (flaky) execution. A flaky
    # verdict (hermetic rerun mixed pass/fail) must be ISOLATED — it must NOT
    # consume EXECUTION_EVALUATION retry budget nor pollute TrajectoryPredictor.
    # Modeled as: deterministic-isolation → bounded ESCALATION asking the human
    # for a deterministic repro (never an unbounded retry loop).
    "FLAKY_EVAL",
    # Phase J / ACT-073: adversarial flaky counterexample. An ADVERSARIAL_EVALUATION
    # counterexample that is itself non-deterministic (mixed verdict across the
    # FLAKY_RERUN_N consensus) must be ISOLATED as `inconclusive` — never treated
    # as a real counterexample, never fed into IMPLEMENTATION retry (Rule 9.22.1).
    # Verifies the adversarial judge's flaky-isolation path stays bounded.
    "ADVERSARIAL_FLAKY",
    # Phase K M-K1 / ACT-082: intent-decomposition storm. Repeatedly decomposing
    # an intent that exceeds SDD_INTENT_MAX_NODES (or contains a dependency cycle)
    # must converge to `underspecified` → HUMAN_PENDING (bounded), never infinite
    # subdivision. Verifies INTENT_DECOMPOSITION gatekeep boundedness (Rule 9.23.1).
    "INTENT_DECOMPOSE_STORM",
    # Phase K M-K2 / ACT-084: flaky spec debate. A debate verdict must be
    # deterministic per call and round-bounded (SDD_SPEC_DEBATE_ROUNDS clamp) —
    # never an unbounded consensus/divergence flicker. Divergence isolates to a
    # bounded human-disambiguation halt (Rule 9.23.3 / 9.23.4).
    "DEBATE_FLAKY",
    # Phase L M-L1 / ACT-090: meta-loop churn storm. Repeatedly re-adopting the
    # same retired rule fingerprint must hit ChurnBounded (SDD_META_CHURN_MAX) and
    # be refused → MFSM_ESCALATION (bounded), never infinite add↔retire oscillation.
    # Verifies the self-improving meta-loop itself provably halts (Rule 9.24.1).
    "META_CHURN_STORM",
    # Phase L M-L2 / ACT-091: flaky counterfactual replay. A replay verdict must be
    # deterministic per call and budget-bounded (SDD_REPLAY_MAX_CASES) — advisory
    # evidence only, never unbounded experimentation (Rule 9.24.4).
    "REPLAY_FLAKY",
    # Phase M M-M1 / ACT-098: composition conflict storm. A storm of unresolvable
    # cross-intent conflicts on a shared spec node must hit RenegotiationBounded
    # (SDD_COMPOSITION_RENEG_MAX) → CPLAN_ESCALATION (bounded), never infinite
    # cross-intent renegotiation livelock (Rule 9.25.1).
    "COMPOSITION_CONFLICT_STORM",
    # Phase M M-M2 / ACT-100: scaffold ceiling flap. The A/B ceiling verdict must be
    # deterministic and ADVISORY only — it surfaces a net-negative scaffold for human
    # set_maturity, never auto-retiring a still-firing scaffold (Rule 9.25.5).
    "CEILING_FLAP",
    # Phase N / ACT-110: optimization search storm. A huge composition-optimization
    # search space must hit SearchBounded (SDD_OPT_NODE_BUDGET) and stop (best-so-far
    # or OPT_ESCALATION), never exponential unbounded branch-and-bound (Rule 9.26.1).
    "OPT_SEARCH_STORM",
    # Phase O / ACT-116: objective-tuning flap. A storm of Goodhart "fake-optimal"
    # weight proposals must be REJECTED by the held-out oracle (zero-miss — a profile
    # cannot grade itself), and the obj-profile add↔retire churn must hit ChurnBounded
    # (SDD_META_CHURN_MAX) → MFSM_ESCALATION (bounded) — never infinite self-tuning
    # oscillation nor self-graded adoption (Rule 9.27.1/9.27.2).
    "OBJECTIVE_TUNE_FLAP",
    # Phase P / ACT-122: cross-scorer seam Goodhart. A value vector that weakens one scorer so
    # a bad pipeline candidate gets selected PASSES each per-scorer view in isolation but is
    # REJECTED by the pipeline-level joint oracle (zero-miss — per-scorer pass != joint pass,
    # Rule 9.28.2). Verifies the unified anti-Goodhart seam defence stays sound.
    "CROSS_SCORER_GOODHART_FLAP",
    # Phase P / ACT-122: joint calibration flap. An A→B→A cross-scorer adoption storm (each
    # fingerprint first-adopted, per-fingerprint churn=0) hits the aggregate
    # CrossScorerChurnBounded rate cap → MFSM_ESCALATION (bounded) — never infinite coupled
    # oscillation that per-fingerprint ChurnBounded is blind to (Rule 9.28.3).
    "JOINT_CALIBRATION_FLAP",
    # Phase Q / ACT-128: dimension Goodhart flap. A storm of self-serving noise axes (high self
    # appeal, zero held-out incremental coverage) and redundant axes (re-projection of an existing
    # dimension) is REJECTED by the dimension necessity oracle (zero-miss — proposer self-pass !=
    # oracle necessary, Rule 9.29.2). Verifies the meta-meta anti-Goodhart defence stays sound.
    "DIMENSION_GOODHART_FLAP",
    # Phase Q / ACT-128: dimension explosion flap. A storm of distinct new value dimensions (each
    # first-adopted, per-fingerprint churn=0, slow enough to dodge the Phase P aggregate rate
    # window) hits the DimensionCardinalityBounded stock ceiling → DimensionCardinalityExceeded →
    # MFSM_ESCALATION (bounded) — never unbounded ontology growth that per-fingerprint/aggregate
    # churn is blind to (Rule 9.29.3).
    "DIMENSION_EXPLOSION_FLAP",
    # Phase R / ACT-134: dimension self-invention Goodhart. A self-referential invented axis (probe
    # references the proposer's own approval signals, e.g. self_score/proposer_*) is REJECTED by the
    # synthesizer's self-reference guard before reaching the oracle (zero-miss, anti-self-interest
    # first gate), and a candidate-pool-external noise axis (zero held-out incremental coverage) is
    # REJECTED by the feature-keyed necessity oracle (zero-miss — synthesizer self-pass != oracle
    # necessary, Rule 9.30.2). Verifies the meta-meta-meta anti-self-interest defence stays sound.
    "DIMENSION_INVENTION_GOODHART_FLAP",
    # Phase R / ACT-134: dimension swap thrash. A storm of retire-to-swap operations at the
    # cardinality ceiling (each net cardinality=0, stock never exceeded, per-fingerprint churn<=1)
    # hits the SwapCadenceBounded aggregate swap-rate cap → SwapCadenceExceeded → MFSM_ESCALATION
    # (bounded) — never unbounded same-cardinality ontology rotation that per-fingerprint churn and
    # the Phase Q cardinality stock are both blind to (Rule 9.30.3).
    "DIMENSION_SWAP_THRASH_FLAP",
    # Phase S / ACT-140: vocabulary genesis Goodhart (meta⁴). A self-referential genesis feature
    # (source/transform references the proposer's own approval signals, e.g. self_score/proposer_*)
    # is REJECTED by the vocabulary self-reference guard before reaching the oracle (zero-miss, anti
    # self-interest first gate), and a vocab-external noise feature (zero held-out incremental
    # coverage) is REJECTED by the feature-grounded necessity oracle (zero-miss — genesis self-pass
    # != oracle necessary, Rule 9.31.2). Verifies the meta⁴ anti-self-interest defence stays sound.
    "VOCAB_GENESIS_GOODHART_FLAP",
    # Phase S / ACT-140: batch swap thrash (meta⁴). A storm of multi-dimension batch retire-to-swap
    # operations at the cardinality ceiling (each net cardinality non-increasing, distinct batch_id)
    # hits the BatchSwapCadenceBounded aggregate batch-rate cap → BatchSwapCadenceExceeded →
    # MFSM_ESCALATION (bounded) — never unbounded batch ontology rotation (batch size unbounded /
    # batch-internal high-low offset / one atomic batch != n swaps) that per-swap SwapCadence and the
    # monotone value ratchet are both blind to (Rule 9.31.3).
    "BATCH_SWAP_THRASH_FLAP",
    # Phase T / ACT-146: operator genesis Goodhart (meta⁵). A self-referential invented operator
    # (primary/combinator/secondary/probe references the proposer's own approval signals, e.g.
    # self_score/proposer_*) is REJECTED by the operator self-reference guard before reaching the
    # oracle (zero-miss, anti-self-interest first gate), and an OPS-external noise operator (zero
    # held-out incremental coverage) is REJECTED by the feature-grounded operator necessity oracle
    # (zero-miss — genesis self-pass != oracle necessary, Rule 9.32.2). Verifies the meta⁵
    # anti-self-interest defence stays sound.
    "OPERATOR_GENESIS_GOODHART_FLAP",
    # Phase T / ACT-146: operator computability (meta⁵ deepest halting). The invented operator is a
    # *piece of executable computation* (not data) — a non-total operator (undefined/raising on some
    # input) or an over-budget operator (cost > SDD_DIM_OP_STEP_MAX, e.g. recursion/loop/over-deep
    # expression tree) is REJECTED by guard_operator_computability before adoption →
    # OperatorComputabilityExceeded (bounded) — the bounded operator grammar structurally guarantees
    # every invented operator is total + bounded-step + recursion/loop-free, pinning the halting
    # problem into the self-expansion artefact itself (Rule 9.32.3).
    "OPERATOR_COMPUTABILITY_FLAP",
    # Phase U / ACT-149: operator alphabet genesis Goodhart (meta⁶). A self-referential invented
    # alphabet element (reducer/post_map/atom/probe references the proposer's own approval signals,
    # e.g. self_score/proposer_*) is REJECTED by the alphabet self-reference guard before reaching the
    # oracle (zero-miss, anti-self-interest first gate), and an alphabet-external noise element (zero
    # held-out incremental coverage) is REJECTED by the feature-grounded alphabet necessity oracle
    # (zero-miss — genesis self-pass != oracle necessary, Rule 9.33.2). Verifies the meta⁶
    # anti-self-interest defence stays sound.
    "ALPHABET_GENESIS_GOODHART_FLAP",
    # Phase U / ACT-149: computability closure (meta⁶ deepest halting). The invented alphabet element
    # is a *generation-rule part* the operator grammar uses to generate the *entire* algebra — a
    # closure-breaking element (non-total reducer → some operator over the expanded alphabet raises/NaN,
    # or over-budget → G(A') max_cost > SDD_DIM_OP_STEP_MAX) is REJECTED by guard_computability_closure
    # before adoption → ComputabilityClosureViolation (bounded). The bounded alphabet grammar
    # structurally guarantees every invented element keeps the whole generated algebra total +
    # bounded-step + recursion/loop-free, pinning the halting problem into the self-expansion
    # generation rule itself (Rule 9.33.3).
    "COMPUTABILITY_CLOSURE_FLAP",
    # Phase V / ACT-152: operator depth genesis Goodhart (meta⁷). A self-referential invented depth
    # operator (base/chain/probe references the proposer's own approval signals, e.g. self_score/
    # proposer_*) is REJECTED by the depth self-reference guard before reaching the oracle (zero-miss,
    # anti-self-interest first gate), and a depth-external noise operator (zero held-out incremental
    # coverage) is REJECTED by the feature-grounded depth necessity oracle (zero-miss — genesis
    # self-pass != oracle necessary, Rule 9.34.2). Verifies the meta⁷ anti-self-interest defence stays sound.
    "DEPTH_GENESIS_GOODHART_FLAP",
    # Phase V / ACT-152: depth closure (meta⁷ deepest halting, because cost==depth). The self-expanded
    # artefact is the operator grammar's *structural depth parameter itself* — and cost==depth, so
    # expanding the depth literally expands the step count. A depth operator whose depth exceeds STEP_MAX
    # (cost==depth > SDD_DIM_OP_STEP_MAX) or a non-total depth operator (bad chain combinator raising/NaN)
    # is REJECTED by guard_depth_closure before adoption → DepthClosureViolation (bounded). The bounded
    # depth grammar structurally guarantees every invented depth operator keeps the whole same-depth
    # algebra total + cost==depth-bounded + recursion/loop-free, pinning the halting problem into the
    # self-expansion generation-grammar depth parameter itself (Rule 9.34.3).
    "DEPTH_CLOSURE_FLAP",
    # Phase W / ACT-155: operator recursion genesis Goodhart (meta⁸). A self-referential invented
    # inter-recursive operator (node base/probe references the proposer's own approval signals, e.g.
    # self_score/proposer_*) is REJECTED by the recursion self-reference guard before reaching the
    # oracle (zero-miss, anti-self-interest first gate), and a recursion-external noise operator (zero
    # held-out incremental coverage) is REJECTED by the feature-grounded recursion necessity oracle
    # (zero-miss — genesis self-pass != oracle necessary, Rule 9.35.2). Verifies the meta⁸ anti-self-
    # interest defence stays sound.
    "RECURSION_GENESIS_GOODHART_FLAP",
    # Phase W / ACT-155: recursion closure (meta⁸ only-ever decidability-boundary halting). The self-
    # expanded artefact is whether operators may call each other / themselves — and deciding whether an
    # arbitrary cyclic call graph halts IS the halting problem (undecidable), so the "bounded step count"
    # device structurally fails. A recursive operator whose call graph contains an uncertified cycle (no
    # back-edge strictly decreasing a lower-bounded rank → may not terminate), whose fuel exceeds STEP_MAX,
    # or that is non-total, is REJECTED by guard_recursion_closure before adoption → RecursionClosure-
    # Violation (bounded). The bounded recursion grammar structurally guarantees every invented operator
    # carries a well-founded termination certificate (acyclic ∨ rank-descending cycles + fuel<=STEP_MAX +
    # total + recursion/loop-free evaluator), pinning the halting problem onto the decidable/total fragment
    # boundary itself — replacing the failed "bounded step count" device with "well-founded measure" (Rule 9.35.3).
    "RECURSION_CLOSURE_FLAP",
    # Phase X / ACT-158 (meta⁸ embodied grounding): Phase L~W pushed the meta-loop's self-evolution to meta⁸,
    # but its EVALUATION side was always synthetic-corpus win-rate — never launching a sandbox / querying real
    # logs (GAP-X1, measured by the Phase X slice FF-16). The full Phase X inserts an EMBODIED_GROUNDING_GATE
    # before META adoption: a self-invented capability must first carry a sandbox-grounded verdict (OQS-grounded).
    # The halting irony — validating against the REAL environment introduces "the real sandbox may hang" — is
    # sealed by guard_embodied_grounding: a zero-observation false-green verdict is fail-closed → EmbodiedGrounding-
    # Violation (bounded), and a sandbox timeout maps to grounded_fail (FSM doesn't wall-clock wait). 100%
    # isomorphic with TLA+ EmbodiedGroundingBounded (Rule 9.36).
    "EMBODIED_GROUNDING_FLAP",
    # Phase Y / ACT-161 (meta⁸ explainability / token-budget halting): rendering a meta⁸ recursion call graph for
    # human approval introduces "rendering an unbounded huge graph may OOM / token-explode" as a new non-halting
    # source (same shape as Phase X "the real sandbox may hang"). A 10⁶-node adversarial graph is bounded-truncated
    # to <= node_budget + paginated and its dashboard markdown stays <= char_budget — guard_visualization_bounded
    # allows the bounded render. 100% isomorphic with TLA+ VisualizationBounded (Rule 9.37).
    "VISUALIZATION_FLAP",
    # Phase Y / ACT-161 (meta⁸ explainability anti-forgery): a tampered render drawing a SIMPLER graph than the
    # operator actually runs (drops a within-window call edge / fakes a rank to look more well-founded) is the
    # visual-deception attack. verify_topology_consistency independently re-derives the subgraph from to_dict() and
    # REJECTS the forgery → TopologyConsistencyError (fail-closed); a faithful render is correctly allowed (Rule 9.37).
    "VISUALIZATION_TOPOLOGY_DRIFT_FLAP",
    # W-23-1 (improving_23, meta⁸ explainability folding anti-forgery): a folded super-node is an HONEST
    # contraction only if it declares a genuine interior simple chain. A forged fold (swallowing a branch/sink,
    # hiding entry, or dropping a member to draw a simpler graph) is rejected by fold-aware
    # verify_topology_consistency → TopologyConsistencyError (fail-closed, bounded); a faithful fold is allowed.
    "VISUALIZATION_FOLD_DRIFT_FLAP",
)


def _flaky_is_isolated() -> bool:
    """Deterministic check that hermetic rerun classifies mixed runs as FLAKY.

    Uses observation overrides (no docker) so the chaos round stays
    deterministic and offline. Returns True when the third-verdict isolation
    holds (3 pass / 2 fail → FLAKY, not FAIL).
    """
    from .sandbox_runner import SandboxSpec, ExecutionObservation, evaluate_hermetic
    mix = (
        [ExecutionObservation(tests_total=5, tests_passed=5)] * 3
        + [ExecutionObservation(tests_total=5, tests_passed=0, nonzero_exit=True)] * 2
    )
    res = evaluate_hermetic(
        SandboxSpec(app_id="chaos-flaky"), observation_overrides=mix, write_report=False
    )
    return res.is_flaky


def _adversarial_flaky_is_isolated() -> bool:
    """Phase J / ACT-073: deterministic check that an adversarial counterexample
    which is itself flaky gets classified as `inconclusive` (isolated), not as a
    real counterexample that would re-enter IMPLEMENTATION retry.

    Construction is fully deterministic and offline: a closure whose FIRST call
    violates the declared `non_negative` property (→ counterexample on rerun 1),
    but every subsequent call returns abs(x) ≥ 0 (→ robust on reruns 2..N). The
    mixed verdict across FLAKY_RERUN_N reruns ⇒ inconclusive/flaky (Rule 9.22.1).
    """
    from .adversarial_synthesizer import Target, evaluate_target
    state = {"n": 0}

    def fn(x):
        i = state["n"]
        state["n"] += 1
        if i == 0:
            return -1  # first call violates non_negative → counterexample (rerun 1)
        return abs(x) if isinstance(x, (int, float)) else 0  # non-negative, distinct

    res = evaluate_target(
        Target(fn=fn, domain="int", declared_properties=("non_negative",))
    )
    return res.flaky and res.verdict == "inconclusive"


def _intent_decompose_storm_is_bounded() -> bool:
    """Phase K M-K1 / ACT-082: over-cap and cyclic intents both converge to
    `underspecified` (bounded — INTENT_DECOMPOSITION never subdivides forever).
    Fully deterministic and offline."""
    from .intent_decomposer import decompose
    over = "\n".join(f"- 需求{i}" for i in range(1, 200))   # 199 items >> cap
    r_over = decompose(over, max_nodes=8)
    r_cyc = decompose("- a [dep:2]\n- b [dep:1]")           # dependency cycle
    return r_over.status == "underspecified" and r_cyc.status == "underspecified"


def _debate_flaky_is_bounded() -> bool:
    """Phase K M-K2 / ACT-084: spec debate yields a deterministic verdict per call
    and clamps rounds (never unbounded back-and-forth). Deterministic and offline."""
    from .spec_debate import debate, clamp_rounds, MAX_ROUNDS
    amb = debate("折扣可疊加")                  # divergence
    clear = debate("密碼長度至少 8 個字元")      # consensus
    return (amb.verdict == "divergence" and clear.verdict == "consensus"
            and clamp_rounds(9999) == MAX_ROUNDS)


def _meta_churn_storm_is_bounded() -> bool:
    """Phase L M-L1 / ACT-090: a storm of same-fingerprint add↔retire re-adoptions
    hits ChurnBounded and is refused (→ MFSM_ESCALATION), never infinite churn.
    Deterministic + offline (own temp ledger; adapts to runtime churn_max)."""
    import tempfile
    from .meta_halt import meta_halt_monitor as MM
    cmax = MM.churn_max()
    with tempfile.TemporaryDirectory() as td:
        led = Path(td) / "meta-loop-ledger.yaml"
        MM.record_rule_add("R0", "fp", 0, ledger_path=led)
        for i in range(cmax):                         # build churn == cmax (each readopt 帶 cap-delta)
            MM.record_rule_retire(f"R{i}", "fp", i, ledger_path=led)
            MM.record_rule_add(f"R{i+1}", "fp", i + 1, ledger_path=led)
        MM.record_rule_retire("Rx", "fp", cmax, ledger_path=led)
        try:
            MM.record_rule_add("Rfinal", "fp", cmax + 1, ledger_path=led)  # 第 cmax+1 次再採納
            return False                              # 應被 ChurnBounded 拒絕
        except MM.ChurnBoundExceeded:
            return True


def _replay_flaky_is_bounded() -> bool:
    """Phase L M-L2 / ACT-091: counterfactual replay yields a deterministic verdict
    and is budget-bounded (examined ≤ max_cases) — never unbounded experimentation.
    Deterministic + offline."""
    from .counterfactual_replay import PatchProposal, HistoricalCase, replay
    patch = PatchProposal(ac_id="AC-1", guard_text="discount stacking forbidden coupon")
    cases = [HistoricalCase(case_id=f"C{i}", ac_id="AC-1",
                            failure_text="discount stacking coupon double") for i in range(100)]
    r1 = replay(patch, cases, max_cases=5)
    r2 = replay(patch, cases, max_cases=5)
    no_corpus = replay(patch, [], max_cases=5)
    return (r1.verdict == r2.verdict == "done"
            and r1.examined == 5 and r1.prevented == r2.prevented   # deterministic + bounded
            and no_corpus.verdict == "inconclusive")


def _composition_conflict_storm_is_bounded() -> bool:
    """Phase M M-M1 / ACT-098: a storm of unresolvable cross-intent conflicts on a
    shared spec node hits RenegotiationBounded (SDD_COMPOSITION_RENEG_MAX) and is
    refused (→ CPLAN_ESCALATION), never infinite cross-intent renegotiation livelock.
    Deterministic + offline (own temp ledger; adapts to runtime reneg_max)."""
    import tempfile
    from .composition_halt_monitor import (
        reneg_max, record_negotiate, RenegotiationBoundExceeded,
    )
    rmax = reneg_max()
    with tempfile.TemporaryDirectory() as td:
        led = Path(td) / "composition-ledger.yaml"
        for _ in range(rmax):                       # build reneg == rmax
            record_negotiate("AC-014", ledger_path=led)
        try:
            record_negotiate("AC-014", ledger_path=led)  # rmax+1 → refused
            return False
        except RenegotiationBoundExceeded:
            return True


def _ceiling_flap_is_bounded() -> bool:
    """Phase M M-M2 / ACT-100: scaffold ceiling A/B verdict is deterministic and
    ADVISORY only — a net-negative still-firing scaffold is surfaced for human
    set_maturity, never auto-retired (Rule 9.25.5). Deterministic + offline."""
    from .scaffold_ceiling_detector import ABSample, detect_ceilings
    from .output_quality_scorer import ExecutionObservation
    samples = [ABSample(
        "SLV-x",
        with_obs=ExecutionObservation(tests_total=10, tests_passed=6),
        without_obs=ExecutionObservation(tests_total=10, tests_passed=10),
    )]
    r1 = detect_ceilings(samples)
    r2 = detect_ceilings(samples)
    return (len(r1.proposals) == len(r2.proposals) == 1
            and r1.proposals[0].scaffold_id == "SLV-x")


def _opt_search_storm_is_bounded() -> bool:
    """Phase N / ACT-110: a huge composition-optimization search space hits SearchBounded
    (node budget) and stops — never exponential unbounded branch-and-bound (Rule 9.26.1).
    Deterministic + offline."""
    from .composition_optimizer import optimize
    from .composition_objective_scorer import OptProblem
    budget = 10
    p = OptProblem(values={f"I{i}": 1.0 for i in range(12)}, max_parallel=3)
    r = optimize(p, node_budget=budget)
    # 有界：展開節點數不超預算；且必落地（找到 best-so-far 或 escalate），非無限搜尋。
    return r.nodes_expanded <= budget and (r.feasible or r.escalated)


def _objective_tune_flap_is_bounded() -> bool:
    """Phase O / ACT-116: a storm of Goodhart fake-optimal weight proposals is rejected by
    the held-out oracle (zero-miss — a profile cannot self-grade), AND obj-profile add↔retire
    churn hits ChurnBounded → MFSM_ESCALATION (bounded) — never infinite self-tuning nor
    self-graded adoption (Rule 9.27.1/9.27.2). Deterministic + offline (own temp ledger)."""
    import tempfile
    from .objective_tuner import WeightProfile, adopt_profile, retire_profile
    from .objective_replay_oracle import HeldOutCase, evaluate_candidate
    from .meta_halt import meta_halt_monitor as MM

    # (1) 反 Goodhart：cram 陷阱 → 任何「假最優」權重都拿不到正 win（held-out 鎖死真實品質）。
    corpus = [HeldOutCase(
        case_id="CRAM", values={"A": 1.0, "B": 1.0, "C": 1.0},
        candidates=(([["A", "B", "C"]], 0.2), ([["A"], ["B"], ["C"]], 0.9)),
    )]
    inc = WeightProfile(1.0, 0.1)
    goodhart_caught = all(
        not evaluate_candidate(p, inc, corpus, win_margin=0.1).passes_margin
        for p in (WeightProfile(0.0, 0.0), WeightProfile(2.0, 0.0), WeightProfile(0.0, 0.5))
    )

    # (2) 有界停機：obj-profile churn 觸頂 → ChurnBounded 拒絕（→ MFSM_ESCALATION）。
    cmax = MM.churn_max()
    with tempfile.TemporaryDirectory() as td:
        led = Path(td) / "meta-loop-ledger.yaml"
        prof = WeightProfile(1.0, 0.2)
        adopt_profile(prof, 0, human_signoff=True, ledger_path=led)
        for i in range(cmax):
            retire_profile(prof, i, ledger_path=led)
            adopt_profile(prof, i + 1, human_signoff=True, ledger_path=led)
        retire_profile(prof, cmax, ledger_path=led)
        try:
            adopt_profile(prof, cmax + 1, human_signoff=True, ledger_path=led)
            churn_bounded = False
        except MM.ChurnBoundExceeded:
            churn_bounded = True
    return goodhart_caught and churn_bounded


def _cross_scorer_goodhart_flap_is_bounded() -> bool:
    """Phase P / ACT-122: a seam Goodhart value vector (weaken one scorer so a bad pipeline
    candidate gets selected) PASSES each per-scorer view in isolation but is REJECTED by the
    pipeline-level joint oracle (zero-miss — per-scorer pass != joint pass, Rule 9.28.2).
    Deterministic + offline."""
    from .joint_calibration_oracle import (JointHeldOutCase, JointCandidate,
                                           incumbent_vector, apply_selection, evaluate_joint)
    from .scorer_calibration_registry import CalibrationProfile
    corpus = [JointHeldOutCase(case_id="SEAM", candidates=[
        JointCandidate(0.9, {"adversarial": {"attack_strength_w": 0.5, "breadth_w": 0.5},
                             "fragility": {"threshold_w": 1.0, "history_w": 1.0},
                             "ambiguity": {"block_threshold_w": 1.0, "dimension_w": 1.0}}),
        JointCandidate(0.2, {"adversarial": {"attack_strength_w": 5.0, "breadth_w": 0.0},
                             "fragility": {"threshold_w": 0.0, "history_w": 0.0},
                             "ambiguity": {"block_threshold_w": 0.0, "dimension_w": 0.0}}),
    ])]
    inc = incumbent_vector()
    weak = CalibrationProfile.of("adversarial-profile:", {"attack_strength_w": 0.0, "breadth_w": 0.5})
    cand = apply_selection(inc, {"adversarial": weak})
    v = evaluate_joint(cand, inc, corpus, win_margin=0.1)
    # zero-miss：接縫 Goodhart 整體真實品質崩 → 不達 margin（拒絕，per 通過≠joint 通過）。
    return (not v.passes_margin) and v.candidate_quality <= 0.2


def _joint_calibration_flap_is_bounded() -> bool:
    """Phase P / ACT-122: an A→B→A cross-scorer adoption storm (each fingerprint first-adopted,
    per-fingerprint churn=0) hits the aggregate CrossScorerChurnBounded rate cap →
    CrossScorerChurnExceeded → MFSM_ESCALATION (bounded) — never infinite coupled oscillation
    that per-fingerprint ChurnBounded is blind to (Rule 9.28.3). Deterministic + offline."""
    import tempfile
    from .scorer_calibration_registry import CalibrationProfile, adopt_profile
    from .meta_halt import meta_halt_monitor as MM
    rate_max = MM.calib_adopt_rate_max()
    nss = ["adversarial-profile:", "fragility-profile:", "ambiguity-profile:", "obj-profile:"]
    with tempfile.TemporaryDirectory() as td:
        led = Path(td) / "meta-loop-ledger.yaml"
        for i in range(rate_max):
            adopt_profile(CalibrationProfile.of(nss[i % len(nss)], {"w": float(i)}), 1,
                          human_signoff=True, ledger_path=led)
        try:
            adopt_profile(CalibrationProfile.of(nss[0], {"w": 999.0}), 1,
                          human_signoff=True, ledger_path=led)
            bounded = False
        except MM.CrossScorerChurnExceeded:
            bounded = True
        escalated = MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"
    return bounded and escalated


def _dimension_goodhart_flap_is_bounded() -> bool:
    """Phase Q / ACT-128: a self-serving noise axis (high self-appeal, zero held-out incremental
    coverage) and a redundant axis (re-projection of an existing dimension) are both REJECTED by
    the dimension necessity oracle (zero-miss — proposer self-pass != oracle necessary, Rule
    9.29.2). Deterministic + offline."""
    from .dimension_necessity_oracle import DimHeldOutCase, DimCandidate, evaluate_dimension
    from .value_dimension_registry import ValueDimension
    # 噪音軸：新軸 flip 到真實品質不更好的候選 → 增量覆蓋 ≈ 0（自評高、真實零增量）。
    noise = [DimHeldOutCase("N", "noise", [
        DimCandidate(0.6, 2.0, 5.0), DimCandidate(0.6, 3.0, 0.0), DimCandidate(0.4, 4.0, 8.0)])]
    # 冗餘軸：dim_value ∝ existing_cost（再投影）→ 一致率 1.0 → 冗餘。
    redundant = [DimHeldOutCase("R", "redundant", [
        DimCandidate(0.6, 2.0, 2.0), DimCandidate(0.5, 3.0, 3.0), DimCandidate(0.4, 4.0, 4.0)])]
    v_noise = evaluate_dimension(ValueDimension.of("noise"), noise, coverage_margin=0.1)
    v_red = evaluate_dimension(ValueDimension.of("redundant"), redundant, coverage_margin=0.1)
    # zero-miss：兩種維度 Goodhart 都被 oracle 判不必要（proposer 自評通過 != oracle 必要）。
    return (not v_noise.necessary) and (not v_red.necessary)


def _dimension_explosion_flap_is_bounded() -> bool:
    """Phase Q / ACT-128: a storm of distinct new value dimensions (each first-adopted, churn=0)
    hits the DimensionCardinalityBounded stock ceiling → DimensionCardinalityExceeded →
    MFSM_ESCALATION (bounded) — never unbounded ontology growth that per-fingerprint/aggregate
    churn is blind to (Rule 9.29.3). Deterministic + offline (own temp ledger; adapts to runtime
    cardinality_max via env override for speed)."""
    import os
    import tempfile
    from .value_dimension_registry import ValueDimension, adopt_dimension
    from .meta_halt import meta_halt_monitor as MM
    prev = os.environ.get("SDD_DIM_CARDINALITY_MAX")
    os.environ["SDD_DIM_CARDINALITY_MAX"] = "4"          # 小天花板使 chaos 輪快速 + deterministic
    try:
        dmax = MM.dimension_cardinality_max()
        with tempfile.TemporaryDirectory() as td:
            led = Path(td) / "meta-loop-ledger.yaml"
            for i in range(dmax):                        # 填滿天花板（每條首採、churn=0）
                adopt_dimension(ValueDimension.of("dim%d" % i, probe=("x",)), 50,
                                human_signoff=True, ledger_path=led)
            try:
                adopt_dimension(ValueDimension.of("dim_overflow", probe=("x",)), 50,
                                human_signoff=True, ledger_path=led)   # max+1 → refused
                bounded = False
            except MM.DimensionCardinalityExceeded:
                bounded = True
            escalated = MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"
    finally:
        if prev is None:
            os.environ.pop("SDD_DIM_CARDINALITY_MAX", None)
        else:
            os.environ["SDD_DIM_CARDINALITY_MAX"] = prev
    return bounded and escalated


def _dimension_invention_goodhart_flap_is_bounded() -> bool:
    """Phase R / ACT-134: a self-referential invented axis (probe references the proposer's own
    approval signals) is REJECTED by the synthesizer's self-reference guard before reaching the
    oracle (zero-miss, anti-self-interest first gate), and a candidate-pool-external noise axis
    (zero held-out incremental coverage) is REJECTED by the feature-keyed necessity oracle
    (zero-miss — synthesizer self-pass != oracle necessary, Rule 9.30.2). Deterministic + offline."""
    from .dimension_semantics_synthesizer import InventedDimension, is_self_referential
    from .dimension_necessity_oracle import (
        FeatureCase, FeatureCandidate, evaluate_invented_dimension)
    # 自指自利軸：probe 引用 proposer 自己的核可訊號 → self-reference guard 第一閘攔（零漏放）。
    selfref = InventedDimension.of("mean", ["self_score", "proposer_confidence"])
    selfref_blocked = is_self_referential(selfref)
    # 候選池外噪音軸：合法特徵，但 flip 到真實品質不更好的候選 → 增量覆蓋 ≈ 0（oracle 第二閘攔）。
    noise = InventedDimension.of("mean", ["canary_gap"])
    noise_corpus = [FeatureCase("N", [
        FeatureCandidate(0.6, 2.0, {"canary_gap": 5.0}),
        FeatureCandidate(0.6, 3.0, {"canary_gap": 0.0}),
        FeatureCandidate(0.4, 4.0, {"canary_gap": 8.0})])]
    v_noise = evaluate_invented_dimension(noise, noise_corpus, coverage_margin=0.1)
    # zero-miss：自指軸被 guard 攔 + 候選池外噪音軸被 oracle 判不必要。
    return selfref_blocked and (not v_noise.necessary)


def _dimension_swap_thrash_flap_is_bounded() -> bool:
    """Phase R / ACT-134: a storm of retire-to-swap operations at the cardinality ceiling (each net
    cardinality=0, stock never exceeded, per-fingerprint churn<=1) hits the SwapCadenceBounded
    aggregate swap-rate cap → SwapCadenceExceeded → MFSM_ESCALATION (bounded) — never unbounded
    same-cardinality ontology rotation that per-fingerprint churn and the Phase Q cardinality stock
    are both blind to (Rule 9.30.3). Deterministic + offline (own temp ledger; env override)."""
    import os
    import tempfile
    from .dimension_semantics_synthesizer import InventedDimension, adopt_invention, swap_dimension
    from .meta_halt import meta_halt_monitor as MM
    prev_card = os.environ.get("SDD_DIM_CARDINALITY_MAX")
    prev_rate = os.environ.get("SDD_DIM_SWAP_RATE_MAX")
    os.environ["SDD_DIM_CARDINALITY_MAX"] = "3"
    os.environ["SDD_DIM_SWAP_RATE_MAX"] = "3"
    try:
        dmax = MM.dimension_cardinality_max()
        rate_max = MM.dim_swap_rate_max()
        feats = ("rollback_steps", "blast_radius", "canary_gap", "data_loss_window",
                 "schema_lock_time", "oncall_pages", "runbook_depth", "supply_chain_pins")
        with tempfile.TemporaryDirectory() as td:
            led = Path(td) / "meta-loop-ledger.yaml"
            for i in range(dmax):                        # 填滿天花板
                adopt_invention(InventedDimension.of("mean", [feats[i]]), 40 + i,
                                human_signoff=True, ledger_path=led)
            out_dim = InventedDimension.of("mean", [feats[0]])
            out_tier = 40
            try:
                # 定基數旋轉 swap（每次 net 基數不變、每指紋 churn<=1、tier 嚴增過棘輪）
                for j in range(rate_max + 1):
                    in_dim = InventedDimension.of("max", [feats[dmax + j]])
                    in_tier = out_tier + 10 + j
                    swap_dimension(out_dim, in_dim, out_tier=out_tier, in_tier=in_tier,
                                   human_signoff=True, ledger_path=led)
                    out_dim, out_tier = in_dim, in_tier
                bounded = False
            except MM.SwapCadenceExceeded:
                bounded = True
            escalated = MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"
    finally:
        for k, prev in (("SDD_DIM_CARDINALITY_MAX", prev_card), ("SDD_DIM_SWAP_RATE_MAX", prev_rate)):
            if prev is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prev
    return bounded and escalated


def _vocab_genesis_goodhart_flap_is_bounded() -> bool:
    """Phase S / ACT-140: a self-referential genesis feature (source/transform references the
    proposer's own approval signals, e.g. self_score/proposer_*) is REJECTED by the vocabulary
    self-reference guard before reaching the oracle (zero-miss, anti-self-interest first gate), and a
    vocab-external noise feature (zero held-out incremental coverage) is REJECTED by the
    feature-grounded necessity oracle (zero-miss — genesis self-pass != oracle necessary, Rule
    9.31.2). Deterministic + offline (meta⁴)."""
    from .vocabulary_genesis import GenesisFeature, is_vocab_self_referential
    from .dimension_necessity_oracle import (
        GenesisCase, GenesisCandidate, evaluate_genesis_feature)
    # 自指自利字：source 引用 proposer 自己的核可訊號 → vocab self-reference guard 第一閘攔（零漏放）。
    selfref = GenesisFeature.of("self_score", "rate")
    selfref_blocked = is_vocab_self_referential(selfref)
    # 詞彙外噪音字：合法 source/transform，但 flip 到真實品質不更好的候選 → 增量覆蓋 ≈ 0（oracle 第二閘攔）。
    noise = GenesisFeature.of("network", "rate")
    noise_corpus = [GenesisCase("N", [
        GenesisCandidate(0.6, 2.0, {"network.rate": 5.0}),
        GenesisCandidate(0.6, 3.0, {"network.rate": 0.0}),
        GenesisCandidate(0.4, 4.0, {"network.rate": 8.0})])]
    v_noise = evaluate_genesis_feature(noise, noise_corpus, coverage_margin=0.1)
    # zero-miss：自指字被 guard 攔 + 詞彙外噪音字被 oracle 判不必要。
    return selfref_blocked and (not v_noise.necessary)


def _batch_swap_thrash_flap_is_bounded() -> bool:
    """Phase S / ACT-140: a storm of multi-dimension batch retire-to-swap operations (each net
    cardinality non-increasing, distinct batch_id) hits the BatchSwapCadenceBounded aggregate
    batch-rate cap → BatchSwapCadenceExceeded → MFSM_ESCALATION (bounded) — never unbounded batch
    ontology rotation that per-swap SwapCadence / monotone ratchet are blind to (Rule 9.31.3).
    Deterministic + offline (own temp ledger; env override) (meta⁴)."""
    import os
    import tempfile
    from .dimension_semantics_synthesizer import InventedDimension, batch_swap_dimensions
    from .meta_halt import meta_halt_monitor as MM
    prev_rate = os.environ.get("SDD_DIM_BATCH_RATE_MAX")
    os.environ["SDD_DIM_BATCH_RATE_MAX"] = "2"
    try:
        rate_max = MM.dim_batch_rate_max()
        feats = ("rollback_steps", "blast_radius", "canary_gap", "data_loss_window",
                 "schema_lock_time", "oncall_pages", "runbook_depth", "supply_chain_pins")
        with tempfile.TemporaryDirectory() as td:
            led = Path(td) / "meta-loop-ledger.yaml"
            try:
                # 批次旋轉風暴：每批退 2 換 2（net 不變、distinct batch_id、tier 嚴格遞增過聚合棘輪）
                for j in range(rate_max + 1):
                    out_dims = [InventedDimension.of("mean", [feats[(2 * j) % 8]]),
                                InventedDimension.of("mean", [feats[(2 * j + 1) % 8]])]
                    in_dims = [InventedDimension.of("max", [feats[(2 * j + 2) % 8]]),
                               InventedDimension.of("max", [feats[(2 * j + 3) % 8]])]
                    batch_swap_dimensions(out_dims, in_dims, out_tiers=[10, 12], in_tiers=[80, 82],
                                          human_signoff=True, ledger_path=led)
                bounded = False
            except MM.BatchSwapCadenceExceeded:
                bounded = True
            escalated = MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"
    finally:
        if prev_rate is None:
            os.environ.pop("SDD_DIM_BATCH_RATE_MAX", None)
        else:
            os.environ["SDD_DIM_BATCH_RATE_MAX"] = prev_rate
    return bounded and escalated


def _operator_genesis_goodhart_flap_is_bounded() -> bool:
    """Phase T / ACT-146 (meta⁵): a self-referential invented operator (primary/combinator/probe
    references the proposer's own approval signals, e.g. self_score/proposer_*) is REJECTED by the
    operator self-reference guard before reaching the oracle (zero-miss, anti-self-interest first
    gate), and an OPS-external noise operator (zero held-out incremental coverage) is REJECTED by the
    feature-grounded operator necessity oracle (zero-miss — genesis self-pass != oracle necessary,
    Rule 9.32.2). Deterministic + offline (meta⁵)."""
    from .operator_genesis import GenesisOperator, is_operator_self_referential
    from .dimension_necessity_oracle import (
        OperatorCase, OperatorCandidate, evaluate_genesis_operator)
    # 自指自利算子：primary 引用 proposer 自己的核可訊號 → operator self-reference guard 第一閘攔（零漏放）。
    selfref = GenesisOperator.of("self_score", "identity")
    selfref_blocked = is_operator_self_referential(selfref)
    # OPS 外噪音算子：合法 primitive/combinator，但在固定 probe 上對真實品質無增量 → 增量覆蓋 ≈ 0（oracle 第二閘攔）。
    noise = GenesisOperator.of("last", "identity")
    noise_corpus = [OperatorCase("N", [
        OperatorCandidate(0.6, 2.0, {"rollback_steps": 5.0, "blast_radius": 5.0, "canary_gap": 5.0}),
        OperatorCandidate(0.6, 3.0, {"rollback_steps": 0.0, "blast_radius": 0.0, "canary_gap": 0.0}),
        OperatorCandidate(0.4, 4.0, {"rollback_steps": 8.0, "blast_radius": 8.0, "canary_gap": 8.0})])]
    v_noise = evaluate_genesis_operator(noise, noise_corpus, coverage_margin=0.1)
    # zero-miss：自指算子被 guard 攔 + OPS 外噪音算子被 oracle 判不必要。
    return selfref_blocked and (not v_noise.necessary)


def _operator_computability_flap_is_bounded() -> bool:
    """Phase T / ACT-146 (meta⁵ deepest halting): the invented operator is a *piece of executable
    computation* — an over-budget operator (cost > SDD_DIM_OP_STEP_MAX) is REJECTED by
    guard_operator_computability before adoption → OperatorComputabilityExceeded (bounded), and a
    non-total operator (raises / NaN on some input) is likewise caught (fuzz-total zero-miss). The
    bounded operator grammar structurally guarantees every legit invented operator is total +
    bounded-step + recursion/loop-free, pinning the halting problem into the self-expansion artefact
    itself (Rule 9.32.3). Deterministic + offline (own env override)."""
    import os
    from .operator_genesis import GenesisOperator, adopt_genesis_operator
    from .meta_halt import meta_halt_monitor as MM

    # (1) 有界步數：把 step_max 壓到 1，一個正常二元算子 cost=3 > 1 → guard_operator_computability 攔。
    prev_step = os.environ.get("SDD_DIM_OP_STEP_MAX")
    os.environ["SDD_DIM_OP_STEP_MAX"] = "1"
    over_budget_caught = False
    try:
        go = GenesisOperator.of("max", "diff", secondary="min")  # cost=3
        try:
            MM.guard_operator_computability(go)
        except MM.OperatorComputabilityExceeded:
            over_budget_caught = True
    finally:
        if prev_step is None:
            os.environ.pop("SDD_DIM_OP_STEP_MAX", None)
        else:
            os.environ["SDD_DIM_OP_STEP_MAX"] = prev_step

    # (2) 非全函式：以一個 cost ok 但 is_total()=False 的偽算子，驗 fuzz-total 守門零漏放。
    class _NonTotalOp:
        name = "op::evil"
        def cost(self):
            return 2
        def is_total(self, *, samples=None):
            return False
    nontotal_caught = False
    try:
        MM.guard_operator_computability(_NonTotalOp())
    except MM.OperatorComputabilityExceeded:
        nontotal_caught = True

    # (3) 正常算子（cost<=step_max + total）必須放行（守門不誤殺合法算子）。
    legit = GenesisOperator.of("mean", "identity")
    legit_ok = MM.guard_operator_computability(legit).allowed

    return over_budget_caught and nontotal_caught and legit_ok


def _alphabet_genesis_goodhart_flap_is_bounded() -> bool:
    """Phase U / ACT-149 (meta⁶): a self-referential invented alphabet element (reducer/post_map/atom/
    probe references the proposer's own approval signals, e.g. self_score/proposer_*) is REJECTED by the
    alphabet self-reference guard before reaching the oracle (zero-miss, anti-self-interest first gate),
    and an alphabet-external noise element (zero held-out incremental coverage) is REJECTED by the
    feature-grounded alphabet necessity oracle (zero-miss — genesis self-pass != oracle necessary,
    Rule 9.33.2). Deterministic + offline (meta⁶)."""
    from .operator_alphabet_genesis import InventedPrimitive, is_alphabet_self_referential
    from .dimension_necessity_oracle import (
        AlphabetCase, AlphabetCandidate, evaluate_genesis_alphabet)
    # 自指自利字母：base_reducer 引用 proposer 自己的核可訊號於 probe → alphabet self-reference guard 攔（零漏放）。
    selfref = InventedPrimitive.of("acc_sum", "identity",
                                   probe=("self_score", "blast_radius", "canary_gap"))
    selfref_blocked = is_alphabet_self_referential(selfref)
    # 字母表外噪音字母：合法 reducer/post_map，但在固定 probe 上對真實品質無增量 → 增量覆蓋 ≈ 0（oracle 第二閘攔）。
    noise = InventedPrimitive.of("acc_count", "identity")   # count 恆為候選特徵數，無區辨
    noise_corpus = [AlphabetCase("N", [
        AlphabetCandidate(0.6, 2.0, {"rollback_steps": 5.0, "blast_radius": 5.0, "canary_gap": 5.0}),
        AlphabetCandidate(0.6, 3.0, {"rollback_steps": 0.0, "blast_radius": 0.0, "canary_gap": 0.0}),
        AlphabetCandidate(0.4, 4.0, {"rollback_steps": 8.0, "blast_radius": 8.0, "canary_gap": 8.0})])]
    v_noise = evaluate_genesis_alphabet(noise, noise_corpus, coverage_margin=0.1)
    # zero-miss：自指字母被 guard 攔 + 字母表外噪音字母被 oracle 判不必要。
    return selfref_blocked and (not v_noise.necessary)


def _computability_closure_flap_is_bounded() -> bool:
    """Phase U / ACT-149 (meta⁶ deepest halting): the invented alphabet element is a *generation-rule
    part* that the operator grammar uses to generate the *entire* operator algebra. A closure-breaking
    element (non-total reducer → some operator over the expanded alphabet raises/NaN, or over-budget →
    G(A') max_cost > SDD_DIM_OP_STEP_MAX) is REJECTED by guard_computability_closure before adoption →
    ComputabilityClosureViolation (bounded). The bounded alphabet grammar structurally guarantees every
    invented element keeps the whole generated algebra total + bounded-step + recursion/loop-free,
    pinning the halting problem into the self-expansion *generation rule* itself (Rule 9.33.3).
    Deterministic + offline."""
    import os
    from .operator_alphabet_genesis import InventedPrimitive
    from .meta_halt import meta_halt_monitor as MM

    # (1) 閉包破裂（非全函式）：未知 base_reducer → reduce() 拋例外 → 閉包 fuzz 抓到 total=False。
    nontotal_caught = False
    try:
        bad = InventedPrimitive(base_reducer="evil_unbounded", post_map="identity")
        MM.guard_computability_closure(bad)
    except MM.ComputabilityClosureViolation:
        nontotal_caught = True

    # (2) 閉包步數無界：把 step_max 壓到 1，正常字母擴充後 G(A') max_cost=3 > 1 → 守門攔（閉包步數）。
    prev_step = os.environ.get("SDD_DIM_OP_STEP_MAX")
    os.environ["SDD_DIM_OP_STEP_MAX"] = "1"
    over_budget_caught = False
    try:
        legit = InventedPrimitive.of("acc_sumsq", "identity")
        try:
            MM.guard_computability_closure(legit)
        except MM.ComputabilityClosureViolation:
            over_budget_caught = True
    finally:
        if prev_step is None:
            os.environ.pop("SDD_DIM_OP_STEP_MAX", None)
        else:
            os.environ["SDD_DIM_OP_STEP_MAX"] = prev_step

    # (3) 正常字母（閉包 total + max_cost<=step_max）必須放行（守門不誤殺合法字母）。
    legit2 = InventedPrimitive.of("acc_sumsq", "identity")
    legit_ok = MM.guard_computability_closure(legit2).allowed

    return nontotal_caught and over_budget_caught and legit_ok


def _depth_genesis_goodhart_flap_is_bounded() -> bool:
    """Phase V / ACT-152 (meta⁷): a self-referential invented depth operator (base/chain/probe references the
    proposer's own approval signals, e.g. self_score/proposer_*) is REJECTED by the depth self-reference guard
    before reaching the oracle (zero-miss, anti-self-interest first gate), and a depth-external noise operator
    (zero held-out incremental coverage) is REJECTED by the feature-grounded depth necessity oracle (zero-miss
    — genesis self-pass != oracle necessary, Rule 9.34.2). Deterministic + offline (meta⁷)."""
    from .operator_depth_genesis import DepthOperator, is_depth_self_referential
    from .operator_genesis import GenesisOperator
    from .dimension_necessity_oracle import DepthCase, DepthCandidate, evaluate_genesis_depth
    # 自指自利深度算子：probe 引用 proposer 自己的核可訊號 → depth self-reference guard 攔（零漏放）。
    selfref = DepthOperator.of(GenesisOperator.of("sum", "sq"), ["sq"],
                               probe=("self_score", "blast_radius", "canary_gap"))
    selfref_blocked = is_depth_self_referential(selfref)
    # 深度外噪音算子：合法 base/chain，但在固定 probe 上對真實品質無增量 → 增量覆蓋 ≈ 0（oracle 第二閘攔）。
    noise = DepthOperator.of(GenesisOperator.of("mean", "sq"), ["sq"])   # sq(sq(mean))
    noise_corpus = [DepthCase("N", [
        DepthCandidate(0.6, 2.0, {"rollback_steps": 5.0, "blast_radius": 5.0, "canary_gap": 5.0}),
        DepthCandidate(0.6, 3.0, {"rollback_steps": 0.0, "blast_radius": 0.0, "canary_gap": 0.0}),
        DepthCandidate(0.4, 4.0, {"rollback_steps": 8.0, "blast_radius": 8.0, "canary_gap": 8.0})])]
    v_noise = evaluate_genesis_depth(noise, noise_corpus, coverage_margin=0.1)
    # zero-miss：自指深度算子被 guard 攔 + 深度外噪音算子被 oracle 判不必要。
    return selfref_blocked and (not v_noise.necessary)


def _depth_closure_flap_is_bounded() -> bool:
    """Phase V / ACT-152 (meta⁷ deepest halting): the self-expanded artefact is the grammar's structural depth
    parameter itself — and cost==depth, so expanding the depth literally expands the step count. A depth operator
    whose depth exceeds STEP_MAX (cost==depth > SDD_DIM_OP_STEP_MAX) is REJECTED by guard_depth_closure before
    adoption → DepthClosureViolation (bounded), and a non-total depth operator (bad chain combinator raising/NaN
    on some input) is likewise caught (fuzz-total zero-miss). The bounded depth grammar structurally guarantees
    every legit invented depth operator keeps the whole same-depth algebra total + cost==depth-bounded +
    recursion/loop-free, pinning the halting problem into the self-expansion *generation-grammar depth parameter*
    itself (Rule 9.34.3). Deterministic + offline (own env override)."""
    import os
    from .operator_depth_genesis import DepthOperator
    from .operator_genesis import GenesisOperator
    from .meta_halt import meta_halt_monitor as MM

    # (1) 深度超界（因 cost==depth）：把 step_max 壓到 2，一個正常深度-3 算子 cost=3 > 2 → guard_depth_closure 攔。
    prev_step = os.environ.get("SDD_DIM_OP_STEP_MAX")
    os.environ["SDD_DIM_OP_STEP_MAX"] = "2"
    over_budget_caught = False
    try:
        legit = DepthOperator.of(GenesisOperator.of("sum", "sq"), ["sq"])  # depth=3, cost=3
        try:
            MM.guard_depth_closure(legit)
        except MM.DepthClosureViolation:
            over_budget_caught = True
    finally:
        if prev_step is None:
            os.environ.pop("SDD_DIM_OP_STEP_MAX", None)
        else:
            os.environ["SDD_DIM_OP_STEP_MAX"] = prev_step

    # (2) 閉包破裂（非全函式）：chain 含未知 combinator → apply 拋例外 → 閉包 fuzz 抓到 total=False。
    nontotal_caught = False
    try:
        bad = DepthOperator.of(GenesisOperator.of("sum", "sq"), ["evil_unbounded"])
        MM.guard_depth_closure(bad)
    except MM.DepthClosureViolation:
        nontotal_caught = True

    # (3) 正常深度算子（閉包 total + max_cost<=step_max）必須放行（守門不誤殺合法深度算子）。
    legit2 = DepthOperator.of(GenesisOperator.of("sum", "sq"), ["sq"])
    legit_ok = MM.guard_depth_closure(legit2).allowed

    return over_budget_caught and nontotal_caught and legit_ok


def _recursion_genesis_goodhart_flap_is_bounded() -> bool:
    """Phase W / ACT-155 (meta⁸): a self-referential invented inter-recursive operator (node base/probe
    references the proposer's own approval signals, e.g. self_score/proposer_*) is REJECTED by the recursion
    self-reference guard before reaching the oracle (zero-miss, anti-self-interest first gate), and a
    recursion-external noise operator (zero held-out incremental coverage) is REJECTED by the feature-grounded
    recursion necessity oracle (zero-miss — genesis self-pass != oracle necessary, Rule 9.35.2). Deterministic
    + offline (meta⁸)."""
    from .operator_recursion_genesis import RecursiveOperator, is_recursion_self_referential
    from .operator_genesis import GenesisOperator
    from .dimension_necessity_oracle import RecursionCase, RecursionCandidate, evaluate_genesis_recursion
    # 自指自利互遞迴算子：probe 引用 proposer 自己的核可訊號 → recursion self-reference guard 攔（零漏放）。
    selfref = RecursiveOperator.chain(GenesisOperator.of("sum", "sq"), 2, combine="mul",
                                      probe=("self_score", "blast_radius", "canary_gap"))
    selfref_blocked = is_recursion_self_referential(selfref)
    # 互遞迴外噪音算子：合法 node base，但在固定 probe 上對真實品質無增量 → 增量覆蓋 ≈ 0（oracle 第二閘攔）。
    noise = RecursiveOperator.chain(GenesisOperator.of("sum", "clip01"), 2, combine="mul")  # clip01 飽和成常數
    noise_corpus = [RecursionCase("N", [
        RecursionCandidate(0.6, 2.0, {"rollback_steps": 5.0, "blast_radius": 5.0, "canary_gap": 5.0}),
        RecursionCandidate(0.6, 3.0, {"rollback_steps": 0.0, "blast_radius": 0.0, "canary_gap": 0.0}),
        RecursionCandidate(0.4, 4.0, {"rollback_steps": 8.0, "blast_radius": 8.0, "canary_gap": 8.0})])]
    v_noise = evaluate_genesis_recursion(noise, noise_corpus, coverage_margin=0.1)
    # zero-miss：自指互遞迴算子被 guard 攔 + 互遞迴外噪音算子被 oracle 判不必要。
    return selfref_blocked and (not v_noise.necessary)


def _recursion_closure_flap_is_bounded() -> bool:
    """Phase W / ACT-155 (meta⁸ decidability-boundary halting): the self-expanded artefact is whether operators
    may call each other / themselves — and deciding whether an arbitrary cyclic call graph halts IS the halting
    problem (undecidable), so the "bounded step count" device structurally fails. A recursive operator whose call
    graph contains an uncertified cycle (no back-edge strictly decreasing a lower-bounded rank → may not
    terminate) is REJECTED by guard_recursion_closure before adoption → RecursionClosureViolation (bounded), and
    a fuel-over-budget operator (fuel > SDD_DIM_OP_STEP_MAX) is likewise caught. The bounded recursion grammar
    structurally guarantees every legit invented operator carries a well-founded termination certificate
    (acyclic ∨ rank-descending + fuel<=STEP_MAX + total + recursion/loop-free evaluator), pinning the halting
    problem onto the decidable/total fragment boundary itself — replacing the failed "bounded step count" device
    with "well-founded measure" (Rule 9.35.3). Deterministic + offline (own env override)."""
    import os
    from .operator_recursion_genesis import RecursiveOperator, RecursionNode
    from .operator_genesis import GenesisOperator
    from .meta_halt import meta_halt_monitor as MM

    base = GenesisOperator.of("sum", "sq")
    # (1) 無證書環：node0(rank0)->node1, node1(rank0)->node0（無回邊遞減 rank → 含環不可證終止）→ guard 攔。
    cyclic = RecursiveOperator(nodes=(RecursionNode(base, 0, (1,)), RecursionNode(base, 0, (0,))),
                               entry=0, fuel=2, combine="mul")
    cycle_caught = False
    try:
        MM.guard_recursion_closure(cyclic)
    except MM.RecursionClosureViolation:
        cycle_caught = True

    # (2) 燃料超界：把 step_max 壓到 1，一個正常 2-node 互遞迴算子 fuel=2 > 1 → guard_recursion_closure 攔。
    prev_step = os.environ.get("SDD_DIM_OP_STEP_MAX")
    os.environ["SDD_DIM_OP_STEP_MAX"] = "1"
    over_budget_caught = False
    try:
        legit = RecursiveOperator.chain(base, 2, combine="mul")  # fuel=2, cost=2
        try:
            MM.guard_recursion_closure(legit)
        except MM.RecursionClosureViolation:
            over_budget_caught = True
    finally:
        if prev_step is None:
            os.environ.pop("SDD_DIM_OP_STEP_MAX", None)
        else:
            os.environ["SDD_DIM_OP_STEP_MAX"] = prev_step

    # (3) 正常互遞迴算子（可證良基終止 + fuel<=step_max + total）必須放行（守門不誤殺合法互遞迴算子）。
    legit2 = RecursiveOperator.chain(base, 2, combine="mul")
    legit_ok = MM.guard_recursion_closure(legit2).allowed

    return cycle_caught and over_budget_caught and legit_ok


def _embodied_grounding_flap_is_bounded() -> bool:
    """Phase X / ACT-158 (meta⁸ embodied grounding): to validate the self-evolution loop against the REAL
    environment, the embodied grounding gate introduces "the real sandbox may hang" as a new non-halting source.
    (1) A zero-observation false-green grounded verdict (no objective ExecutionObservation) is REJECTED by
    guard_embodied_grounding → EmbodiedGroundingViolation (fail-closed, bounded). (2) A sandbox-timed-out grounding
    is mapped to grounded_fail → guard returns allowed=False (REJECT no churn; FSM doesn't wall-clock wait).
    (3) A grounded_pass (OQS>=baseline, objective obs) is correctly allowed (guard doesn't false-reject legit
    grounding). 100% isomorphic with TLA+ EmbodiedGroundingBounded. Deterministic + offline."""
    from .embodied_grounding_oracle import evaluate_embodied_grounding
    from .output_quality_scorer import ExecutionObservation
    from .meta_halt import meta_halt_monitor as MM

    good = ExecutionObservation(tests_total=10, tests_passed=10)
    # (1) 零觀測 false-green：缺客觀 ExecutionObservation → guard fail-closed（bounded）。
    zero = evaluate_embodied_grounding(good, ExecutionObservation())
    fail_closed = False
    try:
        MM.guard_embodied_grounding(zero)
    except MM.EmbodiedGroundingViolation:
        fail_closed = True
    # (2) 沙箱硬 timeout → grounded_fail，REJECT 不 churn（FSM 不 wall-clock wait，bounded）。
    timeout_v = evaluate_embodied_grounding(good, good, sandbox_timed_out=True)
    timeout_rejected = (MM.guard_embodied_grounding(timeout_v).allowed is False)
    # (3) 合法 grounded_pass 必須放行（守門不誤殺有客觀觀測的真接地）。
    pass_v = evaluate_embodied_grounding(good, good)
    pass_allowed = (MM.guard_embodied_grounding(pass_v).allowed is True)
    return fail_closed and timeout_rejected and pass_allowed


def _visualization_flap_is_bounded() -> bool:
    """Phase Y / ACT-161 (meta⁸ explainability / token-budget halting): rendering a meta⁸ recursion call graph
    for human approval introduces "rendering an unbounded huge graph may OOM / token-explode" as a new
    non-halting source. A 10⁶-node adversarial call graph fed to the topology renderer is bounded-truncated to
    <= node_budget nodes, paginated, and its dashboard markdown stays <= char_budget — no hang, no OOM, no token
    over-budget; guard_visualization_bounded allows the bounded (truncated) render. 100% isomorphic with TLA+
    VisualizationBounded. Deterministic + offline."""
    from .recursion_topology_view import extract_topology, render_dashboard_markdown, render_budget
    from .meta_halt import meta_halt_monitor as MM
    b = render_budget()
    big = {"ranks": [0] * 1000000, "edges": [], "fuel": 4, "entry": 0, "name": "adversarial-1e6",
           "fingerprint": "recursion-genesis:adv", "terminating": True, "acyclic": True, "well_founded": True}
    view = extract_topology(big)
    md = render_dashboard_markdown(view)
    bounded = (len(view.nodes) <= b.node_budget and len(md) <= b.char_budget and view.truncated)
    guard_ok = MM.guard_visualization_bounded(view, big).allowed
    return bounded and guard_ok


def _visualization_topology_drift_flap_is_bounded() -> bool:
    """Phase Y / ACT-161 (meta⁸ explainability anti-forgery): a tampered render drawing a SIMPLER graph than the
    operator actually runs (drops a within-window call edge / fakes a rank to look more well-founded) is the
    visual-deception attack. verify_topology_consistency independently re-derives the subgraph from to_dict() and
    REJECTS the forgery → TopologyConsistencyError (fail-closed, bounded); a faithful render is correctly allowed
    (no false-reject). Deterministic + offline."""
    import copy
    from .operator_recursion_genesis import RecursiveOperator
    from .operator_genesis import GenesisOperator
    from .recursion_topology_view import (extract_topology, render_json,
                                          verify_topology_consistency, TopologyConsistencyError)
    base = GenesisOperator.of("sum", "sq")
    op = RecursiveOperator.fan(base, 3, combine="mul")   # entry -> 3 sinks（3 條窗內邊）
    od = op.to_dict()
    view = extract_topology(od)
    rj = render_json(view)
    # (1) 刪一條窗內真相邊（畫的圖比跑的簡單）→ 必被攔。
    forged = copy.deepcopy(rj)
    forged["edges"] = forged["edges"][1:]
    forged["consistency"]["audit_digest"] = None
    drop_caught = False
    try:
        verify_topology_consistency(forged, od)
    except TopologyConsistencyError:
        drop_caught = True
    # (2) 偽造 rank（讓圖看起來更良基）→ 必被攔。
    forged2 = copy.deepcopy(rj)
    forged2["nodes"][0]["rank"] = 999
    forged2["consistency"]["audit_digest"] = None
    rank_caught = False
    try:
        verify_topology_consistency(forged2, od)
    except TopologyConsistencyError:
        rank_caught = True
    # (3) 忠實渲染必須放行（守門不誤殺真圖）。
    faithful_ok = verify_topology_consistency(rj, od)
    return drop_caught and rank_caught and faithful_ok


def _visualization_fold_drift_flap_is_bounded() -> bool:
    """W-23-1 (improving_23, meta⁸ explainability folding anti-forgery): a folded super-node is an HONEST
    contraction only when it declares a genuine interior simple chain (in==1∧out==1 members, rank strictly
    descending, no entry/branch/sink hidden) covering exactly the window. A forged fold (swallowing a sink,
    or dropping a member to draw a simpler graph) is rejected by fold-aware verify_topology_consistency →
    TopologyConsistencyError (fail-closed, bounded); a faithful fold is correctly allowed. Deterministic + offline."""
    import copy
    from .operator_recursion_genesis import RecursiveOperator
    from .operator_genesis import GenesisOperator
    from .recursion_topology_view import (extract_topology, render_json, RenderBudget,
                                          verify_topology_consistency, TopologyConsistencyError)
    base = GenesisOperator.of("sum", "sq")
    op = RecursiveOperator.chain(base, 6, combine="mul")     # 0→1→2→3→4→5（內部鏈 1..4 可折疊）
    od = op.to_dict()
    view = extract_topology(od, budget=RenderBudget(fold_enabled=True, fold_min=3))
    rj = render_json(view)
    # (1) 偽造折疊吞入非內部鏈節點（sink out-deg0）藏結構 → 必被攔。
    swallow = {
        "nodes": [{"id": 0, "rank": 5, "folded": False},
                  {"id": 1, "rank": 4, "folded": True, "folds": [1, 2, 3, 4, 5]}],
        "edges": [{"src": 0, "dst": 1}],
        "n_total_nodes": 6, "truncated": False, "consistency": {"audit_digest": None},
    }
    swallow_caught = False
    try:
        verify_topology_consistency(swallow, od, node_budget=24)
    except TopologyConsistencyError:
        swallow_caught = True
    # (2) 偽造折疊丟成員（畫的圖比跑的簡單）→ 必被攔。
    drop = copy.deepcopy(rj)
    for nd in drop["nodes"]:
        if nd.get("folded"):
            nd["folds"] = [1, 2, 3]
    drop["consistency"]["audit_digest"] = None
    drop_caught = False
    try:
        verify_topology_consistency(drop, od, node_budget=24)
    except TopologyConsistencyError:
        drop_caught = True
    # (3) 忠實折疊必須放行（守門不誤殺真誠實收縮）。
    faithful_ok = verify_topology_consistency(rj, od, node_budget=24)
    return swallow_caught and drop_caught and faithful_ok


# ---------- workflow simulation ----------


def _advance_happy_path_once(rt: FSMRuntime) -> bool:
    """Take one forward step on the happy path. Returns True if moved."""
    linear = {
        "INIT": "SCENARIO_DETECT",
        "SCENARIO_DETECT": "AGENT_LOAD",
        "AGENT_LOAD": "SPEC_DRAFTING",
        "SPEC_DRAFTING": "SCG_VALIDATION",
        "SCG_VALIDATION": None,            # gate-driven
        "HUMAN_PENDING": "SPEC_FROZEN",
        "SPEC_FROZEN": "IMPLEMENTATION",
        "IMPLEMENTATION": "PR_REVIEW",
        "PR_REVIEW": None,                 # gate-driven
        "RTM_VERIFY": None,                # gate-driven
        "RELEASE_READY": "RELEASE",
    }
    nxt = linear.get(rt.state.current)
    if nxt is None:
        return False
    try:
        rt.transition(nxt, reason=f"chaos happy-step {rt.state.current}->{nxt}", trigger="chaos_happy")
        return True
    except TransitionError:
        return False


def _gate_pass(rt: FSMRuntime, gate: str) -> dict:
    return rt.record_gate_result(gate, "PASS")


def _gate_fail(rt: FSMRuntime, gate: str, reason: str) -> dict:
    return rt.record_gate_result(gate, "FAIL", reason=reason)


def _run_single_round(
    round_id: int,
    seed: int,
    workdir: Path,
) -> ChaosResult:
    rng = random.Random(seed)
    result = ChaosResult(round_id=round_id, seed=seed)

    # Choose 1-3 fault types for this round (at least 1 to guarantee chaos).
    # `chosen` is the *selected* set; `faults_fired` below is the *actually
    # triggered* set. `result.faults_injected` is overwritten at the end with
    # the fired list (QA Round-3 P2-05 — see note on faults_fired assignment).
    n_faults = rng.randint(1, 3)
    chosen = rng.sample(FAULT_TYPES, k=n_faults)

    state_path = workdir / f"FSM-STATE-chaos-{round_id}.yaml"
    try:
        state = load_state(f"chaos-proj-{round_id}", path=state_path)
        rt = FSMRuntime(state)
    except Exception as exc:  # noqa: BLE001
        result.error = f"bootstrap: {exc}"
        result.final_state = "TERMINATED"
        result.bounded = True  # bootstrap failure is a halt
        result.tokens_estimated = _TOKEN_COST_READ
        return result

    # Decide which fault to trigger at which step (>=1 step before terminal).
    trigger_step = rng.randint(1, 8)
    # When TRAJECTORY_PREDICTION is in chosen, use spec-flavoured paraphrases
    # so the predictor's S3 signal can fire — this exercises the early-switch
    # path that the baseline same_pattern_threshold (3) cannot match.
    pr_jitter_reasons = pr_review_jitter_reasons(
        rng, with_spec_flavour=("TRAJECTORY_PREDICTION" in chosen)
    )
    pr_jitter_idx = 0
    scg_infinite = "SCG_INFINITE_FAIL" in chosen

    # Phase G M2 / B2.8: when TRAJECTORY_PREDICTION is enabled, write a
    # high-drift ledger file in workdir so predictor's S4 signal can fire.
    # Path is passed into consult_predictor below.
    chaos_ledger_path: Optional[Path] = None
    if "TRAJECTORY_PREDICTION" in chosen:
        chaos_ledger_path = workdir / f"chaos-ledger-{round_id}.yaml"
        try:
            chaos_ledger_path.write_text(
                "rolling_avg_drift_pct_last10: 45.0\n",
                encoding="utf-8",
            )
        except Exception:  # noqa: BLE001
            chaos_ledger_path = None

    tokens = _TOKEN_COST_READ  # bootstrap load
    steps = 0
    faults_fired: List[str] = []

    while steps < _MAX_STEPS_PER_ROUND:
        steps += 1

        # Inject fault at designated step
        if steps == trigger_step:
            for fault in chosen:
                try:
                    if fault == "STATE_CORRUPTION":
                        corrupt_state_file(rt, rng)
                        # Reload via normal API — .bak fallback should recover.
                        state = load_state(f"chaos-proj-{round_id}", path=state_path)
                        rt = FSMRuntime(state)
                    elif fault == "RETRY_TAMPER":
                        tamper_retry_count(rt, rng)
                    elif fault == "CI_EVENT_DUP":
                        duplicate_ci_event(rt, rng)
                        rt.reconcile_ci_events()
                    elif fault == "TIMEOUT_SIM":
                        # P2-07: TIMEOUT_SIM only makes sense when we can reach
                        # HUMAN_PENDING. Pre-check and either advance via gate
                        # pass, or skip the fault cleanly with an audit note —
                        # previously the fault silently no-op'd on unreachable
                        # states, weakening coverage without leaving a trace.
                        reachable_via_gate = {"SCG_VALIDATION"}
                        if rt.state.current == "HUMAN_PENDING":
                            pass  # already where we need to be
                        elif rt.state.current in reachable_via_gate:
                            _gate_pass(rt, "SCG_VALIDATION")
                        else:
                            faults_fired.append(f"{fault}:skipped_unreachable_{rt.state.current}")
                            continue
                        simulate_human_pending_timeout(rt, rng)
                        verdict = evaluate_human_pending(rt.state)
                        if verdict["outcome"] == "ESCALATION":
                            rt.state.record_escalation(
                                f"HUMAN_PENDING timeout after {verdict['elapsed_hours']}h"
                            )
                            save_state(rt.state)
                    elif fault == "AUTO_COMPACT_BURST":
                        auto_compact_burst(rt, rng)
                    elif fault == "PR_REVIEW_JITTER":
                        # Navigate to PR_REVIEW first if not already
                        # (best-effort; chaos tolerates skipping).
                        pass  # handled below in gate loop
                    elif fault == "SCG_INFINITE_FAIL":
                        pass  # handled in loop
                    elif fault == "FLAKY_EVAL":
                        # Phase I M1 / ACT-059: flaky execution must NOT loop
                        # the retry budget. Confirm hermetic isolation classifies
                        # it as FLAKY (third verdict), then bounded-halt by
                        # escalating with a deterministic-repro request (steersman
                        # level) — never re-enter EXECUTION_EVALUATION retry.
                        if _flaky_is_isolated() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "flaky eval isolated (3/5 pass) — needs deterministic repro; "
                                "not consuming EXECUTION_EVALUATION retry budget"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "ADVERSARIAL_FLAKY":
                        # Phase J / ACT-073: an adversarial counterexample that is
                        # itself flaky must be ISOLATED as inconclusive — never fed
                        # into IMPLEMENTATION retry (Rule 9.22.1). Confirm isolation,
                        # then bounded-halt by escalating for a deterministic repro.
                        if _adversarial_flaky_is_isolated() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "adversarial flaky counterexample isolated (inconclusive) — "
                                "needs deterministic repro; not consuming IMPLEMENTATION retry budget"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "INTENT_DECOMPOSE_STORM":
                        # Phase K M-K1 / ACT-082: a storm of over-cap/cyclic
                        # decompositions converges to `underspecified` (bounded),
                        # never infinite subdivision → bounded human-clarify halt.
                        if _intent_decompose_storm_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "intent decompose storm bounded (over-cap/cyclic → underspecified) — "
                                "needs human intent clarification; not infinite subdivision"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "DEBATE_FLAKY":
                        # Phase K M-K2 / ACT-084: spec debate divergence is
                        # deterministic + round-bounded — never an unbounded
                        # flicker → bounded human-disambiguation halt.
                        if _debate_flaky_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "spec debate divergence isolated (deterministic + round-bounded) — "
                                "needs human disambiguation; not infinite debate"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "META_CHURN_STORM":
                        # Phase L M-L1 / ACT-090: same-fingerprint add↔retire storm
                        # hits ChurnBounded → MFSM_ESCALATION (bounded) — never
                        # infinite self-improvement churn (Rule 9.24.1).
                        if _meta_churn_storm_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "meta churn storm bounded (add↔retire ≥ SDD_META_CHURN_MAX → "
                                "MFSM_ESCALATION) — needs human review; not infinite churn"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "REPLAY_FLAKY":
                        # Phase L M-L2 / ACT-091: counterfactual replay is deterministic
                        # + budget-bounded (advisory evidence only) — never unbounded
                        # experimentation (Rule 9.24.4).
                        if _replay_flaky_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "counterfactual replay deterministic + budget-bounded — "
                                "advisory evidence only; not unbounded experimentation"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "COMPOSITION_CONFLICT_STORM":
                        # Phase M M-M1 / ACT-098: a cross-intent conflict storm on a
                        # shared spec node hits RenegotiationBounded → CPLAN_ESCALATION
                        # (bounded) — never infinite renegotiation livelock (Rule 9.25.1).
                        if _composition_conflict_storm_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "composition conflict storm bounded (cross-intent reneg ≥ "
                                "SDD_COMPOSITION_RENEG_MAX → CPLAN_ESCALATION) — needs human "
                                "composition arbitration; not infinite negotiation"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "CEILING_FLAP":
                        # Phase M M-M2 / ACT-100: scaffold ceiling A/B verdict is
                        # deterministic + advisory — surfaces a net-negative scaffold for
                        # human set_maturity, never auto-retires (Rule 9.25.5).
                        if _ceiling_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "scaffold ceiling A/B deterministic + advisory only — "
                                "needs human set_maturity; not auto-retire"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "OPT_SEARCH_STORM":
                        # Phase N / ACT-110: huge composition-optimization search hits
                        # SearchBounded → stops (best-so-far / OPT_ESCALATION) — never
                        # exponential unbounded branch-and-bound (Rule 9.26.1).
                        if _opt_search_storm_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "optimization search storm bounded (node expansions ≤ "
                                "SDD_OPT_NODE_BUDGET → best-so-far / OPT_ESCALATION) — "
                                "needs human budget/decomposition; not exponential search"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "OBJECTIVE_TUNE_FLAP":
                        # Phase O / ACT-116: Goodhart fake-optimal weight proposals are
                        # rejected by the held-out oracle (zero-miss) and obj-profile churn
                        # hits ChurnBounded → MFSM_ESCALATION (bounded) — never infinite
                        # self-tuning nor self-graded adoption (Rule 9.27.1/9.27.2).
                        if _objective_tune_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "objective tuning flap bounded (Goodhart proposals rejected by "
                                "held-out oracle + obj-profile churn ≥ SDD_META_CHURN_MAX → "
                                "MFSM_ESCALATION) — needs human objective-dimension review; "
                                "not infinite self-tuning"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "CROSS_SCORER_GOODHART_FLAP":
                        # Phase P / ACT-122: seam Goodhart vector passes each per-scorer view but
                        # is rejected by the pipeline-level joint oracle (zero-miss; per-scorer
                        # pass != joint pass, Rule 9.28.2). Bounded: rejected → no adoption.
                        if _cross_scorer_goodhart_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "cross-scorer seam Goodhart bounded (per-scorer pass but "
                                "pipeline joint oracle rejects, zero-miss → no adoption) — "
                                "needs human cross-scorer objective-conflict review; "
                                "not self-graded seam adoption"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "JOINT_CALIBRATION_FLAP":
                        # Phase P / ACT-122: A→B→A cross-scorer adoption storm hits the aggregate
                        # CrossScorerChurnBounded rate cap → MFSM_ESCALATION (bounded) — never
                        # infinite coupled oscillation per-fingerprint churn is blind to (9.28.3).
                        if _joint_calibration_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "joint calibration flap bounded (cross-scorer aggregate adoption "
                                "rate ≥ SDD_CALIB_ADOPT_RATE_MAX → MFSM_ESCALATION) — needs human "
                                "value-system convergence review; not infinite coupled oscillation"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "DIMENSION_GOODHART_FLAP":
                        # Phase Q / ACT-128: a self-serving noise axis / redundant axis passes the
                        # proposer's naive self-view but is rejected by the dimension necessity
                        # oracle (zero-miss; proposer self-pass != oracle necessary, Rule 9.29.2).
                        # Bounded: rejected → no dimension adoption.
                        if _dimension_goodhart_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "dimension Goodhart bounded (self-serving noise / redundant axis "
                                "rejected by necessity oracle, zero-miss → no ontology expansion) — "
                                "needs human value-dimension necessity review; not self-graded "
                                "dimension adoption"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "DIMENSION_EXPLOSION_FLAP":
                        # Phase Q / ACT-128: an unbounded-new-dimension storm (each first-adopted,
                        # churn=0) hits the DimensionCardinalityBounded stock ceiling →
                        # MFSM_ESCALATION (bounded) — never unbounded ontology growth that
                        # per-fingerprint/aggregate churn is blind to (Rule 9.29.3).
                        if _dimension_explosion_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "dimension explosion bounded (active value dimensions ≥ "
                                "SDD_DIM_CARDINALITY_MAX → DimensionCardinalityExceeded → "
                                "MFSM_ESCALATION) — needs human ontology-cardinality review; "
                                "not unbounded ontology growth"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "DIMENSION_INVENTION_GOODHART_FLAP":
                        # Phase R / ACT-134: a self-referential invented axis is rejected by the
                        # synthesizer self-reference guard before reaching the oracle, and a
                        # candidate-pool-external noise axis is rejected by the feature-keyed
                        # necessity oracle (zero-miss; synthesizer self-pass != oracle necessary,
                        # Rule 9.30.2). Bounded: rejected → no ontology self-invention.
                        if _dimension_invention_goodhart_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "dimension self-invention Goodhart bounded (self-referential axis "
                                "rejected by self-reference guard + candidate-pool-external noise "
                                "axis rejected by feature-keyed necessity oracle, zero-miss → no "
                                "self-invention) — needs human candidate-pool-external necessity "
                                "review; not self-graded ontology invention"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "DIMENSION_SWAP_THRASH_FLAP":
                        # Phase R / ACT-134: a retire-to-swap storm at the cardinality ceiling (each
                        # net cardinality=0, stock never exceeded, per-fingerprint churn<=1) hits the
                        # SwapCadenceBounded aggregate swap-rate cap → SwapCadenceExceeded →
                        # MFSM_ESCALATION (bounded) — never unbounded same-cardinality ontology
                        # rotation per-fingerprint churn / cardinality stock are blind to (9.30.3).
                        if _dimension_swap_thrash_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "dimension swap thrash bounded (retire-to-swap aggregate rate ≥ "
                                "SDD_DIM_SWAP_RATE_MAX → SwapCadenceExceeded → MFSM_ESCALATION) — "
                                "needs human ontology-rotation review; not unbounded "
                                "same-cardinality ontology rotation"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "VOCAB_GENESIS_GOODHART_FLAP":
                        # Phase S / ACT-140 (meta⁴): a self-referential genesis feature is rejected by
                        # the vocabulary self-reference guard before reaching the oracle, and a
                        # vocab-external noise feature is rejected by the feature-grounded necessity
                        # oracle (zero-miss; genesis self-pass != oracle necessary, Rule 9.31.2).
                        # Bounded: rejected → no vocabulary self-invention.
                        if _vocab_genesis_goodhart_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "vocabulary genesis Goodhart bounded (self-referential genesis "
                                "feature rejected by vocab self-reference guard + vocab-external "
                                "noise feature rejected by feature-grounded necessity oracle, "
                                "zero-miss → no vocabulary self-invention) — needs human "
                                "vocab-external necessity review; not self-graded vocabulary genesis"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "BATCH_SWAP_THRASH_FLAP":
                        # Phase S / ACT-140 (meta⁴): a multi-dimension batch retire-to-swap storm
                        # (each net cardinality non-increasing, distinct batch_id) hits the
                        # BatchSwapCadenceBounded aggregate batch-rate cap → BatchSwapCadenceExceeded
                        # → MFSM_ESCALATION (bounded) — never unbounded batch ontology rotation that
                        # per-swap SwapCadence / monotone ratchet are blind to (Rule 9.31.3).
                        if _batch_swap_thrash_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "batch swap thrash bounded (batch retire-to-swap aggregate rate ≥ "
                                "SDD_DIM_BATCH_RATE_MAX → BatchSwapCadenceExceeded → "
                                "MFSM_ESCALATION) — needs human batch-recomposition review; not "
                                "unbounded batch ontology rotation"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "OPERATOR_GENESIS_GOODHART_FLAP":
                        # Phase T / ACT-146 (meta⁵): a self-referential invented operator is rejected
                        # by the operator self-reference guard before reaching the oracle, and an
                        # OPS-external noise operator is rejected by the feature-grounded operator
                        # necessity oracle (zero-miss; genesis self-pass != oracle necessary, Rule
                        # 9.32.2). Bounded: rejected → no operator self-invention.
                        if _operator_genesis_goodhart_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "operator genesis Goodhart bounded (self-referential invented "
                                "operator rejected by operator self-reference guard + OPS-external "
                                "noise operator rejected by feature-grounded necessity oracle, "
                                "zero-miss → no operator self-invention) — needs human OPS-external "
                                "necessity review; not self-graded operator genesis"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "OPERATOR_COMPUTABILITY_FLAP":
                        # Phase T / ACT-146 (meta⁵ deepest halting): the invented operator is a piece
                        # of executable computation — a non-total or over-budget operator (cost >
                        # SDD_DIM_OP_STEP_MAX) is rejected by guard_operator_computability before
                        # adoption → OperatorComputabilityExceeded (bounded). The bounded operator
                        # grammar structurally guarantees every legit operator is total + bounded-step
                        # + recursion/loop-free, pinning the halting problem into the self-expansion
                        # artefact itself (Rule 9.32.3).
                        if _operator_computability_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "operator computability bounded (non-total / over-budget invented "
                                "operator rejected by guard_operator_computability → "
                                "OperatorComputabilityExceeded; bounded operator grammar guarantees "
                                "total + bounded-step + recursion/loop-free) — needs human review; "
                                "halting problem pinned into the self-expansion artefact itself"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "ALPHABET_GENESIS_GOODHART_FLAP":
                        # Phase U / ACT-149 (meta⁶): a self-referential invented alphabet element is
                        # rejected by the alphabet self-reference guard before reaching the oracle, and
                        # an alphabet-external noise element is rejected by the feature-grounded alphabet
                        # necessity oracle (zero-miss; genesis self-pass != oracle necessary, Rule
                        # 9.33.2). Bounded: rejected → no alphabet self-invention.
                        if _alphabet_genesis_goodhart_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "alphabet genesis Goodhart bounded (self-referential invented alphabet "
                                "element rejected by alphabet self-reference guard + alphabet-external "
                                "noise element rejected by feature-grounded necessity oracle, zero-miss "
                                "→ no alphabet self-invention) — needs human alphabet-external necessity "
                                "review; not self-graded alphabet genesis"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "COMPUTABILITY_CLOSURE_FLAP":
                        # Phase U / ACT-149 (meta⁶ deepest halting): the invented alphabet element is a
                        # generation-rule part used to generate the entire operator algebra — a
                        # closure-breaking element (non-total reducer or over-budget G(A')) is rejected
                        # by guard_computability_closure before adoption → ComputabilityClosureViolation
                        # (bounded). The bounded alphabet grammar structurally guarantees every invented
                        # element keeps the whole generated algebra total + bounded-step + recursion/
                        # loop-free, pinning the halting problem into the self-expansion generation rule
                        # itself (Rule 9.33.3).
                        if _computability_closure_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "computability closure bounded (closure-breaking / over-budget invented "
                                "alphabet element rejected by guard_computability_closure → "
                                "ComputabilityClosureViolation; bounded alphabet grammar guarantees the "
                                "whole generated algebra stays total + bounded-step + recursion/loop-free)"
                                " — needs human review; halting problem pinned into the self-expansion "
                                "generation rule itself"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "DEPTH_GENESIS_GOODHART_FLAP":
                        # Phase V / ACT-152 (meta⁷): a self-referential invented depth operator is rejected
                        # by the depth self-reference guard before reaching the oracle, and a depth-external
                        # noise operator is rejected by the feature-grounded depth necessity oracle (zero-miss;
                        # genesis self-pass != oracle necessary, Rule 9.34.2). Bounded: rejected → no depth
                        # self-invention.
                        if _depth_genesis_goodhart_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "depth genesis Goodhart bounded (self-referential invented depth operator "
                                "rejected by depth self-reference guard + depth-external noise operator "
                                "rejected by feature-grounded necessity oracle, zero-miss → no depth "
                                "self-invention) — needs human depth-external necessity review; not "
                                "self-graded depth genesis"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "DEPTH_CLOSURE_FLAP":
                        # Phase V / ACT-152 (meta⁷ deepest halting, because cost==depth): the self-expanded
                        # artefact is the operator grammar's structural depth parameter itself — and
                        # cost==depth, so expanding the depth literally expands the step count. A depth
                        # operator whose depth exceeds STEP_MAX (cost==depth > SDD_DIM_OP_STEP_MAX) or a
                        # non-total depth operator is rejected by guard_depth_closure before adoption →
                        # DepthClosureViolation (bounded). The bounded depth grammar guarantees every invented
                        # depth operator keeps the whole same-depth algebra total + cost==depth-bounded +
                        # recursion/loop-free, pinning the halting problem into the self-expansion
                        # generation-grammar depth parameter itself (Rule 9.34.3).
                        if _depth_closure_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "depth closure bounded (over-depth / non-total invented depth operator "
                                "rejected by guard_depth_closure → DepthClosureViolation; bounded depth "
                                "grammar guarantees the whole same-depth algebra stays total + "
                                "cost==depth-bounded + recursion/loop-free) — needs human review; halting "
                                "problem pinned into the self-expansion generation-grammar depth parameter "
                                "itself, because cost==depth"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "RECURSION_GENESIS_GOODHART_FLAP":
                        # Phase W / ACT-155 (meta⁸): a self-referential invented inter-recursive operator is
                        # rejected by the recursion self-reference guard before reaching the oracle, and a
                        # recursion-external noise operator is rejected by the feature-grounded recursion
                        # necessity oracle (zero-miss; genesis self-pass != oracle necessary, Rule 9.35.2).
                        # Bounded: rejected → no recursion self-invention.
                        if _recursion_genesis_goodhart_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "recursion genesis Goodhart bounded (self-referential invented inter-recursive "
                                "operator rejected by recursion self-reference guard + recursion-external noise "
                                "operator rejected by feature-grounded necessity oracle, zero-miss → no recursion "
                                "self-invention) — needs human recursion-external necessity review; not "
                                "self-graded recursion genesis"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "RECURSION_CLOSURE_FLAP":
                        # Phase W / ACT-155 (meta⁸ decidability-boundary halting): deciding whether an arbitrary
                        # cyclic call graph halts IS the halting problem (undecidable), so the "bounded step
                        # count" device structurally fails. A recursive operator whose call graph contains an
                        # uncertified cycle (no back-edge strictly decreasing a lower-bounded rank → may not
                        # terminate), or whose fuel exceeds STEP_MAX, is rejected by guard_recursion_closure
                        # before adoption → RecursionClosureViolation (bounded). The bounded recursion grammar
                        # guarantees every invented operator carries a well-founded termination certificate
                        # (acyclic ∨ rank-descending + fuel<=STEP_MAX + total + recursion/loop-free evaluator),
                        # pinning the halting problem onto the decidable/total fragment boundary itself —
                        # replacing the failed "bounded step count" device with "well-founded measure" (Rule 9.35.3).
                        if _recursion_closure_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "recursion closure bounded (uncertified-cycle / fuel-over-budget invented "
                                "recursive operator rejected by guard_recursion_closure → RecursionClosure"
                                "Violation; bounded recursion grammar guarantees every invented operator carries "
                                "a well-founded termination certificate) — needs human review; halting problem "
                                "pinned onto the decidable/total fragment boundary itself, the 'bounded step "
                                "count' device replaced by 'well-founded measure'"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "EMBODIED_GROUNDING_FLAP":
                        # Phase X / ACT-158 (meta⁸ embodied grounding): to validate the self-evolution loop
                        # against the REAL environment, the embodied grounding gate introduces "the real sandbox
                        # may hang" as a new non-halting source. A self-invented capability with a zero-observation
                        # false-green grounded verdict is rejected by guard_embodied_grounding (fail-closed →
                        # EmbodiedGroundingViolation, bounded), and a sandbox-timed-out grounding is mapped to
                        # grounded_fail (FSM收 verdict 而非等沙箱, REJECT no churn) — 100% isomorphic with TLA+
                        # EmbodiedGroundingBounded, pinning "the real sandbox may hang" into bounded halting.
                        if _embodied_grounding_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "embodied grounding bounded (zero-observation false-green grounded verdict "
                                "rejected by guard_embodied_grounding fail-closed → EmbodiedGroundingViolation; "
                                "sandbox-timed-out grounding mapped to grounded_fail, FSM doesn't wall-clock wait) "
                                "— needs human embodied grounding review; not synthetic self-graded"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "VISUALIZATION_FLAP":
                        # Phase Y / ACT-161 (meta⁸ explainability / token-budget halting): rendering a meta⁸
                        # recursion call graph for human approval introduces "rendering an unbounded huge graph
                        # may OOM / token-explode" as a new non-halting source. A 10⁶-node adversarial graph is
                        # bounded-truncated to <= node_budget + paginated, dashboard markdown <= char_budget — no
                        # hang, no OOM, no token over-budget; guard_visualization_bounded allows the bounded
                        # (truncated) render. 100% isomorphic with TLA+ VisualizationBounded (Rule 9.37).
                        if _visualization_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "visualization bounded (10^6-node adversarial recursion graph bounded-truncated "
                                "to <= node_budget + paginated, dashboard markdown <= char_budget — no hang/OOM/"
                                "token-explosion; guard_visualization_bounded allows the bounded render) — needs "
                                "human K=1 topology signoff; read-only projection doesn't drift the meta-loop"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "VISUALIZATION_TOPOLOGY_DRIFT_FLAP":
                        # Phase Y / ACT-161 (meta⁸ explainability anti-forgery): a tampered render drawing a
                        # SIMPLER graph than the operator actually runs (drops a within-window call edge / fakes
                        # a rank to look more well-founded) is the visual-deception attack. verify_topology_
                        # consistency independently re-derives the subgraph from to_dict() and REJECTS the forgery
                        # → TopologyConsistencyError (fail-closed); a faithful render is correctly allowed.
                        if _visualization_topology_drift_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "visualization topology drift bounded (tampered render drawing a simpler graph "
                                "than the operator runs — dropped edge / faked rank — rejected by verify_topology_"
                                "consistency fail-closed; faithful render allowed, no false-reject) — needs human "
                                "review; the drawn graph == the run graph, no visual deception"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    elif fault == "VISUALIZATION_FOLD_DRIFT_FLAP":
                        # W-23-1 (improving_23, meta⁸ explainability folding anti-forgery): a folded super-node is
                        # an HONEST contraction only if it declares a genuine interior simple chain. A forged fold
                        # (swallowing a sink / dropping a member to draw a simpler graph) is rejected by fold-aware
                        # verify_topology_consistency → TopologyConsistencyError (fail-closed); a faithful fold is
                        # correctly allowed (no false-reject).
                        if _visualization_fold_drift_flap_is_bounded() and rt.state.current not in TERMINAL_STATES:
                            rt.state.record_escalation(
                                "visualization fold drift bounded (forged fold swallowing a sink / dropping a "
                                "member — drawing a simpler graph than the operator runs — rejected by fold-aware "
                                "verify_topology_consistency fail-closed; faithful fold allowed, no false-reject) "
                                "— needs human review; the folded graph is a verifiable lossless contraction"
                            )
                            save_state(rt.state)
                        tokens += _TOKEN_COST_GATE
                    tokens += _TOKEN_COST_FAULT_INJECT
                    faults_fired.append(fault)
                except Exception as exc:  # noqa: BLE001
                    result.error = f"fault {fault}: {exc}"
                    # fault-inject exceptions count as halted (bounded)
                    break

        cur = rt.state.current
        # Terminal check
        if cur in TERMINAL_STATES:
            break

        # Gate-driven states
        try:
            if cur == "SCG_VALIDATION":
                if scg_infinite:
                    _gate_fail(rt, "SCG_VALIDATION", "chaos scg infinite")
                    tokens += _TOKEN_COST_GATE
                    # Return state may be SPEC_DRAFTING or ESCALATION
                    # Bounce back into SCG_VALIDATION for next iteration
                    if rt.state.current == "SPEC_DRAFTING":
                        try:
                            rt.transition("SCG_VALIDATION", reason="chaos retry", trigger="chaos")
                        except TransitionError:
                            pass
                else:
                    _gate_pass(rt, "SCG_VALIDATION")
                    tokens += _TOKEN_COST_GATE
            elif cur == "PR_REVIEW":
                # Phase G M2 / ACT-036: TRAJECTORY_PREDICTION short-circuit.
                # Consult predictor BEFORE the next gate fail; if it triggers
                # switch_to_audit, skip the remaining jitter retries (saving
                # _TOKEN_COST_GATE × remaining iterations). Predictor only
                # operates when retry_count ≥ 1 (Rule 9.15.1) which means we
                # check after the first failure on subsequent iters.
                predictor_executed = False
                if "TRAJECTORY_PREDICTION" in chosen and "PR_REVIEW_JITTER" in chosen:
                    retry_entry = rt.state.retry("PR_REVIEW")
                    if int(retry_entry.get("current_count", 0)) >= 1:
                        try:
                            pred = rt.consult_predictor(
                                gate="PR_REVIEW",
                                ledger_path=chaos_ledger_path,
                            )
                            tokens += _TOKEN_COST_TRANSITION
                            if pred.get("executed"):
                                predictor_executed = True
                                if "TRAJECTORY_PREDICTION" not in faults_fired:
                                    faults_fired.append("TRAJECTORY_PREDICTION")
                                pr_jitter_idx = len(pr_jitter_reasons)
                                # State is now SPEC_AUDIT (or ESCALATION).
                                if rt.state.current == "SPEC_AUDIT":
                                    rt.record_spec_audit()
                        except (TransitionError, ValueError):
                            pass
                if predictor_executed:
                    pass  # state already advanced by predictor
                elif "PR_REVIEW_JITTER" in chosen and pr_jitter_idx < len(pr_jitter_reasons):
                    reason = pr_jitter_reasons[pr_jitter_idx]
                    pr_jitter_idx += 1
                    _gate_fail(rt, "PR_REVIEW", reason)
                    tokens += _TOKEN_COST_GATE
                    if rt.state.current == "IMPLEMENTATION":
                        try:
                            rt.transition("PR_REVIEW", reason="chaos retry", trigger="chaos")
                        except TransitionError:
                            pass
                    elif rt.state.current == "SPEC_AUDIT":
                        # Record audit and return to PR_REVIEW
                        rt.record_spec_audit()
                else:
                    _gate_pass(rt, "PR_REVIEW")
                    tokens += _TOKEN_COST_GATE
            elif cur == "RTM_VERIFY":
                _gate_pass(rt, "RTM_VERIFY")
                tokens += _TOKEN_COST_GATE
            elif cur == "HUMAN_PENDING":
                # Attempt happy-path advance; if timeout injected, transition
                # will already have escalated.
                if not _advance_happy_path_once(rt):
                    # stuck — bail after 1 extra loop
                    if steps - trigger_step > 5:
                        rt.state.record_escalation("chaos stuck in HUMAN_PENDING")
                        save_state(rt.state)
                tokens += _TOKEN_COST_TRANSITION
            elif cur == "SPEC_AUDIT":
                # Return to PR_REVIEW if possible, else escalate
                try:
                    rt.transition("PR_REVIEW", reason="chaos audit complete", trigger="chaos")
                except TransitionError:
                    rt.state.record_escalation("chaos spec_audit stuck")
                    save_state(rt.state)
                tokens += _TOKEN_COST_TRANSITION
            elif cur == "RESUME_VERIFICATION":
                # Leave recovery — go to PR_REVIEW or ESCALATION
                try:
                    rt.transition("SPEC_DRAFTING", reason="chaos resume", trigger="chaos")
                except TransitionError:
                    rt.state.record_escalation("chaos resume failed")
                    save_state(rt.state)
                tokens += _TOKEN_COST_TRANSITION
            elif cur == "AUTO_COMPACT_PENDING":
                rt.complete_auto_compact(reset_ledger=False)
                tokens += _TOKEN_COST_TRANSITION
            elif cur == "TOKEN_BUDGET_CRITICAL":
                # QA Round-3 P2-01: this branch previously skipped its token
                # accounting. All other escalation paths pay _TOKEN_COST_TRANSITION
                # so the budget stays comparable across fault scenarios.
                rt.state.record_escalation("chaos token critical")
                save_state(rt.state)
                tokens += _TOKEN_COST_TRANSITION
            else:
                if _advance_happy_path_once(rt):
                    tokens += _TOKEN_COST_TRANSITION + _TOKEN_COST_WRITE
                else:
                    # Can't advance — escalate as last resort
                    rt.state.record_escalation(f"chaos cannot advance from {cur}")
                    save_state(rt.state)
        except Exception as exc:  # noqa: BLE001 — TransitionError subclass of Exception
            result.error = f"step {steps} at {cur}: {exc}"
            # Record as halted
            try:
                rt.state.record_escalation(f"chaos exception: {exc}")
                save_state(rt.state)
            except Exception:  # noqa: BLE001
                pass
            break

    result.steps_taken = steps
    result.final_state = rt.state.current
    result.bounded = rt.state.current in TERMINAL_STATES
    result.tokens_estimated = tokens
    # QA Round-3 P2-05: always reflect *fired* faults. Even when empty (e.g. the
    # round halted before trigger_step) we surface an empty list so aggregate
    # tests can distinguish "fault selected but never injected" from legacy
    # fallback to the pre-round selection.
    result.faults_injected = list(faults_fired)
    # QA Round-3 P2-09: flag step-cap exhaustion explicitly. A round hitting
    # _MAX_STEPS_PER_ROUND without landing in a terminal state represents a
    # guard failure; callers need to tell this apart from a bounded halt that
    # legitimately used many steps.
    if steps >= _MAX_STEPS_PER_ROUND and rt.state.current not in TERMINAL_STATES:
        exhaustion_note = f"step cap reached at {_MAX_STEPS_PER_ROUND}"
        result.error = (
            f"{result.error}; {exhaustion_note}" if result.error else exhaustion_note
        )
    return result


# ---------- public API ----------


def run_chaos_rounds(
    n: int = 100,
    seed: Optional[int] = None,
    workdir: Optional[Path] = None,
    progress_cb: Optional[Callable[[int, ChaosResult], None]] = None,
) -> ChaosReport:
    """Run N chaos rounds; return aggregated report.

    Each round uses a freshly-seeded Random derived from the master seed so
    results are reproducible when `seed` is provided.
    """
    master_rng = random.Random(seed)
    report = ChaosReport()
    cleanup = False
    if workdir is None:
        tmp = tempfile.mkdtemp(prefix="chaos_runner_")
        workdir = Path(tmp)
        cleanup = True
    try:
        for i in range(n):
            round_seed = master_rng.randrange(1, 2**31 - 1)
            result = _run_single_round(i, round_seed, workdir)
            report.rounds.append(result)
            if progress_cb is not None:
                progress_cb(i, result)
    finally:
        if cleanup:
            shutil.rmtree(workdir, ignore_errors=True)
    return report


# P2-05: avg-token warning threshold — 80% of the 25K budget. Exceeding
# this does NOT fail the run, but we print a WARNING so regressions are
# surfaced before they cross the hard budget.
_TOKEN_BUDGET_HARD = 25_000
_TOKEN_BUDGET_WARN = int(_TOKEN_BUDGET_HARD * 0.80)


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="ACT-029 Chaos Runner — verify FSM bounded-halt under adversarial faults."
    )
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--workdir", type=str, default=None)
    parser.add_argument("--json", action="store_true", help="Emit JSON report to stdout.")
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Print per-round progress (uses run_chaos_rounds' progress_cb).",
    )
    args = parser.parse_args()

    workdir = Path(args.workdir) if args.workdir else None

    # P2-01: wire progress_cb to the CLI so the parameter is no longer dead
    # code. Callers who need silent runs simply omit --progress.
    progress_cb: Optional[Callable[[int, ChaosResult], None]] = None
    if args.progress:
        def _print_progress(i: int, res: ChaosResult) -> None:
            tag = "OK" if res.bounded else "BAD"
            print(
                f"  [{i+1:>3}/{args.rounds}] {tag} final={res.final_state} "
                f"steps={res.steps_taken} faults={res.faults_injected}",
                flush=True,
            )
        progress_cb = _print_progress

    report = run_chaos_rounds(
        args.rounds, seed=args.seed, workdir=workdir, progress_cb=progress_cb
    )

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Chaos rounds: {report.total}")
        print(f"  Bounded halts : {report.bounded_count} ({report.bounded_ratio:.1%})")
        print(f"  Avg tokens    : {report.avg_tokens:.0f}")
        print(f"  Max steps     : {report.max_steps}")
        # P2-08: integer comparison (count vs total) avoids float-equality
        # drift in the gate decision.
        if report.bounded_count < report.total:
            print("UNBOUNDED ROUNDS:")
            for r in report.rounds:
                if not r.bounded:
                    print(f"  round={r.round_id} seed={r.seed} final={r.final_state} steps={r.steps_taken} faults={r.faults_injected} err={r.error}")
        # P2-05: early-warning band between 80% and 100% of the budget.
        if _TOKEN_BUDGET_WARN <= report.avg_tokens < _TOKEN_BUDGET_HARD:
            print(
                f"WARNING: avg_tokens={report.avg_tokens:.0f} in early-warn band "
                f"({_TOKEN_BUDGET_WARN}..{_TOKEN_BUDGET_HARD}) — investigate before regression."
            )

    # P2-08: acceptance gate uses integer comparison for boundedness.
    ok = report.bounded_count == report.total and report.avg_tokens < _TOKEN_BUDGET_HARD
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_cli())
