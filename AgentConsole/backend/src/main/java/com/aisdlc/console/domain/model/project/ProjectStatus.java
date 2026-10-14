package com.aisdlc.console.domain.model.project;

/** 專案狀態（PRD §5.1.1；轉移規則見附錄 B.1，實作於 StateMachines）。 */
public enum ProjectStatus {
    DRAFT,
    READY,
    EXECUTING,
    COMPLETED,
    FAILED,
    ARCHIVED
}
