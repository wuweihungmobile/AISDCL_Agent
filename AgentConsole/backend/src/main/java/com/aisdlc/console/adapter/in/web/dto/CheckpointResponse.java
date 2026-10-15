package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.CheckpointView;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/**
 * 可用斷點（契約 §1.2.9）：Bridge 於每個步驟完成時自行記錄歷史快照（append-only，命名 {@code after-<step_id>}）。
 * {@code stepIdx}／{@code stepId} 取自快照內的 {@code step_idx}／{@code step_id}＝<b>還原後下一個要跑的步驟</b>；不含 stateSnapshot 本體。
 */
@Schema(name = "CheckpointResponse")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record CheckpointResponse(
        @NotNull UUID id,
        @NotNull UUID runId,
        @NotNull @Schema(description = "Bridge 命名「after-<step_id>」") String name,
        @NotNull Instant createdAt,
        @JsonProperty("isAutomatic") @Schema(name = "isAutomatic") @NotNull boolean isAutomatic,
        @Schema(description = "還原後下一個要跑的步驟位置（0 起算；＝快照的 step_idx）") Integer stepIdx,
        @Schema(description = "還原後下一個要跑的步驟 step_id；已跑完時為空字串") String stepId,
        @Schema(description = "快照內已完成步驟數") Integer completedSteps) {

    public static CheckpointResponse from(CheckpointView v) {
        return new CheckpointResponse(v.id(), v.runId(), v.name(), v.createdAt(), v.automatic(), v.stepIdx(),
                v.stepId(), v.completedSteps());
    }
}
