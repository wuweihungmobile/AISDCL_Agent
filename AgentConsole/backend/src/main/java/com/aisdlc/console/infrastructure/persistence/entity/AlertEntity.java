package com.aisdlc.console.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;
import java.util.UUID;

/** alerts 表（V4；Architecture §11.3）的 JPA 映射；Phase 5 才會用到，本波只需 validate 通過。 */
@Entity
@Table(name = "alerts")
public class AlertEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "project_id", nullable = false, updatable = false)
    public UUID projectId;

    @Column(name = "run_id")
    public UUID runId;

    @Column(name = "rule", nullable = false, length = 40)
    public String rule;

    @Column(name = "severity", nullable = false, length = 20)
    public String severity;

    @Column(name = "subject", length = 100)
    public String subject;

    @Column(name = "message", nullable = false, columnDefinition = "text")
    public String message;

    @Column(name = "created_at")
    public Instant createdAt;

    @Column(name = "acknowledged", nullable = false)
    public boolean acknowledged;

    @Column(name = "acknowledged_by", length = 100)
    public String acknowledgedBy;

    @Column(name = "acknowledged_at")
    public Instant acknowledgedAt;

    /** 重播錨點（V7；契約 §2.2）：建立當下已處理到的最後一則 Bridge 事件 seq。 */
    @Column(name = "event_seq", nullable = false)
    public int eventSeq;

    /** 同錨點下的子序號（≥1）；0＝Bridge 告警事件的持久化鏡像（SSE 不重播它）。 */
    @Column(name = "event_sub", nullable = false)
    public int eventSub = 1;
}
