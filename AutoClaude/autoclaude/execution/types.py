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
  - 純函式 `_evaluate_impl` / `_validate_batch_compatibility_impl` 維持簽名不變，
    供 PlaybookRunner shim 委派。

R56 修正（跨平台複審）：物理刪除兩支零呼叫端死碼 `_apply_single_mutation_impl` 與
`_prepend_global_goal_brief`。前者的現行 SSOT 是 `execution/mutation_applier/`
（`_dispatcher.py` 分派至 `_simple_mutations.py` / `_complex_mutations.py` /
`_conditional.py`，由 `playbook_runner._apply_single_mutation_full()` 進入），後者是
`plugins/goal_synthesis_plugin.GoalSynthesisPlugin.prepend_global_goal_brief()`
（SD_07 W4-T4-8 已拔除 runner shim）。刪除而非僅替換字面值的理由：死碼內留有 R52 已在
`mutation_applier/_simple_mutations.py` 修正過的 POSIX-only evaluator 兜底字面值
（`git diff --stat HEAD | grep -c .`，Windows cmd.exe 無 grep）之第二、三份未修複本，
留著等同保留「雙寫法／舊寫法復活」入口，與本 repo 反覆處理的 DEF-101-238 同一類別。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ..core.kernel_state import KernelResult
from ..execution.workflow_detector import WorkflowType
from ..models.playbook import PlaybookTask
from ..models.step_mutation import StepMutationType
from ..perception.pty_wrapper import strip_ansi

# ──────────────────────────────────────────────
# 資料結構（SD_06 W6：從 _runner_compat 搬入）
# ──────────────────────────────────────────────


# noqa 註記：刻意 str+Enum（既有 str()／format() 輸出口徑；改 StrEnum 會把
# "PlaybookState.INIT" 變成 "INIT"，屬行為變更，非跨平台議題）。比照
# execution/error_classifier.py:16 ErrorClass 的同款既有慣例。
class PlaybookState(str, Enum):  # noqa: UP042
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
    workflow: WorkflowType | str | None = None,
    step_log: list[str] | None = None,
    halt_for_token: bool = False,
    scheduled_resume_at: str | None = None,
    evolved_playbook_path: str | None = None,
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
    goto_target_idx: int | None = None
    early_return: KernelResult | None = None
    clear_goal_summary: bool = False


# ──────────────────────────────────────────────
# 純函式：突變批次相容性
# ──────────────────────────────────────────────

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


def _evaluate_impl(task: PlaybookTask, output: str) -> tuple[str | None, str, int]:
    """評估步驟輸出（ANSI strip + regex 比對）。"""
    clean = strip_ansi(output)
    if not task.expected_output_regex:
        return None, clean, 0
    if re.search(task.expected_output_regex, clean):
        return None, clean, 0
    return f"regex 不符合 {task.expected_output_regex!r}", clean, 1
