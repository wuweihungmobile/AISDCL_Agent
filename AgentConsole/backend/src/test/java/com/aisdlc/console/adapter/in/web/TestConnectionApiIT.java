package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractOutboundIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.FakeHttpServer.Received;
import com.aisdlc.console.support.FakeHttpServer.Response;
import com.aisdlc.console.support.OutboundFakes;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.http.HttpMethod;
import org.springframework.boot.test.system.OutputCaptureExtension;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 測試模型連線（API-SET-06；契約 §1.5.7、E2E-10）。為什麼重要：這是後端唯一會「依使用者輸入的 URL 主動連出去」的端點——
 * SSRF 防線的每一條規則都要有「422 且沒有任何連線」的證據（假伺服器的請求數必須是 0），放行的路徑則要證明連線真的走到完整端點、
 * 帶對標頭、不跟 redirect、有逾時，並且金鑰與 userinfo 不出現在回應、日誌與審計。
 */
@ExtendWith(OutputCaptureExtension.class)
class TestConnectionApiIT extends AbstractOutboundIT {

    private static final String URL = "/api/v1/settings/test-connection";
    private static final String OUTBOUND = "目標位址未通過 SSRF／allowlist 檢查";
    private static final String SECRET = "sk-secret-xyz";

    private Resp test(Map<String, Object> body) {
        return api.post(admin(), URL, body);
    }

    private static Map<String, Object> request(String apiUrl, String apiKey) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("apiUrl", apiUrl);
        if (apiKey != null) {
            body.put("apiKey", apiKey);
        }
        return body;
    }

    private static String llmUrl() {
        return OutboundFakes.LLM.url(OutboundFakes.CHAT_PATH);
    }

    private static void llmAnswers(int status) {
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH, Response.json(status, "{\"ok\":true}"));
    }

    private static void assertNoConnectionWasMade() {
        assertThat(OutboundFakes.LLM.received()).isEmpty();
        assertThat(OutboundFakes.BRIDGE.received()).isEmpty();
        assertThat(OutboundFakes.TARGET.received()).isEmpty();
    }

    // ── SSRF／allowlist 拒絕（422，且沒有任何連線）────────────────────────────────

    private void assertRejected(String apiUrl, String violation) {
        Resp resp = test(request(apiUrl, SECRET));
        assertThat(resp.status()).as(apiUrl).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).as(apiUrl).isEqualTo(OUTBOUND);
        assertThat(resp.<String>read("$.details.violation")).as(apiUrl).isEqualTo(violation);
        assertThat(resp.<String>read("$.traceId")).isEqualTo(resp.header("X-Trace-Id"));
        assertThat(resp.body()).as("回應不得回顯金鑰或 userinfo").doesNotContain(SECRET)
                .doesNotContain("your_password_here");
        assertNoConnectionWasMade();
    }

    @Test
    void privateAndLinkLocalAddressesAreRefusedWhateverTheConfiguration() {
        for (String url : List.of("http://10.0.0.5:8080", "http://192.168.1.1", "http://172.16.0.9",
                "http://100.64.0.1", "http://0.0.0.0/v1", "http://[fc00::1]/v1")) {
            assertRejected(url, "private_ip");
        }
        assertRejected("http://169.254.169.254/latest/meta-data", "link_local");
        assertRejected("http://[fe80::1]/v1", "link_local");
        assertThat(test(request("http://10.0.0.5:8080", SECRET)).<String>read("$.details.host")).isEqualTo("10.0.0.5");
    }

    @Test
    void aLoopbackLiteralIsRefusedUnlessItIsExactlyOnTheAllowlist() {
        assertRejected("http://[::1]:8080", "loopback");
        assertRejected("http://127.0.0.2:" + OutboundFakes.LLM.port() + "/v1", "loopback");
    }

    @Test
    void nonStandardIpNotationsAreMalformedNotInterpreted() {
        for (String url : List.of("http://0x7f.0.0.1", "http://2130706433", "http://127.1", "http://0177.0.0.1",
                "http://1.2.3", "http://[::1", "http://exämple.com/v1", "http://a b/v1", "http://host\\name/v1")) {
            assertRejected(url, "malformed_url");
        }
    }

    @Test
    void anUnsupportedSchemeUserinfoOrUnlistedHostIsRefused() {
        assertRejected("ftp://api.minimax.io/v1/text/chatcompletion_v2", "scheme");
        assertRejected("file://x/etc/passwd", "scheme");
        assertRejected("http://user:your_password_here@api.minimax.io/v1/text/chatcompletion_v2", "userinfo");
        assertRejected("https://example.com", "not_in_allowlist");
        assertRejected("http://localhost.evil.example", "not_in_allowlist");
        assertRejected("http://api.minimax.io.evil.example/v1", "not_in_allowlist");
        assertRejected("http://evil.example/api.minimax.io", "not_in_allowlist");
    }

    @Test
    void anAllowlistedNameThatResolvesToAPrivateAddressIsRefusedAsDnsRebindingBeforeAnyConnection() {
        assertRejected("http://rebind.e2e.test/v1/chat/completions", "dns_rebinding");
        assertRejected("http://rebind.e2e.test:" + OutboundFakes.LLM.port() + "/v1/chat/completions", "dns_rebinding");
    }

    @Test
    void theStoredApiUrlIsCheckedTooWhenTheRequestOmitsIt() {
        jdbc.update("update console.system_configs set value = 'http://10.0.0.5' where category = 'model' "
                + "and key = 'apiUrl'");

        for (Resp resp : List.of(api.post(admin(), URL), api.post(admin(), URL, Map.of()),
                test(request(null, null)))) {
            assertThat(resp.status()).isEqualTo(422);
            assertThat(resp.<String>read("$.details.violation")).isEqualTo("private_ip");
        }
        assertNoConnectionWasMade();
    }

    // ── 連線成功與各種結果 ──────────────────────────────────────────────────────

    @Test
    void aReachableEndpointIsProbedWithTheDocumentedRequestAndReportsSuccess(CapturedOutput output) {
        configureFakeModel();
        llmAnswers(200);

        Resp resp = test(request(llmUrl(), SECRET));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.success")).isTrue();
        assertThat(resp.<String>read("$.data.message")).isEqualTo("連線成功");
        assertThat(resp.<Integer>read("$.data.httpStatus")).isEqualTo(200);
        assertThat(resp.<String>read("$.data.resolvedHost")).isEqualTo("127.0.0.1");
        assertThat(resp.<Integer>read("$.data.latencyMs")).isGreaterThanOrEqualTo(0);

        assertThat(OutboundFakes.LLM.received()).hasSize(1);
        Received probe = OutboundFakes.LLM.received().get(0);
        assertThat(probe.method()).isEqualTo("POST");
        assertThat(probe.path()).as("原樣 POST 完整端點，不補路徑").isEqualTo("/v1/chat/completions");
        assertThat(probe.headers()).containsEntry("authorization", "Bearer " + SECRET)
                .containsEntry("user-agent", "aisdlc-console");
        assertThat(probe.headers().get("content-type")).startsWith("application/json");
        assertThat(probe.headers().get("accept")).isEqualTo("application/json");
        assertThat(JsonPath.<Integer>read(probe.body(), "$.max_tokens")).isEqualTo(1);
        assertThat(JsonPath.<Boolean>read(probe.body(), "$.stream")).isFalse();
        assertThat(JsonPath.<String>read(probe.body(), "$.messages[0].role")).isEqualTo("user");
        assertThat(JsonPath.<String>read(probe.body(), "$.messages[0].content")).isEqualTo("ping");
        assertThat(JsonPath.<String>read(probe.body(), "$.model")).as("省略時取已儲存的 model.name")
                .isEqualTo("e2e-model");

        assertThat(resp.body()).doesNotContain(SECRET);
        assertThat(output.getAll()).as("金鑰不寫日誌").doesNotContain(SECRET);
    }

    @Test
    void omittedFieldsFallBackToTheStoredModelSettings() {
        configureFakeModel();
        llmAnswers(200);

        Resp resp = api.post(admin(), URL, Map.of());

        assertThat(resp.<Boolean>read("$.data.success")).isTrue();
        Received probe = OutboundFakes.LLM.received().get(0);
        assertThat(probe.headers()).containsEntry("authorization", "Bearer sk-e2e-dummy");
        assertThat(JsonPath.<String>read(probe.body(), "$.model")).isEqualTo("e2e-model");
    }

    @Test
    void aRequestOverrideOfTheModelNameIsUsedAndWithoutAnyKeyNoAuthorizationHeaderIsSent() {
        putSetting("model", "apiUrl", llmUrl(), false);
        llmAnswers(200);

        Map<String, Object> body = request(null, null);
        body.put("model", "custom-model");
        Resp resp = test(body);

        assertThat(resp.<Boolean>read("$.data.success")).isTrue();
        Received probe = OutboundFakes.LLM.received().get(0);
        assertThat(probe.headers()).doesNotContainKey("authorization");
        assertThat(JsonPath.<String>read(probe.body(), "$.model")).isEqualTo("custom-model");
    }

    @Test
    void anEndpointWithoutAPathProvesThatNoPathIsAdded() {
        Resp resp = test(request("http://127.0.0.1:" + OutboundFakes.LLM.port(), null));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.success")).isFalse();
        assertThat(resp.<String>read("$.data.message")).isEqualTo("端點路徑不存在或不接受 POST（HTTP 404）");
        assertThat(resp.<Integer>read("$.data.httpStatus")).isEqualTo(404);
        assertThat(OutboundFakes.LLM.received()).hasSize(1);
        assertThat(OutboundFakes.LLM.received().get(0).path()).isIn("", "/");
    }

    @Test
    void theHttpStatusOfTheEndpointIsTranslatedIntoAnActionableMessage() {
        Map<Integer, String> expected = new LinkedHashMap<>();
        expected.put(401, "認證失敗（HTTP 401）");
        expected.put(403, "認證失敗（HTTP 403）");
        expected.put(404, "端點路徑不存在或不接受 POST（HTTP 404）");
        expected.put(405, "端點路徑不存在或不接受 POST（HTTP 405）");
        expected.put(400, "服務回應錯誤（HTTP 400）");
        expected.put(429, "服務回應錯誤（HTTP 429）");
        expected.put(500, "服務回應錯誤（HTTP 500）");
        expected.put(503, "服務回應錯誤（HTTP 503）");
        expected.forEach((status, message) -> {
            OutboundFakes.LLM.reset();
            llmAnswers(status);
            Resp resp = test(request(llmUrl(), SECRET));
            assertThat(resp.status()).as("HTTP " + status).isEqualTo(200);
            assertThat(resp.<Boolean>read("$.data.success")).isFalse();
            assertThat(resp.<String>read("$.data.message")).isEqualTo(message);
            assertThat(resp.<Integer>read("$.data.httpStatus")).isEqualTo(status);
            assertThat(resp.<Integer>read("$.data.latencyMs")).isNotNull();
        });
        OutboundFakes.LLM.reset();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH, Response.json(204, ""));
        assertThat(test(request(llmUrl(), SECRET)).<Boolean>read("$.data.success")).as("任何 2xx 都算成功").isTrue();
    }

    @Test
    void aRedirectIsReportedAndNeverFollowed() {
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH, Response.redirect(OutboundFakes.TARGET.url("/redirected")));
        OutboundFakes.TARGET.on("POST", "/redirected", Response.json(200, "{}"));
        OutboundFakes.TARGET.on("GET", "/redirected", Response.json(200, "{}"));

        Resp resp = test(request(llmUrl(), SECRET));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.success")).isFalse();
        assertThat(resp.<String>read("$.data.message")).contains("已拒絕跟隨").contains("302");
        assertThat(OutboundFakes.TARGET.receivedAt("/redirected")).as("重導向目標的請求數必須是 0").isEmpty();
        assertThat(OutboundFakes.TARGET.received()).isEmpty();
    }

    @Test
    void aSlowEndpointIsCutOffAtTheConfiguredTimeout() {
        putSetting("model", "timeout", "1", false);
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH, Response.json(200, "{}").delayed(5_000));

        long started = System.nanoTime();
        Resp resp = test(request(llmUrl(), SECRET));
        long elapsedMillis = (System.nanoTime() - started) / 1_000_000;

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.success")).isFalse();
        assertThat(resp.<String>read("$.data.message")).isEqualTo("連線逾時（1 秒）");
        assertThat(resp.<Object>read("$.data.latencyMs")).isNull();
        assertThat(resp.<Object>read("$.data.httpStatus")).isNull();
        assertThat(elapsedMillis).as("約 1 秒內返回，不等滿 5 秒").isLessThan(3_500);
    }

    @Test
    void aClosedPortIsReportedAsAConnectionFailureWithoutLeakingTheUrl() {
        Resp resp = test(request("http://127.0.0.1:1/v1/chat/completions", SECRET));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.success")).isFalse();
        assertThat(resp.<String>read("$.data.message")).startsWith("無法連線：");
        assertThat(resp.<String>read("$.data.resolvedHost")).isEqualTo("127.0.0.1");
        assertThat(resp.<Object>read("$.data.httpStatus")).isNull();
        assertThat(resp.body()).doesNotContain(SECRET);
    }

    // ── 輸入驗證與角色 ──────────────────────────────────────────────────────────

    @Test
    void anOversizedFieldOrAMalformedBodyIs400() {
        assertThat(test(request("http://127.0.0.1/" + "p".repeat(500), null)).status()).isEqualTo(400);
        Map<String, Object> longKey = request(llmUrl(), "k".repeat(513));
        assertThat(test(longKey).status()).isEqualTo(400);
        Map<String, Object> longModel = request(llmUrl(), null);
        longModel.put("model", "m".repeat(101));
        assertThat(test(longModel).status()).isEqualTo(400);
        assertThat(api.raw(admin(), HttpMethod.POST, URL, "{not json").status()).isEqualTo(400);
        assertNoConnectionWasMade();
    }

    @Test
    void onlyAnAdminMayTestAConnection() {
        llmAnswers(200);
        assertThat(api.post(operator(), URL, request(llmUrl(), null)).status()).isEqualTo(403);
        assertThat(api.post(viewer(), URL, request(llmUrl(), null)).status()).isEqualTo(403);
        assertThat(api.post(null, URL, request(llmUrl(), null)).status()).isEqualTo(401);
        assertThat(OutboundFakes.LLM.received()).as("被拒絕的角色不會觸發任何外呼").isEmpty();
    }

    // ── 審計 ─────────────────────────────────────────────────────────────────

    @Test
    void everyCallEvenARefusedOneIsAuditedWithTheHostAndTheOutcomeButNeverTheKeyOrUserinfo(CapturedOutput output) {
        llmAnswers(200);
        assertThat(test(request(llmUrl(), SECRET)).status()).isEqualTo(200);
        assertThat(test(request("http://10.0.0.5:8080", SECRET)).status()).isEqualTo(422);
        assertThat(test(request("http://user:your_password_here@api.minimax.io/v1/x", SECRET)).status())
                .isEqualTo(422);
        assertThat(test(request("http://127.0.0.1:1/v1/x", SECRET)).status()).isEqualTo(200);

        List<String> lines = output.getAll().lines().filter(l -> l.contains("\"action\":\"settings.testConnection\""))
                .map(l -> l.substring(l.indexOf("{\"event\":\"audit\""))).toList();
        assertThat(lines).hasSize(4);
        assertThat(JsonPath.<String>read(lines.get(0), "$.detail.host")).isEqualTo("127.0.0.1");
        assertThat(JsonPath.<Boolean>read(lines.get(0), "$.detail.success")).isTrue();
        assertThat(JsonPath.<Integer>read(lines.get(0), "$.detail.httpStatus")).isEqualTo(200);
        assertThat(JsonPath.<String>read(lines.get(1), "$.detail.host")).isEqualTo("10.0.0.5");
        assertThat(JsonPath.<Boolean>read(lines.get(1), "$.detail.success")).isFalse();
        assertThat(JsonPath.<String>read(lines.get(1), "$.detail.rejected")).isEqualTo("private_ip");
        assertThat(JsonPath.<String>read(lines.get(2), "$.detail.rejected")).isEqualTo("userinfo");
        assertThat(JsonPath.<String>read(lines.get(3), "$.detail.io")).isNotBlank();
        assertThat(output.getAll()).doesNotContain(SECRET).doesNotContain("your_password_here");

        assertThat(jdbc.queryForObject("select count(*) from console.audit_log where path = "
                + "'/api/v1/settings/test-connection' and entity_type = 'settings' and subject = 'admin'",
                Integer.class)).isEqualTo(4);
    }
}
