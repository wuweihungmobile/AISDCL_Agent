package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.application.port.out.RefreshTokenRevocations;
import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.SharedRedis;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * refresh token 撤銷名單的 Redis 實作，對<b>真的 Redis</b>（Testcontainers；契約 §1.9.2；D-19；ADR-001 D16、D23）。
 * 為什麼重要：撤銷的原子性（{@code SET key 1 NX EX ttl}）與 TTL（到 token 的 {@code exp} 為止）只有真 Redis 才驗得到——
 * 記憶體實作與 Mockito 替身都不會顯示「兩個併發換新只有一個成功」或「項目會自己消失」。降級（Redis 不在線）見 {@code RefreshRevocationRedisDownIT}。
 */
class RefreshRevocationRedisIT extends AbstractApiIT {

    private static final String PREFIX = "console:revoked-refresh:";

    @DynamicPropertySource
    static void realRedis(DynamicPropertyRegistry registry) {
        registry.add("spring.data.redis.host", SharedRedis::host);
        registry.add("spring.data.redis.port", SharedRedis::port);
        registry.add("console.security.refresh-revocation.store", () -> "auto");
    }

    @Autowired
    StringRedisTemplate redis;

    @Autowired
    RefreshTokenRevocations revocations;

    @AfterEach
    void emptyTheRevocationKeys() {
        Set<String> keys = redis.keys(PREFIX + "*");
        if (keys != null && !keys.isEmpty()) {
            redis.delete(keys);
        }
    }

    private Resp login() {
        return api.post(null, "/api/v1/auth/login", Map.of("username", "operator", "password", "Operator#Dev2026"));
    }

    private Resp refresh(String refreshToken) {
        return api.post(null, "/api/v1/auth/refresh", Map.of("refreshToken", refreshToken));
    }

    private static String jtiOf(String jwt) {
        String payload = new String(Base64.getUrlDecoder().decode(jwt.split("\\.")[1]), StandardCharsets.UTF_8);
        return JsonPath.read(payload, "$.jti");
    }

    @Test
    void aHostMakesRedisThePreferredStoreWithTheMemoryFallbackBehindIt() {
        assertThat(revocations).isInstanceOf(ResilientRefreshTokenRevocations.class);
    }

    @Test
    void rotationAndLogoutWriteTheDocumentedKeysWithAboutSevenDaysOfTtl() {
        String rt1 = login().read("$.data.refreshToken");
        String rt2 = refresh(rt1).read("$.data.refreshToken");

        assertThat(redis.hasKey(PREFIX + jtiOf(rt1))).as("換新時舊的被撤銷").isTrue();
        assertThat(redis.hasKey(PREFIX + jtiOf(rt2))).as("新的還有效，不在名單內").isFalse();
        assertThat(redis.opsForValue().get(PREFIX + jtiOf(rt1))).isEqualTo("1");
        Long ttlSeconds = redis.getExpire(PREFIX + jtiOf(rt1), TimeUnit.SECONDS);
        assertThat(ttlSeconds).as("TTL＝到 token 的 exp 為止（7 天）").isBetween(7L * 86_400 - 120, 7L * 86_400);

        assertThat(api.post(null, "/api/v1/auth/logout", Map.of("refreshToken", rt2)).status()).isEqualTo(204);
        assertThat(redis.hasKey(PREFIX + jtiOf(rt2))).as("登出撤銷目前的 refresh token").isTrue();

        assertThat(refresh(rt1).status()).isEqualTo(401);
        assertThat(refresh(rt2).status()).isEqualTo(401);
    }

    @Test
    void anAlreadyRevokedTokenIsNeverRevokedTwiceAndKeepsItsOriginalExpiry() {
        String rt = login().read("$.data.refreshToken");
        assertThat(api.post(null, "/api/v1/auth/logout", Map.of("refreshToken", rt)).status()).isEqualTo(204);
        Long first = redis.getExpire(PREFIX + jtiOf(rt), TimeUnit.MILLISECONDS);

        assertThat(api.post(null, "/api/v1/auth/logout", Map.of("refreshToken", rt)).status()).isEqualTo(204);

        assertThat(redis.getExpire(PREFIX + jtiOf(rt), TimeUnit.MILLISECONDS)).as("SET NX：第二次不改寫").isLessThanOrEqualTo(first);
    }

    @Test
    void ofManyConcurrentRefreshesOfOneTokenRedisLetsExactlyOneThrough() throws Exception {
        int threads = 6;
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        try {
            for (int round = 0; round < 10; round++) {
                String rt = login().read("$.data.refreshToken");
                CyclicBarrier start = new CyclicBarrier(threads);
                List<Future<Integer>> statuses = new ArrayList<>();
                for (int i = 0; i < threads; i++) {
                    statuses.add(pool.submit(() -> {
                        start.await(5, TimeUnit.SECONDS);
                        return refresh(rt).status();
                    }));
                }
                int ok = 0;
                for (Future<Integer> status : statuses) {
                    ok += status.get(30, TimeUnit.SECONDS) == 200 ? 1 : 0;
                }
                assertThat(ok).as("round " + round).isEqualTo(1);
            }
        } finally {
            pool.shutdownNow();
        }
    }

    @Test
    void theKeyOfATokenThatIsAboutToExpireStillLivesAtLeastOneSecond() {
        RedisRefreshTokenRevocations direct = new RedisRefreshTokenRevocations(redis, Clock.systemUTC());

        assertThat(direct.tryRevoke("about-to-expire", Instant.now().minusSeconds(30))).isTrue();

        Long ttlMillis = redis.getExpire(PREFIX + "about-to-expire", TimeUnit.MILLISECONDS);
        assertThat(ttlMillis).as("max(exp − 現在, 1 秒)").isBetween(1L, Duration.ofSeconds(1).toMillis());
        assertThat(direct.tryRevoke("about-to-expire", Instant.now().plusSeconds(60))).as("還在 TTL 內：已撤銷").isFalse();
    }
}
