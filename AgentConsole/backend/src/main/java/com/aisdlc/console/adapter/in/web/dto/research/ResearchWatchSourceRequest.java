package com.aisdlc.console.adapter.in.web.dto.research;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 新增追蹤來源的請求本文（API-RP-29）。<b>只供 OpenAPI 說明用</b>：端點以開放物件接收本文，使「本文含未知鍵（含 addedBy）」能被輸入閘逐筆回報（400 unknown_field），
 * 而不是被序列化器默默忽略；操作人一律取 JWT subject，所以這裡沒有 addedBy。
 */
@Schema(name = "ResearchWatchSourceRequest", description = "新增追蹤來源；操作人取 JWT subject，本文沒有 addedBy")
public record ResearchWatchSourceRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "^[a-z0-9][a-z0-9-]{0,31}$；永不重用") String slug,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "https 網址；小寫 host、無埠與 userinfo 與 IP 字面與片段；≤500 字元；原樣判定、不正規化") String url,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"changelog", "docs", "release", "blog", "sitemap", "search"}) String kind,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "1～200 字、無控制字元") String extract,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY"}) String layer,
        @Schema(nullable = true, description = "缺省或 null＝無展開；物件須恰含 mode、prefix、max") WatchSourceDto.Expand expand) {
}
