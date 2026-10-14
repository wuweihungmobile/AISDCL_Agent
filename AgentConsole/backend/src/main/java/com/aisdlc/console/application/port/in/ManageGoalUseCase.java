package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalUpdate;
import com.aisdlc.console.domain.model.goal.NewGoal;
import com.aisdlc.console.domain.model.task.Task;

import java.util.List;
import java.util.UUID;

/** 目標管理用例（PRD §5.1.2／§7.1.2）。找不到（含已軟刪除）一律 NotFoundException（404）。 */
public interface ManageGoalUseCase {

    /** 目標＋其下任務計數（只算未軟刪）。 */
    record GoalWithCounts(Goal goal, int taskCount, int completedTaskCount) {

        /** 完成比例 0.0～1.0；沒有任務時為 0.0。 */
        public double completionRatio() {
            return taskCount == 0 ? 0.0 : (double) completedTaskCount / taskCount;
        }
    }

    /** 目標詳情：目標＋計數＋任務清單（依 sortOrder）。 */
    record GoalDetailView(GoalWithCounts goal, List<Task> tasks) {
    }

    GoalWithCounts create(UUID projectId, NewGoal spec);

    List<GoalWithCounts> list(UUID projectId);

    GoalDetailView get(UUID goalId);

    GoalWithCounts update(UUID goalId, GoalUpdate update);

    void delete(UUID goalId);

    /** 依 orderedGoalIds 的順序重寫 sortOrder；必須恰好包含專案下全部（未軟刪）目標。 */
    void reorder(UUID projectId, List<UUID> orderedGoalIds);

    GoalWithCounts signoff(UUID goalId, String approver);
}
