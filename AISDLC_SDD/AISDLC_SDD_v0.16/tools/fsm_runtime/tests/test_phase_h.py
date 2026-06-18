"""Phase H / ACT-045~058 — Generative-Adversarial Execution Layer tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime.fsm_runtime import FSMRuntime
from tools.fsm_runtime.state_loader import load_state, save_state
from tools.fsm_runtime.transition_rules import (
    TransitionError,
    OBSERVATION_STATES,
    _HAPPY_PATH,
)


def _rt(tmp_path, state_name, current):
    p = tmp_path / f"FSM-STATE-{state_name}.yaml"
    st = load_state(state_name, path=p, create_if_missing=True)
    st.root["current_state"] = current
    save_state(st)
    return FSMRuntime(st)


# ---------- M1: EXECUTION_EVALUATION ----------

def test_execution_evaluation_pass(tmp_path):
    rt = _rt(tmp_path, "ee-pass", "IMPLEMENTATION")
    rt.enter_execution_evaluation()
    assert rt.state.current == "EXECUTION_EVALUATION"
    rt.exit_execution_evaluation("pass")
    assert rt.state.current == "PR_REVIEW"


def test_execution_evaluation_runtime_fail(tmp_path):
    rt = _rt(tmp_path, "ee-fail", "IMPLEMENTATION")
    rt.enter_execution_evaluation()
    rt.exit_execution_evaluation("runtime_fail")
    assert rt.state.current == "IMPLEMENTATION"


def test_execution_evaluation_spec_defect(tmp_path):
    rt = _rt(tmp_path, "ee-spec", "IMPLEMENTATION")
    rt.enter_execution_evaluation()
    rt.exit_execution_evaluation("spec_defect")
    assert rt.state.current == "SPEC_AUDIT"


def test_execution_evaluation_bad_verdict(tmp_path):
    rt = _rt(tmp_path, "ee-bad", "IMPLEMENTATION")
    rt.enter_execution_evaluation()
    with pytest.raises(ValueError):
        rt.exit_execution_evaluation("definitely-not-a-verdict")


# ---------- M2: TEST_CONTRACT_NEGOTIATED ----------

def test_test_contract_agreed(tmp_path):
    rt = _rt(tmp_path, "tc-ok", "SPEC_FROZEN")
    rt.enter_test_contract_negotiated(contract_ref="API_Order.yaml")
    assert rt.state.current == "TEST_CONTRACT_NEGOTIATED"
    rt.exit_test_contract_negotiated("agreed")
    assert rt.state.current == "IMPLEMENTATION"


def test_test_contract_underspecified(tmp_path):
    rt = _rt(tmp_path, "tc-no", "SPEC_FROZEN")
    rt.enter_test_contract_negotiated()
    rt.exit_test_contract_negotiated("underspecified")
    assert rt.state.current == "SPEC_DRAFTING"


def test_record_test_standard_agreement(tmp_path):
    from tools.fsm_runtime import subagent_contract as sc
    rec = sc.record_test_standard_agreement(
        contract_ref="API_Order.yaml",
        acceptance_criteria=["AC-001-1: HTTP 200 + P95<200ms"],
        generator_signed=True,
        out_dir=tmp_path,
    )
    assert rec["ready_for_implementation"] is True
    assert Path(rec["path"]).exists()
    # 未簽署 → 不得進入 IMPLEMENTATION
    rec2 = sc.record_test_standard_agreement(
        contract_ref="x", acceptance_criteria=["AC"], generator_signed=False, out_dir=tmp_path,
    )
    assert rec2["ready_for_implementation"] is False


# ---------- M5: SCAFFOLD_GC ----------

def test_scaffold_gc_observation_state():
    assert "SCAFFOLD_GC" in OBSERVATION_STATES


def test_scaffold_gc_enter_exit_continue(tmp_path):
    rt = _rt(tmp_path, "gc-ok", "RELEASE")
    rt.enter_scaffold_gc()
    assert rt.state.current == "SCAFFOLD_GC"
    rt.exit_scaffold_gc("continue")
    assert rt.state.current == "RELEASE"


def test_scaffold_gc_respec(tmp_path):
    rt = _rt(tmp_path, "gc-respec", "RELEASE")
    rt.enter_scaffold_gc()
    rt.exit_scaffold_gc("respec")
    assert rt.state.current == "SPEC_DRAFTING"


def test_scaffold_gc_illegal_source(tmp_path):
    rt = _rt(tmp_path, "gc-bad", "IMPLEMENTATION")
    with pytest.raises(TransitionError):
        rt.enter_scaffold_gc()


# ---------- M1: Output Quality Scorer ----------

def test_oqs_pass():
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation, score
    obs = ExecutionObservation(tests_total=10, tests_passed=10, ui_assertions_total=4, ui_assertions_passed=4)
    r = score(obs)
    assert r.passed and r.verdict == "pass" and r.score >= 0.8


def test_oqs_runtime_fail():
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation, score
    obs = ExecutionObservation(tests_total=10, tests_passed=4, nonzero_exit=True)
    r = score(obs)
    assert not r.passed and r.verdict == "runtime_fail"


def test_oqs_spec_defect_forced():
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation, score
    obs = ExecutionObservation(tests_total=10, tests_passed=10)
    r = score(obs, spec_defect=True)
    assert r.verdict == "spec_defect" and not r.passed


def test_oqs_inconclusive_on_zero_observation():
    # H-1：完全無觀測（den 全 0）不得 pass，必為 inconclusive。
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation, score
    r = score(ExecutionObservation())
    assert r.verdict == "inconclusive" and r.passed is False


def test_oqs_failure_signal_counts_as_observation():
    # 只有失敗訊號（非零 exit）也算「跑過」→ runtime_fail，非 inconclusive。
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation, score
    r = score(ExecutionObservation(nonzero_exit=True))
    assert r.verdict == "runtime_fail" and r.passed is False


# ---------- M1: Sandbox Runner ----------

def test_sandbox_local_stub_is_inconclusive_not_pass():
    # H-4 + H-1：stub 零觀測「絕不可」放行 pass — 鎖死執行接地契約。
    from tools.fsm_runtime.sandbox_runner import SandboxSpec, evaluate
    res = evaluate(SandboxSpec(app_id="demo"), backend="local")
    assert res.backend == "local-stub"
    assert res.oqs.verdict == "inconclusive"
    assert res.oqs.passed is False


def test_sandbox_override_observation():
    from tools.fsm_runtime.sandbox_runner import SandboxSpec, evaluate
    from tools.fsm_runtime.output_quality_scorer import ExecutionObservation
    obs = ExecutionObservation(tests_total=5, tests_passed=5)
    res = evaluate(SandboxSpec(app_id="demo"), observation_override=obs)
    assert res.oqs.verdict == "pass"


def test_sandbox_playwright_backend_not_configured():
    from tools.fsm_runtime.sandbox_runner import SandboxSpec, evaluate
    with pytest.raises(NotImplementedError):
        evaluate(SandboxSpec(app_id="demo"), backend="playwright")


# ---------- ACT-046: Docker backend real execution-grounding ----------

def test_parse_test_output_pass():
    from tools.fsm_runtime.sandbox_runner import parse_test_output
    obs = parse_test_output("10 passed, 0 failed in 1.2s", "", 0)
    assert obs.tests_total == 10 and obs.tests_passed == 10
    assert obs.nonzero_exit is False and obs.runtime_errors == 0


def test_parse_test_output_fail():
    from tools.fsm_runtime.sandbox_runner import parse_test_output
    obs = parse_test_output("7 passed, 3 failed", "Traceback: boom", 1)
    assert obs.tests_total == 10 and obs.tests_passed == 7
    assert obs.nonzero_exit is True and obs.runtime_errors >= 1


_DOCKER = None
try:
    from tools.fsm_runtime.sandbox_runner import docker_available as _da
    _DOCKER = _da()
except Exception:  # noqa: BLE001
    _DOCKER = False

requires_docker = pytest.mark.skipif(not _DOCKER, reason="docker daemon 不可用")


@requires_docker
def test_docker_backend_real_pass():
    # 真實執行接地：容器實跑成功 → OQS pass。
    from tools.fsm_runtime.sandbox_runner import SandboxSpec, evaluate
    spec = SandboxSpec(app_id="demo", image="busybox",
                       test_cmd=["sh", "-c", "echo '10 passed, 0 failed'; exit 0"],
                       timeout_sec=60)
    res = evaluate(spec, backend="docker")
    assert res.backend == "docker"
    assert res.observation.tests_passed == 10
    assert res.oqs.verdict == "pass" and res.oqs.passed is True


@requires_docker
def test_docker_backend_real_runtime_fail():
    # 真實執行接地：容器實跑失敗（exit 1 + stderr）→ OQS runtime_fail。
    from tools.fsm_runtime.sandbox_runner import SandboxSpec, evaluate
    spec = SandboxSpec(app_id="demo", image="busybox",
                       test_cmd=["sh", "-c", "echo 'error: boom' >&2; exit 1"],
                       timeout_sec=60)
    res = evaluate(spec, backend="docker")
    assert res.observation.nonzero_exit is True
    assert res.oqs.verdict == "runtime_fail" and res.oqs.passed is False


@requires_docker
def test_docker_backend_e2e_through_fsm(tmp_path):
    # 端到端：IMPLEMENTATION → enter_execution_evaluation → 容器實跑 verdict → exit 路由。
    from tools.fsm_runtime.sandbox_runner import SandboxSpec, evaluate
    rt = _rt(tmp_path, "ee-docker", "IMPLEMENTATION")
    rt.enter_execution_evaluation()
    spec = SandboxSpec(app_id="demo", image="busybox",
                       test_cmd=["sh", "-c", "echo '5 passed, 0 failed'; exit 0"],
                       timeout_sec=60)
    res = evaluate(spec, backend="docker")
    rt.exit_execution_evaluation(res.oqs.verdict)
    assert rt.state.current == "PR_REVIEW"


# ---------- M4: Observability Query ----------

def test_logql_lite(tmp_path):
    from tools.fsm_runtime import observability_query as oq
    (tmp_path / "logs.ndjson").write_text(
        '{"level":"error","msg":"deadlock on tx-42"}\n'
        '{"level":"info","msg":"started"}\n'
        '{"level":"error","msg":"timeout"}\n',
        encoding="utf-8",
    )
    hits = oq.logql_lite('{level="error"} |= "deadlock"', obs_dir=tmp_path)
    assert len(hits) == 1 and "deadlock" in hits[0]["msg"]


def test_promql_lite(tmp_path):
    from tools.fsm_runtime import observability_query as oq
    (tmp_path / "metrics.ndjson").write_text(
        '{"name":"http_p95_ms","value":120,"labels":{"route":"/login"}}\n'
        '{"name":"http_p95_ms","value":200,"labels":{"route":"/login"}}\n'
        '{"name":"http_p95_ms","value":50,"labels":{"route":"/health"}}\n',
        encoding="utf-8",
    )
    assert oq.promql_lite("http_p95_ms", agg="max", labels={"route": "/login"}, obs_dir=tmp_path) == 200.0
    assert oq.promql_lite("http_p95_ms", agg="count", obs_dir=tmp_path) == 3.0


def test_obs_dir_accepts_str_path(tmp_path):
    # robustness：obs_dir 接受 str（非僅 Path）— 防 str/str 例外。
    from tools.fsm_runtime import observability_query as oq
    (tmp_path / "logs.ndjson").write_text('{"level":"error","msg":"x"}\n', encoding="utf-8")
    assert oq.logql_lite('{level="error"}', obs_dir=str(tmp_path)) == [{"level": "error", "msg": "x"}]


# ---------- M3: Rule Loader ----------

def test_rule_loader_load_for_state():
    from tools.fsm_runtime import rule_loader
    rules = rule_loader.load_for_state("EXECUTION_EVALUATION")
    assert any(r.id == "R-9.20" for r in rules)
    # ESCALATION 不應命中 phase-h gate 規則
    esc = rule_loader.load_for_state("ESCALATION")
    assert any(r.id == "R-9.14" for r in esc)
    assert not any(r.id == "R-9.20" for r in esc)


def _seed_rule(tmp_path):
    import yaml
    d = tmp_path / "rules"
    d.mkdir()
    (d / "R-9.99-test.yaml").write_text(yaml.safe_dump({
        "id": "R-9.99", "title": "t", "trigger_states": ["IMPLEMENTATION"],
        "severity": "low", "maturity": "active", "spec": "x", "test_ref": "x",
        "scaffold_roi": {"fire_count": 0, "catch_count": 0, "false_positive_count": 0},
    }, allow_unicode=True), encoding="utf-8")
    return d


def test_rule_loader_record_fire_and_graduation(tmp_path):
    from tools.fsm_runtime import rule_loader
    d = _seed_rule(tmp_path)
    for _ in range(rule_loader.GRADUATION_MIN_FIRES):
        rule_loader.record_fire("R-9.99", caught=False, rules_dir=d)
    r = [x for x in rule_loader.load_all(d) if x.id == "R-9.99"][0]
    assert r.scaffold_roi["fire_count"] == rule_loader.GRADUATION_MIN_FIRES
    assert rule_loader.propose_graduation(r) == "audit-only"


def test_rule_loader_set_maturity_requires_reviewer(tmp_path):
    from tools.fsm_runtime import rule_loader
    d = _seed_rule(tmp_path)
    with pytest.raises(rule_loader.RuleOverwriteProtected):
        rule_loader.set_maturity("R-9.99", "audit-only", reviewed_by="", rules_dir=d)
    r = rule_loader.set_maturity("R-9.99", "audit-only", reviewed_by="human@x", rules_dir=d)
    assert r.maturity == "audit-only"


# ---------- M5: Scaffold GC ----------

def test_scaffold_gc_run_report(tmp_path):
    from tools.fsm_runtime import scaffold_gc, rule_loader
    d = _seed_rule(tmp_path)
    for _ in range(rule_loader.GRADUATION_MIN_FIRES):
        rule_loader.record_fire("R-9.99", caught=False, rules_dir=d)
    res = scaffold_gc.run_gc(rules_dir=d, out_dir=tmp_path / "gc", today="2026-05-31")
    assert res.rules_scanned == 1
    assert any(p.rule_id == "R-9.99" for p in res.proposals)
    assert Path(res.report_path).exists()


def test_scaffold_gc_audit_decision_trace(tmp_path):
    # H-5：驗證具體分類語意，而非恆真集合成員檢查。
    from tools.fsm_runtime import scaffold_gc
    rt = _rt(tmp_path, "gc-trace", "IMPLEMENTATION")
    rt.transition("PR_REVIEW", reason="impl done", trigger="impl_complete")
    rt.transition("SPEC_AUDIT", reason="audit", trigger="impl_complete")
    rt.state.current = "ESCALATION"
    rt.transition("TERMINATED", reason="abort", trigger="escalation_abort")
    entries = scaffold_gc.audit_decision_trace(rt.state)
    outcomes = {e.trigger: e.outcome for e in entries}
    # escalation/abort trigger 必歸類 led_to_escalation
    assert outcomes.get("escalation_abort") == "led_to_escalation"
    # 一般 impl_complete 必歸類 productive
    assert "productive" in {e.outcome for e in entries}


# ---------- M6: Steersman Renderer + abort report ----------

def test_steersman_render_spec_conflict():
    from tools.fsm_runtime.steersman_renderer import render_markdown
    from tools.fsm_runtime.diagnostic import diagnose
    d = diagnose("SLV-004 FAIL: AC-003 conflicts INV-002", spec_refs=["AC-003", "INV-002"])
    md = render_markdown(d, slv_contradiction="AC-003-1「P95 < 0ms」與 INV-002 物理矛盾")
    assert "舵手" in md
    assert "sa-analyst" in md
    assert "AC-003-1" in md


def test_save_abort_report_includes_steersman(tmp_path):
    from tools.fsm_runtime.snapshot import save_abort_report
    from tools.fsm_runtime.diagnostic import diagnose
    rt = _rt(tmp_path, "abort", "ESCALATION")
    d = diagnose("SLV-004 FAIL: AC-003 conflicts INV-002", spec_refs=["AC-003", "INV-002"])
    p = save_abort_report(
        rt.state, reason="spec conflict", category="spec-conflict-test",
        diagnostic=d, slv_contradiction="AC-003-1 與 INV-002 物理矛盾",
        out_dir=tmp_path,
    )
    text = Path(p).read_text(encoding="utf-8")
    assert "舵手" in text and "sa-analyst" in text


def test_save_abort_report_backward_compatible(tmp_path):
    """無 diagnostic 時，舊呼叫端不受影響（向後相容）。"""
    from tools.fsm_runtime.snapshot import save_abort_report
    rt = _rt(tmp_path, "abort-bc", "ESCALATION")
    p = save_abort_report(rt.state, reason="x", category="bc-test", out_dir=tmp_path)
    assert Path(p).exists()


def test_act056_structural_escalation_fsm_writes_diagnostic_abort(tmp_path):
    """ACT-056 / §G8 wiring：structural ESCALATION_FINAL 須由 FSM 直接產出
    含 diagnostic 的舵手級 abort 報告，而非僅回傳 diagnostic 讓 caller 自理。"""
    rt = _rt(tmp_path, "g8-wire", "ESCALATION")
    outcome = rt.enter_auto_recovery(
        escalation_reason="SLV-004 FAIL: AC-003-1 P95<0ms 與 INV-002 矛盾",
        resume_state="PR_REVIEW",
    )
    assert outcome["entered"] is False
    assert outcome["next_state"] == "ESCALATION_FINAL"
    path = outcome.get("abort_report_path")
    assert path, "structural ESCALATION_FINAL 未產出 abort 報告（§G8 未接線）"
    content = Path(path).read_text(encoding="utf-8")
    # 證明 diagnostic 真的流入報告（舵手交棒，而非僅 retry exhausted）
    assert "sa-analyst" in content
    assert "舵手" in content or "steersman" in content.lower()
