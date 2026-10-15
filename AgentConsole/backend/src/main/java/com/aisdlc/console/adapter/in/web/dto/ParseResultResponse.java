package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ImportUseCase.ParseOutcome;
import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.domain.model.imports.ImportStatus;
import com.aisdlc.console.domain.model.imports.ParsePath;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;
import java.util.UUID;

/**
 * parse／editResult 成功的回應（契約 §3.3.6）。<b>有界閘違規不走這裡</b>（422 {@code ApiError}），所以成功時
 * {@code errors} 恆為空陣列；欄位保留以維持主控裁決的形狀（契約 §6 D-04）。
 */
public record ParseResultResponse(
        @NotNull UUID importId,
        @NotNull ImportStatus status,
        @NotNull ParsePath path,
        @NotNull ParsedResultDto parsedResult,
        @Schema(description = "parse 成功時恆為 false；editResult 後為 false（編輯撤銷 signoff）") @NotNull boolean signedOff,
        String aiModel,
        Long tokenUsed,
        String reasoning,
        @NotNull List<GateErrorDto> errors,
        @NotNull List<ParseWarningDto> warnings) {

    public static ParseResultResponse from(ParseOutcome outcome) {
        ImportRecord r = outcome.record();
        return new ParseResultResponse(r.id(), r.status(), r.parsePath(), ParsedResultDto.from(r.parsedResult()),
                r.signedOff(), r.aiModel(), r.tokenUsed(), r.parsedResult().reasoning(), List.of(),
                outcome.warnings().stream().map(ParseWarningDto::from).toList());
    }
}
