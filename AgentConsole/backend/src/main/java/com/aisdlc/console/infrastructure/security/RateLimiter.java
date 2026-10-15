package com.aisdlc.console.infrastructure.security;

import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Bucket;
import io.github.bucket4j.ConsumptionProbe;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 記憶體內的限流器（NFR-9.2-06；契約 §0.4 第 4 點）：每個鍵每個固定視窗最多 {@code limit} 次。
 *
 * <p>為什麼是「固定視窗」而不是「貪婪補充」的 token bucket：貪婪補充（每 0.6 秒補 1 個）讓連續 100 次請求跑超過 0.6 秒
 * 時第 101 次仍會成功，「第 101 次回 429」（E2E-11）就變成取決於機器速度的賽局。這裡視窗從<b>該鍵視窗期滿後的第一個請求</b>
 * 起算、固定 {@code window} 長；視窗內計數由 Bucket4j 的原子 CAS 保證（並發安全）；視窗期滿換一個全新的桶。
 * 因此 {@code Retry-After}＝距視窗結束的秒數（1～window）。
 *
 * <p>本類別只關心「鍵」；鍵是什麼（JWT subject 或客戶端 IP）由 {@link RateLimitFilter} 決定。
 */
final class RateLimiter {

    /** 清理殘留視窗的門檻：超過這麼多個鍵時順手移除已期滿者，避免無限成長。 */
    private static final int CLEANUP_THRESHOLD = 10_000;

    /**
     * @param remaining         本次之後視窗內剩餘次數（超限時為 0）
     * @param retryAfterSeconds 距視窗結束的秒數（無條件進位，至少 1）
     */
    record Decision(boolean allowed, long remaining, long retryAfterSeconds) {
    }

    private record Window(Instant start, Bucket bucket) {
    }

    private final int limit;
    private final Duration window;
    private final Clock clock;
    private final ConcurrentHashMap<String, Window> windows = new ConcurrentHashMap<>();

    RateLimiter(int limit, Duration window, Clock clock) {
        this.limit = limit;
        this.window = window;
        this.clock = clock;
    }

    int limit() {
        return limit;
    }

    long windowSeconds() {
        return window.toSeconds();
    }

    Decision tryConsume(String key) {
        Instant now = clock.instant();
        Window current = windows.compute(key,
                (k, existing) -> existing == null || !now.isBefore(existing.start().plus(window))
                        ? new Window(now, newBucket()) : existing);
        ConsumptionProbe probe = current.bucket().tryConsumeAndReturnRemaining(1);
        long retryAfter = Math.max(1, (long) Math.ceil(Duration.between(now, current.start().plus(window))
                .toMillis() / 1000.0));
        if (windows.size() > CLEANUP_THRESHOLD) {
            windows.values().removeIf(w -> !now.isBefore(w.start().plus(window)));
        }
        return new Decision(probe.isConsumed(), probe.getRemainingTokens(), retryAfter);
    }

    private Bucket newBucket() {
        return Bucket.builder().addLimit(Bandwidth.builder().capacity(limit).refillIntervally(limit, window).build())
                .build();
    }
}
