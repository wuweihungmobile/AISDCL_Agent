package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.CurrentStepView;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.UUID;

/**
 * 目前執行中的步驟（契約 §1.2.3）。{@code stepNumber} 是該步驟在批次 playbook 內的位置（1 起算，Bridge 的
 * {@code current_step_number}），與 {@code ExecutionStepResponse.stepNumber}（事件 seq）不同義（契約 §0.6）。
 */
@Schema(name = "CurrentStep")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record CurrentStepDto(
        @NotNull @Schema(description = "playbook step_id（例：G1-T2）") String stepId,
        @NotNull @Schema(description = "該步驟在 playbook 內的位置（1 起算，Bridge 的 current_step_number）；"
                + "與 ExecutionStepResponse.stepNumber（事件 seq）不同義，見 Markdown 契約 §0.6") int stepNumber,
        UUID taskId,
        @NotNull String taskName,
        UUID goalId,
        @NotNull @Schema(description = "第幾次嘗試（1＝首次；RETRYING 為 2 起）") int attempt) {

    public static CurrentStepDto from(CurrentStepView v) {
        return v == null ? null : new CurrentStepDto(v.stepId(), v.stepNumber(), v.taskId(),
                v.taskName() == null ? v.stepId() : v.taskName(), v.goalId(), v.attempt());
    }
}
