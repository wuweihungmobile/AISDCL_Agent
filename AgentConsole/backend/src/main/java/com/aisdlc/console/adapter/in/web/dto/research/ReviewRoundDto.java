package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchViews.PrecheckCheck;
import com.aisdlc.console.domain.model.research.ResearchViews.Round;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;
import java.util.List;

/**
 * 審查輪（契約 §1.3 {@code ReviewRoundDto}；D-57）：<b>只描述已完成評估的輪</b>——輪列只在輪有結果時一次寫入，所以<b>沒有 {@code status}</b>、{@code finishedAt}
 * 必填、結果欄（含 {@code verdict}）非 null；{@code verdict} 只有 PASS、REVISE、ESCALATE（REVIEW_INVALID 不是輪的 verdict：無效輸出不寫輪列，D-55）。
 * 進行中的審查看 {@code research.run}（stage＝REVIEW）事件。{@code weightedScore}（NUMERIC(5,2) 原樣；顯示用 toFixed(2)、比較用整數
 * {@code Math.round(weightedScore*100)} 對 8500，不得先四捨五入到一位；D-42）於前置否決不過時為 null。
 */
@Schema(name = "ReviewRoundDto", description = "四方審查的一個已完成輪（沒有 status：列存在＝輪已完成評估；D-57）")
public record ReviewRoundDto(
        @NotNull int roundNo,
        @NotNull @Schema(description = "輪列的 fsm_generation，供 UI 只比對目前世代（D-59(4)）") int fsmGeneration,
        @NotNull int prdVersionNo,
        @NotNull @Schema(description = "PRD 版本的 semver 字串（含 v 前綴）；prdVersionNo 是整數，兩者並存（D-43）") String prdVersion,
        @NotNull @Schema(description = "AUTO｜MANUAL｜POST_HUMAN") String triggerKind,
        @NotNull PrecheckDto precheck,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "W100/100，兩位小數；前置否決不過時 null") BigDecimal weightedScore,
        @NotNull BigDecimal threshold,
        @NotNull int floorScore,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) Integer minDimensionScore,
        @NotNull ConditionsDto conditions,
        @NotNull int openP1Count,
        @NotNull boolean passed,
        @NotNull @Schema(description = "PASS｜REVISE｜ESCALATE") String verdict,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "PASS｜FAIL；POST_HUMAN 通過時 null（HUMAN_PENDING 下不呼叫 gate PASS，D-50）")
        String fsmGateResult,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "gate FAIL 輪＝其 retry_count；gate PASS 輪＝0；POST_HUMAN 通過輪＝null（D-61）")
        Integer fsmRetryCount,
        @NotNull boolean escalated,
        @NotNull List<ReviewScoreDto> scores,
        @NotNull List<DefectDto> defects,
        @NotNull String startedAt,
        @NotNull String finishedAt) {

    /** 前置否決（SLV-001、SLV-002、SLV-003、AMBIGUITY 四項檢查）。 */
    @Schema(name = "ReviewPrecheckDto")
    public record PrecheckDto(@NotNull boolean passed, @NotNull List<PrecheckCheckDto> checks) {
    }

    /** 前置否決的一項檢查。 */
    @Schema(name = "ReviewPrecheckCheckDto")
    public record PrecheckCheckDto(@NotNull String id, @NotNull boolean passed, @NotNull String detail) {

        static PrecheckCheckDto from(PrecheckCheck check) {
            return new PrecheckCheckDto(check.id(), check.passed(), check.detail());
        }
    }

    /**
     * 通過條件各自是否成立（由 console-api 自欄位導出，供 UI 說明不成立的條件）：前置否決不過（未計分）時 {@code weightedGeThreshold}、
     * {@code allDimensionsGeFloor} 為 null。加權分比較以 NUMERIC(5,2) 的精確值對 threshold（等價於整數 ×100 的比較，D-42）。
     */
    @Schema(name = "ReviewConditionsDto")
    public record ConditionsDto(
            @NotNull boolean precheckPassed,
            @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) Boolean weightedGeThreshold,
            @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) Boolean allDimensionsGeFloor,
            @NotNull boolean noOpenP1) {
    }

    public static ReviewRoundDto from(Round round) {
        Boolean weightedGeThreshold = round.weightedScore() == null ? null : round.weightedScore().compareTo(round.threshold()) >= 0;
        Boolean allDimensionsGeFloor = round.minDimensionScore() == null ? null : round.minDimensionScore() >= round.floorScore();
        PrecheckDto precheck = new PrecheckDto(round.precheckPassed(), round.precheckChecks().stream().map(PrecheckCheckDto::from).toList());
        ConditionsDto conditions = new ConditionsDto(round.precheckPassed(), weightedGeThreshold, allDimensionsGeFloor, round.openP1Count() == 0);
        return new ReviewRoundDto(round.roundNo(), round.fsmGeneration(), round.prdVersionNo(), round.prdVersion(), round.triggerKind(), precheck,
                round.weightedScore(), round.threshold(), round.floorScore(), round.minDimensionScore(), conditions, round.openP1Count(),
                round.passed(), round.verdict(), round.fsmGateResult(), round.fsmRetryCount(), round.escalated(),
                round.scores().stream().map(ReviewScoreDto::from).toList(), round.defects().stream().map(DefectDto::from).toList(),
                Iso.of(round.startedAt()), Iso.of(round.finishedAt()));
    }
}
