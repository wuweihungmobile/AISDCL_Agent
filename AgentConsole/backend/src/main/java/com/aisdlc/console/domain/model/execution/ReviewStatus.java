package com.aisdlc.console.domain.model.execution;

/** 審核項狀態（V3 的 CHECK）：PENDING 之後只有一次人工決定或系統自動關閉。 */
public enum ReviewStatus {
    PENDING, APPROVED, REJECTED, RETRIED, SKIPPED
}
