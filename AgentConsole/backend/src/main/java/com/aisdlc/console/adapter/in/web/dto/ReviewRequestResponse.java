package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.ReviewView;
import com.aisdlc.console.domain.model.execution.ReviewDecision;
import com.aisdlc.console.domain.model.execution.ReviewKind;
import com.aisdlc.console.domain.model.execution.ReviewStatus;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 待審核／已處理的審核項（契約 §1.2.3、§1.2.11、§3.6）；{@code allowedDecisions} 決定 UI 哪些按鈕可按。
 *
 * @param id     review_requests.id；也是 {@code POST review/{stepId}} 路徑的 {stepId}
 * @param stepId 佐證步驟列 {@code execution_steps.id}（UUID，不是 playbook 的 step_id）
 */
@Schema(name = "ReviewRequestResponse", description = "待審核／已處理的審核項；allowedDecisions 決定 UI 哪些按鈕可按")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ReviewRequestResponse(
        @NotNull UUID id,
        @NotNull UUID runId,
        @NotNull ReviewKind kind,
        @NotNull ReviewStatus status,
        @Schema(description = "佐證步驟列 execution_steps.id（UUID，不是 playbook 的 step_id；TASK_CONFIRM／GOAL_*＝剛完成的步驟；"
                + "ESCALATED＝失敗步驟；Markdown 契約 §0.6）") UUID stepId,
        UUID taskId,
        UUID goalId,
        String taskName,
        String goalName,
        @NotNull @Schema(description = "給人看的原因（樣板見 Markdown 契約 §3.6.2）") String reason,
        @NotNull Instant requestedAt,
        String decidedBy,
        Instant decidedAt,
        String comment,
        @NotNull List<ReviewDecision> allowedDecisions) {

    public static ReviewRequestResponse from(ReviewView v) {
        return new ReviewRequestResponse(v.id(), v.runId(), v.kind(), v.status(), v.stepId(), v.taskId(), v.goalId(),
                v.taskName(), v.goalName(), v.reason(), v.requestedAt(), v.decidedBy(), v.decidedAt(), v.comment(),
                v.allowedDecisions());
    }
}
