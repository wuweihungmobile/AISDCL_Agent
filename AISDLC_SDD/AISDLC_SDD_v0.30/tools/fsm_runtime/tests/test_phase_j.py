# enforces (governance rules): R-9.22
"""Phase J（SDD_improving_Automation_10）測試套件 — ACT-073~079.

對抗判官（PJ-1）/ 能力代謝（PJ-2）/ 規格自癒（PJ-3）/ 艦隊人機介面（PJ-4）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import adversarial_synthesizer as ADV
from tools.fsm_runtime import capability_benchmark as CB
from tools.fsm_runtime import competence_envelope as CE
from tools.fsm_runtime import spec_patch_proposer as SPP
from tools.fsm_runtime import diagnostic as DIAG
from tools.fsm_runtime import rule_loader as RL
from tools.fsm_runtime import fleet_orchestrator as FO
from tools.fsm_runtime.fsm_runtime import FSMRuntime
from tools.fsm_runtime.state_loader import load_state, save_state
from tools.fsm_runtime.transition_rules import (
    OBSERVATION_STATES, _HAPPY_PATH, TransitionError,
)


# =====================================================================
# ACT-073 — Adversarial Test Synthesizer（對抗判官 / GAN discriminator）
# =====================================================================

def T(fn, domain="int", declared=(), latent=()):
    return ADV.Target(fn=fn, domain=domain, declared_properties=declared, latent_relations=latent)


# --- 15 robust 程式（verdict 應為 robust）---
ROBUST_CORPUS = [
    ("identity", T(lambda x: x, "int", ("deterministic", "monotonic_increasing"), ("scaling",))),
    ("double", T(lambda x: 2 * x, "int", ("monotonic_increasing", "deterministic"), ("scaling",))),
    ("triple", T(lambda x: 3 * x, "int", ("monotonic_increasing",), ("scaling",))),
    ("abs", T(lambda x: abs(x), "int", ("non_negative", "deterministic"))),
    ("square", T(lambda x: x * x, "int", ("non_negative", "deterministic", "bounded"))),
    ("plus10", T(lambda x: x + 10, "int", ("monotonic_increasing", "deterministic"))),
    ("max0", T(lambda x: max(x, 0), "int", ("non_negative", "monotonic_increasing", "deterministic"))),
    ("clamp", T(lambda x: max(0, min(x, 100)), "int", ("non_negative", "bounded", "deterministic"))),
    ("sum_list", T(lambda xs: sum(xs), "list_int", ("deterministic",), ("order_invariant",))),
    ("len_list", T(lambda xs: len(xs), "list_int", ("non_negative", "deterministic"), ("order_invariant",))),
    ("sorted_list", T(lambda xs: sorted(xs), "list_int", ("length_preserving", "deterministic"),
                      ("order_invariant", "length_preserving"))),
    ("double_list", T(lambda xs: [2 * v for v in xs], "list_int", ("length_preserving", "deterministic"),
                      ("length_preserving",))),
    ("max_list", T(lambda xs: max(xs) if xs else 0, "list_int", ("deterministic",), ("order_invariant",))),
    ("upper", T(lambda s: s.upper(), "str", ("deterministic", "idempotent"))),
    ("strip", T(lambda s: s.strip(), "str", ("deterministic", "idempotent"))),
]

# --- 15 含植入缺陷的程式（verdict 應為 counterexample 或 spec_gap）---
DEFECT_CORPUS = [
    ("neg_identity_nonneg", T(lambda x: x, "int", ("non_negative",)), "counterexample"),
    ("div_zero_crash", T(lambda x: 1 // x if x else 1 // x, "int", ("deterministic",)), "counterexample"),
    ("non_monotonic", T(lambda x: -x, "int", ("monotonic_increasing",)), "counterexample"),
    ("not_idempotent", T(lambda s: s + "!", "str", ("idempotent",)), "counterexample"),
    ("unbounded", T(lambda x: x ** 10, "int", ("bounded",)), "counterexample"),
    ("constant_zero", T(lambda x: 0, "int", ("non_negative", "deterministic")), "counterexample"),
    ("length_changing", T(lambda xs: list(xs) + [0], "list_int", ("length_preserving",)), "counterexample"),
    ("order_sensitive_decl", T(lambda xs: xs[0] if xs else 0, "list_int", ("order_invariant",)), "counterexample"),
    ("str_index_crash", T(lambda s: s[10], "str", ("deterministic",)), "counterexample"),
    ("negative_square", T(lambda x: -(x * x), "int", ("non_negative",)), "counterexample"),
    # spec_gap：宣告性質全過，但隱含 latent 關係被破（AC 漏寫）
    ("plus5_scaling_gap", T(lambda x: x + 5, "int", ("monotonic_increasing", "deterministic"), ("scaling",)), "spec_gap"),
    ("square_scaling_gap", T(lambda x: x * x, "int", ("non_negative", "deterministic"), ("scaling",)), "spec_gap"),
    ("concat_order_gap", T(lambda xs: list(xs), "list_int", ("length_preserving", "deterministic"), ("order_invariant",)), "spec_gap"),
    ("shift_scaling_gap", T(lambda x: x + 1, "int", ("monotonic_increasing", "deterministic"), ("scaling",)), "spec_gap"),
    ("absplus1_scaling_gap", T(lambda x: abs(x) + 1, "int", ("non_negative", "deterministic"), ("scaling",)), "spec_gap"),
]


@pytest.mark.parametrize("name,target", ROBUST_CORPUS)
def test_adversarial_robust_corpus(name, target):
    res = ADV.evaluate_target(target)
    assert res.verdict == "robust", f"{name}: expected robust, got {res.verdict} ({res.counterexamples or res.spec_gaps})"


@pytest.mark.parametrize("name,target,expected", DEFECT_CORPUS)
def test_adversarial_defect_corpus(name, target, expected):
    res = ADV.evaluate_target(target)
    assert not res.robust, f"{name}: expected defect detected, got robust"


def test_adversarial_detection_and_fp_rates():
    """偵出率 ≥ 80%、誤報率 < 15%（驗收標準）。"""
    detected = sum(1 for _n, t, _e in DEFECT_CORPUS if not ADV.evaluate_target(t).robust)
    fp = sum(1 for _n, t in ROBUST_CORPUS if not ADV.evaluate_target(t).robust)
    assert detected / len(DEFECT_CORPUS) >= 0.80
    assert fp / len(ROBUST_CORPUS) < 0.15


def test_adversarial_spec_gap_routes_to_audit():
    """self-verification 核心案例：AC 自洽但違反 metamorphic → spec_gap。"""
    res = ADV.evaluate_target(T(lambda x: x + 5, "int", ("monotonic_increasing", "deterministic"), ("scaling",)))
    assert res.verdict == "spec_gap"
    assert res.spec_gaps


def test_adversarial_rounds_clamp(monkeypatch):
    monkeypatch.setenv("SDD_ADVERSARIAL_ROUNDS", "999")
    assert ADV.adversarial_rounds() == 16
    monkeypatch.setenv("SDD_ADVERSARIAL_ROUNDS", "0")
    assert ADV.adversarial_rounds() == 1
    monkeypatch.setenv("SDD_ADVERSARIAL_ROUNDS", "garbage")
    assert ADV.adversarial_rounds() == 8
    monkeypatch.delenv("SDD_ADVERSARIAL_ROUNDS", raising=False)
    assert ADV.adversarial_rounds() == 8


def test_adversarial_profile_version_frozen():
    assert ADV.ADVERSARIAL_PROFILE_VERSION == "v1.0"
    res = ADV.evaluate_target(ROBUST_CORPUS[0][1])
    assert res.profile_version == "v1.0"


def test_adversarial_deterministic_is_stable():
    t = ROBUST_CORPUS[0][1]
    assert not ADV.evaluate_target(t).flaky


def test_adversarial_nondeterministic_never_robust():
    """去隨機：非確定性程式絕不判 robust（隔離為 inconclusive 或抓成 counterexample）。"""
    counter = {"n": 0}

    def flaky(x):
        counter["n"] += 1
        if counter["n"] % 3 == 0:
            raise ValueError("intermittent")
        return abs(x)

    res = ADV.evaluate_target(T(flaky, "int", ("non_negative",)))
    assert not res.robust


def test_adversarial_attack_types_complete():
    assert set(ADV.ATTACK_TYPES) == {"property_based", "metamorphic", "fuzz", "mutation_guided"}


# =====================================================================
# ACT-075 — Capability Benchmark Harness
# =====================================================================

def _suite():
    return [
        CB.Benchmark("temporal_consistency", "task1", lambda o: o == "ok", scaffold_rule_id="R-SLV-007"),
        CB.Benchmark("boundary_quant", "task2", lambda o: "ms" in o),
    ]


def test_capability_grade_pass_rate():
    b = CB.Benchmark("c", "p", lambda o: o == "yes")
    r = CB.grade(b, ["yes", "yes", "no", "yes"])
    assert r.passed == 3 and r.total == 4 and r.score == 0.75


def test_capability_grade_empty_is_zero():
    b = CB.Benchmark("c", "p", lambda o: True)
    assert CB.grade(b, []).score == 0.0


def test_capability_grader_exception_is_fail():
    b = CB.Benchmark("c", "p", lambda o: 1 / 0)
    assert CB.grade(b, ["x", "y"]).score == 0.0


def test_capability_record_and_rolling(tmp_path):
    led = tmp_path / "capability-ledger.yaml"
    suite = _suite()
    for i in range(12):
        run = CB.run_suite(suite, {"temporal_consistency": ["ok"], "boundary_quant": ["50ms"]},
                           model_id="m", today=f"2026-06-{i+1:02d}")
        CB.record_run(run, path=led)
    import yaml
    data = yaml.safe_load(led.read_text(encoding="utf-8"))
    hist = data["capabilities"]["temporal_consistency"]["history"]
    assert len(hist) == CB.ROLLING_WINDOW  # rolling 截斷


def test_capability_surpassed_true(tmp_path):
    led = tmp_path / "led.yaml"
    suite = _suite()
    for i in range(3):
        run = CB.run_suite(suite, {"temporal_consistency": ["ok"], "boundary_quant": ["50ms"]},
                           model_id="m", today=f"2026-06-0{i+1}")
        CB.record_run(run, path=led)
    assert CB.capability_surpassed("temporal_consistency", path=led) is True


def test_capability_surpassed_false_when_imperfect(tmp_path):
    led = tmp_path / "led.yaml"
    suite = _suite()
    for i in range(3):
        outs = {"temporal_consistency": ["ok", "bad"], "boundary_quant": ["50ms"]}
        run = CB.run_suite(suite, outs, model_id="m", today=f"2026-06-0{i+1}")
        CB.record_run(run, path=led)
    assert CB.capability_surpassed("temporal_consistency", path=led) is False


def test_capability_surpassed_false_insufficient_runs(tmp_path):
    led = tmp_path / "led.yaml"
    run = CB.run_suite(_suite(), {"temporal_consistency": ["ok"], "boundary_quant": ["1ms"]}, today="2026-06-01")
    CB.record_run(run, path=led)
    assert CB.capability_surpassed("temporal_consistency", path=led) is False


def test_capability_surpassed_unknown_capability(tmp_path):
    assert CB.capability_surpassed("nope", path=tmp_path / "missing.yaml") is False


# =====================================================================
# ACT-076 — Capability-driven scaffold graduation
# =====================================================================

def _rule(maturity="active", fire=0, catch=0):
    return RL.Rule(id="R-X", title="x", maturity=maturity,
                   scaffold_roi={"fire_count": fire, "catch_count": catch, "false_positive_count": 0})


def test_capability_graduation_requires_surpassed():
    r = _rule("active", fire=100, catch=0)
    assert RL.propose_graduation_capability(r, capability_surpassed=False) is None
    assert RL.propose_graduation_capability(r, capability_surpassed=True) == "audit-only"


def test_capability_graduation_blocked_when_catching():
    r = _rule("active", fire=100, catch=3)
    assert RL.propose_graduation_capability(r, capability_surpassed=True) is None


def test_capability_graduation_earlier_than_fire_threshold():
    """能力驅動門檻(50)比純 fire-count(1000)早觸發。"""
    r = _rule("active", fire=60, catch=0)
    assert RL.propose_graduation(r) is None  # 純 fire 門檻未達
    assert RL.propose_graduation_capability(r, capability_surpassed=True) == "audit-only"


def test_capability_graduation_audit_to_deprecated():
    r = _rule("audit-only", fire=100, catch=0)
    assert RL.propose_graduation_capability(r, capability_surpassed=True) == "deprecated"


def test_capability_graduation_never_auto_retires(tmp_path):
    """退役必經 set_maturity(reviewed_by=)；空 reviewer 被拒。"""
    with pytest.raises(RL.RuleOverwriteProtected):
        RL.set_maturity("R-X", "deprecated", reviewed_by="", rules_dir=tmp_path)


def test_scaffold_gc_uses_capability_checker(tmp_path):
    from tools.fsm_runtime import scaffold_gc
    import yaml
    rdir = tmp_path / "rules"
    rdir.mkdir()
    (rdir / "R-CAP.yaml").write_text(yaml.safe_dump({
        "id": "R-CAP", "title": "t", "trigger_states": ["*"], "maturity": "active",
        "scaffold_roi": {"fire_count": 60, "catch_count": 0, "false_positive_count": 0},
    }), encoding="utf-8")
    props = scaffold_gc.compute_proposals(rules_dir=rdir, capability_checker=lambda r: True)
    assert any(p.rule_id == "R-CAP" and p.proposed_maturity == "audit-only" for p in props)


# =====================================================================
# ACT-077 — Competence Envelope / OOD（advisory）
# =====================================================================

CORPUS = [
    "temporal inconsistency in spec timestamps",
    "boundary quantifier missing in NFR latency",
    "metamorphic relation scaling violation",
    "SLV logical contradiction AC vs INV",
]


def test_competence_in_distribution():
    v = CE.assess("temporal inconsistency in the spec timestamps ordering", corpus=CORPUS, threshold=0.3)
    assert v.out_of_competence is False
    assert v.blocking is False


def test_competence_ood_flagged():
    v = CE.assess("quantum holographic blockchain neural substrate", corpus=CORPUS, threshold=0.3)
    assert v.out_of_competence is True
    assert v.blocking is False  # advisory-only（Rule 9.22.4）


def test_competence_advisory_never_blocks():
    v = CE.assess("zzz totally unrelated xyzzy", corpus=CORPUS, threshold=0.3)
    assert v.blocking is False


def test_competence_empty_corpus_is_in_distribution():
    v = CE.assess("anything", corpus=[], threshold=0.3)
    assert v.out_of_competence is False
    assert v.corpus_size == 0


def test_competence_threshold_env(monkeypatch):
    monkeypatch.setenv("SDD_OOD_THRESHOLD", "5")
    assert CE.ood_threshold() == 1.0
    monkeypatch.setenv("SDD_OOD_THRESHOLD", "-1")
    assert CE.ood_threshold() == 0.0
    monkeypatch.setenv("SDD_OOD_THRESHOLD", "bad")
    assert CE.ood_threshold() == 0.3
    monkeypatch.delenv("SDD_OOD_THRESHOLD", raising=False)
    assert CE.ood_threshold() == 0.3


def test_competence_classification_accuracy():
    """10 in-distribution + 10 OOD，準確率 ≥ 75%。"""
    in_dist = [
        "temporal inconsistency spec", "boundary quantifier NFR latency",
        "metamorphic relation scaling", "SLV contradiction AC INV",
        "spec timestamps ordering", "latency quantifier missing",
        "scaling violation metamorphic", "logical contradiction invariant",
        "spec inconsistency temporal", "NFR boundary missing",
    ]
    ood = [
        "quantum holographic substrate", "blockchain neural mesh",
        "photosynthesis enzyme kinetics", "medieval poetry meter",
        "underwater basket weaving", "galactic supernova spectra",
        "culinary fermentation chemistry", "tectonic plate subduction",
        "baroque harpsichord tuning", "origami tessellation geometry",
    ]
    correct = 0
    for t in in_dist:
        if not CE.assess(t, corpus=CORPUS, threshold=0.3).out_of_competence:
            correct += 1
    for t in ood:
        if CE.assess(t, corpus=CORPUS, threshold=0.3).out_of_competence:
            correct += 1
    assert correct / 20 >= 0.75


# =====================================================================
# ACT-078 — Spec-Patch Proposer
# =====================================================================

def _sig(ac="AC-005", reason="metamorphic scaling violation", ce="f(2x) != 2 f(x)"):
    return SPP.DefectSignal(ac_id=ac, defect_reason=reason, counterexample=ce)


def test_spec_patch_repeated_defect_detection():
    sigs = [_sig(), _sig(reason="metamorphic scaling violated again")]
    assert SPP.is_repeated_defect(sigs) is True


def test_spec_patch_single_defect_not_repeated():
    assert SPP.is_repeated_defect([_sig()]) is False


def test_spec_patch_proposal_has_three_sections(tmp_path):
    p = SPP.propose("AC-005", "系統應快速回應", [_sig(), _sig()], today="2026-06-01", out_dir=tmp_path)
    assert p.trust_level == "proposed"
    assert p.source == "spec_defect-auto-generated"
    txt = Path(p.report_path).read_text(encoding="utf-8")
    assert "反例證據" in txt and "Before" in txt and "After" in txt
    assert "系統應快速回應" in txt


def test_spec_patch_never_verified(tmp_path):
    p = SPP.propose("AC-1", "x", [_sig(ac="AC-1")], write=False)
    assert p.trust_level != "verified"


def test_spec_patch_after_contains_clarification():
    p = SPP.propose("AC-1", "原始 AC", [_sig(ac="AC-1", ce="空集合未定義")], write=False)
    assert "規格補強" in p.after and "空集合未定義" in p.after


# R38：ac_id 來自缺陷回流訊號（test-failure-analyzer 映射），與 state_loader.py 的
# project/track_id 同一缺陷類別姊妹位置，共用 _sanitize_component（見 state_loader.py）。
def test_spec_patch_filename_sanitizes_hostile_ac_id(tmp_path):
    hostile_ac_id = 'CON<>:"|?*../../etc' + "X" * 300
    p = SPP.propose(hostile_ac_id, "x", [_sig(ac=hostile_ac_id)],
                     today="2026-06-01", out_dir=tmp_path)
    written = Path(p.report_path)
    assert written.parent == tmp_path  # 未逃逸出 out_dir
    for ch in '<>:"|?*\\':
        assert ch not in written.name
    assert len(written.name) < 200


def test_spec_patch_filename_escapes_reserved_device_name_ac_id(tmp_path):
    p = SPP.propose("CON", "x", [_sig(ac="CON")], today="2026-06-01", out_dir=tmp_path)
    written = Path(p.report_path)
    assert written.name.startswith("SPEC-PATCH-_CON-")


# =====================================================================
# ACT-074 — ADVERSARIAL_EVALUATION FSM wiring + diagnostic
# =====================================================================

def _runtime_at(tmp_path, state_name, name="pj"):
    sp = tmp_path / f"FSM-STATE-{name}-{state_name}.yaml"
    st = load_state(name, path=sp, create_if_missing=True)
    st.root["current_state"] = state_name
    save_state(st)
    return FSMRuntime(st)


def test_adversarial_state_is_happy_gatekeep_not_observation():
    assert "ADVERSARIAL_EVALUATION" not in OBSERVATION_STATES
    assert "ADVERSARIAL_EVALUATION" in _HAPPY_PATH


def test_adversarial_enter_only_from_exec_eval(tmp_path):
    rt = _runtime_at(tmp_path, "EXECUTION_EVALUATION")
    rt.enter_adversarial_evaluation()
    assert rt.state.current == "ADVERSARIAL_EVALUATION"
    rt2 = _runtime_at(tmp_path, "IMPLEMENTATION", name="bad")
    with pytest.raises(TransitionError):
        rt2.enter_adversarial_evaluation()


@pytest.mark.parametrize("verdict,target", [
    ("robust", "PR_REVIEW"),
    ("counterexample", "IMPLEMENTATION"),
    ("spec_gap", "SPEC_AUDIT"),
])
def test_adversarial_exit_routing(tmp_path, verdict, target):
    rt = _runtime_at(tmp_path, "EXECUTION_EVALUATION", name=verdict)
    rt.enter_adversarial_evaluation()
    rt.exit_adversarial_evaluation(verdict)
    assert rt.state.current == target


def test_adversarial_exit_rejects_inconclusive(tmp_path):
    rt = _runtime_at(tmp_path, "EXECUTION_EVALUATION")
    rt.enter_adversarial_evaluation()
    with pytest.raises(ValueError):
        rt.exit_adversarial_evaluation("inconclusive")


def test_diagnostic_adversarial_counterexample_transient():
    r = DIAG.diagnose("adversarial counterexample: fuzz crash on empty input")
    assert r.sub_type == "adversarial_counterexample"
    assert r.category == "transient" and r.auto_recoverable is True


def test_diagnostic_adversarial_spec_gap_structural():
    r = DIAG.diagnose("adversarial spec_gap: metamorphic relation violated, AC under-specified")
    assert r.sub_type == "adversarial_spec_gap"
    assert r.category == "structural" and r.auto_recoverable is False


# =====================================================================
# ACT-076 — CAPABILITY_BENCHMARK observation state
# =====================================================================

def test_capability_benchmark_state_is_observation():
    assert "CAPABILITY_BENCHMARK" in OBSERVATION_STATES


@pytest.mark.parametrize("src", ["SCAFFOLD_GC", "MEMORY_CONSOLIDATION"])
def test_capability_benchmark_enter_allowed_sources(tmp_path, src):
    rt = _runtime_at(tmp_path, src, name=src)
    rt.enter_capability_benchmark()
    assert rt.state.current == "CAPABILITY_BENCHMARK"


def test_capability_benchmark_enter_rejects_illegal(tmp_path):
    rt = _runtime_at(tmp_path, "IMPLEMENTATION")
    with pytest.raises(TransitionError):
        rt.enter_capability_benchmark()


@pytest.mark.parametrize("decision,target", [("done", "RELEASE"), ("respec", "SPEC_DRAFTING")])
def test_capability_benchmark_exit(tmp_path, decision, target):
    rt = _runtime_at(tmp_path, "SCAFFOLD_GC", name=decision)
    rt.enter_capability_benchmark()
    rt.exit_capability_benchmark(decision)
    assert rt.state.current == target


def test_capability_benchmark_not_blocking(tmp_path):
    rt = _runtime_at(tmp_path, "SCAFFOLD_GC")
    rt.enter_capability_benchmark()
    rt.assert_tool_allowed("Read", None)  # 觀測態不阻擋工具


# =====================================================================
# ACT-078 — SPEC_PATCH_PROPOSAL observation state
# =====================================================================

def test_spec_patch_state_is_observation():
    assert "SPEC_PATCH_PROPOSAL" in OBSERVATION_STATES


@pytest.mark.parametrize("src", ["SPEC_AUDIT", "ESCALATION"])
def test_spec_patch_enter_allowed_sources(tmp_path, src):
    rt = _runtime_at(tmp_path, src, name=src)
    rt.enter_spec_patch_proposal(ac_id="AC-1")
    assert rt.state.current == "SPEC_PATCH_PROPOSAL"


def test_spec_patch_enter_rejects_illegal(tmp_path):
    rt = _runtime_at(tmp_path, "IMPLEMENTATION")
    with pytest.raises(TransitionError):
        rt.enter_spec_patch_proposal(ac_id="AC-1")


@pytest.mark.parametrize("outcome,target", [("drafted", "HUMAN_PENDING"), ("nodraft", "ESCALATION")])
def test_spec_patch_exit_routing(tmp_path, outcome, target):
    rt = _runtime_at(tmp_path, "SPEC_AUDIT", name=outcome)
    rt.enter_spec_patch_proposal(ac_id="AC-1")
    rt.exit_spec_patch_proposal(outcome)
    assert rt.state.current == target


def test_spec_patch_limit_escalates(tmp_path):
    """同一 AC ≤ 2 次；第 3 次直升 ESCALATION（防抖動，Rule 9.22.5）。"""
    rt = _runtime_at(tmp_path, "SPEC_AUDIT")
    rt.enter_spec_patch_proposal(ac_id="AC-9")          # 1
    rt.exit_spec_patch_proposal("drafted")
    rt.state.current = "SPEC_AUDIT"; save_state(rt.state)
    rt.enter_spec_patch_proposal(ac_id="AC-9")          # 2
    rt.exit_spec_patch_proposal("drafted")
    rt.state.current = "SPEC_AUDIT"; save_state(rt.state)
    res = rt.enter_spec_patch_proposal(ac_id="AC-9")    # 3 → ESCALATION
    assert res.get("escalated") is True
    assert rt.state.current == "ESCALATION"


def test_spec_patch_not_blocking(tmp_path):
    rt = _runtime_at(tmp_path, "SPEC_AUDIT")
    rt.enter_spec_patch_proposal(ac_id="AC-1")
    rt.assert_tool_allowed("Read", None)


# =====================================================================
# ACT-079 — Fleet Decision Aggregator
# =====================================================================

def test_fleet_aggregate_same_root_unblocks_k_tracks():
    pending = [
        FO.PendingDecision("t1", "approve API contract freeze for orders"),
        FO.PendingDecision("t2", "approve API contract freeze for order endpoint"),
        FO.PendingDecision("t3", "approve API contract freeze on orders module"),
    ]
    agg = FO.aggregate_pending(pending)
    assert len(agg) == 1
    assert agg[0].unblocks == 3
    assert agg[0].folded is True


def test_fleet_aggregate_p0_never_folded():
    pending = [
        FO.PendingDecision("t1", "spec conflict AC vs INV", category="structural"),
        FO.PendingDecision("t2", "spec conflict AC vs INV", category="structural"),
    ]
    agg = FO.aggregate_pending(pending)
    # structural 各自獨立，永不折疊
    assert len(agg) == 2
    assert all(a.category == "structural" and a.folded is False for a in agg)


def test_fleet_aggregate_distinct_roots_separate():
    pending = [
        FO.PendingDecision("t1", "approve database schema migration"),
        FO.PendingDecision("t2", "approve OAuth provider selection"),
    ]
    agg = FO.aggregate_pending(pending)
    assert len(agg) == 2


def test_fleet_decision_digest_written(tmp_path):
    pending = [
        FO.PendingDecision("t1", "approve contract freeze"),
        FO.PendingDecision("t2", "approve contract freeze now"),
        FO.PendingDecision("t3", "critical spec conflict", category="structural"),
    ]
    agg = FO.aggregate_pending(pending)
    path = FO.write_decision_digest(agg, out_dir=tmp_path, today="2026-06-01")
    txt = Path(path).read_text(encoding="utf-8")
    assert "艦隊決策 Digest" in txt and "解鎖" in txt


def test_fleet_aggregate_empty():
    assert FO.aggregate_pending([]) == []
