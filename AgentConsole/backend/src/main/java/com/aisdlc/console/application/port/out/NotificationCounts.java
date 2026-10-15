package com.aisdlc.console.application.port.out;

/** 通知摘要的三個計數（只讀、跨專案；契約 §1.4.1）。 */
public interface NotificationCounts {

    /**
     * 專案、目標、任務三表中 {@code signed_off=false} 且未軟刪的列數（目標與任務所屬的專案、目標也須未軟刪），
     * 加上 PARSED／REVIEWING 且未 signoff 的匯入記錄數。每個待簽核的列算一次。
     */
    int pendingSignoffs();

    /** {@code review_requests.status='PENDING'} 總數。 */
    int pendingReviews();

    /** {@code alerts.acknowledged=false} 總數。 */
    int unacknowledgedAlerts();
}
