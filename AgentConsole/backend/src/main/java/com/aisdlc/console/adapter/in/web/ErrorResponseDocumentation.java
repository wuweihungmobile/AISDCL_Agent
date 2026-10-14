package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiError;
import io.swagger.v3.core.converter.ModelConverters;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.PathItem;
import io.swagger.v3.oas.models.media.Content;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.responses.ApiResponse;
import org.springdoc.core.customizers.OpenApiCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Map;
import java.util.Set;

/**
 * 把統一錯誤封包 {@link ApiError}（PRD §7.2；API-FMT-03）寫進 OpenAPI 文件：註冊 schema，並替每個端點補上
 * 它「實際會回」的錯誤狀態碼——前端以 /v3/api-docs 產生型別時，錯誤回應也有型別可用。
 *
 * <p>規則（與實作一致，由 OpenApiIT 驗證）：400＝所有端點（驗證、格式錯誤）；401＝所有端點（登入端點是帳密錯誤）；
 * 403＝需登入的寫入端點（VIEWER 唯讀）；404＝路徑含 id 或 reorder（專案不存在）；409＝有狀態規則的端點。
 */
@Configuration(proxyBeanMethods = false)
public class ErrorResponseDocumentation {

    private static final String ERROR_REF = "#/components/schemas/ApiError";

    /** 有狀態規則、會回 409 的端點（方法＋路徑）。 */
    private static final Set<String> CONFLICT_ENDPOINTS = Set.of(
            "PUT /api/v1/projects/{id}", "DELETE /api/v1/projects/{id}", "POST /api/v1/projects/{id}/signoff",
            "DELETE /api/v1/goals/{id}", "POST /api/v1/goals/{id}/signoff",
            "DELETE /api/v1/tasks/{id}", "POST /api/v1/tasks/{id}/retry", "POST /api/v1/tasks/{id}/signoff");

    @Bean
    OpenApiCustomizer errorEnvelopeCustomizer() {
        return openApi -> {
            Map<String, Schema> schemas = ModelConverters.getInstance(true).readAll(ApiError.class);
            schemas.forEach((name, schema) -> openApi.getComponents().addSchemas(name, schema));
            openApi.getPaths().forEach((path, item) -> item.readOperationsMap().forEach((method, operation) -> {
                boolean isPublic = operation.getSecurity() != null && operation.getSecurity().isEmpty();
                boolean isRead = method == PathItem.HttpMethod.GET;
                add(operation, "400", "請求格式或欄位驗證失敗（errors 列出每個欄位的問題）");
                add(operation, "401", isPublic ? "帳號密碼錯誤，或 refresh token 無效／過期" : "未登入，或 access token 無效／過期");
                if (!isPublic && !isRead) {
                    add(operation, "403", "角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN）");
                }
                if (path.contains("{") || path.endsWith("/reorder")) {
                    add(operation, "404", "資源不存在或已軟刪除");
                }
                if (CONFLICT_ENDPOINTS.contains(method + " " + path)) {
                    add(operation, "409", "與目前狀態衝突（reason 說明原因）");
                }
            }));
        };
    }

    private static void add(Operation operation, String code, String description) {
        if (operation.getResponses().containsKey(code)) {
            return;
        }
        operation.getResponses().addApiResponse(code, new ApiResponse().description(description)
                .content(new Content().addMediaType("application/json",
                        new MediaType().schema(new Schema<>().$ref(ERROR_REF)))));
    }
}
