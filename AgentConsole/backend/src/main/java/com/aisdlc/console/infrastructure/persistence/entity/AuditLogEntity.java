package com.aisdlc.console.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

/** audit_log 表（V6）的 JPA 映射：寫入端點審計落庫（NFR-9.2-07）；只寫不讀（契約沒有任何端點讀它）。 */
@Entity
@Table(name = "audit_log")
public class AuditLogEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "occurred_at", nullable = false, updatable = false)
    public Instant occurredAt;

    @Column(name = "subject", length = 100)
    public String subject;

    @Column(name = "role", length = 20)
    public String role;

    @Column(name = "method", nullable = false, length = 10)
    public String method;

    @Column(name = "path", nullable = false, length = 500)
    public String path;

    @Column(name = "entity_type", length = 50)
    public String entityType;

    @Column(name = "entity_id", length = 100)
    public String entityId;

    @Column(name = "http_status", nullable = false)
    public Integer httpStatus;

    @Column(name = "trace_id", length = 64)
    public String traceId;
}
