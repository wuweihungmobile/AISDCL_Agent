package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.domain.model.imports.ImportSourceType;
import com.aisdlc.console.domain.model.imports.ImportStatus;
import com.aisdlc.console.domain.model.imports.ParsePath;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 匯入記錄回應（契約 §1.1；列表與 upload／text／signoff／reject 共用，不含 {@code sourceContent}／{@code parsedResult}——
 * 詳情見 {@link ImportRecordDetailResponse}）。
 *
 * @param parsePath       採用的解析路徑；第一次成功解析前為 null（缺席）
 * @param lastParseErrors 最近一次 parse 被有界閘拒絕的原因；成功解析後清空
 */
public record ImportRecordResponse(
        @NotNull UUID id,
        @NotNull ImportSourceType sourceType,
        String sourceFileName,
        @NotNull ImportStatus status,
        @NotNull boolean signedOff,
        String signedOffBy,
        Instant signedOffAt,
        UUID projectId,
        @NotNull Instant createdAt,
        String aiModel,
        Long tokenUsed,
        ParsePath parsePath,
        List<GateErrorDto> lastParseErrors) {

    public static ImportRecordResponse from(ImportRecord r) {
        return new ImportRecordResponse(r.id(), r.sourceType(), r.sourceFileName(), r.status(), r.signedOff(),
                r.signedOffBy(), r.signedOffAt(), r.projectId(), r.createdAt(), r.aiModel(), r.tokenUsed(),
                r.parsePath(), gateErrors(r));
    }

    /** domain 的閘違規 → API 形狀；沒有違規（成功解析過、或從未被閘拒絕）為 null。 */
    static List<GateErrorDto> gateErrors(ImportRecord r) {
        return r.lastParseErrors() == null ? null : r.lastParseErrors().stream().map(GateErrorDto::from).toList();
    }
}
