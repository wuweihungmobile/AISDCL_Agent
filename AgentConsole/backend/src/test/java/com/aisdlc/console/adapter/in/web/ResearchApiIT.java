package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.research.ResearchApproveRequest;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchReinitRequest;
import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.BridgeSource;
import com.aisdlc.console.support.ResearchP1Fixtures;
import com.aisdlc.minibridge.MiniBridge;
import com.aisdlc.minibridge.MiniResearch;
import com.aisdlc.minibridge.MiniResearch.Call;
import com.aisdlc.minibridge.MiniResearch.Reply;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.http.HttpMethod;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.RecordComponent;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 研究面 REST 端點的整合測試（TCS-ResearchToPRD-P0 §3：AT-960-4-1～4-8、5-4、14-4、14-E-1、15-7、15-E-2）：完整 Spring Boot context、真 PostgreSQL 與迷你 Bridge 的研究面
 * （{@link MiniResearch}）。測試扮演唯一的寫入者 Bridge 把夾具寫進 {@code console.research_*}，console-api 只讀；寫入端點則真的經 HTTP 到迷你 Bridge 一次、不重試。
 */
@ExtendWith(OutputCaptureExtension.class)
class ResearchApiIT extends AbstractResearchIT {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Pattern UTC_OFFSET_TIME = Pattern.compile("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?\\+00:00");
    /** Bridge 宣告的對帳項識別與順序（{@code gates/reconcile.py} 的 {@code CHECK_IDS}）：期望值取自 Bridge 原始碼，不是測試自己猜的。 */
    private static final List<String> RECONCILE_CHECK_IDS = BridgeSource.constants("CHECK_IDS", "research", "gates", "reconcile.py");
    /** Gate 0 凍結的四份文件（Bridge 的 {@code APPROVE_DOCS}；{@code missing_digests} 的 {@code details.accepted_keys}）。 */
    private static final List<String> ACCEPTED_DIGEST_KEYS = List.of("01_specs/PRD-v1.0.0.md", "00_research/evidence_matrix.md", "00_research/issue_scope.json",
            "01_specs/adr_draft.md");
    /** Bridge 的 {@code digest_problems} 形狀（D-72）：{@code details.files[{key, expected, current}]}。 */
    private static final Map<String, Object> DIGEST_MISMATCH_DETAILS = map("files", List.of(map("key", "00_research/evidence_matrix.md", "expected",
            "sha256:" + "d".repeat(64), "current", "sha256:" + "e".repeat(64))));
    private static final Map<String, Object> MISSING_DIGESTS_DETAILS = map("accepted_keys", ACCEPTED_DIGEST_KEYS);

    // ── 小工具 ───────────────────────────────────────────────────────────────────────────

    @SuppressWarnings("unchecked")
    private static Map<String, Object> scope(Map<String, Object> body) {
        return (Map<String, Object>) body.get("scope");
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> layers(Map<String, Object> body) {
        return (Map<String, Object>) scope(body).get("layers");
    }

    private static Map<String, Object> map(Object... keyValues) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            out.put((String) keyValues[i], keyValues[i + 1]);
        }
        return out;
    }

    private static Map<String, Object> resource(String name) {
        try (InputStream in = ResearchApiIT.class.getResourceAsStream("/research/" + name)) {
            if (in == null) {
                throw new IllegalStateException("找不到黃金檔 research/" + name);
            }
            return JSON.readValue(in, new TypeReference<Map<String, Object>>() { });
        } catch (IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    /** 研究面 FSM 視圖去掉它多出的三個欄位（{@code humanReturnCount}、{@code stage2Frozen}、{@code retryHistory.gates}）＝既有 SddFsmState 的全部欄位。 */
    @SuppressWarnings("unchecked")
    private static Map<String, Object> existingFields(Map<String, Object> view) {
        Map<String, Object> existing = new LinkedHashMap<>(view);
        assertThat(existing.remove("humanReturnCount")).as("研究面視圖多一個 humanReturnCount").isNotNull();
        assertThat(existing.remove("stage2Frozen")).as("P1 起研究面視圖多一個 stage2Frozen（D-125：由 frozenStages 導出）").isNotNull();
        Map<String, Object> retry = new LinkedHashMap<>((Map<String, Object>) existing.get("retryHistory"));
        assertThat(retry.remove("gates")).as("研究面視圖的 retryHistory 多一個 gates").isNotNull();
        existing.put("retryHistory", retry);
        return existing;
    }

    private static List<String> auditLines(CapturedOutput output) {
        return output.getAll().lines().filter(line -> line.contains("{\"event\":\"audit\"")).map(line -> line.substring(line.indexOf("{\"event\":\"audit\""))).toList();
    }

    private List<Map<String, Object>> auditRows() {
        return jdbc.queryForList("select subject, role, method, path, entity_type, entity_id, http_status, trace_id from console.audit_log order by occurred_at, id");
    }

    // ── AT-960-4-1：建立端點輸入閘 ────────────────────────────────────────────────────────

    private record Violation(String label, Map<String, Object> body, String field, String rule, String reason) {
    }

    @Test
    void AT_960_4_1_theCreateGateRejectsEveryViolationWith400AndTouchesNeitherTheBridgeNorTheDatabase() {
        bridge().webLayerEnabled = false;
        assertThat(api.get(viewer(), RESEARCH + "/capabilities").<Boolean>read("$.data.webLayerEnabled")).as("暖快取：Web 層未啟用").isFalse();
        bridge().calls.clear();

        List<Violation> cases = new ArrayList<>();
        Map<String, Object> missingTopic = validCreate("demo");
        missingTopic.remove("topic");
        cases.add(new Violation("缺 topic", missingTopic, "topic", "required", "invalid_request"));
        Map<String, Object> longTopic = validCreate("demo");
        longTopic.put("topic", "字".repeat(501));
        cases.add(new Violation("topic 501 字元", longTopic, "topic", "max_length", "invalid_request"));
        Map<String, Object> fast = validCreate("demo");
        fast.put("depthLevel", "FAST");
        cases.add(new Violation("depthLevel 為 FAST", fast, "depthLevel", "invalid_value", "invalid_request"));
        Map<String, Object> noLayers = validCreate("demo");
        layers(noLayers).replaceAll((key, value) -> false);
        cases.add(new Violation("四層全關", noLayers, "scope.layers", "at_least_one", "invalid_request"));
        Map<String, Object> industry = validCreate("demo");
        layers(industry).put("industry", true);
        cases.add(new Violation("industry 為真而 Web 層未啟用", industry, "scope.layers.industry", "web_layer_disabled", "layer_unavailable"));
        cases.add(new Violation("slug 不合規", validCreate("Bad_Slug"), "slug", "pattern", "invalid_request"));
        Map<String, Object> recency = validCreate("demo");
        scope(recency).put("recencyYears", 4);
        cases.add(new Violation("recencyYears 4", recency, "scope.recencyYears", "invalid_value", "invalid_request"));
        Map<String, Object> axes = validCreate("demo");
        scope(axes).put("applicabilityAxes", List.of("a", "b", "c", "d", "e", "f", "g"));
        cases.add(new Violation("applicabilityAxes 7 項", axes, "scope.applicabilityAxes", "max_items", "invalid_request"));
        Map<String, Object> hint = validCreate("demo");
        hint.put("targetScopeHint", "ELSEWHERE");
        cases.add(new Violation("targetScopeHint 列舉外", hint, "targetScopeHint", "invalid_value", "invalid_request"));

        for (Violation violation : cases) {
            Resp resp = api.post(operator(), RESEARCH + "/projects", violation.body());

            assertThat(resp.status()).as(violation.label()).isEqualTo(400);
            assertThat(resp.<String>read("$.reason")).as(violation.label()).isEqualTo(violation.reason());
            assertThat(resp.errorFields()).as("%s：errors[].field", violation.label()).contains(violation.field());
            assertThat(resp.<List<String>>read("$.details.violations[*].field")).as(violation.label()).contains(violation.field());
            assertThat(resp.<List<String>>read("$.details.violations[*].rule")).as("%s：details.violations[].rule", violation.label()).contains(violation.rule());
            assertThat(resp.has("$.data")).as("%s：失敗沒有 data", violation.label()).isFalse();
        }

        assertThat(bridge().calls).as("迷你 Bridge 收到的請求數為 0").isEmpty();
        assertThat(rows("research_projects")).as("資料庫零新增").isZero();
        assertThat(rows("research_events")).isZero();
        Resp empty = api.get(viewer(), RESEARCH + "/projects");
        assertThat(empty.status()).isEqualTo(200);
        assertThat(empty.<List<Object>>read("$.data")).as("零專案時清單回空陣列（FE-A 勘誤 1：清單回陣列、不是分頁封包）").isEmpty();
    }

    @Test
    void AT_960_4_1_theSlugLengthBoundaryIsOneToThirtyCharactersInclusive() {
        // 上界：30 字放行（送到 Bridge、建立成功）、31 字被輸入閘擋下（零 Bridge 請求）；下界：1 字放行、空字串被擋（契約 §1.2：^[a-z0-9][a-z0-9-]{0,29}$）
        for (String slug : List.of("a".repeat(30), "b")) {
            Resp ok = api.post(operator(), RESEARCH + "/projects", validCreate(slug));

            assertThat(ok.status()).as("slug 長度 " + slug.length()).isEqualTo(201);
            assertThat(ok.<String>read("$.data.slug")).isEqualTo(slug);
        }
        long accepted = bridge().countCalls("POST", "/research/projects");
        assertThat(accepted).as("兩個合法 slug 各一次 Bridge 請求").isEqualTo(2);

        for (String slug : List.of("c".repeat(31), "")) {
            Resp refused = api.post(operator(), RESEARCH + "/projects", validCreate(slug));

            assertThat(refused.status()).as("slug 長度 " + slug.length()).isEqualTo(400);
            assertThat(refused.<String>read("$.reason")).isEqualTo("invalid_request");
            assertThat(refused.<List<String>>read("$.details.violations[*].field")).containsExactly("slug");
            assertThat(refused.<List<String>>read("$.details.violations[*].rule")).containsExactly("pattern");
        }
        assertThat(bridge().countCalls("POST", "/research/projects")).as("被擋下的 slug 沒有送到 Bridge").isEqualTo(accepted);
        assertThat(rows("research_projects")).isEqualTo(2);
    }

    @Test
    void AT_960_4_1_allViolationsAreReportedTogetherAndAMissingScopeIsOneOfThem() {
        Map<String, Object> body = validCreate("Bad_Slug");
        body.remove("topic");
        body.remove("scope");

        Resp resp = api.post(operator(), RESEARCH + "/projects", body);

        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.errorFields()).containsExactlyInAnyOrder("slug", "topic", "scope");
        assertThat(bridge().calls).isEmpty();
    }

    // ── AT-960-4-2：詳情與流程脊 ──────────────────────────────────────────────────────────

    @Test
    void AT_960_4_2_theFlowHasFiveFixedStepsAndTheCursorComesFromTheDatabaseEveryTime() {
        UUID id = fx.project("demo", "studio", "REVIEWING", "RUNNING", "");

        Resp first = api.get(viewer(), RESEARCH + "/projects/" + id);
        Resp again = api.get(viewer(), RESEARCH + "/projects/" + id);

        assertThat(first.status()).isEqualTo(200);
        assertThat(first.<List<String>>read("$.data.flow.steps[*].id")).containsExactly("topic", "studio", "route", "build", "deliver");
        assertThat(first.<List<String>>read("$.data.flow.steps[*].state")).containsExactly("DONE", "CURRENT", "TODO", "TODO", "TODO");
        assertThat(first.<String>read("$.data.flow.currentStep")).isEqualTo("studio");
        assertThat(first.<String>read("$.data.flow.furthestStep")).isEqualTo("studio");
        assertThat(first.<String>read("$.data.flow.resumeHref")).isEqualTo("/research/" + id + "?step=studio");
        assertThat(first.<String>read("$.data.flow.effective.phase")).isEqualTo("REVIEWING");
        assertThat(first.<String>read("$.data.flow.effective.status")).isEqualTo("RUNNING");
        assertThat(first.<String>read("$.data.rpNo")).matches("RP-\\d{4,}");
        assertThat(first.<Map<String, Object>>read("$.data")).as("兩次回應逐欄相等").isEqualTo(again.read("$.data"));
        assertThat(first.<Integer>read("$.data.counts.sources")).isZero();
        Map<String, Object> data = first.read("$.data");
        assertThat(data).as("尚無版本／審查：鍵在、值為 null（與 OpenAPI 的 nullable＋required 一致）").containsKeys("headPrdVersion", "lastReview");
        assertThat(data.get("headPrdVersion")).isNull();
        assertThat(data.get("lastReview")).isNull();
        assertThat(first.<String>read("$.data.createdAt")).matches(UTC_OFFSET_TIME);

        // 游標只取 DB：Bridge 改了游標，下一次讀取就是新值（console-api 沒有任何記憶體內的流程狀態）
        jdbc.update("update console.research_projects set flow_phase = 'GATE0_PENDING', flow_status = 'WAITING_HUMAN' where id = ?", id);
        Resp moved = api.get(viewer(), RESEARCH + "/projects/" + id);
        assertThat(moved.<String>read("$.data.flow.effective.phase")).isEqualTo("GATE0_PENDING");
        assertThat(moved.<String>read("$.data.flowStatus")).isEqualTo("WAITING_HUMAN");
        assertThat(moved.<String>read("$.data.flow.currentStep")).isEqualTo("studio");
    }

    // ── AT-960-4-3：records/audit ────────────────────────────────────────────────────────

    @Test
    void AT_960_4_3_recordsAuditReturnsR1ToR14WithCountsAndTheMissingClassesAtGateZero() {
        UUID id = fx.project("demo", "route", "FROZEN", "IDLE", "");
        fx.artifact(id, "ISSUE_SCOPE", 1, "{}");
        fx.artifact(id, "EVIDENCE_ITEMS", 1, "{\"items\":[]}");
        UUID source = fx.source(id, "S-001", "https://example.org/a", "T1");
        fx.fetch(id, source, "F-0001", "OK");
        fx.prdVersion(id, 1, "v1.0.0", "# PRD");
        UUID round = fx.round(id, 1, 1, 1, "AUTO", true, new BigDecimal("85.00"), 60, 0, true, "PASS", "PASS", 0);
        fx.scores(round, 85);
        fx.decision(id, "GATE0", "APPROVED", "research-demo", "Gate-0", "{\"01_specs/PRD-v1.0.0.md\":\"sha256:" + "a".repeat(64) + "\"}");
        fx.event(id, 1, "research.step", "{}");

        Resp resp = api.get(viewer(), RESEARCH + "/projects/" + id + "/records/audit");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<String>>read("$.data.classes[*].id")).containsExactly("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12", "R13", "R14");
        Map<String, Integer> counts = new LinkedHashMap<>();
        List<Map<String, Object>> classes = resp.read("$.data.classes");
        classes.forEach(c -> counts.put((String) c.get("id"), (Integer) c.get("count")));
        assertThat(counts).containsEntry("R1", 1).containsEntry("R2", 1).containsEntry("R3", 1).containsEntry("R4", 1).containsEntry("R5", 1).containsEntry("R6", 1)
                .containsEntry("R7", 0).containsEntry("R8", 0).containsEntry("R10", 0).containsEntry("R11", 0).containsEntry("R12", 0).containsEntry("R13", 1);
        assertThat(counts.get("R9")).as("R9 stage run：審查輪的 REVIEW run").isGreaterThanOrEqualTo(1);
        assertThat(counts.get("R14")).as("R14 產物登記").isEqualTo(2);
        assertThat(classes).allSatisfy(c -> assertThat((String) c.get("name")).isNotBlank());
        assertThat(resp.<List<String>>read("$.data.missing")).as("Gate 0 時點的 missing 恰為 R7、R8、R11（R10、R12 允許為 0）").containsExactly("R7", "R8", "R11");

        UUID fresh = fx.project("fresh");
        Resp none = api.get(viewer(), RESEARCH + "/projects/" + fresh + "/records/audit");
        assertThat(none.<List<String>>read("$.data.missing")).as("沒有任何決定的新專案另含 R4、R5、R6").contains("R4", "R5", "R6", "R7", "R8", "R11")
                .doesNotContain("R1", "R10", "R12");
    }

    // ── AT-960-4-4：409 與 details.unmet ──────────────────────────────────────────────────

    @Test
    void AT_960_4_4_unmetPreconditionsAreAConflictWithTheBridgeReasonAndDetailsVerbatimAndNothingMoves() {
        UUID id = fx.project("demo");
        fx.event(id, 1, "research.step", "{}");
        bridge().next("stage:draft", Reply.error(409, "stage_conflict", "details", map("unmet", List.of(map("rule", "phase", "expected", List.of("EVIDENCE_READY"), "current", "INGESTED")))));
        bridge().next("stage:revise", Reply.error(409, "stage_conflict", "details",
                map("unmet", List.of(map("rule", "last_round_failed", "expected", "FAIL", "current", null)))));
        String cursorBefore = fx.cursor(id);
        long eventsBefore = fx.eventCount(id);

        Resp draft = api.post(operator(), RESEARCH + "/projects/" + id + "/stages/draft", Map.of());
        Resp revise = api.post(operator(), RESEARCH + "/projects/" + id + "/stages/revise", Map.of());

        for (Resp resp : List.of(draft, revise)) {
            assertThat(resp.status()).isEqualTo(409);
            assertThat(resp.<String>read("$.reason")).as("reason 逐字取自 Bridge").isEqualTo("stage_conflict");
            assertThat(resp.<List<Map<String, Object>>>read("$.details.unmet")).isNotEmpty().allSatisfy(item -> assertThat(item).containsKey("rule"));
            assertThat(resp.has("$.data")).isFalse();
        }
        assertThat(draft.<String>read("$.details.unmet[0].rule")).isEqualTo("phase");
        assertThat(draft.<List<String>>read("$.details.unmet[0].expected")).containsExactly("EVIDENCE_READY");
        assertThat(revise.<String>read("$.details.unmet[0].rule")).isEqualTo("last_round_failed");
        assertThat(fx.cursor(id)).as("游標前後相同").isEqualTo(cursorBefore);
        assertThat(fx.eventCount(id)).as("事件帳行數前後相同").isEqualTo(eventsBefore);
        assertThat(bridge().calls).hasSize(2);
    }

    // ── AT-960-4-5：並發啟動 ─────────────────────────────────────────────────────────────

    @Test
    void AT_960_4_5_theSecondConcurrentStageStartIs409StageConflictAndConsoleApiNeverRetries() throws Exception {
        UUID id = fx.project("demo");
        fx.event(id, 1, "research.step", "{}");
        bridge().stageRace = true;
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            CountDownLatch start = new CountDownLatch(1);
            List<Future<Resp>> futures = new ArrayList<>();
            for (int i = 0; i < 2; i++) {
                futures.add(pool.submit(() -> {
                    start.await();
                    return api.post(operator(), RESEARCH + "/projects/" + id + "/stages/research", Map.of());
                }));
            }
            start.countDown();
            List<Resp> results = new ArrayList<>();
            for (Future<Resp> future : futures) {
                results.add(future.get(30, TimeUnit.SECONDS));
            }

            assertThat(results).extracting(Resp::status).containsExactlyInAnyOrder(202, 409);
            Resp conflict = results.stream().filter(r -> r.status() == 409).findFirst().orElseThrow();
            assertThat(conflict.<String>read("$.reason")).isEqualTo("stage_conflict");
            assertThat(conflict.<String>read("$.details.activeStage")).isEqualTo("RESEARCH");
            Resp accepted = results.stream().filter(r -> r.status() == 202).findFirst().orElseThrow();
            assertThat(accepted.<Integer>read("$.code")).isEqualTo(202);
            assertThat(accepted.<String>read("$.data.stageRunId")).isNotBlank();
            assertThat(accepted.<String>read("$.data.flowStatus")).isEqualTo("RUNNING");
            assertThat(bridge().countCalls("POST", "/research/projects/")).as("console-api 不自行重試：迷你 Bridge 請求數恰 2").isEqualTo(2);
            assertThat(fx.eventCount(id)).as("事件帳 seq 連續無重複（console-api 不寫事件帳）").isEqualTo(1);
        } finally {
            pool.shutdownNow();
        }
    }

    // ── AT-960-4-6：取消、對帳、封存、復原 ─────────────────────────────────────────────────

    @Test
    void AT_960_4_6_cancelReconcileArchiveAndRestoreAreOperatorWritesWithOneBridgeCallEachAndViewerIs403() {
        UUID id = fx.project("demo");
        String base = RESEARCH + "/projects/" + id;

        for (String verb : List.of("archive", "restore", "cancel", "reconcile")) {
            long before = bridge().writeCount();
            Resp denied = api.post(viewer(), base + "/" + verb);
            assertThat(denied.status()).as("VIEWER " + verb).isEqualTo(403);
            assertThat(denied.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
            assertThat(bridge().writeCount()).as("VIEWER 被擋：Bridge 請求數 0").isEqualTo(before);

            Resp ok = api.post(operator(), base + "/" + verb);
            assertThat(ok.status()).as("OPERATOR " + verb).isEqualTo(200);
            assertThat(bridge().writeCount()).as("每個寫入請求恰經一次 Bridge 呼叫：" + verb).isEqualTo(before + 1);
            if ("archive".equals(verb)) {
                assertThat(api.get(viewer(), RESEARCH + "/projects").<List<Object>>read("$.data")).as("封存後預設清單不含該專案").isEmpty();
                Resp archived = api.get(viewer(), RESEARCH + "/projects?archived=true");
                assertThat(archived.<List<String>>read("$.data[*].id")).as("archived=true 可見").containsExactly(id.toString());
                assertThat(archived.<String>read("$.data[0].archivedAt")).matches(UTC_OFFSET_TIME);
                assertThat(api.get(viewer(), base).status()).as("已封存的專案詳情仍可讀").isEqualTo(200);
            }
            if ("restore".equals(verb)) {
                assertThat(api.get(viewer(), RESEARCH + "/projects").<List<String>>read("$.data[*].id")).as("30 天內可復原").containsExactly(id.toString());
                assertThat(api.get(viewer(), RESEARCH + "/projects?archived=true").<List<Object>>read("$.data")).isEmpty();
            }
            if ("reconcile".equals(verb)) {
                assertThat(ok.<Boolean>read("$.data.consistent")).isTrue();
                assertThat(ok.<List<String>>read("$.data.checks[*].name")).as("INT-01：name 取自 Bridge 的 id，不得為空；六項、順序以 Bridge 原始碼的 CHECK_IDS 為準")
                        .allSatisfy(name -> assertThat(name).isNotBlank()).containsExactlyElementsOf(RECONCILE_CHECK_IDS);
                assertThat(ok.<List<String>>read("$.data.checks[*].status")).containsOnly("ok");
            }
        }
        assertThat(bridge().calls.stream().map(Call::token).distinct()).as("每個寫入帶研究寫入權杖").containsExactly(MiniResearch.TOKEN);
        assertThat(bridge().calls.stream().map(Call::traceId)).allSatisfy(trace -> assertThat(trace).isNotBlank());
    }

    @Test
    void AT_960_4_6_reconcileNamesEveryCheckByTheBridgeIdAndCarriesBothDigestsOfEveryDriftRowInCamelCase() {
        UUID id = fx.project("demo");
        String expected = "a".repeat(64);
        String actual = "b".repeat(64);
        List<Map<String, Object>> checks = new ArrayList<>(MiniResearch.consistentReconcileChecks());
        checks.set(0, MiniResearch.reconcileCheck("fsm_flow_mapping", "drift", true, "fsm=HUMAN_PENDING flow=topic/INGESTED",
                List.of(MiniResearch.reconcileDrift("FSM_FLOW", "flow", null, null))));
        checks.set(1, MiniResearch.reconcileCheck("prd_sha256", "drift", true, "",
                List.of(MiniResearch.reconcileDrift("PRD", "01_specs/PRD-v1.0.0.md", expected, actual))));
        checks.set(3, MiniResearch.reconcileCheck("evidence_matrix", "drift", true, "file_missing",
                List.of(MiniResearch.reconcileDrift("EVIDENCE_MATRIX", "00_research/evidence_matrix.md", expected, null))));
        bridge().next("reconcile", new Reply(200, MiniResearch.reconcileBody(checks)));

        Resp resp = api.post(operator(), RESEARCH + "/projects/" + id + "/reconcile");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.consistent")).isFalse();
        assertThat(resp.<List<String>>read("$.data.checks[*].name")).as("name 恆等於 Bridge 的 id（前端靠 fsm_flow_mapping 辨識對映漂移）")
                .containsExactlyElementsOf(RECONCILE_CHECK_IDS);
        assertThat(resp.<List<String>>read("$.data.checks[*].status")).containsExactly("drift", "drift", "ok", "drift", "ok", "ok");
        assertThat(resp.<Map<String, Object>>read("$.data.checks[1].drift[0]")).as("檔案漂移列：兩個摘要都帶、鍵名是 camelCase")
                .containsEntry("kind", "PRD").containsEntry("path", "01_specs/PRD-v1.0.0.md")
                .containsEntry("expectedSha256", expected).containsEntry("actualSha256", actual).doesNotContainKeys("expected_sha256", "actual_sha256");
        assertThat(resp.<Map<String, Object>>read("$.data.checks[3].drift[0]")).as("缺檔：資料庫側的摘要在、檔案側的摘要缺席（Bridge 的 null）")
                .containsEntry("expectedSha256", expected).doesNotContainKey("actualSha256");
        assertThat(resp.<Map<String, Object>>read("$.data.checks[0].drift[0]")).as("對映漂移不是檔案：kind＝FSM_FLOW、沒有任何摘要")
                .containsEntry("kind", "FSM_FLOW").doesNotContainKeys("expectedSha256", "actualSha256");
        assertThat(resp.<List<Object>>read("$.data.checks[2].drift")).as("沒有漂移的項：Bridge 的空陣列原樣轉出").isEmpty();
    }

    // ── AT-960-4-7：審查輪 DTO ───────────────────────────────────────────────────────────

    @Test
    void AT_960_4_7_reviewRoundsDescribeOnlyCompletedRoundsWithoutStatusAndWithFinishedAtAndGeneration() {
        UUID alpha = fx.project("alpha", "studio", "REVIEWING", "IDLE", "");
        fx.prdVersion(alpha, 1, "v0.1.0-draft", "# v1");
        fx.prdVersion(alpha, 2, "v0.2.0-draft", "# v2");
        fx.prdVersion(alpha, 3, "v0.3.0-draft", "# v3");
        int[][] shape = {{1, 1, 1, 70, 55, 1, 1}, {2, 1, 2, 72, 58, 1, 2}, {3, 1, 3, 60, 50, 2, 3}, {4, 2, 3, 74, 59, 1, 1}};
        for (int[] row : shape) {
            String verdict = row[0] == 3 ? "ESCALATE" : "REVISE";
            UUID round = fx.round(alpha, row[0], row[1], row[2], "AUTO", true, new BigDecimal(row[3] + ".00"), row[4], row[5], false, verdict, "FAIL", row[6]);
            fx.scores(round, row[3]);
            fx.defect(round, "D-" + row[0] + "-001", "ARCHITECTURE", "P1", "OPEN");
            fx.defect(round, "D-" + row[0] + "-002", "QA", "P3", "FIXED");
        }
        UUID bravo = fx.project("bravo", "studio", "GATE0_PENDING", "WAITING_HUMAN", "");
        fx.prdVersion(bravo, 1, "v1.0.0", "# v1");
        fx.scores(fx.round(bravo, 1, 1, 1, "AUTO", true, new BigDecimal("85.00"), 60, 0, true, "PASS", "PASS", 0), 85);
        fx.stageRun(bravo, "REVIEW", 2, 1, "FAILED", "review_invalid");

        Resp listA = api.get(operator(), RESEARCH + "/projects/" + alpha + "/review-rounds");
        Resp listB = api.get(operator(), RESEARCH + "/projects/" + bravo + "/review-rounds");
        Resp detail = api.get(operator(), RESEARCH + "/projects/" + alpha + "/review-rounds/1");
        Resp missing = api.get(operator(), RESEARCH + "/projects/" + bravo + "/review-rounds/2");
        Resp docs = api.get(null, "/v3/api-docs");

        assertThat(listA.<List<Object>>read("$.data")).as("甲：四輪").hasSize(4);
        assertThat(listB.<List<Object>>read("$.data")).as("乙：一輪（無效審查的 stage run 不出現為輪）").hasSize(1);
        assertThat(listA.<List<Integer>>read("$.data[*].roundNo")).as("輪號連續無跳號").containsExactly(1, 2, 3, 4);
        assertThat(listA.<List<Integer>>read("$.data[*].fsmGeneration")).containsExactly(1, 1, 1, 2);
        assertThat(listB.<List<Integer>>read("$.data[*].fsmGeneration")).containsExactly(1);
        assertThat(listA.<List<Integer>>read("$.data[*].fsmRetryCount")).containsExactly(1, 2, 3, 1);
        assertThat(listB.<List<Integer>>read("$.data[*].fsmRetryCount")).as("PASS 輪的 fsmRetryCount 為 0").containsExactly(0);
        assertThat(listA.<List<String>>read("$.data[*].verdict")).containsExactly("REVISE", "REVISE", "ESCALATE", "REVISE");
        assertThat(listB.<String>read("$.data[0].prdVersion")).as("prdVersion 是 semver 字串，prdVersionNo 是整數，兩者並存").isEqualTo("v1.0.0");
        assertThat(listB.<Integer>read("$.data[0].prdVersionNo")).isEqualTo(1);
        for (Resp resp : List.of(listA, listB)) {
            List<Map<String, Object>> rounds = resp.read("$.data");
            assertThat(rounds).allSatisfy(round -> {
                assertThat(round).as("沒有 status 鍵").doesNotContainKey("status");
                assertThat((String) round.get("finishedAt")).matches(UTC_OFFSET_TIME);
                assertThat((String) round.get("startedAt")).matches(UTC_OFFSET_TIME);
                assertThat((String) round.get("verdict")).isIn("PASS", "REVISE", "ESCALATE");
                assertThat(round.get("passed")).isInstanceOf(Boolean.class);
                assertThat(round.get("fsmGeneration")).isInstanceOf(Integer.class);
            });
        }
        assertThat(detail.<List<String>>read("$.data.scores[*].dimension")).containsExactly("ARCHITECTURE", "PRODUCT", "QA", "SECURITY");
        assertThat(detail.<List<String>>read("$.data.scores[*].agentId")).containsExactly("sd-architect", "pm-po", "qa-tester", "security-engineer");
        assertThat(detail.<String>read("$.data.scores[3].assistAgentId")).isEqualTo("compliance-officer");
        assertThat(detail.<Object>read("$.data.scores[0].assistAgentId")).isNull();
        assertThat(detail.<List<String>>read("$.data.defects[*].defectNo")).containsExactly("D-1-001", "D-1-002");
        assertThat(detail.<List<String>>read("$.data.defects[*].status")).containsExactly("OPEN", "FIXED");
        assertThat(detail.<Object>read("$.data.defects[0].waiver")).isNull();
        assertThat(detail.<Boolean>read("$.data.conditions.precheckPassed")).isTrue();
        assertThat(detail.<Boolean>read("$.data.conditions.weightedGeThreshold")).isFalse();
        assertThat(detail.<Boolean>read("$.data.conditions.allDimensionsGeFloor")).isFalse();
        assertThat(detail.<Boolean>read("$.data.conditions.noOpenP1")).isFalse();
        assertThat(detail.<String>read("$.data.precheck.checks[0].id")).isEqualTo("SLV-001");
        assertThat(missing.status()).as("{n} 指向沒有列的輪＝404").isEqualTo(404);
        assertThat(missing.<String>read("$.reason")).isEqualTo("research_not_found");

        List<String> required = docs.read("$.components.schemas.ReviewRoundDto.required");
        Map<String, Object> properties = docs.read("$.components.schemas.ReviewRoundDto.properties");
        assertThat(properties).as("OpenAPI 的 ReviewRoundDto 沒有 status 屬性").doesNotContainKey("status").containsKeys("fsmGeneration", "fsmRetryCount", "finishedAt");
        assertThat(required).contains("startedAt", "finishedAt", "passed", "verdict", "fsmGeneration");
    }

    @Test
    void AT_960_4_7_aPrecheckVetoRoundHasNoScoreAndItsConditionsAreNullInsteadOfFalse() {
        UUID id = fx.project("vetoed", "studio", "REVISING", "IDLE", "");
        fx.prdVersion(id, 1, "v0.1.0-draft", "# v1");
        UUID round = fx.round(id, 1, 1, 1, "AUTO", false, null, null, 0, false, "REVISE", "FAIL", 1);
        fx.defect(round, "D-1-001", "PRODUCT", "P2", "WAIVED");

        Resp resp = api.get(viewer(), RESEARCH + "/projects/" + id + "/review-rounds/1");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Object>read("$.data.weightedScore")).isNull();
        assertThat(resp.<Object>read("$.data.minDimensionScore")).isNull();
        assertThat(resp.<Boolean>read("$.data.conditions.precheckPassed")).isFalse();
        assertThat(resp.<Object>read("$.data.conditions.weightedGeThreshold")).as("前置否決不過（未計分）時為 null").isNull();
        assertThat(resp.<Object>read("$.data.conditions.allDimensionsGeFloor")).isNull();
        assertThat(resp.<Boolean>read("$.data.conditions.noOpenP1")).isTrue();
        assertThat(resp.<Boolean>read("$.data.precheck.passed")).isFalse();
        assertThat(resp.<Map<String, Object>>read("$.data.defects[0].waiver")).containsEntry("by", "admin");
        assertThat(resp.<String>read("$.data.defects[0].waiver.at")).matches(UTC_OFFSET_TIME);
        assertThat(resp.<Double>read("$.data.threshold")).isEqualTo(85.0);
    }

    // ── AT-960-4-8：研究面 FSM 視圖 ──────────────────────────────────────────────────────

    @Test
    void AT_960_4_8_theFsmViewKeepsTheExistingRetryHistoryAddsThreeGatesAndCountsOnlyTheCurrentGenerationsHumanReturns() {
        Map<String, Object> state = resource("fsm_retry_gates.snake.json");
        MINI.sdd.states.put("research-demo-g2", state);
        UUID id = fx.project("demo", "studio", "GATE0_PENDING", "WAITING_HUMAN", "");
        fx.generation(id, 2, "research-demo-g2");
        fx.decision(id, "GATE0", "CHANGES", "research-demo", null, "{}");
        fx.decision(id, "GATE0", "CHANGES", "research-demo", null, "{}");
        fx.decision(id, "GATE0", "CHANGES", "research-demo-g2", null, "{}");
        fx.decision(id, "GATE0", "APPROVED", "research-demo-g2", "Gate-0", "{\"01_specs/PRD-v1.0.0.md\":\"sha256:" + "b".repeat(64) + "\"}");
        fx.decision(id, "SCR", "CHANGES", "research-demo-g2", null, "{}");

        for (String token : List.of(operator(), viewer())) {
            Resp resp = api.get(token, RESEARCH + "/projects/" + id + "/fsm");

            assertThat(resp.status()).isEqualTo(200);
            assertThat(resp.<String>read("$.data.project")).isEqualTo("research-demo-g2");
            assertThat(resp.<String>read("$.data.currentState")).isEqualTo("HUMAN_PENDING");
            assertThat(existingFields(resp.read("$.data"))).as("既有 SddFsmState 的全部欄位與黃金檔逐值相等（camelCase；巢狀內容保留 snake_case 鍵）")
                    .isEqualTo(resource("fsm_retry_gates.camel.json"));
            assertThat(resp.<Integer>read("$.data.retryHistory.count")).isEqualTo(3);
            assertThat(resp.<Map<String, Object>>read("$.data.retryHistory.last")).as("last 與黃金檔既有投影逐值相同（鍵保持 snake_case、含 gate 欄）")
                    .isEqualTo(((Map<?, ?>) state.get("retry_history")).get("last"));
            assertThat(resp.<Map<String, Object>>read("$.data.retryHistory.gates").keySet()).containsExactly("SCG_VALIDATION", "PR_REVIEW", "RTM_VERIFY");
            assertThat(resp.<Integer>read("$.data.retryHistory.gates.SCG_VALIDATION.currentCount")).isEqualTo(2);
            assertThat(resp.<Integer>read("$.data.retryHistory.gates.SCG_VALIDATION.entries")).isEqualTo(3);
            for (String gate : List.of("PR_REVIEW", "RTM_VERIFY")) {
                assertThat(resp.<Integer>read("$.data.retryHistory.gates." + gate + ".currentCount")).isZero();
                assertThat(resp.<Integer>read("$.data.retryHistory.gates." + gate + ".entries")).isZero();
            }
            assertThat(resp.<Integer>read("$.data.humanReturnCount")).as("只數目前 fsm_project 之下 GATE0 且 CHANGES 的筆數").isEqualTo(1);
        }
        assertThat(MINI.sdd.rootsSeen).as("迷你 Bridge 收到外環鍵路徑與 root 參數").anySatisfy(seen -> {
            assertThat(seen.request()).isEqualTo("GET /sdd/fsm/research-demo-g2");
            assertThat(seen.root()).isEqualTo("/research-root/demo");
        });

        Resp docs = api.get(null, "/v3/api-docs");
        Map<String, Object> viewProperties = docs.read("$.components.schemas.ResearchFsmViewDto.properties");
        Map<String, Object> sddProperties = docs.read("$.components.schemas.SddFsmState.properties");
        assertThat(viewProperties.keySet()).containsAll(sddProperties.keySet()).contains("humanReturnCount");
        assertThat(docs.<String>read("$.components.schemas.ResearchFsmViewDto.properties.retryHistory['$ref']")).endsWith("/ResearchRetryHistory");
        assertThat(docs.<Map<String, Object>>read("$.components.schemas.ResearchRetryHistory.properties").keySet()).containsExactlyInAnyOrder("count", "last", "gates");
        assertThat(docs.<List<String>>read("$.components.schemas.ResearchRetryHistory.required")).contains("gates");
        assertThat(docs.<List<String>>read("$.components.schemas.ResearchFsmViewDto.required")).contains("humanReturnCount");
        assertThat(docs.<List<String>>read("$.components.schemas.SddFsmState.required")).as("既有 SddFsmState.required（六項）不動")
                .containsExactlyInAnyOrder("project", "frozenStages", "decisionTrace", "source", "humanPending", "retryHistory");
        assertThat(docs.<String>read("$.components.schemas.SddFsmState.properties.retryHistory['$ref']")).endsWith("/SddRetryHistory");
        assertThat(docs.<List<String>>read("$.components.schemas.SddRetryHistory.required")).containsExactlyInAnyOrder("count", "last");
    }

    // ── AT-960-5-4：allowlist ────────────────────────────────────────────────────────────

    @Test
    void AT_960_5_4_theAllowlistApiLetsOnlyAdminAddAndDisableAndEveryWriteLeavesOneAuditRowWithoutTouchingTheEventLedger(CapturedOutput output) {
        Resp initial = api.get(viewer(), RESEARCH + "/allowlist");
        assertThat(initial.status()).isEqualTo(200);
        assertThat(initial.<List<String>>read("$.data[*].host")).as("預設部署恰四組基底主機").containsExactlyInAnyOrderElementsOf(MiniResearch.FETCH_HOSTS);
        assertThat(initial.<List<String>>read("$.data[*].source")).containsOnly("ENV");
        assertThat(initial.<List<String>>read("$.data[*].listKind")).as("Web 清單為空").containsOnly("FETCH");
        assertThat(initial.<List<String>>read("$.data[*].host")).noneMatch(host -> host.contains("reddit"));
        assertThat(initial.<List<Object>>read("$.data[*].id")).as("ENV 基底條目沒有 id").containsOnlyNulls();

        Map<String, Object> industry = map("listKind", "WEB", "host", "example.com", "layer", "INDUSTRY", "purpose", "產業部落格", "tosNote", "條款已讀",
                "minIntervalSeconds", 5, "tosAcknowledged", false);
        long auditBefore = rows("audit_log");
        Resp added = api.post(admin(), RESEARCH + "/allowlist", industry);
        assertThat(added.status()).isEqualTo(201);
        String entryId = added.read("$.data.id");
        assertThat(added.<String>read("$.data.source")).isEqualTo("ADMIN");
        assertThat(added.<String>read("$.data.addedBy")).as("新增人取 JWT subject").isEqualTo("admin");
        assertThat(rows("audit_log")).isEqualTo(auditBefore + 1);
        Map<String, Object> row = auditRows().get(auditRows().size() - 1);
        assertThat(row).containsEntry("entity_type", "research_allowlist").containsEntry("entity_id", entryId).containsEntry("subject", "admin")
                .containsEntry("role", "ADMIN").containsEntry("http_status", 201).containsEntry("method", "POST");
        assertThat((String) row.get("trace_id")).isNotBlank();
        assertThat(auditLines(output)).anySatisfy(line -> {
            assertThat(JsonPath.<String>read(line, "$.action")).isEqualTo("research.allowlist");
            assertThat(JsonPath.<String>read(line, "$.entity")).isEqualTo("research_allowlist:" + entryId);
            assertThat(JsonPath.<Integer>read(line, "$.status")).isEqualTo(201);
        });

        Map<String, Object> reddit = map("listKind", "WEB", "host", "reddit.com", "layer", "COMMUNITY", "purpose", "社群", "tosNote", "", "minIntervalSeconds", 5,
                "tosAcknowledged", false);
        Resp refused = api.post(admin(), RESEARCH + "/allowlist", reddit);
        assertThat(refused.status()).isEqualTo(422);
        assertThat(refused.<String>read("$.reason")).isEqualTo("terms_ack_required");
        assertThat(rows("audit_log")).as("被拒的 422 也多恰一列").isEqualTo(auditBefore + 2);
        assertThat(auditRows().get(auditRows().size() - 1)).containsEntry("http_status", 422).containsEntry("subject", "admin");
        reddit.put("tosAcknowledged", true);
        Resp acknowledged = api.post(admin(), RESEARCH + "/allowlist", reddit);
        assertThat(acknowledged.status()).isEqualTo(201);
        assertThat(rows("audit_log")).isEqualTo(auditBefore + 3);

        Resp disabled = api.raw(admin(), HttpMethod.PATCH, RESEARCH + "/allowlist/" + entryId, ApiClient.toJson(map("enabled", false)));
        assertThat(disabled.status()).isEqualTo(200);
        assertThat(disabled.<Boolean>read("$.data.enabled")).isFalse();
        assertThat(rows("audit_log")).isEqualTo(auditBefore + 4);
        assertThat(auditRows().get(auditRows().size() - 1)).containsEntry("entity_type", "research_allowlist").containsEntry("entity_id", entryId)
                .containsEntry("http_status", 200).containsEntry("method", "PATCH");

        Resp extra = api.raw(admin(), HttpMethod.PATCH, RESEARCH + "/allowlist/" + entryId, ApiClient.toJson(map("enabled", true, "minIntervalSeconds", 99)));
        assertThat(extra.status()).as("PATCH 只收 enabled").isEqualTo(422);
        assertThat(extra.<String>read("$.reason")).isEqualTo("invalid_request");
        assertThat(extra.<List<String>>read("$.details.violations[*].field")).containsExactly("minIntervalSeconds");
        assertThat(bridge().allowlist.stream().filter(e -> e.get("id").equals(entryId)).findFirst().orElseThrow()).as("條目不變").containsEntry("enabled", false)
                .containsEntry("min_interval_seconds", 5);

        long writesBeforeDenied = bridge().writeCount();
        for (String token : List.of(operator(), viewer())) {
            long auditNow = rows("audit_log");
            Resp denied = api.post(token, RESEARCH + "/allowlist", industry);
            assertThat(denied.status()).isEqualTo(403);
            assertThat(denied.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
            assertThat(rows("audit_log")).as("403 也多恰一列").isEqualTo(auditNow + 1);
        }
        assertThat(auditRows().get(auditRows().size() - 2)).containsEntry("subject", "operator").containsEntry("role", "OPERATOR").containsEntry("http_status", 403);
        assertThat(auditRows().get(auditRows().size() - 1)).containsEntry("subject", "viewer").containsEntry("role", "VIEWER").containsEntry("http_status", 403);
        assertThat(bridge().writeCount()).as("OPERATOR 與 VIEWER 被擋：迷你 Bridge 請求數為 0").isEqualTo(writesBeforeDenied);
        assertThat(rows("research_events")).as("allowlist 是全域資源，事件帳不變").isZero();
        assertThat(api.get(operator(), RESEARCH + "/allowlist").<List<String>>read("$.data[*].host")).contains("example.com", "reddit.com");
    }

    // ── AT-960-14-4：核准的 approver 只取 JWT subject ────────────────────────────────────

    @Test
    void AT_960_14_4_theApproverIsAlwaysTheJwtSubjectAndAForgedApproverInTheBodyIsIgnored() {
        UUID id = fx.project("demo", "studio", "GATE0_PENDING", "WAITING_HUMAN", "");
        String alice = adminAs("alice");
        Map<String, String> digests = new LinkedHashMap<>();
        for (String path : List.of("01_specs/PRD-v0.2.0-draft.md", "00_research/evidence_matrix.md", "00_research/issue_scope.json", "01_specs/adr_draft.md")) {
            digests.put(path, "sha256:" + "c".repeat(64));
        }
        Map<String, Object> plain = map("prdVersion", 2, "expectedDigests", digests);
        Map<String, Object> forged = map("prdVersion", 2, "expectedDigests", digests, "approver", "mallory", "decidedBy", "mallory");

        Resp first = api.post(alice, RESEARCH + "/projects/" + id + "/approve", plain);
        Resp second = api.post(alice, RESEARCH + "/projects/" + id + "/approve", forged);

        assertThat(first.status()).isEqualTo(200);
        assertThat(second.status()).isEqualTo(200);
        assertThat(first.<String>read("$.data.stage")).isEqualTo("Gate-0");
        assertThat(first.<String>read("$.data.fsmState")).isEqualTo("SPEC_FROZEN");
        assertThat(first.<Map<String, Object>>read("$.data.specDocDigests")).containsOnlyKeys(digests.keySet());
        List<Call> approvals = bridge().calls.stream().filter(c -> c.path().endsWith(":approve-baseline")).toList();
        assertThat(approvals).hasSize(2);
        assertThat(approvals).extracting(c -> c.body().get("approver")).as("迷你 Bridge 收到的 approver 恆為 alice").containsExactly("alice", "alice");
        assertThat(approvals).allSatisfy(call -> assertThat(call.body()).doesNotContainKeys("decidedBy", "decided_by", "mallory").containsEntry("prd_version", 2));
        assertThat(Arrays.stream(ResearchApproveRequest.class.getRecordComponents()).map(RecordComponent::getName)).as("請求本文型別沒有 approver 欄")
                .doesNotContain("approver", "decidedBy");
        List<Map<String, Object>> rows = auditRows();
        assertThat(rows).hasSize(2).allSatisfy(row -> assertThat(row).containsEntry("method", "POST").containsEntry("subject", "alice").containsEntry("role", "ADMIN")
                .containsEntry("http_status", 200));
        assertThat(rows.get(0).get("path")).isEqualTo("/api/v1/research/projects/" + id + "/approve");
        // 稽核列與決定列以 trace_id 互證：迷你 Bridge 回的 audit_trace_id 就是它收到的 X-Trace-Id，也就是 audit_log 該列的 trace_id
        assertThat(approvals.get(0).traceId()).isEqualTo(rows.get(0).get("trace_id")).isEqualTo(first.header("X-Trace-Id"));
        assertThat(approvals.get(1).traceId()).isEqualTo(rows.get(1).get("trace_id"));
        assertThat(rows.stream().map(Object::toString)).as("稽核列不含請求本文").noneMatch(text -> text.contains("mallory") || text.contains("sha256"));
    }

    // ── AT-960-14-E-1：核准的權杖與後端失敗對映 ───────────────────────────────────────────

    @Test
    void AT_960_14_E_1_everyBridgeFailureIsRelayedWithItsStatusAndReasonVerbatimWithoutRetryOrData() {
        UUID id = fx.project("demo", "studio", "GATE0_PENDING", "WAITING_HUMAN", "");
        Map<String, Object> body = map("prdVersion", 2, "expectedDigests", map("01_specs/PRD-v0.2.0-draft.md", "sha256:" + "d".repeat(64)));
        String url = RESEARCH + "/projects/" + id + "/approve";
        Map<String, Reply> replies = new LinkedHashMap<>();
        replies.put("503 research_write_disabled", Reply.error(503, "research_write_disabled", "detail", "BRIDGE_RESEARCH_WRITE_TOKEN 未設"));
        replies.put("403 research_write_forbidden", Reply.error(403, "research_write_forbidden"));
        replies.put("409 review_not_passed", Reply.error(409, "review_not_passed"));
        replies.put("422 digest_mismatch", Reply.error(422, "digest_mismatch", "details", DIGEST_MISMATCH_DETAILS));
        replies.put("422 missing_digests", Reply.error(422, "missing_digests", "details", MISSING_DIGESTS_DETAILS));
        replies.put("409 fsm_state_conflict", Reply.error(409, "fsm_state_conflict", "details", map("current_state", "SPEC_FROZEN", "expected_state", "HUMAN_PENDING")));
        replies.put("409 escalated", Reply.error(409, "escalated", "details", map("recovery", map("target", "SPEC_DRAFTING"))));
        replies.put("503 research_requires_db", Reply.error(503, "research_requires_db"));
        replies.put("503 db_blocked", Reply.error(503, "db_blocked"));
        replies.put("422 sanitization_failed", Reply.error(422, "sanitization_failed", "violations", List.of(map("field", "docs[0]", "rule", "outside_root", "message", "路徑跑出根目錄"))));
        int expectedStatus = 0;
        for (Map.Entry<String, Reply> entry : replies.entrySet()) {
            bridge().calls.clear();
            bridge().next("approve", entry.getValue());

            Resp resp = api.post(admin(), url, body);

            String label = entry.getKey();
            assertThat(resp.status()).as(label).isEqualTo(entry.getValue().status());
            assertThat(resp.<String>read("$.reason")).as(label).isEqualTo(entry.getValue().body().get("reason"));
            assertThat(resp.has("$.data")).as("%s：失敗沒有 data", label).isFalse();
            assertThat(bridge().calls).as("%s：console-api 不重試", label).hasSize(1);
            expectedStatus++;
        }
        assertThat(expectedStatus).isEqualTo(replies.size());
        assertThat(api.post(admin(), url, body).<String>read("$.data.fsmState")).as("沒有腳本時回預設成功").isEqualTo("SPEC_FROZEN");
        assertThat(rows("research_gate_decisions")).as("皆無 R6 列（console-api 不寫決定列）").isZero();
    }

    @Test
    void AT_960_14_E_1_theDigestProblemsOfD72AreRelayedAs422WithTheirDetailsVerbatimAndNoLongerAs409SpecDigestChanged() {
        UUID id = fx.project("demo", "studio", "GATE0_PENDING", "WAITING_HUMAN", "");
        Map<String, Object> body = map("prdVersion", 2, "expectedDigests", map("00_research/evidence_matrix.md", "sha256:" + "d".repeat(64)));
        String url = RESEARCH + "/projects/" + id + "/approve";

        bridge().next("approve", Reply.error(422, "digest_mismatch", "details", DIGEST_MISMATCH_DETAILS));
        Resp mismatch = api.post(admin(), url, body);
        bridge().next("approve", Reply.error(422, "missing_digests", "details", MISSING_DIGESTS_DETAILS));
        Resp blind = api.post(admin(), url, body);

        assertThat(mismatch.status()).as("摘要不符是 422（不是契約原列的 409 spec_digest_changed）").isEqualTo(422);
        assertThat(mismatch.<String>read("$.reason")).isEqualTo("digest_mismatch");
        assertThat(mismatch.<List<Map<String, Object>>>read("$.details.files")).as("details.files 逐鍵列出送來的值與現值（Bridge 原樣）").singleElement()
                .satisfies(file -> assertThat(file).containsEntry("key", "00_research/evidence_matrix.md").containsEntry("expected", "sha256:" + "d".repeat(64))
                        .containsEntry("current", "sha256:" + "e".repeat(64)));
        assertThat(blind.status()).isEqualTo(422);
        assertThat(blind.<String>read("$.reason")).isEqualTo("missing_digests");
        assertThat(blind.<List<String>>read("$.details.accepted_keys")).as("Bridge 列出可送的鍵").containsExactlyElementsOf(ACCEPTED_DIGEST_KEYS);
        assertThat(List.of(mismatch, blind)).allSatisfy(resp -> assertThat(resp.has("$.data")).isFalse());
        assertThat(rows("research_gate_decisions")).as("皆無 R6 列（console-api 不寫決定列）").isZero();
    }

    @Test
    void AT_960_14_E_1_aMissingOrWrongTokenAndAnUnreachableOrSlowBridgeAreMappedWithoutAnyRetry() {
        UUID id = fx.project("demo", "studio", "GATE0_PENDING", "WAITING_HUMAN", "");
        Map<String, Object> body = map("prdVersion", 2, "expectedDigests", map("01_specs/PRD-v0.2.0-draft.md", "sha256:" + "d".repeat(64)));
        String url = RESEARCH + "/projects/" + id + "/approve";

        endpoints.tokenUnset();
        Resp unset = api.post(admin(), url, body);
        assertThat(unset.status()).isEqualTo(503);
        assertThat(unset.<String>read("$.reason")).isEqualTo("research_write_disabled");
        assertThat(unset.<String>read("$.details.cause")).isEqualTo("bridge_token_unset");
        assertThat(bridge().calls).as("backend 沒設權杖：一個請求都不發").isEmpty();

        endpoints.reset();
        endpoints.tokenWrong();
        Resp wrong = api.post(admin(), url, body);
        assertThat(wrong.status()).isEqualTo(403);
        assertThat(wrong.<String>read("$.reason")).isEqualTo("research_write_forbidden");
        assertThat(bridge().calls).hasSize(1);

        endpoints.reset();
        bridge().calls.clear();
        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp down = api.post(admin(), url, body);
        assertThat(down.status()).isEqualTo(502);
        assertThat(down.<String>read("$.reason")).isEqualTo("bridge_unreachable");
        assertThat(down.has("$.data")).isFalse();
        assertThat(bridge().calls).as("連不上的 Bridge：沒有任何請求抵達").isEmpty();
        resetSystemConfigs();

        readTimeout.cap(Duration.ofMillis(400));
        bridge().delayMillis = 2500;
        bridge().calls.clear();
        Resp slow = api.post(admin(), url, body);
        assertThat(slow.status()).isEqualTo(504);
        assertThat(slow.<String>read("$.reason")).isEqualTo("bridge_timeout");
        assertThat(bridge().calls).as("POST 不重試：讀取逾時也只送一次").hasSize(1);
        assertThat(rows("research_gate_decisions")).isZero();
    }

    // ── AT-960-15-7：GET fsm 轉 Bridge 並回 SddFsmState 形狀 ─────────────────────────────

    @Test
    void AT_960_15_7_getFsmRelaysTheBridgeSddFsmStateGoldenFileInSddFsmStateDtoShape() {
        Map<String, Object> snake = resource("fsm_escalation.snake.json");
        Map<String, Object> camel = resource("fsm_escalation.camel.json");
        MINI.sdd.states.put("research-demo", snake);
        UUID id = fx.project("demo", "studio", "REVIEWING", "ESCALATED", "");

        Resp resp = api.get(viewer(), RESEARCH + "/projects/" + id + "/fsm");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(existingFields(resp.read("$.data"))).as("既有欄位與 SddFsmStateDto 黃金檔逐值相等（camelCase；研究面視圖只多 retryHistory.gates 與 humanReturnCount）")
                .isEqualTo(camel);
        assertThat(resp.<String>read("$.data.recovery.target")).isEqualTo("SPEC_DRAFTING");
        assertThat(resp.<Integer>read("$.data.retryHistory.gates.SCG_VALIDATION.currentCount")).isEqualTo(3);
        assertThat(MINI.sdd.rootsSeen).anySatisfy(seen -> {
            assertThat(seen.request()).isEqualTo("GET /sdd/fsm/research-demo");
            assertThat(seen.root()).isEqualTo("/research-root/demo");
        });
    }

    // ── AT-960-15-E-2：換世代的輸入與轉送 ────────────────────────────────────────────────

    @Test
    void AT_960_15_E_2_reinitNextRequiresAReasonUsesOnlyTheJwtSubjectAsDeciderAndRelaysBridgeConflictsVerbatim() {
        UUID id = fx.project("demo", "studio", "REVIEWING", "ESCALATED", "");
        String alice = adminAs("alice");
        String url = RESEARCH + "/projects/" + id + "/reinit";

        Resp ok = api.post(alice, url, map("generation", "next", "reason", "放棄舊鍵，換世代重審"));
        Resp forged = api.post(alice, url, map("generation", "next", "reason", "再來一次", "decidedBy", "mallory"));

        assertThat(ok.status()).isEqualTo(200);
        assertThat(ok.<String>read("$.data.fsmProject")).isEqualTo("research-demo-g2");
        assertThat(ok.<Integer>read("$.data.fsmGeneration")).isEqualTo(2);
        assertThat(ok.<String>read("$.data.gateDecisionId")).isNotBlank();
        assertThat(ok.<List<String>>read("$.data.flow.steps[*].id")).containsExactly("topic", "studio", "route", "build", "deliver");
        assertThat(forged.status()).isEqualTo(200);
        List<Call> relayed = bridge().calls.stream().filter(c -> c.path().endsWith(":reinit")).toList();
        assertThat(relayed).as("每個合法請求恰一個 :reinit").hasSize(2);
        assertThat(relayed).allSatisfy(call -> assertThat(call.body()).containsEntry("generation", "next").containsEntry("decided_by", "alice")
                .doesNotContainKeys("decidedBy", "mallory"));
        assertThat(relayed.get(0).body()).containsEntry("reason", "放棄舊鍵，換世代重審");
        assertThat(Arrays.stream(ResearchReinitRequest.class.getRecordComponents()).map(RecordComponent::getName)).as("請求本文型別沒有決定者欄")
                .containsExactly("generation", "reason");

        int calls = bridge().calls.size();
        for (Map<String, Object> bad : List.of(map("generation", "next"), map("generation", "next", "reason", "   "), map("generation", "next", "reason", "字".repeat(501)))) {
            Resp resp = api.post(alice, url, bad);
            assertThat(resp.status()).as(String.valueOf(bad)).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).isEqualTo("invalid_request");
            assertThat(resp.<List<String>>read("$.details.violations[*].field")).containsExactly("reason");
        }
        assertThat(bridge().calls).as("422 之後迷你 Bridge 請求數不增（轉送前依輸入閘驗證）").hasSize(calls);

        bridge().next("reinit:next", Reply.error(409, "fsm_state_conflict", "details", map("current_state", "IMPLEMENTATION")));
        Resp conflict = api.post(alice, url, map("generation", "next", "reason", "現態不對"));
        assertThat(conflict.status()).isEqualTo(409);
        assertThat(conflict.<String>read("$.reason")).isEqualTo("fsm_state_conflict");
        assertThat(conflict.<String>read("$.details.current_state")).isEqualTo("IMPLEMENTATION");

        List<Map<String, Object>> rows = auditRows();
        assertThat(rows).as("每個請求各多恰一列（含 422）").hasSize(2 + 3 + 1);
        assertThat(rows.subList(0, 2)).allSatisfy(row -> assertThat(row).containsEntry("subject", "alice").containsEntry("role", "ADMIN").containsEntry("http_status", 200));
        assertThat(rows.stream().map(r -> r.get("http_status"))).containsExactly(200, 200, 422, 422, 422, 409);
        assertThat(rows.stream().map(Object::toString)).noneMatch(text -> text.contains("mallory") || text.contains("放棄舊鍵"));
        assertThat(Set.of(rows.get(0).get("path"))).containsExactly("/api/v1/research/projects/" + id + "/reinit");
    }

    // ═══ ResearchToPRD P1（PKG-API-P1）══════════════════════════════════════════════════════

    @Test
    void AT_961_15_9_theDetailCarriesTheReadOnlyTargetScopeAndNothingElseChanges() {
        ResearchP1Fixtures p1 = new ResearchP1Fixtures(jdbc);
        for (String scope : List.of("AISDLC_MODULE", "STANDALONE_PROJECT", "UNDECIDED")) {
            UUID id = p1.project("scope-" + scope.toLowerCase().replace('_', '-'), scope);
            Resp resp = api.get(viewer(), RESEARCH + "/projects/" + id);
            assertThat(resp.status()).isEqualTo(200);
            assertThat(resp.<String>read("$.data.targetScope")).isEqualTo(scope);
        }
        assertThat(Arrays.stream(com.aisdlc.console.adapter.in.web.dto.research.ResearchCreateRequest.class.getRecordComponents()).map(RecordComponent::getName))
                .as("targetScope 是唯讀欄位：不出現在建立請求").doesNotContain("targetScope");
    }

    @Test
    void AT_961_15_E_2_anAllowlistEntry404NoLongerReadsAsAMissingResearchProject() {
        UUID id = fx.project("e2-404");

        Resp entry = api.raw(admin(), HttpMethod.PATCH, RESEARCH + "/allowlist/" + UUID.randomUUID(), "{\"enabled\":false}");
        bridge().next("cancel", Reply.error(404, "research_not_found", "research_id", id.toString()));
        Resp project = api.post(operator(), RESEARCH + "/projects/" + id + "/cancel");

        assertThat(entry.status()).isEqualTo(404);
        assertThat(project.status()).isEqualTo(404);
        assertThat(entry.<String>read("$.reason")).isEqualTo("research_not_found");
        assertThat(project.<String>read("$.reason")).isEqualTo("research_not_found");
        assertThat(entry.<String>read("$.message")).contains("允許清單條目不存在");
        assertThat(project.<String>read("$.message")).isEqualTo("研究專案不存在或已刪除");
    }

    @Test
    void AT_961_21_1_recordsAuditCountsR7R8R10R11R12FromTheV19TablesAndMissingIsExactlyR11AfterRouteAndSignoff() {
        ResearchP1Fixtures p1 = new ResearchP1Fixtures(jdbc);
        UUID id = p1.project("v19-audit", "UNDECIDED");
        fx.artifact(id, "ISSUE_SCOPE", 1, "{}");
        fx.artifact(id, "EVIDENCE_ITEMS", 1, "{\"items\":[]}");
        UUID source = fx.source(id, "S-001", "https://example.org/a", "T1");
        fx.fetch(id, source, "F-0001", "OK");
        fx.prdVersion(id, 1, "v1.0.0", "# PRD");
        UUID round = fx.round(id, 1, 1, 1, "AUTO", true, new BigDecimal("85.00"), 60, 0, true, "PASS", "PASS", 0);
        fx.scores(round, 85);
        fx.decision(id, "GATE0", "APPROVED", "research-v19-audit", "Gate-0", "{\"01_specs/PRD-v1.0.0.md\":\"sha256:" + "a".repeat(64) + "\"}");
        fx.event(id, 1, "research.step", "{}");
        p1.route(id, "SUCCEEDED", null);
        p1.decomposition(id, "SIGNED_OFF", "a".repeat(64), ResearchP1Fixtures.content("a".repeat(64), "[]", 2, 2));
        p1.scr(id, 1, "MINOR", "APPLIED");

        Resp done = api.get(viewer(), RESEARCH + "/projects/" + id + "/records/audit");
        List<Map<String, Object>> classes = done.read("$.data.classes");
        Map<String, Integer> counts = new LinkedHashMap<>();
        classes.forEach(c -> counts.put((String) c.get("id"), (Integer) c.get("count")));

        assertThat(classes).hasSize(14);
        assertThat(counts).containsEntry("R7", 1).containsEntry("R8", 1).containsEntry("R10", 0).containsEntry("R11", 0).containsEntry("R12", 1);
        assertThat(done.<List<String>>read("$.data.missing")).as("完成分流與簽核後 missing 恰為 R11（R10、R12 允許為 0）").containsExactly("R11");
        UUID fresh = p1.project("v19-fresh", "UNDECIDED");
        assertThat(api.get(viewer(), RESEARCH + "/projects/" + fresh + "/records/audit").<List<String>>read("$.data.missing")).contains("R7", "R8", "R11");
    }

    @Test
    void AT_961_21_2_confirmedRouteAndSignedOffDecompositionEachLeaveOneSuccessAuditRowWithTheBridgeTraceId() {
        ResearchP1Fixtures p1 = new ResearchP1Fixtures(jdbc);
        UUID routeResearch = p1.project("v19-route", "UNDECIDED");
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("track", "A");
        request.put("targetModule", "agentconsole");
        assertThat(api.post(admin(), RESEARCH + "/projects/" + routeResearch + "/route", request).status()).isEqualTo(200);

        UUID signResearch = p1.project("v19-sign", "UNDECIDED");
        fx.decision(signResearch, "GATE0", "APPROVED", "research-v19-sign", "Gate-0", "{\"01_specs/PRD-v1.0.0.md\":\"sha256:" + "a".repeat(64) + "\"}");
        String console = createProject(Map.of("name", "v19-sign-console", "executionPath", "/work/v19-sign", "passCriteria", "- 通過", "draft", true));
        p1.bind(signResearch, UUID.fromString(console));
        p1.decomposition(signResearch, "DRAFTED", "a".repeat(64), ResearchP1Fixtures.content("a".repeat(64), "[]", 2, 2));
        assertThat(api.post(operator(), RESEARCH + "/projects/" + signResearch + "/decomposition/signoff", Map.of()).status()).isEqualTo(200);

        for (String[] c : new String[][] {{"/projects/" + routeResearch + "/route", "admin", ":route"}, {"/projects/" + signResearch + "/decomposition/signoff", "operator",
                ":decomposition-signoff"}}) {
            List<Map<String, Object>> rows = jdbc.queryForList("select subject, role, method, http_status, trace_id from console.audit_log where path = ?", RESEARCH + c[0]);
            assertThat(rows).hasSize(1);
            assertThat(rows.get(0)).containsEntry("subject", c[1]).containsEntry("method", "POST").containsEntry("http_status", 200);
            String trace = String.valueOf(rows.get(0).get("trace_id"));
            assertThat(bridge().calls.stream().filter(call -> call.path().endsWith(c[2])).map(Call::traceId)).as("與送給 Bridge 的 X-Trace-Id 同一個").containsExactly(trace);
        }
    }

    @Test
    void AT_961_21_E_1_everyRejectedRouteRelatedWriteLeavesItsOwnAuditRowWithTheTrueStatus() {
        UUID id = new ResearchP1Fixtures(jdbc).project("v19-rejected", "UNDECIDED");
        String route = RESEARCH + "/projects/" + id + "/route";
        String scr = RESEARCH + "/projects/" + id + "/scr";
        bridge().next("scr", Reply.error(422, "invalid_request", "violations", List.of(map("field", "reason", "rule", "x", "message", "m"))));

        int viewerRoute = api.post(viewer(), route, Map.of("track", "A")).status();
        int operatorRoute = api.post(operator(), route, Map.of("track", "A")).status();
        int anonymous = api.post(null, route, Map.of("track", "A")).status();
        int scrRejected = api.post(operator(), scr, Map.of("kind", "MINOR", "sourceKind", "HUMAN", "reason", "x")).status();

        assertThat(List.of(viewerRoute, operatorRoute, anonymous, scrRejected)).containsExactly(403, 403, 401, 422);
        assertThat(jdbc.queryForList("select http_status from console.audit_log where path = ? order by occurred_at", Integer.class, route)).containsExactly(403, 403, 401);
        assertThat(jdbc.queryForList("select http_status from console.audit_log where path = ?", Integer.class, scr)).containsExactly(422);
    }

    @Test
    void AT_961_25_3_afterASuccessfulFreezeOnlyAResearchBoundProjectTriggersExactlyOneReconcileAndAFailingReconcileNeverBreaksTheFreeze() {
        ResearchP1Fixtures p1 = new ResearchP1Fixtures(jdbc);
        UUID bound = p1.project("freeze-bound", "UNDECIDED");
        String boundProject = createProject(Map.of("name", "e2e-bravo", "executionPath", "/work/e2e-bravo", "passCriteria", "- 通過"));
        p1.bind(bound, UUID.fromString(boundProject));
        String doc = "docs/03_testing/contracts/TCS-Alpha-20261017.md";

        Resp ok = api.post(operator(), "/api/v1/projects/" + boundProject + "/sdd/freeze", Map.of("reason", "規格已由 SDD session 走完，核准凍結", "docs", List.of(doc)));
        assertThat(ok.status()).isEqualTo(200);
        assertThat(bridge().countCalls("POST", "/research/projects/" + bound + ":reconcile")).as("恰一次").isEqualTo(1);

        MINI.sdd.addProject("e2e-delta", "HUMAN_PENDING", 1, "sid-delta", "2026-11-02T00:00:00+00:00", new MiniBridge.Sdd.SddRetry(0, null), Map.of("count", 0, "items", List.of()));
        String unbound = createProject(Map.of("name", "e2e-delta", "executionPath", "/work/e2e-delta", "passCriteria", "- 通過"));
        long before = bridge().calls.size();
        assertThat(api.post(operator(), "/api/v1/projects/" + unbound + "/sdd/freeze", Map.of("reason", "規格已由 SDD session 走完，核准凍結", "docs", List.of(doc))).status())
                .isEqualTo(200);
        assertThat(bridge().calls.size()).as("未綁研究專案：Bridge 的研究端點零請求").isEqualTo((int) before);

        MINI.sdd.addProject("e2e-echo", "HUMAN_PENDING", 1, "sid-echo", "2026-11-02T00:00:00+00:00", new MiniBridge.Sdd.SddRetry(0, null), Map.of("count", 0, "items", List.of()));
        UUID failing = p1.project("freeze-failing", "UNDECIDED");
        String failingProject = createProject(Map.of("name", "e2e-echo", "executionPath", "/work/e2e-echo", "passCriteria", "- 通過"));
        p1.bind(failing, UUID.fromString(failingProject));
        bridge().always("reconcile", Reply.error(500, "internal"));
        Resp survived = api.post(operator(), "/api/v1/projects/" + failingProject + "/sdd/freeze", Map.of("reason", "規格已由 SDD session 走完，核准凍結", "docs", List.of(doc)));
        assertThat(survived.status()).as("對帳失敗只記日誌，凍結照常成功").isEqualTo(200);
        assertThat(survived.<String>read("$.data.currentState")).isEqualTo("SPEC_FROZEN");
    }

    @Test
    void AT_961_20_E_3_theReconcileDtoPassesThePendingCorrectionStateThroughAndTheOpenApiNamesFourValues() {
        UUID id = fx.project("pending-correction");
        bridge().next("reconcile", Reply.ok(200, "consistent", false, "driftCount", 0, "checks", List.of(MiniResearch.reconcileCheck("fsm_flow_mapping", "pending_correction", true, "", List.of()))));

        Resp resp = api.post(operator(), RESEARCH + "/projects/" + id + "/reconcile");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.checks[0].status")).isEqualTo("pending_correction");
        String docs = api.get(null, "/v3/api-docs").body();
        assertThat(docs).contains("pending_correction").contains("NOT_EVALUABLE");
    }
}
