package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ManageGoalUseCase.GoalWithCounts;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import jakarta.validation.constraints.NotNull;

import java.util.UUID;

/** 專案詳情內的目標摘要（US-P-06：每個目標標題旁顯示任務數量）。 */
public record GoalBrief(
        @NotNull UUID id,
        @NotNull String name,
        @NotNull GoalStatus status,
        @NotNull int sortOrder,
        @NotNull boolean signedOff,
        @NotNull int taskCount,
        @NotNull int completedTaskCount) {

    public static GoalBrief from(GoalWithCounts view) {
        Goal g = view.goal();
        return new GoalBrief(g.id(), g.name(), g.status(), g.sortOrder(), g.signedOff(), view.taskCount(),
                view.completedTaskCount());
    }
}
