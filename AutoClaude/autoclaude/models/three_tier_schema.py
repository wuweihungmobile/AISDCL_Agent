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

from pydantic import BaseModel, Field, model_validator

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
    estimated_minutes: int | None = Field(default=None, ge=0)
    # W-94-1 可執行欄（攤平為 PlaybookTask 用；Optional 向後相容）
    prompt: str | None = Field(default=None, description="可執行 task prompt（無則退回 action）")
    expected_output_regex: str | None = Field(default=None, description="期望輸出 regex")
    evaluator_command: str | None = Field(default=None, description="評估指令（白名單消毒）")


class GoalTask(BaseModel):
    """中層目標任務（W3 對應 goal_tasks 表，遞迴 sub_tasks）。

    PM #1：depth ≤ 3；本 model 於 model_validator 強制檢查整棵子樹深度。
    """

    goal_task_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    # 本欄自身的上界由 `le=` 核心約束強制（pydantic v2 的 field 約束先於 field_validator
    # 執行）。此處曾另有一支 `_validate_depth_upper_bound` field_validator 重覆檢查
    # `v > MAX_GOAL_TASK_DEPTH`，但該分支在 `le=` 之後**永遠不可達**——實測 depth=4／99
    # 皆由 `le=` 攔下（"Input should be less than or equal to 3"），自訂訊息從未出現過。
    # 已移除；勿再加回。跨節點（子樹）的檢查則仍需 model_validator，見下方。
    depth: int = Field(..., ge=1, le=MAX_GOAL_TASK_DEPTH)
    priority: int = Field(default=3, ge=1, le=5)
    sub_tasks: list[GoalTask] = Field(default_factory=list)
    execution_items: list[ExecutionItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_subtree_depth(self) -> GoalTask:
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
    description: str | None = None
    goal_tasks: list[GoalTask] = Field(default_factory=list)


class ThreeTierFixture(BaseModel):
    """W0 fixture 載入入口（tests/fixtures/sample_goal_tasks.yaml）。"""

    version: str
    fixture_purpose: str | None = None
    projects: list[Project]


__all__ = [
    "MAX_GOAL_TASK_DEPTH",
    "ExecutionItem",
    "GoalTask",
    "Project",
    "ThreeTierFixture",
]
