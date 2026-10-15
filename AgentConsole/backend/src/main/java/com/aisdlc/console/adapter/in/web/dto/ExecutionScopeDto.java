package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.execution.RunLimits;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.List;
import java.util.UUID;

/**
 * 執行範圍（請求 {@code StartExecutionRequest.scope} 與回應 {@code ExecutionRunResponse.scope} 共用；契約 §1.2.1）。
 *
 * <p>{@code ALL}＝專案內全部「可執行」任務（排除 COMPLETED／SKIPPED）；{@code SELECTED}＝{@code goalIds} 的全部可執行任務 ∪
 * {@code taskIds}。請求中 {@code mode} 可省略（預設 ALL）；{@code followUpOfRunId} 只出現在後續批次的回應、請求帶了也忽略。
 *
 * <p>{@code mode} 刻意宣告成字串（以 allowableValues 文件化成列舉）：請求的欄位驗證要在「專案存在」之後才做（契約 §1.2.1
 * 驗證順序 1→2），若在這裡用列舉型別，反序列化失敗會先於 404 回 400。
 */
@Schema(name = "ExecutionScope", description = "ALL＝全部可執行任務；SELECTED＝goalIds 的全部可執行任務 ∪ taskIds。"
        + "followUpOfRunId 只出現在後續批次（follow-up run）的回應")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ExecutionScopeDto(
        @Schema(allowableValues = {"ALL", "SELECTED"}, description = "請求可省略（預設 ALL）；回應一律帶") String mode,
        List<UUID> goalIds,
        List<UUID> taskIds,
        Limits limits,
        UUID followUpOfRunId) {

    /** US-E-10 的單一任務／單一目標 Token 上限；超過 → TOKEN_BUDGET_EXCEEDED 告警＋自動暫停。 */
    @Schema(name = "ExecutionLimits", description = "US-E-10 的單一任務／單一目標 Token 上限（整體上限是 tokenBudget）；"
            + "超過 → TOKEN_BUDGET_EXCEEDED 告警＋自動暫停")
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Limits(
            @Schema(minimum = "1") Long taskTokens,
            @Schema(minimum = "1") Long goalTokens) {
    }

    public static ExecutionScopeDto from(RunScope scope) {
        RunLimits limits = scope.limits();
        return new ExecutionScopeDto(scope.mode().name(), scope.goalIds(), scope.taskIds(),
                limits == null || limits.isEmpty() ? null : new Limits(limits.taskTokens(), limits.goalTokens()),
                scope.followUpOfRunId());
    }
}
