package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.MonitorUseCase.TaskTrendView;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;

/** 任務執行趨勢的一個桶（契約 §1.3.3、§3.8.2）：桶內 STARTED／COMPLETED／FAILED／RETRYING 步驟列的筆數。 */
@Schema(name = "TaskTrendPoint")
public record TaskTrendPoint(
        @NotNull Instant bucketStart,
        @NotNull int started,
        @NotNull int completed,
        @NotNull int failed,
        @NotNull int retried) {

    public static TaskTrendPoint from(TaskTrendView v) {
        return new TaskTrendPoint(v.bucketStart(), v.started(), v.completed(), v.failed(), v.retried());
    }
}
