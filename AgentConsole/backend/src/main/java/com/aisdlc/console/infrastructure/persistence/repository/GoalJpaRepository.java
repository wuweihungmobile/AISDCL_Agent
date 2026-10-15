package com.aisdlc.console.infrastructure.persistence.repository;

import com.aisdlc.console.infrastructure.persistence.entity.GoalEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface GoalJpaRepository extends JpaRepository<GoalEntity, UUID> {

    Optional<GoalEntity> findByIdAndDeletedFalse(UUID id);

    List<GoalEntity> findByProjectIdAndDeletedFalseOrderBySortOrderAscCreatedAtAscIdAsc(UUID projectId);

    @Query("select coalesce(max(g.sortOrder), -1) from GoalEntity g where g.projectId = :projectId and g.deleted = false")
    int maxSortOrder(@Param("projectId") UUID projectId);

    @Query("select new com.aisdlc.console.infrastructure.persistence.repository.KeyedCount(g.projectId, count(g)) "
            + "from GoalEntity g where g.projectId in :projectIds and g.deleted = false group by g.projectId")
    List<KeyedCount> countByProjects(@Param("projectIds") Collection<UUID> projectIds);

    /** 軟刪除專案下全部仍存活的目標：{@code deleted_at} 與專案同值（V9；復原據此辨識「同一次刪除連帶軟刪」）。 */
    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update GoalEntity g set g.deleted = true, g.deletedAt = :now, g.updatedAt = :now "
            + "where g.projectId = :projectId and g.deleted = false")
    int softDeleteByProjectId(@Param("projectId") UUID projectId, @Param("now") Instant now);

    /** 復原：只還原 {@code deleted_at} 等於專案刪除時間者；單獨先刪除的目標（deleted_at 不同）維持已刪除。 */
    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update GoalEntity g set g.deleted = false, g.deletedAt = null, g.updatedAt = :now "
            + "where g.projectId = :projectId and g.deleted = true and g.deletedAt = :deletedAt")
    int restoreDeletedWithProject(@Param("projectId") UUID projectId, @Param("deletedAt") Instant deletedAt,
                                  @Param("now") Instant now);
}
