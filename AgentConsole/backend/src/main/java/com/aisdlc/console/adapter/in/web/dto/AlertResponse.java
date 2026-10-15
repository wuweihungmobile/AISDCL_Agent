package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.MonitorUseCase.AlertView;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/** 持久化的告警（契約 §1.3.4、§3.7）。 */
@Schema(name = "AlertResponse")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record AlertResponse(
        @NotNull UUID id,
        @NotNull UUID projectId,
        UUID runId,
        @NotNull @Schema(allowableValues = {"TOKEN_BUDGET_WARNING", "TOKEN_BUDGET_EXCEEDED", "CONSECUTIVE_FAILURES",
                "AGENT_UNRESPONSIVE", "TASK_DURATION_EXCEEDED", "HIGH_RETRY_RATE", "ENGINE_ESCALATION",
                "ENGINE_TOKEN_HALT"}, description = "前六個是 PRD §5.4.4 的規則；後兩個是引擎原生告警（ESCALATION／TOKEN_HALT）"
                + "的持久化規則名") String rule,
        @NotNull @Schema(allowableValues = {"WARNING", "CRITICAL"}) String severity,
        @Schema(description = "去重對象：run:<uuid>／task:<uuid>／goal:<uuid>／step:<step_id>") String subject,
        @NotNull String message,
        @NotNull Instant createdAt,
        @NotNull boolean acknowledged,
        String acknowledgedBy,
        Instant acknowledgedAt) {

    public static AlertResponse from(AlertView v) {
        return new AlertResponse(v.id(), v.projectId(), v.runId(), v.rule(), v.severity(), v.subject(), v.message(),
                v.createdAt(), v.acknowledged(), v.acknowledgedBy(), v.acknowledgedAt());
    }
}
