package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.infrastructure.security.RateLimiter.Decision;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 限流器（NFR-9.2-06；契約 §0.4 第 4 點）。為什麼重要：「第 101 次一定回 429」不能取決於機器速度——所以是固定視窗，
 * 不是貪婪補充；視窗從該鍵視窗期滿後的第一個請求起算，{@code Retry-After}＝距視窗結束的秒數。
 */
class RateLimiterTest {

    /** 可調的時鐘。 */
    private static final class MutableClock extends Clock {
        private Instant now = Instant.parse("2026-10-15T08:00:00Z");

        void advance(Duration duration) {
            now = now.plus(duration);
        }

        @Override
        public ZoneOffset getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(java.time.ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return now;
        }
    }

    private final MutableClock clock = new MutableClock();
    private final RateLimiter limiter = new RateLimiter(100, Duration.ofSeconds(60), clock);

    @Test
    void theFirstHundredRequestsPassWithADecreasingRemainingCountAndTheHundredAndFirstIsDenied() {
        for (int i = 1; i <= 100; i++) {
            Decision decision = limiter.tryConsume("u:viewer");
            assertThat(decision.allowed()).as("第 " + i + " 次").isTrue();
            assertThat(decision.remaining()).isEqualTo(100 - i);
        }
        Decision denied = limiter.tryConsume("u:viewer");
        assertThat(denied.allowed()).isFalse();
        assertThat(denied.remaining()).isZero();
        assertThat(denied.retryAfterSeconds()).isBetween(1L, 60L);
    }

    @Test
    void theHundredAndFirstIsDeniedEvenWhenTheBurstTakesAlmostAWholeWindow() {
        for (int i = 0; i < 100; i++) {
            assertThat(limiter.tryConsume("k").allowed()).isTrue();
            clock.advance(Duration.ofMillis(590));     // 貪婪補充每 600ms 補 1 個：這裡每次都夠補一個也不會被放行
        }
        // 58.999 秒後：仍在視窗內
        assertThat(limiter.tryConsume("k").allowed()).as("固定視窗內第 101 次仍被拒").isFalse();
    }

    @Test
    void retryAfterIsTheWholeSecondsLeftInTheWindowRoundedUpAndNeverBelowOne() {
        for (int i = 0; i < 100; i++) {
            limiter.tryConsume("k");
        }
        clock.advance(Duration.ofSeconds(20));
        assertThat(limiter.tryConsume("k").retryAfterSeconds()).isEqualTo(40L);
        clock.advance(Duration.ofMillis(39_500));
        assertThat(limiter.tryConsume("k").retryAfterSeconds()).isEqualTo(1L);
    }

    @Test
    void afterTheWindowEndsTheNextRequestStartsAFreshWindow() {
        for (int i = 0; i < 101; i++) {
            limiter.tryConsume("k");
        }
        clock.advance(Duration.ofSeconds(60));
        Decision fresh = limiter.tryConsume("k");
        assertThat(fresh.allowed()).isTrue();
        assertThat(fresh.remaining()).isEqualTo(99);
        assertThat(fresh.retryAfterSeconds()).isEqualTo(60L);
    }

    @Test
    void differentKeysHaveIndependentBuckets() {
        for (int i = 0; i < 100; i++) {
            limiter.tryConsume("u:viewer");
        }
        assertThat(limiter.tryConsume("u:viewer").allowed()).isFalse();
        assertThat(limiter.tryConsume("u:operator").allowed()).as("另一個使用者不受影響").isTrue();
        assertThat(limiter.tryConsume("ip:203.0.113.7").allowed()).as("IP 鍵空間獨立").isTrue();
    }

    @Test
    void theLimitAndWindowAreExposedForTheResponseHeaders() {
        assertThat(limiter.limit()).isEqualTo(100);
        assertThat(limiter.windowSeconds()).isEqualTo(60L);
    }

    @Test
    void concurrentRequestsNeverAdmitMoreThanTheLimit() throws InterruptedException {
        RateLimiter shared = new RateLimiter(100, Duration.ofSeconds(60), Clock.systemUTC());
        java.util.concurrent.atomic.AtomicInteger allowed = new java.util.concurrent.atomic.AtomicInteger();
        java.util.List<Thread> threads = new java.util.ArrayList<>();
        for (int t = 0; t < 8; t++) {
            Thread thread = new Thread(() -> {
                for (int i = 0; i < 50; i++) {
                    if (shared.tryConsume("hot").allowed()) {
                        allowed.incrementAndGet();
                    }
                }
            });
            threads.add(thread);
            thread.start();
        }
        for (Thread thread : threads) {
            thread.join();
        }
        assertThat(allowed.get()).isEqualTo(100);
    }
}
