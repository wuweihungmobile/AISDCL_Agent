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
                true, null, null, false, T0, T0, "tester", null, null, null, null, null);
    }

    /** 帶 SDD 綁定三欄的專案（契約 §0.5 V12；null＝尚未綁定），其餘同 {@link #project(String)}。 */
    public static Project boundProject(String name, String executionPath, String sddProject, String sddSpecDir,
                                       String sddSpecFile) {
        return Project.restore(UUID.randomUUID(), name, executionPath, "全部完成", "說明", ProjectStatus.DRAFT, 3,
                true, null, null, false, T0, T0, "tester", null, null, sddProject, sddSpecDir, sddSpecFile);
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

    /** 路徑 A（規格驅動）產生的任務：{@code passCriteriaSpec} 是 JSON 文字（可為 null），簽核人承襲匯入記錄；maxRetries＝5（SCG-4 型）。 */
    public static Task sddTask(UUID goalId, String name, int sortOrder, String passCriteriaSpecJson, String signedOffBy) {
        return Task.restore(UUID.randomUUID(), goalId, name, "請輸出 [" + name + "_DONE]", "輸出含 [" + name + "_DONE]",
                null, "\\[" + name + "_DONE\\]", passCriteriaSpecJson, sortOrder, TaskStatus.PENDING, null, null, 0, 5,
                null, null, true, signedOffBy, null, false, T0.plusSeconds(sortOrder), T0, null, null, null);
    }

    /** {@code {source:"sdd", stepId, specDigest, weakRegex:false}} 的 JSON 文字（路徑 A 的 {@code passCriteriaSpec} 形狀）。 */
    public static String sddSpec(String stepId, String specDigest) {
        return "{\"source\":\"sdd\",\"specDigest\":\"" + specDigest + "\",\"stepId\":\"" + stepId + "\",\"weakRegex\":false}";
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
