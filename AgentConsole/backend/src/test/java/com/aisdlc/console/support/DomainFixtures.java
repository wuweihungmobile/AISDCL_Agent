package com.aisdlc.console.support;

import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.domain.service.ExecutionPlanner.GoalWithTasks;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** 純領域層測試用的建構小幫手（不經資料庫）：專案、目標、任務一律已 signoff、未刪除。 */
public final class DomainFixtures {

    public static final Instant T0 = Instant.parse("2026-10-15T08:00:00Z");

    private DomainFixtures() {
    }

    public static Project project(String name) {
        return Project.restore(UUID.randomUUID(), name, "/work/" + name, "全部完成", "說明", ProjectStatus.DRAFT, 3,
                true, null, null, false, T0, T0, "tester", null, null);
    }

    public static Goal goal(UUID projectId, String name, int sortOrder, UUID... dependsOn) {
        return goal(projectId, name, sortOrder, GoalStatus.PENDING, dependsOn);
    }

    public static Goal goal(UUID projectId, String name, int sortOrder, GoalStatus status, UUID... dependsOn) {
        return Goal.restore(UUID.randomUUID(), projectId, name, "", "完成 " + name, sortOrder, status,
                List.of(dependsOn), true, null, null, false, T0.plusSeconds(sortOrder), T0, null);
    }

    public static Task task(UUID goalId, String name, int sortOrder) {
        return task(goalId, name, sortOrder, TaskStatus.PENDING);
    }

    public static Task task(UUID goalId, String name, int sortOrder, TaskStatus status) {
        return Task.restore(UUID.randomUUID(), goalId, name, "請輸出 [" + name + "_DONE]", "輸出含 [" + name + "_DONE]",
                null, "\\[" + name + "_DONE\\]", null, sortOrder, status, null, null, 0, 1, null, null, true, null,
                null, false, T0.plusSeconds(sortOrder), T0, null, null, null);
    }

    public static Task taskWith(UUID goalId, String name, int sortOrder, String description, String evaluator,
                                String regex, int maxRetries, Long estimatedTokens) {
        return Task.restore(UUID.randomUUID(), goalId, name, description, "通過", evaluator, regex, null, sortOrder,
                TaskStatus.PENDING, estimatedTokens, null, 0, maxRetries, null, null, true, null, null, false,
                T0.plusSeconds(sortOrder), T0, null, null, null);
    }

    public static GoalWithTasks with(Goal goal, Task... tasks) {
        return new GoalWithTasks(goal, List.of(tasks));
    }
}
