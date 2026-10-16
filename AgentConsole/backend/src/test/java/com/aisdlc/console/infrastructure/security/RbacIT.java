package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * RBAC（NFR-9.2-02；Architecture §8.2）：VIEWER 只能讀；OPERATOR／ADMIN 可寫；免認證端點不需 token；
 * 其餘 /actuator/** 只有 ADMIN。每一個寫入端點都逐一驗，避免日後新增端點時漏掉授權規則。
 */
class RbacIT extends AbstractApiIT {

    private record Write(String method, String url, Object body) {
    }

    /**
     * 專案／目標／任務（Phase 2）與執行／審核／告警確認（Phase 4～5）的寫入端點（PUT／POST／DELETE）。專案、目標、任務用真實存在的資源，
     * 確保 403 是授權擋的而不是 404；執行批次、checkpoint、審核項、告警沒有「活著」的實體可用，一律用隨機 UUID——授權發生在 controller 之前，
     * viewer 的 403 與匿名的 401 與資源存不存在無關（operator 越過授權層後的 404 另有測試證明）。
     */
    private List<Write> everyWriteEndpoint(String project, String goal, String task) {
        Map<String, Object> newProject = Map.of("name", "X", "executionPath", "/x", "passCriteria", "c");
        Map<String, Object> newGoal = Map.of("name", "X", "passCriteria", "c");
        Map<String, Object> newTask = Map.of("name", "X", "passCriteria", "c");
        Map<String, Object> approver = Map.of("approver", "someone");
        List<Write> phase2 = List.of(
                new Write("POST", "/api/v1/projects", newProject),
                new Write("PUT", "/api/v1/projects/" + project, Map.of("name", "renamed")),
                new Write("DELETE", "/api/v1/projects/" + project, null),
                new Write("POST", "/api/v1/projects/" + project + "/signoff", approver),
                new Write("POST", "/api/v1/projects/" + project + "/goals", newGoal),
                new Write("PUT", "/api/v1/goals/" + goal, Map.of("name", "renamed")),
                new Write("DELETE", "/api/v1/goals/" + goal, null),
                new Write("PUT", "/api/v1/goals/reorder", Map.of("projectId", project, "orderedGoalIds", List.of(goal))),
                new Write("POST", "/api/v1/goals/" + goal + "/signoff", approver),
                new Write("POST", "/api/v1/goals/" + goal + "/tasks", newTask),
                new Write("PUT", "/api/v1/tasks/" + task, Map.of("name", "renamed")),
                new Write("DELETE", "/api/v1/tasks/" + task, null),
                new Write("POST", "/api/v1/tasks/" + task + "/retry", null),
                new Write("POST", "/api/v1/tasks/" + task + "/signoff", approver));
        List<Write> all = new ArrayList<>(phase2);
        all.addAll(executionWrites(project, UUID.randomUUID().toString()));
        return all;
    }

    /** Phase 4～5 的寫入端點：啟動、暫停、恢復、取消、還原、審核、確認告警。 */
    private static List<Write> executionWrites(String project, String run) {
        return List.of(
                new Write("POST", "/api/v1/projects/" + project + "/execute", Map.of()),
                new Write("POST", "/api/v1/executions/" + run + "/pause", null),
                new Write("POST", "/api/v1/executions/" + run + "/resume", null),
                new Write("POST", "/api/v1/executions/" + run + "/cancel", null),
                new Write("POST", "/api/v1/executions/" + run + "/restore/" + run, null),
                new Write("POST", "/api/v1/executions/" + run + "/review/" + run, Map.of("decision", "APPROVE")),
                new Write("POST", "/api/v1/monitor/alerts/" + run + "/acknowledge", null));
    }

    private Resp call(String token, Write write) {
        return switch (write.method()) {
            case "POST" -> write.body() == null ? api.post(token, write.url()) : api.post(token, write.url(), write.body());
            case "PUT" -> api.put(token, write.url(), write.body());
            case "DELETE" -> api.delete(token, write.url());
            default -> throw new IllegalArgumentException(write.method());
        };
    }

    @Test
    void viewerCanReadEverythingButEveryWriteEndpointIs403AndChangesNothing() {
        String project = createProject("Rbac");
        String goal = createGoal(project, "G");
        String task = createTask(goal, "T");

        for (String url : List.of("/api/v1/projects", "/api/v1/projects/" + project,
                "/api/v1/projects/" + project + "/goals", "/api/v1/goals/" + goal, "/api/v1/goals/" + goal + "/tasks",
                "/api/v1/tasks/" + task)) {
            assertThat(api.get(viewer(), url).status()).as("GET " + url).isEqualTo(200);
        }
        for (Write write : everyWriteEndpoint(project, goal, task)) {
            Resp resp = call(viewer(), write);
            assertThat(resp.status()).as(write.method() + " " + write.url()).isEqualTo(403);
            assertThat(resp.<Integer>read("$.code")).isEqualTo(403);
            assertThat(resp.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
            assertThat(resp.<String>read("$.traceId")).isEqualTo(resp.header("X-Trace-Id"));
        }
        assertThat(api.get(viewer(), "/api/v1/projects/" + project).<String>read("$.data.name"))
                .as("403 的寫入不可生效").isEqualTo("Rbac");
        assertThat(api.get(viewer(), "/api/v1/tasks/" + task).status()).isEqualTo(200);
    }

    @Test
    void everyWriteEndpointRequiresAuthenticationWith401() {
        String project = createProject("Rbac anon");
        String goal = createGoal(project, "G");
        String task = createTask(goal, "T");
        for (Write write : everyWriteEndpoint(project, goal, task)) {
            Resp resp = call(null, write);
            assertThat(resp.status()).as(write.method() + " " + write.url()).isEqualTo(401);
            assertThat(resp.<String>read("$.reason")).isEqualTo("UNAUTHENTICATED");
        }
        assertThat(api.get(null, "/api/v1/projects").status()).isEqualTo(401);
        assertThat(api.get(null, "/api/v1/tasks/" + task).status()).isEqualTo(401);
    }

    @Test
    void operatorAndAdminMayWrite() {
        for (String token : List.of(operator(), admin())) {
            Resp create = api.post(token, "/api/v1/projects", Map.of("name", "By " + UUID.randomUUID(),
                    "executionPath", "/x", "passCriteria", "c"));
            assertThat(create.status()).isEqualTo(201);
            assertThat(api.delete(token, "/api/v1/projects/" + create.id()).status()).isEqualTo(204);
        }
    }

    @Test
    void viewerReadsTheExecutionAndMonitoringEndpointsAndAnonymousGets401() {
        String project = createProject("Rbac exec read");
        String run = UUID.randomUUID().toString();
        for (String url : List.of("/api/v1/projects/" + project + "/executions",
                "/api/v1/monitor/projects/" + project + "/metrics",
                "/api/v1/monitor/projects/" + project + "/token-trend",
                "/api/v1/monitor/projects/" + project + "/task-trend",
                "/api/v1/monitor/projects/" + project + "/alerts",
                "/api/v1/monitor/projects/" + project + "/logs",
                "/api/v1/monitor/projects/" + project + "/report")) {
            assertThat(api.get(viewer(), url).status()).as("viewer GET " + url).isEqualTo(200);
            assertThat(api.get(null, url).status()).as("匿名 GET " + url).isEqualTo(401);
        }
        for (String suffix : List.of("", "/steps", "/dag", "/checkpoints")) {
            String url = "/api/v1/executions/" + run + suffix;
            assertThat(api.get(viewer(), url).status()).as("viewer 通過授權層、到 controller 才得 404：GET " + url)
                    .isEqualTo(404);
            assertThat(api.get(null, url).status()).as("匿名 GET " + url).isEqualTo(401);
        }
    }

    /** v1.4（§0.8）：新增的兩個 GET 落在「GET /api/v1/** 為 VIEWER 以上」的既有規則，不必動 matcher——這裡把它釘成會失敗的事實。 */
    @Test
    void viewerReadsTheEngineStatusAndThePendingSignoffListAndAnonymousGets401() {
        for (String url : List.of("/api/v1/engines/sdd", "/api/v1/signoffs/pending")) {
            for (String token : List.of(viewer(), operator(), admin())) {
                assertThat(api.get(token, url).status()).as("GET " + url).isEqualTo(200);
            }
            assertThat(api.get(null, url).status()).as("匿名 GET " + url).isEqualTo(401);
        }
    }

    @Test
    void operatorAndAdminPassTheAuthorizationLayerOfEveryExecutionWriteAndReachTheController() {
        // 隨機 UUID 的專案／批次不存在 ⇒ 404 是 controller（用例）回的：證明 403／401 都不是它們造成的
        List<Write> writes = executionWrites(UUID.randomUUID().toString(), UUID.randomUUID().toString());
        for (String token : List.of(operator(), admin())) {
            for (Write write : writes) {
                Resp resp = call(token, write);
                assertThat(resp.status()).as(write.method() + " " + write.url()).isEqualTo(404);
                assertThat(resp.<Integer>read("$.code")).isEqualTo(404);
            }
        }
    }

    @Test
    void publicEndpointsNeedNoToken() {
        assertThat(api.get(null, "/actuator/health").status()).isEqualTo(200);
        assertThat(api.get(null, "/actuator/prometheus").status()).isEqualTo(200);
        assertThat(api.get(null, "/v3/api-docs").status()).isEqualTo(200);
        assertThat(api.get(null, "/swagger-ui/index.html").status()).isEqualTo(200);
        assertThat(api.get(null, "/swagger-ui.html").status()).as("導向 /swagger-ui/index.html").isEqualTo(302);
        assertThat(api.post(null, "/api/v1/auth/login", Map.of("username", "x", "password", "y")).status())
                .as("登入端點本身免認證（帳密錯誤是 401，但不是因為沒 token）").isEqualTo(401);
        assertThat(api.post(null, "/api/v1/auth/logout", Map.of("refreshToken", "not-a-token")).status())
                .as("v1.4：登出端點同樣免認證（登出時 access token 可能已過期，仍必須能撤銷 refresh token）").isEqualTo(204);
    }

    @Test
    void otherActuatorEndpointsAreAdminOnly() {
        assertThat(api.get(null, "/actuator/info").status()).isEqualTo(401);
        assertThat(api.get(viewer(), "/actuator/info").status()).isEqualTo(403);
        assertThat(api.get(operator(), "/actuator/info").status()).isEqualTo(403);
        assertThat(api.get(admin(), "/actuator/info").status()).isEqualTo(200);
    }

    @Test
    void unknownPathsAre404ForSignedInUsersAnd401ForAnonymous() {
        assertThat(api.get(viewer(), "/api/v1/nope").status()).isEqualTo(404);
        assertThat(api.get(admin(), "/no/such/path").status()).isEqualTo(404);
        assertThat(api.get(null, "/no/such/path").status()).isEqualTo(401);
    }

    @Test
    void corsAllowsOnlyTheConfiguredOrigin() {
        Resp allowed = api.send(null, MockMvcRequestBuilders.options("/api/v1/projects")
                .header(HttpHeaders.ORIGIN, "http://localhost:3000")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "POST")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS, "authorization,content-type"));
        assertThat(allowed.status()).isEqualTo(200);
        assertThat(allowed.header(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isEqualTo("http://localhost:3000");
        assertThat(allowed.header(HttpHeaders.ACCESS_CONTROL_ALLOW_METHODS)).contains("POST", "PUT", "DELETE");

        Resp denied = api.send(null, MockMvcRequestBuilders.options("/api/v1/projects")
                .header(HttpHeaders.ORIGIN, "https://evil.example")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "POST"));
        assertThat(denied.status()).isEqualTo(403);
        assertThat(denied.header(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isNull();

        Resp simple = api.send(admin(), MockMvcRequestBuilders.get("/api/v1/projects")
                .header(HttpHeaders.ORIGIN, "http://localhost:3000"));
        assertThat(simple.header(HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS)).contains("X-Trace-Id");
    }

    @Test
    void corsExposesEveryResponseHeaderTheBrowserFrontendNeedsToRead() {
        Resp simple = api.send(viewer(), MockMvcRequestBuilders.get("/api/v1/projects")
                .header(HttpHeaders.ORIGIN, "http://localhost:3000"));
        assertThat(simple.header(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isEqualTo("http://localhost:3000");
        assertThat(simple.header(HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS))
                .as("追蹤碼、審核 RETRY／SKIP 的新批次 id、限流等待秒數、報表檔名：少一個，跨來源的前端就讀不到（契約 §0.7）")
                .contains("X-Trace-Id", "X-Follow-Up-Run-Id", "Retry-After", "Content-Disposition");

        String project = createProject("Cors report");
        Resp report = api.send(viewer(), MockMvcRequestBuilders
                .get("/api/v1/monitor/projects/" + project + "/report")
                .header(HttpHeaders.ORIGIN, "http://localhost:3000"));
        assertThat(report.status()).isEqualTo(200);
        assertThat(report.header(HttpHeaders.CONTENT_DISPOSITION)).startsWith("attachment");
        assertThat(report.header(HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS)).contains("Content-Disposition");
    }

    @Test
    void theCorsPreflightOfAnSseReconnectAllowsLastEventIdAndAuthorizationButNothingElse() {
        String path = "/api/v1/stream/executions/" + UUID.randomUUID() + "/logs";
        Resp preflight = api.send(null, MockMvcRequestBuilders.options(path)
                .header(HttpHeaders.ORIGIN, "http://localhost:3000")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "GET")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS, "last-event-id,authorization,accept"));
        assertThat(preflight.status()).isEqualTo(200);
        assertThat(preflight.header(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isEqualTo("http://localhost:3000");
        assertThat(preflight.header(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS)).containsIgnoringCase("Last-Event-ID")
                .containsIgnoringCase("Authorization");

        Resp refused = api.send(null, MockMvcRequestBuilders.options(path)
                .header(HttpHeaders.ORIGIN, "http://localhost:3000")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "GET")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS, "x-not-in-the-allow-list"));
        assertThat(refused.status()).as("沒列在 allowedHeaders 的請求標頭，預檢被拒").isEqualTo(403);
    }

    @Test
    void roleIsTakenFromTheTokenNotFromAnythingTheClientSends() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("name", "Role spoof");
        body.put("executionPath", "/x");
        body.put("passCriteria", "c");
        body.put("role", "ADMIN");
        Resp resp = api.send(viewer(), MockMvcRequestBuilders.post("/api/v1/projects")
                .header("X-Role", "ADMIN").contentType(MediaType.APPLICATION_JSON).content(ApiClient.toJson(body)));
        assertThat(resp.status()).isEqualTo(403);
    }
}
