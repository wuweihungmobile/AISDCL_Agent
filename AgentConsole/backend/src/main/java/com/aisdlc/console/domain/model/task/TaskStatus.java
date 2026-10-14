package com.aisdlc.console.domain.model.task;

/** 任務狀態（PRD §5.1.3 的 11 態；轉移規則見附錄 B.3，實作於 StateMachines）。 */
public enum TaskStatus {
    PENDING,
    QUEUED,
    BLOCKED,
    RUNNING,
    VALIDATING,
    COMPLETED,
    FAILED,
    ESCALATED,
    PAUSED,
    SKIPPED,
    CANCELLED
}
