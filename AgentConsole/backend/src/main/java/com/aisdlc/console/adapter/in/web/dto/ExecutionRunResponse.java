package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunView;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/**
 * 執行批次快照（契約 §1.2.1、§1.2.4～§1.2.6、§1.2.10）。{@code status} 是 PG 的六態、{@code bridgeStatus} 是 Bridge 原值
 * （{@code PAUSING}／{@code CANCELLING} 在此可見）；控制類端點回的是「呼叫 Bridge 成功後立刻再讀一次」的快照。
 */
@Schema(name = "ExecutionRunResponse")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ExecutionRunResponse(
        @NotNull UUID id,
        @NotNull UUID projectId,
        @NotNull @Schema(description = "同專案內遞增") int runNumber,
        @NotNull RunStatus status,
        BridgeStatus bridgeStatus,
        @NotNull int autonomyLevel,
        @NotNull ExecutionScopeDto scope,
        @NotNull @Schema(description = "Bridge 寫入 execution_runs.total_tokens_used（console-api 只讀）") long totalTokensUsed,
        Long tokenBudget,
        @NotNull Instant startedAt,
        Instant completedAt) {

    public static ExecutionRunResponse from(RunView v) {
        return new ExecutionRunResponse(v.id(), v.projectId(), v.runNumber(), v.status(), v.bridgeStatus(),
                v.autonomyLevel(), ExecutionScopeDto.from(v.scope()), v.totalTokensUsed(), v.tokenBudget(),
                v.startedAt(), v.completedAt());
    }
}
