package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.application.port.out.RefreshTokenRevocations;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Redis 優先、不在線降級為單實例記憶體的撤銷名單（契約 §1.9.2；D-19；ADR-001 D16「Redis 不在線仍可用」的承諾）。
 *
 * <ul>
 *   <li><b>先問記憶體</b>：降級期間在記憶體撤銷的 {@code jti} 在 Redis 恢復後<b>不回補</b>到 Redis，所以每次都先查記憶體名單（便宜的 map 查詢）；
 *       在名單內＝已撤銷（false）。</li>
 *   <li><b>再問 Redis</b>：任何例外（連線失敗、逾時、{@code DataAccessException}…）＝降級：改用記憶體撤銷並回傳它的結果。</li>
 *   <li><b>日誌只在狀態轉換時記</b>：進入降級 WARN 一次、恢復 INFO 一次——Redis 掛掉期間每個登入／換新都會經過這裡，逐次記會把日誌灌爆。</li>
 *   <li><b>降級後不每次都撞牆</b>：降級期間 {@value #RETRY_SECONDS} 秒才再試一次 Redis，其餘呼叫直接走記憶體（否則每個請求都要等一次連線逾時）。</li>
 * </ul>
 */
public final class ResilientRefreshTokenRevocations implements RefreshTokenRevocations {

    static final int RETRY_SECONDS = 30;
    private static final Duration RETRY_AFTER = Duration.ofSeconds(RETRY_SECONDS);
    private static final Logger LOG = LoggerFactory.getLogger(ResilientRefreshTokenRevocations.class);

    private final RefreshTokenRevocations redis;
    private final InMemoryRefreshTokenRevocations memory;
    private final Clock clock;
    private final AtomicBoolean degraded = new AtomicBoolean(false);
    private final AtomicReference<Instant> nextRedisAttempt = new AtomicReference<>(Instant.MIN);

    public ResilientRefreshTokenRevocations(RefreshTokenRevocations redis, InMemoryRefreshTokenRevocations memory,
                                            Clock clock) {
        this.redis = redis;
        this.memory = memory;
        this.clock = clock;
    }

    @Override
    public boolean tryRevoke(String tokenId, Instant expiresAt) {
        if (memory.contains(tokenId)) {
            return false;
        }
        Instant now = clock.instant();
        if (degraded.get() && now.isBefore(nextRedisAttempt.get())) {
            return memory.tryRevoke(tokenId, expiresAt);
        }
        try {
            boolean first = redis.tryRevoke(tokenId, expiresAt);
            if (degraded.compareAndSet(true, false)) {
                LOG.info("refresh token 撤銷名單：Redis 已恢復，新的撤銷改寫回 Redis（降級期間記在記憶體的項目仍會被查到，直到它們自己的 exp）");
            }
            return first;
        } catch (RuntimeException e) {
            nextRedisAttempt.set(now.plus(RETRY_AFTER));
            if (degraded.compareAndSet(false, true)) {
                LOG.warn("refresh token 撤銷名單：Redis 不可用，降級為單實例記憶體名單（降級期間的撤銷只對本實例有效，Redis 恢復後不回補）：{}",
                        e.toString());
            }
            return memory.tryRevoke(tokenId, expiresAt);
        }
    }

    /** 目前是否處於降級狀態；測試與診斷用。 */
    boolean degraded() {
        return degraded.get();
    }
}
