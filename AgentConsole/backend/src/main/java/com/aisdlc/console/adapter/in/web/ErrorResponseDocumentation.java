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
 * <p>規則（與實作一致，由 OpenApiIT 驗證）：400＝有輸入的端點（路徑／查詢參數或請求本文：驗證、格式錯誤；
 * 沒有任何輸入的端點——例如 {@code GET /notifications/summary}、{@code POST /settings/export}——不可能回 400，不列）；
 * 401＝所有端點（登入端點是帳密錯誤）；
 * 403＝需登入的寫入端點（VIEWER 唯讀）與可能帶 {@code reveal=true} 的設定讀取；404＝路徑含 id 或 reorder（專案不存在）；
 * 409＝有狀態規則的端點；429＝所有 {@code /api/**} 端點（限流，契約 §0.4 第 4 點）；
 * 413／415／422／502／504 各依端點的契約列出（{@link #EXTRA}）。
 */
@Configuration(proxyBeanMethods = false)
public class ErrorResponseDocumentation {

    private static final String ERROR_REF = "#/components/schemas/ApiError";

    /** 有狀態規則、會回 409 的端點（方法＋路徑）。 */
    private static final Set<String> CONFLICT_ENDPOINTS = Set.of(
            "PUT /api/v1/projects/{id}", "DELETE /api/v1/projects/{id}", "POST /api/v1/projects/{id}/signoff",
            "DELETE /api/v1/goals/{id}", "POST /api/v1/goals/{id}/signoff",
            "DELETE /api/v1/tasks/{id}", "POST /api/v1/tasks/{id}/retry", "POST /api/v1/tasks/{id}/signoff",
            // Phase 3 匯入：狀態不允許、已 signoff、草案失效、未 signoff 即 confirm…
            "POST /api/v1/import/{id}/parse", "PUT /api/v1/import/{id}/result", "POST /api/v1/import/{id}/signoff",
            "POST /api/v1/import/{id}/confirm", "POST /api/v1/import/{id}/reject",
            // Phase 6 設定：敏感參數未帶 confirm=true
            "PUT /api/v1/settings/{category}/{key}", "POST /api/v1/settings/{category}/{key}/reset",
            // Phase 4 執行：草案未 signoff、專案／批次狀態不允許、鎖被占用、審核項已處理…
            "POST /api/v1/projects/{projectId}/execute", "POST /api/v1/executions/{runId}/pause",
            "POST /api/v1/executions/{runId}/resume", "POST /api/v1/executions/{runId}/cancel",
            "POST /api/v1/executions/{runId}/restore/{checkpointId}",
            "POST /api/v1/executions/{runId}/review/{stepId}");

    /** pause／resume／cancel 的上游錯誤：Bridge 無法連線、逾時（DB 狀態不變）。 */
    private static final Map<String, String> BRIDGE_UPSTREAM = Map.of(
            "502", "引擎橋接服務無法連線／回了非預期的錯誤（DB 狀態不變）",
            "504", "引擎橋接服務逾時（DB 狀態不變）");

    /** 其餘（非 400／401／403／404／409／429）的狀態碼：方法＋路徑 → 狀態碼與說明。 */
    private static final Map<String, Map<String, String>> EXTRA = Map.ofEntries(
            Map.entry("POST /api/v1/import/upload", Map.of(
                    "413", "上傳超過 10MB 上限（reason：檔案超過 10MB 上限）",
                    "415", "副檔名不在 .md／.pdf／.docx（reason：只支援 .md／.pdf／.docx 檔案）",
                    "422", "檔案內容與副檔名不符、非 UTF-8、PDF 已加密、檔案已損毀、無法擷取文字")),
            Map.entry("POST /api/v1/import/{id}/parse", Map.of(
                    "422", "未通過有界閘（reason：解析結果未通過有界閘，errors[] 帶 gate／detail／location）或 SDD 規格被拒",
                    "502", "引擎橋接服務無法連線／回了非預期的錯誤",
                    "504", "引擎橋接服務逾時")),
            Map.entry("PUT /api/v1/import/{id}/result", Map.of(
                    "422", "未通過有界閘（任務 name／description 為空白字串＝empty_prompt）")),
            Map.entry("POST /api/v1/import/{id}/signoff", Map.of(
                    "502", "Bridge 無法連線／批准草案時回了非預期的錯誤（不改任何狀態）",
                    "504", "引擎橋接服務逾時")),
            Map.entry("POST /api/v1/settings/import", Map.of(
                    "413", "設定檔超過 1MB 上限",
                    "415", "只接受 JSON 設定檔")),
            Map.entry("POST /api/v1/settings/test-connection", Map.of(
                    "422", "目標位址未通過 SSRF／allowlist 檢查（未發出任何連線）")),
            // Phase 4 執行：物化失敗（prompt 超過上限、評估指令、regex、任務數）與 Bridge 的 409／422／502／504
            Map.entry("POST /api/v1/projects/{projectId}/execute", Map.of(
                    "422", "物化失敗（步驟 prompt 超過 20000 字元、評估指令禁用字元／不在白名單、regex 無法編譯、範圍任務數超過 500、"
                            + "任務 maxRetries 超過 20）或 Bridge 拒絕（reason：引擎拒絕此請求）",
                    "502", "引擎橋接服務無法連線／回了非預期的錯誤（剛建的 run 列已補償刪除）",
                    "504", "引擎橋接服務逾時（剛建的 run 列已補償刪除）")),
            Map.entry("POST /api/v1/executions/{runId}/pause", BRIDGE_UPSTREAM),
            Map.entry("POST /api/v1/executions/{runId}/resume", BRIDGE_UPSTREAM),
            Map.entry("POST /api/v1/executions/{runId}/cancel", BRIDGE_UPSTREAM),
            Map.entry("POST /api/v1/executions/{runId}/restore/{checkpointId}", Map.of(
                    "422", "Bridge 拒絕（execution_path 重驗失敗；reason：引擎拒絕此請求）",
                    "502", "引擎橋接服務無法連線／回了非預期的錯誤（DB 狀態不變）",
                    "504", "引擎橋接服務逾時（DB 狀態不變）")),
            Map.entry("POST /api/v1/executions/{runId}/review/{stepId}", Map.of(
                    "422", "SKIP／RETRY 開後續批次或 restore 時 Bridge 拒絕（reason：引擎拒絕此請求）",
                    "502", "引擎橋接服務無法連線／回了非預期的錯誤（審核項維持 PENDING）",
                    "504", "引擎橋接服務逾時（審核項維持 PENDING）")),
            // Phase 5 監控：PDF 報表 W5 才提供
            Map.entry("GET /api/v1/monitor/projects/{projectId}/report", Map.of(
                    "501", "PDF 報表尚未提供（W5）；format=csv 為必做")));

    /** 讀取端點中，會因 {@code reveal=true} 而回 403 的路徑（GET 預設不列 403）。 */
    private static final Set<String> REVEAL_ENDPOINTS = Set.of("GET /api/v1/settings", "GET /api/v1/settings/{category}");

    @Bean
    OpenApiCustomizer errorEnvelopeCustomizer() {
        return openApi -> {
            Map<String, Schema> schemas = ModelConverters.getInstance(true).readAll(ApiError.class);
            schemas.forEach((name, schema) -> openApi.getComponents().addSchemas(name, schema));
            openApi.getPaths().forEach((path, item) -> item.readOperationsMap().forEach((method, operation) -> {
                String key = method + " " + path;
                boolean isPublic = operation.getSecurity() != null && operation.getSecurity().isEmpty();
                boolean isRead = method == PathItem.HttpMethod.GET;
                boolean hasInput = (operation.getParameters() != null && !operation.getParameters().isEmpty())
                        || operation.getRequestBody() != null;
                if (hasInput) {
                    add(operation, "400", "請求格式或欄位驗證失敗（errors 列出每個欄位的問題）");
                }
                add(operation, "401", isPublic ? "帳號密碼錯誤，或 refresh token 無效／過期" : "未登入，或 access token 無效／過期");
                if ((!isPublic && !isRead) || REVEAL_ENDPOINTS.contains(key)) {
                    add(operation, "403", "角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN）");
                }
                if (path.contains("{") || path.endsWith("/reorder")) {
                    add(operation, "404", "資源不存在或已軟刪除");
                }
                if (CONFLICT_ENDPOINTS.contains(key)) {
                    add(operation, "409", "與目前狀態衝突（reason 說明原因）");
                }
                if (path.startsWith("/api/")) {
                    add(operation, "429", "超過每分鐘 100 次請求上限（reason：超過每分鐘 100 次請求上限；帶 Retry-After）");
                }
                EXTRA.getOrDefault(key, Map.of()).forEach((code, description) -> add(operation, code, description));
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
