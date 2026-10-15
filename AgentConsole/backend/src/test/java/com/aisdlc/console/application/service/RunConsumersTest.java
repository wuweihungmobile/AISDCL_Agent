package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.AlertEventData;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Kind;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeEvent;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.application.service.RunEventProcessor.Outcome;
import com.aisdlc.console.application.service.RunEventProcessor.PauseAction;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunStatus;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.stubbing.Answer;
import org.springframework.transaction.PlatformTransactionManager;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 事件消費者的生命週期與錯誤處理（契約 §3.5.4）。為什麼重要：投影（任務、目標、專案、審核項）全靠這條消費線把 Bridge 的事件變成讀模型——
 * 它悄悄停掉＝畫面永遠停在「執行中」；它在 Bridge 掛掉時無限快速重試＝把 Bridge 與資料庫一起拖垮；它把同一次中斷重複告警＝前端被洗版。
 * 整合測試涵蓋「跑完一個 run」的正常路徑，這裡用腳本化的 Bridge 逐一壓每個失敗分支。
 */
class RunConsumersTest {

    private static final Instant NOW = Instant.parse("2026-10-15T08:00:00Z");
    private static final Duration WAIT = Duration.ofSeconds(5);

    /** 前端連線的替身：記錄收到的框架與「該 run 已結束」通知。 */
    private static final class Front implements RunEventHub.Listener {

        final List<Frame> frames = new CopyOnWriteArrayList<>();
        volatile int ended;

        @Override
        public void accept(Frame frame) {
            frames.add(frame);
        }

        @Override
        public void runEnded() {
            ended++;
        }

        List<String> alertCodes() {
            return frames.stream().filter(f -> f.data() instanceof AlertEventData)
                    .map(f -> ((AlertEventData) f.data()).code()).toList();
        }
    }

    private final AgentBridge bridge = mock(AgentBridge.class);
    private final ExecutionRunRepository runs = mock(ExecutionRunRepository.class);
    private final RunEventProcessor processor = mock(RunEventProcessor.class);
    private final RunEventHub hub = new RunEventHub();
    private final RunRegistry registry = new RunRegistry();
    private final RuntimeSettings settings = mock(RuntimeSettings.class);
    private final PlatformTransactionManager transactions = mock(PlatformTransactionManager.class);
    private final UUID runId = UUID.randomUUID();
    private final Front front = new Front();
    private RunConsumers consumers;

    @BeforeEach
    void setUp() {
        when(settings.consumerBackoffInitial()).thenReturn(Duration.ofMillis(5));
        when(settings.consumerBackoffMax()).thenReturn(Duration.ofMillis(20));
        when(settings.consumerIdleTimeout()).thenReturn(Duration.ofSeconds(45));
        consumers = new RunConsumers(bridge, runs, processor, hub, registry, settings, transactions,
                Clock.fixed(NOW, ZoneOffset.UTC));
        hub.subscribe(runId, front);
    }

    @AfterEach
    void stopEverything() {
        consumers.stopAll();
    }

    // ── 夾具 ────────────────────────────────────────────────────────────────────

    private static BridgeEvent event(int seq) {
        return new BridgeEvent(seq, NOW.toString(), "status", Map.of("status", "RUNNING"));
    }

    private static Frame frame(int seq) {
        return new Frame(Kind.LOGS, seq, 0, "log", "m" + seq);
    }

    private static Outcome terminal(Frame... frames) {
        return new Outcome(List.of(frames), List.of(), true);
    }

    private static Outcome progress(Frame... frames) {
        return new Outcome(List.of(frames), List.of(), false);
    }

    private ExecutionRun run(RunStatus status) {
        return new ExecutionRun(runId, UUID.randomUUID(), 1, status, 4, null, 0, null, NOW, null, null, 0, null);
    }

    private static BridgeRejectedException rejected(int status) {
        return new BridgeRejectedException(status, status == 404 ? "run_not_found" : "busy", null, null, List.of(),
                Map.of());
    }

    /** 串流：依序把 {@code events} 交給消費者的處理函式後正常返回（＝伺服器關閉了串流）。 */
    private static Answer<Object> streams(BridgeEvent... events) {
        return invocation -> {
            Consumer<BridgeEvent> handler = invocation.getArgument(3);
            for (BridgeEvent e : events) {
                handler.accept(e);
            }
            return null;
        };
    }

    private void stubStream(Answer<?>... answers) {
        var stubber = doAnswer(answers[0]);
        for (int i = 1; i < answers.length; i++) {
            stubber = stubber.doAnswer(answers[i]);
        }
        stubber.when(bridge).streamEvents(eq(runId), anyInt(), any(), any());
    }

    private static Answer<Object> failing(RuntimeException e) {
        return invocation -> {
            throw e;
        };
    }

    private void runToTheEnd() {
        consumers.start(runId, 0);
        assertThat(consumers.awaitIdle(WAIT)).as("消費者在 %s 內結束", WAIT).isTrue();
    }

    /** 消費者先把自己標成結束、再從表中移除（兩步之間有一瞬間）：用輪詢等第二步完成。 */
    private static boolean eventually(BooleanSupplier condition) {
        long deadline = System.nanoTime() + Duration.ofSeconds(2).toNanos();
        while (System.nanoTime() < deadline) {
            if (condition.getAsBoolean()) {
                return true;
            }
            try {
                Thread.sleep(10);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
        return condition.getAsBoolean();
    }

    // ── 正常結束 ────────────────────────────────────────────────────────────────

    @Test
    void aTerminalEventPublishesItsFramesNotifiesTheFrontAndEndsTheConsumer() {
        stubStream(streams(event(1), event(2)));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 1))).thenReturn(progress(frame(1)));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 2))).thenReturn(terminal(frame(2)));

        runToTheEnd();

        assertThat(front.frames).extracting(Frame::seq).containsExactly(1, 2);
        assertThat(front.ended).isEqualTo(1);
        assertThat(consumers.isRunning(runId)).isFalse();
        assertThat(eventually(() -> consumers.endedState(runId).isEmpty())).as("結束的消費者自己從表中移除").isTrue();
        verify(bridge, times(1)).streamEvents(eq(runId), anyInt(), any(), any());
    }

    @Test
    void anEventTheProcessorHasNothingToSayAboutPublishesNothing() {
        stubStream(streams(event(1)));
        when(processor.process(eq(runId), any())).thenReturn(Outcome.NOTHING);
        when(runs.findById(runId)).thenReturn(Optional.of(run(RunStatus.COMPLETED)));

        runToTheEnd();

        assertThat(front.frames).isEmpty();
        assertThat(front.ended).isZero();
    }

    // ── 串流被關閉 ──────────────────────────────────────────────────────────────

    @Test
    void aStreamClosedWhileTheRunIsStillActiveIsReconnectedAfterACatchUp() {
        when(runs.findById(runId)).thenReturn(Optional.of(run(RunStatus.RUNNING)));
        stubStream(streams(), streams(event(3)));
        when(processor.process(eq(runId), any())).thenReturn(terminal(frame(3)));

        runToTheEnd();

        verify(bridge, times(2)).streamEvents(eq(runId), anyInt(), any(), any());
        verify(bridge, times(1)).listEvents(eq(runId), anyInt(), anyInt());
        assertThat(front.frames).extracting(Frame::seq).containsExactly(3);
    }

    @Test
    void aStreamClosedForARunTheDatabaseAlreadyHoldsAsTerminalEndsTheConsumerWithoutReconnecting() {
        when(runs.findById(runId)).thenReturn(Optional.of(run(RunStatus.COMPLETED)));
        stubStream(streams());

        runToTheEnd();

        verify(bridge, times(1)).streamEvents(eq(runId), anyInt(), any(), any());
        verify(bridge, never()).listEvents(any(), anyInt(), anyInt());
    }

    @Test
    void aStreamForARunWithNoDatabaseRowEndsTheConsumerToo() {
        stubStream(streams());

        runToTheEnd();

        verify(bridge, times(1)).streamEvents(eq(runId), anyInt(), any(), any());
    }

    @Test
    void theCatchUpAfterAReconnectPagesThroughTheMissedEventsAndCanFinishTheRunWithoutAnotherStream() {
        when(runs.findById(runId)).thenReturn(Optional.of(run(RunStatus.RUNNING)));
        stubStream(streams());
        when(bridge.listEvents(eq(runId), anyInt(), anyInt())).thenReturn(List.of(event(4), event(5)));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 4))).thenReturn(progress(frame(4)));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 5))).thenReturn(terminal(frame(5)));

        runToTheEnd();

        assertThat(front.frames).extracting(Frame::seq).containsExactly(4, 5);
        verify(bridge, times(1)).streamEvents(eq(runId), anyInt(), any(), any());
        assertThat(front.ended).isEqualTo(1);
    }

    @Test
    void theCatchUpKeepsAskingForTheNextPageUntilItComesBackEmpty() {
        when(runs.findById(runId)).thenReturn(Optional.of(run(RunStatus.RUNNING)));
        stubStream(streams(), streams(event(9)));
        when(bridge.listEvents(eq(runId), anyInt(), anyInt())).thenReturn(List.of(event(4)), List.of());
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 4))).thenReturn(progress(frame(4)));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 9))).thenReturn(terminal(frame(9)));

        runToTheEnd();

        verify(bridge, times(2)).listEvents(eq(runId), anyInt(), anyInt());
        assertThat(front.frames).extracting(Frame::seq).containsExactly(4, 9);
    }

    // ── 錯誤 ────────────────────────────────────────────────────────────────────

    @Test
    void aBridgeThatRefusesTheStreamWithAnotherStatusIsRetriedWithBackoff() {
        stubStream(failing(rejected(503)), failing(rejected(503)), streams(event(1)));
        when(processor.process(eq(runId), any())).thenReturn(terminal(frame(1)));

        runToTheEnd();

        verify(bridge, times(3)).streamEvents(eq(runId), anyInt(), any(), any());
        assertThat(front.alertCodes()).as("被拒絕不是「不可達」，不對前端送連線告警").isEmpty();
    }

    @Test
    void aBridgeThatNoLongerKnowsTheRunAnnouncesItOnceThenTheFrontIsToldTheRunEnded() {
        stubStream(failing(rejected(404)));

        runToTheEnd();

        assertThat(front.alertCodes()).containsExactly("BRIDGE_RUN_UNKNOWN");
        assertThat(front.frames.get(0).hasId()).as("連線層暫態告警不帶 id").isFalse();
        assertThat(front.ended).isEqualTo(1);
        verify(bridge, times(1)).streamEvents(eq(runId), anyInt(), any(), any());
    }

    @Test
    void anUnreachableBridgeIsAnnouncedOncePerOutageWhileTheConsumerKeepsRetrying() {
        when(runs.findById(runId)).thenReturn(Optional.of(run(RunStatus.RUNNING)));
        UpstreamException down = new UpstreamException.Unavailable("connection refused");
        // 第一次中斷：連續三次失敗；恢復（串流正常返回但 run 仍在跑）；第二次中斷；最後恢復並收到終態
        stubStream(failing(down), failing(down), failing(down), streams(), failing(down), failing(down),
                streams(event(7)));
        when(processor.process(eq(runId), any())).thenReturn(terminal(frame(7)));

        runToTheEnd();

        assertThat(front.alertCodes()).as("同一次中斷只告警一次，恢復後再斷才再告警")
                .containsExactly("BRIDGE_UNREACHABLE", "BRIDGE_UNREACHABLE");
        assertThat(front.frames.stream().filter(f -> f.data() instanceof AlertEventData)
                .map(Frame::hasId)).containsOnly(false);
        verify(bridge, times(7)).streamEvents(eq(runId), anyInt(), any(), any());
    }

    @Test
    void anUnexpectedErrorIsLoggedAndTheConsumerRetriesInsteadOfDying() {
        stubStream(failing(new IllegalStateException("boom")), streams(event(1)));
        when(processor.process(eq(runId), any())).thenReturn(terminal(frame(1)));

        runToTheEnd();

        verify(bridge, times(2)).streamEvents(eq(runId), anyInt(), any(), any());
        assertThat(front.frames).extracting(Frame::seq).containsExactly(1);
    }

    // ── 暫停動作 ────────────────────────────────────────────────────────────────

    private Outcome pauseFor(String why) {
        return new Outcome(List.of(), List.of(new PauseAction(why)), false);
    }

    @Test
    void aPauseActionIsExecutedAfterTheTransactionCommitsByCallingTheBridge() {
        stubStream(streams(event(1), event(2)));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 1))).thenReturn(pauseFor("gate"));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 2))).thenReturn(terminal(frame(2)));

        runToTheEnd();

        verify(bridge, times(1)).pauseRun(runId);
    }

    @Test
    void aBridgeThatRefusesAGatePauseClearsTheGateFlagButABudgetPauseKeepsItsState() {
        stubStream(streams(event(1), event(2), event(3)));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 1))).thenReturn(pauseFor("budget"));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 2))).thenReturn(pauseFor("gate"));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 3))).thenReturn(terminal());
        when(bridge.pauseRun(runId)).thenThrow(rejected(409));
        registry.runtime(runId).gatePauseRequested = true;

        runToTheEnd();

        verify(bridge, times(2)).pauseRun(runId);
        assertThat(registry.runtime(runId).gatePauseRequested).as("引擎拒絕閘點暫停：不再以為「已要求暫停」").isFalse();
    }

    @Test
    void aBudgetPauseRefusedByTheBridgeDoesNotTouchTheGateFlag() {
        stubStream(streams(event(1), event(2)));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 1))).thenReturn(pauseFor("budget"));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 2))).thenReturn(terminal());
        when(bridge.pauseRun(runId)).thenThrow(rejected(409));
        registry.runtime(runId).gatePauseRequested = true;

        runToTheEnd();

        assertThat(registry.runtime(runId).gatePauseRequested).isTrue();
    }

    @Test
    void aPauseThatCannotReachTheBridgeIsLoggedAndTheRunKeepsBeingConsumed() {
        stubStream(streams(event(1), event(2)));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 1))).thenReturn(pauseFor("gate"));
        when(processor.process(eq(runId), argThat(e -> e != null && e.seq() == 2))).thenReturn(terminal(frame(2)));
        when(bridge.pauseRun(runId)).thenThrow(new UpstreamException.TimedOut("slow"));

        runToTheEnd();

        assertThat(front.frames).extracting(Frame::seq).as("暫停失敗不影響後續事件的消費").containsExactly(2);
    }

    // ── 停止與狀態 ──────────────────────────────────────────────────────────────

    @Test
    void stopAllEndsAConsumerThatIsBlockedInsideTheBridgeStreamWithoutWaitingForTheBridge() throws Exception {
        CountDownLatch inside = new CountDownLatch(1);
        stubStream(invocation -> {
            inside.countDown();
            try {
                Thread.sleep(60_000);
            } catch (InterruptedException e) {
                throw new IllegalStateException("interrupted by stopAll", e);
            }
            return null;
        });
        consumers.start(runId, 0);
        assertThat(inside.await(5, TimeUnit.SECONDS)).isTrue();
        assertThat(consumers.isRunning(runId)).isTrue();
        assertThat(consumers.activeCount()).isEqualTo(1);
        assertThat(consumers.endedState(runId)).contains(false);
        assertThat(consumers.awaitIdle(Duration.ofMillis(50))).as("還在跑：等不到閒置").isFalse();

        consumers.stopAll();

        assertThat(consumers.awaitIdle(WAIT)).isTrue();
        assertThat(consumers.isRunning(runId)).isFalse();
    }

    @Test
    void startingAnAlreadyRunningConsumerAgainDoesNotStartASecondOne() throws Exception {
        CountDownLatch inside = new CountDownLatch(1);
        stubStream(invocation -> {
            inside.countDown();
            try {
                Thread.sleep(60_000);
            } catch (InterruptedException e) {
                throw new IllegalStateException("interrupted by stopAll", e);
            }
            return null;
        });
        consumers.start(runId, 0);
        assertThat(inside.await(5, TimeUnit.SECONDS)).isTrue();

        consumers.start(runId, 0);
        consumers.start(runId, 5);

        assertThat(consumers.activeCount()).isEqualTo(1);
        verify(bridge, times(1)).streamEvents(eq(runId), anyInt(), any(), any());
    }

    @Test
    void aConsumerSleepingInItsBackoffIsWokenByStopAllAndTreatsItAsAStopRequest() throws Exception {
        when(settings.consumerBackoffInitial()).thenReturn(Duration.ofSeconds(30));
        when(settings.consumerBackoffMax()).thenReturn(Duration.ofSeconds(30));
        CountDownLatch failedOnce = new CountDownLatch(1);
        stubStream(invocation -> {
            failedOnce.countDown();
            throw new UpstreamException.Unavailable("down");
        });
        consumers.start(runId, 0);
        assertThat(failedOnce.await(5, TimeUnit.SECONDS)).isTrue();

        consumers.stopAll();

        assertThat(consumers.awaitIdle(WAIT)).as("退避睡眠中被喚醒、不再重試").isTrue();
        verify(bridge, times(1)).streamEvents(eq(runId), anyInt(), any(), any());
    }

    @Test
    void aConsumerThatIsToldToStopBeforeItsFirstDatabaseAccessDoesNothing() {
        consumers.stopAll();

        assertThat(consumers.activeCount()).isZero();
        assertThat(consumers.awaitIdle(Duration.ofMillis(10))).isTrue();
        assertThat(consumers.endedState(runId)).isEmpty();
    }
}
