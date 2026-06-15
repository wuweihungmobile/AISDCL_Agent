"""test_post_commit_drift.py — Phase G M4 / ACT-039 hook verification.

Acceptance:
  - Hook completes < 2s budget (Rule 9.17.1)
  - Hook is advisory only — never raises (always exit 0 on failure path)
  - .git/COMMIT_DRIFT_WARNING written when drift_score >= 0.3
"""
from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

HOOK_PATH = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "post_commit_drift.py"


@pytest.fixture
def hook_module():
    spec = importlib.util.spec_from_file_location("post_commit_drift", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hook_module_imports_cleanly(hook_module):
    assert hasattr(hook_module, "main")
    assert hook_module.BUDGET_SEC == 2


def test_hook_completes_under_2s_budget(hook_module, tmp_path):
    """Rule 9.17.1: budget < 2s."""
    # Patch _current_sha to avoid needing real git, and REPO_ROOT to a clean tmp
    with patch.object(hook_module, "_current_sha", return_value="testsha-001"), \
         patch.object(hook_module, "REPO_ROOT", tmp_path):
        start = time.monotonic()
        rc = hook_module.main()
        elapsed = time.monotonic() - start
    assert rc == 0
    assert elapsed < 2.0, f"hook took {elapsed:.3f}s, exceeds 2s budget"


def test_hook_writes_warning_when_drift_high(hook_module, tmp_path):
    """When drift_score >= 0.3 → write .git/COMMIT_DRIFT_WARNING (advisory)."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    from tools.fsm_runtime.drift_monitor import DriftReport

    high = DriftReport(commit_sha="sha-high", api_drift=0.8, type_drift=0.0, total_score=0.5)
    with patch.object(hook_module, "_current_sha", return_value="sha-high"), \
         patch.object(hook_module, "REPO_ROOT", tmp_path), \
         patch.object(hook_module, "compute_drift", return_value=high), \
         patch.object(hook_module, "check_consecutive_drift", return_value=(False, [])):
        rc = hook_module.main()
    assert rc == 0
    warn = git_dir / "COMMIT_DRIFT_WARNING"
    assert warn.exists()
    assert "0.5" in warn.read_text(encoding="utf-8")


def test_hook_silent_when_drift_low(hook_module, tmp_path):
    """When drift_score < 0.3 → no warning written."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    from tools.fsm_runtime.drift_monitor import DriftReport

    low = DriftReport(commit_sha="sha-low", api_drift=0.05, type_drift=0.0, total_score=0.03)
    with patch.object(hook_module, "_current_sha", return_value="sha-low"), \
         patch.object(hook_module, "REPO_ROOT", tmp_path), \
         patch.object(hook_module, "compute_drift", return_value=low), \
         patch.object(hook_module, "check_consecutive_drift", return_value=(False, [])):
        rc = hook_module.main()
    assert rc == 0
    assert not (git_dir / "COMMIT_DRIFT_WARNING").exists()


def test_hook_advisory_on_compute_failure(hook_module, tmp_path):
    """Rule 9.17.1 advisory: any exception inside hook → exit 0 + warning, never block."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    with patch.object(hook_module, "_current_sha", return_value="sha-err"), \
         patch.object(hook_module, "REPO_ROOT", tmp_path), \
         patch.object(hook_module, "compute_drift", side_effect=RuntimeError("simulated")):
        rc = hook_module.main()
    assert rc == 0
    warn = git_dir / "COMMIT_DRIFT_WARNING"
    assert warn.exists()
    assert "error" in warn.read_text(encoding="utf-8")


def test_hook_consecutive_warning(hook_module, tmp_path):
    """Rule 9.17.3: when consecutive_drift detected → second warning."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    from tools.fsm_runtime.drift_monitor import DriftReport
    high = DriftReport(commit_sha="sha-3rd", api_drift=0.8, type_drift=0.0, total_score=0.5)
    with patch.object(hook_module, "_current_sha", return_value="sha-3rd"), \
         patch.object(hook_module, "REPO_ROOT", tmp_path), \
         patch.object(hook_module, "compute_drift", return_value=high), \
         patch.object(hook_module, "check_consecutive_drift", return_value=(True, ["a", "b", "c"])):
        rc = hook_module.main()
    assert rc == 0
    warn = git_dir / "COMMIT_DRIFT_WARNING"
    text = warn.read_text(encoding="utf-8")
    assert "consecutive" in text.lower() or "SPEC_AUDIT" in text
