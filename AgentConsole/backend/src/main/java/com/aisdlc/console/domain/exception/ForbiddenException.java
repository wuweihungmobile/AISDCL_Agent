package com.aisdlc.console.domain.exception;

import java.util.Map;

/** 已認證但角色不足（對映 HTTP 403）；由安全層（RBAC）在 filter 階段轉成此例外後交給統一錯誤處理。 */
public final class ForbiddenException extends DomainException {

    public ForbiddenException(String message, String reason) {
        super(message, reason, Map.of());
    }
}
