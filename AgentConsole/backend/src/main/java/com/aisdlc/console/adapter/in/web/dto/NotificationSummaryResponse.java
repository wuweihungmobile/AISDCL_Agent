package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.NotificationUseCase.NotificationSummary;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;

/**
 * 通知與待辦計數（契約 §1.4.1）：頂列通知鈴與 signoff 佇列徽章輪詢用（間隔不得小於 {@code monitor.refreshIntervalMs}，
 * 預設與最小值皆 10 秒）。{@code bridgeConnected}／{@code bridgeCheckedAt} 在 W3-B1 階段恆為 null（探測環由 W3-B2 建立）。
 */
public record NotificationSummaryResponse(
        @NotNull int pendingSignoffs,
        @NotNull int pendingReviews,
        @NotNull int unacknowledgedAlerts,
        @Schema(description = "最近一次 Bridge 健康探測的結果；尚未探測過為 null", nullable = true) Boolean bridgeConnected,
        @Schema(description = "最近一次 Bridge 健康探測的時間；尚未探測過為 null", nullable = true) Instant bridgeCheckedAt) {

    public static NotificationSummaryResponse from(NotificationSummary s) {
        return new NotificationSummaryResponse(s.pendingSignoffs(), s.pendingReviews(), s.unacknowledgedAlerts(),
                s.bridgeConnected(), s.bridgeCheckedAt());
    }
}
