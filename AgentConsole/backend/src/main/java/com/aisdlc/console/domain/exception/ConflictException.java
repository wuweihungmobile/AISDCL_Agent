package com.aisdlc.console.domain.exception;

import java.util.Map;

/** 與資源目前狀態衝突（對映 HTTP 409）：非法狀態轉移、EXECUTING 受限操作、重複 signoff 等。 */
public class ConflictException extends DomainException {

    public ConflictException(String message, String reason) {
        super(message, reason, Map.of());
    }

    public ConflictException(String message, String reason, Map<String, Object> details) {
        super(message, reason, details);
    }
}
