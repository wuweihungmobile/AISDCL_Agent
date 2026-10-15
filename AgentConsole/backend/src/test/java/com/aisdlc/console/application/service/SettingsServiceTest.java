package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.SettingsUseCase.ConfigView;
import com.aisdlc.console.application.port.in.SettingsUseCase.ConnectionTestResult;
import com.aisdlc.console.application.port.in.SettingsUseCase.ExportedItem;
import com.aisdlc.console.application.port.in.SettingsUseCase.ImportResult;
import com.aisdlc.console.application.port.in.SettingsUseCase.TestConnectionCommand;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.OutboundHttp;
import com.aisdlc.console.application.port.out.OutboundHttp.HttpResult;
import com.aisdlc.console.application.port.out.OutboundHttp.OutboundIoException;
import com.aisdlc.console.application.port.out.SecretCipher;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.model.config.ConfigHistoryEntry;
import com.aisdlc.console.domain.model.config.ConfigValueType;
import com.aisdlc.console.domain.service.OutboundUrlPolicy;
import com.aisdlc.console.support.InMemorySystemConfigRepository;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 系統參數用例的單元層（整合測試涵蓋端到端；這裡釘住 HTTP 層看不到的內部約定）：測試連線的逾時上限、
 * 探測本文的跳脫、授權標頭的有無、審計補充欄位絕不含金鑰與 userinfo、揭露只記範圍與次數、加密參數只存密文且歷史只存遮罩。
 */
class SettingsServiceTest {

    private static final Instant NOW = Instant.parse("2026-10-15T08:00:00Z");
    private static final String MASK = ConfigHistoryEntry.MASK;

    private final InMemorySystemConfigRepository repository = new InMemorySystemConfigRepository();
    private final OutboundHttp outbound = mock(OutboundHttp.class);
    private final AuditTrail audit = mock(AuditTrail.class);
    private final SecretCipher cipher = new SecretCipher() {
        @Override
        public String encrypt(String plainText) {
            return "enc:" + plainText;
        }

        @Override
        public String decrypt(String stored) {
            return stored.substring("enc:".length());
        }
    };
    private SettingsService service;

    @BeforeEach
    void setUp() {
        repository.with("model", "apiUrl", ConfigValueType.STRING, "https://api.minimax.io/v1/text/chatcompletion_v2")
                .withEncrypted("model", "apiKey", "")
                .with("model", "name", ConfigValueType.STRING, "MiniMax-M2.7")
                .with("model", "timeout", ConfigValueType.INTEGER, "3")
                .with("model", "temperature", ConfigValueType.FLOAT, "0.3")
                .with("model", "topP", ConfigValueType.FLOAT, "0.9")
                .with("model", "maxTokensPerRequest", ConfigValueType.INTEGER, "8192")
                .with("model", "enableKernelBrain", ConfigValueType.BOOLEAN, "false")
                .withEncrypted("autoclaude", "dbDsn", "");
        OutboundUrlPolicy policy = new OutboundUrlPolicy(List.of("api.minimax.io"), false);
        SettingsReader reader = new SettingsReader(repository, cipher);
        service = new SettingsService(repository, cipher, policy, outbound, reader,
                Clock.fixed(NOW, ZoneOffset.UTC), audit);
    }

    private void outboundAnswers(int status) {
        when(outbound.postJson(anyString(), anyMap(), anyString(), any(), any()))
                .thenReturn(new HttpResult(status, "{}", 42, "api.minimax.io"));
    }

    @SuppressWarnings("unchecked")
    private Map<String, String> sentHeaders() {
        ArgumentCaptor<Map<String, String>> headers = ArgumentCaptor.forClass(Map.class);
        verify(outbound).postJson(anyString(), headers.capture(), anyString(), any(), any());
        return headers.getValue();
    }

    private String sentBody() {
        ArgumentCaptor<String> body = ArgumentCaptor.forClass(String.class);
        verify(outbound).postJson(anyString(), anyMap(), body.capture(), any(), any());
        return body.getValue();
    }

    // ── 測試連線 ──────────────────────────────────────────────────────────────

    @Test
    void theTotalTimeoutIsTheStoredModelTimeoutCappedAtTenSecondsWithAFloorOfOne() {
        outboundAnswers(200);
        for (String[] c : new String[][] {{"3", "3"}, {"10", "10"}, {"11", "10"}, {"600", "10"}, {"0", "1"}}) {
            repository.set("model", "timeout", c[0]);
            service.testConnection(null, "admin");
        }

        ArgumentCaptor<Duration> connect = ArgumentCaptor.forClass(Duration.class);
        ArgumentCaptor<Duration> total = ArgumentCaptor.forClass(Duration.class);
        verify(outbound, times(5)).postJson(anyString(), anyMap(), anyString(), connect.capture(), total.capture());
        assertThat(total.getAllValues()).containsExactly(Duration.ofSeconds(3), Duration.ofSeconds(10),
                Duration.ofSeconds(10), Duration.ofSeconds(10), Duration.ofSeconds(1));
        assertThat(connect.getAllValues()).as("連線逾時固定 5 秒").containsOnly(Duration.ofSeconds(5));
    }

    @Test
    void anAuthorizationHeaderIsSentOnlyWhenThereIsAKeyAndTheRequestsKeyWinsOverTheStoredOne() {
        outboundAnswers(200);
        service.testConnection(null, "admin");
        assertThat(sentHeaders()).as("沒有金鑰就不帶").doesNotContainKey("Authorization")
                .containsEntry("User-Agent", "aisdlc-console").containsEntry("Accept", "application/json")
                .containsEntry("Content-Type", "application/json");

        reset(outbound);
        outboundAnswers(200);
        service.update("model", "apiKey", "sk-stored", true, "admin");
        service.testConnection(new TestConnectionCommand(null, "   ", null), "admin");
        assertThat(sentHeaders()).as("請求的 apiKey 空白＝沿用已儲存的（解密後）")
                .containsEntry("Authorization", "Bearer sk-stored");

        reset(outbound);
        outboundAnswers(200);
        service.testConnection(new TestConnectionCommand(null, "sk-typed", null), "admin");
        assertThat(sentHeaders()).containsEntry("Authorization", "Bearer sk-typed");
    }

    @Test
    void theProbeBodyIsTheDocumentedPingAndAHostileModelNameCannotInjectFields() {
        outboundAnswers(200);
        String hostile = "x\",\"max_tokens\":9999,\"stream\":true,\"y\":\"";

        service.testConnection(new TestConnectionCommand(null, null, hostile), "admin");

        String body = sentBody();
        assertThat(JsonPath.<String>read(body, "$.model")).isEqualTo(hostile);
        assertThat(JsonPath.<Integer>read(body, "$.max_tokens")).isEqualTo(1);
        assertThat(JsonPath.<Boolean>read(body, "$.stream")).isFalse();
        assertThat(JsonPath.<String>read(body, "$.messages[0].content")).isEqualTo("ping");
        assertThat(JsonPath.<String>read(body, "$.messages[0].role")).isEqualTo("user");
    }

    @Test
    void theHttpStatusIsTranslatedIntoTheDocumentedMessages() {
        Map<Integer, String> expected = new LinkedHashMap<>();
        expected.put(200, "連線成功");
        expected.put(201, "連線成功");
        expected.put(299, "連線成功");
        expected.put(301, "目標回應重新導向，已拒絕跟隨（HTTP 301）");
        expected.put(307, "目標回應重新導向，已拒絕跟隨（HTTP 307）");
        expected.put(401, "認證失敗（HTTP 401）");
        expected.put(403, "認證失敗（HTTP 403）");
        expected.put(404, "端點路徑不存在或不接受 POST（HTTP 404）");
        expected.put(405, "端點路徑不存在或不接受 POST（HTTP 405）");
        expected.put(400, "服務回應錯誤（HTTP 400）");
        expected.put(500, "服務回應錯誤（HTTP 500）");
        expected.put(503, "服務回應錯誤（HTTP 503）");

        expected.forEach((status, message) -> {
            outboundAnswers(status);
            ConnectionTestResult result = service.testConnection(null, "admin");
            assertThat(result.message()).as("HTTP " + status).isEqualTo(message);
            assertThat(result.success()).isEqualTo(status >= 200 && status < 300);
            assertThat(result.httpStatus()).isEqualTo(status);
            assertThat(result.latencyMs()).isEqualTo(42L);
            assertThat(result.resolvedHost()).isEqualTo("api.minimax.io");
        });
    }

    @Test
    void networkFailuresAreReportedAsAResultNotAnException() {
        when(outbound.postJson(anyString(), anyMap(), anyString(), any(), any()))
                .thenThrow(new OutboundIoException(OutboundIoException.Kind.TIMEOUT, "read timed out"));
        ConnectionTestResult timeout = service.testConnection(null, "admin");
        assertThat(timeout.success()).isFalse();
        assertThat(timeout.message()).isEqualTo("連線逾時（3 秒）");
        assertThat(timeout.latencyMs()).isNull();
        assertThat(timeout.httpStatus()).isNull();
        assertThat(timeout.resolvedHost()).isEqualTo("api.minimax.io");

        doThrow(new OutboundIoException(OutboundIoException.Kind.CONNECT, "Connection refused")).when(outbound)
                .postJson(anyString(), anyMap(), anyString(), any(), any());
        ConnectionTestResult refused = service.testConnection(null, "admin");
        assertThat(refused.message()).isEqualTo("無法連線：Connection refused");
    }

    @Test
    void aPolicyRefusalNeverReachesTheNetworkAndIsAuditedWithoutTheUrlOrUserinfo() {
        assertThatThrownBy(() -> service.testConnection(new TestConnectionCommand(
                "http://admin:your_password_here@api.minimax.io/v1/x", "sk-secret", null), "admin"))
                .isInstanceOfSatisfying(UnprocessableException.class, e -> {
                    assertThat(e.reason()).isEqualTo(ErrorReasons.OUTBOUND_REJECTED);
                    assertThat(e.details()).containsEntry("violation", "userinfo").containsEntry("host",
                            "api.minimax.io");
                    assertThat(e.getMessage()).doesNotContain("your_password_here").doesNotContain("sk-secret");
                });
        verify(outbound, never()).postJson(anyString(), anyMap(), anyString(), any(), any());

        ArgumentCaptor<Map<String, Object>> extra = extraCaptor();
        verify(audit).note(eq("settings.testConnection"), eq("settings"), eq("model.apiUrl"), extra.capture());
        assertThat(extra.getValue()).containsEntry("success", false).containsEntry("rejected", "userinfo");
        assertThat(extra.getValue().toString()).doesNotContain("your_password_here").doesNotContain("sk-secret");
    }

    @Test
    void theAuditExtrasOfASuccessfulProbeCarryTheHostAndOutcomeButNeverTheKey() {
        outboundAnswers(200);
        service.testConnection(new TestConnectionCommand(null, "sk-secret-xyz", null), "admin");

        ArgumentCaptor<Map<String, Object>> extra = extraCaptor();
        verify(audit).note(eq("settings.testConnection"), eq("settings"), eq("model.apiUrl"), extra.capture());
        assertThat(extra.getValue()).containsEntry("host", "api.minimax.io").containsEntry("success", true)
                .containsEntry("httpStatus", 200);
        assertThat(extra.getValue().toString()).doesNotContain("sk-secret-xyz");
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private static ArgumentCaptor<Map<String, Object>> extraCaptor() {
        return (ArgumentCaptor) ArgumentCaptor.forClass(Map.class);
    }

    // ── 揭露與加密參數 ──────────────────────────────────────────────────────────

    @Test
    void aRevealIsAuditedWithOnlyTheScopeAndTheNumberOfRevealedSecrets() {
        service.update("model", "apiKey", "sk-1", true, "admin");

        List<ConfigView> model = service.listCategory("model", true);
        assertThat(model).filteredOn(v -> v.config().key().equals("apiKey")).singleElement()
                .satisfies(v -> assertThat(v.displayValue()).isEqualTo("sk-1"));
        verify(audit).event("settings.reveal", Map.of("scope", "model", "count", 1));

        service.listAll(true);
        verify(audit).event("settings.reveal", Map.of("scope", "all", "count", 1));
    }

    @Test
    void withoutRevealNothingIsAuditedAndEncryptedValuesAreMasked() {
        service.update("model", "apiKey", "sk-1", true, "admin");

        List<ConfigView> model = service.listCategory("model", false);

        assertThat(model).filteredOn(v -> v.config().encrypted()).singleElement().satisfies(v -> {
            assertThat(v.displayValue()).isEqualTo(MASK);
            assertThat(v.hasValue()).isTrue();
        });
        verify(audit, never()).event(anyString(), anyMap());
    }

    @Test
    void anEncryptedValueIsStoredAsCiphertextAndTheHistoryOnlyEverHoldsTheMask() {
        service.update("model", "apiKey", "sk-1", true, "admin");
        service.update("model", "apiKey", "sk-2", true, "admin");
        service.update("model", "apiKey", "", true, "admin");

        assertThat(repository.find("model", "apiKey").orElseThrow().value()).isEmpty();
        assertThat(repository.historyEntries()).hasSize(3);
        assertThat(repository.historyEntries()).allSatisfy(h -> {
            assertThat(h.oldValue()).isEqualTo(MASK);
            assertThat(h.newValue()).isEqualTo(MASK);
            assertThat(h.changedBy()).isEqualTo("admin");
            assertThat(h.changedAt()).isEqualTo(NOW);
        });
        service.update("model", "apiKey", "sk-3", true, "admin");
        assertThat(repository.find("model", "apiKey").orElseThrow().value()).isEqualTo("enc:sk-3");
    }

    @Test
    void anEncryptedUpdateWithoutConfirmationIsRefusedBeforeAnythingIsWritten() {
        assertThatThrownBy(() -> service.update("model", "apiKey", "sk-1", false, "admin"))
                .isInstanceOfSatisfying(ConflictException.class,
                        e -> assertThat(e.reason()).isEqualTo(ErrorReasons.CONFIG_UPDATE_CONFIRM));
        assertThat(repository.find("model", "apiKey").orElseThrow().value()).isEmpty();
        assertThat(repository.historyEntries()).isEmpty();
    }

    @Test
    void anUnchangedValueWritesNoHistoryRowAndDoesNotTouchTheUpdater() {
        service.update("model", "name", "MiniMax-M2.7", false, "admin");
        assertThat(repository.historyEntries()).isEmpty();
        assertThat(repository.find("model", "name").orElseThrow().updatedBy()).as("值未變：連修改者都不更新").isNull();
    }

    @Test
    void anUnknownKeyOrCategoryIsNotFound() {
        assertThatThrownBy(() -> service.update("model", "nope", "x", false, "admin"))
                .isInstanceOf(NotFoundException.class);
        assertThatThrownBy(() -> service.listCategory("nope", false)).isInstanceOf(NotFoundException.class);
        assertThatThrownBy(() -> service.resetCategory("nope", false, "admin")).isInstanceOf(NotFoundException.class);
    }

    // ── 匯入的判定順序（C-6、DEF-AC-002；契約 §1.5.10）──────────────────────────────

    private static final String UNLISTED_URL = "https://not-listed.example/v1/chat";

    @Test
    void anImportedValueEqualToTheCurrentOneIsSkippedWithoutAnyValidationEvenWhenTheCurrentValueWouldBeRejected() {
        // 現值的主機不在 allowlist（e2e 環境預設的 api.minimax.io 就不在白名單）：值規則與 SEC-04 對「沒有要改的值」沒有意義
        repository.set("model", "apiUrl", UNLISTED_URL);

        ImportResult result = service.importSettings(List.of(new ExportedItem("model", "apiUrl", UNLISTED_URL)),
                "admin");

        assertThat(result.applied()).isZero();
        assertThat(result.skipped()).isEqualTo(1);
        assertThat(result.errors()).isEmpty();
        assertThat(repository.historyEntries()).isEmpty();
    }

    @Test
    void aChangedValueIsStillValidatedSoAnUnlistedHostIsRejectedAndNothingIsWritten() {
        ImportResult result = service.importSettings(List.of(new ExportedItem("model", "apiUrl", UNLISTED_URL)),
                "admin");

        assertThat(result.applied()).isZero();
        assertThat(result.skipped()).isZero();
        assertThat(result.errors()).singleElement().satisfies(e -> {
            assertThat(e.category()).isEqualTo("model");
            assertThat(e.key()).isEqualTo("apiUrl");
            assertThat(e.reason()).isEqualTo(ErrorReasons.OUTBOUND_REJECTED);
        });
        assertThat(repository.find("model", "apiUrl").orElseThrow().value())
                .isEqualTo("https://api.minimax.io/v1/text/chatcompletion_v2");
        assertThat(repository.historyEntries()).isEmpty();
    }

    @Test
    void thePlaceholderAndEncryptedPlaintextRulesComeBeforeTheUnchangedCheck() {
        // 加密鍵現值為空字串；匯入的明文剛好也是空字串＝「值相同」，但加密鍵給非佔位值一律是 errors（匯入不能繞過二次確認）
        ImportResult result = service.importSettings(List.of(
                new ExportedItem("model", "apiKey", SettingsService.ENCRYPTED_PLACEHOLDER),
                new ExportedItem("autoclaude", "dbDsn", "")), "admin");

        assertThat(result.skipped()).as("佔位值略過").isEqualTo(1);
        assertThat(result.applied()).isZero();
        assertThat(result.errors()).singleElement().satisfies(e -> {
            assertThat(e.key()).isEqualTo("dbDsn");
            assertThat(e.reason()).isEqualTo(ErrorReasons.CONFIG_UPDATE_CONFIRM);
        });
    }
}
