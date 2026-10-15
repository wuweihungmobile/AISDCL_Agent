package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunStatus;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.atLeast;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * 啟動對帳與排程（契約 §3.5.4、§3.4.5 第 6 點）。為什麼重要：console-api 重啟後，沒有人會再替「停機期間發生的事」補處理——
 * 這裡漏掉一類批次，專案與任務就永遠卡在執行中；反過來，對一個 Bridge 已經不認得的批次硬啟動消費者，會讓連線層無限重試。
 * 重啟時 Bridge 暫時不可達是常態（兩邊一起重啟），所以不可達時仍要啟動消費者、由連線層重試。
 */
class MonitorTickerTest {

    private static final Instant NOW = Instant.parse("2026-10-15T08:00:00Z");

    private final RuntimeSettings settings = mock(RuntimeSettings.class);
    private final ExecutionRunRepository runs = mock(ExecutionRunRepository.class);
    private final AgentBridge bridge = mock(AgentBridge.class);
    private final RunConsumers consumers = mock(RunConsumers.class);
    private final BridgeHealthMonitor health = mock(BridgeHealthMonitor.class);
    private final TimeRuleEvaluator timeRules = mock(TimeRuleEvaluator.class);
    private final RunLauncher launcher = mock(RunLauncher.class);
    private MonitorTicker ticker;

    @BeforeEach
    void setUp() {
        ticker = new MonitorTicker(settings, runs, bridge, consumers, health, timeRules, launcher,
                Clock.fixed(NOW, ZoneOffset.UTC));
        when(settings.backgroundEnabled()).thenReturn(true);
        when(settings.monitorTickInterval()).thenReturn(Duration.ofMillis(20));
        when(runs.findByStatuses(any())).thenReturn(List.of());
        when(runs.findTerminalOfExecutingProjects()).thenReturn(List.of());
    }

    @AfterEach
    void stopTheScheduler() {
        ticker.stop();
    }

    private static ExecutionRun run(RunStatus status, int lastSeq, Instant startedAt) {
        return new ExecutionRun(UUID.randomUUID(), UUID.randomUUID(), 1, status, 4, null, 0, null, startedAt, null, null,
                lastSeq, null);
    }

    private static BridgeRejectedException rejected(int status) {
        return new BridgeRejectedException(status, status == 404 ? "run_not_found" : "boom", null, null, List.of(),
                Map.of());
    }

    private void listRunsWithStatus(RunStatus status, ExecutionRun... rows) {
        when(runs.findByStatuses(any())).thenAnswer(invocation -> {
            Collection<RunStatus> asked = invocation.getArgument(0);
            return asked.contains(status) ? List.of(rows) : List.of();
        });
    }

    // ── 啟動 ────────────────────────────────────────────────────────────────────

    @Test
    void whenBackgroundWorkIsDisabledNothingStartsNotEvenTheProbe() {
        when(settings.backgroundEnabled()).thenReturn(false);

        ticker.onReady();

        verifyNoInteractions(health, bridge, consumers, timeRules);
    }

    @Test
    void whenEnabledItProbesOnceReconcilesAndThenTicksOnItsOwnSchedule() {
        ticker.onReady();

        verify(health, timeout(2_000).atLeast(3)).probeNow();
        verify(timeRules, timeout(2_000).atLeast(2)).evaluateAll();
        verify(runs, atLeast(1)).findTerminalOfExecutingProjects();
    }

    @Test
    void startingTwiceDoesNotStartASecondSchedulerOrReconcileAgain() {
        ticker.start();
        ticker.start();

        verify(runs, times(1)).findTerminalOfExecutingProjects();
    }

    @Test
    void stoppingEndsTheScheduleAndIsSafeToRepeat() throws Exception {
        ticker.start();
        verify(timeRules, timeout(2_000).atLeast(1)).evaluateAll();

        ticker.stop();
        ticker.stop();
        Thread.sleep(80);
        int ticksAfterStop = org.mockito.Mockito.mockingDetails(timeRules).getInvocations().size();
        Thread.sleep(200);

        assertThat(org.mockito.Mockito.mockingDetails(timeRules).getInvocations())
                .as("停止之後（容許最後一個已在途的 tick 跑完）不再有任何 tick").hasSize(ticksAfterStop);
    }

    @Test
    void aFailingTickIsLoggedAndDoesNotKillTheScheduleOrPropagate() {
        doThrow(new IllegalStateException("probe boom")).when(health).probeNow();

        ticker.tick();
        ticker.tick();

        verify(health, times(2)).probeNow();
        verify(timeRules, never()).evaluateAll();
    }

    // ── 對帳：RUNNING／PAUSED ────────────────────────────────────────────────────

    @Test
    void aRunningRunWhoseBridgeIsReachableGetsItsConsumerAtTheStoredOffset() {
        ExecutionRun running = run(RunStatus.RUNNING, 41, NOW.minusSeconds(600));
        listRunsWithStatus(RunStatus.RUNNING, running);

        ticker.reconcile();

        verify(bridge).getRun(running.id());
        verify(consumers).start(running.id(), 41);
    }

    @Test
    void aRunTheBridgeNoLongerKnowsIsLeftAloneAndGetsNoConsumer() {
        ExecutionRun lost = run(RunStatus.PAUSED, 7, NOW.minusSeconds(600));
        listRunsWithStatus(RunStatus.PAUSED, lost);
        when(bridge.getRun(lost.id())).thenThrow(rejected(404));

        ticker.reconcile();

        verify(consumers, never()).start(any(), anyInt());
        verify(launcher, never()).compensate(any());
    }

    @Test
    void aBridgeThatRefusesTheQueryWithAnotherStatusAlsoGetsNoConsumer() {
        ExecutionRun refused = run(RunStatus.RUNNING, 7, NOW.minusSeconds(600));
        listRunsWithStatus(RunStatus.RUNNING, refused);
        when(bridge.getRun(refused.id())).thenThrow(rejected(500));

        ticker.reconcile();

        verify(consumers, never()).start(any(), anyInt());
    }

    @Test
    void anUnreachableBridgeStillStartsTheConsumerSoTheConnectionLayerKeepsRetrying() {
        ExecutionRun running = run(RunStatus.RUNNING, 12, NOW.minusSeconds(600));
        listRunsWithStatus(RunStatus.RUNNING, running);
        when(bridge.getRun(running.id())).thenThrow(new UpstreamException.Unavailable("connection refused"));

        ticker.reconcile();

        verify(consumers).start(running.id(), 12);
    }

    // ── 對帳：停機期間跑完的批次 ───────────────────────────────────────────────────

    @Test
    void aTerminalRunOfAProjectStillMarkedExecutingIsProcessedFromItsStoredOffset() {
        ExecutionRun finished = run(RunStatus.COMPLETED, 30, NOW.minusSeconds(900));
        when(runs.findTerminalOfExecutingProjects()).thenReturn(List.of(finished));

        ticker.reconcile();

        verify(consumers).start(finished.id(), 30);
    }

    // ── 對帳：INITIALIZING ──────────────────────────────────────────────────────

    @Test
    void aStaleInitializingRunTheBridgeDoesNotKnowIsCompensated() {
        ExecutionRun stale = run(RunStatus.INITIALIZING, 0, NOW.minusSeconds(61));
        listRunsWithStatus(RunStatus.INITIALIZING, stale);
        when(bridge.getRun(stale.id())).thenThrow(rejected(404));

        ticker.reconcile();

        verify(launcher).compensate(stale.id());
        verify(consumers, never()).start(any(), anyInt());
    }

    @Test
    void aStaleInitializingRunThatTheBridgeKnowsGetsItsConsumer() {
        ExecutionRun stale = run(RunStatus.INITIALIZING, 3, NOW.minusSeconds(120));
        listRunsWithStatus(RunStatus.INITIALIZING, stale);

        ticker.reconcile();

        verify(consumers).start(stale.id(), 3);
        verify(launcher, never()).compensate(any());
    }

    @Test
    void anInitializingRunYoungerThanSixtySecondsIsNotTouchedBecauseTheStartIsStillInFlight() {
        ExecutionRun fresh = run(RunStatus.INITIALIZING, 0, NOW.minusSeconds(59));
        ExecutionRun withoutStart = run(RunStatus.INITIALIZING, 0, null);
        listRunsWithStatus(RunStatus.INITIALIZING, fresh, withoutStart);

        ticker.reconcile();

        verifyNoInteractions(bridge, launcher);
        verify(consumers, never()).start(any(), anyInt());
    }

    @Test
    void aStaleInitializingRunWhenTheBridgeIsUnreachableOrRefusesIsLeftForTheNextReconcile() {
        ExecutionRun unreachable = run(RunStatus.INITIALIZING, 0, NOW.minusSeconds(300));
        ExecutionRun refused = run(RunStatus.INITIALIZING, 0, NOW.minusSeconds(300));
        listRunsWithStatus(RunStatus.INITIALIZING, unreachable, refused);
        when(bridge.getRun(unreachable.id())).thenThrow(new UpstreamException.TimedOut("slow"));
        when(bridge.getRun(refused.id())).thenThrow(rejected(500));

        ticker.reconcile();

        verify(launcher, never()).compensate(any());
        verify(consumers, never()).start(any(), anyInt());
    }
}
