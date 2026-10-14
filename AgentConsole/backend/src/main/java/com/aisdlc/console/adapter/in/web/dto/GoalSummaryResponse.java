package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ManageGoalUseCase.GoalWithCounts;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import jakarta.validation.constraints.NotNull;

import java.util.UUID;

/** 目標列表的一列（US-G-02）：名稱、狀態、任務數量與完成比例（任務計數只算未軟刪）。 */
public record GoalSummaryResponse(
        @NotNull UUID id,
        @NotNull UUID projectId,
        @NotNull String name,
        @NotNull int sortOrder,
        @NotNull GoalStatus status,
        @NotNull boolean signedOff,
        @NotNull int taskCount,
        @NotNull int completedTaskCount,
        @NotNull double completionRatio) {

    public static GoalSummaryResponse from(GoalWithCounts view) {
        Goal g = view.goal();
        return new GoalSummaryResponse(g.id(), g.projectId(), g.name(), g.sortOrder(), g.status(), g.signedOff(),
                view.taskCount(), view.completedTaskCount(), view.completionRatio());
    }
}
