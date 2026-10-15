package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeHealth;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.DecomposeRequest;
import com.aisdlc.console.application.port.out.AgentBridge.DecomposeResult;
import com.aisdlc.console.application.port.out.AgentBridge.SddCompileResult;
import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

/**
 * Bridge 出站介面卡（契約 §3.1／§3.2）。以 {@code MockRestServiceServer} 驗「送出的請求」與「各種回應如何分流」。
 * 為什麼重要：Bridge 的 4xx 要原樣帶回給用例（它們決定 409／422 的語意），連線失敗與逾時要分成 502／504，
 * 5xx 不可被當成成功；請求欄位名錯一個字，Bridge 的 {@code extra=forbid} 就整個拒絕。
 */
class BridgeHttpAdapterTest {

    /** 記憶體內的設定值（不需要資料庫）。 */
    private static final class FakeSettings implements SettingValues {
        final Map<String, String> values = new HashMap<>();
        final Map<String, String> customized = new HashMap<>();

        @Override
        public Optional<String> find(String category, String key) {
            return Optional.ofNullable(values.get(category + "." + key));
        }

        @Override
        public Optional<String> findCustomized(String category, String key) {
            return Optional.ofNullable(customized.get(category + "." + key));
        }
    }

    private static final String BASE = "http://bridge.test:8081";

    private final FakeSettings settings = new FakeSettings();
    private MockRestServiceServer server;
    private BridgeHttpAdapter adapter;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder();
        server = MockRestServiceServer.bindTo(builder).build();
        // 回 null＝沿用 Builder 自己的（被 MockRestServiceServer 接手的）請求工廠
        adapter = new BridgeHttpAdapter(builder, new BridgeEndpoints(settings, new BridgeProperties(BASE)),
                (connect, read) -> null);
    }

    // ── decompose ────────────────────────────────────────────────────────────

    @Test
    void decomposePostsTheDocumentedBodyAndParsesTheDraft() {
        server.expect(requestTo(BASE + "/autoclaude/decompose")).andExpect(method(HttpMethod.POST))
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.goal").value("做一個待辦清單"))
                .andExpect(jsonPath("$.context").value("補充"))
                .andExpect(jsonPath("$.project").value("做一個待辦清單"))
                .andExpect(jsonPath("$.max_steps").value(24))
                .andExpect(jsonPath("$.config_overrides.minimax.base_url").value("https://api.minimax.io/v1/x"))
                .andExpect(jsonPath("$.config_overrides.minimax.model").value("MiniMax-M2.7"))
                .andExpect(jsonPath("$.config_overrides.minimax.timeout_seconds").value(120))
                .andRespond(withSuccess("""
                        {"draft_id":"d-1","goal_hash":"h","reasoning":"先拆再做","signed_off":false,
                         "playbook":{"project":"x","tasks":[
                           {"step_id":"s1","name":"建檔","prompt":"請建立檔案","evaluator_command":"pytest -q"},
                           {"step_id":"s2","name":"測試","prompt":"請測試"}]}}
                        """, MediaType.APPLICATION_JSON));

        DecomposeResult result = adapter.decompose(new DecomposeRequest("做一個待辦清單", "補充", "做一個待辦清單", 24,
                Map.of("base_url", "https://api.minimax.io/v1/x", "model", "MiniMax-M2.7", "timeout_seconds", 120)),
                Duration.ofSeconds(135));

        server.verify();
        assertThat(result.draftId()).isEqualTo("d-1");
        assertThat(result.reasoning()).isEqualTo("先拆再做");
        assertThat(result.steps()).hasSize(2);
        assertThat(result.steps().get(0).stepId()).isEqualTo("s1");
        assertThat(result.steps().get(0).evaluatorCommand()).isEqualTo("pytest -q");
        assertThat(result.steps().get(1).evaluatorCommand()).isNull();
    }

    @Test
    void decomposeOmitsConfigOverridesWhenThereIsNoMiniMaxKey() {
        server.expect(requestTo(BASE + "/autoclaude/decompose"))
                .andExpect(jsonPath("$.config_overrides").doesNotExist())
                .andRespond(withSuccess("{\"draft_id\":\"d\",\"playbook\":{\"tasks\":[]}}", MediaType.APPLICATION_JSON));
        assertThat(adapter.decompose(new DecomposeRequest("g", "", "p", 24, null), Duration.ofSeconds(30)).steps())
                .isEmpty();
        server.verify();
    }

    @Test
    void aBridge422WithAGateIsCarriedBackVerbatimForTheUseCaseToTranslate() {
        server.expect(requestTo(BASE + "/autoclaude/decompose")).andRespond(withStatus(
                org.springframework.http.HttpStatus.UNPROCESSABLE_CONTENT).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":422,\"reason\":\"too_many_steps\",\"gate\":\"max_steps\",\"detail\":\"超過 24 步\"}"));
        assertThatThrownBy(() -> adapter.decompose(new DecomposeRequest("g", "", "p", 24, null), Duration.ofSeconds(5)))
                .isInstanceOfSatisfying(BridgeRejectedException.class, e -> {
                    assertThat(e.status()).isEqualTo(422);
                    assertThat(e.reason()).isEqualTo("too_many_steps");
                    assertThat(e.gate()).isEqualTo("max_steps");
                    assertThat(e.detail()).isEqualTo("超過 24 步");
                });
    }

    // ── approve ──────────────────────────────────────────────────────────────

    @Test
    void approvePostsToTheColonSuffixedPathWithTheApprover() {
        server.expect(requestTo(BASE + "/autoclaude/decompose/9b2c1a0e-aaaa-bbbb-cccc-0123456789ab:approve"))
                .andExpect(method(HttpMethod.POST)).andExpect(jsonPath("$.approver").value("Alice"))
                .andRespond(withSuccess("{\"signed_off\":true,\"approver\":\"Alice\"}", MediaType.APPLICATION_JSON));
        adapter.approveDraft("9b2c1a0e-aaaa-bbbb-cccc-0123456789ab", "Alice");
        server.verify();
    }

    @Test
    void approveReportsBridgeConflictAndNotFoundAsRejectionsWithTheirReasons() {
        server.expect(requestTo(BASE + "/autoclaude/decompose/d1:approve")).andRespond(withStatus(
                org.springframework.http.HttpStatus.CONFLICT).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":409,\"reason\":\"already_signed_off\",\"approver\":\"Bob\"}"));
        assertThatThrownBy(() -> adapter.approveDraft("d1", "Alice")).isInstanceOfSatisfying(
                BridgeRejectedException.class, e -> {
                    assertThat(e.status()).isEqualTo(409);
                    assertThat(e.reason()).isEqualTo("already_signed_off");
                });
        server.reset();
        server.expect(requestTo(BASE + "/autoclaude/decompose/d2:approve")).andRespond(withStatus(
                org.springframework.http.HttpStatus.NOT_FOUND).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":404,\"reason\":\"draft_not_found\",\"draft_id\":\"d2\"}"));
        assertThatThrownBy(() -> adapter.approveDraft("d2", "Alice")).isInstanceOfSatisfying(
                BridgeRejectedException.class, e -> assertThat(e.reason()).isEqualTo("draft_not_found"));
    }

    // ── sdd compile ──────────────────────────────────────────────────────────

    @Test
    void sddCompilePostsTheSpecDirAndParsesTheContracts() {
        server.expect(requestTo(BASE + "/sdd/compile")).andExpect(method(HttpMethod.POST))
                .andExpect(jsonPath("$.spec_dir").value("C:\\work\\proj"))
                .andRespond(withSuccess("""
                        {"scenario":"購物車","spec_path":"/spec/a.yaml","digest":"abcdef0123456789","spec_format_version":"1",
                         "contracts":[],
                         "tasks":[{"step_id":"C1","name":"加入商品","prompt":"實作加入","expected_output_regex":"OK\\\\d+",
                                   "evaluator_command":"pytest -q","weak_regex":true},
                                  {"step_id":"C2","name":"結帳","prompt":"實作結帳"}]}
                        """, MediaType.APPLICATION_JSON));
        SddCompileResult result = adapter.sddCompile("C:\\work\\proj");
        server.verify();
        assertThat(result.scenario()).isEqualTo("購物車");
        assertThat(result.digest()).isEqualTo("abcdef0123456789");
        assertThat(result.tasks()).hasSize(2);
        assertThat(result.tasks().get(0).weakRegex()).isTrue();
        assertThat(result.tasks().get(0).expectedOutputRegex()).isEqualTo("OK\\d+");
        assertThat(result.tasks().get(1).weakRegex()).isFalse();
        assertThat(result.tasks().get(1).expectedOutputRegex()).isNull();
    }

    @Test
    void sddCompileSpecRejectionsAreFourTwentyTwoRejectionsWithTheBridgeReason() {
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withStatus(
                org.springframework.http.HttpStatus.UNPROCESSABLE_CONTENT).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":422,\"reason\":\"spec_not_frozen\",\"detail\":\"規格尚未凍結\"}"));
        assertThatThrownBy(() -> adapter.sddCompile("/spec")).isInstanceOfSatisfying(BridgeRejectedException.class,
                e -> {
                    assertThat(e.status()).isEqualTo(422);
                    assertThat(e.reason()).isEqualTo("spec_not_frozen");
                    assertThat(e.detail()).isEqualTo("規格尚未凍結");
                    assertThat(e.body()).containsEntry("reason", "spec_not_frozen");
                });
    }

    @Test
    void sanitizationViolationsAreCarriedAsAList() {
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withStatus(
                org.springframework.http.HttpStatus.UNPROCESSABLE_CONTENT).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":422,\"reason\":\"sanitization_failed\",\"violations\":[{\"field\":\"spec_dir\","
                        + "\"rule\":\"allowed_root\",\"message\":\"不在 allowlist 內\"}]}"));
        assertThatThrownBy(() -> adapter.sddCompile("/etc")).isInstanceOfSatisfying(BridgeRejectedException.class,
                e -> assertThat(e.violations()).singleElement().satisfies(v ->
                        assertThat(v).containsEntry("message", "不在 allowlist 內")));
    }

    // ── 錯誤分流 ─────────────────────────────────────────────────────────────

    @Test
    void aBridgeServerErrorIsAnUpstreamFailureWithItsStatusAndReason() {
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withStatus(
                org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":500,\"reason\":\"spawn_failed\"}"));
        assertThatThrownBy(() -> adapter.sddCompile("/spec")).isInstanceOfSatisfying(UpstreamException.Failure.class,
                e -> {
                    assertThat(e.reason()).isEqualTo("引擎橋接服務錯誤");
                    assertThat(e.details()).containsEntry("bridgeStatus", 500).containsEntry("bridgeReason",
                            "spawn_failed");
                });
    }

    @Test
    void aBridgeServerErrorWithAnUnparsableBodyStillReportsTheStatus() {
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withStatus(
                org.springframework.http.HttpStatus.BAD_GATEWAY).body("<html>proxy error</html>"));
        assertThatThrownBy(() -> adapter.sddCompile("/spec")).isInstanceOfSatisfying(UpstreamException.Failure.class,
                e -> assertThat(e.details()).containsEntry("bridgeStatus", 502).doesNotContainKey("bridgeReason"));
    }

    @Test
    void aSuccessBodyThatIsNotJsonIsAnUpstreamFailureNotAnException500() {
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withSuccess("not json", MediaType.TEXT_PLAIN));
        assertThatThrownBy(() -> adapter.sddCompile("/spec")).isInstanceOf(UpstreamException.Failure.class);
    }

    @Test
    void connectionFailuresAreUnavailableAndReadTimeoutsAreTimedOut() {
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withException(new ConnectException("refused")));
        assertThatThrownBy(() -> adapter.sddCompile("/spec")).isInstanceOf(UpstreamException.Unavailable.class)
                .hasMessageNotContaining("bridge.test");
        server.reset();
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withException(new SocketTimeoutException("slow")));
        assertThatThrownBy(() -> adapter.sddCompile("/spec")).isInstanceOf(UpstreamException.TimedOut.class);
        server.reset();
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(
                withException(new java.io.IOException("something else")));
        assertThatThrownBy(() -> adapter.sddCompile("/spec")).isInstanceOf(UpstreamException.Unavailable.class);
    }

    // ── health ───────────────────────────────────────────────────────────────

    @Test
    void healthIsOkOnTwoHundredAndDownOtherwiseWithoutThrowing() {
        server.expect(requestTo(BASE + "/health")).andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess("{\"status\":\"ok\"}", MediaType.APPLICATION_JSON));
        assertThat(adapter.health()).isEqualTo(new BridgeHealth(true, 200));
        server.reset();
        server.expect(requestTo(BASE + "/health")).andRespond(withStatus(
                org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE));
        assertThat(adapter.health()).isEqualTo(new BridgeHealth(false, 503));
        server.reset();
        server.expect(requestTo(BASE + "/health")).andRespond(withException(new ConnectException("down")));
        assertThat(adapter.health()).isEqualTo(new BridgeHealth(false, 0));
    }

    @Test
    void healthUsesTheConfiguredHealthCheckPath() {
        settings.values.put("autoclaude.healthCheckPath", "/autoclaude/health");
        server.expect(requestTo(BASE + "/autoclaude/health")).andRespond(withSuccess());
        assertThat(adapter.health().ok()).isTrue();
        server.verify();
    }

    // ── 位址解析 ─────────────────────────────────────────────────────────────

    @Test
    void anAdminCustomizedEngineUrlWinsOverTheEnvironmentDefaultAndEachPrefixUsesItsOwnSetting() {
        settings.customized.put("autoclaude.engineUrl", "http://custom-bridge:9000/");
        settings.customized.put("sdd.engineUrl", "http://sdd-bridge:9100");
        BridgeEndpoints endpoints = new BridgeEndpoints(settings, new BridgeProperties(BASE));
        assertThat(endpoints.autoclaudeBase()).isEqualTo("http://custom-bridge:9000");
        assertThat(endpoints.sddBase()).isEqualTo("http://sdd-bridge:9100");
    }

    @Test
    void withoutACustomizedSettingTheEnvironmentValueIsUsedAndTheLocalDefaultIsTheLastResort() {
        assertThat(new BridgeEndpoints(settings, new BridgeProperties("http://engine-bridge:8081/")).autoclaudeBase())
                .isEqualTo("http://engine-bridge:8081");
        assertThat(new BridgeEndpoints(settings, new BridgeProperties("")).sddBase())
                .isEqualTo("http://localhost:8081");
        assertThat(new BridgeEndpoints(settings, new BridgeProperties(null)).healthPath()).isEqualTo("/health");
        settings.values.put("autoclaude.healthCheckPath", "custom/health");
        assertThat(new BridgeEndpoints(settings, new BridgeProperties(null)).healthPath()).isEqualTo("/custom/health");
    }
}
