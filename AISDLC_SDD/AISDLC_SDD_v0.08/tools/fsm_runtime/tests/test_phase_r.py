# enforces (governance rules): R-9.30
"""Phase R / ACT-129~134 — 價值維度語意的自我發明 + 退役聯動（meta-meta-meta）回歸守門.

涵蓋：
  - ACT-129 Dimension Semantics Synthesizer：候選池外有界生成文法（可枚舉、cap budget）、
    自指 probe self-reference guard 零漏放、deterministic、只透過注入 evaluate 取必要性（結構性無
    自評）、proposed-only、反 big-bang K_dim=1 截斷、對抗分離（不 import oracle）
  - ACT-130 feature-keyed 必要性 oracle：evaluate_invented_dimension（不靠 dimension_name）、
    候選池外真必要偵出、自我發明 Goodhart（噪音軸+冗餘軸）零漏放、necessity tier 唯一來源、隔離
  - ACT-131 退役聯動 swap + SwapCadenceBounded：net 基數不變、定基數旋轉 swap 速率觸頂→
    SwapCadenceExceeded→MFSM_ESCALATION、單調價值棘輪、META_FSM 不增第六軌/不增狀態變數
  - ACT-132 steersman 候選池外發明 diff + 退役聯動 diff（advisory + 反 big-bang + 人工 gate）
  - ACT-134 chaos DIMENSION_INVENTION_GOODHART_FLAP / DIMENSION_SWAP_THRASH_FLAP 有界
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from tools.fsm_runtime import dimension_semantics_synthesizer as S
from tools.fsm_runtime import dimension_necessity_oracle as DO
from tools.fsm_runtime.dimension_semantics_synthesizer import InventedDimension

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# ACT-129 — Dimension Semantics Synthesizer（候選池外有界生成文法 + 自指守門）
# ---------------------------------------------------------------------------

def test_enumerate_inventions_bounded():
    """Rule 9.30.1 有界生成文法：枚舉節點 <= budget（候選池外≠無界）。"""
    assert len(S.enumerate_inventions(budget=64)) == 64
    assert len(S.enumerate_inventions(budget=10)) == 10
    assert len(S.enumerate_inventions(budget=1)) == 1


def test_enumerate_inventions_deterministic():
    a = S.enumerate_inventions(budget=32)
    b = S.enumerate_inventions(budget=32)
    assert [d.name for d in a] == [d.name for d in b]


def test_enumerate_respects_arity():
    """arity=1 → 每條發明只組合 1 個特徵（無聚合算子退化重複）。"""
    dims = S.enumerate_inventions(budget=256, arity=1)
    assert all(len(d.probe) == 1 for d in dims)
    # 不超過 |VOCAB|（arity=1 + 單一 op）
    assert len(dims) == len(S.VOCAB)


def test_invented_dimension_namespace_and_fingerprint():
    d = InventedDimension.of("mean", ("rollback_steps", "blast_radius"))
    fp = d.fingerprint()
    assert fp.startswith("value-dimension:")
    # deterministic + 與 probe 序無關
    d2 = InventedDimension.of("mean", ("blast_radius", "rollback_steps"))
    assert d.fingerprint() == d2.fingerprint()
    # op 不同 → 指紋不同（語意不同的發明軸）
    d3 = InventedDimension.of("max", ("rollback_steps", "blast_radius"))
    assert d.fingerprint() != d3.fingerprint()


def test_invented_dimension_apply():
    d = InventedDimension.of("mean", ("a", "b"))
    assert d.apply({"a": 2.0, "b": 4.0}) == 3.0
    assert InventedDimension.of("max", ("a", "b")).apply({"a": 2.0, "b": 4.0}) == 4.0
    assert InventedDimension.of("min", ("a", "b")).apply({"a": 2.0, "b": 4.0}) == 2.0
    assert InventedDimension.of("sum", ("a", "b")).apply({"a": 2.0, "b": 4.0}) == 6.0
    # 缺特徵以 0.0 計
    assert InventedDimension.of("mean", ("a", "z")).apply({"a": 4.0}) == 2.0


def test_invented_fingerprint_is_dimension_namespace():
    """Rule 9.30.3：發明維度共用 value-dimension 命名空間（churn/cardinality/swap 治理）。"""
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    fp = InventedDimension.of("mean", ("rollback_steps",)).fingerprint()
    assert ML.is_dimension_fingerprint(fp)
    assert not ML.is_calibration_fingerprint(fp)


def test_self_reference_guard_rejects_self_referential():
    """Rule 9.30.2 反自利第一閘：自指 probe（引用 proposer/oracle 內部信號）零漏放。"""
    for probe in (("self_score",), ("proposer_confidence",), ("necessity",),
                  ("dim_value",), ("oracle_score",), ("rollback_steps", "self_score")):
        d = InventedDimension.of("mean", probe)
        assert S.is_self_referential(d), f"{probe} 應被判自指"
    # 合法特徵不被誤判
    assert not S.is_self_referential(InventedDimension.of("mean", ("rollback_steps", "blast_radius")))


def test_self_reference_guard_filters_list():
    dims = [InventedDimension.of("mean", ("rollback_steps",)),
            InventedDimension.of("mean", ("self_score",)),
            InventedDimension.of("max", ("blast_radius",))]
    survivors = S.self_reference_guard(dims)
    assert len(survivors) == 2
    assert all(not S.is_self_referential(d) for d in survivors)


def test_enumerate_never_emits_self_referential():
    """生產 VOCAB 無自指 token → 枚舉恆不產自指發明（self-ref guard 仍對受擾注入零漏放）。"""
    dims = S.enumerate_inventions(budget=256)
    assert all(not S.is_self_referential(d) for d in dims)


def test_invent_finds_necessary_invention():
    """synthesizer 在注入必要性上找到真必要發明（達 margin、送 signoff）。"""
    target = InventedDimension.of("mean", ("rollback_steps", "blast_radius"))
    ev = lambda d: 0.22 if d.name == target.name else 0.0
    prop = S.invent(ev, candidates=S.enumerate_inventions(budget=64))
    assert prop.accepted
    assert prop.dimension.name == target.name
    assert prop.necessity >= prop.margin
    assert prop.to_dict()["maturity"] == "proposed"


def test_invent_search_bounded():
    prop = S.invent(lambda d: 0.5, budget=5)
    assert prop.nodes_searched <= 5


def test_invent_no_acceptance_when_all_below_margin():
    prop = S.invent(lambda d: 0.0)
    assert not prop.accepted


def test_invent_round_respects_bigbang_kdim():
    """一輪至多 K_dim 條發明進 proposed（按 necessity 取前 K_dim），其餘順延（Rule 9.30.4）。"""
    cands = S.enumerate_inventions(budget=8)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda d: scores.get(d.name, 0.0)
    rnd = S.invent_round(ev, candidates=cands, k=1)
    assert len(rnd.selected) == 1
    assert rnd.selected[0].dimension.name == cands[0].name   # necessity 最高
    assert len(rnd.deferred) == 2
    assert all(p.accepted for p in rnd.selected)


def test_invent_round_default_kdim_is_one():
    """NoUnboundedSelfInvention：env 未設時 K_dim 預設 1（沿用 Phase Q）。"""
    from tools.fsm_runtime.value_dimension_registry import dim_expand_k
    assert dim_expand_k() == 1


def test_invent_budget_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_DIM_INVENT_BUDGET", raising=False)
    assert S.invent_budget() == 64
    monkeypatch.setenv("SDD_DIM_INVENT_BUDGET", "9999")
    assert S.invent_budget() == 256
    monkeypatch.setenv("SDD_DIM_INVENT_BUDGET", "1")
    assert S.invent_budget() == 8


def test_invent_arity_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_DIM_INVENT_ARITY", raising=False)
    assert S.invent_arity() == 2
    monkeypatch.setenv("SDD_DIM_INVENT_ARITY", "99")
    assert S.invent_arity() == 4
    monkeypatch.setenv("SDD_DIM_INVENT_ARITY", "0")
    assert S.invent_arity() == 1


def test_synthesizer_structurally_blind_to_oracle():
    """Rule 9.30.2：synthesizer **不得 import** 任何必要性 oracle、不得觸及語料（對抗分離）。"""
    tree = ast.parse(inspect.getsource(S))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported |= {a.name for a in node.names}
    assert not any("oracle" in m.lower() for m in imported), "synthesizer 不得 import oracle（破對抗分離）"
    assert not any("necessity" in m.lower() for m in imported)
    src = inspect.getsource(S)
    assert "dimension_necessity_oracle" not in src
    assert "held-out-corpus" not in src and "held_out" not in src.lower()


def test_adopt_invention_requires_human_signoff(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    d = InventedDimension.of("mean", ("rollback_steps",))
    with pytest.raises(S.SignoffRequired):
        S.adopt_invention(d, 50, ledger_path=led)
    assert not led.exists()


def test_adopt_invention_rejects_self_referential(tmp_path):
    """Rule 9.30.2：自指發明維度連採納路徑都拒絕（即使帶 human_signoff）。"""
    led = tmp_path / "meta-loop-ledger.yaml"
    d = InventedDimension.of("mean", ("self_score",))
    with pytest.raises(S.SelfReferentialInvention):
        S.adopt_invention(d, 50, human_signoff=True, ledger_path=led)
    assert not led.exists()


def test_adopt_invention_goes_through_meta_guard(tmp_path):
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    led = tmp_path / "meta-loop-ledger.yaml"
    d = InventedDimension.of("mean", ("rollback_steps", "blast_radius"))
    ev = S.adopt_invention(d, 70, human_signoff=True, ledger_path=led)
    assert ev.fingerprint.startswith("value-dimension:")
    assert ML.compute_churn(ev.fingerprint, ledger_path=led) == 0
    assert len(ML.active_value_dimensions(ledger_path=led)) == 1


def test_record_round_writes_pending_signoff(tmp_path):
    cands = S.enumerate_inventions(budget=8)
    ev = lambda d: 0.3 if d.name == cands[0].name else 0.0
    rnd = S.invent_round(ev, candidates=cands, k=1)
    led = tmp_path / "value-dimension-ledger.yaml"
    entry = S.record_round(rnd, ledger_path=led, ts="2026-06-04T00:00:00+00:00")
    assert led.exists()
    assert entry["signoff"] == "pending"
    assert all(p["maturity"] == "proposed" for p in entry["selected"])


# ---------------------------------------------------------------------------
# ACT-130 — feature-keyed 必要性 oracle（候選池外自我發明反 Goodhart）
# ---------------------------------------------------------------------------

def _true_feature_case():
    """真必要：baseline 選 BAD（existing 誤排），發明軸（mean rollback/blast）翻到 GOOD。"""
    return DO.FeatureCase(case_id="T", candidates=[
        DO.FeatureCandidate(0.9, 5.0, {"rollback_steps": 0.0, "blast_radius": 0.0}),  # GOOD
        DO.FeatureCandidate(0.3, 2.0, {"rollback_steps": 9.0, "blast_radius": 9.0}),  # BAD（baseline 選）
        DO.FeatureCandidate(0.6, 4.0, {"rollback_steps": 4.0, "blast_radius": 4.0})])  # MID


def _noise_feature_case():
    return DO.FeatureCase(case_id="N", candidates=[
        DO.FeatureCandidate(0.6, 2.0, {"canary_gap": 5.0}),
        DO.FeatureCandidate(0.6, 3.0, {"canary_gap": 0.0}),
        DO.FeatureCandidate(0.4, 4.0, {"canary_gap": 8.0})])


def _redundant_feature_case():
    return DO.FeatureCase(case_id="R", candidates=[
        DO.FeatureCandidate(0.6, 2.0, {"oncall_pages": 2.0}),
        DO.FeatureCandidate(0.5, 3.0, {"oncall_pages": 3.0}),
        DO.FeatureCandidate(0.4, 4.0, {"oncall_pages": 4.0})])


def test_invented_true_necessity_detected():
    dim = InventedDimension.of("mean", ("rollback_steps", "blast_radius"))
    v = DO.evaluate_invented_dimension(dim, [_true_feature_case()], coverage_margin=0.1)
    assert v.incremental_coverage == pytest.approx(0.6)
    assert v.redundancy < v.redundancy_max
    assert v.necessary and v.tier == 60


def test_invented_noise_rejected_by_coverage():
    dim = InventedDimension.of("mean", ("canary_gap",))
    v = DO.evaluate_invented_dimension(dim, [_noise_feature_case()], coverage_margin=0.1)
    assert v.incremental_coverage < v.coverage_margin
    assert not v.necessary and v.tier == 0


def test_invented_redundant_rejected_by_redundancy():
    dim = InventedDimension.of("mean", ("oncall_pages",))
    v = DO.evaluate_invented_dimension(dim, [_redundant_feature_case()], coverage_margin=0.1)
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary


def test_invented_redundancy_is_independent_gate():
    """即使覆蓋門檻放寬到必過，冗餘發明軸仍被非冗餘度獨立否決。"""
    dim = InventedDimension.of("mean", ("oncall_pages",))
    v = DO.evaluate_invented_dimension(dim, [_redundant_feature_case()], coverage_margin=-1.0)
    assert v.incremental_coverage >= v.coverage_margin
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary, "冗餘發明軸須被非冗餘度獨立否決"


def test_necessity_score_invented_zero_when_not_necessary():
    assert DO.necessity_score_invented(
        InventedDimension.of("mean", ("rollback_steps", "blast_radius")),
        [_true_feature_case()]) == pytest.approx(0.6)
    assert DO.necessity_score_invented(
        InventedDimension.of("mean", ("canary_gap",)), [_noise_feature_case()]) == 0.0
    assert DO.necessity_score_invented(
        InventedDimension.of("mean", ("oncall_pages",)), [_redundant_feature_case()]) == 0.0


def test_synthesizer_self_passes_but_oracle_rejects():
    """synthesizer 樸素自評視噪音發明為必要，但 oracle 在 held-out 上否決 → 以 oracle 為準。"""
    noise_dim = InventedDimension.of("mean", ("canary_gap",))
    per = S.invent(lambda d: 0.9, candidates=[noise_dim])
    assert per.accepted, "synthesizer 樸素自評視之為必要（接縫前提）"
    v = DO.evaluate_invented_dimension(noise_dim, [_noise_feature_case()], coverage_margin=0.1)
    assert not v.necessary


def test_evaluate_invented_bounded(monkeypatch):
    corpus = [_true_feature_case() for _ in range(100)]
    v = DO.evaluate_invented_dimension(
        InventedDimension.of("mean", ("rollback_steps", "blast_radius")), corpus, max_cases=5)
    assert v.examined == 5


def test_feature_corpus_fingerprint_tamper_and_stable():
    base = [_true_feature_case()]
    assert DO.feature_corpus_fingerprint(base) == DO.feature_corpus_fingerprint([_true_feature_case()])
    tampered = [_true_feature_case()]
    tampered[0].candidates[1].real_quality = 0.95
    assert DO.feature_corpus_fingerprint(base) != DO.feature_corpus_fingerprint(tampered)


def test_synthesizer_cannot_reach_feature_corpus():
    """Rule 9.30.2 對抗分離：synthesizer（proposer）無法觸及 feature 必要性語料載入符號/路徑。"""
    assert not hasattr(S, "load_feature_corpus")
    assert not hasattr(S, "FeatureCase")
    src = inspect.getsource(S)
    assert "dimension_necessity_oracle" not in src       # 不 import 評估器
    assert "load_feature_corpus" not in src              # 不讀 feature 必要性語料
    assert "held_out" not in src.lower() and "held-out-corpus" not in src


# ---------------------------------------------------------------------------
# ACT-130 驗收 — 12 凍結 feature 必要性語料統計性驗收（6 真必要 + 3 噪音 + 3 冗餘；零漏放）
# ---------------------------------------------------------------------------

import yaml as _yaml  # noqa: E402


def _load_inv_scenarios():
    out = []
    for p in sorted(DO.HELD_OUT_CORPUS_DIR.glob("INV-*.yaml")):
        doc = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if doc.get("expect") in ("true_invention", "noise_invention", "redundant_invention"):
            out.append(doc)
    return out


def _verdict_for_inv(doc):
    dim = InventedDimension.of(doc["invented"]["op"], doc["invented"]["probe"])
    cases = [DO.FeatureCase(case_id=doc["case_id"], candidates=[
        DO.FeatureCandidate(c["real_quality"], c["existing_cost"], c["features"])
        for c in doc["candidates"]])]
    return DO.evaluate_invented_dimension(dim, cases, coverage_margin=0.1)


def test_inv_corpus_has_12_labelled_cases():
    metas = _load_inv_scenarios()
    true_cases = [m for m in metas if m["expect"] == "true_invention"]
    noise_cases = [m for m in metas if m["expect"] == "noise_invention"]
    redundant_cases = [m for m in metas if m["expect"] == "redundant_invention"]
    assert len(true_cases) == 6, f"真必要發明 fixture 應為 6，實得 {len(true_cases)}"
    assert len(noise_cases) == 3, f"噪音發明 fixture 應為 3，實得 {len(noise_cases)}"
    assert len(redundant_cases) == 3, f"冗餘發明 fixture 應為 3，實得 {len(redundant_cases)}"


@pytest.mark.parametrize("doc", [m for m in _load_inv_scenarios()
                                 if m["expect"] == "true_invention"],
                         ids=lambda d: d["case_id"])
def test_inv_true_necessity_detected(doc):
    v = _verdict_for_inv(doc)
    assert v.necessary, f"{doc['case_id']} 真必要卻被判不必要（cov={v.incremental_coverage}, redun={v.redundancy}）"
    assert v.tier == int(round(v.incremental_coverage * 100))


@pytest.mark.parametrize("doc", [m for m in _load_inv_scenarios()
                                 if m["expect"] in ("noise_invention", "redundant_invention")],
                         ids=lambda d: d["case_id"])
def test_inv_goodhart_intercepted(doc):
    """每個自我發明 Goodhart（噪音軸/冗餘軸）：oracle 必判不必要（零漏放，安全紅線）。"""
    v = _verdict_for_inv(doc)
    assert not v.necessary, f"{doc['case_id']} 自我發明 Goodhart 漏放（安全紅線破！cov={v.incremental_coverage}, redun={v.redundancy}）"


def test_inv_acceptance_rates_meet_blueprint():
    """ACT-130 驗收統計：真必要偵出率 >= 85%、自我發明 Goodhart 攔截率 100%（零漏放）。"""
    metas = _load_inv_scenarios()
    true_cases = [m for m in metas if m["expect"] == "true_invention"]
    goodhart_cases = [m for m in metas if m["expect"] in ("noise_invention", "redundant_invention")]
    true_detected = sum(1 for m in true_cases if _verdict_for_inv(m).necessary)
    goodhart_intercepted = sum(1 for m in goodhart_cases if not _verdict_for_inv(m).necessary)
    assert true_detected / len(true_cases) >= 0.85, \
        f"真必要偵出率 {true_detected}/{len(true_cases)} < 85%"
    assert goodhart_intercepted == len(goodhart_cases), \
        f"自我發明 Goodhart 攔截率非 100%（{goodhart_intercepted}/{len(goodhart_cases)}，零漏放破！）"


# ---------------------------------------------------------------------------
# ACT-131 — 退役聯動 swap + SwapCadenceBounded（不增第六軌/不增狀態變數）
# ---------------------------------------------------------------------------

def _invented(i):
    return InventedDimension.of("mean", (S.VOCAB[i % len(S.VOCAB)],))


def test_swap_net_cardinality_unchanged(tmp_path, monkeypatch):
    """Rule 9.30.3：退役聯動 swap = retire 1 + add 1 → net 基數不變。"""
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    monkeypatch.setenv("SDD_DIM_CARDINALITY_MAX", "3")
    led = tmp_path / "meta-loop-ledger.yaml"
    dims = [InventedDimension.of("mean", (f,)) for f in S.VOCAB[:3]]
    for i, d in enumerate(dims):
        S.adopt_invention(d, 40 + i, human_signoff=True, ledger_path=led)
    assert len(ML.active_value_dimensions(ledger_path=led)) == 3
    new_in = InventedDimension.of("max", (S.VOCAB[4],))
    S.swap_dimension(dims[0], new_in, out_tier=40, in_tier=80, human_signoff=True, ledger_path=led)
    assert len(ML.active_value_dimensions(ledger_path=led)) == 3   # net 不變


def test_swap_cadence_storm_escalates(tmp_path, monkeypatch):
    """Rule 9.30.3：定基數旋轉 swap 速率觸頂 → SwapCadenceExceeded → MFSM_ESCALATION。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.setenv("SDD_DIM_CARDINALITY_MAX", "3")
    monkeypatch.setenv("SDD_DIM_SWAP_RATE_MAX", "3")
    led = tmp_path / "meta-loop-ledger.yaml"
    for i, f in enumerate(S.VOCAB[:3]):
        S.adopt_invention(InventedDimension.of("mean", (f,)), 40 + i, human_signoff=True, ledger_path=led)
    out_dim, out_tier = InventedDimension.of("mean", (S.VOCAB[0],)), 40
    cnt = 0
    with pytest.raises(MM.SwapCadenceExceeded):
        for j in range(5):
            in_dim = InventedDimension.of("max", (S.VOCAB[3 + j],))
            in_tier = out_tier + 10 + j
            S.swap_dimension(out_dim, in_dim, out_tier=out_tier, in_tier=in_tier,
                             human_signoff=True, ledger_path=led)
            out_dim, out_tier = in_dim, in_tier
            cnt += 1
    assert cnt == 3, "swap 速率上限 3 → 第 4 次觸頂"
    assert MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"


def test_swap_monotonic_value_ratchet(tmp_path):
    """Rule 9.30.3：入軸 tier 未嚴格 > 出軸 tier + margin → SwapValueRatchetViolation（防 A↔B↔A）。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    led = tmp_path / "meta-loop-ledger.yaml"
    out_dim = InventedDimension.of("mean", (S.VOCAB[0],))
    in_dim = InventedDimension.of("max", (S.VOCAB[1],))
    with pytest.raises(MM.SwapValueRatchetViolation):
        S.swap_dimension(out_dim, in_dim, out_tier=50, in_tier=50, human_signoff=True, ledger_path=led)


def test_swap_requires_signoff(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    with pytest.raises(S.SignoffRequired):
        S.swap_dimension(InventedDimension.of("mean", (S.VOCAB[0],)),
                         InventedDimension.of("max", (S.VOCAB[1],)),
                         out_tier=40, in_tier=80, ledger_path=led)


def test_swap_rejects_self_referential_in(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    with pytest.raises(S.SelfReferentialInvention):
        S.swap_dimension(InventedDimension.of("mean", (S.VOCAB[0],)),
                         InventedDimension.of("mean", ("self_score",)),
                         out_tier=40, in_tier=80, human_signoff=True, ledger_path=led)


def test_swap_guard_rejects_non_dimension(tmp_path):
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    with pytest.raises(ValueError):
        MM.guard_dimension_swap("adversarial-profile:abc", "value-dimension:xyz", 10, 50)


def test_swap_rate_env_clamp(monkeypatch):
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.delenv("SDD_DIM_SWAP_RATE_MAX", raising=False)
    assert MM.dim_swap_rate_max() == 3
    monkeypatch.setenv("SDD_DIM_SWAP_RATE_MAX", "999")
    assert MM.dim_swap_rate_max() == 16
    monkeypatch.setenv("SDD_DIM_SWAP_RATE_MAX", "0")
    assert MM.dim_swap_rate_max() == 1


def test_meta_fsm_declares_swap_invariant():
    """ACT-131：META_FSM.tla 定義 SwapCadenceBounded，且 .cfg INVARIANT 區塊列入（TLC 會檢查）。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal" / "META_FSM.cfg").read_text(encoding="utf-8")
    assert "SwapCadenceBounded ==" in tla
    assert "SwapCadenceBounded" in cfg


def test_meta_fsm_variables_unchanged_no_new_state():
    """Rule 9.30.3：不新增狀態變數（仍 mstate/churn/cap）→ 本軌 reachable(13 distinct) 不回歸。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert "VARIABLES mstate," in tla
    assert "vars == <<mstate, churn, cap>>" in tla
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla


def test_no_sixth_formal_track():
    """Rule 9.30.3：不增第六軌——formal/ 仍恰 5 個 .tla。"""
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_single_track_no_swap_leak():
    """Rule 9.30.3：self-invention/swap 不污染單軌 SDD_FSM.tla。"""
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "SwapCadence" not in sdd and "value-dimension" not in sdd and "self-invention" not in sdd


# ---------------------------------------------------------------------------
# ACT-132 — steersman 候選池外發明 diff + 退役聯動 diff（advisory + 反 big-bang + 人工 gate）
# ---------------------------------------------------------------------------

def _accepted_invent_round(k=1):
    cands = S.enumerate_inventions(budget=8)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda d: scores.get(d.name, 0.0)
    return S.invent_round(ev, candidates=cands, k=k)


def test_render_semantic_invention_proposal():
    from tools.fsm_runtime.steersman_renderer import render_semantic_invention_proposal
    rnd = _accepted_invent_round(k=1)
    verdict = DO.evaluate_invented_dimension(
        InventedDimension.of("mean", ("rollback_steps", "blast_radius")),
        [_true_feature_case()], coverage_margin=0.1)
    md = render_semantic_invention_proposal(rnd, verdict=verdict)
    assert "Self-Inventing Value Dimensions" in md
    assert "候選池外" in md
    assert "K_dim=1" in md
    assert "signoff" in md and "待人工" in md
    assert "非自指" in md
    assert verdict.corpus_fingerprint in md
    assert rnd.selected[0].dimension.name in md


def test_render_invention_shows_deferred_under_bigbang():
    from tools.fsm_runtime.steersman_renderer import render_semantic_invention_proposal
    rnd = _accepted_invent_round(k=1)
    md = render_semantic_invention_proposal(rnd)
    assert "K_dim=1" in md
    assert rnd.deferred[0] in md


def test_render_invention_never_auto_commits():
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_semantic_invention_proposal)
    assert "record_rule_add" not in src and "adopt_invention" not in src and "swap_dimension" not in src


def test_render_invention_no_verdict_degrades():
    from tools.fsm_runtime.steersman_renderer import render_semantic_invention_proposal
    md = render_semantic_invention_proposal(_accepted_invent_round(k=1))
    assert "候選池外" in md and "待人工" in md


def test_render_dimension_swap_proposal():
    from tools.fsm_runtime.steersman_renderer import render_dimension_swap_proposal
    from tools.fsm_runtime.meta_halt.meta_halt_monitor import SwapGuardResult
    out_dim = InventedDimension.of("mean", ("oncall_pages",))
    in_dim = InventedDimension.of("max", ("rollback_steps", "blast_radius"))
    state = SwapGuardResult(allowed=True, in_tier=80, out_tier=40, margin=0,
                            window_swaps=1, rate_max=3, window=12)
    md = render_dimension_swap_proposal(out_dim, in_dim, out_tier=40, in_tier=80, swap_state=state)
    assert "Retirement-Swap" in md
    assert "net" in md.lower() or "基數" in md
    assert out_dim.name in md and in_dim.name in md
    assert "signoff" in md
    assert "SDD_DIM_SWAP_RATE_MAX" in md


def test_render_swap_never_auto_commits():
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_dimension_swap_proposal)
    assert "record_rule_add" not in src and "swap_dimension" not in src


# ---------------------------------------------------------------------------
# ACT-134 — chaos 雙故障型 deterministic bounded（單元層；100 輪整合在 chaos 套件）
# ---------------------------------------------------------------------------

def test_chaos_dimension_invention_goodhart_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _dimension_invention_goodhart_flap_is_bounded
    assert _dimension_invention_goodhart_flap_is_bounded()


def test_chaos_dimension_swap_thrash_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _dimension_swap_thrash_flap_is_bounded
    assert _dimension_swap_thrash_flap_is_bounded()


def test_chaos_new_fault_types_registered():
    from tools.fsm_runtime.chaos_runner import FAULT_TYPES
    assert "DIMENSION_INVENTION_GOODHART_FLAP" in FAULT_TYPES
    assert "DIMENSION_SWAP_THRASH_FLAP" in FAULT_TYPES


# ---------------------------------------------------------------------------
# Phase R ownership（R-9.30 enforces 連結）
# ---------------------------------------------------------------------------

def test_phase_r_rule_file_exists():
    assert (ROOT.parent.parent / "governance" / "rules"
            / "R-9.30-self-inventing-value-dimensions-phase-r.yaml").exists()
