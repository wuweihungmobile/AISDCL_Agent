"""SD_Improving_06 W0-T0-5：三層任務模型 Pydantic 雛形

對應規格：
    [SD_Improving_06.md](../../docs/04_planning/SD_Improving_06.md) §6.5 AC3-1 ~ AC3-5
    PM 拍板 #1：sub-task 深度上限 ≤ 3

W0 雛形範圍（只做 Pydantic 模型 + 不變式驗證）：
    - W3 alembic 0009_three_tier_schema：對應 PG 三表 schema
    - W4 tools/migrate_yaml_to_db.py：YAML → 本模型 → DB 入庫
    - 紅線：sub_tasks 巢狀深度不可 > 3（W4 import 工具必須拒絕）

三層結構：
    Project (頂層)
      └── GoalTask (中層，可巢狀 sub_tasks，depth ≤ 3)
            └── ExecutionItem (底層原子單元)
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# PM #1：sub-task 深度上限（W4 import 工具拒絕邊界）
MAX_GOAL_TASK_DEPTH: int = 3


class ExecutionItem(BaseModel):
    """底層原子執行單元（W3 對應 execution_items 表）。

    AutoSDD_improving_94 W-94-1：新增三個 optional「可執行欄」，使底層單元裝得下一個
    可被 AutoClaude runner 執行的 task 規格（原本只有 action 描述、攤不出可執行 playbook）。
    tools/three_tier_to_playbook.py 攤平時：prompt→PlaybookTask.prompt（無則退回 action）、
    expected_output_regex→同名欄、evaluator_command→經白名單消毒後填入。三欄皆 Optional
    預設 None → 既有 sample_goal_tasks.yaml / migrate_yaml_to_db 既有資料向後相容。
    """

    exec_id: str = Field(..., min_length=1, description="唯一 ID（W3 PK）")
    action: str = Field(..., min_length=1, description="動作描述")
    status: str = Field(default="pending", description="pending / ok / failed")
    estimated_minutes: Optional[int] = Field(default=None, ge=0)
    # W-94-1 可執行欄（攤平為 PlaybookTask 用；Optional 向後相容）
    prompt: Optional[str] = Field(default=None, description="可執行 task prompt（無則退回 action）")
    expected_output_regex: Optional[str] = Field(default=None, description="期望輸出 regex")
    evaluator_command: Optional[str] = Field(default=None, description="評估指令（白名單消毒）")


class GoalTask(BaseModel):
    """中層目標任務（W3 對應 goal_tasks 表，遞迴 sub_tasks）。

    PM #1：depth ≤ 3；本 model 於 model_validator 強制檢查整棵子樹深度。
    """

    goal_task_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    depth: int = Field(..., ge=1, le=MAX_GOAL_TASK_DEPTH)
    priority: int = Field(default=3, ge=1, le=5)
    sub_tasks: List["GoalTask"] = Field(default_factory=list)
    execution_items: List[ExecutionItem] = Field(default_factory=list)

    @field_validator("depth")
    @classmethod
    def _validate_depth_upper_bound(cls, v: int) -> int:
        if v > MAX_GOAL_TASK_DEPTH:
            raise ValueError(
                f"goal_task depth={v} 超過 PM #1 上限 {MAX_GOAL_TASK_DEPTH}"
            )
        return v

    @model_validator(mode="after")
    def _validate_subtree_depth(self) -> "GoalTask":
        """整棵子樹任一節點不得 > MAX_GOAL_TASK_DEPTH。"""
        for child in self.sub_tasks:
            if child.depth > MAX_GOAL_TASK_DEPTH:
                raise ValueError(
                    f"sub_task {child.goal_task_id} depth={child.depth} > "
                    f"上限 {MAX_GOAL_TASK_DEPTH}"
                )
        return self


# Pydantic v2 self-reference 解析
GoalTask.model_rebuild()


class Project(BaseModel):
    """頂層專案（W3 對應 projects 表）。"""

    project_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    goal_tasks: List[GoalTask] = Field(default_factory=list)


class ThreeTierFixture(BaseModel):
    """W0 fixture 載入入口（tests/fixtures/sample_goal_tasks.yaml）。"""

    version: str
    fixture_purpose: Optional[str] = None
    projects: List[Project]


__all__ = [
    "MAX_GOAL_TASK_DEPTH",
    "ExecutionItem",
    "GoalTask",
    "Project",
    "ThreeTierFixture",
]
