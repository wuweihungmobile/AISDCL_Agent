package com.aisdlc.console.domain.exception;

import java.util.Map;

/** 超過每分鐘請求上限（對映 HTTP 429；契約 §0.4 第 4 點）。 */
public final class RateLimitedException extends DomainException {

    public RateLimitedException(int limit, int windowSeconds, long retryAfterSeconds) {
        super("請求過於頻繁：每分鐘最多 " + limit + " 次，請 " + retryAfterSeconds + " 秒後再試", ErrorReasons.RATE_LIMITED,
                Map.of("limit", limit, "windowSeconds", windowSeconds, "retryAfterSeconds", retryAfterSeconds));
    }
}
