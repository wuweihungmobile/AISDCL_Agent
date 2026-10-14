package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.infrastructure.persistence.repository.TaskJpaRepository;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** {@link TaskRepository} 的 JPA 實作（Entity↔Domain 轉換在 {@link TaskMapper}）。 */
@Component
class TaskRepositoryAdapter implements TaskRepository {

    private final TaskJpaRepository tasks;

    TaskRepositoryAdapter(TaskJpaRepository tasks) {
        this.tasks = tasks;
    }

    @Override
    public Task save(Task task) {
        tasks.save(TaskMapper.toEntity(task));
        return task;
    }

    @Override
    public Optional<Task> findById(UUID id) {
        return tasks.findByIdAndDeletedFalse(id).map(TaskMapper::toDomain);
    }

    @Override
    public List<Task> findByGoalId(UUID goalId) {
        return tasks.findByGoalIdAndDeletedFalseOrderBySortOrderAscCreatedAtAscIdAsc(goalId).stream()
                .map(TaskMapper::toDomain).toList();
    }

    @Override
    public int nextSortOrder(UUID goalId) {
        return tasks.maxSortOrder(goalId) + 1;
    }

    @Override
    public boolean existsByGoalIdAndStatus(UUID goalId, TaskStatus status) {
        return tasks.existsByGoalIdAndStatusAndDeletedFalse(goalId, status);
    }

    @Override
    public int softDeleteByGoalId(UUID goalId, Instant now) {
        return tasks.softDeleteByGoalId(goalId, now);
    }

    @Override
    public int softDeleteByProjectId(UUID projectId, Instant now) {
        return tasks.softDeleteByProjectId(projectId, now);
    }
}
