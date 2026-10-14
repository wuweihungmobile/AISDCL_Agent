package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ManageGoalUseCase.GoalDetailView;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** 目標詳情（Architecture §11.2 的 D 欄）：全部欄位＋依賴＋任務標題清單。 */
public record GoalDetailResponse(
        @NotNull UUID id,
        @NotNull UUID projectId,
        @NotNull String name,
        String description,
        @NotNull String passCriteria,
        @NotNull int sortOrder,
        @NotNull GoalStatus status,
        @NotNull List<UUID> dependsOn,
        @NotNull boolean signedOff,
        String signedOffBy,
        Instant signedOffAt,
        @NotNull int taskCount,
        @NotNull int completedTaskCount,
        @NotNull double completionRatio,
        @NotNull List<TaskBrief> tasks,
        @NotNull Instant createdAt,
        @NotNull Instant updatedAt) {

    public static GoalDetailResponse from(GoalDetailView view) {
        Goal g = view.goal().goal();
        return new GoalDetailResponse(g.id(), g.projectId(), g.name(), g.description(), g.passCriteria(),
                g.sortOrder(), g.status(), List.copyOf(g.dependsOn()), g.signedOff(), g.signedOffBy(),
                g.signedOffAt(), view.goal().taskCount(), view.goal().completedTaskCount(),
                view.goal().completionRatio(), view.tasks().stream().map(TaskBrief::from).toList(), g.createdAt(),
                g.updatedAt());
    }
}
