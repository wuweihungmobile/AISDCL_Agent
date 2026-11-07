package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.ResearchP1Fixtures;
import com.aisdlc.console.support.ResearchP2Fixtures;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 看板投影（API-RP-26；TCS-ResearchToPRD-P2 AC-962-10）。為什麼重要：看板是掌舵者一眼判斷內環進度的唯一畫面——它必須與各來源端點同值（不另算第二份）、
 * Bridge 不可達時誠實標示「未知」而不是回舊值或假值、而且全程不產生任何寫入（不是第二套執行控制）。
 * 本類以資料庫事實為主；迷你 Bridge 沒有該內環鍵的 FSM 檔，所以 FSM 衍生欄一律走「不可讀＝unknown」分支。
 */
class ResearchKanbanApiIT extends AbstractResearchIT {

    private ResearchP1Fixtures p1;
    private UUID research;
    private UUID console;

    @BeforeEach
    void fixtures() {
        p1 = new ResearchP1Fixtures(jdbc);
        research = p1.project("kb-" + UUID.randomUUID().toString().substring(0, 8), "UNDECIDED");
        console = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria, sdd_project) values (?, '看板專案', ?, '通過', ?)", console,
                "/e2e/" + console, "impl-" + console);
        p1.bind(research, console);
    }

    private String url(String suffix) {
        return RESEARCH + "/projects/" + research + suffix;
    }

    private UUID goal() {
        UUID goal = UUID.randomUUID();
        jdbc.update("insert into console.goals (id, project_id, name, pass_criteria) values (?, ?, ?, '通過')", goal, console, "目標 " + goal);
        return goal;
    }

    private UUID task(UUID goal, String status) {
        UUID task = UUID.randomUUID();
        jdbc.update("insert into console.tasks (id, goal_id, name, pass_criteria, status) values (?, ?, ?, '通過', ?)", task, goal, "任務 " + task, status);
        return task;
    }

    private UUID run(int number) {
        UUID run = UUID.randomUUID();
        jdbc.update("insert into console.execution_runs (id, project_id, run_number, status, autonomy_level, scope) values (?, ?, ?, 'RUNNING', 4, '{}'::jsonb)", run, console, number);
        return run;
    }

    private void gate(String gate, int minute) {
        jdbc.update("insert into console.research_gate_decisions (research_id, gate, decision, decided_by, decided_at, fsm_project, fsm_state_after, reason) "
                + "values (?, ?, 'APPROVED', 'alice', ?::timestamptz, 'impl', 'PR_REVIEW', ?)", research, gate, String.format("2026-11-08T01:%02d:00Z", minute), gate + "-" + minute);
    }

    private long writes() {
        return rows("research_gate_decisions") + rows("research_events") + rows("research_deliveries") + rows("review_requests") + rows("execution_steps");
    }

    @Test
    void AT_962_10_1_theDecomposeColumnIsDoneOnlyWhenSignedOffAndNotStale() {
        assertThat(api.get(viewer(), url("/kanban")).<String>read("$.data.columns.decompose.status")).isEqualTo("NONE");
        String sha = "a".repeat(64);
        p1.decomposition(research, "DRAFTED", sha, ResearchP1Fixtures.content(sha, "[]", 2, 2));
        Resp drafted = api.get(viewer(), url("/kanban"));
        assertThat(drafted.<Boolean>read("$.data.columns.decompose.done")).isFalse();
        assertThat(drafted.<String>read("$.data.columns.decompose.status")).isEqualTo("DRAFTED");
        p1.decomposition(research, "SIGNED_OFF", sha, ResearchP1Fixtures.content(sha, "[]", 2, 2));
        Resp kanban = api.get(viewer(), url("/kanban"));
        Resp source = api.get(viewer(), url("/decomposition"));
        assertThat(kanban.<String>read("$.data.columns.decompose.status")).isEqualTo(source.<String>read("$.data.status"));
        assertThat(kanban.<Integer>read("$.data.columns.decompose.tasksCount")).isEqualTo(source.<Integer>read("$.data.tasksCount"));
        assertThat(kanban.<Boolean>read("$.data.columns.decompose.stale")).isEqualTo(source.<Boolean>read("$.data.stale"));
    }

    @Test
    void AT_962_10_3_theImplementColumnCountsAndItsDoneBoundaryAreExact() {
        Resp empty = api.get(viewer(), url("/kanban"));
        assertThat(empty.<Boolean>read("$.data.columns.implement.done")).as("total 為 0 不算完成").isFalse();
        UUID goal = goal();
        task(goal, "COMPLETED");
        task(goal, "SKIPPED");
        assertThat(api.get(viewer(), url("/kanban")).<Boolean>read("$.data.columns.implement.done")).as("completed 加 skipped 等於 total").isTrue();
        task(goal, "RUNNING");
        task(goal, "FAILED");
        task(goal, "ESCALATED");
        Resp mixed = api.get(viewer(), url("/kanban"));
        assertThat(mixed.<Boolean>read("$.data.columns.implement.done")).as("差 1 以上").isFalse();
        assertThat(mixed.<Integer>read("$.data.columns.implement.tasks.total")).isEqualTo(5);
        assertThat(mixed.<Integer>read("$.data.columns.implement.tasks.running")).isEqualTo(1);
        assertThat(mixed.<Integer>read("$.data.columns.implement.tasks.completed")).isEqualTo(1);
        assertThat(mixed.<Integer>read("$.data.columns.implement.tasks.skipped")).isEqualTo(1);
        assertThat(mixed.<Integer>read("$.data.columns.implement.tasks.failed")).isEqualTo(1);
        assertThat(mixed.<Integer>read("$.data.columns.implement.tasks.escalated")).isEqualTo(1);
    }

    @Test
    void AT_962_10_4_theHealingColumnEqualsTheHealingEndpoint() {
        UUID goal = goal();
        UUID task = task(goal, "ESCALATED");
        UUID run = run(1);
        jdbc.update("insert into console.execution_steps (id, run_id, task_id, step_number, action, status, \"timestamp\") values (?, ?, ?, 1, '動作', 'RETRYING', now())",
                UUID.randomUUID(), run, task);

        Resp kanban = api.get(viewer(), url("/kanban"));

        Resp source = api.get(viewer(), url("/healing"));
        assertThat(kanban.<Integer>read("$.data.columns.healing.retryingSteps")).isEqualTo(source.<Integer>read("$.data.retryingSteps"));
        assertThat(kanban.<Integer>read("$.data.columns.healing.escalatedTasks")).isEqualTo(source.<Integer>read("$.data.escalatedTasks"));
        assertThat(kanban.<Integer>read("$.data.columns.healing.retryingSteps")).isEqualTo(1);
        assertThat(kanban.<Integer>read("$.data.columns.healing.escalatedTasks")).isEqualTo(1);
        assertThat(kanban.<Boolean>read("$.data.columns.healing.done")).isFalse();
        assertThat(kanban.<Integer>read("$.data.columns.healing.maxRetries")).isEqualTo(api.get(viewer(), url("/healing")).<Integer>read("$.data.maxRetries"));
    }

    @Test
    void AT_962_10_6_pendingReviewsListOnlyThisProjectsUndecidedItemsWithTheFixedKeys() {
        UUID goal = goal();
        UUID task = task(goal, "ESCALATED");
        UUID run = run(1);
        jdbc.update("insert into console.review_requests (id, run_id, task_id, kind, status, reason) values (?, ?, ?, 'ESCALATED', 'PENDING', '需要人介入')", UUID.randomUUID(), run, task);
        jdbc.update("insert into console.review_requests (id, run_id, task_id, kind, status, reason) values (?, ?, ?, 'TASK_CONFIRM', 'PENDING', '請確認')", UUID.randomUUID(), run, task);
        jdbc.update("insert into console.review_requests (id, run_id, task_id, kind, status, reason, decided_by, decided_at) values (?, ?, ?, 'TASK_CONFIRM', 'APPROVED', '已決', 'a', now())",
                UUID.randomUUID(), run, task);
        UUID otherConsole = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria) values (?, '他專案', '/e2e/other', '通過')", otherConsole);
        UUID otherRun = UUID.randomUUID();
        jdbc.update("insert into console.execution_runs (id, project_id, run_number, status, autonomy_level, scope) values (?, ?, 1, 'RUNNING', 4, '{}'::jsonb)", otherRun, otherConsole);
        jdbc.update("insert into console.review_requests (id, run_id, kind, status, reason) values (?, ?, 'GOAL_CONFIRM', 'PENDING', '他專案')", UUID.randomUUID(), otherRun);

        Resp first = api.get(viewer(), url("/kanban"));
        Resp second = api.get(viewer(), url("/kanban"));

        assertThat(first.<List<Object>>read("$.data.pendingReviews")).hasSize(2);
        assertThat(first.<List<String>>read("$.data.pendingReviews[*].kind")).containsExactlyInAnyOrder("ESCALATED", "TASK_CONFIRM");
        for (String key : List.of("reviewId", "runId", "kind", "taskId", "reason", "createdAt", "allowedDecisions")) {
            assertThat(first.has("$.data.pendingReviews[0]." + key)).as(key).isTrue();
        }
        assertThat(first.<Object>read("$.data.pendingReviews")).isEqualTo(second.<Object>read("$.data.pendingReviews"));
    }

    @Test
    void AT_962_10_7_eachGateKindListsAtMostTheLatestFiveNewestFirstIncludingScg6() {
        for (String gate : List.of("SCG4", "SCG5", "SCG6")) {
            for (int minute = 1; minute <= 6; minute++) {
                gate(gate, minute);
            }
        }

        Resp resp = api.get(viewer(), url("/kanban"));

        assertThat(resp.<List<Object>>read("$.data.gates")).hasSize(15);
        for (String gate : List.of("SCG4", "SCG5", "SCG6")) {
            assertThat(resp.<List<String>>read("$.data.gates[?(@.gate=='" + gate + "')].reason")).containsExactly(gate + "-6", gate + "-5", gate + "-4", gate + "-3", gate + "-2");
        }
        for (String key : List.of("gate", "decision", "decidedBy", "decidedAt", "fsmStateAfter", "reason")) {
            assertThat(resp.has("$.data.gates[0]." + key)).as(key).isTrue();
        }
    }

    @Test
    void AT_962_10_8_anUnreadableOrUnreachableBridgeGivesAStaleSnapshotWithUnknownMarkersAndTheLatestOfTheThreeSourceTimes() {
        jdbc.update("insert into console.research_gate_decisions (research_id, gate, decision, decided_by, decided_at, fsm_project, reason) "
                + "values (?, 'SCG4', 'APPROVED', 'alice', '2099-01-01T00:00:00Z', 'impl', 'future')", research);

        Resp resp = api.get(viewer(), url("/kanban"));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.bridgeReachable")).isFalse();
        assertThat(resp.<Boolean>read("$.data.stale")).isTrue();
        assertThat(resp.<Boolean>read("$.data.columns.tcs.unknown")).isTrue();
        assertThat(resp.<Boolean>read("$.data.columns.implement.unknown")).isTrue();
        assertThat(resp.<Boolean>read("$.data.columns.regression.unknown")).isTrue();
        assertThat(resp.body()).contains("\"stage2Frozen\":null").contains("\"releaseReady\":null");
        assertThat(resp.<String>read("$.data.snapshotAt")).startsWith("2099-01-01");
    }

    @Test
    void AT_962_10_9_aProjectWithoutRunsHasANullLatestRunIdAndNoRtm() {
        Resp resp = api.get(viewer(), url("/kanban"));

        assertThat(resp.body()).contains("\"latestRunId\":null");
        assertThat(resp.<Boolean>read("$.data.columns.regression.rtmAvailable")).isFalse();
        assertThat(resp.body()).contains("\"rtm\":null");
    }

    @Test
    void AT_962_10_E_2_theKanbanReadWritesNothingAndSendsNoBridgeWriteRequest() {
        long before = writes();

        api.get(viewer(), url("/kanban"));

        assertThat(writes()).isEqualTo(before);
        assertThat(bridge().calls.stream().filter(c -> !"GET".equals(c.method()))).isEmpty();
    }

    @Test
    void AT_962_10_E_3_anUnsignedProjectStillCannotBeExecutedAfterAKanbanRead() {
        api.get(viewer(), url("/kanban"));

        Resp execute = api.post(admin(), "/api/v1/projects/" + console + "/execute", Map.of());

        assertThat(execute.status()).as("看板不重造守衛：未簽核的專案執行仍 409").isEqualTo(409);
        p1.scr(research, 1, "MINOR", "OPEN");
        Resp scrOpen = api.post(admin(), "/api/v1/projects/" + console + "/execute", Map.of());
        assertThat(scrOpen.status()).as("SCR 開啟期間執行仍 409").isEqualTo(409);
    }

    @Test
    void AT_962_10_E_4_viewerReadsAnonymousIs401UnknownProjectIs404AndAnUnboundProjectGetsEmptyColumns() {
        assertThat(api.get(null, url("/kanban")).status()).isEqualTo(401);
        assertThat(api.get(viewer(), url("/kanban")).status()).isEqualTo(200);
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + UUID.randomUUID() + "/kanban").status()).isEqualTo(404);
        UUID unbound = p1.project("kb-unbound-" + UUID.randomUUID().toString().substring(0, 8), "UNDECIDED");
        Resp resp = api.get(viewer(), RESEARCH + "/projects/" + unbound + "/kanban");
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.columns.implement.tasks.total")).isZero();
        assertThat(resp.<List<Object>>read("$.data.pendingReviews")).isEmpty();
    }

    // ── D-159：以迷你 Bridge 的 FSM 與 RTM 注入補齊 10-2、10-5、14-8 ──

    private ResearchP2Fixtures p2() {
        return new ResearchP2Fixtures(jdbc, MINI);
    }

    @Test
    void AT_962_10_2_theTcsColumnCarriesTheRealStage2FrozenValueAndTheFsmStateAndNegotiatedIsUnknownNotFalse() {
        ResearchP2Fixtures.Ready open = p2().ready("kb102a");
        p2().fsm(open, "SPEC_FROZEN", false);
        Resp notFrozen = api.get(viewer(), RESEARCH + "/projects/" + open.research() + "/kanban");
        assertThat(notFrozen.<Boolean>read("$.data.columns.tcs.stage2Frozen")).isFalse();
        assertThat(notFrozen.<Boolean>read("$.data.columns.tcs.done")).isFalse();
        assertThat(notFrozen.<String>read("$.data.columns.tcs.fsmState")).isEqualTo("SPEC_FROZEN");

        ResearchP2Fixtures.Ready frozen = p2().ready("kb102b");
        p2().fsm(frozen, "IMPLEMENTATION", true);
        Resp resp = api.get(viewer(), RESEARCH + "/projects/" + frozen.research() + "/kanban");
        assertThat(resp.<Boolean>read("$.data.columns.tcs.stage2Frozen")).isTrue();
        assertThat(resp.<Boolean>read("$.data.columns.tcs.done")).as("done 等於 stage2Frozen").isTrue();
        assertThat(resp.<String>read("$.data.columns.implement.fsmState")).isEqualTo("IMPLEMENTATION");
        assertThat(resp.<Boolean>read("$.data.bridgeReachable")).isTrue();
        assertThat(resp.<Boolean>read("$.data.stale")).isFalse();
        assertThat(resp.body()).as("來源拿不到 negotiated：回 null（未知），不回 false").contains("\"negotiated\":null");
    }

    @Test
    void AT_962_10_5_theRegressionColumnEqualsTheRtmEndpointAndDoneOnlyForFullRtmAtAReleaseState() {
        record Row(String state, boolean fullyCovered, double acPct, boolean done) {
        }
        List<Row> rows = List.of(new Row("RELEASE_READY", true, 100.0, true), new Row("RELEASE", true, 100.0, true), new Row("RTM_VERIFY", true, 100.0, false),
                new Row("RELEASE_READY", true, 99.99, false), new Row("RELEASE_READY", false, 100.0, false));
        int n = 0;
        for (Row row : rows) {
            ResearchP2Fixtures.Ready ready = p2().ready("kb105-" + n++);
            p2().fsm(ready, row.state(), true);
            p2().rtm(ready, row.fullyCovered(), row.acPct());

            Resp kanban = api.get(viewer(), RESEARCH + "/projects/" + ready.research() + "/kanban");
            Resp source = api.get(viewer(), "/api/v1/executions/" + ready.run() + "/rtm");

            String label = row.toString();
            assertThat(kanban.<Boolean>read("$.data.columns.regression.done")).as(label).isEqualTo(row.done());
            assertThat(kanban.<Boolean>read("$.data.columns.regression.rtmAvailable")).as(label).isTrue();
            assertThat(kanban.<Boolean>read("$.data.columns.regression.rtm.advisory")).as(label).isTrue();
            assertThat(kanban.<Double>read("$.data.columns.regression.rtm.acPct")).as(label).isEqualTo(source.<Double>read("$.data.ac.pct"));
            assertThat(kanban.<Boolean>read("$.data.columns.regression.rtm.fullyCovered")).as(label).isEqualTo(source.<Boolean>read("$.data.fullyCovered"));
            assertThat(kanban.<Integer>read("$.data.columns.regression.rtm.atPassed")).as(label).isEqualTo(source.<Integer>read("$.data.at.passed"));
            assertThat(kanban.<Integer>read("$.data.columns.regression.rtm.acTotal")).as(label).isEqualTo(source.<Integer>read("$.data.ac.total"));
            assertThat(kanban.<Boolean>read("$.data.columns.regression.releaseReady")).as(label).isEqualTo(row.state().startsWith("RELEASE"));
        }
        ResearchP2Fixtures.Ready noRtm = p2().ready("kb105-none");
        p2().fsm(noRtm, "RELEASE_READY", true);
        Resp none = api.get(viewer(), RESEARCH + "/projects/" + noRtm.research() + "/kanban");
        assertThat(none.<Boolean>read("$.data.columns.regression.rtmAvailable")).isFalse();
        assertThat(none.<Boolean>read("$.data.columns.regression.done")).isFalse();
        assertThat(none.body()).contains("\"rtm\":null");
    }

    @Test
    void AT_962_14_8_aDecisionIsStoredByTheExistingReviewEndpointAndWritesNoGateDecisionRow() {
        ResearchP2Fixtures.Ready ready = p2().ready("kb148");
        UUID task = jdbc.queryForObject("select t.id from console.tasks t join console.goals g on g.id = t.goal_id where g.project_id = ? limit 1", UUID.class, ready.console());
        UUID review = UUID.randomUUID();
        jdbc.update("insert into console.review_requests (id, run_id, task_id, kind, status, reason) values (?, ?, ?, 'ESCALATED', 'PENDING', '需要人介入')",
                review, ready.run(), task);
        long gates = rows("research_gate_decisions");
        long audit = rows("audit_log");

        Resp resp = api.post(operator(), "/api/v1/executions/" + ready.run() + "/review/" + review, Map.of("decision", "REJECT", "comment", "人工決定"));

        assertThat(resp.status()).as(resp.body()).isEqualTo(204);
        Map<String, Object> row = jdbc.queryForMap("select status, decided_by, comment, decided_at from console.review_requests where id = ?", review);
        assertThat(row.get("decided_by")).isEqualTo("operator");
        assertThat(row.get("comment")).isEqualTo("人工決定");
        assertThat(row.get("decided_at")).isNotNull();
        assertThat(rows("audit_log")).as("audit_log 恰多一列").isEqualTo(audit + 1);
        assertThat(rows("research_gate_decisions")).as("不寫 research_gate_decisions").isEqualTo(gates);
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + ready.research() + "/kanban").<List<Object>>read("$.data.pendingReviews")).as("已決定者不再列出").isEmpty();
    }

    @Test
    void AT_962_10_E_5_aFullRtmDoesNotLiftDoneWhileTheFsmIsNotAtAReleaseStateBecauseRtmIsAdvisoryOnly() {
        ResearchP2Fixtures.Ready ready = p2().ready("kb10e5");
        p2().fsm(ready, "IMPLEMENTATION", true);
        p2().rtm(ready, true, 100.0);

        Resp resp = api.get(viewer(), RESEARCH + "/projects/" + ready.research() + "/kanban");

        assertThat(resp.<Boolean>read("$.data.columns.regression.rtm.advisory")).isTrue();
        assertThat(resp.<Double>read("$.data.columns.regression.rtm.acPct")).isEqualTo(100.0);
        assertThat(resp.<Boolean>read("$.data.columns.regression.done")).as("RTM 100 但現態非 RELEASE_READY／RELEASE：不算完成").isFalse();
    }
}
