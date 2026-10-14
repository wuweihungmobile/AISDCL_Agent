package com.aisdlc.console.infrastructure.persistence.repository;

import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.infrastructure.persistence.entity.TaskEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TaskJpaRepository extends JpaRepository<TaskEntity, UUID> {

    Optional<TaskEntity> findByIdAndDeletedFalse(UUID id);

    List<TaskEntity> findByGoalIdAndDeletedFalseOrderBySortOrderAscCreatedAtAscIdAsc(UUID goalId);

    boolean existsByGoalIdAndStatusAndDeletedFalse(UUID goalId, TaskStatus status);

    @Query("select coalesce(max(t.sortOrder), -1) from TaskEntity t where t.goalId = :goalId and t.deleted = false")
    int maxSortOrder(@Param("goalId") UUID goalId);

    @Query("select new com.aisdlc.console.infrastructure.persistence.repository.KeyedTaskCount("
            + "g.projectId, count(t), coalesce(sum(case when t.status = :done then 1L else 0L end), 0L)) "
            + "from TaskEntity t join GoalEntity g on t.goalId = g.id "
            + "where g.projectId in :projectIds and t.deleted = false and g.deleted = false group by g.projectId")
    List<KeyedTaskCount> countByProjects(@Param("projectIds") Collection<UUID> projectIds,
                                         @Param("done") TaskStatus done);

    @Query("select new com.aisdlc.console.infrastructure.persistence.repository.KeyedTaskCount("
            + "t.goalId, count(t), coalesce(sum(case when t.status = :done then 1L else 0L end), 0L)) "
            + "from TaskEntity t where t.goalId in :goalIds and t.deleted = false group by t.goalId")
    List<KeyedTaskCount> countByGoals(@Param("goalIds") Collection<UUID> goalIds, @Param("done") TaskStatus done);

    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update TaskEntity t set t.deleted = true, t.updatedAt = :now where t.goalId = :goalId and t.deleted = false")
    int softDeleteByGoalId(@Param("goalId") UUID goalId, @Param("now") Instant now);

    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update TaskEntity t set t.deleted = true, t.updatedAt = :now "
            + "where t.deleted = false and t.goalId in (select g.id from GoalEntity g where g.projectId = :projectId)")
    int softDeleteByProjectId(@Param("projectId") UUID projectId, @Param("now") Instant now);
}
