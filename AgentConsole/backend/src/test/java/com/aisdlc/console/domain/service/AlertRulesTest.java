package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.monitor.AlertRule;
import com.aisdlc.console.domain.model.monitor.AlertSeverity;
import com.aisdlc.console.domain.service.AlertRules.Candidate;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/** 告警六規則各一正一反（契約 §3.7）；訊息樣板逐字，E2E 以 message 逐字比對。 */
class AlertRulesTest {

    private final UUID runId = UUID.fromString("e5a7c3b9-2f1d-4b6a-8c0e-1d2f3a4b5c31");
    private final UUID taskId = UUID.fromString("c7e2b1a0-3d4f-4a5b-9c6d-7e8f9a0b1c21");
    private final UUID goalId = UUID.fromString("a1f4c2d3-5b6e-4c7d-8e9f-0a1b2c3d4e11");

    @Test
    void tokenWarningFiresAtTheThresholdWithTheRoundedPercentage() {
        Candidate c = AlertRules.tokenBudgetWarning(runId, 1240, 1500L, 0.8).orElseThrow();
        assertThat(c.rule()).isEqualTo(AlertRule.TOKEN_BUDGET_WARNING);
        assertThat(c.severity()).isEqualTo(AlertSeverity.WARNING);
        assertThat(c.subject()).isEqualTo("run:" + runId);
        assertThat(c.message()).isEqualTo("Token 使用量已達預算的 83%（1240 / 1500）");

        assertThat(AlertRules.tokenBudgetWarning(runId, 1200, 1500L, 0.8)).as("恰好 80% 就觸發").isPresent();
        assertThat(AlertRules.tokenBudgetWarning(runId, 1199, 1500L, 0.8)).as("差 1 不觸發").isEmpty();
        assertThat(AlertRules.tokenBudgetWarning(runId, 99999, null, 0.8)).as("沒有預算不判定").isEmpty();
    }

    @Test
    void tokenExceededNeedsStrictlyMoreThanTheBudget() {
        Candidate c = AlertRules.tokenBudgetExceeded(runId, 2480, 1500L).orElseThrow();
        assertThat(c.severity()).isEqualTo(AlertSeverity.CRITICAL);
        assertThat(c.message()).isEqualTo("Token 使用量已超出預算（2480 / 1500），已要求暫停執行");

        assertThat(AlertRules.tokenBudgetExceeded(runId, 1500, 1500L)).as("用滿但未超過").isEmpty();
        assertThat(AlertRules.tokenBudgetExceeded(runId, 5, null)).isEmpty();
    }

    @Test
    void perTaskAndPerGoalLimitsHaveTheirOwnSubjectAndMessage() {
        Candidate task = AlertRules.taskTokenLimitExceeded(taskId, "初始化", 1240, 1000L).orElseThrow();
        assertThat(task.subject()).isEqualTo("task:" + taskId);
        assertThat(task.message()).isEqualTo("任務「初始化」Token 用量 1240 超過上限 1000，已要求暫停執行");
        assertThat(AlertRules.taskTokenLimitExceeded(taskId, "初始化", 1000, 1000L)).isEmpty();
        assertThat(AlertRules.taskTokenLimitExceeded(taskId, "初始化", 5000, null)).isEmpty();

        Candidate goal = AlertRules.goalTokenLimitExceeded(goalId, "基礎", 3000, 2000L).orElseThrow();
        assertThat(goal.subject()).isEqualTo("goal:" + goalId);
        assertThat(goal.rule()).isEqualTo(AlertRule.TOKEN_BUDGET_EXCEEDED);
        assertThat(AlertRules.goalTokenLimitExceeded(goalId, "基礎", 2000, 2000L)).isEmpty();
    }

    @Test
    void consecutiveFailuresLooksOnlyAtTheLastNOutcomes() {
        List<Boolean> failures = List.of(false, false, false);
        Candidate c = AlertRules.consecutiveFailures(goalId, "基礎", failures, 3).orElseThrow();
        assertThat(c.rule()).isEqualTo(AlertRule.CONSECUTIVE_FAILURES);
        assertThat(c.severity()).isEqualTo(AlertSeverity.CRITICAL);
        assertThat(c.message()).isEqualTo("目標「基礎」連續 3 個任務失敗");

        assertThat(AlertRules.consecutiveFailures(goalId, "基礎", List.of(true, false, false, false), 3)).isPresent();
        assertThat(AlertRules.consecutiveFailures(goalId, "基礎", List.of(false, false, true), 3))
                .as("最近一個成功就中斷連續").isEmpty();
        assertThat(AlertRules.consecutiveFailures(goalId, "基礎", List.of(false, false), 3)).as("不足 3 個").isEmpty();
    }

    @Test
    void agentUnresponsiveNeedsBothSilenceAndAFailedProbe() {
        Candidate c = AlertRules.agentUnresponsive(runId, 301, 300, true).orElseThrow();
        assertThat(c.severity()).isEqualTo(AlertSeverity.CRITICAL);
        assertThat(c.message()).isEqualTo("Agent 已超過 300 秒無回應");

        assertThat(AlertRules.agentUnresponsive(runId, 301, 300, false)).as("單純長步驟、探測正常不告警").isEmpty();
        assertThat(AlertRules.agentUnresponsive(runId, 300, 300, true)).as("剛好等於閾值不告警").isEmpty();
    }

    @Test
    void taskDurationUsesTheTaskTimeoutTimesTheMultiplier() {
        Candidate c = AlertRules.taskDurationExceeded(taskId, "設定", 1300, 600, 2.0).orElseThrow();
        assertThat(c.rule()).isEqualTo(AlertRule.TASK_DURATION_EXCEEDED);
        assertThat(c.severity()).isEqualTo(AlertSeverity.WARNING);
        assertThat(c.subject()).isEqualTo("task:" + taskId);
        assertThat(c.message()).isEqualTo("任務「設定」已執行 1300 秒，超過門檻 1200 秒（2 倍）");

        assertThat(AlertRules.taskDurationExceeded(taskId, "設定", 1200, 600, 2.0)).as("等於門檻不告警").isEmpty();
        assertThat(AlertRules.taskDurationExceeded(taskId, "設定", 1600, 600, 2.5).orElseThrow().message())
                .isEqualTo("任務「設定」已執行 1600 秒，超過門檻 1500 秒（2.5 倍）");
    }

    @Test
    void highRetryRateNeedsTwoStartedTasksAndMoreThanHalfRetried() {
        Candidate c = AlertRules.highRetryRate(goalId, "基礎", 3, 2).orElseThrow();
        assertThat(c.message()).isEqualTo("目標「基礎」重試率 67%，超過 50%");
        assertThat(c.severity()).isEqualTo(AlertSeverity.WARNING);

        assertThat(AlertRules.highRetryRate(goalId, "基礎", 2, 1)).as("剛好 50% 不算超過").isEmpty();
        assertThat(AlertRules.highRetryRate(goalId, "基礎", 1, 1)).as("樣本不足 2 個").isEmpty();
        assertThat(AlertRules.highRetryRate(goalId, "基礎", 0, 0)).isEmpty();
    }

    @Test
    void engineAlertsPersistUnderTheirOwnRuleNames() {
        Candidate esc = AlertRules.engineEscalation(runId, "G1-T2", "重試耗盡");
        assertThat(esc.rule()).isEqualTo(AlertRule.ENGINE_ESCALATION);
        assertThat(esc.severity()).isEqualTo(AlertSeverity.CRITICAL);
        assertThat(esc.subject()).isEqualTo("step:" + runId + ":G1-T2");
        assertThat(esc.message()).isEqualTo("引擎升級（ESCALATION）：重試耗盡");

        Candidate halt = AlertRules.engineTokenHalt(runId, "G1-T1", "超過門檻");
        assertThat(halt.rule()).isEqualTo(AlertRule.ENGINE_TOKEN_HALT);
        assertThat(halt.severity()).isEqualTo(AlertSeverity.WARNING);
        assertThat(halt.subject()).isEqualTo("step:G1-T1");
        assertThat(AlertRules.engineTokenHalt(runId, null, "x").subject()).isEqualTo("run:" + runId);
        assertThat(halt.message()).isEqualTo("引擎因 Token／額度門檻停機：超過門檻");
    }

    /**
     * C-7（QA O-14）：stepId 每個批次重新編號（G1-T1 在每一批都叫 G1-T1，甚至指向不同任務），去重對象若只有 stepId，
     * 第二批的升級會被第一批未確認的舊告警吞掉——使用者只剩 SSE 轉發、沒有告警列可看。
     */
    @Test
    void escalationsOfTwoRunsOnTheSameStepIdAreDifferentAlertSubjectsSoTheOldOneCannotSwallowTheNewOne() {
        UUID otherRun = UUID.randomUUID();

        Candidate first = AlertRules.engineEscalation(runId, "G1-T1", "第一批失敗");
        Candidate second = AlertRules.engineEscalation(otherRun, "G1-T1", "第二批失敗");

        assertThat(first.subject()).isEqualTo("step:" + runId + ":G1-T1");
        assertThat(second.subject()).isEqualTo("step:" + otherRun + ":G1-T1");
        assertThat(second.subject()).as("去重對象不同：兩批各自產生告警列").isNotEqualTo(first.subject());
        assertThat(AlertRules.engineEscalation(runId, "G1-T1", "同一批次同一步驟再次升級").subject())
                .as("同一批次的同一步驟仍是同一個去重對象").isEqualTo(first.subject());
        assertThat(AlertRules.engineEscalation(runId, "G1-T2", "同一批次的另一步驟").subject())
                .as("同一批次的不同步驟各自成立").isNotEqualTo(first.subject());
    }

    @Test
    void anEscalationWithoutAStepFallsBackToTheRunAsItsSubjectLikeTheTokenHalt() {
        assertThat(AlertRules.engineEscalation(runId, null, "x").subject()).isEqualTo("run:" + runId);
        assertThat(AlertRules.engineEscalation(runId, "  ", "x").subject()).isEqualTo("run:" + runId);
    }
}
