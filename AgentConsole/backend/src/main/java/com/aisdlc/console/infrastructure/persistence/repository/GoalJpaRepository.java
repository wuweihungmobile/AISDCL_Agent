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

    @Modifying(flushAutomatically = true, clearAutomatically = true)
    @Query("update GoalEntity g set g.deleted = true, g.updatedAt = :now "
            + "where g.projectId = :projectId and g.deleted = false")
    int softDeleteByProjectId(@Param("projectId") UUID projectId, @Param("now") Instant now);
}
