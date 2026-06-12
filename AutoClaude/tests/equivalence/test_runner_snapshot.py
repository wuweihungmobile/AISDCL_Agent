"""
Equivalence Test 基準線（SD_Improving_02.md v1.1 §0.2）。

目的：在動任何重構之前，建立 byte-level 穩定的 PlaybookRunner 行為基準。
所有 13 個 golden fixture 在 dry_run 模式下產生 11 欄 snapshot，
與 fixtures/{stem}.snapshot.json 比對。

snapshot 11 欄（v1.1 規定）：
  v1.0 既有 4 欄：
    - step_log               # PlaybookResult.step_log
    - completed_steps        # PlaybookResult.completed_steps（int → 序列化）
    - halt_for_token         # PlaybookResult.halt_for_token
    - evolved_playbook_path  # PlaybookResult.evolved_playbook_path
  v1.1 新增 7 欄（鎖死 Gap-009/012/041/042/048）：
    - mutation_log           # 步驟突變紀錄（dry_run 通常為空）
    - completed_step_ids     # Gap-041：已完成步驟 ID
    - goto_counter           # Gap-042：GOTO_STEP 計數器
    - inject_before_counter  # Gap-042：INJECT_BEFORE 計數器
    - skip_to_counter        # Gap-042：SKIP_TO 計數器
    - step_evolution_counter # Gap-048：per-step 演化次數
    - failure_history        # Gap-007-A：FailureTracker 歷史

比對方式：JSON sort_keys + ensure_ascii=False，達 byte-level deterministic。

baseline 產生：
  pytest tests/equivalence/ -v --snapshot-update     # 第一次或允許更新時
  pytest tests/equivalence/ -v                       # 之後比對
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from autoclaude.execution.playbook_runner import PlaybookRunner
from autoclaude.utils.config import AppConfig

FIXTURES_DIR = Path(__file__).parent / "fixtures"

GOLDEN_PLAYBOOKS: list[str] = [
    "01_simple_2_step.yaml",
    "02_with_correction.yaml",
    "03_with_mutation.yaml",
    "04_token_halt_resume.yaml",
    "05_evolution_inject.yaml",
    "06_goal_synthesis.yaml",
    "07_goto_step.yaml",
    "08_skip_to.yaml",
    "09_conditional.yaml",
    "10_full_e2e_dry_run.yaml",
    "11_goto_counter_token_halt.yaml",
    "12_evolution_counter_esc_f12.yaml",
    "13_max_goto_per_step_override.yaml",
]


def _make_runner(checkpoint_dir: Path):
    """回傳 (runner, checkpoint_mgr) tuple，避免測試直接存取 internal alias。"""
    from autoclaude.utils.checkpoint_manager import CheckpointManager
    cfg = AppConfig()
    cfg.checkpoint_dir = str(checkpoint_dir)
    cfg.token_guard.enabled = False  # dry_run baseline 關閉 token guard
    cfg.notification.enabled = False
    minimax = MagicMock()
    hotkey = MagicMock()
    hotkey.triggered = False
    cp_mgr = CheckpointManager(str(checkpoint_dir))
    runner = PlaybookRunner(cfg, minimax, hotkey, dry_run=True, checkpoint_mgr=cp_mgr)
    return runner, cp_mgr


def _capture_snapshot(runner: PlaybookRunner, checkpoint_mgr, playbook_path: str) -> dict[str, Any]:
    """執行 dry_run 並擷取 11 欄 snapshot。"""
    result = runner.run(playbook_path, fresh=True)

    # 從注入的 checkpoint_mgr 讀取（不再依賴 runner._checkpoint_mgr internal alias）
    cp = checkpoint_mgr.load(playbook_path)

    snapshot: dict[str, Any] = {
        # v1.0 既有 4 欄
        "step_log": list(result.step_log),
        "completed_steps": int(result.completed_steps),
        "halt_for_token": bool(result.halt_for_token),
        "evolved_playbook_path": result.evolved_playbook_path,
        # v1.1 新增 7 欄（cp 為 None 時取預設值）
        "mutation_log": [],
        "completed_step_ids": list(cp.completed_step_ids) if cp else [],
        "goto_counter": dict(cp.goto_counter) if cp else {},
        "inject_before_counter": dict(cp.inject_before_counter) if cp else {},
        "skip_to_counter": dict(cp.skip_to_counter) if cp else {},
        "step_evolution_counter": dict(cp.step_evolution_counter) if cp else {},
        "failure_history": list(cp.failure_history) if cp else [],
    }
    return snapshot


def _serialize(snapshot: dict[str, Any]) -> str:
    """deterministic JSON：sort_keys + ensure_ascii=False + indent=2。"""
    return json.dumps(snapshot, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def _snapshot_path(fixture_name: str) -> Path:
    return FIXTURES_DIR / f"{Path(fixture_name).stem}.snapshot.json"


@pytest.mark.parametrize("fixture_name", GOLDEN_PLAYBOOKS)
def test_runner_produces_stable_snapshot(
    fixture_name: str, tmp_path: Path, request
) -> None:
    """
    確保 PlaybookRunner 在 dry_run 模式下產生 byte-level 穩定的執行軌跡。

    baseline 不存在或設定 SNAPSHOT_UPDATE=1 時自動寫入。
    """
    fixture_path = str(FIXTURES_DIR / fixture_name)
    runner, cp_mgr = _make_runner(tmp_path)
    snapshot = _capture_snapshot(runner, cp_mgr, fixture_path)
    actual_json = _serialize(snapshot)

    snap_file = _snapshot_path(fixture_name)
    update = os.environ.get("SNAPSHOT_UPDATE") == "1" or not snap_file.exists()
    if update:
        snap_file.write_text(actual_json, encoding="utf-8")
        return  # baseline 寫入後 PASS

    expected_json = snap_file.read_text(encoding="utf-8")
    assert actual_json == expected_json, (
        f"行為不一致（byte-level）: {fixture_name}\n"
        f"--- expected ---\n{expected_json}\n--- actual ---\n{actual_json}"
    )


def test_snapshot_schema_has_11_fields() -> None:
    """v1.1 規定 snapshot 必須恰好 11 個欄位（4 既有 + 7 新增）。"""
    runner, cp_mgr = _make_runner(FIXTURES_DIR)
    fixture_path = str(FIXTURES_DIR / GOLDEN_PLAYBOOKS[0])
    snapshot = _capture_snapshot(runner, cp_mgr, fixture_path)
    assert len(snapshot) == 11, f"預期 11 欄，實際 {len(snapshot)} 欄: {list(snapshot.keys())}"
    expected_keys = {
        "step_log", "completed_steps", "halt_for_token", "evolved_playbook_path",
        "mutation_log", "completed_step_ids", "goto_counter",
        "inject_before_counter", "skip_to_counter", "step_evolution_counter",
        "failure_history",
    }
    assert set(snapshot.keys()) == expected_keys


def test_all_13_fixtures_exist() -> None:
    """確保 13 個 golden fixture 完整存在。"""
    for name in GOLDEN_PLAYBOOKS:
        assert (FIXTURES_DIR / name).exists(), f"缺少 fixture: {name}"
    assert len(GOLDEN_PLAYBOOKS) == 13


def test_gap_042_048_049_fixtures_present() -> None:
    """v1.1 必要修改 #1：fixture 11/12/13 對應 Gap-042/048/049。"""
    assert (FIXTURES_DIR / "11_goto_counter_token_halt.yaml").exists()      # Gap-042
    assert (FIXTURES_DIR / "12_evolution_counter_esc_f12.yaml").exists()    # Gap-048
    assert (FIXTURES_DIR / "13_max_goto_per_step_override.yaml").exists()   # Gap-049
