package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.AlertEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Kind;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.LogEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.MetricUpdateEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.StatusChangeEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.TokenUpdateEventData;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeEvent;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.service.RunEventProcessor.Outcome;
import com.aisdlc.console.application.service.RunEventProcessor.PauseAction;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Edge;
import com.aisdlc.console.domain.model.execution.DagSnapshot.EdgeKind;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.DagSnapshot.NodeKind;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.aisdlc.console.support.AbstractExecutionIT;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 事件投影表（契約 §3.5.2）逐列：每一種 Bridge 事件對任務、目標、專案、審核項、告警與前端框架的效果，以及冪等
 * （{@code seq ≤ console_last_seq} 一律略過；重複的 {@code STARTED} 被忽略）。
 *
 * <p>直接把 {@link BridgeEvent} 餵給 {@link RunEventProcessor}（不經網路、不經消費者執行緒），事件序列完全由測試決定，
 * 所以每個轉換都能精確斷言；批次列與 DAG 以 PRJ-A 的 id 手動寫入（等同「execute 成功之後」的狀態）。
 */
class RunEventProjectionIT extends AbstractExecutionIT {

    @Autowired
    private RunEventProcessor processor;
    @Autowired
    private ExecutionRunRepository runRepository;
    @Autowired
    private RunRegistry registry;
    @Autowired
    private PlatformTransactionManager transactions;

    /** 一個已啟動的批次與它的事件序號計數器。 */
    private final class Run {

        final Fixture f;
        final UUID id;
        int seq;

        Run(Fixture f, UUID id) {
            this.f = f;
            this.id = id;
        }

        Outcome send(String event, Object... keyValues) {
            Map<String, Object> data = new LinkedHashMap<>();
            for (int i = 0; i < keyValues.length; i += 2) {
                data.put((String) keyValues[i], keyValues[i + 1]);
            }
            return sendAt(++seq, event, data);
        }

        Outcome sendAt(int atSeq, String event, Map<String, Object> data) {
            BridgeEvent e = new BridgeEvent(atSeq, OffsetDateTime.now(ZoneOffset.UTC).toString(), event, data);
            return new TransactionTemplate(transactions).execute(status ->
                    registry.locked(id, () -> processor.process(id, e)));
        }

        Outcome status(String status, String reason) {
            return send("status", "status", status, "reason", reason);
        }

        Outcome step(String stepId, int position, String status, int attempt, String name) {
            return send("step", "step_id", stepId, "step_number", position, "status", status, "attempt", attempt,
                    "name", name, "total_steps", 3);
        }

        Outcome token(long used) {
            return send("token", "pct", 0.6, "tokens_used", used);
        }
    }

    private Run launched(String name, int level, Long budget) {
        Fixture f = prjA(name, level);
        List<Node> nodes = List.of(
                new Node(UUID.fromString(f.g1()), NodeKind.GOAL, "基礎", null, null, 1),
                new Node(UUID.fromString(f.g2()), NodeKind.GOAL, "核心", null, null, 2),
                new Node(UUID.fromString(f.t1()), NodeKind.TASK, "初始化", UUID.fromString(f.g1()), "G1-T1", 1),
                new Node(UUID.fromString(f.t2()), NodeKind.TASK, "設定", UUID.fromString(f.g1()), "G1-T2", 2),
                new Node(UUID.fromString(f.t3()), NodeKind.TASK, "實作", UUID.fromString(f.g2()), "G2-T1", 3));
        List<Edge> edges = List.of(new Edge(UUID.fromString(f.g1()), UUID.fromString(f.g2()), EdgeKind.DEPENDENCY));
        ExecutionRun run = runRepository.insert(new ExecutionRun(UUID.randomUUID(), UUID.fromString(f.projectId()), 1,
                RunStatus.INITIALIZING, level, RunScope.all(), 0L, budget, Instant.now(), null,
                new DagSnapshot(nodes, edges), 0, null));
        // 「execute 成功之後」的讀模型：專案 EXECUTING、範圍內任務 QUEUED
        jdbc.update("update console.projects set status = 'EXECUTING' where id = ?", UUID.fromString(f.projectId()));
        jdbc.update("update console.tasks set status = 'QUEUED' where goal_id in (?, ?)", UUID.fromString(f.g1()),
                UUID.fromString(f.g2()));
        return new Run(f, run.id());
    }

    private Run running(String name, int level) {
        Run run = launched(name, level, null);
        run.status("INITIALIZING", "run 已建立");
        run.status("RUNNING", "引擎已啟動");
        return run;
    }

    private Map<String, Object> task(String taskId) {
        return jdbc.queryForMap("select status, started_at, completed_at, assigned_agent, retry_count, actual_tokens, "
                + "execution_log from console.tasks where id = ?", UUID.fromString(taskId));
    }

    private static Frame frame(Outcome out, Kind kind, String event) {
        return out.frames().stream().filter(f -> f.kind() == kind && event.equals(f.event())).findFirst()
                .orElseThrow(() -> new AssertionError("沒有 " + kind + "／" + event + " 框架：" + out.frames()));
    }

    private static List<String> ids(Outcome out, Kind kind) {
        return out.frames().stream().filter(f -> f.kind() == kind).map(f -> f.id() + ":" + f.event()).toList();
    }

    // ── status ──────────────────────────────────────────────────────────────────

    @Test
    void everyEventAdvancesTheStoredOffsetInTheSameTransactionAndStatusEventsProduceBothStreamsFrames() {
        Run run = launched("offset", 4, null);
        Outcome initializing = run.status("INITIALIZING", "run 已建立，準備啟動引擎");
        assertThat(consoleLastSeq(run.id.toString())).isEqualTo(1);
        assertThat(ids(initializing, Kind.LOGS)).containsExactly("1:status-change");
        assertThat(ids(initializing, Kind.METRICS)).containsExactly("1:progress-update");
        Outcome running = run.status("RUNNING", "引擎已啟動");
        assertThat(consoleLastSeq(run.id.toString())).isEqualTo(2);
        assertThat(projectStatus(run.f.projectId())).isEqualTo("EXECUTING");
        assertThat(running.terminal()).isFalse();
        StatusChangeEventData data = (StatusChangeEventData) frame(running, Kind.LOGS, "status-change").data();
        assertThat(data.runStatus()).isEqualTo(RunStatus.RUNNING);
        assertThat(data.bridgeStatus().name()).isEqualTo("RUNNING");
        assertThat(data.reason()).isEqualTo("引擎已啟動");
    }

    @Test
    void anUnrecognisedStatusOrEventIsIgnoredButTheOffsetStillMoves() {
        Run run = running("unknown", 4);
        Outcome weird = run.status("WEIRD", "x");
        assertThat(weird.frames()).isEmpty();
        Outcome mystery = run.send("mystery", "a", 1);
        assertThat(mystery.frames()).isEmpty();
        assertThat(consoleLastSeq(run.id.toString())).isEqualTo(4);
    }

    // ── step ────────────────────────────────────────────────────────────────────

    @Test
    void theFirstStartedMarksTheTaskRunningStampsItAndMovesTheGoalToInProgress() {
        Run run = running("started", 4);
        Outcome out = run.step("G1-T1", 1, "STARTED", 1, "初始化");
        Map<String, Object> t1 = task(run.f.t1());
        assertThat(t1.get("status")).isEqualTo("RUNNING");
        assertThat(t1.get("started_at")).isNotNull();
        assertThat(t1.get("assigned_agent")).isEqualTo("AutoClaude");
        assertThat((String) t1.get("execution_log")).contains("開始：初始化（G1-T1，第 1 次）");
        assertThat(taskStatus(run.f.t2())).isEqualTo("QUEUED");
        assertThat(goalStatus(run.f.g1())).isEqualTo("IN_PROGRESS");
        assertThat(goalStatus(run.f.g2())).isEqualTo("PENDING");
        assertThat(ids(out, Kind.LOGS)).containsExactly("3:log");
        assertThat(ids(out, Kind.METRICS)).containsExactly("3:progress-update");
        LogEventData log =
                (LogEventData) frame(out, Kind.LOGS, "log")
                        .data();
        assertThat(log.source()).isEqualTo("STEP");
        assertThat(log.level()).isEqualTo("INFO");
        assertThat(log.message()).isEqualTo("開始：初始化（G1-T1，第 1 次）");
        assertThat(log.stepNumber()).isEqualTo(1);
        assertThat(log.stepStatus()).isEqualTo("STARTED");
        assertThat(log.taskName()).isEqualTo("初始化");
        assertThat(log.tokensUsed()).isNull();
    }

    @Test
    void aDuplicateStartedForARunningTaskChangesNothingAndNeverRestartsTheLog() {
        Run run = running("duplicate-started", 4);
        run.step("G1-T1", 1, "STARTED", 1, "初始化");
        Map<String, Object> before = task(run.f.t1());
        run.send("log", "level", "WARNING", "line", "警告行");
        Map<String, Object> withWarning = task(run.f.t1());
        assertThat((String) withWarning.get("execution_log")).contains("[WARNING] 警告行");

        Outcome duplicate = run.step("G1-T1", 1, "STARTED", 1, "初始化");
        Map<String, Object> after = task(run.f.t1());
        assertThat(after.get("started_at")).as("started_at 只在第一次寫").isEqualTo(before.get("started_at"));
        assertThat(after.get("execution_log")).as("重複的 STARTED 不清空日誌").isEqualTo(withWarning.get("execution_log"));
        assertThat(after.get("status")).isEqualTo("RUNNING");
        assertThat(duplicate.actions()).isEmpty();
        assertThat(duplicate.frames()).as("框架照送（客戶端以 id 去重），但讀模型不變").isNotEmpty();
    }

    @Test
    void theGatePauseIsRequestedOncePerStepPositionEvenWhenTheStartedIsRepeated() {
        Run run = running("gate-once", 1);
        Outcome first = run.step("G1-T1", 1, "STARTED", 1, "初始化");
        assertThat(first.actions()).containsExactly(new PauseAction("gate"));
        Outcome repeat = run.step("G1-T1", 1, "STARTED", 1, "初始化");
        assertThat(repeat.actions()).isEmpty();
        Outcome second = run.step("G1-T1", 1, "COMPLETED", 1, "初始化");
        assertThat(second.actions()).isEmpty();
    }

    @Test
    void theLastStepAndLevelFourNeverAskForAGatePause() {
        Run levelOne = running("gate-last", 1);
        levelOne.step("G1-T1", 1, "STARTED", 1, "初始化");
        levelOne.step("G1-T1", 1, "COMPLETED", 1, "初始化");
        levelOne.step("G1-T2", 2, "STARTED", 1, "設定");
        levelOne.step("G1-T2", 2, "COMPLETED", 1, "設定");
        Outcome last = levelOne.step("G2-T1", 3, "STARTED", 1, "實作");
        assertThat(last.actions()).as("最後一步（i＝N）不暫停").isEmpty();

        Run levelFour = running("gate-l4", 4);
        assertThat(levelFour.step("G1-T1", 1, "STARTED", 1, "初始化").actions()).isEmpty();
    }

    @Test
    void retryingCountsTheRetryKeepsTheTaskRunningAndRecordsTheAttempt() {
        Run run = running("retrying", 4);
        run.step("G1-T1", 1, "STARTED", 1, "初始化");
        Outcome retry = run.step("G1-T1", 1, "RETRYING", 2, "初始化");
        Map<String, Object> t1 = task(run.f.t1());
        assertThat(t1.get("status")).isEqualTo("RUNNING");
        assertThat(t1.get("retry_count")).isEqualTo(1);
        assertThat((String) t1.get("execution_log")).contains("重試：初始化（G1-T1，第 2 次）");
        LogEventData log =
                (LogEventData) frame(retry, Kind.LOGS, "log")
                        .data();
        assertThat(log.level()).isEqualTo("WARN");
        assertThat(log.attempt()).isEqualTo(2);
        assertThat(ids(retry, Kind.METRICS)).as("RETRYING 只送 progress-update").containsExactly("4:progress-update");
    }

    @Test
    void completedMarksTheTaskCompletedStampsItAndRecomputesTheGoalWithAMetricFrame() {
        Run run = running("completed", 4);
        run.step("G1-T1", 1, "STARTED", 1, "初始化");
        run.token(1240);
        Outcome done = run.step("G1-T1", 1, "COMPLETED", 1, "初始化");
        Map<String, Object> t1 = task(run.f.t1());
        assertThat(t1.get("status")).isEqualTo("COMPLETED");
        assertThat(t1.get("completed_at")).isNotNull();
        assertThat(t1.get("actual_tokens")).isEqualTo(1240L);
        assertThat(goalStatus(run.f.g1())).as("還有 T2 沒完成").isEqualTo("IN_PROGRESS");
        assertThat(ids(done, Kind.METRICS)).containsExactly("5:progress-update", "5.1:metric-update");
        LogEventData log =
                (LogEventData) frame(done, Kind.LOGS, "log")
                        .data();
        assertThat(log.message()).isEqualTo("完成：初始化（G1-T1） Token: 1240");
        assertThat(log.tokensUsed()).isEqualTo(1240L);
        MetricUpdateEventData metric =
                (MetricUpdateEventData)
                        frame(done, Kind.METRICS, "metric-update").data();
        assertThat(metric.completedTasks()).isEqualTo(1);
        assertThat(metric.totalTasks()).isEqualTo(3);
        assertThat(metric.totalTokensUsed()).isEqualTo(1240L);
    }

    @Test
    void failedMarksTheTaskFailedAndKeepsTheErrorLineButCreatesNoReviewUntilTheRunFails() {
        Run run = running("failed-step", 4);
        run.step("G1-T2", 2, "STARTED", 1, "設定");
        run.step("G1-T2", 2, "RETRYING", 2, "設定");
        Outcome failed = run.step("G1-T2", 2, "FAILED", 2, "設定");
        Map<String, Object> t2 = task(run.f.t2());
        assertThat(t2.get("status")).isEqualTo("FAILED");
        assertThat((String) t2.get("execution_log")).contains("失敗：設定（G1-T2，第 2 次）");
        assertThat(goalStatus(run.f.g1())).isEqualTo("FAILED");
        assertThat(ids(failed, Kind.METRICS)).containsExactly("5:progress-update", "5.1:metric-update");
        assertThat(jdbc.queryForObject("select count(*) from console.review_requests", Long.class)).isZero();
    }

    // ── token ───────────────────────────────────────────────────────────────────

    @Test
    void aTokenEventWritesAnIdempotentSampleAttributesTheDeltaToTheCurrentStepAndEmitsTwoFrames() {
        Run run = running("token", 4);
        run.step("G1-T1", 1, "STARTED", 1, "初始化");
        Outcome token = run.token(1240);
        assertThat(ids(token, Kind.METRICS)).containsExactly("4:token-update", "4.1:metric-update");
        TokenUpdateEventData data =
                (TokenUpdateEventData)
                        frame(token, Kind.METRICS, "token-update").data();
        assertThat(data.tokensUsed()).isEqualTo(1240L);
        assertThat(data.delta()).as("第一則的 delta＝tokensUsed").isEqualTo(1240L);
        assertThat(data.contextPct()).isEqualTo(0.6);
        assertThat(data.taskId()).isEqualTo(UUID.fromString(run.f.t1()));
        assertThat(task(run.f.t1()).get("actual_tokens")).isEqualTo(1240L);

        run.token(2480);
        assertThat(jdbc.queryForList("select delta from console.run_token_samples where run_id = ? order by seq",
                Long.class, run.id)).containsExactly(1240L, 1240L);
        assertThat(task(run.f.t1()).get("actual_tokens")).isEqualTo(2480L);

        Outcome replay = run.sendAt(4, "token", Map.of("pct", 0.6, "tokens_used", 1240));
        assertThat(replay.frames()).as("seq ≤ console_last_seq 一律略過").isEmpty();
        assertThat(jdbc.queryForObject("select count(*) from console.run_token_samples where run_id = ?", Long.class,
                run.id)).isEqualTo(2L);
    }

    @Test
    void aTokenEventWithoutACurrentStepIsStoredWithoutATaskAttribution() {
        Run run = running("token-no-step", 4);
        run.token(1240);
        assertThat(jdbc.queryForList("select task_id from console.run_token_samples where run_id = ?", Object.class,
                run.id)).containsExactly((Object) null);
        assertThat(jdbc.queryForObject("select coalesce(sum(actual_tokens), 0) from console.tasks", Long.class)).isZero();
    }

    // ── alert（Bridge 原生）──────────────────────────────────────────────────────

    @Test
    void anEscalationAlertIsPersistedOnceWhileUnacknowledgedAndAlwaysForwarded() {
        Run run = running("alert-esc", 4);
        Outcome first = run.send("alert", "level", "error", "code", "ESCALATION", "message", "任務「設定」重試 1 次仍失敗",
                "step_id", "G1-T2");
        AlertEventData data =
                (AlertEventData)
                        frame(first, Kind.LOGS, "alert").data();
        assertThat(data.origin()).isEqualTo("ENGINE");
        assertThat(data.code()).isEqualTo("ESCALATION");
        assertThat(data.severity()).as("error → CRITICAL").isEqualTo("CRITICAL");
        assertThat(data.rule()).isEqualTo("ENGINE_ESCALATION");
        assertThat(data.alertId()).as("新增了一列才帶 alertId").isNotNull();
        assertThat(data.subject()).as("C-7：去重對象帶 runId").isEqualTo("step:" + run.id + ":G1-T2");
        assertThat(ids(first, Kind.LOGS)).containsExactly("3:alert");
        assertThat(ids(first, Kind.METRICS)).as("alert 不進 /metrics").isEmpty();

        Outcome second = run.send("alert", "level", "error", "code", "ESCALATION", "message", "再一次", "step_id", "G1-T2");
        AlertEventData again =
                (AlertEventData)
                        frame(second, Kind.LOGS, "alert").data();
        assertThat(again.alertId()).as("被未確認的同一告警擋下者不帶 alertId，SSE 照常轉發").isNull();
        assertThat(jdbc.queryForObject("select count(*) from console.alerts where rule = 'ENGINE_ESCALATION'",
                Long.class)).isEqualTo(1L);
        assertThat(jdbc.queryForObject("select event_sub from console.alerts", Integer.class)).isZero();
    }

    @Test
    void onlyEscalationAndTokenHaltArePersistedTheOtherEngineAlertsAreForwardedOnly() {
        Run run = running("alert-other", 4);
        run.send("alert", "level", "warning", "code", "TOKEN_HALT", "message", "額度 96%");
        for (String code : List.of("LIMIT_RETRY", "RESTORE", "FORCE_KILL", "CONFIG_OVERRIDE_IGNORED", "STEP_TRACKING_GAP",
                "ENV_LOST", "BRIDGE_INTERNAL")) {
            Outcome out = run.send("alert", "level", "info", "code", code, "message", code);
            assertThat(frame(out, Kind.LOGS, "alert")).isNotNull();
        }
        assertThat(jdbc.queryForList("select rule from console.alerts", String.class)).containsExactly("ENGINE_TOKEN_HALT");
        assertThat(jdbc.queryForObject("select subject from console.alerts", String.class))
                .as("沒有 step_id 時以 run 為對象").isEqualTo("run:" + run.id);
    }

    // ── 暫停、終態 ───────────────────────────────────────────────────────────────

    @Test
    void aPausedStatusWithoutAGateRequestMovesTheProjectToReadyAndCreatesNoReview() {
        Run run = running("paused-manual", 4);
        run.step("G1-T1", 1, "STARTED", 1, "初始化");
        run.step("G1-T1", 1, "COMPLETED", 1, "初始化");
        Outcome paused = run.status("PAUSED", "在步驟邊界暫停（已完成 1 步）");
        assertThat(projectStatus(run.f.projectId())).isEqualTo("READY");
        assertThat(jdbc.queryForObject("select count(*) from console.review_requests", Long.class)).isZero();
        assertThat(paused.terminal()).isFalse();
        run.status("RUNNING", "引擎已啟動（第 2 次 spawn）");
        assertThat(projectStatus(run.f.projectId())).as("resume 之後專案回 EXECUTING").isEqualTo("EXECUTING");
    }

    @Test
    void aPausedStatusAfterAGatePauseRequestCreatesTheReviewItemWithTheNextTaskAndAnAnchoredSubSeq() {
        Run run = running("paused-gate", 1);
        Outcome started = run.step("G1-T1", 1, "STARTED", 1, "初始化");
        assertThat(started.actions()).containsExactly(new PauseAction("gate"));
        run.step("G1-T1", 1, "COMPLETED", 1, "初始化");
        Outcome paused = run.status("PAUSED", "在步驟邊界暫停（已完成 1 步，續跑點：G1-T2）");
        assertThat(ids(paused, Kind.LOGS)).as("先 status-change，再它衍生的 review-request").containsExactly(
                "5:status-change", "5.1:review-request");
        Map<String, Object> review = jdbc.queryForMap("select kind, status, task_id, goal_id, reason, event_seq, "
                + "event_sub from console.review_requests");
        assertThat(review.get("kind")).isEqualTo("TASK_CONFIRM");
        assertThat(review.get("status")).isEqualTo("PENDING");
        assertThat(review.get("task_id")).isEqualTo(UUID.fromString(run.f.t2()));
        assertThat(review.get("goal_id")).isEqualTo(UUID.fromString(run.f.g1()));
        assertThat(review.get("reason")).isEqualTo("Level 1：請確認是否繼續執行任務「設定」");
        assertThat(review.get("event_seq")).isEqualTo(5);
        assertThat(review.get("event_sub")).isEqualTo(1);
    }

    @Test
    void completedStatusCompletesResidualTasksTheGoalsAndTheProjectAndClosesOpenGateItems() {
        Run run = running("status-completed", 4);
        for (int i = 1; i <= 3; i++) {
            String stepId = i == 3 ? "G2-T1" : "G1-T" + i;
            run.step(stepId, i, "STARTED", 1, "任務" + i);
            if (i < 3) {
                run.step(stepId, i, "COMPLETED", 1, "任務" + i);
            }
        }
        Outcome done = run.status("COMPLETED", "引擎正常結束");
        assertThat(done.terminal()).isTrue();
        assertThat(taskStatus(run.f.t3())).as("最後一步的 COMPLETED 與 status COMPLETED 同時抵達：殘留的 RUNNING 補正").isEqualTo("COMPLETED");
        assertThat(goalStatus(run.f.g1())).isEqualTo("COMPLETED");
        assertThat(goalStatus(run.f.g2())).isEqualTo("COMPLETED");
        assertThat(projectStatus(run.f.projectId())).isEqualTo("COMPLETED");
        assertThat(ids(done, Kind.METRICS)).as("終態另送最終 metric-update").endsWith("8.1:metric-update");
    }

    @Test
    void completedStatusOfAPartialScopeLeavesTheProjectReadyNotCompleted() {
        Run run = running("status-partial", 4);
        jdbc.update("update console.tasks set status = 'PENDING' where id = ?", UUID.fromString(run.f.t3()));
        run.step("G1-T1", 1, "STARTED", 1, "初始化");
        run.step("G1-T1", 1, "COMPLETED", 1, "初始化");
        run.step("G1-T2", 2, "STARTED", 1, "設定");
        run.status("COMPLETED", "引擎正常結束");
        assertThat(taskStatus(run.f.t3())).isEqualTo("PENDING");
        assertThat(projectStatus(run.f.projectId())).isEqualTo("READY");
    }

    @Test
    void anEscalationFailureEscalatesTheLastFailedTaskResetsQueuedOnesFailsTheProjectAndOpensTheReviewAfterTheStatusFrame() {
        Run run = running("status-failed-esc", 4);
        run.step("G1-T1", 1, "STARTED", 1, "初始化");
        run.step("G1-T1", 1, "COMPLETED", 1, "初始化");
        run.step("G1-T2", 2, "STARTED", 1, "設定");
        run.step("G1-T2", 2, "RETRYING", 2, "設定");
        run.step("G1-T2", 2, "FAILED", 2, "設定");
        run.send("alert", "level", "error", "code", "ESCALATION", "message", "任務「設定」重試 1 次仍失敗", "step_id", "G1-T2");
        Outcome failed = run.status("FAILED", "引擎升級（ESCALATION）：任務「設定」重試 1 次仍失敗");

        assertThat(failed.terminal()).isTrue();
        assertThat(taskStatus(run.f.t1())).isEqualTo("COMPLETED");
        assertThat(taskStatus(run.f.t2())).isEqualTo("ESCALATED");
        assertThat(taskStatus(run.f.t3())).as("範圍內仍 QUEUED 者系統重設為 PENDING").isEqualTo("PENDING");
        assertThat(goalStatus(run.f.g1())).isEqualTo("FAILED");
        assertThat(projectStatus(run.f.projectId())).isEqualTo("FAILED");
        assertThat(ids(failed, Kind.LOGS)).as("終態 status-change 之後才是它衍生的審核項，且 id 嚴格遞增")
                .containsExactly("9:status-change", "9.1:review-request");
        Map<String, Object> review = jdbc.queryForMap("select kind, task_id, goal_id, reason from console.review_requests");
        assertThat(review.get("kind")).isEqualTo("ESCALATED");
        assertThat(review.get("task_id")).isEqualTo(UUID.fromString(run.f.t2()));
        assertThat((String) review.get("reason")).isEqualTo("任務「設定」重試 1 次仍失敗，需要人類介入：引擎升級（ESCALATION）：任務「設定」重試 1 次仍失敗");
    }

    @Test
    void aNonEscalationFailureOnlyCreatesAReviewFromLevelFiveAndLeavesTheTaskFailed() {
        String halt = "引擎因 token／額度門檻停機（halted），未自動續跑";
        Run levelFour = running("status-failed-halt-4", 4);
        levelFour.step("G1-T1", 1, "STARTED", 1, "初始化");
        levelFour.step("G1-T1", 1, "FAILED", 1, "初始化");
        levelFour.status("FAILED", halt);
        assertThat(taskStatus(levelFour.f.t1())).as("非升級的失敗維持 FAILED").isEqualTo("FAILED");
        assertThat(jdbc.queryForObject("select count(*) from console.review_requests", Long.class))
                .as("等級 1～4 遇到非升級的失敗不建審核項").isZero();
        assertThat(projectStatus(levelFour.f.projectId())).isEqualTo("FAILED");

        Run levelFive = running("status-failed-halt-5", 5);
        levelFive.step("G1-T1", 1, "STARTED", 1, "初始化");
        levelFive.step("G1-T1", 1, "FAILED", 1, "初始化");
        levelFive.status("FAILED", halt);
        Map<String, Object> review = jdbc.queryForMap("select kind, reason, task_id from console.review_requests where "
                + "run_id = ?", levelFive.id);
        assertThat(review.get("kind")).isEqualTo("ESCALATED");
        assertThat((String) review.get("reason")).isEqualTo("執行失敗：" + halt);
        assertThat(review.get("task_id")).isEqualTo(UUID.fromString(levelFive.f.t1()));
    }

    @Test
    void cancelledResetsRunningAndQueuedTasksToCancelledMovesTheProjectToReadyAndClosesGateItems() {
        Run run = running("status-cancelled", 1);
        run.step("G1-T1", 1, "STARTED", 1, "初始化");
        run.step("G1-T1", 1, "COMPLETED", 1, "初始化");
        run.status("PAUSED", "在步驟邊界暫停");
        assertThat(jdbc.queryForObject("select count(*) from console.review_requests where status = 'PENDING'",
                Long.class)).isEqualTo(1L);

        Outcome cancelled = run.status("CANCELLED", "使用者取消");
        assertThat(cancelled.terminal()).isTrue();
        assertThat(taskStatus(run.f.t1())).isEqualTo("COMPLETED");
        assertThat(taskStatus(run.f.t2())).isEqualTo("CANCELLED");
        assertThat(taskStatus(run.f.t3())).isEqualTo("CANCELLED");
        assertThat(projectStatus(run.f.projectId())).isEqualTo("READY");
        Map<String, Object> review = jdbc.queryForMap("select status, decided_by, comment from console.review_requests");
        assertThat(review.get("status")).isEqualTo("REJECTED");
        assertThat(review.get("decided_by")).isEqualTo("system");
        assertThat(review.get("comment")).isEqualTo("執行已取消");
    }

    @Test
    void aTerminalEventOfASupersededRunDoesNotTouchTheReadModelOfTheNewerRun() {
        Run old = running("superseded", 4);
        old.step("G1-T1", 1, "STARTED", 1, "初始化");
        // 後續批次已接手：任務重新 QUEUED、專案 EXECUTING；舊批次遲到的 CANCELLED 不得動它們
        runRepository.insert(new ExecutionRun(UUID.randomUUID(), UUID.fromString(old.f.projectId()), 2,
                RunStatus.INITIALIZING, 4, RunScope.all(), 0L, null, Instant.now(), null, DagSnapshot.EMPTY, 0, null));
        jdbc.update("update console.tasks set status = 'QUEUED' where id = ?", UUID.fromString(old.f.t1()));
        Outcome late = old.status("CANCELLED", "使用者取消");
        assertThat(late.terminal()).as("舊批次的消費者照常結束").isTrue();
        assertThat(taskStatus(old.f.t1())).isEqualTo("QUEUED");
        assertThat(projectStatus(old.f.projectId())).isEqualTo("EXECUTING");
    }

    // ── 冪等：整段事件序列重放 ───────────────────────────────────────────────────────

    @Test
    void replayingTheWholeEventSequenceProducesNothingAndChangesNothing() {
        Run run = running("replay", 1);
        List<Outcome> firstPass = new java.util.ArrayList<>();
        firstPass.add(run.step("G1-T1", 1, "STARTED", 1, "初始化"));
        firstPass.add(run.token(1240));
        firstPass.add(run.step("G1-T1", 1, "COMPLETED", 1, "初始化"));
        firstPass.add(run.status("PAUSED", "在步驟邊界暫停"));
        long reviews = jdbc.queryForObject("select count(*) from console.review_requests", Long.class);
        long samples = jdbc.queryForObject("select count(*) from console.run_token_samples", Long.class);
        String t1 = task(run.f.t1()).toString();

        for (int seq = 1; seq <= run.seq; seq++) {
            Outcome replay = run.sendAt(seq, "step", Map.of("step_id", "G1-T1", "status", "STARTED"));
            assertThat(replay.frames()).as("seq " + seq).isEmpty();
            assertThat(replay.actions()).isEmpty();
            assertThat(replay.terminal()).isFalse();
        }
        assertThat(jdbc.queryForObject("select count(*) from console.review_requests", Long.class)).isEqualTo(reviews);
        assertThat(jdbc.queryForObject("select count(*) from console.run_token_samples", Long.class)).isEqualTo(samples);
        assertThat(task(run.f.t1()).toString()).isEqualTo(t1);
        assertThat(consoleLastSeq(run.id.toString())).isEqualTo(run.seq);
    }

    @Test
    void aBatchDeletedByCompensationMakesLateEventsHarmless() {
        Run run = running("deleted", 4);
        jdbc.update("delete from console.execution_runs where id = ?", run.id);
        Outcome late = run.step("G1-T1", 1, "STARTED", 1, "初始化");
        assertThat(late.frames()).isEmpty();
        assertThat(taskStatus(run.f.t1())).isEqualTo("QUEUED");
    }
}
