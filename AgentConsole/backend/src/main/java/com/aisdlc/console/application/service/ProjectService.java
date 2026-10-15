package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ManageGoalUseCase.GoalWithCounts;
import com.aisdlc.console.application.port.in.ManageProjectUseCase;
import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.GoalRepository.TaskCounts;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.project.NewProject;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.project.ProjectUpdate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** 專案管理用例實作（PRD §5.1.1）。每個公開方法一個交易；寫入類失敗會整筆回滾。 */
@Service
@Transactional
public class ProjectService implements ManageProjectUseCase {

    /** PUT 可手動設定的狀態目標：其餘狀態（EXECUTING／COMPLETED／FAILED／ARCHIVED）只由執行引擎事件或刪除驅動。 */
    private static final Set<ProjectStatus> MANUAL_STATUS_TARGETS =
            EnumSet.of(ProjectStatus.DRAFT, ProjectStatus.READY);

    static final int MAX_PAGE_SIZE = 100;

    private final ProjectRepository projects;
    private final GoalRepository goals;
    private final TaskRepository tasks;
    private final RuntimeSettings settings;
    private final AuditTrail audit;
    private final Clock clock;

    public ProjectService(ProjectRepository projects, GoalRepository goals, TaskRepository tasks,
                          RuntimeSettings settings, AuditTrail audit, Clock clock) {
        this.projects = projects;
        this.goals = goals;
        this.tasks = tasks;
        this.settings = settings;
        this.audit = audit;
        this.clock = clock;
    }

    @Override
    public ProjectView create(NewProject spec, String createdBy) {
        Project project = Project.create(spec, createdBy, clock.instant());
        projects.save(project);
        return new ProjectView(project, ProjectCounts.ZERO);
    }

    @Override
    @Transactional(readOnly = true)
    public PageResult<ProjectView> list(ListQuery query) {
        Violations v = new Violations();
        if (query.page() < 0) {
            v.add("page", "page 不可為負數");
        }
        if (query.size() < 1 || query.size() > MAX_PAGE_SIZE) {
            v.add("size", "size 必須介於 1 到 " + MAX_PAGE_SIZE);
        }
        v.throwIfAny();
        PageResult<Project> page = projects.search(query);
        Map<UUID, ProjectCounts> counts = projects.countsFor(page.content().stream().map(Project::id).toList());
        return page.map(p -> new ProjectView(p, counts.getOrDefault(p.id(), ProjectCounts.ZERO)));
    }

    @Override
    @Transactional(readOnly = true)
    public ProjectDetailView get(UUID projectId) {
        Project project = load(projectId);
        List<Goal> projectGoals = goals.findByProjectId(projectId);
        Map<UUID, TaskCounts> taskCounts = goals.taskCountsFor(projectGoals.stream().map(Goal::id).toList());
        List<GoalWithCounts> briefs = projectGoals.stream().map(g -> {
            TaskCounts c = taskCounts.getOrDefault(g.id(), TaskCounts.ZERO);
            return new GoalWithCounts(g, c.total(), c.completed());
        }).toList();
        int tasksTotal = briefs.stream().mapToInt(GoalWithCounts::taskCount).sum();
        int tasksDone = briefs.stream().mapToInt(GoalWithCounts::completedTaskCount).sum();
        return new ProjectDetailView(project, new ProjectCounts(briefs.size(), tasksTotal, tasksDone), briefs);
    }

    @Override
    public ProjectView update(UUID projectId, ProjectUpdate update) {
        Project project = load(projectId);
        if (update.status() != null && update.status() != project.status()
                && !MANUAL_STATUS_TARGETS.contains(update.status())) {
            throw new ConflictException("狀態 " + update.status() + " 只能由執行引擎事件驅動，不可手動設定",
                    "不可手動轉移至該狀態",
                    Map.of("from", project.status().name(), "to", update.status().name(),
                            "allowedManualTargets", MANUAL_STATUS_TARGETS.stream().map(Enum::name).sorted().toList()));
        }
        project.update(update, clock.instant());
        projects.save(project);
        return viewOf(project);
    }

    @Override
    public void delete(UUID projectId) {
        Project project = load(projectId);
        Instant now = clock.instant();
        project.softDelete(now);
        projects.save(project);
        // 連帶軟刪目標與任務（US-G-05／US-P-05）；兩者都在同一個交易內，且與專案寫同一個 deleted_at（V9）——
        // 復原靠「目標／任務的 deleted_at 等於專案的」辨識同一次刪除連帶軟刪的列。
        tasks.softDeleteByProjectId(projectId, now);
        goals.softDeleteByProjectId(projectId, now);
    }

    /**
     * 復原軟刪除的專案（契約 §1.6.1，C-3）：專案本身還原為刪除前的狀態、同一次刪除連帶軟刪的目標與任務一併回來；在存活專案內
     * 單獨先刪除的目標／任務（{@code deleted_at} 與專案的不同）維持已刪除。單一交易，專案列先鎖住（兩個並發的 restore 只有一個成功，
     * 另一個看到「未被刪除」的 409）。保留期與清除排程是否開啟無關：超過 {@code soft-delete-days} 的專案即使資料還在也不可復原。
     */
    @Override
    public ProjectDetailView restore(UUID projectId) {
        Project project = projects.findIncludingDeletedForUpdate(projectId).orElseThrow(
                () -> new NotFoundException("專案不存在或已清除：" + projectId));
        if (!project.deleted()) {
            throw new ConflictException("專案未被刪除，不需復原", ErrorReasons.PROJECT_NOT_DELETED,
                    Map.of("projectId", projectId.toString(), "status", project.status().name()));
        }
        Instant now = clock.instant();
        int retentionDays = settings.softDeleteRetentionDays();
        Instant deletedAt = project.deletedAt();
        if (deletedAt.isBefore(now.minus(Duration.ofDays(retentionDays)))) {
            throw new ConflictException("專案已刪除超過 " + retentionDays + " 天，不可復原", ErrorReasons.RESTORE_WINDOW_EXPIRED,
                    Map.of("projectId", projectId.toString(), "deletedAt", deletedAt.toString(),
                            "retentionDays", retentionDays));
        }
        project.recover(now);
        projects.save(project);
        goals.restoreDeletedWithProject(projectId, deletedAt, now);
        tasks.restoreDeletedWithProject(projectId, deletedAt, now);
        audit.note("project.restore", "project", projectId.toString());
        return get(projectId);
    }

    @Override
    public ProjectView signoff(UUID projectId, String approver) {
        Project project = load(projectId);
        project.signoff(approver, clock.instant());
        projects.save(project);
        return viewOf(project);
    }

    private Project load(UUID projectId) {
        return projects.findById(projectId).orElseThrow(() -> NotFoundException.of("專案", projectId));
    }

    private ProjectView viewOf(Project project) {
        return new ProjectView(project,
                projects.countsFor(List.of(project.id())).getOrDefault(project.id(), ProjectCounts.ZERO));
    }
}
