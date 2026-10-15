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
 * import_records 表（PRD §6.2）的 JPA 映射（Phase 3 匯入）。{@code parse_path}／{@code last_parse_errors} 為 V5 增補
 * （契約 §0.5、AR-07）：{@code parsed_result} 在第一次成功解析前為 NULL，失敗的 parse 不寫它。
 */
@Entity
@Table(name = "import_records")
public class ImportRecordEntity {

    @Id
    @Column(name = "id", nullable = false, updatable = false)
    public UUID id;

    @Column(name = "source_type", nullable = false, length = 20)
    public String sourceType;

    @Column(name = "source_content", nullable = false, columnDefinition = "text")
    public String sourceContent;

    @Column(name = "source_file_name", length = 500)
    public String sourceFileName;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "parsed_result", columnDefinition = "jsonb")
    public String parsedResult;

    @Column(name = "project_id")
    public UUID projectId;

    @Column(name = "status", nullable = false, length = 20)
    public String status;

    @Column(name = "signed_off", nullable = false)
    public boolean signedOff;

    @Column(name = "signed_off_by", length = 100)
    public String signedOffBy;

    @Column(name = "signed_off_at")
    public Instant signedOffAt;

    @Column(name = "created_at")
    public Instant createdAt;

    @Column(name = "ai_model", length = 100)
    public String aiModel;

    @Column(name = "token_used")
    public Long tokenUsed;

    /** SDD／LLM／DECOMPOSE；第一次成功解析後才有值。 */
    @Column(name = "parse_path", length = 20)
    public String parsePath;

    /** GateError 陣列（JSON 文字）；僅「被有界閘拒絕」時寫入，成功解析後清為 NULL。 */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "last_parse_errors", columnDefinition = "jsonb")
    public String lastParseErrors;
}
