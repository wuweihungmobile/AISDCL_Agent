package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunView;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.RunSnapshot;
import com.aisdlc.console.application.port.out.CheckpointRepository;
import com.aisdlc.console.application.port.out.CheckpointRepository.CheckpointRow;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ReviewRequestRepository;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.ReviewRequest;
import com.aisdlc.console.domain.model.execution.ReviewStatus;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.domain.service.GoalDerivation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/**
 * 執行控制（契約 §1.2.4～§1.2.6、§1.2.10）：pause／resume／cancel／restore 直通 Bridge。
 *
 * <p>每個操作都在該 run 的互斥鎖內（與事件消費序列化）；DB 預檢失敗不呼叫 Bridge；Bridge 的 409 {@code invalid_state} 原樣轉成
 * 409 附 reason；回應是 {@code ExecutionRunResponse} <b>快照</b>——呼叫 Bridge 成功後立刻再讀一次 {@code GET run}
 * （例：pause 後為 {@code RUNNING}＋{@code PAUSING}）。
 *
 * <p>resume／restore 前再做一次 signoff 校驗（範圍＝該批次 DAG 內的任務與目標、以及專案）：暫停期間使用者可能改過內容，
 * 「未經人工審批的草案不可執行」對每條通往引擎的路都成立。
 */
@Component
public class ExecutionControlService {

    private static final Logger LOG = LoggerFactory.getLogger(ExecutionControlService.class);

    private final ExecutionRunRepository runs;
    private final ProjectRepository projects;
    private final GoalRepository goals;
    private final TaskRepository tasks;
    private final ReviewRequestRepository reviews;
    private final CheckpointRepository checkpoints;
    private final AgentBridge bridge;
    private final ConfigMaterializer config;
    private final RunConsumers consumers;
    private final RunRegistry registry;
    private final TransactionTemplate tx;
    private final Clock clock;

    @SuppressWarnings("java:S107")
    public ExecutionControlService(ExecutionRunRepository runs, ProjectRepository projects, GoalRepository goals,
                                   TaskRepository tasks, ReviewRequestRepository reviews,
                                   CheckpointRepository checkpoints, AgentBridge bridge, ConfigMaterializer config,
                                   RunConsumers consumers, RunRegistry registry,
                                   PlatformTransactionManager transactions, Clock clock) {
        this.runs = runs;
        this.projects = projects;
        this.goals = goals;
        this.tasks = tasks;
        this.reviews = reviews;
        this.checkpoints = checkpoints;
        this.bridge = bridge;
        this.config = config;
        this.consumers = consumers;
        this.registry = registry;
        this.tx = new TransactionTemplate(transactions);
        this.clock = clock;
    }

    // ── pause／resume／cancel ───────────────────────────────────────────────────

    public RunView pause(UUID runId) {
        return registry.locked(runId, () -> {
            ExecutionRun run = require(runId);
            requireStatus(run, "pause", RunStatus.RUNNING);
            call(run, "pause", () -> bridge.pauseRun(runId));
            return snapshot(runId);
        });
    }

    public RunView resume(UUID runId, String actor) {
        return registry.locked(runId, () -> {
            ExecutionRun run = require(runId);
            requireStatus(run, "resume", RunStatus.PAUSED);
            requireSignedOff(run);
            call(run, "resume", () -> bridge.resumeRun(runId, config.materialize(run.autonomyLevel()).env()));
            tx.executeWithoutResult(status -> afterResume(run, actor, "以手動恢復處理"));
            return snapshot(runId);
        });
    }

    public RunView cancel(UUID runId) {
        return registry.locked(runId, () -> {
            ExecutionRun run = require(runId);
            requireStatus(run, "cancel", RunStatus.RUNNING, RunStatus.PAUSED);
            call(run, "cancel", () -> bridge.stopRun(runId));
            return snapshot(runId);
        });
    }

    // ── restore ─────────────────────────────────────────────────────────────────

    public RunView restore(UUID runId, UUID checkpointId, String actor) {
        return registry.locked(runId, () -> {
            ExecutionRun run = require(runId);
            CheckpointRow checkpoint = checkpoints.findById(checkpointId).filter(c -> c.runId().equals(runId))
                    .orElseThrow(() -> new NotFoundException("checkpoint 不存在或不屬於此執行：" + checkpointId));
            Optional<ExecutionRun> latest = runs.findLatestByProject(run.projectId());
            if (latest.isPresent() && !latest.get().id().equals(runId)) {
                throw new ConflictException("只能還原專案最新的執行批次", ErrorReasons.RESTORE_ONLY_LATEST,
                        Map.of("latestRunId", latest.get().id().toString(), "latestRunNumber",
                                latest.get().runNumber()));
            }
            requireStatus(run, "restore", RunStatus.PAUSED, RunStatus.COMPLETED, RunStatus.FAILED,
                    RunStatus.CANCELLED);
            requireSignedOff(run);
            callRestore(run, checkpoint);
            tx.executeWithoutResult(status -> afterRestore(run, checkpoint, actor));
            return snapshot(runId);
        });
    }

    /**
     * 呼叫 Bridge restore（帶重新物化的 env）。審核 RETRY 也走這裡；呼叫端須持有該 run 的鎖。只取 {@code .env()}：
     * 引擎設定檔在 spawn 時就凍結，{@code engineCapabilities} 不重算（契約 §3.4.2 一致性規則③）。
     */
    void callRestore(ExecutionRun run, CheckpointRow checkpoint) {
        call(run, "restore", () -> {
            bridge.restoreRun(run.id(), checkpoint.id(), config.materialize(run.autonomyLevel()).env());
            return BridgeStatus.RUNNING;
        });
    }

    // ── 交易內的讀模型副作用（Bridge 接受之後；契約 §3.5.3）────────────────────────

    /** resume 之後：專案回 EXECUTING；該批次仍待決的 gate 審核項自動關閉（APPROVED、決定人＝呼叫者）。 */
    void afterResume(ExecutionRun run, String actor, String comment) {
        Instant now = clock.instant();
        Project project = projects.findByIdForUpdate(run.projectId()).orElseThrow();
        if (project.status() == ProjectStatus.READY) {
            project.systemSetStatus(ProjectStatus.EXECUTING, now);
            projects.save(project);
        }
        for (ReviewRequest pending : reviews.findByRunAndStatus(run.id(), ReviewStatus.PENDING)) {
            if (pending.kind().gate()) {
                reviews.update(pending.decided(ReviewStatus.APPROVED, actor, now, comment));
            }
        }
        resetRuntimeAfterContinue(run.id());
    }

    /**
     * restore 被 Bridge 接受之後：不在快照 {@code completed_step_ids} 內的範圍任務重設為 QUEUED（SKIPPED 不重設；已花的 Token 保留）、
     * 目標依 R-goal 重算、專案回 EXECUTING、待決的 gate 審核項自動 REJECTED（decided_by＝system）；終態 run 的消費者已結束，重新啟動。
     */
    List<UUID> afterRestore(ExecutionRun run, CheckpointRow checkpoint, String actor) {
        Instant now = clock.instant();
        List<UUID> reset = resetTasksAfterCheckpoint(run, checkpoint, now);
        Project project = projects.findByIdForUpdate(run.projectId()).orElseThrow();
        project.systemSetStatus(ProjectStatus.EXECUTING, now);
        projects.save(project);
        for (ReviewRequest pending : reviews.findByRunAndStatus(run.id(), ReviewStatus.PENDING)) {
            if (pending.kind().gate()) {
                reviews.update(pending.decided(ReviewStatus.REJECTED, ReviewRequest.SYSTEM, now, "執行已還原"));
            }
        }
        resetRuntimeAfterContinue(run.id());
        if (run.status().terminal()) {
            consumers.start(run.id(), run.consoleLastSeq());
        }
        LOG.info("批次 {} 由 {} 從 checkpoint {} 還原", run.id(), actor, checkpoint.name());
        return reset;
    }

    /** 範圍任務依快照重設；回傳被重設的任務 id。 */
    List<UUID> resetTasksAfterCheckpoint(ExecutionRun run, CheckpointRow checkpoint, Instant now) {
        Set<String> keep = new HashSet<>(checkpoint.completedStepIds());
        List<UUID> reset = new ArrayList<>();
        Map<UUID, Task> byId = new LinkedHashMap<>();
        tasks.findByIds(run.dag().taskNodes().stream().map(Node::id).toList()).forEach(t -> byId.put(t.id(), t));
        for (Node node : run.dag().taskNodes()) {
            Task task = byId.get(node.id());
            if (task == null || keep.contains(node.stepId()) || task.status() == TaskStatus.SKIPPED) {
                continue;
            }
            task.queueForRun(now);
            tasks.save(task);
            reset.add(task.id());
        }
        recomputeGoals(run.dag(), run.projectId(), now);
        return reset;
    }

    /** 對 dag 涉及的目標套 R-goal（單純重算；人工判定由事件消費者在每個重算點補上）。 */
    void recomputeGoals(DagSnapshot dag, UUID projectId, Instant now) {
        Map<UUID, Goal> byId = new LinkedHashMap<>();
        goals.findByProjectId(projectId).forEach(g -> byId.put(g.id(), g));
        for (Node goalNode : dag.goalNodes()) {
            Goal goal = byId.get(goalNode.id());
            if (goal == null) {
                continue;
            }
            goal.systemSetStatus(GoalDerivation.derive(tasks.findByGoalId(goal.id()).stream().map(Task::status)
                    .toList()), now);
            goals.save(goal);
        }
    }

    private void resetRuntimeAfterContinue(UUID runId) {
        RunRegistry.Runtime rt = registry.runtime(runId);
        rt.gatePausedPositions.clear();
        rt.gatePauseRequested = false;
        rt.currentStepId = null;
        rt.bridgeStatus = BridgeStatus.RUNNING;
    }

    // ── 驗證與快照 ──────────────────────────────────────────────────────────────

    ExecutionRun require(UUID runId) {
        return runs.findById(runId).orElseThrow(() -> NotFoundException.of("執行批次", runId));
    }

    private void requireStatus(ExecutionRun run, String action, RunStatus... allowed) {
        for (RunStatus status : allowed) {
            if (run.status() == status) {
                return;
            }
        }
        throw stateNotAllowed(run, action);
    }

    ConflictException stateNotAllowed(ExecutionRun run, String action) {
        BridgeStatus known = registry.runtime(run.id()).bridgeStatus;
        return new ConflictException("目前執行狀態（" + run.status() + "）不允許 " + action,
                ErrorReasons.RUN_STATE_NOT_ALLOWED, Map.of("action", action, "runStatus", run.status().name(),
                        "bridgeStatus", (known == null ? run.status().name() : known.name())));
    }

    /** resume／restore 前重驗 signoff：專案與該批次 DAG 內的全部目標、任務（details 形狀同 execute 第 5 項）。 */
    void requireSignedOff(ExecutionRun run) {
        Project project = projects.findById(run.projectId()).orElseThrow(() -> NotFoundException.of("專案",
                run.projectId()));
        Set<UUID> goalIds = new HashSet<>();
        run.dag().goalNodes().forEach(n -> goalIds.add(n.id()));
        List<String> unsignedGoals = goals.findByProjectId(run.projectId()).stream()
                .filter(g -> goalIds.contains(g.id()) && !g.signedOff()).map(g -> g.id().toString()).toList();
        List<String> unsignedTasks = tasks.findByIds(run.dag().taskNodes().stream().map(Node::id).toList()).stream()
                .filter(t -> !t.signedOff()).map(t -> t.id().toString()).toList();
        if (!project.signedOff() || !unsignedGoals.isEmpty() || !unsignedTasks.isEmpty()) {
            throw ExecuteProjectService.unsignedDraft(project, unsignedGoals, unsignedTasks);
        }
    }

    /** 呼叫 Bridge 並把 4xx 轉成契約的 409／404／422；5xx、連線失敗與逾時維持 502／504（DB 不動）。 */
    <T> T call(ExecutionRun run, String action, java.util.function.Supplier<T> bridgeCall) {
        try {
            return bridgeCall.get();
        } catch (BridgeRejectedException e) {
            throw BridgeErrors.forControl(e, action, run.id(), run.status().name());
        }
    }

    /**
     * 回應快照：再讀一次 Bridge；Bridge 暫時讀不到就退回 DB 欄位。{@code engineCapabilities} 讀自 DB（建立時凍結，契約 §1.2.1），
     * 不隨 resume／restore 重算。
     */
    RunView snapshot(UUID runId) {
        ExecutionRun run = require(runId);
        try {
            RunSnapshot snap = bridge.getRun(runId);
            return new RunView(run.id(), run.projectId(), run.runNumber(), snap.status().fold(), snap.status(),
                    run.autonomyLevel(), run.scope(), snap.tokensUsed(), run.tokenBudget(), run.startedAt(),
                    completedAt(snap, run), run.engineCapabilities());
        } catch (BridgeRejectedException | UpstreamException e) {
            LOG.warn("控制操作成功，但讀不到批次 {} 的 Bridge 快照：{}", runId, e.getMessage());
            return new RunView(run.id(), run.projectId(), run.runNumber(), run.status(), null, run.autonomyLevel(),
                    run.scope(), run.totalTokensUsed(), run.tokenBudget(), run.startedAt(), run.completedAt(),
                    run.engineCapabilities());
        }
    }

    private static Instant completedAt(RunSnapshot snap, ExecutionRun run) {
        if (snap.completedAt() == null) {
            return run.completedAt();
        }
        try {
            return OffsetDateTime.parse(snap.completedAt()).toInstant();
        } catch (DateTimeParseException e) {
            return run.completedAt();
        }
    }
}
