package com.aisdlc.console.domain.model.monitor;

/** 持久化的告警嚴重度（只用 WARNING／CRITICAL；SSE 另有 INFO，只轉發不入庫）。 */
public enum AlertSeverity {
    WARNING, CRITICAL
}
