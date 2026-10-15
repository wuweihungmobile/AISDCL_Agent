package com.aisdlc.console.application.service;

import com.aisdlc.console.application.service.RunRegistry.Runtime;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 每個 run 的互斥鎖與記憶體內的執行期狀態。為什麼重要：契約 §1.2 要求同一個 run 的控制操作（暫停、恢復、取消、還原、審核）與事件消費
 * 互相排隊，否則「還原」會與正在寫入的事件處理互相踩踏；審核決定在持鎖時又會呼叫控制操作，所以鎖必須可重入，否則自己鎖死自己。
 * 不同 run 之間不得互相阻塞（一個卡住的 run 不能拖住其他 run）。
 */
class RunRegistryTest {

    @Test
    void theLockOfOneRunSerializesItsCriticalSectionsAcrossThreads() throws Exception {
        RunRegistry registry = new RunRegistry();
        UUID run = UUID.randomUUID();
        AtomicInteger inside = new AtomicInteger();
        AtomicInteger maxInside = new AtomicInteger();
        AtomicInteger total = new AtomicInteger();
        ExecutorService pool = Executors.newFixedThreadPool(6);
        try {
            List<Future<?>> futures = new ArrayList<>();
            for (int t = 0; t < 6; t++) {
                futures.add(pool.submit(() -> {
                    for (int i = 0; i < 300; i++) {
                        registry.locked(run, () -> {
                            int now = inside.incrementAndGet();
                            maxInside.accumulateAndGet(now, Math::max);
                            total.incrementAndGet();
                            inside.decrementAndGet();
                        });
                    }
                }));
            }
            for (Future<?> future : futures) {
                future.get(30, TimeUnit.SECONDS);
            }
        } finally {
            pool.shutdownNow();
        }

        assertThat(total).hasValue(1_800);
        assertThat(maxInside).as("同一個 run 同時只有一個執行緒在臨界區").hasValue(1);
    }

    @Test
    void theLockIsReentrantSoAReviewDecisionCanCallAControlOperationWhileHoldingIt() {
        RunRegistry registry = new RunRegistry();
        UUID run = UUID.randomUUID();

        String result = registry.locked(run, () -> registry.locked(run, () -> "inner"));
        List<String> order = new ArrayList<>();
        registry.locked(run, () -> {
            order.add("outer-start");
            registry.locked(run, () -> order.add("inner"));
            order.add("outer-end");
        });

        assertThat(result).isEqualTo("inner");
        assertThat(order).containsExactly("outer-start", "inner", "outer-end");
    }

    @Test
    void aRunHoldingItsLockNeverBlocksAnotherRun() throws Exception {
        RunRegistry registry = new RunRegistry();
        UUID busy = UUID.randomUUID();
        UUID other = UUID.randomUUID();
        CountDownLatch holding = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        ExecutorService pool = Executors.newSingleThreadExecutor();
        try {
            Future<?> holder = pool.submit(() -> registry.locked(busy, () -> {
                holding.countDown();
                try {
                    release.await(10, TimeUnit.SECONDS);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }));
            assertThat(holding.await(5, TimeUnit.SECONDS)).isTrue();

            long start = System.nanoTime();
            String value = registry.locked(other, () -> "free");

            assertThat(value).isEqualTo("free");
            assertThat(Duration.ofNanos(System.nanoTime() - start)).isLessThan(Duration.ofSeconds(2));
            release.countDown();
            holder.get(5, TimeUnit.SECONDS);
        } finally {
            release.countDown();
            pool.shutdownNow();
        }
    }

    @Test
    void theRuntimeOfARunIsCreatedOnceAndForgottenWithItsLock() {
        RunRegistry registry = new RunRegistry();
        UUID run = UUID.randomUUID();

        Runtime first = registry.runtime(run);
        first.currentStepId = "G1-T1";
        first.gatePausedPositions.add(2);

        assertThat(registry.runtime(run)).isSameAs(first);
        assertThat(registry.runtime(UUID.randomUUID())).isNotSameAs(first);
        registry.forget(run);
        Runtime fresh = registry.runtime(run);
        assertThat(fresh).isNotSameAs(first);
        assertThat(fresh.currentStepId).isNull();
        assertThat(fresh.gatePausedPositions).isEmpty();
        assertThat(registry.locked(run, () -> "lock still usable after forget")).isNotBlank();
    }

    // ── traceId（契約 §0.4 第 6 點，C-12）：背景呼叫 Bridge 時沿用啟動該 run 的請求的 traceId ─────────────

    @Test
    void aBoundTraceIdIsReturnedAsIsAndABlankOrMissingOneBindsNothing() {
        RunRegistry registry = new RunRegistry();
        UUID run = UUID.randomUUID();

        registry.bindTrace(run, "trace-from-execute");
        assertThat(registry.traceIdOf(run)).isEqualTo("trace-from-execute");

        UUID other = UUID.randomUUID();
        registry.bindTrace(other, null);
        registry.bindTrace(other, "  ");
        assertThat(registry.runtime(other).traceId.get()).as("沒有請求上下文（null／空白）就什麼都不綁").isNull();
    }

    @Test
    void anUnboundRunGetsOneGeneratedUuidThatIsThenRememberedForEveryLaterCall() {
        RunRegistry registry = new RunRegistry();
        UUID run = UUID.randomUUID();

        String first = registry.traceIdOf(run);

        assertThat(UUID.fromString(first)).isNotNull();
        assertThat(registry.traceIdOf(run)).isEqualTo(first);
        assertThat(registry.traceIdOf(UUID.randomUUID())).as("各 run 各自一個").isNotEqualTo(first);
    }

    @Test
    void concurrentFirstCallsAgreeOnASingleGeneratedTraceId() throws Exception {
        RunRegistry registry = new RunRegistry();
        UUID run = UUID.randomUUID();
        ExecutorService pool = Executors.newFixedThreadPool(8);
        try {
            List<Future<String>> futures = new ArrayList<>();
            for (int i = 0; i < 8; i++) {
                futures.add(pool.submit(() -> registry.traceIdOf(run)));
            }
            List<String> seen = new ArrayList<>();
            for (Future<String> future : futures) {
                seen.add(future.get(10, TimeUnit.SECONDS));
            }

            assertThat(seen).as("消費者與對帳同時第一次取用，也只會有一個值").containsOnly(seen.get(0));
        } finally {
            pool.shutdownNow();
        }
    }

    @Test
    void forgettingARunAlsoForgetsItsTraceId() {
        RunRegistry registry = new RunRegistry();
        UUID run = UUID.randomUUID();
        registry.bindTrace(run, "trace-from-execute");

        registry.forget(run);

        assertThat(registry.traceIdOf(run)).isNotEqualTo("trace-from-execute");
    }
}
