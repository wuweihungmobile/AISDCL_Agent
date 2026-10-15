package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.infrastructure.persistence.entity.GoalDependencyEntity;
import com.aisdlc.console.infrastructure.persistence.entity.GoalEntity;
import com.aisdlc.console.infrastructure.persistence.repository.GoalDependencyJpaRepository;
import com.aisdlc.console.infrastructure.persistence.repository.GoalJpaRepository;
import com.aisdlc.console.infrastructure.persistence.repository.KeyedTaskCount;
import com.aisdlc.console.infrastructure.persistence.repository.TaskJpaRepository;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/** {@link GoalRepository} 的 JPA 實作；goal.dependsOn() 與 goal_dependencies 邊在 save 時做差異同步。 */
@Component
class GoalRepositoryAdapter implements GoalRepository {

    private final GoalJpaRepository goals;
    private final GoalDependencyJpaRepository dependencies;
    private final TaskJpaRepository tasks;

    GoalRepositoryAdapter(GoalJpaRepository goals, GoalDependencyJpaRepository dependencies,
                          TaskJpaRepository tasks) {
        this.goals = goals;
        this.dependencies = dependencies;
        this.tasks = tasks;
    }

    @Override
    public Goal save(Goal goal) {
        goals.save(GoalMapper.toEntity(goal));
        syncDependencies(goal);
        return goal;
    }

    @Override
    public Optional<Goal> findById(UUID id) {
        return goals.findByIdAndDeletedFalse(id).map(entity -> {
            List<UUID> deps = dependencies.findLiveEdgesByGoal(id).stream()
                    .map(edge -> edge.dependsOnGoalId).toList();
            return GoalMapper.toDomain(entity, deps);
        });
    }

    @Override
    public List<Goal> findByProjectId(UUID projectId) {
        List<GoalEntity> entities = goals.findByProjectIdAndDeletedFalseOrderBySortOrderAscCreatedAtAscIdAsc(projectId);
        Map<UUID, List<UUID>> deps = new HashMap<>();
        for (GoalDependencyEntity edge : dependencies.findLiveEdgesByProject(projectId)) {
            deps.computeIfAbsent(edge.goalId, k -> new ArrayList<>()).add(edge.dependsOnGoalId);
        }
        return entities.stream()
                .map(entity -> GoalMapper.toDomain(entity, deps.getOrDefault(entity.id, List.of())))
                .toList();
    }

    @Override
    public Map<UUID, Set<UUID>> dependencyGraph(UUID projectId) {
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>();
        for (GoalEntity goal : goals.findByProjectIdAndDeletedFalseOrderBySortOrderAscCreatedAtAscIdAsc(projectId)) {
            graph.put(goal.id, new LinkedHashSet<>());
        }
        for (GoalDependencyEntity edge : dependencies.findLiveEdgesByProject(projectId)) {
            graph.get(edge.goalId).add(edge.dependsOnGoalId);
        }
        return graph;
    }

    @Override
    public Map<UUID, TaskCounts> taskCountsFor(Collection<UUID> goalIds) {
        Map<UUID, TaskCounts> result = new HashMap<>();
        if (goalIds.isEmpty()) {
            return result;
        }
        for (KeyedTaskCount row : tasks.countByGoals(goalIds, TaskStatus.COMPLETED)) {
            result.put(row.key(), new TaskCounts(row.total().intValue(), row.completed().intValue()));
        }
        return result;
    }

    @Override
    public int nextSortOrder(UUID projectId) {
        return goals.maxSortOrder(projectId) + 1;
    }

    @Override
    public int softDeleteByProjectId(UUID projectId, Instant now) {
        return goals.softDeleteByProjectId(projectId, now);
    }

    @Override
    public int restoreDeletedWithProject(UUID projectId, Instant deletedAt, Instant now) {
        return goals.restoreDeletedWithProject(projectId, deletedAt, now);
    }

    /** 把 goal.dependsOn() 同步成資料表的邊：只刪「不再需要的」、只加「新的」，保留既有邊的建立時間。 */
    private void syncDependencies(Goal goal) {
        Map<UUID, GoalDependencyEntity> existing = new LinkedHashMap<>();
        for (GoalDependencyEntity edge : dependencies.findByGoalId(goal.id())) {
            existing.put(edge.dependsOnGoalId, edge);
        }
        List<GoalDependencyEntity> toRemove = existing.entrySet().stream()
                .filter(entry -> !goal.dependsOn().contains(entry.getKey()))
                .map(Map.Entry::getValue).toList();
        if (!toRemove.isEmpty()) {
            dependencies.deleteAll(toRemove);
            dependencies.flush();
        }
        int offset = 0;
        List<GoalDependencyEntity> toAdd = new ArrayList<>();
        for (UUID dependency : goal.dependsOn()) {
            if (!existing.containsKey(dependency)) {
                GoalDependencyEntity edge = new GoalDependencyEntity();
                edge.id = UUID.randomUUID();
                edge.goalId = goal.id();
                edge.dependsOnGoalId = dependency;
                // 以遞增的微秒偏移保留使用者給的依賴順序（timestamptz 精度為微秒）。
                edge.createdAt = goal.updatedAt().plus(offset++, ChronoUnit.MICROS);
                toAdd.add(edge);
            }
        }
        dependencies.saveAll(toAdd);
    }
}
