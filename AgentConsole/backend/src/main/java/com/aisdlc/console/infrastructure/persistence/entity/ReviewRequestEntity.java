package com.aisdlc.console.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

/** review_requests 表（V3；Architecture §11.3）的 JPA 映射；Phase 4 才會用到，本波只需 validate 通過。 */
@Entity
@Table(name = "review_requests")
public class ReviewRequestEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "run_id", nullable = false, updatable = false)
    public UUID runId;

    @Column(name = "step_id")
    public UUID stepId;

    @Column(name = "task_id")
    public UUID taskId;

    @Column(name = "goal_id")
    public UUID goalId;

    @Column(name = "kind", nullable = false, length = 20)
    public String kind;

    @Column(name = "status", nullable = false, length = 20)
    public String status;

    @Column(name = "reason", columnDefinition = "text")
    public String reason;

    @Column(name = "requested_at")
    public Instant requestedAt;

    @Column(name = "decided_by", length = 100)
    public String decidedBy;

    @Column(name = "decided_at")
    public Instant decidedAt;

    @Column(name = "comment", columnDefinition = "text")
    public String comment;
}
