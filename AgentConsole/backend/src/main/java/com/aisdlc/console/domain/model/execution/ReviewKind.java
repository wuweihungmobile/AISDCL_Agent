package com.aisdlc.console.domain.model.execution;

/** 審核項種類（與 V3 migration 的 CHECK 一致，不擴充；契約 §3.6.2）。 */
public enum ReviewKind {
    TASK_CONFIRM, GOAL_CONFIRM, GOAL_COMPLETED, ESCALATED;

    /** gate 類（讓人在閘點決定是否繼續）：TASK_CONFIRM／GOAL_CONFIRM／GOAL_COMPLETED。 */
    public boolean gate() {
        return this != ESCALATED;
    }
}
