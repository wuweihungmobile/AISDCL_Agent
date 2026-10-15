package com.aisdlc.console.infrastructure.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * OpenAPI 文件（NFR-9.4-03）：宣告 Bearer JWT 安全機制；{@code /v3/api-docs} 與 {@code /swagger-ui} 免認證。
 * 另宣告 {@code queryAccessToken}：只有 {@code /api/v1/stream/**} 接受 {@code ?access_token=}（EventSource 不能帶標頭；契約 §2.1）。
 */
@Configuration(proxyBeanMethods = false)
public class OpenApiConfig {

    static final String BEARER_SCHEME = "bearerAuth";
    static final String QUERY_TOKEN_SCHEME = "queryAccessToken";

    @Bean
    OpenAPI consoleOpenApi() {
        return new OpenAPI()
                .info(new Info()
                        .title("AISDLC Agent Console — console-api")
                        .version("v1")
                        .description("專案／目標／任務管理、人工 signoff 硬閘、BRD/PRD 匯入、專案執行與監控、系統參數與認證。"
                                + "所有成功回應包 {code,message,data,timestamp,traceId}，錯誤回應含 errors[]，"
                                + "分頁資料在 data 內（content/page/size/totalElements/totalPages）。"))
                .components(new Components()
                        .addSecuritySchemes(BEARER_SCHEME, new SecurityScheme()
                                .type(SecurityScheme.Type.HTTP)
                                .scheme("bearer")
                                .bearerFormat("JWT"))
                        .addSecuritySchemes(QUERY_TOKEN_SCHEME, new SecurityScheme()
                                .type(SecurityScheme.Type.APIKEY)
                                .in(SecurityScheme.In.QUERY)
                                .name("access_token")
                                .description("只有 /api/v1/stream/** 接受（EventSource 不能帶標頭）；必須是 access token"
                                        + "（refresh token 一律 401）。後端任何存取日誌不得輸出含 access_token 的 query string，"
                                        + "nginx 的 log_format 須遮罩此參數（契約 §0.7）")))
                .addSecurityItem(new SecurityRequirement().addList(BEARER_SCHEME));
    }
}
