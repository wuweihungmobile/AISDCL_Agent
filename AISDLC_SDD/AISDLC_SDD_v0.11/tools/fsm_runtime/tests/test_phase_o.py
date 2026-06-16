# enforces (governance rules): R-9.27
"""Phase O / ACT-111~116 — 自我調參的對抗式有界元最佳化 回歸守門.

涵蓋：
  - ACT-111 Objective Tuner：bounded 格點生成、SearchBounded、deterministic、只透過注入
    evaluate 評分（結構性無自評）、advisory（不自動 commit）、incumbent 唯讀
  - ACT-112 Objective Replay Oracle：held-out 真實品質評估、反 Goodhart（cram 陷阱零漏放）、
    capability tier = held-out 唯一來源、有界、content-hash、tuner↔oracle 結構隔離
  - ACT-113 obj-profile 納入既有 META_FSM（共用 churn 預算）：ChurnBounded / GraduationRatchet
    涵蓋 obj-profile 指紋、不增第六軌、不污染單軌
  - ACT-114 steersman 價值觀 diff 渲染（advisory + 人工 gate）
  - ACT-116 chaos OBJECTIVE_TUNE_FLAP 有界
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from tools.fsm_runtime import objective_tuner as TU
from tools.fsm_runtime import objective_replay_oracle as OR
from tools.fsm_runtime.objective_tuner import WeightProfile

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 共用 fixtures（held-out 現實代理語料）
# ---------------------------------------------------------------------------

def _tradeoff_corpus():
    """批次數↔延遲真實權衡：incumbent(1.0,0.1) 次優、調高 latency 才挑到真實最優（HELDOUT-001）。"""
    return [OR.HeldOutCase(
        case_id="TRADEOFF-1",
        values={"A": 10.0, "B": 1.0, "C": 1.0, "D": 1.0},
        candidates=(
            ([["B", "C"], ["A", "D"]], 0.3),    # A 晚 → latency 11 → 真實差
            ([["A", "B"], ["C"], ["D"]], 0.9),  # A 早 → latency 3 → 真實好
        ),
    )]


def _cram_trap_corpus():
    """缺維度陷阱：cram（1 批）真實差但成本恆最低 → 任何權重都挑 cram → 無法靠調參脫困。"""
    return [OR.HeldOutCase(
        case_id="CRAM-TRAP-1",
        values={"A": 1.0, "B": 1.0, "C": 1.0},
        candidates=(
            ([["A", "B", "C"]], 0.2),           # cram：1 批、latency 0 → 成本恆最低、真實差
            ([["A"], ["B"], ["C"]], 0.9),       # split：3 批 → 真實好但成本恆較高
        ),
    )]


def _incumbent_optimal_corpus():
    """incumbent 已最優：唯一好排程的成本在 incumbent 權重下即最低。"""
    return [OR.HeldOutCase(
        case_id="INC-OPT-1",
        values={"A": 10.0, "B": 1.0},
        candidates=(
            ([["A"], ["B"]], 0.9),              # A 早、latency 1 → 任何 lw>0 皆挑此 → 真實好
            ([["B"], ["A"]], 0.2),              # A 晚、latency 10 → 真實差
        ),
    )]


# ---------------------------------------------------------------------------
# ACT-111 — Objective Tuner
# ---------------------------------------------------------------------------

def test_tune_budget_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_OBJ_TUNE_BUDGET", raising=False)
    assert TU.obj_tune_budget() == 64
    monkeypatch.setenv("SDD_OBJ_TUNE_BUDGET", "9999")
    assert TU.obj_tune_budget() == 256
    monkeypatch.setenv("SDD_OBJ_TUNE_BUDGET", "1")
    assert TU.obj_tune_budget() == 8
    monkeypatch.setenv("SDD_OBJ_TUNE_BUDGET", "garbage")
    assert TU.obj_tune_budget() == 64


def test_win_margin_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_OBJ_WIN_MARGIN", raising=False)
    assert TU.obj_win_margin() == 0.10
    monkeypatch.setenv("SDD_OBJ_WIN_MARGIN", "5")
    assert TU.obj_win_margin() == 1.0
    monkeypatch.setenv("SDD_OBJ_WIN_MARGIN", "-1")
    assert TU.obj_win_margin() == 0.0
    monkeypatch.setenv("SDD_OBJ_WIN_MARGIN", "garbage")
    assert TU.obj_win_margin() == 0.10


def test_incumbent_profile_reads_frozen_constants():
    from tools.fsm_runtime import composition_objective_scorer as OS
    inc = TU.incumbent_profile()
    assert inc.batch_w == OS.BATCH_W and inc.latency_w == OS.LATENCY_W


def test_weight_profile_score_mirrors_objective_scorer():
    """incumbent profile 的 score 與 composition_objective_scorer.score_schedule 一致。"""
    from tools.fsm_runtime import composition_objective_scorer as OS
    inc = TU.incumbent_profile()
    sched = [["A", "C"], ["B"]]
    vals = {"A": 3.0, "B": 1.0, "C": 1.0}
    assert inc.score_schedule(sched, vals) == OS.score_schedule(sched, vals)


def test_profile_fingerprint_namespaced_and_stable():
    p = WeightProfile(1.0, 0.2)
    assert p.fingerprint().startswith(TU.OBJ_PROFILE_NS)
    assert p.fingerprint() == WeightProfile(1.0, 0.2).fingerprint()      # deterministic
    assert p.fingerprint() != WeightProfile(1.0, 0.35).fingerprint()     # 不同權重不同指紋


def test_candidate_grid_search_bounded():
    grid = TU.candidate_grid(budget=8)
    assert len(grid) <= 8                                                 # SearchBounded（Rule 9.27.1）
    assert TU.incumbent_profile() not in grid                            # 排除 incumbent 自身


def test_candidate_grid_deterministic():
    assert TU.candidate_grid(budget=20) == TU.candidate_grid(budget=20)


def test_propose_finds_improvement_on_tradeoff():
    """tuner 在 incumbent 次優的語料上找到真實改進（達 margin、送 signoff）。"""
    corpus = _tradeoff_corpus()
    ev = OR.make_evaluator(corpus)
    prop = TU.propose(ev)
    assert prop.accepted
    assert prop.candidate_quality == 0.9 and prop.incumbent_quality == 0.3
    assert prop.win_delta >= prop.win_margin
    assert prop.tier == 90


def test_propose_search_bounded():
    """nodes_searched ≤ budget（Rule 9.27.1，永不指數爆炸）。"""
    corpus = _tradeoff_corpus()
    ev = OR.make_evaluator(corpus)
    prop = TU.propose(ev, budget=8)
    assert prop.nodes_searched <= 8


def test_propose_deterministic():
    corpus = _tradeoff_corpus()
    ev = OR.make_evaluator(corpus)
    p1 = TU.propose(ev)
    p2 = TU.propose(ev)
    assert p1.candidate == p2.candidate and p1.win_delta == p2.win_delta


def test_propose_no_improvement_when_incumbent_optimal():
    """incumbent 已最優 → 無候選嚴格優於它達 margin → 不送 signoff。"""
    corpus = _incumbent_optimal_corpus()
    ev = OR.make_evaluator(corpus)
    prop = TU.propose(ev)
    assert not prop.accepted


def test_propose_cannot_escape_missing_dimension():
    """缺維度（cram 陷阱）→ 任何權重都挑 cram → tuner 誠實提不出改進（導人工換維度）。"""
    corpus = _cram_trap_corpus()
    ev = OR.make_evaluator(corpus)
    prop = TU.propose(ev)
    assert not prop.accepted                          # 不可能靠調參把 cram 說成好
    assert prop.incumbent_quality == 0.2              # incumbent 也只能挑到 cram


def test_propose_only_uses_injected_evaluate():
    """結構保證：tuner.propose 只透過注入 evaluate 取得品質（反 Goodhart 對抗分離）。"""
    seen = []

    def spy(profile):
        seen.append(profile)
        return 0.0
    TU.propose(spy, budget=8)
    assert len(seen) >= 1                              # 確實呼叫了注入評估器


def test_tuner_is_structurally_blind_to_oracle_corpus():
    """Rule 9.27.2：objective_tuner **不得 import** oracle、不得觸及 held-out 語料路徑（對抗分離）。

    用 AST 檢查真實 import 依賴（非 docstring prose）：tuner 只能收到注入的 evaluate 回呼，
    結構性無法自己取得現實代理語料——這是反 Goodhart 的編譯期保證。
    """
    import ast
    tree = ast.parse(inspect.getsource(TU))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported |= {a.name for a in node.names}
    assert not any("objective_replay_oracle" in m for m in imported), \
        "tuner 不得 import oracle（破對抗分離）"
    assert not any("held_out" in m.lower() or "held-out" in m.lower() for m in imported)
    # 模組命名空間實際不存在 oracle / 語料載入符號
    assert not hasattr(TU, "load_corpus") and not hasattr(TU, "HeldOutCase")


def test_record_proposal_writes_pending_signoff(tmp_path):
    corpus = _tradeoff_corpus()
    prop = TU.propose(OR.make_evaluator(corpus))
    led = tmp_path / "objective-tuning-ledger.yaml"
    entry = TU.record_proposal(prop, ledger_path=led, ts="2026-06-03T00:00:00+00:00")
    assert led.exists()
    assert entry["signoff"] == "pending" and entry["maturity"] == "proposed"


def test_proposal_to_dict_forces_proposed():
    prop = TU.propose(OR.make_evaluator(_tradeoff_corpus()))
    assert prop.to_dict()["maturity"] == "proposed"


# ---------------------------------------------------------------------------
# ACT-112 — Objective Replay Oracle（反 Goodhart）
# ---------------------------------------------------------------------------

def test_evaluate_profile_picks_argmin_real_quality():
    corpus = _tradeoff_corpus()
    inc = TU.incumbent_profile()                      # (1.0, 0.1) → 挑 S_a（真實 0.3）
    good = WeightProfile(1.0, 0.2)                     # → 挑 S_b（真實 0.9）
    assert OR.evaluate_profile(inc, corpus) == 0.3
    assert OR.evaluate_profile(good, corpus) == 0.9


def test_evaluate_profile_empty_corpus():
    assert OR.evaluate_profile(WeightProfile(1.0, 0.1), []) == 0.0


def test_evaluate_profile_bounded(monkeypatch):
    """重放筆數 clamp SDD_REPLAY_MAX_CASES（Rule 9.27.2/9.24.4）。"""
    corpus = _tradeoff_corpus() * 100                 # 100 筆
    val = OR.evaluate_profile(WeightProfile(1.0, 0.2), corpus, max_cases=5)
    assert val == 0.9                                  # 同質語料，前 5 筆即代表
    # examined 受 cap 限制
    v = OR.evaluate_candidate(WeightProfile(1.0, 0.2), TU.incumbent_profile(),
                              corpus, win_margin=0.1, max_cases=5)
    assert v.examined == 5


def test_evaluate_candidate_tier_from_held_out_only():
    """Rule 9.27.5：tier 唯一來源 = held-out 真實品質（= round(quality*100)）。"""
    corpus = _tradeoff_corpus()
    v = OR.evaluate_candidate(WeightProfile(1.0, 0.2), TU.incumbent_profile(),
                              corpus, win_margin=0.1)
    assert v.tier == 90 and v.candidate_quality == 0.9
    assert v.passes_margin and v.win_delta == pytest.approx(0.6)


def test_corpus_fingerprint_changes_on_tamper():
    base = _tradeoff_corpus()
    tampered = [OR.HeldOutCase(
        case_id="TRADEOFF-1", values={"A": 10.0, "B": 1.0, "C": 1.0, "D": 1.0},
        candidates=(([["B", "C"], ["A", "D"]], 0.9),   # 竄改真實品質 0.3→0.9
                    ([["A", "B"], ["C"], ["D"]], 0.9)),
    )]
    assert OR.corpus_fingerprint(base) != OR.corpus_fingerprint(tampered)


def test_corpus_fingerprint_stable():
    assert OR.corpus_fingerprint(_tradeoff_corpus()) == OR.corpus_fingerprint(_tradeoff_corpus())


def test_goodhart_zero_miss_on_cram_trap():
    """安全紅線：cram 陷阱語料上，任何權重（含自評看似超優者）都拿不到正 win → 零漏放。

    cram 真實差但成本恆最低，任何 profile 都被迫挑 cram → 真實品質鎖死 0.2 →
    不可能靠調權重把它說成好（Rule 9.27.2/9.27.5）。8 個刻意挑的「假最優」profile 全數被攔。
    """
    corpus = _cram_trap_corpus()
    inc = TU.incumbent_profile()
    fake_optimal = [
        WeightProfile(0.0, 0.0),    # 全零（一切成本 0，自評看似完美）
        WeightProfile(2.0, 0.0),    # 高 batch_w（cram 看似最划算）
        WeightProfile(0.0, 0.5),    # 純延遲
        WeightProfile(2.0, 0.5),
        WeightProfile(0.5, 0.0),
        WeightProfile(1.5, 0.05),
        WeightProfile(0.0, 0.35),
        WeightProfile(2.0, 0.2),
    ]
    for p in fake_optimal:
        v = OR.evaluate_candidate(p, inc, corpus, win_margin=0.1)
        assert not v.passes_margin, f"Goodhart 漏放：{p} 假最優卻通過 margin"
        assert v.candidate_quality <= 0.2              # 真實品質鎖死在 cram


def test_make_evaluator_hides_corpus():
    """注入 closure 對 tuner 不透明（拿不到 corpus 本體）。"""
    ev = OR.make_evaluator(_tradeoff_corpus())
    # closure 只暴露一個可呼叫介面，回傳數字；不暴露語料結構
    assert callable(ev)
    assert isinstance(ev(WeightProfile(1.0, 0.2)), float)


def test_load_frozen_corpus_from_disk():
    """ACT-112 凍結語料：knowledge/held-out-corpus/HELDOUT-001.yaml 可載入且品質正確。"""
    corpus = OR.load_corpus()
    assert any(c.case_id == "HELDOUT-001" for c in corpus)
    h1 = next(c for c in corpus if c.case_id == "HELDOUT-001")
    # incumbent 在此凍結語料上次優（0.3）、調高 latency 可達 0.9（與 in-memory 版一致）
    assert OR.evaluate_profile(TU.incumbent_profile(), [h1]) == 0.3
    assert OR.evaluate_profile(WeightProfile(1.0, 0.2), [h1]) == 0.9


# ---------------------------------------------------------------------------
# ACT-113 — obj-profile 納入既有 META_FSM（共用 churn 預算，不增第六軌）
# ---------------------------------------------------------------------------

def test_adopt_profile_requires_human_signoff(tmp_path):
    """Rule 9.27.3：tuner 不得自動 commit——human_signoff=False 直接 raise。"""
    led = tmp_path / "meta-loop-ledger.yaml"
    with pytest.raises(TU.SignoffRequired):
        TU.adopt_profile(WeightProfile(1.0, 0.2), 90, ledger_path=led)
    assert not led.exists()                            # 未落帳


def test_adopt_profile_goes_through_meta_guard(tmp_path):
    """obj-profile 採納走既有 meta_halt_monitor、落共用 meta-loop-ledger（Rule 9.27.4）。"""
    from tools.fsm_runtime.meta_halt import meta_ledger as ML
    led = tmp_path / "meta-loop-ledger.yaml"
    ev = TU.adopt_profile(WeightProfile(1.0, 0.2), 90, human_signoff=True, ledger_path=led)
    assert ev.fingerprint.startswith(TU.OBJ_PROFILE_NS)
    assert ML.compute_churn(ev.fingerprint, ledger_path=led) == 0   # 首採納非 churn


def test_obj_profile_churn_storm_hits_churnbounded(tmp_path, monkeypatch):
    """obj-profile add↔retire 抖動觸 ChurnBounded → 拒絕（→ MFSM_ESCALATION），與 SLV 規則同預算。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.delenv("SDD_META_CHURN_MAX", raising=False)
    cmax = MM.churn_max()
    led = tmp_path / "meta-loop-ledger.yaml"
    prof = WeightProfile(1.0, 0.2)
    TU.adopt_profile(prof, 0, human_signoff=True, ledger_path=led)
    for i in range(cmax):                              # 累積 churn 至上限（每次 readopt 帶 cap-delta）
        TU.retire_profile(prof, i, ledger_path=led)
        TU.adopt_profile(prof, i + 1, human_signoff=True, ledger_path=led)
    TU.retire_profile(prof, cmax, ledger_path=led)
    with pytest.raises(MM.ChurnBoundExceeded):         # 第 cmax+1 次再採納 → 觸頂
        TU.adopt_profile(prof, cmax + 1, human_signoff=True, ledger_path=led)


def test_obj_profile_readopt_without_capability_delta_rejected(tmp_path):
    """Goodhart 防線：再採納退役過的 obj-profile 但無 held-out tier 提升 → GraduationRatchetViolation。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    led = tmp_path / "meta-loop-ledger.yaml"
    prof = WeightProfile(1.0, 0.2)
    TU.adopt_profile(prof, 50, human_signoff=True, ledger_path=led)
    TU.retire_profile(prof, 50, ledger_path=led)
    with pytest.raises(MM.GraduationRatchetViolation):  # tier 未嚴格高於退役當下 → 拒絕
        TU.adopt_profile(prof, 50, human_signoff=True, ledger_path=led)


def test_obj_profile_shares_meta_state_escalation(tmp_path, monkeypatch):
    """共用 churn 預算：obj-profile churn 觸頂使整個 META_FSM meta_state → MFSM_ESCALATION。"""
    from tools.fsm_runtime.meta_halt import meta_halt_monitor as MM
    monkeypatch.delenv("SDD_META_CHURN_MAX", raising=False)
    cmax = MM.churn_max()
    led = tmp_path / "meta-loop-ledger.yaml"
    prof = WeightProfile(1.0, 0.2)
    # 直接用 ledger 記到 churn==cmax（meta_state 掃所有指紋，obj-profile 與 SLV 同集合）
    fp = prof.fingerprint()
    MM.record_rule_add("OBJ-x", fp, 0, ledger_path=led)
    for i in range(cmax):
        MM.record_rule_retire("OBJ-x", fp, i, ledger_path=led)
        MM.record_rule_add("OBJ-x", fp, i + 1, ledger_path=led)
    assert MM.meta_state(ledger_path=led) == "MFSM_ESCALATION"


def test_no_sixth_formal_track():
    """Rule 9.27.4：不增第六軌——formal/ 仍恰 5 個 .tla（SDD/META/FLEET/COMPOSITION/OPTIMIZATION）。"""
    tlas = {p.stem for p in (ROOT / "formal").glob("*.tla")}
    assert tlas == {"SDD_FSM", "META_FSM", "FLEET_FSM", "COMPOSITION_FSM", "OPTIMIZATION_FSM"}


def test_meta_fsm_tla_states_unchanged():
    """META_FSM.tla 狀態宇宙不因 obj-profile 改動（仍 5 態，obj-profile 共用不新增狀態）。"""
    tla = (ROOT / "formal" / "META_FSM.tla").read_text(encoding="utf-8")
    assert 'MetaStates == {"MFSM_OBSERVE", "MFSM_GROW", "MFSM_SHRINK", "MFSM_STABLE", "MFSM_ESCALATION"}' in tla
    assert "obj" not in tla.lower().replace("object", "")   # 無 obj-profile 專屬狀態洩漏


def test_single_track_no_obj_profile_leak():
    """Rule 9.27.4：obj-profile 不污染單軌 SDD_FSM.tla。"""
    sdd = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "OBJ_" not in sdd and "obj-profile" not in sdd


# ---------------------------------------------------------------------------
# ACT-114 — steersman 價值觀 diff 渲染（advisory + 人工 gate）
# ---------------------------------------------------------------------------

def test_steersman_render_tuning_proposal():
    from tools.fsm_runtime.steersman_renderer import render_objective_tuning_proposal
    corpus = _tradeoff_corpus()
    prop = TU.propose(OR.make_evaluator(corpus))
    verdict = OR.evaluate_candidate(prop.candidate, prop.incumbent, corpus, win_margin=prop.win_margin)
    md = render_objective_tuning_proposal(prop, verdict=verdict)
    assert "Meta-Optimization" in md
    assert "OBJECTIVE_PROFILE_VERSION" in md           # 明示人工 bump gate
    assert "待人工 signoff" in md or "未達 margin" in md
    assert "batch_w" in md and "latency_w" in md       # 價值觀 diff
    assert verdict.corpus_fingerprint in md            # 凍結語料證據


def test_steersman_render_tuning_proposal_no_verdict():
    """無 verdict 時亦可渲染（degrade gracefully）。"""
    from tools.fsm_runtime.steersman_renderer import render_objective_tuning_proposal
    prop = TU.propose(OR.make_evaluator(_incumbent_optimal_corpus()))
    md = render_objective_tuning_proposal(prop)
    assert "未達 margin" in md                          # incumbent 已最優 → 不送 signoff


def test_steersman_render_never_auto_commits():
    """渲染器純文字產出，不觸發任何採納（無 record_rule_add / bump 副作用）。"""
    from tools.fsm_runtime import steersman_renderer as SR
    src = inspect.getsource(SR.render_objective_tuning_proposal)
    assert "record_rule_add" not in src and "adopt_profile" not in src
