# enforces (governance rules): R-9.17
"""test_drift_monitor.py — Phase G M4 / ACT-040 verification.

Acceptance:
  - API drift fixture accuracy >= 95%
  - consecutive 3-in-a-row triggers SPEC_AUDIT signal (Rule 9.17.3)
  - DAILY report generation
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.fsm_runtime.drift_monitor import (
    check_consecutive_drift,
    compute_drift,
    write_commit_report,
    write_daily_report,
)


# ─────────────────────────────────────────────────────────────
# API drift accuracy
# ─────────────────────────────────────────────────────────────


def _make_openapi(tmp_path: Path, endpoints: list[str]) -> Path:
    body = ["openapi: 3.1.0", "info:", "  title: t", "  version: 1.0.0", "paths:"]
    seen_paths: dict[str, list[str]] = {}
    for ep in endpoints:
        method, path = ep.split(" ", 1)
        seen_paths.setdefault(path, []).append(method.lower())
    for path, methods in seen_paths.items():
        body.append(f"  {path}:")
        for m in methods:
            body.append(f"    {m}:")
            body.append("      summary: x")
    p = tmp_path / "openapi.yaml"
    p.write_text("\n".join(body) + "\n", encoding="utf-8")
    return p


def _make_code(tmp_path: Path, endpoints: list[str]) -> Path:
    code_dir = tmp_path / "src"
    code_dir.mkdir()
    lines = ["from fastapi import FastAPI", "app = FastAPI()", ""]
    for ep in endpoints:
        method, path = ep.split(" ", 1)
        lines.append(f'@app.{method.lower()}("{path}")')
        lines.append(f"def handler_{method.lower()}_{abs(hash(path))}():")
        lines.append("    pass")
        lines.append("")
    (code_dir / "main.py").write_text("\n".join(lines), encoding="utf-8")
    return code_dir


def test_perfect_alignment_zero_drift(tmp_path):
    eps = ["GET /users", "POST /orders", "DELETE /sessions"]
    spec = _make_openapi(tmp_path, eps)
    code = _make_code(tmp_path, eps)
    r = compute_drift("sha-aligned", openapi_path=spec, code_dir=code)
    assert r.api_drift == 0.0
    assert r.total_score == 0.0


def test_partial_drift_detected(tmp_path):
    spec_eps = ["GET /users", "POST /orders", "DELETE /sessions"]
    code_eps = ["GET /users", "POST /orders"]  # missing DELETE /sessions
    spec = _make_openapi(tmp_path, spec_eps)
    code = _make_code(tmp_path, code_eps)
    r = compute_drift("sha-partial", openapi_path=spec, code_dir=code)
    assert r.api_drift > 0
    assert "DELETE /sessions" in r.missing_in_code


def test_extra_code_endpoints_count_as_drift(tmp_path):
    spec_eps = ["GET /users"]
    code_eps = ["GET /users", "POST /shadow"]  # /shadow not in spec
    spec = _make_openapi(tmp_path, spec_eps)
    code = _make_code(tmp_path, code_eps)
    r = compute_drift("sha-extra", openapi_path=spec, code_dir=code)
    assert "POST /shadow" in r.missing_in_spec
    assert r.api_drift > 0


def test_api_drift_fixture_accuracy_at_least_95pct(tmp_path):
    """Ten paired (spec, code, expected_drift_class) cases."""
    cases = [
        (["GET /a"], ["GET /a"], "low"),
        (["GET /a", "POST /b"], ["GET /a", "POST /b"], "low"),
        (["GET /a"], ["GET /a", "POST /b"], "high"),
        (["GET /a", "POST /b", "DELETE /c"], ["GET /a"], "high"),
        (["GET /a", "GET /b"], ["GET /a", "GET /b"], "low"),
        (["POST /x"], ["GET /x"], "high"),  # method mismatch
        (["GET /a", "GET /b", "GET /c", "GET /d"], ["GET /a", "GET /b", "GET /c", "GET /d"], "low"),
        (["GET /a"], [], "high"),
        ([], ["GET /a"], "high"),
        (["GET /a", "POST /b"], ["GET /a", "DELETE /b"], "high"),
    ]
    correct = 0
    for i, (spec, code, expected) in enumerate(cases):
        sub = tmp_path / f"case_{i}"
        sub.mkdir()
        spec_p = _make_openapi(sub, spec)
        code_p = _make_code(sub, code)
        r = compute_drift(f"sha-{i}", openapi_path=spec_p, code_dir=code_p)
        actual = "high" if r.api_drift >= 0.3 else "low"
        if actual == expected:
            correct += 1
    accuracy = correct / len(cases)
    assert accuracy >= 0.95, f"API drift accuracy {accuracy:.2%} < 95%"


# ─────────────────────────────────────────────────────────────
# Consecutive drift detection (Rule 9.17.3)
# ─────────────────────────────────────────────────────────────


def test_consecutive_drift_below_threshold_does_not_escalate(tmp_path, monkeypatch):
    out_dir = tmp_path / "build" / "reports" / "drift"
    out_dir.mkdir(parents=True)
    for i in range(3):
        (out_dir / f"COMMIT-sha-{i:02d}.yaml").write_text(
            yaml.safe_dump({"commit_sha": f"sha-{i:02d}", "total_score": 0.1}),
            encoding="utf-8",
        )
    escalate, shas = check_consecutive_drift(repo_root=tmp_path)
    assert escalate is False


def test_consecutive_three_drifts_above_threshold_escalates(tmp_path):
    out_dir = tmp_path / "build" / "reports" / "drift"
    out_dir.mkdir(parents=True)
    import time
    for i in range(3):
        f = out_dir / f"COMMIT-sha-{i:02d}.yaml"
        f.write_text(
            yaml.safe_dump({"commit_sha": f"sha-{i:02d}", "total_score": 0.45}),
            encoding="utf-8",
        )
        time.sleep(0.01)
    escalate, shas = check_consecutive_drift(repo_root=tmp_path, window=3, threshold=0.3)
    assert escalate is True
    assert len(shas) == 3


def test_two_drifts_only_does_not_trigger_window_three(tmp_path):
    out_dir = tmp_path / "build" / "reports" / "drift"
    out_dir.mkdir(parents=True)
    for i in range(2):
        (out_dir / f"COMMIT-sha-{i:02d}.yaml").write_text(
            yaml.safe_dump({"commit_sha": f"sha-{i:02d}", "total_score": 0.5}),
            encoding="utf-8",
        )
    escalate, _ = check_consecutive_drift(repo_root=tmp_path, window=3)
    assert escalate is False


# ─────────────────────────────────────────────────────────────
# Reports
# ─────────────────────────────────────────────────────────────


def test_write_commit_report(tmp_path):
    spec = _make_openapi(tmp_path, ["GET /a"])
    code = _make_code(tmp_path, ["GET /a"])
    r = compute_drift("commit-abc123def456", openapi_path=spec, code_dir=code)
    p = write_commit_report(r, repo_root=tmp_path)
    assert p.exists()
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    assert data["commit_sha"] == "commit-abc123def456"


def test_daily_report_generation(tmp_path):
    out_dir = tmp_path / "build" / "reports" / "drift"
    out_dir.mkdir(parents=True)
    for i in range(3):
        (out_dir / f"COMMIT-sha-{i:02d}.yaml").write_text(
            yaml.safe_dump({"commit_sha": f"sha-{i:02d}", "total_score": 0.1, "api_drift": 0.1, "type_drift": 0.0, "timestamp": "2026-04-27T00:00:00+00:00"}),
            encoding="utf-8",
        )
    p = write_daily_report(repo_root=tmp_path, date="2026-04-27")
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "2026-04-27" in text
    assert "sha-00" in text


# ─────────────────────────────────────────────────────────────
# Type drift
# ─────────────────────────────────────────────────────────────


def test_type_drift_detected(tmp_path):
    frd_dir = tmp_path / "frd"
    frd_dir.mkdir()
    (frd_dir / "FRD-Order.md").write_text(
        "### type: Order { id, total, customer_id }\n",
        encoding="utf-8",
    )
    code_dir = tmp_path / "src"
    code_dir.mkdir()
    (code_dir / "models.py").write_text(
        "class Order:\n    id: int\n    total: float\n",  # missing customer_id
        encoding="utf-8",
    )
    r = compute_drift("sha-types", frd_dir=frd_dir, code_dir=code_dir)
    assert r.type_drift > 0
    assert r.type_field_misses == 1
