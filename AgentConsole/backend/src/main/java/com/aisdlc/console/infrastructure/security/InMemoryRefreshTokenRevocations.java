package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.application.port.out.RefreshTokenRevocations;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 單實例記憶體撤銷名單（契約 §1.9.2；D-19）：{@code ConcurrentHashMap<jti, 到期時間>}。
 *
 * <p>兩種用途：①{@code store=memory} 或 {@code auto} 且沒設 {@code spring.data.redis.host} 時的唯一實作（本機開發、e2e、單元測試）；
 * ②Redis 不在線時 {@link ResilientRefreshTokenRevocations} 的降級後備。<b>已知限制</b>（契約 §1.9.2 已知限制②）：只對本實例有效、隨行程重啟清空——
 * 重啟前已登出、尚未過期的 refresh token 在重啟後復活；降級期間在這裡撤銷的 {@code jti}，Redis 恢復後也<b>不回補</b>到 Redis
 * （這份名單繼續查到它們自己的 {@code exp}）。Console 目前是單實例部署（Architecture §2），這個限制可接受；多實例前須改成只認 Redis。
 *
 * <p>清除：讀取時惰性清除（過了 {@code exp} 的項目視為不存在、被新的撤銷覆寫），另每 {@value #SWEEP_MINUTES} 分鐘在呼叫路徑上順手掃一次
 * （不另開執行緒）。{@code tryRevoke} 是原子的：{@code ConcurrentHashMap.compute} 保證兩個併發撤銷同一個 {@code jti} 只有一個拿到 true。
 */
public final class InMemoryRefreshTokenRevocations implements RefreshTokenRevocations {

    static final int SWEEP_MINUTES = 10;
    private static final Duration SWEEP_INTERVAL = Duration.ofMinutes(SWEEP_MINUTES);
    /** 項目至少保留多久（契約：{@code max(exp − 現在, 1 秒)}）。 */
    private static final Duration MIN_TTL = Duration.ofSeconds(1);

    private final Clock clock;
    private final ConcurrentHashMap<String, Instant> revoked = new ConcurrentHashMap<>();
    private final AtomicReference<Instant> nextSweep;

    public InMemoryRefreshTokenRevocations(Clock clock) {
        this.clock = clock;
        this.nextSweep = new AtomicReference<>(clock.instant().plus(SWEEP_INTERVAL));
    }

    @Override
    public boolean tryRevoke(String tokenId, Instant expiresAt) {
        Instant now = clock.instant();
        sweepIfDue(now);
        Instant keepUntil = expiresAt.isAfter(now.plus(MIN_TTL)) ? expiresAt : now.plus(MIN_TTL);
        AtomicBoolean first = new AtomicBoolean(false);
        revoked.compute(tokenId, (id, current) -> {
            if (current != null && current.isAfter(now)) {
                return current;
            }
            first.set(true);
            return keepUntil;
        });
        return first.get();
    }

    /** 這個 {@code jti} 現在是否仍在名單內（降級包裝在 Redis 恢復後仍要先問它：降級期間撤銷的項目不會回補到 Redis）。 */
    boolean contains(String tokenId) {
        Instant keepUntil = revoked.get(tokenId);
        return keepUntil != null && keepUntil.isAfter(clock.instant());
    }

    /** 目前名單裡（含尚未被掃掉的過期）的項目數；測試與診斷用。 */
    int size() {
        return revoked.size();
    }

    private void sweepIfDue(Instant now) {
        Instant due = nextSweep.get();
        if (now.isBefore(due) || !nextSweep.compareAndSet(due, now.plus(SWEEP_INTERVAL))) {
            return;
        }
        revoked.values().removeIf(keepUntil -> !keepUntil.isAfter(now));
    }
}
