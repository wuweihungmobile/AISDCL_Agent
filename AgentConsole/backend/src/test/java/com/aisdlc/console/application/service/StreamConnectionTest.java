package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Kind;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Sink;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Semaphore;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.BooleanSupplier;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 前端 SSE 連線的內部約定（契約 §2.1、§2.3）。為什麼重要：慢速的前端不得拖住事件發布端（佇列滿＝伺服器主動關閉，客戶端用
 * {@code Last-Event-ID} 重連補齊）；重播與即時事件交會處不得漏、不得重、不得亂序；連線只收自己那一種串流（{@code /logs}
 * 與 {@code /metrics} 的 id 會撞號，混進來會被去重誤丟）。這些都在寫出執行緒與發布執行緒的並發之下成立，用真執行緒驗。
 */
class StreamConnectionTest {

    /** 記錄收到什麼的寫出端；{@link #hold} 讓 {@code send} 卡住，用來製造「慢速訂閱者」。 */
    private static final class RecordingSink implements Sink {

        final List<Frame> frames = new CopyOnWriteArrayList<>();
        final List<String> comments = new CopyOnWriteArrayList<>();
        final AtomicBoolean closed = new AtomicBoolean();
        final Semaphore hold = new Semaphore(Integer.MAX_VALUE / 2);
        volatile boolean clientGone;

        @Override
        public boolean send(Frame frame) {
            hold.acquireUninterruptibly();
            if (clientGone) {
                return false;
            }
            frames.add(frame);
            return true;
        }

        @Override
        public boolean comment(String text) {
            if (clientGone) {
                return false;
            }
            comments.add(text);
            return true;
        }

        @Override
        public void close() {
            closed.set(true);
        }

        List<String> ids() {
            return frames.stream().map(Frame::id).toList();
        }
    }

    private final UUID runId = UUID.randomUUID();
    private final RunEventHub hub = new RunEventHub();
    private final RecordingSink sink = new RecordingSink();
    private final List<StreamConnection> opened = new ArrayList<>();

    @AfterEach
    void closeEverything() {
        sink.hold.release(1000);
        opened.forEach(StreamConnection::close);
    }

    private StreamConnection connect(Kind kind, int capacity, Duration keepAlive) {
        StreamConnection connection = new StreamConnection(runId, kind, sink, capacity, keepAlive, hub);
        opened.add(connection);
        hub.subscribe(runId, connection);
        connection.startWriter();
        return connection;
    }

    private static Frame log(int seq, int sub) {
        return new Frame(Kind.LOGS, seq, sub, "log", "m" + seq + "." + sub);
    }

    private static Frame metric(int seq, int sub) {
        return new Frame(Kind.METRICS, seq, sub, "progress-update", "p" + seq + "." + sub);
    }

    private static boolean await(BooleanSupplier condition) {
        long deadline = System.nanoTime() + Duration.ofSeconds(5).toNanos();
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

    @Test
    void replayFramesGoOutFirstThenTheLiveOnesBufferedDuringTheReplayInOrderWithoutRepeats() {
        StreamConnection connection = connect(Kind.LOGS, 100, Duration.ofSeconds(30));
        // 重播還在計算時，即時事件已經到了（含一則與重播重疊的、一則比重播更舊的、一則亂序的）
        hub.publish(runId, List.of(log(43, 0), log(42, 0), log(44, 1), log(41, 0)));

        connection.deliverReplay(List.of(log(41, 0), log(42, 0)), false);

        assertThat(await(() -> sink.frames.size() == 4)).isTrue();
        assertThat(sink.ids()).as("嚴格遞增、各一次；重播內的 41、42 不因即時副本再送一次").containsExactly("41", "42", "43", "44.1");
    }

    @Test
    void framesOfTheOtherStreamKindNeverReachThisConnection() {
        StreamConnection connection = connect(Kind.LOGS, 100, Duration.ofSeconds(30));
        connection.deliverReplay(List.of(), false);

        hub.publish(runId, List.of(metric(50, 1), log(50, 0), metric(50, 2)));

        assertThat(await(() -> sink.frames.size() == 1)).isTrue();
        assertThat(sink.frames).extracting(Frame::kind).containsOnly(Kind.LOGS);
        assertThat(sink.ids()).containsExactly("50");
    }

    @Test
    void aFrameWithoutAnIdIsDeliveredButDoesNotMoveTheDedupCursor() {
        StreamConnection connection = connect(Kind.LOGS, 100, Duration.ofSeconds(30));
        connection.deliverReplay(List.of(), false);

        hub.publish(runId, List.of(log(10, 0),
                new Frame(Kind.LOGS, 10, Frame.NO_ID, "alert", "BRIDGE_UNREACHABLE"),
                new Frame(Kind.LOGS, 10, Frame.NO_ID, "alert", "BRIDGE_UNREACHABLE"), log(11, 0)));

        assertThat(await(() -> sink.frames.size() == 4)).isTrue();
        assertThat(sink.ids()).as("連線層暫態告警不帶 id、不參與去重").containsExactly("10", null, null, "11");
    }

    @Test
    void aFullQueueClosesTheSlowConnectionInsteadOfBlockingThePublisher() {
        sink.hold.drainPermits();
        StreamConnection connection = connect(Kind.LOGS, 2, Duration.ofSeconds(30));
        connection.deliverReplay(List.of(), false);

        // 寫出執行緒卡在第一個框架；佇列容量 2 再收兩個，第四個放不進去
        hub.publish(runId, List.of(log(1, 0)));
        assertThat(await(() -> sink.hold.hasQueuedThreads())).isTrue();
        hub.publish(runId, List.of(log(2, 0), log(3, 0)));
        assertThat(connection.isClosed()).isFalse();
        long start = System.nanoTime();
        hub.publish(runId, List.of(log(4, 0)));

        assertThat(Duration.ofNanos(System.nanoTime() - start)).as("發布端不被拖住").isLessThan(Duration.ofSeconds(1));
        assertThat(connection.isClosed()).isTrue();
        assertThat(sink.closed).as("伺服器主動關閉：通知前端的 emitter 完成").isTrue();
        assertThat(hub.subscriberCount(runId)).as("並取消訂閱，之後的事件不再送進來").isZero();
    }

    @Test
    void whenTheRunEndsTheQueuedFramesAreSentBeforeTheConnectionIsClosed() {
        StreamConnection connection = connect(Kind.LOGS, 100, Duration.ofSeconds(30));
        connection.deliverReplay(List.of(), false);

        hub.publish(runId, List.of(log(7, 0), log(8, 0)));
        hub.complete(runId);

        assertThat(await(() -> sink.closed.get())).isTrue();
        assertThat(sink.ids()).as("終態前的框架一個不少").containsExactly("7", "8");
        assertThat(connection.isClosed()).isTrue();
    }

    @Test
    void aRunThatEndsDuringTheReplayClosesOnlyAfterTheReplayAndTheBufferedFramesAreDelivered() {
        StreamConnection connection = connect(Kind.LOGS, 100, Duration.ofSeconds(30));
        hub.publish(runId, List.of(log(9, 0)));
        hub.complete(runId);
        assertThat(connection.isClosed()).as("重播尚未送完，不能先關").isFalse();

        connection.deliverReplay(List.of(log(8, 0)), false);

        assertThat(await(() -> sink.closed.get())).isTrue();
        assertThat(sink.ids()).containsExactly("8", "9");
    }

    @Test
    void aTerminalReplayIsFollowedByTheCloseEvenWhenNothingLiveArrives() {
        StreamConnection connection = connect(Kind.LOGS, 100, Duration.ofSeconds(30));

        connection.deliverReplay(List.of(log(1, 0), log(2, 0)), true);

        assertThat(await(() -> sink.closed.get())).isTrue();
        assertThat(sink.ids()).containsExactly("1", "2");
        assertThat(connection.isClosed()).isTrue();
    }

    @Test
    void anIdleConnectionGetsKeepAliveCommentsAndEveryFrameRestartsTheIdleTimer() {
        StreamConnection connection = connect(Kind.LOGS, 100, Duration.ofMillis(60));
        connection.deliverReplay(List.of(), false);

        assertThat(await(() -> sink.comments.size() >= 2)).isTrue();
        assertThat(sink.comments).containsOnly("keep-alive");

        hub.publish(runId, List.of(log(1, 0)));
        assertThat(await(() -> sink.frames.size() == 1)).isTrue();
        assertThat(connection.isClosed()).isFalse();
    }

    @Test
    void whenTheClientHasGoneTheConnectionEndsWithoutTouchingTheSinkAgain() {
        StreamConnection connection = connect(Kind.LOGS, 100, Duration.ofSeconds(30));
        connection.deliverReplay(List.of(), false);
        sink.clientGone = true;

        hub.publish(runId, List.of(log(1, 0)));

        assertThat(await(connection::isClosed)).isTrue();
        assertThat(sink.closed).as("客戶端已斷線：不必再通知 emitter 完成").isFalse();
        assertThat(await(() -> hub.subscriberCount(runId) == 0)).isTrue();
    }

    @Test
    void whenTheClientGoneIsDetectedByAKeepAliveTheConnectionEndsToo() {
        StreamConnection connection = connect(Kind.LOGS, 100, Duration.ofMillis(40));
        connection.deliverReplay(List.of(), false);

        sink.clientGone = true;

        assertThat(await(connection::isClosed)).isTrue();
        assertThat(sink.closed).isFalse();
    }

    @Test
    void closingTheConnectionStopsDeliveryAndUnsubscribes() {
        StreamConnection connection = connect(Kind.LOGS, 100, Duration.ofSeconds(30));
        connection.deliverReplay(List.of(), false);

        connection.close();
        hub.publish(runId, List.of(log(1, 0)));
        connection.deliverReplay(List.of(log(2, 0)), false);

        assertThat(connection.isClosed()).isTrue();
        assertThat(hub.subscriberCount(runId)).isZero();
        assertThat(sink.frames).isEmpty();
        assertThat(sink.closed).as("由我方關閉不是「伺服器主動關閉」").isFalse();
    }
}
