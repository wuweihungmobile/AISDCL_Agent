package com.aisdlc.console.adapter.in.web.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;
import java.util.UUID;

/** 調整目標順序（PRD §7.1.2）：orderedGoalIds 必須恰好是專案下全部（未刪除）目標，依新順序排列。 */
public record ReorderRequest(
        @NotNull(message = "projectId 不能為空") UUID projectId,
        @NotNull(message = "orderedGoalIds 不能為空")
        @Schema(description = "新的目標順序（第 0 個＝sortOrder 0）") List<@NotNull(message = "目標 id 不可為空") UUID> orderedGoalIds) {
}
