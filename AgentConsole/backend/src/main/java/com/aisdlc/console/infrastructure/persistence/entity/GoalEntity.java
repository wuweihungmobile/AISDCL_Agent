package com.aisdlc.console.infrastructure.persistence.entity;

import com.aisdlc.console.domain.model.goal.GoalStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

/** goals 表（PRD §6.2）的 JPA 映射；依賴關係在 {@link GoalDependencyEntity}。 */
@Entity
@Table(name = "goals")
public class GoalEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "project_id", nullable = false, updatable = false)
    public UUID projectId;

    @Column(name = "name", nullable = false, length = 200)
    public String name;

    @Column(name = "description", columnDefinition = "text")
    public String description;

    @Column(name = "pass_criteria", nullable = false, columnDefinition = "text")
    public String passCriteria;

    @Column(name = "sort_order")
    public Integer sortOrder;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    public GoalStatus status;

    @Column(name = "signed_off", nullable = false)
    public boolean signedOff;

    @Column(name = "signed_off_by", length = 100)
    public String signedOffBy;

    @Column(name = "signed_off_at")
    public Instant signedOffAt;

    @Column(name = "is_deleted")
    public Boolean deleted;

    @Column(name = "created_at")
    public Instant createdAt;

    @Column(name = "updated_at")
    public Instant updatedAt;

    /** V9（C-3）：軟刪除當下的時間；隨專案一起軟刪者與專案的 deleted_at 相同（復原據此辨識）。未刪除為 NULL。 */
    @Column(name = "deleted_at")
    public Instant deletedAt;
}
