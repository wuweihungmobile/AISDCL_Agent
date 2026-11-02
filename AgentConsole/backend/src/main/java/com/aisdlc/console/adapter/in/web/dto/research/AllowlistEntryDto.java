package com.aisdlc.console.adapter.in.web.dto.research;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

/**
 * 研究來源 allowlist 的一個條目（契約 §1.3 {@code AllowlistEntryDto}；API-RP-22）。有效清單＝環境變數基底（{@code source=ENV}，沒有 id、layer、addedBy、addedAt）
 * ∪ 啟用中的 ADMIN 條目（{@code source=ADMIN}）；Bridge 本文是 snake_case，這裡逐欄轉成 camelCase。{@code minIntervalSeconds} 建立時決定、建立後不可改。
 */
@Schema(name = "AllowlistEntryDto", description = "allowlist 條目（ENV 部署基底或 ADMIN 新增；ENV 條目沒有 id 與 layer）")
public record AllowlistEntryDto(
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "條目 id（UUID）；ENV 基底條目為 null") String id,
        @NotNull @Schema(description = "FETCH｜WEB") String listKind,
        @NotNull String host,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "ACADEMIC｜INDUSTRY｜OSS｜COMMUNITY；ENV 基底條目為 null") String layer,
        @NotNull String purpose,
        @NotNull String tosNote,
        @NotNull @Schema(description = "實際間隔＝max(Bridge 內建下限, 本值)；建立後不可改") int minIntervalSeconds,
        @NotNull boolean enabled,
        @NotNull boolean tosAcknowledged,
        @NotNull @Schema(description = "ENV｜ADMIN") String source,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String addedBy,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String addedAt) {

    public static AllowlistEntryDto from(Map<String, Object> entry) {
        Integer interval = Iso.integer(entry.get("min_interval_seconds"));
        return new AllowlistEntryDto(Iso.text(entry.get("id")), Iso.text(entry.get("list_kind"), ""), Iso.text(entry.get("host"), ""),
                Iso.text(entry.get("layer")), Iso.text(entry.get("purpose"), ""), Iso.text(entry.get("tos_note"), ""),
                interval == null ? 0 : interval, !Boolean.FALSE.equals(entry.get("enabled")), Iso.flag(entry.get("tos_acknowledged")),
                Iso.text(entry.get("source"), "ADMIN"), Iso.text(entry.get("added_by")), Iso.text(entry.get("added_at")));
    }
}
