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

    List<TaskEntity> findByIdInAndDeletedFalse(Collection<UUID> ids);

    /** 專案內全部未軟刪任務（其目標也須未軟刪），依 sortOrder、createdAt、id 排序。 */
    @Query("select t from TaskEntity t join GoalEntity g on t.goalId = g.id "
            + "where g.projectId = :projectId and t.deleted = false and g.deleted = false "
            + "order by t.sortOrder asc, t.createdAt asc, t.id asc")
    List<TaskEntity> findByProject(@Param("projectId") UUID projectId);

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
    @Query("update TaskEntity t set t.deleted = true, t.deletedAt = :now, t.updatedAt = :now "
            + "where t.goalId = :goalId and t.deleted = false")
    int softDeleteByGoalId(@Param("goalId") UUID goalId, @Param("now") Instant now);

    /** 軟刪除專案下全部仍存活的任務：{@code deleted_at} 與專案同值（V9；復原據此辨識「同一次刪除連帶軟刪」）。 */
    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update TaskEntity t set t.deleted = true, t.deletedAt = :now, t.updatedAt = :now "
            + "where t.deleted = false and t.goalId in (select g.id from GoalEntity g where g.projectId = :projectId)")
    int softDeleteByProjectId(@Param("projectId") UUID projectId, @Param("now") Instant now);

    /** 復原：只還原 {@code deleted_at} 等於專案刪除時間者；單獨先刪除的任務（deleted_at 不同）維持已刪除。 */
    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update TaskEntity t set t.deleted = false, t.deletedAt = null, t.updatedAt = :now "
            + "where t.deleted = true and t.deletedAt = :deletedAt "
            + "and t.goalId in (select g.id from GoalEntity g where g.projectId = :projectId)")
    int restoreDeletedWithProject(@Param("projectId") UUID projectId, @Param("deletedAt") Instant deletedAt,
                                  @Param("now") Instant now);
}
