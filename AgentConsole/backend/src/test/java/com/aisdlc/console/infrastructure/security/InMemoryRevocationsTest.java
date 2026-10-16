package com.aisdlc.console.infrastructure.security;

import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 單實例記憶體撤銷名單（契約 §1.9.2；D-19）。為什麼重要：這是 Redis 不在線時（以及沒設 Redis 的本機與 e2e）唯一擋住「被竊的 refresh token
 * 在登出或換新之後還能用」的東西；{@code tryRevoke} 若不是原子的，同一個 refresh token 的兩個併發換新會雙雙成功（換出兩對有效 token）；
 * 項目若不依 {@code exp} 清除，名單只增不減（記憶體洩漏）。
 */
class InMemoryRevocationsTest {

    /** 由測試撥動的時鐘。 */
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

    private final MutableClock clock = new MutableClock();
    private final InMemoryRefreshTokenRevocations revocations = new InMemoryRefreshTokenRevocations(clock);

    @Test
    void theFirstRevocationWinsAndLaterOnesAreToldAlreadyRevoked() {
        Instant exp = clock.instant().plusSeconds(3600);

        assertThat(revocations.tryRevoke("jti-1", exp)).isTrue();
        assertThat(revocations.tryRevoke("jti-1", exp)).isFalse();
        assertThat(revocations.tryRevoke("jti-1", exp)).isFalse();
        assertThat(revocations.tryRevoke("jti-2", exp)).as("別的 token 不受影響").isTrue();
        assertThat(revocations.contains("jti-1")).isTrue();
        assertThat(revocations.contains("never-seen")).isFalse();
    }

    @Test
    void anEntryLivesUntilTheExpiryOfItsTokenAndThenTheNameIsFree() {
        revocations.tryRevoke("jti-1", clock.instant().plusSeconds(60));

        clock.advanceSeconds(59);
        assertThat(revocations.contains("jti-1")).as("exp 之前仍在名單內").isTrue();
        assertThat(revocations.tryRevoke("jti-1", clock.instant().plusSeconds(1))).isFalse();

        clock.advanceSeconds(2);
        assertThat(revocations.contains("jti-1")).as("過了 exp：token 本來就被拒，不必再記").isFalse();
        assertThat(revocations.tryRevoke("jti-1", clock.instant().plusSeconds(60))).as("惰性清除：名字可以再被撤銷").isTrue();
    }

    @Test
    void anEntryIsKeptAtLeastOneSecond() {
        revocations.tryRevoke("about-to-expire", clock.instant().plusMillis(100));
        revocations.tryRevoke("already-expired", clock.instant().minusSeconds(30));

        assertThat(revocations.contains("about-to-expire")).as("max(exp − 現在, 1 秒)").isTrue();
        assertThat(revocations.contains("already-expired")).isTrue();

        clock.advanceSeconds(2);
        assertThat(revocations.contains("about-to-expire")).isFalse();
        assertThat(revocations.contains("already-expired")).isFalse();
    }

    @Test
    void theListIsSweptAboutEveryTenMinutesSoItDoesNotGrowForever() {
        for (int i = 0; i < 50; i++) {
            revocations.tryRevoke("short-" + i, clock.instant().plusSeconds(120));
        }
        revocations.tryRevoke("long", clock.instant().plusSeconds(86_400));
        assertThat(revocations.size()).isEqualTo(51);

        clock.advanceSeconds(11 * 60);
        revocations.tryRevoke("trigger", clock.instant().plusSeconds(60));

        assertThat(revocations.size()).as("50 筆短命項目已過期被掃掉，剩長命的與剛加入的").isEqualTo(2);
        assertThat(revocations.contains("long")).isTrue();
    }

    @Test
    void ofManyConcurrentRevocationsOfOneTokenExactlyOneWins() throws Exception {
        int threads = 8;
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        try {
            for (int round = 0; round < 50; round++) {
                String jti = "race-" + round;
                CyclicBarrier start = new CyclicBarrier(threads);
                List<Future<Boolean>> results = new ArrayList<>();
                for (int t = 0; t < threads; t++) {
                    results.add(pool.submit(() -> {
                        start.await(5, TimeUnit.SECONDS);
                        return revocations.tryRevoke(jti, clock.instant().plusSeconds(3600));
                    }));
                }
                int winners = 0;
                for (Future<Boolean> result : results) {
                    winners += result.get(10, TimeUnit.SECONDS) ? 1 : 0;
                }
                assertThat(winners).as("round " + round).isEqualTo(1);
            }
        } finally {
            pool.shutdownNow();
        }
    }
}
