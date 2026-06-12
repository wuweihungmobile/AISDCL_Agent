"""dry_run e2e 性能 baseline（SD_08 W5 / ADR-SD08-003 §2.2 場景 #1）。

採集環境：CI nightly（ubuntu-latest，CPU-bound only）
SLA 目標：p95 < baseline × 1.15

注意：本測試的 smoke 版本可在正常 CI 跑（純 CPU、可重現）；perf-baseline-nightly
job 另跑帶 pytest-benchmark 的版本以取得正式 baseline 數字。

SD_09 W0 Pre-W0 audit B-07 修復（2026-05-20）：
  - 移除玩具 `for i in range(2000): total += i*i` 負載
  - 改為呼叫真實 5-step mock Playbook 經 PlaybookRunner.run(dry_run=True)
  - 工作負載涵蓋 Playbook 載入 + 5 步驟 dry_run regex 合成輸出 + 評估
"""
from __future__ import annotations

from pathlib import Path

import pytest

from autoclaude.utils.perf_baseline import measure

pytestmark = pytest.mark.perf


def _build_mock_playbook(tmp_dir: Path) -> Path:
    """SD_09 B-07：建立 5-step mock playbook（regex 合成輸出，純 CPU）。"""
    body = """version: "1.0"
project: "perf_baseline_dry_run_e2e"
global_goal: "perf baseline dry_run 5-step measurement"
global_invariants:
  max_retries_per_step: 1
  auto_compact_interval: 5
tasks:
  - step_id: "P01"
    name: "perf step 1"
    prompt: "step1 prompt body"
    expected_output_regex: "DONE_P01"
    max_retries: 1
  - step_id: "P02"
    name: "perf step 2"
    prompt: "step2 prompt body"
    expected_output_regex: "DONE_P02"
    max_retries: 1
  - step_id: "P03"
    name: "perf step 3"
    prompt: "step3 prompt body"
    expected_output_regex: "DONE_P03"
    max_retries: 1
  - step_id: "P04"
    name: "perf step 4"
    prompt: "step4 prompt body"
    expected_output_regex: "DONE_P04"
    max_retries: 1
  - step_id: "P05"
    name: "perf step 5"
    prompt: "step5 prompt body"
    expected_output_regex: "DONE_P05"
    max_retries: 1
"""
    path = tmp_dir / "perf_dry_run_e2e.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _build_runner(tmp_dir: Path):
    """建立 PlaybookRunner(dry_run=True) 實例（最小依賴）。"""
    from unittest.mock import MagicMock

    from autoclaude.execution.playbook_runner import PlaybookRunner
    from autoclaude.utils.config import AppConfig

    cfg = AppConfig()
    cfg.checkpoint_dir = str(tmp_dir / "ckpt")
    cfg.log_dir = str(tmp_dir / "logs")

    Path(cfg.checkpoint_dir).mkdir(parents=True, exist_ok=True)
    Path(cfg.log_dir).mkdir(parents=True, exist_ok=True)

    minimax = MagicMock()
    hotkey = MagicMock()

    return PlaybookRunner(
        config=cfg,
        minimax_client=minimax,
        hotkey_handler=hotkey,
        dry_run=True,
    )


def _make_workload(tmp_dir: Path):
    """B-07：真實 5-step mock playbook dry_run 負載產生器。"""
    playbook_path = _build_mock_playbook(tmp_dir)

    def _workload() -> None:
        runner = _build_runner(tmp_dir)
        result = runner.run(str(playbook_path), fresh=True)
        # 不強制 success（dry_run regex 合成可能不命中）；只確保有跑完
        assert result is not None  # noqa: S101
        assert result.total_steps == 5  # noqa: S101

    return _workload


def test_dry_run_e2e_baseline_smoke(tmp_path):
    """smoke：measure() 能跑完 20 runs 並回 PerfBaseline。

    SD_09 W2-#1：samples=20 採集（ADR-SD08-003 v1.1 §2.3）— 解 samples=7 統計噪音。
    """
    workload = _make_workload(tmp_path)
    baseline = measure("dry_run_e2e", workload, runs=20)

    assert baseline.scenario == "dry_run_e2e"
    assert baseline.samples == 20
    assert baseline.p50_ms > 0
    assert baseline.p95_ms >= baseline.p50_ms
    assert baseline.p99_ms >= baseline.p95_ms

    # SD_09 B-08：暫存供 conftest pytest_sessionfinish 寫出 perf_results.json
    _record_baseline(baseline)


def _record_baseline(baseline) -> None:
    """SD_09 B-08：注入 module-level registry，供 conftest 收集。"""
    import sys

    mod = sys.modules.get("tests.perf.conftest")
    if mod is not None and hasattr(mod, "_PERF_RESULTS"):
        mod._PERF_RESULTS.append(baseline)
