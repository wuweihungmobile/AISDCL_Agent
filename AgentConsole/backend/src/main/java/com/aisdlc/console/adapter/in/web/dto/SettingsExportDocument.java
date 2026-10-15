package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SettingsUseCase.ExportedSettings;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;

/**
 * 設定匯出檔（契約 §1.5.9）：<b>不包 ApiResult</b>，直接回 {@code application/json} 檔。全部 50 個鍵都輸出；
 * 加密參數的 {@code value} 固定為佔位字串 {@code <encrypted>}（匯入時略過，所以匯出檔與匯入檔同形狀、可往返）。
 */
public record SettingsExportDocument(
        @NotNull @Schema(description = "固定為 1；匯入時 version≠1 回 400") int version,
        @NotNull Instant exportedAt,
        @NotNull List<ExportedConfig> configs) {

    /** 一個鍵。 */
    @Schema(name = "ExportedConfig")
    public record ExportedConfig(@NotNull String category, @NotNull String key,
                                 @Schema(description = "加密參數固定為 <encrypted>") @NotNull String value) {
    }

    public static SettingsExportDocument from(ExportedSettings exported) {
        return new SettingsExportDocument(exported.version(), exported.exportedAt(), exported.configs().stream()
                .map(i -> new ExportedConfig(i.category(), i.key(), i.value())).toList());
    }
}
