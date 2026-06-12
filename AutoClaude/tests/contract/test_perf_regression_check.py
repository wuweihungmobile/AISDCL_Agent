"""perf_regression_check contract test（SD_08 W5 / ADR-SD08-003 §2.4-§2.5）。

≥ 4 case：
  1. 通過（< 10% 增量）
  2. 警告（10-15% 增量 → exit=0 + ::warning:: annotation）
  3. 阻塞（≥ 15% 增量 → exit=1 + ::error:: annotation + PR comment）
  4. 缺 baseline → exit=1
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = PROJECT_ROOT / "tools" / "perf_regression_check.py"


def _write_baseline(tmp_path: Path, p95: float, samples: int = 20) -> Path:
    """寫測試用 .perf_baseline.toml（單一場景 dry_run_e2e）。

    SD_09 W0 P0-AUDIT-perf-followup：預設 samples=20（避免無謂觸發 undersampled downgrade）；
    需測 undersampled 行為時傳入 samples=7。
    """
    path = tmp_path / "baseline.toml"
    body = (
        "[dry_run_e2e]\n"
        f"p50_ms = {p95 * 0.7}\n"
        f"p95_ms = {p95}\n"
        f"p99_ms = {p95 * 1.1}\n"
        f'samples = {samples}\n'
        'git_sha = "test"\n'
        'captured_at = "2026-05-21T00:00:00+00:00"\n'
    )
    path.write_text(body, encoding="utf-8")
    return path


def _write_results(tmp_path: Path, p95: float) -> Path:
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"dry_run_e2e": p95}), encoding="utf-8")
    return path


def _run_tool(results: Path, baseline: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    comment_out = tmp_path / "comment.md"
    return subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            str(results),
            str(baseline),
            "--comment-out",
            str(comment_out),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )


def test_perf_regression_check_pass(tmp_path):
    """場景 1：增量 +5% → exit=0、無 ::warning:: 也無 ::error::。"""
    baseline = _write_baseline(tmp_path, 1000.0)
    results = _write_results(tmp_path, 1050.0)  # +5%

    result = _run_tool(results, baseline, tmp_path)

    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "::error::" not in result.stdout
    assert "::warning::Perf" not in result.stdout  # warn annotation 不該出現


def test_perf_regression_check_warn(tmp_path):
    """場景 2：增量 +12% → SD_09 W3 Round 2 audit P0-6 三態：exit=2（warn）+ ::warning::。"""
    baseline = _write_baseline(tmp_path, 1000.0)
    results = _write_results(tmp_path, 1120.0)  # +12%

    result = _run_tool(results, baseline, tmp_path)

    # P0-6 三態：warn → rc=2（與 green rc=0 區分）
    assert result.returncode == 2, f"stdout={result.stdout!r}"
    assert "::warning::" in result.stdout
    assert "::error::" not in result.stdout


def test_perf_regression_check_block(tmp_path):
    """場景 3：增量 +20% → exit=1 + ::error:: annotation + PR comment 產出。"""
    baseline = _write_baseline(tmp_path, 1000.0)
    results = _write_results(tmp_path, 1200.0)  # +20%

    comment_out = tmp_path / "comment.md"
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            str(results),
            str(baseline),
            "--comment-out",
            str(comment_out),
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "::error::" in result.stdout
    assert comment_out.exists(), "block 等級必須寫出 PR comment markdown"
    md = comment_out.read_text(encoding="utf-8")
    assert "🔴 阻塞" in md
    assert "dry_run_e2e" in md


def test_perf_regression_check_missing_baseline(tmp_path):
    """場景 4：baseline 檔不存在 → exit=1 + ::error::。"""
    baseline = tmp_path / "no_such_baseline.toml"  # 不寫
    results = _write_results(tmp_path, 1000.0)

    result = _run_tool(results, baseline, tmp_path)

    assert result.returncode == 1
    assert "::error::" in result.stdout
    assert "baseline 不存在" in result.stdout or "為空" in result.stdout


def test_perf_regression_check_undersampled_baseline_downgrades_block_to_warn(tmp_path):
    """場景 5（SD_09 W0 P0-AUDIT-perf-followup mirror test）：

    baseline samples=7 < MIN_BASELINE_SAMPLES=20 + 增量 +20% → 原本 BLOCK 退化為 WARN
    （SD_09 W3 Round 2 audit P0-6：rc 三態 → warn=2，非 0；對齊既有 warning「not blocking」
    宣告意圖；紀律 #1 區分真實失敗 vs 統計噪音）。
    """
    baseline = _write_baseline(tmp_path, 1000.0, samples=7)  # 強制 undersampled
    results = _write_results(tmp_path, 1200.0)  # +20%（原本應 BLOCK）

    result = _run_tool(results, baseline, tmp_path)

    # P0-6 三態：BLOCK→WARN 退化 rc=2（非 1 block，也非 0 green）
    assert result.returncode == 2, f"stdout={result.stdout!r}"
    assert "BLOCK→WARN downgrade" in result.stdout
    assert "::error::" not in result.stdout


def test_perf_regression_check_locked_baseline_still_blocks_block_level(tmp_path):
    """場景 6（SD_09 W0 P0-AUDIT-perf-followup 反向 mirror）：

    baseline samples=20（已鎖定）+ 增量 +20% → 維持 BLOCK（不該退化）；
    證明 downgrade 只在 undersampled 時生效，未污染正常路徑。
    """
    baseline = _write_baseline(tmp_path, 1000.0, samples=20)  # 已鎖定
    results = _write_results(tmp_path, 1200.0)  # +20%

    result = _run_tool(results, baseline, tmp_path)

    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "::error::" in result.stdout
    assert "BLOCK→WARN downgrade" not in result.stdout
