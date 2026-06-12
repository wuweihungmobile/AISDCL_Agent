"""SD_Improving_06 W0-T0-5 配套契約測試：三層 schema Pydantic 雛形

W0 範圍（僅雛形驗證，不含 PG）：
    1. Pydantic 模型可載入 tests/fixtures/sample_goal_tasks.yaml
    2. 10 projects + 深度分布 1×4 / 2×4 / 3×2（與 T0-4 對齊）
    3. depth=4 必須 raise ValidationError（PM #1 上限 ≤ 3）
    4. 整棵子樹任一節點 depth > 3 → reject

W3 階段 tests/contract/test_three_tier_schema.py（≥ 12 case，AC3-1~AC3-5）
為完整 PG schema 契約測試；本檔僅鎖 W0 雛形。
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from autoclaude.models.three_tier_schema import (
    MAX_GOAL_TASK_DEPTH,
    GoalTask,
    Project,
    ThreeTierFixture,
)

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "sample_goal_tasks.yaml"


@pytest.fixture(scope="module")
def fixture_data() -> dict:
    return yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))


class TestThreeTierFixtureLoading:
    def test_fixture_loads_into_pydantic_model(self, fixture_data: dict) -> None:
        """sample_goal_tasks.yaml 可完整載入 ThreeTierFixture。"""
        model = ThreeTierFixture.model_validate(fixture_data)
        assert len(model.projects) == 10

    def test_depth_distribution_matches_pm_1(self, fixture_data: dict) -> None:
        """PM #1：深度分布 1×4 / 2×4 / 3×2（共 10 projects 頂層 goal_task）。"""
        model = ThreeTierFixture.model_validate(fixture_data)
        top_depths = [
            gt.depth for proj in model.projects for gt in proj.goal_tasks
        ]
        counts = {1: 0, 2: 0, 3: 0}
        for d in top_depths:
            counts[d] += 1
        assert counts == {1: 4, 2: 4, 3: 2}, f"depth 分布偏移：{counts}"

    def test_no_subtree_exceeds_max_depth(self, fixture_data: dict) -> None:
        """整棵子樹任一節點 depth ≤ MAX_GOAL_TASK_DEPTH。"""
        model = ThreeTierFixture.model_validate(fixture_data)

        def walk(gt: GoalTask) -> None:
            assert gt.depth <= MAX_GOAL_TASK_DEPTH
            for child in gt.sub_tasks:
                walk(child)

        for proj in model.projects:
            for gt in proj.goal_tasks:
                walk(gt)


class TestDepthInvariants:
    def test_depth_4_rejected(self) -> None:
        """PM #1 紅線：depth=4 直接 raise。"""
        with pytest.raises(ValidationError):
            GoalTask(goal_task_id="GT-BAD", title="x", depth=4)

    def test_depth_0_rejected(self) -> None:
        """depth 必須 ≥ 1。"""
        with pytest.raises(ValidationError):
            GoalTask(goal_task_id="GT-BAD", title="x", depth=0)

    def test_project_with_empty_goal_tasks_ok(self) -> None:
        """Project 允許空 goal_tasks（W4 初始 import 階段）。"""
        proj = Project(project_id="PRJ-EMPTY", name="empty")
        assert proj.goal_tasks == []
