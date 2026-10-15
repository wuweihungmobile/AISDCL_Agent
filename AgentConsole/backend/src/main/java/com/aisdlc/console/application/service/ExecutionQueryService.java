package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase;
import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.RunSnapshot;
import com.aisdlc.console.application.port.out.CheckpointRepository;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.ExecutionStepRepository;
import com.aisdlc.console.application.port.out.ExecutionStepRepository.StepRow;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ReviewRequestRepository;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.application.port.out.TokenSampleRepository;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.DagSnapshot.NodeKind;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.ReviewStatus;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * 執行批次的讀取（契約 §1.2.2、§1.2.3、§1.2.7～§1.2.9）。資料庫段落各自在唯讀交易內完成，呼叫 Bridge 時不持有交易。
 *
 * <p>{@code GET /executions/{runId}} 合併 DB 列與 Bridge {@code GET run}；<b>Bridge 不可達（連線失敗或逾時）時仍回 200</b>，
 * {@code bridge.connected=false}、進度退回 DB 衍生值（不回 5xx，主控裁決）；Bridge 可達但回 404 {@code run_not_found}
 * （工作區被清）→ {@code connected=true}、{@code runKnown=false}。回應不外露 pid 與 lock key。
 */
@Service
public class ExecutionQueryService implements ExecutionQueryUseCase {

    private static final Logger LOG = LoggerFactory.getLogger(ExecutionQueryService.class);
    private static final int MAX_LIST_SIZE = 100;
    private static final int MAX_STEPS_SIZE = 200;

    private final ExecutionRunRepository runs;
    private final ProjectRepository projects;
    private final GoalRepository goals;
    private final TaskRepository tasks;
    private final ExecutionStepRepository steps;
    private final TokenSampleRepository samples;
    private final ReviewRequestRepository reviews;
    private final CheckpointRepository checkpoints;
    private final AgentBridge bridge;
    private final TransactionTemplate readTx;
    private final Clock clock;

    @SuppressWarnings("java:S107")
    public ExecutionQueryService(ExecutionRunRepository runs, ProjectRepository projects, GoalRepository goals,
                                 TaskRepository tasks, ExecutionStepRepository steps, TokenSampleRepository samples,
                                 ReviewRequestRepository reviews, CheckpointRepository checkpoints, AgentBridge bridge,
                                 PlatformTransactionManager transactions, Clock clock) {
        this.runs = runs;
        this.projects = projects;
        this.goals = goals;
        this.tasks = tasks;
        this.steps = steps;
        this.samples = samples;
        this.reviews = reviews;
        this.checkpoints = checkpoints;
        this.bridge = bridge;
        this.readTx = new TransactionTemplate(transactions);
        this.readTx.setReadOnly(true);
        this.clock = clock;
    }

    private ExecutionRun require(UUID runId) {
        return runs.findById(runId).orElseThrow(() -> NotFoundException.of("執行批次", runId));
    }

    // ── GET /executions/{runId} ────────────────────────────────────────────────

    @Override
    public RunDetailView get(UUID runId) {
        ExecutionRun run = readTx.execute(status -> require(runId));
        RunSnapshot snapshot = null;
        boolean connected = true;
        Boolean runKnown = true;
        try {
            snapshot = bridge.getRun(runId);
        } catch (BridgeRejectedException e) {
            if (e.status() == 404) {
                runKnown = false;
            } else {
                LOG.warn("讀取批次 {} 的 Bridge 快照被拒：{} {}", runId, e.status(), e.reason());
                connected = false;
                runKnown = null;
            }
        } catch (UpstreamException e) {
            LOG.debug("Bridge 不可達（批次 {}）：{}", runId, e.getMessage());
            connected = false;
            runKnown = null;
        }
        RunSnapshot snap = snapshot;
        boolean isConnected = connected;
        Boolean known = runKnown;
        return readTx.execute(status -> detail(run, snap, isConnected, known));
    }

    private RunDetailView detail(ExecutionRun dbRun, RunSnapshot snap, boolean connected, Boolean runKnown) {
        ExecutionRun run = require(dbRun.id());
        Instant now = clock.instant();
        BridgeStatus bridgeStatus = snap == null ? null : snap.status();
        RunView view = new RunView(run.id(), run.projectId(), run.runNumber(),
                bridgeStatus == null ? run.status() : bridgeStatus.fold(), bridgeStatus, run.autonomyLevel(),
                run.scope(), snap == null ? run.totalTokensUsed() : snap.tokensUsed(), run.tokenBudget(),
                run.startedAt(), snap == null ? run.completedAt() : parse(snap.completedAt(), run.completedAt()));
        List<StepRow> rows = snap == null ? steps.findAllByRun(run.id()) : List.of();
        int total = run.dag().totalSteps();
        int completed = snap != null ? snap.completedSteps() : distinctTasks(rows, "COMPLETED");
        Integer lastSeq = snap != null ? Integer.valueOf(snap.lastEventSeq())
                : rows.stream().map(StepRow::stepNumber).max(Integer::compare).orElse(null);
        CurrentStepView current = snap == null ? null : currentStep(run.dag(), snap);
        Instant end = run.completedAt() != null && run.status().terminal() ? run.completedAt() : now;
        long elapsed = run.startedAt() == null ? 0 : Math.max(0, Duration.between(run.startedAt(), end).getSeconds());
        List<ReviewView> pending = reviews.findByRunAndStatus(run.id(), ReviewStatus.PENDING).stream()
                .map(r -> StreamFrames.reviewView(r, run.dag())).toList();
        BridgeInfoView info = new BridgeInfoView(connected,
                snap != null && snap.bridgeInstance() != null ? snap.bridgeInstance() : run.bridgeInstance(),
                bridgeStatus, runKnown, now);
        return new RunDetailView(view, current, completed, total, lastSeq, snap == null ? null : snap.reason(),
                elapsed, pending, info);
    }

    private static CurrentStepView currentStep(DagSnapshot dag, RunSnapshot snap) {
        if (snap.currentStep() == null) {
            return null;
        }
        Node node = dag.taskByStepId(snap.currentStep()).orElse(null);
        int position = snap.currentStepNumber() != null ? snap.currentStepNumber()
                : node == null ? 0 : node.sequence();
        return new CurrentStepView(snap.currentStep(), position, node == null ? null : node.id(),
                node == null ? null : node.label(), node == null ? null : node.goalId(), Math.max(snap.attempt(), 1));
    }

    private static int distinctTasks(List<StepRow> rows, String status) {
        Set<UUID> ids = new HashSet<>();
        rows.stream().filter(r -> status.equals(r.status())).forEach(r -> ids.add(r.taskId()));
        return ids.size();
    }

    private static Instant parse(String iso, Instant fallback) {
        if (iso == null) {
            return fallback;
        }
        try {
            return OffsetDateTime.parse(iso).toInstant();
        } catch (DateTimeParseException e) {
            return fallback;
        }
    }

    // ── GET /projects/{projectId}/executions ───────────────────────────────────

    @Override
    public PageResult<RunSummaryView> list(UUID projectId, RunListQuery query) {
        Violations v = new Violations();
        if (query.page() < 0) {
            v.add("page", "page 不可為負數");
        }
        if (query.size() < 1 || query.size() > MAX_LIST_SIZE) {
            v.add("size", "size 必須介於 1 到 " + MAX_LIST_SIZE);
        }
        return readTx.execute(status -> {
            v.throwIfAny();
            projects.findById(projectId).orElseThrow(() -> NotFoundException.of("專案", projectId));
            PageResult<ExecutionRun> page = runs.findPageByProject(projectId, query.status(), query.byRunNumber(),
                    query.ascending(), query.page(), query.size());
            Instant now = clock.instant();
            return page.map(run -> summary(run, now));
        });
    }

    private RunSummaryView summary(ExecutionRun run, Instant now) {
        List<StepRow> rows = steps.findAllByRun(run.id());
        int completed = distinctTasks(rows, "COMPLETED");
        int failed = distinctTasks(rows, "FAILED");
        Double rate = completed + failed == 0 ? null
                : StreamFrames.round1(completed * 100.0 / (completed + failed));
        Instant end = run.completedAt() != null ? run.completedAt() : now;
        long duration = run.startedAt() == null ? 0 : Math.max(0, Duration.between(run.startedAt(), end).getSeconds());
        return new RunSummaryView(run.id(), run.projectId(), run.runNumber(), run.status(), run.autonomyLevel(),
                run.scope().mode().name(), run.totalTokensUsed(), run.tokenBudget(), run.startedAt(),
                run.completedAt(), duration, run.dag().totalSteps(), completed, failed, rate);
    }

    // ── GET /executions/{runId}/steps ──────────────────────────────────────────

    @Override
    public PageResult<StepView> steps(UUID runId, int afterSeq, int page, int size) {
        Violations v = new Violations();
        if (afterSeq < 0) {
            v.add("afterSeq", "afterSeq 不可為負數");
        }
        if (page < 0) {
            v.add("page", "page 不可為負數");
        }
        if (size < 1 || size > MAX_STEPS_SIZE) {
            v.add("size", "size 必須介於 1 到 " + MAX_STEPS_SIZE);
        }
        return readTx.execute(status -> {
            ExecutionRun run = require(runId);
            v.throwIfAny();
            Map<UUID, Node> byTask = new HashMap<>();
            run.dag().taskNodes().forEach(n -> byTask.put(n.id(), n));
            PageResult<StepRow> rows = steps.findPage(runId, afterSeq, page, size);
            return rows.map(row -> {
                Node node = byTask.get(row.taskId());
                boolean terminal = "COMPLETED".equals(row.status()) || "FAILED".equals(row.status());
                Long tokens = terminal ? samples.sumDeltaForTask(runId, row.taskId()) : null;
                return new StepView(row.id(), row.runId(), row.taskId(), node == null ? null : node.label(),
                        node == null ? null : node.goalId(), row.stepNumber(), row.stepId(), row.attempt(),
                        row.action(), row.status(), tokens, row.errorMessage(), row.output(), row.timestamp());
            });
        });
    }

    // ── GET /tasks/{id} 的 executionHistory ────────────────────────────────────

    @Override
    public List<TaskStepView> taskHistory(UUID taskId) {
        return readTx.execute(status -> {
            Map<UUID, Long> tokensByRun = new HashMap<>();
            return steps.findRecentByTask(taskId, TASK_HISTORY_LIMIT).stream().map(row -> {
                boolean terminal = "COMPLETED".equals(row.status()) || "FAILED".equals(row.status());
                Long tokens = terminal
                        ? tokensByRun.computeIfAbsent(row.runId(), id -> samples.sumDeltaForTask(id, taskId)) : null;
                return new TaskStepView(row.id(), row.stepNumber(), row.action(), row.status(), tokens,
                        row.errorMessage(), row.timestamp());
            }).toList();
        });
    }

    // ── GET /executions/{runId}/dag ────────────────────────────────────────────

    @Override
    public DagView dag(UUID runId) {
        return readTx.execute(status -> {
            ExecutionRun run = require(runId);
            Map<UUID, Task> taskById = new HashMap<>();
            tasks.findByIds(run.dag().taskNodes().stream().map(Node::id).toList())
                    .forEach(t -> taskById.put(t.id(), t));
            Map<UUID, Goal> goalById = new HashMap<>();
            goals.findByProjectId(run.projectId()).forEach(g -> goalById.put(g.id(), g));
            List<DagNodeView> nodes = run.dag().nodes().stream().map(n -> {
                String nodeStatus;
                if (n.kind() == NodeKind.GOAL) {
                    Goal goal = goalById.get(n.id());
                    nodeStatus = goal == null ? "PENDING" : goal.status().name();
                } else {
                    Task task = taskById.get(n.id());
                    nodeStatus = task == null ? TaskStatus.PENDING.name() : task.status().name();
                }
                return new DagNodeView(n.id(), n.kind(), n.label(), nodeStatus, n.goalId(), n.stepId(), n.sequence());
            }).toList();
            return new DagView(runId, nodes, run.dag().edges(), clock.instant());
        });
    }

    // ── GET /executions/{runId}/checkpoints ────────────────────────────────────

    @Override
    public List<CheckpointView> checkpoints(UUID runId) {
        return readTx.execute(status -> {
            require(runId);
            return checkpoints.findByRun(runId).stream().map(c -> new CheckpointView(c.id(), c.runId(), c.name(),
                    c.createdAt(), c.automatic(), c.stepIdx(), c.stepId(), c.completedSteps())).toList();
        });
    }
}
