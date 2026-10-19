package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.CheckpointRepository;
import com.aisdlc.console.application.port.out.CheckpointRepository.CheckpointRow;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ReviewRequestRepository;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.ReviewDecision;
import com.aisdlc.console.domain.model.execution.ReviewKind;
import com.aisdlc.console.domain.model.execution.ReviewRequest;
import com.aisdlc.console.domain.model.execution.RunLimits;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.aisdlc.console.domain.model.execution.ScopeMode;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.domain.service.ExecutionPlanner;
import com.aisdlc.console.domain.service.ExecutionPlanner.GoalWithTasks;
import com.aisdlc.console.domain.service.ExecutionPlanner.Plan;
import com.aisdlc.console.domain.service.PlaybookBuilder;
import com.aisdlc.console.domain.service.ReviewGatePolicy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 審核決定（契約 §1.2.11、§3.6.3）：路徑的 {@code {stepId}} 是 {@code review_requests.id}（UUID），審核人取自 JWT subject。
 *
 * <p>決定與動作（逐 kind，契約 §3.6.3 的資料化）：
 * <ul>
 *   <li>gate 類（{@code TASK_CONFIRM}／{@code GOAL_CONFIRM}／{@code GOAL_COMPLETED}）：{@code APPROVE}＝Bridge {@code :resume}（run 須
 *       PAUSED）；{@code REJECT}＝{@code :stop}，run CANCELLED（{@code GOAL_COMPLETED} 另把被審目標設為 FAILED——人類判定，
 *       優先於 R-goal 重算）；{@code GOAL_COMPLETED} 的 {@code RETRY}＝restore 到「該目標第一個步驟之前」的 checkpoint
 *       （{@code step_idx = p−1}），找不到（首個目標）改為先 {@code :stop}、再開後續批次；</li>
 *   <li>{@code ESCALATED}：{@code RETRY}＝restore 到失敗步驟之前的 checkpoint（找不到改開後續批次）；{@code SKIP}＝失敗任務標
 *       SKIPPED，並以剔除它的新 playbook 開後續批次（Bridge 的 resume 只收 PAUSED、restore 無法跳過步驟）；{@code REJECT}＝只關閉審核項，
 *       不呼叫 Bridge。</li>
 * </ul>
 * <b>原子性</b>：後續批次先完成「建 run 列＋Bridge 接受」，成功後才提交審核項與任務的狀態變更；任何一步失敗全部回滾，審核項維持
 * PENDING。<b>先後</b>（AR-21）：先把這個審核項標 {@code SKIPPED}／{@code RETRIED}、任務標 SKIPPED，再讓新批次自動關閉
 * 其他仍 PENDING 的審核項。
 */
@Component
public class ReviewService {

    private static final Logger LOG = LoggerFactory.getLogger(ReviewService.class);

    private final ProjectRepository projects;
    private final GoalRepository goals;
    private final TaskRepository tasks;
    private final ReviewRequestRepository reviews;
    private final CheckpointRepository checkpoints;
    private final AgentBridge bridge;
    private final ExecutionControlService control;
    private final RunLauncher launcher;
    private final ConfigMaterializer config;
    private final SddBatches sddBatches;
    private final SettingsReader settings;
    private final RuntimeSettings runtime;
    private final RunRegistry registry;
    private final TransactionTemplate tx;
    private final Clock clock;

    @SuppressWarnings("java:S107")
    public ReviewService(ProjectRepository projects, GoalRepository goals,
                         TaskRepository tasks, ReviewRequestRepository reviews, CheckpointRepository checkpoints,
                         AgentBridge bridge, ExecutionControlService control, RunLauncher launcher,
                         ConfigMaterializer config, SddBatches sddBatches, SettingsReader settings,
                         RuntimeSettings runtime, RunRegistry registry, PlatformTransactionManager transactions,
                         Clock clock) {
        this.projects = projects;
        this.goals = goals;
        this.tasks = tasks;
        this.reviews = reviews;
        this.checkpoints = checkpoints;
        this.bridge = bridge;
        this.control = control;
        this.launcher = launcher;
        this.config = config;
        this.sddBatches = sddBatches;
        this.settings = settings;
        this.runtime = runtime;
        this.registry = registry;
        this.tx = new TransactionTemplate(transactions);
        this.clock = clock;
    }

    /** @return 後續批次的 id（SKIP、或找不到還原點而改開後續批次的 RETRY）；其餘決定回 empty。 */
    public Optional<UUID> decide(UUID runId, UUID reviewId, ReviewDecision decision, String comment, String actor) {
        return registry.locked(runId, () -> {
            ExecutionRun run = control.require(runId);
            ReviewRequest review = reviews.findById(reviewId).filter(r -> r.runId().equals(runId))
                    .orElseThrow(() -> new NotFoundException("審核項不存在或不屬於此執行：" + reviewId));
            requirePending(review);
            requireAllowed(review, decision);
            requireRunState(run, review, decision);
            String note = comment == null || comment.isBlank() ? null : comment;
            return switch (review.kind()) {
                case TASK_CONFIRM, GOAL_CONFIRM -> decideGate(run, review, decision, note, actor);
                case GOAL_COMPLETED -> decideGoalCompleted(run, review, decision, note, actor);
                case ESCALATED -> decideEscalated(run, review, decision, note, actor);
            };
        });
    }

    // ── 前置檢查 ────────────────────────────────────────────────────────────────

    private static void requirePending(ReviewRequest review) {
        if (!review.pending()) {
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("status", review.status().name());
            if (review.decidedBy() != null) {
                details.put("decidedBy", review.decidedBy());
            }
            if (review.decidedAt() != null) {
                details.put("decidedAt", review.decidedAt().toString());
            }
            throw new ConflictException("審核項已處理", ErrorReasons.REVIEW_ALREADY_DECIDED, details);
        }
    }

    private static void requireAllowed(ReviewRequest review, ReviewDecision decision) {
        List<ReviewDecision> allowed = ReviewGatePolicy.allowedDecisions(review.kind(), review.taskId() != null);
        if (!allowed.contains(decision)) {
            throw new ConflictException("此審核項（" + review.kind() + "）不允許決定 " + decision,
                    ErrorReasons.REVIEW_DECISION_NOT_ALLOWED, Map.of("kind", review.kind().name(), "decision",
                            decision.name(), "allowedDecisions", allowed.stream().map(Enum::name).toList()));
        }
    }

    /** gate 類的 APPROVE／REJECT 需 run 為 PAUSED；ESCALATED 類的 RETRY／SKIP 需 run 為終態（FAILED）。 */
    private void requireRunState(ExecutionRun run, ReviewRequest review, ReviewDecision decision) {
        boolean ok;
        if (review.kind().gate()) {
            ok = run.status() == RunStatus.PAUSED;
        } else if (decision == ReviewDecision.REJECT) {
            ok = true;
        } else {
            ok = run.status().terminal();
        }
        if (!ok) {
            throw control.stateNotAllowed(run, "review");
        }
    }

    // ── gate 類 ─────────────────────────────────────────────────────────────────

    private Optional<UUID> decideGate(ExecutionRun run, ReviewRequest review, ReviewDecision decision, String note,
                                      String actor) {
        if (decision == ReviewDecision.APPROVE) {
            control.requireSignedOff(run);
            control.call(run, "review", () -> bridge.resumeRun(run.id(), config.materialize(run.autonomyLevel()).env()));
            tx.executeWithoutResult(status -> {
                markDecided(review, decision, actor, note);
                control.afterResume(run, actor, "已核准");
            });
            return Optional.empty();
        }
        // REJECT：:stop → run CANCELLED；TASK_CONFIRM／GOAL_CONFIRM 不標任何目標
        control.call(run, "review", () -> bridge.stopRun(run.id()));
        tx.executeWithoutResult(status -> markDecided(review, decision, actor, note));
        return Optional.empty();
    }

    private Optional<UUID> decideGoalCompleted(ExecutionRun run, ReviewRequest review, ReviewDecision decision,
                                               String note, String actor) {
        return switch (decision) {
            case APPROVE -> decideGate(run, review, decision, note, actor);
            case REJECT -> {
                control.call(run, "review", () -> bridge.stopRun(run.id()));
                tx.executeWithoutResult(status -> {
                    markGoalFailed(review.goalId());
                    markDecided(review, decision, actor, note);
                });
                yield Optional.empty();
            }
            default -> retry(run, review, note, actor);
        };
    }

    /** 人工判定：被否決的目標設為 FAILED（之後事件消費者每個重算點都會再套一次，不被 R-goal 蓋回，AR-11）。 */
    private void markGoalFailed(UUID goalId) {
        if (goalId == null) {
            return;
        }
        Optional<Goal> goal = goals.findById(goalId);
        goal.ifPresent(g -> {
            g.systemSetStatus(GoalStatus.FAILED, clock.instant());
            goals.save(g);
        });
    }

    // ── ESCALATED ───────────────────────────────────────────────────────────────

    private Optional<UUID> decideEscalated(ExecutionRun run, ReviewRequest review, ReviewDecision decision,
                                           String note, String actor) {
        return switch (decision) {
            case REJECT -> {
                tx.executeWithoutResult(status -> markDecided(review, decision, actor, note));
                yield Optional.empty();
            }
            case SKIP -> Optional.of(skip(run, review, note, actor));
            case RETRY -> retry(run, review, note, actor);
            default -> throw new IllegalStateException("ESCALATED 不允許 " + decision);
        };
    }

    // ── RETRY（restore 或後續批次）──────────────────────────────────────────────

    /**
     * RETRY：要還原到「步驟位置 {@code p} 之前」＝取 {@code step_idx = p−1} 的快照；{@code GOAL_COMPLETED} 的 {@code p} 是該目標第一個步驟的
     * 位置，{@code ESCALATED} 的 {@code p} 是失敗步驟的位置。找不到快照（{@code p = 1}，沒有更早的快照）改開後續批次。
     */
    private Optional<UUID> retry(ExecutionRun run, ReviewRequest review, String note, String actor) {
        int position = retryPosition(run, review);
        Optional<CheckpointRow> target = position <= 1 ? Optional.empty()
                : checkpoints.findByRun(run.id()).stream().filter(c -> c.stepIdx() == position - 1).findFirst();
        if (target.isPresent()) {
            CheckpointRow checkpoint = target.get();
            control.callRestore(run, checkpoint);
            tx.executeWithoutResult(status -> {
                // 先把這個審核項標成 RETRIED，afterRestore 才不會把它當成「待決的 gate 審核項」自動 REJECTED
                markDecided(review, ReviewDecision.RETRY, actor, note);
                List<UUID> reset = control.afterRestore(run, checkpoint, actor);
                if (review.taskId() != null && reset.contains(review.taskId())) {
                    Instant now = clock.instant();
                    tasks.findById(review.taskId()).ifPresent(t -> {
                        t.countRetry(now);
                        tasks.save(t);
                    });
                }
            });
            return Optional.empty();
        }
        return Optional.of(retryAsFollowUp(run, review, position, note, actor));
    }

    private int retryPosition(ExecutionRun run, ReviewRequest review) {
        if (review.kind() == ReviewKind.GOAL_COMPLETED && review.goalId() != null) {
            return run.dag().firstPositionOfGoal(review.goalId()).orElse(1);
        }
        return review.taskId() == null ? 1 : run.dag().taskById(review.taskId()).map(Node::sequence).orElse(1);
    }

    /** 找不到還原點的 RETRY：先 {@code :stop}（run 非終態時），再開後續批次（範圍＝該位置起的全部任務，已完成者視為重跑）。 */
    private UUID retryAsFollowUp(ExecutionRun run, ReviewRequest review, int position, String note, String actor) {
        if (!run.status().terminal()) {
            control.call(run, "review", () -> bridge.stopRun(run.id()));
        }
        Project project = projects.findById(run.projectId()).orElseThrow(() -> NotFoundException.of("專案",
                run.projectId()));
        List<Task> all = tasks.findByProjectId(run.projectId());
        List<Task> rerun = new ArrayList<>();
        for (Node node : run.dag().taskNodes()) {
            if (node.sequence() >= position) {
                all.stream().filter(t -> t.id().equals(node.id())).findFirst().ifPresent(rerun::add);
            }
        }
        Instant now = clock.instant();
        // 範圍任務在規劃時須「未完成」：已完成者先在記憶體內重設，Bridge 接受之後才在交易內真的落庫
        rerun.forEach(t -> t.systemReset(TaskStatus.PENDING, now));
        ExecutionRun followUp = launchFollowUp(run, project, all, rerun.stream().map(Task::id).toList(), null, actor,
                created -> {
                    rerun.forEach(t -> {
                        t.systemReset(TaskStatus.PENDING, now);
                        tasks.save(t);
                    });
                    markDecided(review, ReviewDecision.RETRY, actor, note);
                    control.recomputeGoals(run.dag(), run.projectId(), now);
                });
        return followUp.id();
    }

    // ── SKIP（剔除該任務的後續批次）────────────────────────────────────────────

    private UUID skip(ExecutionRun run, ReviewRequest review, String note, String actor) {
        Project project = projects.findById(run.projectId()).orElseThrow(() -> NotFoundException.of("專案",
                run.projectId()));
        List<Task> all = tasks.findByProjectId(run.projectId());
        Instant now = clock.instant();
        Task skipped = all.stream().filter(t -> t.id().equals(review.taskId())).findFirst()
                .orElseThrow(() -> NotFoundException.of("任務", review.taskId()));
        skipped.skip(now);
        List<UUID> remaining = all.stream().filter(t -> t.status() != TaskStatus.COMPLETED
                && t.status() != TaskStatus.SKIPPED).map(Task::id).toList();
        if (remaining.isEmpty()) {
            // 沒有其餘任務可跑：不開後續批次，只收尾（任務與審核項標 SKIPPED，專案依全部任務狀態重算）
            tx.executeWithoutResult(status -> {
                tasks.save(skipped);
                markDecided(review, ReviewDecision.SKIP, actor, note);
                control.recomputeGoals(run.dag(), run.projectId(), now);
                projects.findByIdForUpdate(run.projectId()).ifPresent(p -> {
                    p.systemSetStatus(ProjectStatus.COMPLETED, now);
                    projects.save(p);
                });
            });
            return run.id();
        }
        ExecutionRun followUp = launchFollowUp(run, project, all, remaining, skipped, actor, created -> {
            tasks.save(skipped);
            markDecided(review, ReviewDecision.SKIP, actor, note);
            control.recomputeGoals(run.dag(), run.projectId(), now);
        });
        return followUp.id();
    }

    /**
     * 開後續批次：範圍＝{@code taskIds}（{@code SELECTED}，{@code scope.followUpOfRunId}＝原批次），繼承原批次的自治等級與
     * Token 預算／限額；後續批次不檢查「依賴已完成」（範圍本來就是專案內其餘任務）。
     */
    private ExecutionRun launchFollowUp(ExecutionRun original, Project project, List<Task> allTasks, List<UUID> taskIds,
                                        Task skipped, String actor, java.util.function.Consumer<ExecutionRun> beforeEffects) {
        List<Goal> projectGoals = goals.findByProjectId(project.id());
        List<GoalWithTasks> grouped = new ArrayList<>();
        for (Goal goal : projectGoals) {
            grouped.add(new GoalWithTasks(goal, allTasks.stream().filter(t -> t.goalId().equals(goal.id()))
                    .collect(Collectors.toList())));
        }
        RunScope scope = new RunScope(ScopeMode.SELECTED, List.of(), taskIds,
                original.scope().limits() == null ? RunLimits.NONE : original.scope().limits(), original.id());
        ExecutionPlanner.Strategy strategy = ExecutionPlanner.Strategy.parse(
                settings.value("execution", "dagSchedulerStrategy"));
        Plan plan = ExecutionPlanner.plan(grouped, goals.dependencyGraph(project.id()), scope, strategy, false);
        // v1.5（契約 §1.10.6）：後續批次走同一條建立路徑——同樣依資格送 sdd、同樣預檢；警告只寫日誌（RunLauncher 以 WARN 記），這些端點回 204
        SddBatches.Prepared sdd = sddBatches.prepare(project, plan, actor);
        PlaybookBuilder.Playbook playbook = PlaybookBuilder.build(project, sdd.plan(),
                settings.intValue("agent", "maxRetries"), runtime.evaluatorAllowlist(), sdd.decision().specs());
        LOG.info("審核決定開後續批次：原批次 {}，範圍任務 {} 個{}", original.id(), taskIds.size(),
                skipped == null ? "" : "（剔除 " + skipped.id() + "）");
        return launcher.launch(new RunLauncher.Launch(project, sdd.plan(), playbook, scope, original.autonomyLevel(),
                original.tokenBudget(), sdd.decision(), sdd.approver()), beforeEffects);
    }

    // ── 共用 ────────────────────────────────────────────────────────────────────

    private void markDecided(ReviewRequest review, ReviewDecision decision, String actor, String note) {
        ReviewRequest current = reviews.findByIdForUpdate(review.id()).orElse(review);
        if (!current.pending()) {
            throw new ConflictException("審核項已處理", ErrorReasons.REVIEW_ALREADY_DECIDED,
                    Map.of("status", current.status().name()));
        }
        reviews.update(current.decided(decision.resultingStatus(), actor, clock.instant(), note));
    }
}
