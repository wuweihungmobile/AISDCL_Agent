package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunView;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 執行批次快照（契約 §1.2.1、§1.2.4～§1.2.6、§1.2.10）。{@code status} 是 PG 的六態、{@code bridgeStatus} 是 Bridge 原值
 * （{@code PAUSING}／{@code CANCELLING} 在此可見）；控制類端點回的是「呼叫 Bridge 成功後立刻再讀一次」的快照。
 *
 * <p>{@code engineCapabilities}（v1.3，D-11）：spawn 時 Console 送進引擎的能力狀態，execute 的 201、詳情與控制類快照都帶同一份值
 * （讀自 DB，建立時凍結）；V10 之前建立的批次缺席（前端不顯示、不猜測）。批次列表項（{@code ExecutionRunSummaryResponse}）不帶它。
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
        Instant completedAt,
        @Schema(description = "v1.3（D-11）：該批次 spawn 時 Console 實際送進引擎的能力狀態（契約 §3.4.2 的決策表）。落庫於 "
                + "execution_runs.engine_capabilities（V10），建立時凍結，resume／restore 不更新；V10 之前建立的批次缺席或為 null（不得猜測）。"
                + "execute 的 201、GET /executions/{runId}、pause／resume／cancel／restore 的快照同值；批次列表不帶它")
        EngineCapabilitiesDto engineCapabilities,
        @ArraySchema(arraySchema = @Schema(description = "v1.5（D-115-06；契約 §1.10.6）：<b>只有 execute 的 201</b> 帶；沒有警告就缺席（維持 v1.4 的回應形狀）。"
                + "sdd_governance_inactive＝範圍內有 SDD 來源任務、但本批次沒有啟用 SDD 治理（cause 見契約 §1.10.5）；sdd_frozen_digest_absent＝"
                + "已啟用治理、但凍結時沒有記錄內容摘要（Bridge 回的 201 warnings 原樣轉入）。審核決定開的後續批次回 204，警告只寫日誌"))
        List<ExecutionWarningDto> warnings) {

    public static ExecutionRunResponse from(RunView v) {
        return new ExecutionRunResponse(v.id(), v.projectId(), v.runNumber(), v.status(), v.bridgeStatus(),
                v.autonomyLevel(), ExecutionScopeDto.from(v.scope()), v.totalTokensUsed(), v.tokenBudget(),
                v.startedAt(), v.completedAt(), EngineCapabilitiesDto.from(v.engineCapabilities()),
                v.warnings().isEmpty() ? null : v.warnings().stream().map(ExecutionWarningDto::from).toList());
    }
}
