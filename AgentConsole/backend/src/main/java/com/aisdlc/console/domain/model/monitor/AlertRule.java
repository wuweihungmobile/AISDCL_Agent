package com.aisdlc.console.domain.model.monitor;

/** 告警規則名（PRD §5.4.4 的六條，加上引擎原生告警持久化用的兩個；契約 §3.7）。 */
public enum AlertRule {
    TOKEN_BUDGET_WARNING, TOKEN_BUDGET_EXCEEDED, CONSECUTIVE_FAILURES, AGENT_UNRESPONSIVE, TASK_DURATION_EXCEEDED,
    HIGH_RETRY_RATE, ENGINE_ESCALATION, ENGINE_TOKEN_HALT
}
