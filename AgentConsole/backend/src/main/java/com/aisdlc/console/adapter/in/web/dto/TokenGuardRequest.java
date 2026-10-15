package com.aisdlc.console.adapter.in.web.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

/**
 * 原子更新 token_guard 群組（契約 §1.5.4；NFR-SEC-05）：兩個閾值一併提交，同一交易內做跨鍵校驗 {@code halt > compact}
 * （相等也違規）。範圍違規是 400 Bean Validation（無 reason）；{@code halt <= compact} 是 400 reason＝PRD 逐字常數。
 */
public record TokenGuardRequest(
        @NotNull(message = "compactThresholdPct 不可缺漏")
        @Min(value = 1, message = "compactThresholdPct 必須介於 1 到 99")
        @Max(value = 99, message = "compactThresholdPct 必須介於 1 到 99")
        @Schema(description = "達此 context 百分比觸發 /compact") Integer compactThresholdPct,
        @NotNull(message = "haltThresholdPct 不可缺漏")
        @Min(value = 2, message = "haltThresholdPct 必須介於 2 到 100")
        @Max(value = 100, message = "haltThresholdPct 必須介於 2 到 100")
        @Schema(description = "達此 context 百分比 checkpoint 收斂；必須大於 compactThresholdPct") Integer haltThresholdPct) {
}
