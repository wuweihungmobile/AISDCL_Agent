package com.aisdlc.console.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.Immutable;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.UUID;

/** checkpoints 表（PRD §6.2）的 JPA 映射。由 Engine Bridge 寫入，console 端只讀（{@link Immutable}）。 */
@Entity
@Immutable
@Table(name = "checkpoints")
public class CheckpointEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "run_id", nullable = false)
    public UUID runId;

    @Column(name = "name", nullable = false, length = 200)
    public String name;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "state_snapshot", nullable = false, columnDefinition = "jsonb")
    public String stateSnapshot;

    @Column(name = "created_at")
    public Instant createdAt;

    @Column(name = "is_automatic")
    public Boolean automatic;
}
