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
            Map.entry("/api/v1/settings/{category}/{key}/reset", List.of("post"))));

    private Resp docs() {
        Resp resp = api.get(null, "/v3/api-docs");
        assertThat(resp.status()).isEqualTo(200);
        return resp;
    }

    @Test
    void theDocumentListsExactlyTheEndpointsDeliveredSoFarPhaseOneTwoAndTheFirstBackendBaton() {
        Resp docs = docs();
        Set<String> paths = new TreeSet<>(docs.<Map<String, Object>>read("$.paths").keySet());
        assertThat(paths).containsExactlyElementsOf(EXPECTED.keySet());
        for (Map.Entry<String, List<String>> expected : EXPECTED.entrySet()) {
            Map<String, Object> operations = docs.read("$.paths['" + expected.getKey() + "']");
            assertThat(new TreeSet<>(operations.keySet())).as(expected.getKey())
                    .containsExactlyElementsOf(expected.getValue());
        }
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
    void theBearerSchemeIsGlobalButLoginAndRefreshAreMarkedPublic() {
        Resp docs = docs();
        assertThat(docs.<String>read("$.components.securitySchemes.bearerAuth.scheme")).isEqualTo("bearer");
        assertThat(docs.<String>read("$.components.securitySchemes.bearerAuth.bearerFormat")).isEqualTo("JWT");
        assertThat(docs.<List<Object>>read("$.security")).isNotEmpty();
        assertThat(docs.<List<Object>>read("$.paths['/api/v1/auth/login'].post.security")).isEmpty();
        assertThat(docs.<List<Object>>read("$.paths['/api/v1/auth/refresh'].post.security")).isEmpty();
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
}
