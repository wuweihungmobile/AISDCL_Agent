package com.aisdlc.console.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

/** system_config_history 表（PRD §6.2）的 JPA 映射；Phase 6 才會用到，本波只需 validate 通過。 */
@Entity
@Table(name = "system_config_history")
public class SystemConfigHistoryEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "config_id", nullable = false, updatable = false)
    public UUID configId;

    @Column(name = "old_value", columnDefinition = "text")
    public String oldValue;

    @Column(name = "new_value", nullable = false, columnDefinition = "text")
    public String newValue;

    @Column(name = "changed_at")
    public Instant changedAt;

    @Column(name = "changed_by", length = 100)
    public String changedBy;
}
