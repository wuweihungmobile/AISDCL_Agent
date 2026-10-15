package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.application.service.RunRegistry;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import com.aisdlc.minibridge.MiniRun;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 一個批次的完整生命週期（契約 §5：E2E-03 啟動到 COMPLETED、E2E-06 取消、E2E-07 還原，以及 Bridge 不可達、重連回補、啟動對帳）。
 * 全部對迷你 Bridge（真 HTTP／SSE）進行；Bridge 欄位鏡射進同一顆資料庫，REST 端點讀的就是這些列。
 */
class ExecutionLifecycleApiIT extends AbstractExecutionIT {

    // ── E2E-03：Level 4 跑到 COMPLETED，讀模型逐項對得上 ──────────────────────────────

    @Test
    void aLevelFourRunProjectsEveryEventAndEndsCompletedWithAllReadModelsInAgreement() {
        Fixture f = prjA("e2e03", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        MiniRun bridge = mini(run);

        // 任務、目標、專案
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
        assertThat(goalStatus(f.g1())).isEqualTo("COMPLETED");
        assertThat(goalStatus(f.g2())).isEqualTo("COMPLETED");
        assertThat(projectStatus(f.projectId())).isEqualTo("COMPLETED");
        assertThat(jdbc.queryForList("select actual_tokens from console.tasks where goal_id in (?, ?)",
                Long.class, UUID.fromString(f.g1()), UUID.fromString(f.g2()))).containsOnly(1240L);
        assertThat(jdbc.queryForObject("select count(*) from console.tasks where assigned_agent = 'AutoClaude' "
                + "and started_at is not null and completed_at is not null", Long.class)).isEqualTo(3L);

        // A1：DB 與 Bridge 一致；位移＝Bridge 最後一則事件
        assertThat(jdbc.queryForObject("select total_tokens_used from console.execution_runs where id = ?", Long.class,
                UUID.fromString(run))).isEqualTo(bridge.tokens()).isEqualTo(3720L);
        assertThat(consoleLastSeq(run)).isEqualTo(bridge.lastSeq());
        assertThat(jdbc.queryForList("select delta from console.run_token_samples where run_id = ? order by seq",
                Long.class, UUID.fromString(run))).containsExactly(1240L, 1240L, 1240L);

        // GET run
        Resp detail = getRun(run);
        assertThat(detail.status()).isEqualTo(200);
        assertThat(detail.<String>read("$.data.status")).isEqualTo("COMPLETED");
        assertThat(detail.<String>read("$.data.bridgeStatus")).isEqualTo("COMPLETED");
        assertThat(detail.<Integer>read("$.data.completedSteps")).isEqualTo(3);
        assertThat(detail.<Integer>read("$.data.totalSteps")).isEqualTo(3);
        assertThat(detail.<Integer>read("$.data.lastEventSeq")).isEqualTo(bridge.lastSeq());
        assertThat(detail.<Integer>read("$.data.totalTokensUsed")).isEqualTo(3720);
        assertThat(detail.has("$.data.currentStep")).isFalse();
        assertThat(detail.<Boolean>read("$.data.bridge.connected")).isTrue();
        assertThat(detail.<Boolean>read("$.data.bridge.runKnown")).isTrue();
        assertThat(detail.<String>read("$.data.bridge.instance")).isEqualTo("mini-bridge");
        assertThat(detail.<List<Object>>read("$.data.pendingReviews")).isEmpty();
        assertThat(detail.<String>read("$.data.completedAt")).isNotBlank();
        assertThat(detail.<Integer>read("$.data.elapsedSec")).isNotNegative();
        assertThat(detail.<String>read("$.data.reason")).isEqualTo("引擎正常結束");

        // E2E-03 步驟 8：任務詳情的執行歷史＝該任務的 step 事件列（STARTED、COMPLETED），COMPLETED 帶本批次的 Token 歸因
        List<Integer> t1Seqs = bridge.events().stream().filter(e -> "step".equals(e.get("event"))
                && "G1-T1".equals(e.get("step_id"))).map(e -> ((Number) e.get("seq")).intValue()).toList();
        for (String taskId : f.taskIds()) {
            List<Map<String, Object>> history = api.get(viewer(), "/api/v1/tasks/" + taskId)
                    .read("$.data.executionHistory");
            assertThat(history).as("任務 %s 的執行歷史", taskId).extracting(h -> h.get("status"))
                    .containsExactly("STARTED", "COMPLETED");
            assertThat(history.get(0).get("tokensUsed")).as("STARTED 列沒有 Token 歸因").isNull();
            assertThat(history.get(1).get("tokensUsed")).isEqualTo(1240);
            assertThat(history.get(0).get("timestamp")).isNotNull();
        }
        List<Map<String, Object>> t1 = api.get(viewer(), "/api/v1/tasks/" + f.t1()).read("$.data.executionHistory");
        assertThat(t1.get(0).get("action")).isEqualTo("G1-T1: 初始化");
        assertThat(t1).extracting(h -> h.get("stepNumber")).containsExactlyElementsOf(t1Seqs);
        assertThat(t1.get(0).get("id")).isNotNull();
    }

    @Test
    void aTaskHistoryListsRetriesTheErrorAndEveryRunOfTheTaskInTimeOrder() {
        Fixture f = prjA("task-history", 4);
        MINI.failStepIds.add("G1-T1");
        String first = startRun(f.projectId());
        assertThat(awaitProjected(first, "FAILED")).isTrue();
        String item = (String) pendingReviews(first).get(0).get("id");
        MINI.failStepIds.clear();
        String followUp = review(first, item, "RETRY").header("X-Follow-Up-Run-Id");
        assertThat(followUp).isNotBlank();
        assertThat(awaitProjected(followUp, "COMPLETED")).isTrue();

        List<Map<String, Object>> history = api.get(viewer(), "/api/v1/tasks/" + f.t1()).read("$.data.executionHistory");
        assertThat(history).extracting(h -> h.get("status")).as("第一批次：開始、重試、失敗；第二批次：開始、完成")
                .containsExactly("STARTED", "RETRYING", "FAILED", "STARTED", "COMPLETED");
        assertThat(history.get(2).get("errorMessage")).isEqualTo("任務「初始化」重試 1 次仍失敗");
        assertThat(history.get(1).get("tokensUsed")).as("RETRYING 列沒有 Token 歸因").isNull();
        assertThat(history.get(2).get("tokensUsed")).as("FAILED 列＝第一批次兩次 attempt 的 Token").isEqualTo(2480);
        assertThat(history.get(4).get("tokensUsed")).as("第二批次各自歸因，不混入第一批次").isEqualTo(1240);
        assertThat(history.stream().map(h -> Instant.parse((String) h.get("timestamp"))).toList())
                .as("跨批次依時間升冪").isSorted();

        List<Map<String, Object>> t2 = api.get(viewer(), "/api/v1/tasks/" + f.t2()).read("$.data.executionHistory");
        assertThat(t2).as("只有自己的列：第一批次在 T1 失敗後 T2 從未開始").extracting(h -> h.get("status"))
                .containsExactly("STARTED", "COMPLETED");
    }

    @Test
    void stepsAreTheEventRowsWithTheBridgeSeqAsStepNumberAndAfterSeqIsStrictlyGreater() {
        Fixture f = prjA("steps", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();

        Resp all = api.get(viewer(), "/api/v1/executions/" + run + "/steps?size=200");
        assertThat(all.status()).isEqualTo(200);
        List<Map<String, Object>> rows = all.read("$.data.content");
        assertThat(rows).extracting(r -> r.get("status")).containsExactly("STARTED", "COMPLETED", "STARTED",
                "COMPLETED", "STARTED", "COMPLETED");
        List<Integer> seqs = mini(run).events().stream().filter(e -> "step".equals(e.get("event")))
                .map(e -> ((Number) e.get("seq")).intValue()).toList();
        assertThat(rows).extracting(r -> r.get("stepNumber")).containsExactlyElementsOf(seqs);
        assertThat(rows).extracting(r -> r.get("stepId")).containsExactly("G1-T1", "G1-T1", "G1-T2", "G1-T2", "G2-T1",
                "G2-T1");
        assertThat(rows.get(0).get("action")).isEqualTo("G1-T1: 初始化");
        assertThat(rows.get(0).get("attempt")).isEqualTo(1);
        assertThat(rows.get(0).get("taskName")).isEqualTo("初始化");
        assertThat(rows.get(0).get("tokensUsed")).as("STARTED 列沒有 Token 歸因").isNull();
        assertThat(rows.get(0)).containsKey("tokensUsed");
        assertThat(rows.get(1).get("tokensUsed")).as("COMPLETED 列＝該任務在本批次的 token 加總").isEqualTo(1240);
        assertThat(all.<Integer>read("$.data.totalElements")).isEqualTo(6);

        int pivot = seqs.get(2);
        Resp after = api.get(viewer(), "/api/v1/executions/" + run + "/steps?afterSeq=" + pivot);
        assertThat(after.<List<Integer>>read("$.data.content[*].stepNumber")).as("嚴格大於")
                .containsExactlyElementsOf(seqs.subList(3, seqs.size()));
        Resp paged = api.get(viewer(), "/api/v1/executions/" + run + "/steps?size=2&page=1");
        assertThat(paged.<List<Integer>>read("$.data.content[*].stepNumber")).containsExactly(seqs.get(2), seqs.get(3));
        assertThat(paged.<Integer>read("$.data.totalPages")).isEqualTo(3);
    }

    @Test
    void stepsRejectsOutOfRangeQueryParametersWith400() {
        Fixture f = prjA("steps-400", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        Resp tooBig = api.get(viewer(), "/api/v1/executions/" + run + "/steps?size=201");
        assertThat(tooBig.status()).isEqualTo(400);
        assertThat(tooBig.errorFields()).contains("size");
        assertThat(api.get(viewer(), "/api/v1/executions/" + run + "/steps?afterSeq=-1").status()).isEqualTo(400);
        assertThat(api.get(viewer(), "/api/v1/executions/" + run + "/steps?page=-1").status()).isEqualTo(400);
        assertThat(api.get(viewer(), "/api/v1/executions/" + run + "/steps?size=200").status()).isEqualTo(200);
    }

    @Test
    void theDagIsFrozenAtLaunchAndEachNodeCarriesTheCurrentStatus() {
        Fixture f = prjA("dag", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        Resp dag = api.get(viewer(), "/api/v1/executions/" + run + "/dag");
        assertThat(dag.status()).isEqualTo(200);
        assertThat(dag.<String>read("$.data.runId")).isEqualTo(run);
        assertThat(dag.<String>read("$.data.statusAsOf")).isNotBlank();
        List<Map<String, Object>> nodes = dag.read("$.data.nodes");
        assertThat(nodes).hasSize(5);
        assertThat(nodes.stream().filter(n -> "GOAL".equals(n.get("kind"))).toList())
                .extracting(n -> n.get("id")).containsExactly(f.g1(), f.g2());
        assertThat(nodes.stream().filter(n -> "GOAL".equals(n.get("kind"))).toList())
                .extracting(n -> n.get("sequence")).containsExactly(1, 2);
        List<Map<String, Object>> tasks = nodes.stream().filter(n -> "TASK".equals(n.get("kind"))).toList();
        assertThat(tasks).extracting(n -> n.get("stepId")).containsExactly("G1-T1", "G1-T2", "G2-T1");
        assertThat(tasks).extracting(n -> n.get("sequence")).containsExactly(1, 2, 3);
        assertThat(tasks).extracting(n -> n.get("goalId")).containsExactly(f.g1(), f.g1(), f.g2());
        assertThat(tasks).extracting(n -> n.get("label")).containsExactly("初始化", "設定", "實作");
        assertThat(nodes).extracting(n -> n.get("status")).containsOnly("COMPLETED");
        List<Map<String, Object>> edges = dag.read("$.data.edges");
        assertThat(edges).extracting(e -> e.get("kind") + ":" + e.get("from") + ">" + e.get("to"))
                .containsExactlyInAnyOrder("DEPENDENCY:" + f.g1() + ">" + f.g2(), "CONTAINS:" + f.g1() + ">" + f.t1(),
                        "CONTAINS:" + f.g1() + ">" + f.t2(), "CONTAINS:" + f.g2() + ">" + f.t3());
    }

    @Test
    void checkpointsListTheBridgeSnapshotsOldestFirstWithTheNextStepAndWithoutTheSnapshotBody() {
        Fixture f = prjA("checkpoints", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        Resp resp = api.get(viewer(), "/api/v1/executions/" + run + "/checkpoints");
        assertThat(resp.status()).isEqualTo(200);
        List<Map<String, Object>> cps = resp.read("$.data");
        assertThat(cps).extracting(c -> c.get("name")).containsExactly("after-G1-T1", "after-G1-T2", "after-G2-T1");
        assertThat(cps).extracting(c -> c.get("stepIdx")).containsExactly(1, 2, 3);
        assertThat(cps).extracting(c -> c.get("stepId")).containsExactly("G1-T2", "G2-T1", "");
        assertThat(cps).extracting(c -> c.get("completedSteps")).containsExactly(1, 2, 3);
        assertThat(cps).extracting(c -> c.get("isAutomatic")).containsOnly(true);
        assertThat(cps.get(0)).doesNotContainKeys("stateSnapshot", "state_snapshot");
        assertThat(cps.get(0).get("runId")).isEqualTo(run);
    }

    @Test
    void theExecutionListGivesATerminalRunItsTokensDurationAndSuccessRate() {
        Fixture f = prjA("list", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        Resp resp = api.get(viewer(), "/api/v1/projects/" + f.projectId() + "/executions");
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.totalElements")).isEqualTo(1);
        Map<String, Object> row = resp.<List<Map<String, Object>>>read("$.data.content").get(0);
        assertThat(row.get("id")).isEqualTo(run);
        assertThat(row.get("status")).isEqualTo("COMPLETED");
        assertThat(row.get("scopeMode")).isEqualTo("ALL");
        assertThat(row.get("totalTokensUsed")).isEqualTo(3720);
        assertThat(((Number) row.get("durationSec")).longValue()).isNotNegative();
        assertThat(row.get("tasksTotal")).isEqualTo(3);
        assertThat(row.get("tasksCompleted")).isEqualTo(3);
        assertThat(row.get("tasksFailed")).isEqualTo(0);
        assertThat(((Number) row.get("successRate")).doubleValue()).isEqualTo(100.0);
        assertThat(row.get("completedAt")).isNotNull();
        assertThat(row.get("autonomyLevel")).isEqualTo(4);
    }

    // ── 批次列表的 bridgeStatus（C-11；契約 §1.2.2、E2E-13 第 11 列）─────────────────────────

    private Map<String, Object> listRow(String projectId, String runId) {
        List<Map<String, Object>> rows = api.get(viewer(), "/api/v1/projects/" + projectId + "/executions")
                .read("$.data.content");
        return rows.stream().filter(r -> runId.equals(r.get("id"))).findFirst().orElseThrow();
    }

    /** 列表的 status 必須是 bridgeStatus 的六態折疊值（PAUSING／CANCELLING 折為 RUNNING）；沒有 bridgeStatus 的列不判。 */
    private static void assertFoldsBack(Map<String, Object> row) {
        Object bridge = row.get("bridgeStatus");
        if (bridge != null) {
            String folded = "PAUSING".equals(bridge) || "CANCELLING".equals(bridge) ? "RUNNING" : (String) bridge;
            assertThat(row.get("status")).as("bridgeStatus=%s 折疊後應等於 status", bridge).isEqualTo(folded);
        }
    }

    @Test
    void theExecutionListShowsPausingWhileTheConsumerFollowsTheRunAndTheSameNameOnceTheRunSettles() {
        Fixture f = prjA("list-bridge-status", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();

        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/pause").<String>read("$.data.bridgeStatus"))
                .isEqualTo("PAUSING");
        assertThat(awaitUntil(Duration.ofSeconds(10),
                () -> "PAUSING".equals(listRow(f.projectId(), run).get("bridgeStatus"))))
                .as("事件消費者處理到 PAUSING 的 status 事件後，列表顯示過渡態").isTrue();
        Map<String, Object> pausing = listRow(f.projectId(), run);
        assertThat(pausing.get("status")).as("DB 仍是六態的 RUNNING").isEqualTo("RUNNING");
        assertFoldsBack(pausing);

        mini(run).release(1);
        assertThat(awaitProjected(run, "PAUSED")).isTrue();
        Map<String, Object> paused = listRow(f.projectId(), run);
        assertThat(paused.get("status")).isEqualTo("PAUSED");
        assertThat(paused.get("bridgeStatus")).isEqualTo("PAUSED");

        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/resume").status()).isEqualTo(200);
        mini(run).release(5);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        Map<String, Object> completed = listRow(f.projectId(), run);
        assertThat(completed.get("status")).isEqualTo("COMPLETED");
        assertThat(completed.get("bridgeStatus")).as("終態批次的 bridgeStatus 等於 status").isEqualTo("COMPLETED");
    }

    @Test
    void aCancelledRunIsListedAsCancelledAndEveryRowAlwaysFoldsBackToItsStatus() {
        Fixture f = prjA("list-cancel", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();

        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/cancel").status()).isEqualTo(200);
        // 迷你 Bridge 的步驟在閘上等著、被 stop 後立刻收尾：CANCELLING 可能只出現一瞬間，所以不斷言它；
        // 但無論哪一刻去看，列表的 status 都必須是 bridgeStatus 的折疊值。
        assertFoldsBack(listRow(f.projectId(), run));
        assertThat(awaitProjected(run, "CANCELLED")).isTrue();
        Map<String, Object> cancelled = listRow(f.projectId(), run);
        assertThat(cancelled.get("status")).isEqualTo("CANCELLED");
        assertThat(cancelled.get("bridgeStatus")).isEqualTo("CANCELLED");
    }

    @Autowired
    private RunRegistry registry;

    @Test
    void afterConsoleApiLosesItsMemoryTheListFallsBackToTheDatabaseStatusAndOmitsTheFieldForARunningRun() {
        Fixture f = prjA("list-restart", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();

        registry.forget(UUID.fromString(run));          // console-api 重啟：記憶體內的執行期狀態全部消失

        Map<String, Object> running = listRow(f.projectId(), run);
        assertThat(running.get("status")).isEqualTo("RUNNING");
        assertThat(running).as("RUNNING 又沒有記憶體值：無從判斷 RUNNING／PAUSING／CANCELLING → 缺席")
                .doesNotContainKey("bridgeStatus");

        mini(run).release(5);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(listRow(f.projectId(), run).get("bridgeStatus")).isEqualTo("COMPLETED");
    }

    @Test
    void theExecutionListFiltersByStatusSortsAndRejectsBadParameters() {
        Fixture f = prjA("list-sort", 4);
        String first = startRun(f.projectId());
        assertThat(awaitProjected(first, "COMPLETED")).isTrue();
        createFixtureTask(f.g2(), "再一個", 4);
        String second = startRun(f.projectId());
        assertThat(awaitProjected(second, "COMPLETED")).isTrue();

        String base = "/api/v1/projects/" + f.projectId() + "/executions";
        assertThat(api.get(viewer(), base).<List<String>>read("$.data.content[*].id")).as("預設 startedAt,desc")
                .containsExactly(second, first);
        assertThat(api.get(viewer(), base + "?sort=runNumber,asc").<List<String>>read("$.data.content[*].id"))
                .containsExactly(first, second);
        assertThat(api.get(viewer(), base + "?status=COMPLETED").<Integer>read("$.data.totalElements")).isEqualTo(2);
        assertThat(api.get(viewer(), base + "?status=FAILED").<Integer>read("$.data.totalElements")).isZero();
        assertThat(api.get(viewer(), base + "?status=NOPE").status()).isEqualTo(400);
        assertThat(api.get(viewer(), base + "?sort=bogus").status()).isEqualTo(400);
        assertThat(api.get(viewer(), base + "?sort=startedAt,sideways").status()).isEqualTo(400);
        assertThat(api.get(viewer(), base + "?size=101").status()).isEqualTo(400);
        assertThat(api.get(viewer(), "/api/v1/projects/" + UUID.randomUUID() + "/executions").status()).isEqualTo(404);
    }

    @Test
    void unknownAndMalformedRunIdsFollowThePhaseTwoConventions() {
        String unknown = UUID.randomUUID().toString();
        Resp missing = api.get(viewer(), "/api/v1/executions/" + unknown);
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.<String>read("$.message")).isEqualTo("執行批次不存在或已刪除：" + unknown);
        Resp malformed = api.get(viewer(), "/api/v1/executions/not-a-uuid");
        assertThat(malformed.status()).isEqualTo(400);
        assertThat(malformed.<String>read("$.message")).isEqualTo("參數 runId 的值格式不正確");
        assertThat(api.get(viewer(), "/api/v1/executions/" + unknown + "/steps").status()).isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/executions/" + unknown + "/dag").status()).isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/executions/" + unknown + "/checkpoints").status()).isEqualTo(404);
        assertThat(api.post(operator(), "/api/v1/executions/" + unknown + "/pause").status()).isEqualTo(404);
        assertThat(api.post(operator(), "/api/v1/executions/" + unknown + "/resume").status()).isEqualTo(404);
        assertThat(api.post(operator(), "/api/v1/executions/" + unknown + "/cancel").status()).isEqualTo(404);
    }

    // ── 控制：pause／resume／cancel（E2E-06）───────────────────────────────────────

    @Test
    void cancelStopsARunningRunResetsTheScopeAndTheProjectCanBeExecutedAgain() {
        Fixture f = prjA("e2e06", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();

        Resp cancel = api.post(operator(), "/api/v1/executions/" + run + "/cancel");
        assertThat(cancel.status()).isEqualTo(200);
        // 快照是呼叫 Bridge 成功後「立刻再讀一次」：典型是 RUNNING＋CANCELLING，迷你 Bridge 的步驟在閘上等著、被 stop 後立刻收尾，
        // 所以也可能已是 CANCELLED＋CANCELLED（真 Bridge 同理）。不論哪一種，status 都必須是 bridgeStatus 的六態折疊值。
        String bridgeStatus = cancel.read("$.data.bridgeStatus");
        assertThat(bridgeStatus).isIn("CANCELLING", "CANCELLED");
        assertThat(cancel.<String>read("$.data.status")).as("六態折疊值")
                .isEqualTo("CANCELLING".equals(bridgeStatus) ? "RUNNING" : "CANCELLED");
        assertThat(awaitProjected(run, "CANCELLED")).isTrue();

        assertThat(taskStatus(f.t1())).isEqualTo("CANCELLED");
        assertThat(taskStatus(f.t2())).isEqualTo("CANCELLED");
        assertThat(taskStatus(f.t3())).isEqualTo("CANCELLED");
        assertThat(goalStatus(f.g1())).isEqualTo("PENDING");
        assertThat(projectStatus(f.projectId())).isEqualTo("READY");
        assertThat(getRun(run).<String>read("$.data.status")).isEqualTo("CANCELLED");
        assertThat(consumers.awaitIdle(Duration.ofSeconds(5))).as("終態處理完消費者結束").isTrue();

        MINI.manualSteps = false;
        Resp again = execute(f.projectId(), Map.of());
        assertThat(again.status()).isEqualTo(201);
        assertThat(again.<Integer>read("$.data.runNumber")).isEqualTo(2);
        assertThat(awaitProjected(again.id(), "COMPLETED")).isTrue();
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
    }

    @Test
    void cancellingAPausedRunIsImmediateAndThePausedRunKeepsItsLockUntilThen() {
        Fixture f = prjA("cancel-paused", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/pause").<String>read("$.data.bridgeStatus"))
                .isEqualTo("PAUSING");
        mini(run).release(1);
        assertThat(awaitRunStatus(run, "PAUSED")).isTrue();

        Resp cancel = api.post(operator(), "/api/v1/executions/" + run + "/cancel");
        assertThat(cancel.status()).isEqualTo(200);
        assertThat(cancel.<String>read("$.data.status")).isEqualTo("CANCELLED");
        assertThat(cancel.<String>read("$.data.bridgeStatus")).isEqualTo("CANCELLED");
        assertThat(awaitProjected(run, "CANCELLED")).isTrue();
        assertThat(taskStatus(f.t1())).as("已完成的任務不動").isEqualTo("COMPLETED");
        assertThat(taskStatus(f.t2())).isEqualTo("CANCELLED");
        assertThat(projectStatus(f.projectId())).isEqualTo("READY");
    }

    @Test
    void aManualPauseNeverCreatesAReviewItemAndResumeContinuesFromTheSameProgress() {
        Fixture f = prjA("manual-pause", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();

        Resp pause = api.post(operator(), "/api/v1/executions/" + run + "/pause");
        assertThat(pause.status()).isEqualTo(200);
        assertThat(pause.<String>read("$.data.status")).isEqualTo("RUNNING");
        assertThat(pause.<String>read("$.data.bridgeStatus")).as("過渡態在回應中可見").isEqualTo("PAUSING");
        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/pause").<String>read("$.data.bridgeStatus"))
                .as("PAUSING 時冪等").isEqualTo("PAUSING");
        mini(run).release(1);
        assertThat(awaitProjected(run, "PAUSED")).isTrue();
        assertThat(projectStatus(f.projectId())).isEqualTo("READY");
        assertThat(pendingReviews(run)).as("手動暫停沒有待決的閘").isEmpty();
        assertThat(getRun(run).<String>read("$.data.bridgeStatus")).isEqualTo("PAUSED");

        Resp pauseAgain = api.post(operator(), "/api/v1/executions/" + run + "/pause");
        assertThat(pauseAgain.status()).isEqualTo(409);
        assertThat(pauseAgain.<String>read("$.reason")).isEqualTo(ErrorReasons.RUN_STATE_NOT_ALLOWED);
        assertThat(pauseAgain.<String>read("$.details.action")).isEqualTo("pause");
        assertThat(pauseAgain.<String>read("$.details.runStatus")).isEqualTo("PAUSED");

        Resp resume = api.post(operator(), "/api/v1/executions/" + run + "/resume");
        assertThat(resume.status()).isEqualTo(200);
        assertThat(resume.<String>read("$.data.bridgeStatus")).isEqualTo("RUNNING");
        assertThat(projectStatus(f.projectId())).isEqualTo("EXECUTING");
        mini(run).release(5);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
        assertThat(mini(run).events().stream().filter(e -> "step".equals(e.get("event"))
                && "STARTED".equals(e.get("status")) && "G1-T1".equals(e.get("step_id"))).count())
                .as("續跑不重做已完成的步驟").isEqualTo(1);
    }

    // ── E2E-13 第 12 列（C-12）：traceId 貫穿 console-api → Bridge ──────────────────────────

    private List<String> tracesOf(String request) {
        return MINI.traced().stream().filter(t -> t.request().equals(request)).map(MiniBridge.Traced::traceId).toList();
    }

    @Test
    void theTraceIdOfTheRequestThatStartedARunFollowsItToTheBridgeAndTheConsumerReusesItWhileLaterRequestsCarryTheirOwn() {
        Fixture f = prjA("trace-e2e", 4);
        MINI.manualSteps = true;

        Resp execute = execute(f.projectId(), Map.of());

        assertThat(execute.status()).isEqualTo(201);
        String executeTrace = execute.header("X-Trace-Id");
        String run = execute.id();
        assertThat(executeTrace).isNotBlank();
        assertThat(tracesOf("POST /autoclaude/runs")).as("使用者請求觸發的呼叫：取當前請求的 traceId").containsExactly(executeTrace);
        assertThat(tracesOf("GET /health")).as("啟動後立即的健康探測也在同一個請求裡").containsExactly(executeTrace);
        String streamRequest = "GET /autoclaude/runs/" + run + "/stream";
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> !tracesOf(streamRequest).isEmpty()))
                .as("背景事件消費者連上了串流").isTrue();
        assertThat(tracesOf(streamRequest)).as("背景消費者沒有請求上下文：用該 run 的 traceId＝啟動它的 execute 請求的")
                .containsOnly(executeTrace);

        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        Resp pause = api.post(operator(), "/api/v1/executions/" + run + "/pause");
        assertThat(pause.status()).isEqualTo(200);
        String pauseTrace = pause.header("X-Trace-Id");
        assertThat(pauseTrace).isNotBlank().isNotEqualTo(executeTrace);
        assertThat(tracesOf("POST /autoclaude/runs/" + run + ":pause")).as("之後的使用者請求各帶自己的 traceId")
                .containsExactly(pauseTrace);

        mini(run).release(10);
        assertThat(awaitProjected(run, "PAUSED")).isTrue();
        mini(run).release(10);
        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/resume").status()).isEqualTo(200);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(MINI.traced()).as("整個過程沒有任何一個請求漏帶標頭").extracting(MiniBridge.Traced::traceId)
                .doesNotContainNull();
    }

    @Test
    void controlPreconditionsAreCheckedAgainstTheDatabaseBeforeTheBridgeIsCalled() {
        Fixture f = prjA("preconditions", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        long before = MINI.countRequests("POST /autoclaude/runs/" + run + ":");
        for (String action : List.of("pause", "resume", "cancel")) {
            Resp resp = api.post(operator(), "/api/v1/executions/" + run + "/" + action);
            assertThat(resp.status()).as(action).isEqualTo(409);
            assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.RUN_STATE_NOT_ALLOWED);
            assertThat(resp.<String>read("$.details.action")).isEqualTo(action);
            assertThat(resp.<String>read("$.details.runStatus")).isEqualTo("COMPLETED");
            assertThat(resp.<String>read("$.details.bridgeStatus")).isEqualTo("COMPLETED");
        }
        assertThat(MINI.countRequests("POST /autoclaude/runs/" + run + ":")).as("DB 預檢失敗不呼叫 Bridge")
                .isEqualTo(before);
    }

    @Test
    void controlEndpointsNeedOperatorAndUpstreamFailuresAreTranslatedWithTheDatabaseUnchanged() {
        Fixture f = prjA("control-errors", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(api.post(viewer(), "/api/v1/executions/" + run + "/pause").status()).isEqualTo(403);
        assertThat(api.post(null, "/api/v1/executions/" + run + "/cancel").status()).isEqualTo(401);

        MINI.failNext("pause", 500, Map.of("code", 500, "reason", "internal"));
        Resp boom = api.post(operator(), "/api/v1/executions/" + run + "/pause");
        assertThat(boom.status()).isEqualTo(502);
        assertThat(boom.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_ERROR);
        assertThat(runStatus(run)).isEqualTo("RUNNING");

        MINI.failNext("stop", 404, Map.of("code", 404, "reason", "run_not_found"));
        Resp unknown = api.post(operator(), "/api/v1/executions/" + run + "/cancel");
        assertThat(unknown.status()).isEqualTo(409);
        assertThat(unknown.<String>read("$.reason")).isEqualTo(ErrorReasons.RUN_UNKNOWN_AT_BRIDGE);
        assertThat(unknown.<String>read("$.details.runId")).isEqualTo(run);

        MINI.failNext("pause", 409, Map.of("code", 409, "reason", "invalid_state", "status", "PAUSED"));
        Resp invalid = api.post(operator(), "/api/v1/executions/" + run + "/pause");
        assertThat(invalid.status()).isEqualTo(409);
        assertThat(invalid.<String>read("$.reason")).isEqualTo(ErrorReasons.RUN_STATE_NOT_ALLOWED);
    }

    // ── E2E-07：還原 ───────────────────────────────────────────────────────────────

    @Test
    void restoreFromAnHistoricalCheckpointResetsTheLaterTasksKeepsTheirTokensAndRunsToTheEndAgain() {
        Fixture f = prjA("e2e07", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(consumers.awaitIdle(Duration.ofSeconds(5))).isTrue();
        String checkpoint = api.get(viewer(), "/api/v1/executions/" + run + "/checkpoints")
                .<List<Map<String, Object>>>read("$.data").stream().filter(c -> "after-G1-T1".equals(c.get("name")))
                .map(c -> (String) c.get("id")).findFirst().orElseThrow();
        int seqBefore = consoleLastSeq(run);
        MINI.manualSteps = true;

        Resp restore = api.post(operator(), "/api/v1/executions/" + run + "/restore/" + checkpoint);
        assertThat(restore.status()).isEqualTo(200);
        assertThat(restore.<String>read("$.data.status")).isEqualTo("RUNNING");
        assertThat(restore.<String>read("$.data.bridgeStatus")).isEqualTo("RUNNING");
        assertThat(projectStatus(f.projectId())).isEqualTo("EXECUTING");
        assertThat(taskStatus(f.t1())).as("快照內已完成的步驟不重設").isEqualTo("COMPLETED");
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t2())))).isTrue();
        assertThat(taskStatus(f.t3())).isEqualTo("QUEUED");
        assertThat(goalStatus(f.g2())).isEqualTo("PENDING");
        assertThat(consumers.isRunning(UUID.fromString(run))).as("終態 run 被 restore 後消費者重啟").isTrue();

        mini(run).release(5);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(consoleLastSeq(run)).isGreaterThan(seqBefore);
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
        assertThat(jdbc.queryForObject("select actual_tokens from console.tasks where id = ?", Long.class,
                UUID.fromString(f.t2()))).as("被重設任務已花的 Token 保留").isEqualTo(2480L);
        assertThat(mini(run).events().stream().filter(e -> "alert".equals(e.get("event"))
                && "RESTORE".equals(e.get("code"))).count()).isEqualTo(1);
        assertThat(projectStatus(f.projectId())).isEqualTo("COMPLETED");
    }

    @Test
    void restoreIsRefusedForUnknownCheckpointsRunningRunsOlderRunsAndUnsignedDrafts() {
        Fixture f = prjA("restore-guards", 4);
        String first = startRun(f.projectId());
        assertThat(awaitProjected(first, "COMPLETED")).isTrue();
        assertThat(consumers.awaitIdle(Duration.ofSeconds(5))).isTrue();
        String firstCheckpoint = api.get(viewer(), "/api/v1/executions/" + first + "/checkpoints")
                .<String>read("$.data[0].id");

        String missing = UUID.randomUUID().toString();
        Resp unknown = api.post(operator(), "/api/v1/executions/" + first + "/restore/" + missing);
        assertThat(unknown.status()).isEqualTo(404);
        assertThat(unknown.<String>read("$.message")).isEqualTo("checkpoint 不存在或不屬於此執行：" + missing);
        assertThat(api.post(operator(), "/api/v1/executions/" + first + "/restore/not-a-uuid").status()).isEqualTo(400);

        // 未 signoff（暫停期間被改成草案）：409，details 同 execute
        jdbc.update("update console.tasks set signed_off = false where id = ?", UUID.fromString(f.t2()));
        Resp unsigned = api.post(operator(), "/api/v1/executions/" + first + "/restore/" + firstCheckpoint);
        assertThat(unsigned.status()).isEqualTo(409);
        assertThat(unsigned.<String>read("$.reason")).isEqualTo(ErrorReasons.UNSIGNED_DRAFT);
        assertThat(unsigned.<List<String>>read("$.details.unsignedTaskIds")).containsExactly(f.t2());
        jdbc.update("update console.tasks set signed_off = true where id = ?", UUID.fromString(f.t2()));

        // 只能還原專案最新的批次
        createFixtureTask(f.g2(), "新增", 4);
        String second = startRun(f.projectId());
        assertThat(awaitProjected(second, "COMPLETED")).isTrue();
        Resp old = api.post(operator(), "/api/v1/executions/" + first + "/restore/" + firstCheckpoint);
        assertThat(old.status()).isEqualTo(409);
        assertThat(old.<String>read("$.reason")).isEqualTo(ErrorReasons.RESTORE_ONLY_LATEST);
        assertThat(old.<String>read("$.details.latestRunId")).isEqualTo(second);
        assertThat(old.<Integer>read("$.details.latestRunNumber")).isEqualTo(2);

        // 一個 checkpoint 屬於另一個 run：404
        String secondCheckpoint = api.get(viewer(), "/api/v1/executions/" + second + "/checkpoints")
                .<List<String>>read("$.data[*].id").get(0);
        assertThat(api.post(operator(), "/api/v1/executions/" + second + "/restore/" + firstCheckpoint).status())
                .isEqualTo(404);
        assertThat(secondCheckpoint).isNotEqualTo(firstCheckpoint);
    }

    @Test
    void restoreOfARunningRunIs409() {
        Fixture f = prjA("restore-running", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        mini(run).release(1);
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> jdbc.queryForObject(
                "select count(*) from console.checkpoints where run_id = ?", Long.class, UUID.fromString(run)) >= 1))
                .isTrue();
        String checkpoint = api.get(viewer(), "/api/v1/executions/" + run + "/checkpoints")
                .<List<String>>read("$.data[*].id").get(0);
        Resp resp = api.post(operator(), "/api/v1/executions/" + run + "/restore/" + checkpoint);
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.RUN_STATE_NOT_ALLOWED);
        assertThat(resp.<String>read("$.details.action")).isEqualTo("restore");
    }

    @Test
    void restoringAPausedRunDiscardsTheOpenGateReviewAsRestoredBySystem() {
        Fixture f = prjA("restore-paused", 1);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "PAUSING".equals(mini(run).status()))).isTrue();
        mini(run).release(1);
        String review = awaitPendingReview(run);
        String checkpoint = api.get(viewer(), "/api/v1/executions/" + run + "/checkpoints")
                .<List<String>>read("$.data[*].id").get(0);

        Resp restore = api.post(operator(), "/api/v1/executions/" + run + "/restore/" + checkpoint);
        assertThat(restore.status()).isEqualTo(200);
        Map<String, Object> row = jdbc.queryForMap("select status, decided_by, comment from console.review_requests "
                + "where id = ?", UUID.fromString(review));
        assertThat(row.get("status")).isEqualTo("REJECTED");
        assertThat(row.get("decided_by")).isEqualTo("system");
        assertThat(row.get("comment")).isEqualTo("執行已還原");
    }

    // ── Bridge 不可達、不認得、重連與啟動對帳 ─────────────────────────────────────────

    @Test
    void whenTheBridgeIsUnreachableGetRunStillAnswers200FromTheDatabaseWithConnectedFalse() {
        Fixture f = prjA("unreachable", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        setting("autoclaude", "engineUrl", "http://127.0.0.1:1");

        Resp resp = getRun(run);
        assertThat(resp.status()).as("Bridge 不可達不回 5xx（主控裁決）").isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.bridge.connected")).isFalse();
        assertThat(resp.has("$.data.bridge.status")).isFalse();
        assertThat(resp.has("$.data.currentStep")).isFalse();
        assertThat(resp.<String>read("$.data.status")).isEqualTo("COMPLETED");
        assertThat(resp.<Integer>read("$.data.completedSteps")).as("由 DB 衍生").isEqualTo(3);
        assertThat(resp.<Integer>read("$.data.totalSteps")).isEqualTo(3);
        assertThat(resp.<Integer>read("$.data.lastEventSeq")).isPositive();
        assertThat(resp.<String>read("$.data.bridge.checkedAt")).isNotBlank();
    }

    @Test
    void whenTheBridgeNoLongerKnowsTheRunItIsReportedAsConnectedButUnknown() {
        Fixture f = prjA("unknown-at-bridge", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        MINI.reset();
        Resp resp = getRun(run);
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.bridge.connected")).isTrue();
        assertThat(resp.<Boolean>read("$.data.bridge.runKnown")).isFalse();
        assertThat(resp.<Integer>read("$.data.completedSteps")).isEqualTo(3);
    }

    @Test
    void aDroppedEventStreamIsReconnectedAndTheGapIsBackfilledWithoutDuplicates() {
        Fixture f = prjA("reconnect", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        MINI.dropStreams();
        mini(run).release(3);

        assertThat(awaitProjected(run, "COMPLETED")).as("斷線期間發生的事件由重連回補").isTrue();
        assertThat(consoleLastSeq(run)).isEqualTo(mini(run).lastSeq());
        assertThat(jdbc.queryForObject("select count(*) from console.execution_steps where run_id = ?", Long.class,
                UUID.fromString(run))).isEqualTo(6L);
        assertThat(jdbc.queryForObject("select count(*) from console.run_token_samples where run_id = ?", Long.class,
                UUID.fromString(run))).as("Token 樣本冪等").isEqualTo(3L);
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
        assertThat(jdbc.queryForObject("select sum(actual_tokens) from console.tasks", Long.class)).isEqualTo(3720L);
    }

    @Test
    void afterAConsoleRestartTheStartupReconciliationResumesConsumptionFromTheStoredOffset() {
        Fixture f = prjA("reconcile", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        mini(run).release(1);
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "COMPLETED".equals(taskStatus(f.t1())))).isTrue();

        consumers.stopAll();
        assertThat(consumers.isRunning(UUID.fromString(run))).isFalse();
        int stored = consoleLastSeq(run);
        mini(run).release(5);
        assertThat(awaitRunStatus(run, "COMPLETED")).isTrue();
        assertThat(consoleLastSeq(run)).as("消費者停著時位移不動").isEqualTo(stored);

        ticker.reconcile();
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
        assertThat(projectStatus(f.projectId())).isEqualTo("COMPLETED");
    }

    @Test
    void theStartupReconciliationLeavesTheDatabaseAloneWhenTheBridgeNoLongerKnowsTheRun() {
        Fixture f = prjA("reconcile-404", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        consumers.stopAll();
        MINI.reset();

        ticker.reconcile();
        assertThat(consumers.isRunning(UUID.fromString(run))).as("Bridge 回 404 → 不啟動消費者").isFalse();
        assertThat(runStatus(run)).as("狀態欄由 Bridge 擁有，DB 不動").isEqualTo("RUNNING");
        assertThat(taskStatus(f.t1())).isEqualTo("RUNNING");
    }

    @Test
    void theStartupReconciliationStartsConsumersEvenWhenTheBridgeIsTemporarilyUnreachable() {
        Fixture f = prjA("reconcile-down", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        consumers.stopAll();
        setting("autoclaude", "engineUrl", "http://127.0.0.1:1");

        ticker.reconcile();
        assertThat(consumers.isRunning(UUID.fromString(run))).as("不可達時仍啟動消費者，由連線層重試").isTrue();
    }

    // ── 健康探測環與通知摘要 ─────────────────────────────────────────────────────

    @Test
    void theNotificationSummaryShowsTheLatestBridgeProbeResultAndTime() {
        health.probeNow();
        Resp up = api.get(viewer(), "/api/v1/notifications/summary");
        assertThat(up.<Boolean>read("$.data.bridgeConnected")).isTrue();
        assertThat(up.<String>read("$.data.bridgeCheckedAt")).isNotBlank();

        setting("autoclaude", "engineUrl", "http://127.0.0.1:1");
        health.probeNow();
        assertThat(api.get(viewer(), "/api/v1/notifications/summary").<Boolean>read("$.data.bridgeConnected"))
                .isFalse();
    }

    @Test
    void startingARunProbesTheBridgeAndTheTickerKeepsProbing() {
        Fixture f = prjA("probe", 4);
        MINI.manualSteps = true;
        int before = health.size();
        startRun(f.projectId());
        assertThat(health.size()).as("每個 run 開始時立即探測一次").isGreaterThan(before);
        int afterStart = health.size();
        ticker.tick();
        assertThat(health.size()).isEqualTo(afterStart + 1);
        assertThat(MINI.countRequests("GET /health")).isGreaterThanOrEqualTo(2);
    }
}
