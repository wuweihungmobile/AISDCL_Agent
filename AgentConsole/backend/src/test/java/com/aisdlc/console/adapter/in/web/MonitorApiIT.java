package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.service.BridgeHealthMonitor.Probe;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Edge;
import com.aisdlc.console.domain.model.execution.DagSnapshot.EdgeKind;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.DagSnapshot.NodeKind;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 專案監控 API（Phase 5；契約 §1.3、§3.8；API-MON-01～07、US-M-01～10）。以資料庫直接種下<b>固定時間</b>的批次、步驟、Token 樣本、
 * 告警與審核項，逐項對照契約 §3.8 的公式（視窗 {@code W}、前一視窗 {@code W'}、四捨五入、null 規則）——數字都是手算的期望值，
 * 不是從實作回頭推的。
 *
 * <pre>
 * 種子（UTC）：視窗 W＝[2026-10-14, 2026-10-15)，前一視窗 W'＝[2026-10-13, 2026-10-14)
 *   R1（run#1，FAILED，預算 10,000，已用 2,000）10-13：T1 STARTED 10:00／COMPLETED 10:10；T2 STARTED 10:20／RETRYING 10:25／FAILED 10:30
 *   R2（run#2，COMPLETED，預算 8,000，已用 3,720）10-14：T2 STARTED 09:00／COMPLETED 09:30；T3 STARTED 09:40／RETRYING 09:45、09:50／COMPLETED 10:00
 *   Token 樣本：R1 10-13 10:10 +1000、10:30 +1000；R2 10-14 09:30、09:50、10:00 各 +1240
 * </pre>
 */
class MonitorApiIT extends AbstractExecutionIT {

    private static final String W = "from=2026-10-14T00:00:00Z&to=2026-10-15T00:00:00Z";
    private static final String BOTH_DAYS = "from=2026-10-13T00:00:00Z&to=2026-10-15T00:00:00Z";

    @Autowired
    private ExecutionRunRepository runRepository;

    private record Seed(Fixture f, UUID r1, UUID r2) {
    }

    private static OffsetDateTime at(String iso) {
        return OffsetDateTime.parse(iso);
    }

    private void taskRow(String taskId, String status, String started, String completed, int retries, long tokens) {
        jdbc.update("update console.tasks set status = ?, started_at = ?, completed_at = ?, retry_count = ?, "
                + "actual_tokens = ? where id = ?", status, started == null ? null : at(started),
                completed == null ? null : at(completed), retries, tokens, UUID.fromString(taskId));
    }

    private void step(UUID run, String taskId, int seq, String status, String time, String stepId, int attempt,
                      String error, String taskName) {
        jdbc.update("insert into console.execution_steps (id, run_id, task_id, step_number, action, status, input, "
                + "error_message, timestamp) values (?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?)", UUID.randomUUID(), run,
                UUID.fromString(taskId), seq, stepId + ": " + taskName, status,
                "{\"step_id\":\"" + stepId + "\",\"position\":1,\"attempt\":" + attempt + "}", error, at(time));
    }

    private void sample(UUID run, int seq, String time, long used, long delta, String taskId) {
        jdbc.update("insert into console.run_token_samples (run_id, seq, ts, tokens_used, delta, context_pct, task_id) "
                + "values (?, ?, ?, ?, ?, 0.6, ?)", run, seq, at(time), used, delta, UUID.fromString(taskId));
    }

    private UUID run(Fixture f, int number, String started, String completed, String status, long budget, long used,
                     List<String> taskIds) {
        List<Node> nodes = new ArrayList<>();
        nodes.add(new Node(UUID.fromString(f.g1()), NodeKind.GOAL, "基礎", null, null, 1));
        nodes.add(new Node(UUID.fromString(f.g2()), NodeKind.GOAL, "核心", null, null, 2));
        List<Edge> edges = new ArrayList<>();
        edges.add(new Edge(UUID.fromString(f.g1()), UUID.fromString(f.g2()), EdgeKind.DEPENDENCY));
        Map<String, String[]> info = Map.of(f.t1(), new String[] {"初始化", f.g1(), "G1-T1"}, f.t2(),
                new String[] {"設定", f.g1(), "G1-T2"}, f.t3(), new String[] {"實作", f.g2(), "G2-T1"});
        int position = 1;
        for (String taskId : taskIds) {
            String[] i = info.get(taskId);
            nodes.add(new Node(UUID.fromString(taskId), NodeKind.TASK, i[0], UUID.fromString(i[1]),
                    taskIds.size() == 3 ? i[2] : (taskId.equals(f.t2()) ? "G1-T1" : "G2-T1"), position++));
        }
        ExecutionRun run = runRepository.insert(new ExecutionRun(UUID.randomUUID(), UUID.fromString(f.projectId()),
                number, RunStatus.INITIALIZING, 4, RunScope.all(), 0L, budget, at(started).toInstant(), null,
                new DagSnapshot(nodes, edges), 0, null, null));
        jdbc.update("update console.execution_runs set status = ?, total_tokens_used = ?, completed_at = ?, "
                + "bridge_instance = 'seed' where id = ?", status, used, at(completed), run.id());
        return run.id();
    }

    private Seed seed() {
        Fixture f = prjA("mon", 4);
        taskRow(f.t1(), "COMPLETED", "2026-10-13T10:00:00Z", "2026-10-13T10:10:00Z", 0, 1000);
        taskRow(f.t2(), "COMPLETED", "2026-10-14T09:00:00Z", "2026-10-14T09:30:00Z", 1, 2480);
        taskRow(f.t3(), "COMPLETED", "2026-10-14T09:40:00Z", "2026-10-14T10:00:00Z", 2, 1240);
        jdbc.update("update console.goals set status = 'COMPLETED' where id = ?", UUID.fromString(f.g1()));
        jdbc.update("update console.goals set status = 'IN_PROGRESS' where id = ?", UUID.fromString(f.g2()));
        setProjectStatus(f.projectId(), "COMPLETED");
        // 全域專案完成率的分母：另有一個 DRAFT（計入）與一個 ARCHIVED（不計入）
        createProject("draft-one");
        setProjectStatus(createProject("archived-one"), "ARCHIVED");

        UUID r1 = run(f, 1, "2026-10-13T09:00:00Z", "2026-10-13T11:00:00Z", "FAILED", 10000, 2000,
                List.of(f.t1(), f.t2(), f.t3()));
        step(r1, f.t1(), 1, "STARTED", "2026-10-13T10:00:00Z", "G1-T1", 1, null, "初始化");
        step(r1, f.t1(), 2, "COMPLETED", "2026-10-13T10:10:00Z", "G1-T1", 1, null, "初始化");
        step(r1, f.t2(), 3, "STARTED", "2026-10-13T10:20:00Z", "G1-T2", 1, null, "設定");
        step(r1, f.t2(), 4, "RETRYING", "2026-10-13T10:25:00Z", "G1-T2", 2, null, "設定");
        step(r1, f.t2(), 5, "FAILED", "2026-10-13T10:30:00Z", "G1-T2", 2, "boom", "設定");
        sample(r1, 1, "2026-10-13T10:10:00Z", 1000, 1000, f.t1());
        sample(r1, 2, "2026-10-13T10:30:00Z", 2000, 1000, f.t2());

        UUID r2 = run(f, 2, "2026-10-14T08:50:00Z", "2026-10-14T10:00:00Z", "COMPLETED", 8000, 3720,
                List.of(f.t2(), f.t3()));
        step(r2, f.t2(), 1, "STARTED", "2026-10-14T09:00:00Z", "G1-T1", 1, null, "設定");
        step(r2, f.t2(), 2, "COMPLETED", "2026-10-14T09:30:00Z", "G1-T1", 1, null, "設定");
        step(r2, f.t3(), 3, "STARTED", "2026-10-14T09:40:00Z", "G2-T1", 1, null, "實作");
        step(r2, f.t3(), 4, "RETRYING", "2026-10-14T09:45:00Z", "G2-T1", 2, null, "實作");
        step(r2, f.t3(), 5, "RETRYING", "2026-10-14T09:50:00Z", "G2-T1", 3, null, "實作");
        step(r2, f.t3(), 6, "COMPLETED", "2026-10-14T10:00:00Z", "G2-T1", 3, null, "實作");
        sample(r2, 1, "2026-10-14T09:30:00Z", 1240, 1240, f.t2());
        sample(r2, 2, "2026-10-14T09:50:00Z", 2480, 1240, f.t3());
        sample(r2, 3, "2026-10-14T10:00:00Z", 3720, 1240, f.t3());

        // 健康探測（只算視窗內）：3 成功 1 失敗＝75.0
        health.record(new Probe(Instant.parse("2026-10-14T01:00:00Z"), true));
        health.record(new Probe(Instant.parse("2026-10-14T02:00:00Z"), true));
        health.record(new Probe(Instant.parse("2026-10-14T03:00:00Z"), true));
        health.record(new Probe(Instant.parse("2026-10-14T04:00:00Z"), false));

        // 告警與審核項（日誌衍生用）
        jdbc.update("insert into console.alerts (id, project_id, run_id, rule, severity, subject, message, created_at) "
                + "values (?, ?, ?, 'TOKEN_BUDGET_WARNING', 'WARNING', ?, ?, ?)", UUID.randomUUID(),
                UUID.fromString(f.projectId()), r2, "run:" + r2, "Token 使用量已達預算的 100%（8000 / 8000）",
                at("2026-10-14T09:50:00Z"));
        jdbc.update("insert into console.alerts (id, project_id, run_id, rule, severity, subject, message, created_at, "
                + "acknowledged, acknowledged_by, acknowledged_at) values (?, ?, ?, 'ENGINE_ESCALATION', 'CRITICAL', "
                + "'step:G1-T2', ?, ?, true, 'operator', ?)", UUID.randomUUID(), UUID.fromString(f.projectId()), r1,
                "引擎升級（ESCALATION）：boom", at("2026-10-13T10:30:30Z"), at("2026-10-13T12:00:00Z"));
        jdbc.update("insert into console.review_requests (id, run_id, task_id, goal_id, kind, status, reason, "
                + "requested_at, decided_by, decided_at) values (?, ?, ?, ?, 'ESCALATED', 'RETRIED', ?, ?, 'operator', ?)",
                UUID.randomUUID(), r1, UUID.fromString(f.t2()), UUID.fromString(f.g1()), "任務「設定」重試 1 次仍失敗",
                at("2026-10-13T10:30:40Z"), at("2026-10-13T10:40:00Z"));
        return new Seed(f, r1, r2);
    }

    private static String metrics(Seed s, String query) {
        return "/api/v1/monitor/projects/" + s.f().projectId() + "/metrics?" + query;
    }

    private static void expect(Resp resp, String kpi, Number value, Number previous, Number delta) {
        assertThat(resp.<Number>read("$.data." + kpi + ".value")).as(kpi + ".value").isEqualTo(value);
        assertThat(resp.<Object>read("$.data." + kpi + ".previousValue")).as(kpi + ".previousValue").isEqualTo(previous);
        assertThat(resp.<Object>read("$.data." + kpi + ".delta")).as(kpi + ".delta").isEqualTo(delta);
    }

    // ── §3.8.1 KPI 公式（整個專案）─────────────────────────────────────────────────────

    @Test
    void everyKpiOfTheWholeProjectFollowsTheContractFormulaWithThePreviousWindowComparison() {
        Seed s = seed();
        Resp resp = api.get(viewer(), metrics(s, W));
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.projectId")).isEqualTo(s.f().projectId());
        assertThat(resp.has("$.data.runId")).isFalse();
        assertThat(resp.<String>read("$.data.from")).isEqualTo("2026-10-14T00:00:00Z");
        assertThat(resp.<String>read("$.data.to")).isEqualTo("2026-10-15T00:00:00Z");
        assertThat(resp.<String>read("$.data.generatedAt")).isNotBlank();

        expect(resp, "taskCompletionRate", 100.0, 33.3, 66.7);
        expect(resp, "taskSuccessRate", 100.0, 50.0, 50.0);
        expect(resp, "retryRate", 50.0, 50.0, 0.0);
        expect(resp, "averageRetryCount", 1.0, 0.5, 0.5);
        expect(resp, "totalTokens", 3720, 2000, 1720);
        expect(resp, "averageTaskDurationSec", 1500.0, 600.0, 900.0);
        expect(resp, "tokenBudgetUsageRate", 31.8, null, null);
        expect(resp, "projectCompletionRate", 50.0, null, null);
        expect(resp, "goalAchievementRate", 50.0, null, null);
        expect(resp, "agentAvailability", 75.0, null, null);
        assertThat(resp.<Number>read("$.data.tokenBudget")).isEqualTo(18000);
    }

    @Test
    void theDistributionsAlwaysListAllElevenStatusesAndSixRetryBucketsAndTheTopDurations() {
        Seed s = seed();
        Resp resp = api.get(viewer(), metrics(s, W));
        Map<String, Integer> status = resp.read("$.data.taskStatusDistribution");
        assertThat(status).containsOnlyKeys("PENDING", "QUEUED", "BLOCKED", "RUNNING", "VALIDATING", "COMPLETED",
                "FAILED", "ESCALATED", "PAUSED", "SKIPPED", "CANCELLED");
        assertThat(status.get("COMPLETED")).isEqualTo(3);
        assertThat(status.entrySet().stream().filter(e -> !e.getKey().equals("COMPLETED")).mapToInt(Map.Entry::getValue)
                .sum()).isZero();
        List<Map<String, Object>> buckets = resp.read("$.data.retryDistribution");
        assertThat(buckets).extracting(b -> b.get("retries")).containsExactly(0, 1, 2, 3, 4, 5);
        assertThat(buckets).extracting(b -> b.get("tasks")).containsExactly(1, 1, 1, 0, 0, 0);
        List<Map<String, Object>> durations = resp.read("$.data.taskDurations");
        assertThat(durations).extracting(d -> d.get("taskName")).as("視窗內完成的任務，由長到短").containsExactly("設定", "實作");
        assertThat(durations).extracting(d -> d.get("durationSec")).containsExactly(1800.0, 1200.0);
        assertThat(durations).extracting(d -> d.get("goalName")).containsExactly("基礎", "核心");
        assertThat(durations.get(0).get("taskId")).isEqualTo(s.f().t2());
    }

    @Test
    void retryBucketsFoldFiveOrMoreIntoTheLastBucket() {
        Seed s = seed();
        jdbc.update("update console.tasks set retry_count = 9 where id = ?", UUID.fromString(s.f().t1()));
        jdbc.update("update console.tasks set retry_count = 5 where id = ?", UUID.fromString(s.f().t2()));
        List<Map<String, Object>> buckets = api.get(viewer(), metrics(s, W)).read("$.data.retryDistribution");
        assertThat(buckets).extracting(b -> b.get("tasks")).containsExactly(0, 0, 1, 0, 0, 2);
    }

    @Test
    void aSingleRunNarrowsTheScopeToItsDagAndTheTasksOutsideItDoNotCount() {
        Seed s = seed();
        Resp resp = api.get(viewer(), metrics(s, W + "&runId=" + s.r2()));
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.runId")).isEqualTo(s.r2().toString());
        expect(resp, "taskCompletionRate", 100.0, 0.0, 100.0);
        expect(resp, "taskSuccessRate", 100.0, null, null);
        expect(resp, "retryRate", 50.0, null, null);
        expect(resp, "averageRetryCount", 1.0, null, null);
        expect(resp, "totalTokens", 3720, 0, 3720);
        expect(resp, "averageTaskDurationSec", 1500.0, null, null);
        expect(resp, "tokenBudgetUsageRate", 46.5, null, null);
        expect(resp, "goalAchievementRate", 50.0, null, null);
        assertThat(resp.<Number>read("$.data.tokenBudget")).isEqualTo(8000);
        Map<String, Integer> status = resp.read("$.data.taskStatusDistribution");
        assertThat(status.get("COMPLETED")).as("R2 的 DAG 只有 T2、T3").isEqualTo(2);
    }

    @Test
    void whenNothingCanBeComputedTheValuesAreNullAndTheDistributionsStayComplete() {
        Fixture empty = prjA("empty", 4);
        jdbc.update("delete from console.tasks where goal_id in (?, ?)", UUID.fromString(empty.g1()),
                UUID.fromString(empty.g2()));
        Resp resp = api.get(viewer(), "/api/v1/monitor/projects/" + empty.projectId() + "/metrics?" + W);
        assertThat(resp.status()).isEqualTo(200);
        for (String kpi : List.of("taskCompletionRate", "taskSuccessRate", "retryRate", "averageRetryCount",
                "tokenBudgetUsageRate", "averageTaskDurationSec")) {
            assertThat(resp.<Object>read("$.data." + kpi + ".value")).as(kpi).isNull();
            assertThat(resp.<Object>read("$.data." + kpi + ".previousValue")).isNull();
            assertThat(resp.<Object>read("$.data." + kpi + ".delta")).isNull();
        }
        assertThat(resp.<Number>read("$.data.totalTokens.value")).as("沒有樣本的 Token 總和是 0，不是 null").isEqualTo(0);
        assertThat(resp.<Object>read("$.data.tokenBudget")).isNull();
        assertThat(resp.<List<Object>>read("$.data.taskDurations")).isEmpty();
        assertThat(resp.<Map<String, Integer>>read("$.data.taskStatusDistribution")).hasSize(11);
        assertThat(resp.<List<Object>>read("$.data.retryDistribution")).hasSize(6);
    }

    @Test
    void aRunWithoutABudgetIsLeftOutOfTheBudgetUsageAndTheTrendBudgetLineIsNull() {
        Seed s = seed();
        jdbc.update("update console.execution_runs set token_budget = null where id = ?", s.r1());
        Resp usage = api.get(viewer(), metrics(s, W));
        expect(usage, "tokenBudgetUsageRate", 46.5, null, null);
        assertThat(usage.<Number>read("$.data.tokenBudget")).isEqualTo(8000);
        Resp trend = api.get(viewer(), "/api/v1/monitor/projects/" + s.f().projectId()
                + "/token-trend?" + BOTH_DAYS + "&bucket=DAY");
        assertThat(trend.<Object>read("$.data[0].budget")).isNull();
        assertThat(trend.<Map<String, Object>>read("$.data[0]")).containsKey("budget");
        assertThat(trend.<Number>read("$.data[1].budget")).isEqualTo(8000);
    }

    // ── §3.8.2 趨勢 ──────────────────────────────────────────────────────────────────

    @Test
    void theTokenTrendBucketsTheSamplesAccumulatesFromTheWindowStartAndCarriesTheBudgetLine() {
        Seed s = seed();
        String base = "/api/v1/monitor/projects/" + s.f().projectId() + "/token-trend?";
        Resp hourly = api.get(viewer(), base + W + "&bucket=HOUR");
        assertThat(hourly.status()).isEqualTo(200);
        assertThat(hourly.<List<String>>read("$.data[*].bucketStart")).containsExactly("2026-10-14T09:00:00Z",
                "2026-10-14T10:00:00Z");
        assertThat(hourly.<List<Number>>read("$.data[*].tokens")).containsExactly(2480, 1240);
        assertThat(hourly.<List<Number>>read("$.data[*].cumulativeTokens")).containsExactly(2480, 3720);
        assertThat(hourly.<List<Number>>read("$.data[*].budget")).containsExactly(8000, 8000);

        Resp daily = api.get(viewer(), base + BOTH_DAYS + "&bucket=DAY");
        assertThat(daily.<List<String>>read("$.data[*].bucketStart")).as("沒有資料的桶不補零")
                .containsExactly("2026-10-13T00:00:00Z", "2026-10-14T00:00:00Z");
        assertThat(daily.<List<Number>>read("$.data[*].tokens")).containsExactly(2000, 3720);
        assertThat(daily.<List<Number>>read("$.data[*].cumulativeTokens")).containsExactly(2000, 5720);
        assertThat(daily.<List<Number>>read("$.data[*].budget")).as("各批次自己的預算").containsExactly(10000, 8000);

        assertThat(api.get(viewer(), base + W + "&runId=" + s.r1()).<List<Object>>read("$.data"))
                .as("R1 在這個視窗內沒有樣本").isEmpty();
    }

    @Test
    void theDefaultBucketIsHourlyForWindowsUpTo48HoursAndDailyBeyondThat() {
        Seed s = seed();
        String base = "/api/v1/monitor/projects/" + s.f().projectId() + "/token-trend?";
        assertThat(api.get(viewer(), base + "from=2026-10-13T12:00:00Z&to=2026-10-15T12:00:00Z")
                .<List<String>>read("$.data[*].bucketStart")).as("恰 48 小時用 HOUR").containsExactly(
                "2026-10-14T09:00:00Z", "2026-10-14T10:00:00Z");
        assertThat(api.get(viewer(), base + "from=2026-10-13T09:59:00Z&to=2026-10-15T12:00:00Z")
                .<List<String>>read("$.data[*].bucketStart")).as("超過 48 小時（50 小時 1 分）用 DAY").containsExactly(
                "2026-10-13T00:00:00Z", "2026-10-14T00:00:00Z");
    }

    @Test
    void theTaskTrendCountsTheStepRowsPerStatusInEachBucket() {
        Seed s = seed();
        Resp resp = api.get(viewer(), "/api/v1/monitor/projects/" + s.f().projectId() + "/task-trend?" + W
                + "&bucket=HOUR");
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<String>>read("$.data[*].bucketStart")).containsExactly("2026-10-14T09:00:00Z",
                "2026-10-14T10:00:00Z");
        assertThat(resp.<List<Number>>read("$.data[*].started")).containsExactly(2, 0);
        assertThat(resp.<List<Number>>read("$.data[*].completed")).containsExactly(1, 1);
        assertThat(resp.<List<Number>>read("$.data[*].failed")).containsExactly(0, 0);
        assertThat(resp.<List<Number>>read("$.data[*].retried")).containsExactly(2, 0);
        Resp both = api.get(viewer(), "/api/v1/monitor/projects/" + s.f().projectId() + "/task-trend?" + BOTH_DAYS
                + "&bucket=DAY");
        assertThat(both.<List<String>>read("$.data[*].bucketStart")).containsExactly("2026-10-13T00:00:00Z",
                "2026-10-14T00:00:00Z");
        assertThat(both.<List<Number>>read("$.data[*].failed")).containsExactly(1, 0);
    }

    // ── 視窗與參數驗證 ──────────────────────────────────────────────────────────────────

    @Test
    void anInvalidTimeRangeIs400WithTheReasonAndTheOffendingRangeInDetails() {
        Seed s = seed();
        String base = "/api/v1/monitor/projects/" + s.f().projectId();
        Resp reversed = api.get(viewer(), base + "/metrics?from=2026-10-15T00:00:00Z&to=2026-10-14T00:00:00Z");
        assertThat(reversed.status()).isEqualTo(400);
        assertThat(reversed.<String>read("$.reason")).isEqualTo(ErrorReasons.TIME_RANGE_INVALID);
        assertThat(reversed.<String>read("$.details.from")).isEqualTo("2026-10-15T00:00:00Z");
        assertThat(reversed.<String>read("$.details.to")).isEqualTo("2026-10-14T00:00:00Z");
        assertThat(api.get(viewer(), base + "/metrics?from=2026-10-14T00:00:00Z&to=2026-10-14T00:00:00Z").status())
                .as("from 必須早於 to").isEqualTo(400);

        Resp tooLong = api.get(viewer(), base + "/metrics?from=2025-10-14T00:00:00Z&to=2026-10-16T00:00:00Z");
        assertThat(tooLong.status()).as("視窗上限 366 天").isEqualTo(400);
        assertThat(tooLong.<String>read("$.reason")).isEqualTo(ErrorReasons.TIME_RANGE_INVALID);
        assertThat(api.get(viewer(), base + "/metrics?from=2025-10-15T00:00:00Z&to=2026-10-16T00:00:00Z").status())
                .as("恰 366 天可以").isEqualTo(200);

        Resp buckets = api.get(viewer(), base + "/token-trend?from=2026-08-01T00:00:00Z&to=2026-10-01T00:00:00Z&bucket=HOUR");
        assertThat(buckets.status()).as("桶數超過 1,000").isEqualTo(400);
        assertThat(buckets.<String>read("$.reason")).isEqualTo(ErrorReasons.TIME_RANGE_INVALID);
        assertThat(api.get(viewer(), base + "/token-trend?from=2026-08-01T00:00:00Z&to=2026-10-01T00:00:00Z&bucket=DAY")
                .status()).isEqualTo(200);
        assertThat(api.get(viewer(), base + "/task-trend?" + W + "&bucket=WEEK").status()).isEqualTo(400);
    }

    @Test
    void timestampsMayBeWrittenWithAnOffsetEvenWhenThePlusSignWasNotUrlEncoded() {
        Seed s = seed();
        String base = metrics(s, "");
        String path = "/api/v1/monitor/projects/" + s.f().projectId() + "/metrics";
        Resp encodedPlus = api.send(viewer(), MockMvcRequestBuilders.get(path)
                .param("from", "2026-10-14T08:00:00+08:00").param("to", "2026-10-15T08:00:00+08:00"));
        assertThat(encodedPlus.status()).as("正確編碼的 +（參數值就是 +）").isEqualTo(200);
        assertThat(encodedPlus.<String>read("$.data.from")).isEqualTo("2026-10-14T00:00:00Z");
        Resp decodedSpace = api.send(viewer(), MockMvcRequestBuilders.get(path)
                .param("from", "2026-10-14T08:00:00 08:00").param("to", "2026-10-15T08:00:00 08:00"));
        assertThat(decodedSpace.status()).as("未編碼的 + 被容器解碼成空白之後的樣子，仍當成 offset").isEqualTo(200);
        assertThat(decodedSpace.<String>read("$.data.from")).isEqualTo("2026-10-14T00:00:00Z");
        assertThat(decodedSpace.<String>read("$.data.to")).isEqualTo("2026-10-15T00:00:00Z");
        Resp bad = api.get(viewer(), base + "from=yesterday&to=2026-10-15T00:00:00Z");
        assertThat(bad.status()).isEqualTo(400);
        assertThat(bad.errorFields()).contains("from");
        assertThat(api.get(viewer(), base + "from=2026-10-14T00:00:00&to=2026-10-15T00:00:00Z").status())
                .as("缺 offset").isEqualTo(400);
    }

    @Test
    void aLiteralPlusInTheQueryStringOverRealHttpIsStillReadAsAnOffset() throws Exception {
        Seed s = seed();
        java.net.http.HttpRequest request = java.net.http.HttpRequest.newBuilder(java.net.URI.create(baseUrl()
                + "/api/v1/monitor/projects/" + s.f().projectId()
                + "/metrics?from=2026-10-14T08:00:00+08:00&to=2026-10-15T08:00:00+08:00"))
                .header("Authorization", "Bearer " + viewer()).GET().build();
        java.net.http.HttpResponse<String> response = java.net.http.HttpClient.newHttpClient().send(request,
                java.net.http.HttpResponse.BodyHandlers.ofString());
        assertThat(response.statusCode()).isEqualTo(200);
        assertThat(response.body()).contains("\"from\":\"2026-10-14T00:00:00Z\"");
        java.net.http.HttpRequest encoded = java.net.http.HttpRequest.newBuilder(java.net.URI.create(baseUrl()
                + "/api/v1/monitor/projects/" + s.f().projectId()
                + "/metrics?from=2026-10-14T08:00:00%2B08:00&to=2026-10-15T08:00:00%2B08:00"))
                .header("Authorization", "Bearer " + viewer()).GET().build();
        assertThat(java.net.http.HttpClient.newHttpClient().send(encoded, java.net.http.HttpResponse.BodyHandlers
                .ofString()).body()).contains("\"from\":\"2026-10-14T00:00:00Z\"");
    }

    @Test
    void theDefaultWindowIsTheLast24HoursEndingNow() {
        Seed s = seed();
        Instant before = Instant.now();
        Resp resp = api.get(viewer(), metrics(s, ""));
        Instant to = Instant.parse(resp.read("$.data.to"));
        Instant from = Instant.parse(resp.read("$.data.from"));
        assertThat(Duration.between(from, to)).isEqualTo(Duration.ofHours(24));
        assertThat(to).isBetween(before.minusSeconds(1), Instant.now().plusSeconds(1));
        Resp onlyFrom = api.get(viewer(), metrics(s, "from=2026-10-13T00:00:00Z&to=2026-10-14T00:00:00Z"));
        assertThat(onlyFrom.<Number>read("$.data.totalTokens.value")).isEqualTo(2000);
    }

    @Test
    void unknownProjectsRunsOfOtherProjectsAndMalformedIdsAreRejectedOnEveryMonitorEndpoint() {
        Seed s = seed();
        Fixture other = prjA("another", 4);
        String unknown = UUID.randomUUID().toString();
        for (String tail : List.of("metrics", "token-trend", "task-trend", "alerts", "logs", "report")) {
            assertThat(api.get(viewer(), "/api/v1/monitor/projects/" + unknown + "/" + tail).status()).as(tail)
                    .isEqualTo(404);
            Resp foreignRun = api.get(viewer(), "/api/v1/monitor/projects/" + other.projectId() + "/" + tail + "?runId="
                    + s.r1());
            assertThat(foreignRun.status()).as(tail + " 的 runId 屬於別的專案").isEqualTo(404);
            assertThat(foreignRun.<String>read("$.message")).isEqualTo("執行批次不存在或不屬於此專案：" + s.r1());
            assertThat(api.get(viewer(), "/api/v1/monitor/projects/not-a-uuid/" + tail).status()).as(tail).isEqualTo(400);
            assertThat(api.get(viewer(), "/api/v1/monitor/projects/" + s.f().projectId() + "/" + tail + "?runId=bad")
                    .status()).as(tail).isEqualTo(400);
            assertThat(api.get(null, "/api/v1/monitor/projects/" + s.f().projectId() + "/" + tail).status()).as(tail)
                    .isEqualTo(401);
        }
        assertThat(api.get(viewer(), "/api/v1/monitor/projects/" + unknown + "/metrics").<String>read("$.message"))
                .isEqualTo("專案不存在或已刪除：" + unknown);
    }

    // ── §3.8.3 日誌 ───────────────────────────────────────────────────────────────────

    /** 以請求參數（不經 URL 樣板的二次編碼）帶關鍵字：{@code %}、{@code _} 這類字元要原樣送到伺服器。 */
    private List<Map<String, Object>> keyword(Seed s, String q) {
        Resp resp = api.send(viewer(), MockMvcRequestBuilders.get("/api/v1/monitor/projects/" + s.f().projectId()
                + "/logs").param("from", "2026-10-13T00:00:00Z").param("to", "2026-10-15T00:00:00Z").param("q", q)
                .param("size", "200"));
        assertThat(resp.status()).isEqualTo(200);
        return resp.read("$.data.content");
    }

    private List<Map<String, Object>> logs(Seed s, String query) {
        Resp resp = api.get(viewer(), "/api/v1/monitor/projects/" + s.f().projectId() + "/logs?" + BOTH_DAYS + query);
        assertThat(resp.status()).isEqualTo(200);
        return resp.read("$.data.content");
    }

    @Test
    void logsAreDerivedFromStepsRunsAlertsAndReviewsWithStableIdsLevelsAndTemplates() {
        Seed s = seed();
        Resp resp = api.get(viewer(), "/api/v1/monitor/projects/" + s.f().projectId() + "/logs?" + BOTH_DAYS + "&size=200");
        List<Map<String, Object>> all = resp.read("$.data.content");
        assertThat(all).hasSize(19);
        assertThat(resp.<Integer>read("$.data.totalElements")).isEqualTo(19);
        assertThat(all.stream().filter(e -> "STEP".equals(e.get("source"))).count()).isEqualTo(11);
        assertThat(all.stream().filter(e -> "RUN".equals(e.get("source"))).count()).isEqualTo(4);
        assertThat(all.stream().filter(e -> "ALERT".equals(e.get("source"))).count()).isEqualTo(2);
        assertThat(all.stream().filter(e -> "REVIEW".equals(e.get("source"))).count()).isEqualTo(2);
        assertThat(all.stream().filter(e -> "INFO".equals(e.get("level"))).count()).isEqualTo(12);
        assertThat(all.stream().filter(e -> "WARN".equals(e.get("level"))).count()).isEqualTo(4);
        assertThat(all.stream().filter(e -> "ERROR".equals(e.get("level"))).count()).isEqualTo(3);

        Map<String, Map<String, Object>> byId = new java.util.HashMap<>();
        all.forEach(e -> byId.put((String) e.get("id"), e));
        assertThat(byId).hasSize(19).containsKeys("run:" + s.r1() + ":started", "run:" + s.r1() + ":FAILED",
                "run:" + s.r2() + ":started", "run:" + s.r2() + ":COMPLETED");
        assertThat(byId.get("run:" + s.r1() + ":started").get("message")).isEqualTo("Run #1 開始執行（自治等級 4）");
        assertThat(byId.get("run:" + s.r1() + ":FAILED").get("message")).isEqualTo("Run #1 失敗");
        assertThat(byId.get("run:" + s.r1() + ":FAILED").get("level")).isEqualTo("ERROR");
        assertThat(byId.get("run:" + s.r2() + ":COMPLETED").get("message")).isEqualTo("Run #2 已完成");
        assertThat(byId.get("run:" + s.r2() + ":COMPLETED").get("level")).isEqualTo("INFO");
        assertThat(byId.get("run:" + s.r2() + ":started").get("runId")).isEqualTo(s.r2().toString());

        List<Map<String, Object>> steps = all.stream().filter(e -> "STEP".equals(e.get("source"))).toList();
        assertThat(steps).allSatisfy(e -> assertThat((String) e.get("id")).matches("step:[0-9a-f-]{36}"));
        Map<String, Object> failed = steps.stream().filter(e -> ((String) e.get("message")).startsWith("失敗：")).findFirst()
                .orElseThrow();
        assertThat(failed.get("message")).isEqualTo("失敗：設定（G1-T2，第 2 次）：boom");
        assertThat(failed.get("level")).isEqualTo("ERROR");
        assertThat(failed.get("taskId")).isEqualTo(s.f().t2());
        assertThat(failed.get("stepId")).isEqualTo("G1-T2");
        assertThat(failed.get("runId")).isEqualTo(s.r1().toString());
        assertThat(steps.stream().map(e -> (String) e.get("message"))).contains("開始：初始化（G1-T1，第 1 次）",
                "重試：設定（G1-T2，第 2 次）", "完成：實作（G2-T1）", "重試：實作（G2-T1，第 3 次）");
        assertThat(steps.stream().filter(e -> ((String) e.get("message")).startsWith("重試：")).map(e -> e.get("level")))
                .containsOnly("WARN");
        assertThat(steps.stream().filter(e -> ((String) e.get("message")).startsWith("完成：")).map(e -> (String) e.get("message")))
                .as("COMPLETED 不含 Token").noneMatch(m -> m.contains("Token"));

        Map<String, Object> warning = all.stream().filter(e -> "ALERT".equals(e.get("source")) && "WARN".equals(e.get("level")))
                .findFirst().orElseThrow();
        assertThat(warning.get("message")).isEqualTo("Token 使用量已達預算的 100%（8000 / 8000）");
        assertThat((String) warning.get("id")).startsWith("alert:");
        List<Map<String, Object>> reviews = all.stream().filter(e -> "REVIEW".equals(e.get("source"))).toList();
        assertThat(reviews.stream().map(e -> (String) e.get("message"))).containsExactlyInAnyOrder(
                "待審核：任務「設定」重試 1 次仍失敗", "審核 RETRIED：operator");
        assertThat(reviews.stream().map(e -> (String) e.get("id"))).allMatch(id -> id.matches(
                "review:[0-9a-f-]{36}:(requested|decided)"));
    }

    @Test
    void logsAreOrderedByTimestampThenIdAndTheOrderParameterFlipsThem() {
        Seed s = seed();
        List<Map<String, Object>> desc = logs(s, "&size=200");
        List<Map<String, Object>> asc = logs(s, "&size=200&order=asc");
        assertThat(asc.stream().map(e -> e.get("id")).toList()).isEqualTo(
                new ArrayList<>(desc.stream().map(e -> e.get("id")).toList().reversed()));
        for (int i = 1; i < asc.size(); i++) {
            String previous = asc.get(i - 1).get("timestamp") + "|" + asc.get(i - 1).get("id");
            String current = asc.get(i).get("timestamp") + "|" + asc.get(i).get("id");
            assertThat(previous.compareTo(current)).as("(timestamp, id) 升冪：" + previous + " → " + current).isNegative();
        }
        assertThat(desc.get(0).get("timestamp")).isEqualTo("2026-10-14T10:00:00Z");
        assertThat(asc.get(0).get("timestamp")).isEqualTo("2026-10-13T09:00:00Z");
        assertThat(api.get(viewer(), "/api/v1/monitor/projects/" + s.f().projectId() + "/logs?" + BOTH_DAYS + "&order=sideways")
                .status()).isEqualTo(400);
    }

    @Test
    void logFiltersByLevelTaskKeywordAndRunAreAppliedAndTheTaskFilterKeepsOnlyStepRows() {
        Seed s = seed();
        assertThat(logs(s, "&level=ERROR&size=200")).extracting(e -> e.get("source"))
                .containsExactlyInAnyOrder("STEP", "RUN", "ALERT");
        assertThat(logs(s, "&level=WARN&size=200")).hasSize(4);
        assertThat(logs(s, "&level=ALL&size=200")).hasSize(19);
        assertThat(logs(s, "&level=warn&size=200")).as("等級不分大小寫").hasSize(4);
        List<Map<String, Object>> byTask = logs(s, "&taskId=" + s.f().t2() + "&size=200");
        assertThat(byTask).hasSize(5);
        assertThat(byTask).extracting(e -> e.get("source")).containsOnly("STEP");
        assertThat(byTask).extracting(e -> e.get("taskId")).containsOnly(s.f().t2());
        assertThat(logs(s, "&q=BOOM&size=200")).as("關鍵字不分大小寫（步驟的失敗行與告警）").hasSize(2);
        assertThat(keyword(s, "100%")).as("% 視為字面").hasSize(1);
        assertThat(keyword(s, "%")).hasSize(1);
        assertThat(keyword(s, "_")).as("_ 視為字面").isEmpty();
        assertThat(keyword(s, "設定（G1-T2")).as("關鍵字含全形括號與連字號（R1 的 T2 三個步驟列）").hasSize(3);
        assertThat(logs(s, "&runId=" + s.r2() + "&size=200")).as("R2：6 個步驟列、起訖 2 行、1 則告警").hasSize(9);
        assertThat(api.get(viewer(), "/api/v1/monitor/projects/" + s.f().projectId() + "/logs?" + BOTH_DAYS + "&q=" + "x".repeat(201))
                .status()).as("關鍵字最長 200 字元").isEqualTo(400);
    }

    @Test
    void theLogPageSizeIsCappedAndPagesSliceTheSortedList() {
        Seed s = seed();
        String base = "/api/v1/monitor/projects/" + s.f().projectId() + "/logs?" + BOTH_DAYS;
        Resp first = api.get(viewer(), base + "&size=5&page=0");
        assertThat(first.<List<Object>>read("$.data.content")).hasSize(5);
        assertThat(first.<Integer>read("$.data.totalElements")).isEqualTo(19);
        assertThat(first.<Integer>read("$.data.totalPages")).isEqualTo(4);
        Resp last = api.get(viewer(), base + "&size=5&page=3");
        assertThat(last.<List<Object>>read("$.data.content")).hasSize(4);
        assertThat(api.get(viewer(), base + "&size=5&page=4").<List<Object>>read("$.data.content")).isEmpty();
        List<String> pages = new ArrayList<>();
        for (int page = 0; page < 4; page++) {
            pages.addAll(api.get(viewer(), base + "&size=5&page=" + page).<List<String>>read("$.data.content[*].id"));
        }
        assertThat(pages).hasSize(19).doesNotHaveDuplicates();
        assertThat(api.get(viewer(), base + "&size=201").status()).isEqualTo(400);
        assertThat(api.get(viewer(), base + "&size=0").status()).isEqualTo(400);
        assertThat(api.get(viewer(), base + "&page=-1").status()).isEqualTo(400);
        assertThat(api.get(viewer(), base + "&level=FATAL").status()).isEqualTo(400);
        assertThat(api.get(viewer(), base + "&size=200").status()).isEqualTo(200);
    }

    @Test
    void logsOutsideTheWindowAreExcludedAndTheDefaultWindowIsTheLast24Hours() {
        Seed s = seed();
        String base = "/api/v1/monitor/projects/" + s.f().projectId() + "/logs?";
        assertThat(api.get(viewer(), base + W + "&size=200").<Integer>read("$.data.totalElements"))
                .as("W 內：R2 的 6 步＋2 個 RUN＋1 個告警").isEqualTo(9);
        assertThat(api.get(viewer(), base + "from=2026-10-14T09:30:00Z&to=2026-10-14T09:50:00Z&size=200")
                .<Integer>read("$.data.totalElements")).as("[from, to)：09:30、09:40、09:45 在內；09:50 不在").isEqualTo(3);
        assertThat(api.get(viewer(), base + "from=2026-10-14T09:30:00Z&to=2026-10-14T09:50:01Z&size=200")
                .<Integer>read("$.data.totalElements")).as("加上 09:50 的第二次重試與同刻的告警").isEqualTo(5);
    }

    // ── §1.3.7 CSV 報表 ───────────────────────────────────────────────────────────────

    private Resp report(Seed s, String query) {
        return api.get(viewer(), "/api/v1/monitor/projects/" + s.f().projectId() + "/report?" + query);
    }

    @Test
    void theCsvReportIsAnAttachmentWithBomCrlfAndTheFourSectionsInOrder() {
        Seed s = seed();
        Resp resp = report(s, BOTH_DAYS);
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.header("Content-Type")).isEqualToIgnoringCase("text/csv;charset=UTF-8");
        String disposition = resp.header("Content-Disposition");
        assertThat(disposition).startsWith("attachment;");
        Matcher name = Pattern.compile("filename=\"monitor-report-([0-9a-f]{8})-(\\d{8}-\\d{4})\\.csv\"").matcher(disposition);
        assertThat(name.find()).as(disposition).isTrue();
        assertThat(name.group(1)).isEqualTo(s.f().projectId().substring(0, 8));

        String body = resp.body();
        assertThat(body).startsWith("﻿");
        assertThat(body).as("行尾一律 CRLF").doesNotContain("\r\r").doesNotMatch("(?s).*[^\r]\n.*");
        List<String> lines = List.of(body.substring(1).split("\r\n", -1));
        assertThat(lines.get(0)).isEqualTo("#report,mon,2026-10-13T00:00:00Z,2026-10-15T00:00:00Z,ALL");
        assertThat(lines.indexOf("#section,summary")).isEqualTo(1);
        assertThat(lines.get(2)).isEqualTo("metric,value,previousValue,delta,unit");
        assertThat(lines.subList(3, 13).stream().map(l -> l.split(",")[0])).containsExactly("taskCompletionRate",
                "taskSuccessRate", "retryRate", "totalTokens", "tokenBudgetUsageRate", "averageRetryCount",
                "projectCompletionRate", "goalAchievementRate", "averageTaskDurationSec", "agentAvailability");
        assertThat(lines.get(3)).isEqualTo("taskCompletionRate,100.0,0.0,100.0,PERCENT");
        assertThat(lines.get(6)).isEqualTo("totalTokens,5720,0,5720,TOKENS");
        assertThat(lines.get(7)).as("null 輸出空字串").isEqualTo("tokenBudgetUsageRate,31.8,,,PERCENT");
        assertThat(lines.get(8)).endsWith(",COUNT");
        assertThat(lines.get(11)).endsWith(",SECONDS");
        assertThat(lines.get(13)).as("段與段之間空一行").isEmpty();
        int runs = lines.indexOf("#section,runs");
        int tasks = lines.indexOf("#section,tasks");
        int alerts = lines.indexOf("#section,alerts");
        assertThat(runs).isGreaterThan(13);
        assertThat(tasks).isGreaterThan(runs);
        assertThat(alerts).isGreaterThan(tasks);
        assertThat(lines.get(runs + 1)).isEqualTo("runNumber,runId,status,autonomyLevel,startedAt,completedAt,durationSec,"
                + "totalTokensUsed,tokenBudget,tasksTotal,tasksCompleted,tasksFailed");
        assertThat(lines.get(runs + 2)).isEqualTo("1," + s.r1() + ",FAILED,4,2026-10-13T09:00:00Z,2026-10-13T11:00:00Z,7200,"
                + "2000,10000,3,1,1");
        assertThat(lines.get(runs + 3)).isEqualTo("2," + s.r2() + ",COMPLETED,4,2026-10-14T08:50:00Z,2026-10-14T10:00:00Z,"
                + "4200,3720,8000,2,2,0");
        assertThat(lines.get(tasks + 1)).isEqualTo("goalName,taskName,status,retryCount,maxRetries,actualTokens,startedAt,"
                + "completedAt,durationSec");
        assertThat(lines.get(tasks + 2)).isEqualTo("基礎,初始化,COMPLETED,0,1,1000,2026-10-13T10:00:00Z,"
                + "2026-10-13T10:10:00Z,600.0");
        assertThat(lines.get(alerts + 1)).isEqualTo("createdAt,severity,rule,subject,message,acknowledged,acknowledgedBy,"
                + "acknowledgedAt");
        assertThat(lines.get(alerts + 2)).isEqualTo("2026-10-13T10:30:30Z,CRITICAL,ENGINE_ESCALATION,step:G1-T2,"
                + "引擎升級（ESCALATION）：boom,true,operator,2026-10-13T12:00:00Z");
        assertThat(lines.get(alerts + 3)).startsWith("2026-10-14T09:50:00Z,WARNING,TOKEN_BUDGET_WARNING,run:" + s.r2() + ",");
        assertThat(lines.get(alerts + 3)).endsWith(",false,,");
    }

    @Test
    void textFieldsAreQuotedPerRfc4180AndFormulaCharactersAreDefused() {
        Seed s = seed();
        jdbc.update("update console.tasks set name = '=SUM(A1)' where id = ?", UUID.fromString(s.f().t1()));
        jdbc.update("update console.tasks set name = '@evil' where id = ?", UUID.fromString(s.f().t2()));
        jdbc.update("update console.tasks set name = '-1+1' where id = ?", UUID.fromString(s.f().t3()));
        jdbc.update("update console.goals set name = '核,\"心\"' where id = ?", UUID.fromString(s.f().g2()));
        jdbc.update("update console.projects set name = '+cmd' where id = ?", UUID.fromString(s.f().projectId()));
        String body = report(s, BOTH_DAYS).body();
        assertThat(body).contains("'=SUM(A1)").contains("'@evil").contains("'-1+1");
        assertThat(body).as("引號跳脫").contains("\"核,\"\"心\"\"\"");
        assertThat(body).as("專案名稱同樣防護").startsWith("﻿#report,'+cmd,");
        assertThat(body).doesNotContain(",=SUM").doesNotContain(",@evil").doesNotContain(",-1+1");
    }

    @Test
    void theReportCanBeNarrowedToOneRunAndNamesTheRunInTheHeader() {
        Seed s = seed();
        String body = report(s, BOTH_DAYS + "&runId=" + s.r2()).body();
        List<String> lines = List.of(body.substring(1).split("\r\n", -1));
        assertThat(lines.get(0)).isEqualTo("#report,mon,2026-10-13T00:00:00Z,2026-10-15T00:00:00Z," + s.r2());
        int runs = lines.indexOf("#section,runs");
        int tasks = lines.indexOf("#section,tasks");
        assertThat(lines.subList(runs + 2, tasks - 1)).hasSize(1);
        assertThat(lines.subList(tasks + 2, lines.indexOf("#section,alerts") - 1)).hasSize(2);
    }

    // ── §1.3.7 PDF 報表（v1.2，C-4）────────────────────────────────────────────────────

    private static String pdfText(Resp resp) throws IOException {
        try (PDDocument document = Loader.loadPDF(resp.bytes())) {
            return new PDFTextStripper().getText(document);
        }
    }

    @Test
    void thePdfReportIsAnAttachmentWithTheSameFourSectionsAndTheTitleTheRangeAndTheGenerationTime() throws IOException {
        Seed s = seed();
        Resp resp = api.send(viewer(), MockMvcRequestBuilders
                .get("/api/v1/monitor/projects/" + s.f().projectId() + "/report?format=pdf&" + BOTH_DAYS)
                .accept("application/pdf"));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.header("Content-Type")).isEqualTo("application/pdf");
        String disposition = resp.header("Content-Disposition");
        assertThat(disposition).startsWith("attachment;");
        Matcher name = Pattern.compile("filename=\"monitor-report-([0-9a-f]{8})-(\\d{8}-\\d{4})\\.pdf\"")
                .matcher(disposition);
        assertThat(name.find()).as(disposition).isTrue();
        assertThat(name.group(1)).isEqualTo(s.f().projectId().substring(0, 8));
        assertThat(new String(resp.bytes(), 0, 5, StandardCharsets.US_ASCII)).isEqualTo("%PDF-");

        String text = pdfText(resp);
        assertThat(text).as("標題：專案名稱＋「監控報表」").contains("mon 監控報表");
        assertThat(text).contains("時間範圍：2026-10-13T00:00:00Z ～ 2026-10-15T00:00:00Z").contains("範圍：全部批次")
                .contains("產生時間（UTC）：");
        assertThat(text).as("四個區段標題").contains("summary").contains("runs").contains("tasks").contains("alerts");
        assertThat(text).as("E2E-13 #4：可以找到專案名稱、區段標題與 totalTokens").contains("totalTokens").contains("5720")
                .contains("taskCompletionRate");
        assertThat(text).as("兩個批次").contains(s.r1().toString()).contains(s.r2().toString());
        assertThat(text).as("中文目標與任務名稱、告警訊息").contains("基礎").contains("初始化").contains("引擎升級");
    }

    @Test
    void thePdfCanBeNarrowedToOneRunAndTheFormatDecidesTheOutputNotTheAcceptHeader() throws IOException {
        Seed s = seed();
        String url = "/api/v1/monitor/projects/" + s.f().projectId() + "/report?format=PDF&" + BOTH_DAYS + "&runId="
                + s.r2();

        Resp withCsvAccept = api.send(viewer(), MockMvcRequestBuilders.get(url).accept("text/csv"));
        Resp withoutAccept = api.get(viewer(), url);

        for (Resp resp : List.of(withCsvAccept, withoutAccept)) {
            assertThat(resp.status()).as("後端以 format 為準，不因 Accept 不符回 406").isEqualTo(200);
            assertThat(resp.header("Content-Type")).isEqualTo("application/pdf");
            String text = pdfText(resp);
            assertThat(text).contains("範圍：" + s.r2()).contains(s.r2().toString());
            assertThat(text).as("只含該批次").doesNotContain(s.r1().toString());
        }
    }

    @Test
    void anUnknownFormatIs400AndEveryReportErrorIsAJsonApiError() {
        Seed s = seed();
        Resp bad = report(s, "format=xml");
        assertThat(bad.status()).isEqualTo(400);
        assertThat(bad.<String>read("$.reason")).isEqualTo(ErrorReasons.REPORT_FORMAT_UNSUPPORTED);
        assertThat(bad.<String>read("$.details.format")).isEqualTo("xml");
        assertThat(bad.<List<String>>read("$.details.supported")).containsExactly("csv", "pdf");
        Resp range = report(s, "from=2026-10-15T00:00:00Z&to=2026-10-14T00:00:00Z");
        assertThat(range.status()).isEqualTo(400);
        assertThat(range.<String>read("$.reason")).isEqualTo(ErrorReasons.TIME_RANGE_INVALID);
        assertThat(report(s, "format=CSV").status()).as("格式不分大小寫").isEqualTo(200);
        assertThat(report(s, "format=pdf&from=2026-10-15T00:00:00Z&to=2026-10-14T00:00:00Z").<String>read("$.reason"))
                .as("PDF 與 CSV 同一組驗證").isEqualTo(ErrorReasons.TIME_RANGE_INVALID);
    }

    @Test
    void aPdfReportOfAnUnknownProjectIs404AndAnAnonymousCallerIs401() {
        String unknown = "/api/v1/monitor/projects/" + UUID.randomUUID() + "/report?format=pdf";

        Resp missing = api.get(viewer(), unknown);
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.header("Content-Type")).as("錯誤一律是 JSON 封包，不是壞掉的 PDF").startsWith("application/json");
        assertThat(api.get(null, unknown).status()).isEqualTo(401);
    }
}
