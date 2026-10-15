package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Edge;
import com.aisdlc.console.domain.model.execution.DagSnapshot.EdgeKind;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.DagSnapshot.NodeKind;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.ScopeMode;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;

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
 * 執行計畫：範圍解析、目標依賴排序、展平成 playbook 步驟序列（契約 §1.2.1 第 6～8 項、§3.4.4）。純 Java。
 *
 * <p>範圍：{@code ALL}＝專案內全部「可執行」任務（狀態不是 COMPLETED／SKIPPED）；{@code SELECTED}＝所選目標的全部可執行任務 ∪
 * 所選任務。目標順序＝依 {@code goal_dependencies} 做<b>分層 Kahn</b>（{@link DagService#layeredOrder}），同層依
 * {@link Strategy} 擇一；目標內任務依 {@code sortOrder}（平手取 {@code createdAt}、{@code id}，由呼叫端排好傳入）。
 * {@code step_id} ＝ {@code G<目標位置>-T<任務位置>}（位置＝本批次範圍內的 1 起序號，整份 playbook 唯一）。
 */
public final class ExecutionPlanner {

    /** {@code execution.dagSchedulerStrategy}：決定同層目標的比較器。 */
    public enum Strategy {
        /** 同層依 {@code sortOrder} 升冪。 */
        TOPOLOGICAL,
        /** PRD 沒有優先欄位，視同 {@code sortOrder}。 */
        PRIORITY,
        /** 所屬目標內（範圍內任務）預估 Token 總和升冪（null 視為 0），平手取 {@code sortOrder}。 */
        SHORTEST_FIRST;

        public static Strategy parse(String raw) {
            if (raw == null) {
                return TOPOLOGICAL;
            }
            try {
                return valueOf(raw.strip());
            } catch (IllegalArgumentException e) {
                return TOPOLOGICAL;
            }
        }
    }

    /** 專案內一個未刪除的目標與其未刪除的任務（任務已依 sortOrder、createdAt、id 排好）。 */
    public record GoalWithTasks(Goal goal, List<Task> tasks) {
    }

    /** 展平後的一個步驟。 */
    public record PlannedTask(Task task, Goal goal, int goalPosition, int taskPosition, int sequence, String stepId) {
    }

    /** 計畫：依序的目標、依序的步驟，以及要凍結進 {@code execution_runs.dag} 的結構。 */
    public record Plan(List<Goal> goals, List<PlannedTask> tasks, DagSnapshot dag) {

        public Plan {
            goals = List.copyOf(goals);
            tasks = List.copyOf(tasks);
        }
    }

    private ExecutionPlanner() {
    }

    /**
     * @param enforceDependencies 是否檢查 7b（所選目標依賴了未選且未完成的前置目標）。審核 SKIP／RETRY 開的後續批次
     *                            （範圍＝專案內其餘未完成任務）不檢查，其餘情況一律檢查
     */
    public static Plan plan(List<GoalWithTasks> projectGoals, Map<UUID, Set<UUID>> dependencyGraph, RunScope scope,
                            Strategy strategy, boolean enforceDependencies) {
        Map<UUID, GoalWithTasks> goalsById = new LinkedHashMap<>();
        Map<UUID, Task> tasksById = new HashMap<>();
        for (GoalWithTasks entry : projectGoals) {
            goalsById.put(entry.goal().id(), entry);
            entry.tasks().forEach(t -> tasksById.put(t.id(), t));
        }
        requireScopeBelongsToProject(scope, goalsById, tasksById);

        Set<UUID> inScope = new LinkedHashSet<>();
        if (scope.mode() == ScopeMode.ALL) {
            for (GoalWithTasks entry : projectGoals) {
                entry.tasks().stream().filter(t -> !done(t.status())).forEach(t -> inScope.add(t.id()));
            }
        } else {
            requireNothingSelectedIsDone(scope, goalsById, tasksById);
            for (UUID goalId : scope.goalIds()) {
                goalsById.get(goalId).tasks().stream().filter(t -> !done(t.status())).forEach(t -> inScope.add(t.id()));
            }
            inScope.addAll(scope.taskIds());
        }

        List<GoalWithTasks> planGoals = projectGoals.stream()
                .filter(g -> g.tasks().stream().anyMatch(t -> inScope.contains(t.id()))).toList();
        Set<UUID> planGoalIds = new LinkedHashSet<>();
        planGoals.forEach(g -> planGoalIds.add(g.goal().id()));

        if (scope.mode() == ScopeMode.SELECTED && enforceDependencies) {
            requireDependenciesAreSelectedOrDone(planGoalIds, dependencyGraph, goalsById);
        }
        if (inScope.isEmpty()) {
            throw new ConflictException("範圍內沒有可執行的任務", ErrorReasons.NOTHING_TO_EXECUTE);
        }

        Map<UUID, Set<UUID>> restricted = new LinkedHashMap<>();
        for (GoalWithTasks g : planGoals) {
            Set<UUID> deps = new LinkedHashSet<>();
            for (UUID dep : dependencyGraph.getOrDefault(g.goal().id(), Set.of())) {
                if (planGoalIds.contains(dep)) {
                    deps.add(dep);
                }
            }
            restricted.put(g.goal().id(), deps);
        }
        Optional<List<UUID>> cycle = DagService.findCycle(restricted);
        if (cycle.isPresent()) {
            List<String> ids = cycle.get().stream().map(UUID::toString).toList();
            throw new ConflictException("目標依賴成環：" + String.join(" -> ", ids), ErrorReasons.DEPENDENCY_CYCLE,
                    Map.of("cycle", ids));
        }

        Comparator<UUID> comparator = comparatorFor(strategy, goalsById, inScope);
        List<UUID> order = DagService.layeredOrder(restricted, comparator);
        return flatten(order, goalsById, restricted, inScope);
    }

    private static Plan flatten(List<UUID> order, Map<UUID, GoalWithTasks> goalsById,
                                Map<UUID, Set<UUID>> restricted, Set<UUID> inScope) {
        List<Goal> goals = new ArrayList<>();
        List<PlannedTask> planned = new ArrayList<>();
        List<Node> nodes = new ArrayList<>();
        List<Edge> dependencyEdges = new ArrayList<>();
        List<Edge> containsEdges = new ArrayList<>();
        Map<UUID, Integer> goalPosition = new HashMap<>();
        for (UUID goalId : order) {
            goalPosition.put(goalId, goalPosition.size() + 1);
        }
        int sequence = 0;
        for (UUID goalId : order) {
            GoalWithTasks entry = goalsById.get(goalId);
            Goal goal = entry.goal();
            int g = goalPosition.get(goalId);
            goals.add(goal);
            nodes.add(new Node(goal.id(), NodeKind.GOAL, goal.name(), null, null, g));
            restricted.get(goalId).stream().sorted(Comparator.comparingInt(goalPosition::get))
                    .forEach(dep -> dependencyEdges.add(new Edge(dep, goalId, EdgeKind.DEPENDENCY)));
            int t = 0;
            for (Task task : entry.tasks()) {
                if (!inScope.contains(task.id())) {
                    continue;
                }
                t++;
                sequence++;
                String stepId = "G" + g + "-T" + t;
                planned.add(new PlannedTask(task, goal, g, t, sequence, stepId));
                nodes.add(new Node(task.id(), NodeKind.TASK, task.name(), goal.id(), stepId, sequence));
                containsEdges.add(new Edge(goal.id(), task.id(), EdgeKind.CONTAINS));
            }
        }
        List<Edge> edges = new ArrayList<>(dependencyEdges);
        edges.addAll(containsEdges);
        return new Plan(goals, planned, new DagSnapshot(nodes, edges));
    }

    private static Comparator<UUID> comparatorFor(Strategy strategy, Map<UUID, GoalWithTasks> goalsById,
                                                  Set<UUID> inScope) {
        Comparator<UUID> bySortOrder = Comparator
                .comparingInt((UUID id) -> goalsById.get(id).goal().sortOrder())
                .thenComparing(id -> goalsById.get(id).goal().createdAt(), Comparator.nullsLast(Comparator.naturalOrder()))
                .thenComparing(id -> id);
        if (strategy != Strategy.SHORTEST_FIRST) {
            return bySortOrder;
        }
        return Comparator.comparingLong((UUID id) -> estimatedTokens(goalsById.get(id), inScope))
                .thenComparing(bySortOrder);
    }

    private static long estimatedTokens(GoalWithTasks entry, Set<UUID> inScope) {
        return entry.tasks().stream().filter(t -> inScope.contains(t.id()))
                .mapToLong(t -> t.estimatedTokens() == null ? 0L : t.estimatedTokens()).sum();
    }

    /** 第 6 項：所選目標與任務都必須屬於該專案（400 {@code 所選範圍不合法}）。 */
    private static void requireScopeBelongsToProject(RunScope scope, Map<UUID, GoalWithTasks> goalsById,
                                                     Map<UUID, Task> tasksById) {
        List<String> invalidGoals = scope.goalIds().stream().filter(id -> !goalsById.containsKey(id)).distinct()
                .map(UUID::toString).toList();
        List<String> invalidTasks = scope.taskIds().stream().filter(id -> !tasksById.containsKey(id)).distinct()
                .map(UUID::toString).toList();
        if (!invalidGoals.isEmpty() || !invalidTasks.isEmpty()) {
            String message = "所選範圍包含不屬於此專案（或已刪除）的目標或任務";
            throw new ValidationException(message, ErrorReasons.SCOPE_INVALID, List.of(new Violation("scope", message)),
                    Map.of("invalidGoalIds", invalidGoals, "invalidTaskIds", invalidTasks));
        }
    }

    /** 第 7a 項：SELECTED 內有已 COMPLETED／SKIPPED 的目標或任務（409）。 */
    private static void requireNothingSelectedIsDone(RunScope scope, Map<UUID, GoalWithTasks> goalsById,
                                                     Map<UUID, Task> tasksById) {
        List<String> doneGoals = scope.goalIds().stream().distinct()
                .filter(id -> doneGoal(goalsById.get(id).goal().status())).map(UUID::toString).toList();
        List<String> doneTasks = scope.taskIds().stream().distinct()
                .filter(id -> done(tasksById.get(id).status())).map(UUID::toString).toList();
        if (!doneGoals.isEmpty() || !doneTasks.isEmpty()) {
            throw new ConflictException("所選目標或任務已完成，不可再次執行", ErrorReasons.SCOPE_ALREADY_DONE,
                    Map.of("goalIds", doneGoals, "taskIds", doneTasks));
        }
    }

    /** 第 7b 項：範圍內的目標依賴了「未選且未完成」的目標（409）。COMPLETED 與 SKIPPED 都算已滿足。 */
    private static void requireDependenciesAreSelectedOrDone(Set<UUID> planGoalIds, Map<UUID, Set<UUID>> graph,
                                                             Map<UUID, GoalWithTasks> goalsById) {
        Set<String> missing = new LinkedHashSet<>();
        for (UUID goalId : planGoalIds) {
            for (UUID dep : graph.getOrDefault(goalId, Set.of())) {
                GoalWithTasks depGoal = goalsById.get(dep);
                if (!planGoalIds.contains(dep) && depGoal != null && !doneGoal(depGoal.goal().status())) {
                    missing.add(dep.toString());
                }
            }
        }
        if (!missing.isEmpty()) {
            throw new ConflictException("所選目標依賴了尚未完成、也未被選取的前置目標",
                    ErrorReasons.SCOPE_MISSING_DEPENDENCIES, Map.of("missingGoalIds", List.copyOf(missing)));
        }
    }

    private static boolean done(TaskStatus status) {
        return status == TaskStatus.COMPLETED || status == TaskStatus.SKIPPED;
    }

    private static boolean doneGoal(GoalStatus status) {
        return status == GoalStatus.COMPLETED || status == GoalStatus.SKIPPED;
    }
}
