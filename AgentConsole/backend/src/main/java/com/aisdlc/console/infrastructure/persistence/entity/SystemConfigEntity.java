package com.aisdlc.console.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

/**
 * system_configs 表（PRD §6.2）的 JPA 映射；Phase 6（設定頁）才會用到，本波只需 validate 通過。
 * Java 欄位名 {@code configKey}／{@code configValue} 對應 {@code key}／{@code value} 欄（避開 HQL 關鍵字）。
 */
@Entity
@Table(name = "system_configs")
public class SystemConfigEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "category", nullable = false, length = 50)
    public String category;

    @Column(name = "key", nullable = false, length = 200)
    public String configKey;

    @Column(name = "value", nullable = false, columnDefinition = "text")
    public String configValue;

    @Column(name = "value_type", nullable = false, length = 20)
    public String valueType;

    @Column(name = "default_value", columnDefinition = "text")
    public String defaultValue;

    @Column(name = "description", length = 500)
    public String description;

    @Column(name = "is_encrypted")
    public Boolean encrypted;

    @Column(name = "validation_rule", length = 500)
    public String validationRule;

    @Column(name = "updated_at")
    public Instant updatedAt;

    @Column(name = "updated_by", length = 100)
    public String updatedBy;
}
