package com.aisdlc.console.infrastructure.persistence.entity;

import com.aisdlc.console.domain.model.task.TaskStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.UUID;

/** tasks 表（PRD §6.2）的 JPA 映射；passCriteriaSpec 以 JSON 文字存進 jsonb 欄。 */
@Entity
@Table(name = "tasks")
public class TaskEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "goal_id", nullable = false, updatable = false)
    public UUID goalId;

    @Column(name = "name", nullable = false, length = 200)
    public String name;

    @Column(name = "description", columnDefinition = "text")
    public String description;

    @Column(name = "pass_criteria", nullable = false, columnDefinition = "text")
    public String passCriteria;

    @Column(name = "evaluator_command", length = 1000)
    public String evaluatorCommand;

    @Column(name = "expected_output_regex", length = 1000)
    public String expectedOutputRegex;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "pass_criteria_spec", columnDefinition = "jsonb")
    public String passCriteriaSpec;

    @Column(name = "sort_order")
    public Integer sortOrder;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    public TaskStatus status;

    @Column(name = "estimated_tokens")
    public Long estimatedTokens;

    @Column(name = "actual_tokens")
    public Long actualTokens;

    @Column(name = "retry_count")
    public Integer retryCount;

    @Column(name = "max_retries")
    public Integer maxRetries;

    @Column(name = "assigned_agent", length = 100)
    public String assignedAgent;

    @Column(name = "execution_log", columnDefinition = "text")
    public String executionLog;

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

    @Column(name = "started_at")
    public Instant startedAt;

    @Column(name = "completed_at")
    public Instant completedAt;

    /** V9（C-3）：軟刪除當下的時間；隨專案一起軟刪者與專案的 deleted_at 相同（復原據此辨識）。未刪除為 NULL。 */
    @Column(name = "deleted_at")
    public Instant deletedAt;
}
