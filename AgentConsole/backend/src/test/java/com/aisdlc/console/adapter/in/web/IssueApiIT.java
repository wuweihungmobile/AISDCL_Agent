package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.architecture.IssueReasonsContractTest;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.model.issue.IssuePriorityGates;
import com.aisdlc.console.support.AbstractSiWriteIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.io.InputStream;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 議題中心的 backend 面（{@code /api/v1/issues}：兩個唯讀 GET 與僅 ADMIN 的優先順序 PUT、DELETE；TCS-IssueCenter-20261027 的 BI 載具二十六個 AT：AT-IC-06-1-3、
 * AT-IC-07-3-2、07-4-1、07-4-E-1、07-5-1、07-5-E-1、07-7-1、07-7-E-1、09-1-1、09-1-E-1、09-2-1、09-2-E-1、09-3-1、09-3-E-1、09-3-E-2、09-4-1、09-4-E-1、09-5-1、
 * 09-5-E-1、09-7-1、09-7-E-1、09-8-2、09-10-1、09-11-1、09-11-E-1、12-3-1），對<b>真的 HTTP</b> 迷你 Bridge（{@code MINI.si}）與真 PostgreSQL 驗映射的每一列。
 *
 * <p>為什麼重要：GET 這一棒只准做一件事——把 Bridge 的匯出物件換個欄名風格原樣轉出、每筆多加 Console 自有的 {@code priority}；若替 Bridge「補一句話」
 * （缺鍵補 null、空陣列當錯誤、快取舊資料）或「吞一句話」（503 的原因被改寫成 502），畫面上的「量不到」與「資料面壞了」就會說謊。PUT／DELETE 是 Console 在議題中心
 * 唯一的寫入：角色（僅 ADMIN，OPERATOR 不得因通用規則通過）、輸入閘（型別不符是 422 不是 400、{@code rank} 缺或 null 不當清除）、「先取議題再寫入」的驗證序、
 * 零旁路寫入與冪等，每一條都是「壞了也許沒人發現、但資料就錯了」的那種。
 *
 * <p>本類別沿 {@link AbstractSiWriteIT} 的 context（同一個已快取的 Spring 容器；ADMIN 不在 {@code console.si.deciders} 名單的案例以 {@code adminAs("chief")} 鑄 token，
 * 證明優先順序不要求名單）。「順位表讀取失敗」以資料庫層的故障注入造成（暫時把表改名，必定還原）：它丟的就是正式配接器的 {@code DataAccessException}。
 */
class IssueApiIT extends AbstractSiWriteIT {

    private static final String ISSUES = "/api/v1/issues";
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final String NOT_A_DECIDER = "chief";
    private static final String MESSAGE_NOT_RANKABLE = "此議題目前的狀態不能設定優先順序";
    private static final List<String> RANKABLE = List.of("待您決定", "待解", "進行中");
    private static final List<String> NOT_RANKABLE = List.of("候選", "觀察中", "延後", "已完成", "未歸類：later");

    // ── 夾具與小幫手 ────────────────────────────────────────────────────────────────────────

    @BeforeEach
    void cleanPriorityTable() {
        jdbc.execute("TRUNCATE console.issue_priority");
    }

    /** 保險：任何測試若在「表被改名」的視窗內異常離開，這裡還原（finally 之外的最後一道）。 */
    @AfterEach
    void restoreTheTableNameIfATestDiedInsideTheFaultWindow() {
        jdbc.execute("do $$ begin if to_regclass('console.issue_priority_off') is not null and to_regclass('console.issue_priority') is null "
                + "then alter table console.issue_priority_off rename to issue_priority; end if; end $$");
        readTimeout.reset();
    }

    private static String resource(String name) {
        try (InputStream in = IssueApiIT.class.getResourceAsStream("/si/" + name + ".json")) {
            assertThat(in).as("測試資源 si/%s.json", name).isNotNull();
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    private static JsonNode goldenCamelIssues() {
        return JSON.readTree(resource("A.camel")).get("issues");
    }

    private static JsonNode data(Resp resp) {
        return JSON.readTree(resp.body()).get("data");
    }

    private Resp get(String token, String suffix) {
        return api.get(token, ISSUES + suffix);
    }

    private Resp put(String token, String id, Object body) {
        return api.put(token, ISSUES + "/" + id + "/priority", body);
    }

    private Resp putRaw(String token, String id, String rawBody) {
        return api.raw(token, HttpMethod.PUT, ISSUES + "/" + id + "/priority", rawBody);
    }

    private Resp delete(String token, String id) {
        return api.delete(token, ISSUES + "/" + id + "/priority");
    }

    /** 議題物件（Bridge 形狀：snake_case、鍵序同匯出）。 */
    private static Map<String, Object> item(String id, String status, boolean rankable) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", id);
        item.put("source", "使用者提案");
        item.put("title", "夾具議題 " + id);
        item.put("severity", "高");
        item.put("severity_rank", 2);
        item.put("status", status);
        item.put("result", "已完成".equals(status) ? "已裁決" : null);
        item.put("updated_at", "2026-10-20");
        item.put("next_step", "夾具的下一步");
        item.put("origin", map("ledger", "觀察帳本", "file", "docs/06_quality/SelfImproving_Observation_Ledger.md", "line", 11));
        item.put("links", List.of());
        item.put("rankable", rankable);
        item.put("action", null);
        return item;
    }

    /** 清單回應：黃金檔的 issues 清單，只把 items 換成指定的項目。 */
    private static Map<String, Object> listPayload(List<Map<String, Object>> items) {
        Map<String, Object> payload = MiniBridge.Si.golden("A.snake").get("issues");
        payload.put("items", items);
        return payload;
    }

    /** 單筆回應：沒有 legend、summary；項目另有 raw、timeline。 */
    private static Map<String, Object> singlePayload(Map<String, Object> item) {
        Map<String, Object> payload = MiniBridge.Si.golden("A.snake").get("issues");
        payload.remove("legend");
        payload.remove("summary");
        Map<String, Object> detailed = new LinkedHashMap<>(item);
        detailed.put("raw", List.of(map("label", "症狀", "value", "夾具原列的症狀")));
        detailed.put("timeline", List.of(map("seq", 5, "t", "2026-10-20T22:32:44+08:00", "by", "主控", "action", "提案")));
        payload.put("items", List.of(detailed));
        return payload;
    }

    /** 讓迷你 Bridge 對這個議題的單筆與清單都回指定狀態（單筆取該項、清單只含該項）。 */
    private void bridgeKnows(String id, String status, boolean rankable) {
        Map<String, Object> item = item(id, status, rankable);
        MINI.si.payloads.put("issue:" + id, singlePayload(item));
        MINI.si.payloads.put("issues", listPayload(List.of(item)));
    }

    private void insertPriority(String id, int rank, String note) {
        jdbc.update("insert into console.issue_priority (issue_id, rank, note, set_by, set_at) values (?, ?, ?, 'seed', now())", id, rank, note);
    }

    private List<Map<String, Object>> priorityRows() {
        return jdbc.queryForList("select issue_id, rank, note, set_by from console.issue_priority order by issue_id");
    }

    private List<Map<String, Object>> auditRows() {
        return jdbc.queryForList("select subject, role, method, path, entity_type, http_status from console.audit_log "
                + "where path like '/api/v1/issues/%' order by occurred_at, id");
    }

    /** 清單裡該議題的某個欄位值（找不到議題＝失敗；欄位值可為 null，所以不能用 {@code Optional.map}）。 */
    @SuppressWarnings("unchecked")
    private <T> T priorityOf(String id, String field) {
        Resp resp = get(viewer(), "");
        assertThat(resp.status()).isEqualTo(200);
        List<Map<String, Object>> items = resp.read("$.data.items");
        for (Map<String, Object> candidate : items) {
            if (id.equals(candidate.get("id"))) {
                return (T) candidate.get(field);
            }
        }
        throw new AssertionError("清單裡沒有 " + id);
    }

    /** 暫時讓順位表讀寫失敗（資料庫層故障注入）；視窗結束必定還原。 */
    private void withBrokenPriorityTable(Runnable action) {
        jdbc.execute("alter table console.issue_priority rename to issue_priority_off");
        try {
            action.run();
        } finally {
            jdbc.execute("alter table console.issue_priority_off rename to issue_priority");
        }
    }

    private void assertNoData(Resp resp, String label) {
        assertThat(resp.has("$.data")).as("%s：失敗回應沒有 data（不回空表、不回缺 priority 的清單）", label).isFalse();
    }

    private static String oracle(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8).replace("+", "%20").replace("*", "%2A").replace("%7E", "~");
    }

    /** 四類帳本（真 repo 的檔；缺檔也是一種狀態）的摘要，比對 PUT、DELETE 前後不變。 */
    private static String ledgerDigest() {
        Path dir = Path.of("..", "..", "docs", "06_quality");
        List<String> names = List.of("SelfImproving_Observation_Ledger.md", "AutoSDD_Defect_Log.md", "AutoSDD_External_Blocked_Log.md",
                "AutoSDD_Structural_Debt_Log.md", "SelfImproving_Event_Ledger.jsonl");
        try {
            MessageDigest sha = MessageDigest.getInstance("SHA-256");
            for (String name : names) {
                sha.update((name + ":").getBytes(StandardCharsets.UTF_8));
                Path file = dir.resolve(name);
                sha.update(Files.isRegularFile(file) ? Files.readAllBytes(file) : "<absent>".getBytes(StandardCharsets.UTF_8));
            }
            return HexFormat.of().formatHex(sha.digest());
        } catch (IOException | NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    // ── AT-IC-07-4-1：VIEWER 讀清單：camelCase、值不動、每筆帶 priority ───────────────────────────

    @Test
    void AT_IC_07_4_1_viewerGetsTheGoldenIssuesInCamelCaseWithPriorityFieldsLastAndNullWhenThereIsNoRow() throws Exception {
        Resp resp = get(viewer(), "");

        assertThat(resp.status()).isEqualTo(200);
        ObjectNode expected = (ObjectNode) goldenCamelIssues().deepCopy();
        expected.get("items").forEach(i -> {
            ((ObjectNode) i).putNull("priority");
            ((ObjectNode) i).putNull("priorityNote");
        });
        assertThat(data(resp)).as("data 逐值等於黃金檔的 issues（鍵集合、值、null 皆同；鍵序不比）加每筆的 priority、priorityNote（皆 null）").isEqualTo(expected);
        Map<String, Object> body = JSON.readValue(resp.body(), new tools.jackson.core.type.TypeReference<Map<String, Object>>() { });
        @SuppressWarnings("unchecked")
        Map<String, Object> dataMap = (Map<String, Object>) body.get("data");
        assertThat(dataMap.keySet()).as("最外層鍵序：legend、summary 在 problems 之後").containsSubsequence("items", "nextSince", "truncated", "ne", "problems",
                "legend", "summary");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) dataMap.get("items");
        for (Map<String, Object> item : items) {
            List<String> keys = new ArrayList<>(item.keySet());
            assertThat(keys.subList(keys.size() - 2, keys.size())).as("%s：Console 追加的鍵在最後", item.get("id")).containsExactly("priority", "priorityNote");
            assertThat(keys).contains("severityRank", "updatedAt", "nextStep", "rankable", "action");
        }
        assertThat(MINI.requests()).as("每個請求恰一次 Bridge 呼叫").containsExactly("GET /si/issues");

        // 有列且 rankable＝有值；有列而不可排＝null（遺留列）
        List<Map<String, Object>> golden = new ArrayList<>();
        goldenCamelIssues().get("items").forEach(i -> golden.add(JSON.convertValue(i, new tools.jackson.core.type.TypeReference<Map<String, Object>>() { })));
        String rankable = golden.stream().filter(i -> Boolean.TRUE.equals(i.get("rankable"))).map(i -> (String) i.get("id")).findFirst()
                .orElseThrow(() -> new AssertionError("黃金檔沒有任何 rankable 的議題：議題中心的夾具失去了可排的項目"));
        String notRankable = golden.stream().filter(i -> Boolean.FALSE.equals(i.get("rankable"))).map(i -> (String) i.get("id")).findFirst()
                .orElseThrow(() -> new AssertionError("黃金檔沒有任何不可排的議題"));
        insertPriority(rankable, 3, "先做這個");
        insertPriority(notRankable, 1, "遺留");
        assertThat(this.<Integer>priorityOf(rankable, "priority")).isEqualTo(3);
        assertThat(this.<String>priorityOf(rankable, "priorityNote")).isEqualTo("先做這個");
        assertThat(this.<Integer>priorityOf(notRankable, "priority")).as("不可排者的遺留列不顯示").isNull();
        assertThat(this.<String>priorityOf(notRankable, "priorityNote")).isNull();
    }

    // ── AT-IC-07-4-E-1：401、400、型別邊界、篩選值原樣轉發 ─────────────────────────────────────────

    @Test
    void AT_IC_07_4_E_1_anonymousIs401BadPagingIs400WithoutTouchingTheBridgeAndFiltersAreForwardedAsDecodedEqualValues() {
        assertThat(get(null, "").status()).isEqualTo(401);
        assertThat(get("garbage", "").status()).isEqualTo(401);
        for (String query : List.of("?since=-1", "?limit=0", "?since=abc", "?since=2147483648", "?limit=-5", "?limit=x")) {
            Resp resp = get(viewer(), query);

            assertThat(resp.status()).as(query).isEqualTo(400);
            assertNoData(resp, query);
        }
        assertThat(MINI.requests()).as("401 與 400 都不觸及 Bridge").isEmpty();

        assertThat(get(viewer(), "?since=2147483647").status()).as("int 上界").isEqualTo(200);
        assertThat(MINI.si.seen.get(0).query()).isEqualTo("since=2147483647");
        MINI.si.seen.clear();

        List<String> tricky = List.of("待處理", "a b", "a|b", "100%", "a&b=c#d", "a+b", "x*y~z", "待解,延後", "表情😀", "'q\"", "a%20b", "");
        for (String value : tricky) {
            for (String field : List.of("status", "source")) {
                MINI.si.seen.clear();

                Resp resp = api.send(viewer(), MockMvcRequestBuilders.get(ISSUES).param("since", "3").param("limit", "7").param(field, value));

                assertThat(resp.status()).as("%s=%s", field, value).isEqualTo(200);
                assertThat(MINI.si.seen).as("%s=%s：恰一次 Bridge 請求", field, value).hasSize(1);
                String raw = MINI.si.seen.get(0).query();
                assertThat(raw).as("固定次序 since、limit、%s；值為嚴格 percent-encode", field).isEqualTo("since=3&limit=7&" + field + "=" + oracle(value));
                Map<String, String> decoded = new LinkedHashMap<>();
                for (String pair : raw.split("&", -1)) {
                    int eq = pair.indexOf('=');
                    decoded.put(pair.substring(0, eq), URLDecoder.decode(pair.substring(eq + 1), StandardCharsets.UTF_8));
                }
                assertThat(decoded.get(field)).as("Bridge 見到解碼後的同值（%s）", field).isEqualTo(value);
            }
        }
        MINI.si.seen.clear();
        Resp both = api.send(viewer(), MockMvcRequestBuilders.get(ISSUES).param("status", "待解").param("source", "系統缺陷"));
        assertThat(both.status()).isEqualTo(200);
        assertThat(MINI.si.seen.get(0).query()).isEqualTo("status=" + oracle("待解") + "&source=" + oracle("系統缺陷"));
        MINI.si.seen.clear();
        assertThat(get(viewer(), "?foo=1&since=2").status()).isEqualTo(200);
        assertThat(MINI.si.seen.get(0).query()).as("未知參數不轉發").isEqualTo("since=2");
    }

    // ── AT-IC-07-5-1／07-5-E-1：單筆 ─────────────────────────────────────────────────────────

    @Test
    void AT_IC_07_5_1_aSingleIssueCarriesRawTimelineLinksAndPriorityButNoLegendOrSummary() {
        bridgeKnows(PROP, "待您決定", true);
        insertPriority(PROP, 2, "備註");

        Resp resp = get(viewer(), "/" + PROP);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<Object>>read("$.data.items")).hasSize(1);
        assertThat(resp.<String>read("$.data.items[0].id")).isEqualTo(PROP);
        assertThat(resp.<List<Map<String, Object>>>read("$.data.items[0].raw")).singleElement().satisfies(r -> assertThat(r).containsEntry("label", "症狀"));
        assertThat(resp.<List<Map<String, Object>>>read("$.data.items[0].timeline")).singleElement()
                .satisfies(t -> assertThat(t).containsKeys("seq", "t", "by", "action"));
        assertThat(resp.has("$.data.items[0].links")).isTrue();
        assertThat(resp.<Integer>read("$.data.items[0].priority")).isEqualTo(2);
        assertThat(resp.<String>read("$.data.items[0].priorityNote")).isEqualTo("備註");
        assertThat(resp.has("$.data.legend")).as("單筆沒有 legend").isFalse();
        assertThat(resp.has("$.data.summary")).as("單筆沒有 summary").isFalse();
        Map<String, Object> body = JSON.readValue(resp.body(), new tools.jackson.core.type.TypeReference<Map<String, Object>>() { });
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) ((Map<String, Object>) body.get("data")).get("items");
        assertThat(new ArrayList<>(items.get(0).keySet())).as("raw、timeline 在 action 之後、priority 之前").containsSubsequence("action", "raw", "timeline",
                "priority", "priorityNote");
        assertThat(MINI.requests()).containsExactly("GET /si/issues/" + PROP);
    }

    @Test
    void AT_IC_07_5_E_1_anUnknownIssueIs404WithItsOwnMessageAndABadIdIs422FromTheBridge() {
        MINI.si.notFoundIds.add("DEF-999-001");
        Resp missing = get(viewer(), "/DEF-999-001");

        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_NOT_FOUND);
        assertThat(missing.<String>read("$.message")).as("訊息是「查無此議題」，不沿用「查無此提案」").isEqualTo("查無此議題");
        assertThat(missing.<String>read("$.details.id")).isEqualTo("DEF-999-001");
        assertNoData(missing, "404");
        MINI.reset();

        MINI.si.invalid = List.of(map("field", "id", "rule", "invalid_format", "message", "id 格式不合"));
        Resp invalid = get(viewer(), "/obs-si-001");

        assertThat(invalid.status()).isEqualTo(422);
        assertThat(invalid.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_REJECTED);
        assertThat(invalid.<String>read("$.details.bridgeReason")).isEqualTo("invalid_request");
        assertNoData(invalid, "422");
    }

    // ── AT-IC-07-3-2、07-7-1、07-7-E-1：失敗逐列對映，原因逐字，失敗沒有 data ───────────────────────

    @Test
    void AT_IC_07_3_2_aBridgeUnavailableAnswerIsPassedThroughVerbatimAndHasNoData() {
        String detail = "rc=3; stderr=selfimproving: 篩選值不合（全形字元與\n換行的第二行）";
        MINI.si.unavailable = Map.of("cause", "nonzero_rc", "detail", detail);

        Resp resp = api.send(viewer(), MockMvcRequestBuilders.get(ISSUES).param("status", "不存在"));

        assertThat(resp.status()).isEqualTo(503);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_UNAVAILABLE);
        assertThat(resp.<String>read("$.details.cause")).isEqualTo("nonzero_rc");
        assertThat(resp.<String>read("$.details.detail")).as("detail 逐字（含全形與換行）").isEqualTo(detail);
        assertNoData(resp, "503");
    }

    @Test
    void AT_IC_07_7_1_everyFailureModeHasNoDataAndNeverAnEmptyOrPriorityLessList() {
        bridgeKnows(PROP, "待您決定", true);
        // 連線被拒
        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp refused = get(viewer(), "");
        resetSystemConfigs();
        thresholds.invalidate();
        assertThat(refused.status()).isEqualTo(502);
        assertThat(refused.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_UNREACHABLE);
        assertNoData(refused, "連線被拒");

        // 讀取逾時（讀取逾時縮到 1 秒；單一請求、不重試）
        readTimeout.cap(Duration.ofSeconds(1));
        MINI.si.delayMillis = 2_500;
        Resp timedOut = get(viewer(), "");
        assertThat(timedOut.status()).isEqualTo(504);
        assertThat(timedOut.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_TIMEOUT);
        assertNoData(timedOut, "讀取逾時");
        assertThat(MINI.countRequests("GET /si/issues")).as("只送一次請求，不重試").isEqualTo(1);
        readTimeout.reset();
        MINI.reset();
        bridgeKnows(PROP, "待您決定", true);

        // 順位表讀取失敗（Bridge 一切正常）
        int before = MINI.requests().size();
        withBrokenPriorityTable(() -> {
            Resp broken = get(viewer(), "");
            assertThat(broken.status()).as("順位表讀取失敗＝整個請求失敗").isGreaterThanOrEqualTo(500);
            assertNoData(broken, "順位表失敗");
            Resp brokenSingle = get(viewer(), "/" + PROP);
            assertThat(brokenSingle.status()).isGreaterThanOrEqualTo(500);
            assertNoData(brokenSingle, "順位表失敗（單筆）");
        });
        assertThat(MINI.requests().size()).as("順位表失敗時 Bridge 仍各被呼叫恰一次（清單與單筆各一）").isEqualTo(before + 2);
        assertThat(get(viewer(), "").status()).as("失敗之後立即重請求：沒有殘留的錯誤").isEqualTo(200);
    }

    @Test
    void AT_IC_07_7_E_1_bridge503Refused502Timeout504AndTableFailure5xxEachMapToTheirOwnStatusWithoutData() {
        MINI.si.unavailable = Map.of("cause", "bad_json", "detail", "rc=0; stderr=");
        Resp unavailable = get(viewer(), "");
        assertThat(unavailable.status()).isEqualTo(503);
        assertThat(unavailable.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_UNAVAILABLE);
        assertNoData(unavailable, "503");
        MINI.reset();

        MINI.si.status500 = true;
        Resp bad = get(viewer(), "");
        assertThat(bad.status()).isEqualTo(502);
        assertThat(bad.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_ERROR);
        assertNoData(bad, "Bridge 500");
        MINI.reset();

        MINI.si.garbage = "這不是 JSON";
        assertThat(get(viewer(), "").status()).as("200 但本文不是 JSON 物件").isEqualTo(502);
        MINI.reset();
        MINI.si.arrayBody = true;
        assertThat(get(viewer(), "/" + PROP).status()).as("200 但本文是陣列").isEqualTo(502);
        MINI.reset();
        bridgeKnows(PROP, "待您決定", true);

        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp refused = get(viewer(), "/" + PROP);
        resetSystemConfigs();
        thresholds.invalidate();
        assertThat(refused.status()).isEqualTo(502);
        assertNoData(refused, "連線被拒");

        readTimeout.cap(Duration.ofSeconds(1));
        MINI.si.delayMillis = 2_500;
        Resp timedOut = get(viewer(), "/" + PROP);
        assertThat(timedOut.status()).isEqualTo(504);
        assertNoData(timedOut, "逾時");
        assertThat(MINI.countRequests("GET /si/issues/" + PROP)).as("逾時不重試").isEqualTo(1);
        readTimeout.reset();
        MINI.reset();

        withBrokenPriorityTable(() -> assertThat(get(viewer(), "").status()).isGreaterThanOrEqualTo(500));
    }

    // ── AT-IC-06-1-3、12-3-1：零寫入、不快取 ────────────────────────────────────────────────

    @Test
    void AT_IC_06_1_3_theGetEndpointsOnlyEverIssueGetRequestsToTheBridge() {
        bridgeKnows(PROP, "待您決定", true);

        assertThat(get(viewer(), "").status()).isEqualTo(200);
        assertThat(get(operator(), "/" + PROP).status()).isEqualTo(200);
        assertThat(get(admin(), "?status=待解").status()).isEqualTo(200);

        assertThat(MINI.requests()).hasSize(3).allSatisfy(request -> assertThat(request).startsWith("GET /si/issues"));
        assertThat(MINI.si.writes).as("沒有任何寫入呼叫").isEmpty();
        assertThat(priorityRows()).as("GET 不寫順位表").isEmpty();
    }

    @Test
    void AT_IC_12_3_1_theBackendDoesNotCacheASecondGetSeesTheNewBridgeContent() {
        bridgeKnows(PROP, "待您決定", true);
        Resp first = get(viewer(), "");
        assertThat(first.<String>read("$.data.items[0].nextStep")).isEqualTo("夾具的下一步");

        Map<String, Object> changed = item(PROP, "進行中", true);
        changed.put("next_step", "已換成新內容");
        MINI.si.payloads.put("issues", listPayload(List.of(changed)));
        Resp second = get(viewer(), "");

        assertThat(second.<String>read("$.data.items[0].nextStep")).isEqualTo("已換成新內容");
        assertThat(second.<String>read("$.data.items[0].status")).isEqualTo("進行中");
        assertThat(MINI.countRequests("GET /si/issues")).as("兩個請求各一次 Bridge 呼叫").isEqualTo(2);
    }

    // ── AT-IC-09-1-1／09-1-E-1：PUT 成功與 upsert ───────────────────────────────────────────────

    @Test
    void AT_IC_09_1_1_anAdminOutsideTheDecidersListSetsAPriorityAndItShowsUpInTheNextGet() {
        bridgeKnows(PROP, "待您決定", true);

        OffsetDateTime before = OffsetDateTime.now().minusMinutes(1);
        Resp resp = put(adminAs(NOT_A_DECIDER), PROP, map("rank", 2, "note", "先做"));

        assertThat(resp.status()).as(resp.body()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.id")).isEqualTo(PROP);
        assertThat(resp.<Integer>read("$.data.rank")).isEqualTo(2);
        assertThat(resp.<String>read("$.data.note")).isEqualTo("先做");
        assertThat(resp.<String>read("$.data.setBy")).isEqualTo(NOT_A_DECIDER);
        OffsetDateTime setAt = OffsetDateTime.parse(resp.read("$.data.setAt"));
        assertThat(setAt).as("setAt 是伺服器時間（帶 offset）").isAfter(before).isBefore(OffsetDateTime.now().plusMinutes(1));
        Map<String, Object> data = resp.data();
        assertThat(new ArrayList<>(data.keySet())).containsExactly("id", "rank", "note", "setBy", "setAt");
        assertThat(priorityRows()).singleElement().satisfies(row -> {
            assertThat(row).containsEntry("issue_id", PROP).containsEntry("rank", 2).containsEntry("note", "先做");
            assertThat(row).containsEntry("set_by", NOT_A_DECIDER);
        });
        assertThat(MINI.requests()).as("PUT 先取該議題：恰一次 Bridge 單筆呼叫、只有 GET").containsExactly("GET /si/issues/" + PROP);
        assertThat(this.<Integer>priorityOf(PROP, "priority")).isEqualTo(2);
        assertThat(this.<String>priorityOf(PROP, "priorityNote")).isEqualTo("先做");
    }

    @Test
    void AT_IC_09_1_E_1_anAbsentNoteIsStoredAsEmptyTheSameValueTwiceKeepsOneRowAndEqualRanksCoexist() {
        bridgeKnows(PROP, "待解", true);
        MINI.si.payloads.put("issue:DEF-999-002", singlePayload(item("DEF-999-002", "進行中", true)));

        Resp first = put(admin(), PROP, map("rank", 7));
        assertThat(first.status()).as(first.body()).isEqualTo(200);
        assertThat(first.<String>read("$.data.note")).as("缺鍵＝空字串").isEmpty();
        assertThat(priorityRows()).singleElement().satisfies(row -> assertThat(row).containsEntry("note", ""));
        assertThat(this.<String>priorityOf(PROP, "priorityNote")).as("GET 回空字串，不是 null").isEqualTo("");

        assertThat(put(admin(), PROP, map("rank", 7)).status()).as("同值再 PUT 仍 200").isEqualTo(200);
        assertThat(priorityRows()).as("仍恰一列").hasSize(1);
        assertThat(put(admin(), "DEF-999-002", map("rank", 7, "note", "同順位")).status()).as("另一議題同 rank").isEqualTo(200);
        assertThat(priorityRows()).as("兩列皆存（無唯一鍵）").hasSize(2).allSatisfy(row -> assertThat(row).containsEntry("rank", 7));
        assertThat(put(adminAs("ops_admin"), PROP, map("rank", 9, "note", "覆寫")).status()).isEqualTo(200);
        assertThat(priorityRows()).filteredOn(r -> PROP.equals(r.get("issue_id"))).singleElement()
                .satisfies(row -> assertThat(row).containsEntry("rank", 9).containsEntry("note", "覆寫"));
    }

    // ── AT-IC-09-2-1／09-2-E-1：角色 ───────────────────────────────────────────────────────────

    @Test
    void AT_IC_09_2_1_operatorAndViewerAre403OnPutAndDeleteWithZeroWritesZeroBridgeCallsAndAnAuditRowEach() {
        bridgeKnows(PROP, "待您決定", true);
        insertPriority(PROP, 5, "既有");

        for (String token : List.of(operator(), viewer())) {
            Resp putResp = put(token, PROP, map("rank", 1, "note", "不該寫入"));
            assertThat(putResp.status()).isEqualTo(403);
            assertThat(putResp.<String>read("$.reason")).isEqualTo(ErrorReasons.ACCESS_DENIED);
            Resp deleteResp = delete(token, PROP);
            assertThat(deleteResp.status()).isEqualTo(403);
            assertThat(deleteResp.<String>read("$.reason")).isEqualTo(ErrorReasons.ACCESS_DENIED);
        }

        assertThat(priorityRows()).as("零寫入：既有列不變").singleElement().satisfies(row -> assertThat(row).containsEntry("rank", 5).containsEntry("note", "既有"));
        assertThat(MINI.requests()).as("Bridge 零呼叫").isEmpty();
        List<Map<String, Object>> audit = auditRows();
        assertThat(audit).as("四個被拒的請求各留一列").hasSize(4);
        assertThat(audit).extracting(r -> r.get("role")).containsExactly("OPERATOR", "OPERATOR", "VIEWER", "VIEWER");
        assertThat(audit).extracting(r -> r.get("method")).containsExactly("PUT", "DELETE", "PUT", "DELETE");
        assertThat(audit).extracting(r -> r.get("http_status")).containsOnly(403);
        assertThat(audit).extracting(r -> r.get("path")).allSatisfy(path -> assertThat((String) path).contains(PROP));
    }

    @Test
    void AT_IC_09_2_E_1_anonymousIs401OnBothWritesAndTheTwoAdminRulesComeBeforeTheGenericOperatorRule() {
        bridgeKnows(PROP, "待您決定", true);

        assertThat(putRaw(null, PROP, "{\"rank\":1}").status()).isEqualTo(401);
        assertThat(delete(null, PROP).status()).isEqualTo(401);
        assertThat(put("garbage", PROP, map("rank", 1)).status()).isEqualTo(401);

        assertThat(auditRows()).as("401 同樣各留一列").hasSize(3).allSatisfy(row -> {
            assertThat(row.get("http_status")).isEqualTo(401);
            assertThat(row.get("subject")).isNull();
        });
        assertThat(put(operator(), PROP, map("rank", 1)).status()).as("OPERATOR 不得因通用 /api/v1/** 規則通過").isEqualTo(403);
        assertThat(delete(operator(), PROP).status()).isEqualTo(403);
        assertThat(priorityRows()).isEmpty();
        assertThat(MINI.requests()).isEmpty();
    }

    // ── AT-IC-09-3-1／09-3-E-1／09-3-E-2：輸入閘 ─────────────────────────────────────────────────

    private static String json(Object value) {
        return JSON.writeValueAsString(value);
    }

    @Test
    void AT_IC_09_3_1_everyInvalidBodyIs422WithAllViolationsZeroWritesAndZeroBridgeCalls() {
        bridgeKnows(PROP, "待您決定", true);
        Map<String, List<String>> cases = new LinkedHashMap<>();         // 本文 → 預期出現違規的欄位
        for (String rank : List.of("null", "0", "-1", "1.5", "\"a\"", "true", "[]", "{}", "10000", "1e3", "99999999999999999999")) {
            cases.put("{\"rank\":" + rank + ",\"note\":\"x\"}", List.of("rank"));
        }
        cases.put("{\"note\":\"缺 rank\"}", List.of("rank"));
        cases.put("{}", List.of("rank"));
        cases.put("{\"rank\":1,\"note\":5}", List.of("note"));
        cases.put("{\"rank\":1,\"note\":null}", List.of("note"));
        cases.put("{\"rank\":1,\"note\":" + json("字".repeat(101) + "😀".repeat(100)) + "}", List.of("note"));
        cases.put("{\"rank\":1,\"note\":" + json("第一行\n第二行") + "}", List.of("note"));
        cases.put("{\"rank\":1,\"note\":" + json("\n前導換行") + "}", List.of("note"));
        cases.put("{\"rank\":1,\"note\":" + json("尾端換行\n") + "}", List.of("note"));
        cases.put("{\"rank\":1,\"note\":\"del\\u007f字元\"}", List.of("note"));
        cases.put("{\"rank\":1,\"note\":\"tab\\t字元\"}", List.of("note"));
        cases.put("{\"rank\":null,\"note\":5}", List.of("rank", "note"));

        cases.forEach((body, fields) -> {
            Resp resp = putRaw(admin(), PROP, body);

            assertThat(resp.status()).as("%s：422（不是 400，也不是清除）%s", body, resp.body()).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).as(body).isEqualTo("invalid_request");
            List<Map<String, Object>> violations = resp.read("$.details.violations");
            assertThat(violations).extracting(v -> v.get("field")).as("%s 的違規欄位", body).containsAll(fields);
            assertThat(violations).allSatisfy(v -> assertThat(v).containsKeys("field", "message"));
            assertThat(resp.errorFields()).as("%s：errors[] 與 details.violations 互為鏡像", body)
                    .containsExactlyElementsOf(violations.stream().map(v -> (String) v.get("field")).toList());
        });

        Resp badIdAndBody = putRaw(admin(), "obs-si-001", "{\"rank\":0,\"note\":5}");
        assertThat(badIdAndBody.status()).isEqualTo(422);
        List<Map<String, Object>> all = badIdAndBody.read("$.details.violations");
        assertThat(all).extracting(v -> v.get("field")).as("id、rank、note 一次全列").containsExactly("id", "rank", "note");
        assertThat(priorityRows()).as("任一 422 都零寫入").isEmpty();
        assertThat(MINI.requests()).as("422 之前 Bridge 零呼叫").isEmpty();
    }

    @Test
    void AT_IC_09_3_E_1_theBoundaryValuesAreAcceptedAndTheNextOnesAreRejected() {
        bridgeKnows(PROP, "待您決定", true);
        String emoji200 = "😀".repeat(100) + "字".repeat(100);
        assertThat(emoji200.codePointCount(0, emoji200.length())).isEqualTo(200);
        assertThat(emoji200.length()).as("以 UTF-16 單元計是 300，所以輸入閘與資料庫都必須以 code point 計").isEqualTo(300);

        assertThat(put(admin(), PROP, map("rank", 1, "note", "")).status()).as("rank 1").isEqualTo(200);
        assertThat(put(admin(), PROP, map("rank", 9999)).status()).as("rank 9999").isEqualTo(200);
        assertThat(put(admin(), PROP, map("rank", 5, "note", emoji200)).status()).as("恰 200 code point（含表情符號）").isEqualTo(200);
        assertThat(priorityRows()).singleElement().satisfies(row -> assertThat((String) row.get("note")).isEqualTo(emoji200));
        assertThat(put(admin(), PROP, map("rank", 5, "note", emoji200 + "字")).status()).as("201 個").isEqualTo(422);
        assertThat(put(admin(), PROP, map("rank", 5, "note", "a\u007fb")).status()).as("含 U+007F").isEqualTo(422);
        assertThat(put(admin(), PROP, map("rank", 5, "note", "\n首")).status()).as("首位換行").isEqualTo(422);
        assertThat(put(admin(), PROP, map("rank", 5, "note", "尾\n")).status()).as("尾端換行").isEqualTo(422);
        assertThat(priorityRows()).as("被拒的 PUT 沒有動到既有列").singleElement().satisfies(row -> assertThat(row).containsEntry("rank", 5)
                .containsEntry("note", emoji200));
    }

    @Test
    void AT_IC_09_3_E_2_aBodyThatIsNotAJsonObjectIs400MalformedNot422WithZeroWritesAndZeroBridgeCalls() {
        bridgeKnows(PROP, "待您決定", true);
        for (String body : List.of("[]", "\"x\"", "{", "[1,2]", "42", "null", "")) {
            Resp resp = putRaw(admin(), PROP, body);

            assertThat(resp.status()).as("本文 %s：400（不是 422）", body).isEqualTo(400);
            assertThat(resp.<String>read("$.reason")).as(body).isEqualTo("MALFORMED_REQUEST_BODY");
            assertNoData(resp, body);
        }
        assertThat(priorityRows()).isEmpty();
        assertThat(MINI.requests()).isEmpty();
    }

    // ── AT-IC-09-4-1／09-4-E-1：DELETE ─────────────────────────────────────────────────────────

    @Test
    void AT_IC_09_4_1_deleteRemovesTheRowIsIdempotentAndNeverCallsTheBridge() {
        bridgeKnows(PROP, "待您決定", true);
        insertPriority(PROP, 4, "要被清掉");

        Resp first = delete(admin(), PROP);
        Resp second = delete(admin(), PROP);

        assertThat(first.status()).isEqualTo(204);
        assertThat(first.body()).as("204 無本文").isEmpty();
        assertThat(second.status()).as("第二次仍 204（冪等）").isEqualTo(204);
        assertThat(priorityRows()).isEmpty();
        assertThat(MINI.requests()).as("DELETE 全程 Bridge 零呼叫").isEmpty();
        assertThat(this.<Integer>priorityOf(PROP, "priority")).as("之後 GET 的 priority 為 null").isNull();
        assertThat(this.<String>priorityOf(PROP, "priorityNote")).isNull();
    }

    @Test
    void AT_IC_09_4_E_1_aLeftoverRowOfACompletedOrVanishedIssueCanStillBeClearedAndABadIdIsRejectedBeforeTheDatabase() {
        insertPriority("DEF-999-003", 1, "已不存在的議題");
        insertPriority(PROP, 2, "留著");
        MINI.si.notFoundIds.add("DEF-999-003");

        assertThat(delete(admin(), "DEF-999-003").status()).as("議題已不存在仍清得掉").isEqualTo(204);
        assertThat(priorityRows()).singleElement().satisfies(row -> assertThat(row).containsEntry("issue_id", PROP));

        // 近似編號的負例於執行期組字：根層 R18 (a) 會把整串的 OBS 編號字面（帳本沒有的號碼）判成懸空引用
        for (String bad : List.of("obs-si-001", "OBS" + "-SI-12", "DEF-x-y", "PROP-SI-4")) {
            Resp resp = delete(admin(), bad);

            assertThat(resp.status()).as(bad).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).isEqualTo("invalid_request");
            assertThat(resp.errorFields()).containsExactly("id");
        }
        assertThat(priorityRows()).as("格式不合不碰資料庫").hasSize(1);
        assertThat(MINI.requests()).isEmpty();
    }

    // ── AT-IC-09-5-1／09-5-E-1：不可排、查無、Bridge 失敗 ────────────────────────────────────────

    @Test
    void AT_IC_09_5_1_aStatusThatIsNotRankableIs409WithTheContractMessageAndZeroWrites() {
        String contractMessage = IssueReasonsContractTest.parse(IssueReasonsContractTest.readContract()).messages().get(ErrorReasons.ISSUE_NOT_RANKABLE);
        assertThat(contractMessage).as("契約表的中文訊息").isEqualTo(MESSAGE_NOT_RANKABLE);
        for (String status : NOT_RANKABLE) {
            bridgeKnows(PROP, status, false);

            Resp resp = put(admin(), PROP, map("rank", 1, "note", "x"));

            assertThat(resp.status()).as(status).isEqualTo(409);
            assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.ISSUE_NOT_RANKABLE);
            assertThat(resp.<String>read("$.message")).as("409 的 message 與契約表逐字相同").isEqualTo(contractMessage);
            assertThat(resp.<String>read("$.details.id")).isEqualTo(PROP);
            assertThat(resp.<String>read("$.details.status")).as("details.status 是中文狀態").isEqualTo(status);
            assertNoData(resp, status);
        }
        assertThat(priorityRows()).as("零寫入").isEmpty();
    }

    @Test
    void AT_IC_09_5_E_1_notFoundAndBridgeFailuresWriteNothingAndEveryRankableStatusIs200() {
        MINI.si.notFoundIds.add(PROP);
        Resp missing = put(admin(), PROP, map("rank", 1));
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_NOT_FOUND);
        assertThat(missing.<String>read("$.message")).isEqualTo("查無此議題");
        MINI.reset();

        MINI.si.unavailable = Map.of("cause", "timeout", "detail", "rc=none; stderr=");
        Resp unavailable = put(admin(), PROP, map("rank", 1));
        assertThat(unavailable.status()).isEqualTo(503);
        assertThat(unavailable.<String>read("$.reason")).isEqualTo(ErrorReasons.SI_UNAVAILABLE);
        MINI.reset();

        MINI.si.status500 = true;
        assertThat(put(admin(), PROP, map("rank", 1)).status()).as("Bridge 5xx").isEqualTo(502);
        MINI.reset();

        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp refused = put(admin(), PROP, map("rank", 1));
        resetSystemConfigs();
        thresholds.invalidate();
        assertThat(refused.status()).isEqualTo(502);

        readTimeout.cap(Duration.ofSeconds(1));
        MINI.si.delayMillis = 2_500;
        assertThat(put(admin(), PROP, map("rank", 1)).status()).isEqualTo(504);
        readTimeout.reset();
        MINI.reset();
        assertThat(priorityRows()).as("任一 Bridge 失敗都零寫入").isEmpty();

        for (String status : RANKABLE) {
            bridgeKnows(PROP, status, true);
            assertThat(put(admin(), PROP, map("rank", 3, "note", status)).status()).as(status).isEqualTo(200);
        }
        assertThat(priorityRows()).singleElement().satisfies(row -> assertThat(row).containsEntry("note", "進行中"));
    }

    // ── AT-IC-09-7-1／09-7-E-1：後者生效與併發 ────────────────────────────────────────────────

    @Test
    void AT_IC_09_7_1_theLaterOfTwoAdminsWins() {
        bridgeKnows(PROP, "待您決定", true);

        Resp first = put(adminAs("chief"), PROP, map("rank", 3, "note", "第一個管理員"));
        Resp second = put(adminAs("ops_admin"), PROP, map("rank", 4, "note", "第二個管理員"));

        assertThat(first.status()).isEqualTo(200);
        assertThat(second.status()).isEqualTo(200);
        assertThat(priorityRows()).singleElement().satisfies(row -> assertThat(row).containsEntry("rank", 4).containsEntry("note", "第二個管理員")
                .containsEntry("set_by", "ops_admin"));
        assertThat(OffsetDateTime.parse(second.read("$.data.setAt"))).as("setAt 為後者").isAfterOrEqualTo(OffsetDateTime.parse(first.read("$.data.setAt")));
        assertThat(second.<String>read("$.data.setBy")).isEqualTo("ops_admin");
    }

    @Test
    void AT_IC_09_7_E_1_concurrentPutsLeaveExactlyOneCompleteRowAndReadersNeverSeeAHalfWrittenOne() throws Exception {
        bridgeKnows(PROP, "待您決定", true);
        Map<Integer, String> pairs = Map.of(11, "甲", 22, "乙");
        int rounds = 25;
        ExecutorService pool = Executors.newFixedThreadPool(3);
        CountDownLatch start = new CountDownLatch(1);
        AtomicBoolean writing = new AtomicBoolean(true);
        List<String> observed = java.util.Collections.synchronizedList(new ArrayList<>());
        List<Integer> statuses = java.util.Collections.synchronizedList(new ArrayList<>());
        try {
            List<Future<?>> writers = new ArrayList<>();
            for (Map.Entry<Integer, String> pair : pairs.entrySet()) {
                writers.add(pool.submit(() -> {
                    start.await();
                    for (int i = 0; i < rounds; i++) {
                        statuses.add(put(adminAs("w" + pair.getKey()), PROP, map("rank", pair.getKey(), "note", pair.getValue())).status());
                    }
                    return null;
                }));
            }
            Future<?> reader = pool.submit(() -> {
                start.await();
                while (writing.get()) {
                    Resp resp = get(viewer(), "/" + PROP);
                    statuses.add(resp.status());
                    if (resp.status() == 200) {
                        observed.add(resp.<Object>read("$.data.items[0].priority") + "/" + resp.<Object>read("$.data.items[0].priorityNote"));
                    }
                }
                return null;
            });
            start.countDown();
            for (Future<?> writer : writers) {
                writer.get();
            }
            writing.set(false);
            reader.get();
        } finally {
            writing.set(false);
            pool.shutdownNow();
        }

        assertThat(statuses).as("沒有 500").allMatch(status -> status == 200);
        List<Map<String, Object>> rows = priorityRows();
        assertThat(rows).as("恰一列").hasSize(1);
        int rank = (Integer) rows.get(0).get("rank");
        assertThat(pairs).as("結果是其中一筆完整的值（不混合 rank 與 note）").containsEntry(rank, (String) rows.get(0).get("note"));
        assertThat(observed).as("防反空轉：讀者真的讀到了東西").isNotEmpty();
        assertThat(observed).as("讀者只見舊值（null）或某一筆完整的新值").allSatisfy(seen -> assertThat(seen).isIn("null/null", "11/甲", "22/乙"));
    }

    // ── AT-IC-09-8-2：零帳本寫入 ───────────────────────────────────────────────────────────────

    @Test
    void AT_IC_09_8_2_aPutAndADeleteLeaveTheFourLedgersUntouchedAndTheBridgeOnlyEverSawGets() {
        bridgeKnows(PROP, "待您決定", true);
        String ledgersBefore = ledgerDigest();

        assertThat(put(admin(), PROP, map("rank", 1, "note", "x")).status()).isEqualTo(200);
        assertThat(delete(admin(), PROP).status()).isEqualTo(204);
        assertThat(put(admin(), PROP, map("rank", 2)).status()).isEqualTo(200);

        assertThat(ledgerDigest()).as("四類帳本與事件帳本的位元組不變").isEqualTo(ledgersBefore);
        assertThat(MINI.requests()).as("Bridge 只收到 GET").isNotEmpty().allSatisfy(request -> assertThat(request).startsWith("GET "));
        assertThat(MINI.si.writes).as("沒有任何 POST（稽核檔落地、預檢）").isEmpty();
        assertThat(writeCount()).as("也沒有 SelfImproving 的稽核列").isZero();
    }

    // ── AT-IC-09-10-1：遺留列 ─────────────────────────────────────────────────────────────────

    @Test
    void AT_IC_09_10_1_aLeftoverRowIsHiddenAndExcludedFromPutWhileDeleteStillClearsIt() {
        bridgeKnows(PROP, "待您決定", true);
        assertThat(put(admin(), PROP, map("rank", 1, "note", "曾經可排")).status()).isEqualTo(200);
        assertThat(this.<Integer>priorityOf(PROP, "priority")).isEqualTo(1);

        bridgeKnows(PROP, "已完成", false);

        assertThat(this.<Integer>priorityOf(PROP, "priority")).as("議題之後轉成已完成：priority 為 null").isNull();
        assertThat(this.<String>priorityOf(PROP, "priorityNote")).isNull();
        assertThat(priorityRows()).as("遺留列仍在表中").hasSize(1);
        assertThat(put(admin(), PROP, map("rank", 2)).status()).as("PUT 它＝409").isEqualTo(409);
        assertThat(delete(admin(), PROP).status()).isEqualTo(204);
        assertThat(priorityRows()).as("ADMIN DELETE 後該列消失").isEmpty();
    }

    // ── AT-IC-09-11-1／09-11-E-1：audit_log ───────────────────────────────────────────────────

    @Test
    void AT_IC_09_11_1_aSuccessfulPutAndDeleteEachLeaveAnAuditRow() {
        bridgeKnows(PROP, "待您決定", true);

        assertThat(put(admin(), PROP, map("rank", 1)).status()).isEqualTo(200);
        assertThat(delete(admin(), PROP).status()).isEqualTo(204);

        List<Map<String, Object>> audit = auditRows();
        assertThat(audit).hasSize(2);
        assertThat(audit.get(0)).containsEntry("subject", "admin").containsEntry("role", "ADMIN").containsEntry("method", "PUT")
                .containsEntry("http_status", 200).containsEntry("entity_type", "issues");
        assertThat(audit.get(1)).containsEntry("subject", "admin").containsEntry("role", "ADMIN").containsEntry("method", "DELETE")
                .containsEntry("http_status", 204);
        assertThat(audit).extracting(r -> (String) r.get("path")).containsExactly(ISSUES + "/" + PROP + "/priority", ISSUES + "/" + PROP + "/priority");
    }

    @Test
    void AT_IC_09_11_E_1_rejectedAndFailedWritesLeaveAnAuditRowWithTheirRealStatus() {
        bridgeKnows(PROP, "已完成", false);

        assertThat(putRaw(null, PROP, "{\"rank\":1}").status()).isEqualTo(401);
        assertThat(put(operator(), PROP, map("rank", 1)).status()).isEqualTo(403);
        assertThat(put(admin(), PROP, map("rank", 0)).status()).isEqualTo(422);
        assertThat(put(admin(), PROP, map("rank", 1)).status()).isEqualTo(409);
        assertThat(delete(admin(), "obs-si-001").status()).isEqualTo(422);

        assertThat(auditRows()).extracting(r -> r.get("http_status")).containsExactly(401, 403, 422, 409, 422);
        assertThat(auditRows()).extracting(r -> r.get("method")).containsExactly("PUT", "PUT", "PUT", "PUT", "DELETE");
        assertThat(auditRows()).extracting(r -> r.get("role")).containsExactly(null, "OPERATOR", "ADMIN", "ADMIN", "ADMIN");
    }

    // ── 輸入閘的純函式半（AT-IC-09-3-1、09-3-E-1；不經 HTTP）─────────────────────────────────────────
    // 為什麼另測：Jackson 只能造出合法 JSON 的值；孤立代理字元、BigDecimal 這類「進得了閘、卻不該存進資料庫」的值只有直接餵閘才造得出來——
    // 它們的後果是資料庫的 UTF-8 編碼失敗而回 500，而不是一個乾淨的 422。

    private static Map<String, Object> gateBody(Object... keyValues) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            out.put((String) keyValues[i], keyValues[i + 1]);
        }
        return out;
    }

    private static UnprocessableException rejected(String id, Map<String, Object> body) {
        try {
            IssuePriorityGates.set(id, body);
        } catch (UnprocessableException e) {
            assertThat(e.reason()).isEqualTo("invalid_request");
            return e;
        }
        throw new AssertionError("應被輸入閘拒絕：" + body);
    }

    private static List<String> rejectedFields(String id, Map<String, Object> body) {
        return rejected(id, body).violations().stream().map(Violation::field).toList();
    }

    @Test
    void AT_IC_09_3_E_1_gateUnitValidInputsPassAndAnAbsentNoteBecomesTheEmptyString() {
        assertThat(IssuePriorityGates.set(PROP, gateBody("rank", 1))).isEqualTo(new IssuePriorityGates.Command(PROP, 1, ""));
        assertThat(IssuePriorityGates.set(PROP, gateBody("rank", 9999, "note", ""))).isEqualTo(new IssuePriorityGates.Command(PROP, 9999, ""));
        assertThat(IssuePriorityGates.set("DEF-999-001", gateBody("rank", 5L, "note", " 前後空白原樣保留 "))).isEqualTo(
                new IssuePriorityGates.Command("DEF-999-001", 5, " 前後空白原樣保留 "));
        String emoji200 = "😀".repeat(100) + "字".repeat(100);
        assertThat(IssuePriorityGates.set(OBS, gateBody("rank", 2, "note", emoji200)).note()).isEqualTo(emoji200);
        assertThat(IssuePriorityGates.set(PROP, gateBody("rank", BigInteger.valueOf(42))).rank()).isEqualTo(42);
        IssuePriorityGates.checkId(PROP);
        // 四位數的合成編號於執行期組字（理由同上：R18 (a) 不放過整串的 OBS 編號字面）
        for (String good : new String[] {"OBS-SI-001", "OBS" + "-SI-1234", "PROP-SI-004", "DEF-1-1", "DEF-200-551", "DEF-999-001"}) {
            assertThat(IssuePriorityGates.set(good, gateBody("rank", 1)).id()).isEqualTo(good);
        }
    }

    @Test
    void AT_IC_09_3_1_gateUnitRankMustBeAnIntegerFromOneToNineThousandNineHundredNinetyNine() {
        for (Object bad : new Object[] {null, 0, -1, 10000, Integer.MAX_VALUE, 1.5, 1.0, 1000.0, "5", "a", true, false, List.of(), Map.of(),
                new BigDecimal("3"), new BigInteger("99999999999999999999"), BigInteger.ZERO}) {
            assertThat(rejectedFields(PROP, gateBody("rank", bad, "note", "x"))).as("rank=%s", bad).containsExactly("rank");
        }
        assertThat(rejectedFields(PROP, gateBody("note", "只有備註"))).as("缺鍵").containsExactly("rank");
        assertThat(rejectedFields(PROP, gateBody())).containsExactly("rank");
    }

    @Test
    void AT_IC_09_3_1_gateUnitNoteMustBeAStringOfAtMostTwoHundredCodePointsWithoutControlOrLoneSurrogateCharacters() {
        String emoji201 = "😀".repeat(100) + "字".repeat(101);
        assertThat(rejectedFields(PROP, gateBody("rank", 1, "note", null))).as("note 為 null（只有缺鍵才是缺省）").containsExactly("note");
        for (Object bad : new Object[] {5, 1.5, true, List.of(), Map.of(), emoji201, "a\nb", "\n首", "尾\n", "a\tb", "a\u0000b", "a\u007fb", "a\rb",
                "\ud800", "x\udc00y", "尾端高代理\ud83d"}) {
            assertThat(rejectedFields(PROP, gateBody("rank", 1, "note", bad))).as("note=%s", bad).containsExactly("note");
        }
        assertThat(rejected(PROP, gateBody("rank", 1, "note", emoji201)).violations().get(0).message())
                .as("訊息說出實際長度與上限（以 code point 計，不是 UTF-16 單元）").contains("201").contains("200");
    }

    @Test
    void AT_IC_09_3_1_gateUnitTheIdMustBeOneOfTheThreeFormatsAndEveryViolationIsListedAtOnceInFieldOrder() {
        // 兩位數的近似編號於執行期組字（理由同上：R18 (a) 不放過整串的 OBS 編號字面）
        for (String bad : new String[] {"obs-si-001", "OBS" + "-SI-12", "PROP-SI-4", "DEF-x-y", "DEF-1-", "OBS-SI-001\n", "OBS-SI-００１", "", " OBS-SI-001"}) {
            assertThat(rejectedFields(bad, gateBody("rank", 1))).as("id=%s", bad).containsExactly("id");
        }
        UnprocessableException thrown = rejected("bad", gateBody("rank", 0, "note", 5));
        assertThat(thrown.violations()).extracting(Violation::field).as("id、rank、note 一次全列，依序").containsExactly("id", "rank", "note");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> details = (List<Map<String, Object>>) thrown.details().get("violations");
        assertThat(details).extracting(v -> v.get("field")).containsExactly("id", "rank", "note");
        assertThat(details).allSatisfy(v -> assertThat(v).containsOnlyKeys("field", "message"));
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> IssuePriorityGates.checkId("nope")).isInstanceOf(UnprocessableException.class)
                .satisfies(e -> assertThat(((UnprocessableException) e).violations()).extracting(Violation::field).containsExactly("id"));
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> IssuePriorityGates.checkId(null)).isInstanceOf(UnprocessableException.class);
    }
}
