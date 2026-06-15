# enforces (governance rules): R-9.19
"""test_path_cost.py — Phase G M6 / ACT-043/044 verification.

Acceptance:
  - Cold start (samples < 10) → 8000 token default (Rule 9.19.1)
  - Rolling-30 estimate error < 30% on synthetic stable workload
  - Gate logic: passes iff remaining > estimated * 1.2
  - REJECTED log structure (Rule 9.19.2)
  - Calibration warn after 5 consecutive > 50% errors (Rule 9.19.4)
  - Consecutive 3 dispatch rejections → ESCALATION (Rule 9.19.3)
"""
from __future__ import annotations

import statistics
from pathlib import Path

import pytest
import yaml

from tools.fsm_runtime.path_cost import (
    COLD_START_DEFAULT_TOKENS,
    GATE_MULTIPLIER,
    MIN_SAMPLES,
    PathCostEstimator,
    record_dispatch_rejection,
)


# ─────────────────────────────────────────────────────────────
# Cold start (Rule 9.19.1)
# ─────────────────────────────────────────────────────────────


def test_cold_start_returns_default_8000(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    est = e.estimate("dev-senior", "implementation_pr")
    assert est.value == COLD_START_DEFAULT_TOKENS
    assert est.source == "cold_start"
    assert est.samples == 0


def test_cold_start_holds_until_min_samples(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    for _ in range(MIN_SAMPLES - 1):
        e.record_sample("dev-senior", "impl", 5000)
    est = e.estimate("dev-senior", "impl")
    assert est.source == "cold_start"
    e.record_sample("dev-senior", "impl", 5000)
    est = e.estimate("dev-senior", "impl")
    assert est.source == "rolling_30"


# ─────────────────────────────────────────────────────────────
# Rolling-30 estimate
# ─────────────────────────────────────────────────────────────


def test_rolling_estimate_error_under_30pct(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    samples = [5000 + (i % 5) * 200 for i in range(30)]  # stable around 5400
    for s in samples:
        e.record_sample("sa-analyst", "spec_drafting", s)
    est = e.estimate("sa-analyst", "spec_drafting")
    avg_actual = statistics.mean(samples)
    error = abs(est.value - avg_actual) / avg_actual
    assert error < 0.30, f"estimate error {error:.2%} >= 30%"


def test_rolling_window_caps_at_30(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    for i in range(50):
        e.record_sample("dev-senior", "impl", 1000 + i)
    est = e.estimate("dev-senior", "impl")
    assert est.samples == 30  # capped


# ─────────────────────────────────────────────────────────────
# NA-3 milestone hook (Phase G Final post-CF-6)
# ─────────────────────────────────────────────────────────────


def test_milestone_fires_once_at_30th_sample(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    paths = []
    for i in range(35):
        p = e.record_sample("dev-senior", "impl", 5000 + i)
        if p is not None:
            paths.append(p)
    # Exactly one milestone path emitted, at the 30th sample
    assert len(paths) == 1
    milestone = paths[0]
    assert milestone.exists()
    assert milestone.name.startswith("CALIBRATION-MILESTONE-dev-senior-impl-")
    body = yaml.safe_load(milestone.read_text(encoding="utf-8"))
    assert body["milestone"] == "rolling_30_saturated"
    assert body["samples_count"] == 30
    assert body["subagent"] == "dev-senior"


def test_milestone_isolated_per_pair(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    for i in range(30):
        e.record_sample("dev-senior", "impl", 5000)
    # Different (subagent, classification) should fire its own milestone
    paths = []
    for i in range(30):
        p = e.record_sample("sa-analyst", "spec", 3000)
        if p is not None:
            paths.append(p)
    assert len(paths) == 1
    assert "sa-analyst-spec" in paths[0].name


def test_milestone_does_not_refire_after_saturation(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    for _ in range(30):
        e.record_sample("dev-senior", "impl", 5000)
    # Subsequent samples must not refire
    refires = [e.record_sample("dev-senior", "impl", 5000) for _ in range(20)]
    assert all(r is None for r in refires)


# ─────────────────────────────────────────────────────────────
# Gate logic
# ─────────────────────────────────────────────────────────────


def test_gate_pass_when_remaining_above_safety_margin(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    for _ in range(15):
        e.record_sample("dev-senior", "impl", 5000)
    passed, est = e.gate_pass("dev-senior", "impl", token_remaining=int(est_value(e, "dev-senior", "impl") * 2))
    assert passed is True


def test_gate_block_when_remaining_below_safety_margin(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    for _ in range(15):
        e.record_sample("dev-senior", "impl", 5000)
    est_val = est_value(e, "dev-senior", "impl")
    passed, est = e.gate_pass("dev-senior", "impl", token_remaining=int(est_val * GATE_MULTIPLIER) - 1)
    assert passed is False


def test_gate_block_in_cold_start_with_low_budget(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    passed, est = e.gate_pass("new-agent", "fresh", token_remaining=1000)
    assert est.value == COLD_START_DEFAULT_TOKENS
    assert passed is False  # 1000 < 8000 * 1.2


def est_value(e: PathCostEstimator, agent: str, cls: str) -> int:
    return e.estimate(agent, cls).value


# ─────────────────────────────────────────────────────────────
# REJECTED log (Rule 9.19.2)
# ─────────────────────────────────────────────────────────────


def test_record_dispatch_rejection_writes_yaml(tmp_path):
    p = record_dispatch_rejection(
        subagent="dev-senior",
        classification="impl",
        estimated=12000,
        remaining=9500,
        reason="budget_exhausted",
        proposed_alternative="stage-compaction first",
        repo_root=tmp_path,
    )
    assert p.exists()
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert len(data["rejected"]) == 1
    row = data["rejected"][0]
    assert row["subagent"] == "dev-senior"
    assert row["estimated"] == 12000
    assert row["remaining"] == 9500
    assert row["proposed_alternative"]


def test_record_dispatch_rejection_appends_existing_log(tmp_path):
    record_dispatch_rejection(
        subagent="a", classification="x", estimated=1000, remaining=500,
        reason="r1", repo_root=tmp_path,
    )
    p = record_dispatch_rejection(
        subagent="b", classification="y", estimated=2000, remaining=900,
        reason="r2", repo_root=tmp_path,
    )
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert len(data["rejected"]) == 2
    assert {r["subagent"] for r in data["rejected"]} == {"a", "b"}


# ─────────────────────────────────────────────────────────────
# Calibration warn (Rule 9.19.4)
# ─────────────────────────────────────────────────────────────


def test_calibration_warn_after_5_consecutive_high_errors(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    out = None
    for _ in range(5):
        out = e.record_calibration("dev-senior", "impl", estimated=1000, actual=2000)
    assert out is not None and out.exists()
    text = out.read_text(encoding="utf-8")
    assert "Rule 9.19.4" in text


def test_calibration_no_warn_under_threshold(tmp_path):
    e = PathCostEstimator(repo_root=tmp_path)
    out = None
    for _ in range(5):
        out = e.record_calibration("dev-senior", "impl", estimated=1000, actual=1100)  # 10% error
    assert out is None


# ─────────────────────────────────────────────────────────────
# Consecutive 3 rejections → ESCALATION (Rule 9.19.3) — integration with FSMRuntime
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def fsm_runtime(tmp_path, monkeypatch):
    from tools.fsm_runtime import state_loader as sl
    from tools.fsm_runtime import fsm_runtime as fr
    state_dir = tmp_path / "fsm-state"
    state_dir.mkdir()
    monkeypatch.setattr(sl, "DEFAULT_STATE_DIR", state_dir)
    monkeypatch.setattr(fr, "DEFAULT_STATE_DIR", state_dir, raising=False)
    return fr.FSMRuntime.bootstrap(project="test")


def test_record_dispatch_rejection_increments(fsm_runtime):
    r1 = fsm_runtime.record_dispatch_rejection(reason="budget_exhausted")
    assert r1["escalated"] is False
    assert r1["count"] == 1


def test_three_consecutive_rejections_escalate(fsm_runtime):
    for _ in range(2):
        fsm_runtime.record_dispatch_rejection(reason="budget_exhausted")
    r = fsm_runtime.record_dispatch_rejection(reason="budget_exhausted")
    assert r["escalated"] is True
    assert fsm_runtime.state.current == "ESCALATION"


def test_reset_dispatch_rejections_clears_count(fsm_runtime):
    fsm_runtime.record_dispatch_rejection()
    fsm_runtime.record_dispatch_rejection()
    fsm_runtime.reset_dispatch_rejections()
    r = fsm_runtime.record_dispatch_rejection(reason="x")
    # After reset, this is the first; should not escalate yet
    assert r["escalated"] is False
    assert r["count"] == 1
