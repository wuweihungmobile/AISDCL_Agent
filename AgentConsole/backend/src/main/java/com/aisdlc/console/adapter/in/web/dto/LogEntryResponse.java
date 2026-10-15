package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.MonitorUseCase.LogView;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/**
 * 結構化日誌的一列（契約 §1.3.6、§3.8.3）：由既有資料衍生（步驟事件、批次生命週期、告警、審核項），不含引擎原始 stdout
 * （原始行只在 SSE 的 {@code log} 事件，{@code source=ENGINE}）。
 */
@Schema(name = "LogEntryResponse")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record LogEntryResponse(
        @NotNull @Schema(description = "穩定的衍生 id（來源表 id 加前綴，例：step:<uuid>）") String id,
        @NotNull Instant timestamp,
        @NotNull @Schema(allowableValues = {"INFO", "WARN", "ERROR"}) String level,
        @NotNull @Schema(allowableValues = {"STEP", "RUN", "ALERT", "REVIEW"},
                description = "STEP＝步驟事件；RUN＝批次生命週期；ALERT＝告警；REVIEW＝審核項") String source,
        @NotNull String message,
        UUID runId,
        UUID taskId,
        String stepId) {

    public static LogEntryResponse from(LogView v) {
        return new LogEntryResponse(v.id(), v.timestamp(), v.level(), v.source(), v.message(), v.runId(), v.taskId(),
                v.stepId());
    }
}
