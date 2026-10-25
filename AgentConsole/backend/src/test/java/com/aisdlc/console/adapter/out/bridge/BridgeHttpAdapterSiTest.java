package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.si.SiExport;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.test.web.client.RequestMatcher;
import org.springframework.test.web.client.ResponseCreator;
import org.springframework.test.web.client.response.DefaultResponseCreator;
import org.springframework.web.client.RestClient;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;
import static org.hamcrest.Matchers.emptyOrNullString;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.headerDoesNotExist;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

/**
 * SelfImproving 唯讀鏡像的 Bridge 呼叫（TCS-SelfImprovingMirror-P1b R7、R8、R10；AT-932-3-4、AT-940-8-3），以
 * {@code MockRestServiceServer} 驗「送出的請求」與「各種回應拋出的例外型別」。
 * 為什麼重要：這支呼叫的失敗模式有十種，前端靠例外型別對映到「資料面不可用」「查無此提案」「引擎故障」三種完全不同的畫面——
 * 任何一種被吞成別種（例如 503 被當成 502、重試把一次失敗變兩次請求）都會讓畫面說錯話；而 {@code {id}} 若沒被編成單一路徑段，
 * 就是路徑穿越的入口（含編碼斜線的網址進不了 backend，所以防線只能在這一層斷言）。
 */
class BridgeHttpAdapterSiTest {

    private static final String BASE = "http://bridge.test:8081";
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final String OBSERVATIONS = """
            {"schema_rev":1,"kind":"observations","generated_at":"2026-10-21T00:00:00+08:00","head_sha":null,
             "items":[{"id":"OBS-SI-001","marks_kv":{"面":"流程"},"line":11,"touched_sha256":null}],
             "next_since":null,"truncated":false,"ne":[],"problems":[],"future_key":{"x_y":[1,null]}}
            """;
    private static final String PROPOSAL = """
            {"schema_rev":1,"kind":"proposals","generated_at":"2026-10-21T00:00:00+08:00","head_sha":"%s",
             "items":[{"id":"PROP-SI-004","card":"[PROP-SI-004] 卡面\\n"}],"next_since":null,"truncated":false,"ne":[],"problems":[]}
            """.formatted("0".repeat(40));

    /** 一個接上 {@code MockRestServiceServer} 的介面卡，與它被要求的（連線，讀取）逾時。 */
    private static final class Rig {
        final MockRestServiceServer server;
        final BridgeHttpAdapter adapter;
        final List<Duration[]> timeouts = new ArrayList<>();

        Rig() {
            RestClient.Builder builder = RestClient.builder();
            server = MockRestServiceServer.bindTo(builder).build();
            SettingValues settings = new SettingValues() {
                @Override
                public Optional<String> find(String category, String key) {
                    return Optional.empty();
                }

                @Override
                public Optional<String> findCustomized(String category, String key) {
                    return Optional.empty();
                }
            };
            adapter = new BridgeHttpAdapter(builder, new BridgeEndpoints(settings, new BridgeProperties(BASE, null, null)),
                    (connect, read) -> {
                        timeouts.add(new Duration[] {connect, read});
                        return null;
                    });
        }
    }

    private final Rig rig = new Rig();

    private static Map<String, Object> asMap(String json) {
        return JSON.readValue(json, new TypeReference<Map<String, Object>>() { });
    }

    private static DefaultResponseCreator jsonStatus(HttpStatus status, String body) {
        return withStatus(status).contentType(MediaType.APPLICATION_JSON).body(body);
    }

    // ── 請求形態與逾時 ─────────────────────────────────────────────────────────────

    @Test
    void AT_932_3_4_theRequestShapeIsAGetWithATraceIdNoTokenAndTheTwoAndTwentySecondTimeouts() {
        rig.server.expect(requestTo(BASE + "/si/observations?since=5&limit=10")).andExpect(method(HttpMethod.GET))
                .andExpect(header("X-Trace-Id", not(emptyOrNullString())))
                .andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withSuccess(OBSERVATIONS, MediaType.APPLICATION_JSON));
        rig.server.expect(requestTo(BASE + "/si/proposals/PROP-SI-004")).andExpect(method(HttpMethod.GET))
                .andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withSuccess(PROPOSAL, MediaType.APPLICATION_JSON));

        SiExport list = rig.adapter.siExport("observations", 5, 10, null);
        SiExport single = rig.adapter.siExport("proposals", null, null, "PROP-SI-004");

        rig.server.verify();
        assertThat(list.raw()).as("snake_case 鍵與 null、未知鍵逐值原樣").isEqualTo(asMap(OBSERVATIONS));
        assertThat(list.raw().keySet()).containsExactlyElementsOf(asMap(OBSERVATIONS).keySet());
        assertThat(list.raw()).containsEntry("head_sha", null);
        assertThat(single.raw()).isEqualTo(asMap(PROPOSAL));
        assertThat(rig.timeouts).hasSize(2).allSatisfy(pair -> {
            assertThat(pair[0]).as("連線逾時").isEqualTo(Duration.ofSeconds(2));
            assertThat(pair[1]).as("讀取逾時（Bridge 的 15 秒子行程逾時之上）").isEqualTo(Duration.ofSeconds(20));
        });
    }

    @Test
    void AT_932_3_4_queryParametersAreSentInTheFixedOrderAndNeverForStatusOrASingleProposal() {
        Map<String, String[]> cases = new LinkedHashMap<>();
        cases.put("/si/observations", new String[] {"observations", null, null});
        cases.put("/si/events?since=0", new String[] {"events", "0", null});
        cases.put("/si/runs?limit=3", new String[] {"runs", null, "3"});
        cases.put("/si/proposals?since=7&limit=100", new String[] {"proposals", "7", "100"});
        cases.put("/si/status", new String[] {"status", "5", "10"});             // status 不收任何查詢參數
        for (Map.Entry<String, String[]> entry : cases.entrySet()) {
            String[] c = entry.getValue();
            rig.server.reset();
            rig.server.expect(requestTo(BASE + entry.getKey()))
                    .andRespond(withSuccess(OBSERVATIONS, MediaType.APPLICATION_JSON));

            rig.adapter.siExport(c[0], c[1] == null ? null : Integer.valueOf(c[1]),
                    c[2] == null ? null : Integer.valueOf(c[2]), null);

            rig.server.verify();
        }
        rig.server.reset();
        rig.server.expect(requestTo(BASE + "/si/proposals/PROP-SI-004")).andRespond(withSuccess(PROPOSAL,
                MediaType.APPLICATION_JSON));
        rig.adapter.siExport("proposals", 5, 10, "PROP-SI-004");              // 單筆：since 與 limit 都不送
        rig.server.verify();
    }

    // ── 十種 Bridge 回應各自拋出的例外型別，且每種失敗只送一次請求 ───────────────────────────────────

    private void expectOneRequest(String path, ResponseCreator answer) {
        rig.server.reset();
        rig.server.expect(requestTo(BASE + path)).andRespond(answer);
    }

    @Test
    void AT_932_3_4_everyBridgeAnswerThrowsTheDocumentedExceptionWithExactlyOneRequest() {
        String unavailable = """
                {"code":503,"reason":"si_unavailable","cause":"nonzero_rc","detail":"rc=3; stderr=錯誤：全形與\\n換行"}""";
        String notFound = "{\"code\":404,\"reason\":\"si_not_found\",\"id\":\"PROP-SI-998\"}";
        String invalid = "{\"code\":422,\"reason\":\"invalid_request\",\"violations\":[{\"field\":\"id\","
                + "\"rule\":\"invalid_format\",\"message\":\"x\"}]}";
        Map<String, ResponseCreator> answers = new LinkedHashMap<>();
        answers.put("200 非 JSON", withSuccess("this is not json", MediaType.TEXT_PLAIN));
        answers.put("200 JSON 陣列", withSuccess("[1,2,3]", MediaType.APPLICATION_JSON));
        answers.put("503 si_unavailable", jsonStatus(HttpStatus.SERVICE_UNAVAILABLE, unavailable));
        answers.put("404 si_not_found", jsonStatus(HttpStatus.NOT_FOUND, notFound));
        answers.put("422 invalid_request", jsonStatus(HttpStatus.UNPROCESSABLE_CONTENT, invalid));
        answers.put("500", jsonStatus(HttpStatus.INTERNAL_SERVER_ERROR, "{\"code\":500,\"reason\":\"boom\"}"));
        answers.put("403", jsonStatus(HttpStatus.FORBIDDEN, "{\"code\":403,\"reason\":\"forbidden\"}"));
        answers.put("連線例外", withException(new ConnectException("Connection refused")));
        answers.put("讀取逾時例外", withException(new SocketTimeoutException("Read timed out")));
        for (Map.Entry<String, ResponseCreator> entry : answers.entrySet()) {
            String label = entry.getKey();
            expectOneRequest("/si/proposals/PROP-SI-004", entry.getValue());

            Throwable thrown = catchThrowable(() -> rig.adapter.siExport("proposals", null, null, "PROP-SI-004"));

            rig.server.verify();                    // 恰好一次請求：重試會在第二次請求時被 MockRestServiceServer 拒絕
            assertThat(thrown).as(label).isNotNull();
            switch (label) {
                case "200 非 JSON", "200 JSON 陣列", "500" ->
                        assertThat(thrown).as(label).isInstanceOf(UpstreamException.Failure.class);
                case "連線例外" -> assertThat(thrown).as(label).isInstanceOf(UpstreamException.Unavailable.class);
                case "讀取逾時例外" -> assertThat(thrown).as(label).isInstanceOf(UpstreamException.TimedOut.class);
                default -> assertThat(thrown).as(label).isInstanceOf(BridgeRejectedException.class);
            }
            if (thrown instanceof BridgeRejectedException rejected) {
                switch (label) {
                    case "503 si_unavailable" -> {
                        assertThat(rejected.status()).isEqualTo(503);
                        assertThat(rejected.reason()).isEqualTo("si_unavailable");
                        assertThat(rejected.body()).containsEntry("cause", "nonzero_rc")
                                .containsEntry("detail", "rc=3; stderr=錯誤：全形與\n換行");
                        assertThat(rejected.detail()).as("detail 逐字（含全形字元與換行）")
                                .isEqualTo("rc=3; stderr=錯誤：全形與\n換行");
                    }
                    case "404 si_not_found" -> {
                        assertThat(rejected.status()).isEqualTo(404);
                        assertThat(rejected.reason()).isEqualTo("si_not_found");
                        assertThat(rejected.body()).containsEntry("id", "PROP-SI-998");
                    }
                    case "422 invalid_request" -> {
                        assertThat(rejected.status()).isEqualTo(422);
                        assertThat(rejected.reason()).isEqualTo("invalid_request");
                        assertThat(rejected.violations()).singleElement()
                                .satisfies(v -> assertThat(v).containsEntry("field", "id"));
                    }
                    default -> {
                        assertThat(rejected.status()).isEqualTo(403);
                        assertThat(rejected.reason()).isEqualTo("forbidden");
                    }
                }
            }
            if (thrown instanceof UpstreamException.Failure failure && "500".equals(label)) {
                assertThat(failure.details()).containsEntry("bridgeStatus", 500).containsEntry("bridgeReason", "boom");
            }
        }
        assertThat(rig.timeouts).as("每次呼叫的連線與讀取逾時").hasSize(answers.size()).allSatisfy(pair -> {
            assertThat(pair[0]).isEqualTo(Duration.ofSeconds(2));
            assertThat(pair[1]).isEqualTo(Duration.ofSeconds(20));
        });
    }

    // ── {id} 的編碼：嚴格 percent-encode 成單一路徑段 ─────────────────────────────────────────────

    private static String oracle(String id) {
        // 獨立於被測碼的參照：URLEncoder 的結果再訂正三處與 RFC 3986 嚴格編碼的差異（+→%20、*→%2A、%7E→~）
        return URLEncoder.encode(id, StandardCharsets.UTF_8).replace("+", "%20").replace("*", "%2A").replace("%7E", "~");
    }

    @Test
    void AT_932_3_4_maliciousIdsAreEncodedAsOneStrictPathSegment() {
        Map<String, String> expected = new LinkedHashMap<>();
        expected.put("a/b", "a%2Fb");
        expected.put("..", "%2E%2E");
        expected.put(".", "%2E");
        expected.put("%2F", "%252F");
        expected.put("a b", "a%20b");
        expected.put("專案", "%E5%B0%88%E6%A1%88");
        expected.put("a?b", "a%3Fb");
        expected.put("a#b", "a%23b");
        expected.put("a;b", "a%3Bb");
        expected.put("a\\b", "a%5Cb");
        expected.put("a%b", "a%25b");
        String longId = ("a b/專案?#;\\%." + "x").repeat(100).substring(0, 1000);
        assertThat(longId).hasSize(1000);
        expected.put(longId, oracle(longId));
        for (Map.Entry<String, String> entry : expected.entrySet()) {
            String id = entry.getKey();
            String label = id.length() > 40 ? "1000 字元長字串" : id;
            List<URI> seen = new ArrayList<>();
            RequestMatcher capture = request -> seen.add(request.getURI());
            rig.server.reset();
            rig.server.expect(requestTo(BASE + "/si/proposals/" + entry.getValue())).andExpect(capture)
                    .andRespond(withSuccess(PROPOSAL, MediaType.APPLICATION_JSON));

            assertThat(rig.adapter.siExport("proposals", null, null, id).raw()).as(label).isNotEmpty();

            rig.server.verify();
            URI uri = seen.get(0);
            String tail = uri.getRawPath().substring("/si/proposals/".length());
            assertThat(uri.getRawPath()).as(label).startsWith("/si/proposals/");
            assertThat(tail).as("%s：路徑只比 /si/proposals/ 多一段", label).doesNotContain("/").isEqualTo(entry.getValue());
            assertThat(uri.getRawQuery()).as(label).isNull();
            assertThat(uri.getRawFragment()).as(label).isNull();
        }
        assertThat(BridgeHttpAdapter.pathSegment("..")).isEqualTo("%2E%2E");
        assertThat(BridgeHttpAdapter.pathSegment("...")).as("只有整段恰為 . 或 .. 才額外編點").isEqualTo("...");
        assertThat(BridgeHttpAdapter.pathSegment("a.b")).isEqualTo("a.b");
        assertThat(BridgeHttpAdapter.pathSegment("PROP-SI-004_~x")).isEqualTo("PROP-SI-004_~x");
    }

    // ── siBase：解析規則同 sddBase 且每次重新解析 ─────────────────────────────────────────────────

    @Test
    void AT_940_8_3_siBaseResolvesExactlyLikeSddBaseAndReReadsTheSettingEveryTime() {
        AtomicReference<String> custom = new AtomicReference<>();
        SettingValues settings = new SettingValues() {
            @Override
            public Optional<String> find(String category, String key) {
                return Optional.empty();
            }

            @Override
            public Optional<String> findCustomized(String category, String key) {
                return "sdd".equals(category) && "engineUrl".equals(key) ? Optional.ofNullable(custom.get())
                        : Optional.empty();
            }
        };
        BridgeEndpoints endpoints = new BridgeEndpoints(settings, new BridgeProperties("http://env.test:8081/", null, null));

        assertThat(endpoints.siBase()).as("(a) 只有 ENGINE_BRIDGE_URL：去尾斜線").isEqualTo("http://env.test:8081")
                .isEqualTo(endpoints.sddBase());
        custom.set("http://custom.test:9000");
        assertThat(endpoints.siBase()).as("(b) 自訂 sdd.engineUrl 優先").isEqualTo("http://custom.test:9000")
                .isEqualTo(endpoints.sddBase());
        custom.set("http://custom.test:9100///");
        assertThat(endpoints.siBase()).as("(c) 兩者都有且結尾帶多個斜線：取自訂、去尾斜線")
                .isEqualTo("http://custom.test:9100").isEqualTo(endpoints.sddBase());
        custom.set("http://custom.test:9200");
        assertThat(endpoints.siBase()).as("每次呼叫重新解析：設定改變後下一次即為新值").isEqualTo("http://custom.test:9200");
        custom.set(null);
        assertThat(endpoints.siBase()).isEqualTo("http://env.test:8081");
    }
}
