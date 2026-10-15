package com.aisdlc.console.domain.exception;

import java.util.Map;

/** 上傳超過大小上限（對映 HTTP 413）：匯入檔案 10MB、設定檔 1MB。 */
public final class PayloadTooLargeException extends DomainException {

    public PayloadTooLargeException(String message, String reason, Map<String, Object> details) {
        super(message, reason, details);
    }
}
