package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.CurrentStepView;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeEvent;
import com.aisdlc.console.application.port.out.AlertRepository;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.ExecutionStepRepository;
import com.aisdlc.console.application.port.out.ExecutionStepRepository.StepRow;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ReviewRequestRepository;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.application.port.out.TokenSampleRepository;
import com.aisdlc.console.application.port.out.TokenSampleRepository.Sample;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.ReviewKind;
import com.aisdlc.console.domain.model.execution.ReviewRequest;
import com.aisdlc.console.domain.model.execution.ReviewStatus;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.monitor.Alert;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.domain.service.AlertRules;
import com.aisdlc.console.domain.service.AlertRules.Candidate;
import com.aisdlc.console.domain.service.GoalDerivation;
import com.aisdlc.console.domain.service.ReviewGatePolicy;
import com.aisdlc.console.domain.service.ReviewGatePolicy.GateReview;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/**
 * 一則 Bridge 事件 → Console 讀模型與前端框架（契約 §3.5.2、§3.6、§3.7；Architecture §7.3）。
 *
 * <p><b>呼叫端的責任</b>：持有該 run 的互斥鎖、並在一個交易內呼叫 {@link #process}——讀模型更新、審核項與告警的寫入、
 * {@code console_last_seq} 的推進必須同一交易（冪等：{@code seq ≤ console_last_seq} 一律略過，重複處理同一 seq
 * 不會產生第二筆審核項／告警／Token 樣本）。交易提交後呼叫端才把 {@link Outcome#frames()} 發給前端、執行
 * {@link Outcome#actions()}（{@code :pause} 這類會呼叫 Bridge 的動作不放在資料庫交易內）。
 *
 * <p>為什麼「step STARTED」才決定閘點：{@code :pause} 在呼叫之後的下一個步驟邊界才生效，所以要在步驟 i 之後停，
 * 就得在步驟 i 剛開始時呼叫（{@link ReviewGatePolicy}）。
 */
@Component
public class RunEventProcessor {

    private static final Logger LOG = LoggerFactory.getLogger(RunEventProcessor.class);
    private static final String ESCALATION_PREFIX = "引擎升級（ESCALATION）";
    private static final String AGENT = "AutoClaude";
    private static final int TASK_LOG_LIMIT = 20_000;

    /** 交易提交後要執行的動作（會呼叫 Bridge）。 */
    public sealed interface Action permits PauseAction {
    }

    /** 要求 Bridge 暫停（{@code why}：{@code gate}／{@code budget}／{@code consecutiveFailures}）。 */
    public record PauseAction(String why) implements Action {
    }

    /**
     * @param frames   要發給前端的框架（依發生順序）
     * @param actions  交易提交後要執行的動作
     * @param terminal 這則事件讓 run 進入終態：消費者處理完就結束
     */
    public record Outcome(List<Frame> frames, List<Action> actions, boolean terminal) {

        static final Outcome NOTHING = new Outcome(List.of(), List.of(), false);
    }

    private final ExecutionRunRepository runs;
    private final ProjectRepository projects;
    private final GoalRepository goals;
    private final TaskRepository tasks;
    private final ExecutionStepRepository steps;
    private final TokenSampleRepository samples;
    private final ReviewRequestRepository reviews;
    private final AlertRepository alerts;
    private final AlertThresholds thresholds;
    private final RunRegistry registry;
    private final Clock clock;

    @SuppressWarnings("java:S107")
    public RunEventProcessor(ExecutionRunRepository runs, ProjectRepository projects, GoalRepository goals,
                             TaskRepository tasks, ExecutionStepRepository steps, TokenSampleRepository samples,
                             ReviewRequestRepository reviews, AlertRepository alerts, AlertThresholds thresholds,
                             RunRegistry registry, Clock clock) {
        this.runs = runs;
        this.projects = projects;
        this.goals = goals;
        this.tasks = tasks;
        this.steps = steps;
        this.samples = samples;
        this.reviews = reviews;
        this.alerts = alerts;
        this.thresholds = thresholds;
        this.registry = registry;
        this.clock = clock;
    }

    /** 處理一則事件（見類別說明的呼叫約定）。run 已不存在（被補償刪除）時回 {@link Outcome#NOTHING}。 */
    public Outcome process(UUID runId, BridgeEvent event) {
        Optional<ExecutionRun> found = runs.findById(runId);
        if (found.isEmpty()) {
            return Outcome.NOTHING;
        }
        ExecutionRun run = found.get();
        if (event.seq() <= run.consoleLastSeq()) {
            return Outcome.NOTHING;
        }
        Ctx c = new Ctx(run, event);
        if (c.rt.bridgeStatus == null) {
            c.rt.bridgeStatus = bridgeStatusOf(run.status());
        }
        loadCounters(c);
        switch (event.event()) {
            case "status" -> onStatus(c);
            case "step" -> onStep(c);
            case "token" -> onToken(c);
            case "alert" -> onAlert(c);
            case "log" -> onLog(c);
            default -> LOG.debug("略過 Console 不處理的 Bridge 事件：{}", event.event());
        }
        c.rt.lastEventAt = c.now;
        runs.updateConsoleLastSeq(runId, event.seq());
        return new Outcome(c.frames, c.actions, c.terminal);
    }

    // ── 單一事件的處理脈絡 ──────────────────────────────────────────────────────

    private final class Ctx {

        final ExecutionRun run;
        final BridgeEvent event;
        final RunRegistry.Runtime rt;
        final Instant now = clock.instant();
        final DagSnapshot dag;
        final Project project;
        /**
         * 這個批次是否為專案最新的批次。審核 {@code SKIP}／{@code RETRY} 另開後續批次時，原批次可能還有一則「被我們 stop 出來」的終態
         * 事件在途（例：{@code GOAL_COMPLETED} 的 RETRY 先 {@code :stop} 暫停中的 run、再開後續批次）；那則遲到的 {@code CANCELLED}
         * 不能把已交給新批次（QUEUED／RUNNING）的任務、目標與專案重設回去——讀模型只反映最新批次。
         */
        final boolean latest;
        final Map<UUID, Task> taskMap = new LinkedHashMap<>();
        final Map<UUID, Goal> goalMap = new HashMap<>();
        final List<Frame> frames = new ArrayList<>();
        final List<Action> actions = new ArrayList<>();
        boolean terminal;

        Ctx(ExecutionRun run, BridgeEvent event) {
            this.run = run;
            this.event = event;
            this.rt = registry.runtime(run.id());
            this.dag = run.dag();
            this.project = projects.findById(run.projectId()).orElseThrow();
            this.latest = runs.findLatestByProject(run.projectId()).map(r -> r.id().equals(run.id())).orElse(true);
            tasks.findByIds(dag.taskNodes().stream().map(Node::id).toList()).forEach(t -> taskMap.put(t.id(), t));
            goals.findByProjectId(run.projectId()).forEach(g -> goalMap.put(g.id(), g));
        }

        int seq() {
            return event.seq();
        }

        String ts() {
            return event.ts() == null ? now.toString() : event.ts();
        }

        Task task(UUID id) {
            return taskMap.get(id);
        }

        void save(Task task) {
            tasks.save(task);
        }

        long completedCount() {
            return dag.taskNodes().stream().map(n -> taskMap.get(n.id()))
                    .filter(t -> t != null && t.status() == TaskStatus.COMPLETED).count();
        }

        long failedCount() {
            return dag.taskNodes().stream().map(n -> taskMap.get(n.id()))
                    .filter(t -> t != null && (t.status() == TaskStatus.FAILED || t.status() == TaskStatus.ESCALATED))
                    .count();
        }

        CurrentStepView currentStep() {
            if (rt.currentStepId == null) {
                return null;
            }
            Node node = dag.taskByStepId(rt.currentStepId).orElse(null);
            return node == null ? null : new CurrentStepView(node.stepId(), node.sequence(), node.id(), node.label(),
                    node.goalId(), rt.currentAttempt);
        }
    }

    // ── 重試統計（HIGH_RETRY_RATE、metric-update）──────────────────────────────

    /** 第一次處理這個 run 的事件（含 console-api 重啟後）時，從步驟列重建「開始過／重試過」的統計。 */
    private void loadCounters(Ctx c) {
        if (c.rt.countersLoaded) {
            return;
        }
        c.rt.countersLoaded = true;
        for (StepRow row : steps.findAllByRun(c.run.id())) {
            if ("STARTED".equals(row.status())) {
                c.rt.startedTasks.add(row.taskId());
            } else if ("RETRYING".equals(row.status())) {
                c.rt.retriedTasks.add(row.taskId());
                c.rt.retryEvents++;
            }
        }
    }

    // ── status ──────────────────────────────────────────────────────────────────

    private void onStatus(Ctx c) {
        BridgeStatus status = BridgeStatus.parse(c.event.text("status")).orElse(null);
        String reason = c.event.text("reason") == null ? "" : c.event.text("reason");
        if (status == null) {
            LOG.warn("Bridge 回了無法辨識的狀態事件（seq={}）：{}", c.seq(), c.event.text("status"));
            return;
        }
        c.rt.bridgeStatus = status;
        c.frames.add(StreamFrames.statusChange(c.event, status, reason));
        switch (status) {
            case PAUSED -> onPaused(c);
            case RUNNING -> onRunning(c);
            case COMPLETED -> onCompleted(c);
            case FAILED -> onFailed(c, reason);
            case CANCELLED -> onCancelled(c);
            default -> { }
        }
        c.frames.add(progressFrame(c, c.seq(), 0));
        if (c.terminal) {
            c.frames.add(metricFrame(c, c.seq(), 1));
        }
    }

    private void onRunning(Ctx c) {
        if (c.project.status() == ProjectStatus.READY) {
            c.project.systemSetStatus(ProjectStatus.EXECUTING, c.now);
            projects.save(c.project);
        }
        c.rt.gatePauseRequested = false;
        c.rt.gatePausedPositions.clear();
    }

    private void onPaused(Ctx c) {
        if (c.project.status() == ProjectStatus.EXECUTING) {
            c.project.systemSetStatus(ProjectStatus.READY, c.now);
            projects.save(c.project);
        }
        recomputeGoals(c);
        boolean gate = c.rt.gatePauseRequested;
        c.rt.gatePauseRequested = false;
        c.rt.gatePausedPositions.clear();
        c.rt.currentStepId = null;
        if (gate) {
            createGateReview(c);
        }
    }

    private void onCompleted(Ctx c) {
        if (c.latest) {
            for (Node node : c.dag.taskNodes()) {
                Task task = c.task(node.id());
                if (task != null && (task.status() == TaskStatus.RUNNING || task.status() == TaskStatus.VALIDATING)) {
                    task.markCompleted(c.now);
                    c.save(task);
                }
            }
            recomputeGoals(c);
            List<Task> all = tasks.findByProjectId(c.run.projectId());
            boolean everythingDone = !all.isEmpty() && all.stream()
                    .allMatch(t -> t.status() == TaskStatus.COMPLETED || t.status() == TaskStatus.SKIPPED);
            c.project.systemSetStatus(everythingDone ? ProjectStatus.COMPLETED : ProjectStatus.READY, c.now);
            projects.save(c.project);
        }
        closeGateReviews(c, "執行已結束");
        c.rt.currentStepId = null;
        c.terminal = true;
    }

    private void onFailed(Ctx c, String reason) {
        if (!c.latest) {
            c.rt.currentStepId = null;
            c.terminal = true;
            return;
        }
        boolean escalation = reason.startsWith(ESCALATION_PREFIX);
        Node failed = failedNode(c);
        if (escalation && failed != null) {
            Task task = c.task(failed.id());
            if (task != null) {
                task.markEscalated(c.now);
                c.save(task);
            }
        }
        for (Node node : c.dag.taskNodes()) {
            Task task = c.task(node.id());
            if (task != null && task.status() == TaskStatus.QUEUED) {
                task.systemReset(TaskStatus.PENDING, c.now);
                c.save(task);
            }
        }
        recomputeGoals(c);
        c.project.systemSetStatus(ProjectStatus.FAILED, c.now);
        projects.save(c.project);
        boolean consecutive = failed != null && evaluateConsecutiveFailures(c, failed);
        if (ReviewGatePolicy.createsReviewOnFailure(c.run.autonomyLevel(), escalation)) {
            createFailureReview(c, failed, escalation, reason, consecutive);
        }
        c.rt.currentStepId = null;
        c.terminal = true;
    }

    private void onCancelled(Ctx c) {
        if (c.latest) {
            for (Node node : c.dag.taskNodes()) {
                Task task = c.task(node.id());
                if (task != null && (task.status() == TaskStatus.RUNNING || task.status() == TaskStatus.VALIDATING
                        || task.status() == TaskStatus.QUEUED)) {
                    task.systemReset(TaskStatus.CANCELLED, c.now);
                    c.save(task);
                }
            }
            recomputeGoals(c);
            c.project.systemSetStatus(ProjectStatus.READY, c.now);
            projects.save(c.project);
        }
        closeGateReviews(c, "執行已取消");
        c.rt.currentStepId = null;
        c.terminal = true;
    }

    /** run FAILED 時「失敗的那個任務」：優先用事件追蹤到的步驟，其次找 dag 內最後一個 FAILED／ESCALATED 的任務。 */
    private Node failedNode(Ctx c) {
        if (c.rt.lastFailedStepId != null) {
            Optional<Node> node = c.dag.taskByStepId(c.rt.lastFailedStepId);
            if (node.isPresent()) {
                return node.get();
            }
        }
        Node last = null;
        for (Node node : c.dag.taskNodes()) {
            Task task = c.task(node.id());
            if (task != null && (task.status() == TaskStatus.FAILED || task.status() == TaskStatus.ESCALATED)) {
                last = node;
            }
        }
        return last;
    }

    // ── R-goal（先重算、再套人工判定）────────────────────────────────────────────

    /**
     * 目標狀態：先對 dag 涉及的目標套 R-goal，再套人工判定——本批次被人工 {@code REJECT} 的 {@code GOAL_COMPLETED} 審核項所指的
     * 目標一律 {@code FAILED}（人類的否決是最終判定，不能被後續事件的機械推導蓋掉，AR-11）。
     */
    private void recomputeGoals(Ctx c) {
        Set<UUID> goalIds = new LinkedHashSet<>();
        c.dag.goalNodes().forEach(n -> goalIds.add(n.id()));
        for (UUID goalId : goalIds) {
            Goal goal = c.goalMap.get(goalId);
            if (goal == null) {
                continue;
            }
            List<Task> goalTasks = tasks.findByGoalId(goalId);
            goal.systemSetStatus(GoalDerivation.derive(goalTasks.stream().map(Task::status).toList()), c.now);
            goals.save(goal);
        }
        for (ReviewRequest review : reviews.findByRun(c.run.id())) {
            if (review.kind() == ReviewKind.GOAL_COMPLETED && review.status() == ReviewStatus.REJECTED
                    && review.goalId() != null && !ReviewRequest.SYSTEM.equals(review.decidedBy())) {
                Goal goal = c.goalMap.get(review.goalId());
                if (goal != null) {
                    goal.systemSetStatus(com.aisdlc.console.domain.model.goal.GoalStatus.FAILED, c.now);
                    goals.save(goal);
                }
            }
        }
    }

    // ── step ────────────────────────────────────────────────────────────────────

    private void onStep(Ctx c) {
        BridgeEvent e = c.event;
        String stepId = e.text("step_id");
        String status = e.text("status") == null ? "" : e.text("status");
        int position = e.integer("step_number") == null ? 0 : e.integer("step_number");
        int attempt = e.integer("attempt") == null ? 1 : e.integer("attempt");
        Node node = c.dag.taskByStepId(stepId).orElse(null);
        Task task = node == null ? null : c.task(node.id());
        if (node == null || task == null) {
            LOG.warn("step 事件的 step_id 不在批次 {} 的 DAG 內：{}", c.run.id(), stepId);
        }
        Long tokens = null;
        String error = null;
        if (node != null && "COMPLETED".equals(status)) {
            tokens = samples.sumDeltaForTask(c.run.id(), node.id());
        }
        if (node != null && "FAILED".equals(status)) {
            error = steps.findLatest(c.run.id(), stepId, "FAILED").map(StepRow::errorMessage).orElse(null);
        }
        String message = StreamFrames.stepMessage(status, node == null ? stepId : node.label(), stepId, attempt,
                tokens, error);
        c.frames.add(StreamFrames.stepLog(e, node, stepId, status, position, attempt, tokens, error));
        if (task != null) {
            applyStep(c, node, task, stepId, status, attempt, message);
        }
        c.frames.add(progressFrame(c, c.seq(), 0));
        if ("COMPLETED".equals(status) || "FAILED".equals(status)) {
            c.frames.add(metricFrame(c, c.seq(), 1));
        }
    }

    private void applyStep(Ctx c, Node node, Task task, String stepId, String status, int attempt, String message) {
        switch (status) {
            case "STARTED" -> {
                if (task.status() == TaskStatus.RUNNING) {
                    c.rt.currentStepId = stepId;
                    c.rt.currentAttempt = attempt;
                    return;
                }
                task.markRunning(AGENT, c.now);
                task.resetExecutionLog(c.now);
                task.appendExecutionLog(message, TASK_LOG_LIMIT, c.now);
                c.save(task);
                c.rt.currentStepId = stepId;
                c.rt.currentAttempt = attempt;
                c.rt.startedTasks.add(task.id());
                recomputeGoals(c);
                decideGatePause(c, node);
            }
            case "RETRYING" -> {
                task.countRetry(c.now);
                task.appendExecutionLog(message, TASK_LOG_LIMIT, c.now);
                c.save(task);
                c.rt.currentAttempt = attempt;
                c.rt.retriedTasks.add(task.id());
                c.rt.retryEvents++;
                evaluateHighRetryRate(c, node);
            }
            case "COMPLETED" -> {
                task.markCompleted(c.now);
                task.appendExecutionLog(message, TASK_LOG_LIMIT, c.now);
                c.save(task);
                c.rt.currentStepId = null;
                recomputeGoals(c);
                evaluateTaskDuration(c, task);
            }
            case "FAILED" -> {
                task.markFailed(c.now);
                task.appendExecutionLog(message, TASK_LOG_LIMIT, c.now);
                c.save(task);
                c.rt.lastFailedStepId = stepId;
                c.rt.lastFailedAttempt = attempt;
                c.rt.currentStepId = null;
                recomputeGoals(c);
                evaluateConsecutiveFailures(c, node);
            }
            default -> LOG.debug("略過未知的步驟狀態：{}", status);
        }
    }

    /** 閘點（§3.6.1）：步驟第一次開始時依自治等級決定要不要呼叫 {@code :pause}；每個 (run, 步驟) 只呼叫一次，Bridge 不是 RUNNING 時不呼叫。 */
    private void decideGatePause(Ctx c, Node node) {
        boolean running = c.rt.bridgeStatus == BridgeStatus.RUNNING;
        if (running && ReviewGatePolicy.shouldPauseAtStart(c.run.autonomyLevel(), node.sequence(),
                c.dag.totalSteps(), c.dag) && c.rt.gatePausedPositions.add(node.sequence())) {
            c.rt.gatePauseRequested = true;
            c.actions.add(new PauseAction("gate"));
        }
    }

    // ── token ───────────────────────────────────────────────────────────────────

    private void onToken(Ctx c) {
        BridgeEvent e = c.event;
        long used = e.longValue("tokens_used") == null ? 0L : e.longValue("tokens_used");
        double pct = e.decimal("pct") == null ? 0.0 : e.decimal("pct");
        long previous = samples.latest(c.run.id()).map(Sample::tokensUsed).orElse(0L);
        long delta = Math.max(0L, used - previous);
        Node current = c.rt.currentStepId == null ? null : c.dag.taskByStepId(c.rt.currentStepId).orElse(null);
        UUID taskId = current == null ? null : current.id();
        samples.insert(new Sample(c.run.id(), c.seq(), parseTs(e.ts(), c.now), used, delta, pct, taskId));
        if (taskId != null && c.task(taskId) != null && delta > 0) {
            Task task = c.task(taskId);
            task.addActualTokens(delta, c.now);
            c.save(task);
        }
        c.frames.add(StreamFrames.token(c.seq(), 0, c.ts(), used, delta, pct, c.run.tokenBudget(), taskId));
        c.frames.add(metricFrame(c, c.seq(), 1));
        evaluateTokenRules(c, used, current);
    }

    private void evaluateTokenRules(Ctx c, long used, Node current) {
        AlertThresholds.Values th = thresholds.current();
        UUID runId = c.run.id();
        AlertRules.tokenBudgetWarning(runId, used, c.run.tokenBudget(), th.tokenWarning())
                .ifPresent(candidate -> emitAlert(c, candidate));
        boolean pause = AlertRules.tokenBudgetExceeded(runId, used, c.run.tokenBudget())
                .map(candidate -> emitAlert(c, candidate)).orElse(false);
        if (current != null && c.run.scope().limits().taskTokens() != null) {
            long taskUsed = samples.sumDeltaForTask(runId, current.id());
            pause |= AlertRules.taskTokenLimitExceeded(current.id(), current.label(), taskUsed,
                    c.run.scope().limits().taskTokens()).map(candidate -> emitAlert(c, candidate)).orElse(false);
        }
        if (current != null && current.goalId() != null && c.run.scope().limits().goalTokens() != null) {
            long goalUsed = samples.sumDeltaForGoal(runId, current.goalId());
            String goalName = c.dag.goalById(current.goalId()).map(Node::label).orElse("");
            pause |= AlertRules.goalTokenLimitExceeded(current.goalId(), goalName, goalUsed,
                    c.run.scope().limits().goalTokens()).map(candidate -> emitAlert(c, candidate)).orElse(false);
        }
        if (pause && c.rt.bridgeStatus == BridgeStatus.RUNNING) {
            c.actions.add(new PauseAction("budget"));
        }
    }

    // ── alert（Bridge 原生告警）─────────────────────────────────────────────────

    private void onAlert(Ctx c) {
        BridgeEvent e = c.event;
        String code = e.text("code") == null ? "" : e.text("code");
        String stepId = e.text("step_id");
        String message = e.text("message") == null ? "" : e.text("message");
        Candidate candidate = switch (code) {
            case "ESCALATION" -> AlertRules.engineEscalation(c.run.id(), stepId, message);
            case "TOKEN_HALT" -> AlertRules.engineTokenHalt(c.run.id(), stepId, message);
            default -> null;
        };
        Alert persisted = null;
        String subject = null;
        if (candidate != null) {
            subject = candidate.subject();
            Alert alert = new Alert(UUID.randomUUID(), c.run.projectId(), c.run.id(), candidate.rule(),
                    candidate.severity(), candidate.subject(), candidate.message(), c.now, false, null, null, c.seq(),
                    0);
            persisted = alerts.insertIfAbsent(alert).orElse(null);
        }
        c.frames.add(StreamFrames.engineAlert(e, persisted, subject));
    }

    // ── log ─────────────────────────────────────────────────────────────────────

    private void onLog(Ctx c) {
        Node current = c.rt.currentStepId == null ? null : c.dag.taskByStepId(c.rt.currentStepId).orElse(null);
        c.frames.add(StreamFrames.engineLog(c.event, current, c.rt.currentStepId));
        String level = c.event.text("level") == null ? "" : c.event.text("level").toUpperCase(java.util.Locale.ROOT);
        if (current != null && ("WARNING".equals(level) || "ERROR".equals(level) || "CRITICAL".equals(level))) {
            Task task = c.task(current.id());
            if (task != null) {
                task.appendExecutionLog("[" + level + "] " + c.event.text("line"), TASK_LOG_LIMIT, c.now);
                c.save(task);
            }
        }
    }

    // ── 審核項 ──────────────────────────────────────────────────────────────────

    private void createGateReview(Ctx c) {
        int completed = (int) c.completedCount();
        Optional<GateReview> decision = ReviewGatePolicy.reviewOnPause(c.run.autonomyLevel(), completed,
                c.dag.totalSteps(), c.dag);
        if (decision.isEmpty()) {
            return;
        }
        GateReview gate = decision.get();
        Node subject = c.dag.taskAtPosition(gate.subjectPosition()).orElse(null);
        Node evidence = c.dag.taskAtPosition(gate.evidencePosition()).orElse(null);
        UUID evidenceRow = evidence == null ? null
                : steps.findLatest(c.run.id(), evidence.stepId(), "COMPLETED").map(StepRow::id).orElse(null);
        String goalName = subject == null || subject.goalId() == null ? ""
                : c.dag.goalById(subject.goalId()).map(Node::label).orElse("");
        String taskName = subject == null ? "" : subject.label();
        String reason = switch (gate.kind()) {
            case GOAL_CONFIRM -> "Level 2：請確認是否開始目標「" + goalName + "」";
            case GOAL_COMPLETED -> "目標「" + goalName + "」已完成，等待人類審核";
            default -> "Level " + c.run.autonomyLevel() + "：請確認是否繼續執行任務「" + taskName + "」"
                    + (gate.degraded() ? "（暫停點比預期晚一步）" : "");
        };
        insertReview(c, gate.kind(), evidenceRow, subject == null ? null : subject.id(),
                subject == null ? null : subject.goalId(), reason);
    }

    private void createFailureReview(Ctx c, Node failed, boolean escalation, String engineReason, boolean consecutive) {
        UUID taskId = failed == null ? null : failed.id();
        UUID goalId = failed == null ? null : failed.goalId();
        UUID evidence = failed == null ? null : steps.findLatest(c.run.id(), failed.stepId(), "FAILED")
                .map(StepRow::id).orElse(null);
        String reason;
        if (escalation && failed != null) {
            int retries = Math.max(c.rt.lastFailedAttempt - 1, 0);
            reason = "任務「" + failed.label() + "」重試 " + retries + " 次仍失敗，需要人類介入：" + engineReason;
            if (consecutive) {
                reason += "（連續 " + thresholds.current().consecutiveFailures()
                        + " 個任務失敗，已觸發 CONSECUTIVE_FAILURES 告警）";
            }
        } else {
            reason = escalation ? engineReason : "執行失敗：" + engineReason;
        }
        insertReview(c, ReviewKind.ESCALATED, evidence, taskId, goalId, reason);
    }

    private void insertReview(Ctx c, ReviewKind kind, UUID evidenceStepRow, UUID taskId, UUID goalId, String reason) {
        int sub = reviews.nextEventSub(c.run.id(), c.seq());
        ReviewRequest review = new ReviewRequest(UUID.randomUUID(), c.run.id(), evidenceStepRow, taskId, goalId, kind,
                ReviewStatus.PENDING, reason, c.now, null, null, null, c.seq(), sub);
        reviews.insert(review);
        c.frames.add(StreamFrames.review(review, StreamFrames.reviewView(review, c.dag)));
    }

    /** run 進入 COMPLETED／CANCELLED 時，該批次仍 PENDING 的 gate 類審核項自動 REJECTED（ESCALATED 類不在此列）。 */
    private void closeGateReviews(Ctx c, String comment) {
        for (ReviewRequest pending : reviews.findByRunAndStatus(c.run.id(), ReviewStatus.PENDING)) {
            if (pending.kind().gate()) {
                reviews.update(pending.decided(ReviewStatus.REJECTED, ReviewRequest.SYSTEM, c.now, comment));
            }
        }
    }

    // ── 告警（六規則）──────────────────────────────────────────────────────────

    /** 持久化一則 Console 規則告警；真的新增了才發 SSE。回傳是否新增（呼叫端據此決定要不要 {@code :pause}）。 */
    private boolean emitAlert(Ctx c, Candidate candidate) {
        int sub = reviews.nextEventSub(c.run.id(), c.seq());
        Alert alert = new Alert(UUID.randomUUID(), c.run.projectId(), c.run.id(), candidate.rule(),
                candidate.severity(), candidate.subject(), candidate.message(), c.now, false, null, null, c.seq(), sub);
        Optional<Alert> inserted = alerts.insertIfAbsent(alert);
        inserted.ifPresent(a -> c.frames.add(StreamFrames.consoleAlert(a, c.now)));
        return inserted.isPresent();
    }

    private void evaluateHighRetryRate(Ctx c, Node node) {
        if (node.goalId() == null) {
            return;
        }
        List<Node> siblings = c.dag.tasksOfGoal(node.goalId());
        int started = (int) siblings.stream().filter(n -> c.rt.startedTasks.contains(n.id())).count();
        int retried = (int) siblings.stream().filter(n -> c.rt.retriedTasks.contains(n.id())).count();
        String goalName = c.dag.goalById(node.goalId()).map(Node::label).orElse("");
        AlertRules.highRetryRate(node.goalId(), goalName, started, retried)
                .ifPresent(candidate -> emitAlert(c, candidate));
    }

    private void evaluateTaskDuration(Ctx c, Task task) {
        if (task.startedAt() == null) {
            return;
        }
        AlertThresholds.Values th = thresholds.current();
        long elapsed = Duration.between(task.startedAt(), c.now).getSeconds();
        AlertRules.taskDurationExceeded(task.id(), task.name(), elapsed, th.taskTimeoutSec(), th.durationMultiplier())
                .ifPresent(candidate -> emitAlert(c, candidate));
    }

    /** 同一目標連續失敗：依「終局」時間排序該目標下任務的結果（COMPLETED 成功、FAILED／ESCALATED 失敗，SKIPPED 略過）。 */
    private boolean evaluateConsecutiveFailures(Ctx c, Node node) {
        if (node.goalId() == null) {
            return false;
        }
        record TaskResult(Instant at, boolean success) {
        }
        List<TaskResult> outcomes = new ArrayList<>();
        for (Task task : tasks.findByGoalId(node.goalId())) {
            if (task.status() == TaskStatus.COMPLETED && task.completedAt() != null) {
                outcomes.add(new TaskResult(task.completedAt(), true));
            } else if (task.status() == TaskStatus.FAILED || task.status() == TaskStatus.ESCALATED) {
                outcomes.add(new TaskResult(task.updatedAt(), false));
            }
        }
        outcomes.sort(Comparator.comparing(TaskResult::at));
        String goalName = c.dag.goalById(node.goalId()).map(Node::label).orElse("");
        AlertThresholds.Values th = thresholds.current();
        Optional<Candidate> candidate = AlertRules.consecutiveFailures(node.goalId(), goalName,
                outcomes.stream().map(TaskResult::success).toList(), th.consecutiveFailures());
        if (candidate.isEmpty()) {
            return false;
        }
        boolean inserted = emitAlert(c, candidate.get());
        if (inserted && c.rt.bridgeStatus == BridgeStatus.RUNNING) {
            c.actions.add(new PauseAction("consecutiveFailures"));
        }
        return true;
    }

    // ── 指標框架 ────────────────────────────────────────────────────────────────

    private Frame progressFrame(Ctx c, int seq, int sub) {
        BridgeStatus status = c.rt.bridgeStatus == null ? BridgeStatus.RUNNING : c.rt.bridgeStatus;
        return StreamFrames.progress(seq, sub, c.ts(), status, (int) c.completedCount(), c.dag.totalSteps(),
                c.currentStep());
    }

    private Frame metricFrame(Ctx c, int seq, int sub) {
        long total = samples.latest(c.run.id()).map(Sample::tokensUsed).orElse(c.run.totalTokensUsed());
        int started = c.rt.startedTasks.size();
        double average = started == 0 ? 0.0 : StreamFrames.round2((double) c.rt.retryEvents / started);
        long elapsed = Math.max(0L, Duration.between(c.run.startedAt() == null ? c.now : c.run.startedAt(), c.now)
                .getSeconds());
        return StreamFrames.metric(seq, sub, c.ts(), (int) c.completedCount(), (int) c.failedCount(),
                c.dag.totalSteps(), c.rt.retriedTasks.size(), average, total, c.run.tokenBudget(), elapsed);
    }

    // ── 小工具 ──────────────────────────────────────────────────────────────────

    private static BridgeStatus bridgeStatusOf(RunStatus status) {
        return switch (status) {
            case INITIALIZING -> BridgeStatus.INITIALIZING;
            case RUNNING -> BridgeStatus.RUNNING;
            case PAUSED -> BridgeStatus.PAUSED;
            case COMPLETED -> BridgeStatus.COMPLETED;
            case FAILED -> BridgeStatus.FAILED;
            case CANCELLED -> BridgeStatus.CANCELLED;
        };
    }

    private static Instant parseTs(String ts, Instant fallback) {
        if (ts == null) {
            return fallback;
        }
        try {
            return OffsetDateTime.parse(ts).toInstant();
        } catch (DateTimeParseException e) {
            return fallback;
        }
    }
}
