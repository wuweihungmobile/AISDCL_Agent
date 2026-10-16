package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunDetailView;
import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunView;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 執行批次詳情＝{@link ExecutionRunResponse} 的全部欄位 ＋ 進度、待審核項與 Bridge 連線資訊（契約 §1.2.3）。
 *
 * <p>Bridge 不可達（連線失敗或逾時）時仍回 200：{@code bridge.connected=false}、{@code currentStep} 缺席，
 * {@code completedSteps}／{@code totalSteps}／{@code lastEventSeq} 由 DB 衍生（主控裁決：不回 5xx）。
 *
 * <p>v1.3：{@code engineCapabilities}（D-11，讀自 DB、建立時凍結）與 {@code bridge.resources}（D-12，引擎行程樹的資源取樣，
 * 來自同一次 Bridge 快照）。只有本回應帶 {@code bridge} 物件，控制類端點的快照沒有。
 */
@Schema(name = "ExecutionRunDetailResponse", description = "ExecutionRunResponse ＋ 進度、待審核項與 Bridge 連線資訊")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ExecutionRunDetailResponse(
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
        Instant completedAt,
        @Schema(description = "v1.3（D-11）：該批次 spawn 時 Console 實際送進引擎的能力狀態；同 ExecutionRunResponse.engineCapabilities"
                + "（讀自 DB，建立時凍結；V10 之前建立的批次缺席或為 null）")
        EngineCapabilitiesDto engineCapabilities,
        CurrentStepDto currentStep,
        @NotNull int completedSteps,
        @NotNull int totalSteps,
        @Schema(description = "Bridge 最後一則事件 seq；Bridge 不可達時為 DB 內最大 step_number 或 null") Integer lastEventSeq,
        @Schema(description = "Bridge 的狀態原因（例：「引擎升級（ESCALATION）：…」）") String reason,
        @Schema(description = "進行中＝現在−startedAt；終態＝completedAt−startedAt") Long elapsedSec,
        @NotNull List<ReviewRequestResponse> pendingReviews,
        @NotNull BridgeInfoDto bridge) {

    public static ExecutionRunDetailResponse from(RunDetailView d) {
        RunView v = d.run();
        return new ExecutionRunDetailResponse(v.id(), v.projectId(), v.runNumber(), v.status(), v.bridgeStatus(),
                v.autonomyLevel(), ExecutionScopeDto.from(v.scope()), v.totalTokensUsed(), v.tokenBudget(),
                v.startedAt(), v.completedAt(), EngineCapabilitiesDto.from(v.engineCapabilities()),
                CurrentStepDto.from(d.currentStep()), d.completedSteps(),
                d.totalSteps(), d.lastEventSeq(), d.reason(), d.elapsedSec(),
                d.pendingReviews().stream().map(ReviewRequestResponse::from).toList(), BridgeInfoDto.from(d.bridge()));
    }
}
