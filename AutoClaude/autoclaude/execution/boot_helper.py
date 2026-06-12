"""boot_helper.py — Playbook 載入 / checkpoint 恢復 / workflow 偵測等 boot 階段邏輯。

對應：
  - SD_Improving_06.md v1.2 §4 W2（god-class 拆解）
  - SD06_Execution_Guide.md W2 mixin 進一步下沉

設計原則：
  - 從 _runner_internals.py 抽出 boot 階段 5 個方法（_resolve_start / _wait_for_scheduled_resume
    / _load_playbook / _detect_workflow / _validate_evaluator_commands）
  - 純委派函式（runner: PlaybookRunner 作為第一參數）
  - 不依賴 plugin 內部，僅透過 runner.* 訪問既有屬性
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import yaml

from ..models.playbook import Playbook
from ..utils.checkpoint_manager import CheckpointManager, PlaybookCheckpoint
from .workflow_detector import WorkflowType

if TYPE_CHECKING:
    from .playbook_runner import PlaybookRunner

logger = logging.getLogger("autoclaude.execution.playbook")


def resolve_start_impl(
    runner: "PlaybookRunner", playbook_path: str, fresh: bool, playbook: Playbook,
) -> tuple[int, list[str], bool, Optional[PlaybookCheckpoint]]:
    """SD_06 W2：_resolve_start 下沉。"""
    if fresh:
        return 0, [], True, None
    cp = runner._checkpoint_mgr.load(playbook_path)
    if cp is None:
        return 0, [], True, None

    if cp.step_idx >= len(playbook.tasks):
        logger.warning(
            "Checkpoint step_idx=%d 超出 Playbook 步驟數 %d，Playbook 已修改，從頭執行。",
            cp.step_idx, len(playbook.tasks),
        )
        runner._checkpoint_mgr.clear(playbook_path)
        return 0, [], True, None

    actual_id = playbook.tasks[cp.step_idx].step_id
    if actual_id != cp.step_id:
        logger.warning(
            "Checkpoint step_id 不一致（期望 %s，實際 %s），Playbook 已修改，從頭執行。",
            cp.step_id, actual_id,
        )
        runner._checkpoint_mgr.clear(playbook_path)
        return 0, [], True, None

    logger.info("從檢查點繼續 | step %d [%s]", cp.step_idx + 1, cp.step_id)
    return cp.step_idx, cp.completed_step_log, True, cp


def wait_for_scheduled_resume_impl(
    runner: "PlaybookRunner", playbook_path: str, resume_count: int,
) -> float:
    """SD_06 W2：_wait_for_scheduled_resume 下沉。"""
    cp = runner._checkpoint_mgr.load(playbook_path)
    if cp is None:
        return 0.0
    secs = CheckpointManager.seconds_until_resume(cp)
    if secs > 0:
        runner._notify(
            f"AutoClaude — 排程中 (第 {resume_count} 次恢復)",
            f"等待 {secs / 60:.1f} 分鐘後繼續執行…",
        )
    return secs


def load_playbook_impl(path: str) -> Playbook:
    """SD_06 W2：_load_playbook 下沉（純函式，無 runner 依賴）。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Playbook 不存在: {path}")
    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Playbook.model_validate(raw)


def detect_workflow_impl(
    runner: "PlaybookRunner", playbook: Playbook,
) -> WorkflowType:
    """SD_06 W2：_detect_workflow 下沉。"""
    if playbook.workflow_type != "auto":
        try:
            return WorkflowType(playbook.workflow_type)
        except ValueError:
            logger.warning("未知的 workflow_type: %s", playbook.workflow_type)
            return WorkflowType.UNKNOWN

    if playbook.workflow_path:
        return runner._detector.detect(playbook.workflow_path)

    search_paths = list(runner._cfg.workflow_search_paths) + [str(Path.cwd())]
    for p in search_paths:
        wt = runner._detector.detect(p)
        if wt != WorkflowType.UNKNOWN:
            return wt
    return WorkflowType.UNKNOWN


def validate_evaluator_commands_impl(playbook: Playbook) -> None:
    """SD_06 W2：_validate_evaluator_commands 下沉（純函式，但需 shutil patch path）。"""
    from .playbook_runner import _pr
    for task in playbook.tasks:
        if not task.evaluator_command:
            continue
        binary = task.evaluator_command.strip().split()[0]
        if not _pr().shutil.which(binary):
            logger.warning(
                "=== Gap-009-D | [%s] evaluator_command '%s' 不在 PATH 中，"
                "step 執行時可能立即 ESCALATION。===",
                task.step_id, binary,
            )
