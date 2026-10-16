package com.aisdlc.console.infrastructure.security;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.application.port.out.RefreshTokenRevocations;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.RedisConnectionFailureException;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

/**
 * Redis 優先、不在線降級為記憶體的撤銷名單（契約 §1.9.2；D-19；ADR-001 D16 的承諾「Redis 不在線仍可用」）。為什麼重要：登出與換新是
 * 每個使用者每天都會碰的路徑，Redis 掛掉不能讓它們跟著壞；但降級之後撤銷仍要有效（否則被登出的 token 照用），而且日誌只能在狀態轉換時記——
 * Redis 掛掉期間每個登入與換新都會經過這裡，逐次記一行會把日誌灌爆。用丟 {@code RedisConnectionFailureException} 的替身驗，不需真 Redis。
 */
class ResilientRevocationsTest {

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
    private final RefreshTokenRevocations redis = mock(RefreshTokenRevocations.class);
    private final InMemoryRefreshTokenRevocations memory = new InMemoryRefreshTokenRevocations(clock);
    private final ResilientRefreshTokenRevocations resilient = new ResilientRefreshTokenRevocations(redis, memory, clock);
    private final ListAppender<ILoggingEvent> logs = new ListAppender<>();
    private Logger logger;

    @BeforeEach
    void captureLogs() {
        logger = (Logger) LoggerFactory.getLogger(ResilientRefreshTokenRevocations.class);
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

    private Instant exp() {
        return clock.instant().plusSeconds(3600);
    }

    private void redisDown() {
        doThrow(new RedisConnectionFailureException("Unable to connect to Redis")).when(redis).tryRevoke(anyString(), any());
    }

    private long count(Level level) {
        return logs.list.stream().filter(event -> event.getLevel() == level).count();
    }

    @Test
    void whileRedisIsUpEveryAnswerComesFromRedisAndNothingIsLogged() {
        doReturn(true).when(redis).tryRevoke("jti-1", exp());
        doReturn(false).when(redis).tryRevoke("jti-2", exp());

        assertThat(resilient.tryRevoke("jti-1", exp())).isTrue();
        assertThat(resilient.tryRevoke("jti-2", exp())).as("Redis 說已被撤銷").isFalse();

        assertThat(memory.size()).isZero();
        assertThat(logs.list).isEmpty();
    }

    @Test
    void whenRedisFailsTheRevocationFallsBackToMemory() {
        redisDown();

        assertThat(resilient.tryRevoke("jti-1", exp())).isTrue();
        assertThat(resilient.tryRevoke("jti-1", exp())).as("同一個 token 第二次：記憶體說已撤銷").isFalse();
        assertThat(resilient.tryRevoke("jti-2", exp())).isTrue();
        assertThat(memory.contains("jti-1")).isTrue();
        assertThat(resilient.degraded()).isTrue();
    }

    @Test
    void enteringTheDegradedStateIsLoggedExactlyOnceNoMatterHowManyCallsFollow() {
        redisDown();

        for (int i = 0; i < 50; i++) {
            resilient.tryRevoke("jti-" + i, exp());
            clock.advanceSeconds(1);
        }

        assertThat(count(Level.WARN)).as("進入降級只記一次 WARN（Redis 掛掉期間每個登入與換新都經過這裡）").isEqualTo(1);
        assertThat(logs.list).filteredOn(event -> event.getLevel() == Level.WARN).singleElement()
                .satisfies(event -> assertThat(event.getFormattedMessage()).contains("降級").contains("Redis"));
        assertThat(count(Level.INFO)).isZero();
    }

    @Test
    void whileDegradedRedisIsRetriedOnlyAfterTheBackoff() {
        redisDown();
        resilient.tryRevoke("jti-1", exp());
        verify(redis, times(1)).tryRevoke(anyString(), any());

        for (int i = 0; i < 20; i++) {
            resilient.tryRevoke("later-" + i, exp());
        }
        verify(redis, times(1)).tryRevoke(anyString(), any());

        clock.advanceSeconds(ResilientRefreshTokenRevocations.RETRY_SECONDS + 1);
        resilient.tryRevoke("after-the-backoff", exp());
        verify(redis, times(2)).tryRevoke(anyString(), any());
        assertThat(count(Level.WARN)).as("再試仍失敗：沒有狀態轉換，不再記").isEqualTo(1);
    }

    @Test
    void whenRedisComesBackItIsLoggedOnceAndNewRevocationsGoToRedisAgain() {
        redisDown();
        resilient.tryRevoke("during-the-outage", exp());
        org.mockito.Mockito.reset(redis);
        doReturn(true).when(redis).tryRevoke(anyString(), any());
        clock.advanceSeconds(ResilientRefreshTokenRevocations.RETRY_SECONDS + 1);

        assertThat(resilient.tryRevoke("after-recovery", exp())).isTrue();
        assertThat(resilient.tryRevoke("another", exp())).isTrue();

        assertThat(resilient.degraded()).isFalse();
        assertThat(count(Level.INFO)).as("恢復只記一次 INFO").isEqualTo(1);
        verify(redis, times(2)).tryRevoke(anyString(), any());
        assertThat(memory.contains("after-recovery")).as("恢復後的新撤銷寫進 Redis，不再寫記憶體").isFalse();
    }

    @Test
    void anOutageRevocationSurvivesRedisRecoveryBecauseItIsNeverBackfilled() {
        redisDown();
        assertThat(resilient.tryRevoke("revoked-while-down", exp())).isTrue();
        org.mockito.Mockito.reset(redis);
        doReturn(true).when(redis).tryRevoke(anyString(), any());
        clock.advanceSeconds(ResilientRefreshTokenRevocations.RETRY_SECONDS + 1);

        assertThat(resilient.tryRevoke("revoked-while-down", exp()))
                .as("Redis 沒有這一筆（不回補），但記憶體名單繼續查到它自己的 exp：仍是已撤銷").isFalse();
        verify(redis, never()).tryRevoke(eq("revoked-while-down"), any());
    }

    @Test
    void anyRuntimeExceptionCountsAsRedisBeingDownNotOnlyConnectionFailures() {
        doThrow(new IllegalStateException("Redis 對 SET NX 回了 null")).when(redis).tryRevoke(anyString(), any());

        assertThat(resilient.tryRevoke("jti-1", exp())).isTrue();
        assertThat(resilient.degraded()).isTrue();
    }
}
