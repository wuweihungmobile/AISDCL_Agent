package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 全域任務總計 {@code GET /api/v1/monitor/task-totals}（C-1、DEF-AC-009；契約 §1.3.8、E2E-13 第 1 列；API-MON-08）。
 * 為什麼重要：儀表板「本週完成」原本對每個專案各打一次 {@code task-trend} 再加總，30 個專案就是每分鐘 31 次請求、用掉三成限流額度；
 * 這支端點把它收成每分鐘 1 次——但「收成一次」只有在數字與逐專案加總<b>一致</b>時才是修復，否則只是換了一個會騙人的數字。
 * 所以核心不變量是「各專案 task-trend 各桶加總 ＝ 本端點」（以兩個真跑的專案釘住），再加上封存、軟刪除、視窗語意與驗證。
 */
class TaskTotalsApiIT extends AbstractExecutionIT {

    private static final String TOTALS = "/api/v1/monitor/task-totals";
    private static final List<String> COUNTERS = List.of("started", "completed", "failed", "retried");

    /** 兩個真跑完的專案：A 全部完成（3 任務）；B 的第一個任務重試 1 次後失敗（STARTED、RETRYING、FAILED）。 */
    private record TwoRuns(String from, Fixture a, Fixture b) {
    }

    private TwoRuns twoRealRuns() {
        String from = Instant.now().minusSeconds(60).toString();
        Fixture a = prjA("totals-a", 4);
        assertThat(awaitProjected(startRun(a.projectId()), "COMPLETED")).isTrue();
        MINI.failStepIds.add("G1-T1");
        Fixture b = prjA("totals-b", 4);
        assertThat(awaitProjected(startRun(b.projectId()), "FAILED")).isTrue();
        return new TwoRuns(from, a, b);
    }

    private Resp totals(String query) {
        return api.get(viewer(), TOTALS + "?" + query);
    }

    private void assertTotals(Resp resp, long started, long completed, long failed, long retried, int projects) {
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Number>read("$.data.started").longValue()).as("started").isEqualTo(started);
        assertThat(resp.<Number>read("$.data.completed").longValue()).as("completed").isEqualTo(completed);
        assertThat(resp.<Number>read("$.data.failed").longValue()).as("failed").isEqualTo(failed);
        assertThat(resp.<Number>read("$.data.retried").longValue()).as("retried").isEqualTo(retried);
        assertThat(resp.<Number>read("$.data.projectsCounted").intValue()).as("projectsCounted").isEqualTo(projects);
    }

    /** 一個專案在視窗內 task-trend（DAY 桶）各桶加總。 */
    private Map<String, Long> trendSums(String projectId, String from, String to) {
        Resp trend = api.get(viewer(), "/api/v1/monitor/projects/" + projectId + "/task-trend?from=" + from + "&to="
                + to + "&bucket=DAY");
        assertThat(trend.status()).isEqualTo(200);
        Map<String, Long> sums = new LinkedHashMap<>();
        for (String counter : COUNTERS) {
            sums.put(counter, trend.<List<Number>>read("$.data[*]." + counter).stream()
                    .mapToLong(Number::longValue).sum());
        }
        return sums;
    }

    // ── 不變量：與各專案 task-trend 加總一致 ─────────────────────────────────────────────

    @Test
    void theTotalsEqualTheSumOfEveryProjectsTaskTrendBucketsAfterTwoRealRuns() {
        TwoRuns runs = twoRealRuns();

        Resp totals = totals("from=" + runs.from());

        assertTotals(totals, 4, 3, 1, 1, 2);
        String to = totals.read("$.data.to");
        Map<String, Long> a = trendSums(runs.a().projectId(), runs.from(), to);
        Map<String, Long> b = trendSums(runs.b().projectId(), runs.from(), to);
        for (String counter : COUNTERS) {
            assertThat(totals.<Number>read("$.data." + counter).longValue()).as("逐欄等於兩專案各桶加總：" + counter)
                    .isEqualTo(a.get(counter) + b.get(counter));
        }
        assertThat(a).as("A 全部完成：3 個任務各 STARTED、COMPLETED").containsEntry("started", 3L)
                .containsEntry("completed", 3L).containsEntry("failed", 0L).containsEntry("retried", 0L);
        assertThat(b).as("B 的 G1-T1：STARTED、RETRYING、FAILED").containsEntry("started", 1L)
                .containsEntry("completed", 0L).containsEntry("failed", 1L).containsEntry("retried", 1L);
    }

    @Test
    void anArchivedProjectASoftDeletedGoalAndASoftDeletedProjectAreNotCountedAndTheInvariantStillHolds() {
        TwoRuns runs = twoRealRuns();
        assertTotals(totals("from=" + runs.from()), 4, 3, 1, 1, 2);

        setProjectStatus(runs.b().projectId(), "ARCHIVED");
        Resp archived = totals("from=" + runs.from());
        assertTotals(archived, 3, 3, 0, 0, 1);
        assertThat(trendSums(runs.a().projectId(), runs.from(), archived.read("$.data.to")))
                .as("封存專案不計：只剩 A，且與 A 的 task-trend 加總一致").containsEntry("started", 3L)
                .containsEntry("completed", 3L);

        jdbc.update("update console.goals set is_deleted = true where id = ?", UUID.fromString(runs.a().g1()));
        Resp goalDeleted = totals("from=" + runs.from());
        assertTotals(goalDeleted, 1, 1, 0, 0, 1);
        assertThat(trendSums(runs.a().projectId(), runs.from(), goalDeleted.read("$.data.to")))
                .as("軟刪除目標底下的任務不計（task-trend 的範圍任務同樣排除它們）").containsEntry("started", 1L)
                .containsEntry("completed", 1L);

        jdbc.update("update console.tasks set is_deleted = true where id = ?", UUID.fromString(runs.a().t3()));
        assertTotals(totals("from=" + runs.from()), 0, 0, 0, 0, 0);

        jdbc.update("update console.goals set is_deleted = false where id = ?", UUID.fromString(runs.a().g1()));
        jdbc.update("update console.projects set is_deleted = true where id = ?", UUID.fromString(runs.a().projectId()));
        setProjectStatus(runs.b().projectId(), "READY");
        Resp bBackOnly = totals("from=" + runs.from());
        assertTotals(bBackOnly, 1, 0, 1, 1, 1);
    }

    // ── 視窗語意：[from, to)、只計四種狀態 ───────────────────────────────────────────────

    private UUID insertRun(String projectId, int runNumber) {
        UUID run = UUID.randomUUID();
        jdbc.update("insert into console.execution_runs (id, project_id, run_number, status, autonomy_level, scope) "
                + "values (?, ?, ?, 'COMPLETED', 4, '{\"mode\":\"ALL\",\"goalIds\":[],\"taskIds\":[]}'::jsonb)", run,
                UUID.fromString(projectId), runNumber);
        return run;
    }

    private void insertStep(UUID run, String taskId, int seq, String status, String time) {
        jdbc.update("insert into console.execution_steps (id, run_id, task_id, step_number, action, status, input, "
                + "timestamp) values (?, ?, ?, ?, 'seed', ?, '{}'::jsonb, ?)", UUID.randomUUID(), run,
                UUID.fromString(taskId), seq, status, OffsetDateTime.parse(time));
    }

    @Test
    void theWindowIsHalfOpenFromInclusiveToExclusiveAndOnlyTheFourStepStatusesAreCounted() {
        Fixture f = prjA("totals-window", 4);
        UUID run = insertRun(f.projectId(), 1);
        insertStep(run, f.t1(), 1, "STARTED", "2026-10-10T10:00:00Z");
        insertStep(run, f.t1(), 2, "COMPLETED", "2026-10-10T10:00:01Z");
        insertStep(run, f.t2(), 3, "FAILED", "2026-10-10T10:00:02Z");
        insertStep(run, f.t2(), 4, "RETRYING", "2026-10-10T10:00:03Z");
        insertStep(run, f.t3(), 5, "SOMETHING_ELSE", "2026-10-10T10:00:00Z");
        Fixture quiet = prjA("totals-quiet", 4);
        insertStep(insertRun(quiet.projectId(), 1), quiet.t1(), 1, "SOMETHING_ELSE", "2026-10-10T10:00:00Z");

        assertTotals(totals("from=2026-10-10T10:00:00Z&to=2026-10-10T10:00:03Z"), 1, 1, 1, 0, 1);
        assertTotals(totals("from=2026-10-10T10:00:01Z&to=2026-10-10T10:00:04Z"), 0, 1, 1, 1, 1);
        assertTotals(totals("from=2026-10-10T10:00:03Z&to=2026-10-10T10:00:04Z"), 0, 0, 0, 1, 1);
        assertTotals(totals("from=2026-10-10T10:00:04Z&to=2026-10-10T11:00:00Z"), 0, 0, 0, 0, 0);
        assertTotals(totals("from=2026-10-10T09:00:00Z&to=2026-10-10T10:00:00Z"), 0, 0, 0, 0, 0);
    }

    @Test
    void aStepWhoseTaskBelongsToAnotherProjectIsNotCountedForTheRunsProjectJustLikeTaskTrend() {
        Fixture a = prjA("totals-own", 4);
        Fixture other = prjA("totals-foreign", 4);
        UUID run = insertRun(a.projectId(), 1);
        insertStep(run, a.t1(), 1, "STARTED", "2026-10-10T10:00:00Z");
        insertStep(run, other.t1(), 2, "STARTED", "2026-10-10T10:00:01Z");

        Resp totals = totals("from=2026-10-10T09:00:00Z&to=2026-10-10T11:00:00Z");

        assertTotals(totals, 1, 0, 0, 0, 1);
        assertThat(trendSums(a.projectId(), "2026-10-10T09:00:00Z", "2026-10-10T11:00:00Z")).containsEntry("started", 1L);
    }

    // ── 參數與回應形狀 ─────────────────────────────────────────────────────────────────────

    @Test
    void anEmptyWindowIsAValidAnswerOfAllZerosAndTheResponseHasExactlyTheContractFields() {
        Resp resp = totals("from=2026-01-01T00:00:00Z&to=2026-01-02T00:00:00Z");

        assertTotals(resp, 0, 0, 0, 0, 0);
        assertThat(resp.<Map<String, Object>>read("$.data").keySet()).containsExactlyInAnyOrder("from", "to", "started",
                "completed", "failed", "retried", "projectsCounted");
        assertThat(resp.<String>read("$.data.from")).isEqualTo("2026-01-01T00:00:00Z");
        assertThat(resp.<String>read("$.data.to")).isEqualTo("2026-01-02T00:00:00Z");
        assertThat(resp.<Integer>read("$.code")).isEqualTo(200);
        assertThat(resp.<String>read("$.traceId")).isNotBlank();
    }

    @Test
    void anOmittedToDefaultsToNowAndIsEchoedAsTheEffectiveWindowEnd() {
        Instant before = Instant.now();
        Resp resp = totals("from=" + before.minus(1, ChronoUnit.DAYS));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(Instant.parse(resp.read("$.data.to"))).isBetween(before.minusSeconds(1), Instant.now().plusSeconds(1));
    }

    @Test
    void fromIsRequiredAndAnUnparsableTimeIsRejectedOnTheOffendingField() {
        for (String query : List.of("", "from=", "from=%20%20")) {
            Resp missing = totals(query);
            assertThat(missing.status()).as("缺漏或空白的 from：" + query).isEqualTo(400);
            assertThat(missing.errorFields()).containsExactly("from");
            assertThat(missing.has("$.reason")).as("Bean Validation 型的 400 沒有 reason").isFalse();
        }
        Resp badFrom = totals("from=yesterday");
        assertThat(badFrom.status()).isEqualTo(400);
        assertThat(badFrom.errorFields()).containsExactly("from");
        Resp noOffset = totals("from=2026-10-14T00:00:00&to=2026-10-15T00:00:00Z");
        assertThat(noOffset.status()).as("缺 offset").isEqualTo(400);
        Resp badTo = totals("from=2026-10-14T00:00:00Z&to=tomorrow");
        assertThat(badTo.status()).isEqualTo(400);
        assertThat(badTo.errorFields()).containsExactly("to");
    }

    @Test
    void aWindowThatIsNotForwardOrLongerThanNinetyTwoDaysIs400WithTheToFieldAndTheLimitInDetails() {
        for (String query : List.of("from=2026-10-15T00:00:00Z&to=2026-10-14T00:00:00Z",
                "from=2026-10-14T00:00:00Z&to=2026-10-14T00:00:00Z", "from=2026-07-14T00:00:00Z&to=2026-10-15T00:00:00Z")) {
            Resp resp = totals(query);
            assertThat(resp.status()).as(query).isEqualTo(400);
            assertThat(resp.<String>read("$.reason")).as(query).isEqualTo(ErrorReasons.TIME_RANGE_INVALID);
            assertThat(resp.errorFields()).as(query).containsExactly("to");
            assertThat(resp.<Integer>read("$.details.maxDays")).as(query).isEqualTo(92);
            assertThat(resp.<String>read("$.details.from")).as(query).isNotBlank();
            assertThat(resp.<String>read("$.details.to")).as(query).isNotBlank();
        }
        Resp tooLong = totals("from=2026-07-14T00:00:00Z&to=2026-10-15T00:00:00Z");
        assertThat(tooLong.<String>read("$.details.from")).isEqualTo("2026-07-14T00:00:00Z");
        assertThat(tooLong.<String>read("$.details.to")).isEqualTo("2026-10-15T00:00:00Z");
        assertThat(totals("from=2026-07-15T00:00:00Z&to=2026-10-15T00:00:00Z").status()).as("恰 92 天可以").isEqualTo(200);
        assertThat(totals("from=" + Instant.now().plus(1, ChronoUnit.DAYS)).status()).as("from 在未來、to 預設現在：from 不早於 to")
                .isEqualTo(400);
    }

    @Test
    void anOffsetWrittenWithAnUnencodedPlusIsStillReadAsAnOffset() {
        Resp encoded = api.send(viewer(), MockMvcRequestBuilders.get(TOTALS).param("from", "2026-10-14T08:00:00+08:00")
                .param("to", "2026-10-15T08:00:00+08:00"));
        assertThat(encoded.status()).isEqualTo(200);
        assertThat(encoded.<String>read("$.data.from")).isEqualTo("2026-10-14T00:00:00Z");

        Resp decodedSpace = api.send(viewer(), MockMvcRequestBuilders.get(TOTALS)
                .param("from", "2026-10-14T08:00:00 08:00").param("to", "2026-10-15T08:00:00 08:00"));
        assertThat(decodedSpace.status()).as("未編碼的 + 被容器解碼成空白之後的樣子").isEqualTo(200);
        assertThat(decodedSpace.<String>read("$.data.to")).isEqualTo("2026-10-15T00:00:00Z");
    }

    @Test
    void anyLoggedInRoleMayReadItAndAnonymousIs401() {
        String query = "?from=2026-10-14T00:00:00Z&to=2026-10-15T00:00:00Z";
        assertThat(api.get(viewer(), TOTALS + query).status()).isEqualTo(200);
        assertThat(api.get(operator(), TOTALS + query).status()).isEqualTo(200);
        assertThat(api.get(admin(), TOTALS + query).status()).isEqualTo(200);
        assertThat(api.get(null, TOTALS + query).status()).isEqualTo(401);
    }
}
