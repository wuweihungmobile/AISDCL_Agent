package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.signoff.PendingSignoffs;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;

/** {@code GET /api/v1/signoffs/pending} 的 {@code data}（契約 §1.8.1；D-18）。 */
@Schema(name = "PendingSignoffsResponse", description = "GET /api/v1/signoffs/pending 的 data（v1.4，D-18；Markdown 契約 §1.8.1）")
public record PendingSignoffsResponse(
        @NotNull PendingSignoffCountsDto counts,
        @NotNull @ArraySchema(maxItems = 200, arraySchema = @Schema(description = "依 createdAt 升冪；最多 limit 筆（預設 50、上限 200）"))
        List<PendingSignoffItemDto> items) {

    public static PendingSignoffsResponse from(PendingSignoffs pending) {
        return new PendingSignoffsResponse(PendingSignoffCountsDto.from(pending.counts()),
                pending.items().stream().map(PendingSignoffItemDto::from).toList());
    }
}
