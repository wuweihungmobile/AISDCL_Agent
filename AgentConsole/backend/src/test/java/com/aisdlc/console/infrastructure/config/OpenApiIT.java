package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.domain.model.config.ConfigCatalog;
import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * OpenAPI 文件（NFR-9.4-03）：端點清單必須「恰好」等於目前已交付的範圍。前端以 /v3/api-docs 產生型別，
 * 少一個端點或多出未規劃的端點都要在這裡被抓到。
 *
 * <p>契約 §0.8 的既有測試同步：Phase 1+2 的 13 個路徑，加上 W3-B1 的 20 個路徑（匯入 9、通知摘要 1、設定 10；
 * 方法與路徑變數名逐字取自 {@code openapi-p3-6.yaml}）＝33。W3-B2 再加 20 個（執行 11、監控 7、SSE 2）＝53。
 * W5（契約 v1.2）再加 {@code GET /monitor/task-totals}（C-1）＝54、{@code POST /projects/{id}/restore}（C-3）＝55。
 * W7（契約 v1.4）再加 {@code GET /engines/sdd}（D-16）＝56、{@code GET /signoffs/pending}（D-18）＝57、
 * {@code POST /auth/logout}（D-19）＝58（操作數 64→67）。
 * 整合輪 115（契約 v1.5）再加 {@code POST /projects/{id}/sdd/freeze}（API-SGN-06）、{@code PUT /projects/{id}/sdd-binding}（API-PRJ-08）、
 * {@code GET /executions/{runId}/rtm}（API-EXE-16）＝61（操作數 67→70）。
 * SelfImproving P1b（TCS-SelfImprovingMirror-P1b）再加六個 SI GET（{@code /api/v1/si/} 的 status、observations、events、proposals、
 * proposals/{id}、runs；路徑 61→67、操作 70→76；只增不減）。
 * SelfImproving P2b（TCS-SelfImprovingDecide-P2b）再加四個路徑——{@code /si/proposals/{id}/decide}、{@code /si/observations/{id}/close}、
 * {@code /si/observations/validate} 的 POST 與 {@code /si/console-writes} 的 GET——並讓 {@code /si/observations} 多一個 POST
 * （路徑 67→71、操作 76→81；只增不減）。
 * 議題中心（TCS-IssueCenter-20261027）再加三個路徑——{@code /issues}（GET）、{@code /issues/{id}}（GET）、{@code /issues/{id}/priority}（PUT、DELETE）
 * （路徑 71→74、操作 81→85；只增不減）。
 */
class OpenApiIT extends AbstractApiIT {

    private static final Map<String, List<String>> EXPECTED = new TreeMap<>(Map.ofEntries(
            Map.entry("/api/v1/auth/login", List.of("post")),
            Map.entry("/api/v1/auth/refresh", List.of("post")),
            Map.entry("/api/v1/projects", List.of("get", "post")),
            Map.entry("/api/v1/projects/{id}", List.of("delete", "get", "put")),
            Map.entry("/api/v1/projects/{id}/signoff", List.of("post")),
            Map.entry("/api/v1/projects/{projectId}/goals", List.of("get", "post")),
            Map.entry("/api/v1/goals/{id}", List.of("delete", "get", "put")),
            Map.entry("/api/v1/goals/reorder", List.of("put")),
            Map.entry("/api/v1/goals/{id}/signoff", List.of("post")),
            Map.entry("/api/v1/goals/{goalId}/tasks", List.of("get", "post")),
            Map.entry("/api/v1/tasks/{id}", List.of("delete", "get", "put")),
            Map.entry("/api/v1/tasks/{id}/retry", List.of("post")),
            Map.entry("/api/v1/tasks/{id}/signoff", List.of("post")),
            // ── W3-B1：匯入（Phase 3）──
            Map.entry("/api/v1/import", List.of("get")),
            Map.entry("/api/v1/import/upload", List.of("post")),
            Map.entry("/api/v1/import/text", List.of("post")),
            Map.entry("/api/v1/import/{id}", List.of("get")),
            Map.entry("/api/v1/import/{id}/parse", List.of("post")),
            Map.entry("/api/v1/import/{id}/result", List.of("put")),
            Map.entry("/api/v1/import/{id}/signoff", List.of("post")),
            Map.entry("/api/v1/import/{id}/confirm", List.of("post")),
            Map.entry("/api/v1/import/{id}/reject", List.of("post")),
            // ── W3-B1：通知摘要 ──
            Map.entry("/api/v1/notifications/summary", List.of("get")),
            // ── W3-B1：系統設定（Phase 6）──
            Map.entry("/api/v1/settings", List.of("get")),
            Map.entry("/api/v1/settings/history", List.of("get")),
            Map.entry("/api/v1/settings/export", List.of("post")),
            Map.entry("/api/v1/settings/import", List.of("post")),
            Map.entry("/api/v1/settings/test-connection", List.of("post")),
            Map.entry("/api/v1/settings/execution/token-guard", List.of("put")),
            Map.entry("/api/v1/settings/{category}", List.of("get")),
            Map.entry("/api/v1/settings/{category}/reset", List.of("post")),
            Map.entry("/api/v1/settings/{category}/{key}", List.of("put")),
            Map.entry("/api/v1/settings/{category}/{key}/reset", List.of("post")),
            // ── W3-B2：專案執行（Phase 4）──
            Map.entry("/api/v1/projects/{projectId}/execute", List.of("post")),
            Map.entry("/api/v1/projects/{projectId}/executions", List.of("get")),
            Map.entry("/api/v1/executions/{runId}", List.of("get")),
            Map.entry("/api/v1/executions/{runId}/pause", List.of("post")),
            Map.entry("/api/v1/executions/{runId}/resume", List.of("post")),
            Map.entry("/api/v1/executions/{runId}/cancel", List.of("post")),
            Map.entry("/api/v1/executions/{runId}/steps", List.of("get")),
            Map.entry("/api/v1/executions/{runId}/dag", List.of("get")),
            Map.entry("/api/v1/executions/{runId}/checkpoints", List.of("get")),
            Map.entry("/api/v1/executions/{runId}/restore/{checkpointId}", List.of("post")),
            Map.entry("/api/v1/executions/{runId}/review/{stepId}", List.of("post")),
            // ── W3-B2：專案監控（Phase 5）──
            Map.entry("/api/v1/monitor/projects/{projectId}/metrics", List.of("get")),
            Map.entry("/api/v1/monitor/projects/{projectId}/token-trend", List.of("get")),
            Map.entry("/api/v1/monitor/projects/{projectId}/task-trend", List.of("get")),
            Map.entry("/api/v1/monitor/projects/{projectId}/alerts", List.of("get")),
            Map.entry("/api/v1/monitor/alerts/{alertId}/acknowledge", List.of("post")),
            Map.entry("/api/v1/monitor/projects/{projectId}/logs", List.of("get")),
            Map.entry("/api/v1/monitor/projects/{projectId}/report", List.of("get")),
            // ── W3-B2：前端 SSE 兩條端點 ──
            Map.entry("/api/v1/stream/executions/{runId}/logs", List.of("get")),
            Map.entry("/api/v1/stream/executions/{runId}/metrics", List.of("get")),
            // ── W5（契約 v1.2）：全域任務總計（C-1）、軟刪除專案復原（C-3）──
            Map.entry("/api/v1/monitor/task-totals", List.of("get")),
            Map.entry("/api/v1/projects/{id}/restore", List.of("post")),
            // ── W7（契約 v1.4）：引擎狀態（D-16）、待簽核清單（D-18）、登出（D-19）──
            Map.entry("/api/v1/engines/sdd", List.of("get")),
            Map.entry("/api/v1/signoffs/pending", List.of("get")),
            Map.entry("/api/v1/auth/logout", List.of("post")),
            // ── 整合輪 115（契約 v1.5）：核准凍結、SDD 綁定編輯、執行追溯覆蓋 ──
            Map.entry("/api/v1/projects/{id}/sdd/freeze", List.of("post")),
            Map.entry("/api/v1/projects/{id}/sdd-binding", List.of("put")),
            Map.entry("/api/v1/executions/{runId}/rtm", List.of("get")),
            // ── SelfImproving P1b：唯讀鏡像（六個 GET；沒有任何寫入端點）──
            Map.entry("/api/v1/si/status", List.of("get")),
            Map.entry("/api/v1/si/observations", List.of("get", "post")),
            Map.entry("/api/v1/si/events", List.of("get")),
            Map.entry("/api/v1/si/proposals", List.of("get")),
            Map.entry("/api/v1/si/proposals/{id}", List.of("get")),
            Map.entry("/api/v1/si/runs", List.of("get")),
            // ── SelfImproving P2b：寫入載體（僅 ADMIN）與對帳讀面 ──
            Map.entry("/api/v1/si/proposals/{id}/decide", List.of("post")),
            Map.entry("/api/v1/si/observations/{id}/close", List.of("post")),
            Map.entry("/api/v1/si/observations/validate", List.of("post")),
            Map.entry("/api/v1/si/console-writes", List.of("get")),
            // ── 議題中心：兩個唯讀 GET 與僅 ADMIN 的優先順序寫入（PUT、DELETE）──
            Map.entry("/api/v1/issues", List.of("get")),
            Map.entry("/api/v1/issues/{id}", List.of("get")),
            Map.entry("/api/v1/issues/{id}/priority", List.of("delete", "put"))));

    private Resp docs() {
        Resp resp = api.get(null, "/v3/api-docs");
        assertThat(resp.status()).isEqualTo(200);
        return resp;
    }

    @Test
    void theDocumentListsExactlyTheEndpointsDeliveredSoFarPhaseOneTwoAndBothBackendBatons() {
        Resp docs = docs();
        Set<String> paths = new TreeSet<>(docs.<Map<String, Object>>read("$.paths").keySet());
        assertThat(paths).hasSize(74).containsExactlyElementsOf(EXPECTED.keySet());
        int operationCount = 0;
        for (Map.Entry<String, List<String>> expected : EXPECTED.entrySet()) {
            Map<String, Object> operations = docs.read("$.paths['" + expected.getKey() + "']");
            assertThat(new TreeSet<>(operations.keySet())).as(expected.getKey())
                    .containsExactlyElementsOf(expected.getValue());
            operationCount += operations.size();
        }
        assertThat(operationCount).as("契約 v1.5 的操作總數加 P1b 的六個 SI GET、P2b 的五個新操作與議題中心的四個操作").isEqualTo(85);
    }

    /**
     * SelfImproving P2b（TCS-SelfImprovingDecide-P2b AT-950-10-1；W16、W23）：SI 路徑與操作的精確集合與五個新 operationId，且 SI 路徑沒有 delete、put、patch。
     * 為什麼重要：前端以 /v3/api-docs 產生型別——多出一個沒規劃的寫入端點，前端就有了不該有的呼叫；operationId 變了，產生的函式名跟著變，
     * 前端的 API 層與測試就一起斷；而「SI 沒有刪除能力」是 PRD AC-SI-35-3 的結構承諾。
     */
    @Test
    void AT_950_10_1_theSiPathsAreExactlyTheElevenOnesWithTheFiveNewOperationIds() {
        Resp docs = docs();
        Map<String, Object> paths = docs.read("$.paths");
        List<String> si = paths.keySet().stream().filter(p -> p.startsWith("/api/v1/si/")).sorted().toList();
        assertThat(si).containsExactlyInAnyOrder("/api/v1/si/status", "/api/v1/si/observations", "/api/v1/si/events",
                "/api/v1/si/proposals", "/api/v1/si/proposals/{id}", "/api/v1/si/runs", "/api/v1/si/proposals/{id}/decide",
                "/api/v1/si/observations/{id}/close", "/api/v1/si/observations/validate", "/api/v1/si/console-writes");
        assertThat(paths).hasSize(74);
        for (String path : si) {
            Map<String, Object> operations = docs.read("$.paths['" + path + "']");
            assertThat(operations.keySet()).as(path).doesNotContain("delete", "put", "patch");
        }
        assertThat(new TreeSet<>(docs.<Map<String, Object>>read("$.paths['/api/v1/si/observations']").keySet()))
                .containsExactly("get", "post");
        for (String path : List.of("/api/v1/si/proposals/{id}/decide", "/api/v1/si/observations/{id}/close",
                "/api/v1/si/observations/validate")) {
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "']").keySet()).as(path).containsExactly("post");
        }
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/si/console-writes']").keySet()).containsExactly("get");

        Map<String, String> operationIds = new java.util.LinkedHashMap<>();
        operationIds.put("$.paths['/api/v1/si/proposals/{id}/decide'].post.operationId", "postSiDecide");
        operationIds.put("$.paths['/api/v1/si/observations'].post.operationId", "postSiObservation");
        operationIds.put("$.paths['/api/v1/si/observations/{id}/close'].post.operationId", "postSiObservationClose");
        operationIds.put("$.paths['/api/v1/si/observations/validate'].post.operationId", "postSiObservationValidate");
        operationIds.put("$.paths['/api/v1/si/console-writes'].get.operationId", "getSiConsoleWrites");
        operationIds.forEach((path, id) -> assertThat(docs.<String>read(path)).as(path).isEqualTo(id));
    }

    /** SelfImproving P2b 的錯誤狀態碼集合（W10、W15）：寫入端點有 201、輸入閘 422、結果不明的 504 與寫入面停用的 503；id 端點不會回 404。 */
    @Test
    void AT_950_10_1_theSiWriteEndpointsDocumentTheirOwnStatusCodes() {
        Resp docs = docs();
        Map<String, Set<String>> codes = Map.of(
                "post /api/v1/si/proposals/{id}/decide", Set.of("201", "400", "401", "403", "409", "422", "429", "502", "503", "504"),
                "post /api/v1/si/observations", Set.of("201", "400", "401", "403", "409", "422", "429", "502", "503", "504"),
                "post /api/v1/si/observations/{id}/close", Set.of("201", "400", "401", "403", "409", "422", "429", "502", "503", "504"),
                "post /api/v1/si/observations/validate", Set.of("200", "400", "401", "403", "422", "429", "502", "503", "504"),
                "get /api/v1/si/console-writes", Set.of("200", "400", "401", "429"));
        for (Map.Entry<String, Set<String>> expected : codes.entrySet()) {
            String method = expected.getKey().substring(0, expected.getKey().indexOf(' '));
            String path = expected.getKey().substring(expected.getKey().indexOf(' ') + 1);
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "']." + method + ".responses").keySet())
                    .as(expected.getKey()).containsExactlyInAnyOrderElementsOf(expected.getValue());
        }
        assertThat(docs.<Boolean>read("$.paths['/api/v1/si/observations/validate'].post.requestBody.required")).isTrue();
        assertThat(docs.<String>read("$.paths['/api/v1/si/proposals/{id}/decide'].post.requestBody.content['application/json']"
                + ".schema['$ref']")).endsWith("/SiDecideRequest");
        assertThat(docs.<String>read("$.paths['/api/v1/si/observations'].post.requestBody.content['application/json'].schema['$ref']"))
                .endsWith("/SiObservationRequest");
        assertThat(docs.<String>read("$.paths['/api/v1/si/observations/{id}/close'].post.requestBody.content['application/json']"
                + ".schema['$ref']")).endsWith("/SiCloseRequest");
    }

    @Test
    void creatingResourcesDocuments201AndDeletesDocument204() {
        Resp docs = docs();
        for (String path : Arrays.asList("/api/v1/projects", "/api/v1/projects/{projectId}/goals",
                "/api/v1/goals/{goalId}/tasks")) {
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "'].post.responses").keySet())
                    .as(path).contains("201");
        }
        for (String path : Arrays.asList("/api/v1/projects/{id}", "/api/v1/goals/{id}", "/api/v1/tasks/{id}")) {
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "'].delete.responses").keySet())
                    .as(path).contains("204");
        }
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/goals/reorder'].put.responses").keySet())
                .contains("204");
    }

    @Test
    void theBearerSchemeIsGlobalButLoginRefreshAndLogoutAreMarkedPublic() {
        Resp docs = docs();
        assertThat(docs.<String>read("$.components.securitySchemes.bearerAuth.scheme")).isEqualTo("bearer");
        assertThat(docs.<String>read("$.components.securitySchemes.bearerAuth.bearerFormat")).isEqualTo("JWT");
        assertThat(docs.<List<Object>>read("$.security")).isNotEmpty();
        assertThat(docs.<List<Object>>read("$.paths['/api/v1/auth/login'].post.security")).isEmpty();
        assertThat(docs.<List<Object>>read("$.paths['/api/v1/auth/refresh'].post.security")).isEmpty();
        assertThat(docs.<List<Object>>read("$.paths['/api/v1/auth/logout'].post.security"))
                .as("登出免認證（契約 §1.9.1）：登出時 access token 可能已過期").isEmpty();
    }

    @Test
    void responseEnvelopeSchemasAreDocumentedWithTheirRequiredFields() {
        Resp docs = docs();
        assertThat(docs.<List<String>>read("$.components.schemas.ApiResultProjectResponse.required"))
                .contains("code", "message", "data", "timestamp", "traceId");
        assertThat(docs.<String>read("$.components.schemas.ApiResultProjectResponse.properties.data['$ref']"))
                .endsWith("/ProjectResponse");
        assertThat(docs.<Map<String, Object>>read("$.components.schemas.PageDataProjectSummaryResponse.properties")
                .keySet()).contains("content", "page", "size", "totalElements", "totalPages");
    }

    @Test
    void theErrorEnvelopeIsDocumentedSoClientsCanTypeIt() {
        Resp docs = docs();
        assertThat(docs.<Map<String, Object>>read("$.components.schemas").keySet()).contains("ApiError");
        assertThat(docs.<List<String>>read("$.components.schemas.ApiError.required"))
                .contains("code", "message", "errors", "timestamp", "traceId");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/projects/{id}'].put.responses").keySet())
                .contains("400", "401", "403", "404", "409");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/auth/login'].post.responses").keySet())
                .contains("400", "401").doesNotContain("403");
    }

    // ── W3-B1 與契約 openapi-p3-6.yaml 對帳的結論（逐端點比對由 Python 腳本做過；這裡釘住會再退化的幾處）──────────

    @Test
    void anEndpointWithoutAnyInputDoesNotDocumentA400ButOnesWithInputDo() {
        Resp docs = docs();
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/notifications/summary'].get.responses").keySet())
                .as("沒有任何參數或本文，不可能回 400").doesNotContain("400");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/settings/export'].post.responses").keySet())
                .doesNotContain("400");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/settings'].get.responses").keySet())
                .as("reveal=abc 是型別錯誤").contains("400", "401", "403", "429");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/import/{id}'].get.responses").keySet())
                .contains("400", "401", "404", "429");
    }

    @Test
    void theSettingsCategoryIsDocumentedAsTheSixValueEnumInTheParametersAndTheResponse() {
        Resp docs = docs();
        List<String> categories = ConfigCatalog.CATEGORIES;
        for (String path : List.of("/api/v1/settings/{category}", "/api/v1/settings/{category}/reset")) {
            String method = path.endsWith("reset") ? "post" : "get";
            assertThat(docs.<List<String>>read("$.paths['" + path + "']." + method
                    + ".parameters[?(@.name=='category')].schema.enum[*]")).as(path).containsExactlyElementsOf(categories);
        }
        assertThat(docs.<List<String>>read("$.paths['/api/v1/settings/{category}/{key}'].put"
                + ".parameters[?(@.name=='category')].schema.enum[*]")).containsExactlyElementsOf(categories);
        assertThat(docs.<List<String>>read("$.paths['/api/v1/settings/{category}/{key}/reset'].post"
                + ".parameters[?(@.name=='category')].schema.enum[*]")).containsExactlyElementsOf(categories);
        assertThat(docs.<List<String>>read("$.components.schemas.ConfigResponse.properties.category.enum"))
                .containsExactlyElementsOf(categories);
    }

    @Test
    void theTwoFileUploadEndpointsDocumentARequiredMultipartBodyWithARequiredBinaryFileField() {
        Resp docs = docs();
        for (String path : List.of("/api/v1/import/upload", "/api/v1/settings/import")) {
            assertThat(docs.<Boolean>read("$.paths['" + path + "'].post.requestBody.required")).as(path).isTrue();
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "'].post.requestBody.content").keySet())
                    .containsExactly("multipart/form-data");
        }
    }

    @Test
    void gateErrorsAndWarningsAreTypedWithTheirRequiredFieldsAndTheGateEnum() {
        Resp docs = docs();
        assertThat(docs.<List<String>>read("$.components.schemas.GateError.required")).containsExactlyInAnyOrder("gate",
                "detail");
        assertThat(docs.<List<String>>read("$.components.schemas.GateError.properties.gate.enum"))
                .containsExactlyInAnyOrder("empty_prompt", "max_steps", "cycle", "prompt_too_long", "brain_unsupported",
                        "brain_failed");
        assertThat(docs.<List<String>>read("$.components.schemas.ParseWarning.required")).containsExactlyInAnyOrder(
                "code", "detail");
        assertThat(docs.<String>read("$.components.schemas.ParseResultResponse.properties.errors.items['$ref']"))
                .endsWith("/GateError");
        assertThat(docs.<String>read("$.components.schemas.ParseResultResponse.properties.warnings.items['$ref']"))
                .endsWith("/ParseWarning");
    }

    @Test
    void theExportDocumentVersionIsAPlainRequiredInteger() {
        Resp docs = docs();
        assertThat(docs.<String>read("$.components.schemas.SettingsExportDocument.properties.version.type"))
                .isEqualTo("integer");
        assertThat(docs.<List<String>>read("$.components.schemas.SettingsExportDocument.required"))
                .contains("version", "exportedAt", "configs");
    }

    // ── W3-B2 與契約 openapi-p3-6.yaml 對帳的結論（逐端點比對由 Python 腳本做過；這裡釘住狀態碼集合與幾處易退化的形狀）─────

    /** 契約 yaml 逐端點的狀態碼集合（W3-B2 的 20 個端點；v1.2 起報表不再有 501，C-4）。 */
    private static final Map<String, Set<String>> W3B2_STATUS_CODES = Map.ofEntries(
            Map.entry("post /api/v1/projects/{projectId}/execute",
                    Set.of("201", "400", "401", "403", "404", "409", "422", "429", "502", "504")),
            Map.entry("get /api/v1/projects/{projectId}/executions", Set.of("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/executions/{runId}", Set.of("200", "400", "401", "404", "429")),
            Map.entry("post /api/v1/executions/{runId}/pause",
                    Set.of("200", "400", "401", "403", "404", "409", "429", "502", "504")),
            Map.entry("post /api/v1/executions/{runId}/resume",
                    Set.of("200", "400", "401", "403", "404", "409", "429", "502", "504")),
            Map.entry("post /api/v1/executions/{runId}/cancel",
                    Set.of("200", "400", "401", "403", "404", "409", "429", "502", "504")),
            Map.entry("get /api/v1/executions/{runId}/steps", Set.of("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/executions/{runId}/dag", Set.of("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/executions/{runId}/checkpoints", Set.of("200", "400", "401", "404", "429")),
            Map.entry("post /api/v1/executions/{runId}/restore/{checkpointId}",
                    Set.of("200", "400", "401", "403", "404", "409", "422", "429", "502", "504")),
            Map.entry("post /api/v1/executions/{runId}/review/{stepId}",
                    Set.of("204", "400", "401", "403", "404", "409", "422", "429", "502", "504")),
            Map.entry("get /api/v1/monitor/projects/{projectId}/metrics", Set.of("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/monitor/projects/{projectId}/token-trend",
                    Set.of("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/monitor/projects/{projectId}/task-trend",
                    Set.of("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/monitor/projects/{projectId}/alerts", Set.of("200", "400", "401", "404", "429")),
            Map.entry("post /api/v1/monitor/alerts/{alertId}/acknowledge",
                    Set.of("204", "400", "401", "403", "404", "429")),
            Map.entry("get /api/v1/monitor/projects/{projectId}/logs", Set.of("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/monitor/projects/{projectId}/report", Set.of("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/stream/executions/{runId}/logs", Set.of("200", "204", "400", "401", "404", "429")),
            Map.entry("get /api/v1/stream/executions/{runId}/metrics",
                    Set.of("200", "204", "400", "401", "404", "429")));

    @Test
    void everyW3B2EndpointDocumentsExactlyTheStatusCodesOfTheContract() {
        Resp docs = docs();
        assertThat(W3B2_STATUS_CODES).hasSize(20);
        for (Map.Entry<String, Set<String>> expected : W3B2_STATUS_CODES.entrySet()) {
            String method = expected.getKey().substring(0, expected.getKey().indexOf(' '));
            String path = expected.getKey().substring(expected.getKey().indexOf(' ') + 1);
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "']." + method + ".responses").keySet())
                    .as(expected.getKey()).containsExactlyInAnyOrderElementsOf(expected.getValue());
        }
    }

    @Test
    void theTaskTotalsEndpointDocumentsAMandatoryFromAnOptionalToAndTheTotalsSchema() {
        Resp docs = docs();
        String path = "$.paths['/api/v1/monitor/task-totals'].get";
        assertThat(docs.<Map<String, Object>>read(path + ".responses").keySet())
                .as("沒有路徑變數：不會有 404；全域資料：不需要 403").containsExactlyInAnyOrder("200", "400", "401", "429");
        assertThat(docs.<List<Boolean>>read(path + ".parameters[?(@.name=='from')].required")).containsExactly(true);
        assertThat(docs.<List<Boolean>>read(path + ".parameters[?(@.name=='to')].required")).containsExactly(false);
        assertThat(docs.<List<String>>read("$.components.schemas.TaskTotalsResponse.required"))
                .containsExactlyInAnyOrder("from", "to", "started", "completed", "failed", "retried", "projectsCounted");
        assertThat(docs.<String>read("$.components.schemas.TaskTotalsResponse.properties.started.format"))
                .isEqualTo("int64");
        assertThat(docs.<String>read("$.components.schemas.TaskTotalsResponse.properties.projectsCounted.format"))
                .isEqualTo("int32");
    }

    @Test
    void theRestoreEndpointAndTheDeletedProjectListAreDocumentedWithTheirErrorsAndFields() {
        Resp docs = docs();
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/projects/{id}/restore'].post.responses").keySet())
                .as("寫入端點：401／403；路徑變數：400／404；有狀態規則：409（project_not_deleted、restore_window_expired）")
                .containsExactlyInAnyOrder("200", "400", "401", "403", "404", "409", "429");
        assertThat(docs.<List<String>>read("$.paths['/api/v1/projects/{id}/restore'].post.responses['200']"
                + ".content.*.schema['$ref']")).singleElement().asString().endsWith("/ApiResultProjectDetailResponse");

        String list = "$.paths['/api/v1/projects'].get";
        assertThat(docs.<Map<String, Object>>read(list + ".responses").keySet())
                .as("deleted=true 對 VIEWER 回 403，所以列表端點也要文件化 403")
                .containsExactlyInAnyOrder("200", "400", "401", "403", "429");
        assertThat(docs.<List<String>>read(list + ".parameters[?(@.name=='deleted')].schema.type"))
                .containsExactly("boolean");
        assertThat(docs.<List<Boolean>>read(list + ".parameters[?(@.name=='deleted')].schema.default"))
                .containsExactly(false);
        assertThat(docs.<List<String>>read(list + ".parameters[*].name"))
                .as("登入身分（Authentication）是執行期注入的，不是查詢參數").doesNotContain("authentication");

        assertThat(docs.<Map<String, Object>>read("$.components.schemas.ProjectSummaryResponse.properties").keySet())
                .contains("deletedAt");
        assertThat(docs.<List<String>>read("$.components.schemas.ProjectSummaryResponse.required"))
                .as("deletedAt 只在 deleted=true 的列表出現，不是必填").doesNotContain("deletedAt");
    }

    @Test
    void theTwoSseEndpointsAcceptBearerOrTheAccessTokenQueryParameter() {
        Resp docs = docs();
        assertThat(docs.<String>read("$.components.securitySchemes.queryAccessToken.in")).isEqualTo("query");
        assertThat(docs.<String>read("$.components.securitySchemes.queryAccessToken.name")).isEqualTo("access_token");
        for (String tail : List.of("logs", "metrics")) {
            String path = "/api/v1/stream/executions/{runId}/" + tail;
            List<Map<String, Object>> security = docs.read("$.paths['" + path + "'].get.security");
            assertThat(security.stream().flatMap(m -> m.keySet().stream()).toList())
                    .as(path).containsExactlyInAnyOrder("bearerAuth", "queryAccessToken");
            assertThat(docs.<List<String>>read("$.paths['" + path + "'].get.parameters[?(@.in=='header')].name"))
                    .as(path).containsExactly("Last-Event-ID");
            assertThat(docs.<List<String>>read("$.paths['" + path + "'].get.parameters[?(@.name=='access_token')].in"))
                    .as(path).containsExactly("query");
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "'].get.responses['200'].content").keySet())
                    .as(path).containsExactly("text/event-stream");
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "'].get.responses['204']").keySet())
                    .as(path + " 的 204 沒有本文（契約：結束重連的空回應，不是一條串流）").doesNotContain("content");
        }
        assertThat(docs.<List<String>>read("$.paths['/api/v1/stream/executions/{runId}/logs'].get.parameters"
                + "[?(@.name=='tail')].schema.type")).containsExactly("integer");
    }

    @Test
    void theReviewEndpointDocumentsTheFollowUpHeaderAndTheReportDocumentsBothFileTypes() {
        Resp docs = docs();
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/executions/{runId}/review/{stepId}']"
                + ".post.responses['204'].headers").keySet()).containsExactly("X-Follow-Up-Run-Id");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/monitor/projects/{projectId}/report']"
                + ".get.responses['200'].content").keySet()).containsExactlyInAnyOrder("text/csv", "application/pdf");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/monitor/projects/{projectId}/report']"
                + ".get.responses['200'].headers").keySet()).containsExactly("Content-Disposition");
    }

    /**
     * v1.3（D-11、D-12；契約 §1.2.1、§1.2.3、§3.1.2）：引擎能力與資源取樣的 schema 與 {@code openapi-p3-6.yaml} 的欄位名、必填集合、
     * 列舉值與型別一致——前端以 yaml 產生型別，這裡的名稱或列舉值一旦漂移，前端的 {@code engineCapabilities} 晶片與「資源使用」欄就讀不到。
     * 差異（已登記）：yaml 把狀態列舉獨立成 {@code EngineCapabilityState}，springdoc 把它內嵌在兩個欄位上（與 RunStatus 等既有列舉同做法）。
     */
    @Test
    void theEngineCapabilitiesAndTheResourceUsageSchemasMatchTheContractYaml() {
        Resp docs = docs();
        String capabilities = "$.components.schemas.EngineCapabilities";
        assertThat(docs.<List<String>>read(capabilities + ".required")).containsExactlyInAnyOrder("autoMutation",
                "selfEvolution");
        for (String property : List.of("autoMutation", "selfEvolution")) {
            assertThat(docs.<List<String>>read(capabilities + ".properties." + property + ".enum"))
                    .as(property).containsExactly("ENABLED", "OFF", "UNAVAILABLE_NO_API_KEY");
        }
        for (String response : List.of("ExecutionRunResponse", "ExecutionRunDetailResponse")) {
            assertThat(docs.<String>read("$.components.schemas." + response + ".properties.engineCapabilities['$ref']"))
                    .as(response).endsWith("/EngineCapabilities");
            assertThat(docs.<List<String>>read("$.components.schemas." + response + ".required"))
                    .as(response + "：engineCapabilities 不是必填（V10 之前的批次缺席）").doesNotContain("engineCapabilities");
        }
        assertThat(docs.<Map<String, Object>>read("$.components.schemas.ExecutionRunSummaryResponse.properties")
                .keySet()).as("批次列表項不帶能力狀態").doesNotContain("engineCapabilities");

        String usage = "$.components.schemas.ResourceUsage";
        assertThat(docs.<List<String>>read(usage + ".required")).containsExactlyInAnyOrder("cpuPercent",
                "memoryBytes", "processCount", "sampledAt");
        assertThat(docs.<String>read(usage + ".properties.cpuPercent.type")).isEqualTo("number");
        assertThat(docs.<Integer>read(usage + ".properties.cpuPercent.minimum")).isEqualTo(0);
        assertThat(docs.<Integer>read(usage + ".properties.cpuPercent.maximum")).isEqualTo(100);
        assertThat(docs.<String>read(usage + ".properties.memoryBytes.type")).isEqualTo("integer");
        assertThat(docs.<String>read(usage + ".properties.memoryBytes.format")).isEqualTo("int64");
        assertThat(docs.<String>read(usage + ".properties.processCount.format")).isEqualTo("int32");
        assertThat(docs.<Integer>read(usage + ".properties.processCount.minimum")).isEqualTo(1);
        assertThat(docs.<String>read(usage + ".properties.sampledAt.type")).isEqualTo("string");
        assertThat(docs.<String>read(usage + ".properties.sampledAt.format")).isEqualTo("date-time");

        assertThat(docs.<String>read("$.components.schemas.BridgeInfo.properties.resources['$ref']"))
                .endsWith("/ResourceUsage");
        assertThat(docs.<List<String>>read("$.components.schemas.BridgeInfo.required"))
                .containsExactlyInAnyOrder("connected", "checkedAt");
    }

    /**
     * v1.4（D-16、D-18、D-19；契約 §1.7.1、§1.8.1、§1.9.1）：三個新端點的狀態碼集合與參數規則逐字等於 {@code openapi-p3-6.yaml}。
     * 為什麼重要：前端以 yaml 產生型別與錯誤處理——登出若多文件化一個 401，前端會為「登出被拒」寫出永遠走不到的分支；{@code limit}
     * 的範圍文件與實作不一致，前端的輸入檢查就會放行會得到 400 的值。
     */
    @Test
    void theV14EndpointsDocumentTheStatusCodesAndParametersOfTheContract() {
        Resp docs = docs();
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/engines/sdd'].get.responses").keySet())
                .as("v1.5：projectId 找不到專案 → 404").containsExactlyInAnyOrder("200", "400", "401", "404", "429");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/signoffs/pending'].get.responses").keySet())
                .containsExactlyInAnyOrder("200", "400", "401", "429");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/auth/logout'].post.responses").keySet())
                .as("免認證：沒有 401；請求格式合法一律 204").containsExactlyInAnyOrder("204", "400", "429");
        assertThat(docs.<Boolean>read("$.paths['/api/v1/auth/logout'].post.requestBody.required")).isTrue();
        assertThat(docs.<String>read("$.paths['/api/v1/auth/logout'].post.requestBody.content['application/json']"
                + ".schema['$ref']")).endsWith("/LogoutRequest");

        String project = "$.paths['/api/v1/engines/sdd'].get.parameters[?(@.name=='project')]";
        assertThat(docs.<List<String>>read("$.paths['/api/v1/engines/sdd'].get.parameters[*].name"))
                .as("v1.5 多一個選填的 projectId").containsExactlyInAnyOrder("projectId", "project");
        String projectId = "$.paths['/api/v1/engines/sdd'].get.parameters[?(@.name=='projectId')]";
        assertThat(docs.<List<Boolean>>read(projectId + ".required")).containsExactly(false);
        assertThat(docs.<List<String>>read(projectId + ".schema.type")).containsExactly("string");
        assertThat(docs.<List<String>>read(projectId + ".schema.format")).containsExactly("uuid");
        assertThat(docs.<List<Boolean>>read(project + ".required")).containsExactly(false);
        assertThat(docs.<List<String>>read(project + ".schema.pattern"))
                .as("v1.5：Console 不再淨化專案名，只驗長度與控制字元（專案名規則在 Bridge）")
                .containsExactly("^[^\\x00-\\x1f\\x7f]{1,200}$");
        assertThat(docs.<List<Integer>>read(project + ".schema.minLength")).containsExactly(1);
        assertThat(docs.<List<Integer>>read(project + ".schema.maxLength")).containsExactly(200);

        String limit = "$.paths['/api/v1/signoffs/pending'].get.parameters[?(@.name=='limit')]";
        assertThat(docs.<List<String>>read("$.paths['/api/v1/signoffs/pending'].get.parameters[*].name"))
                .containsExactly("limit");
        assertThat(docs.<List<Boolean>>read(limit + ".required")).containsExactly(false);
        assertThat(docs.<List<Integer>>read(limit + ".schema.minimum")).containsExactly(1);
        assertThat(docs.<List<Integer>>read(limit + ".schema.maximum")).containsExactly(200);
        assertThat(docs.<List<Integer>>read(limit + ".schema.default")).containsExactly(50);
    }

    /**
     * v1.4（D-16；契約 §1.7.1、§3.1.3）：AISDLC_SDD 引擎狀態的 schema 欄位名、必填集合、列舉值與上限與 {@code openapi-p3-6.yaml} 一致。
     * 差異（已登記）：yaml 把 {@code reason} 的值域獨立成 {@code SddEngineReason} 再以 oneOf 與 null 組合，springdoc 把列舉值內嵌在欄位上。
     */
    @Test
    void theSddEngineSchemasMatchTheContractYaml() {
        Resp docs = docs();
        String schemas = "$.components.schemas.";
        String status = schemas + "SddEngineStatusResponse";
        assertThat(docs.<List<String>>read(status + ".required")).containsExactlyInAnyOrder("available", "reason",
                "version", "projects", "fsm", "checkedAt");
        assertThat(docs.<List<String>>read(status + ".properties.reason.enum").stream().filter(v -> v != null).toList())
                .containsExactlyInAnyOrder("bridge_unreachable", "sdd_unavailable", "bridge_error", "fsm_not_found",
                        "fsm_state_unreadable", "sdd_root_rejected");
        assertThat(docs.<List<String>>read(status + ".properties.version..['$ref']")).singleElement().asString()
                .endsWith("/SddVersion");
        assertThat(docs.<String>read(status + ".properties.projects.items['$ref']")).endsWith("/SddProjectEntry");
        assertThat(docs.<List<String>>read(status + ".properties.fsm..['$ref']")).singleElement().asString()
                .endsWith("/SddFsmState");
        assertThat(docs.<String>read(status + ".properties.checkedAt.format")).isEqualTo("date-time");

        assertThat(docs.<List<String>>read(schemas + "SddVersion.required")).containsExactlyInAnyOrder("latest", "root");
        assertThat(docs.<List<String>>read(schemas + "SddProjectEntry.required")).containsExactlyInAnyOrder("project",
                "source", "currentState", "updatedAt");
        assertThat(docs.<Integer>read(schemas + "SddProjectEntry.properties.project.maxLength")).isEqualTo(80);
        assertThat(docs.has(schemas + "SddProjectEntry.properties.project.pattern"))
                .as("v1.5：淨化後的標準鍵可含 CJK、空白與括號，不再有 [A-Za-z0-9._-] 的 pattern").isFalse();

        assertThat(docs.<List<String>>read(schemas + "SddFsmState.required")).containsExactlyInAnyOrder("project",
                "source", "frozenStages", "decisionTrace", "humanPending", "retryHistory");
        assertThat(docs.<Integer>read(schemas + "SddFsmState.properties.decisionTrace.maxItems")).isEqualTo(5);
        // v1.5（G-13、D-115-16）：階段、升級歷史、升級來源、標準鍵、恢復指令五個選填欄位（required 集合不變：舊版 Bridge 缺鍵由 Backend 補預設）
        assertThat(docs.<Map<String, Object>>read(schemas + "SddFsmState.properties").keySet()).contains("phase",
                "escalationHistory", "escalationProvenance", "fsmProject", "recovery");
        assertThat(docs.<Integer>read(schemas + "SddFsmState.properties.escalationHistory.maxItems")).isEqualTo(5);
        assertThat(docs.<List<String>>read(schemas + "SddFsmPhase.required")).containsExactlyInAnyOrder("name", "order",
                "blocking", "observation");
        assertThat(docs.<Integer>read(schemas + "SddFsmPhase.properties.order.minimum")).isZero();
        assertThat(docs.<Integer>read(schemas + "SddFsmPhase.properties.order.maximum")).isEqualTo(8);
        assertThat(docs.<List<String>>read(schemas + "SddRecovery.required")).containsExactlyInAnyOrder("target",
                "powershell", "posix");
        assertThat(docs.<String>read(schemas + "SddFsmState.properties.humanPending['$ref']")).endsWith("/SddHumanPending");
        assertThat(docs.<String>read(schemas + "SddFsmState.properties.retryHistory['$ref']"))
                .endsWith("/SddRetryHistory");
        assertThat(docs.<List<String>>read(schemas + "SddHumanPending.required")).containsExactlyInAnyOrder("count",
                "items");
        assertThat(docs.<Integer>read(schemas + "SddHumanPending.properties.items.maxItems")).isEqualTo(5);
        assertThat(docs.<Integer>read(schemas + "SddHumanPending.properties.count.minimum")).isZero();
        assertThat(docs.<List<String>>read(schemas + "SddRetryHistory.required")).containsExactlyInAnyOrder("count",
                "last");
    }

    /** v1.4（D-18、D-19；契約 §1.8.1、§1.9.1）：待簽核清單與登出請求的 schema 與 {@code openapi-p3-6.yaml} 一致。 */
    @Test
    void thePendingSignoffAndLogoutSchemasMatchTheContractYaml() {
        Resp docs = docs();
        String schemas = "$.components.schemas.";
        assertThat(docs.<List<String>>read(schemas + "PendingSignoffsResponse.required"))
                .containsExactlyInAnyOrder("counts", "items");
        assertThat(docs.<Integer>read(schemas + "PendingSignoffsResponse.properties.items.maxItems")).isEqualTo(200);
        assertThat(docs.<String>read(schemas + "PendingSignoffsResponse.properties.items.items['$ref']"))
                .endsWith("/PendingSignoffItem");
        assertThat(docs.<String>read(schemas + "PendingSignoffsResponse.properties.counts['$ref']"))
                .endsWith("/PendingSignoffCounts");
        assertThat(docs.<List<String>>read(schemas + "PendingSignoffCounts.required"))
                .containsExactlyInAnyOrder("projects", "goals", "tasks", "imports", "total");
        for (String count : List.of("projects", "goals", "tasks", "imports", "total")) {
            assertThat(docs.<Integer>read(schemas + "PendingSignoffCounts.properties." + count + ".minimum"))
                    .as(count).isZero();
        }
        assertThat(docs.<List<String>>read(schemas + "PendingSignoffItem.required")).containsExactlyInAnyOrder("kind",
                "id", "projectId", "projectName", "parentId", "title", "createdAt");
        assertThat(docs.<List<String>>read(schemas + "PendingSignoffItem.properties.kind.enum"))
                .containsExactlyInAnyOrder("PROJECT", "GOAL", "TASK", "IMPORT");
        assertThat(docs.<String>read(schemas + "PendingSignoffItem.properties.createdAt.format")).isEqualTo("date-time");

        assertThat(docs.<List<String>>read(schemas + "LogoutRequest.required")).containsExactly("refreshToken");
        assertThat(docs.<Integer>read(schemas + "LogoutRequest.properties.refreshToken.minLength")).isEqualTo(1);
    }

    /**
     * v1.5（整合輪 115；契約 §1.10）：三個新端點的 operationId、狀態碼集合、請求本文與回應 schema 逐字等於 {@code openapi-p3-6.yaml}。
     * 為什麼重要：前端以 yaml 產生型別與錯誤處理——凍結若少文件化 503，前端就沒有「SDD 寫入面停用」的分支；RTM 的 404 若不是 JSON
     * 封包（reason 是這個端點獨有的例外），前端分不出「批次不存在」與「批次存在但沒有報告」。
     */
    @Test
    void theV15EndpointsDocumentTheStatusCodesAndSchemasOfTheContract() {
        Resp docs = docs();
        Map<String, Set<String>> codes = Map.of(
                "post /api/v1/projects/{id}/sdd/freeze",
                Set.of("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504"),
                "put /api/v1/projects/{id}/sdd-binding", Set.of("200", "400", "401", "403", "404", "409", "429"),
                "get /api/v1/executions/{runId}/rtm", Set.of("200", "400", "401", "404", "422", "429", "502", "504"));
        for (Map.Entry<String, Set<String>> expected : codes.entrySet()) {
            String method = expected.getKey().substring(0, expected.getKey().indexOf(' '));
            String path = expected.getKey().substring(expected.getKey().indexOf(' ') + 1);
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "']." + method + ".responses").keySet())
                    .as(expected.getKey()).containsExactlyInAnyOrderElementsOf(expected.getValue());
        }

        String freeze = "$.paths['/api/v1/projects/{id}/sdd/freeze'].post";
        assertThat(docs.<String>read(freeze + ".operationId")).isEqualTo("freezeProjectSddSpec");
        assertThat(docs.<Boolean>read(freeze + ".requestBody.required")).isTrue();
        assertThat(docs.<String>read(freeze + ".requestBody.content['application/json'].schema['$ref']"))
                .endsWith("/SddFreezeRequest");
        assertThat(docs.<List<String>>read(freeze + ".responses['200'].content.*.schema['$ref']")).singleElement()
                .asString().endsWith("/ApiResultSddFsmState");

        String binding = "$.paths['/api/v1/projects/{id}/sdd-binding'].put";
        assertThat(docs.<String>read(binding + ".operationId")).isEqualTo("updateProjectSddBinding");
        assertThat(docs.<Boolean>read(binding + ".requestBody.required")).isTrue();
        assertThat(docs.<String>read(binding + ".requestBody.content['application/json'].schema['$ref']"))
                .endsWith("/SddBindingRequest");
        assertThat(docs.<List<String>>read(binding + ".responses['200'].content.*.schema['$ref']")).singleElement()
                .asString().endsWith("/ApiResultProjectDetailResponse");

        String rtm = "$.paths['/api/v1/executions/{runId}/rtm'].get";
        assertThat(docs.<String>read(rtm + ".operationId")).isEqualTo("getExecutionRtm");
        assertThat(docs.<List<String>>read(rtm + ".responses['200'].content.*.schema['$ref']")).singleElement()
                .asString().endsWith("/ApiResultExecutionRtmResponse");
        assertThat(docs.<Map<String, Object>>read(rtm + ".responses['404'].content").keySet())
                .as("404 是 JSON 的 ApiError（reason 是本端點獨有的例外）").containsExactly("application/json");
        assertThat(docs.<String>read(rtm + ".responses['404'].content['application/json'].schema['$ref']"))
                .endsWith("/ApiError");
    }

    /**
     * v1.5（整合輪 115）：新的請求／回應 schema 與 {@code openapi-p3-6.yaml} 的欄位名、必填集合與上下限一致。
     * 為什麼重要：前端依 yaml 產生型別與輸入檢查——{@code expectedDigests} 的 pattern、{@code docs} 的筆數上限若與實作不同，前端放行的值會得到 400；
     * {@code advisory} 若不是必填的恆真欄位，前端就沒有義務標示「諮詢視圖」。
     */
    @Test
    void theV15SchemasMatchTheContractYaml() {
        Resp docs = docs();
        String schemas = "$.components.schemas.";

        assertThat(docs.<List<String>>read(schemas + "SddFreezeRequest.required")).containsExactly("reason");
        assertThat(docs.<Integer>read(schemas + "SddFreezeRequest.properties.reason.minLength")).isEqualTo(1);
        assertThat(docs.<Integer>read(schemas + "SddFreezeRequest.properties.reason.maxLength")).isEqualTo(500);
        assertThat(docs.<String>read(schemas + "SddFreezeRequest.properties.stage.pattern"))
                .isEqualTo("^[A-Za-z0-9._-]{1,64}$");
        assertThat(docs.<Integer>read(schemas + "SddFreezeRequest.properties.docs.minItems")).isEqualTo(1);
        assertThat(docs.<Integer>read(schemas + "SddFreezeRequest.properties.docs.maxItems")).isEqualTo(20);
        assertThat(docs.<Integer>read(schemas + "SddFreezeRequest.properties.docs.items.maxLength")).isEqualTo(500);
        assertThat(docs.<String>read(schemas + "SddFreezeRequest.properties.expectedDigests.type")).isEqualTo("object");
        assertThat(docs.<String>read(schemas + "SddFreezeRequest.properties.expectedDigests.additionalProperties.type"))
                .isEqualTo("string");
        assertThat(docs.<Map<String, Object>>read(schemas + "SddFreezeRequest.properties").keySet())
                .as("approver 不在請求內（一律取 JWT subject），也沒有 binding 欄").containsExactlyInAnyOrder("reason", "stage",
                        "docs", "expectedDigests");

        assertThat(docs.<List<String>>read(schemas + "SddBindingRequest.required")).containsExactly("sddProject");
        assertThat(docs.<Integer>read(schemas + "SddBindingRequest.properties.sddProject.minLength")).isEqualTo(1);
        assertThat(docs.<Integer>read(schemas + "SddBindingRequest.properties.sddProject.maxLength")).isEqualTo(100);

        assertThat(docs.<List<String>>read(schemas + "ExecutionRtmResponse.required")).containsExactlyInAnyOrder(
                "scenario", "specDigest", "at", "ac", "failedAtIds", "weakRegexAtIds", "unmappedAtIds", "fullyCovered",
                "advisory");
        assertThat(docs.<String>read(schemas + "ExecutionRtmResponse.properties.at['$ref']")).endsWith("/RtmAtCoverage");
        assertThat(docs.<String>read(schemas + "ExecutionRtmResponse.properties.ac['$ref']")).endsWith("/RtmAcCoverage");
        Map<String, Object> advisory = docs.read(schemas + "ExecutionRtmResponse.properties.advisory");
        assertThat(advisory.get("type")).isEqualTo("boolean");
        assertThat(advisory).as("契約寫 const: true；springdoc 的 allowableValues 對 boolean 會產出字串 enum「true」（與 type 不符），"
                + "所以不用它，改以說明表達").doesNotContainKey("enum");
        assertThat((String) advisory.get("description")).contains("恆為 true");
        assertThat(docs.<List<String>>read(schemas + "RtmAtCoverage.required")).containsExactlyInAnyOrder("passed",
                "total", "unmapped", "pct");
        assertThat(docs.<List<String>>read(schemas + "RtmAcCoverage.required")).containsExactlyInAnyOrder("covered",
                "total", "pct");
        for (String bucket : List.of("RtmAtCoverage", "RtmAcCoverage")) {
            assertThat(docs.<Integer>read(schemas + bucket + ".properties.pct.minimum")).as(bucket).isZero();
            assertThat(docs.<Integer>read(schemas + bucket + ".properties.pct.maximum")).as(bucket).isEqualTo(100);
            assertThat(docs.<Integer>read(schemas + bucket + ".properties.total.minimum")).as(bucket).isZero();
        }

        assertThat(docs.<List<String>>read(schemas + "ExecutionWarning.required")).containsExactlyInAnyOrder("code",
                "detail");
        assertThat(docs.<String>read(schemas + "ExecutionRunResponse.properties.warnings.items['$ref']"))
                .endsWith("/ExecutionWarning");
        assertThat(docs.<List<String>>read(schemas + "ExecutionRunResponse.required"))
                .as("warnings 只有 execute 的 201 帶，不是必填").doesNotContain("warnings");
        assertThat(docs.has(schemas + "ExecutionWarning.properties.code.enum"))
                .as("契約：日後新增的 code 前端要原樣顯示，所以文件上是開放字串、不是列舉").isFalse();
        assertThat(docs.has(schemas + "ExecutionWarning.properties.cause.enum"))
                .as("同上：cause 的五個值寫在說明裡，不列舉").isFalse();
        assertThat(docs.<String>read(schemas + "ExecutionWarning.properties.cause.description"))
                .contains("not_bound", "token_not_configured", "mixed_scope", "spec_mismatch", "duplicate_step_id");
    }

    /**
     * v1.5（整合輪 115）：既有 schema 的新欄位——專案的三個綁定欄、匯入選項的三個參數、解析結果的四個伺服器擁有欄位。
     * 為什麼重要：這些欄位是前端「專案詳情的 SDD 治理區」與「匯入到既有專案」的資料來源；伺服器擁有的欄位若被文件化成必填，
     * 前端的編輯請求就必須帶它們（而 {@code PUT /import/{id}/result} 本來就會忽略這些欄位）。
     */
    @Test
    void theV15FieldsOfTheExistingSchemasMatchTheContractYaml() {
        Resp docs = docs();
        String schemas = "$.components.schemas.";
        for (String response : List.of("ProjectResponse", "ProjectDetailResponse")) {
            assertThat(docs.<Map<String, Object>>read(schemas + response + ".properties").keySet()).as(response)
                    .contains("sddProject", "sddSpecDir", "sddSpecFile");
            assertThat(docs.<Integer>read(schemas + response + ".properties.sddProject.maxLength")).as(response)
                    .isEqualTo(100);
            assertThat(docs.<Integer>read(schemas + response + ".properties.sddSpecDir.maxLength")).as(response)
                    .isEqualTo(500);
            assertThat(docs.<Integer>read(schemas + response + ".properties.sddSpecFile.maxLength")).as(response)
                    .isEqualTo(500);
            assertThat(docs.<List<String>>read(schemas + response + ".required")).as(response + "：缺席等價於 null")
                    .doesNotContain("sddProject", "sddSpecDir", "sddSpecFile");
        }

        String options = schemas + "ParseOptions";
        assertThat(docs.<List<String>>read(options + ".required")).containsExactly("executionPath");
        assertThat(docs.<Integer>read(options + ".properties.specFile.maxLength")).isEqualTo(500);
        assertThat(docs.<Integer>read(options + ".properties.sddProject.minLength")).isEqualTo(1);
        assertThat(docs.<Integer>read(options + ".properties.sddProject.maxLength")).isEqualTo(200);
        assertThat(docs.<String>read(options + ".properties.sddProject.pattern")).isEqualTo("^[^\\x00-\\x1f\\x7f]{1,200}$");
        assertThat(docs.<String>read(options + ".properties.targetProjectId.type")).isEqualTo("string");
        assertThat(docs.<String>read(options + ".properties.targetProjectId.format")).isEqualTo("uuid");

        String result = schemas + "ParsedResult";
        assertThat(docs.<List<String>>read(result + ".required")).containsExactlyInAnyOrder("project", "goals");
        assertThat(docs.<Map<String, Object>>read(result + ".properties").keySet()).contains("specFormatVersion",
                "sddProject", "sddSpecDir", "sddSpecFile");

        assertThat(docs.<String>read(schemas + "ParseWarning.properties.code.description"))
                .as("v1.5 的三個新警告碼寫在說明裡").contains("at_unmapped", "frozen_digest_absent", "state_dir_not_ignored");
    }

    @Test
    void theExecutionAndMonitorSchemasCarryTheContractRequiredFieldsAndNames() {
        Resp docs = docs();
        assertThat(docs.<List<String>>read("$.components.schemas.ExecutionRunResponse.required"))
                .containsExactlyInAnyOrder("id", "projectId", "runNumber", "status", "autonomyLevel", "scope",
                        "totalTokensUsed", "startedAt");
        assertThat(docs.<List<String>>read("$.components.schemas.ExecutionRunDetailResponse.required"))
                .contains("completedSteps", "totalSteps", "pendingReviews", "bridge");
        assertThat(docs.<List<String>>read("$.components.schemas.ReviewRequestResponse.required"))
                .containsExactlyInAnyOrder("id", "runId", "kind", "status", "reason", "requestedAt",
                        "allowedDecisions");
        assertThat(docs.<List<String>>read("$.components.schemas.ReviewRequest.required"))
                .containsExactly("decision");
        assertThat(docs.<List<String>>read("$.components.schemas.MetricValue.required")).containsExactly("value");
        assertThat(docs.<List<String>>read("$.components.schemas.CheckpointResponse.required"))
                .containsExactlyInAnyOrder("id", "runId", "name", "createdAt", "isAutomatic");
        assertThat(docs.<Map<String, Object>>read("$.components.schemas.CheckpointResponse.properties").keySet())
                .contains("isAutomatic", "stepIdx", "stepId", "completedSteps");
        assertThat(docs.<List<String>>read("$.components.schemas.DagNode.required"))
                .containsExactlyInAnyOrder("id", "kind", "label", "status");
        assertThat(docs.<List<String>>read("$.components.schemas.AlertResponse.properties.rule.enum"))
                .containsExactlyInAnyOrder("TOKEN_BUDGET_WARNING", "TOKEN_BUDGET_EXCEEDED", "CONSECUTIVE_FAILURES",
                        "AGENT_UNRESPONSIVE", "TASK_DURATION_EXCEEDED", "HIGH_RETRY_RATE", "ENGINE_ESCALATION",
                        "ENGINE_TOKEN_HALT");
        assertThat(docs.<List<String>>read("$.components.schemas.ExecutionStepResponse.properties.status.enum"))
                .containsExactlyInAnyOrder("STARTED", "COMPLETED", "FAILED", "RETRYING");
        assertThat(docs.<List<String>>read("$.components.schemas.ExecutionRunResponse.properties.bridgeStatus.enum"))
                .containsExactlyInAnyOrder("INITIALIZING", "RUNNING", "PAUSING", "PAUSED", "CANCELLING", "COMPLETED",
                        "FAILED", "CANCELLED");
    }
}
