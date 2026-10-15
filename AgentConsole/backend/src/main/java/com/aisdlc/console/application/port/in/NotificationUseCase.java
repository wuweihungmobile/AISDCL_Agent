package com.aisdlc.console.application.port.in;

import java.time.Instant;

/** 通知與待辦計數（API-NTF-01；契約 §1.4.1）：供頂列通知鈴與 signoff 佇列徽章輪詢。 */
public interface NotificationUseCase {

    /**
     * @param pendingSignoffs      待簽核：專案／目標／任務三表中未 signoff 且未軟刪的列數，加上 PARSED／REVIEWING 且未
     *                             signoff 的匯入記錄數
     * @param pendingReviews       {@code review_requests.status=PENDING} 總數
     * @param unacknowledgedAlerts {@code alerts.acknowledged=false} 總數
     * @param bridgeConnected      最近一次 Bridge 健康探測的結果；尚未探測過為 null（B1 階段恆為 null，AR-08）
     * @param bridgeCheckedAt      最近一次探測的時間；尚未探測過為 null
     */
    record NotificationSummary(int pendingSignoffs, int pendingReviews, int unacknowledgedAlerts,
                               Boolean bridgeConnected, Instant bridgeCheckedAt) {
    }

    NotificationSummary summary();
}
