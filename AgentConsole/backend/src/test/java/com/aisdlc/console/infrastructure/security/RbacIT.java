package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.ResearchFixtures;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * RBAC（NFR-9.2-02；Architecture §8.2）：VIEWER 只能讀；OPERATOR／ADMIN 可寫；免認證端點不需 token；
 * 其餘 /actuator/** 只有 ADMIN。每一個寫入端點都逐一驗，避免日後新增端點時漏掉授權規則。
 *
 * <p>ResearchToPRD P0（TCS-ResearchToPRD-P0 AT-960-5-1、5-2、5-3、15-9）：本類別改繼承 {@link AbstractExecutionIT}（RANDOM_PORT＋迷你 Bridge；MockMvc 照常可用），
 * 才數得到「被授權鏈擋下的請求有沒有真的沒到 Bridge」；既有案例的斷言與資料都不動。
 */
class RbacIT extends AbstractExecutionIT {

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
        all.addAll(sddWrites(project));
        return all;
    }

    /** v1.5（整合輪 115）的兩個 SDD 寫入端點：核准凍結（人工閘）與編輯 FSM 專案綁定。 */
    private static List<Write> sddWrites(String project) {
        return List.of(
                new Write("POST", "/api/v1/projects/" + project + "/sdd/freeze", Map.of("reason", "規格已核准")),
                new Write("PUT", "/api/v1/projects/" + project + "/sdd-binding", Map.of("sddProject", "rbac-key")));
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
            case "PATCH" -> api.raw(token, HttpMethod.PATCH, write.url(), ApiClient.toJson(write.body()));
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
        for (String suffix : List.of("", "/steps", "/dag", "/checkpoints", "/rtm")) {
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
        String unknown = "/api/v1/engines/sdd?projectId=" + UUID.randomUUID();
        assertThat(api.get(viewer(), unknown).status()).as("v1.5：projectId 找不到專案 → 404（VIEWER 通過授權層）").isEqualTo(404);
        assertThat(api.get(null, unknown).status()).as("匿名 GET " + unknown).isEqualTo(401);
    }

    @Test
    void operatorAndAdminPassTheAuthorizationLayerOfEveryExecutionWriteAndReachTheController() {
        // 隨機 UUID 的專案／批次不存在 ⇒ 404 是 controller（用例）回的：證明 403／401 都不是它們造成的
        String unknownProject = UUID.randomUUID().toString();
        List<Write> writes = new ArrayList<>(executionWrites(unknownProject, UUID.randomUUID().toString()));
        writes.addAll(sddWrites(unknownProject));
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

    // ── ResearchToPRD P0：研究面的角色矩陣（TCS-ResearchToPRD-P0 §3） ───────────────────────────────

    private static final String RESEARCH = "/api/v1/research";
    private static final Path SECURITY_CONFIG = Path.of("src", "main", "java", "com", "aisdlc", "console", "infrastructure", "config", "SecurityConfig.java");

    private static Map<String, Object> researchCreateBody(String slug) {
        Map<String, Object> layers = new LinkedHashMap<>();
        layers.put("academic", true);
        layers.put("industry", false);
        layers.put("oss", true);
        layers.put("community", false);
        Map<String, Object> scope = new LinkedHashMap<>();
        scope.put("layers", layers);
        scope.put("inScope", List.of("範圍內一項"));
        scope.put("recencyYears", 2);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("slug", slug);
        body.put("title", "RBAC 研究");
        body.put("topic", "RBAC 議題");
        body.put("scope", scope);
        body.put("depthLevel", "STANDARD");
        return body;
    }

    private static Map<String, Object> allowlistBody() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("listKind", "WEB");
        body.put("host", "example.com");
        body.put("layer", "INDUSTRY");
        body.put("purpose", "產業部落格");
        body.put("tosNote", "條款已讀");
        body.put("minIntervalSeconds", 5);
        body.put("tosAcknowledged", false);
        return body;
    }

    private static Map<String, Object> approveBody() {
        return Map.of("prdVersion", 1, "expectedDigests", Map.of("01_specs/PRD-v1.0.0.md", "sha256:" + "a".repeat(64)));
    }

    /** AT-960-5-1：approve、return、POST allowlist、PATCH allowlist/{id} 只有 ADMIN；被擋的請求一個都不到迷你 Bridge。 */
    @Test
    void AT_960_5_1_adminOnlyResearchEndpointsAre401ForAnonymousAnd403ForViewerAndOperatorAndNeverReachTheBridge() {
        UUID project = new ResearchFixtures(jdbc).project("rbac-admin-only");
        List<Write> adminOnly = List.of(
                new Write("POST", RESEARCH + "/projects/" + project + "/approve", approveBody()),
                new Write("POST", RESEARCH + "/projects/" + project + "/return", Map.of("reason", "退回修訂")),
                new Write("POST", RESEARCH + "/allowlist", allowlistBody()),
                new Write("PATCH", RESEARCH + "/allowlist/" + UUID.randomUUID(), Map.of("enabled", false)),
                // P1（AT-961-15-6）：SCR 套用僅 ADMIN（route 的 ADMIN 規則 P0 已預置，確認分流由 ResearchRouteApiIT 另驗）
                new Write("POST", RESEARCH + "/projects/" + project + "/scr/1/apply", Map.of()));

        for (Write write : adminOnly) {
            String label = write.method() + " " + write.url();
            int callsBefore = MINI.research.calls.size();

            assertThat(call(null, write).status()).as("匿名 " + label).isEqualTo(401);
            for (String token : List.of(viewer(), operator())) {
                Resp denied = call(token, write);
                assertThat(denied.status()).as(label).isEqualTo(403);
                assertThat(denied.<Integer>read("$.code")).isEqualTo(403);
                assertThat(denied.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
                assertThat(denied.<String>read("$.traceId")).isEqualTo(denied.header("X-Trace-Id"));
            }
            assertThat(MINI.research.calls).as(label + "：匿名、VIEWER、OPERATOR 的請求都沒有到迷你 Bridge").hasSize(callsBefore);

            long writesBefore = MINI.research.writeCount();
            Resp admin = call(admin(), write);
            assertThat(admin.status()).as("ADMIN 通過授權層：" + label).isNotIn(401, 403);
            assertThat(MINI.research.writeCount()).as(label + "：ADMIN 的請求到達迷你 Bridge 恰一次").isEqualTo(writesBefore + 1);
        }
    }

    /** AT-960-5-2：一般寫入端點 VIEWER 403（Bridge 請求數 0）、OPERATOR 與 ADMIN 通過；全部研究 GET 三種角色皆可讀、匿名 401。 */
    @Test
    void AT_960_5_2_generalResearchWritesNeedOperatorAndEveryResearchGetIsOpenToAViewerButNotToAnAnonymousCaller() {
        UUID project = new ResearchFixtures(jdbc).project("rbac-general");
        MINI.sdd.addProject("research-rbac-general", "HUMAN_PENDING", 1, "sid-rbac", "2026-11-02T00:00:00+00:00", new MiniBridge.Sdd.SddRetry(0, null),
                Map.of("count", 0, "items", List.of()));
        String base = RESEARCH + "/projects/" + project;
        List<Write> general = List.of(
                new Write("POST", RESEARCH + "/projects", researchCreateBody("rbac-created")),
                new Write("PUT", base + "/prd", Map.of("baseVersion", 0, "content", "# PRD", "changeSummary", "第一版")),
                new Write("POST", base + "/stages/research", Map.of()),
                // P1（AT-961-15-6）：OPERATOR 以上的四個新寫入
                new Write("POST", base + "/route/preview", Map.of("track", "A")),
                new Write("POST", base + "/scr", Map.of("kind", "MINOR", "sourceKind", "HUMAN", "reason", "規格調整")),
                new Write("POST", base + "/decomposition", Map.of()),
                new Write("POST", base + "/cancel", null),
                new Write("POST", base + "/reconcile", null),
                new Write("POST", base + "/archive", null),
                new Write("POST", base + "/restore", null),
                new Write("POST", base + "/reinit", Map.of()));

        for (Write write : general) {
            String label = write.method() + " " + write.url();
            int callsBefore = MINI.research.calls.size();
            Resp viewerResp = call(viewer(), write);
            assertThat(viewerResp.status()).as("VIEWER " + label).isEqualTo(403);
            assertThat(viewerResp.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
            assertThat(call(null, write).status()).as("匿名 " + label).isEqualTo(401);
            assertThat(MINI.research.calls).as(label + "：VIEWER 與匿名的請求都沒有到迷你 Bridge").hasSize(callsBefore);
        }
        for (String token : List.of(operator(), admin())) {
            for (Write write : general) {
                String label = write.method() + " " + write.url();
                long writesBefore = MINI.research.writeCount();
                Resp resp = call(token, write);
                assertThat(resp.status()).as("通過授權層（不是 401 或 403）：" + label).isNotIn(401, 403);
                assertThat(MINI.research.writeCount()).as(label + "：到達迷你 Bridge 恰一次（二次呼叫的 4xx 也是 Bridge 的回應）").isEqualTo(writesBefore + 1);
            }
        }

        // P1：簽核需要已分流與有拆解才會到 Bridge（先走既有 import 路徑），這裡只驗授權層：VIEWER 403、匿名 401、OPERATOR 與 ADMIN 通過
        Write signoff = new Write("POST", base + "/decomposition/signoff", Map.of());
        assertThat(call(viewer(), signoff).status()).isEqualTo(403);
        assertThat(call(null, signoff).status()).isEqualTo(401);
        assertThat(call(operator(), signoff).status()).isNotIn(401, 403);
        assertThat(call(admin(), signoff).status()).isNotIn(401, 403);

        List<String> gets = List.of(RESEARCH + "/capabilities", RESEARCH + "/projects", RESEARCH + "/allowlist", base, base + "/events", base + "/sources",
                base + "/evidence", base + "/prd/versions", base + "/prd/versions/1", base + "/review-rounds", base + "/review-rounds/1", base + "/fsm",
                base + "/records/audit", base + "/route", base + "/scr", base + "/decomposition");
        for (String url : gets) {
            for (String token : List.of(viewer(), operator(), admin())) {
                Resp resp = api.get(token, url);
                assertThat(resp.status()).as("GET " + url).isIn(200, 404);
                if (resp.status() == 404) {
                    assertThat(resp.<String>read("$.reason")).as("GET " + url + " 的 404").isEqualTo("research_not_found");
                }
            }
            assertThat(api.get(null, url).status()).as("匿名 GET " + url).isEqualTo(401);
        }
        String ghost = RESEARCH + "/projects/" + UUID.randomUUID();
        for (String suffix : List.of("", "/events", "/sources", "/evidence", "/prd/versions", "/prd/versions/1", "/review-rounds", "/review-rounds/1", "/fsm",
                "/records/audit")) {
            Resp resp = api.get(viewer(), ghost + suffix);
            assertThat(resp.status()).as("專案不存在時授權層放行、由 controller 回 404：" + suffix).isEqualTo(404);
            assertThat(resp.<String>read("$.reason")).isEqualTo("research_not_found");
        }
    }

    /** {@code SecurityConfig} 原始碼裡的一條授權規則：行號、matcher 引數（空白折疊）、角色引數。 */
    private record Rule(int line, String matcher, String role) {
    }

    private static List<Rule> authorizationRules() {
        String source;
        try {
            source = Files.readString(SECURITY_CONFIG, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("讀不到 " + SECURITY_CONFIG.toAbsolutePath(), e);
        }
        Matcher found = Pattern.compile("\\.requestMatchers\\(([^)]*)\\)\\s*\\.(hasRole|hasAnyRole|permitAll)\\(([^)]*)\\)").matcher(source);
        List<Rule> rules = new ArrayList<>();
        while (found.find()) {
            int line = 1 + (int) source.substring(0, found.start()).chars().filter(c -> c == '\n').count();
            rules.add(new Rule(line, found.group(1).replaceAll("\\s+", " ").strip(), found.group(2) + "(" + found.group(3).strip() + ")"));
        }
        return rules;
    }

    /** AT-960-5-3：研究 ADMIN 規則逐條置於通用規則之前；route/preview 不在其中；既有規則的內容與次序不變。 */
    @Test
    void AT_960_5_3_everyResearchAdminRuleSitsBeforeTheGenericRuleAndTheExistingRulesKeepTheirOrder() {
        List<Rule> rules = authorizationRules();
        List<Rule> research = rules.stream().filter(rule -> rule.matcher().contains("/api/v1/research/")).toList();
        Rule generic = rules.stream().filter(rule -> rule.matcher().equals("\"/api/v1/**\"")).findFirst().orElseThrow();

        assertThat(research).extracting(Rule::matcher).containsExactly(
                "HttpMethod.POST, \"/api/v1/research/projects/*/approve\"",
                "HttpMethod.POST, \"/api/v1/research/projects/*/return\"",
                "HttpMethod.POST, \"/api/v1/research/projects/*/route\"",
                "HttpMethod.POST, \"/api/v1/research/projects/*/scr/*/apply\"",
                "HttpMethod.POST, \"/api/v1/research/projects/*/gates\"",
                "HttpMethod.POST, \"/api/v1/research/projects/*/delivery/tag\"",
                "HttpMethod.POST, \"/api/v1/research/projects/*/delivery/pr\"",
                "HttpMethod.POST, \"/api/v1/research/allowlist\"",
                "HttpMethod.PATCH, \"/api/v1/research/allowlist/*\"");
        assertThat(research).as("每條研究規則都是 ADMIN 專屬").extracting(Rule::role).containsOnly("hasRole(\"ADMIN\")");
        assertThat(research).as("每條研究規則的行號都小於通用 /api/v1/** 規則（先中者定案）").allSatisfy(rule -> assertThat(rule.line()).isLessThan(generic.line()));
        assertThat(research).as("…/reinit 與 …/route/preview 都不在 ADMIN 規則內").noneMatch(rule -> rule.matcher().contains("reinit") || rule.matcher().contains("preview"));

        List<String> others = rules.stream().filter(rule -> !research.contains(rule)).map(Rule::matcher).toList();
        assertThat(others).as("拿掉研究規則之後剩下的，恰為既有的規則序列（si、issues、sysadmin、settings、通用都不動）").containsExactly(
                "HttpMethod.POST, \"/api/v1/auth/login\", \"/api/v1/auth/refresh\", \"/api/v1/auth/logout\"",
                "\"/actuator/health\", \"/actuator/health/**\", \"/actuator/prometheus\"",
                "\"/v3/api-docs\", \"/v3/api-docs/**\", \"/swagger-ui.html\", \"/swagger-ui/**\"",
                "HttpMethod.GET, \"/api/v1/**\"",
                "HttpMethod.POST, \"/api/v1/si/**\"",
                "HttpMethod.PUT, \"/api/v1/issues/**\"",
                "HttpMethod.DELETE, \"/api/v1/issues/**\"",
                "HttpMethod.POST, \"/api/v1/sysadmin/**\"",
                "\"/api/v1/settings/**\"",
                "\"/api/v1/**\"",
                "\"/actuator/**\"");
        int lastExisting = rules.stream().filter(rule -> rule.matcher().contains("/sysadmin/")).findFirst().orElseThrow().line();
        int settings = rules.stream().filter(rule -> rule.matcher().contains("/settings/")).findFirst().orElseThrow().line();
        assertThat(research).as("研究規則夾在 sysadmin 與 settings 之間").allSatisfy(rule -> assertThat(rule.line()).isBetween(lastExisting + 1, settings - 1));

        // 行為探針：精確路徑的 ADMIN 規則真的生效，route/preview 則是 OPERATOR 可用
        UUID project = new ResearchFixtures(jdbc).project("rbac-order");
        for (String path : List.of("approve", "return", "route", "scr/1/apply", "gates", "delivery/tag", "delivery/pr")) {
            String url = RESEARCH + "/projects/" + project + "/" + path;
            Resp operator = api.post(operator(), url, Map.of());
            assertThat(operator.status()).as("OPERATOR POST " + path).isEqualTo(403);
            assertThat(operator.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
            assertThat(api.post(admin(), url, Map.of()).status()).as("ADMIN POST " + path + " 通過授權層").isNotIn(401, 403);
        }
        String preview = RESEARCH + "/projects/" + project + "/route/preview";
        assertThat(api.post(operator(), preview, Map.of()).status()).as("OPERATOR 通過 route/preview 的授權層").isNotIn(401, 403);
        assertThat(api.post(viewer(), preview, Map.of()).status()).as("VIEWER 仍被通用 POST 規則擋下").isEqualTo(403);
        assertThat(api.post(operator(), RESEARCH + "/projects/" + project + "/x/approve", Map.of()).status())
                .as("* 只比對單一路徑段：多一段的路徑不命中 ADMIN 規則").isNotEqualTo(403);
    }

    /** AT-960-15-9：換世代（generation:"next"）只有 ADMIN——角色檢查在服務層；不帶 generation 的重試初始化 OPERATOR 仍可用。 */
    @Test
    void AT_960_15_9_reinitWithGenerationNextIsAdminOnlyInTheServiceLayerWhileTheRetryInitModeStaysOperator() {
        ResearchFixtures fx = new ResearchFixtures(jdbc);
        UUID escalated = fx.project("rbac-escalated", "studio", "REVIEWING", "ESCALATED", "");
        UUID failedInit = fx.project("rbac-init-failed", "topic", "INGESTED", "FAILED", "init_failed:fsm");
        Map<String, Object> next = Map.of("generation", "next", "reason", "放棄舊鍵，換世代重審");
        String nextUrl = RESEARCH + "/projects/" + escalated + "/reinit";
        String retryUrl = RESEARCH + "/projects/" + failedInit + "/reinit";

        Resp viewerNext = api.post(viewer(), nextUrl, next);
        assertThat(viewerNext.status()).isEqualTo(403);
        assertThat(viewerNext.<Integer>read("$.code")).isEqualTo(403);
        assertThat(viewerNext.<String>read("$.reason")).as("VIEWER：既有授權鏈（通用 POST 規則要求 OPERATOR 以上）").isEqualTo("ACCESS_DENIED");
        Resp operatorNext = api.post(operator(), nextUrl, next);
        assertThat(operatorNext.status()).isEqualTo(403);
        assertThat(operatorNext.<String>read("$.reason")).as("OPERATOR：服務層的角色檢查，與授權鏈的 ACCESS_DENIED 不同").isEqualTo("research_write_forbidden");
        assertThat(MINI.research.calls).as("VIEWER 與 OPERATOR 被擋：迷你 Bridge 請求數皆為 0").isEmpty();

        Resp adminNext = api.post(admin(), nextUrl, next);
        assertThat(adminNext.status()).as("ADMIN 通過").isEqualTo(200);
        assertThat(MINI.research.calls).as("ADMIN 的換世代恰一個 :reinit").hasSize(1);
        assertThat(MINI.research.calls.get(0).path()).endsWith("/" + escalated + ":reinit");

        MINI.research.calls.clear();
        Resp operatorRetry = api.post(operator(), retryUrl, Map.of());
        assertThat(operatorRetry.status()).as("不帶 generation 的重試初始化：OPERATOR 仍可用").isEqualTo(200);
        assertThat(MINI.research.calls).hasSize(1);
        assertThat(MINI.research.calls.get(0).body()).as("重試初始化不帶 generation").doesNotContainKey("generation");
        Resp viewerRetry = api.post(viewer(), retryUrl, Map.of());
        assertThat(viewerRetry.status()).isEqualTo(403);
        assertThat(viewerRetry.<String>read("$.reason")).as("既有 OPERATOR 以上的寫入規則不變").isEqualTo("ACCESS_DENIED");
        assertThat(MINI.research.calls).as("VIEWER 的重試初始化沒到 Bridge").hasSize(1);

        assertThat(authorizationRules().stream().filter(rule -> rule.matcher().contains("/api/v1/research/")))
                .as("SecurityConfig 的研究 ADMIN matcher 清單不含 …/reinit（同路徑同方法無法依請求本文分流，所以分流在服務層）")
                .noneMatch(rule -> rule.matcher().contains("reinit"));
    }

    // ── PKG-API-P2（TCS-ResearchToPRD-P2 AC-962-4、19、20、24）：內環閘登錄與交付寫入僅 ADMIN；四個新 GET 為 VIEWER 以上 ──

    private List<Write> p2AdminWrites(UUID project) {
        String base = RESEARCH + "/projects/" + project;
        return List.of(
                new Write("POST", base + "/gates", Map.of("gate", "RTM_VERIFY", "result", "PASS", "reviewerIndependent", false)),
                new Write("POST", base + "/delivery/tag", Map.of("tagName", "v1.0.0")),
                new Write("POST", base + "/delivery/pr", Map.of("bodyPreviewAck", true)));
    }

    private void assertDeniedBeforeAnything(String token, String who, UUID project, List<String> tables) {
        Map<String, Long> before = new java.util.LinkedHashMap<>();
        for (String table : tables) {
            before.put(table, jdbc.queryForObject("select count(*) from console." + table, Long.class));
        }
        int callsBefore = MINI.research.calls.size();
        for (Write write : p2AdminWrites(project)) {
            Resp resp = call(token, write);
            assertThat(resp.status()).as(who + " " + write.url()).isEqualTo(403);
            assertThat(resp.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
        }
        assertThat(MINI.research.calls.size()).as(who + "：被擋的請求一個都不到迷你 Bridge").isEqualTo(callsBefore);
        for (String table : tables) {
            assertThat(jdbc.queryForObject("select count(*) from console." + table, Long.class)).as(table + " 列數不變").isEqualTo(before.get(table));
        }
    }

    /** AT-962-4-E-1：OPERATOR 呼叫 gates（與 tag、pr）回 403 授權鏈拒絕，Bridge 請求 0，研究表列數不變。 */
    @Test
    void AT_962_4_E_1_operatorGetsAccessDeniedOnGatesAndNothingReachesTheBridgeOrTheResearchTables() {
        UUID project = new ResearchFixtures(jdbc).project("rbac-p2-operator");
        assertDeniedBeforeAnything(operator(), "OPERATOR", project, List.of("research_gate_decisions", "research_events", "research_deliveries"));
    }

    /** AT-962-4-E-2：VIEWER 同為授權鏈拒絕。 */
    @Test
    void AT_962_4_E_2_viewerGetsTheSameAccessDeniedAsOperatorOnGates() {
        UUID project = new ResearchFixtures(jdbc).project("rbac-p2-viewer");
        assertDeniedBeforeAnything(viewer(), "VIEWER", project, List.of("research_gate_decisions", "research_events", "research_deliveries"));
        assertThat(call(null, p2AdminWrites(project).get(0)).status()).as("匿名").isEqualTo(401);
    }

    /** AT-962-19-E-1：OPERATOR 呼叫 tag 回 403、不留任何交付列。 */
    @Test
    void AT_962_19_E_1_operatorCannotCreateATag() {
        UUID project = new ResearchFixtures(jdbc).project("rbac-p2-tag-op");
        int callsBefore = MINI.research.calls.size();
        Resp resp = api.post(operator(), RESEARCH + "/projects/" + project + "/delivery/tag", Map.of("tagName", "v1.0.0"));
        assertThat(resp.status()).isEqualTo(403);
        assertThat(resp.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
        assertThat(MINI.research.calls.size()).isEqualTo(callsBefore);
        assertThat(jdbc.queryForObject("select count(*) from console.research_deliveries where research_id = ?", Long.class, project)).isZero();
    }

    /** AT-962-19-E-2：VIEWER 呼叫 tag 回 403（與 OPERATOR 同為授權鏈拒絕）。 */
    @Test
    void AT_962_19_E_2_viewerCannotCreateATag() {
        UUID project = new ResearchFixtures(jdbc).project("rbac-p2-tag-viewer");
        int callsBefore = MINI.research.calls.size();
        Resp resp = api.post(viewer(), RESEARCH + "/projects/" + project + "/delivery/tag", Map.of("tagName", "v1.0.0"));
        assertThat(resp.status()).isEqualTo(403);
        assertThat(resp.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
        assertThat(MINI.research.calls.size()).isEqualTo(callsBefore);
    }

    /** AT-962-20-E-1：OPERATOR 與 VIEWER 呼叫 pr 皆 403，Bridge 請求 0。 */
    @Test
    void AT_962_20_E_1_operatorAndViewerCannotCreateAPullRequest() {
        UUID project = new ResearchFixtures(jdbc).project("rbac-p2-pr");
        int callsBefore = MINI.research.calls.size();
        for (String token : List.of(operator(), viewer())) {
            Resp resp = api.post(token, RESEARCH + "/projects/" + project + "/delivery/pr", Map.of("bodyPreviewAck", true));
            assertThat(resp.status()).isEqualTo(403);
            assertThat(resp.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
        }
        assertThat(MINI.research.calls.size()).isEqualTo(callsBefore);
    }

    /** AT-962-24-4：四個新 GET（kanban、healing、delivery、delivery/traceability）VIEWER 可讀、匿名 401；SecurityConfig 的 ADMIN 規則三條不動。 */
    @Test
    void AT_962_24_4_theFourNewReadEndpointsAreViewerUpAndAnonymousIs401() {
        UUID project = new ResearchFixtures(jdbc).project("rbac-p2-reads");
        for (String path : List.of("kanban", "healing", "delivery")) {
            String url = RESEARCH + "/projects/" + project + "/" + path;
            assertThat(api.get(viewer(), url).status()).as("VIEWER GET " + path).isEqualTo(200);
            assertThat(api.get(null, url).status()).as("匿名 GET " + path).isEqualTo(401);
        }
        String trace = RESEARCH + "/projects/" + project + "/delivery/traceability";
        assertThat(api.get(viewer(), trace).status()).as("VIEWER 通過授權層（Bridge 的 409／503 另計）").isNotIn(401, 403);
        assertThat(api.get(null, trace).status()).isEqualTo(401);
        assertThat(authorizationRules().stream().filter(rule -> rule.matcher().contains("/gates") || rule.matcher().contains("/delivery/tag")
                || rule.matcher().contains("/delivery/pr"))).as("三條 ADMIN 規則已預置於 SecurityConfig").hasSize(3);
    }
}
