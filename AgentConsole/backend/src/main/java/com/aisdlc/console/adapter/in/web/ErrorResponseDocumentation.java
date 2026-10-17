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
 * 413／415／422／502／504 各依端點的契約列出（{@link #EXTRA}）。{@code GET /projects} 另有 403：{@code deleted=true}（已刪除專案清單）
 * 只准 OPERATOR 以上（{@link #ROLE_GATED_READ_ENDPOINTS}，契約 §1.6.2）。
 */
@Configuration(proxyBeanMethods = false)
public class ErrorResponseDocumentation {

    private static final String ERROR_REF = "#/components/schemas/ApiError";

    /** 有狀態規則、會回 409 的端點（方法＋路徑）。 */
    private static final Set<String> CONFLICT_ENDPOINTS = Set.of(
            "PUT /api/v1/projects/{id}", "DELETE /api/v1/projects/{id}", "POST /api/v1/projects/{id}/signoff",
            // v1.2（C-3）：復原只在專案已被軟刪除、且仍在保留期內才成立（project_not_deleted／restore_window_expired）
            "POST /api/v1/projects/{id}/restore",
            "DELETE /api/v1/goals/{id}", "POST /api/v1/goals/{id}/signoff",
            "DELETE /api/v1/tasks/{id}", "POST /api/v1/tasks/{id}/retry", "POST /api/v1/tasks/{id}/signoff",
            // Phase 3 匯入：狀態不允許、已 signoff、草案失效、未 signoff 即 confirm…
            "POST /api/v1/import/{id}/parse", "PUT /api/v1/import/{id}/result", "POST /api/v1/import/{id}/signoff",
            "POST /api/v1/import/{id}/confirm", "POST /api/v1/import/{id}/reject",
            // Phase 6 設定：敏感參數未帶 confirm=true
            "PUT /api/v1/settings/{category}/{key}", "POST /api/v1/settings/{category}/{key}/reset",
            // Phase 4 執行：草案未 signoff、專案／批次狀態不允許、鎖被占用、審核項已處理…
            // v1.5：核准凍結（FSM 不在 HUMAN_PENDING、沒有狀態檔、摘要不符、綁定衝突）與編輯綁定（唯一性）
            "POST /api/v1/projects/{id}/sdd/freeze", "PUT /api/v1/projects/{id}/sdd-binding",
            "POST /api/v1/projects/{projectId}/execute", "POST /api/v1/executions/{runId}/pause",
            "POST /api/v1/executions/{runId}/resume", "POST /api/v1/executions/{runId}/cancel",
            "POST /api/v1/executions/{runId}/restore/{checkpointId}",
            "POST /api/v1/executions/{runId}/review/{stepId}");

    /** 404 的說明有端點專屬版本時的覆寫（預設是「資源不存在或已軟刪除」）。 */
    private static final Map<String, String> NOT_FOUND_DESCRIPTION = Map.of(
            // v1.5（契約 §1.10.3）：本端點是「404 的 reason 省略」慣例的唯一例外
            "GET /api/v1/executions/{runId}/rtm", "批次不存在（訊息「執行批次不存在或已刪除：<id>」，無 reason），或批次存在但沒有追溯報告"
                    + "（reason rtm_not_found；本端點是「404 的 reason 省略」慣例的唯一例外）");

    /** pause／resume／cancel 的上游錯誤：Bridge 無法連線、逾時（DB 狀態不變）。 */
    private static final Map<String, String> BRIDGE_UPSTREAM = Map.of(
            "502", "引擎橋接服務無法連線／回了非預期的錯誤（DB 狀態不變）",
            "504", "引擎橋接服務逾時（DB 狀態不變）");

    /** 其餘（非 400／401／403／404／409／429）的狀態碼：方法＋路徑 → 狀態碼與說明。 */
    private static final Map<String, Map<String, String>> EXTRA = Map.ofEntries(
            // v1.5（契約 §1.10.4）：端點沒有路徑變數，但選填的 projectId 找不到專案時回 404（訊息「專案不存在或已刪除：<id>」，無 reason）
            Map.entry("GET /api/v1/engines/sdd", Map.of(
                    "404", "projectId 找不到（專案不存在或已軟刪除；訊息「專案不存在或已刪除：<id>」，無 reason）")),
            // v1.5（契約 §1.10.2）：核准凍結的 Bridge 失敗對映——422 引擎拒絕、502 含 403 sdd_write_forbidden、503 sdd_write_disabled
            Map.entry("POST /api/v1/projects/{id}/sdd/freeze", Map.of(
                    "422", "引擎拒絕此請求（details.bridgeReason 為 sanitization_failed／sdd_invalid_argument／fsm_state_unreadable；"
                            + "docs 不合法、缺檔、跑出根目錄、不含 TCS，或 approver／reason 值域不合）",
                    "502", "引擎橋接服務無法連線／回了非預期的錯誤（含 403 sdd_write_forbidden＝兩端權杖設定不一致；已寫回的綁定不回滾）",
                    "503", "sdd_write_disabled：backend 或 Bridge 沒有設定寫入權杖（BRIDGE_SDD_WRITE_TOKEN），SDD 寫入面停用",
                    "504", "引擎橋接服務逾時")),
            // v1.5（契約 §1.10.3）：RTM 報告壞掉（422 rtm_unreadable）與 Bridge 失敗
            Map.entry("GET /api/v1/executions/{runId}/rtm", Map.of(
                    "422", "報告檔存在但壞掉（引擎拒絕此請求；details.bridgeReason=rtm_unreadable）",
                    "502", "引擎橋接服務無法連線／回了非預期的錯誤",
                    "504", "引擎橋接服務逾時")),
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
                    "504", "引擎橋接服務逾時（審核項維持 PENDING）")));

    /**
     * 讀取端點中，會因查詢參數而有角色限制、回 403 的路徑（GET 預設不列 403）：{@code reveal=true}（僅 ADMIN）與
     * {@code GET /projects?deleted=true}（OPERATOR 以上；v1.2）。
     */
    private static final Set<String> ROLE_GATED_READ_ENDPOINTS = Set.of("GET /api/v1/settings",
            "GET /api/v1/settings/{category}", "GET /api/v1/projects");

    /**
     * 免認證端點中「不可能回 401」的：{@code POST /auth/logout} 只要請求格式合法就一律 204（不論 token 有沒有效——不讓它變成探測 token 有效性的管道，
     * 契約 §1.9.1），格式不合是 400；登入與續期的 401 是帳密錯誤與 refresh token 無效，所以仍列。
     */
    private static final Set<String> NEVER_UNAUTHORIZED = Set.of("POST /api/v1/auth/logout");

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
                if (!NEVER_UNAUTHORIZED.contains(key)) {
                    add(operation, "401", isPublic ? "帳號密碼錯誤，或 refresh token 無效／過期／已被撤銷" : "未登入，或 access token 無效／過期");
                }
                if ((!isPublic && !isRead) || ROLE_GATED_READ_ENDPOINTS.contains(key)) {
                    add(operation, "403", "角色不足（VIEWER 只能讀取；寫入需要 OPERATOR 或 ADMIN；系統參數寫入與 reveal 僅 ADMIN；"
                            + "已刪除專案清單需 OPERATOR 以上）");
                }
                if (path.contains("{") || path.endsWith("/reorder")) {
                    add(operation, "404", NOT_FOUND_DESCRIPTION.getOrDefault(key, "資源不存在或已軟刪除"));
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
