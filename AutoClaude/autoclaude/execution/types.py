"""autoclaude.execution.types — Playbook 執行期共用資料類別與純函式。

SD_Improving_06 W6（T6-6/T6-7）：取代原 `_runner_compat.py`（物理刪除）。
SD_Improving_07 W4（T4-9~T4-15）：`PlaybookResult` dataclass 物理拔除，改 factory function。

主要變更：
  - `PlaybookResult` 為 **thin factory function**（SD_07 W4 物理拔除 dataclass），
    回傳 `KernelResult`；保持簽名相容性供下游零改動升級（既有 17 處 source +
    8 處 test 構造無需大改）。內部統一處理：
      * `workflow` Enum → str（取 .value）
      * `halt_for_token` → `halted` 映射
      * `step_log=None` → 空 list
  - `KernelResult` 新增 `halt_for_token` property alias（reflective alias of
    `halted`）作為 backward compat（測試與 main.py CLI 仍可讀取舊欄位名）；
  - `PlaybookState` / `_StepOutput` / `_MutationResult` 直接搬移（介面不變）；
  - 純函式 `_evaluate_impl` / `_validate_batch_compatibility_impl` /
    `_prepend_global_goal_brief` 維持簽名不變，供 PlaybookRunner shim 委派。

詳見 §69-79 factory function docstring（PlaybookResult 路徑說明）。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..core.kernel_state import KernelResult
from ..models.playbook import Playbook, PlaybookTask
from ..models.step_mutation import StepMutation, StepMutationType
from ..execution.workflow_detector import WorkflowType
from ..perception.pty_wrapper import strip_ansi

logger = logging.getLogger("autoclaude.execution.playbook")


# ──────────────────────────────────────────────
# 資料結構（SD_06 W6：從 _runner_compat 搬入）
# ──────────────────────────────────────────────

class PlaybookState(str, Enum):
    INIT = "INIT"
    EXECUTE = "EXECUTE"
    EVALUATE = "EVALUATE"
    CORRECTION = "CORRECTION"
    TOKEN_COMPACT = "TOKEN_COMPACT"
    TOKEN_HALT = "TOKEN_HALT"
    CONTEXT_RESET = "CONTEXT_RESET"
    ESCALATION = "ESCALATION"
    DONE = "DONE"


@dataclass
class _StepOutput:
    """_execute_prompt 回傳值（backward compat 保留）。"""
    text: str
    peak_token_pct: float = 0.0
    triggered_compact: bool = False
    triggered_halt: bool = False


def PlaybookResult(  # noqa: N802 — backward-compat factory name (class look-alike)
    success: bool,
    completed_steps: int,
    total_steps: int,
    reason: str,
    workflow: "Optional[WorkflowType | str]" = None,
    step_log: Optional[list[str]] = None,
    halt_for_token: bool = False,
    scheduled_resume_at: Optional[str] = None,
    evolved_playbook_path: Optional[str] = None,
    evolution_fresh_required: bool = False,
    **kwargs,
) -> KernelResult:
    """SD_07 W4-T4-12：PlaybookResult dataclass 物理拔除；改為 thin factory → KernelResult。

    保留**原 positional 簽名與 keyword 介面**作為過渡相容（既有 17 處 source + 8 處 test
    構造無需大改）；內部統一轉為 KernelResult SSOT：
      * `workflow` Enum → str（取 .value）
      * `halt_for_token` → `halted`
      * `step_log=None` → 空 list
    KernelResult.halt_for_token property alias 確保既有 `.halt_for_token` 讀取仍 work。

    後續路徑（SD_08 候選）：所有 caller 改 import `KernelResult`，本 factory 物理刪除。
    """
    if workflow is None:
        wf_str = ""
    elif hasattr(workflow, "value"):
        wf_str = workflow.value
    else:
        wf_str = str(workflow)
    return KernelResult(
        success=success,
        completed_steps=completed_steps,
        total_steps=total_steps,
        reason=reason,
        step_log=list(step_log or []),
        halted=halt_for_token,
        workflow=wf_str,
        scheduled_resume_at=scheduled_resume_at,
        evolved_playbook_path=evolved_playbook_path,
        evolution_fresh_required=evolution_fresh_required,
        **kwargs,
    )


@dataclass
class _MutationResult:
    """_apply_single_mutation 回傳值。

    SD_07 W4-T4-12：PlaybookResult 已物理拔除為 thin factory；`early_return` 型別
    對齊 KernelResult SSOT（factory 內部已轉換）。
    """
    should_break: bool = False
    inject_before_pending: bool = False
    goto_target_idx: Optional[int] = None
    early_return: Optional[KernelResult] = None
    clear_goal_summary: bool = False


# ──────────────────────────────────────────────
# 純函式：突變應用
# ──────────────────────────────────────────────

def _apply_single_mutation_impl(
    mutation: StepMutation,
    playbook: Playbook,
    playbook_path: str,
    task: PlaybookTask,
    step_idx: int,
    step_log: list,
    _mutation_log: list,
    attempt: int,
    _inject_before_counter: dict,
    _goto_counter: dict,
    _skip_to_counter: dict,
    workflow,
    total: int,
    tracker,
    eval_output: str,
    persist_fn=None,
) -> _MutationResult:
    result = _MutationResult()

    if mutation.mutation_type == StepMutationType.REVISE_CURRENT and mutation.revised_prompt:
        task.prompt = mutation.revised_prompt
        logger.info("REVISE_CURRENT step %s prompt updated", task.step_id)
        _mutation_log.append(f"[attempt {attempt}] REVISE_CURRENT: step {task.step_id}")
        if persist_fn:
            persist_fn(playbook, playbook_path)
        result.clear_goal_summary = True

    elif mutation.mutation_type == StepMutationType.INJECT_AFTER and mutation.new_step_prompt:
        new_task = PlaybookTask(
            step_id=mutation.new_step_id or f"{task.step_id}_INJECT",
            name=mutation.new_step_name or f"{task.name}（注入步驟）",
            prompt=mutation.new_step_prompt,
            expected_output_regex=mutation.new_step_expected_regex,
            evaluator_command=(
                mutation.new_step_evaluator_command or "git diff --stat HEAD | grep -c ."
            ),
            max_retries=mutation.new_step_max_retries,
        )
        playbook.tasks.insert(step_idx + 1, new_task)
        logger.info("INJECT_AFTER %s after %s", new_task.step_id, task.step_id)
        _mutation_log.append(f"[attempt {attempt}] INJECT_AFTER: step {new_task.step_id}")
        if persist_fn:
            persist_fn(playbook, playbook_path)

    elif mutation.mutation_type == StepMutationType.DELETE_STEP and mutation.delete_step_id:
        del_idx = next(
            (i for i, t in enumerate(playbook.tasks) if t.step_id == mutation.delete_step_id),
            None,
        )
        if del_idx is not None and del_idx > step_idx:
            del playbook.tasks[del_idx]
            step_log.append(f"[DELETED] {mutation.delete_step_id}")
            if persist_fn:
                persist_fn(playbook, playbook_path)

    elif mutation.mutation_type == StepMutationType.INJECT_BEFORE and mutation.new_step_prompt:
        cnt = _inject_before_counter.get(task.step_id, 0) + 1
        if cnt > 5:
            logger.warning("INJECT_BEFORE %s exceeded limit (%d)", task.step_id, cnt)
        else:
            _inject_before_counter[task.step_id] = cnt
            proposed_id = mutation.new_step_id or f"{task.step_id}_PRE"
            existing_ids = {t.step_id for t in playbook.tasks}
            base_prefix = proposed_id.rstrip("_0123456789").rstrip("_PRE")
            similar = [
                sid for sid in existing_ids
                if sid.startswith(base_prefix) and sid != task.step_id and "PRE" in sid
            ]
            if similar:
                proposed_id = f"{task.step_id}_PRE_{cnt}"
            pre_task = PlaybookTask(
                step_id=proposed_id,
                name=mutation.new_step_name or f"前置步驟（注入於 {task.step_id} 前）",
                prompt=mutation.new_step_prompt,
                expected_output_regex=mutation.new_step_expected_regex,
                evaluator_command=(
                    mutation.new_step_evaluator_command or "git diff --stat HEAD | grep -c ."
                ),
                max_retries=mutation.new_step_max_retries,
            )
            playbook.tasks.insert(step_idx, pre_task)
            result.inject_before_pending = True
            result.should_break = True
            if persist_fn:
                persist_fn(playbook, playbook_path)

    return result


def _validate_batch_compatibility_impl(batch: list) -> tuple[bool, str]:
    """Gap-025 / Gap-029：批次突變相容性預驗證。"""
    types = [m.mutation_type for m in batch]
    inject_before_count = types.count(StepMutationType.INJECT_BEFORE)
    inject_after_count = types.count(StepMutationType.INJECT_AFTER)
    if inject_before_count > 1:
        return False, f"批次中 INJECT_BEFORE 超過 1 次（共 {inject_before_count} 次）"
    if StepMutationType.GOTO_STEP in types and StepMutationType.INJECT_BEFORE in types:
        return False, "GOTO_STEP 與 INJECT_BEFORE 不可同時存在於批次中"
    if StepMutationType.CONDITIONAL in types:
        return False, "CONDITIONAL 突變不支援批次模式"
    if inject_before_count >= 1 and inject_after_count >= 1:
        return False, "INJECT_BEFORE 與 INJECT_AFTER 不可同時存在於批次中（插入位置語意衝突）"
    return True, ""


# ──────────────────────────────────────────────
# 純函式：目標相關（backward compat）
# ──────────────────────────────────────────────

def _prepend_global_goal_brief(prompt: str, global_goal: Optional[str], cfg=None) -> str:
    """Gap-015-A：精簡版 global_goal 前置（最大 global_goal_brief_chars 字元）。"""
    if not global_goal:
        return prompt
    brief_chars = 100
    if cfg is not None:
        brief_chars = getattr(getattr(cfg, "playbook", cfg), "global_goal_brief_chars", brief_chars)
    brief = global_goal[:brief_chars] + ("…" if len(global_goal) > brief_chars else "")
    return f"[總目標方向] {brief}\n\n{prompt}"


def _evaluate_impl(task: PlaybookTask, output: str) -> tuple[Optional[str], str, int]:
    """評估步驟輸出（ANSI strip + regex 比對）。"""
    clean = strip_ansi(output)
    if not task.expected_output_regex:
        return None, clean, 0
    if re.search(task.expected_output_regex, clean):
        return None, clean, 0
    return f"regex 不符合 {task.expected_output_regex!r}", clean, 1
