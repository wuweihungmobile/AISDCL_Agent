package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunSummaryView;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/** 批次列表的一列（契約 §1.2.2；含 US-M-06 批次比較所需的 Token／時間／成功率）。 */
@Schema(name = "ExecutionRunSummaryResponse", description = "批次列表（含 US-M-06 批次比較所需欄位）")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ExecutionRunSummaryResponse(
        @NotNull UUID id,
        @NotNull UUID projectId,
        @NotNull int runNumber,
        @NotNull RunStatus status,
        @NotNull int autonomyLevel,
        @NotNull @Schema(allowableValues = {"ALL", "SELECTED"}) String scopeMode,
        @NotNull long totalTokensUsed,
        Long tokenBudget,
        @NotNull Instant startedAt,
        Instant completedAt,
        @Schema(description = "已完成批次＝completedAt−startedAt；進行中＝現在−startedAt") Long durationSec,
        @NotNull @Schema(description = "範圍內任務數（取自凍結的 dag）") int tasksTotal,
        @NotNull @Schema(description = "該批次內有 COMPLETED 步驟列的相異任務數") int tasksCompleted,
        @NotNull @Schema(description = "該批次內有 FAILED 步驟列的相異任務數") int tasksFailed,
        @JsonInclude(JsonInclude.Include.ALWAYS)
        @Schema(nullable = true, description = "tasksCompleted÷(tasksCompleted＋tasksFailed)×100（小數 1 位）；兩者皆 0 為 null")
        Double successRate) {

    public static ExecutionRunSummaryResponse from(RunSummaryView v) {
        return new ExecutionRunSummaryResponse(v.id(), v.projectId(), v.runNumber(), v.status(), v.autonomyLevel(),
                v.scopeMode(), v.totalTokensUsed(), v.tokenBudget(), v.startedAt(), v.completedAt(), v.durationSec(),
                v.tasksTotal(), v.tasksCompleted(), v.tasksFailed(), v.successRate());
    }
}
