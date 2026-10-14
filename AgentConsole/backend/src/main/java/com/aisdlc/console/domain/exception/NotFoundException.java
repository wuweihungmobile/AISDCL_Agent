package com.aisdlc.console.domain.exception;

import java.util.Map;
import java.util.UUID;

/** 資源不存在或已軟刪除（對映 HTTP 404）。 */
public final class NotFoundException extends DomainException {

    public NotFoundException(String message) {
        super(message, null, Map.of());
    }

    public static NotFoundException of(String resource, UUID id) {
        return new NotFoundException(resource + "不存在或已刪除：" + id);
    }
}
