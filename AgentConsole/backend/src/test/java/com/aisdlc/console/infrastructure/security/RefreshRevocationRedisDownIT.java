package com.aisdlc.console.infrastructure.security;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.application.port.out.RefreshTokenRevocations;
import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.TestPropertySource;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 「Redis 不在線仍可登出與換新」（契約 §1.9.2；D-19；ADR-001 D16 的承諾）。設了 {@code spring.data.redis.host} 但那個位址沒有 Redis
 * （埠 1，連線立刻被拒）：登入、換新、登出都必須照常運作，撤銷仍然有效（改記在單實例記憶體），{@code /actuator/health} 仍是 UP（沒有 Redis 健康指標），
 * 而且整段中斷只在日誌留<b>一行</b> WARN——不是每個請求一行。
 */
@TestPropertySource(properties = {"spring.data.redis.host=127.0.0.1", "spring.data.redis.port=1",
        "console.security.refresh-revocation.store=redis"})
class RefreshRevocationRedisDownIT extends AbstractApiIT {

    @Autowired
    RefreshTokenRevocations revocations;

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

    private Resp login() {
        return api.post(null, "/api/v1/auth/login", Map.of("username", "operator", "password", "Operator#Dev2026"));
    }

    private Resp refresh(String refreshToken) {
        return api.post(null, "/api/v1/auth/refresh", Map.of("refreshToken", refreshToken));
    }

    private Resp logout(String refreshToken) {
        return api.post(null, "/api/v1/auth/logout", Map.of("refreshToken", refreshToken));
    }

    @Test
    void theStoreIsRedisFirstNotMemoryOnly() {
        assertThat(revocations).isInstanceOf(ResilientRefreshTokenRevocations.class);
    }

    @Test
    void refreshAndLogoutKeepWorkingAndKeepRevokingWithoutRedis() {
        String rt1 = login().read("$.data.refreshToken");

        Resp rotated = refresh(rt1);
        assertThat(rotated.status()).as("Redis 不在線：換新照常").isEqualTo(200);
        String rt2 = rotated.read("$.data.refreshToken");

        Resp replay = refresh(rt1);
        assertThat(replay.status()).as("降級後撤銷仍有效（記在記憶體）").isEqualTo(401);
        assertThat(replay.<String>read("$.reason")).isEqualTo("INVALID_REFRESH_TOKEN");

        assertThat(logout(rt2).status()).as("Redis 不在線：登出照常").isEqualTo(204);
        assertThat(refresh(rt2).status()).as("登出後不能再換新").isEqualTo(401);
    }

    @Test
    void healthStaysUpAndHasNoRedisIndicator() {
        refresh(login().<String>read("$.data.refreshToken"));

        Resp health = api.get(null, "/actuator/health");

        assertThat(health.status()).isEqualTo(200);
        assertThat(health.<String>read("$.status")).isEqualTo("UP");
        assertThat(health.body()).doesNotContainIgnoringCase("redis");
    }

    /**
     * 進入降級的那一次 WARN 發生在這個 context 的<b>第一個</b>撤銷請求，可能早於本測試開始記錄（同一個類別的其他測試先跑），所以這裡只釘
     * 「不是每個請求一行」：45 次經過撤銷名單的呼叫最多一行 WARN。「進入降級恰好一次、恢復恰好一次」的精確斷言在
     * {@code ResilientRevocationsTest}（可控制 Redis 與時鐘的替身）。
     */
    @Test
    void theOutageIsNeverLoggedPerRequest() {
        for (int i = 0; i < 15; i++) {
            String rt = login().read("$.data.refreshToken");
            refresh(rt);
            logout(rt);
        }

        assertThat(logs.list).filteredOn(event -> event.getLevel() == Level.WARN).hasSizeLessThanOrEqualTo(1)
                .allSatisfy(event -> assertThat(event.getFormattedMessage()).contains("Redis").contains("降級"));
    }

    @Test
    void concurrentRefreshesStillLetExactlyOneThroughInMemory() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            for (int round = 0; round < 10; round++) {
                String rt = login().read("$.data.refreshToken");
                CyclicBarrier start = new CyclicBarrier(2);
                List<Future<Integer>> statuses = new ArrayList<>();
                for (int i = 0; i < 2; i++) {
                    statuses.add(pool.submit(() -> {
                        start.await(5, TimeUnit.SECONDS);
                        return refresh(rt).status();
                    }));
                }
                List<Integer> result = new ArrayList<>();
                for (Future<Integer> status : statuses) {
                    result.add(status.get(30, TimeUnit.SECONDS));
                }
                assertThat(result).as("round " + round).containsExactlyInAnyOrder(200, 401);
            }
        } finally {
            pool.shutdownNow();
        }
    }
}
