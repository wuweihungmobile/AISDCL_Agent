package com.aisdlc.console.domain.exception;

import java.util.Map;

/** 功能尚未提供（對映 HTTP 501）：目前只有 {@code format=pdf} 的監控報表（W5 之前一律 501，契約 §1.3.7）。 */
public final class NotImplementedYetException extends DomainException {

    public NotImplementedYetException(String message, String reason) {
        super(message, reason, Map.of());
    }
}
