package com.aisdlc.console.infrastructure.persistence.repository;

import com.aisdlc.console.infrastructure.persistence.entity.GoalDependencyEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.UUID;

public interface GoalDependencyJpaRepository extends JpaRepository<GoalDependencyEntity, UUID> {

    /** 某目標的全部依賴邊（含指向已軟刪目標者；同步差異時用）。 */
    List<GoalDependencyEntity> findByGoalId(UUID goalId);

    /** 某目標的「有效」依賴邊：被依賴的目標必須未軟刪。 */
    @Query("select d from GoalDependencyEntity d join GoalEntity g on d.dependsOnGoalId = g.id "
            + "where d.goalId = :goalId and g.deleted = false order by d.createdAt, d.id")
    List<GoalDependencyEntity> findLiveEdgesByGoal(@Param("goalId") UUID goalId);

    /** 專案內「有效」依賴邊：兩端目標都必須未軟刪。 */
    @Query("select d from GoalDependencyEntity d "
            + "join GoalEntity g1 on d.goalId = g1.id "
            + "join GoalEntity g2 on d.dependsOnGoalId = g2.id "
            + "where g1.projectId = :projectId and g1.deleted = false and g2.deleted = false "
            + "order by d.createdAt, d.id")
    List<GoalDependencyEntity> findLiveEdgesByProject(@Param("projectId") UUID projectId);
}
