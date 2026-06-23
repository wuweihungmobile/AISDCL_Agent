# enforces (governance rules): R-9.29
"""Phase Q / ACT-123~128 — 價值維度的自我擴充（meta-meta 層有界本體論演化）回歸守門.

涵蓋：
  - ACT-123 Value Dimension Registry：候選維度池、提案骨架、bounded 搜尋、deterministic、
    只透過注入 evaluate 取必要性（結構性無自評）、proposed-only、反 big-bang K_dim=1 截斷、對抗分離
  - ACT-124 Dimension Necessity Oracle：增量覆蓋 ∧ 非冗餘 held-out 評估、維度 Goodhart（噪音軸+
    冗餘軸）零漏放、necessity tier = 唯一來源、proposer 自評通過但 oracle 否決以 oracle 為準、隔離
  - ACT-125 DimensionCardinalityBounded：維度基數 stock 天花板、爆炸→MFSM_ESCALATION、不增第六軌
  - ACT-126 steersman 本體論 diff（advisory + 反 big-bang 增維 + 人工 gate）
  - ACT-128 chaos DIMENSION_GOODHART_FLAP / DIMENSION_EXPLOSION_FLAP 有界
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from tools.fsm_runtime import value_dimension_registry as VDR
from tools.fsm_runtime import dimension_necessity_oracle as DO
from tools.fsm_runtime.value_dimension_registry import ValueDimension

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# ACT-123 — Value Dimension Registry + 維度提案骨架
# ---------------------------------------------------------------------------

def test_candidate_pool_nonempty_and_bounded():
    pool = VDR.candidate_pool()
    assert len(pool) >= 4
    # SearchBounded（Rule 9.29.1）
    assert len(VDR.candidate_pool(budget=2)) == 2


def test_candidate_pool_deterministic():
    assert VDR.candidate_pool() == VDR.candidate_pool()
    assert VDR.candidate_names() == sorted(VDR.candidate_names())


def test_dimension_namespace_and_fingerprint():
    d = ValueDimension.of("maintainability_cost", probe=("cyclomatic", "coupling"))
    fp = d.fingerprint()
    assert fp.startswith("value-dimension:")
    assert VDR.is_dimension_fingerprint(fp)
    # deterministic + 與 probe 序無關
    d2 = ValueDimension.of("maintainability_cost", probe=("coupling", "cyclomatic"))
    assert d.fingerprint() == d2.fingerprint()
    d3 = ValueDimension.of("security_surface", probe=("cyclomatic", "coupling"))
    assert d.fingerprint() != d3.fingerprint()


def test_dimension_fp_not_calibration():
    """Rule 9.29.3：value-dimension 不以 `-profile:` 結尾 → 與 Phase P calibration 聚合守門互不干涉。"""
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    fp = ValueDimension.of("maintainability_cost").fingerprint()
    assert ML.is_dimension_fingerprint(fp)
    assert not ML.is_calibration_fingerprint(fp)


def test_propose_finds_necessary_dimension():
    """proposer 在注入必要性上找到真必要新維度（達 margin、送 signoff）。"""
    ev = lambda d: 0.21 if d.name == "maintainability_cost" else 0.0
    prop = VDR.propose(ev)
    assert prop.accepted
    assert prop.dimension.name == "maintainability_cost"
    assert prop.necessity >= prop.margin
    assert prop.to_dict()["maturity"] == "proposed"


def test_propose_search_bounded():
    prop = VDR.propose(lambda d: 0.5, budget=3)
    assert prop.nodes_searched <= 3


def test_propose_deterministic():
    ev = lambda d: {"maintainability_cost": 0.3, "security_surface": 0.2}.get(d.name, 0.0)
    p1 = VDR.propose(ev)
    p2 = VDR.propose(ev)
    assert p1.dimension == p2.dimension and p1.necessity == p2.necessity


def test_propose_no_acceptance_when_all_below_margin():
    """所有候選必要性 < margin（維度已足夠）→ 不提案。"""
    prop = VDR.propose(lambda d: 0.0)
    assert not prop.accepted


def test_propose_only_uses_injected_evaluate():
    seen = []

    def spy(d):
        seen.append(d)
        return 0.0
    VDR.propose(spy, budget=4)
    assert len(seen) >= 1


def test_propose_round_respects_bigbang_kdim():
    """一輪至多 K_dim 條新維度進 proposed（按 necessity 取前 K_dim），其餘順延（Rule 9.29.4）。"""
    ev = lambda d: {"maintainability_cost": 0.5, "security_surface": 0.4,
                    "operability_cost": 0.3}.get(d.name, 0.0)
    rnd = VDR.propose_expansion_round(ev, k=1)
    assert len(rnd.selected) == 1                       # 反 big-bang：預設 K_dim=1
    assert rnd.selected[0].dimension.name == "maintainability_cost"   # necessity 最高
    assert len(rnd.deferred) == 2
    assert all(p.accepted for p in rnd.selected)


def test_propose_round_default_kdim_is_one():
    """NoUnboundedOntologyExpansion：env 未設時 K_dim 預設 1（比 Phase P calibration K=2 更嚴）。"""
    assert VDR.dim_expand_k() == 1


def test_expand_k_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_DIM_EXPAND_K", raising=False)
    assert VDR.dim_expand_k() == 1
    monkeypatch.setenv("SDD_DIM_EXPAND_K", "99")
    assert VDR.dim_expand_k() == 8
    monkeypatch.setenv("SDD_DIM_EXPAND_K", "0")
    assert VDR.dim_expand_k() == 1


def test_propose_budget_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_DIM_PROPOSE_BUDGET", raising=False)
    assert VDR.dim_propose_budget() == 32
    monkeypatch.setenv("SDD_DIM_PROPOSE_BUDGET", "9999")
    assert VDR.dim_propose_budget() == 128
    monkeypatch.setenv("SDD_DIM_PROPOSE_BUDGET", "1")
    assert VDR.dim_propose_budget() == 4


def test_registry_structurally_blind_to_oracle():
    """Rule 9.29.2：registry/proposer **不得 import** 任何必要性 oracle、不得觸及語料（對抗分離）。"""
    tree = ast.parse(inspect.getsource(VDR))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported |= {a.name for a in node.names}
    assert not any("oracle" in m.lower() for m in imported), "registry 不得 import oracle（破對抗分離）"
    assert not any("necessity" in m.lower() for m in imported)
    assert not any("held_out" in m.lower() for m in imported)


def test_adopt_requires_human_signoff(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    d = ValueDimension.of("maintainability_cost", probe=("cyclomatic",))
    with pytest.raises(VDR.SignoffRequired):
        VDR.adopt_dimension(d, 50, ledger_path=led)
    assert not led.exists()


def test_adopt_goes_through_meta_guard(tmp_path):
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    led = tmp_path / "meta-loop-ledger.yaml"
    d = ValueDimension.of("security_surface", probe=("exposed_endpoints",))
    ev = VDR.adopt_dimension(d, 70, human_signoff=True, ledger_path=led)
    assert ev.fingerprint.startswith("value-dimension:")
    assert ML.compute_churn(ev.fingerprint, ledger_path=led) == 0      # 首採納非 churn
    assert len(ML.active_value_dimensions(ledger_path=led)) == 1


def test_record_round_writes_pending_signoff(tmp_path):
    ev = lambda d: 0.3 if d.name == "maintainability_cost" else 0.0
    rnd = VDR.propose_expansion_round(ev, k=1)
    led = tmp_path / "value-dimension-ledger.yaml"
    entry = VDR.record_round(rnd, ledger_path=led, ts="2026-06-04T00:00:00+00:00")
    assert led.exists()
    assert entry["signoff"] == "pending"
    assert all(p["maturity"] == "proposed" for p in entry["selected"])


# ---------------------------------------------------------------------------
# ACT-125 — DimensionCardinalityBounded（stock 天花板 + META_FSM 納管，不增第六軌）
# ---------------------------------------------------------------------------

def _make_dims(n):
    return [ValueDimension.of("auto_dim_%d" % i, probe=("x",)) for i in range(n)]


def test_dimension_cardinality_bounded(tmp_path, monkeypatch):
    """Rule 9.29.3：現存活躍維度數觸頂 → DimensionCardinalityExceeded（per-fingerprint churn=0）。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.setenv("SDD_DIM_CARDINALITY_MAX", "4")
    led = tmp_path / "meta-loop-ledger.yaml"
    dims = _make_dims(5)
    for d in dims[:4]:                                  # 前 4 條成功（< max）
        VDR.adopt_dimension(d, 50, human_signoff=True, ledger_path=led)
    with pytest.raises(MM.DimensionCardinalityExceeded):  # 第 5 條觸頂
        VDR.adopt_dimension(dims[4], 50, human_signoff=True, ledger_path=led)


def test_cardinality_storm_escalates_meta_state(tmp_path, monkeypatch):
    """維度基數觸頂使整個 META_FSM meta_state → MFSM_ESCALATION（Rule 9.29.3）。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.setenv("SDD_DIM_CARDINALITY_MAX", "3")
    led = tmp_path / "meta-loop-ledger.yaml"
    for d in _make_dims(3):                             # 採滿 max
        VDR.adopt_dimension(d, 50, human_signoff=True, ledger_path=led)
    assert MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"


def test_cardinality_guard_ignores_non_dimension(tmp_path):
    """非 value-dimension 指紋（calibration profile / SLV 規則）不受 stock 天花板守門。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    led = tmp_path / "meta-loop-ledger.yaml"
    res = MM.guard_dimension_expansion("adversarial-profile:abc", ledger_path=led)
    assert res.allowed and res.active == 0
    res2 = MM.guard_dimension_expansion("some-slv-rule-tokenbag", ledger_path=led)
    assert res2.allowed


def test_retire_then_readopt_requires_capability_delta(tmp_path):
    """Rule 9.29.3：退役維度再採納須挾 necessity capability-delta（維度棘輪，沿用 GraduationRatchet）。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    led = tmp_path / "meta-loop-ledger.yaml"
    d = ValueDimension.of("operability_cost", probe=("alert_noise",))
    VDR.adopt_dimension(d, 50, human_signoff=True, ledger_path=led)
    VDR.retire_dimension(d, 50, ledger_path=led)
    # 無 capability-delta re-adopt（cap 仍 50）→ GraduationRatchetViolation
    with pytest.raises(MM.GraduationRatchetViolation):
        VDR.adopt_dimension(d, 50, human_signoff=True, ledger_path=led)


def test_cardinality_max_env_clamp(monkeypatch):
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.delenv("SDD_DIM_CARDINALITY_MAX", raising=False)
    assert MM.dimension_cardinality_max() == 16
    monkeypatch.setenv("SDD_DIM_CARDINALITY_MAX", "999")
    assert MM.dimension_cardinality_max() == 32
    monkeypatch.setenv("SDD_DIM_CARDINALITY_MAX", "0")
    assert MM.dimension_cardinality_max() == 1


def test_no_sixth_formal_track():
    """Rule 9.29.3：不增第六軌——formal/ 仍恰 5 個 .tla。"""
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_meta_fsm_states_unchanged():
    """META_FSM.tla 狀態宇宙不因 value-dimension 改動（仍 5 態）。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla


def test_meta_fsm_declares_dimension_invariant():
    """ACT-125：META_FSM.tla 定義 DimensionCardinalityBounded，且 .cfg INVARIANT 區塊列入（TLC 會檢查）。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal" / "META_FSM.cfg").read_text(encoding="utf-8")
    assert "DimensionCardinalityBounded ==" in tla
    assert "DimensionCardinalityBounded" in cfg


def test_meta_fsm_variables_unchanged_no_new_state():
    """Rule 9.29.3：不新增狀態變數（仍 mstate/churn/cap）→ 本軌 reachable(13 distinct) 不回歸。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert "VARIABLES mstate," in tla
    assert "vars == <<mstate, churn, cap>>" in tla


def test_single_track_no_dimension_leak():
    """Rule 9.29.3：value-dimension 不污染單軌 SDD_FSM.tla。"""
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "value-dimension" not in sdd and "DimensionCardinality" not in sdd


# ---------------------------------------------------------------------------
# ACT-124 — Dimension Necessity Oracle（meta-meta 反 Goodhart）
# ---------------------------------------------------------------------------

def _true_case():
    """真必要：baseline 選 BAD（existing 誤排），augmented（新軸）翻到 GOOD。"""
    return DO.DimHeldOutCase(case_id="T", dimension_name="d", candidates=[
        DO.DimCandidate(real_quality=0.9, existing_cost=5.0, dim_value=0.0),   # GOOD
        DO.DimCandidate(real_quality=0.3, existing_cost=2.0, dim_value=9.0),   # BAD（baseline 選）
        DO.DimCandidate(real_quality=0.6, existing_cost=4.0, dim_value=4.0),   # MID
    ])


def _noise_case():
    """自利噪音軸：新軸 flip 到真實品質不更好的候選 → 增量覆蓋 ≈ 0。"""
    return DO.DimHeldOutCase(case_id="N", dimension_name="d", candidates=[
        DO.DimCandidate(real_quality=0.6, existing_cost=2.0, dim_value=5.0),   # baseline 選
        DO.DimCandidate(real_quality=0.6, existing_cost=3.0, dim_value=0.0),   # augmented 選（同品質）
        DO.DimCandidate(real_quality=0.4, existing_cost=4.0, dim_value=8.0),
    ])


def _redundant_case():
    """冗餘軸：dim_value ∝ existing_cost（再投影）→ 一致率 1.0 → 冗餘。"""
    return DO.DimHeldOutCase(case_id="R", dimension_name="d", candidates=[
        DO.DimCandidate(real_quality=0.6, existing_cost=2.0, dim_value=2.0),
        DO.DimCandidate(real_quality=0.5, existing_cost=3.0, dim_value=3.0),
        DO.DimCandidate(real_quality=0.4, existing_cost=4.0, dim_value=4.0),
    ])


def test_true_necessity_detected():
    v = DO.evaluate_dimension(ValueDimension.of("d"), [_true_case()], coverage_margin=0.1)
    assert v.incremental_coverage == pytest.approx(0.6)
    assert v.redundancy < v.redundancy_max
    assert v.necessary and v.tier == 60


def test_noise_axis_rejected_by_coverage():
    v = DO.evaluate_dimension(ValueDimension.of("d"), [_noise_case()], coverage_margin=0.1)
    assert v.incremental_coverage < v.coverage_margin   # 增量覆蓋 ≈ 0
    assert not v.necessary and v.tier == 0


def test_redundant_axis_rejected_by_redundancy():
    v = DO.evaluate_dimension(ValueDimension.of("d"), [_redundant_case()], coverage_margin=0.1)
    assert v.redundancy >= v.redundancy_max             # 與既有排序一致率 1.0
    assert not v.necessary


def test_redundancy_is_independent_gate():
    """關鍵：即使把 coverage_margin 放寬到負值（覆蓋必過），冗餘軸仍被非冗餘度獨立否決。"""
    v = DO.evaluate_dimension(ValueDimension.of("d"), [_redundant_case()],
                              coverage_margin=-1.0)       # 覆蓋門檻放寬到必過
    assert v.incremental_coverage >= v.coverage_margin   # 覆蓋這關會過
    assert v.redundancy >= v.redundancy_max              # 但冗餘度仍觸門檻
    assert not v.necessary, "冗餘軸須被非冗餘度獨立否決（過擬合防護）"


def test_necessity_score_zero_when_not_necessary():
    """necessity_score（注入 proposer 的純量）：必要回增量覆蓋、不必要回 0（反自評接縫）。"""
    assert DO.necessity_score(ValueDimension.of("d"), [_true_case()]) == pytest.approx(0.6)
    assert DO.necessity_score(ValueDimension.of("d"), [_noise_case()]) == 0.0
    assert DO.necessity_score(ValueDimension.of("d"), [_redundant_case()]) == 0.0


def test_proposer_self_passes_but_oracle_rejects():
    """關鍵：proposer 樸素自評視噪音軸為必要，但 oracle 在 held-out 上否決 → 以 oracle 為準。"""
    noise_dim = ValueDimension.of("proposer_self_score", probe=("self",))
    # (a) proposer 樸素自評：對任何維度都「覺得必要」（盲於真實增量覆蓋）→ 若無 oracle 就中招
    naive_self = lambda d: 0.9
    per = VDR.propose(naive_self, pool=[noise_dim])
    assert per.accepted, "proposer 樸素自評視之為必要（接縫前提）"
    # (b) 但 oracle 在 held-out 上判不必要（噪音軸增量覆蓋 ≈ 0）→ 以 oracle 為準
    noise_corpus = [DO.DimHeldOutCase(case_id="N", dimension_name="proposer_self_score",
                                      candidates=_noise_case().candidates)]
    v = DO.evaluate_dimension(noise_dim, noise_corpus, coverage_margin=0.1)
    assert not v.necessary


def test_evaluate_dimension_bounded(monkeypatch):
    corpus = [_true_case() for _ in range(100)]
    v = DO.evaluate_dimension(ValueDimension.of("d"), corpus, max_cases=5)
    assert v.examined == 5


def test_corpus_fingerprint_tamper_and_stable():
    base = [_true_case()]
    assert DO.corpus_fingerprint(base) == DO.corpus_fingerprint([_true_case()])
    tampered = [_true_case()]
    tampered[0].candidates[1].real_quality = 0.95        # 竄改 BAD 真實品質
    assert DO.corpus_fingerprint(base) != DO.corpus_fingerprint(tampered)


def test_redundancy_max_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_DIM_REDUNDANCY_MAX", raising=False)
    assert DO.dim_redundancy_max() == 0.95
    monkeypatch.setenv("SDD_DIM_REDUNDANCY_MAX", "2.0")
    assert DO.dim_redundancy_max() == 1.0
    monkeypatch.setenv("SDD_DIM_REDUNDANCY_MAX", "-1")
    assert DO.dim_redundancy_max() == 0.0


def test_proposer_cannot_reach_necessity_corpus():
    """Rule 9.29.2 對抗分離：registry（proposer）無法觸及必要性語料載入符號/路徑。"""
    assert not hasattr(VDR, "load_necessity_corpus")
    assert not hasattr(VDR, "DimHeldOutCase")
    src = inspect.getsource(VDR)
    assert "dimension_necessity_oracle" not in src
    assert "held-out-corpus" not in src and "held_out" not in src.lower()


# ---------------------------------------------------------------------------
# ACT-124 驗收 — 16 凍結維度必要性語料統計性驗收（8 真必要 + 4 噪音軸 + 4 冗餘軸；零漏放）
# ---------------------------------------------------------------------------

import yaml as _yaml  # noqa: E402


def _load_dim_yaml_meta():
    out = []
    for p in sorted(DO.HELD_OUT_CORPUS_DIR.glob("DIM-*.yaml")):
        doc = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if doc.get("expect") in ("true_necessity", "noise_axis", "redundant_axis"):
            out.append(doc)
    return out


def _verdict_for(doc):
    dim = ValueDimension.of(doc["dimension_name"])
    return DO.evaluate_dimension(dim, DO.load_necessity_corpus(), coverage_margin=0.1)


def test_dim_corpus_has_16_labelled_cases():
    metas = _load_dim_yaml_meta()
    true_cases = [m for m in metas if m["expect"] == "true_necessity"]
    noise_cases = [m for m in metas if m["expect"] == "noise_axis"]
    redundant_cases = [m for m in metas if m["expect"] == "redundant_axis"]
    assert len(true_cases) == 8, f"真必要 fixture 應為 8，實得 {len(true_cases)}"
    assert len(noise_cases) == 4, f"噪音軸 fixture 應為 4，實得 {len(noise_cases)}"
    assert len(redundant_cases) == 4, f"冗餘軸 fixture 應為 4，實得 {len(redundant_cases)}"


@pytest.mark.parametrize("doc", [m for m in _load_dim_yaml_meta()
                                 if m["expect"] == "true_necessity"],
                         ids=lambda d: d["case_id"])
def test_dim_true_necessity_detected(doc):
    v = _verdict_for(doc)
    assert v.necessary, f"{doc['case_id']} 真必要卻被判不必要（cov={v.incremental_coverage}, redun={v.redundancy}）"
    assert v.tier == int(round(v.incremental_coverage * 100))


@pytest.mark.parametrize("doc", [m for m in _load_dim_yaml_meta()
                                 if m["expect"] in ("noise_axis", "redundant_axis")],
                         ids=lambda d: d["case_id"])
def test_dim_goodhart_intercepted(doc):
    """每個維度 Goodhart（噪音軸/冗餘軸）：oracle 必判不必要（零漏放，安全紅線）。"""
    v = _verdict_for(doc)
    assert not v.necessary, f"{doc['case_id']} 維度 Goodhart 漏放（安全紅線破！cov={v.incremental_coverage}, redun={v.redundancy}）"


def test_dim_acceptance_rates_meet_blueprint():
    """ACT-124 驗收統計：真必要偵出率 ≥ 85%、維度 Goodhart 攔截率 100%（零漏放）。"""
    metas = _load_dim_yaml_meta()
    true_cases = [m for m in metas if m["expect"] == "true_necessity"]
    goodhart_cases = [m for m in metas if m["expect"] in ("noise_axis", "redundant_axis")]
    true_detected = sum(1 for m in true_cases if _verdict_for(m).necessary)
    goodhart_intercepted = sum(1 for m in goodhart_cases if not _verdict_for(m).necessary)
    assert true_detected / len(true_cases) >= 0.85, \
        f"真必要偵出率 {true_detected}/{len(true_cases)} < 85%"
    assert goodhart_intercepted == len(goodhart_cases), \
        f"維度 Goodhart 攔截率非 100%（{goodhart_intercepted}/{len(goodhart_cases)}，零漏放破！）"


# ---------------------------------------------------------------------------
# ACT-126 — steersman 本體論 diff（advisory + 反 big-bang 增維 + 人工 gate）
# ---------------------------------------------------------------------------

def _accepted_expansion_round(k=1):
    ev = lambda d: {"maintainability_cost": 0.5, "security_surface": 0.4,
                    "operability_cost": 0.3}.get(d.name, 0.0)
    return VDR.propose_expansion_round(ev, k=k)


def test_render_ontology_expansion_proposal():
    from tools.fsm_runtime.steersman_renderer import render_ontology_expansion_proposal
    rnd = _accepted_expansion_round(k=1)
    verdict = DO.evaluate_dimension(ValueDimension.of("d"), [_true_case()], coverage_margin=0.1)
    md = render_ontology_expansion_proposal(rnd, verdict=verdict)
    assert "本體論" in md
    assert "Self-Expanding Value Dimensions" in md
    assert "K_dim=1" in md                               # 反 big-bang 增維上限明示（Rule 9.29.4）
    assert "signoff" in md                               # 人工 gate
    assert "待人工" in md
    assert verdict.corpus_fingerprint in md
    assert rnd.selected[0].dimension.name in md


def test_render_shows_deferred_under_bigbang():
    """K_dim=1 → 渲染明示順延的維度（反 big-bang 增維，Rule 9.29.4）。"""
    from tools.fsm_runtime.steersman_renderer import render_ontology_expansion_proposal
    rnd = _accepted_expansion_round(k=1)
    md = render_ontology_expansion_proposal(rnd)
    assert "K_dim=1" in md
    assert rnd.deferred[0] in md                         # 順延者被列出


def test_render_ontology_never_auto_commits():
    """渲染器純文字產出，不觸發任何採納/納入（無 record_rule_add / adopt_dimension 副作用）。"""
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_ontology_expansion_proposal)
    assert "record_rule_add" not in src and "adopt_dimension" not in src


def test_render_ontology_no_verdict_degrades():
    from tools.fsm_runtime.steersman_renderer import render_ontology_expansion_proposal
    rnd = _accepted_expansion_round(k=1)
    md = render_ontology_expansion_proposal(rnd)          # 無 verdict
    assert "本體論" in md and "待人工" in md


# ---------------------------------------------------------------------------
# ACT-128 — chaos 雙故障型 deterministic bounded（單元層；100 輪整合在 test 末）
# ---------------------------------------------------------------------------

def test_chaos_dimension_goodhart_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _dimension_goodhart_flap_is_bounded
    assert _dimension_goodhart_flap_is_bounded()


def test_chaos_dimension_explosion_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _dimension_explosion_flap_is_bounded
    assert _dimension_explosion_flap_is_bounded()
