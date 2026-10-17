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
import com.aisdlc.console.domain.model.execution.ExecutionWarning;
import com.aisdlc.console.domain.model.execution.ReviewRequest;
import com.aisdlc.console.domain.model.execution.ReviewStatus;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.service.ExecutionPlanner.Plan;
import com.aisdlc.console.domain.service.ExecutionPlanner.PlannedTask;
import com.aisdlc.console.domain.service.PlaybookBuilder.Playbook;
import com.aisdlc.console.domain.service.SddBatchPolicy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.function.Consumer;

/**
 * 建立一個執行批次並交給 Bridge（契約 §3.4.5）：execute 與審核的後續批次共用。
 *
 * <ol>
 *   <li><b>物化</b>（交易 1 之前，只呼叫一次，契約 §3.4.2 一致性規則）：{@link ConfigMaterializer#materialize(int)} 的回傳值同時用於
 *       下一步 INSERT 的 {@code engine_capabilities} 與送給 Bridge 的 {@code config_overrides}／{@code env}——兩次分開讀設定，
 *       設定可能在中間被改，落庫的值就會與實際送出的不符；</li>
 *   <li><b>交易 1</b>：鎖專案列 → 取 {@code run_number} → 插入 {@code execution_runs}（只寫 console 欄位，含
 *       {@code engine_capabilities}）→ <b>提交</b>（Bridge 的 {@code UPDATE … WHERE id=run_id} 需要列已存在）；</li>
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
     * @param plan         已通過範圍／依賴驗證的計畫（凍結進 {@code dag}）；SDD 批次的 step_id 已換成 {@code passCriteriaSpec.stepId}
     * @param playbook     已通過第 9a～9f 項驗證的 Playbook
     * @param scope        寫進 {@code execution_runs.scope} 的範圍（後續批次帶 {@code followUpOfRunId}）
     * @param sdd          SDD 批次判定（契約 §1.10.5）：{@code active} 才送 {@code sdd} 區塊；不成立時可能帶要出聲的警告
     * @param approver     {@code sdd.approver}（只有 {@code sdd.active} 時有值）
     */
    public record Launch(Project project, Plan plan, Playbook playbook, RunScope scope, int autonomyLevel,
                         Long tokenBudget, SddBatchPolicy.Decision sdd, String approver) {

        /** 非 SDD 批次（沒有 {@code sdd} 區塊、沒有警告）。 */
        public Launch(Project project, Plan plan, Playbook playbook, RunScope scope, int autonomyLevel,
                      Long tokenBudget) {
            this(project, plan, playbook, scope, autonomyLevel, tokenBudget, SddBatchPolicy.Decision.NONE, null);
        }
    }

    /** {@link #launchWithWarnings} 的結果：建好的批次，與要回給呼叫端的警告（console 自己的判定＋Bridge 201 的 {@code warnings}）。 */
    public record Launched(ExecutionRun run, List<ExecutionWarning> warnings) {
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
        return launchWithWarnings(launch, beforeEffects).run();
    }

    /**
     * 同 {@link #launch}，另回警告（契約 §1.10.6）：console 自己的 {@code sdd_governance_inactive}（資格不成立）加 Bridge 201 帶的
     * {@code warnings}（{@code sdd_frozen_digest_absent}）。每個警告同時以 WARN 記進 console-api 日誌——審核決定開的後續批次回 204、
     * 沒有地方回警告，日誌是它們唯一的出口。
     */
    public Launched launchWithWarnings(Launch launch, Consumer<ExecutionRun> beforeEffects) {
        UUID projectId = launch.project().id();
        // 在交易 1 之前、只呼叫這一次：結果同時決定落庫的 engine_capabilities 與送給 Bridge 的請求（契約 §3.4.2 一致性規則）。
        // 物化失敗（例如設定讀取失敗）發生在建列之前，所以不需要補償。
        ConfigMaterializer.Materialized materialized = config.materialize(launch.autonomyLevel());
        ExecutionRun created = tx.execute(status -> {
            projects.findByIdForUpdate(projectId).orElseThrow(() -> NotFoundException.of("專案", projectId));
            ExecutionRun draft = new ExecutionRun(UUID.randomUUID(), projectId, runs.nextRunNumber(projectId),
                    RunStatus.INITIALIZING, launch.autonomyLevel(), launch.scope(), 0L, launch.tokenBudget(),
                    clock.instant(), null, launch.plan().dag(), 0, null, materialized.engineCapabilities());
            return runs.insert(draft);
        });
        // 契約 §0.4 第 6 點：背景消費者之後呼叫 Bridge 沿用「啟動這個 run 的請求」的 traceId（只存記憶體）
        registry.bindTrace(created.id(), TraceIds.current());
        List<ExecutionWarning> warnings = new ArrayList<>();
        if (launch.sdd().warning() != null) {
            warnings.add(launch.sdd().warning());
        }
        // 帶 sdd 區塊的批次，Bridge 的預檢失敗要把「送出的有效 FSM 專案」放進 sdd_fsm_not_found 的 details
        String sddProject = launch.sdd().active() ? launch.project().effectiveSddProject() : null;
        try {
            AgentBridge.RunStarted started = bridge.startRun(startRequest(launch, created, materialized));
            warnings.addAll(started.warnings());
            LOG.info("Bridge 已接受批次 {}（run #{}，狀態 {}）", created.id(), created.runNumber(), started.status());
        } catch (BridgeRejectedException e) {
            compensate(created.id());
            throw BridgeErrors.forStart(e, sddProject);
        } catch (RuntimeException e) {
            compensate(created.id());
            throw e;
        }
        for (ExecutionWarning warning : warnings) {
            LOG.warn("批次 {} 的警告 {}（cause={}）：{}", created.id(), warning.code(), warning.cause(), warning.detail());
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
        return new Launched(created, List.copyOf(warnings));
    }

    private static StartRunRequest startRequest(Launch launch, ExecutionRun run,
                                                ConfigMaterializer.Materialized materialized) {
        return new StartRunRequest(run.id(), launch.playbook().project(), launch.project().executionPath(),
                launch.playbook().toMap(), materialized.configOverrides(), materialized.env(), false, sddBlock(launch));
    }

    /**
     * 資格成立時的頂層 {@code sdd} 區塊（契約 §1.10.6）：規格目錄／規格檔取自專案的綁定、{@code fsm_project} 是<b>有效值</b>
     * （原名或標準鍵，Bridge 一律先淨化）、{@code root} 是專案根、{@code approver} 永遠具名。權杖由出站介面卡以標頭附上。
     */
    private static AgentBridge.SddBlock sddBlock(Launch launch) {
        if (!launch.sdd().active()) {
            return null;
        }
        Project project = launch.project();
        return new AgentBridge.SddBlock(project.sddSpecDir(), project.sddSpecFile(), project.effectiveSddProject(),
                project.executionPath(), launch.approver());
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
