package com.aisdlc.console.domain.model.execution;

/** 人工審核決定（{@code POST /executions/{runId}/review/{stepId}} 的 {@code decision}）。 */
public enum ReviewDecision {
    APPROVE, REJECT, RETRY, SKIP;

    /** 決定對應的審核項終態（APPROVE→APPROVED、REJECT→REJECTED、RETRY→RETRIED、SKIP→SKIPPED）。 */
    public ReviewStatus resultingStatus() {
        return switch (this) {
            case APPROVE -> ReviewStatus.APPROVED;
            case REJECT -> ReviewStatus.REJECTED;
            case RETRY -> ReviewStatus.RETRIED;
            case SKIP -> ReviewStatus.SKIPPED;
        };
    }
}
