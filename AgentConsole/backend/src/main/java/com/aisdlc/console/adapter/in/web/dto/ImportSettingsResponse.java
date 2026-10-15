package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SettingsUseCase.ImportResult;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;

/** 匯入設定的結果（契約 §1.5.10）：部分失敗仍是 200，逐筆原因在 {@code errors}。 */
public record ImportSettingsResponse(
        @NotNull int applied,
        @Schema(description = "值未變、或加密佔位值略過的筆數") @NotNull int skipped,
        @NotNull List<ImportSettingsError> errors) {

    /** 單筆失敗。 */
    @Schema(name = "ImportSettingsError")
    public record ImportSettingsError(@NotNull String category, @NotNull String key, @NotNull String reason) {
    }

    public static ImportSettingsResponse from(ImportResult result) {
        return new ImportSettingsResponse(result.applied(), result.skipped(), result.errors().stream()
                .map(e -> new ImportSettingsError(e.category(), e.key(), e.reason())).toList());
    }
}
