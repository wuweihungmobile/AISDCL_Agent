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

/**
 * execution_steps 表（PRD §6.2）的 JPA 映射。整張表由 Engine Bridge 寫入，console 端只讀
 * （Architecture §7.2），故標 {@link Immutable}：Hibernate 不會對它產生 UPDATE。
 * Java 欄位名 {@code occurredAt} 對應資料表的 {@code timestamp} 欄（避開保留字意涵）。
 */
@Entity
@Immutable
@Table(name = "execution_steps")
public class ExecutionStepEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "run_id", nullable = false)
    public UUID runId;

    @Column(name = "task_id", nullable = false)
    public UUID taskId;

    @Column(name = "step_number", nullable = false)
    public Integer stepNumber;

    @Column(name = "action", nullable = false, length = 500)
    public String action;

    @Column(name = "status", nullable = false, length = 20)
    public String status;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "input", columnDefinition = "jsonb")
    public String input;

    @Column(name = "output", columnDefinition = "text")
    public String output;

    @Column(name = "tokens_used")
    public Long tokensUsed;

    @Column(name = "error_message", columnDefinition = "text")
    public String errorMessage;

    @Column(name = "timestamp")
    public Instant occurredAt;
}
