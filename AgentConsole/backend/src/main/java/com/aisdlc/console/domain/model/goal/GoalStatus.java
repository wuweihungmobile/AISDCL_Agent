package com.aisdlc.console.domain.model.goal;

/** 目標狀態（PRD §5.1.2；轉移規則見附錄 B.2，實作於 StateMachines）。 */
public enum GoalStatus {
    PENDING,
    IN_PROGRESS,
    COMPLETED,
    FAILED,
    SKIPPED
}
