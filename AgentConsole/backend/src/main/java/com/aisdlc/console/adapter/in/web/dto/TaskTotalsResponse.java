package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.MonitorUseCase.TaskTotalsView;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;

/**
 * 全域任務總計（契約 §1.3.8，C-1）：跨全部未封存且未軟刪除的專案，{@code execution_steps} 在 {@code [from, to)} 內各狀態的列數——
 * 與 {@code task-trend} 同表同判準，只是不分桶、不分專案。{@code from}／{@code to} 是實際採用的視窗。
 */
@Schema(name = "TaskTotalsResponse")
public record TaskTotalsResponse(
        @NotNull Instant from,
        @NotNull Instant to,
        @NotNull long started,
        @NotNull long completed,
        @NotNull long failed,
        @NotNull long retried,
        @NotNull int projectsCounted) {

    public static TaskTotalsResponse from(TaskTotalsView v) {
        return new TaskTotalsResponse(v.from(), v.to(), v.started(), v.completed(), v.failed(), v.retried(),
                v.projectsCounted());
    }
}
