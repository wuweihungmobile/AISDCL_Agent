package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.StartRunRequest;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.ExecutionStepRepository;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ReviewRequestRepository;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.ReviewRequest;
import com.aisdlc.console.domain.model.execution.ReviewStatus;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.service.ExecutionPlanner.Plan;
import com.aisdlc.console.domain.service.ExecutionPlanner.PlannedTask;
import com.aisdlc.console.domain.service.PlaybookBuilder.Playbook;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.function.Consumer;

/**
 * 建立一個執行批次並交給 Bridge（契約 §3.4.5）：execute 與審核的後續批次共用。
 *
 * <ol>
 *   <li><b>交易 1</b>：鎖專案列 → 取 {@code run_number} → 插入 {@code execution_runs}（只寫 console 欄位）→ <b>提交</b>
 *       （Bridge 的 {@code UPDATE … WHERE id=run_id} 需要列已存在）；</li>
 *   <li>呼叫 Bridge {@code POST /autoclaude/runs}（非冪等，不重試）；</li>
 *   <li>201 → <b>交易 2</b>：專案 {@code EXECUTING}、範圍內任務 {@code QUEUED}、前一批次仍 PENDING 的審核項自動關閉，
 *       然後啟動事件消費者；</li>
 *   <li>失敗 → <b>交易 3</b>：補償刪除剛建的列（守門只有一條：該 run 尚無任何 {@code execution_steps}，不看狀態——
 *       Bridge 在 {@code spawn_failed} 時已把列標成 FAILED，仍要刪，否則留下佔用 run_number 的空批次，AR-15），再轉譯錯誤。</li>
 * </ol>
 */
@Component
public class RunLauncher {

    private static final Logger LOG = LoggerFactory.getLogger(RunLauncher.class);

    /**
     * @param plan         已通過範圍／依賴驗證的計畫（凍結進 {@code dag}）
     * @param playbook     已通過第 9a～9f 項驗證的 Playbook
     * @param scope        寫進 {@code execution_runs.scope} 的範圍（後續批次帶 {@code followUpOfRunId}）
     */
    public record Launch(Project project, Plan plan, Playbook playbook, RunScope scope, int autonomyLevel,
                         Long tokenBudget) {
    }

    private final ExecutionRunRepository runs;
    private final ExecutionStepRepository steps;
    private final ProjectRepository projects;
    private final TaskRepository tasks;
    private final ReviewRequestRepository reviews;
    private final AgentBridge bridge;
    private final ConfigMaterializer config;
    private final RunConsumers consumers;
    private final BridgeHealthMonitor health;
    private final RunRegistry registry;
    private final TransactionTemplate tx;
    private final Clock clock;

    @SuppressWarnings("java:S107")
    public RunLauncher(ExecutionRunRepository runs, ExecutionStepRepository steps, ProjectRepository projects,
                       TaskRepository tasks, ReviewRequestRepository reviews, AgentBridge bridge,
                       ConfigMaterializer config, RunConsumers consumers, BridgeHealthMonitor health,
                       RunRegistry registry, PlatformTransactionManager transactions, Clock clock) {
        this.runs = runs;
        this.steps = steps;
        this.projects = projects;
        this.tasks = tasks;
        this.reviews = reviews;
        this.bridge = bridge;
        this.config = config;
        this.consumers = consumers;
        this.health = health;
        this.registry = registry;
        this.tx = new TransactionTemplate(transactions);
        this.clock = clock;
    }

    /**
     * @param beforeEffects 在「交易 2」最前面執行（審核 SKIP 在這裡先把審核項與任務標成 SKIPPED，再讓新批次自動關閉其他待決項，
     *                      契約 §1.2.11 的先後）；失敗則整個交易 2 回滾
     */
    public ExecutionRun launch(Launch launch, Consumer<ExecutionRun> beforeEffects) {
        UUID projectId = launch.project().id();
        ExecutionRun created = tx.execute(status -> {
            projects.findByIdForUpdate(projectId).orElseThrow(() -> NotFoundException.of("專案", projectId));
            ExecutionRun draft = new ExecutionRun(UUID.randomUUID(), projectId, runs.nextRunNumber(projectId),
                    RunStatus.INITIALIZING, launch.autonomyLevel(), launch.scope(), 0L, launch.tokenBudget(),
                    clock.instant(), null, launch.plan().dag(), 0, null);
            return runs.insert(draft);
        });
        // 契約 §0.4 第 6 點：背景消費者之後呼叫 Bridge 沿用「啟動這個 run 的請求」的 traceId（只存記憶體）
        registry.bindTrace(created.id(), TraceIds.current());
        try {
            AgentBridge.RunStarted started = bridge.startRun(startRequest(launch, created));
            LOG.info("Bridge 已接受批次 {}（run #{}，狀態 {}）", created.id(), created.runNumber(), started.status());
        } catch (BridgeRejectedException e) {
            compensate(created.id());
            throw BridgeErrors.forStart(e);
        } catch (RuntimeException e) {
            compensate(created.id());
            throw e;
        }
        try {
            tx.executeWithoutResult(status -> {
                if (beforeEffects != null) {
                    beforeEffects.accept(created);
                }
                applyLaunchEffects(created, launch.plan());
            });
        } catch (RuntimeException e) {
            LOG.error("批次 {} 已被 Bridge 接受，但讀模型更新失敗，嘗試取消：{}", created.id(), e.toString());
            try {
                bridge.stopRun(created.id());
            } catch (RuntimeException stopFailure) {
                LOG.error("取消批次 {} 也失敗：{}", created.id(), stopFailure.toString());
            }
            compensate(created.id());
            throw e;
        }
        health.probeNow();
        consumers.start(created.id(), 0);
        return created;
    }

    private StartRunRequest startRequest(Launch launch, ExecutionRun run) {
        ConfigMaterializer.Materialized materialized = config.materialize();
        return new StartRunRequest(run.id(), launch.playbook().project(), launch.project().executionPath(),
                launch.playbook().toMap(), materialized.configOverrides(), materialized.env(), false);
    }

    /** 專案 EXECUTING、範圍內任務 QUEUED、前一批次仍待決的審核項自動關閉（契約 §3.5.3）。 */
    private void applyLaunchEffects(ExecutionRun run, Plan plan) {
        Instant now = clock.instant();
        Project project = projects.findByIdForUpdate(run.projectId())
                .orElseThrow(() -> NotFoundException.of("專案", run.projectId()));
        project.startExecuting(now);
        projects.save(project);
        List<UUID> taskIds = plan.tasks().stream().map(PlannedTask::task).map(Task::id).toList();
        for (Task task : tasks.findByIds(taskIds)) {
            task.queueForRun(now);
            tasks.save(task);
        }
        for (ReviewRequest pending : reviews.findPendingOfOtherRuns(run.projectId(), run.id())) {
            reviews.update(pending.decided(ReviewStatus.REJECTED, ReviewRequest.SYSTEM, now,
                    "已由第 " + run.runNumber() + " 批次取代"));
        }
    }

    /** 補償刪除（交易 3）：守門只有一條——該 run 尚無任何 {@code execution_steps}（不看列的狀態）。 */
    void compensate(UUID runId) {
        try {
            tx.executeWithoutResult(status -> {
                if (!steps.existsByRun(runId)) {
                    runs.deleteById(runId);
                } else {
                    LOG.warn("批次 {} 已有步驟列，不做補償刪除", runId);
                }
            });
        } catch (RuntimeException e) {
            LOG.error("補償刪除批次 {} 失敗：{}", runId, e.toString());
        }
        registry.forget(runId);
    }
}
