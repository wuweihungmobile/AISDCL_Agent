package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.StepView;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/**
 * 一個步驟事件列（契約 §1.2.7）：Bridge 每個 {@code step} 事件寫一列，狀態只有 {@code STARTED／RETRYING／COMPLETED／FAILED}。
 * {@code stepNumber} 是該事件的 Bridge {@code seq}（與 SSE {@code id:} 同一個序號空間，所以 {@code afterSeq} 可直接對
 * {@code Last-Event-ID} 的整數部分）；{@code stepId} 才是 playbook 的 step_id。
 */
@Schema(name = "ExecutionStepResponse")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ExecutionStepResponse(
        @NotNull UUID id,
        @NotNull UUID runId,
        @NotNull UUID taskId,
        String taskName,
        UUID goalId,
        @NotNull @Schema(description = "＝該 step 事件的 Bridge seq（與 SSE id 同序號空間）；不是步驟位置，位置請以 stepId 對 dag 的 sequence"
                + "（Markdown 契約 §0.6）") int stepNumber,
        @Schema(description = "playbook step_id（取自 input.step_id）") String stepId,
        @Schema(description = "取自 input.attempt") Integer attempt,
        @NotNull @Schema(description = "Bridge 寫成「<step_id>: <任務名稱>」") String action,
        @NotNull @Schema(allowableValues = {"STARTED", "COMPLETED", "FAILED", "RETRYING"},
                description = "Bridge 實際寫入的四種步驟狀態（沒有 IN_PROGRESS）") String status,
        @JsonInclude(JsonInclude.Include.ALWAYS)
        @Schema(nullable = true, description = "Bridge 不寫此欄；COMPLETED／FAILED 列由 Console 以 token 事件歸因後回傳，其餘為 null")
        Long tokensUsed,
        String errorMessage,
        String output,
        @NotNull Instant timestamp) {

    public static ExecutionStepResponse from(StepView v) {
        return new ExecutionStepResponse(v.id(), v.runId(), v.taskId(), v.taskName(), v.goalId(), v.stepNumber(),
                v.stepId(), v.attempt(), v.action(), v.status(), v.tokensUsed(), v.errorMessage(), v.output(),
                v.timestamp());
    }
}
