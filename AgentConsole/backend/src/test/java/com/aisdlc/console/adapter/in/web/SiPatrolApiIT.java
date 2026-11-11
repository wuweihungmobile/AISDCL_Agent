package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 巡邏快照的 backend 面（{@code GET /api/v1/si/patrol}；TCS-SiFlowVisibility-20261111 AT-966-3-1～3-4、3-E-1；3-5 在 {@code OpenApiIT}、3-6 在
 * {@code SiReadOnlyArchTest}），對真的 HTTP 迷你 Bridge（{@code MINI.patrol(...)}）驗映射的每一列。
 * 為什麼重要：快照是主機巡邏器的「畫面不能說謊」的資料源——backend 只准把 Bridge 的本文換欄名風格原樣轉出；若替它補一句話、吞一句話（把
 * {@code report_missing} 改寫成別的原因）、快取舊資料、或每次呼叫都寫稽核列，掌舵者看到的「巡邏有沒有在跑」就不可信。
 */
class SiPatrolApiIT extends AbstractExecutionIT {

    private static final String PATROL = "/api/v1/si/patrol";
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final String READ_AT = "2026-11-11T14:00:00+08:00";
    private static final List<String> CAUSES = List.of("report_dir_unset", "report_missing", "report_unreadable", "report_invalid");
    /** 測試獨立的欄名對映（與 {@code SiKeyNames} 同規則：符合小寫底線式才轉駝峰），作為逐值比對的預期來源，不借用被測程式。 */
    private static final Pattern SNAKE = Pattern.compile("[a-z][a-z0-9]*(?:_[a-z0-9]+)+");

    private static Map<String, Object> map(Object... keyValues) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            out.put((String) keyValues[i], keyValues[i + 1]);
        }
        return out;
    }

    /** 測試獨立的單一鍵對映。 */
    private static String camelOf(String key) {
        if (!SNAKE.matcher(key).matches()) {
            return key;
        }
        String[] parts = key.split("_");
        StringBuilder out = new StringBuilder(parts[0]);
        for (int i = 1; i < parts.length; i++) {
            out.append(Character.toUpperCase(parts[i].charAt(0))).append(parts[i].substring(1));
        }
        return out.toString();
    }

    /** {@code PR()}：C-1 的 {@code report} 基準夾具（snake_case；含 schedule、ingest、runs、push 的全部巢狀鍵）。 */
    private static Map<String, Object> report() {
        return map(
                "schema_rev", 1, "generated_at", "2026-11-11T13:57:00+08:00", "off", false, "heartbeat_minutes", 15, "ledger_seq", 130,
                "truncated", false,
                "steps", List.of(map("step", "巡視", "result", "完成"), map("step", "入帳", "result", "完成"), map("step", "到期", "result", "完成"),
                        map("step", "運轉", "result", "完成"), map("step", "推進", "result", "完成")),
                "schedule", map("enabled", true, "current", map("code", "SCHED-CELL-RAN", "text", "本期已經跑過一次，等下一期"),
                        "last_skip", map("seq", 99, "t", "2026-11-11T09:00:00+08:00", "code", "SKIP-BUSY", "text", "有運轉進行中，略過",
                                "audit_ref", "a1000000-0000-4000-8000-000000000001")),
                "ingest", List.of(map("audit_ref", "a1000000-0000-4000-8000-000000000002", "kind", "decide", "status", "rejected",
                        "code", "ING-X", "text", "前提態不符", "permanent", true)),
                "props", List.of(map("id", "PROP-SI-901", "state", "verified", "code", "WAIT-PROMOTE-DECISION", "who", "掌舵者",
                        "text", "驗證通過，等你決定是否晉升")),
                "runs", map("live", List.of(map("run", "RUN-SI-901", "purpose", "scheduled", "started_at", "2026-11-11T13:00:00+08:00",
                                "wall_due_at", "2026-11-11T17:00:00+08:00")),
                        "waiting", List.of(map("run", "RUN-SI-902", "code", "RUN-WAIT-QUOTA", "text", "等額度")), "queued", List.of()),
                "push", map("enabled", true, "state", "idle", "code", "PUSH-NOT-AHEAD", "text", "沒有待推送的提交", "retry", null, "sha", null,
                        "ahead", 0, "attempts", 0, "finished_at", null, "tick_at", null));
    }

    private static Map<String, Object> body(Map<String, Object> report) {
        return map("schema_rev", 1, "kind", "patrol", "read_at", READ_AT, "report", report);
    }

    private Resp get(String token) {
        return api.get(token, PATROL);
    }

    private static JsonNode data(Resp resp) {
        return JSON.readTree(resp.body()).get("data");
    }

    private static MockHttpServletRequestBuilder withBody(MockHttpServletRequestBuilder builder) {
        return builder.contentType(MediaType.APPLICATION_JSON).content("{}");
    }

    /** 把 snake_case 的來源樹以測試自己的規則轉成預期的 camelCase 樹（不改值）。 */
    private static JsonNode expectedCamel(JsonNode node) {
        if (node.isObject()) {
            var out = JSON.createObjectNode();
            Iterator<Map.Entry<String, JsonNode>> fields = node.properties().iterator();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                out.set(camelOf(field.getKey()), expectedCamel(field.getValue()));
            }
            return out;
        }
        if (node.isArray()) {
            var out = JSON.createArrayNode();
            node.forEach(item -> out.add(expectedCamel(item)));
            return out;
        }
        return node;
    }

    private static TreeSet<String> allKeys(JsonNode node) {
        TreeSet<String> keys = new TreeSet<>();
        if (node.isObject()) {
            node.properties().forEach(e -> {
                keys.add(e.getKey());
                keys.addAll(allKeys(e.getValue()));
            });
        } else if (node.isArray()) {
            node.forEach(item -> keys.addAll(allKeys(item)));
        }
        return keys;
    }

    // ── AT-966-3-1：角色矩陣與非 GET 方法 ────────────────────────────────────────────────────────

    @Test
    void AT_966_3_1_theRoleMatrixAllowsViewerAndAboveAndEveryNonGetMethodIs405ForAdmin() {
        MINI.patrol(200, body(report()));
        String viewer = viewer();
        String operator = operator();
        String admin = admin();
        assertThat(get(null).status()).as("無 token").isEqualTo(401);
        assertThat(get(null).has("$.data")).as("401 沒有 data").isFalse();
        assertThat(get("garbage").status()).as("壞 token").isEqualTo(401);
        assertThat(MINI.requests()).as("401 不觸及 Bridge").isEmpty();
        Resp asViewer = get(viewer);
        Resp asOperator = get(operator);
        Resp asAdmin = get(admin);
        assertThat(asViewer.status()).isEqualTo(200);
        assertThat(asOperator.status()).isEqualTo(200);
        assertThat(asAdmin.status()).isEqualTo(200);
        assertThat(data(asOperator)).as("三種角色的 data 相同（信封的追蹤欄位每次不同）").isEqualTo(data(asViewer));
        assertThat(data(asAdmin)).isEqualTo(data(asViewer));
        List<MockHttpServletRequestBuilder> nonGet = List.of(
                withBody(MockMvcRequestBuilders.post(PATROL)), withBody(MockMvcRequestBuilders.put(PATROL)),
                withBody(MockMvcRequestBuilders.patch(PATROL)), withBody(MockMvcRequestBuilders.delete(PATROL)));
        assertThat(nonGet).hasSize(4);
        for (MockHttpServletRequestBuilder request : nonGet) {
            assertThat(api.send(admin, request).status()).as("ADMIN 的非 GET 方法").isEqualTo(405);
        }
        assertThat(MINI.requests()).as("只有三個 GET 觸及 Bridge").hasSize(3);
    }

    // ── AT-966-3-2：欄名深層對映 ────────────────────────────────────────────────────────────────

    @Test
    void AT_966_3_2_everyNestedKeyIsMappedToCamelCaseAndEveryValueIsUnchanged() {
        Map<String, Object> source = body(report());
        MINI.patrol(200, source);

        JsonNode actual = data(get(viewer()));

        assertThat(actual.get("schemaRev").asInt()).isEqualTo(1);
        assertThat(actual.get("kind").asString()).isEqualTo("patrol");
        assertThat(actual.get("readAt").asString()).isEqualTo(READ_AT);
        JsonNode report = actual.get("report");
        for (String key : List.of("generatedAt", "heartbeatMinutes", "ledgerSeq", "truncated", "off")) {
            assertThat(report.has(key)).as("report.%s", key).isTrue();
        }
        assertThat(report.at("/schedule/lastSkip/auditRef").asString()).isEqualTo("a1000000-0000-4000-8000-000000000001");
        assertThat(report.at("/ingest/0/auditRef").asString()).isEqualTo("a1000000-0000-4000-8000-000000000002");
        assertThat(report.at("/runs/live/0/startedAt").asString()).isEqualTo("2026-11-11T13:00:00+08:00");
        assertThat(report.at("/runs/live/0/wallDueAt").asString()).isEqualTo("2026-11-11T17:00:00+08:00");
        assertThat(report.at("/runs/waiting/0/code").asString()).isEqualTo("RUN-WAIT-QUOTA");
        assertThat(report.at("/push/finishedAt").isNull()).as("null 值保留（push.finishedAt）").isTrue();
        assertThat(report.at("/push/tickAt").isNull()).isTrue();
        assertThat(report.at("/push/retry").isNull()).isTrue();
        assertThat(report.at("/props/0/id").asString()).isEqualTo("PROP-SI-901");
        assertThat(report.at("/runs/queued").isArray() && report.at("/runs/queued").isEmpty()).as("queued 恆空陣列原樣").isTrue();
        assertThat(actual).as("整棵樹與測試獨立算出的預期 camelCase 樹逐值相等").isEqualTo(expectedCamel(JSON.valueToTree(source)));
        for (String snake : List.of("schema_rev", "read_at", "generated_at", "heartbeat_minutes", "ledger_seq", "last_skip", "audit_ref",
                "started_at", "wall_due_at", "finished_at", "tick_at")) {
            assertThat(allKeys(actual)).as("原 snake_case 鍵 %s 不存在", snake).doesNotContain(snake);
        }
        assertThat(allKeys(actual)).as("已是 camelCase 或單字的鍵恆等").contains("runs", "push", "schedule", "steps", "props");
    }

    // ── AT-966-3-3：Bridge 錯誤逐字透傳 ─────────────────────────────────────────────────────────

    @Test
    void AT_966_3_3_everyBridgeCauseIsForwardedVerbatimWithoutDataAndWithoutRetry() {
        String viewer = viewer();
        for (String cause : CAUSES) {
            MINI.reset();
            String detail = "原因說明：" + cause + "\n第二行（全形）";
            MINI.patrol(503, map("reason", "si_unavailable", "cause", cause, "detail", detail));

            Resp resp = get(viewer);

            assertThat(resp.status()).as(cause).isEqualTo(503);
            assertThat(resp.<String>read("$.reason")).as(cause).isEqualTo(ErrorReasons.SI_UNAVAILABLE);
            assertThat(resp.<String>read("$.details.cause")).as(cause).isEqualTo(cause);
            assertThat(resp.<String>read("$.details.detail")).as("%s：detail 逐字", cause).isEqualTo(detail);
            assertThat(resp.has("$.data")).as("%s：失敗沒有 data", cause).isFalse();
            assertThat(MINI.countRequests("GET /si/patrol")).as("%s：只打一次 Bridge（不重試）", cause).isEqualTo(1);
        }
        MINI.reset();
        MINI.patrol(200, body(report()));
        assertThat(get(viewer).status()).as("失敗之後立即重請求：沒有殘留的錯誤").isEqualTo(200);

        MINI.reset();

        // 不可達＝502
        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp refused = get(viewer);
        assertThat(refused.status()).isEqualTo(502);
        assertThat(refused.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_UNREACHABLE);
        assertThat(refused.has("$.data")).isFalse();
        resetSystemConfigs();
        thresholds.invalidate();

        // 讀取逾時＝504，約 20 秒、不重試
        MINI.reset();
        MINI.patrol(200, body(report()));
        MINI.si.delayMillis = 21_000;
        long started = System.nanoTime();
        Resp timedOut = get(viewer);
        Duration elapsed = Duration.ofNanos(System.nanoTime() - started);
        assertThat(timedOut.status()).isEqualTo(504);
        assertThat(timedOut.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_TIMEOUT);
        assertThat(timedOut.has("$.data")).isFalse();
        assertThat(elapsed).as("讀取逾時 20 秒、不重試（若重試會超過 40 秒）").isBetween(Duration.ofSeconds(19), Duration.ofSeconds(40));
        assertThat(MINI.countRequests("GET /si/patrol")).as("逾時只送一次請求").isEqualTo(1);
    }

    // ── AT-966-3-4：恰一次 Bridge 呼叫、零 DB 寫入 ───────────────────────────────────────────────

    private List<String> snapshot(String table) {
        List<String> rows = new ArrayList<>();
        jdbc.queryForList("select * from console." + table).forEach(row -> rows.add(row.toString()));
        rows.sort(null);
        return rows;
    }

    @Test
    void AT_966_3_4_eachRequestIsExactlyOneBridgeGetAndNothingIsWrittenToTheDatabase() {
        String viewer = viewer();
        String admin = admin();
        MINI.patrol(200, body(report()));
        List<String> writesBefore = snapshot("si_console_writes");
        List<String> auditBefore = snapshot("audit_log");
        MINI.si.patrolSeen.clear();

        List<Integer> statuses = new ArrayList<>();
        for (int i = 0; i < 4; i++) {
            statuses.add(get(i % 2 == 0 ? viewer : admin).status());
        }
        MINI.patrol(503, map("reason", "si_unavailable", "cause", "report_missing", "detail", "還沒有快照"));
        statuses.add(get(viewer).status());

        assertThat(statuses).containsExactly(200, 200, 200, 200, 503);
        assertThat(MINI.requests()).as("恰五筆，皆為 GET /si/patrol").containsExactly(
                "GET /si/patrol", "GET /si/patrol", "GET /si/patrol", "GET /si/patrol", "GET /si/patrol");
        assertThat(MINI.si.patrolSeen).hasSize(5).allSatisfy(seen -> {
            assertThat(seen.method()).isEqualTo("GET");
            assertThat(seen.uri()).isEqualTo("/si/patrol");
            assertThat(seen.query()).as("不轉發任何查詢參數").isNull();
            assertThat(seen.tokenHeader()).as("讀取不帶 X-Bridge-Token").isFalse();
            assertThat(seen.bodyBytes()).as("無請求本文").isLessThanOrEqualTo(0L);
        });
        assertThat(snapshot("si_console_writes")).as("si_console_writes 列數與內容不變").isEqualTo(writesBefore);
        assertThat(snapshot("audit_log")).as("audit_log 列數與內容不變（不為巡邏快照寫稽核列）").isEqualTo(auditBefore);
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log where entity_type ilike '%patrol%'", Integer.class)).isZero();
    }

    // ── AT-966-3-E-1：未知鍵、非 ASCII、1 MiB 本文與腳本字樣原樣 ────────────────────────────────

    @Test
    void AT_966_3_E_1_unknownKeysNonAsciiTheScriptTextAndAMebibyteBodyComeThroughUnchanged() {
        String hostile = "<script>alert(1)</script>**粗體** ＡＢＣ１２３ 😀   結尾";
        Map<String, Object> report = report();
        List<Map<String, Object>> props = new ArrayList<>();
        props.add(map("id", "PROP-SI-901", "state", "verified", "code", "WAIT-PROMOTE-DECISION", "who", "掌舵者", "text", hostile));
        report.put("props", props);
        report.put("future_key", "舊鍵值");
        report.put("futureKey", "新鍵值");
        report.put("another_unknown", map("nested_one", 1, "nestedTwo", 2));
        String filler = "x".repeat(1_040_000);
        report.put("filler", filler);
        Map<String, Object> source = body(report);
        source.put("extra_top_key", "頂層未知鍵");
        MINI.patrol(200, source);
        int sourceBytes = JSON.writeValueAsBytes(source).length;
        assertThat(sourceBytes).as("夾具的 report 約 1,048,000 位元組").isBetween(1_040_000, 1_048_576);

        Resp resp = get(viewer());

        assertThat(resp.status()).isEqualTo(200);
        JsonNode data = data(resp);
        assertThat(data.get("extraTopKey").asString()).as("頂層未知鍵依規則轉換").isEqualTo("頂層未知鍵");
        JsonNode got = data.get("report");
        assertThat(got.at("/props/0/text").asString()).as("字串值逐位元組相等（不轉義、不截斷）").isEqualTo(hostile);
        assertThat(got.get("futureKey").asString()).as("不變的鍵先保有名字").isEqualTo("新鍵值");
        assertThat(got.get("future_key").asString()).as("撞名者保留原鍵、不丟欄").isEqualTo("舊鍵值");
        assertThat(got.at("/anotherUnknown/nestedOne").asInt()).isEqualTo(1);
        assertThat(got.at("/anotherUnknown/nestedTwo").asInt()).isEqualTo(2);
        assertThat(got.get("filler").asString()).as("1 MiB 級本文不被截斷").isEqualTo(filler);
        assertThat(resp.body().length()).as("回應完整可解析").isGreaterThan(1_040_000);
    }
}
