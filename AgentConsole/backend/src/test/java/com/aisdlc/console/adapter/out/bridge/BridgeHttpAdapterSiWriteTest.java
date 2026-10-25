package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.si.SiValidation;
import com.aisdlc.console.domain.model.si.SiWriteAck;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.test.web.client.ResponseCreator;
import org.springframework.test.web.client.response.DefaultResponseCreator;
import org.springframework.web.client.RestClient;

import java.net.ConnectException;
import java.net.SocketException;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;
import static org.hamcrest.Matchers.emptyOrNullString;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.headerDoesNotExist;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

/**
 * SelfImproving 稽核檔落地與預檢的 Bridge 呼叫（TCS-SelfImprovingDecide-P2b AT-950-6-1、AT-950-6-2；W11、W15），以
 * {@code MockRestServiceServer} 驗「送出的請求」與「各種回應拋出的例外」。為什麼重要：稽核 JSON 是 {@code audit_sha256} 與 HMAC 的對象，
 * 位元組只要被重新序列化過（多一個空白、換個鍵序、非 ASCII 字元被跳脫成 Unicode 轉義），主機端 CLI 就以 AUDIT-MAC-MISMATCH 拒收；而 backend 的補償邏輯
 * 全押在例外型別上——確定沒送達（連線被拒）若被當成結果不明，會留下幽靈待入帳；結果不明（送出後連線被重設）若被當成確定未送達，
 * 會刪掉一列「其實檔已落地」的稽核列，帳本就多出一個 Console 看不見的 orphan。
 */
class BridgeHttpAdapterSiWriteTest {

    private static final String BASE = "http://bridge.test:8081";
    private static final String TOKEN = "si-write-token-for-tests-0123456789-abcdef";
    private static final String REF = "a1000000-0000-4000-8000-000000000001";
    /** 含全形字元、引號、反斜線與換行：任何重新序列化都會讓位元組改變。 */
    private static final String AUDIT = "{\"schema_rev\":1,\"kind\":\"decide\",\"audit_ref\":\"" + REF
            + "\",\"subject\":\"PROP-SI-004\",\"body\":\"{\\\"reason\\\":\\\"證據座標不足，無法判定\\\\n\\\"}\",\"key_id\":\"f076edf0\"}";
    private static final String ACK = "{\"audit_ref\":\"" + REF + "\",\"stored\":true}";

    /** 一個接上 {@code MockRestServiceServer} 的介面卡，與它被要求的（連線，讀取）逾時。 */
    private static final class Rig {
        final MockRestServiceServer server;
        final BridgeHttpAdapter adapter;
        final List<Duration[]> timeouts = new ArrayList<>();

        Rig(String siToken) {
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
            adapter = new BridgeHttpAdapter(builder, new BridgeEndpoints(settings, new BridgeProperties(BASE, null, siToken)),
                    (connect, read) -> {
                        timeouts.add(new Duration[] {connect, read});
                        return null;
                    });
        }
    }

    private final Rig rig = new Rig(TOKEN);

    private static DefaultResponseCreator jsonStatus(HttpStatus status, String body) {
        return withStatus(status).contentType(MediaType.APPLICATION_JSON).body(body);
    }

    // ── AT-950-6-1：請求形態 ─────────────────────────────────────────────────────────────

    @Test
    void AT_950_6_1_theThreeWritesPostTheRawAuditBytesWithTheTokenAndTheValidatePostsWithoutIt() {
        byte[] audit = AUDIT.getBytes(StandardCharsets.UTF_8);
        String unsigned = "{\"schema_rev\":1,\"kind\":\"obs-add\",\"user\":\"admin\",\"context\":\"Console・自我進化頁\"}";
        String validation = "{\"ok\":true,\"row\":\"| OBS | … |\",\"row_bytes\":287,\"row_max_bytes\":700,\"findings\":[]}";
        rig.server.expect(requestTo(BASE + "/si/proposals/PROP-SI-004:decide")).andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Bridge-Token", TOKEN)).andExpect(header("X-Trace-Id", not(emptyOrNullString())))
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON)).andExpect(content().bytes(audit))
                .andRespond(withSuccess(ACK, MediaType.APPLICATION_JSON));
        rig.server.expect(requestTo(BASE + "/si/observations")).andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Bridge-Token", TOKEN)).andExpect(content().bytes(audit))
                .andRespond(jsonStatus(HttpStatus.CREATED, ACK));
        rig.server.expect(requestTo(BASE + "/si/observations/OBS-SI-005:close")).andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Bridge-Token", TOKEN)).andExpect(content().bytes(audit))
                .andRespond(jsonStatus(HttpStatus.CREATED, ACK));
        rig.server.expect(requestTo(BASE + "/si/observations:validate")).andExpect(method(HttpMethod.POST))
                .andExpect(headerDoesNotExist("X-Bridge-Token")).andExpect(content().bytes(unsigned.getBytes(StandardCharsets.UTF_8)))
                .andRespond(withSuccess(validation, MediaType.APPLICATION_JSON));

        SiWriteAck decided = rig.adapter.siWriteDecide("PROP-SI-004", AUDIT);
        SiWriteAck added = rig.adapter.siWriteObservation(AUDIT);
        SiWriteAck closed = rig.adapter.siWriteObservationClose("OBS-SI-005", AUDIT);
        SiValidation checked = rig.adapter.siValidateObservation(unsigned);

        rig.server.verify();
        for (SiWriteAck ack : List.of(decided, added, closed)) {
            assertThat(ack).isEqualTo(new SiWriteAck(REF, true));
        }
        assertThat(checked.ok()).isTrue();
        assertThat(checked.row()).isEqualTo("| OBS | … |");
        assertThat(checked.rowBytes()).isEqualTo(287);
        assertThat(checked.rowMaxBytes()).isEqualTo(700L);
        assertThat(checked.findings()).isEmpty();
        assertThat(rig.timeouts).as("連線逾時 2 秒、讀取逾時 20 秒（Bridge 的 15 秒子行程逾時之上）").hasSize(4)
                .allSatisfy(pair -> {
                    assertThat(pair[0]).isEqualTo(Duration.ofSeconds(2));
                    assertThat(pair[1]).isEqualTo(Duration.ofSeconds(20));
                });
    }

    @Test
    void AT_950_6_1_theIdIsEncodedAsOneStrictPathSegmentBeforeTheLiteralAction() {
        Map<String, String> expected = new LinkedHashMap<>();
        expected.put("a b/專案", "a%20b%2F%E5%B0%88%E6%A1%88");
        expected.put("..", "%2E%2E");
        expected.put("x?y#z;w", "x%3Fy%23z%3Bw");
        for (Map.Entry<String, String> entry : expected.entrySet()) {
            rig.server.reset();
            rig.server.expect(requestTo(BASE + "/si/proposals/" + entry.getValue() + ":decide"))
                    .andRespond(withSuccess(ACK, MediaType.APPLICATION_JSON));
            rig.server.expect(requestTo(BASE + "/si/observations/" + entry.getValue() + ":close"))
                    .andRespond(withSuccess(ACK, MediaType.APPLICATION_JSON));

            rig.adapter.siWriteDecide(entry.getKey(), AUDIT);
            rig.adapter.siWriteObservationClose(entry.getKey(), AUDIT);

            rig.server.verify();
        }
    }

    @Test
    void AT_950_6_1_withoutAConfiguredTokenNoRequestIsSentAndTheErrorNamesTheCauseButNeverAToken() {
        Rig unset = new Rig(null);

        Throwable thrown = catchThrowable(() -> unset.adapter.siWriteDecide("PROP-SI-004", AUDIT));

        unset.server.verify();                                   // 沒有任何期望：若發出了請求，MockRestServiceServer 會讓呼叫失敗
        assertThat(thrown).isInstanceOfSatisfying(ServiceUnavailableException.class, e -> {
            assertThat(e.reason()).isEqualTo(ErrorReasons.SI_WRITE_DISABLED);
            assertThat(e.details()).containsEntry("cause", "bridge_token_unset");
        });
        assertThat(unset.timeouts).isEmpty();
        // 預檢不需要權杖：沒設權杖時仍會發出
        unset.server.expect(requestTo(BASE + "/si/observations:validate")).andExpect(headerDoesNotExist("X-Bridge-Token"))
                .andRespond(withSuccess("{\"ok\":false,\"row\":\"\",\"row_bytes\":0,\"row_max_bytes\":null,"
                        + "\"findings\":[{\"code\":\"FIELD-EMPTY\",\"detail\":\"欄位為空\"}]}", MediaType.APPLICATION_JSON));

        SiValidation invalid = unset.adapter.siValidateObservation("{}");

        unset.server.verify();
        assertThat(invalid.ok()).isFalse();
        assertThat(invalid.rowMaxBytes()).as("根層量不到上限＝null，不補 700").isNull();
        assertThat(invalid.findings()).singleElement().satisfies(f -> {
            assertThat(f.code()).isEqualTo("FIELD-EMPTY");
            assertThat(f.detail()).isEqualTo("欄位為空");
        });
    }

    // ── AT-950-6-2：十二種回應各自拋出的例外，且每種只送一次請求 ───────────────────────────────────

    private void expectOne(ResponseCreator answer) {
        rig.server.reset();
        rig.server.expect(requestTo(BASE + "/si/proposals/PROP-SI-004:decide")).andRespond(answer);
    }

    @Test
    void AT_950_6_2_everyBridgeAnswerMapsToTheDocumentedExceptionWithExactlyOneRequest() {
        String disabled = "{\"code\":503,\"reason\":\"si_write_disabled\",\"detail\":\"BRIDGE_SI_WRITE_TOKEN 未設\"}";
        String forbidden = "{\"code\":403,\"reason\":\"si_write_forbidden\"}";
        String exists = "{\"code\":409,\"reason\":\"si_audit_exists\"}";
        String invalid = "{\"code\":422,\"reason\":\"invalid_request\",\"violations\":[{\"field\":\"subject\","
                + "\"rule\":\"mismatch\",\"message\":\"與路徑不符\"}]}";
        String unavailable = "{\"code\":503,\"reason\":\"si_unavailable\",\"cause\":\"audit_write_failed\","
                + "\"detail\":\"errno=28; OSError\"}";
        Map<String, ResponseCreator> answers = new LinkedHashMap<>();
        answers.put("201", jsonStatus(HttpStatus.CREATED, ACK));
        answers.put("503 si_write_disabled", jsonStatus(HttpStatus.SERVICE_UNAVAILABLE, disabled));
        answers.put("403 si_write_forbidden", jsonStatus(HttpStatus.FORBIDDEN, forbidden));
        answers.put("409 si_audit_exists", jsonStatus(HttpStatus.CONFLICT, exists));
        answers.put("422 invalid_request", jsonStatus(HttpStatus.UNPROCESSABLE_CONTENT, invalid));
        answers.put("503 si_unavailable", jsonStatus(HttpStatus.SERVICE_UNAVAILABLE, unavailable));
        answers.put("500", jsonStatus(HttpStatus.INTERNAL_SERVER_ERROR, "{\"code\":500,\"reason\":\"boom\"}"));
        answers.put("500 非 JSON", withStatus(HttpStatus.INTERNAL_SERVER_ERROR).contentType(MediaType.TEXT_PLAIN)
                .body("Internal Server Error"));
        answers.put("連線被拒", withException(new ConnectException("Connection refused")));
        answers.put("送出後連線被重設", withException(new SocketException("Connection reset")));
        answers.put("讀取逾時", withException(new SocketTimeoutException("Read timed out")));
        answers.put("201 非 JSON", withSuccess("created, trust me", MediaType.TEXT_PLAIN));
        assertThat(answers).hasSize(12);
        for (Map.Entry<String, ResponseCreator> entry : answers.entrySet()) {
            String label = entry.getKey();
            expectOne(entry.getValue());

            Throwable thrown = catchThrowable(() -> rig.adapter.siWriteDecide("PROP-SI-004", AUDIT));

            rig.server.verify();                    // 恰好一次請求：重試會在第二次請求時被 MockRestServiceServer 拒絕
            if ("201".equals(label)) {
                assertThat(thrown).as(label).isNull();
                continue;
            }
            assertThat(thrown).as(label).isNotNull();
            assertThat(String.valueOf(thrown.getMessage())).as("%s：權杖不出現在任何例外訊息", label).doesNotContain(TOKEN);
            switch (label) {
                case "503 si_write_disabled", "403 si_write_forbidden", "409 si_audit_exists", "422 invalid_request",
                        "503 si_unavailable" -> assertRejected(label, thrown);
                case "500", "500 非 JSON" -> assertThat(thrown).as(label).isInstanceOfSatisfying(UpstreamException.Failure.class,
                        failure -> assertThat(failure.details()).containsEntry("bridgeStatus", 500));
                case "連線被拒" -> assertThat(thrown).as(label).isInstanceOfSatisfying(UpstreamException.Unavailable.class,
                        unavailableEx -> assertThat(unavailableEx.deliveryUncertain()).as("連線階段：確定沒有送達").isFalse());
                case "送出後連線被重設" -> assertThat(thrown).as(label).isInstanceOfSatisfying(UpstreamException.Unavailable.class,
                        unavailableEx -> assertThat(unavailableEx.deliveryUncertain()).as("送出之後：結果不明").isTrue());
                case "讀取逾時" -> assertThat(thrown).as(label).isInstanceOf(UpstreamException.TimedOut.class);
                default -> assertThat(thrown).as(label).isInstanceOfSatisfying(UpstreamException.Failure.class,
                        failure -> assertThat(failure.details()).as("2xx 本文無法解析：bridgeStatus 為 200（結果不明）")
                                .containsEntry("bridgeStatus", 200));
            }
        }
        assertThat(rig.timeouts).as("每次呼叫的連線與讀取逾時").hasSize(answers.size()).allSatisfy(pair -> {
            assertThat(pair[0]).isEqualTo(Duration.ofSeconds(2));
            assertThat(pair[1]).isEqualTo(Duration.ofSeconds(20));
        });
    }

    private static void assertRejected(String label, Throwable thrown) {
        assertThat(thrown).as(label).isInstanceOf(BridgeRejectedException.class);
        BridgeRejectedException rejected = (BridgeRejectedException) thrown;
        switch (label) {
            case "503 si_write_disabled" -> {
                assertThat(rejected.status()).isEqualTo(503);
                assertThat(rejected.reason()).isEqualTo("si_write_disabled");
                assertThat(rejected.detail()).isEqualTo("BRIDGE_SI_WRITE_TOKEN 未設");
            }
            case "403 si_write_forbidden" -> {
                assertThat(rejected.status()).isEqualTo(403);
                assertThat(rejected.reason()).isEqualTo("si_write_forbidden");
            }
            case "409 si_audit_exists" -> {
                assertThat(rejected.status()).isEqualTo(409);
                assertThat(rejected.reason()).isEqualTo("si_audit_exists");
            }
            case "422 invalid_request" -> {
                assertThat(rejected.status()).isEqualTo(422);
                assertThat(rejected.reason()).isEqualTo("invalid_request");
                assertThat(rejected.violations()).singleElement()
                        .satisfies(v -> assertThat(v).containsEntry("field", "subject"));
            }
            default -> {
                assertThat(rejected.status()).isEqualTo(503);
                assertThat(rejected.reason()).isEqualTo("si_unavailable");
                assertThat(rejected.body()).containsEntry("cause", "audit_write_failed");
                assertThat(rejected.detail()).isEqualTo("errno=28; OSError");
            }
        }
    }

    @Test
    void AT_950_6_2_theSddWriteDisabledAnswerIsStillAnExplicitRejectionAndAnOtherFiveHundredThreeIsAFailure() {
        expectOne(jsonStatus(HttpStatus.SERVICE_UNAVAILABLE, "{\"code\":503,\"reason\":\"sdd_write_disabled\"}"));
        assertThat(catchThrowable(() -> rig.adapter.siWriteDecide("PROP-SI-004", AUDIT))).as("沿用既有的 SDD 判準")
                .isInstanceOf(BridgeRejectedException.class);

        expectOne(jsonStatus(HttpStatus.SERVICE_UNAVAILABLE, "{\"code\":503,\"reason\":\"something_else\"}"));
        assertThat(catchThrowable(() -> rig.adapter.siWriteDecide("PROP-SI-004", AUDIT))).as("其他 503 是故障、不是明確拒絕")
                .isInstanceOfSatisfying(UpstreamException.Failure.class,
                        failure -> assertThat(failure.details()).containsEntry("bridgeStatus", 503));
    }

    @Test
    void AT_950_6_2_aMalformedAckIsAFailureWithStatus200ForEveryShapeThatLacksAuditRefOrStored() {
        for (String body : List.of("{}", "{\"audit_ref\":\"" + REF + "\"}", "{\"audit_ref\":\"" + REF + "\",\"stored\":false}",
                "{\"stored\":true}", "[1,2]")) {
            expectOne(withSuccess(body, MediaType.APPLICATION_JSON));

            Throwable thrown = catchThrowable(() -> rig.adapter.siWriteDecide("PROP-SI-004", AUDIT));

            rig.server.verify();
            assertThat(thrown).as(body).isInstanceOfSatisfying(UpstreamException.Failure.class,
                    failure -> assertThat(failure.details()).containsEntry("bridgeStatus", 200));
        }
    }
}
