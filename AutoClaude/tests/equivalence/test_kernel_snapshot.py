"""Stage A Kernel 等價測試（SD_03 §2.4）。

目的：以「真實 Kernel + DryRunExecutor + ShellEvaluator」跑 13 個 golden fixture，
驗證 semantic-level 快照與 snapshots_kernel/ 下的基準一致。

Semantic-level 比對規則（SD_03 §2.4）：
  - completed_steps 完全一致
  - completed_step_ids 集合相同（order-insensitive）
  - step_log 行數一致
  - 每行可由共通 regex `^\\[\\w+\\] [\\w_-]+.*(attempt[  =]\\d+|\\[FAIL\\])` 解析
  - step_id 集合相同

更新快照：
  pytest tests/equivalence/test_kernel_snapshot.py --snapshot-update
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

from autoclaude.core.kernel import PlaybookKernel
from autoclaude.core.kernel_state import KernelResult
from autoclaude.infra.adapters.dry_run_executor import DryRunExecutor
from autoclaude.infra.adapters.shell_evaluator import ShellEvaluator
from autoclaude.models.playbook import Playbook
from autoclaude.utils.config import PlaybookConfig

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SNAPSHOTS_DIR = Path(__file__).parent / "snapshots_kernel"

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

_STEP_LOG_PATTERN = re.compile(
    r"^\[[\w_-]+\] .+(attempt[ =]\d+|\[FAIL\])"
)


def _build_executor_from_playbook(playbook_data: dict) -> DryRunExecutor:
    """依 yaml 中每個 task 的 expected_output_regex 建立 DryRunExecutor。"""
    step_outputs: dict[str, str] = {}
    for task in playbook_data.get("tasks", []):
        step_id = task.get("step_id", "")
        regex = task.get("expected_output_regex")
        step_outputs[step_id] = DryRunExecutor.keyword_from_regex(regex)
    return DryRunExecutor(step_outputs)


def _run_kernel(yaml_path: Path) -> KernelResult:
    """用 DryRunExecutor + 最簡 Kernel（無 Plugin）跑 fixture。"""
    with open(yaml_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    executor = _build_executor_from_playbook(raw)
    evaluator = ShellEvaluator(PlaybookConfig())

    kernel = PlaybookKernel(executor=executor, evaluator=evaluator)
    playbook = Playbook.model_validate(raw)
    return kernel.run(playbook)


def _capture_semantic_snapshot(result: KernelResult) -> dict[str, Any]:
    """擷取 Stage A semantic-level 欄位。"""
    return {
        "completed_steps": result.completed_steps,
        "total_steps": result.total_steps,
        "completed_step_ids": sorted(result.completed_step_ids),
        "step_log_count": len(result.step_log),
        "step_log": result.step_log,
        "halted": result.halted,
        "escalated": result.escalated,
        "success": result.success,
    }


def _assert_semantic(actual: dict[str, Any], expected: dict[str, Any], stem: str) -> None:
    """Semantic-level 比對：欄位一致 + step_log 每行符合 pattern。"""
    assert actual["completed_steps"] == expected["completed_steps"], \
        f"{stem}: completed_steps {actual['completed_steps']} != {expected['completed_steps']}"
    assert actual["step_log_count"] == expected["step_log_count"], \
        f"{stem}: step_log_count {actual['step_log_count']} != {expected['step_log_count']}"
    assert set(actual["completed_step_ids"]) == set(expected["completed_step_ids"]), \
        f"{stem}: completed_step_ids mismatch"
    assert actual["success"] == expected["success"], f"{stem}: success mismatch"
    for line in actual["step_log"]:
        assert _STEP_LOG_PATTERN.match(line), \
            f"{stem}: step_log line does not match pattern: {line!r}"


@pytest.mark.parametrize("playbook_file", GOLDEN_PLAYBOOKS)
def test_kernel_snapshot(playbook_file: str, request):
    yaml_path = FIXTURES_DIR / playbook_file
    stem = Path(playbook_file).stem
    snapshot_path = SNAPSHOTS_DIR / f"{stem}.snapshot.json"

    result = _run_kernel(yaml_path)
    actual = _capture_semantic_snapshot(result)

    update = request.config.getoption("--snapshot-update", default=False)

    if update or not snapshot_path.exists():
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(actual, f, ensure_ascii=False, sort_keys=True, indent=2)
        return

    with open(snapshot_path, encoding="utf-8") as f:
        expected = json.load(f)

    _assert_semantic(actual, expected, stem)
