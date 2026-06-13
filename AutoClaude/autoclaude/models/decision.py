from __future__ import annotations
from typing import Optional
from pydantic import BaseModel

from .step_mutation import StepMutation


class CorrectionDecision(BaseModel):
    """Minimax 針對 Playbook 步驟失敗回傳的修正 Prompt。"""
    correction_prompt: str
    reasoning: str = ""
    task_goal_summary: Optional[str] = None  # Gap-010-B: 任務目標摘要（30 字以內），首次 correction 時由 Minimax 生成
    step_mutation: Optional[StepMutation] = None  # Gap-011-B: 步驟動態修正（選填）


class GoalAchievementDecision(BaseModel):
    """Gap-014: Minimax 針對 global_goal 全局達成的驗證決策。"""
    is_achieved: bool
    completion_prompt: str = ""   # 未達成時，補完步驟的 prompt（空字串表示達成）
    gap_analysis: str = ""        # 未達成時，分析缺口說明（供 logging）
    suggested_evaluator: Optional[str] = None  # Gap-030：建議的 GOAL_SYNTHESIS 驗證指令


class EvolutionDecision(BaseModel):
    """Gap-016: Minimax 針對 ESCALATION 失敗提議的 Playbook 演化策略。"""
    evolution_type: str           # "INJECT_STEP" | "SPLIT_STEP" | "REVISE_EVALUATOR"
    reasoning: str = ""
    new_step_id: Optional[str] = None
    new_step_name: Optional[str] = None
    new_step_prompt: Optional[str] = None   # INJECT_STEP 使用
    split_context_bridge: str = ""           # SPLIT_STEP 使用：Part B 的 context 前置摘要
    revised_evaluator: Optional[str] = None  # REVISE_EVALUATOR 使用


class DecompositionStep(BaseModel):
    """F-A1 / ADR-AGT-002：Brain 拆解出的單一步驟節點（DAG node）。"""
    step_id: str
    name: str
    prompt: str
    depends_on: list[str] = []               # DAG edges：本步驟相依之前序 step_id
    evaluator_command: Optional[str] = None  # 選填，對齊 PlaybookTask.evaluator_command


class DecompositionDecision(BaseModel):
    """F-A1 / ADR-AGT-002：Brain 對高階 goal 的一次性拆解候選 DAG。

    本地有界性驗證（≤24 步 / 無環 / 非空 prompt）由 GoalDecomposer 負責，
    本模型僅承載 Brain 候選輸出，不做業務判定。
    """
    steps: list[DecompositionStep] = []
    reasoning: str = ""
