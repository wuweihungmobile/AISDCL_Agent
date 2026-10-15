package com.aisdlc.console.domain.model.execution;

/**
 * US-E-10 的單一任務／單一目標 Token 上限（整體上限是批次的 {@code tokenBudget}）；null＝不限。
 * 由 console-api 依 token 事件的歸因判定，超過走 {@code TOKEN_BUDGET_EXCEEDED}（契約 D-35）。
 */
public record RunLimits(Long taskTokens, Long goalTokens) {

    public static final RunLimits NONE = new RunLimits(null, null);

    public boolean isEmpty() {
        return taskTokens == null && goalTokens == null;
    }
}
