package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/** 統一回應封包（PRD §7.2；API-FMT-01～03）與 traceId（NFR-9.4-04）。 */
class ResponseEnvelopeIT extends AbstractApiIT {

    private static final Pattern UUID_PATTERN = Pattern.compile(
            "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}");

    @Test
    void successEnvelopeHasExactlyTheDocumentedKeys() {
        Resp resp = api.post(operator(), "/api/v1/projects",
                Map.of("name", "Envelope", "executionPath", "/x", "passCriteria", "c"));
        assertThat(resp.<Map<String, Object>>read("$").keySet())
                .containsExactlyInAnyOrder("code", "message", "data", "timestamp", "traceId");
        assertThat(resp.<String>read("$.message")).isEqualTo("success");
        assertThat(resp.<Integer>read("$.code")).isEqualTo(201);
        assertThat(OffsetDateTime.parse(resp.read("$.timestamp"))).as("ISO-8601 且帶 offset").isNotNull();
        assertThat(resp.<String>read("$.timestamp")).matches(".*(Z|[+-]\\d{2}:\\d{2})$");
    }

    @Test
    void traceIdIsAFreshUuidPerRequestAndMatchesTheResponseHeader() {
        Resp first = api.get(admin(), "/api/v1/projects");
        Resp second = api.get(admin(), "/api/v1/projects");
        assertThat(first.<String>read("$.traceId")).matches(UUID_PATTERN).isEqualTo(first.header("X-Trace-Id"));
        assertThat(second.<String>read("$.traceId")).isEqualTo(second.header("X-Trace-Id"));
        assertThat(first.<String>read("$.traceId")).isNotEqualTo(second.<String>read("$.traceId"));
    }

    @Test
    void aClientSuppliedTraceIdIsIgnored() {
        Resp resp = api.send(admin(), MockMvcRequestBuilders
                .get("/api/v1/projects").header("X-Trace-Id", "attacker-controlled\nforged log line"));
        assertThat(resp.header("X-Trace-Id")).matches(UUID_PATTERN);
    }

    @Test
    void paginationEnvelopeCarriesContentPageSizeTotalElementsAndTotalPages() {
        createProject("Page A");
        createProject("Page B");
        createProject("Page C");
        Resp resp = api.get(viewer(), "/api/v1/projects?page=1&size=2&sort=name,asc");
        assertThat(resp.<Map<String, Object>>read("$.data").keySet())
                .containsExactlyInAnyOrder("content", "page", "size", "totalElements", "totalPages");
        assertThat(resp.<Integer>read("$.data.page")).isEqualTo(1);
        assertThat(resp.<Integer>read("$.data.size")).isEqualTo(2);
        assertThat(resp.<Integer>read("$.data.totalElements")).isEqualTo(3);
        assertThat(resp.<Integer>read("$.data.totalPages")).isEqualTo(2);
    }

    @Test
    void validationErrorEnvelopeListsEveryFieldProblem() {
        Resp resp = api.post(operator(), "/api/v1/projects", Map.of("name", "", "executionPath", "", "passCriteria", ""));
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<Map<String, Object>>read("$").keySet())
                .containsExactlyInAnyOrder("code", "message", "errors", "timestamp", "traceId");
        assertThat(resp.<Integer>read("$.code")).isEqualTo(400);
        assertThat(resp.<String>read("$.message")).isEqualTo("Validation failed");
        assertThat(resp.errorFields()).containsExactlyInAnyOrder("name", "executionPath", "passCriteria");
        assertThat(resp.<List<String>>read("$.errors[?(@.field=='name')].message")).containsExactly("名稱不能為空");
        assertThat(resp.<String>read("$.traceId")).isEqualTo(resp.header("X-Trace-Id"));
    }

    @Test
    void everyKindOfErrorUsesTheSameEnvelope() {
        String missing = "00000000-0000-0000-0000-000000000000";
        Map<String, Resp> samples = Map.of(
                "404 找不到", api.get(viewer(), "/api/v1/projects/" + missing),
                "404 未知路徑", api.get(admin(), "/no/such/path"),
                "405 方法不支援", api.send(admin(), MockMvcRequestBuilders
                        .patch("/api/v1/projects")),
                "400 畸形 JSON", api.raw(operator(), HttpMethod.POST, "/api/v1/projects", "{"),
                "400 UUID 格式", api.get(viewer(), "/api/v1/projects/xyz"),
                "401 未登入", api.get(null, "/api/v1/projects"),
                "403 角色不足", api.delete(viewer(), "/api/v1/projects/" + missing));
        samples.forEach((label, resp) -> {
            assertThat(resp.<Integer>read("$.code")).as(label).isEqualTo(resp.status());
            assertThat(resp.<String>read("$.message")).as(label).isNotBlank();
            assertThat(resp.<Object>read("$.errors")).as(label).isNotNull();
            assertThat(resp.<String>read("$.timestamp")).as(label).isNotBlank();
            assertThat(resp.<String>read("$.traceId")).as(label).isEqualTo(resp.header("X-Trace-Id"));
        });
        assertThat(samples.get("404 找不到").status()).isEqualTo(404);
        assertThat(samples.get("405 方法不支援").status()).isEqualTo(405);
        assertThat(samples.get("401 未登入").status()).isEqualTo(401);
        assertThat(samples.get("403 角色不足").status()).isEqualTo(403);
    }

    @Test
    void deleteAndReorderReturnNoContentWithAnEmptyBody() {
        String project = createProject("No content");
        String goal = createGoal(project, "G");
        Resp reorder = api.put(operator(), "/api/v1/goals/reorder",
                Map.of("projectId", project, "orderedGoalIds", List.of(goal)));
        assertThat(reorder.status()).isEqualTo(204);
        assertThat(reorder.body()).isEmpty();
        Resp delete = api.delete(operator(), "/api/v1/projects/" + project);
        assertThat(delete.status()).isEqualTo(204);
        assertThat(delete.body()).isEmpty();
        assertThat(delete.header("X-Trace-Id")).matches(UUID_PATTERN);
    }
}
