# enforces (governance rules): R-9.31
"""Phase S / ACT-135~140 — 生成文法詞彙自我擴充（meta⁴）+ 多維度批次退役聯動 回歸守門.

涵蓋：
  - ACT-135 Vocabulary Genesis Grammar：VOCAB 外有界詞彙生成文法（可枚舉、cap budget）、詞彙自指
    vocab_self_reference_guard 零漏放、deterministic、只透過注入 evaluate 取必要性（結構性無自評）、
    proposed-only、反 big-bang K_vocab=1 截斷、對抗分離（不 import oracle）、expanded_vocab
  - ACT-136 feature-grounded 必要性 oracle：evaluate_genesis_feature（不靠特徵欄名）、詞彙外真必要
    偵出、詞彙自我發明 Goodhart（噪音字+冗餘字）零漏放、necessity tier 唯一來源、隔離
  - ACT-137 詞彙 stock VocabGenesisBounded + 多維度批次退役 BatchSwapCadenceBounded：詞彙基數觸頂→
    VocabCardinalityExceeded→MFSM_ESCALATION、批次大小界/批次聚合棘輪/批次速率三鎖、net 非增、
    META_FSM 不增第六軌/不增狀態變數
  - ACT-138 steersman 詞彙外發明 diff + 批次重構 diff（advisory + 反 big-bang + 人工 gate）
  - ACT-140 chaos VOCAB_GENESIS_GOODHART_FLAP / BATCH_SWAP_THRASH_FLAP 有界
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from tools.fsm_runtime import vocabulary_genesis as VG
from tools.fsm_runtime import dimension_semantics_synthesizer as S
from tools.fsm_runtime import dimension_necessity_oracle as DO
from tools.fsm_runtime.vocabulary_genesis import GenesisFeature
from tools.fsm_runtime.dimension_semantics_synthesizer import InventedDimension

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# ACT-135 — Vocabulary Genesis Grammar（VOCAB 外有界詞彙生成文法 + 詞彙自指守門，meta⁴）
# ---------------------------------------------------------------------------

def test_enumerate_genesis_bounded():
    """Rule 9.31.1 有界詞彙生成文法：枚舉節點 <= budget（VOCAB 外≠無界）。"""
    assert len(VG.enumerate_genesis_features(budget=10)) == 10
    assert len(VG.enumerate_genesis_features(budget=1)) == 1
    # 文法總大小 = |SOURCES| × |TRANSFORMS|；超大 budget 被文法大小截住（仍有界）
    full = len(VG.SOURCES) * len(VG.TRANSFORMS)
    assert len(VG.enumerate_genesis_features(budget=999)) == full


def test_enumerate_genesis_deterministic():
    a = VG.enumerate_genesis_features(budget=20)
    b = VG.enumerate_genesis_features(budget=20)
    assert [g.name for g in a] == [g.name for g in b]


def test_genesis_feature_term_name_fingerprint():
    g = GenesisFeature.of("secret", "window")
    assert g.term == "secret.window"
    assert g.name == "vocab::secret.window"
    fp = g.fingerprint()
    assert fp.startswith("vocab-genesis:")
    # source/transform 不同 → 指紋不同
    assert g.fingerprint() != GenesisFeature.of("secret", "rate").fingerprint()
    assert g.fingerprint() != GenesisFeature.of("identity", "window").fingerprint()


def test_genesis_feature_apply():
    g = GenesisFeature.of("secret", "window")
    assert g.apply({"secret.window": 4.0}) == 4.0
    assert g.apply({"other.term": 9.0}) == 0.0   # 缺特徵以 0.0 計


def test_genesis_fingerprint_is_vocab_genesis_namespace():
    """Rule 9.31.3：詞彙發明字走獨立 vocab-genesis 命名空間（與維度/calibration 分開治理）。"""
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    fp = GenesisFeature.of("secret", "window").fingerprint()
    assert ML.is_vocab_genesis_fingerprint(fp)
    assert not ML.is_dimension_fingerprint(fp)
    assert not ML.is_calibration_fingerprint(fp)


def test_vocab_self_reference_guard_rejects():
    """Rule 9.31.2 反自利第一閘：自指 source/transform 零漏放。"""
    for s, t in (("self_score", "rate"), ("proposer_x", "rate"), ("necessity", "window"),
                 ("oracle_x", "depth"), ("secret", "self_score")):
        assert VG.is_vocab_self_referential(GenesisFeature.of(s, t)), f"{s}.{t} 應被判自指"
    assert not VG.is_vocab_self_referential(GenesisFeature.of("secret", "window"))


def test_vocab_self_reference_guard_filters_list():
    gs = [GenesisFeature.of("secret", "window"),
          GenesisFeature.of("self_score", "rate"),
          GenesisFeature.of("identity", "depth")]
    survivors = VG.vocab_self_reference_guard(gs)
    assert len(survivors) == 2
    assert all(not VG.is_vocab_self_referential(g) for g in survivors)


def test_enumerate_never_emits_self_referential():
    """生產 SOURCES/TRANSFORMS 無自指 token → 枚舉恆不產自指詞彙（guard 仍對受擾注入零漏放）。"""
    gs = VG.enumerate_genesis_features(budget=999)
    assert all(not VG.is_vocab_self_referential(g) for g in gs)


def test_genesis_finds_necessary():
    target = GenesisFeature.of("secret", "window")
    ev = lambda g: 0.22 if g.name == target.name else 0.0
    prop = VG.genesis(ev, candidates=VG.enumerate_genesis_features(budget=999))
    assert prop.accepted
    assert prop.feature.name == target.name
    assert prop.necessity >= prop.margin
    assert prop.to_dict()["maturity"] == "proposed"


def test_genesis_search_bounded():
    prop = VG.genesis(lambda g: 0.5, budget=5)
    assert prop.nodes_searched <= 5


def test_genesis_no_acceptance_when_all_below_margin():
    prop = VG.genesis(lambda g: 0.0)
    assert not prop.accepted


def test_genesis_round_respects_bigbang_kvocab():
    """一輪至多 K_vocab 個詞彙發明進 proposed（按 necessity 取前 K_vocab），其餘順延（Rule 9.31.4）。"""
    cands = VG.enumerate_genesis_features(budget=999)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda g: scores.get(g.name, 0.0)
    rnd = VG.genesis_round(ev, candidates=cands, k=1)
    assert len(rnd.selected) == 1
    assert rnd.selected[0].feature.name == cands[0].name   # necessity 最高
    assert len(rnd.deferred) == 2
    assert all(p.accepted for p in rnd.selected)


def test_genesis_round_default_kvocab_is_one():
    """NoUnboundedVocabGenesis：env 未設時 K_vocab 預設 1（沿用 Phase Q/R）。"""
    from tools.fsm_runtime.value_dimension_registry import dim_expand_k
    assert dim_expand_k() == 1


def test_vocab_budget_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_DIM_VOCAB_BUDGET", raising=False)
    assert VG.vocab_budget() == 32
    monkeypatch.setenv("SDD_DIM_VOCAB_BUDGET", "9999")
    assert VG.vocab_budget() == 128
    monkeypatch.setenv("SDD_DIM_VOCAB_BUDGET", "1")
    assert VG.vocab_budget() == 8


def test_expanded_vocab_unions_base():
    from tools.fsm_runtime.dimension_semantics_synthesizer import VOCAB
    assert VG.expanded_vocab([]) == VOCAB
    ext = VG.expanded_vocab(["secret.window"])
    assert "secret.window" in ext and len(ext) == len(VOCAB) + 1
    # 去重保序
    assert VG.expanded_vocab(["secret.window", "secret.window"]) == ext


def test_genesis_structurally_blind_to_oracle():
    """Rule 9.31.2：vocabulary_genesis **不得 import** 任何必要性 oracle、不得觸及語料（對抗分離）。"""
    tree = ast.parse(inspect.getsource(VG))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported |= {a.name for a in node.names}
    assert not any("oracle" in m.lower() for m in imported), "vocabulary_genesis 不得 import oracle"
    assert not any("necessity" in m.lower() for m in imported)
    src = inspect.getsource(VG)
    assert "dimension_necessity_oracle" not in src
    assert "load_genesis_corpus" not in src
    assert "held_out" not in src.lower() and "held-out-corpus" not in src


def test_adopt_genesis_requires_human_signoff(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    with pytest.raises(VG.SignoffRequired):
        VG.adopt_genesis_feature(GenesisFeature.of("secret", "window"), 50, ledger_path=led)
    assert not led.exists()


def test_adopt_genesis_rejects_self_referential(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    with pytest.raises(VG.SelfReferentialGenesis):
        VG.adopt_genesis_feature(GenesisFeature.of("self_score", "rate"), 50,
                                 human_signoff=True, ledger_path=led)
    assert not led.exists()


def test_adopt_genesis_goes_through_meta_guard(tmp_path):
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    led = tmp_path / "meta-loop-ledger.yaml"
    ev = VG.adopt_genesis_feature(GenesisFeature.of("secret", "window"), 70,
                                  human_signoff=True, ledger_path=led)
    assert ev.fingerprint.startswith("vocab-genesis:")
    assert ML.compute_churn(ev.fingerprint, ledger_path=led) == 0
    assert len(ML.active_vocab_genesis_features(ledger_path=led)) == 1


def test_record_genesis_round_writes_pending_signoff(tmp_path):
    cands = VG.enumerate_genesis_features(budget=999)
    ev = lambda g: 0.3 if g.name == cands[0].name else 0.0
    rnd = VG.genesis_round(ev, candidates=cands, k=1)
    led = tmp_path / "value-dimension-ledger.yaml"
    entry = VG.record_round(rnd, ledger_path=led, ts="2026-06-04T00:00:00+00:00")
    assert led.exists()
    assert entry["signoff"] == "pending"
    assert all(p["maturity"] == "proposed" for p in entry["selected"])


# ---------------------------------------------------------------------------
# ACT-136 — feature-grounded 必要性 oracle（VOCAB 外詞彙自我發明反 Goodhart，meta⁴）
# ---------------------------------------------------------------------------

def _true_genesis_case():
    """真必要：baseline 選 BAD（existing 誤排），詞彙字（secret.window 低）翻到 GOOD。"""
    return DO.GenesisCase(case_id="T", candidates=[
        DO.GenesisCandidate(0.9, 5.0, {"secret.window": 0.0}),   # GOOD
        DO.GenesisCandidate(0.3, 2.0, {"secret.window": 9.0}),   # BAD（baseline 選）
        DO.GenesisCandidate(0.6, 4.0, {"secret.window": 4.0})])  # MID


def _noise_genesis_case():
    return DO.GenesisCase(case_id="N", candidates=[
        DO.GenesisCandidate(0.6, 2.0, {"network.rate": 5.0}),
        DO.GenesisCandidate(0.6, 3.0, {"network.rate": 0.0}),
        DO.GenesisCandidate(0.4, 4.0, {"network.rate": 8.0})])


def _redundant_genesis_case():
    return DO.GenesisCase(case_id="R", candidates=[
        DO.GenesisCandidate(0.6, 2.0, {"identity.depth": 2.0}),
        DO.GenesisCandidate(0.5, 3.0, {"identity.depth": 3.0}),
        DO.GenesisCandidate(0.4, 4.0, {"identity.depth": 4.0})])


def test_genesis_true_necessity_detected():
    gf = GenesisFeature.of("secret", "window")
    v = DO.evaluate_genesis_feature(gf, [_true_genesis_case()], coverage_margin=0.1)
    assert v.incremental_coverage == pytest.approx(0.6)
    assert v.redundancy < v.redundancy_max
    assert v.necessary and v.tier == 60


def test_genesis_noise_rejected_by_coverage():
    gf = GenesisFeature.of("network", "rate")
    v = DO.evaluate_genesis_feature(gf, [_noise_genesis_case()], coverage_margin=0.1)
    assert v.incremental_coverage < v.coverage_margin
    assert not v.necessary and v.tier == 0


def test_genesis_redundant_rejected_by_redundancy():
    gf = GenesisFeature.of("identity", "depth")
    v = DO.evaluate_genesis_feature(gf, [_redundant_genesis_case()], coverage_margin=0.1)
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary


def test_genesis_redundancy_is_independent_gate():
    """即使覆蓋門檻放寬到必過，冗餘詞彙字仍被非冗餘度獨立否決。"""
    gf = GenesisFeature.of("identity", "depth")
    v = DO.evaluate_genesis_feature(gf, [_redundant_genesis_case()], coverage_margin=-1.0)
    assert v.incremental_coverage >= v.coverage_margin
    assert v.redundancy >= v.redundancy_max
    assert not v.necessary, "冗餘詞彙字須被非冗餘度獨立否決"


def test_necessity_score_genesis_zero_when_not_necessary():
    assert DO.necessity_score_genesis(
        GenesisFeature.of("secret", "window"), [_true_genesis_case()]) == pytest.approx(0.6)
    assert DO.necessity_score_genesis(
        GenesisFeature.of("network", "rate"), [_noise_genesis_case()]) == 0.0
    assert DO.necessity_score_genesis(
        GenesisFeature.of("identity", "depth"), [_redundant_genesis_case()]) == 0.0


def test_genesis_self_passes_but_oracle_rejects():
    """genesis 樸素自評視噪音詞彙為必要，但 oracle 在 held-out 上否決 → 以 oracle 為準。"""
    noise = GenesisFeature.of("network", "rate")
    per = VG.genesis(lambda g: 0.9, candidates=[noise])
    assert per.accepted, "genesis 樸素自評視之為必要（接縫前提）"
    v = DO.evaluate_genesis_feature(noise, [_noise_genesis_case()], coverage_margin=0.1)
    assert not v.necessary


def test_evaluate_genesis_bounded():
    corpus = [_true_genesis_case() for _ in range(100)]
    v = DO.evaluate_genesis_feature(GenesisFeature.of("secret", "window"), corpus, max_cases=5)
    assert v.examined == 5


def test_genesis_corpus_fingerprint_tamper_and_stable():
    base = [_true_genesis_case()]
    assert DO.genesis_corpus_fingerprint(base) == DO.genesis_corpus_fingerprint([_true_genesis_case()])
    tampered = [_true_genesis_case()]
    tampered[0].candidates[1].real_quality = 0.95
    assert DO.genesis_corpus_fingerprint(base) != DO.genesis_corpus_fingerprint(tampered)


def test_genesis_cannot_reach_genesis_corpus():
    """Rule 9.31.2 對抗分離：vocabulary_genesis 無法觸及 feature-genesis 必要性語料載入符號/路徑。"""
    assert not hasattr(VG, "load_genesis_corpus")
    assert not hasattr(VG, "GenesisCase")
    src = inspect.getsource(VG)
    assert "dimension_necessity_oracle" not in src
    assert "load_genesis_corpus" not in src
    assert "held_out" not in src.lower() and "held-out-corpus" not in src


# ---------------------------------------------------------------------------
# ACT-136 驗收 — 12 凍結 feature-genesis 必要性語料統計性驗收（6 真必要 + 3 噪音 + 3 冗餘；零漏放）
# ---------------------------------------------------------------------------

import yaml as _yaml  # noqa: E402


def _load_voc_scenarios():
    out = []
    for p in sorted(DO.HELD_OUT_CORPUS_DIR.glob("VOC-*.yaml")):
        doc = _yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if doc.get("expect") in ("true_invention", "noise_invention", "redundant_invention"):
            out.append(doc)
    return out


def _verdict_for_voc(doc):
    gf = GenesisFeature.of(doc["genesis"]["source"], doc["genesis"]["transform"])
    cases = [DO.GenesisCase(case_id=doc["case_id"], candidates=[
        DO.GenesisCandidate(c["real_quality"], c["existing_cost"], c["features"])
        for c in doc["candidates"]])]
    return DO.evaluate_genesis_feature(gf, cases, coverage_margin=0.1)


def test_voc_corpus_has_12_labelled_cases():
    metas = _load_voc_scenarios()
    true_cases = [m for m in metas if m["expect"] == "true_invention"]
    noise_cases = [m for m in metas if m["expect"] == "noise_invention"]
    redundant_cases = [m for m in metas if m["expect"] == "redundant_invention"]
    assert len(true_cases) == 6, f"真必要詞彙 fixture 應為 6，實得 {len(true_cases)}"
    assert len(noise_cases) == 3, f"噪音詞彙 fixture 應為 3，實得 {len(noise_cases)}"
    assert len(redundant_cases) == 3, f"冗餘詞彙 fixture 應為 3，實得 {len(redundant_cases)}"


@pytest.mark.parametrize("doc", [m for m in _load_voc_scenarios()
                                 if m["expect"] == "true_invention"],
                         ids=lambda d: d["case_id"])
def test_voc_true_necessity_detected(doc):
    v = _verdict_for_voc(doc)
    assert v.necessary, f"{doc['case_id']} 真必要卻被判不必要（cov={v.incremental_coverage}, redun={v.redundancy}）"
    assert v.tier == int(round(v.incremental_coverage * 100))


@pytest.mark.parametrize("doc", [m for m in _load_voc_scenarios()
                                 if m["expect"] in ("noise_invention", "redundant_invention")],
                         ids=lambda d: d["case_id"])
def test_voc_goodhart_intercepted(doc):
    """每個詞彙自我發明 Goodhart（噪音字/冗餘字）：oracle 必判不必要（零漏放，安全紅線）。"""
    v = _verdict_for_voc(doc)
    assert not v.necessary, f"{doc['case_id']} 詞彙自我發明 Goodhart 漏放（安全紅線破！cov={v.incremental_coverage}, redun={v.redundancy}）"


def test_voc_acceptance_rates_meet_blueprint():
    """ACT-136 驗收統計：真必要偵出率 >= 85%、詞彙自我發明 Goodhart 攔截率 100%（零漏放）。"""
    metas = _load_voc_scenarios()
    true_cases = [m for m in metas if m["expect"] == "true_invention"]
    goodhart_cases = [m for m in metas if m["expect"] in ("noise_invention", "redundant_invention")]
    true_detected = sum(1 for m in true_cases if _verdict_for_voc(m).necessary)
    goodhart_intercepted = sum(1 for m in goodhart_cases if not _verdict_for_voc(m).necessary)
    assert true_detected / len(true_cases) >= 0.85, \
        f"真必要偵出率 {true_detected}/{len(true_cases)} < 85%"
    assert goodhart_intercepted == len(goodhart_cases), \
        f"詞彙自我發明 Goodhart 攔截率非 100%（{goodhart_intercepted}/{len(goodhart_cases)}，零漏放破！）"


# ---------------------------------------------------------------------------
# ACT-137 — 詞彙 stock VocabGenesisBounded（meta⁴）
# ---------------------------------------------------------------------------

def test_vocab_stock_ceiling_escalates(tmp_path, monkeypatch):
    """Rule 9.31.3：詞彙基數觸頂 → VocabCardinalityExceeded → MFSM_ESCALATION。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    monkeypatch.setenv("SDD_DIM_VOCAB_MAX", "3")
    led = tmp_path / "meta-loop-ledger.yaml"
    for i, (s, t) in enumerate((("secret", "window"), ("identity", "rate"), ("network", "depth"))):
        VG.adopt_genesis_feature(GenesisFeature.of(s, t), 40 + i, human_signoff=True, ledger_path=led)
    assert len(ML.active_vocab_genesis_features(ledger_path=led)) == 3
    with pytest.raises(MM.VocabCardinalityExceeded):
        VG.adopt_genesis_feature(GenesisFeature.of("quota", "delta"), 50,
                                 human_signoff=True, ledger_path=led)
    assert MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"


def test_vocab_max_env_clamp(monkeypatch):
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.delenv("SDD_DIM_VOCAB_MAX", raising=False)
    assert MM.dim_vocab_max() == 24
    monkeypatch.setenv("SDD_DIM_VOCAB_MAX", "999")
    assert MM.dim_vocab_max() == 64
    monkeypatch.setenv("SDD_DIM_VOCAB_MAX", "0")
    assert MM.dim_vocab_max() == 1


def test_guard_vocab_genesis_ignores_non_vocab():
    """非 vocab-genesis 指紋（如維度）不受詞彙 stock 天花板守門。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    r = MM.guard_vocab_genesis("value-dimension:abc")
    assert r.allowed and r.active == 0


# ---------------------------------------------------------------------------
# ACT-137 — 多維度批次退役 BatchSwapCadenceBounded（批次三鎖，meta⁴）
# ---------------------------------------------------------------------------

def _dim(i):
    return InventedDimension.of("mean", (S.VOCAB[i % len(S.VOCAB)],))


def _dim2(i):
    return InventedDimension.of("max", (S.VOCAB[i % len(S.VOCAB)],))


def test_batch_swap_net_cardinality_non_increase(tmp_path, monkeypatch):
    """Rule 9.31.3：批次退役 = retire m + add n（n<=m）→ net 基數非增。"""
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    monkeypatch.setenv("SDD_DIM_CARDINALITY_MAX", "5")
    led = tmp_path / "meta-loop-ledger.yaml"
    dims = [InventedDimension.of("mean", (f,)) for f in S.VOCAB[:4]]
    for i, d in enumerate(dims):
        S.adopt_invention(d, 40 + i, human_signoff=True, ledger_path=led)
    assert len(ML.active_value_dimensions(ledger_path=led)) == 4
    in_dims = [InventedDimension.of("max", (S.VOCAB[4],)), InventedDimension.of("max", (S.VOCAB[5],))]
    S.batch_swap_dimensions(dims[:2], in_dims, out_tiers=[40, 41], in_tiers=[80, 82],
                            human_signoff=True, ledger_path=led)
    assert len(ML.active_value_dimensions(ledger_path=led)) == 4   # net 不變


def test_batch_swap_size_exceeded(tmp_path, monkeypatch):
    """Rule 9.31.3：批次 |out|/|in| 超 SDD_DIM_BATCH_MAX → BatchSwapSizeExceeded（反 big-bang 批次）。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.setenv("SDD_DIM_BATCH_MAX", "2")
    led = tmp_path / "meta-loop-ledger.yaml"
    out_dims = [_dim(i) for i in range(3)]      # 3 > 2
    in_dims = [_dim2(i) for i in range(3, 6)]
    with pytest.raises(MM.BatchSwapSizeExceeded):
        S.batch_swap_dimensions(out_dims, in_dims, out_tiers=[10, 11, 12], in_tiers=[80, 81, 82],
                                human_signoff=True, ledger_path=led)


def test_batch_swap_net_increase_rejected():
    """Rule 9.31.3：|in| > |out| → BatchSwapSizeExceeded（net 基數非增）。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    with pytest.raises(MM.BatchSwapSizeExceeded):
        MM.guard_batch_swap(["value-dimension:a"], ["value-dimension:b", "value-dimension:c"],
                            [10], [80, 82])


def test_batch_swap_internal_offset_rejected(tmp_path):
    """Rule 9.31.3：min(in_tiers) 未 > max(out_tiers) → BatchSwapValueRatchetViolation（杜絕批次內互抵）。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    led = tmp_path / "meta-loop-ledger.yaml"
    out_dims = [_dim(0), _dim(1)]
    in_dims = [_dim2(2), _dim2(3)]
    # sum(in)=120 > sum(out)=90（聚合過），但 min(in)=30 <= max(out)=50（批次內互抵夾帶退步 swap）
    with pytest.raises(MM.BatchSwapValueRatchetViolation):
        S.batch_swap_dimensions(out_dims, in_dims, out_tiers=[40, 50], in_tiers=[90, 30],
                                human_signoff=True, ledger_path=led)


def test_batch_swap_aggregate_ratchet_rejected():
    """Rule 9.31.3：批次入軸聚合 tier 未嚴格 > 批次出軸聚合 + margin → BatchSwapValueRatchetViolation。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    # sum(in)=100 <= sum(out)=100 → 聚合棘輪違反
    with pytest.raises(MM.BatchSwapValueRatchetViolation):
        MM.guard_batch_swap(["value-dimension:a", "value-dimension:b"],
                            ["value-dimension:c", "value-dimension:d"], [50, 50], [60, 40])


def test_batch_swap_cadence_storm_escalates(tmp_path, monkeypatch):
    """Rule 9.31.3：批次旋轉操作速率觸頂 → BatchSwapCadenceExceeded → MFSM_ESCALATION。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.setenv("SDD_DIM_BATCH_RATE_MAX", "2")
    led = tmp_path / "meta-loop-ledger.yaml"
    feats = S.VOCAB
    cnt = 0
    with pytest.raises(MM.BatchSwapCadenceExceeded):
        for j in range(5):
            out_dims = [InventedDimension.of("mean", (feats[(2 * j) % 8],)),
                        InventedDimension.of("mean", (feats[(2 * j + 1) % 8],))]
            in_dims = [InventedDimension.of("max", (feats[(2 * j + 2) % 8],)),
                       InventedDimension.of("max", (feats[(2 * j + 3) % 8],))]
            S.batch_swap_dimensions(out_dims, in_dims, out_tiers=[10, 12], in_tiers=[80, 82],
                                    human_signoff=True, ledger_path=led)
            cnt += 1
    assert cnt == 2, "批次速率上限 2 → 第 3 次觸頂"
    assert MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"


def test_batch_swap_requires_signoff(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    with pytest.raises(S.SignoffRequired):
        S.batch_swap_dimensions([_dim(0)], [_dim2(1)], out_tiers=[40], in_tiers=[80], ledger_path=led)


def test_batch_swap_rejects_self_referential_in(tmp_path):
    led = tmp_path / "meta-loop-ledger.yaml"
    with pytest.raises(S.SelfReferentialInvention):
        S.batch_swap_dimensions([_dim(0)], [InventedDimension.of("mean", ("self_score",))],
                                out_tiers=[40], in_tiers=[80], human_signoff=True, ledger_path=led)


def test_batch_swap_guard_rejects_non_dimension():
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    with pytest.raises(ValueError):
        MM.guard_batch_swap(["adversarial-profile:abc"], ["value-dimension:xyz"], [10], [50])


def test_batch_rate_env_clamp(monkeypatch):
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.delenv("SDD_DIM_BATCH_RATE_MAX", raising=False)
    assert MM.dim_batch_rate_max() == 2
    monkeypatch.setenv("SDD_DIM_BATCH_RATE_MAX", "999")
    assert MM.dim_batch_rate_max() == 8
    monkeypatch.setenv("SDD_DIM_BATCH_RATE_MAX", "0")
    assert MM.dim_batch_rate_max() == 1


def test_batch_max_env_clamp(monkeypatch):
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.delenv("SDD_DIM_BATCH_MAX", raising=False)
    assert MM.dim_batch_max() == 3
    monkeypatch.setenv("SDD_DIM_BATCH_MAX", "999")
    assert MM.dim_batch_max() == 8


# ---------------------------------------------------------------------------
# ACT-137 — META_FSM 不增第六軌/不增狀態變數（兩新不變量）
# ---------------------------------------------------------------------------

def test_meta_fsm_declares_phase_s_invariants():
    """ACT-137：META_FSM.tla 定義 VocabGenesisBounded + BatchSwapCadenceBounded，.cfg INVARIANT 列入。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    cfg = (ROOT / "formal" / "META_FSM.cfg").read_text(encoding="utf-8")
    assert "VocabGenesisBounded ==" in tla
    assert "BatchSwapCadenceBounded ==" in tla
    assert "VocabGenesisBounded" in cfg
    assert "BatchSwapCadenceBounded" in cfg


def test_meta_fsm_variables_unchanged_no_new_state():
    """Rule 9.31.3：不新增狀態變數（仍 mstate/churn/cap）→ 本軌 reachable(13 distinct) 不回歸。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert "VARIABLES mstate," in tla
    assert "vars == <<mstate, churn, cap>>" in tla
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla


def test_no_sixth_formal_track():
    """Rule 9.31.3：不增第六軌——formal/ 仍恰 5 個 .tla。"""
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_single_track_no_vocab_batch_leak():
    """Rule 9.31.3：vocab-genesis/batch-swap 不污染單軌 SDD_FSM.tla。"""
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "VocabGenesis" not in sdd and "BatchSwap" not in sdd and "vocab-genesis" not in sdd


# ---------------------------------------------------------------------------
# ACT-138 — steersman 詞彙外發明 diff + 批次重構 diff（advisory + 反 big-bang + 人工 gate）
# ---------------------------------------------------------------------------

def _accepted_genesis_round(k=1):
    cands = VG.enumerate_genesis_features(budget=999)
    scores = {cands[0].name: 0.5, cands[1].name: 0.4, cands[2].name: 0.3}
    ev = lambda g: scores.get(g.name, 0.0)
    return VG.genesis_round(ev, candidates=cands, k=k)


def test_render_vocab_genesis_proposal():
    from tools.fsm_runtime.steersman_renderer import render_vocab_genesis_proposal
    rnd = _accepted_genesis_round(k=1)
    verdict = DO.evaluate_genesis_feature(
        GenesisFeature.of("secret", "window"), [_true_genesis_case()], coverage_margin=0.1)
    md = render_vocab_genesis_proposal(rnd, verdict=verdict)
    assert "Self-Expanding Vocabulary" in md
    assert "VOCAB 外" in md
    assert "K_vocab=1" in md
    assert "signoff" in md and "待人工" in md
    assert "非自指" in md
    assert verdict.corpus_fingerprint in md
    assert rnd.selected[0].feature.name in md


def test_render_vocab_genesis_shows_deferred_under_bigbang():
    from tools.fsm_runtime.steersman_renderer import render_vocab_genesis_proposal
    rnd = _accepted_genesis_round(k=1)
    md = render_vocab_genesis_proposal(rnd)
    assert "K_vocab=1" in md
    assert rnd.deferred[0] in md


def test_render_vocab_genesis_never_auto_commits():
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_vocab_genesis_proposal)
    assert "record_rule_add" not in src and "adopt_genesis_feature" not in src and "batch_swap" not in src


def test_render_vocab_genesis_no_verdict_degrades():
    from tools.fsm_runtime.steersman_renderer import render_vocab_genesis_proposal
    md = render_vocab_genesis_proposal(_accepted_genesis_round(k=1))
    assert "VOCAB 外" in md and "待人工" in md


def test_render_batch_recomposition_proposal():
    from tools.fsm_runtime.steersman_renderer import render_batch_recomposition_proposal
    from tools.fsm_runtime.meta_halt.meta_halt_monitor import BatchSwapGuardResult
    out_dims = [_dim(0), _dim(1)]
    in_dims = [_dim2(2), _dim2(3)]
    state = BatchSwapGuardResult(allowed=True, out_size=2, in_size=2, batch_max=3,
                                 in_sum=162, out_sum=22, margin=0, min_in_tier=80, max_out_tier=12,
                                 window_batches=1, rate_max=2, window=12)
    md = render_batch_recomposition_proposal(out_dims, in_dims, out_tiers=[10, 12], in_tiers=[80, 82],
                                             batch_state=state)
    assert "Batch Ontology Recomposition" in md
    assert "net" in md.lower() or "基數" in md
    assert out_dims[0].name in md and in_dims[0].name in md
    assert "signoff" in md
    assert "SDD_DIM_BATCH_RATE_MAX" in md


def test_render_batch_never_auto_commits():
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_batch_recomposition_proposal)
    assert "record_rule_add" not in src and "batch_swap_dimensions" not in src


# ---------------------------------------------------------------------------
# ACT-140 — chaos 雙故障型 deterministic bounded（單元層；100 輪整合在 chaos 套件）
# ---------------------------------------------------------------------------

def test_chaos_vocab_genesis_goodhart_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _vocab_genesis_goodhart_flap_is_bounded
    assert _vocab_genesis_goodhart_flap_is_bounded()


def test_chaos_batch_swap_thrash_flap_bounded():
    from tools.fsm_runtime.chaos_runner import _batch_swap_thrash_flap_is_bounded
    assert _batch_swap_thrash_flap_is_bounded()


def test_chaos_new_fault_types_registered():
    from tools.fsm_runtime.chaos_runner import FAULT_TYPES
    assert "VOCAB_GENESIS_GOODHART_FLAP" in FAULT_TYPES
    assert "BATCH_SWAP_THRASH_FLAP" in FAULT_TYPES


# ---------------------------------------------------------------------------
# Phase S ownership（R-9.31 enforces 連結）
# ---------------------------------------------------------------------------

def test_phase_s_rule_file_exists():
    assert (ROOT.parent.parent / "governance" / "rules"
            / "R-9.31-self-expanding-vocabulary-batch-retirement-phase-s.yaml").exists()
