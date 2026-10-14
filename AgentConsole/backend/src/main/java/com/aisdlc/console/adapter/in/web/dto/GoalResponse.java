package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ManageGoalUseCase.GoalWithCounts;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/** 建立／更新／signoff 後的目標回應（Architecture §11.2 的 R 欄）。 */
public record GoalResponse(
        @NotNull UUID id,
        @NotNull UUID projectId,
        @NotNull String name,
        String description,
        @NotNull String passCriteria,
        @NotNull int sortOrder,
        @NotNull GoalStatus status,
        @NotNull boolean signedOff,
        String signedOffBy,
        Instant signedOffAt,
        @NotNull Instant createdAt,
        @NotNull Instant updatedAt) {

    public static GoalResponse from(GoalWithCounts view) {
        Goal g = view.goal();
        return new GoalResponse(g.id(), g.projectId(), g.name(), g.description(), g.passCriteria(), g.sortOrder(),
                g.status(), g.signedOff(), g.signedOffBy(), g.signedOffAt(), g.createdAt(), g.updatedAt());
    }
}
