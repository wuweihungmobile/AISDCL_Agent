# enforces (governance rules): R-9.35
"""Phase W / ACT-153~155 — 算子間互遞迴文法自我擴充（meta⁸）+ 良基停機證書回歸守門.

涵蓋：
  - ACT-153 Operator Recursion Genesis Grammar：非遞迴外有界互遞迴生成文法（可枚舉、cap budget、呼叫圖
    節點 <= recur_nodes、結構性可證良基終止 + fuel<=step_max + 求值器零真遞迴零 while）、良基停機證書
    verify_recursion_closure（整代數 total + 可證終止 + fuel<=step_max）、互遞迴自指 recursion_self_reference_guard
    零漏放、deterministic、只透過注入 evaluate 取必要性（結構性無自評）、proposed-only、反 big-bang K_recur=1
    截斷、對抗分離（不 import oracle）、expanded_recursion_ops
  - ACT-154 feature-grounded 必要性 oracle：evaluate_genesis_recursion（不靠算子名）、互遞迴外真必要偵出、
    互遞迴自我發明 Goodhart（噪音算子+冗餘算子）零漏放、necessity tier 唯一來源、隔離、RCR 凍結語料；
    互遞迴 stock RecursionGenesisBounded + 良基停機證書 RecursionClosureBounded（無證書環/fuel 超界/非全函式→
    RecursionClosureViolation、互遞迴算子基數觸頂→RecursionCardinalityExceeded→MFSM_ESCALATION）、
    META_FSM 不增第六軌/不增狀態變數
  - ACT-155 steersman 互遞迴外發明 diff + 良基停機證書證據（advisory + 反 big-bang + 人工 gate）+
    chaos RECURSION_GENESIS_GOODHART_FLAP / RECURSION_CLOSURE_FLAP 有界
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from tools.fsm_runtime import operator_recursion_genesis as RG
from tools.fsm_runtime import dimension_necessity_oracle as DO
from tools.fsm_runtime.operator_recursion_genesis import RecursiveOperator, RecursionNode
from tools.fsm_runtime.operator_genesis import GenesisOperator
from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM

ROOT = Path(__file__).resolve().parent.parent


def _recsum4() -> RecursiveOperator:
    """標準真必要互遞迴算子：2-node mul-fold of sq(sum)，沿 rank 遞減呼叫圖計算 (Σ)²×(Σ)²=sum⁴.

    這是「真互遞迴的最小可證良基終止形態」——node0(rank1) 呼叫 node1(rank0)，呼叫圖良基（DAG），
    語意等價 Phase V 的 sum⁴ 深度算子，但由**算子互相呼叫的呼叫圖**而非深度鏈表達。
    """
    return RecursiveOperator.chain(GenesisOperator.of("sum", "sq"), 2, combine="mul")


# ---------------------------------------------------------------------------
# ACT-153 — Recursion Genesis Grammar（非遞迴外有界互遞迴生成文法 + 互遞迴自指守門 + 良基停機證書，meta⁸）
# ---------------------------------------------------------------------------

def test_enumerate_recursion_bounded():
    """Rule 9.35.1 有界互遞迴生成文法：枚舉節點 <= budget（非遞迴外≠無界）。"""
    assert len(RG.enumerate_genesis_recursion(budget=10)) == 10
    assert len(RG.enumerate_genesis_recursion(budget=1)) == 1
    full = len(RG.enumerate_genesis_recursion(budget=100000))
    assert 0 < full < 100000


def test_enumerate_recursion_deterministic():
    a = RG.enumerate_genesis_recursion(budget=30)
    b = RG.enumerate_genesis_recursion(budget=30)
    assert [e.name for e in a] == [e.name for e in b]


def test_enumerate_recursion_all_terminating_total():
    """每個產出皆可證良基終止（DAG）+ 全函式 + fuel<=step_max（Rule 9.35.1/9.35.3）。"""
    step_max = MM.dim_op_step_max()
    cands = RG.enumerate_genesis_recursion(budget=100000)
    assert cands
    for c in cands:
        cert = c.termination_certificate()
        assert cert.terminating and cert.acyclic
        assert c.is_total()
        assert c._fuel() <= step_max
        assert c.n_nodes() >= 2


def test_recursion_branching_call_graph_terminating():
    """meta⁸ 真互遞迴呼叫圖：一個算子**同時呼叫多個**其他算子（分支/共享，Phase V 線性深度鏈表達不出）.

    fan(base, width=2)：entry(rank1) 呼叫 2 個 sink(rank0)，結果由 fold 組合。呼叫圖帶良基 ranking function
    （每邊 rank 1→0 嚴格遞減），證書通過、全函式、fuel<=step_max。
    """
    op = RecursiveOperator.fan(GenesisOperator.of("sum", "sq"), 2, combine="mul")
    assert op.n_nodes() == 3
    assert len(op.nodes[0].calls) == 2, "entry 算子須同時呼叫多個（分支呼叫圖，非線性鏈）"
    cert = op.termination_certificate()
    assert cert.terminating and cert.well_founded and cert.acyclic
    assert op.is_total()
    assert op.cost() <= MM.dim_op_step_max()
    rep = RG.verify_recursion_closure(op)
    assert rep.total and rep.terminating
    # 分支呼叫圖算出的值與單一非遞迴 base 不同（mul-fold 三節點 = base^3 量級，需呼叫圖表達）。
    feats = {"rollback_steps": 2.0, "blast_radius": 1.0, "canary_gap": 1.0}  # sum=4 -> sq=16 -> 16*16*16
    assert op.apply(feats) == 16.0 ** 3


def test_well_founded_ranking_function_gates_certificate():
    """M-1 修復守門：ranking function（well_founded）真正 gating——非遞減 rank 邊即使無環也判不可證終止。

    node0(rank0) 呼叫 node1(rank1)：邊 0→1 的 rank 上升（無 ranking function），但圖無環（acyclic=True）。
    舊實作 terminating=acyclic=True 會誤放；修復後 terminating 須納入 well_founded → False（拒絕）。
    """
    base = GenesisOperator.of("sum", "sq")
    no_ranking = RecursiveOperator(
        nodes=(RecursionNode(base, 0, (1,)), RecursionNode(base, 1, ())), entry=0, fuel=2, combine="mul")
    cert = no_ranking.termination_certificate()
    assert cert.acyclic is True, "此圖確實無環（隔離 well_founded gating）"
    assert cert.well_founded is False, "邊 0→1 rank 上升 → 無良基 ranking function"
    assert cert.terminating is False, "M-1：無 ranking function 即須判不可證終止（well_founded 真 gating）"
    with pytest.raises(MM.RecursionClosureViolation):
        MM.guard_recursion_closure(no_ranking)


def test_recursion_operator_name_cost_fingerprint():
    op = _recsum4()
    assert op.name.startswith("rec::mul[")
    assert op.n_nodes() == 2
    assert op.cost() == 2
    fp = op.fingerprint()
    assert fp.startswith("recursion-genesis:")
    assert op.fingerprint() != RecursiveOperator.chain(
        GenesisOperator.of("mean", "sq"), 2, combine="mul").fingerprint()


def test_recursion_cost_equals_fuel():
    """Rule 9.35.3：cost == fuel（== 良基測度上界）——互遞迴步數由良基測度終止界定，而非有界步數靜態量。"""
    two = RG.RecursiveOperator.chain(GenesisOperator.of("sum", "sq"), 2, combine="mul")
    assert two.cost() == two._fuel() == 2
    three = RG.RecursiveOperator.chain(GenesisOperator.of("sum", "sq"), 3, combine="mul")
    assert three.cost() == three._fuel() == 3


def test_recursion_closure_over_all_candidates_total_bounded():
    """Rule 9.35.3 良基停機證書：每個候選互遞迴算子，整代數 total + 可證終止 + max_cost<=step_max。"""
    step_max = MM.dim_op_step_max()
    for e in RG.enumerate_genesis_recursion(budget=100000):
        rep = RG.verify_recursion_closure(e)
        assert rep.total, f"互遞迴算子 {e.name} 破壞閉包全函式"
        assert rep.terminating, f"互遞迴算子 {e.name} 不可證良基終止"
        assert rep.max_cost <= step_max, f"互遞迴算子 {e.name} fuel 超界"
        assert rep.n_operators > 0


def test_closure_detects_uncertified_cycle():
    """Rule 9.35.3：無證書環互遞迴算子（含環、無回邊遞減下有界 rank）→ 證書 terminating=False。"""
    base = GenesisOperator.of("sum", "sq")
    cyclic = RecursiveOperator(nodes=(RecursionNode(base, 0, (1,)), RecursionNode(base, 0, (0,))),
                               entry=0, fuel=2, combine="mul")
    cert = cyclic.termination_certificate()
    assert cert.terminating is False and cert.acyclic is False
    assert RG.verify_recursion_closure(cyclic).terminating is False


def test_recursion_apply_is_total_fuzz():
    """Rule 9.35.3 全函式：對極端輸入 fuzz，互遞迴算子 apply 永不拋例外、無 NaN/inf。"""
    extreme = [[], [0.0], [-5.0], [1e18, -1e18], [0.0, 0.0, 0.0], [1e-18], [1e308], [1e308, 1e308]]
    for e in RG.enumerate_genesis_recursion(budget=100000):
        for vals in extreme:
            feats = {f: (vals[i] if i < len(vals) else 0.0) for i, f in enumerate(e.probe)}
            r = e.apply(feats)
            assert r == r and r not in (float("inf"), float("-inf"))


def test_recursion_eval_path_no_while_no_recursion():
    """Rule 9.35.3 求值器零真遞迴零 while：互遞迴求值路徑（apply/cost）無 while、無自呼叫（唯一 for 是有界 fuel 工作集）。"""
    src = (ROOT / "operator_recursion_genesis.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    targets = {"apply", "cost"}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in targets:
            for sub in ast.walk(node):
                assert not isinstance(sub, ast.While), f"{node.name} 含 while（破求值器零迴圈）"
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                    assert sub.func.id != node.name, f"{node.name} 自呼叫（破求值器零真遞迴）"


def test_recursion_self_reference_guard_zero_miss():
    """Rule 9.35.2 反自利第一閘：任何 node base/probe 自指 → 結構性丟棄。"""
    decoys = [
        RecursiveOperator.chain(GenesisOperator.of("sum", "sq"), 2, combine="mul",
                                probe=["self_score", "blast_radius", "canary_gap"]),
        RecursiveOperator.chain(GenesisOperator.of("sum", "sq", probe=["proposer_x", "y", "z"]), 2,
                                combine="mul"),
        RecursiveOperator(nodes=(RecursionNode(GenesisOperator.of("necessity"), 1, (1,)),
                                 RecursionNode(GenesisOperator.of("sum"), 0, ())), entry=0, fuel=2),
    ]
    for d in decoys:
        assert RG.is_recursion_self_referential(d)
    kept = RG.recursion_self_reference_guard(decoys + [_recsum4()])
    assert len(kept) == 1 and not RG.is_recursion_self_referential(kept[0])


def test_enumerate_excludes_self_referential():
    """生產 node base/probe 無自指 token → 枚舉恆無自指互遞迴算子。"""
    assert all(not RG.is_recursion_self_referential(e)
               for e in RG.enumerate_genesis_recursion(budget=100000))


def test_recursion_genesis_only_via_injected_evaluate():
    """Rule 9.35.2 對抗分離：genesis 只呼叫注入 evaluate、結構性無自評。"""
    seen = {}
    def ev(e):
        seen[e.name] = seen.get(e.name, 0) + 1
        return 0.5 if e.name == _recsum4().name else 0.0
    cands = list(RG.enumerate_genesis_recursion(budget=40)) + [_recsum4()]
    prop = RG.recursion_genesis(ev, candidates=cands)
    assert prop.operator is not None and prop.accepted
    assert prop.operator.name == _recsum4().name
    assert seen, "genesis 必須透過注入 evaluate 取必要性"


def test_recursion_genesis_isolation_from_oracle():
    """Rule 9.35.2 對抗分離：operator_recursion_genesis 結構性不 import oracle、不讀必要性語料。"""
    src = (ROOT / "operator_recursion_genesis.py").read_text(encoding="utf-8")
    assert "dimension_necessity_oracle" not in src
    assert "load_recursion_corpus" not in src
    assert "held-out-corpus" not in src


def test_recursion_genesis_round_k_truncation():
    """Rule 9.35.4 反 big-bang：一輪至多 K_recur 個，其餘順延。"""
    cands = RG.enumerate_genesis_recursion(budget=30)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda e: scores.get(e.name, 0.0)
    rnd = RG.recursion_genesis_round(ev, candidates=cands, k=1)
    assert len(rnd.selected) == 1
    assert rnd.selected[0].operator.name == cands[0].name
    assert len(rnd.deferred) == 2


def test_expanded_recursion_ops():
    base = RG.expanded_recursion_ops([])
    assert base == ()
    grown = RG.expanded_recursion_ops([_recsum4().name, _recsum4().name])   # 去重
    assert grown == (_recsum4().name,)


def test_adopt_recursion_requires_signoff():
    with pytest.raises(RG.SignoffRequired):
        RG.adopt_genesis_recursion(_recsum4(), 50, human_signoff=False)


def test_adopt_recursion_rejects_self_referential():
    e = RecursiveOperator.chain(GenesisOperator.of("sum", "sq"), 2, combine="mul",
                                probe=["self_score", "x", "y"])
    with pytest.raises(RG.SelfReferentialRecursion):
        RG.adopt_genesis_recursion(e, 50, human_signoff=True)


# ---------------------------------------------------------------------------
# ACT-154 — feature-grounded 互遞迴必要性 oracle（evaluate_genesis_recursion，反 Goodhart）
# ---------------------------------------------------------------------------

def _C(q, cost, f):
    return DO.RecursionCandidate(q, cost, {"rollback_steps": float(f[0]), "blast_radius": float(f[1]),
                                           "canary_gap": float(f[2])})


def _true_recursion_case():
    # 反相關：A 高 sum/低品質/最低 cost（baseline 誤選）；B 低 sum/高品質/高 cost（sum⁴ 救回）；C 中。
    return DO.RecursionCase("T", [_C(0.45, 2.0, (9, 8, 7)), _C(0.87, 5.0, (1, 1, 2)), _C(0.62, 3.0, (4, 3, 3))])


def _noise_recursion_case():
    return DO.RecursionCase("N", [_C(0.6, 2.0, (5, 5, 5)), _C(0.6, 3.0, (0, 0, 0)), _C(0.4, 4.0, (8, 8, 8))])


def _redundant_recursion_case():
    # canary_gap 與 existing_cost 同序遞增 → mul-fold of sq(last) 的 dim_value 與 existing_cost 排序一致 → 冗餘
    return DO.RecursionCase("R", [_C(0.6, 2.0, (2, 2, 2)), _C(0.5, 3.0, (3, 3, 3)), _C(0.4, 4.0, (4, 4, 4))])


def _redundant_op():
    return RecursiveOperator.chain(GenesisOperator.of("last", "sq"), 2, combine="mul")   # (canary_gap)⁴


def _noise_op():
    # mul-fold of clip01(sum)：sum 對所有候選皆 >1 → clip01 飽和成常數 1.0 → mul 仍 1.0（零區辨、零增量覆蓋），
    # 仍真正需要互遞迴呼叫圖（兩個 node 互相呼叫，非單一非遞迴算子可表達）。
    return RecursiveOperator.chain(GenesisOperator.of("sum", "clip01"), 2, combine="mul")


def test_evaluate_recursion_true_necessary():
    v = DO.evaluate_genesis_recursion(_recsum4(), [_true_recursion_case()], coverage_margin=0.1)
    assert v.incremental_coverage >= 0.1
    assert v.redundancy < v.redundancy_max
    assert v.necessary and v.tier > 0


def test_evaluate_recursion_noise_rejected_by_coverage():
    v = DO.evaluate_genesis_recursion(_noise_op(), [_noise_recursion_case()], coverage_margin=0.1)
    assert v.incremental_coverage < v.coverage_margin
    assert not v.necessary and v.tier == 0


def test_evaluate_recursion_redundant_rejected_by_redundancy():
    v = DO.evaluate_genesis_recursion(_redundant_op(), [_redundant_recursion_case()], coverage_margin=0.1)
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary


def test_recursion_redundancy_is_independent_gate():
    """即使覆蓋門檻放寬到必過，冗餘互遞迴算子仍被非冗餘度獨立否決。"""
    v = DO.evaluate_genesis_recursion(_redundant_op(), [_redundant_recursion_case()], coverage_margin=-1.0)
    assert v.incremental_coverage >= v.coverage_margin
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary, "冗餘互遞迴算子須被非冗餘度獨立否決"


def test_recursion_goodhart_zero_miss():
    """安全紅線：噪音互遞迴算子 + 冗餘互遞迴算子攔截零漏放。"""
    assert not DO.evaluate_genesis_recursion(_noise_op(), [_noise_recursion_case()], coverage_margin=0.1).necessary
    assert not DO.evaluate_genesis_recursion(_redundant_op(), [_redundant_recursion_case()], coverage_margin=0.1).necessary


def test_necessity_score_recursion_zero_when_not_necessary():
    assert DO.necessity_score_recursion(_recsum4(), [_true_recursion_case()]) > 0.0
    assert DO.necessity_score_recursion(_noise_op(), [_noise_recursion_case()]) == 0.0


def test_recursion_genesis_self_passes_but_oracle_rejects():
    """genesis 樸素自評視噪音互遞迴算子為必要，但 oracle 在 held-out 上否決 → 以 oracle 為準。"""
    noise = _noise_op()
    per = RG.recursion_genesis(lambda e: 0.9, candidates=[noise])
    assert per.accepted, "genesis 樸素自評視之為必要（接縫前提）"
    v = DO.evaluate_genesis_recursion(noise, [_noise_recursion_case()], coverage_margin=0.1)
    assert not v.necessary


def test_evaluate_recursion_replay_bounded():
    corpus = [_true_recursion_case() for _ in range(100)]
    v = DO.evaluate_genesis_recursion(_recsum4(), corpus, max_cases=5)
    assert v.examined == 5


def test_load_recursion_corpus_12_cases():
    corpus = DO.load_recursion_corpus()
    assert len(corpus) >= 12, f"RCR 凍結語料應 >= 12，實得 {len(corpus)}"


def test_load_recursion_corpus_makes_recsum4_necessary():
    """端到端：載入凍結 RCR 語料 → sum⁴ 互遞迴算子在其上必要（feature-grounded）。"""
    corpus = DO.load_recursion_corpus()
    v = DO.evaluate_genesis_recursion(_recsum4(), corpus, coverage_margin=0.1)
    assert v.necessary and v.incremental_coverage >= 0.1


def test_load_recursion_corpus_rejects_noise():
    """端到端：噪音互遞迴算子在凍結 RCR 語料上不必要（零漏放）。"""
    corpus = DO.load_recursion_corpus()
    assert not DO.evaluate_genesis_recursion(_noise_op(), corpus, coverage_margin=0.1).necessary


def test_recursion_corpus_fingerprint_deterministic():
    corpus = DO.load_recursion_corpus()
    assert DO.recursion_corpus_fingerprint(corpus) == DO.recursion_corpus_fingerprint(corpus)


# ---------------------------------------------------------------------------
# ACT-154 — META_FSM 不增第六軌/不增狀態變數（兩新不變量）+ 守門
# ---------------------------------------------------------------------------

def test_meta_fsm_declares_phase_w_invariants():
    """META_FSM.tla 定義 RecursionGenesisBounded + RecursionClosureBounded，.cfg INVARIANT 列入。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal" / "META_FSM.cfg").read_text(encoding="utf-8")
    assert "RecursionGenesisBounded ==" in tla
    assert "RecursionClosureBounded ==" in tla
    assert "RecursionGenesisBounded" in cfg
    assert "RecursionClosureBounded" in cfg


def test_meta_fsm_variables_unchanged_no_new_state():
    """Rule 9.35.4：不新增狀態變數（仍 mstate/churn/cap）→ 本軌 reachable(13 distinct) 不回歸。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert "VARIABLES mstate," in tla
    assert "vars == <<mstate, churn, cap>>" in tla
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla


def test_no_sixth_formal_track():
    """Rule 9.35.4：不增第六軌——formal/ 仍恰 5 個 .tla。"""
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_single_track_no_recursion_leak():
    """Rule 9.35.4：recursion-genesis 不污染單軌 SDD_FSM.tla。"""
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "RecursionGenesis" not in sdd and "recursion-genesis" not in sdd


def test_recursion_genesis_namespace_isolation():
    """Rule 9.35.4：recursion-genesis 與維度/詞彙/算子/字母/深度/calibration 命名空間分開治理。"""
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    assert ML.is_recursion_genesis_fingerprint("recursion-genesis:abc")
    assert not ML.is_recursion_genesis_fingerprint("depth-genesis:abc")
    assert not ML.is_recursion_genesis_fingerprint("alphabet-genesis:abc")
    assert not ML.is_recursion_genesis_fingerprint("operator-genesis:abc")
    assert not ML.is_recursion_genesis_fingerprint("value-dimension:abc")
    assert not ML.is_recursion_genesis_fingerprint("vocab-genesis:abc")
    assert not ML.is_calibration_fingerprint("recursion-genesis:abc")
    assert not ML.is_depth_genesis_fingerprint("recursion-genesis:abc")


def test_dim_recur_max_env(monkeypatch):
    monkeypatch.delenv("SDD_DIM_RECUR_MAX", raising=False)
    assert MM.dim_recur_max() == 16
    monkeypatch.setenv("SDD_DIM_RECUR_MAX", "999")
    assert MM.dim_recur_max() == 64
    monkeypatch.setenv("SDD_DIM_RECUR_MAX", "0")
    assert MM.dim_recur_max() == 1


def test_guard_recursion_closure_break_uncertified_cycle():
    """Rule 9.35.3：無證書環（含環、無回邊遞減下有界 rank）→ RecursionClosureViolation。"""
    base = GenesisOperator.of("sum", "sq")
    cyclic = RecursiveOperator(nodes=(RecursionNode(base, 0, (1,)), RecursionNode(base, 0, (0,))),
                               entry=0, fuel=2, combine="mul")
    with pytest.raises(MM.RecursionClosureViolation):
        MM.guard_recursion_closure(cyclic)


def test_guard_recursion_closure_over_budget(monkeypatch):
    """Rule 9.35.3：fuel 超界（step_max 壓到 2，3-node 互遞迴算子 fuel==3）→ RecursionClosureViolation。"""
    monkeypatch.setenv("SDD_DIM_OP_STEP_MAX", "2")
    three = RG.RecursiveOperator.chain(GenesisOperator.of("sum", "sq"), 3, combine="mul")
    with pytest.raises(MM.RecursionClosureViolation):
        MM.guard_recursion_closure(three)


def test_guard_recursion_closure_passes_legit():
    r = MM.guard_recursion_closure(_recsum4())
    assert r.allowed and r.total and r.terminating and r.fuel <= r.step_max


def test_guard_recursion_genesis_stock_ceiling(tmp_path, monkeypatch):
    """Rule 9.35.4：互遞迴算子 stock 觸頂 → RecursionCardinalityExceeded + meta_state ESCALATION。"""
    monkeypatch.setenv("SDD_DIM_RECUR_MAX", "2")
    led = tmp_path / "meta-loop-ledger.yaml"
    ops = [
        RecursiveOperator.chain(GenesisOperator.of("sum", "sq"), 2, combine="mul"),
        RecursiveOperator.chain(GenesisOperator.of("mean", "sq"), 2, combine="mul"),
        RecursiveOperator.chain(GenesisOperator.of("max", "sq"), 2, combine="mul"),
    ]
    for i in range(2):
        RG.adopt_genesis_recursion(ops[i], 40 + i, human_signoff=True, ledger_path=led)
    assert MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"
    with pytest.raises(MM.RecursionCardinalityExceeded):
        RG.adopt_genesis_recursion(ops[2], 99, human_signoff=True, ledger_path=led)


def test_adopt_recursion_happy_path(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    op = _recsum4()
    ev = RG.adopt_genesis_recursion(op, 70, human_signoff=True, ledger_path=led)
    assert ev.fingerprint == op.fingerprint()
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    assert op.fingerprint() in ML.active_recursion_genesis_features(ledger_path=led)


# ---------------------------------------------------------------------------
# ACT-155 — steersman 互遞迴外發明 diff + 良基停機證書證據（advisory + 反 big-bang + 人工 gate）
# ---------------------------------------------------------------------------

def _accepted_recursion_round(k=1):
    cands = RG.enumerate_genesis_recursion(budget=30)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda e: scores.get(e.name, 0.0)
    return RG.recursion_genesis_round(ev, candidates=cands, k=k)


def test_render_recursion_genesis_proposal():
    from tools.fsm_runtime.steersman_renderer import render_recursion_genesis_proposal
    rnd = _accepted_recursion_round(k=1)
    verdict = DO.evaluate_genesis_recursion(_recsum4(), [_true_recursion_case()], coverage_margin=0.1)
    md = render_recursion_genesis_proposal(rnd, verdict=verdict)
    assert "Self-Expanding Operator Recursion" in md
    assert "互遞迴" in md
    assert "K_recur=1" in md
    assert "signoff" in md and "待人工" in md
    assert "良基" in md and "fuel" in md          # 良基停機證書證據
    assert "非自指" in md
    assert verdict.corpus_fingerprint in md
    assert rnd.selected[0].operator.name in md


def test_render_recursion_genesis_shows_deferred_under_bigbang():
    from tools.fsm_runtime.steersman_renderer import render_recursion_genesis_proposal
    rnd = _accepted_recursion_round(k=1)
    md = render_recursion_genesis_proposal(rnd)
    assert "K_recur=1" in md
    assert rnd.deferred[0] in md


def test_render_recursion_genesis_never_auto_commits():
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_recursion_genesis_proposal)
    assert "record_rule_add" not in src and "adopt_genesis_recursion" not in src


def test_render_recursion_genesis_no_verdict_degrades():
    from tools.fsm_runtime.steersman_renderer import render_recursion_genesis_proposal
    md = render_recursion_genesis_proposal(_accepted_recursion_round(k=1))
    assert "互遞迴" in md and "待人工" in md


# ---------------------------------------------------------------------------
# ACT-155 — chaos 雙故障型 deterministic bounded（單元層；100 輪整合在 chaos 套件）
# ---------------------------------------------------------------------------

def test_chaos_recursion_genesis_goodhart_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _recursion_genesis_goodhart_flap_is_bounded
    assert _recursion_genesis_goodhart_flap_is_bounded()


def test_chaos_recursion_closure_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _recursion_closure_flap_is_bounded
    assert _recursion_closure_flap_is_bounded()


def test_chaos_new_fault_types_registered():
    from tools.fsm_runtime.chaos_runner import FAULT_TYPES
    assert "RECURSION_GENESIS_GOODHART_FLAP" in FAULT_TYPES
    assert "RECURSION_CLOSURE_FLAP" in FAULT_TYPES


# ---------------------------------------------------------------------------
# Phase W ownership（R-9.35 enforces 連結）
# ---------------------------------------------------------------------------

def test_phase_w_enforces_rule_9_35():
    """本檔頭 `# enforces (governance rules): R-9.35` 連結 Phase W 守門至 R-9.35。"""
    head = (ROOT / "tests" / "test_phase_w.py").read_text(encoding="utf-8").splitlines()[0]
    assert head == "# enforces (governance rules): R-9.35"
