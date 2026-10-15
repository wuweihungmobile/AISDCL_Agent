package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Kind;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 事件樞紐（一個 run 的所有前端連線各收一份框架）。為什麼重要：訂閱與取消訂閱發生在不同執行緒（HTTP 請求、寫出執行緒、
 * 事件消費者）；若「最後一個訂閱者離開就移除該 run 的項目」與「新訂閱者剛好加入」不是原子的，新連線會訂在一個已被丟棄的清單上，
 * 之後整條串流靜默收不到任何事件——這種錯誤只在並發下出現，平常的測試看不到。
 */
class RunEventHubTest {

    private static final class Recorder implements RunEventHub.Listener {

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
    }

    private static Frame frame(int seq) {
        return new Frame(Kind.LOGS, seq, 0, "log", "m" + seq);
    }

    @Test
    void everySubscriberOfARunGetsEveryFrameInOrderAndOtherRunsGetNothing() {
        RunEventHub hub = new RunEventHub();
        UUID run = UUID.randomUUID();
        Recorder a = new Recorder();
        Recorder b = new Recorder();
        Recorder other = new Recorder();
        hub.subscribe(run, a);
        hub.subscribe(run, b);
        hub.subscribe(UUID.randomUUID(), other);

        hub.publish(run, List.of(frame(1), frame(2), frame(3)));
        hub.publish(UUID.randomUUID(), List.of(frame(99)));
        hub.publish(run, List.of());

        assertThat(a.frames).extracting(Frame::seq).containsExactly(1, 2, 3);
        assertThat(b.frames).extracting(Frame::seq).containsExactly(1, 2, 3);
        assertThat(other.frames).isEmpty();
        assertThat(hub.subscriberCount(run)).isEqualTo(2);
    }

    @Test
    void completeTellsEverySubscriberOfThatRunOnly() {
        RunEventHub hub = new RunEventHub();
        UUID run = UUID.randomUUID();
        Recorder a = new Recorder();
        Recorder other = new Recorder();
        hub.subscribe(run, a);
        hub.subscribe(UUID.randomUUID(), other);

        hub.complete(run);
        hub.complete(UUID.randomUUID());

        assertThat(a.ended).isEqualTo(1);
        assertThat(other.ended).isZero();
    }

    @Test
    void anUnsubscribedListenerStopsReceivingAndTheLastOneLeavingForgetsTheRun() {
        RunEventHub hub = new RunEventHub();
        UUID run = UUID.randomUUID();
        Recorder a = new Recorder();
        Recorder b = new Recorder();
        hub.subscribe(run, a);
        hub.subscribe(run, b);

        hub.unsubscribe(run, a);
        hub.publish(run, List.of(frame(1)));
        assertThat(a.frames).isEmpty();
        assertThat(b.frames).hasSize(1);
        assertThat(hub.subscriberCount(run)).isEqualTo(1);

        hub.unsubscribe(run, b);
        hub.unsubscribe(run, b);
        assertThat(hub.subscriberCount(run)).as("沒有訂閱者就不留空項目").isZero();
        hub.publish(run, List.of(frame(2)));
        hub.complete(run);
        assertThat(b.frames).hasSize(1);

        Recorder late = new Recorder();
        hub.subscribe(run, late);
        hub.publish(run, List.of(frame(3)));
        assertThat(late.frames).extracting(Frame::seq).as("之後重新訂閱照常運作").containsExactly(3);
    }

    @Test
    void concurrentSubscribeAndUnsubscribeOfTheSameRunNeverLoseALiveSubscriber() throws Exception {
        RunEventHub hub = new RunEventHub();
        UUID run = UUID.randomUUID();
        Recorder stayer = new Recorder();
        hub.subscribe(run, stayer);
        int rounds = 2_000;
        ExecutorService pool = Executors.newFixedThreadPool(4);
        try {
            CountDownLatch go = new CountDownLatch(1);
            List<Future<?>> futures = new ArrayList<>();
            for (int t = 0; t < 4; t++) {
                futures.add(pool.submit(() -> {
                    go.await();
                    for (int i = 0; i < rounds; i++) {
                        Recorder transient1 = new Recorder();
                        hub.subscribe(run, transient1);
                        hub.unsubscribe(run, transient1);
                    }
                    return null;
                }));
            }
            go.countDown();
            for (Future<?> future : futures) {
                future.get();
            }
        } finally {
            pool.shutdownNow();
        }

        assertThat(hub.subscriberCount(run)).as("只剩常駐的那一個").isEqualTo(1);
        hub.publish(run, List.of(frame(1)));
        assertThat(stayer.frames).hasSize(1);
    }

    @Test
    void whenTheFirstSubscriberOfARunRacesWithAnotherLeavingTheNewcomerStillReceives() throws Exception {
        RunEventHub hub = new RunEventHub();
        int rounds = 3_000;
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            for (int i = 0; i < rounds; i++) {
                UUID run = UUID.randomUUID();
                Recorder leaver = new Recorder();
                Recorder newcomer = new Recorder();
                hub.subscribe(run, leaver);
                CountDownLatch go = new CountDownLatch(1);
                Future<?> leave = pool.submit(() -> {
                    go.await();
                    hub.unsubscribe(run, leaver);
                    return null;
                });
                Future<?> join = pool.submit(() -> {
                    go.await();
                    hub.subscribe(run, newcomer);
                    return null;
                });
                go.countDown();
                leave.get();
                join.get();
                hub.publish(run, List.of(frame(i)));
                assertThat(newcomer.frames).as("第 %d 輪：新訂閱者不得因為舊訂閱者同時離開而訂在被丟棄的清單上", i).hasSize(1);
            }
        } finally {
            pool.shutdownNow();
        }
    }
}
