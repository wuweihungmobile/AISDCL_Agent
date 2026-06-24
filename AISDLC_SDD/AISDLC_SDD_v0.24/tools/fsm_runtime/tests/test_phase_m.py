# enforces (governance rules): R-9.25
"""Phase M M-M1~M3 / ACT-097~102 — 組合級意圖自治 + 進步性監測 + 組合脆弱性 回歸守門.

涵蓋：
  - ACT-097 Intent Composer：共享節點、語義方向相反偵測（22 fixture）、組合帳本 reneg
  - ACT-098 Composition-Halt Monitor：RenegotiationBounded 守門、compose_state 分類；
    COMPOSITION_FSM.tla 離線可達性 BFS（reachable=N/N + 每態可達 terminal）、雙源狀態
    一致（.tla ↔ composition_halt_monitor.COMPOSITION_STATES）、cfg invariant/property 宣告
  - ACT-099 Capability Trajectory Monitor：RISING/PLATEAU/REGRESSION/CONVERGED 判定
  - ACT-100 Scaffold Ceiling Detector：A/B 淨負偵測 + 永不自動退役
  - ACT-101 Composition Blast Analyzer：組合爆炸半徑 + 排程序列化建議
  - ACT-102 steersman 整合（組合脆弱熱圖 + 軌跡警示）
  - opt-in 完整 TLC 窮舉（SDD_RUN_TLC=1）
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from tools.fsm_runtime import intent_composer as IC
from tools.fsm_runtime import composition_halt_monitor as CM
from tools.fsm_runtime import capability_trajectory_monitor as TM
from tools.fsm_runtime import scaffold_ceiling_detector as CD
from tools.fsm_runtime import composition_blast_analyzer as BA
from tools.fsm_runtime.output_quality_scorer import ExecutionObservation

ROOT = Path(__file__).resolve().parent.parent
COMP_TLA = ROOT / "formal" / "COMPOSITION_FSM.tla"
COMP_CFG = ROOT / "formal" / "COMPOSITION_FSM.cfg"


# ---------------------------------------------------------------------------
# ACT-097 — Intent Composer（22 fixture：6 衝突 + 16 無衝突）
# ---------------------------------------------------------------------------

_CONFLICT_PAIRS = [
    ("discount stackable", "discount exclusive"),       # antonym
    ("折扣可疊加", "折扣禁止疊加"),                        # 否定 parity + 共享
    ("feature enable", "feature disable"),              # antonym
    ("payment synchronous", "payment asynchronous"),    # antonym
    ("coupon allowed", "coupon forbidden"),             # antonym
    ("登入必須驗證碼", "登入不需驗證碼"),                  # 否定 parity + 共享
]

_NO_CONFLICT_PAIRS = [
    ("discount up to 50 percent", "discount applies to electronics"),
    ("折扣上限百分之五十", "折扣適用電子產品"),
    ("password length minimum eight", "password length minimum eight"),  # identical
    ("cache ttl sixty seconds", "cache eviction policy lru"),
    ("api returns json", "api rate limit hundred"),
    ("user can login", "user can logout"),
    ("order total includes tax", "order ships in two days"),
    ("report exported weekly", "report stored encrypted"),
    ("折扣適用會員", "折扣適用新客"),
    ("session timeout thirty", "session cookie httponly"),
    ("email template welcome", "email template receipt"),
    ("search supports filter", "search supports sort"),
    ("backup runs nightly", "backup retained ninety days"),
    ("avatar size square", "avatar format png"),
    ("invoice numbered sequential", "invoice currency usd"),
    ("notification via push", "notification via inbox"),
]


def test_conflict_detection_100_percent():
    """6 條衝突 fixture 全部偵出（衝突偵出率 100%）。"""
    for a, b in _CONFLICT_PAIRS:
        assert IC.is_conflict(a, b), f"未偵出衝突：{a!r} ⟂ {b!r}"


def test_no_conflict_zero_false_positive():
    """16 條無衝突 fixture 零誤判（無衝突誤判 0）。"""
    for a, b in _NO_CONFLICT_PAIRS:
        assert not IC.is_conflict(a, b), f"誤判為衝突：{a!r} vs {b!r}"


def test_compute_shared_nodes():
    intents = [
        IC.IntentSpec("INT-A", "折扣重構", {"AC-014": "折扣可疊加", "AC-020": "x"}),
        IC.IntentSpec("INT-B", "結帳優化", {"AC-014": "折扣禁止疊加", "AC-030": "y"}),
        IC.IntentSpec("INT-C", "報表", {"AC-040": "z"}),
    ]
    assert IC.compute_shared_nodes(intents) == ["AC-014"]


def test_compute_conflicts_detects_shared_contradiction():
    intents = [
        IC.IntentSpec("INT-A", "折扣重構", {"AC-014": "折扣可疊加"}),
        IC.IntentSpec("INT-B", "結帳優化", {"AC-014": "折扣禁止疊加"}),
    ]
    conflicts = IC.compute_conflicts(intents)
    assert len(conflicts) == 1
    assert conflicts[0].node_id == "AC-014"
    assert {conflicts[0].intent_a, conflicts[0].intent_b} == {"INT-A", "INT-B"}


def test_compute_conflicts_none_when_compatible():
    intents = [
        IC.IntentSpec("INT-A", "a", {"AC-014": "折扣適用會員"}),
        IC.IntentSpec("INT-B", "b", {"AC-014": "折扣適用新客"}),
    ]
    assert IC.compute_conflicts(intents) == []


def test_compose_result():
    intents = [
        IC.IntentSpec("INT-A", "a", {"AC-1": "enable feature"}),
        IC.IntentSpec("INT-B", "b", {"AC-1": "disable feature"}),
    ]
    r = IC.compose(intents)
    assert r.has_conflicts() and r.conflicting_nodes() == ["AC-1"]


def test_ledger_reneg_counting(tmp_path):
    p = tmp_path / "composition-ledger.yaml"
    assert IC.compute_reneg("AC-014", ledger_path=p) == 0
    IC.record_negotiate("AC-014", intent_a="A", intent_b="B", ledger_path=p)
    IC.record_negotiate("AC-014", intent_a="A", intent_b="B", ledger_path=p)
    assert IC.compute_reneg("AC-014", ledger_path=p) == 2
    # 不同節點互不干擾
    assert IC.compute_reneg("AC-099", ledger_path=p) == 0


# ---------------------------------------------------------------------------
# ACT-098 — Composition-Halt Monitor（RenegotiationBounded 守門）
# ---------------------------------------------------------------------------


def test_reneg_max_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_COMPOSITION_RENEG_MAX", raising=False)
    assert CM.reneg_max() == 2
    monkeypatch.setenv("SDD_COMPOSITION_RENEG_MAX", "4")
    assert CM.reneg_max() == 4
    monkeypatch.setenv("SDD_COMPOSITION_RENEG_MAX", "99")
    assert CM.reneg_max() == 5
    monkeypatch.setenv("SDD_COMPOSITION_RENEG_MAX", "0")
    assert CM.reneg_max() == 1
    monkeypatch.setenv("SDD_COMPOSITION_RENEG_MAX", "garbage")
    assert CM.reneg_max() == 2


def test_guard_negotiate_allows_within_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("SDD_COMPOSITION_RENEG_MAX", "2")
    p = tmp_path / "composition-ledger.yaml"
    r = CM.guard_negotiate("AC-014", ledger_path=p)
    assert r.allowed and r.reneg == 0


def test_guard_negotiate_blocks_when_topped(tmp_path, monkeypatch):
    """RenegotiationBounded（Rule 9.25.1）：協商輪數達上限後再協商 → 拒絕，導 ESCALATION。"""
    monkeypatch.setenv("SDD_COMPOSITION_RENEG_MAX", "2")
    p = tmp_path / "composition-ledger.yaml"
    CM.record_negotiate("AC-014", ledger_path=p)   # reneg 1
    CM.record_negotiate("AC-014", ledger_path=p)   # reneg 2
    assert IC.compute_reneg("AC-014", ledger_path=p) == 2
    with pytest.raises(CM.RenegotiationBoundExceeded):
        CM.record_negotiate("AC-014", ledger_path=p)   # 第三次 → 拒絕


def test_record_negotiate_blocks_before_persist(tmp_path, monkeypatch):
    """守門拋出時不得落盤該 negotiate（避免帳本被污染）。"""
    monkeypatch.setenv("SDD_COMPOSITION_RENEG_MAX", "1")
    p = tmp_path / "composition-ledger.yaml"
    CM.record_negotiate("AC-014", ledger_path=p)   # reneg 1（達上限）
    before = len(IC.load_ledger(p)["events"])
    with pytest.raises(CM.RenegotiationBoundExceeded):
        CM.record_negotiate("AC-014", ledger_path=p)
    after = len(IC.load_ledger(p)["events"])
    assert after == before


def test_compose_state_classifier(tmp_path, monkeypatch):
    monkeypatch.setenv("SDD_COMPOSITION_RENEG_MAX", "2")
    p = tmp_path / "composition-ledger.yaml"
    clean = IC.compose([
        IC.IntentSpec("A", "a", {"AC-1": "enable feature"}),
        IC.IntentSpec("B", "b", {"AC-2": "other"}),
    ])
    assert CM.compose_state(clean, ledger_path=p) == "CPLAN_STABLE"   # 無共享衝突
    conflict = IC.compose([
        IC.IntentSpec("A", "a", {"AC-1": "enable feature"}),
        IC.IntentSpec("B", "b", {"AC-1": "disable feature"}),
    ])
    assert CM.compose_state(conflict, ledger_path=p) == "CPLAN_NEGOTIATE"
    CM.record_negotiate("AC-1", ledger_path=p)
    CM.record_negotiate("AC-1", ledger_path=p)
    assert CM.compose_state(conflict, ledger_path=p) == "CPLAN_ESCALATION"


# ---------------------------------------------------------------------------
# ACT-098 — COMPOSITION_FSM.tla 形式化（離線 BFS + 雙源一致）
# ---------------------------------------------------------------------------


def _read_comp_tla() -> str:
    return COMP_TLA.read_text(encoding="utf-8")


def _named_sets(tla: str) -> dict:
    out: dict = {}
    for m in re.finditer(r"^([A-Z][A-Za-z_]*)\s*==\s*\{([^}]*)\}", tla, re.MULTILINE):
        items = re.findall(r'"([A-Z_]+)"', m.group(2))
        if items:
            out[m.group(1)] = set(items)
    return out


def _comp_pairs(tla: str) -> set:
    """從含 `cstate' = "DST"` 的 action 區塊抽 (src, dst) pair。"""
    sets = _named_sets(tla)
    pairs: set = set()
    block_re = re.compile(
        r"^([A-Z][A-Za-z_]*)\s*==\s*((?:.|\n)*?)(?=\n[A-Z][A-Za-z_]*\s*==|\n====|\Z)",
        re.MULTILINE,
    )
    for m in block_re.finditer(tla):
        body = m.group(2)
        dst_m = re.search(r"cstate'\s*=\s*\"([A-Z_]+)\"", body)
        if not dst_m:
            continue
        dst = dst_m.group(1)
        srcs: set = set()
        for g in re.finditer(r"(?<!')\bcstate\s*=\s*\"([A-Z_]+)\"", body):
            srcs.add(g.group(1))
        for g in re.finditer(r"cstate\s*\\in\s*\{([^}]*)\}", body):
            srcs |= set(re.findall(r'"([A-Z_]+)"', g.group(1)))
        for g in re.finditer(r"cstate\s*\\in\s*([A-Z][A-Za-z_]*)", body):
            srcs |= sets.get(g.group(1), set())
        for s in srcs:
            pairs.add((s, dst))
    return pairs


def test_composition_fsm_states_match_python():
    """雙源一致（Rule 9.25.3 精神）：.tla CompStates ↔ monitor.COMPOSITION_STATES。"""
    sets = _named_sets(_read_comp_tla())
    assert sets.get("CompStates") == set(CM.COMPOSITION_STATES)
    assert sets.get("CompTerminals") == set(CM.COMPOSITION_TERMINALS)


def test_composition_fsm_all_states_reachable_offline():
    """從 CPLAN_OBSERVE BFS 必達所有宣告狀態（reachable=N/N，無死狀態）。"""
    tla = _read_comp_tla()
    pairs = _comp_pairs(tla)
    declared = _named_sets(tla)["CompStates"]
    fwd: dict = {}
    for s, d in pairs:
        fwd.setdefault(s, set()).add(d)
    seen = {"CPLAN_OBSERVE"}
    stack = ["CPLAN_OBSERVE"]
    while stack:
        for nxt in fwd.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    dead = declared - seen
    assert not dead, f"COMPOSITION_FSM reachable < 100%：死狀態 {sorted(dead)}"


def test_composition_fsm_every_state_reaches_terminal_offline():
    """反向 BFS 自 {STABLE, ESCALATION}：所有狀態皆可抵達 terminal（EventuallyComposed 結構必要條件）。"""
    tla = _read_comp_tla()
    pairs = _comp_pairs(tla)
    sets = _named_sets(tla)
    declared = sets["CompStates"]
    terminals = sets["CompTerminals"]
    rev: dict = {}
    for s, d in pairs:
        rev.setdefault(d, set()).add(s)
    can_reach = set(terminals)
    stack = list(terminals)
    while stack:
        for prv in rev.get(stack.pop(), ()):
            if prv not in can_reach:
                can_reach.add(prv)
                stack.append(prv)
    stuck = declared - can_reach
    assert not stuck, f"無法抵達 terminal 的狀態（潛在無界協商）：{sorted(stuck)}"


def test_composition_fsm_cfg_declares_invariants_and_liveness():
    cfg = COMP_CFG.read_text(encoding="utf-8")
    for inv in ("TypeOK", "CompositionConsistent", "RenegotiationBounded",
                "ConflictResolvedOrEscalated", "StableIsFixpoint"):
        assert inv in cfg, f"COMPOSITION_FSM.cfg 缺 INVARIANT {inv}"
    assert "EventuallyComposed" in cfg, "COMPOSITION_FSM.cfg 缺 liveness PROPERTY"


def test_single_track_sdd_fsm_unaffected():
    """COMPOSITION_FSM 為獨立命名空間：單軌 SDD_FSM.tla 不含 CPLAN_* 狀態（不污染 42/42）。"""
    sdd_tla = (ROOT / "formal" / "SDD_FSM.tla").read_text(encoding="utf-8")
    assert "CPLAN_" not in sdd_tla, "COMPOSITION 狀態洩漏進單軌 SDD_FSM.tla（破 Rule 9.25.3）"


# ---------------------------------------------------------------------------
# ACT-099 — Capability Trajectory Monitor（進步性監測）
# ---------------------------------------------------------------------------


def _sample(sid, oqs, esc, roi, churn):
    return TM.CapabilitySample(sid, oqs_avg=oqs, escalation_rate=esc,
                               scaffold_roi_avg=roi, churn=churn)


def test_trajectory_rising():
    s = [_sample("s1", 0.6, 0.3, 0.5, 0), _sample("s2", 0.75, 0.2, 0.6, 0),
         _sample("s3", 0.9, 0.1, 0.7, 0)]
    r = TM.classify_trajectory(s, window=3)
    assert r.verdict == "RISING" and r.slope > 0


def test_trajectory_plateau_with_churn():
    """高原：能力平坦但仍 churn（白忙）→ PLATEAU，導人類。"""
    s = [_sample("s1", 0.8, 0.1, 0.6, 2), _sample("s2", 0.8, 0.1, 0.6, 1),
         _sample("s3", 0.8, 0.1, 0.6, 3)]
    r = TM.classify_trajectory(s, window=3)
    assert r.verdict == "PLATEAU" and r.churn_in_window > 0


def test_trajectory_converged_no_churn():
    """平坦且零 churn → CONVERGED（健康，非高原）。"""
    s = [_sample("s1", 0.85, 0.1, 0.6, 0), _sample("s2", 0.85, 0.1, 0.6, 0),
         _sample("s3", 0.85, 0.1, 0.6, 0)]
    assert TM.classify_trajectory(s, window=3).verdict == "CONVERGED"


def test_trajectory_regression():
    s = [_sample("s1", 0.9, 0.1, 0.7, 0), _sample("s2", 0.7, 0.2, 0.6, 0),
         _sample("s3", 0.5, 0.4, 0.4, 0)]
    r = TM.classify_trajectory(s, window=3)
    assert r.verdict == "REGRESSION" and r.slope < 0


def test_trajectory_insufficient():
    assert TM.classify_trajectory([_sample("s1", 0.8, 0.1, 0.6, 0)], window=3).verdict == "INSUFFICIENT"


def test_trajectory_window_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_TRAJECTORY_WINDOW", raising=False)
    assert TM.trajectory_window() == 3
    monkeypatch.setenv("SDD_TRAJECTORY_WINDOW", "99")
    assert TM.trajectory_window() == 10
    monkeypatch.setenv("SDD_TRAJECTORY_WINDOW", "1")
    assert TM.trajectory_window() == 2


def test_trajectory_profile_version_frozen():
    assert TM.TRAJECTORY_PROFILE_VERSION == "v1.0"
    assert abs(sum(TM._WEIGHTS.values()) - 1.0) < 1e-9


def test_trajectory_report_writes(tmp_path):
    s = [_sample("s1", 0.6, 0.3, 0.5, 0), _sample("s2", 0.75, 0.2, 0.6, 0),
         _sample("s3", 0.9, 0.1, 0.7, 0)]
    r = TM.classify_trajectory(s, window=3)
    path = TM.write_report(r, out_dir=tmp_path, today="2026-06-03")
    assert path.exists() and "Capability Trajectory" in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ACT-100 — Scaffold Ceiling Detector（A/B 淨負偵測 + 永不自動退役）
# ---------------------------------------------------------------------------


def _obs(passed, total, errors=0, nonzero=False):
    return ExecutionObservation(tests_total=total, tests_passed=passed,
                                runtime_errors=errors, nonzero_exit=nonzero)


def test_ceiling_detects_net_negative(monkeypatch):
    """WITHOUT 顯著優於 WITH → 淨負天花板，輸出退役建議。"""
    monkeypatch.setenv("SDD_CEILING_DELTA", "0.05")
    samples = [CD.ABSample("SLV-009", with_obs=_obs(6, 10), without_obs=_obs(10, 10))]
    res = CD.detect_ceilings(samples)
    assert len(res.proposals) == 1
    assert res.proposals[0].scaffold_id == "SLV-009"
    assert res.proposals[0].delta > 0.05


def test_ceiling_net_positive_no_proposal(monkeypatch):
    """WITH ≥ WITHOUT → 鷹架仍有價值，不建議退役。"""
    monkeypatch.setenv("SDD_CEILING_DELTA", "0.05")
    samples = [CD.ABSample("SLV-007", with_obs=_obs(10, 10), without_obs=_obs(7, 10))]
    assert CD.detect_ceilings(samples).proposals == []


def test_ceiling_skips_non_firing():
    """死/被超越（still_firing=False）鷹架不在本偵測範圍（走 scaffold_gc）。"""
    samples = [CD.ABSample("SLV-dead", with_obs=_obs(5, 10), without_obs=_obs(10, 10),
                           still_firing=False)]
    res = CD.detect_ceilings(samples)
    assert res.proposals == [] and res.scanned == 0


def test_ceiling_detector_never_calls_set_maturity(monkeypatch):
    """🔴 Rule 9.25.5：detector 絕不自呼叫 set_maturity（退役必經人工 gate）。"""
    import tools.fsm_runtime.rule_loader as RL
    called = {"n": 0}
    monkeypatch.setattr(RL, "set_maturity",
                        lambda *a, **k: called.__setitem__("n", called["n"] + 1))
    samples = [CD.ABSample("SLV-009", with_obs=_obs(5, 10), without_obs=_obs(10, 10))]
    CD.detect_ceilings(samples)
    assert called["n"] == 0, "detector 不得自動退役任何鷹架（破 Rule 9.25.5）"


def test_ceiling_delta_env_clamp(monkeypatch):
    monkeypatch.delenv("SDD_CEILING_DELTA", raising=False)
    assert CD.ceiling_delta() == 0.05
    monkeypatch.setenv("SDD_CEILING_DELTA", "0.99")
    assert CD.ceiling_delta() == 0.50
    monkeypatch.setenv("SDD_CEILING_DELTA", "0.001")
    assert CD.ceiling_delta() == 0.01


def test_ceiling_report_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("SDD_CEILING_DELTA", "0.05")
    samples = [CD.ABSample("SLV-009", with_obs=_obs(6, 10), without_obs=_obs(10, 10))]
    res = CD.detect_ceilings(samples)
    path = CD.write_report(res, out_dir=tmp_path, today="2026-06-03")
    assert path.exists() and "Scaffold Ceiling" in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ACT-101 — Composition Blast Analyzer（組合爆炸半徑 + 排程序列化）
# ---------------------------------------------------------------------------


def test_blast_multiplier_increases_with_sharing_and_fragility():
    intents = [
        IC.IntentSpec("A", "a", {"AC-014": "折扣可疊加", "AC-020": "x"}),
        IC.IntentSpec("B", "b", {"AC-014": "折扣禁止疊加", "AC-020": "x"}),
        IC.IntentSpec("C", "c", {"AC-014": "折扣限一張"}),
    ]
    report = BA.analyze_blast(intents, single_fragility={"AC-014": 0.9, "AC-020": 0.2})
    top = report.scores[0]
    # AC-014：3 意圖共享 + 高單一脆弱 + 有衝突耦合 → blast 最大
    assert top.node_id == "AC-014"
    assert top.blast > report.scores[-1].blast


def test_blast_recommend_serialization():
    intents = [
        IC.IntentSpec("A", "a", {"AC-014": "折扣可疊加"}),
        IC.IntentSpec("B", "b", {"AC-014": "折扣禁止疊加"}),
        IC.IntentSpec("C", "c", {"AC-099": "獨立"}),
    ]
    report = BA.analyze_blast(intents, single_fragility={"AC-014": 0.9})
    sched = BA.recommend_schedule(intents, report, threshold=0.5)
    assert ["A", "B"] in sched["serialize"]
    assert "C" in sched["parallel"]


def test_blast_profile_version_frozen():
    assert BA.COMPOSITION_FRAGILITY_PROFILE_VERSION == "v1.0"


def test_blast_report_writes(tmp_path):
    intents = [
        IC.IntentSpec("A", "a", {"AC-014": "x"}),
        IC.IntentSpec("B", "b", {"AC-014": "y"}),
    ]
    report = BA.analyze_blast(intents, single_fragility={"AC-014": 0.7})
    path = BA.write_report(report, out_dir=tmp_path, today="2026-06-03")
    assert path.exists() and "Composition Blast" in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# ACT-102 — steersman 整合（advisory 加掛）
# ---------------------------------------------------------------------------


def test_steersman_render_composition_blast():
    from tools.fsm_runtime.steersman_renderer import render_composition_blast
    intents = [
        IC.IntentSpec("A", "a", {"AC-014": "enable"}),
        IC.IntentSpec("B", "b", {"AC-014": "disable"}),
    ]
    md = render_composition_blast(intents, single_fragility={"AC-014": 0.8})
    assert "Composition Blast" in md and "AC-014" in md


def test_steersman_render_trajectory():
    from tools.fsm_runtime.steersman_renderer import render_trajectory
    s = [_sample("s1", 0.8, 0.1, 0.6, 2), _sample("s2", 0.8, 0.1, 0.6, 1),
         _sample("s3", 0.8, 0.1, 0.6, 3)]
    md = render_trajectory(s, window=3)
    assert "PLATEAU" in md


# ---------------------------------------------------------------------------
# ACT-098 — opt-in 完整 TLC 窮舉
# ---------------------------------------------------------------------------


@pytest.mark.tlc
def test_composition_fsm_tlc_full_verification_opt_in():
    """完整 TLC 窮舉 COMPOSITION_FSM（5 safety + 1 liveness）。需 SDD_RUN_TLC=1 + java + jar。"""
    if os.environ.get("SDD_RUN_TLC") != "1":
        pytest.skip("set SDD_RUN_TLC=1 to run full TLC（離線可達性不變量已常駐守門）")
    from tools.fsm_runtime import tlc_runner as T
    if T.find_java() is None or not T.jar_path().exists():
        pytest.skip("java 或 tla2tools.jar 不存在")
    res = T.run_tlc(depth=50, tla="COMPOSITION_FSM.tla", cfg="COMPOSITION_FSM.cfg")
    assert res["ok"], f"COMPOSITION_FSM TLC 驗證失敗：{res.get('log_tail') or res.get('error')}"
    assert res["distinct"] > 0
