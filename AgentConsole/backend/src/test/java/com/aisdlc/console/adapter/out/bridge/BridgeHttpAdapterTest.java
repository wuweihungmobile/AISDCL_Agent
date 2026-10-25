package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeHealth;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.DecomposeRequest;
import com.aisdlc.console.application.port.out.AgentBridge.DecomposeResult;
import com.aisdlc.console.application.port.out.AgentBridge.SddCompileResult;
import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.engine.SddFsmList;
import com.aisdlc.console.domain.model.engine.SddFsmState;
import com.aisdlc.console.domain.model.engine.SddProjectEntry;
import com.aisdlc.console.domain.model.engine.SddVersion;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.ExpectedCount;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
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
    /** 每個 Bridge 呼叫向請求工廠要求的（連線逾時，讀取逾時），依呼叫順序（契約 §3.1 呼叫總表的逾時欄）。 */
    private final List<Duration[]> requestedTimeouts = new ArrayList<>();
    private MockRestServiceServer server;
    private BridgeHttpAdapter adapter;

    @BeforeEach
    void setUp() {
        RestClient.Builder builder = RestClient.builder();
        server = MockRestServiceServer.bindTo(builder).build();
        // 回 null＝沿用 Builder 自己的（被 MockRestServiceServer 接手的）請求工廠；順便記下每次要求的逾時
        adapter = new BridgeHttpAdapter(builder, new BridgeEndpoints(settings, new BridgeProperties(BASE, null, null)),
                (connect, read) -> {
                    requestedTimeouts.add(new Duration[] {connect, read});
                    return null;
                });
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
        SddCompileResult result = adapter.sddCompile("C:\\work\\proj", null, null);
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
        assertThatThrownBy(() -> adapter.sddCompile("/spec", null, null)).isInstanceOfSatisfying(BridgeRejectedException.class,
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
        assertThatThrownBy(() -> adapter.sddCompile("/etc", null, null)).isInstanceOfSatisfying(BridgeRejectedException.class,
                e -> assertThat(e.violations()).singleElement().satisfies(v ->
                        assertThat(v).containsEntry("message", "不在 allowlist 內")));
    }

    // ── 錯誤分流 ─────────────────────────────────────────────────────────────

    @Test
    void aBridgeServerErrorIsAnUpstreamFailureWithItsStatusAndReason() {
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withStatus(
                org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":500,\"reason\":\"spawn_failed\"}"));
        assertThatThrownBy(() -> adapter.sddCompile("/spec", null, null)).isInstanceOfSatisfying(UpstreamException.Failure.class,
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
        assertThatThrownBy(() -> adapter.sddCompile("/spec", null, null)).isInstanceOfSatisfying(UpstreamException.Failure.class,
                e -> assertThat(e.details()).containsEntry("bridgeStatus", 502).doesNotContainKey("bridgeReason"));
    }

    @Test
    void aSuccessBodyThatIsNotJsonIsAnUpstreamFailureNotAnException500() {
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withSuccess("not json", MediaType.TEXT_PLAIN));
        assertThatThrownBy(() -> adapter.sddCompile("/spec", null, null)).isInstanceOf(UpstreamException.Failure.class);
    }

    @Test
    void connectionFailuresAreUnavailableAndReadTimeoutsAreTimedOut() {
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withException(new ConnectException("refused")));
        assertThatThrownBy(() -> adapter.sddCompile("/spec", null, null)).isInstanceOf(UpstreamException.Unavailable.class)
                .hasMessageNotContaining("bridge.test");
        server.reset();
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withException(new SocketTimeoutException("slow")));
        assertThatThrownBy(() -> adapter.sddCompile("/spec", null, null)).isInstanceOf(UpstreamException.TimedOut.class);
        server.reset();
        server.expect(requestTo(BASE + "/sdd/compile")).andRespond(
                withException(new java.io.IOException("something else")));
        assertThatThrownBy(() -> adapter.sddCompile("/spec", null, null)).isInstanceOf(UpstreamException.Unavailable.class);
    }

    // ── health ───────────────────────────────────────────────────────────────

    @Test
    void healthIsOkOnTwoHundredAndDownOtherwiseWithoutThrowing() {
        server.expect(requestTo(BASE + "/health/deep")).andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess("{\"status\":\"ok\"}", MediaType.APPLICATION_JSON));
        assertThat(adapter.health()).isEqualTo(new BridgeHealth(true, 200));
        server.reset();
        server.expect(requestTo(BASE + "/health/deep")).andRespond(withStatus(
                org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE));
        assertThat(adapter.health()).isEqualTo(new BridgeHealth(false, 503));
        server.reset();
        server.expect(requestTo(BASE + "/health/deep")).andRespond(withException(new ConnectException("down")));
        assertThat(adapter.health()).isEqualTo(new BridgeHealth(false, 0));
    }

    @Test
    void healthUsesTheConfiguredHealthCheckPath() {
        settings.values.put("autoclaude.healthCheckPath", "/autoclaude/health");
        server.expect(requestTo(BASE + "/autoclaude/health")).andRespond(withSuccess());
        assertThat(adapter.health().ok()).isTrue();
        server.verify();
    }

    // ── D-17：探測改打深度探針（契約 §3.1、§3.1.1）──────────────────────────────────────────────
    // 為什麼重要：淺層 /health 在引擎壞了時照回 200，頂列燈與 Agent 可用率因此永遠說謊；深度探針在引擎自檢未通過時回 503，
    // 探測環必須把它算成失敗。但 sdd 檢查只當資訊——它失敗時 Bridge 仍回 200，探測環不可以因為本文裡的 sdd.ok=false 就判失敗。

    @Test
    void theDefaultProbeIsDeepAndTheShallowOneStaysReachable() {
        server.expect(requestTo(BASE + "/health/deep")).andRespond(withSuccess());
        assertThat(adapter.health().ok()).isTrue();
        server.verify();
        server.reset();

        settings.values.put("autoclaude.healthCheckPath", "/health");
        server.expect(requestTo(BASE + "/health")).andRespond(withSuccess("{\"status\":\"ok\"}",
                MediaType.APPLICATION_JSON));
        assertThat(adapter.health()).as("管理員把路徑改回 /health＝只檢查行程是否存活").isEqualTo(new BridgeHealth(true, 200));
        server.verify();
    }

    @Test
    void aDegradedDeepProbeWithADetailedBodyIsAFailureAndTheBodyIsNotRead() {
        server.expect(requestTo(BASE + "/health/deep")).andRespond(withStatus(
                org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE).contentType(MediaType.APPLICATION_JSON)
                .body("{\"status\":\"degraded\",\"reason\":\"git: 找不到 git 執行檔\",\"checks\":{\"git\":"
                        + "{\"ok\":false,\"reason\":\"找不到 git 執行檔\"}}}"));
        assertThat(adapter.health()).isEqualTo(new BridgeHealth(false, 503));
    }

    @Test
    void aDeepProbeWithFailedSddCheckIsStillASuccess() {
        server.expect(requestTo(BASE + "/health/deep")).andRespond(withSuccess("""
                {"status":"ok","checks":{"git":{"ok":true,"version":"git version 2.39.5"},"autoclaude":{"ok":true},
                 "workspace":{"ok":true},"db":{"ok":null},
                 "sdd":{"ok":false,"latest":null,"reason":"SDD_ROOT 不是目錄：sdd"}}}
                """, MediaType.APPLICATION_JSON));
        assertThat(adapter.health()).as("與 AutoClaude 批次無關的 SDD 目錄問題不拉低可用率（主控裁決 Q4）")
                .isEqualTo(new BridgeHealth(true, 200));
    }

    @Test
    void everyOtherNonTwoHundredAnswerOfTheProbeIsAFailureToo() {
        for (org.springframework.http.HttpStatus status : List.of(org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR,
                org.springframework.http.HttpStatus.BAD_GATEWAY, org.springframework.http.HttpStatus.NOT_FOUND)) {
            server.reset();
            server.expect(requestTo(BASE + "/health/deep")).andRespond(withStatus(status));
            assertThat(adapter.health()).as(status.toString()).isEqualTo(new BridgeHealth(false, status.value()));
        }
    }

    @Test
    void theProbeAllowsEightSecondsToReadAndTheEngineStatusCallsThree() {
        server.expect(requestTo(BASE + "/health/deep")).andRespond(withSuccess());
        server.expect(requestTo(BASE + "/sdd/version")).andRespond(withSuccess(
                "{\"latest\":\"AISDLC_SDD_v9.99\",\"root\":\"/sdd\"}", MediaType.APPLICATION_JSON));

        adapter.health();
        adapter.sddVersion();

        assertThat(requestedTimeouts).hasSize(2);
        assertThat(requestedTimeouts.get(0)).as("健康探測：連線 2 秒、讀取 8 秒（v1.4；git --version 自己最多等 5 秒）")
                .containsExactly(Duration.ofSeconds(2), Duration.ofSeconds(8));
        assertThat(requestedTimeouts.get(1)).as("引擎狀態查詢：連線 2 秒、讀取 3 秒")
                .containsExactly(Duration.ofSeconds(2), Duration.ofSeconds(3));
    }

    // ── D-16：AISDLC_SDD 唯讀查詢（契約 §3.1 三列、§3.1.3）──────────────────────────────────────────
    // 為什麼重要：這三個呼叫是 Console 對 FSM 狀態的唯一消費點。Bridge 的 snake_case 本文要轉成 camelCase 而巢狀內容一字不動
    // （NFR-OBS-01：FSM 檔 ↔ API ↔ 畫面逐值比對）；錯誤要分得出「專案層級」（404／422）與「引擎層級」（503／連線／逾時）；
    // 而且不重試——前端 30 秒輪詢一次，重試只會讓一個壞掉的 Bridge 被打三倍。

    private static final String FSM_BODY = """
            {"project":"e2e-alpha","current_state":"IMPLEMENTATION","current_sprint":2,"session_id":"sid-alpha",
             "updated_at":"2026-10-16T01:02:03+00:00","frozen_stages":[{"stage":"SCG-0"}],
             "decision_trace":[{"ts":"t3","from":"A","to":"B","reason":"r3","spec_refs":["S3"],"agents_consulted":[],"trigger":"auto"},
                               {"ts":"t4","from":"B","to":"C","reason":"r4","spec_refs":[],"agents_consulted":["sa"],"trigger":"auto"}],
             "source":"FSM-STATE-e2e-alpha.yaml",
             "human_pending":{"count":1,"items":[{"entered_at":"2026-10-15T08:00:00+00:00","reminder_hours":72}]},
             "retry_history":{"count":3,"last":{"gate":"PR_REVIEW","attempt":1,"date":"2026-10-16T00:30:00+00:00"}},
             "rtm_coverage":null}
            """;

    @Test
    void sddVersionReadsTheLatestDirectoryAndItsRoot() {
        server.expect(requestTo(BASE + "/sdd/version")).andExpect(method(HttpMethod.GET)).andRespond(withSuccess(
                "{\"latest\":\"AISDLC_SDD_v0.30\",\"root\":\"/sdd/AISDLC_SDD_v0.30\"}", MediaType.APPLICATION_JSON));

        SddVersion version = adapter.sddVersion();

        assertThat(version).isEqualTo(new SddVersion("AISDLC_SDD_v0.30", "/sdd/AISDLC_SDD_v0.30"));
    }

    @Test
    void sddFsmListKeepsTheBridgeOrderAndTheNullsAndCollectsTheUnreadableNames() {
        server.expect(requestTo(BASE + "/sdd/fsm")).andRespond(withSuccess("""
                {"root":"AISDLC_SDD_v0.30","projects":[
                   {"project":"AISDLC_SDD","source":"FSM-STATE-AISDLC_SDD.yaml","current_state":"INIT","updated_at":"2026-07-15T17:36:40+00:00"},
                   {"project":"zulu","source":"FSM-STATE-zulu.yaml","current_state":null,"updated_at":null}],
                 "errors":["FSM-STATE-broken.yaml","FSM-STATE-bad name.yaml"]}
                """, MediaType.APPLICATION_JSON));

        SddFsmList list = adapter.sddFsmList(null);

        assertThat(list.root()).isEqualTo("AISDLC_SDD_v0.30");
        assertThat(list.projects()).containsExactly(
                new SddProjectEntry("AISDLC_SDD", "FSM-STATE-AISDLC_SDD.yaml", "INIT", "2026-07-15T17:36:40+00:00"),
                new SddProjectEntry("zulu", "FSM-STATE-zulu.yaml", null, null));
        assertThat(list.errors()).containsExactly("FSM-STATE-broken.yaml", "FSM-STATE-bad name.yaml");
    }

    @Test
    void anEmptyFsmDirectoryIsAnEmptyListAndNotAnError() {
        server.expect(requestTo(BASE + "/sdd/fsm")).andRespond(withSuccess(
                "{\"root\":\"AISDLC_SDD_v0.30\",\"projects\":[],\"errors\":[]}", MediaType.APPLICATION_JSON));

        SddFsmList list = adapter.sddFsmList(null);

        assertThat(list.projects()).isEmpty();
        assertThat(list.errors()).isEmpty();
    }

    @Test
    void sddFsmMapsTheTopLevelKeysToCamelCaseAndLeavesTheNestedContentUntouched() {
        server.expect(requestTo(BASE + "/sdd/fsm/e2e-alpha")).andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess(FSM_BODY, MediaType.APPLICATION_JSON));

        SddFsmState state = adapter.sddFsm("e2e-alpha", null);

        assertThat(state.project()).isEqualTo("e2e-alpha");
        assertThat(state.currentState()).isEqualTo("IMPLEMENTATION");
        assertThat(state.currentSprint()).isEqualTo(2);
        assertThat(state.sessionId()).isEqualTo("sid-alpha");
        assertThat(state.updatedAt()).as("原樣的字串，不轉型").isEqualTo("2026-10-16T01:02:03+00:00");
        assertThat(state.source()).isEqualTo("FSM-STATE-e2e-alpha.yaml");
        assertThat(state.frozenStages()).containsExactly(Map.of("stage", "SCG-0"));
        assertThat(state.decisionTrace()).hasSize(2);
        assertThat(state.decisionTrace().get(0)).as("巢狀內容保留 snake_case 鍵")
                .containsEntry("spec_refs", List.of("S3")).containsEntry("agents_consulted", List.of())
                .containsEntry("reason", "r3");
        assertThat(state.humanPending().count()).isEqualTo(1);
        assertThat(state.humanPending().items()).singleElement().satisfies(item -> assertThat(item)
                .containsEntry("entered_at", "2026-10-15T08:00:00+00:00").containsEntry("reminder_hours", 72));
        assertThat(state.retryHistory().count()).isEqualTo(3);
        assertThat(state.retryHistory().last()).containsEntry("gate", "PR_REVIEW").containsEntry("attempt", 1);
        assertThat(state.rtmCoverage()).as("現行 FSM-STATE 沒有 RTM 覆蓋數值：恆為 null").isNull();
    }

    @Test
    void sddFsmKeepsOnlyTheLastFiveDecisionsEvenIfABridgeSendsMore() {
        StringBuilder trace = new StringBuilder();
        for (int i = 1; i <= 7; i++) {
            trace.append(i > 1 ? "," : "").append("{\"reason\":\"r").append(i).append("\"}");
        }
        server.expect(requestTo(BASE + "/sdd/fsm/long")).andRespond(withSuccess(
                "{\"project\":\"long\",\"decision_trace\":[" + trace + "]}", MediaType.APPLICATION_JSON));

        SddFsmState state = adapter.sddFsm("long", null);

        assertThat(state.decisionTrace()).extracting(entry -> entry.get("reason"))
                .containsExactly("r3", "r4", "r5", "r6", "r7");
    }

    @Test
    void sddFsmFillsInTheNameAndPassesRtmCoverageThrough() {
        server.expect(requestTo(BASE + "/sdd/fsm/bare")).andRespond(withSuccess(
                "{\"source\":\"FSM-STATE-bare.yaml\",\"rtm_coverage\":{\"percent\":87.5}}", MediaType.APPLICATION_JSON));

        SddFsmState state = adapter.sddFsm("bare", null);

        assertThat(state.project()).isEqualTo("bare");
        assertThat(state.frozenStages()).isEmpty();
        assertThat(state.decisionTrace()).isEmpty();
        assertThat(state.humanPending().count()).isZero();
        assertThat(state.retryHistory().count()).isZero();
        assertThat(state.retryHistory().last()).isNull();
        assertThat(state.rtmCoverage()).isEqualTo(Map.of("percent", 87.5));
    }

    @Test
    void aMissingFsmFileAndAnUnreadableOneAreRejectionsWithTheirBridgeReasons() {
        server.expect(requestTo(BASE + "/sdd/fsm/nope")).andRespond(withStatus(
                org.springframework.http.HttpStatus.NOT_FOUND).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":404,\"reason\":\"fsm_not_found\",\"project\":\"nope\"}"));
        assertThatThrownBy(() -> adapter.sddFsm("nope", null)).isInstanceOfSatisfying(BridgeRejectedException.class, e -> {
            assertThat(e.status()).isEqualTo(404);
            assertThat(e.reason()).isEqualTo("fsm_not_found");
        });
        server.reset();
        server.expect(requestTo(BASE + "/sdd/fsm/broken")).andRespond(withStatus(
                org.springframework.http.HttpStatus.UNPROCESSABLE_CONTENT).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":422,\"reason\":\"fsm_state_unreadable\",\"detail\":\"while scanning a simple key\"}"));
        assertThatThrownBy(() -> adapter.sddFsm("broken", null)).isInstanceOfSatisfying(BridgeRejectedException.class, e -> {
            assertThat(e.status()).isEqualTo(422);
            assertThat(e.reason()).isEqualTo("fsm_state_unreadable");
            assertThat(e.detail()).isEqualTo("while scanning a simple key");
        });
    }

    @Test
    void anInvalidSddRootIsAnUpstreamFailureThatCarriesTheBridgeStatusAndReason() {
        for (String path : List.of("/sdd/version", "/sdd/fsm", "/sdd/fsm/alpha")) {
            server.reset();
            server.expect(requestTo(BASE + path)).andRespond(withStatus(
                    org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE).contentType(MediaType.APPLICATION_JSON)
                    .body("{\"code\":503,\"reason\":\"sdd_unavailable\",\"detail\":\"找不到 AISDLC_SDD 目錄\"}"));
            Runnable call = switch (path) {
                case "/sdd/version" -> adapter::sddVersion;
                case "/sdd/fsm" -> () -> adapter.sddFsmList(null);
                default -> () -> adapter.sddFsm("alpha", null);
            };
            assertThatThrownBy(call::run).as(path).isInstanceOfSatisfying(UpstreamException.Failure.class,
                    e -> assertThat(e.details()).containsEntry("bridgeStatus", 503)
                            .containsEntry("bridgeReason", "sdd_unavailable"));
        }
    }

    @Test
    void aTwoHundredBodyOfTheWrongShapeIsAnUpstreamFailureNotAnException() {
        server.expect(requestTo(BASE + "/sdd/version")).andRespond(withSuccess("{\"unexpected\":true}",
                MediaType.APPLICATION_JSON));
        assertThatThrownBy(() -> adapter.sddVersion()).isInstanceOf(UpstreamException.Failure.class);
        server.reset();
        server.expect(requestTo(BASE + "/sdd/fsm")).andRespond(withSuccess("{\"root\":\"x\"}",
                MediaType.APPLICATION_JSON));
        assertThatThrownBy(() -> adapter.sddFsmList(null)).as("沒有 projects 陣列").isInstanceOf(UpstreamException.Failure.class);
        server.reset();
        server.expect(requestTo(BASE + "/sdd/fsm")).andRespond(withSuccess(
                "{\"root\":\"x\",\"projects\":[{\"source\":\"FSM-STATE-a.yaml\"}]}", MediaType.APPLICATION_JSON));
        assertThatThrownBy(() -> adapter.sddFsmList(null)).as("清單項沒有專案名：不猜").isInstanceOf(UpstreamException.Failure.class);
        server.reset();
        server.expect(requestTo(BASE + "/sdd/fsm/x")).andRespond(withSuccess("not json", MediaType.TEXT_PLAIN));
        assertThatThrownBy(() -> adapter.sddFsm("x", null)).isInstanceOf(UpstreamException.Failure.class);
    }

    @Test
    void connectionFailuresAndReadTimeoutsOfTheEngineStatusCallsAreNeverRetried() {
        server.expect(requestTo(BASE + "/sdd/version")).andRespond(withException(new ConnectException("down")));
        assertThatThrownBy(() -> adapter.sddVersion()).isInstanceOf(UpstreamException.Unavailable.class);
        server.verify();
        server.reset();
        // MockRestServiceServer 的期望是「恰好一次」：若有重試，第二個請求會因「沒有後續期望」而炸出 AssertionError，而不是 TimedOut
        server.expect(requestTo(BASE + "/sdd/fsm")).andRespond(withException(new SocketTimeoutException("slow")));
        assertThatThrownBy(() -> adapter.sddFsmList(null)).isInstanceOf(UpstreamException.TimedOut.class);
        server.verify();
        server.reset();
        server.expect(requestTo(BASE + "/sdd/fsm/alpha")).andRespond(withException(new ConnectException("down")));
        assertThatThrownBy(() -> adapter.sddFsm("alpha", null)).isInstanceOf(UpstreamException.Unavailable.class);
        server.verify();
    }

    @Test
    void theSddCallsFollowTheSddEngineUrlSetting() {
        settings.customized.put("sdd.engineUrl", "http://sdd-bridge:9100");
        settings.customized.put("autoclaude.engineUrl", "http://autoclaude-bridge:9200");
        server.expect(requestTo("http://sdd-bridge:9100/sdd/version")).andRespond(withSuccess(
                "{\"latest\":\"AISDLC_SDD_v9.99\",\"root\":\"/sdd\"}", MediaType.APPLICATION_JSON));

        adapter.sddVersion();

        server.verify();
    }

    // ── X-Trace-Id（契約 §0.4 第 6 點，C-12；NFR-9.4-04）──────────────────────────────
    // 為什麼重要：同一次使用者操作在 console-api 日誌、Bridge 日誌與前端錯誤封包上的 traceId 要能用同一個值串起來；
    // 任何一種呼叫（POST、GET、健康探測各走各的建構路徑）漏帶標頭，那一段就斷線了。

    private static final Pattern UUID_FORMAT = Pattern.compile(
            "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}");

    @AfterEach
    void clearTheMdc() {
        MDC.remove("traceId");
    }

    @Test
    void postGetAndHealthCallsAllCarryTheTraceIdOfTheCallingThread() {
        MDC.put("traceId", "trace-from-the-request");
        String runId = "4c6a2a58-4e1d-4b29-9d3e-6a1b5c8d9e02";
        server.expect(requestTo(BASE + "/autoclaude/decompose")).andExpect(header("X-Trace-Id", "trace-from-the-request"))
                .andRespond(withSuccess("{\"draft_id\":\"d\",\"playbook\":{\"tasks\":[]}}", MediaType.APPLICATION_JSON));
        server.expect(requestTo(BASE + "/autoclaude/decompose/d:approve"))
                .andExpect(header("X-Trace-Id", "trace-from-the-request"))
                .andRespond(withSuccess("{\"signed_off\":true}", MediaType.APPLICATION_JSON));
        server.expect(requestTo(BASE + "/sdd/compile")).andExpect(header("X-Trace-Id", "trace-from-the-request"))
                .andRespond(withSuccess("{\"tasks\":[]}", MediaType.APPLICATION_JSON));
        server.expect(requestTo(BASE + "/health/deep")).andExpect(header("X-Trace-Id", "trace-from-the-request"))
                .andRespond(withSuccess());
        server.expect(requestTo(BASE + "/autoclaude/runs/" + runId))
                .andExpect(header("X-Trace-Id", "trace-from-the-request"))
                .andRespond(withSuccess("{\"run_id\":\"" + runId + "\",\"status\":\"RUNNING\"}",
                        MediaType.APPLICATION_JSON));
        // v1.4：引擎狀態的三個唯讀查詢同樣帶標頭（契約 §0.4 第 6 點：console-api 對 Bridge 的每一個請求都帶）
        server.expect(requestTo(BASE + "/sdd/version")).andExpect(header("X-Trace-Id", "trace-from-the-request"))
                .andRespond(withSuccess("{\"latest\":\"AISDLC_SDD_v9.99\",\"root\":\"/sdd\"}",
                        MediaType.APPLICATION_JSON));
        server.expect(requestTo(BASE + "/sdd/fsm")).andExpect(header("X-Trace-Id", "trace-from-the-request"))
                .andRespond(withSuccess("{\"root\":\"AISDLC_SDD_v9.99\",\"projects\":[],\"errors\":[]}",
                        MediaType.APPLICATION_JSON));
        server.expect(requestTo(BASE + "/sdd/fsm/alpha")).andExpect(header("X-Trace-Id", "trace-from-the-request"))
                .andRespond(withSuccess("{\"project\":\"alpha\",\"source\":\"FSM-STATE-alpha.yaml\"}",
                        MediaType.APPLICATION_JSON));

        adapter.decompose(new DecomposeRequest("g", "", "p", 24, null), Duration.ofSeconds(30));
        adapter.approveDraft("d", "Alice");
        adapter.sddCompile("/spec", null, null);
        adapter.health();
        adapter.getRun(UUID.fromString(runId));
        adapter.sddVersion();
        adapter.sddFsmList(null);
        adapter.sddFsm("alpha", null);

        server.verify();
    }

    @Test
    void withoutATraceContextEachCallGetsItsOwnFreshUuid() {
        List<String> seen = new ArrayList<>();
        server.expect(ExpectedCount.times(3), requestTo(BASE + "/health/deep")).andExpect(request -> seen.add(
                request.getHeaders().getFirst("X-Trace-Id"))).andRespond(withSuccess());

        adapter.health();
        adapter.health();
        adapter.health();

        assertThat(seen).hasSize(3).allSatisfy(id -> assertThat(id).matches(UUID_FORMAT));
        assertThat(seen).as("背景工作（探測環）每次探測各自新產一個").doesNotHaveDuplicates();
    }

    @Test
    void aBlankTraceIdInTheMdcIsTreatedAsMissing() {
        MDC.put("traceId", "   ");
        List<String> seen = new ArrayList<>();
        server.expect(requestTo(BASE + "/health/deep")).andExpect(request -> seen.add(
                request.getHeaders().getFirst("X-Trace-Id"))).andRespond(withSuccess());

        adapter.health();

        assertThat(seen).singleElement().satisfies(id -> assertThat(id).matches(UUID_FORMAT));
    }

    @Test
    void theRetriesOfOneGetCallAllCarryTheSameGeneratedTraceId() {
        UUID runId = UUID.randomUUID();
        List<String> seen = new ArrayList<>();
        server.expect(ExpectedCount.times(3), requestTo(BASE + "/autoclaude/runs/" + runId)).andExpect(request -> seen.add(
                request.getHeaders().getFirst("X-Trace-Id"))).andRespond(withException(new ConnectException("down")));

        assertThatThrownBy(() -> adapter.getRun(runId)).isInstanceOf(UpstreamException.Unavailable.class);

        assertThat(seen).as("連線失敗重試 2 次＝共 3 次嘗試").hasSize(3).containsOnly(seen.get(0));
        assertThat(seen.get(0)).matches(UUID_FORMAT);
    }

    // ── 位址解析 ─────────────────────────────────────────────────────────────

    @Test
    void anAdminCustomizedEngineUrlWinsOverTheEnvironmentDefaultAndEachPrefixUsesItsOwnSetting() {
        settings.customized.put("autoclaude.engineUrl", "http://custom-bridge:9000/");
        settings.customized.put("sdd.engineUrl", "http://sdd-bridge:9100");
        BridgeEndpoints endpoints = new BridgeEndpoints(settings, new BridgeProperties(BASE, null, null));
        assertThat(endpoints.autoclaudeBase()).isEqualTo("http://custom-bridge:9000");
        assertThat(endpoints.sddBase()).isEqualTo("http://sdd-bridge:9100");
    }

    @Test
    void withoutACustomizedSettingTheEnvironmentValueIsUsedAndTheLocalDefaultIsTheLastResort() {
        assertThat(new BridgeEndpoints(settings, new BridgeProperties("http://engine-bridge:8081/", null, null)).autoclaudeBase())
                .isEqualTo("http://engine-bridge:8081");
        assertThat(new BridgeEndpoints(settings, new BridgeProperties("", null, null)).sddBase())
                .isEqualTo("http://localhost:8081");
        assertThat(new BridgeEndpoints(settings, new BridgeProperties(null, null, null)).healthPath())
                .as("設定缺席時的兜底：v1.4 起是深度探針").isEqualTo("/health/deep");
        settings.values.put("autoclaude.healthCheckPath", "custom/health");
        assertThat(new BridgeEndpoints(settings, new BridgeProperties(null, null, null)).healthPath()).isEqualTo("/custom/health");
    }
}
