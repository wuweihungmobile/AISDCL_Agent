package com.aisdlc.console.domain.exception;

import java.util.Map;

/** 認證失敗（對映 HTTP 401）：帳密錯誤、refresh token 無效或已過期。 */
public final class UnauthorizedException extends DomainException {

    public UnauthorizedException(String message, String reason) {
        super(message, reason, Map.of());
    }
}
