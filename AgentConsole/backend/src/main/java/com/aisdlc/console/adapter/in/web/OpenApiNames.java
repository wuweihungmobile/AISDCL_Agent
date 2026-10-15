package com.aisdlc.console.adapter.in.web;

/**
 * OpenAPI 安全機制名稱（{@code @SecurityRequirement} 要編譯期常數）。與 {@code infrastructure.config.OpenApiConfig} 宣告的
 * {@code components.securitySchemes} 鍵逐字一致（adapter.in 不得依賴 infrastructure，所以各持一份字面；
 * {@code OpenApiIT} 驗證兩者對得上）。
 */
final class OpenApiNames {

    /** HTTP Bearer JWT（全域預設）。 */
    static final String BEARER = "bearerAuth";
    /** {@code ?access_token=}：只有 {@code /api/v1/stream/**} 接受（EventSource 不能帶標頭）。 */
    static final String QUERY_TOKEN = "queryAccessToken";

    private OpenApiNames() {
    }
}
