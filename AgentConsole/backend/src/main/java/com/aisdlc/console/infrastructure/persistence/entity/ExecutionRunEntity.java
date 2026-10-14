package com.aisdlc.console.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.UUID;

/**
 * execution_runs 表（PRD §6.2）的 JPA 映射——欄位級寫入分工（Architecture §7.1／ADR-001 D10）：
 * <ul>
 *   <li>console-api 只在「建立」時寫 id／project_id／run_number／autonomy_level／scope／token_budget／dag／started_at，
 *       這些欄位 {@code updatable=false}（建立後 console 不再改）。</li>
 *   <li>Bridge 擁有 status／subprocess_pid／bridge_instance／advisory_lock_key／total_tokens_used／completed_at，
 *       console 端 {@code insertable=false, updatable=false}：INSERT 不帶這些欄位（status 取 DDL 預設 INITIALIZING），
 *       之後只讀，杜絕雙寫漂移（PRD §0.2.2）。</li>
 * </ul>
 * 所有權由 ExecutionRunOwnershipIT 以真 PostgreSQL 驗證。
 */
@Entity
@Table(name = "execution_runs")
public class ExecutionRunEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "project_id", nullable = false, updatable = false)
    public UUID projectId;

    @Column(name = "run_number", nullable = false, updatable = false)
    public Integer runNumber;

    /** Bridge 擁有；DDL 預設 INITIALIZING。 */
    @Column(name = "status", insertable = false, updatable = false, length = 20)
    public String status;

    @Column(name = "autonomy_level", nullable = false, updatable = false)
    public Integer autonomyLevel;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "scope", nullable = false, updatable = false, columnDefinition = "jsonb")
    public String scope;

    /** Bridge 擁有。 */
    @Column(name = "total_tokens_used", insertable = false, updatable = false)
    public Long totalTokensUsed;

    @Column(name = "token_budget", updatable = false)
    public Long tokenBudget;

    /** Bridge 擁有。 */
    @Column(name = "advisory_lock_key", insertable = false, updatable = false)
    public Long advisoryLockKey;

    /** Bridge 擁有。 */
    @Column(name = "subprocess_pid", insertable = false, updatable = false)
    public Integer subprocessPid;

    /** Bridge 擁有。 */
    @Column(name = "bridge_instance", insertable = false, updatable = false, length = 100)
    public String bridgeInstance;

    @Column(name = "started_at", updatable = false)
    public Instant startedAt;

    /** Bridge 擁有。 */
    @Column(name = "completed_at", insertable = false, updatable = false)
    public Instant completedAt;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "dag", updatable = false, columnDefinition = "jsonb")
    public String dag;
}
