# enforces (governance rules): R-9.33
"""Phase U / ACT-147~149 — 組合算子文法自我擴充（meta⁶）+ 可計算性閉包回歸守門.

涵蓋：
  - ACT-147 Operator Alphabet Genesis Grammar：PRIMITIVES/COMBINATORS 外有界字母表生成文法（可枚舉、
    cap budget、兩型皆生成、結構性 total + cost-1 + 零遞迴零迴圈）、可計算性閉包 verify_computability_closure
    （擴充後 G(A') 整代數 total + 有界步數）、字母自指 alphabet_self_reference_guard 零漏放、deterministic、
    只透過注入 evaluate 取必要性（結構性無自評）、proposed-only、反 big-bang K_alpha=1 截斷、對抗分離
    （不 import oracle）、expanded_alphabet
  - ACT-148 feature-grounded 必要性 oracle：evaluate_genesis_alphabet（不靠字母名）、字母表外真必要偵出、
    字母自我發明 Goodhart（噪音字母+冗餘字母）零漏放、necessity tier 唯一來源、隔離、ALG 凍結語料；
    字母 stock AlphabetGenesisBounded + 可計算性閉包 ComputabilityClosureBounded（閉包破裂/超界→
    ComputabilityClosureViolation、字母基數觸頂→AlphabetCardinalityExceeded→MFSM_ESCALATION）、
    META_FSM 不增第六軌/不增狀態變數
  - ACT-149 steersman 字母表外發明 diff + 可計算性閉包證據（advisory + 反 big-bang + 人工 gate）+
    chaos ALPHABET_GENESIS_GOODHART_FLAP / COMPUTABILITY_CLOSURE_FLAP 有界
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from tools.fsm_runtime import operator_alphabet_genesis as AG
from tools.fsm_runtime import dimension_necessity_oracle as DO
from tools.fsm_runtime.operator_alphabet_genesis import InventedPrimitive, InventedCombinator
from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# ACT-147 — Alphabet Genesis Grammar（PRIMITIVES/COMBINATORS 外有界字母表生成文法 + 字母自指守門 + 閉包，meta⁶）
# ---------------------------------------------------------------------------

def test_enumerate_alphabet_bounded():
    """Rule 9.33.1 有界字母表生成文法：枚舉節點 <= budget（字母表外≠無界）。"""
    assert len(AG.enumerate_genesis_alphabet(budget=10)) == 10
    assert len(AG.enumerate_genesis_alphabet(budget=1)) == 1
    full = len(AG.enumerate_genesis_alphabet(budget=10000))
    assert 0 < full < 10000


def test_enumerate_alphabet_deterministic():
    a = AG.enumerate_genesis_alphabet(budget=30)
    b = AG.enumerate_genesis_alphabet(budget=30)
    assert [e.name for e in a] == [e.name for e in b]


def test_enumerate_alphabet_includes_both_types():
    """字母表生成文法應同時可發明 primitive 與 combinator（interleave 確保任何 budget 切片皆含兩型）。"""
    cands = AG.enumerate_genesis_alphabet(budget=32)
    assert any(isinstance(c, InventedPrimitive) for c in cands)
    assert any(isinstance(c, InventedCombinator) for c in cands)


def test_invented_primitive_name_cost_fingerprint():
    p = InventedPrimitive.of("acc_sumsq", "sqrt_safe")
    assert p.name == "prim::sqrt_safe(acc_sumsq)"
    assert InventedPrimitive.of("acc_sum", "identity").name == "prim::acc_sum"
    assert p.cost() == 1
    fp = p.fingerprint()
    assert fp.startswith("alphabet-genesis:")
    assert p.fingerprint() != InventedPrimitive.of("acc_sum", "identity").fingerprint()


def test_invented_combinator_name_cost():
    c = InventedCombinator.of("wmean", "binary")
    assert c.name == "comb::wmean" and c.is_binary and c.cost() == 1
    u = InventedCombinator.of("sqrt_safe", "unary")
    assert u.name == "comb::sqrt_safe/1" and not u.is_binary
    assert c.fingerprint().startswith("alphabet-genesis:")


def test_computability_closure_over_all_candidates_total_bounded():
    """Rule 9.33.3 可計算性閉包：對每個候選字母，擴充後 G(A') 整代數 total + max_cost<=step_max。"""
    step_max = MM.dim_op_step_max()
    for e in AG.enumerate_genesis_alphabet(budget=10000):
        rep = AG.verify_computability_closure(e)
        assert rep.total, f"字母 {e.name} 破壞閉包全函式"
        assert rep.max_cost <= step_max, f"字母 {e.name} 破壞閉包有界步數"
        assert rep.max_cost <= 3            # 結構性（一元 2 / 二元 3）
        assert rep.n_operators > 0


def test_closure_detects_non_total_element():
    """Rule 9.33.3：非全函式字母（未知 base_reducer → reduce 拋例外）→ 閉包 total=False。"""
    bad = InventedPrimitive(base_reducer="evil_unbounded", post_map="identity")
    assert AG.verify_computability_closure(bad).total is False


def test_alphabet_apply_is_total_fuzz():
    """Rule 9.33.3 全函式：對極端輸入 fuzz，字母 apply 永不拋例外、無 NaN/inf。"""
    extreme = [[], [0.0], [-5.0], [1e18, -1e18], [0.0, 0.0, 0.0], [1e-18], [1e308]]
    for e in AG.enumerate_genesis_alphabet(budget=10000):
        for vals in extreme:
            feats = {f: (vals[i] if i < len(vals) else 0.0) for i, f in enumerate(e.probe)}
            r = e.apply(feats)
            assert r == r and r not in (float("inf"), float("-inf"))


def test_alphabet_eval_path_no_while_no_recursion():
    """Rule 9.33.3 零遞迴零迴圈：字母求值路徑（_reduce/_post/_binary_atom/reduce/combine/apply/cost）無
    while、無自呼叫。"""
    src = (ROOT / "operator_alphabet_genesis.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    targets = {"_reduce", "_post", "_binary_atom", "reduce", "combine", "apply", "cost"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in targets:
            for sub in ast.walk(node):
                assert not isinstance(sub, ast.While), f"{node.name} 含 while（破可計算性零迴圈）"
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    assert sub.func.id != node.name, f"{node.name} 自呼叫（破可計算性零遞迴）"


def test_alphabet_self_reference_guard_zero_miss():
    """Rule 9.33.2 反自利第一閘：任何 reducer/post_map/atom/probe 自指 → 結構性丟棄。"""
    decoys = [
        InventedPrimitive.of("acc_sum", "identity", probe=["self_score", "blast_radius", "canary_gap"]),
        InventedPrimitive.of("acc_sum", "identity", probe=["proposer_x"]),
        InventedCombinator.of("wmean", "binary", probe=["necessity"]),
        InventedCombinator.of("hypot", "binary", probe=["oracle_score"]),
    ]
    for d in decoys:
        assert AG.is_alphabet_self_referential(d)
    kept = AG.alphabet_self_reference_guard(decoys + [InventedPrimitive.of("acc_sum", "identity")])
    assert len(kept) == 1 and not AG.is_alphabet_self_referential(kept[0])


def test_enumerate_excludes_self_referential():
    """生產 ATOM_REDUCERS/POST_MAPS/BINARY_ATOMS 無自指 token → 枚舉恆無自指字母。"""
    assert all(not AG.is_alphabet_self_referential(e)
               for e in AG.enumerate_genesis_alphabet(budget=10000))


def test_alphabet_genesis_only_via_injected_evaluate():
    """Rule 9.33.2 對抗分離：genesis 只呼叫注入 evaluate、結構性無自評。"""
    seen = {}
    def ev(e):
        seen[e.name] = seen.get(e.name, 0) + 1
        return 0.5 if e.name == "prim::acc_sum" else 0.0
    prop = AG.alphabet_genesis(ev, budget=30)
    assert prop.element is not None and prop.accepted
    assert prop.nodes_searched <= 30
    assert seen, "genesis 必須透過注入 evaluate 取必要性"


def test_alphabet_genesis_isolation_from_oracle():
    """Rule 9.33.2 對抗分離：operator_alphabet_genesis 結構性不 import oracle、不讀必要性語料。"""
    src = (ROOT / "operator_alphabet_genesis.py").read_text(encoding="utf-8")
    assert "dimension_necessity_oracle" not in src
    assert "load_alphabet_corpus" not in src
    assert "held-out-corpus" not in src


def test_alphabet_genesis_round_k_truncation():
    """Rule 9.33.4 反 big-bang：一輪至多 K_alpha 個，其餘順延。"""
    cands = AG.enumerate_genesis_alphabet(budget=30)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda e: scores.get(e.name, 0.0)
    rnd = AG.alphabet_genesis_round(ev, candidates=cands, k=1)
    assert len(rnd.selected) == 1
    assert rnd.selected[0].element.name == cands[0].name
    assert len(rnd.deferred) == 2


def test_expanded_alphabet():
    base = AG.expanded_alphabet([])
    assert "mean" in base and "identity" in base and "diff" in base   # 基礎 PRIMITIVES ∪ COMBINATORS
    grown = AG.expanded_alphabet(["prim::acc_sumsq"])
    assert "prim::acc_sumsq" in grown and len(grown) == len(base) + 1


def test_adopt_alphabet_requires_signoff():
    e = InventedPrimitive.of("acc_sumsq", "identity")
    with pytest.raises(AG.SignoffRequired):
        AG.adopt_genesis_alphabet(e, 50, human_signoff=False)


def test_adopt_alphabet_rejects_self_referential():
    e = InventedPrimitive.of("acc_sum", "identity", probe=["self_score", "x", "y"])
    with pytest.raises(AG.SelfReferentialAlphabet):
        AG.adopt_genesis_alphabet(e, 50, human_signoff=True)


# ---------------------------------------------------------------------------
# ACT-148 — feature-grounded 字母必要性 oracle（evaluate_genesis_alphabet，反 Goodhart）
# ---------------------------------------------------------------------------

def _true_alphabet_case():
    # sumsq/concentration-sensitive 字母救回 baseline 漏判的低幅度好候選（高 existing_cost）
    return DO.AlphabetCase(case_id="T", candidates=[
        DO.AlphabetCandidate(0.45, 2.0, {"rollback_steps": 9.0, "blast_radius": 8.0, "canary_gap": 7.0}),
        DO.AlphabetCandidate(0.87, 5.0, {"rollback_steps": 1.0, "blast_radius": 1.0, "canary_gap": 2.0}),
        DO.AlphabetCandidate(0.62, 3.0, {"rollback_steps": 4.0, "blast_radius": 3.0, "canary_gap": 3.0})])


def _noise_alphabet_case():
    return DO.AlphabetCase(case_id="N", candidates=[
        DO.AlphabetCandidate(0.6, 2.0, {"rollback_steps": 5.0, "blast_radius": 5.0, "canary_gap": 5.0}),
        DO.AlphabetCandidate(0.6, 3.0, {"rollback_steps": 0.0, "blast_radius": 0.0, "canary_gap": 0.0}),
        DO.AlphabetCandidate(0.4, 4.0, {"rollback_steps": 8.0, "blast_radius": 8.0, "canary_gap": 8.0})])


def _redundant_alphabet_case():
    # acc_first(probe)=rollback_steps 等於 existing_cost 排序（再投影既有成本）→ concordance 高 → 冗餘
    return DO.AlphabetCase(case_id="R", candidates=[
        DO.AlphabetCandidate(0.6, 2.0, {"rollback_steps": 2.0, "blast_radius": 2.0, "canary_gap": 2.0}),
        DO.AlphabetCandidate(0.5, 3.0, {"rollback_steps": 3.0, "blast_radius": 3.0, "canary_gap": 3.0}),
        DO.AlphabetCandidate(0.4, 4.0, {"rollback_steps": 4.0, "blast_radius": 4.0, "canary_gap": 4.0})])


def test_evaluate_alphabet_true_necessary():
    el = InventedPrimitive.of("acc_sumsq", "identity")
    v = DO.evaluate_genesis_alphabet(el, [_true_alphabet_case()], coverage_margin=0.1)
    assert v.incremental_coverage >= 0.1
    assert v.redundancy < v.redundancy_max
    assert v.necessary and v.tier > 0


def test_evaluate_alphabet_noise_rejected_by_coverage():
    noise = InventedPrimitive.of("acc_count", "identity")   # count 恆 3 → 無區辨
    v = DO.evaluate_genesis_alphabet(noise, [_noise_alphabet_case()], coverage_margin=0.1)
    assert v.incremental_coverage < v.coverage_margin
    assert not v.necessary and v.tier == 0


def test_evaluate_alphabet_redundant_rejected_by_redundancy():
    el = InventedPrimitive.of("acc_first", "identity")
    v = DO.evaluate_genesis_alphabet(el, [_redundant_alphabet_case()], coverage_margin=0.1)
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary


def test_alphabet_redundancy_is_independent_gate():
    """即使覆蓋門檻放寬到必過，冗餘字母仍被非冗餘度獨立否決。"""
    el = InventedPrimitive.of("acc_first", "identity")
    v = DO.evaluate_genesis_alphabet(el, [_redundant_alphabet_case()], coverage_margin=-1.0)
    assert v.incremental_coverage >= v.coverage_margin
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary, "冗餘字母須被非冗餘度獨立否決"


def test_alphabet_goodhart_zero_miss():
    """安全紅線：噪音字母 + 冗餘字母攔截零漏放。"""
    assert not DO.evaluate_genesis_alphabet(
        InventedPrimitive.of("acc_count", "identity"), [_noise_alphabet_case()], coverage_margin=0.1).necessary
    assert not DO.evaluate_genesis_alphabet(
        InventedPrimitive.of("acc_first", "identity"), [_redundant_alphabet_case()], coverage_margin=0.1).necessary


def test_necessity_score_alphabet_zero_when_not_necessary():
    el = InventedPrimitive.of("acc_sumsq", "identity")
    assert DO.necessity_score_alphabet(el, [_true_alphabet_case()]) > 0.0
    assert DO.necessity_score_alphabet(
        InventedPrimitive.of("acc_count", "identity"), [_noise_alphabet_case()]) == 0.0


def test_alphabet_genesis_self_passes_but_oracle_rejects():
    """genesis 樸素自評視噪音字母為必要，但 oracle 在 held-out 上否決 → 以 oracle 為準。"""
    noise = InventedPrimitive.of("acc_count", "identity")
    per = AG.alphabet_genesis(lambda e: 0.9, candidates=[noise])
    assert per.accepted, "genesis 樸素自評視之為必要（接縫前提）"
    v = DO.evaluate_genesis_alphabet(noise, [_noise_alphabet_case()], coverage_margin=0.1)
    assert not v.necessary


def test_evaluate_alphabet_replay_bounded():
    corpus = [_true_alphabet_case() for _ in range(100)]
    v = DO.evaluate_genesis_alphabet(InventedPrimitive.of("acc_sumsq", "identity"), corpus, max_cases=5)
    assert v.examined == 5


def test_load_alphabet_corpus_12_cases():
    corpus = DO.load_alphabet_corpus()
    assert len(corpus) >= 12, f"ALG 凍結語料應 >= 12，實得 {len(corpus)}"


def test_load_alphabet_corpus_makes_sumsq_necessary():
    """端到端：載入凍結 ALG 語料 → sumsq 字母在其上必要（feature-grounded）。"""
    corpus = DO.load_alphabet_corpus()
    el = InventedPrimitive.of("acc_sumsq", "identity")
    v = DO.evaluate_genesis_alphabet(el, corpus, coverage_margin=0.1)
    assert v.necessary and v.incremental_coverage >= 0.1


def test_load_alphabet_corpus_rejects_noise():
    """端到端：噪音字母在凍結 ALG 語料上不必要（零漏放）。"""
    corpus = DO.load_alphabet_corpus()
    assert not DO.evaluate_genesis_alphabet(
        InventedPrimitive.of("acc_count", "identity"), corpus, coverage_margin=0.1).necessary


def test_alphabet_corpus_fingerprint_deterministic():
    corpus = DO.load_alphabet_corpus()
    assert DO.alphabet_corpus_fingerprint(corpus) == DO.alphabet_corpus_fingerprint(corpus)


# ---------------------------------------------------------------------------
# ACT-148 — META_FSM 不增第六軌/不增狀態變數（兩新不變量）+ 守門
# ---------------------------------------------------------------------------

def test_meta_fsm_declares_phase_u_invariants():
    """META_FSM.tla 定義 AlphabetGenesisBounded + ComputabilityClosureBounded，.cfg INVARIANT 列入。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal" / "META_FSM.cfg").read_text(encoding="utf-8")
    assert "AlphabetGenesisBounded ==" in tla
    assert "ComputabilityClosureBounded ==" in tla
    assert "AlphabetGenesisBounded" in cfg
    assert "ComputabilityClosureBounded" in cfg


def test_meta_fsm_variables_unchanged_no_new_state():
    """Rule 9.33.4：不新增狀態變數（仍 mstate/churn/cap）→ 本軌 reachable(13 distinct) 不回歸。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert "VARIABLES mstate," in tla
    assert "vars == <<mstate, churn, cap>>" in tla
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla


def test_no_sixth_formal_track():
    """Rule 9.33.4：不增第六軌——formal/ 仍恰 5 個 .tla。"""
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_single_track_no_alphabet_leak():
    """Rule 9.33.4：alphabet-genesis 不污染單軌 SDD_FSM.tla。"""
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "AlphabetGenesis" not in sdd and "alphabet-genesis" not in sdd


def test_alphabet_genesis_namespace_isolation():
    """Rule 9.33.4：alphabet-genesis 與維度/詞彙/算子/calibration 命名空間分開治理。"""
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    assert ML.is_alphabet_genesis_fingerprint("alphabet-genesis:abc")
    assert not ML.is_alphabet_genesis_fingerprint("operator-genesis:abc")
    assert not ML.is_alphabet_genesis_fingerprint("value-dimension:abc")
    assert not ML.is_alphabet_genesis_fingerprint("vocab-genesis:abc")
    assert not ML.is_calibration_fingerprint("alphabet-genesis:abc")
    assert not ML.is_operator_genesis_fingerprint("alphabet-genesis:abc")


def test_dim_alphabet_max_env(monkeypatch):
    monkeypatch.delenv("SDD_DIM_ALPHABET_MAX", raising=False)
    assert MM.dim_alphabet_max() == 16
    monkeypatch.setenv("SDD_DIM_ALPHABET_MAX", "999")
    assert MM.dim_alphabet_max() == 64
    monkeypatch.setenv("SDD_DIM_ALPHABET_MAX", "0")
    assert MM.dim_alphabet_max() == 1


def test_guard_computability_closure_break_nontotal():
    """Rule 9.33.3：閉包破裂（非全函式字母）→ ComputabilityClosureViolation。"""
    bad = InventedPrimitive(base_reducer="evil_unbounded", post_map="identity")
    with pytest.raises(MM.ComputabilityClosureViolation):
        MM.guard_computability_closure(bad)


def test_guard_computability_closure_over_budget(monkeypatch):
    """Rule 9.33.3：閉包步數超界（step_max 壓到 1，G(A') max_cost=3）→ ComputabilityClosureViolation。"""
    monkeypatch.setenv("SDD_DIM_OP_STEP_MAX", "1")
    el = InventedPrimitive.of("acc_sumsq", "identity")
    with pytest.raises(MM.ComputabilityClosureViolation):
        MM.guard_computability_closure(el)


def test_guard_computability_closure_passes_legit():
    el = InventedPrimitive.of("acc_sumsq", "identity")
    r = MM.guard_computability_closure(el)
    assert r.allowed and r.total and r.max_cost <= r.step_max


def test_guard_alphabet_genesis_stock_ceiling(tmp_path, monkeypatch):
    """Rule 9.33.4：字母 stock 觸頂 → AlphabetCardinalityExceeded + meta_state ESCALATION。"""
    monkeypatch.setenv("SDD_DIM_ALPHABET_MAX", "2")
    led = tmp_path / "meta-loop-ledger.yaml"
    reducers = ["acc_sum", "acc_sumsq", "acc_sumabs"]
    for i in range(2):
        AG.adopt_genesis_alphabet(InventedPrimitive.of(reducers[i], "identity"), 40 + i,
                                  human_signoff=True, ledger_path=led)
    assert MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"
    with pytest.raises(MM.AlphabetCardinalityExceeded):
        AG.adopt_genesis_alphabet(InventedPrimitive.of(reducers[2], "identity"), 99,
                                  human_signoff=True, ledger_path=led)


def test_adopt_alphabet_happy_path(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    el = InventedPrimitive.of("acc_sumsq", "identity")
    ev = AG.adopt_genesis_alphabet(el, 70, human_signoff=True, ledger_path=led)
    assert ev.fingerprint == el.fingerprint()
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    assert el.fingerprint() in ML.active_alphabet_genesis_features(ledger_path=led)


# ---------------------------------------------------------------------------
# ACT-149 — steersman 字母表外發明 diff + 可計算性閉包證據（advisory + 反 big-bang + 人工 gate）
# ---------------------------------------------------------------------------

def _accepted_alphabet_round(k=1):
    cands = AG.enumerate_genesis_alphabet(budget=30)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda e: scores.get(e.name, 0.0)
    return AG.alphabet_genesis_round(ev, candidates=cands, k=k)


def test_render_alphabet_genesis_proposal():
    from tools.fsm_runtime.steersman_renderer import render_alphabet_genesis_proposal
    rnd = _accepted_alphabet_round(k=1)
    verdict = DO.evaluate_genesis_alphabet(
        InventedPrimitive.of("acc_sumsq", "identity"), [_true_alphabet_case()], coverage_margin=0.1)
    md = render_alphabet_genesis_proposal(rnd, verdict=verdict)
    assert "Self-Expanding Operator Alphabet" in md
    assert "字母表外" in md
    assert "K_alpha=1" in md
    assert "signoff" in md and "待人工" in md
    assert "閉包" in md and "max_cost" in md          # 可計算性閉包證據
    assert "非自指" in md
    assert verdict.corpus_fingerprint in md
    assert rnd.selected[0].element.name in md


def test_render_alphabet_genesis_shows_deferred_under_bigbang():
    from tools.fsm_runtime.steersman_renderer import render_alphabet_genesis_proposal
    rnd = _accepted_alphabet_round(k=1)
    md = render_alphabet_genesis_proposal(rnd)
    assert "K_alpha=1" in md
    assert rnd.deferred[0] in md


def test_render_alphabet_genesis_never_auto_commits():
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_alphabet_genesis_proposal)
    assert "record_rule_add" not in src and "adopt_genesis_alphabet" not in src


def test_render_alphabet_genesis_no_verdict_degrades():
    from tools.fsm_runtime.steersman_renderer import render_alphabet_genesis_proposal
    md = render_alphabet_genesis_proposal(_accepted_alphabet_round(k=1))
    assert "字母表外" in md and "待人工" in md


# ---------------------------------------------------------------------------
# ACT-149 — chaos 雙故障型 deterministic bounded（單元層；100 輪整合在 chaos 套件）
# ---------------------------------------------------------------------------

def test_chaos_alphabet_genesis_goodhart_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _alphabet_genesis_goodhart_flap_is_bounded
    assert _alphabet_genesis_goodhart_flap_is_bounded()


def test_chaos_computability_closure_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _computability_closure_flap_is_bounded
    assert _computability_closure_flap_is_bounded()


def test_chaos_new_fault_types_registered():
    from tools.fsm_runtime.chaos_runner import FAULT_TYPES
    assert "ALPHABET_GENESIS_GOODHART_FLAP" in FAULT_TYPES
    assert "COMPUTABILITY_CLOSURE_FLAP" in FAULT_TYPES


# ---------------------------------------------------------------------------
# Phase U ownership（R-9.33 enforces 連結）
# ---------------------------------------------------------------------------

def test_phase_u_enforces_rule_9_33():
    """本檔頭 `# enforces (governance rules): R-9.33` 連結 Phase U 守門至 R-9.33。"""
    head = (ROOT / "tests" / "test_phase_u.py").read_text(encoding="utf-8").splitlines()[0]
    assert head == "# enforces (governance rules): R-9.33"
