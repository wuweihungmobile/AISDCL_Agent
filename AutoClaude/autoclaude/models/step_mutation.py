"""
StepMutation — Minimax 步驟動態修正資料模型（Gap-011-B / Gap-012-A~C / Gap-017 / Gap-019）。
當步驟反覆失敗且收斂趨勢為 stuck/oscillating/cycling 時，
Minimax 可提議修改步驟設計本身（而非僅產生 correction_prompt）。
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class StepMutationType(str, Enum):
    REVISE_CURRENT = "REVISE_CURRENT"   # 修改當前步驟 prompt 定義
    INJECT_AFTER = "INJECT_AFTER"       # 在當前步驟後插入新的輔助步驟
    INJECT_BEFORE = "INJECT_BEFORE"     # Gap-012-A：在當前步驟前注入前置步驟並立即執行
    GOTO_STEP = "GOTO_STEP"             # Gap-012-B：跳回指定步驟重新執行（含無限迴圈防護）
    DELETE_STEP = "DELETE_STEP"         # Gap-012-C：刪除後續已確定冗餘的步驟
    SKIP_TO = "SKIP_TO"                 # Gap-017：向前跳轉至指定步驟（跳過中間冗餘步驟）
    CONDITIONAL = "CONDITIONAL"         # Gap-021：條件式分支突變（依 shell exit code 選擇分支）


class StepMutation(BaseModel):
    mutation_type: StepMutationType
    revised_prompt: Optional[str] = None    # REVISE_CURRENT 時填寫：新的步驟 prompt（完整替換）
    new_step_id: Optional[str] = None       # INJECT_AFTER / INJECT_BEFORE 時填寫
    new_step_name: Optional[str] = None     # INJECT_AFTER / INJECT_BEFORE 時填寫
    new_step_prompt: Optional[str] = None   # INJECT_AFTER / INJECT_BEFORE 時填寫
    goto_step_id: Optional[str] = None      # Gap-012-B：GOTO_STEP 目標步驟 step_id
    delete_step_id: Optional[str] = None    # Gap-012-C：DELETE_STEP 要刪除的步驟 step_id
    skip_to_step_id: Optional[str] = None   # Gap-017：SKIP_TO 目標步驟 step_id（必須在當前步驟之後）
    skip_reason: Optional[str] = None       # Gap-017：被跳過步驟的說明（記錄至 step_log）
    reasoning: str = ""
    batch_mutations: Optional[list["StepMutation"]] = None  # Gap-019：批次突變清單（最多 3 個）
    # Gap-021：CONDITIONAL 欄位
    condition_evaluator: Optional[str] = None        # shell 指令，exit 0 = 條件成立
    true_mutation: Optional["StepMutation"] = None   # 條件成立時執行的突變
    false_mutation: Optional["StepMutation"] = None  # 條件不成立時執行的突變
    # Gap-036：INJECT_BEFORE / INJECT_AFTER 注入步驟評估欄位（防假陽性通過）
    new_step_evaluator_command: Optional[str] = None  # 注入步驟的 shell 評估指令
    new_step_expected_regex: Optional[str] = None     # 注入步驟的輸出 regex
    new_step_max_retries: Optional[int] = None        # 注入步驟的重試上限


StepMutation.model_rebuild()  # Gap-019/Gap-021：解析自參照遞迴型別
