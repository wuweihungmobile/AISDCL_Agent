package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.monitor.AlertRule;
import com.aisdlc.console.domain.model.monitor.AlertSeverity;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 告警六規則（＋引擎原生告警）的純判定（契約 §3.7；PRD §5.4.4）。純 Java：只回「該不該產生告警與其內容」，
 * 去重（同規則＋對象在被確認前不重複）、持久化、SSE 與 {@code :pause} 動作都在 application 層。
 *
 * <p>訊息樣板逐字取自契約 §3.7；百分比一律四捨五入到整數。
 */
public final class AlertRules {

    /** 判定結果：要產生的告警內容。 */
    public record Candidate(AlertRule rule, AlertSeverity severity, String subject, String message) {
    }

    /** 高重試率的最小樣本：已開始的任務數需 ≥ 2 才判定。 */
    public static final int HIGH_RETRY_MIN_SAMPLE = 2;
    /** 高重試率的固定門檻 50%（PRD；嚴格大於）。 */
    public static final double HIGH_RETRY_THRESHOLD = 0.5;

    private AlertRules() {
    }

    /** {@code TOKEN_BUDGET_WARNING}：預算非 null 且 {@code used ≥ budget × 閾值}（{@code execution.tokenBudgetWarningThreshold}，預設 0.8）。 */
    public static Optional<Candidate> tokenBudgetWarning(UUID runId, long used, Long budget, double threshold) {
        if (budget == null || budget <= 0 || used < budget * threshold) {
            return Optional.empty();
        }
        return Optional.of(new Candidate(AlertRule.TOKEN_BUDGET_WARNING, AlertSeverity.WARNING, "run:" + runId,
                "Token 使用量已達預算的 " + percent(used, budget) + "%（" + used + " / " + budget + "）"));
    }

    /** {@code TOKEN_BUDGET_EXCEEDED}（整體）：{@code used > budget}；動作＝持久化＋SSE＋{@code :pause}。 */
    public static Optional<Candidate> tokenBudgetExceeded(UUID runId, long used, Long budget) {
        if (budget == null || used <= budget) {
            return Optional.empty();
        }
        return Optional.of(new Candidate(AlertRule.TOKEN_BUDGET_EXCEEDED, AlertSeverity.CRITICAL, "run:" + runId,
                "Token 使用量已超出預算（" + used + " / " + budget + "），已要求暫停執行"));
    }

    /** {@code TOKEN_BUDGET_EXCEEDED}（單一任務上限，{@code scope.limits.taskTokens}）。 */
    public static Optional<Candidate> taskTokenLimitExceeded(UUID taskId, String taskName, long used, Long limit) {
        if (limit == null || used <= limit) {
            return Optional.empty();
        }
        return Optional.of(new Candidate(AlertRule.TOKEN_BUDGET_EXCEEDED, AlertSeverity.CRITICAL, "task:" + taskId,
                "任務「" + taskName + "」Token 用量 " + used + " 超過上限 " + limit + "，已要求暫停執行"));
    }

    /** {@code TOKEN_BUDGET_EXCEEDED}（單一目標上限，{@code scope.limits.goalTokens}）。 */
    public static Optional<Candidate> goalTokenLimitExceeded(UUID goalId, String goalName, long used, Long limit) {
        if (limit == null || used <= limit) {
            return Optional.empty();
        }
        return Optional.of(new Candidate(AlertRule.TOKEN_BUDGET_EXCEEDED, AlertSeverity.CRITICAL, "goal:" + goalId,
                "目標「" + goalName + "」Token 用量 " + used + " 超過上限 " + limit + "，已要求暫停執行"));
    }

    /**
     * {@code CONSECUTIVE_FAILURES}：該目標下任務的終局結果序列（依終局步驟時間；{@code true}＝成功、{@code false}＝失敗，
     * 已略過 SKIPPED）最近 {@code threshold} 個全是失敗。
     */
    public static Optional<Candidate> consecutiveFailures(UUID goalId, String goalName, List<Boolean> outcomes,
                                                          int threshold) {
        if (threshold < 1 || outcomes.size() < threshold) {
            return Optional.empty();
        }
        List<Boolean> lastN = outcomes.subList(outcomes.size() - threshold, outcomes.size());
        if (lastN.stream().anyMatch(Boolean::booleanValue)) {
            return Optional.empty();
        }
        return Optional.of(new Candidate(AlertRule.CONSECUTIVE_FAILURES, AlertSeverity.CRITICAL, "goal:" + goalId,
                "目標「" + goalName + "」連續 " + threshold + " 個任務失敗"));
    }

    /**
     * {@code AGENT_UNRESPONSIVE}：run 為 RUNNING／PAUSING／CANCELLING，距最後一則事件超過 {@code thresholdSec}，
     * <b>且</b>最近一次探測失敗（單純長步驟、探測正常不告警）。
     */
    public static Optional<Candidate> agentUnresponsive(UUID runId, long silentSeconds, int thresholdSec,
                                                        boolean probeFailed) {
        if (silentSeconds <= thresholdSec || !probeFailed) {
            return Optional.empty();
        }
        return Optional.of(new Candidate(AlertRule.AGENT_UNRESPONSIVE, AlertSeverity.CRITICAL, "run:" + runId,
                "Agent 已超過 " + thresholdSec + " 秒無回應"));
    }

    /** {@code TASK_DURATION_EXCEEDED}：耗時 {@code > agent.taskTimeout × monitor.alertTaskDurationMultiplier}。 */
    public static Optional<Candidate> taskDurationExceeded(UUID taskId, String taskName, long elapsedSec,
                                                           int taskTimeoutSec, double multiplier) {
        double threshold = taskTimeoutSec * multiplier;
        if (elapsedSec <= threshold) {
            return Optional.empty();
        }
        return Optional.of(new Candidate(AlertRule.TASK_DURATION_EXCEEDED, AlertSeverity.WARNING, "task:" + taskId,
                "任務「" + taskName + "」已執行 " + elapsedSec + " 秒，超過門檻 " + Math.round(threshold) + " 秒（"
                        + BigDecimal.valueOf(multiplier).stripTrailingZeros().toPlainString() + " 倍）"));
    }

    /** {@code HIGH_RETRY_RATE}：{@code 有重試的任務數 ÷ 已開始的任務數 > 0.5}（最小樣本 2 個已開始的任務）。 */
    public static Optional<Candidate> highRetryRate(UUID goalId, String goalName, int startedTasks, int retriedTasks) {
        if (startedTasks < HIGH_RETRY_MIN_SAMPLE || (double) retriedTasks / startedTasks <= HIGH_RETRY_THRESHOLD) {
            return Optional.empty();
        }
        return Optional.of(new Candidate(AlertRule.HIGH_RETRY_RATE, AlertSeverity.WARNING, "goal:" + goalId,
                "目標「" + goalName + "」重試率 " + percent(retriedTasks, startedTasks) + "%，超過 50%"));
    }

    /** {@code ENGINE_ESCALATION}（Bridge {@code alert} 的 {@code code=ESCALATION}）；subject＝{@code step:<stepId>}。 */
    public static Candidate engineEscalation(String stepId, String detail) {
        return new Candidate(AlertRule.ENGINE_ESCALATION, AlertSeverity.CRITICAL, "step:" + stepId,
                "引擎升級（ESCALATION）：" + detail);
    }

    /** {@code ENGINE_TOKEN_HALT}（{@code code=TOKEN_HALT}）；subject＝{@code step:<stepId>}，沒有步驟則 {@code run:<runId>}。 */
    public static Candidate engineTokenHalt(UUID runId, String stepId, String detail) {
        String subject = stepId == null || stepId.isBlank() ? "run:" + runId : "step:" + stepId;
        return new Candidate(AlertRule.ENGINE_TOKEN_HALT, AlertSeverity.WARNING, subject,
                "引擎因 Token／額度門檻停機：" + detail);
    }

    /** 百分比四捨五入到整數（half-up）。 */
    static long percent(long part, long whole) {
        return BigDecimal.valueOf(part).multiply(BigDecimal.valueOf(100))
                .divide(BigDecimal.valueOf(whole), 0, java.math.RoundingMode.HALF_UP).longValue();
    }
}
