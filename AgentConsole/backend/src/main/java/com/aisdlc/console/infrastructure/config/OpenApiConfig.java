package com.aisdlc.console.infrastructure.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** OpenAPI 文件（NFR-9.4-03）：宣告 Bearer JWT 安全機制；{@code /v3/api-docs} 與 {@code /swagger-ui} 免認證。 */
@Configuration(proxyBeanMethods = false)
public class OpenApiConfig {

    static final String BEARER_SCHEME = "bearerAuth";

    @Bean
    OpenAPI consoleOpenApi() {
        return new OpenAPI()
                .info(new Info()
                        .title("AISDLC Agent Console — console-api")
                        .version("v1")
                        .description("專案／目標／任務管理、人工 signoff 硬閘與認證。"
                                + "所有成功回應包 {code,message,data,timestamp,traceId}，錯誤回應含 errors[]，"
                                + "分頁資料在 data 內（content/page/size/totalElements/totalPages）。"))
                .components(new Components().addSecuritySchemes(BEARER_SCHEME, new SecurityScheme()
                        .type(SecurityScheme.Type.HTTP)
                        .scheme("bearer")
                        .bearerFormat("JWT")))
                .addSecurityItem(new SecurityRequirement().addList(BEARER_SCHEME));
    }
}
