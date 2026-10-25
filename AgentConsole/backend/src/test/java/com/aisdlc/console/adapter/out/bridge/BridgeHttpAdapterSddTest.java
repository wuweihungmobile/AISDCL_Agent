package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.RunStarted;
import com.aisdlc.console.application.port.out.AgentBridge.SddBlock;
import com.aisdlc.console.application.port.out.AgentBridge.SddCompileResult;
import com.aisdlc.console.application.port.out.AgentBridge.SddFreeze;
import com.aisdlc.console.application.port.out.AgentBridge.StartRunRequest;
import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.engine.SddFsmState;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.ExecutionRtm;
import com.aisdlc.console.domain.model.execution.ExecutionWarning;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.mock.http.client.MockClientHttpRequest;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.test.web.client.RequestMatcher;
import org.springframework.web.client.RestClient;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.headerDoesNotExist;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

/**
 * v1.5 新增的 Bridge 呼叫（契約 §3.1 呼叫總表、§3.1.4、§3.1.6；ADR-XPLAT-016 §9）：核准凍結、帶 {@code sdd} 區塊的建立批次、
 * resume／restore 的權杖、RTM 讀取、{@code root} 查詢、{@code /sdd/compile} 的新欄位。以 {@code MockRestServiceServer} 驗「送出的請求」。
 * 為什麼重要：權杖只准出現在那四個會寫 FSM 的呼叫上（多一個地方就是外洩面，少一個地方 Bridge 就 403）；沒設權杖時 console-api
 * 必須在本地就停手而不是去敲 Bridge；Bridge 的 {@code extra=forbid} 讓請求多一個鍵就整個被拒；逾時照呼叫總表（freeze 40 秒、帶 sdd 的建立 90 秒）。
 */
class BridgeHttpAdapterSddTest {

    private static final String BASE = "http://bridge.test:8081";
    private static final String TOKEN = "mock-bridge-sdd-write-token-for-tests-0123456789";
    private static final String RUN = "4c6a2a58-4e1d-4b29-9d3e-6a1b5c8d9e02";
    private static final String CHECKPOINT = "0b0f3b5e-87b7-4a37-9a3e-0d8a3b5f7c11";
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final SddFreeze FREEZE = new SddFreeze("/work/p", null, List.of("docs/a.md"), "operator", "核准", null);

    /** 一個接上 {@code MockRestServiceServer} 的介面卡，與它被要求的（連線，讀取）逾時。 */
    private static final class Rig {
        final MockRestServiceServer server;
        final BridgeHttpAdapter adapter;
        final List<Duration[]> timeouts = new ArrayList<>();

        Rig(String token) {
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
            adapter = new BridgeHttpAdapter(builder, new BridgeEndpoints(settings, new BridgeProperties(BASE, token, null)),
                    (connect, read) -> {
                        timeouts.add(new Duration[] {connect, read});
                        return null;
                    });
        }

        Duration lastRead() {
            return timeouts.get(timeouts.size() - 1)[1];
        }
    }

    private final Rig withToken = new Rig(TOKEN);
    private final Rig withoutToken = new Rig(null);

    /** 請求本文（或它的 {@code nested} 子物件）的鍵集合恰為 {@code keys}：「多一個鍵 Bridge 就拒絕」的機械檢查。 */
    private static RequestMatcher keysAt(String nested, String... keys) {
        return request -> {
            Map<String, Object> body = JSON.readValue(((MockClientHttpRequest) request).getBodyAsString(),
                    new TypeReference<Map<String, Object>>() { });
            @SuppressWarnings("unchecked")
            Map<String, Object> node = nested == null ? body : (Map<String, Object>) body.get(nested);
            assertThat(node).containsOnlyKeys(keys);
        };
    }

    private static RequestMatcher bodyKeys(String... keys) {
        return keysAt(null, keys);
    }

    private static final String FROZEN = """
            {"project":"e2e-bravo","current_state":"SPEC_FROZEN","current_sprint":1,"session_id":"sid-b",
             "updated_at":"2026-10-17T01:02:03+00:00","frozen_stages":[{"stage":"Stage-1","approved_by":"operator"}],
             "decision_trace":[],"source":"FSM-STATE-e2e-bravo.yaml","human_pending":{"count":0,"items":[]},
             "retry_history":{"count":0,"last":null},"rtm_coverage":null,
             "phase":{"name":"FROZEN","order":4,"blocking":false,"observation":false},
             "escalation_history":[],"escalation_provenance":null,"fsm_project":"e2e-bravo",
             "stage":"Stage-1","spec_doc_digests":{"docs/a.md":"sha256:1"}}
            """;

    private static final String CREATED = """
            {"run_id":"%s","status":"RUNNING","pid":4242,"workspace":"w","bridge_instance":"bridge-1"}
            """.formatted(RUN);

    // ── 核准凍結 ────────────────────────────────────────────────────────────────

    @Test
    void freezePostsTheColonPathWithTheTokenAndOnlyTheDocumentedKeys() {
        withToken.server.expect(requestTo(BASE + "/sdd/fsm/e2e-bravo:freeze")).andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Bridge-Token", TOKEN))
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(bodyKeys("root", "stage", "docs", "approver", "reason", "expected_digests"))
                .andExpect(jsonPath("$.root").value("/work/e2e-bravo"))
                .andExpect(jsonPath("$.stage").value("Stage-1"))
                .andExpect(jsonPath("$.docs[0]").value("docs/a.md"))
                .andExpect(jsonPath("$.approver").value("operator"))
                .andExpect(jsonPath("$.reason").value("規格已核准"))
                .andExpect(jsonPath("$.expected_digests['docs/a.md']").value("sha256:1"))
                .andRespond(withSuccess(FROZEN, MediaType.APPLICATION_JSON));

        SddFsmState state = withToken.adapter.sddFreeze("e2e-bravo", new SddFreeze("/work/e2e-bravo", "Stage-1",
                List.of("docs/a.md"), "operator", "規格已核准", Map.of("docs/a.md", "sha256:1")));

        withToken.server.verify();
        assertThat(state.currentState()).isEqualTo("SPEC_FROZEN");
        assertThat(state.fsmProject()).isEqualTo("e2e-bravo");
        assertThat(state.phase()).isEqualTo(new SddFsmState.Phase("FROZEN", 4, false, false));
        assertThat(state.frozenStages()).singleElement().satisfies(stage -> assertThat(stage)
                .containsEntry("approved_by", "operator"));
        assertThat(withToken.lastRead()).as("核准凍結：讀取逾時 40 秒（契約 §3.1）").isEqualTo(Duration.ofSeconds(40));
    }

    @Test
    void freezeOmitsTheStageAndTheDigestsWhenTheyAreBlankOrEmpty() {
        for (SddFreeze request : List.of(
                new SddFreeze("/work/p", " ", List.of("docs/a.md"), "operator", "核准", Map.of()),
                new SddFreeze("/work/p", null, List.of("docs/a.md"), "operator", "核准", null))) {
            withToken.server.reset();
            withToken.server.expect(requestTo(BASE + "/sdd/fsm/p:freeze"))
                    .andExpect(bodyKeys("root", "docs", "approver", "reason"))
                    .andRespond(withSuccess(FROZEN, MediaType.APPLICATION_JSON));

            withToken.adapter.sddFreeze("p", request);

            withToken.server.verify();
        }
    }

    @Test
    void freezeEncodesTheProjectNameAsOneStrictlyEncodedPathSegment() {
        withToken.server.expect(requestTo(BASE + "/sdd/fsm/x%2Fy%20z%20%E5%B0%88:freeze"))
                .andRespond(withSuccess(FROZEN, MediaType.APPLICATION_JSON));

        withToken.adapter.sddFreeze("x/y z 專", FREEZE);

        withToken.server.verify();
    }

    @Test
    void freezeWithoutALocalTokenIs503AndSendsNothing() {
        assertThatThrownBy(() -> withoutToken.adapter.sddFreeze("p", FREEZE))
                .isInstanceOfSatisfying(ServiceUnavailableException.class,
                        e -> assertThat(e.reason()).isEqualTo(ErrorReasons.SDD_WRITE_DISABLED));

        withoutToken.server.verify();
        assertThat(withoutToken.timeouts).as("連請求都沒建立").isEmpty();
    }

    @Test
    void aBridgeSideTokenRefusalIsARejectionButAnotherOutageIsAFailure() {
        withToken.server.expect(requestTo(BASE + "/sdd/fsm/p:freeze")).andRespond(withStatus(
                HttpStatus.SERVICE_UNAVAILABLE).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":503,\"reason\":\"sdd_write_disabled\"}"));
        assertThatThrownBy(() -> withToken.adapter.sddFreeze("p", FREEZE)).as("503 sdd_write_disabled：明確拒絕")
                .isInstanceOfSatisfying(BridgeRejectedException.class, e -> {
                    assertThat(e.status()).isEqualTo(503);
                    assertThat(e.reason()).isEqualTo("sdd_write_disabled");
                });

        withToken.server.reset();
        withToken.server.expect(requestTo(BASE + "/sdd/fsm/p:freeze")).andRespond(withStatus(HttpStatus.FORBIDDEN)
                .contentType(MediaType.APPLICATION_JSON).body("{\"code\":403,\"reason\":\"sdd_write_forbidden\"}"));
        assertThatThrownBy(() -> withToken.adapter.sddFreeze("p", FREEZE)).as("403 sdd_write_forbidden：明確拒絕")
                .isInstanceOfSatisfying(BridgeRejectedException.class, e -> {
                    assertThat(e.status()).isEqualTo(403);
                    assertThat(e.reason()).isEqualTo("sdd_write_forbidden");
                });

        withToken.server.reset();
        withToken.server.expect(requestTo(BASE + "/sdd/fsm/p:freeze")).andRespond(withStatus(
                HttpStatus.SERVICE_UNAVAILABLE).contentType(MediaType.APPLICATION_JSON)
                .body("{\"code\":503,\"reason\":\"sdd_unavailable\"}"));
        assertThatThrownBy(() -> withToken.adapter.sddFreeze("p", FREEZE)).as("其他的 503 是故障")
                .isInstanceOfSatisfying(UpstreamException.Failure.class,
                        e -> assertThat(e.details()).containsEntry("bridgeStatus", 503)
                                .containsEntry("bridgeReason", "sdd_unavailable"));
    }

    // ── 建立批次（帶 sdd 區塊才需要權杖）──────────────────────────────────────────────

    private static StartRunRequest run(SddBlock sdd) {
        return new StartRunRequest(UUID.fromString(RUN), "demo", "/work/demo",
                Map.of("version", "1.0", "project", "demo", "tasks", List.of()), Map.of(), Map.of(), false, sdd);
    }

    @Test
    void aSddRunSendsTheBlockTheTokenAndWaitsNinetySeconds() {
        withToken.server.expect(requestTo(BASE + "/autoclaude/runs")).andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Bridge-Token", TOKEN))
                .andExpect(bodyKeys("run_id", "project", "execution_path", "playbook", "config_overrides", "env",
                        "fresh", "sdd"))
                .andExpect(keysAt("sdd", "spec_dir", "spec_file", "fsm_project", "root", "approver"))
                .andExpect(jsonPath("$.sdd.spec_dir").value("/work/demo/docs"))
                .andExpect(jsonPath("$.sdd.spec_file").value("/work/demo/docs/TCS-A.md"))
                .andExpect(jsonPath("$.sdd.fsm_project").value("Demo 專案"))
                .andExpect(jsonPath("$.sdd.root").value("/work/demo"))
                .andExpect(jsonPath("$.sdd.approver").value("operator"))
                .andRespond(withStatus(HttpStatus.CREATED).contentType(MediaType.APPLICATION_JSON).body(CREATED));

        RunStarted started = withToken.adapter.startRun(run(new SddBlock("/work/demo/docs",
                "/work/demo/docs/TCS-A.md", "Demo 專案", "/work/demo", "operator")));

        withToken.server.verify();
        assertThat(started.status()).isEqualTo(BridgeStatus.RUNNING);
        assertThat(started.warnings()).isEmpty();
        assertThat(withToken.lastRead()).as("含最多三次 FSM CLI 子行程：90 秒").isEqualTo(Duration.ofSeconds(90));
    }

    @Test
    void anOrdinaryRunHasNoSddKeyNoTokenAndWaitsThirtySeconds() {
        withToken.server.expect(requestTo(BASE + "/autoclaude/runs")).andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andExpect(bodyKeys("run_id", "project", "execution_path", "playbook", "config_overrides", "env",
                        "fresh"))
                .andRespond(withStatus(HttpStatus.CREATED).contentType(MediaType.APPLICATION_JSON).body(CREATED));

        RunStarted started = withToken.adapter.startRun(run(null));

        withToken.server.verify();
        assertThat(started.warnings()).isEmpty();
        assertThat(withToken.lastRead()).as("一般批次維持 30 秒").isEqualTo(Duration.ofSeconds(30));
    }

    @Test
    void theSpecFileKeyIsLeftOutOfTheSddBlockWhenThereIsNone() {
        for (String specFile : new String[] {null, " "}) {
            withToken.server.reset();
            withToken.server.expect(requestTo(BASE + "/autoclaude/runs"))
                    .andExpect(keysAt("sdd", "spec_dir", "fsm_project", "root", "approver"))
                    .andRespond(withStatus(HttpStatus.CREATED).contentType(MediaType.APPLICATION_JSON).body(CREATED));

            withToken.adapter.startRun(run(new SddBlock("/work/demo/docs", specFile, "demo", "/work/demo", "operator")));

            withToken.server.verify();
        }
    }

    @Test
    void aSddRunWithoutALocalTokenIs503AndSendsNothing() {
        assertThatThrownBy(() -> withoutToken.adapter.startRun(run(new SddBlock("/d", "/d/f.md", "demo", "/r", "a"))))
                .isInstanceOfSatisfying(ServiceUnavailableException.class,
                        e -> assertThat(e.reason()).isEqualTo(ErrorReasons.SDD_WRITE_DISABLED));

        withoutToken.server.verify();
        assertThat(withoutToken.timeouts).isEmpty();
    }

    @Test
    void theBridgeWarningsOfA201AreParsedAndOddShapesAreSkipped() {
        withToken.server.expect(requestTo(BASE + "/autoclaude/runs")).andRespond(withStatus(HttpStatus.CREATED)
                .contentType(MediaType.APPLICATION_JSON).body("""
                        {"run_id":"%s","status":"RUNNING","warnings":[
                          {"code":"sdd_frozen_digest_absent","detail":"舊狀態檔：凍結時沒有記錄內容摘要"},
                          {"detail":"沒有 code 的項目"},"字串項目"]}
                        """.formatted(RUN)));

        RunStarted started = withToken.adapter.startRun(run(new SddBlock("/d", "/d/f.md", "demo", "/r", "a")));

        assertThat(started.warnings()).containsExactly(
                new ExecutionWarning("sdd_frozen_digest_absent", null, "舊狀態檔：凍結時沒有記錄內容摘要"));
    }

    // ── resume／restore 附權杖、pause／stop 從不附 ─────────────────────────────────────

    @Test
    void resumeAndRestoreCarryTheTokenWhilePauseAndStopNeverDo() {
        UUID id = UUID.fromString(RUN);
        String path = BASE + "/autoclaude/runs/" + RUN;
        withToken.server.expect(requestTo(path + ":pause")).andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withStatus(HttpStatus.ACCEPTED).contentType(MediaType.APPLICATION_JSON)
                        .body("{\"status\":\"PAUSING\"}"));
        withToken.server.expect(requestTo(path + ":resume")).andExpect(header("X-Bridge-Token", TOKEN))
                .andRespond(withStatus(HttpStatus.ACCEPTED).contentType(MediaType.APPLICATION_JSON)
                        .body("{\"status\":\"RUNNING\"}"));
        withToken.server.expect(requestTo(path + ":stop")).andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withStatus(HttpStatus.ACCEPTED).contentType(MediaType.APPLICATION_JSON)
                        .body("{\"status\":\"CANCELLING\"}"));
        withToken.server.expect(requestTo(path + "/restore")).andExpect(header("X-Bridge-Token", TOKEN))
                .andExpect(jsonPath("$.checkpoint_id").value(CHECKPOINT))
                .andExpect(jsonPath("$.env.MOCK").value("1"))
                .andRespond(withStatus(HttpStatus.ACCEPTED).contentType(MediaType.APPLICATION_JSON)
                        .body("{\"status\":\"RUNNING\"}"));

        assertThat(withToken.adapter.pauseRun(id)).isEqualTo(BridgeStatus.PAUSING);
        assertThat(withToken.adapter.resumeRun(id, Map.of())).isEqualTo(BridgeStatus.RUNNING);
        assertThat(withToken.adapter.stopRun(id)).isEqualTo(BridgeStatus.CANCELLING);
        withToken.adapter.restoreRun(id, UUID.fromString(CHECKPOINT), Map.of("MOCK", "1"));

        withToken.server.verify();
        assertThat(withToken.timeouts).extracting(t -> t[1]).as("pause 5／resume 30／stop 10／restore 30 秒")
                .containsExactly(Duration.ofSeconds(5), Duration.ofSeconds(30), Duration.ofSeconds(10),
                        Duration.ofSeconds(30));
    }

    @Test
    void withoutALocalTokenResumeAndRestoreSendNoHeaderButWork() {
        UUID id = UUID.fromString(RUN);
        String path = BASE + "/autoclaude/runs/" + RUN;
        withoutToken.server.expect(requestTo(path + ":resume")).andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withStatus(HttpStatus.ACCEPTED).contentType(MediaType.APPLICATION_JSON)
                        .body("{\"status\":\"RUNNING\"}"));
        withoutToken.server.expect(requestTo(path + "/restore")).andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withStatus(HttpStatus.ACCEPTED).contentType(MediaType.APPLICATION_JSON)
                        .body("{\"status\":\"RUNNING\"}"));

        assertThat(withoutToken.adapter.resumeRun(id, Map.of())).isEqualTo(BridgeStatus.RUNNING);
        withoutToken.adapter.restoreRun(id, UUID.fromString(CHECKPOINT), Map.of());

        withoutToken.server.verify();
    }

    // ── RTM ────────────────────────────────────────────────────────────────────

    @Test
    void rtmReadsTheReportWithoutATokenInThreeSeconds() {
        withToken.server.expect(requestTo(BASE + "/autoclaude/runs/" + RUN + "/rtm")).andExpect(method(HttpMethod.GET))
                .andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withSuccess("""
                        {"scenario":"購物車","spec_digest":"sha256:abc","at":{"passed":3,"total":4,"unmapped":1,"pct":75.0},
                         "ac":{"covered":1,"total":2,"pct":50.0},"failed_at_ids":["AT-002"],"weak_regex_at_ids":["AT-001"],
                         "unmapped_at_ids":["AT-009"],"fully_covered":false,"advisory":true}
                        """, MediaType.APPLICATION_JSON));

        ExecutionRtm rtm = withToken.adapter.getRunRtm(UUID.fromString(RUN));

        withToken.server.verify();
        assertThat(rtm).isEqualTo(new ExecutionRtm("購物車", "sha256:abc", new ExecutionRtm.At(3, 4, 1, 75.0),
                new ExecutionRtm.Ac(1, 2, 50.0), List.of("AT-002"), List.of("AT-001"), List.of("AT-009"), false));
        assertThat(rtm.advisory()).as("Console 自己恆為 true，不依賴 Bridge 的欄位").isTrue();
        assertThat(withToken.timeouts.get(0)).containsExactly(Duration.ofSeconds(2), Duration.ofSeconds(3));
    }

    @Test
    void anOldRtmReportGetsZeroesAndEmptyListsInsteadOfFailing() {
        withToken.server.expect(requestTo(BASE + "/autoclaude/runs/" + RUN + "/rtm")).andRespond(withSuccess("""
                {"scenario":"s","at":{"passed":1,"total":2,"pct":50.0},"ac":{"covered":0,"total":0,"pct":0.0}}
                """, MediaType.APPLICATION_JSON));

        ExecutionRtm old = withToken.adapter.getRunRtm(UUID.fromString(RUN));

        assertThat(old.at()).isEqualTo(new ExecutionRtm.At(1, 2, 0, 50.0));
        assertThat(old.specDigest()).isEmpty();
        assertThat(old.unmappedAtIds()).as("舊報告缺欄為空").isEmpty();
        assertThat(old.failedAtIds()).isEmpty();
        assertThat(old.weakRegexAtIds()).isEmpty();
        assertThat(old.fullyCovered()).isFalse();

        withToken.server.reset();
        withToken.server.expect(requestTo(BASE + "/autoclaude/runs/" + RUN + "/rtm")).andRespond(withSuccess("{}",
                MediaType.APPLICATION_JSON));
        ExecutionRtm empty = withToken.adapter.getRunRtm(UUID.fromString(RUN));
        assertThat(empty.scenario()).isEmpty();
        assertThat(empty.at()).isEqualTo(new ExecutionRtm.At(0, 0, 0, 0.0));
        assertThat(empty.ac()).isEqualTo(new ExecutionRtm.Ac(0, 0, 0.0));
    }

    @Test
    void rtmRefusalsAreRejectionsAndOutagesAreNeverRetried() {
        String url = BASE + "/autoclaude/runs/" + RUN + "/rtm";
        withToken.server.expect(requestTo(url)).andRespond(withStatus(HttpStatus.NOT_FOUND)
                .contentType(MediaType.APPLICATION_JSON).body("{\"code\":404,\"reason\":\"rtm_not_found\"}"));
        assertThatThrownBy(() -> withToken.adapter.getRunRtm(UUID.fromString(RUN)))
                .isInstanceOfSatisfying(BridgeRejectedException.class, e -> {
                    assertThat(e.status()).isEqualTo(404);
                    assertThat(e.reason()).isEqualTo("rtm_not_found");
                });

        withToken.server.reset();
        withToken.server.expect(requestTo(url)).andRespond(withStatus(HttpStatus.UNPROCESSABLE_CONTENT)
                .contentType(MediaType.APPLICATION_JSON).body("{\"code\":422,\"reason\":\"rtm_unreadable\"}"));
        assertThatThrownBy(() -> withToken.adapter.getRunRtm(UUID.fromString(RUN)))
                .isInstanceOfSatisfying(BridgeRejectedException.class,
                        e -> assertThat(e.reason()).isEqualTo("rtm_unreadable"));

        // MockRestServiceServer 的期望是「恰好一次」：若有重試，第二個請求會因沒有後續期望而炸出 AssertionError，而不是 Unavailable／TimedOut
        withToken.server.reset();
        withToken.server.expect(requestTo(url)).andRespond(withException(new ConnectException("down")));
        assertThatThrownBy(() -> withToken.adapter.getRunRtm(UUID.fromString(RUN)))
                .isInstanceOf(UpstreamException.Unavailable.class);
        withToken.server.verify();

        withToken.server.reset();
        withToken.server.expect(requestTo(url)).andRespond(withException(new SocketTimeoutException("slow")));
        assertThatThrownBy(() -> withToken.adapter.getRunRtm(UUID.fromString(RUN)))
                .isInstanceOf(UpstreamException.TimedOut.class);
        withToken.server.verify();
    }

    // ── 唯讀 FSM 查詢：root 與 v1.5 欄位 ─────────────────────────────────────────────

    @Test
    void theRootGoesInAStrictlyEncodedQueryOfBothFsmReads() {
        withToken.server.expect(requestTo(BASE + "/sdd/fsm/a%20b?root=%2Fwork%2Fmy%20proj"))
                .andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withSuccess("{\"project\":\"a b\",\"current_state\":\"INIT\"}", MediaType.APPLICATION_JSON));

        assertThat(withToken.adapter.sddFsm("a b", "/work/my proj").project()).isEqualTo("a b");
        withToken.server.verify();

        withToken.server.reset();
        withToken.server.expect(requestTo(BASE + "/sdd/fsm?root=%2Fwork%2Fp"))
                .andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withSuccess("{\"root\":\"x\",\"projects\":[],\"errors\":[]}", MediaType.APPLICATION_JSON));

        assertThat(withToken.adapter.sddFsmList("/work/p").projects()).isEmpty();
        withToken.server.verify();
    }

    @Test
    void v15FsmFieldsAreMappedAndAnOldBridgeGetsDefaults() {
        StringBuilder history = new StringBuilder();
        for (int i = 1; i <= 7; i++) {
            history.append(i > 1 ? "," : "").append("{\"n\":").append(i).append('}');
        }
        withToken.server.expect(requestTo(BASE + "/sdd/fsm/p")).andRespond(withSuccess("""
                {"project":"P 原名","current_state":"ESCALATION","phase":{"name":"BLOCKED","order":0,"blocking":true,"observation":false},
                 "escalation_history":[%s],"escalation_provenance":{"from_state":"IMPLEMENTATION","note":"x"},
                 "fsm_project":"P_原名",
                 "recovery":{"target":"IMPLEMENTATION","powershell":"Push-Location ...","posix":"cd ..."}}
                """.formatted(history), MediaType.APPLICATION_JSON));

        SddFsmState state = withToken.adapter.sddFsm("p", null);

        assertThat(state.phase()).isEqualTo(new SddFsmState.Phase("BLOCKED", 0, true, false));
        assertThat(state.escalationHistory()).as("尾 5 筆，舊→新").extracting(e -> e.get("n"))
                .containsExactly(3, 4, 5, 6, 7);
        assertThat(state.escalationProvenance()).containsEntry("from_state", "IMPLEMENTATION").containsEntry("note", "x");
        assertThat(state.fsmProject()).as("標準鍵與檔內原名不同").isEqualTo("P_原名");
        assertThat(state.project()).isEqualTo("P 原名");
        assertThat(state.recovery()).isEqualTo(new SddFsmState.Recovery("IMPLEMENTATION", "Push-Location ...", "cd ..."));

        withToken.server.reset();
        withToken.server.expect(requestTo(BASE + "/sdd/fsm/p")).andRespond(withSuccess(
                "{\"project\":\"p\",\"current_state\":\"INIT\"}", MediaType.APPLICATION_JSON));
        SddFsmState old = withToken.adapter.sddFsm("p", null);
        assertThat(old.phase()).isNull();
        assertThat(old.escalationHistory()).isEmpty();
        assertThat(old.escalationProvenance()).isNull();
        assertThat(old.fsmProject()).isNull();
        assertThat(old.recovery()).isNull();
    }

    @Test
    void aMalformedPhaseOrRecoveryIsDroppedNotGuessed() {
        withToken.server.expect(requestTo(BASE + "/sdd/fsm/p")).andRespond(withSuccess("""
                {"project":"p","phase":{"name":"FROZEN"},"recovery":{"target":"X","powershell":"p"},
                 "escalation_provenance":"text"}
                """, MediaType.APPLICATION_JSON));
        SddFsmState partial = withToken.adapter.sddFsm("p", null);
        assertThat(partial.phase()).as("缺 order").isNull();
        assertThat(partial.recovery()).as("缺 posix").isNull();
        assertThat(partial.escalationProvenance()).as("不是映射").isNull();

        withToken.server.reset();
        withToken.server.expect(requestTo(BASE + "/sdd/fsm/p")).andRespond(withSuccess(
                "{\"project\":\"p\",\"phase\":\"FROZEN\",\"recovery\":\"cd\"}", MediaType.APPLICATION_JSON));
        SddFsmState scalar = withToken.adapter.sddFsm("p", null);
        assertThat(scalar.phase()).isNull();
        assertThat(scalar.recovery()).isNull();
    }

    // ── /sdd/compile 的 v1.5 欄位 ────────────────────────────────────────────────

    @Test
    void compileSendsSpecFileAndFsmProjectOnlyWhenTheyAreGiven() {
        withToken.server.expect(requestTo(BASE + "/sdd/compile")).andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andExpect(bodyKeys("spec_dir", "spec_file", "fsm_project"))
                .andExpect(jsonPath("$.spec_file").value("TCS-A.md"))
                .andExpect(jsonPath("$.fsm_project").value("Demo 專案"))
                .andRespond(withSuccess("{\"tasks\":[]}", MediaType.APPLICATION_JSON));
        withToken.adapter.sddCompile("/work/demo/docs", "TCS-A.md", "Demo 專案");
        withToken.server.verify();

        withToken.server.reset();
        withToken.server.expect(requestTo(BASE + "/sdd/compile")).andExpect(bodyKeys("spec_dir"))
                .andRespond(withSuccess("{\"tasks\":[]}", MediaType.APPLICATION_JSON));
        withToken.adapter.sddCompile("/work/demo/docs", " ", "");
        withToken.server.verify();
    }

    @Test
    void compileParsesTheV15FieldsAndToleratesTheirAbsence() {
        withToken.server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withSuccess("""
                {"scenario":"購物車","spec_path":"/work/demo/docs/TCS-A.md","digest":"sha256:abc","spec_file":"TCS-A.md",
                 "fsm_project":"Demo_專案","frozen_digest":"verified","spec_format_version":"2",
                 "unmapped_at_ids":["AT-009"],
                 "warnings":[{"code":"state_dir_not_ignored","detail":"build/reports/fsm 未被 .gitignore"},{"detail":"沒有 code"}],
                 "tasks":[{"step_id":"sdd-a-at-001-1-1","name":"加入商品","prompt":"實作","max_retries":5,
                           "maintain_context":true,"spec_digest":"sha256:abc","weak_regex":false}]}
                """, MediaType.APPLICATION_JSON));

        SddCompileResult result = withToken.adapter.sddCompile("/work/demo/docs", null, null);

        assertThat(result.specFile()).isEqualTo("TCS-A.md");
        assertThat(result.fsmProject()).isEqualTo("Demo_專案");
        assertThat(result.frozenDigest()).isEqualTo("verified");
        assertThat(result.specFormatVersion()).isEqualTo("2");
        assertThat(result.unmappedAtIds()).containsExactly("AT-009");
        assertThat(result.warnings()).singleElement().satisfies(w -> {
            assertThat(w.code()).isEqualTo("state_dir_not_ignored");
            assertThat(w.detail()).contains(".gitignore");
        });
        assertThat(result.tasks()).singleElement().satisfies(t -> {
            assertThat(t.maxRetries()).isEqualTo(5);
            assertThat(t.maintainContext()).isTrue();
            assertThat(t.specDigest()).isEqualTo("sha256:abc");
        });

        withToken.server.reset();
        withToken.server.expect(requestTo(BASE + "/sdd/compile")).andRespond(withSuccess(
                "{\"scenario\":\"s\",\"tasks\":[{\"step_id\":\"C1\",\"name\":\"n\",\"prompt\":\"p\"}]}",
                MediaType.APPLICATION_JSON));
        SddCompileResult old = withToken.adapter.sddCompile("/work/demo/docs", null, null);
        assertThat(old.specFile()).isNull();
        assertThat(old.fsmProject()).isNull();
        assertThat(old.frozenDigest()).isNull();
        assertThat(old.unmappedAtIds()).isEmpty();
        assertThat(old.warnings()).isEmpty();
        assertThat(old.tasks().get(0).maxRetries()).isNull();
        assertThat(old.tasks().get(0).maintainContext()).isNull();
        assertThat(old.tasks().get(0).specDigest()).isNull();
    }
}
