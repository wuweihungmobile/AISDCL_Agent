package com.aisdlc.console.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

/** goal_dependencies 表（PRD §6.2）：goalId 依賴 dependsOnGoalId；UNIQUE 與自依賴 CHECK 由 DDL 把關。 */
@Entity
@Table(name = "goal_dependencies")
public class GoalDependencyEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "goal_id", nullable = false, updatable = false)
    public UUID goalId;

    @Column(name = "depends_on_goal_id", nullable = false, updatable = false)
    public UUID dependsOnGoalId;

    @Column(name = "created_at")
    public Instant createdAt;
}
