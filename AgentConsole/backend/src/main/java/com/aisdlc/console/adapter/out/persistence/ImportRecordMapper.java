package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.domain.model.imports.GateError;
import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.domain.model.imports.ImportSourceType;
import com.aisdlc.console.domain.model.imports.ImportStatus;
import com.aisdlc.console.domain.model.imports.ParsePath;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.infrastructure.persistence.entity.ImportRecordEntity;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.json.JsonMapper;

import java.util.List;

/**
 * ImportRecord（domain）↔ ImportRecordEntity（JPA）的轉換。{@code parsed_result}／{@code last_parse_errors} 是 JSONB：
 * domain 的 {@link ParsedResult}／{@link GateError} 在這一層轉成 JSON 文字（domain 不依賴 JSON 函式庫）。
 */
final class ImportRecordMapper {

    private static final JsonMapper JSON = JsonMapper.builder()
            .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES).build();
    private static final TypeReference<List<GateError>> GATE_ERRORS = new TypeReference<>() { };

    private ImportRecordMapper() {
    }

    static ImportRecordEntity toEntity(ImportRecord r) {
        ImportRecordEntity e = new ImportRecordEntity();
        e.id = r.id();
        e.sourceType = r.sourceType().name();
        e.sourceContent = r.sourceContent();
        e.sourceFileName = r.sourceFileName();
        e.parsedResult = r.parsedResult() == null ? null : JSON.writeValueAsString(r.parsedResult());
        e.projectId = r.projectId();
        e.status = r.status().name();
        e.signedOff = r.signedOff();
        e.signedOffBy = r.signedOffBy();
        e.signedOffAt = r.signedOffAt();
        e.createdAt = r.createdAt();
        e.aiModel = r.aiModel();
        e.tokenUsed = r.tokenUsed();
        e.parsePath = r.parsePath() == null ? null : r.parsePath().name();
        e.lastParseErrors = r.lastParseErrors() == null ? null : JSON.writeValueAsString(r.lastParseErrors());
        return e;
    }

    static ImportRecord toDomain(ImportRecordEntity e) {
        return ImportRecord.restore(e.id, ImportSourceType.valueOf(e.sourceType), e.sourceContent, e.sourceFileName,
                e.parsedResult == null ? null : JSON.readValue(e.parsedResult, ParsedResult.class),
                e.parsePath == null ? null : ParsePath.valueOf(e.parsePath), e.aiModel, e.tokenUsed,
                ImportStatus.valueOf(e.status), e.signedOff, e.signedOffBy, e.signedOffAt, e.projectId, e.createdAt,
                errorsOf(e.lastParseErrors));
    }

    /** 列表投影：不含 {@code source_content}／{@code parsed_result}（大文字欄位不隨列表載入）。 */
    static ImportRecord toSummary(Object[] row) {
        return ImportRecord.restore((java.util.UUID) row[0], ImportSourceType.valueOf((String) row[1]), null,
                (String) row[2], null, row[11] == null ? null : ParsePath.valueOf((String) row[11]),
                (String) row[9], (Long) row[10], ImportStatus.valueOf((String) row[3]), (Boolean) row[4],
                (String) row[5], (java.time.Instant) row[6], (java.util.UUID) row[7], (java.time.Instant) row[8],
                errorsOf((String) row[12]));
    }

    private static List<GateError> errorsOf(String json) {
        return json == null ? null : JSON.readValue(json, GATE_ERRORS);
    }
}
