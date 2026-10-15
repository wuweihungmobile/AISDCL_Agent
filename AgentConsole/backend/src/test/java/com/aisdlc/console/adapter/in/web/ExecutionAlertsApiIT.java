package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.application.service.RunRegistry;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 告警規則的端到端行為（契約 §3.7；E2E-08；API-ALR-01～06）：Token 預算（警告／超額＋自動暫停）、單一任務上限、連續失敗、
 * 純時間型規則（任務逾時、Agent 無回應）與確認告警。去重：同一規則＋對象在被確認前不重複產生，被去重擋下的重複判定不再呼叫 {@code :pause}。
 */
class ExecutionAlertsApiIT extends AbstractExecutionIT {

    @Autowired
    private RunRegistry registry;

    private List<Map<String, Object>> alerts(String projectId, String runId) {
        return api.get(viewer(), "/api/v1/monitor/projects/" + projectId + "/alerts?runId=" + runId).read("$.data");
    }

    private List<Map<String, Object>> alertsOf(String projectId, String runId, String rule) {
        return alerts(projectId, runId).stream().filter(a -> rule.equals(a.get("rule"))).toList();
    }

    /**
     * 4 個步驟的專案；預算 2000：第 2 個 token 事件（累計 2480）同時達到警告與超額並要求暫停。迷你 Bridge 的
     * {@code completionDelayMillis} 讓 Console 對 token 事件的反應趕在該步驟 COMPLETED 之前到達，所以暫停決定性地落在第 2 步之後的邊界
     * （第 3 步還沒開始）。
     */
    private record BudgetRun(Fixture fixture, String run) {
    }

    private BudgetRun pausedByBudget(String name) {
        Fixture f = prjA(name, 4);
        createFixtureTask(f.g2(), "收尾", 4);
        MINI.manualSteps = true;
        MINI.completionDelayMillis = 250;
        String run = startRun(f.projectId(), Map.of("tokenBudget", 2000));
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        mini(run).release(1);
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t2())))).isTrue();
        mini(run).release(1);
        assertThat(awaitProjected(run, "PAUSED")).as("暫停落在第 2 步之後的邊界").isTrue();
        assertThat(alertsOf(f.projectId(), run, "TOKEN_BUDGET_EXCEEDED")).hasSize(1);
        return new BudgetRun(f, run);
    }

    // ── E2E-08：Token 預算 ──────────────────────────────────────────────────────────

    @Test
    void crossingTheBudgetRaisesWarningAndExceededAlertsAndRequestsExactlyOnePause() {
        BudgetRun b = pausedByBudget("e2e08");
        List<Map<String, Object>> warning = alertsOf(b.fixture().projectId(), b.run(), "TOKEN_BUDGET_WARNING");
        List<Map<String, Object>> exceeded = alertsOf(b.fixture().projectId(), b.run(), "TOKEN_BUDGET_EXCEEDED");
        assertThat(warning).hasSize(1);
        assertThat(warning.get(0).get("severity")).isEqualTo("WARNING");
        assertThat(warning.get(0).get("subject")).isEqualTo("run:" + b.run());
        assertThat((String) warning.get(0).get("message")).isEqualTo("Token 使用量已達預算的 124%（2480 / 2000）");
        assertThat(exceeded).hasSize(1);
        assertThat(exceeded.get(0).get("severity")).isEqualTo("CRITICAL");
        assertThat((String) exceeded.get(0).get("message")).isEqualTo("Token 使用量已超出預算（2480 / 2000），已要求暫停執行");
        assertThat(exceeded.get(0).get("acknowledged")).isEqualTo(false);
        assertThat(exceeded.get(0).get("runId")).isEqualTo(b.run());
        assertThat(exceeded.get(0).get("projectId")).isEqualTo(b.fixture().projectId());

        Resp detail = getRun(b.run());
        assertThat(detail.<String>read("$.data.status")).isEqualTo("PAUSED");
        assertThat(pendingReviews(b.run())).as("預算暫停不建審核項（沒有待決的閘）").isEmpty();
        assertThat(taskStatus(b.fixture().t1())).isEqualTo("COMPLETED");
        assertThat(taskStatus(b.fixture().t2())).isEqualTo("COMPLETED");
        assertThat(taskStatus(b.fixture().t3())).isEqualTo("QUEUED");
        assertThat(projectStatus(b.fixture().projectId())).isEqualTo("READY");
        assertThat(MINI.countRequests("POST /autoclaude/runs/" + b.run() + ":pause")).isEqualTo(1);
    }

    @Test
    void anUnacknowledgedAlertIsNotRaisedAgainSoResumingDoesNotPauseTheRunAgain() {
        BudgetRun b = pausedByBudget("e2e08-resume");
        assertThat(api.post(operator(), "/api/v1/executions/" + b.run() + "/resume").status()).isEqualTo(200);
        mini(b.run()).release(5);
        assertThat(awaitProjected(b.run(), "COMPLETED")).isTrue();

        assertThat(alertsOf(b.fixture().projectId(), b.run(), "TOKEN_BUDGET_EXCEEDED")).as("未確認前不重複產生")
                .hasSize(1);
        assertThat(alertsOf(b.fixture().projectId(), b.run(), "TOKEN_BUDGET_WARNING")).hasSize(1);
        assertThat(MINI.countRequests("POST /autoclaude/runs/" + b.run() + ":pause"))
                .as("被去重擋下的重複判定不再呼叫 :pause（AR-21）").isEqualTo(1);
    }

    @Test
    void afterAcknowledgingTheSameRuleCanBeRaisedAgainAndPausesAgain() {
        BudgetRun b = pausedByBudget("e2e08-ack");
        String exceeded = (String) alertsOf(b.fixture().projectId(), b.run(), "TOKEN_BUDGET_EXCEEDED").get(0).get("id");
        assertThat(api.post(operator(), "/api/v1/monitor/alerts/" + exceeded + "/acknowledge").status()).isEqualTo(204);
        assertThat(api.post(operator(), "/api/v1/executions/" + b.run() + "/resume").status()).isEqualTo(200);
        mini(b.run()).release(5);
        assertThat(awaitProjected(b.run(), "PAUSED")).as("第 3 步的 token 事件再次超額 → 再暫停在它之後的邊界").isTrue();

        List<Map<String, Object>> all = alertsOf(b.fixture().projectId(), b.run(), "TOKEN_BUDGET_EXCEEDED");
        assertThat(all).as("確認後同一規則＋對象可再產生新告警").hasSize(2);
        assertThat(all.stream().filter(a -> Boolean.FALSE.equals(a.get("acknowledged"))).count()).isEqualTo(1);
        assertThat(MINI.countRequests("POST /autoclaude/runs/" + b.run() + ":pause")).isEqualTo(2);
    }

    @Test
    void aSingleTaskLimitRaisesAPerTaskAlertAndPauses() {
        Fixture f = prjA("task-limit", 4);
        MINI.manualSteps = true;
        MINI.completionDelayMillis = 250;
        String run = startRun(f.projectId(), Map.of("scope", Map.of("mode", "ALL", "limits", Map.of("taskTokens", 1000))));
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        mini(run).release(1);

        assertThat(awaitProjected(run, "PAUSED")).as("單一任務超額 → 暫停在該任務之後的邊界").isTrue();
        List<Map<String, Object>> exceeded = alertsOf(f.projectId(), run, "TOKEN_BUDGET_EXCEEDED");
        assertThat(exceeded).hasSize(1);
        assertThat(exceeded.get(0).get("subject")).isEqualTo("task:" + f.t1());
        assertThat((String) exceeded.get(0).get("message")).isEqualTo("任務「初始化」Token 用量 1240 超過上限 1000，已要求暫停執行");
        assertThat(alertsOf(f.projectId(), run, "TOKEN_BUDGET_WARNING")).as("沒有整體預算就沒有警告").isEmpty();
        assertThat(taskStatus(f.t1())).isEqualTo("COMPLETED");
    }

    @Test
    void aBudgetThatIsNotReachedRaisesNothing() {
        Fixture f = prjA("budget-ok", 4);
        String run = startRun(f.projectId(), Map.of("tokenBudget", 100000));
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(alerts(f.projectId(), run)).isEmpty();
        assertThat(MINI.countRequests("POST /autoclaude/runs/" + run + ":pause")).isZero();
    }

    // ── 確認告警 ────────────────────────────────────────────────────────────────────

    @Test
    void acknowledgingIsIdempotentAndKeepsTheFirstAcknowledger() {
        BudgetRun b = pausedByBudget("ack");
        String projectId = b.fixture().projectId();
        String id = (String) alertsOf(projectId, b.run(), "TOKEN_BUDGET_WARNING").get(0).get("id");
        String path = "/api/v1/monitor/alerts/" + id + "/acknowledge";

        assertThat(api.post(viewer(), path).status()).isEqualTo(403);
        assertThat(api.post(null, path).status()).isEqualTo(401);
        assertThat(api.post(operator(), path).status()).isEqualTo(204);
        Map<String, Object> first = jdbc.queryForMap("select acknowledged, acknowledged_by, acknowledged_at "
                + "from console.alerts where id = ?", UUID.fromString(id));
        assertThat(first.get("acknowledged")).isEqualTo(true);
        assertThat(first.get("acknowledged_by")).isEqualTo("operator");
        Object firstAt = first.get("acknowledged_at");
        assertThat(firstAt).isNotNull();

        sleep(30);
        assertThat(api.post(admin(), path).status()).as("已確認者再次確認仍 204").isEqualTo(204);
        Map<String, Object> second = jdbc.queryForMap("select acknowledged_by, acknowledged_at from console.alerts "
                + "where id = ?", UUID.fromString(id));
        assertThat(second.get("acknowledged_by")).as("不改寫第一次的確認人").isEqualTo("operator");
        assertThat(second.get("acknowledged_at")).isEqualTo(firstAt);

        String base = "/api/v1/monitor/projects/" + projectId + "/alerts?runId=" + b.run();
        assertThat(api.get(viewer(), base + "&acknowledged=true").<List<String>>read("$.data[*].id"))
                .containsExactly(id);
        assertThat(api.get(viewer(), base + "&acknowledged=false").<List<String>>read("$.data[*].id"))
                .doesNotContain(id).hasSize(1);
        Resp shown = api.get(viewer(), base + "&acknowledged=true");
        assertThat(shown.<String>read("$.data[0].acknowledgedBy")).isEqualTo("operator");
        assertThat(shown.<String>read("$.data[0].acknowledgedAt")).isNotBlank();

        String missing = UUID.randomUUID().toString();
        Resp unknown = api.post(operator(), "/api/v1/monitor/alerts/" + missing + "/acknowledge");
        assertThat(unknown.status()).isEqualTo(404);
        assertThat(unknown.<String>read("$.message")).isEqualTo("告警不存在：" + missing);
        assertThat(api.post(operator(), "/api/v1/monitor/alerts/not-a-uuid/acknowledge").status()).isEqualTo(400);
    }

    @Test
    void alertListingFiltersByRunValidatesTheLimitAndReturnsNewestFirst() {
        BudgetRun b = pausedByBudget("list-alerts");
        String projectId = b.fixture().projectId();
        String base = "/api/v1/monitor/projects/" + projectId + "/alerts";
        assertThat(api.get(viewer(), base).<List<Object>>read("$.data")).hasSize(2);
        assertThat(api.get(viewer(), base + "?limit=1").<List<Object>>read("$.data")).hasSize(1);
        assertThat(api.get(viewer(), base + "?limit=0").status()).isEqualTo(400);
        assertThat(api.get(viewer(), base + "?limit=201").status()).isEqualTo(400);
        assertThat(api.get(viewer(), base + "?runId=" + UUID.randomUUID()).status()).isEqualTo(404);
        Fixture other = prjA("other-project", 4);
        assertThat(api.get(viewer(), "/api/v1/monitor/projects/" + other.projectId() + "/alerts?runId=" + b.run())
                .status()).as("runId 必須屬於該專案").isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/monitor/projects/" + UUID.randomUUID() + "/alerts").status())
                .isEqualTo(404);
        List<String> createdAt = api.get(viewer(), base).read("$.data[*].createdAt");
        assertThat(createdAt).isSortedAccordingTo(java.util.Comparator.reverseOrder());
    }

    // ── 連續失敗 ────────────────────────────────────────────────────────────────────

    @Test
    void twoConsecutiveFailedTasksInTheSameGoalRaiseTheAlertAndAnnotateTheEscalatedReview() {
        Fixture f = prjA("consecutive", 4);
        setting("monitor", "alertConsecutiveFailures", "2");
        // 前一個任務先前就失敗過（它的 updated_at 早於這一輪）；這一輪只跑 T2，T2 又失敗 → 該目標最近 2 個終局結果都是失敗
        jdbc.update("update console.tasks set status = 'FAILED', updated_at = now() - interval '1 hour' where id = ?",
                UUID.fromString(f.t1()));
        MINI.failStepIds.add("G1-T1"); // step_id 每個批次獨立編號：只選 T2 時它就是這一批的 G1-T1（契約 §3.4.4）
        String run = startRun(f.projectId(), Map.of("scope", Map.of("mode", "SELECTED", "taskIds", List.of(f.t2()))));
        assertThat(awaitProjected(run, "FAILED")).isTrue();

        List<Map<String, Object>> alert = alertsOf(f.projectId(), run, "CONSECUTIVE_FAILURES");
        assertThat(alert).hasSize(1);
        assertThat(alert.get(0).get("severity")).isEqualTo("CRITICAL");
        assertThat(alert.get(0).get("subject")).isEqualTo("goal:" + f.g1());
        assertThat(alert.get(0).get("message")).isEqualTo("目標「基礎」連續 2 個任務失敗");
        assertThat((String) pendingReviews(run).get(0).get("reason"))
                .endsWith("（連續 2 個任務失敗，已觸發 CONSECUTIVE_FAILURES 告警）");
    }

    @Test
    void aSuccessBetweenTheFailuresMeansNoConsecutiveFailureAlert() {
        Fixture f = prjA("not-consecutive", 4);
        setting("monitor", "alertConsecutiveFailures", "2");
        jdbc.update("update console.tasks set status = 'COMPLETED', completed_at = now() - interval '1 hour', "
                + "updated_at = now() - interval '1 hour' where id = ?", UUID.fromString(f.t1()));
        MINI.failStepIds.add("G1-T1"); // T1 已完成不在範圍內，T2 是這一批的 G1-T1
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "FAILED")).isTrue();
        assertThat(alertsOf(f.projectId(), run, "CONSECUTIVE_FAILURES")).isEmpty();
    }

    // ── 純時間型規則（30 秒排程 tick）──────────────────────────────────────────────────

    @Test
    void aTaskRunningLongerThanTheTimeoutTimesTheMultiplierRaisesTheDurationAlertOnce() {
        Fixture f = prjA("duration", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();

        ticker.tick();
        assertThat(alertsOf(f.projectId(), run, "TASK_DURATION_EXCEEDED")).as("剛開始的任務沒有逾時").isEmpty();

        jdbc.update("update console.tasks set started_at = now() - interval '2000 seconds' where id = ?",
                UUID.fromString(f.t1()));
        ticker.tick();
        List<Map<String, Object>> alerts = alertsOf(f.projectId(), run, "TASK_DURATION_EXCEEDED");
        assertThat(alerts).hasSize(1);
        assertThat(alerts.get(0).get("severity")).isEqualTo("WARNING");
        assertThat(alerts.get(0).get("subject")).isEqualTo("task:" + f.t1());
        assertThat((String) alerts.get(0).get("message")).startsWith("任務「初始化」已執行 2000 秒，超過門檻 1200 秒（2 倍）");
        ticker.tick();
        assertThat(alertsOf(f.projectId(), run, "TASK_DURATION_EXCEEDED")).as("未確認前不重複").hasSize(1);
    }

    @Test
    void aSilentRunRaisesTheUnresponsiveAlertOnlyWhenTheHealthProbeAlsoFails() {
        Fixture f = prjA("unresponsive", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        registry.locked(UUID.fromString(run), () -> registry.runtime(UUID.fromString(run)).lastEventAt =
                Instant.now().minusSeconds(1000));

        ticker.tick();
        assertThat(alertsOf(f.projectId(), run, "AGENT_UNRESPONSIVE")).as("單純長步驟（探測正常）不告警").isEmpty();

        setting("autoclaude", "engineUrl", "http://127.0.0.1:1");
        ticker.tick();
        List<Map<String, Object>> alerts = alertsOf(f.projectId(), run, "AGENT_UNRESPONSIVE");
        assertThat(alerts).hasSize(1);
        assertThat(alerts.get(0).get("severity")).isEqualTo("CRITICAL");
        assertThat(alerts.get(0).get("subject")).isEqualTo("run:" + run);
        assertThat(alerts.get(0).get("message")).isEqualTo("Agent 已超過 300 秒無回應");
    }
}
