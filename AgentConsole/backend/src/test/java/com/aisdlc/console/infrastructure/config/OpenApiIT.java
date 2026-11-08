package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.domain.exception.ErrorReasons;
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
 * SelfImproving 決定重送去重（TCS-SelfImprovingDecideDedupe）不新增路徑與操作（77、89 不變）：對帳項 {@code SiConsoleWriteItem} 由九鍵增為十一鍵，決定端點的
 * 409 說明載明新 reason（AT-951-6-1）。
 * 系統管理／資料庫備份（TCS-SysAdminBackup-20261027 R-BK-59）再加三個路徑——{@code /sysadmin/backups}（GET）、{@code /sysadmin/backups/jobs}（GET、POST）、
 * {@code /sysadmin/backups/jobs/{id}}（GET）（路徑 74→77、操作 85→89；只增不減；sysadmin 路徑沒有 put、patch、delete）。
 * ResearchToPRD P0（TCS-ResearchToPRD-P0 §4 #14、AT-960-5-5）再加研究面 24 條路徑（{@code /research/**} 23 條與 SSE {@code /stream/research/{id}}）、26 個操作
 * （路徑 77→101、操作 89→115；只增不減；研究路徑沒有 delete）。
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
            Map.entry("/api/v1/issues/{id}/priority", List.of("delete", "put")),
            // ── 系統管理／資料庫備份：總覽與工作紀錄（GET）、僅 ADMIN 的手動觸發（POST）；沒有 put、patch、delete ──
            Map.entry("/api/v1/sysadmin/backups", List.of("get")),
            Map.entry("/api/v1/sysadmin/backups/jobs", List.of("get", "post")),
            Map.entry("/api/v1/sysadmin/backups/jobs/{id}", List.of("get")),
            // ── ResearchToPRD P0（TCS-ResearchToPRD-P0 §4 #14）：研究面 24 條路徑（含 SSE）、26 個操作；研究路徑沒有 delete ──
            Map.entry("/api/v1/research/capabilities", List.of("get")),
            Map.entry("/api/v1/research/projects", List.of("get", "post")),
            Map.entry("/api/v1/research/projects/{id}", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/events", List.of("get")),
            Map.entry("/api/v1/stream/research/{id}", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/sources", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/evidence", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/prd/versions", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/prd/versions/{n}", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/prd", List.of("put")),
            Map.entry("/api/v1/research/projects/{id}/review-rounds", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/review-rounds/{n}", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/stages/{stage}", List.of("post")),
            Map.entry("/api/v1/research/projects/{id}/approve", List.of("post")),
            Map.entry("/api/v1/research/projects/{id}/fsm", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/cancel", List.of("post")),
            Map.entry("/api/v1/research/projects/{id}/reconcile", List.of("post")),
            Map.entry("/api/v1/research/projects/{id}/archive", List.of("post")),
            Map.entry("/api/v1/research/projects/{id}/restore", List.of("post")),
            Map.entry("/api/v1/research/projects/{id}/records/audit", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/reinit", List.of("post")),
            Map.entry("/api/v1/research/projects/{id}/return", List.of("post")),
            Map.entry("/api/v1/research/allowlist", List.of("get", "post")),
            Map.entry("/api/v1/research/allowlist/{id}", List.of("patch")),
        // ── ResearchToPRD P1（TCS-ResearchToPRD-P1 AT-961-15-3）：新增 6 條路徑、9 個操作（同路徑的 get 與 post 合併計一條）──
        Map.entry("/api/v1/research/projects/{id}/route/preview", List.of("post")),
        Map.entry("/api/v1/research/projects/{id}/route", List.of("get", "post")),
        Map.entry("/api/v1/research/projects/{id}/scr", List.of("get", "post")),
        Map.entry("/api/v1/research/projects/{id}/scr/{scrNo}/apply", List.of("post")),
        Map.entry("/api/v1/research/projects/{id}/decomposition", List.of("get", "post")),
        Map.entry("/api/v1/research/projects/{id}/decomposition/signoff", List.of("post")),
            // P2＋7：kanban、gates、healing、delivery、delivery/tag、delivery/pr、delivery/traceability
            Map.entry("/api/v1/research/projects/{id}/kanban", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/gates", List.of("post")),
            Map.entry("/api/v1/research/projects/{id}/healing", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/delivery", List.of("get")),
            Map.entry("/api/v1/research/projects/{id}/delivery/tag", List.of("post")),
            Map.entry("/api/v1/research/projects/{id}/delivery/pr", List.of("post")),
            Map.entry("/api/v1/research/projects/{id}/delivery/traceability", List.of("get"))));

    /** 路徑總數與操作總數的期望值（既有 77 條、89 個，加研究面 24 條、26 個；只增不減）。 */
    private static final int EXPECTED_PATH_COUNT = 114;   // P1 自算：101＋6（route/preview、route、scr、scr/{scrNo}/apply、decomposition、decomposition/signoff）
    private static final int EXPECTED_OPERATION_COUNT = 131;   // P1 自算：115＋9（previewResearchRoute、routeResearchProject、getResearchRoute、openResearchScr、listResearchScr、applyResearchScr、getResearchDecomposition、triggerResearchDecomposition、signoffResearchDecomposition）

    private Resp docs() {
        Resp resp = api.get(null, "/v3/api-docs");
        assertThat(resp.status()).isEqualTo(200);
        return resp;
    }

    @Test
    void theDocumentListsExactlyTheEndpointsDeliveredSoFarPhaseOneTwoAndBothBackendBatons() {
        Resp docs = docs();
        Set<String> paths = new TreeSet<>(docs.<Map<String, Object>>read("$.paths").keySet());
        assertThat(paths).hasSize(EXPECTED_PATH_COUNT).containsExactlyElementsOf(EXPECTED.keySet());
        int operationCount = 0;
        for (Map.Entry<String, List<String>> expected : EXPECTED.entrySet()) {
            Map<String, Object> operations = docs.read("$.paths['" + expected.getKey() + "']");
            assertThat(new TreeSet<>(operations.keySet())).as(expected.getKey())
                    .containsExactlyElementsOf(expected.getValue());
            operationCount += operations.size();
        }
        assertThat(operationCount).as("契約 v1.5 的操作總數加 P1b 的六個 SI GET、P2b 的五個新操作、議題中心的四個操作、備份的四個操作與研究面的 26 個操作")
                .isEqualTo(EXPECTED_OPERATION_COUNT);
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
        assertThat(paths).hasSize(EXPECTED_PATH_COUNT);
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

    /** AT-962-24-3：七個 P2 操作的 operationId 逐字、路徑與方法固定，寫入端點文件化 409／422／502／503／504，讀端含 401 與 404（狀態碼集合另由三表逐一鎖住）。 */
    @Test
    void AT_962_24_3_theSevenP2OperationsDocumentTheirIdsAndFailureStatusCodes() {
        Resp docs = docs();
        String base = "/api/v1/research/projects/{id}/";
        Map<String, String> ids = new java.util.LinkedHashMap<>();
        ids.put("get kanban", "getResearchKanban");
        ids.put("post gates", "registerResearchGate");
        ids.put("get healing", "getResearchHealing");
        ids.put("get delivery", "getResearchDelivery");
        ids.put("post delivery/tag", "createResearchTag");
        ids.put("post delivery/pr", "createResearchPr");
        ids.put("get delivery/traceability", "getResearchTraceability");
        ids.forEach((key, operationId) -> {
            String method = key.substring(0, key.indexOf(' '));
            String path = base + key.substring(key.indexOf(' ') + 1);
            assertThat(docs.<String>read("$.paths['" + path + "']." + method + ".operationId")).as(key).isEqualTo(operationId);
            Set<String> codes = docs.<Map<String, Object>>read("$.paths['" + path + "']." + method + ".responses").keySet();
            assertThat(codes).as(key).contains("401", "404");
            if ("post".equals(method)) {
                assertThat(codes).as(key).contains("403", "409", "422", "502", "503", "504");
            }
        });
        assertThat(docs.<String>read("$.paths['" + base + "delivery/tag'].post.responses['502'].description")).contains("delivery_step_failed");
        assertThat(docs.<String>read("$.paths['" + base + "delivery/tag'].post.responses['409'].description")).contains("tag_exists");
    }
    /** 一個 schema 的預期：必填鍵（出現的鍵，含可空但必出現者）與可空鍵（值可為 null）。 */
    private record Shape(String schema, List<String> required, List<String> nullable) {
    }

    private static Shape shape(String schema, String required, String nullable) {
        return new Shape(schema, required.isBlank() ? List.of() : List.of(required.split(",")), nullable.isBlank() ? List.of() : List.of(nullable.split(",")));
    }

    private static boolean isNullable(Map<String, Object> property) {
        if (Boolean.TRUE.equals(property.get("nullable"))) {
            return true;
        }
        Object type = property.get("type");
        if (type instanceof List<?> types && types.contains("null")) {
            return true;
        }
        for (String combiner : List.of("oneOf", "anyOf")) {
            if (property.get(combiner) instanceof List<?> options && options.stream().anyMatch(o -> o instanceof Map<?, ?> m && "null".equals(m.get("type")))) {
                return true;
            }
        }
        return false;
    }

    /**
     * AT-962-24-2（必填與可空鎖，D-160）：P2 的 DTO 在 OpenAPI 裡「必定出現的鍵」一律進 {@code required}（含可空但必出現者），值可為 null 的鍵另標可空，
     * 只有真正可省略的鍵（請求的選填欄、只在為 true 時出現的 {@code unknown}）不在 {@code required}。FE-W3 重產型別才不會把每個欄位都變成選填，
     * 也不會把「可空」與「可省略」混為一談。
     */
    @Test
    void AT_962_24_2_theP2DtosDeclareRequiredAndNullableKeysExactly() {
        Resp docs = docs();
        List<Shape> shapes = List.of(
                shape("KanbanDto", "researchId,consoleProjectId,latestRunId,generatedAt,bridgeReachable,snapshotAt,stale,scrOpen,columns,pendingReviews,gates",
                        "consoleProjectId,latestRunId,snapshotAt"),
                shape("Columns", "decompose,tcs,implement,healing,regression", ""),
                shape("KanbanDecompose", "done,status,tasksCount,stale", ""),
                shape("KanbanTcs", "done,stage2Frozen,negotiated,fsmState", "stage2Frozen,negotiated,fsmState"),
                shape("KanbanTaskCounts", "total,running,completed,skipped,failed,escalated,retrying", ""),
                shape("KanbanImplement", "done,fsmState,tasks", "fsmState"),
                shape("KanbanHealing", "done,retryingSteps,escalatedTasks,maxRetries", ""),
                shape("KanbanRtm", "runId,atPassed,atTotal,acCovered,acTotal,acPct,fullyCovered,advisory", ""),
                shape("KanbanRegression", "done,fsmState,releaseReady,rtmAvailable,rtm", "fsmState,releaseReady,rtm"),
                shape("KanbanPendingReview", "reviewId,runId,kind,taskId,reason,createdAt,allowedDecisions", "taskId,reason"),
                shape("KanbanGate", "gate,decision,decidedBy,decidedAt,fsmStateAfter,reason", "fsmStateAfter"),
                shape("GateRegisterRequest", "gate,result", "reason,reviewReportRef,reviewerIndependent"),
                shape("GateRegisterResult", "gateDecisionId,gate,result,fsmStateBefore,nextState,escalated,flow", "fsmStateBefore,nextState"),
                shape("ResearchFlowCursor", "step,phase,status,detail", ""),
                shape("HealingDto", "researchId,rows,maxRetries,retryingSteps,escalatedTasks,logSyncedThrough,logLag,specChange", "logSyncedThrough,specChange"),
                shape("HealingRow", "runId,taskId,stepNumber,attempt,status,excerpt,occurredAt,resolved,escalated,specChangeForbidden,attribution,patchResult",
                        "attribution,patchResult"),
                shape("HealingSpecChange", "paths,detectedAt", ""),
                shape("DeliveryDto", "kind,ref,commitSha,url,rtmReportRef,fsmStateAfter,status,createdBy,createdAt,snapshotSha256",
                        "commitSha,url,rtmReportRef,fsmStateAfter,snapshotSha256"),
                shape("DeliverySnapshot", "relPath,sha256", ""),
                shape("DeliveryPreconditions", "releaseReady,rtmFull,scrOpen,hasOrigin,ghAvailable", "hasOrigin,ghAvailable"),
                shape("DeliveryOverviewDto", "deliveries,snapshot,projectRoot,containerMode,preconditions", "snapshot,projectRoot"),
                shape("TagRequest", "tagName", "message,push,createGithubRelease"),
                shape("TagResult", "delivery,snapshot,flow,fsmState", "snapshot,fsmState"),
                shape("PrRequest", "bodyPreviewAck", "branch,title"),
                shape("PrResult", "delivery,created", ""),
                shape("TraceabilityGherkin", "given,when,then", ""),
                shape("TraceabilityRow", "ac,userStory,gherkinSummary,unitStatus,e2eStatus,lastRunAt,source", "lastRunAt"),
                shape("TraceabilityTotals", "acTotal,covered,uncovered,frTotal", ""),
                shape("TraceabilityRtm", "runId,fullyCovered,acPct,advisory", "acPct"),
                shape("TraceabilityDto", "rows,totals,rtm,generatedAt", "rtm"));

        for (Shape shape : shapes) {
            String base = "$.components.schemas." + shape.schema();
            List<String> required;
            try {
                required = docs.read(base + ".required");
            } catch (com.jayway.jsonpath.PathNotFoundException e) {
                required = List.of();
            }
            assertThat(required).as(shape.schema() + ".required").containsExactlyInAnyOrderElementsOf(shape.required());
            Map<String, Object> properties = docs.read(base + ".properties");
            for (String key : properties.keySet()) {
                @SuppressWarnings("unchecked")
                Map<String, Object> property = (Map<String, Object>) properties.get(key);
                if (property.containsKey("$ref")) {
                    // springdoc 不會在 $ref 旁輸出 nullable（本專案既有慣例，例：DecompositionDto.tcs）：這幾個物件型可空鍵只鎖「必填」，可空由 FE 手動收窄（交卷列出清單）
                    assertThat(shape.nullable().contains(key) || shape.required().contains(key)).as(shape.schema() + "." + key).isTrue();
                    continue;
                }
                assertThat(isNullable(property)).as(shape.schema() + "." + key + " 的可空標記").isEqualTo(shape.nullable().contains(key));
            }
            assertThat(properties.keySet()).as(shape.schema() + " 的鍵").containsAll(shape.required());
        }
        assertThat(docs.<List<String>>read("$.components.schemas.ScrDto.required")).contains("evidenceUrl");
        assertThat(isNullable(docs.<Map<String, Object>>read("$.components.schemas.ScrDto.properties.evidenceUrl"))).isTrue();
        assertThat(docs.<List<String>>read("$.components.schemas.KanbanTcs.required")).as("unknown 只在為 true 時出現：非必填").doesNotContain("unknown");
        assertThat(docs.<List<String>>read("$.components.schemas.KanbanImplement.required")).doesNotContain("unknown");
        assertThat(docs.<List<String>>read("$.components.schemas.KanbanRegression.required")).doesNotContain("unknown");
    }
    /** AT-962-26-E-2：{@code :healing-sync} 是 console-api 的內部通知，不在任何路由與 OpenAPI 路徑（零命中）。 */
    @Test
    void AT_962_26_E_2_healingSyncIsNotAnyConsoleApiRouteOrOpenApiPath() {
        Resp docs = docs();

        assertThat(docs.<Map<String, Object>>read("$.paths").keySet()).noneMatch(path -> path.contains("healing-sync") || path.contains(":healing"));
        assertThat(docs.<Map<String, Object>>read("$.paths").keySet()).contains("/api/v1/research/projects/{id}/healing");
    }
    /**
     * AT-962-24-2（強型別）：P2 七個操作的回應與請求都是具名 schema（不是 additionalProperties 的 map），gate／result 在請求與結果都是列舉——
     * FE-W3 重產型別時才不會退化成 {@code Record<string, unknown>}；追溯表的 gherkinSummary 是物件、source 是字串陣列；{@code prdSha256} 維持 nullable。
     */
    @Test
    void AT_962_24_2_theP2OperationsUseNamedTypedSchemasWithEnumsAndNestedObjects() {
        Resp docs = docs();
        String schemas = "$.components.schemas.";

        assertThat(docs.<List<String>>read(schemas + "GateRegisterRequest.properties.gate.enum")).containsExactly("PR_REVIEW", "RTM_VERIFY", "RELEASE_READY");
        assertThat(docs.<List<String>>read(schemas + "GateRegisterRequest.properties.result.enum")).containsExactly("PASS", "FAIL");
        assertThat(docs.<List<String>>read(schemas + "GateRegisterResult.properties.gate.enum")).containsExactly("PR_REVIEW", "RTM_VERIFY", "RELEASE_READY");
        assertThat(docs.<List<String>>read(schemas + "GateRegisterResult.properties.result.enum")).containsExactly("PASS", "FAIL");
        assertThat(docs.<Map<String, Object>>read(schemas + "GateRegisterResult.properties").keySet())
                .containsExactlyInAnyOrder("gateDecisionId", "gate", "result", "fsmStateBefore", "nextState", "escalated", "flow", "replayed");
        assertThat(docs.<Map<String, Object>>read(schemas + "TagResult.properties").keySet()).containsExactlyInAnyOrder("delivery", "snapshot", "flow", "fsmState");
        assertThat(docs.<Map<String, Object>>read(schemas + "PrResult.properties").keySet()).containsExactlyInAnyOrder("delivery", "created");
        assertThat(docs.<Map<String, Object>>read(schemas + "TagRequest.properties").keySet()).containsExactlyInAnyOrder("tagName", "message", "push", "createGithubRelease");
        assertThat(docs.<Map<String, Object>>read(schemas + "PrRequest.properties").keySet()).containsExactlyInAnyOrder("branch", "title", "bodyPreviewAck");
        assertThat(docs.<Map<String, Object>>read(schemas + "TraceabilityRow.properties").keySet())
                .containsExactlyInAnyOrder("ac", "userStory", "gherkinSummary", "unitStatus", "e2eStatus", "lastRunAt", "source");
        assertThat(docs.<String>read(schemas + "TraceabilityRow.properties.source.type")).isEqualTo("array");
        assertThat(docs.<String>read(schemas + "TraceabilityRow.properties.source.items.type")).isEqualTo("string");
        assertThat(docs.<String>read(schemas + "TraceabilityRow.properties.gherkinSummary.$ref")).endsWith("/TraceabilityGherkin");
        assertThat(docs.<Map<String, Object>>read(schemas + "TraceabilityTotals.properties").keySet()).containsExactlyInAnyOrder("acTotal", "covered", "uncovered", "frTotal");
        assertThat(docs.<Map<String, Object>>read(schemas + "HealingDto.properties").keySet())
                .containsExactlyInAnyOrder("researchId", "rows", "maxRetries", "retryingSteps", "escalatedTasks", "logSyncedThrough", "logLag", "specChange");
        assertThat(docs.<Map<String, Object>>read(schemas + "KanbanDto.properties").keySet()).contains("columns", "pendingReviews", "gates", "bridgeReachable", "snapshotAt");
        assertThat(docs.<String>read("$.paths['/api/v1/research/projects/{id}/gates'].post.responses['200'].content['application/json'].schema.$ref"))
                .contains("GateRegisterResult");
        assertThat(docs.<Map<String, Object>>read(schemas + "DecompositionDto.properties.prdSha256")).as("prdSha256 維持 nullable（DB 欄可為 NULL，D-159 追認）").isNotEmpty();
    }
    /**
     * SelfImproving 決定重送去重（TCS-SelfImprovingDecideDedupe AT-951-6-1；W-D1、W-D3、W-D6）：對帳項 {@code SiConsoleWriteItem} 恰十一鍵（多 {@code dkind} 與
     * {@code supersededBy}，兩者皆非必填），決定端點的 409 與 operation 說明載明 {@code si_decision_duplicate}，其餘兩個寫入 POST 的 409 說明不含它，路徑與
     * 操作總數不變。為什麼重要：前端以 /v3/api-docs 產生型別——對帳項少一個鍵，面板就讀不到取代狀態；把新鍵標成必填，既有呼叫端與夾具全部要跟著改；
     * 而 409 說明沒載明新 reason，使用者與整合者就只會看到泛用的「與目前狀態衝突」。
     */
    @Test
    void AT_951_6_1_theConsoleWriteItemHasElevenKeysAndTheDecideEndpointDocumentsTheDuplicateReason() {
        Resp docs = docs();

        Map<String, Object> properties = docs.read("$.components.schemas.SiConsoleWriteItem.properties");
        assertThat(properties.keySet()).containsExactlyInAnyOrder("auditRef", "kind", "dkind", "user", "role", "time", "subjectId", "digest",
                "keyId", "ingested", "supersededBy");
        assertThat(docs.<List<String>>read("$.components.schemas.SiConsoleWriteItem.required"))
                .as("必填集合不變：dkind 與 supersededBy 非必填").containsExactlyInAnyOrder("auditRef", "kind", "user", "role", "time", "keyId");

        String duplicate = "si_decision_duplicate";
        // 一審 F-01：說明文字（ErrorResponseDocumentation、SiController）與前端 SI_REASONS 都寫死這個字面；常數若被改掉，線上 reason 與常數同步變、說明卻不會跟著變，
        // 光比說明含字面看不出——所以另釘「常數值就是線上字面」
        assertThat(ErrorReasons.SI_DECISION_DUPLICATE).as("ErrorReasons.SI_DECISION_DUPLICATE 的值就是線上 reason 字面").isEqualTo(duplicate);
        assertThat(docs.<String>read("$.paths['/api/v1/si/proposals/{id}/decide'].post.responses['409'].description"))
                .as("決定端點的 409 說明載明新 reason").contains(duplicate);
        assertThat(docs.<String>read("$.paths['/api/v1/si/proposals/{id}/decide'].post.description"))
                .as("postSiDecide 的 operation 說明載明新 reason").contains(duplicate);
        for (String other : List.of("/api/v1/si/observations", "/api/v1/si/observations/{id}/close")) {
            assertThat(docs.<String>read("$.paths['" + other + "'].post.responses['409'].description")).as("%s 的 409 說明不含新 reason", other)
                    .doesNotContain(duplicate);
        }
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/si/proposals/{id}/decide'].post.responses").keySet())
                .as("決定端點的回應狀態碼集合與既有相同")
                .containsExactlyInAnyOrder("201", "400", "401", "403", "409", "422", "429", "502", "503", "504");
        assertThat(docs.<Map<String, Object>>read("$.paths").keySet()).as("本鍵不新增路徑（總數隨後續鍵增為現值）").hasSize(EXPECTED_PATH_COUNT);
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
    void theSettingsCategoryIsDocumentedAsTheSevenValueEnumInTheParametersAndTheResponse() {
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

    // ── ResearchToPRD P0（TCS-ResearchToPRD-P0 AT-960-5-5；API 契約 §1.1）────────────────────────────────

    /** 研究面 25 個有 operationId 的操作（鍵＝方法加路徑）；SSE 的 {@code GET /stream/research/{id}} 契約的 operationId 欄為「—」，不在表內。 */
    private static final Map<String, String> RESEARCH_OPERATION_IDS = Map.ofEntries(
            Map.entry("get /api/v1/research/capabilities", "getResearchCapabilities"),
            Map.entry("get /api/v1/research/projects", "listResearchProjects"),
            Map.entry("post /api/v1/research/projects", "createResearchProject"),
            Map.entry("get /api/v1/research/projects/{id}", "getResearchProject"),
            Map.entry("get /api/v1/research/projects/{id}/events", "listResearchEvents"),
            Map.entry("get /api/v1/research/projects/{id}/sources", "listResearchSources"),
            Map.entry("get /api/v1/research/projects/{id}/evidence", "listResearchEvidence"),
            Map.entry("get /api/v1/research/projects/{id}/prd/versions", "listPrdVersions"),
            Map.entry("get /api/v1/research/projects/{id}/prd/versions/{n}", "getPrdVersion"),
            Map.entry("put /api/v1/research/projects/{id}/prd", "savePrdVersion"),
            Map.entry("get /api/v1/research/projects/{id}/review-rounds", "listReviewRounds"),
            Map.entry("get /api/v1/research/projects/{id}/review-rounds/{n}", "getReviewRound"),
            Map.entry("post /api/v1/research/projects/{id}/stages/{stage}", "startResearchStage"),
            Map.entry("post /api/v1/research/projects/{id}/approve", "approveResearchBaseline"),
            Map.entry("get /api/v1/research/projects/{id}/fsm", "getResearchFsm"),
            Map.entry("post /api/v1/research/projects/{id}/cancel", "cancelResearchStage"),
            Map.entry("post /api/v1/research/projects/{id}/reconcile", "reconcileResearch"),
            Map.entry("post /api/v1/research/projects/{id}/archive", "archiveResearchProject"),
            Map.entry("post /api/v1/research/projects/{id}/restore", "restoreResearchProject"),
            Map.entry("get /api/v1/research/projects/{id}/records/audit", "getResearchRecordsAudit"),
            Map.entry("post /api/v1/research/projects/{id}/reinit", "reinitResearchProject"),
            Map.entry("post /api/v1/research/projects/{id}/return", "returnResearchPrd"),
            Map.entry("get /api/v1/research/allowlist", "listResearchAllowlist"),
            Map.entry("post /api/v1/research/allowlist", "addResearchAllowlistEntry"),
            Map.entry("patch /api/v1/research/allowlist/{id}", "updateResearchAllowlistEntry"),
            // P1 的九個 operationId（D-118 ⚖P1-24）
            Map.entry("post /api/v1/research/projects/{id}/route/preview", "previewResearchRoute"),
            Map.entry("post /api/v1/research/projects/{id}/route", "routeResearchProject"),
            Map.entry("get /api/v1/research/projects/{id}/route", "getResearchRoute"),
            Map.entry("post /api/v1/research/projects/{id}/scr", "openResearchScr"),
            Map.entry("get /api/v1/research/projects/{id}/scr", "listResearchScr"),
            Map.entry("post /api/v1/research/projects/{id}/scr/{scrNo}/apply", "applyResearchScr"),
            Map.entry("get /api/v1/research/projects/{id}/decomposition", "getResearchDecomposition"),
            Map.entry("post /api/v1/research/projects/{id}/decomposition", "triggerResearchDecomposition"),
            Map.entry("post /api/v1/research/projects/{id}/decomposition/signoff", "signoffResearchDecomposition"),
            Map.entry("get /api/v1/research/projects/{id}/kanban", "getResearchKanban"),
            Map.entry("post /api/v1/research/projects/{id}/gates", "registerResearchGate"),
            Map.entry("get /api/v1/research/projects/{id}/healing", "getResearchHealing"),
            Map.entry("get /api/v1/research/projects/{id}/delivery", "getResearchDelivery"),
            Map.entry("post /api/v1/research/projects/{id}/delivery/tag", "createResearchTag"),
            Map.entry("post /api/v1/research/projects/{id}/delivery/pr", "createResearchPr"),
            Map.entry("get /api/v1/research/projects/{id}/delivery/traceability", "getResearchTraceability"));

    private static Set<String> codes(String... codes) {
        return Set.of(codes);
    }

    /**
     * 研究面 26 個操作各自會回的狀態碼集合（契約 §0.2 共通失敗表）：400＝有路徑／查詢參數或請求本文；403＝寫入（含研究專屬的 research_write_forbidden）；404＝路徑含變數；
     * 409＝有狀態規則（slug、版本、stage、核准、退回、封存、重試初始化、allowlist 重複）；422／502／503／504＝依端點（輸入閘、Bridge 失敗）；429＝所有 /api/ 端點。
     * 為什麼重要：前端以 /v3/api-docs 產生型別與錯誤處理——多文件化一個回不出來的狀態碼，前端會寫出永遠走不到的分支；少一個，前端沒有該失敗的型別。
     */
    private static final Map<String, Set<String>> RESEARCH_STATUS_CODES = Map.ofEntries(
            Map.entry("get /api/v1/research/capabilities", codes("200", "401", "429", "502", "504")),
            Map.entry("get /api/v1/research/projects", codes("200", "400", "401", "429")),
            Map.entry("post /api/v1/research/projects", codes("201", "400", "401", "403", "409", "422", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/projects/{id}", codes("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/research/projects/{id}/events", codes("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/stream/research/{id}", codes("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/research/projects/{id}/sources", codes("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/research/projects/{id}/evidence", codes("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/research/projects/{id}/prd/versions", codes("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/research/projects/{id}/prd/versions/{n}", codes("200", "400", "401", "404", "429")),
            Map.entry("put /api/v1/research/projects/{id}/prd", codes("201", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/projects/{id}/review-rounds", codes("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/research/projects/{id}/review-rounds/{n}", codes("200", "400", "401", "404", "429")),
            Map.entry("post /api/v1/research/projects/{id}/stages/{stage}", codes("202", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("post /api/v1/research/projects/{id}/approve", codes("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/projects/{id}/fsm", codes("200", "400", "401", "404", "422", "429", "502", "504")),
            Map.entry("post /api/v1/research/projects/{id}/cancel", codes("200", "400", "401", "403", "404", "429", "502", "503", "504")),
            Map.entry("post /api/v1/research/projects/{id}/reconcile", codes("200", "400", "401", "403", "404", "429", "502", "503", "504")),
            Map.entry("post /api/v1/research/projects/{id}/archive", codes("200", "400", "401", "403", "404", "409", "429", "502", "503", "504")),
            Map.entry("post /api/v1/research/projects/{id}/restore", codes("200", "400", "401", "403", "404", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/projects/{id}/records/audit", codes("200", "400", "401", "404", "429")),
            Map.entry("post /api/v1/research/projects/{id}/reinit", codes("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("post /api/v1/research/projects/{id}/return", codes("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/allowlist", codes("200", "401", "429", "502", "503", "504")),
            Map.entry("post /api/v1/research/allowlist", codes("201", "400", "401", "403", "409", "422", "429", "502", "503", "504")),
            Map.entry("patch /api/v1/research/allowlist/{id}", codes("200", "400", "401", "403", "404", "422", "429", "502", "503", "504")),
            // P1 的九個操作
            Map.entry("post /api/v1/research/projects/{id}/route/preview", codes("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("post /api/v1/research/projects/{id}/route", codes("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/projects/{id}/route", codes("200", "400", "401", "404", "429")),
            Map.entry("post /api/v1/research/projects/{id}/scr", codes("202", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/projects/{id}/scr", codes("200", "400", "401", "404", "429")),
            Map.entry("post /api/v1/research/projects/{id}/scr/{scrNo}/apply", codes("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/projects/{id}/decomposition", codes("200", "400", "401", "404", "429")),
            Map.entry("post /api/v1/research/projects/{id}/decomposition", codes("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("post /api/v1/research/projects/{id}/decomposition/signoff", codes("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/projects/{id}/kanban", codes("200", "400", "401", "404", "429")),
            Map.entry("post /api/v1/research/projects/{id}/gates", codes("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/projects/{id}/healing", codes("200", "400", "401", "404", "429")),
            Map.entry("get /api/v1/research/projects/{id}/delivery", codes("200", "400", "401", "404", "429")),
            Map.entry("post /api/v1/research/projects/{id}/delivery/tag", codes("201", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("post /api/v1/research/projects/{id}/delivery/pr", codes("200", "400", "401", "403", "404", "409", "422", "429", "502", "503", "504")),
            Map.entry("get /api/v1/research/projects/{id}/delivery/traceability", codes("200", "400", "401", "404", "409", "429", "502", "503", "504")));

    private static boolean isResearchPath(String path) {
        return path.startsWith("/api/v1/research/") || path.startsWith("/api/v1/stream/research/");
    }

    @Test
    void AT_960_5_5_theResearchPathsHaveExactlyTheContractOperationsAndOperationIdsAndNoneCanDelete() {
        Resp docs = docs();
        Map<String, Object> paths = docs.read("$.paths");
        List<String> researchPaths = paths.keySet().stream().filter(OpenApiIT::isResearchPath).sorted().toList();

        assertThat(researchPaths).as("研究路徑 37 條：P0 的 24 條加 P1 的 6 條加 P2 的 7 條").hasSize(37);
        int operations = 0;
        for (String path : researchPaths) {
            Map<String, Object> methods = docs.read("$.paths['" + path + "']");
            assertThat(methods.keySet()).as(path + "：研究路徑沒有 delete").doesNotContain("delete");
            assertThat(new TreeSet<>(methods.keySet())).as(path).containsExactlyElementsOf(EXPECTED.get(path));
            operations += methods.size();
        }
        assertThat(operations).as("研究面的操作總數（P0 的 26 加 P1 的 9 加 P2 的 7）").isEqualTo(42);
        assertThat(RESEARCH_OPERATION_IDS).as("有 operationId 的研究操作：P0 的 25 加 P1 的 9 加 P2 的 7＝41（SSE 沒有）").hasSize(41);
        for (Map.Entry<String, String> expected : RESEARCH_OPERATION_IDS.entrySet()) {
            String method = expected.getKey().substring(0, expected.getKey().indexOf(' '));
            String path = expected.getKey().substring(expected.getKey().indexOf(' ') + 1);
            assertThat(docs.<String>read("$.paths['" + path + "']." + method + ".operationId")).as(expected.getKey()).isEqualTo(expected.getValue());
        }
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/stream/research/{id}']").keySet()).containsExactly("get");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/stream/research/{id}'].get.responses['200'].content").keySet())
                .containsExactly("text/event-stream");
        List<Map<String, Object>> security = docs.read("$.paths['/api/v1/stream/research/{id}'].get.security");
        assertThat(security.stream().flatMap(m -> m.keySet().stream()).toList())
                .as("研究事件串流同既有兩條 SSE：Bearer 標頭或 ?access_token=").containsExactlyInAnyOrder("bearerAuth", "queryAccessToken");
        assertThat(docs.<List<String>>read("$.paths['/api/v1/stream/research/{id}'].get.parameters[?(@.in=='header')].name")).containsExactly("Last-Event-ID");
    }

    @Test
    void AT_960_5_5_everyResearchOperationDocumentsExactlyTheStatusCodesItCanReturn() {
        Resp docs = docs();

        assertThat(RESEARCH_STATUS_CODES).as("42 個研究操作").hasSize(42);
        for (Map.Entry<String, Set<String>> expected : RESEARCH_STATUS_CODES.entrySet()) {
            String method = expected.getKey().substring(0, expected.getKey().indexOf(' '));
            String path = expected.getKey().substring(expected.getKey().indexOf(' ') + 1);
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "']." + method + ".responses").keySet())
                    .as(expected.getKey()).containsExactlyInAnyOrderElementsOf(expected.getValue());
        }
    }

    /**
     * Gate 0 核准的錯誤說明照 D-72 反映真實回應（PKG-FIX-API；INT-13、SCG-4 F-05）：摘要不符與零鍵都是 422（{@code digest_mismatch}、{@code missing_digests}），
     * 409 清單不再有契約原列的 {@code spec_digest_changed}；請求本文的 {@code expectedDigests} 說明是「至少一鍵、只比對送來的鍵」而不是「須涵蓋四個檔」。
     * 為什麼重要：前端依 /v3/api-docs 產生型別與錯誤處理——說明講「409 spec_digest_changed」而實際回 422，前端會為一個永遠走不到的分支寫處理。
     */
    @Test
    void AT_960_5_5_theApproveOperationDocumentsTheD72DigestReasonsAs422AndNoLongerTheSpecDigestChanged409() {
        Resp docs = docs();
        String operation = "$.paths['/api/v1/research/projects/{id}/approve'].post";

        String unprocessable = docs.read(operation + ".responses['422'].description");
        String conflict = docs.read(operation + ".responses['409'].description");
        String description = docs.read(operation + ".description");
        String digests = docs.read("$.components.schemas.ResearchApproveRequest.properties.expectedDigests.description");

        assertThat(unprocessable).contains("digest_mismatch", "details.files", "missing_digests");
        assertThat(conflict).contains("review_not_passed", "fsm_state_conflict", "escalated").doesNotContain("spec_digest_changed");
        assertThat(description).contains("422 digest_mismatch", "422 missing_digests").doesNotContain("spec_digest_changed");
        assertThat(digests).contains("missing_digests", "只比對送來的鍵").doesNotContain("須涵蓋");
    }

    /**
     * 能力探針與專案範圍的欄位在 OpenAPI 上與 Bridge 對齊（PKG-FIX-API；INT-03、INT-08）：{@code CapabilitiesDto} 多一個 required 且 nullable 的 {@code sddRoot}
     * （Bridge 的 {@code sdd_root}；解析不到為 null）；專案詳情的 {@code scope} 說明是 camelCase 鍵（{@code inScope}…），不再是 Bridge 的 snake_case 鏡像。
     */
    @Test
    void AT_960_5_5_theCapabilitiesAndScopeSchemasCarryTheBridgeAlignedFieldsInCamelCase() {
        Resp docs = docs();

        assertThat(docs.<List<String>>read("$.components.schemas.CapabilitiesDto.required")).contains("sddRoot", "researchRoot", "scaffoldRoot", "repoWritable", "fetchHosts");
        assertThat(docs.<List<String>>read("$.components.schemas.CapabilitiesDto.properties.sddRoot.type")).as("sddRoot 可為 null（框架樹解析不到、或舊版 Bridge 沒回）；OpenAPI 3.1 以型別陣列表示")
                .containsExactlyInAnyOrder("string", "null");
        String scope = docs.read("$.components.schemas.ResearchProjectDetail.properties.scope.description");
        assertThat(scope).contains("camelCase", "inScope", "techStack", "recencyYears", "applicabilityAxes").doesNotContain("snake_case 鍵原樣");
        assertThat(docs.<List<String>>read("$.components.schemas.ReconcileResult.required")).containsExactlyInAnyOrder("consistent", "checks");
        assertThat(docs.<List<String>>read("$.components.schemas.ReconcileCheckDto.required")).as("name 是 Bridge 的 id；drift 缺席時省略").containsExactlyInAnyOrder("name", "status");
    }
}
