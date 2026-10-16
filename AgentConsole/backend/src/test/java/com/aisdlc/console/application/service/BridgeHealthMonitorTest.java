package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeHealth;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * Bridge 健康探測環（契約 §3.1；D-17）。為什麼重要：v1.4 起探測打的是深度探針，Bridge 行程活著但引擎自檢未通過時回 503——
 * 這一筆探測必須被記成「失敗」，頂列的「Engine Bridge」燈、Agent 可用率與「Agent 無回應」告警才會跟著反映；
 * 反過來，連線失敗與 503 在環裡沒有差別（都是一筆失敗），而成功與失敗各佔多少決定可用率。
 */
class BridgeHealthMonitorTest {

    /** 由測試撥動的時鐘（可用率以探測時間落在哪個視窗為準）。 */
    private static final class MutableClock extends Clock {
        private final AtomicReference<Instant> now = new AtomicReference<>(Instant.parse("2026-10-16T08:00:00Z"));

        void advanceSeconds(long seconds) {
            now.updateAndGet(current -> current.plusSeconds(seconds));
        }

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return now.get();
        }
    }

    private final AgentBridge bridge = mock(AgentBridge.class);
    private final RuntimeSettings settings = mock(RuntimeSettings.class);
    private final MutableClock clock = new MutableClock();
    private BridgeHealthMonitor monitor;

    private BridgeHealthMonitor monitor(int capacity) {
        when(settings.healthProbeCapacity()).thenReturn(capacity);
        monitor = new BridgeHealthMonitor(bridge, settings, clock);
        return monitor;
    }

    @Test
    void aDegraded503ProbeIsRecordedAsAFailureAndTheLightGoesOut() {
        monitor(10);
        when(bridge.health()).thenReturn(new BridgeHealth(false, 503));

        BridgeHealthMonitor.Probe probe = monitor.probeNow();

        assertThat(probe.ok()).as("503 degraded＝引擎自檢未通過＝不可用").isFalse();
        assertThat(monitor.lastProbeFailed()).isTrue();
        assertThat(monitor.last()).contains(probe);
    }

    @Test
    void aConnectionFailureAndAnHttp503AreTheSameKindOfFailureInTheRing() {
        monitor(10);
        when(bridge.health()).thenReturn(new BridgeHealth(false, 0), new BridgeHealth(false, 503));

        BridgeHealthMonitor.Probe unreachable = monitor.probeNow();
        BridgeHealthMonitor.Probe degraded = monitor.probeNow();

        assertThat(unreachable.ok()).isEqualTo(degraded.ok()).isFalse();
        assertThat(monitor.size()).isEqualTo(2);
    }

    @Test
    void availabilityCountsEveryFailedProbeSoADegradedBridgeLowersIt() {
        monitor(10);
        when(bridge.health()).thenReturn(new BridgeHealth(true, 200), new BridgeHealth(false, 503),
                new BridgeHealth(true, 200), new BridgeHealth(false, 503));
        Instant from = clock.instant();
        for (int i = 0; i < 4; i++) {
            monitor.probeNow();
            clock.advanceSeconds(30);
        }

        assertThat(monitor.availability(from, clock.instant())).hasValueSatisfying(value ->
                assertThat(value).as("四筆裡兩筆失敗").isEqualTo(50.0));
    }

    @Test
    void aHealthyProbeAfterAFailureBringsTheLightBack() {
        monitor(10);
        when(bridge.health()).thenReturn(new BridgeHealth(false, 503), new BridgeHealth(true, 200));

        monitor.probeNow();
        assertThat(monitor.lastProbeFailed()).isTrue();
        monitor.probeNow();

        assertThat(monitor.lastProbeFailed()).isFalse();
        assertThat(monitor.last()).hasValueSatisfying(probe -> assertThat(probe.ok()).isTrue());
    }

    @Test
    void anEmptyRingHasNoFailureEvidenceAndNoAvailability() {
        monitor(10);

        assertThat(monitor.last()).isEmpty();
        assertThat(monitor.lastProbeFailed()).as("從未探測過＝沒有失敗證據（頂列燈顯示未知）").isFalse();
        assertThat(monitor.availability(clock.instant().minusSeconds(60), clock.instant())).isEmpty();
    }

    @Test
    void theRingKeepsOnlyTheNewestProbesUpToItsCapacity() {
        monitor(3);
        when(bridge.health()).thenReturn(new BridgeHealth(false, 503), new BridgeHealth(false, 503),
                new BridgeHealth(true, 200), new BridgeHealth(true, 200), new BridgeHealth(true, 200));
        for (int i = 0; i < 5; i++) {
            monitor.probeNow();
            clock.advanceSeconds(30);
        }

        assertThat(monitor.size()).isEqualTo(3);
        assertThat(monitor.availability(Instant.EPOCH, clock.instant())).hasValueSatisfying(value ->
                assertThat(value).as("最舊的兩筆失敗已被擠出環").isEqualTo(100.0));
    }
}
