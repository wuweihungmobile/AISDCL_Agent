# enforces (governance rules): R-9.21, R-SELF-STRIDE
"""Phase I / ACT-059~069 — Trustworthy Scaled Reality-Grounded Autonomy tests.

涵蓋三 Pillar：
  A 可信接地：hermetic 重跑+FLAKY（ACT-059）/ sandbox 硬化（ACT-060）/
    SANDBOX_HARDENING_GATE + self-STRIDE（ACT-061）/ OQS 校準（ACT-062）/
    oracle 新鮮度 + EVALUATOR_AUDIT（ACT-063）
  C 可持續證明：spec_monitor + MONITOR_VIOLATION（ACT-064）
  B 規模增殖：SPL 結晶 + MEMORY_CONSOLIDATION（ACT-066）/ behavioral 回饋 +
    PRODUCTION_BEHAVIORAL_SIGNAL（ACT-067）/ value_planner + BACKLOG_PRIORITIZED +
    attention_router（ACT-068）
  §6 自我驗證 e2e：flaky + 惡意碼 + 漂移判官
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.fsm_runtime import FSMRuntime
from tools.fsm_runtime.state_loader import load_state, save_state
from tools.fsm_runtime.transition_rules import TransitionError, OBSERVATION_STATES


def _rt(tmp_path, name, current):
    p = tmp_path / f"FSM-STATE-{name}.yaml"
    st = load_state(name, path=p, create_if_missing=True)
    st.root["current_state"] = current
    save_state(st)
    return FSMRuntime(st)


# ==================== ACT-059: hermetic 重跑 + FLAKY ====================

def test_hermetic_all_pass():
    from tools.fsm_runtime.sandbox_runner import (
        evaluate_hermetic, SandboxSpec, ExecutionObservation)
    obs = [ExecutionObservation(tests_total=5, tests_passed=5) for _ in range(5)]
    r = evaluate_hermetic(SandboxSpec(app_id="a"), observation_overrides=obs, write_report=False)
    assert r.verdict == "PASS"
    assert r.to_exec_verdict() == "pass"


def test_hermetic_all_fail():
    from tools.fsm_runtime.sandbox_runner import (
        evaluate_hermetic, SandboxSpec, ExecutionObservation)
    obs = [ExecutionObservation(tests_total=5, tests_passed=0, nonzero_exit=True) for _ in range(5)]
    r = evaluate_hermetic(SandboxSpec(app_id="a"), observation_overrides=obs, write_report=False)
    assert r.verdict == "FAIL"
    assert r.to_exec_verdict() == "runtime_fail"


def test_hermetic_flaky_isolated(tmp_path):
    from tools.fsm_runtime.sandbox_runner import (
        evaluate_hermetic, SandboxSpec, ExecutionObservation)
    mix = ([ExecutionObservation(tests_total=5, tests_passed=5)] * 3
           + [ExecutionObservation(tests_total=5, tests_passed=0, nonzero_exit=True)] * 2)
    r = evaluate_hermetic(SandboxSpec(app_id="flaky"), observation_overrides=mix,
                          report_dir=tmp_path)
    assert r.verdict == "FLAKY" and r.is_flaky
    # FLAKY 不可映射為 exec verdict（隔離，不進 retry 迴圈）
    with pytest.raises(ValueError):
        r.to_exec_verdict()
    # FLAKY 報告寫出
    assert r.flaky_report_path and Path(r.flaky_report_path).exists()


def test_hermetic_flaky_report_sanitizes_app_id_path_traversal(tmp_path):
    """R39 Scan-A：SandboxSpec.app_id 未淨化即組 FLAKY-*.yaml 檔名，路徑穿越
    輸入應被 state_loader._sanitize_component 收斂，不逃出 report_dir。"""
    from tools.fsm_runtime.sandbox_runner import (
        evaluate_hermetic, SandboxSpec, ExecutionObservation)
    mix = ([ExecutionObservation(tests_total=5, tests_passed=5)] * 3
           + [ExecutionObservation(tests_total=5, tests_passed=0, nonzero_exit=True)] * 2)
    r = evaluate_hermetic(SandboxSpec(app_id="../../evil"), observation_overrides=mix,
                          report_dir=tmp_path)
    assert r.flaky_report_path
    written = Path(r.flaky_report_path)
    assert written.resolve().parent == tmp_path.resolve()
    assert written.exists()


def test_hermetic_rerun_capped():
    from tools.fsm_runtime.sandbox_runner import (
        evaluate_hermetic, SandboxSpec, ExecutionObservation, FLAKY_RERUN_N)
    obs = [ExecutionObservation(tests_total=1, tests_passed=1) for _ in range(20)]
    r = evaluate_hermetic(SandboxSpec(app_id="a"), observation_overrides=obs,
                          n=99, write_report=False)
    assert r.runs == FLAKY_RERUN_N  # 硬上限封頂


# ==================== ACT-060: sandbox 硬化 ====================

def test_security_profile_args():
    from tools.fsm_runtime.sandbox_runner import SecurityProfile
    args = " ".join(SecurityProfile().docker_args())
    for flag in ("--network none", "--cap-drop ALL", "--read-only",
                 "--user 65534:65534", "--memory", "--pids-limit",
                 "--security-opt no-new-privileges"):
        assert flag in args


def test_security_profile_seccomp_default_off():
    # 預設不發出 seccomp 旗標（沿用 Docker 內建 default seccomp，向後相容）
    from tools.fsm_runtime.sandbox_runner import SecurityProfile
    args = " ".join(SecurityProfile().docker_args())
    assert "seccomp" not in args
    assert "seccomp=unconfined" not in args  # 從不停用內建 seccomp


def test_security_profile_seccomp_custom():
    # 設定自訂 profile 時發出 --security-opt seccomp=<profile>
    from tools.fsm_runtime.sandbox_runner import SecurityProfile
    args = SecurityProfile(seccomp_profile="/etc/seccomp/strict.json").docker_args()
    assert "--security-opt" in args
    assert "seccomp=/etc/seccomp/strict.json" in args


def test_image_allowlist():
    from tools.fsm_runtime.sandbox_runner import image_allowed
    assert image_allowed("busybox")
    assert image_allowed("python:3.11-slim")
    assert not image_allowed("evilcorp/backdoor:latest")
    assert not image_allowed(None)


def test_docker_backend_rejects_unlisted_image():
    from tools.fsm_runtime.sandbox_runner import DockerBackend, SandboxSpec, SandboxPolicyViolation
    be = DockerBackend()
    with pytest.raises(SandboxPolicyViolation):
        be.run(SandboxSpec(app_id="x", image="evilcorp/backdoor"))


# ==================== ACT-061: SANDBOX_HARDENING_GATE + self-STRIDE ====================

def test_sandbox_hardening_gate_pass(tmp_path):
    rt = _rt(tmp_path, "shg-pass", "IMPLEMENTATION")
    rt.enter_sandbox_hardening_gate()
    assert rt.state.current == "SANDBOX_HARDENING_GATE"
    rt.exit_sandbox_hardening_gate("pass")
    assert rt.state.current == "EXECUTION_EVALUATION"


def test_sandbox_hardening_gate_policy_violation(tmp_path):
    rt = _rt(tmp_path, "shg-fail", "IMPLEMENTATION")
    rt.enter_sandbox_hardening_gate()
    rt.exit_sandbox_hardening_gate("policy_violation")
    assert rt.state.current == "ESCALATION"


def test_loop_threat_model_pass():
    from tools.fsm_runtime.loop_threat_model import evaluate_hardening
    from tools.fsm_runtime.sandbox_runner import SandboxSpec
    res = evaluate_hardening(SandboxSpec(app_id="a", image="busybox"))
    assert res.passed
    assert all(res.stride_controls.values())


def test_loop_threat_model_evil_image():
    from tools.fsm_runtime.loop_threat_model import evaluate_hardening
    from tools.fsm_runtime.sandbox_runner import SandboxSpec
    res = evaluate_hardening(SandboxSpec(app_id="a", image="evil/x"))
    assert not res.passed
    assert any("allow-list" in v for v in res.violations)


def test_loop_threat_model_supply_chain_and_signature(tmp_path):
    from tools.fsm_runtime.loop_threat_model import (
        evaluate_hardening, sign_spec, file_sha256)
    from tools.fsm_runtime.sandbox_runner import SandboxSpec
    lock = tmp_path / "lock.txt"
    lock.write_text("dep==1.0\n", encoding="utf-8")
    good_hash = file_sha256(lock)
    payload = "spec-body"
    sig = sign_spec(payload)
    res = evaluate_hardening(
        SandboxSpec(app_id="a", image="busybox"),
        spec_payload=payload, spec_signature=sig, require_signature=True,
        lockfile_path=lock, expected_lockfile_hash=good_hash, require_lockfile=True,
    )
    assert res.passed
    # 竄改 lockfile → 違反
    lock.write_text("dep==9.9 EVIL\n", encoding="utf-8")
    res2 = evaluate_hardening(
        SandboxSpec(app_id="a", image="busybox"),
        spec_payload=payload, spec_signature=sig, require_signature=True,
        lockfile_path=lock, expected_lockfile_hash=good_hash, require_lockfile=True,
    )
    assert not res2.passed


def test_diagnostic_sandbox_policy_violation_structural():
    from tools.fsm_runtime.diagnostic import diagnose
    r = diagnose("sandbox_policy_violation: image not in allow-list")
    assert r.category == "structural"
    assert r.sub_type == "sandbox_policy_violation"
    assert r.auto_recoverable is False


# ==================== ACT-062: OQS 校準 ====================

def test_oqs_calibration_drift(tmp_path):
    from tools.fsm_runtime import oqs_calibration as oc
    rolling = tmp_path / "rolling.yaml"
    res = None
    for _ in range(3):
        res = oc.record_calibration(verdict="pass", downstream_violated=True,
                                    ac_id="AC-1", rolling_path=rolling)
    assert res.drifted
    assert res.consecutive_pass_but_violated >= 3
    rpt = oc.write_oqs_drift_report(res, out_dir=tmp_path)
    assert rpt and Path(rpt).exists()


def test_oqs_calibration_flaky_excluded(tmp_path):
    from tools.fsm_runtime import oqs_calibration as oc
    rolling = tmp_path / "rolling.yaml"
    res = oc.record_calibration(verdict="FLAKY", downstream_violated=True, rolling_path=rolling)
    assert res.samples == 0  # FLAKY 不進校準樣本
    assert not rolling.exists()


# ==================== ACT-063: oracle 新鮮度 + EVALUATOR_AUDIT ====================

def test_oracle_freshness(tmp_path):
    from tools.fsm_runtime import oracle_freshness as ofr
    spec = tmp_path / "frd.md"
    spec.write_text("AC-1: do X\n", encoding="utf-8")
    sha = ofr.compute_spec_sha([spec])
    assert ofr.check(frozen_spec_sha=sha, spec_paths=[spec]).fresh
    spec.write_text("AC-1: do Y differently\n", encoding="utf-8")
    res = ofr.check(frozen_spec_sha=sha, spec_paths=[spec])
    assert res.stale


def test_evaluator_audit_transitions(tmp_path):
    rt = _rt(tmp_path, "ea", "EXECUTION_EVALUATION")
    rt.enter_evaluator_audit()
    assert rt.state.current == "EVALUATOR_AUDIT"
    rt.exit_evaluator_audit("continue")
    assert rt.state.current == "EXECUTION_EVALUATION"


def test_evaluator_audit_illegal_source(tmp_path):
    rt = _rt(tmp_path, "ea2", "PR_REVIEW")
    with pytest.raises(TransitionError):
        rt.enter_evaluator_audit()


# ==================== ACT-064: spec_monitor + MONITOR_VIOLATION ====================

def test_spec_monitor_detects_retry_violation(tmp_path):
    rt = _rt(tmp_path, "mon", "IMPLEMENTATION")
    rt.state.root.setdefault("retry_history", {})["PR_REVIEW"] = {"current_count": 99}
    save_state(rt.state)
    res = rt.run_spec_monitor()
    assert not res["ok"]
    assert res["escalated"]
    assert rt.state.current == "ESCALATION"


def test_spec_monitor_clean_state(tmp_path):
    rt = _rt(tmp_path, "mon2", "IMPLEMENTATION")
    res = rt.run_spec_monitor()
    assert res["ok"]
    assert rt.state.current == "IMPLEMENTATION"


def test_monitor_violation_only_exits_escalation(tmp_path):
    rt = _rt(tmp_path, "mv", "IMPLEMENTATION")
    rt.enter_monitor_violation(invariant="RetryBounded", detail="x")
    assert rt.state.current == "MONITOR_VIOLATION"
    assert "MONITOR_VIOLATION" in OBSERVATION_STATES
    rt.exit_monitor_violation()
    assert rt.state.current == "ESCALATION"


# ==================== ACT-066: SPL 結晶 + MEMORY_CONSOLIDATION ====================

def test_memory_consolidation_transitions(tmp_path):
    rt = _rt(tmp_path, "mc", "RELEASE")
    rt.enter_memory_consolidation()
    assert rt.state.current == "MEMORY_CONSOLIDATION"
    rt.exit_memory_consolidation("done")
    assert rt.state.current == "RELEASE"


def test_spl_consolidator_proposes_proposed_only(tmp_path):
    from tools.fsm_runtime import spl_consolidator as spl
    rt = _rt(tmp_path, "spl", "RELEASE")
    # 注入 4 筆同模式 productive 軌跡
    trace = [{"from_state": "IMPLEMENTATION", "to_state": "PR_REVIEW",
              "trigger": "gate_pass", "reason": "impl complete feature X"} for _ in range(4)]
    rt.state.root["decision_trace"] = trace
    save_state(rt.state)
    proposals = spl.consolidate(rt.state, out_dir=tmp_path, today="2026-06-01")
    assert proposals
    assert all(p.trust_level == "proposed" for p in proposals)
    assert proposals[0].reuse_count >= spl.CONSOLIDATION_MIN_EPISODES


def test_reverse_graduation_proposal():
    from tools.fsm_runtime.rule_loader import Rule, propose_promotion
    r = Rule(id="R-X", title="t", scaffold_roi={"fire_count": 100, "catch_count": 90,
                                                "false_positive_count": 0})
    assert propose_promotion(r) is not None
    weak = Rule(id="R-Y", title="t", scaffold_roi={"fire_count": 5, "catch_count": 5,
                                                   "false_positive_count": 0})
    assert propose_promotion(weak) is None


# ==================== ACT-067: behavioral 回饋 + PRODUCTION_BEHAVIORAL_SIGNAL ====================

def test_behavioral_drift_scorer():
    from tools.fsm_runtime.behavioral_drift_scorer import (
        score_behavioral_drift, BehavioralObservation, FrozenContract, dominant_kind)
    contract = FrozenContract(ac_id="AC-1", required_fields=["id", "total"],
                              invariants=["INV-1"], required_branches=["happy", "refund"])
    obs = BehavioralObservation(ac_id="AC-1", observed_fields=["id"],
                                invariants_violated=["INV-1"], branches_hit=["happy"])
    res = score_behavioral_drift(obs, contract)
    assert res.diverged and res.score > 0
    assert dominant_kind(res) in ("contract_shape", "invariant_violation", "missing_branch")


def test_production_to_fpl_threshold(tmp_path):
    from tools.fsm_runtime import production_to_fpl as p2f
    events = [p2f.BehavioralDriftEvent(ac_id="AC-1", divergence_kind="invariant_violation", score=0.5)
              for _ in range(3)]
    written = p2f.process_drift_events(events, out_dir=tmp_path, today="2026-06-01")
    assert written
    txt = Path(written[0]).read_text(encoding="utf-8")
    assert "trust_level" in txt and "proposed" in txt


def test_production_to_fpl_sanitizes_path_traversal_ac_id(tmp_path):
    """R39 Scan-A：ac_id/divergence_kind 為生產遙測衍生、外部可控，未淨化即組檔名
    可路徑穿越（DEF-101-3xx 系列同類缺陷，收斂為重用 state_loader._sanitize_component）。"""
    from tools.fsm_runtime import production_to_fpl as p2f
    path_str = p2f.generate_fpl_draft(
        "../../evil", "../../../also-evil", occurrences=3, out_dir=tmp_path, today="2026-06-01"
    )
    written = Path(path_str)
    assert written.resolve().parent == tmp_path.resolve()
    assert written.exists()


def test_production_to_fpl_sanitizes_explicit_fpl_id_override(tmp_path):
    """R39 一審 SD 發現：explicit `fpl_id` 覆寫分支原本完全繞過淨化（只有
    fallback 組裝分支有淨化），為本輪修復範圍內未收斂完整的同一縫隙。"""
    from tools.fsm_runtime import production_to_fpl as p2f
    path_str = p2f.generate_fpl_draft(
        "AC-1", "kind", occurrences=3, out_dir=tmp_path, today="2026-06-01",
        fpl_id="../../escaped-evil",
    )
    written = Path(path_str)
    assert written.resolve().parent == tmp_path.resolve()
    assert written.exists()


def test_production_behavioral_signal_transitions(tmp_path):
    rt = _rt(tmp_path, "pbs", "RELEASE")
    rt.enter_production_behavioral_signal()
    assert rt.state.current == "PRODUCTION_BEHAVIORAL_SIGNAL"
    rt.exit_production_behavioral_signal("learn")
    assert rt.state.current == "LEARNING_COMMIT"


# ==================== ACT-068: value_planner + BACKLOG + attention ====================

def test_value_planner_ranks_by_roi(tmp_path):
    from tools.fsm_runtime.value_planner import BacklogCandidate, write_backlog_rank
    cands = [
        BacklogCandidate("C1", "low", business_value=0.2, confidence=0.5, estimated_cost=10000),
        BacklogCandidate("C2", "high", business_value=0.9, confidence=0.9, estimated_cost=5000),
    ]
    res = write_backlog_rank(cands, out_dir=tmp_path, today="2026-06-01")
    assert res.ranked[0].candidate_id == "C2"
    assert Path(res.report_path).exists()


def test_backlog_prioritized_gate(tmp_path):
    rt = _rt(tmp_path, "bp", "AGENT_LOAD")
    rt.enter_backlog_prioritized()
    assert rt.state.current == "BACKLOG_PRIORITIZED"
    rt.exit_backlog_prioritized(selected_ref="EPIC-1")
    assert rt.state.current == "SPEC_DRAFTING"


def test_attention_router_p0_never_folded(tmp_path):
    from tools.fsm_runtime.attention_budget import AttentionEvent, route, write_digest
    events = [
        AttentionEvent("e1", "structural", "spec_conflict", "AC vs INV"),
        AttentionEvent("e2", "structural", "spec_conflict", "AC vs INV again"),
        AttentionEvent("e3", "transient", "ci_timeout", "runner slow"),
        AttentionEvent("e4", "transient", "ci_timeout", "runner slow too"),
    ]
    digest = route(events)
    # structural P0 全保留（永不折疊）
    assert len(digest.p0_events) == 2
    # transient 同模式去重折疊
    assert digest.folded
    path = write_digest(digest, out_dir=tmp_path, today="2026-06-01")
    assert Path(path).exists()


def test_abort_raw_audit_no_overwrite(tmp_path):
    from tools.fsm_runtime.snapshot import save_abort_report
    rt = _rt(tmp_path, "abort", "ESCALATION")
    save_abort_report(rt.state, reason="r1", category="cat", out_dir=tmp_path)
    save_abort_report(rt.state, reason="r2", category="cat", out_dir=tmp_path)
    raw = list(tmp_path.glob("ABORT-RAW-*.yaml"))
    assert raw
    import yaml
    doc = yaml.safe_load(raw[0].read_text(encoding="utf-8"))
    # 同 category 兩次 abort 都在 raw audit（不覆寫）
    assert len(doc["events"]) == 2


# ==================== §6 自我驗證 e2e：flaky + 惡意碼 + 漂移判官 ====================

def test_section6_e2e_flaky_malicious_drifted_judge(tmp_path):
    """§6 極端案例：flaky test + phone-home 相依套件 + 已漂移 OQS。

    驗證三道遞進關卡：
      1. SANDBOX_HARDENING_GATE 在「執行前」擋下惡意 image（PI-4）
      2. hermetic 重跑把 flaky 判為第三 verdict、隔離不進 retry（PI-3）
      3. OQS 校準鏈偵測漂移判官 → 進 EVALUATOR_AUDIT（PI-2）
    """
    from tools.fsm_runtime.sandbox_runner import (
        evaluate_hermetic, SandboxSpec, ExecutionObservation, image_allowed)
    from tools.fsm_runtime.loop_threat_model import evaluate_hardening
    from tools.fsm_runtime import oqs_calibration as oc

    # 關卡 1（PI-4）：惡意 image 在執行前被硬化閘擋下 → ESCALATION
    rt = _rt(tmp_path, "e2e", "IMPLEMENTATION")
    malicious = SandboxSpec(app_id="evil", image="evilcorp/phonehome")
    hard = evaluate_hardening(malicious)
    assert not hard.passed  # 惡意 image 不在 allow-list
    rt.enter_sandbox_hardening_gate()
    rt.exit_sandbox_hardening_gate("policy_violation")
    assert rt.state.current == "ESCALATION"

    # 關卡 2（PI-3）：改用合法依賴，但 test 為 flaky（3/5）→ 隔離為 FLAKY
    mix = ([ExecutionObservation(tests_total=5, tests_passed=5)] * 3
           + [ExecutionObservation(tests_total=5, tests_passed=0, nonzero_exit=True)] * 2)
    herm = evaluate_hermetic(SandboxSpec(app_id="legit", image="busybox"),
                             observation_overrides=mix, report_dir=tmp_path)
    assert herm.is_flaky
    # FLAKY 不進 OQS 校準樣本（不污染判官）
    rolling = tmp_path / "rolling.yaml"
    assert oc.record_calibration(verdict="FLAKY", downstream_violated=True,
                                 rolling_path=rolling).samples == 0

    # 關卡 3（PI-2）：漂移判官 — 連續 3 次「OQS pass 但生產違反」→ drift
    drift = None
    for _ in range(3):
        drift = oc.record_calibration(verdict="pass", downstream_violated=True,
                                      ac_id="AC-1", rolling_path=rolling)
    assert drift.drifted
    # 進 EVALUATOR_AUDIT 要求人工 recalibrate（從 EXECUTION_EVALUATION 入）
    rt2 = _rt(tmp_path, "e2e-audit", "EXECUTION_EVALUATION")
    rt2.enter_evaluator_audit(drift_ref="OQS-DRIFT")
    assert rt2.state.current == "EVALUATOR_AUDIT"
    rt2.exit_evaluator_audit("recalibrate")
    assert rt2.state.current == "RELEASE"
