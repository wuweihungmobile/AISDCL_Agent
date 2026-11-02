package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.ResearchBridge.ResearchFsm;
import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ResearchBridgeException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.test.web.client.ResponseCreator;
import org.springframework.test.web.client.response.DefaultResponseCreator;
import org.springframework.web.client.RestClient;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.ConnectException;
import java.net.SocketException;
import java.net.SocketTimeoutException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.catchThrowable;
import static org.hamcrest.Matchers.emptyOrNullString;
import static org.hamcrest.Matchers.not;
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
 * 研究面的 Bridge 呼叫（TCS-ResearchToPRD-P0 AT-960-5-E-1；契約 §0.2 第 8 列、§2），以 {@code MockRestServiceServer} 驗「送出的請求」與「各種回應拋出的例外」。
 * 為什麼重要：研究寫入是非冪等的（建立會配 {@code rp_no}、核准會凍結基線）——重試一次就是兩個專案、兩次凍結；權杖標頭漏了，Bridge 一律 403 而使用者看不出為什麼；
 * 而 console-api 的服務層全押在例外型別上對映狀態碼：連線被拒若被當成讀取逾時，使用者以為「請求可能已生效」而不敢重送；讀取逾時若被當成連線被拒，則會誤導重送而重複寫入。
 */
class BridgeHttpAdapterResearchTest {

    private static final String BASE = "http://bridge.test:8081";
    private static final String TOKEN = "research-write-token-for-tests-0123456789-abcdef";
    private static final UUID ID = UUID.fromString("a1000000-0000-4000-8000-000000000001");

    /** 一個接上 {@code MockRestServiceServer} 的介面卡，與它被要求的（連線，讀取）逾時。 */
    private static final class Rig {
        final MockRestServiceServer server;
        final BridgeHttpAdapter adapter;
        final List<Duration[]> timeouts = new ArrayList<>();

        Rig(String researchToken) {
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
            adapter = new BridgeHttpAdapter(builder, new BridgeEndpoints(settings, new BridgeProperties(BASE, null, null, researchToken)), (connect, read) -> {
                timeouts.add(new Duration[] {connect, read});
                return null;
            });
        }
    }

    private final Rig rig = new Rig(TOKEN);

    private static DefaultResponseCreator jsonStatus(HttpStatus status, String body) {
        return withStatus(status).contentType(MediaType.APPLICATION_JSON).body(body);
    }

    private static Map<String, Object> body(Object... keyValues) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            out.put((String) keyValues[i], keyValues[i + 1]);
        }
        return out;
    }

    // ── 請求形態 ─────────────────────────────────────────────────────────────────────────

    @Test
    void AT_960_5_E_1_everyWriteCarriesTheTokenAndTheTraceHeaderAndPostsTheBodyVerbatimWithoutRetry() {
        rig.server.expect(requestTo(BASE + "/research/projects")).andExpect(method(HttpMethod.POST)).andExpect(header("X-Bridge-Token", TOKEN))
                .andExpect(header("X-Trace-Id", not(emptyOrNullString()))).andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.slug").value("demo")).andExpect(jsonPath("$.created_by").value("alice"))
                .andRespond(jsonStatus(HttpStatus.CREATED, "{\"research_id\":\"" + ID + "\",\"rp_no\":\"RP-0001\"}"));
        rig.server.expect(requestTo(BASE + "/research/projects/" + ID + "/stages/draft:start")).andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Bridge-Token", TOKEN)).andExpect(header("X-Trace-Id", not(emptyOrNullString())))
                .andExpect(jsonPath("$.requested_by").value("alice")).andExpect(jsonPath("$.after_escalation").value(false))
                .andRespond(jsonStatus(HttpStatus.ACCEPTED, "{\"stage_run_id\":\"s1\",\"flow\":{\"phase\":\"DRAFTING\",\"status\":\"RUNNING\"}}"));
        rig.server.expect(requestTo(BASE + "/research/projects/" + ID + "/prd")).andExpect(method(HttpMethod.PUT)).andExpect(header("X-Bridge-Token", TOKEN))
                .andExpect(jsonPath("$.base_version").value(2)).andExpect(jsonPath("$.author").value("alice"))
                .andRespond(jsonStatus(HttpStatus.CREATED, "{\"version_no\":3,\"semver\":\"v0.3.0-draft\"}"));
        rig.server.expect(requestTo(BASE + "/research/projects/" + ID + ":approve-baseline")).andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Bridge-Token", TOKEN)).andExpect(jsonPath("$.approver").value("alice")).andExpect(jsonPath("$.prd_version").value(3))
                .andRespond(withSuccess("{\"gate_decision_id\":\"g1\",\"stage\":\"Gate-0\"}", MediaType.APPLICATION_JSON));
        rig.server.expect(requestTo(BASE + "/research/projects/" + ID + ":return")).andExpect(method(HttpMethod.POST)).andExpect(header("X-Bridge-Token", TOKEN))
                .andExpect(jsonPath("$.approver").value("alice")).andExpect(jsonPath("$.reason").value("缺證據"))
                .andRespond(withSuccess("{\"gate_decision_id\":\"g2\",\"fsm_retry_count\":1,\"escalated\":false}", MediaType.APPLICATION_JSON));

        Map<String, Object> created = rig.adapter.createProject(body("research_id", ID.toString(), "slug", "demo", "created_by", "alice"));
        Map<String, Object> started = rig.adapter.startStage(ID, "draft", body("requested_by", "alice", "after_escalation", false));
        Map<String, Object> saved = rig.adapter.savePrd(ID, body("base_version", 2, "content", "# PRD", "author", "alice"));
        Map<String, Object> approved = rig.adapter.approve(ID, body("prd_version", 3, "approver", "alice"));
        Map<String, Object> returned = rig.adapter.returnPrd(ID, body("approver", "alice", "reason", "缺證據"));

        rig.server.verify();
        assertThat(created).containsEntry("rp_no", "RP-0001");
        assertThat(started).containsEntry("stage_run_id", "s1");
        assertThat(saved).containsEntry("version_no", 3);
        assertThat(approved).containsEntry("gate_decision_id", "g1");
        assertThat(returned).containsEntry("fsm_retry_count", 1);
        assertThat(rig.timeouts).as("寫入：連線 2 秒、讀取 30 秒").hasSize(5).allSatisfy(pair -> {
            assertThat(pair[0]).isEqualTo(Duration.ofSeconds(2));
            assertThat(pair[1]).isEqualTo(Duration.ofSeconds(30));
        });
    }

    @Test
    void AT_960_5_E_1_theOtherWritesUseTheDocumentedPathsAndTheIdIsEncodedAsOneStrictPathSegment() {
        for (String verb : List.of("cancel", "reconcile", "archive", "restore", "reinit")) {
            rig.server.expect(requestTo(BASE + "/research/projects/" + ID + ":" + verb)).andExpect(method(HttpMethod.POST))
                    .andExpect(header("X-Bridge-Token", TOKEN)).andRespond(withSuccess("{\"ok\":true}", MediaType.APPLICATION_JSON));
        }
        rig.server.expect(requestTo(BASE + "/research/allowlist")).andExpect(method(HttpMethod.POST)).andExpect(header("X-Bridge-Token", TOKEN))
                .andRespond(jsonStatus(HttpStatus.CREATED, "{\"id\":\"e1\"}"));
        rig.server.expect(requestTo(BASE + "/research/allowlist/a%20b%2F%E5%B0%88%E6%A1%88")).andExpect(method(HttpMethod.PATCH))
                .andExpect(header("X-Bridge-Token", TOKEN)).andRespond(withSuccess("{\"id\":\"e1\"}", MediaType.APPLICATION_JSON));
        rig.server.expect(requestTo(BASE + "/research/allowlist/%2E%2E")).andExpect(method(HttpMethod.PATCH)).andRespond(withSuccess("{}", MediaType.APPLICATION_JSON));

        for (String verb : List.of("cancel", "reconcile", "archive", "restore")) {
            assertThat(rig.adapter.action(ID, verb, body())).containsEntry("ok", true);
        }
        assertThat(rig.adapter.reinit(ID, body())).containsEntry("ok", true);
        assertThat(rig.adapter.addAllowlistEntry(body("host", "example.org"))).containsEntry("id", "e1");
        assertThat(rig.adapter.patchAllowlistEntry("a b/專案", body("enabled", false))).containsEntry("id", "e1");
        rig.adapter.patchAllowlistEntry("..", body("enabled", true));

        rig.server.verify();
    }

    @Test
    void AT_960_5_E_1_anUnknownActionVerbIsRefusedBeforeAnyRequestBecauseTheVerbGoesStraightIntoTheUrl() {
        assertThatThrownBy(() -> rig.adapter.action(ID, "approve-baseline/../x", body())).isInstanceOf(IllegalArgumentException.class);

        rig.server.verify();
        assertThat(rig.timeouts).isEmpty();
    }

    @Test
    void AT_960_5_E_1_theReadsCarryNoTokenAndUseTheirOwnTimeouts() {
        String capabilities = "{\"mode\":\"local\",\"db\":false,\"web_layer_enabled\":true}";
        rig.server.expect(requestTo(BASE + "/research/capabilities")).andExpect(method(HttpMethod.GET)).andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andExpect(header("X-Trace-Id", not(emptyOrNullString()))).andRespond(withSuccess(capabilities, MediaType.APPLICATION_JSON));
        rig.server.expect(requestTo(BASE + "/research/allowlist")).andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withSuccess("{\"items\":[{\"host\":\"a\"}],\"effective\":{}}", MediaType.APPLICATION_JSON));
        rig.server.expect(requestTo(BASE + "/research/allowlist")).andRespond(withSuccess("[{\"host\":\"b\"}]", MediaType.APPLICATION_JSON));
        rig.server.expect(request -> {
            assertThat(request.getURI().getPath()).isEqualTo("/sdd/fsm/research-demo-g2");
            assertThat(UriComponentsBuilder.fromUri(request.getURI()).build().getQueryParams().getFirst("root")).isEqualTo("%2Fresearch-root%2Fdemo%20x");
            assertThat(request.getHeaders().get("X-Bridge-Token")).isNull();
        }).andRespond(withSuccess("{\"project\":\"research-demo-g2\",\"current_state\":\"HUMAN_PENDING\",\"retry_history\":{\"count\":3,\"last\":null},"
                + "\"retry_gates\":{\"SCG_VALIDATION\":{\"current_count\":2,\"entries\":3},\"PR_REVIEW\":{\"current_count\":0}}}", MediaType.APPLICATION_JSON));

        assertThat(rig.adapter.writeEnabled()).isTrue();
        assertThat(rig.adapter.capabilities()).containsEntry("db", false).containsEntry("web_layer_enabled", true);
        assertThat(rig.adapter.allowlist().get("items")).asInstanceOf(org.assertj.core.api.InstanceOfAssertFactories.LIST).hasSize(1);
        assertThat(rig.adapter.allowlist().get("items")).as("裸陣列也包成 items").asInstanceOf(org.assertj.core.api.InstanceOfAssertFactories.LIST).hasSize(1);
        ResearchFsm fsm = rig.adapter.fsm("research-demo-g2", "/research-root/demo x");

        rig.server.verify();
        assertThat(fsm.state().currentState()).isEqualTo("HUMAN_PENDING");
        assertThat(fsm.state().retryHistory().count()).isEqualTo(3);
        assertThat(fsm.gates()).containsOnlyKeys("SCG_VALIDATION", "PR_REVIEW");
        assertThat(fsm.gates().get("SCG_VALIDATION").currentCount()).isEqualTo(2);
        assertThat(fsm.gates().get("SCG_VALIDATION").entries()).isEqualTo(3);
        assertThat(fsm.gates().get("PR_REVIEW").entries()).as("缺欄位補 0").isZero();
        assertThat(rig.timeouts).hasSize(4);
        assertThat(rig.timeouts.get(0)).containsExactly(Duration.ofSeconds(2), Duration.ofSeconds(10));
        assertThat(rig.timeouts.get(1)).containsExactly(Duration.ofSeconds(2), Duration.ofSeconds(10));
        assertThat(rig.timeouts.get(3)).containsExactly(Duration.ofSeconds(2), Duration.ofSeconds(3));
    }

    @Test
    void AT_960_5_E_1_aReadThatIsNotAJsonObjectIsAFailureAndAnEmptyFsmBodyIsToo() {
        rig.server.expect(requestTo(BASE + "/research/capabilities")).andRespond(withSuccess("[1,2]", MediaType.APPLICATION_JSON));
        rig.server.expect(requestTo(BASE + "/research/allowlist")).andRespond(withSuccess("\"nope\"", MediaType.APPLICATION_JSON));
        rig.server.expect(request -> { }).andRespond(withSuccess("{}", MediaType.APPLICATION_JSON));

        assertThat(catchThrowable(rig.adapter::capabilities)).isInstanceOf(UpstreamException.Failure.class);
        assertThat(catchThrowable(rig.adapter::allowlist)).isInstanceOf(UpstreamException.Failure.class);
        assertThat(catchThrowable(() -> rig.adapter.fsm("k", "/r"))).isInstanceOf(UpstreamException.Failure.class);

        rig.server.verify();
    }

    // ── 錯誤對映：每種失敗恰一次請求 ─────────────────────────────────────────────────────────

    private void expectOne(ResponseCreator answer) {
        rig.server.reset();
        rig.server.expect(requestTo(BASE + "/research/projects/" + ID + ":approve-baseline")).andRespond(answer);
    }

    @Test
    void AT_960_5_E_1_everyBridgeAnswerMapsToTheDocumentedExceptionWithExactlyOneRequest() {
        Map<String, ResponseCreator> answers = new LinkedHashMap<>();
        answers.put("200", withSuccess("{\"gate_decision_id\":\"g1\"}", MediaType.APPLICATION_JSON));
        answers.put("403", jsonStatus(HttpStatus.FORBIDDEN, "{\"code\":403,\"reason\":\"research_write_forbidden\"}"));
        answers.put("409", jsonStatus(HttpStatus.CONFLICT, "{\"code\":409,\"reason\":\"fsm_state_conflict\",\"details\":{\"current_state\":\"HUMAN_PENDING\",\"expected_state\":null}}"));
        answers.put("503 requires_db", jsonStatus(HttpStatus.SERVICE_UNAVAILABLE, "{\"code\":503,\"reason\":\"research_requires_db\"}"));
        answers.put("503 write_disabled", jsonStatus(HttpStatus.SERVICE_UNAVAILABLE, "{\"code\":503,\"reason\":\"research_write_disabled\",\"detail\":\"未設\"}"));
        answers.put("503 db_blocked", jsonStatus(HttpStatus.SERVICE_UNAVAILABLE, "{\"code\":503,\"reason\":\"db_blocked\"}"));
        answers.put("503 other", jsonStatus(HttpStatus.SERVICE_UNAVAILABLE, "{\"code\":503,\"reason\":\"something_else\"}"));
        answers.put("422", jsonStatus(HttpStatus.UNPROCESSABLE_CONTENT, "{\"code\":422,\"reason\":\"invalid_request\",\"violations\":[{\"field\":\"reason\",\"rule\":\"invalid_length\",\"message\":\"x\"}]}"));
        answers.put("501", jsonStatus(HttpStatus.NOT_IMPLEMENTED, "{\"code\":501,\"reason\":\"not_implemented\",\"endpoint\":\"approve-baseline\",\"detail\":\"尚未實作\"}"));
        answers.put("502 init_failed", jsonStatus(HttpStatus.BAD_GATEWAY, "{\"code\":502,\"reason\":\"init_failed\",\"details\":{\"step\":\"fsm\"}}"));
        answers.put("500", jsonStatus(HttpStatus.INTERNAL_SERVER_ERROR, "{\"code\":500,\"reason\":\"boom\"}"));
        answers.put("連線被拒", withException(new ConnectException("Connection refused")));
        answers.put("送出後連線被重設", withException(new SocketException("Connection reset")));
        answers.put("讀取逾時", withException(new SocketTimeoutException("Read timed out")));
        answers.put("200 非 JSON", withSuccess("approved, trust me", MediaType.TEXT_PLAIN));
        for (Map.Entry<String, ResponseCreator> entry : answers.entrySet()) {
            String label = entry.getKey();
            expectOne(entry.getValue());

            Throwable thrown = catchThrowable(() -> rig.adapter.approve(ID, body("prd_version", 3, "approver", "alice")));

            rig.server.verify();                    // 恰好一次請求：重試會在第二次請求時被 MockRestServiceServer 拒絕
            if ("200".equals(label)) {
                assertThat(thrown).as(label).isNull();
                continue;
            }
            assertThat(thrown).as(label).isNotNull();
            assertThat(String.valueOf(thrown.getMessage())).as("%s：權杖不出現在任何例外訊息", label).doesNotContain(TOKEN);
            assertMapped(label, thrown);
        }
        assertThat(rig.timeouts).as("每次呼叫的連線與讀取逾時").hasSize(answers.size()).allSatisfy(pair -> {
            assertThat(pair[0]).isEqualTo(Duration.ofSeconds(2));
            assertThat(pair[1]).isEqualTo(Duration.ofSeconds(30));
        });
    }

    private static void assertMapped(String label, Throwable thrown) {
        switch (label) {
            case "403" -> assertRejected(thrown, 403, "research_write_forbidden");
            case "409" -> {
                BridgeRejectedException rejected = assertRejected(thrown, 409, "fsm_state_conflict");
                assertThat(rejected.body()).as("details 逐字帶出（頂層的 null 值已剝掉，不會讓建構丟 NPE）").containsKey("details");
            }
            case "503 requires_db" -> assertRejected(thrown, 503, "research_requires_db");
            case "503 write_disabled" -> assertThat(assertRejected(thrown, 503, "research_write_disabled").detail()).isEqualTo("未設");
            case "503 db_blocked" -> assertRejected(thrown, 503, "db_blocked");
            case "503 other" -> assertThat(thrown).as(label).isInstanceOfSatisfying(UpstreamException.Failure.class,
                    failure -> assertThat(failure.details()).containsEntry("bridgeStatus", 503).containsEntry("bridgeReason", "something_else"));
            case "422" -> assertThat(assertRejected(thrown, 422, "invalid_request").violations()).singleElement()
                    .satisfies(v -> assertThat(v).containsEntry("rule", "invalid_length"));
            case "501" -> assertThat(thrown).as(label).isInstanceOfSatisfying(ResearchBridgeException.class, e -> {
                assertThat(e.kind()).isEqualTo(ResearchBridgeException.Kind.FAILURE);
                assertThat(e.reason()).isEqualTo(ErrorReasons.RESEARCH_NOT_IMPLEMENTED);
                assertThat(e.details()).containsEntry("bridgeStatus", 501).containsEntry("endpoint", "approve-baseline").containsEntry("detail", "尚未實作");
            });
            case "502 init_failed" -> assertThat(thrown).as(label).isInstanceOfSatisfying(ResearchBridgeException.class, e -> {
                assertThat(e.kind()).isEqualTo(ResearchBridgeException.Kind.FAILURE);
                assertThat(e.reason()).isEqualTo(ErrorReasons.RESEARCH_INIT_FAILED);
                assertThat(e.details()).containsEntry("bridgeStatus", 502).containsEntry("step", "fsm");
            });
            case "500" -> assertThat(thrown).as(label).isInstanceOfSatisfying(UpstreamException.Failure.class,
                    failure -> assertThat(failure.details()).containsEntry("bridgeStatus", 500));
            case "連線被拒" -> assertThat(thrown).as(label).isInstanceOfSatisfying(ResearchBridgeException.class, e -> {
                assertThat(e.kind()).isEqualTo(ResearchBridgeException.Kind.UNREACHABLE);
                assertThat(e.reason()).isEqualTo("bridge_unreachable");
                assertThat(e.deliveryUncertain()).as("連線階段：確定沒有送達").isFalse();
            });
            case "送出後連線被重設" -> assertThat(thrown).as(label).isInstanceOfSatisfying(ResearchBridgeException.class, e -> {
                assertThat(e.kind()).isEqualTo(ResearchBridgeException.Kind.UNREACHABLE);
                assertThat(e.reason()).isEqualTo("bridge_unreachable");
                assertThat(e.deliveryUncertain()).as("送出之後：結果不明").isTrue();
            });
            case "讀取逾時" -> assertThat(thrown).as(label).isInstanceOfSatisfying(ResearchBridgeException.class, e -> {
                assertThat(e.kind()).isEqualTo(ResearchBridgeException.Kind.TIMEOUT);
                assertThat(e.reason()).isEqualTo("bridge_timeout");
                assertThat(e.deliveryUncertain()).isTrue();
            });
            default -> assertThat(thrown).as("200 但本文不是 JSON 物件").isInstanceOfSatisfying(UpstreamException.Failure.class,
                    failure -> assertThat(failure.details()).containsEntry("bridgeStatus", 200));
        }
    }

    private static BridgeRejectedException assertRejected(Throwable thrown, int status, String reason) {
        assertThat(thrown).isInstanceOf(BridgeRejectedException.class);
        BridgeRejectedException rejected = (BridgeRejectedException) thrown;
        assertThat(rejected.status()).isEqualTo(status);
        assertThat(rejected.reason()).isEqualTo(reason);
        return rejected;
    }

    // ── 權杖未設 ─────────────────────────────────────────────────────────────────────────

    @Test
    void AT_960_5_E_1_withoutAConfiguredTokenNoRequestIsSentAndTheErrorNamesTheCauseButNeverAToken() {
        Rig unset = new Rig(null);

        Throwable thrown = catchThrowable(() -> unset.adapter.approve(ID, body("approver", "alice")));

        unset.server.verify();                                   // 沒有任何期望：若發出了請求，MockRestServiceServer 會讓呼叫失敗
        assertThat(unset.adapter.writeEnabled()).isFalse();
        assertThat(thrown).isInstanceOfSatisfying(ServiceUnavailableException.class, e -> {
            assertThat(e.reason()).isEqualTo(ErrorReasons.RESEARCH_WRITE_DISABLED);
            assertThat(e.details()).containsEntry("cause", "bridge_token_unset");
        });
        assertThat(unset.timeouts).isEmpty();
        // 讀取不需要權杖：沒設權杖時仍會發出
        unset.server.expect(requestTo(BASE + "/research/capabilities")).andRespond(withSuccess("{\"mode\":\"mock-only\"}", MediaType.APPLICATION_JSON));

        assertThat(unset.adapter.capabilities()).containsEntry("mode", "mock-only");
        unset.server.verify();
    }
}
