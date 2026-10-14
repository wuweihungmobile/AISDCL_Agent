package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.infrastructure.persistence.entity.TaskEntity;

/** Task（domain）↔ TaskEntity（JPA）的轉換；DDL 允許 NULL 的欄位在此補回 domain 的預設值。 */
final class TaskMapper {

    private TaskMapper() {
    }

    static TaskEntity toEntity(Task t) {
        TaskEntity e = new TaskEntity();
        e.id = t.id();
        e.goalId = t.goalId();
        e.name = t.name();
        e.description = t.description();
        e.passCriteria = t.passCriteria();
        e.evaluatorCommand = t.evaluatorCommand();
        e.expectedOutputRegex = t.expectedOutputRegex();
        e.passCriteriaSpec = t.passCriteriaSpec();
        e.sortOrder = t.sortOrder();
        e.status = t.status();
        e.estimatedTokens = t.estimatedTokens();
        e.actualTokens = t.actualTokens();
        e.retryCount = t.retryCount();
        e.maxRetries = t.maxRetries();
        e.assignedAgent = t.assignedAgent();
        e.executionLog = t.executionLog();
        e.signedOff = t.signedOff();
        e.signedOffBy = t.signedOffBy();
        e.signedOffAt = t.signedOffAt();
        e.deleted = t.deleted();
        e.createdAt = t.createdAt();
        e.updatedAt = t.updatedAt();
        e.startedAt = t.startedAt();
        e.completedAt = t.completedAt();
        return e;
    }

    static Task toDomain(TaskEntity e) {
        return Task.restore(e.id, e.goalId, e.name, e.description, e.passCriteria, e.evaluatorCommand,
                e.expectedOutputRegex, e.passCriteriaSpec, e.sortOrder == null ? 0 : e.sortOrder, e.status,
                e.estimatedTokens, e.actualTokens, e.retryCount == null ? 0 : e.retryCount,
                e.maxRetries == null ? Task.DEFAULT_MAX_RETRIES : e.maxRetries, e.assignedAgent,
                e.executionLog, e.signedOff, e.signedOffBy, e.signedOffAt, Boolean.TRUE.equals(e.deleted),
                e.createdAt, e.updatedAt, e.startedAt, e.completedAt);
    }
}
