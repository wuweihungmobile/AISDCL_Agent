package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ManageGoalUseCase;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.GoalRepository.TaskCounts;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalUpdate;
import com.aisdlc.console.domain.model.goal.NewGoal;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.domain.service.DagService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * 目標管理用例實作（PRD §5.1.2）。
 *
 * <p>會改動整張專案依賴圖的操作（建立帶依賴、更新依賴、重排）先對專案列加鎖（SELECT … FOR UPDATE），
 * 讓並發的兩個請求不會各自通過 Kahn 檢查卻合起來成環。
 */
@Service
@Transactional
public class GoalService implements ManageGoalUseCase {

    private final ProjectRepository projects;
    private final GoalRepository goals;
    private final TaskRepository tasks;
    private final Clock clock;

    public GoalService(ProjectRepository projects, GoalRepository goals, TaskRepository tasks, Clock clock) {
        this.projects = projects;
        this.goals = goals;
        this.tasks = tasks;
        this.clock = clock;
    }

    @Override
    public GoalWithCounts create(UUID projectId, NewGoal spec) {
        boolean hasDependencies = spec.dependsOn() != null && !spec.dependsOn().isEmpty();
        var project = hasDependencies ? projects.findByIdForUpdate(projectId) : projects.findById(projectId);
        project.orElseThrow(() -> NotFoundException.of("專案", projectId));
        Goal goal = Goal.create(projectId, spec, goals.nextSortOrder(projectId), clock.instant());
        if (hasDependencies) {
            verifyDependencies(goal);
        }
        goals.save(goal);
        return new GoalWithCounts(goal, 0, 0);
    }

    @Override
    @Transactional(readOnly = true)
    public List<GoalWithCounts> list(UUID projectId) {
        projects.findById(projectId).orElseThrow(() -> NotFoundException.of("專案", projectId));
        List<Goal> projectGoals = goals.findByProjectId(projectId);
        Map<UUID, TaskCounts> counts = goals.taskCountsFor(projectGoals.stream().map(Goal::id).toList());
        return projectGoals.stream().map(g -> withCounts(g, counts.getOrDefault(g.id(), TaskCounts.ZERO))).toList();
    }

    @Override
    @Transactional(readOnly = true)
    public GoalDetailView get(UUID goalId) {
        Goal goal = load(goalId);
        List<Task> goalTasks = tasks.findByGoalId(goalId);
        int completed = (int) goalTasks.stream().filter(t -> t.status() == TaskStatus.COMPLETED).count();
        return new GoalDetailView(new GoalWithCounts(goal, goalTasks.size(), completed), goalTasks);
    }

    @Override
    public GoalWithCounts update(UUID goalId, GoalUpdate update) {
        Goal goal = load(goalId);
        boolean changesDependencies = update.dependsOn() != null;
        if (changesDependencies) {
            projects.findByIdForUpdate(goal.projectId())
                    .orElseThrow(() -> NotFoundException.of("專案", goal.projectId()));
        }
        // 先套用欄位更新：自依賴與欄位驗證在 domain 內擋掉（400），之後才用整張圖檢查成環與跨專案。
        goal.update(update, clock.instant());
        if (changesDependencies) {
            verifyDependencies(goal);
        }
        goals.save(goal);
        return withCounts(goal, goals.taskCountsFor(List.of(goalId)).getOrDefault(goalId, TaskCounts.ZERO));
    }

    @Override
    public void delete(UUID goalId) {
        Goal goal = load(goalId);
        if (tasks.existsByGoalIdAndStatus(goalId, TaskStatus.RUNNING)) {
            throw new ConflictException("目標含執行中的任務，不可刪除", "RUNNING 狀態的任務不可刪除",
                    Map.of("goalId", goalId.toString()));
        }
        Instant now = clock.instant();
        goal.softDelete(now);
        goals.save(goal);
        tasks.softDeleteByGoalId(goalId, now);
    }

    @Override
    public void reorder(UUID projectId, List<UUID> orderedGoalIds) {
        projects.findByIdForUpdate(projectId).orElseThrow(() -> NotFoundException.of("專案", projectId));
        List<UUID> ordered = orderedGoalIds == null ? List.of() : orderedGoalIds;
        Set<UUID> requested = new LinkedHashSet<>(ordered);
        if (requested.size() != ordered.size()) {
            throw ValidationException.of("orderedGoalIds", "orderedGoalIds 不可包含重複的目標 id");
        }
        Map<UUID, Goal> current = new LinkedHashMap<>();
        goals.findByProjectId(projectId).forEach(g -> current.put(g.id(), g));
        if (!requested.equals(current.keySet())) {
            List<String> unknown = requested.stream().filter(id -> !current.containsKey(id)).map(UUID::toString).toList();
            List<String> missing = current.keySet().stream().filter(id -> !requested.contains(id))
                    .map(UUID::toString).toList();
            throw ValidationException.of("orderedGoalIds",
                    "orderedGoalIds 必須恰好包含專案下全部目標（未知 " + unknown.size() + " 個、缺少 " + missing.size() + " 個）",
                    "重排清單與專案目標不一致", Map.of("unknownIds", unknown, "missingIds", missing));
        }
        Instant now = clock.instant();
        int position = 0;
        for (UUID id : ordered) {
            Goal goal = current.get(id);
            int before = goal.sortOrder();
            goal.moveTo(position++, now);
            if (goal.sortOrder() != before) {
                goals.save(goal);
            }
        }
    }

    @Override
    public GoalWithCounts signoff(UUID goalId, String approver) {
        Goal goal = load(goalId);
        goal.signoff(approver, clock.instant());
        goals.save(goal);
        return withCounts(goal, goals.taskCountsFor(List.of(goalId)).getOrDefault(goalId, TaskCounts.ZERO));
    }

    private Goal load(UUID goalId) {
        return goals.findById(goalId).orElseThrow(() -> NotFoundException.of("目標", goalId));
    }

    private static GoalWithCounts withCounts(Goal goal, TaskCounts counts) {
        return new GoalWithCounts(goal, counts.total(), counts.completed());
    }

    /**
     * 依賴完整性：被依賴的目標必須存在、未軟刪且屬於同一專案；再把「這個目標的新依賴集合」放進專案圖，
     * 以 Kahn 試算確認不成環（成環→400，reason＝依賴成環，附環路 id 清單）。
     */
    private void verifyDependencies(Goal goal) {
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>(goals.dependencyGraph(goal.projectId()));
        List<UUID> invalid = goal.dependsOn().stream().filter(id -> !graph.containsKey(id)).toList();
        if (!invalid.isEmpty()) {
            throw invalidTargets(invalid);
        }
        graph.put(goal.id(), new LinkedHashSet<>(goal.dependsOn()));
        DagService.requireAcyclic(graph);
    }

    private ValidationException invalidTargets(List<UUID> invalid) {
        List<String> crossProject = new ArrayList<>();
        List<String> missing = new ArrayList<>();
        for (UUID id : invalid) {
            if (goals.findById(id).isPresent()) {
                crossProject.add(id.toString());
            } else {
                missing.add(id.toString());
            }
        }
        String reason = crossProject.isEmpty() ? "依賴目標不存在" : "跨專案依賴";
        Map<String, Object> details = new HashMap<>();
        details.put("crossProjectIds", crossProject);
        details.put("missingIds", missing);
        return ValidationException.of("dependsOn",
                reason + "：目標只能依賴同一專案內、未刪除的目標", reason, details);
    }
}
