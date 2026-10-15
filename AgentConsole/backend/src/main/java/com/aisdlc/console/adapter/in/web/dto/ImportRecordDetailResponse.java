package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.domain.model.imports.ImportSourceType;
import com.aisdlc.console.domain.model.imports.ImportStatus;
import com.aisdlc.console.domain.model.imports.ParsePath;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 匯入記錄詳情（契約 §1.1.9）：{@link ImportRecordResponse} 的全部欄位＋{@code sourceContent}（原文）＋
 * {@code parsedResult}（第一次成功解析前為 null；失敗的 parse 不會寫入它，AR-07）。
 */
public record ImportRecordDetailResponse(
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
        List<GateErrorDto> lastParseErrors,
        @NotNull String sourceContent,
        @Schema(description = "第一次成功解析前為 null；失敗的 parse 不會寫入它") ParsedResultDto parsedResult) {

    public static ImportRecordDetailResponse from(ImportRecord r) {
        return new ImportRecordDetailResponse(r.id(), r.sourceType(), r.sourceFileName(), r.status(), r.signedOff(),
                r.signedOffBy(), r.signedOffAt(), r.projectId(), r.createdAt(), r.aiModel(), r.tokenUsed(),
                r.parsePath(), ImportRecordResponse.gateErrors(r), r.sourceContent(),
                r.parsedResult() == null ? null : ParsedResultDto.from(r.parsedResult()));
    }
}
