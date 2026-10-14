package com.aisdlc.console.infrastructure.config;

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
 * OpenAPI 文件（NFR-9.4-03）：端點清單必須「恰好」等於本波範圍（PRD §7.1.1～§7.1.3、§7.1.4.1 的三個 signoff、
 * 認證端點）。前端 W3 以 /v3/api-docs 產生型別，少一個端點或多出未規劃的端點都要在這裡被抓到。
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
            Map.entry("/api/v1/tasks/{id}/signoff", List.of("post"))));

    private Resp docs() {
        Resp resp = api.get(null, "/v3/api-docs");
        assertThat(resp.status()).isEqualTo(200);
        return resp;
    }

    @Test
    void theDocumentListsExactlyTheEndpointsOfPhaseOneAndTwo() {
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
}
