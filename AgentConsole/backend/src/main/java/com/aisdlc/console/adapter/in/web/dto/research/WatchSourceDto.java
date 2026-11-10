package com.aisdlc.console.adapter.in.web.dto.research;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

/**
 * 一筆追蹤來源（契約 §5A.2 {@code WatchSourceDto}；API-RP-29）：Bridge 本文是 snake_case，這裡逐欄轉成 camelCase。時間一律 UTC、秒精度（{@code +00:00}）。
 * {@code hostAllowed}＝網域仍在當前有效網域清單（停用網域後追蹤來源列不動，只是 {@code hostAllowed} 轉假）。
 */
@Schema(name = "WatchSourceDto", description = "自我進化追蹤來源（研究來源設定的第二層：網址層；slug 永不重用、只增不刪）")
public record WatchSourceDto(
        @NotNull @Schema(description = "識別碼（小寫英數與連字號，1～32 字）") String slug,
        @NotNull @Schema(description = "https 網址（小寫 host、無埠與 IP 字面與片段）") String url,
        @NotNull @Schema(description = "網址的主機名（由 url 衍生）") String host,
        @NotNull @Schema(description = "changelog｜docs｜release｜blog｜sitemap｜search") String kind,
        @NotNull @Schema(description = "要抓取並逐字保留的內容說明（1～200 字）") String extract,
        @NotNull @Schema(description = "ACADEMIC｜INDUSTRY｜OSS｜COMMUNITY") String layer,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "展開設定；沒有展開為 null") Expand expand,
        @NotNull boolean enabled,
        @NotNull @Schema(description = "host 是否仍在當前有效網域清單（FETCH 或 WEB；只計啟用者）") boolean hostAllowed,
        @NotNull String addedBy,
        @NotNull String addedAt,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String disabledBy,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String disabledAt) {

    /** 展開設定：{@code mode}＝links｜sitemap、{@code prefix} 以 / 起頭、{@code max} 1～3。 */
    @Schema(name = "WatchSourceExpand")
    public record Expand(@NotNull String mode, @NotNull String prefix, @NotNull int max) {
    }

    public static WatchSourceDto from(Map<String, Object> source) {
        Map<String, Object> expand = Iso.map(source.get("expand"));
        Integer max = Iso.integer(expand.get("max"));
        Expand shown = expand.isEmpty() ? null : new Expand(Iso.text(expand.get("mode"), ""), Iso.text(expand.get("prefix"), ""), max == null ? 0 : max);
        return new WatchSourceDto(Iso.text(source.get("slug"), ""), Iso.text(source.get("url"), ""), Iso.text(source.get("host"), ""),
                Iso.text(source.get("kind"), ""), Iso.text(source.get("extract"), ""), Iso.text(source.get("layer"), ""), shown,
                Iso.flag(source.get("enabled")), Iso.flag(source.get("host_allowed")), Iso.text(source.get("added_by"), ""),
                Iso.text(source.get("added_at"), ""), Iso.text(source.get("disabled_by")), Iso.text(source.get("disabled_at")));
    }
}
