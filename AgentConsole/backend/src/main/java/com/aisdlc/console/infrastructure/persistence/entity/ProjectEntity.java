package com.aisdlc.console.infrastructure.persistence.entity;

import com.aisdlc.console.domain.model.project.ProjectStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

/**
 * projects 表（PRD §6.2）的 JPA 映射。純資料持有者、無行為：業務規則在 domain 的 Project，
 * 由 adapter.out.persistence 的 mapper 做轉換（Architecture §4.1：實體與 domain model 分離）。
 * 欄位刻意公開：這層只負責與資料表一一對映，Hibernate 以欄位存取。
 */
@Entity
@Table(name = "projects")
public class ProjectEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "name", nullable = false, length = 200)
    public String name;

    @Column(name = "execution_path", nullable = false, length = 500)
    public String executionPath;

    @Column(name = "pass_criteria", nullable = false, columnDefinition = "text")
    public String passCriteria;

    @Column(name = "description", columnDefinition = "text")
    public String description;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    public ProjectStatus status;

    @Column(name = "autonomy_level")
    public Integer autonomyLevel;

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

    @Column(name = "created_by", length = 100)
    public String createdBy;
}
