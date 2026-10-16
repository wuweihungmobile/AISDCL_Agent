package com.aisdlc.console.application.service;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.engine.SddEngineReason;
import com.aisdlc.console.domain.model.engine.SddEngineStatus;
import com.aisdlc.console.domain.model.engine.SddFsmList;
import com.aisdlc.console.domain.model.engine.SddFsmState;
import com.aisdlc.console.domain.model.engine.SddProjectEntry;
import com.aisdlc.console.domain.model.engine.SddVersion;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * AISDLC_SDD 引擎狀態（契約 §1.7.1 的 {@code reason} 映射表；D-16）。為什麼重要：這支查詢回報的是「引擎現在怎麼樣」，
 * 前端據此畫「不可用」而不是錯誤頁——Bridge 不可達、503、非預期回應都要變成 {@code available=false} 加對的 {@code reason}，
 * 而「專案層級」的 404／422 要讓引擎維持可用（只是那個專案沒有狀態）。分錯一格，監控頁的 SDD 卡就會對使用者說錯話。
 */
class SddEngineQueryServiceTest {

    private static final Instant NOW = Instant.parse("2026-10-16T03:21:45Z");
    private static final SddVersion VERSION = new SddVersion("AISDLC_SDD_v9.99", "/sdd/AISDLC_SDD_v9.99");
    private static final SddProjectEntry ALPHA = new SddProjectEntry("e2e-alpha", "FSM-STATE-e2e-alpha.yaml",
            "IMPLEMENTATION", "2026-10-16T01:02:03+00:00");
    private static final SddFsmState ALPHA_STATE = new SddFsmState("e2e-alpha", "IMPLEMENTATION", 2, "sid-alpha",
            "2026-10-16T01:02:03+00:00", List.of(), List.of(), "FSM-STATE-e2e-alpha.yaml", null, null, null);

    private final AgentBridge bridge = mock(AgentBridge.class);
    private final SddEngineQueryService service = new SddEngineQueryService(bridge,
            Clock.fixed(NOW, ZoneOffset.UTC));
    private final ListAppender<ILoggingEvent> logs = new ListAppender<>();
    private Logger logger;

    @BeforeEach
    void captureLogs() {
        logger = (Logger) LoggerFactory.getLogger(SddEngineQueryService.class);
        logger.setLevel(Level.DEBUG);
        logs.start();
        logger.addAppender(logs);
    }

    @AfterEach
    void releaseLogs() {
        logger.detachAppender(logs);
        logger.setLevel(null);
        logs.stop();
    }

    private static BridgeRejectedException rejected(int status, String reason) {
        return new BridgeRejectedException(status, reason, null, null, List.of(), Map.of("code", status));
    }

    private static UpstreamException.Failure failure(int status, String reason) {
        return new UpstreamException.Failure("Bridge 回了非預期的錯誤", reason == null
                ? Map.of("bridgeStatus", status) : Map.of("bridgeStatus", status, "bridgeReason", reason));
    }

    private void healthyEngine() {
        when(bridge.sddVersion()).thenReturn(VERSION);
        when(bridge.sddFsmList()).thenReturn(new SddFsmList("AISDLC_SDD_v9.99", List.of(ALPHA), List.of()));
    }

    // ── 可用 ────────────────────────────────────────────────────────────────

    @Test
    void withoutAProjectTheEngineIsAvailableWithTheListAndNoFsm() {
        healthyEngine();

        SddEngineStatus status = service.status(null);

        assertThat(status.available()).isTrue();
        assertThat(status.reason()).as("沒問題時不帶 reason（未帶 project 也不帶）").isNull();
        assertThat(status.version()).isEqualTo(VERSION);
        assertThat(status.projects()).containsExactly(ALPHA);
        assertThat(status.fsm()).isNull();
        assertThat(status.checkedAt()).isEqualTo(NOW);
        verify(bridge, never()).sddFsm(anyString());
    }

    @Test
    void aProjectNameAddsItsStateAsTheThirdCall() {
        healthyEngine();
        when(bridge.sddFsm("e2e-alpha")).thenReturn(ALPHA_STATE);

        SddEngineStatus status = service.status("e2e-alpha");

        assertThat(status.available()).isTrue();
        assertThat(status.reason()).isNull();
        assertThat(status.fsm()).isEqualTo(ALPHA_STATE);
        assertThat(status.projects()).containsExactly(ALPHA);
    }

    @Test
    void anEmptyFsmDirectoryIsAnAvailableEngineWithNoProjects() {
        when(bridge.sddVersion()).thenReturn(VERSION);
        when(bridge.sddFsmList()).thenReturn(new SddFsmList("AISDLC_SDD_v9.99", List.of(), List.of()));

        SddEngineStatus status = service.status(null);

        assertThat(status.available()).as("乾淨 clone 沒有 FSM 狀態檔是正常狀態").isTrue();
        assertThat(status.reason()).isNull();
        assertThat(status.projects()).isEmpty();
    }

    // ── 引擎層級的不可用（available=false）──────────────────────────────────────

    @Test
    void anUnreachableOrSlowBridgeIsBridgeUnreachableAndShortCircuits() {
        for (RuntimeException failure : List.<RuntimeException>of(new UpstreamException.Unavailable("refused"),
                new UpstreamException.TimedOut("slow"))) {
            org.mockito.Mockito.reset(bridge);
            when(bridge.sddVersion()).thenThrow(failure);

            SddEngineStatus status = service.status("e2e-alpha");

            assertThat(status.available()).isFalse();
            assertThat(status.reason()).as(failure.getClass().getSimpleName()).isEqualTo(SddEngineReason.BRIDGE_UNREACHABLE);
            assertThat(status.version()).isNull();
            assertThat(status.projects()).isEmpty();
            assertThat(status.fsm()).isNull();
            assertThat(status.checkedAt()).isEqualTo(NOW);
            verify(bridge, never()).sddFsmList();
            verify(bridge, never()).sddFsm(anyString());
        }
    }

    @Test
    void anInvalidSddRootIsSddUnavailableOnEitherOfTheFirstTwoCalls() {
        when(bridge.sddVersion()).thenThrow(failure(503, "sdd_unavailable"));
        SddEngineStatus first = service.status(null);
        assertThat(first.reason()).isEqualTo(SddEngineReason.SDD_UNAVAILABLE);
        assertThat(first.available()).isFalse();
        assertThat(first.version()).isNull();

        // 已經把 sddVersion 設成會丟例外：改回傳值要用 doReturn（when(bridge.sddVersion()) 會先觸發那個例外）
        doReturn(VERSION).when(bridge).sddVersion();
        when(bridge.sddFsmList()).thenThrow(failure(503, "sdd_unavailable"));
        SddEngineStatus second = service.status(null);
        assertThat(second.reason()).isEqualTo(SddEngineReason.SDD_UNAVAILABLE);
        assertThat(second.available()).isFalse();
        assertThat(second.version()).as("第二個呼叫失敗：保留第一個呼叫已取得的版本").isEqualTo(VERSION);
        assertThat(second.projects()).isEmpty();
        verify(bridge, never()).sddFsm(anyString());
    }

    @Test
    void otherFailuresAreBridgeErrorIncludingAnotherReason503AndAWrongShape() {
        for (RuntimeException failure : List.<RuntimeException>of(failure(500, "spawn_failed"), failure(503, "lock_backend"),
                failure(503, null), failure(200, null), rejected(404, ""), rejected(400, "invalid_request"))) {
            org.mockito.Mockito.reset(bridge);
            when(bridge.sddVersion()).thenThrow(failure);

            SddEngineStatus status = service.status(null);

            assertThat(status.available()).as(failure.toString()).isFalse();
            assertThat(status.reason()).as(failure.toString()).isEqualTo(SddEngineReason.BRIDGE_ERROR);
        }
    }

    @Test
    void aFailingSecondCallKeepsTheVersionButHasNoProjectsAndSkipsTheThird() {
        when(bridge.sddVersion()).thenReturn(VERSION);
        when(bridge.sddFsmList()).thenThrow(new UpstreamException.TimedOut("slow"));

        SddEngineStatus status = service.status("e2e-alpha");

        assertThat(status.available()).isFalse();
        assertThat(status.reason()).isEqualTo(SddEngineReason.BRIDGE_UNREACHABLE);
        assertThat(status.version()).isEqualTo(VERSION);
        assertThat(status.projects()).isEmpty();
        verify(bridge, never()).sddFsm(anyString());
    }

    // ── 專案層級的問題（引擎仍可用）與第三個呼叫的其他失敗 ───────────────────────────────

    @Test
    void aMissingFsmFileLeavesTheEngineAvailableWithTheListAndTheNotFoundReason() {
        healthyEngine();
        when(bridge.sddFsm("nope")).thenThrow(rejected(404, "fsm_not_found"));

        SddEngineStatus status = service.status("nope");

        assertThat(status.available()).isTrue();
        assertThat(status.reason()).isEqualTo(SddEngineReason.FSM_NOT_FOUND);
        assertThat(status.fsm()).isNull();
        assertThat(status.version()).isEqualTo(VERSION);
        assertThat(status.projects()).containsExactly(ALPHA);
    }

    @Test
    void anUnreadableFsmFileLeavesTheEngineAvailableWithTheUnreadableReason() {
        healthyEngine();
        when(bridge.sddFsm("e2e-broken")).thenThrow(rejected(422, "fsm_state_unreadable"));

        SddEngineStatus status = service.status("e2e-broken");

        assertThat(status.available()).isTrue();
        assertThat(status.reason()).isEqualTo(SddEngineReason.FSM_STATE_UNREADABLE);
        assertThat(status.fsm()).isNull();
        assertThat(status.projects()).containsExactly(ALPHA);
    }

    @Test
    void aThirdCallFailureMakesTheEngineUnavailableButKeepsEarlierValues() {
        healthyEngine();
        for (Map.Entry<RuntimeException, SddEngineReason> row : Map.<RuntimeException, SddEngineReason>of(
                new UpstreamException.Unavailable("refused"), SddEngineReason.BRIDGE_UNREACHABLE,
                new UpstreamException.TimedOut("slow"), SddEngineReason.BRIDGE_UNREACHABLE,
                failure(503, "sdd_unavailable"), SddEngineReason.SDD_UNAVAILABLE,
                failure(500, "boom"), SddEngineReason.BRIDGE_ERROR,
                rejected(400, "invalid_request"), SddEngineReason.BRIDGE_ERROR).entrySet()) {
            doThrow(row.getKey()).when(bridge).sddFsm("e2e-alpha");

            SddEngineStatus status = service.status("e2e-alpha");

            assertThat(status.available()).as(row.getKey().toString()).isFalse();
            assertThat(status.reason()).as(row.getKey().toString()).isEqualTo(row.getValue());
            assertThat(status.fsm()).isNull();
            assertThat(status.version()).isEqualTo(VERSION);
            assertThat(status.projects()).as("第三個呼叫失敗：保留前兩個呼叫已取得的值").containsExactly(ALPHA);
        }
    }

    // ── project 驗證（400）──────────────────────────────────────────────────────

    @Test
    void aNameOutsideTheWhitelistIsRejectedBeforeAnyBridgeCall() {
        for (String bad : List.of("", " ", "a b", "../x", "a/b", "a%20b", "名稱", "x".repeat(129), "a\nb")) {
            assertThatThrownBy(() -> service.status(bad)).as("[" + bad + "]").isInstanceOfSatisfying(
                    ValidationException.class, e -> assertThat(e.violations()).singleElement()
                            .satisfies(v -> assertThat(v.field()).isEqualTo("project")));
        }
        verifyNoInteractions(bridge);
    }

    @Test
    void theWhitelistAcceptsEveryNameTheBridgeCanProduce() {
        healthyEngine();
        for (String good : List.of("AISDLC_SDD", "test-11472", "a.b_c-d", "..", ".", "x".repeat(128), "0")) {
            when(bridge.sddFsm(good)).thenReturn(ALPHA_STATE);

            assertThat(service.status(good).fsm()).as(good).isEqualTo(ALPHA_STATE);
        }
    }

    // ── errors[]：只記日誌，不轉發 ────────────────────────────────────────────────

    @Test
    void unreadableFileNamesAreLoggedWithoutControlCharactersAndNeverForwarded() {
        when(bridge.sddVersion()).thenReturn(VERSION);
        when(bridge.sddFsmList()).thenReturn(new SddFsmList("AISDLC_SDD_v9.99", List.of(ALPHA),
                List.of("FSM-STATE-broken.yaml", "FSM-STATE-evil\nname.yaml")));

        SddEngineStatus status = service.status(null);

        assertThat(status.toString()).as("狀態物件沒有任何欄位承載 errors[]").doesNotContain("broken").doesNotContain("evil");
        assertThat(logs.list).filteredOn(event -> event.getLevel() == Level.WARN).singleElement().satisfies(event -> {
            assertThat(event.getFormattedMessage()).contains("FSM-STATE-broken.yaml").contains("evil?name")
                    .doesNotContain("\n");
        });
    }

    @Test
    void aListWithoutUnreadableFilesLogsNoWarning() {
        healthyEngine();

        service.status(null);

        assertThat(logs.list).filteredOn(event -> event.getLevel().isGreaterOrEqual(Level.WARN)).isEmpty();
    }
}
