package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecuteProjectUseCase;
import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunView;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunLimits;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.aisdlc.console.domain.model.execution.ScopeMode;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.service.ExecutionPlanner;
import com.aisdlc.console.domain.service.ExecutionPlanner.GoalWithTasks;
import com.aisdlc.console.domain.service.ExecutionPlanner.Plan;
import com.aisdlc.console.domain.service.PlaybookBuilder;
import com.aisdlc.console.domain.service.PlaybookBuilder.Playbook;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * 啟動專案執行（契約 §1.2.1；PRD §5.3.4 US-E-01、02、10）。
 *
 * <p>驗證順序（固定，QA 依序斷言）：1 專案存在 → 2 請求欄位 → 3 專案正在執行 → 4 專案狀態 → 5 <b>人工 signoff 硬閘</b>
 * （PRD 逐字 reason）→ 6 所選範圍屬於該專案 → 7a／7b／7c 範圍內容 → 8 依賴成環 → 9a～9f Playbook 檢查 → 10 Bridge。
 * 第 3～9f 項<b>不呼叫 Bridge</b>；本類別的唯讀階段（1～9f）在一個唯讀交易內完成，呼叫 Bridge 與寫入由 {@link RunLauncher} 負責。
 *
 * <p>簽核檢查的範圍是<b>整個專案</b>（專案、全部未刪除的目標與任務），而不只是所選範圍：契約 E2E-02 步驟 5 要求
 * 「所選目標不屬於該專案、同時專案內仍有未 signoff 的任務」回 409（未 signoff 先於範圍檢查），範圍限定的檢查做不到這點；
 * 整案檢查也更保守（「未經人工審批的草案不可執行」），見交卷〈契約漂移〉。
 */
@Service
public class ExecuteProjectService implements ExecuteProjectUseCase {

    private final ProjectRepository projects;
    private final GoalRepository goals;
    private final TaskRepository tasks;
    private final ExecutionRunRepository runs;
    private final SettingsReader settings;
    private final RuntimeSettings runtime;
    private final RunLauncher launcher;
    private final SddBatches sddBatches;
    private final AuditTrail audit;
    private final TransactionTemplate readTx;

    @SuppressWarnings("java:S107")
    public ExecuteProjectService(ProjectRepository projects, GoalRepository goals, TaskRepository tasks,
                                 ExecutionRunRepository runs, SettingsReader settings, RuntimeSettings runtime,
                                 RunLauncher launcher, SddBatches sddBatches, AuditTrail audit,
                                 PlatformTransactionManager transactions) {
        this.projects = projects;
        this.goals = goals;
        this.tasks = tasks;
        this.runs = runs;
        this.settings = settings;
        this.runtime = runtime;
        this.launcher = launcher;
        this.sddBatches = sddBatches;
        this.audit = audit;
        this.readTx = new TransactionTemplate(transactions);
        this.readTx.setReadOnly(true);
    }

    @Override
    public RunView execute(UUID projectId, Command command, String actor) {
        audit.note("execution.start", "project", projectId.toString());
        RunLauncher.Launch launch = readTx.execute(status -> prepare(projectId, command, actor));
        RunLauncher.Launched launched = launcher.launchWithWarnings(launch, created -> { });
        ExecutionRun run = launched.run();
        return new RunView(run.id(), run.projectId(), run.runNumber(), RunStatus.RUNNING, BridgeStatus.RUNNING,
                run.autonomyLevel(), run.scope(), 0L, run.tokenBudget(), run.startedAt(), null,
                run.engineCapabilities(), launched.warnings());
    }

    private RunLauncher.Launch prepare(UUID projectId, Command command, String actor) {
        Project project = projects.findById(projectId).orElseThrow(() -> NotFoundException.of("專案", projectId));
        RunScope scope = validateRequest(command);
        if (project.status() == ProjectStatus.EXECUTING) {
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("projectId", projectId.toString());
            runs.findActiveRunId(projectId).ifPresent(id -> details.put("runId", id.toString()));
            throw new ConflictException("專案正在執行中", ErrorReasons.PROJECT_EXECUTING, details);
        }
        if (project.status() == ProjectStatus.ARCHIVED) {
            throw new ConflictException("專案已封存，不可執行", ErrorReasons.PROJECT_STATE_NOT_EXECUTABLE,
                    Map.of("status", project.status().name()));
        }
        List<Goal> projectGoals = goals.findByProjectId(projectId);
        List<Task> projectTasks = tasks.findByProjectId(projectId);
        requireSignedOff(project, projectGoals, projectTasks);

        List<GoalWithTasks> grouped = new ArrayList<>();
        for (Goal goal : projectGoals) {
            grouped.add(new GoalWithTasks(goal, projectTasks.stream().filter(t -> t.goalId().equals(goal.id()))
                    .toList()));
        }
        ExecutionPlanner.Strategy strategy = ExecutionPlanner.Strategy.parse(
                settings.value("execution", "dagSchedulerStrategy"));
        Plan plan = ExecutionPlanner.plan(grouped, goals.dependencyGraph(projectId), scope, strategy, true);
        // v1.5：SDD 批次資格判定（契約 §1.10.5）——成立時 step_id 換成 passCriteriaSpec.stepId，Bridge 請求另帶 sdd 區塊；不成立時出聲
        SddBatches.Prepared sdd = sddBatches.prepare(project, plan, actor);
        Set<String> allowlist = runtime.evaluatorAllowlist();
        Playbook playbook = PlaybookBuilder.build(project, sdd.plan(), settings.intValue("agent", "maxRetries"),
                allowlist, sdd.decision().specs());

        int level = command.autonomyLevel() == null ? project.autonomyLevel() : command.autonomyLevel();
        long budget = command.tokenBudget() == null ? settings.longValue("execution", "globalTokenBudget")
                : command.tokenBudget();
        return new RunLauncher.Launch(project, sdd.plan(), playbook, scope, level, budget, sdd.decision(),
                sdd.approver());
    }

    /** 第 2 項：請求欄位（等級 1～10、預算 ≥ 1、範圍模式與 id 的組合、限額 ≥ 1）。 */
    private static RunScope validateRequest(Command command) {
        Violations v = new Violations();
        if (command.autonomyLevel() != null && (command.autonomyLevel() < 1 || command.autonomyLevel() > 10)) {
            v.add("autonomyLevel", "自治等級必須介於 1 到 10");
        }
        if (command.tokenBudget() != null && command.tokenBudget() < 1) {
            v.add("tokenBudget", "Token 預算必須 ≥ 1");
        }
        ScopeMode mode = ScopeMode.ALL;
        if (command.scopeMode() != null) {
            try {
                mode = ScopeMode.valueOf(command.scopeMode());
            } catch (IllegalArgumentException e) {
                v.add("scope.mode", "scope.mode 只能是 ALL 或 SELECTED");
            }
        }
        List<UUID> goalIds = command.goalIds() == null ? List.of() : command.goalIds();
        List<UUID> taskIds = command.taskIds() == null ? List.of() : command.taskIds();
        if (mode == ScopeMode.ALL && (!goalIds.isEmpty() || !taskIds.isEmpty())) {
            v.add("scope", "scope.mode=ALL 時不可帶 goalIds／taskIds");
        }
        if (mode == ScopeMode.SELECTED && goalIds.isEmpty() && taskIds.isEmpty()) {
            v.add("scope", "scope.mode=SELECTED 時 goalIds 與 taskIds 至少要有一個");
        }
        if (command.taskTokens() != null && command.taskTokens() < 1) {
            v.add("scope.limits.taskTokens", "單一任務 Token 上限必須 ≥ 1");
        }
        if (command.goalTokens() != null && command.goalTokens() < 1) {
            v.add("scope.limits.goalTokens", "單一目標 Token 上限必須 ≥ 1");
        }
        v.throwIfAny();
        return new RunScope(mode, goalIds, taskIds, new RunLimits(command.taskTokens(), command.goalTokens()), null);
    }

    /** 第 5 項：專案與其全部目標、任務都已人工 signoff（草案不可執行；PRD §0.4）。 */
    private static void requireSignedOff(Project project, List<Goal> projectGoals, List<Task> projectTasks) {
        List<String> unsignedGoals = projectGoals.stream().filter(g -> !g.signedOff()).map(g -> g.id().toString())
                .toList();
        List<String> unsignedTasks = projectTasks.stream().filter(t -> !t.signedOff()).map(t -> t.id().toString())
                .toList();
        if (project.signedOff() && unsignedGoals.isEmpty() && unsignedTasks.isEmpty()) {
            return;
        }
        throw unsignedDraft(project, unsignedGoals, unsignedTasks);
    }

    static ConflictException unsignedDraft(Project project, List<String> unsignedGoals, List<String> unsignedTasks) {
        Map<String, Object> details = new LinkedHashMap<>();
        if (!project.signedOff()) {
            details.put("unsignedProjectId", project.id().toString());
        }
        details.put("unsignedGoalIds", unsignedGoals);
        details.put("unsignedTaskIds", unsignedTasks);
        return new ConflictException("草案未經人工審批，禁止執行", ErrorReasons.UNSIGNED_DRAFT, details);
    }
}
