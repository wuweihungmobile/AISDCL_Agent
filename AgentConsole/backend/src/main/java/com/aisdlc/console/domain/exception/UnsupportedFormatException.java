package com.aisdlc.console.domain.exception;

import java.util.Map;

/** 副檔名或內容型別不被支援（對映 HTTP 415）。 */
public final class UnsupportedFormatException extends DomainException {

    public UnsupportedFormatException(String message, String reason, Map<String, Object> details) {
        super(message, reason, details);
    }
}
