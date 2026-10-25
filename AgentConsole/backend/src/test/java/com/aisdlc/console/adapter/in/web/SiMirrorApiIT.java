package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SelfImproving 唯讀鏡像的 backend 面（{@code GET /api/v1/si/**}；TCS-SelfImprovingMirror-P1b：AT-932-1-3、AT-932-1-E-3／E-4、
 * AT-932-2-4、AT-932-3-5、AT-932-4-1、AT-932-4-E-1、AT-940-5-2；P2b 起 AT-940-8-1 由 {@code OpenApiIT} 的 AT-950-10-1 取代），對<b>真的 HTTP</b> 迷你 Bridge
 * （{@code MINI.si}）驗映射的每一列。
 * 為什麼重要：差分（AC-SI-32-1）的 backend 這一棒只准做一件事——把 Bridge 的 export 物件換個欄名風格原樣轉出。若這裡替 Bridge「補一句話」
 * （缺鍵補 null、空陣列當錯誤、快取舊資料、用自己的時鐘填 generatedAt）或「吞一句話」（503 的原因被改寫成 502），畫面上的
 * 「量不到」與「資料面壞了」就會說謊；而權限（401／403／405）與 id 編碼（單一路徑段）是安全面的底線。
 */
class SiMirrorApiIT extends AbstractExecutionIT {

    private static final String SI = "/api/v1/si";
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final String ONE = "/proposals/PROP-SI-004";
    private static final List<String> SIX = List.of("/status", "/observations", "/events", "/proposals", ONE, "/runs");
    /** 路徑 → camelCase 黃金檔裡的鍵（黃金檔的頂層鍵本身也經對映：proposal_one → proposalOne）。 */
    private static final Map<String, String> GOLDEN_KEY = Map.of("/status", "status", "/observations", "observations",
            "/events", "events", "/proposals", "proposals", ONE, "proposalOne", "/runs", "runs");

    // ── 小幫手 ────────────────────────────────────────────────────────────────────────

    private static String resource(String name) {
        try (InputStream in = SiMirrorApiIT.class.getResourceAsStream("/si/" + name + ".json")) {
            assertThat(in).as("測試資源 si/%s.json", name).isNotNull();
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    private static JsonNode goldenCamel(String state) {
        return JSON.readTree(resource(state + ".camel"));
    }

    private static JsonNode data(Resp resp) {
        return JSON.readTree(resp.body()).get("data");
    }

    private Resp get(String token, String path) {
        return api.get(token, SI + path);
    }

    private static Map<String, Object> map(Object... keyValues) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            out.put((String) keyValues[i], keyValues[i + 1]);
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> items(Map<String, Object> payload) {
        return (List<Map<String, Object>>) payload.get("items");
    }

    private Resp send(String token, MockHttpServletRequestBuilder builder) {
        return api.send(token, builder);
    }

    // ── AT-932-1-3：六個端點的 data 逐值等於 camelCase 黃金檔 ──────────────────────────────────

    @Test
    void AT_932_1_3_everyEndpointEqualsTheCamelCaseGoldenFileAndNothingIsRecomputed() {
        JsonNode golden = goldenCamel("A");
        Map<String, Map<String, Object>> snake = MiniBridge.Si.golden("A.snake");
        for (String path : SIX) {
            Resp resp = get(viewer(), path);

            assertThat(resp.status()).as(path).isEqualTo(200);
            JsonNode actual = data(resp);
            assertThat(actual).as("%s：data 逐值等於黃金檔（鍵集合、值、null 皆同；鍵序不比）", path).isEqualTo(golden.get(GOLDEN_KEY.get(path)));
            String snakeKey = path.equals(ONE) ? "proposal_one" : path.substring(1);
            assertThat(actual.get("generatedAt").asString()).as("%s：generatedAt 是 Bridge 的值、沒有被 backend 改寫", path)
                    .isEqualTo(snake.get(snakeKey).get("generated_at"));
            assertThat(actual.get("items").size()).as("%s：items 個數", path).isEqualTo(items(snake.get(snakeKey)).size());
        }
        Resp proposals = get(viewer(), "/proposals");
        assertThat(proposals.<String>read("$.data.items[0].card")).as("卡面逐位元組相同（含換行、全形字元、結尾換行）")
                .isEqualTo(items(snake.get("proposals")).get(0).get("card"));
        assertThat(proposals.has("$.data.items[0].headSha")).isFalse();
        List<String> expected = new ArrayList<>(SIX.stream().map(p -> "GET /si" + p).toList());
        expected.add("GET /si/proposals");                                   // 上面為了讀卡面又打了一次 /proposals
        assertThat(MINI.requests()).as("每個 backend 請求恰一次 Bridge 呼叫").containsExactlyElementsOf(expected);
    }

    @Test
    void AT_932_1_3_badQueryParametersAre400WithoutTouchingTheBridgeAndUnknownOnesAreNotForwarded() {
        for (String query : List.of("?since=abc", "?limit=0", "?since=-1", "?limit=-5")) {
            Resp resp = get(viewer(), "/observations" + query);

            assertThat(resp.status()).as(query).isEqualTo(400);
            assertThat(resp.has("$.data")).as("%s：失敗沒有 data", query).isFalse();
        }
        assertThat(MINI.requests()).as("400 不觸及 Bridge").isEmpty();

        Resp resp = get(viewer(), "/observations?foo=1&since=2");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(MINI.si.seen).hasSize(1);
        assertThat(MINI.si.seen.get(0).query()).as("未知參數不轉發：Bridge 收到的查詢字串恰為 since=2").isEqualTo("since=2");
        assertThat(MINI.si.seen.get(0).uri()).isEqualTo("/si/observations");
        MINI.si.seen.clear();
        assertThat(get(viewer(), "/events?limit=7&since=3").status()).isEqualTo(200);
        assertThat(MINI.si.seen.get(0).query()).as("轉發時依固定次序 since、limit").isEqualTo("since=3&limit=7");
        MINI.si.seen.clear();
        assertThat(get(viewer(), "/status?since=1&limit=5").status()).isEqualTo(200);
        assertThat(MINI.si.seen.get(0).query()).as("/status 不收任何查詢參數：不轉發").isNull();
    }

    // ── AT-932-1-E-3：未知鍵與怪值原樣透傳，空表不是錯誤 ─────────────────────────────────────────

    @Test
    void AT_932_1_E_3_unknownKeysAndWeirdValuesPassThroughAndAnEmptyListIsNotAnError() {
        Map<String, Object> payload = MiniBridge.Si.golden("A.snake").get("observations");
        List<Map<String, Object>> rows = items(payload);
        List<String> idsBefore = rows.stream().map(r -> (String) r.get("id")).toList();
        rows.get(0).put("buckets", List.of("AutoClaude", "未分類"));
        rows.get(0).put("x_meta", map("inner_key", 1, "nothing", null));
        rows.get(1).put("severity", "P9");
        rows.get(1).put("category", "weird-category");
        payload.put("console_pending", List.of());
        MINI.si.payloads.put("observations", payload);

        Resp resp = get(viewer(), "/observations");

        assertThat(resp.status()).isEqualTo(200);
        JsonNode d = data(resp);
        assertThat(d.get("items").get(0).get("buckets")).isEqualTo(JSON.valueToTree(List.of("AutoClaude", "未分類")));
        JsonNode xMeta = d.get("items").get(0).get("xMeta");
        assertThat(xMeta.has("innerKey")).as("巢狀物件的底線鍵也轉 camelCase").isTrue();
        assertThat(xMeta.has("nothing") && xMeta.get("nothing").isNull()).as("xMeta 內的 null 仍為 null（不被丟棄）").isTrue();
        assertThat(d.get("consolePending").isArray() && d.get("consolePending").size() == 0).isTrue();
        assertThat(d.get("items").get(1).get("severity").asString()).as("backend 不驗枚舉、不補值、不改值").isEqualTo("P9");
        assertThat(d.get("items").get(1).get("category").asString()).isEqualTo("weird-category");
        List<String> idsAfter = new ArrayList<>();
        d.get("items").forEach(row -> idsAfter.add(row.has("id") ? row.get("id").asString() : "(壞列)"));
        assertThat(idsAfter).as("items 的個數與順序不變").hasSameSizeAs(idsBefore);
        assertThat(idsAfter.subList(0, 11)).containsExactlyElementsOf(idsBefore.subList(0, 11));

        Map<String, Object> empty = MiniBridge.Si.golden("A.snake").get("observations");
        empty.put("items", List.of());
        empty.put("ne", List.of(map("field", "events", "reason", "carrier-not-established"),
                map("field", "head_sha", "reason", "git-unavailable")));
        MINI.si.payloads.put("observations", empty);

        Resp emptyResp = get(viewer(), "/observations");

        assertThat(emptyResp.status()).as("空 items 與非空 ne 是合法輸出，不是錯誤").isEqualTo(200);
        assertThat(data(emptyResp).get("items")).isEqualTo(JSON.valueToTree(List.of()));
        assertThat(data(emptyResp).get("ne")).isEqualTo(JSON.valueToTree(empty.get("ne")));
    }

    // ── AT-932-1-E-4：不快取、generatedAt 是 Bridge 的值 ─────────────────────────────────────────

    @Test
    void AT_932_1_E_4_noCachingAndGeneratedAtIsTheBridgesValueNotTheBackendsClock() {
        Resp first = get(viewer(), "/observations");
        Map<String, Object> b = MiniBridge.Si.golden("B.snake").get("observations");
        b.put("generated_at", "2026-10-21T00:10:00+08:00");
        MINI.si.payloads.put("observations", b);

        Resp second = get(viewer(), "/observations");

        ObjectNode wantA = (ObjectNode) goldenCamel("A").get("observations");
        ObjectNode wantB = (ObjectNode) goldenCamel("B").get("observations");
        String generatedA = wantA.get("generatedAt").asString();
        for (Resp resp : List.of(first, second)) {
            assertThat(resp.status()).isEqualTo(200);
        }
        ObjectNode gotA = (ObjectNode) data(first);
        ObjectNode gotB = (ObjectNode) data(second);
        assertThat(gotA.get("generatedAt").asString()).isEqualTo(generatedA);
        assertThat(gotB.get("generatedAt").asString()).as("兩次的 generatedAt 各等於當次 Bridge 的值").isEqualTo("2026-10-21T00:10:00+08:00")
                .isNotEqualTo(generatedA);
        gotA.remove("generatedAt");
        gotB.remove("generatedAt");
        wantA.remove("generatedAt");
        wantB.remove("generatedAt");
        assertThat(gotA).as("第一次回應＝狀態 A").isEqualTo(wantA);
        assertThat(gotB).as("第二次回應＝狀態 B（沒有被快取成 A）").isEqualTo(wantB);
        assertThat(wantB.get("items").size()).isEqualTo(wantA.get("items").size() + 1);
        for (Resp resp : List.of(first, second)) {
            OffsetDateTime timestamp = OffsetDateTime.parse(resp.read("$.timestamp"));
            assertThat(Duration.between(timestamp, OffsetDateTime.now()).abs()).as("封包的 timestamp 是 backend 自己的時間")
                    .isLessThan(Duration.ofMinutes(5));
            assertThat(resp.<String>read("$.timestamp")).isNotEqualTo(resp.<String>read("$.data.generatedAt"));
        }
        assertThat(MINI.countRequests("GET /si/observations")).as("每個請求一次 Bridge 呼叫、沒有快取").isEqualTo(2);
        String t1 = first.header("X-Trace-Id");
        String t2 = second.header("X-Trace-Id");
        assertThat(t1).isNotBlank().isNotEqualTo(t2);
        assertThat(MINI.traced().stream().filter(t -> t.request().equals("GET /si/observations")).toList())
                .extracting(MiniBridge.Traced::traceId).containsExactly(t1, t2);
    }

    // ── AT-932-2-4：角色乘方法矩陣 ───────────────────────────────────────────────────────────

    private static MockHttpServletRequestBuilder withBody(MockHttpServletRequestBuilder builder) {
        return builder.contentType(MediaType.APPLICATION_JSON).content("{}");
    }

    /** PUT、PATCH、DELETE：SelfImproving 沒有任何這三種方法的對映（P2b 起 POST 另有四個寫入端點，不在這個矩陣）。 */
    private static List<MockHttpServletRequestBuilder> writes(String url) {
        return List.of(withBody(MockMvcRequestBuilders.put(url)), withBody(MockMvcRequestBuilders.patch(url)),
                MockMvcRequestBuilders.delete(url));
    }

    @Test
    void AT_932_2_4_viewerIs403OperatorAndAdminAre405AndAnonymousIs401WithoutTouchingTheBridge() {
        Map<String, Integer> expected = new LinkedHashMap<>();
        expected.put("viewer", 403);
        expected.put("operator", 405);
        expected.put("admin", 405);
        Map<String, String> tokens = Map.of("viewer", viewer(), "operator", operator(), "admin", admin());
        int checked = 0;
        for (Map.Entry<String, Integer> role : expected.entrySet()) {
            for (String path : SIX) {
                for (MockHttpServletRequestBuilder request : writes(SI + path)) {
                    Resp resp = send(tokens.get(role.getKey()), request);
                    assertThat(resp.status()).as("%s %s", role.getKey(), path).isEqualTo(role.getValue());
                    checked++;
                }
            }
        }
        assertThat(checked).as("PUT、PATCH、DELETE 乘六路徑乘三種角色").isEqualTo(54);
        for (String path : SIX) {
            assertThat(send(null, withBody(MockMvcRequestBuilders.put(SI + path))).status()).as("無 token PUT %s", path)
                    .isEqualTo(401);
        }
        for (String token : List.of(viewer(), operator(), admin())) {
            assertThat(api.get(token, SI + "/nothing").status()).as("未定義的路徑").isEqualTo(404);
        }
        assertThat(MINI.requests()).as("沒有任何請求觸及 Bridge").isEmpty();
        for (String path : SIX) {
            assertThat(get(admin(), path).status()).as("對照組：%s 本身可用", path).isEqualTo(200);
        }
    }

    /**
     * P2b（TCS-SelfImprovingDecide-P2b §4 第 9 項）：{@code SecurityConfig} 對 {@code POST /api/v1/si/**} 要求 ADMIN，所以 POST 自上面的矩陣移出。
     * 五個沒有 POST 映射的讀路徑（{@code /observations} 同時是寫入路徑，不在這裡）：無 token 401、Viewer 與 Operator 403（被安全層擋下）、Admin 405（沒有對映）。
     */
    @Test
    void AT_932_2_4_postOnTheFiveReadOnlyPathsIs401ForAnonymous403ForViewerAndOperatorAnd405ForAdmin() {
        List<String> readOnly = SIX.stream().filter(p -> !p.equals("/observations")).toList();
        assertThat(readOnly).hasSize(5);
        for (String path : readOnly) {
            assertThat(send(null, withBody(MockMvcRequestBuilders.post(SI + path))).status()).as("無 token %s", path).isEqualTo(401);
            assertThat(send(viewer(), withBody(MockMvcRequestBuilders.post(SI + path))).status()).as("Viewer %s", path).isEqualTo(403);
            assertThat(send(operator(), withBody(MockMvcRequestBuilders.post(SI + path))).status()).as("Operator %s", path).isEqualTo(403);
            assertThat(send(admin(), withBody(MockMvcRequestBuilders.post(SI + path))).status()).as("Admin %s", path).isEqualTo(405);
        }
        assertThat(MINI.requests()).as("全程不觸 Bridge").isEmpty();
    }

    // ── AT-932-3-5：Bridge 失敗逐列對映，原因逐字，失敗沒有 data ─────────────────────────────────

    private void assertNoData(Resp resp, String label) {
        assertThat(resp.has("$.data")).as("%s：失敗回應沒有 data（不回空表、不回部分資料）", label).isFalse();
    }

    @Test
    void AT_932_3_5_eachBridgeFailureMapsToItsRowOfTheTableWithTheReasonVerbatim() {
        String detail = "rc=3; stderr=錯誤：全形字元與\n換行的第二行";
        MINI.si.unavailable = Map.of("cause", "nonzero_rc", "detail", detail);
        Resp unavailable = get(viewer(), "/status");
        assertThat(unavailable.status()).isEqualTo(503);
        assertThat(unavailable.<String>read("$.reason")).isEqualTo("si_unavailable");
        assertThat(unavailable.<String>read("$.details.detail")).as("detail 逐字（含全形與換行）").isEqualTo(detail);
        assertThat(unavailable.<String>read("$.details.cause")).isEqualTo("nonzero_rc");
        assertNoData(unavailable, "503");
        MINI.reset();

        MINI.si.notFoundIds.add("PROP-SI-004");
        Resp notFound = get(viewer(), ONE);
        assertThat(notFound.status()).isEqualTo(404);
        assertThat(notFound.<String>read("$.reason")).isEqualTo("si_not_found");
        assertThat(notFound.<String>read("$.details.id")).isEqualTo("PROP-SI-004");
        assertNoData(notFound, "404");
        MINI.reset();

        MINI.si.invalid = List.of(map("field", "id", "rule", "invalid_format", "message", "id 格式不合"));
        Resp invalid = get(viewer(), "/observations");
        assertThat(invalid.status()).isEqualTo(422);
        assertThat(invalid.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_REJECTED);
        assertThat(invalid.<String>read("$.details.bridgeReason")).isEqualTo("invalid_request");
        assertThat(invalid.<List<Map<String, Object>>>read("$.details.violations")).singleElement()
                .satisfies(v -> assertThat(v).containsEntry("field", "id"));
        assertNoData(invalid, "422");
        MINI.reset();

        MINI.si.status500 = true;
        assertBadGateway(get(viewer(), "/status"), "500");
        MINI.reset();
        MINI.si.garbage = "這不是 JSON";
        assertBadGateway(get(viewer(), "/observations"), "純文字");
        MINI.reset();
        MINI.si.arrayBody = true;
        assertBadGateway(get(viewer(), "/observations"), "JSON 陣列");
        MINI.reset();
        assertThat(get(viewer(), "/observations").status()).as("失敗之後立即重請求：沒有殘留的錯誤或上一次的結果").isEqualTo(200);
    }

    private void assertBadGateway(Resp resp, String label) {
        assertThat(resp.status()).as(label).isEqualTo(502);
        assertThat(resp.<String>read("$.reason")).as(label).isEqualTo(ErrorReasons.BRIDGE_ERROR);
        assertNoData(resp, label);
    }

    @Test
    void AT_932_3_5_aRefusedConnectionIs502AndAReadTimeoutIs504AfterAboutTwentySecondsWithoutRetry() {
        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp refused = get(viewer(), "/observations");
        assertThat(refused.status()).isEqualTo(502);
        assertThat(refused.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_UNREACHABLE);
        assertNoData(refused, "連線被拒");
        resetSystemConfigs();
        thresholds.invalidate();

        MINI.reset();
        MINI.si.delayMillis = 21_000;
        long started = System.nanoTime();
        Resp timedOut = get(viewer(), "/observations");
        Duration elapsed = Duration.ofNanos(System.nanoTime() - started);
        assertThat(timedOut.status()).isEqualTo(504);
        assertThat(timedOut.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_TIMEOUT);
        assertNoData(timedOut, "讀取逾時");
        assertThat(elapsed).as("讀取逾時 20 秒、不重試（若重試會超過 40 秒）").isBetween(Duration.ofSeconds(19), Duration.ofSeconds(40));
        assertThat(MINI.countRequests("GET /si/observations")).as("只送一次請求").isEqualTo(1);

        MINI.reset();
        Resp recovered = get(viewer(), "/observations");
        assertThat(recovered.status()).as("失敗之後立即重請求").isEqualTo(200);
        assertThat(data(recovered)).isEqualTo(goldenCamel("A").get("observations"));
    }

    // ── AT-932-4-1：JWT 與角色 ───────────────────────────────────────────────────────────────

    @Test
    void AT_932_4_1_withoutAValidTokenEverySiEndpointIs401AndNeverReachesTheBridge() {
        for (String path : SIX) {
            for (String token : new String[] {null, "garbage"}) {
                Resp resp = get(token, path);

                assertThat(resp.status()).as("%s token=%s", path, token).isEqualTo(401);
                assertThat(resp.has("$.data")).as("%s：401 沒有 data", path).isFalse();
            }
        }
        assertThat(MINI.requests()).as("401 不觸及 Bridge").isEmpty();
        int successes = 0;
        for (String token : List.of(viewer(), operator(), admin())) {
            for (String path : SIX) {
                Resp resp = get(token, path);

                assertThat(resp.status()).as(path).isEqualTo(200);
                assertThat(data(resp).size()).as("%s：data 非空", path).isGreaterThan(0);
                successes++;
            }
        }
        assertThat(MINI.requests()).as("成功請求每個恰一次 Bridge 呼叫").hasSize(successes);
    }

    // ── AT-932-4-E-1：三種角色一致，id 編碼為單一路徑段 ─────────────────────────────────────────

    @Test
    void AT_932_4_E_1_everyRoleSeesTheSameProposalAndAnUnknownIdIs404ForAll() {
        String card = items(MiniBridge.Si.golden("A.snake").get("proposal_one")).get(0).get("card").toString();
        MINI.si.notFoundIds.add("PROP-SI-998");
        for (String token : List.of(viewer(), operator(), admin())) {
            Resp real = get(token, ONE);
            assertThat(real.status()).isEqualTo(200);
            assertThat(real.<List<Object>>read("$.data.items")).hasSize(1);
            assertThat(real.<String>read("$.data.items[0].card")).as("卡面逐位元組等於黃金檔").isEqualTo(card);
            Resp missing = get(token, "/proposals/PROP-SI-998");
            assertThat(missing.status()).isEqualTo(404);
            assertThat(missing.<String>read("$.reason")).isEqualTo("si_not_found");
        }
    }

    @Test
    void AT_932_4_E_1_trickyIdsReachTheBridgeAsExactlyOnePathSegment() {
        Map<String, String> ids = new LinkedHashMap<>();
        ids.put("a b", "a%20b");
        ids.put("專案", "%E5%B0%88%E6%A1%88");
        ids.put("a?b", "a%3Fb");
        ids.put("a#b", "a%23b");
        String longId = "a b".repeat(333) + "c";
        assertThat(longId).hasSize(1000);
        ids.put(longId, "a%20b".repeat(333) + "c");
        for (Map.Entry<String, String> entry : ids.entrySet()) {
            String label = entry.getKey().length() > 40 ? "1000 字元長字串" : entry.getKey();
            for (String mode : List.of("not-found", "invalid")) {
                MINI.reset();
                MINI.si.seen.clear();
                if ("not-found".equals(mode)) {
                    MINI.si.notFoundIds.add(entry.getKey());
                } else {
                    MINI.si.invalid = List.of(map("field", "id", "rule", "invalid_format", "message", "x"));
                }

                Resp resp = send(viewer(), MockMvcRequestBuilders.get(SI + "/proposals/{id}", entry.getKey()));

                assertThat(MINI.si.seen).as("%s %s：恰一次 Bridge 請求", label, mode).hasSize(1);
                assertThat(MINI.si.seen.get(0).uri()).as("%s %s：原始 URI 恰為 /si/proposals/ 加單一編碼段", label, mode)
                        .isEqualTo("/si/proposals/" + entry.getValue());
                assertThat(MINI.si.seen.get(0).query()).as(label).isNull();
                if ("not-found".equals(mode)) {
                    assertThat(resp.status()).as(label).isEqualTo(404);
                    assertThat(resp.<String>read("$.reason")).as(label).isEqualTo("si_not_found");
                } else {
                    assertThat(resp.status()).as(label).isEqualTo(422);
                    assertThat(resp.<String>read("$.details.bridgeReason")).as(label).isEqualTo("invalid_request");
                }
            }
        }
    }

    // ── AT-940-5-2：reason 常數與帶 reason 的第二個 404 ─────────────────────────────────────────

    @Test
    void AT_940_5_2_theTwoConstantsExistAndSiNotFoundIsASecondExceptionToTheNoReason404Convention() throws IOException {
        assertThat(ErrorReasons.SI_UNAVAILABLE).isEqualTo("si_unavailable");
        assertThat(ErrorReasons.SI_NOT_FOUND).isEqualTo("si_not_found");
        MINI.si.notFoundIds.add("PROP-SI-004");
        Resp siNotFound = get(viewer(), ONE);
        assertThat(siNotFound.status()).isEqualTo(404);
        assertThat(siNotFound.<String>read("$.reason")).isEqualTo("si_not_found");
        Resp ordinary = api.get(viewer(), "/api/v1/projects/" + UUID.randomUUID());
        assertThat(ordinary.status()).isEqualTo(404);
        assertThat(ordinary.has("$.reason")).as("一般 404 沒有 reason：這是帶 reason 的第二個例外，不是 404 一律帶 reason").isFalse();

        Path root = Path.of("src", "main", "java", "com", "aisdlc", "console");
        String notFoundSource = Files.readString(root.resolve("domain/exception/NotFoundException.java"), StandardCharsets.UTF_8);
        String docSource = Files.readString(root.resolve("adapter/in/web/ErrorResponseDocumentation.java"), StandardCharsets.UTF_8);
        String reasonsSource = Files.readString(root.resolve("domain/exception/ErrorReasons.java"), StandardCharsets.UTF_8);
        for (String source : List.of(notFoundSource, docSource, reasonsSource)) {
            assertThat(source).doesNotContain("唯一帶 reason").doesNotContain("唯一例外");
        }
        assertThat(notFoundSource).contains("si_not_found");
        assertThat(docSource).contains("si_not_found");
        assertThat(reasonsSource).contains("SI_NOT_FOUND = \"si_not_found\"").contains("SI_UNAVAILABLE = \"si_unavailable\"");
    }
}
