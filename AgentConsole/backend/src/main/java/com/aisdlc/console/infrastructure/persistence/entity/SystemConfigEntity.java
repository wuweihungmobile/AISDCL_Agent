package com.aisdlc.console.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

/**
 * system_configs 表（PRD §6.2）的 JPA 映射（Phase 6 系統設定）。
 * Java 欄位名 {@code configKey}／{@code configValue} 對應 {@code key}／{@code value} 欄（避開 HQL 關鍵字）。
 * {@code impact_note} 為 V5 增補（US-S-08 影響範圍提示）。加密參數的 {@code value} 存 {@code v1:<iv>:<密文>}（空字串＝沒有值）。
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

    @Column(name = "impact_note", length = 500)
    public String impactNote;

    @Column(name = "updated_at")
    public Instant updatedAt;

    @Column(name = "updated_by", length = 100)
    public String updatedBy;
}
