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
 * {@code parsedResult}（第一次成功解析前為 null；失敗的 parse 不會寫入它，AR-07）＋{@code warnings}（永遠出現）＋
 * {@code parseOptions}（從未 parse 過為 null）。後兩者是 v1.2（C-10）：重開記錄時前端據此還原黃色提示與解析選項。
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
        @Schema(description = "第一次成功解析前為 null；失敗的 parse 不會寫入它") ParsedResultDto parsedResult,
        @NotNull @Schema(description = "最近一次成功的 parse 或 PUT result 的黃色解析提示（與 ParseResultResponse.warnings 同形）；"
                + "沒有就是 []，永遠出現（v1.2，C-10）") List<ParseWarningDto> warnings,
        @Schema(description = "最近一次 parse 請求的選項（進入 PARSING 時寫入，不論成敗）；從未 parse 過為 null（v1.2，C-10）")
        ParseOptionsRequest parseOptions) {

    public static ImportRecordDetailResponse from(ImportRecord r) {
        return new ImportRecordDetailResponse(r.id(), r.sourceType(), r.sourceFileName(), r.status(), r.signedOff(),
                r.signedOffBy(), r.signedOffAt(), r.projectId(), r.createdAt(), r.aiModel(), r.tokenUsed(),
                r.parsePath(), ImportRecordResponse.gateErrors(r), r.sourceContent(),
                r.parsedResult() == null ? null : ParsedResultDto.from(r.parsedResult()),
                r.warnings().stream().map(ParseWarningDto::from).toList(),
                r.parseOptions() == null ? null : ParseOptionsRequest.from(r.parseOptions()));
    }
}
