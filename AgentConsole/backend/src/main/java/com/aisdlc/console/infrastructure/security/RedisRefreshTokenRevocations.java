package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.application.port.out.RefreshTokenRevocations;
import org.springframework.data.redis.core.StringRedisTemplate;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;

/**
 * Redis 撤銷名單（Lettuce；契約 §1.9.2；D-19）：鍵 {@code console:revoked-refresh:<jti>}、值 {@code 1}、TTL＝{@code max(exp − 現在, 1 秒)}。
 * {@code tryRevoke} 是 {@code SET key 1 NX EX ttl}——原子，所以同一個 refresh token 的兩個併發換新只有一個成功。
 *
 * <p>連線失敗、逾時或任何 Redis 例外一律<b>往外丟</b>（不吞）：由 {@link ResilientRefreshTokenRevocations} 決定降級。本類別不記日誌，
 * 免得 Redis 掛掉時每次呼叫都灌一行。
 */
public final class RedisRefreshTokenRevocations implements RefreshTokenRevocations {

    static final String KEY_PREFIX = "console:revoked-refresh:";
    private static final Duration MIN_TTL = Duration.ofSeconds(1);

    private final StringRedisTemplate redis;
    private final Clock clock;

    public RedisRefreshTokenRevocations(StringRedisTemplate redis, Clock clock) {
        this.redis = redis;
        this.clock = clock;
    }

    @Override
    public boolean tryRevoke(String tokenId, Instant expiresAt) {
        Duration remaining = Duration.between(clock.instant(), expiresAt);
        Duration ttl = remaining.compareTo(MIN_TTL) < 0 ? MIN_TTL : remaining;
        Boolean first = redis.opsForValue().setIfAbsent(KEY_PREFIX + tokenId, "1", ttl);
        if (first == null) {
            // 只有在管線或交易裡才會是 null；這裡不是——回 null 代表 Redis 行為異常，當成故障交給降級包裝處理
            throw new IllegalStateException("Redis 對 SET NX 回了 null");
        }
        return first;
    }
}
