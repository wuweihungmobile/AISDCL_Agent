# enforces (governance rules): R-9.34
"""Phase V / ACT-150~152 — 算子組合深度文法自我擴充（meta⁷）+ 深度可計算性閉包回歸守門.

涵蓋：
  - ACT-150 Operator Depth Genesis Grammar：深度 <=2 外有界深度生成文法（可枚舉、cap budget、深度 >=3 且
    <= depth_limit、結構性 total + cost==depth + 零遞迴零迴圈）、深度可計算性閉包 verify_depth_closure
    （擴充深度後 G(A,depth) 整代數 total + 有界步數）、深度自指 depth_self_reference_guard 零漏放、deterministic、
    只透過注入 evaluate 取必要性（結構性無自評）、proposed-only、反 big-bang K_depth=1 截斷、對抗分離
    （不 import oracle）、expanded_depth_ops
  - ACT-151 feature-grounded 必要性 oracle：evaluate_genesis_depth（不靠算子名）、深度外真必要偵出、
    深度自我發明 Goodhart（噪音算子+冗餘算子）零漏放、necessity tier 唯一來源、隔離、DPT 凍結語料；
    深度 stock DepthGenesisBounded + 深度可計算性閉包 DepthClosureBounded（深度超界/非全函式→
    DepthClosureViolation、深度算子基數觸頂→DepthCardinalityExceeded→MFSM_ESCALATION）、
    META_FSM 不增第六軌/不增狀態變數
  - ACT-152 steersman 深度外發明 diff + 深度可計算性閉包證據（advisory + 反 big-bang + 人工 gate）+
    chaos DEPTH_GENESIS_GOODHART_FLAP / DEPTH_CLOSURE_FLAP 有界
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from tools.fsm_runtime import operator_depth_genesis as DG
from tools.fsm_runtime import dimension_necessity_oracle as DO
from tools.fsm_runtime.operator_depth_genesis import DepthOperator
from tools.fsm_runtime.operator_genesis import GenesisOperator
from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM

ROOT = Path(__file__).resolve().parent.parent


def _sum4() -> DepthOperator:
    """標準真必要深度算子：sq(sq(sum)) = sum⁴（深度-3，兩個堆疊 sq，非深度-2 可表達；正單調遞增）。"""
    return DepthOperator.of(GenesisOperator.of("sum", "sq"), ["sq"])


# ---------------------------------------------------------------------------
# ACT-150 — Depth Genesis Grammar（深度 <=2 外有界深度生成文法 + 深度自指守門 + 閉包，meta⁷）
# ---------------------------------------------------------------------------

def test_enumerate_depth_bounded():
    """Rule 9.34.1 有界深度生成文法：枚舉節點 <= budget（深度 <=2 外≠無界）。"""
    assert len(DG.enumerate_genesis_depth(budget=10)) == 10
    assert len(DG.enumerate_genesis_depth(budget=1)) == 1
    full = len(DG.enumerate_genesis_depth(budget=100000))
    assert 0 < full < 100000


def test_enumerate_depth_deterministic():
    a = DG.enumerate_genesis_depth(budget=30)
    b = DG.enumerate_genesis_depth(budget=30)
    assert [e.name for e in a] == [e.name for e in b]


def test_enumerate_depth_all_depth_ge_3_le_limit():
    """每個產出皆深度 >2（chain 非空）且 <= depth_limit（Rule 9.34.1）。"""
    lim = DG.depth_limit()
    cands = DG.enumerate_genesis_depth(budget=100000)
    assert cands
    assert all(c.depth() >= 3 for c in cands)
    assert all(c.depth() <= lim for c in cands)


def test_depth_operator_name_cost_fingerprint():
    op = _sum4()
    assert op.name == "depth::sq(sq(sum))@rollback_steps+blast_radius+canary_gap|d=3"
    assert op.depth() == 3
    assert op.cost() == 3
    fp = op.fingerprint()
    assert fp.startswith("depth-genesis:")
    assert op.fingerprint() != DepthOperator.of(GenesisOperator.of("mean", "sq"), ["sq"]).fingerprint()


def test_depth_operator_cost_equals_depth():
    """Rule 9.34.3 核心：cost==depth（一元基底）/ depth+1（二元基底）——深度就是步數。"""
    unary = DepthOperator.of(GenesisOperator.of("sum", "sq"), ["sq", "abs"])      # 一元基底 sq(sum)
    assert unary.cost() == unary.depth()
    binary = DepthOperator.of(GenesisOperator.of("max", "diff", secondary="min"), ["sq"])  # 二元基底
    assert binary.cost() == binary.depth() + 1


def test_depth_closure_over_all_candidates_total_bounded():
    """Rule 9.34.3 深度可計算性閉包：對每個候選深度算子，擴充深度後 G(A,depth) 整代數 total + max_cost<=step_max。"""
    step_max = MM.dim_op_step_max()
    for e in DG.enumerate_genesis_depth(budget=100000):
        rep = DG.verify_depth_closure(e)
        assert rep.total, f"深度算子 {e.name} 破壞閉包全函式"
        assert rep.max_cost <= step_max, f"深度算子 {e.name} 破壞閉包有界步數"
        assert rep.n_operators > 0
        # 因 cost==depth（一元基底），整代數 max_cost 與深度線性相關（深度<=limit → cost 有界）
        assert rep.max_cost <= DG.depth_limit() + 1


def test_closure_detects_non_total_element():
    """Rule 9.34.3：非全函式深度算子（chain 含未知 combinator → apply 拋例外）→ 閉包 total=False。"""
    bad = DepthOperator.of(GenesisOperator.of("sum", "sq"), ["evil_unbounded"])
    assert DG.verify_depth_closure(bad).total is False


def test_depth_apply_is_total_fuzz():
    """Rule 9.34.3 全函式：對極端輸入 fuzz，深度算子 apply 永不拋例外、無 NaN/inf。"""
    extreme = [[], [0.0], [-5.0], [1e18, -1e18], [0.0, 0.0, 0.0], [1e-18], [1e308], [1e308, 1e308]]
    for e in DG.enumerate_genesis_depth(budget=100000):
        for vals in extreme:
            feats = {f: (vals[i] if i < len(vals) else 0.0) for i, f in enumerate(e.probe)}
            r = e.apply(feats)
            assert r == r and r not in (float("inf"), float("-inf"))


def test_depth_eval_path_no_while_no_recursion():
    """Rule 9.34.3 零遞迴零迴圈：深度求值路徑（apply/cost/depth）無 while、無自呼叫（唯一 for 是有界鏈走訪）。"""
    src = (ROOT / "operator_depth_genesis.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    targets = {"apply", "cost", "depth"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in targets:
            for sub in ast.walk(node):
                assert not isinstance(sub, ast.While), f"{node.name} 含 while（破可計算性零迴圈）"
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    assert sub.func.id != node.name, f"{node.name} 自呼叫（破可計算性零遞迴）"


def test_depth_self_reference_guard_zero_miss():
    """Rule 9.34.2 反自利第一閘：任何 base/chain/probe 自指 → 結構性丟棄。"""
    decoys = [
        DepthOperator.of(GenesisOperator.of("sum", "sq"), ["sq"],
                         probe=["self_score", "blast_radius", "canary_gap"]),
        DepthOperator.of(GenesisOperator.of("sum", "sq", probe=["proposer_x", "y", "z"]), ["sq"]),
        DepthOperator.of(GenesisOperator.of("sum", "sq"), ["necessity"]),
        DepthOperator.of(GenesisOperator.of("sum", "sq"), ["oracle_score"]),
    ]
    for d in decoys:
        assert DG.is_depth_self_referential(d)
    kept = DG.depth_self_reference_guard(decoys + [_sum4()])
    assert len(kept) == 1 and not DG.is_depth_self_referential(kept[0])


def test_enumerate_excludes_self_referential():
    """生產 base/chain/probe 無自指 token → 枚舉恆無自指深度算子。"""
    assert all(not DG.is_depth_self_referential(e)
               for e in DG.enumerate_genesis_depth(budget=100000))


def test_depth_genesis_only_via_injected_evaluate():
    """Rule 9.34.2 對抗分離：genesis 只呼叫注入 evaluate、結構性無自評。"""
    seen = {}
    def ev(e):
        seen[e.name] = seen.get(e.name, 0) + 1
        return 0.5 if e.name == _sum4().name else 0.0
    cands = list(DG.enumerate_genesis_depth(budget=40)) + [_sum4()]
    prop = DG.depth_genesis(ev, candidates=cands)
    assert prop.operator is not None and prop.accepted
    assert prop.operator.name == _sum4().name
    assert seen, "genesis 必須透過注入 evaluate 取必要性"


def test_depth_genesis_isolation_from_oracle():
    """Rule 9.34.2 對抗分離：operator_depth_genesis 結構性不 import oracle、不讀必要性語料。"""
    src = (ROOT / "operator_depth_genesis.py").read_text(encoding="utf-8")
    assert "dimension_necessity_oracle" not in src
    assert "load_depth_corpus" not in src
    assert "held-out-corpus" not in src


def test_depth_genesis_round_k_truncation():
    """Rule 9.34.4 反 big-bang：一輪至多 K_depth 個，其餘順延。"""
    cands = DG.enumerate_genesis_depth(budget=30)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda e: scores.get(e.name, 0.0)
    rnd = DG.depth_genesis_round(ev, candidates=cands, k=1)
    assert len(rnd.selected) == 1
    assert rnd.selected[0].operator.name == cands[0].name
    assert len(rnd.deferred) == 2


def test_expanded_depth_ops():
    base = DG.expanded_depth_ops([])
    assert base == ()
    grown = DG.expanded_depth_ops([_sum4().name, _sum4().name])   # 去重
    assert grown == (_sum4().name,)


def test_adopt_depth_requires_signoff():
    with pytest.raises(DG.SignoffRequired):
        DG.adopt_genesis_depth(_sum4(), 50, human_signoff=False)


def test_adopt_depth_rejects_self_referential():
    e = DepthOperator.of(GenesisOperator.of("sum", "sq"), ["sq"],
                         probe=["self_score", "x", "y"])
    with pytest.raises(DG.SelfReferentialDepth):
        DG.adopt_genesis_depth(e, 50, human_signoff=True)


# ---------------------------------------------------------------------------
# ACT-151 — feature-grounded 深度必要性 oracle（evaluate_genesis_depth，反 Goodhart）
# ---------------------------------------------------------------------------

def _C(q, cost, f):
    return DO.DepthCandidate(q, cost, {"rollback_steps": float(f[0]), "blast_radius": float(f[1]),
                                       "canary_gap": float(f[2])})


def _true_depth_case():
    # 反相關：A 高 sum/低品質/最低 cost（baseline 誤選）；B 低 sum/高品質/高 cost（sum⁴ 救回）；C 中。
    return DO.DepthCase("T", [_C(0.45, 2.0, (9, 8, 7)), _C(0.87, 5.0, (1, 1, 2)), _C(0.62, 3.0, (4, 3, 3))])


def _noise_depth_case():
    return DO.DepthCase("N", [_C(0.6, 2.0, (5, 5, 5)), _C(0.6, 3.0, (0, 0, 0)), _C(0.4, 4.0, (8, 8, 8))])


def _redundant_depth_case():
    # canary_gap 與 existing_cost 同序遞增 → sq(sq(last)) 的 dim_value 與 existing_cost 排序一致 → 冗餘
    return DO.DepthCase("R", [_C(0.6, 2.0, (2, 2, 2)), _C(0.5, 3.0, (3, 3, 3)), _C(0.4, 4.0, (4, 4, 4))])


def _redundant_op():
    return DepthOperator.of(GenesisOperator.of("last", "sq"), ["sq"])   # sq(sq(canary_gap))


def _noise_op():
    # clip01(sq(sum))：sum² 對所有候選皆 >1 → clip01 飽和成常數 1.0（零區辨、零增量覆蓋），
    # 在 DPT 反相關語料與 _noise_depth_case 上皆無增量；仍真正需要深度-3（sq 後 clip01，不可塌縮成深度-2）。
    return DepthOperator.of(GenesisOperator.of("sum", "sq"), ["clip01"])


def test_evaluate_depth_true_necessary():
    v = DO.evaluate_genesis_depth(_sum4(), [_true_depth_case()], coverage_margin=0.1)
    assert v.incremental_coverage >= 0.1
    assert v.redundancy < v.redundancy_max
    assert v.necessary and v.tier > 0


def test_evaluate_depth_noise_rejected_by_coverage():
    v = DO.evaluate_genesis_depth(_noise_op(), [_noise_depth_case()], coverage_margin=0.1)
    assert v.incremental_coverage < v.coverage_margin
    assert not v.necessary and v.tier == 0


def test_evaluate_depth_redundant_rejected_by_redundancy():
    v = DO.evaluate_genesis_depth(_redundant_op(), [_redundant_depth_case()], coverage_margin=0.1)
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary


def test_depth_redundancy_is_independent_gate():
    """即使覆蓋門檻放寬到必過，冗餘深度算子仍被非冗餘度獨立否決。"""
    v = DO.evaluate_genesis_depth(_redundant_op(), [_redundant_depth_case()], coverage_margin=-1.0)
    assert v.incremental_coverage >= v.coverage_margin
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary, "冗餘深度算子須被非冗餘度獨立否決"


def test_depth_goodhart_zero_miss():
    """安全紅線：噪音深度算子 + 冗餘深度算子攔截零漏放。"""
    assert not DO.evaluate_genesis_depth(_noise_op(), [_noise_depth_case()], coverage_margin=0.1).necessary
    assert not DO.evaluate_genesis_depth(_redundant_op(), [_redundant_depth_case()], coverage_margin=0.1).necessary


def test_necessity_score_depth_zero_when_not_necessary():
    assert DO.necessity_score_depth(_sum4(), [_true_depth_case()]) > 0.0
    assert DO.necessity_score_depth(_noise_op(), [_noise_depth_case()]) == 0.0


def test_depth_genesis_self_passes_but_oracle_rejects():
    """genesis 樸素自評視噪音深度算子為必要，但 oracle 在 held-out 上否決 → 以 oracle 為準。"""
    noise = _noise_op()
    per = DG.depth_genesis(lambda e: 0.9, candidates=[noise])
    assert per.accepted, "genesis 樸素自評視之為必要（接縫前提）"
    v = DO.evaluate_genesis_depth(noise, [_noise_depth_case()], coverage_margin=0.1)
    assert not v.necessary


def test_evaluate_depth_replay_bounded():
    corpus = [_true_depth_case() for _ in range(100)]
    v = DO.evaluate_genesis_depth(_sum4(), corpus, max_cases=5)
    assert v.examined == 5


def test_load_depth_corpus_12_cases():
    corpus = DO.load_depth_corpus()
    assert len(corpus) >= 12, f"DPT 凍結語料應 >= 12，實得 {len(corpus)}"


def test_load_depth_corpus_makes_sum4_necessary():
    """端到端：載入凍結 DPT 語料 → sum⁴ 深度算子在其上必要（feature-grounded）。"""
    corpus = DO.load_depth_corpus()
    v = DO.evaluate_genesis_depth(_sum4(), corpus, coverage_margin=0.1)
    assert v.necessary and v.incremental_coverage >= 0.1


def test_load_depth_corpus_rejects_noise():
    """端到端：噪音深度算子在凍結 DPT 語料上不必要（零漏放）。"""
    corpus = DO.load_depth_corpus()
    assert not DO.evaluate_genesis_depth(_noise_op(), corpus, coverage_margin=0.1).necessary


def test_depth_corpus_fingerprint_deterministic():
    corpus = DO.load_depth_corpus()
    assert DO.depth_corpus_fingerprint(corpus) == DO.depth_corpus_fingerprint(corpus)


# ---------------------------------------------------------------------------
# ACT-151 — META_FSM 不增第六軌/不增狀態變數（兩新不變量）+ 守門
# ---------------------------------------------------------------------------

def test_meta_fsm_declares_phase_v_invariants():
    """META_FSM.tla 定義 DepthGenesisBounded + DepthClosureBounded，.cfg INVARIANT 列入。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal" / "META_FSM.cfg").read_text(encoding="utf-8")
    assert "DepthGenesisBounded ==" in tla
    assert "DepthClosureBounded ==" in tla
    assert "DepthGenesisBounded" in cfg
    assert "DepthClosureBounded" in cfg


def test_meta_fsm_variables_unchanged_no_new_state():
    """Rule 9.34.4：不新增狀態變數（仍 mstate/churn/cap）→ 本軌 reachable(13 distinct) 不回歸。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert "VARIABLES mstate," in tla
    assert "vars == <<mstate, churn, cap>>" in tla
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla


def test_no_sixth_formal_track():
    """Rule 9.34.4：不增第六軌——formal/ 仍恰 5 個 .tla。"""
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_single_track_no_depth_leak():
    """Rule 9.34.4：depth-genesis 不污染單軌 SDD_FSM.tla。"""
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "DepthGenesis" not in sdd and "depth-genesis" not in sdd


def test_depth_genesis_namespace_isolation():
    """Rule 9.34.4：depth-genesis 與維度/詞彙/算子/字母/calibration 命名空間分開治理。"""
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    assert ML.is_depth_genesis_fingerprint("depth-genesis:abc")
    assert not ML.is_depth_genesis_fingerprint("alphabet-genesis:abc")
    assert not ML.is_depth_genesis_fingerprint("operator-genesis:abc")
    assert not ML.is_depth_genesis_fingerprint("value-dimension:abc")
    assert not ML.is_depth_genesis_fingerprint("vocab-genesis:abc")
    assert not ML.is_calibration_fingerprint("depth-genesis:abc")
    assert not ML.is_alphabet_genesis_fingerprint("depth-genesis:abc")


def test_dim_depth_max_env(monkeypatch):
    monkeypatch.delenv("SDD_DIM_DEPTH_MAX", raising=False)
    assert MM.dim_depth_max() == 16
    monkeypatch.setenv("SDD_DIM_DEPTH_MAX", "999")
    assert MM.dim_depth_max() == 64
    monkeypatch.setenv("SDD_DIM_DEPTH_MAX", "0")
    assert MM.dim_depth_max() == 1


def test_guard_depth_closure_break_nontotal():
    """Rule 9.34.3：閉包破裂（非全函式深度算子）→ DepthClosureViolation。"""
    bad = DepthOperator.of(GenesisOperator.of("sum", "sq"), ["evil_unbounded"])
    with pytest.raises(MM.DepthClosureViolation):
        MM.guard_depth_closure(bad)


def test_guard_depth_closure_over_budget(monkeypatch):
    """Rule 9.34.3：深度超界（step_max 壓到 2，深度-3 算子 cost==3）→ DepthClosureViolation（因 cost==depth）。"""
    monkeypatch.setenv("SDD_DIM_OP_STEP_MAX", "2")
    with pytest.raises(MM.DepthClosureViolation):
        MM.guard_depth_closure(_sum4())


def test_guard_depth_closure_passes_legit():
    r = MM.guard_depth_closure(_sum4())
    assert r.allowed and r.total and r.max_cost <= r.step_max


def test_guard_depth_genesis_stock_ceiling(tmp_path, monkeypatch):
    """Rule 9.34.4：深度算子 stock 觸頂 → DepthCardinalityExceeded + meta_state ESCALATION。"""
    monkeypatch.setenv("SDD_DIM_DEPTH_MAX", "2")
    led = tmp_path / "meta-loop-ledger.yaml"
    ops = [
        DepthOperator.of(GenesisOperator.of("sum", "sq"), ["sq"]),
        DepthOperator.of(GenesisOperator.of("mean", "sq"), ["sq"]),
        DepthOperator.of(GenesisOperator.of("max", "sq"), ["sq"]),
    ]
    for i in range(2):
        DG.adopt_genesis_depth(ops[i], 40 + i, human_signoff=True, ledger_path=led)
    assert MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"
    with pytest.raises(MM.DepthCardinalityExceeded):
        DG.adopt_genesis_depth(ops[2], 99, human_signoff=True, ledger_path=led)


def test_adopt_depth_happy_path(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    op = _sum4()
    ev = DG.adopt_genesis_depth(op, 70, human_signoff=True, ledger_path=led)
    assert ev.fingerprint == op.fingerprint()
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    assert op.fingerprint() in ML.active_depth_genesis_features(ledger_path=led)


# ---------------------------------------------------------------------------
# ACT-152 — steersman 深度外發明 diff + 深度可計算性閉包證據（advisory + 反 big-bang + 人工 gate）
# ---------------------------------------------------------------------------

def _accepted_depth_round(k=1):
    cands = DG.enumerate_genesis_depth(budget=30)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda e: scores.get(e.name, 0.0)
    return DG.depth_genesis_round(ev, candidates=cands, k=k)


def test_render_depth_genesis_proposal():
    from tools.fsm_runtime.steersman_renderer import render_depth_genesis_proposal
    rnd = _accepted_depth_round(k=1)
    verdict = DO.evaluate_genesis_depth(_sum4(), [_true_depth_case()], coverage_margin=0.1)
    md = render_depth_genesis_proposal(rnd, verdict=verdict)
    assert "Self-Expanding Operator Depth" in md
    assert "深度外" in md
    assert "K_depth=1" in md
    assert "signoff" in md and "待人工" in md
    assert "閉包" in md and "max_cost" in md          # 深度可計算性閉包證據
    assert "非自指" in md
    assert verdict.corpus_fingerprint in md
    assert rnd.selected[0].operator.name in md


def test_render_depth_genesis_shows_deferred_under_bigbang():
    from tools.fsm_runtime.steersman_renderer import render_depth_genesis_proposal
    rnd = _accepted_depth_round(k=1)
    md = render_depth_genesis_proposal(rnd)
    assert "K_depth=1" in md
    assert rnd.deferred[0] in md


def test_render_depth_genesis_never_auto_commits():
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_depth_genesis_proposal)
    assert "record_rule_add" not in src and "adopt_genesis_depth" not in src


def test_render_depth_genesis_no_verdict_degrades():
    from tools.fsm_runtime.steersman_renderer import render_depth_genesis_proposal
    md = render_depth_genesis_proposal(_accepted_depth_round(k=1))
    assert "深度外" in md and "待人工" in md


# ---------------------------------------------------------------------------
# ACT-152 — chaos 雙故障型 deterministic bounded（單元層；100 輪整合在 chaos 套件）
# ---------------------------------------------------------------------------

def test_chaos_depth_genesis_goodhart_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _depth_genesis_goodhart_flap_is_bounded
    assert _depth_genesis_goodhart_flap_is_bounded()


def test_chaos_depth_closure_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _depth_closure_flap_is_bounded
    assert _depth_closure_flap_is_bounded()


def test_chaos_new_fault_types_registered():
    from tools.fsm_runtime.chaos_runner import FAULT_TYPES
    assert "DEPTH_GENESIS_GOODHART_FLAP" in FAULT_TYPES
    assert "DEPTH_CLOSURE_FLAP" in FAULT_TYPES


# ---------------------------------------------------------------------------
# Phase V ownership（R-9.34 enforces 連結）
# ---------------------------------------------------------------------------

def test_phase_v_enforces_rule_9_34():
    """本檔頭 `# enforces (governance rules): R-9.34` 連結 Phase V 守門至 R-9.34。"""
    head = (ROOT / "tests" / "test_phase_v.py").read_text(encoding="utf-8").splitlines()[0]
    assert head == "# enforces (governance rules): R-9.34"
