package com.aisdlc.console.domain.exception;

import java.util.Map;

/**
 * 領域規則違反的共同基底（純 Java，不依賴 Spring／JPA）。
 *
 * <p>子類別對應 HTTP 語意：{@link ValidationException}＝400、{@link UnauthorizedException}＝401、
 * {@link NotFoundException}＝404、{@link ConflictException}＝409；對映由 adapter 層的
 * {@code GlobalExceptionHandler} 負責，domain 本身不認得 HTTP。
 */
public abstract class DomainException extends RuntimeException {

    private final String reason;
    private final Map<String, Object> details;

    protected DomainException(String message, String reason, Map<String, Object> details) {
        super(message);
        this.reason = reason;
        this.details = details == null ? Map.of() : Map.copyOf(details);
    }

    /** 簡短的原因說明（PRD「409 附 reason」「reason:依賴成環」）；可為 null。 */
    public String reason() {
        return reason;
    }

    /** 結構化補充資訊（例：環路 id 清單、違規字元清單）；不會是 null。 */
    public Map<String, Object> details() {
        return details;
    }
}
