package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 自治等級的審核閘與審核決定（契約 §3.6、§1.2.11；E2E-04、E2E-05）。閘點「提前一步」：在要停的那一步 {@code STARTED} 時就呼叫
 * {@code :pause}，等它的 {@code COMPLETED} 才呼叫就晚了一步。以迷你 Bridge 的手動步驟（{@code manualSteps}）決定性地控制時序：
 * 步驟 STARTED 後停在閘上，測試 {@code release(n)} 才讓它完成。
 */
class ExecutionGateApiIT extends AbstractExecutionIT {

    private void awaitPausing(String run) {
        assertThat(awaitUntil(Duration.ofSeconds(15), () -> "PAUSING".equals(mini(run).status())))
                .as("Console 在步驟 STARTED 時就呼叫了 :pause（提前一步）").isTrue();
    }

    private static List<String> stepStarts(List<Map<String, Object>> events, String stepId) {
        return events.stream().filter(e -> "step".equals(e.get("event")) && "STARTED".equals(e.get("status"))
                && stepId.equals(e.get("step_id"))).map(e -> String.valueOf(e.get("seq"))).toList();
    }

    // ── Level 1：每個下一個任務都要確認 ─────────────────────────────────────────────

    @Test
    void levelOneStopsAfterEveryTaskExceptTheLastAndEachApprovalResumesTheRun() {
        Fixture f = prjA("e2e04-l1", 1);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());

        awaitPausing(run);
        mini(run).release(1);
        String first = awaitPendingReview(run);
        Map<String, Object> pending = pendingReviews(run).get(0);
        assertThat(pending.get("kind")).isEqualTo("TASK_CONFIRM");
        assertThat(pending.get("status")).isEqualTo("PENDING");
        assertThat(pending.get("taskId")).isEqualTo(f.t2());
        assertThat(pending.get("goalId")).isEqualTo(f.g1());
        assertThat(pending.get("taskName")).isEqualTo("設定");
        assertThat(pending.get("goalName")).isEqualTo("基礎");
        assertThat(pending.get("reason")).isEqualTo("Level 1：請確認是否繼續執行任務「設定」");
        assertThat(pending.get("allowedDecisions")).isEqualTo(List.of("APPROVE", "REJECT"));
        String evidence = jdbc.queryForObject("select id::text from console.execution_steps where run_id = ? "
                + "and status = 'COMPLETED' and input ->> 'step_id' = 'G1-T1'", String.class, UUID.fromString(run));
        assertThat(pending.get("stepId")).as("佐證＝剛完成步驟的 COMPLETED 列（execution_steps.id）").isEqualTo(evidence);
        Resp paused = getRun(run);
        assertThat(paused.<String>read("$.data.status")).isEqualTo("PAUSED");
        assertThat(paused.<String>read("$.data.bridgeStatus")).isEqualTo("PAUSED");
        assertThat(projectStatus(f.projectId())).isEqualTo("READY");
        assertThat(taskStatus(f.t1())).isEqualTo("COMPLETED");
        assertThat(taskStatus(f.t2())).as("下一個任務還沒開始").isEqualTo("QUEUED");

        Resp approve = review(run, first, "APPROVE");
        assertThat(approve.status()).isEqualTo(204);
        assertThat(approve.body()).isEmpty();
        assertThat(approve.header("X-Follow-Up-Run-Id")).as("只有 SKIP／RETRY 開後續批次才帶這個標頭").isNull();
        assertThat(projectStatus(f.projectId())).isEqualTo("EXECUTING");
        assertThat(pendingReviews(run)).isEmpty();

        awaitPausing(run);
        mini(run).release(1);
        String second = awaitPendingReview(run);
        assertThat(second).isNotEqualTo(first);
        assertThat(pendingReviews(run).get(0).get("reason")).isEqualTo("Level 1：請確認是否繼續執行任務「實作」");
        assertThat(review(run, second, "APPROVE").status()).isEqualTo(204);

        mini(run).release(1);
        assertThat(awaitProjected(run, "COMPLETED")).as("最後一步不暫停、不建審核項").isTrue();
        List<Map<String, Object>> rows = jdbc.queryForList("select kind, status, decided_by, comment, event_sub "
                + "from console.review_requests where run_id = ? order by requested_at", UUID.fromString(run));
        assertThat(rows).hasSize(2);
        assertThat(rows).extracting(r -> r.get("kind")).containsOnly("TASK_CONFIRM");
        assertThat(rows).extracting(r -> r.get("status")).containsOnly("APPROVED");
        assertThat(rows).extracting(r -> r.get("decided_by")).containsOnly("operator");
        assertThat(rows).extracting(r -> r.get("event_sub")).as("Console 自產事件的子序號 ≥ 1").allMatch(
                sub -> ((Number) sub).intValue() >= 1);
        assertThat(MINI.countRequests("POST /autoclaude/runs/" + run + ":pause")).as("每個 (run, 步驟) 只呼叫一次")
                .isEqualTo(2);
        assertThat(MINI.countRequests("POST /autoclaude/runs/" + run + ":resume")).isEqualTo(2);
        for (String step : List.of("G1-T1", "G1-T2", "G2-T1")) {
            assertThat(stepStarts(mini(run).events(), step)).as(step + " 的 STARTED 恰一次").hasSize(1);
        }
        assertThat(projectStatus(f.projectId())).isEqualTo("COMPLETED");
    }

    @Test
    void rejectingAtALevelOneGateCancelsTheRunWithoutMarkingAnyGoalAndTheOpenItemIsClosed() {
        Fixture f = prjA("e2e04-reject", 1);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        awaitPausing(run);
        mini(run).release(1);
        String item = awaitPendingReview(run);

        Resp reject = api.post(operator(), "/api/v1/executions/" + run + "/review/" + item,
                Map.of("decision", "REJECT", "comment", "結果不符預期"));
        assertThat(reject.status()).isEqualTo(204);
        assertThat(awaitProjected(run, "CANCELLED")).isTrue();
        Map<String, Object> row = jdbc.queryForMap("select status, decided_by, comment from console.review_requests "
                + "where id = ?", UUID.fromString(item));
        assertThat(row.get("status")).isEqualTo("REJECTED");
        assertThat(row.get("decided_by")).isEqualTo("operator");
        assertThat(row.get("comment")).isEqualTo("結果不符預期");
        assertThat(taskStatus(f.t1())).isEqualTo("COMPLETED");
        assertThat(taskStatus(f.t2())).isEqualTo("CANCELLED");
        assertThat(taskStatus(f.t3())).isEqualTo("CANCELLED");
        assertThat(goalStatus(f.g1())).as("TASK_CONFIRM 的 REJECT 不另標目標，由 R-goal 推導").isEqualTo("IN_PROGRESS");
        assertThat(projectStatus(f.projectId())).isEqualTo("READY");
    }

    // ── 審核決定的驗證 ──────────────────────────────────────────────────────────────

    @Test
    void aDecisionOutsideAllowedDecisionsAnAlreadyDecidedItemAndForeignItemsAreRefused() {
        Fixture f = prjA("decisions", 1);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        awaitPausing(run);
        mini(run).release(1);
        String item = awaitPendingReview(run);
        String path = "/api/v1/executions/" + run + "/review/";

        Resp notAllowed = review(run, item, "RETRY");
        assertThat(notAllowed.status()).isEqualTo(409);
        assertThat(notAllowed.<String>read("$.reason")).isEqualTo(ErrorReasons.REVIEW_DECISION_NOT_ALLOWED);
        assertThat(notAllowed.<String>read("$.details.kind")).isEqualTo("TASK_CONFIRM");
        assertThat(notAllowed.<String>read("$.details.decision")).isEqualTo("RETRY");
        assertThat(notAllowed.<List<String>>read("$.details.allowedDecisions")).containsExactly("APPROVE", "REJECT");
        assertThat(review(run, item, "SKIP").status()).isEqualTo(409);
        assertThat(pendingReviews(run)).as("被拒的決定不改任何狀態").hasSize(1);

        String missing = UUID.randomUUID().toString();
        Resp unknown = review(run, missing, "APPROVE");
        assertThat(unknown.status()).isEqualTo(404);
        assertThat(unknown.<String>read("$.message")).isEqualTo("審核項不存在或不屬於此執行：" + missing);
        Fixture other = prjA("other-run", 4);
        MINI.manualSteps = true;
        String otherRun = startRun(other.projectId());
        assertThat(review(otherRun, item, "APPROVE").status()).as("審核項屬於另一個執行").isEqualTo(404);

        assertThat(api.post(operator(), path + item, Map.of()).status()).isEqualTo(400);
        assertThat(api.post(operator(), path + item, Map.of()).errorFields()).contains("decision");
        assertThat(api.post(operator(), path + item, Map.of("decision", "MAYBE")).status()).isEqualTo(400);
        Resp longComment = api.post(operator(), path + item, Map.of("decision", "APPROVE", "comment", "字".repeat(2001)));
        assertThat(longComment.status()).isEqualTo(400);
        assertThat(longComment.errorFields()).contains("comment");
        assertThat(api.post(operator(), path + "not-a-uuid", Map.of("decision", "APPROVE")).status()).isEqualTo(400);
        assertThat(api.post(viewer(), path + item, Map.of("decision", "APPROVE")).status()).isEqualTo(403);
        assertThat(api.post(null, path + item, Map.of("decision", "APPROVE")).status()).isEqualTo(401);

        Resp approved = api.post(operator(), path + item, Map.of("decision", "APPROVE", "comment", "同意"));
        assertThat(approved.status()).isEqualTo(204);
        Resp again = review(run, item, "APPROVE");
        assertThat(again.status()).isEqualTo(409);
        assertThat(again.<String>read("$.reason")).isEqualTo(ErrorReasons.REVIEW_ALREADY_DECIDED);
        assertThat(again.<String>read("$.details.status")).isEqualTo("APPROVED");
        assertThat(again.<String>read("$.details.decidedBy")).isEqualTo("operator");
        assertThat(again.<String>read("$.details.decidedAt")).isNotBlank();
        assertThat(jdbc.queryForObject("select comment from console.review_requests where id = ?", String.class,
                UUID.fromString(item))).isEqualTo("同意");
    }

    @Test
    void aDoubleClickOnTheSameDecisionResumesTheRunExactlyOnce() throws Exception {
        Fixture f = prjA("double-click", 1);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        awaitPausing(run);
        mini(run).release(1);
        String item = awaitPendingReview(run);

        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            List<Callable<Integer>> clicks = new ArrayList<>();
            for (int i = 0; i < 2; i++) {
                clicks.add(() -> review(run, item, "APPROVE").status());
            }
            List<Integer> statuses = new ArrayList<>();
            for (Future<Integer> future : pool.invokeAll(clicks)) {
                statuses.add(future.get());
            }
            assertThat(statuses).containsExactlyInAnyOrder(204, 409);
        } finally {
            pool.shutdownNow();
        }
        assertThat(MINI.countRequests("POST /autoclaude/runs/" + run + ":resume")).isEqualTo(1);
    }

    @Test
    void aManualResumeClosesTheOpenGateItemAsApprovedByTheCaller() {
        Fixture f = prjA("manual-resume", 1);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        awaitPausing(run);
        mini(run).release(1);
        String item = awaitPendingReview(run);

        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/resume").status()).isEqualTo(200);
        Map<String, Object> row = jdbc.queryForMap("select status, decided_by, comment from console.review_requests "
                + "where id = ?", UUID.fromString(item));
        assertThat(row.get("status")).isEqualTo("APPROVED");
        assertThat(row.get("decided_by")).isEqualTo("operator");
        assertThat(row.get("comment")).isEqualTo("以手動恢復處理");
        assertThat(review(run, item, "APPROVE").status()).isEqualTo(409);
    }

    // ── Level 2／3：目標邊界 ────────────────────────────────────────────────────────

    @Test
    void levelTwoAsksBeforeTheNextGoalStarts() {
        Fixture f = prjA("e2e04-l2", 2);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        mini(run).release(1);
        awaitPausing(run);
        mini(run).release(1);
        String item = awaitPendingReview(run);
        Map<String, Object> pending = pendingReviews(run).get(0);
        assertThat(pending.get("kind")).isEqualTo("GOAL_CONFIRM");
        assertThat(pending.get("goalName")).as("下一個目標").isEqualTo("核心");
        assertThat(pending.get("goalId")).isEqualTo(f.g2());
        assertThat(pending.get("taskId")).as("該目標第一個任務").isEqualTo(f.t3());
        assertThat(pending.get("reason")).isEqualTo("Level 2：請確認是否開始目標「核心」");
        assertThat(pending.get("allowedDecisions")).isEqualTo(List.of("APPROVE", "REJECT"));
        assertThat(taskStatus(f.t2())).isEqualTo("COMPLETED");
        assertThat(goalStatus(f.g1())).isEqualTo("COMPLETED");

        assertThat(review(run, item, "APPROVE").status()).isEqualTo(204);
        mini(run).release(1);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(jdbc.queryForObject("select count(*) from console.review_requests where run_id = ?", Long.class,
                UUID.fromString(run))).isEqualTo(1L);
    }

    @Test
    void levelThreeAsksForAReviewOfTheGoalJustFinishedAndApproveContinues() {
        Fixture f = prjA("e2e04-l3", 3);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        mini(run).release(1);
        awaitPausing(run);
        mini(run).release(1);
        String item = awaitPendingReview(run);
        Map<String, Object> pending = pendingReviews(run).get(0);
        assertThat(pending.get("kind")).isEqualTo("GOAL_COMPLETED");
        assertThat(pending.get("goalName")).as("剛完成的目標").isEqualTo("基礎");
        assertThat(pending.get("goalId")).isEqualTo(f.g1());
        assertThat(pending.get("taskId")).as("其最後一個任務").isEqualTo(f.t2());
        assertThat(pending.get("reason")).isEqualTo("目標「基礎」已完成，等待人類審核");
        assertThat(pending.get("allowedDecisions")).isEqualTo(List.of("APPROVE", "REJECT", "RETRY"));

        assertThat(review(run, item, "APPROVE").status()).isEqualTo(204);
        mini(run).release(1);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
    }

    @Test
    void rejectingAFinishedGoalMarksItFailedByHumanJudgementAndALaterRecomputeDoesNotOverwriteIt() {
        Fixture f = prjA("e2e04-l3-reject", 3);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        mini(run).release(1);
        awaitPausing(run);
        mini(run).release(1);
        String item = awaitPendingReview(run);

        assertThat(review(run, item, "REJECT").status()).isEqualTo(204);
        assertThat(awaitProjected(run, "CANCELLED")).isTrue();
        assertThat(taskStatus(f.t1())).isEqualTo("COMPLETED");
        assertThat(taskStatus(f.t2())).isEqualTo("COMPLETED");
        assertThat(goalStatus(f.g1())).as("人工判定優先於 R-goal（AR-11）：任務全完成也維持 FAILED").isEqualTo("FAILED");
        assertThat(projectStatus(f.projectId())).isEqualTo("READY");
    }

    @Test
    void aCrossOriginRetryLetsTheBrowserReadTheFollowUpRunId() {
        Fixture f = prjA("e2e04-cors-retry", 3);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        mini(run).release(1);
        awaitPausing(run);
        mini(run).release(1);
        String item = awaitPendingReview(run);
        assertThat(awaitProjected(run, "PAUSED")).isTrue();

        Resp retry = api.send(operator(), MockMvcRequestBuilders.post("/api/v1/executions/" + run + "/review/" + item)
                .contentType(MediaType.APPLICATION_JSON).content("{\"decision\":\"RETRY\"}")
                .header(HttpHeaders.ORIGIN, "http://localhost:3000"));
        assertThat(retry.status()).isEqualTo(204);
        assertThat(retry.header("X-Follow-Up-Run-Id")).isNotBlank();
        assertThat(retry.header(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isEqualTo("http://localhost:3000");
        assertThat(retry.header(HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS))
                .as("瀏覽器端的 JS 只有在 Expose-Headers 列出它時才讀得到新批次 id（前端據此切換到後續批次）")
                .contains("X-Follow-Up-Run-Id");
    }

    @Test
    void retryingTheFirstGoalHasNoEarlierCheckpointSoItStopsAndOpensAFollowUpRun() {
        Fixture f = prjA("e2e04-l3-retry", 3);
        MINI.manualSteps = true;
        String run = startRun(f.projectId(), Map.of("tokenBudget", 50000));
        mini(run).release(1);
        awaitPausing(run);
        mini(run).release(1);
        String item = awaitPendingReview(run);
        assertThat(awaitProjected(run, "PAUSED")).isTrue();

        Resp retry = review(run, item, "RETRY");
        assertThat(retry.status()).isEqualTo(204);
        String followUp = retry.header("X-Follow-Up-Run-Id");
        assertThat(followUp).as("找不到還原點而改開後續批次").isNotBlank().isNotEqualTo(run);
        assertThat(jdbc.queryForObject("select status from console.review_requests where id = ?", String.class,
                UUID.fromString(item))).isEqualTo("RETRIED");

        Resp detail = getRun(followUp);
        assertThat(detail.<Integer>read("$.data.runNumber")).isEqualTo(2);
        assertThat(detail.<String>read("$.data.scope.mode")).isEqualTo("SELECTED");
        assertThat(detail.<String>read("$.data.scope.followUpOfRunId")).isEqualTo(run);
        assertThat(detail.<List<String>>read("$.data.scope.taskIds")).containsExactlyInAnyOrder(f.t1(), f.t2(), f.t3());
        assertThat(detail.<Integer>read("$.data.autonomyLevel")).as("繼承原批次").isEqualTo(3);
        assertThat(detail.<Integer>read("$.data.tokenBudget")).isEqualTo(50000);
        assertThat(detail.has("$.data.followUpOfRunId")).as("只在 scope 內有").isFalse();

        // 原批次被 stop；它遲到的 CANCELLED 事件不得把已交給新批次的任務重設回去
        assertThat(awaitProjected(run, "CANCELLED")).isTrue();
        assertThat(taskStatus(f.t1())).as("原批次的 CANCELLED 不得重設新批次的任務").isIn("QUEUED", "RUNNING");
        // 後續批次同樣是 Level 3：第一個目標做完再停一次（GOAL_COMPLETED），核准後跑完
        mini(followUp).release(1);
        awaitPausing(followUp);
        mini(followUp).release(1);
        String again = awaitPendingReview(followUp);
        assertThat(review(followUp, again, "APPROVE").status()).isEqualTo(204);
        mini(followUp).release(1);
        assertThat(awaitProjected(followUp, "COMPLETED")).isTrue();
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
        assertThat(goalStatus(f.g1())).isEqualTo("COMPLETED");
        assertThat(goalStatus(f.g2())).isEqualTo("COMPLETED");
        assertThat(projectStatus(f.projectId())).isEqualTo("COMPLETED");
        assertThat(runStatus(run)).isEqualTo("CANCELLED");
    }

    // ── E2E-05：ESCALATED ─────────────────────────────────────────────────────────

    /** 在 G1-T2 失敗的 Level 4 批次（引擎重試 1 次後升級）；回傳已投影到 FAILED 的 runId。 */
    private String failingRun(Fixture f) {
        MINI.failStepIds.add("G1-T2");
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "FAILED")).isTrue();
        return run;
    }

    @Test
    void anEscalationFailsTheRunEscalatesTheTaskAndCreatesTheEscalatedReviewWithThePersistedAlert() {
        Fixture f = prjA("e2e05", 4);
        String run = failingRun(f);

        assertThat(taskStatus(f.t1())).isEqualTo("COMPLETED");
        assertThat(taskStatus(f.t2())).isEqualTo("ESCALATED");
        assertThat(taskStatus(f.t3())).as("範圍內仍 QUEUED 者系統重設為 PENDING").isEqualTo("PENDING");
        assertThat(goalStatus(f.g1())).isEqualTo("FAILED");
        assertThat(goalStatus(f.g2())).isEqualTo("PENDING");
        assertThat(projectStatus(f.projectId())).isEqualTo("FAILED");
        assertThat(jdbc.queryForObject("select retry_count from console.tasks where id = ?", Integer.class,
                UUID.fromString(f.t2()))).isEqualTo(1);
        Resp detail = getRun(run);
        assertThat(detail.<String>read("$.data.status")).isEqualTo("FAILED");
        assertThat(detail.<String>read("$.data.reason")).startsWith("引擎升級（ESCALATION）");

        List<Map<String, Object>> reviews = pendingReviews(run);
        assertThat(reviews).hasSize(1);
        Map<String, Object> escalated = reviews.get(0);
        assertThat(escalated.get("kind")).isEqualTo("ESCALATED");
        assertThat(escalated.get("taskId")).isEqualTo(f.t2());
        assertThat(escalated.get("goalId")).isEqualTo(f.g1());
        assertThat(escalated.get("allowedDecisions")).isEqualTo(List.of("RETRY", "SKIP", "REJECT"));
        assertThat((String) escalated.get("reason")).startsWith("任務「設定」重試 1 次仍失敗，需要人類介入：引擎升級（ESCALATION）");
        String failedRow = jdbc.queryForObject("select id::text from console.execution_steps where run_id = ? "
                + "and status = 'FAILED'", String.class, UUID.fromString(run));
        assertThat(escalated.get("stepId")).isEqualTo(failedRow);

        Resp alerts = api.get(viewer(), "/api/v1/monitor/projects/" + f.projectId() + "/alerts?runId=" + run);
        assertThat(alerts.<List<String>>read("$.data[*].rule")).containsExactly("ENGINE_ESCALATION");
        assertThat(alerts.<String>read("$.data[0].severity")).isEqualTo("CRITICAL");
        assertThat(alerts.<String>read("$.data[0].subject")).isEqualTo("step:G1-T2");
        assertThat(alerts.<String>read("$.data[0].message")).startsWith("引擎升級（ESCALATION）：");
        assertThat(alerts.<Boolean>read("$.data[0].acknowledged")).isFalse();
        assertThat(jdbc.queryForObject("select event_sub from console.alerts where run_id = ?", Integer.class,
                UUID.fromString(run))).as("Bridge 告警的持久化鏡像 event_sub＝0").isZero();
    }

    @Test
    void retryRestoresToTheCheckpointBeforeTheFailedStepAndTheSameRunFinishes() {
        Fixture f = prjA("e2e05-retry", 4);
        String run = failingRun(f);
        String item = (String) pendingReviews(run).get(0).get("id");
        MINI.failStepIds.clear();

        Resp retry = review(run, item, "RETRY");
        assertThat(retry.status()).isEqualTo(204);
        assertThat(retry.header("X-Follow-Up-Run-Id")).as("restore 沿用同一個批次").isNull();
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();

        assertThat(jdbc.queryForObject("select status from console.review_requests where id = ?", String.class,
                UUID.fromString(item))).isEqualTo("RETRIED");
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
        assertThat(jdbc.queryForObject("select retry_count from console.tasks where id = ?", Integer.class,
                UUID.fromString(f.t2()))).as("引擎內重試 1 次＋人工 RETRY 1 次").isEqualTo(2);
        assertThat(projectStatus(f.projectId())).isEqualTo("COMPLETED");
        assertThat(stepStarts(mini(run).events(), "G1-T2")).as("restore 後該步驟再發一次 STARTED（attempt=1）").hasSize(2);
        assertThat(mini(run).events().stream().filter(e -> "alert".equals(e.get("event"))
                && "RESTORE".equals(e.get("code"))).count()).as("審核 RETRY 內部的 restore 也由 Bridge 發 RESTORE 告警").isEqualTo(1);
    }

    @Test
    void skipRemovesTheFailedTaskAndOpensAFollowUpRunForTheRest() {
        Fixture f = prjA("e2e05-skip", 4);
        String run = failingRun(f);
        String item = (String) pendingReviews(run).get(0).get("id");
        MINI.failStepIds.clear();

        Resp skip = review(run, item, "SKIP");
        assertThat(skip.status()).isEqualTo(204);
        String followUp = skip.header("X-Follow-Up-Run-Id");
        assertThat(followUp).isNotBlank().isNotEqualTo(run);
        assertThat(awaitProjected(followUp, "COMPLETED")).isTrue();

        assertThat(jdbc.queryForObject("select status from console.review_requests where id = ?", String.class,
                UUID.fromString(item))).as("先標 SKIPPED，再自動關閉其他待決項（AR-21）").isEqualTo("SKIPPED");
        assertThat(taskStatus(f.t1())).isEqualTo("COMPLETED");
        assertThat(taskStatus(f.t2())).isEqualTo("SKIPPED");
        assertThat(taskStatus(f.t3())).isEqualTo("COMPLETED");
        assertThat(goalStatus(f.g1())).as("COMPLETED／SKIPPED 都算完成，非全部 SKIPPED").isEqualTo("COMPLETED");
        assertThat(goalStatus(f.g2())).isEqualTo("COMPLETED");
        assertThat(projectStatus(f.projectId())).isEqualTo("COMPLETED");
        Resp detail = getRun(followUp);
        assertThat(detail.<String>read("$.data.scope.followUpOfRunId")).isEqualTo(run);
        assertThat(detail.<List<String>>read("$.data.scope.taskIds")).containsExactly(f.t3());
        assertThat(runStatus(run)).as("原批次維持 FAILED").isEqualTo("FAILED");
    }

    @Test
    void rejectingAnEscalationJustClosesTheItemAndNeverCallsTheBridge() {
        Fixture f = prjA("e2e05-reject", 4);
        String run = failingRun(f);
        String item = (String) pendingReviews(run).get(0).get("id");
        long before = MINI.countRequests("POST /autoclaude/runs");

        assertThat(review(run, item, "REJECT").status()).isEqualTo(204);
        assertThat(MINI.countRequests("POST /autoclaude/runs")).as("不呼叫 Bridge").isEqualTo(before);
        assertThat(runStatus(run)).isEqualTo("FAILED");
        assertThat(taskStatus(f.t2())).isEqualTo("ESCALATED");
        assertThat(goalStatus(f.g1())).isEqualTo("FAILED");
        assertThat(projectStatus(f.projectId())).isEqualTo("FAILED");
        assertThat(pendingReviews(run)).isEmpty();
    }

    @Test
    void aFailureAtTheFirstStepOffersNoCheckpointSoRetryOpensAFollowUpRun() {
        Fixture f = prjA("e2e05-first", 4);
        MINI.failStepIds.add("G1-T1");
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "FAILED")).isTrue();
        String item = (String) pendingReviews(run).get(0).get("id");
        MINI.failStepIds.clear();

        Resp retry = review(run, item, "RETRY");
        assertThat(retry.status()).isEqualTo(204);
        String followUp = retry.header("X-Follow-Up-Run-Id");
        assertThat(followUp).isNotBlank();
        assertThat(awaitProjected(followUp, "COMPLETED")).isTrue();
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
        assertThat(jdbc.queryForObject("select status from console.review_requests where id = ?", String.class,
                UUID.fromString(item))).isEqualTo("RETRIED");
    }

    @Test
    void aNewRunClosesTheOldRunsPendingReviewItemsAsReplaced() {
        Fixture f = prjA("replaced", 4);
        String run = failingRun(f);
        String item = (String) pendingReviews(run).get(0).get("id");
        MINI.failStepIds.clear();

        String second = startRun(f.projectId());
        Map<String, Object> row = jdbc.queryForMap("select status, decided_by, comment from console.review_requests "
                + "where id = ?", UUID.fromString(item));
        assertThat(row.get("status")).isEqualTo("REJECTED");
        assertThat(row.get("decided_by")).isEqualTo("system");
        assertThat(row.get("comment")).isEqualTo("已由第 2 批次取代");
        assertThat(awaitProjected(second, "COMPLETED")).isTrue();
    }
}
