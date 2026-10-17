package com.aisdlc.console.domain.exception;

import java.util.Map;
import java.util.UUID;

/** 資源不存在或已軟刪除（對映 HTTP 404）。一般 404 沒有 reason；{@code rtm_not_found} 是唯一帶 reason 的例外（契約 §0.3 第 8 點）。 */
public final class NotFoundException extends DomainException {

    public NotFoundException(String message) {
        super(message, null, Map.of());
    }

    /** 帶 reason 的 404（目前只有 {@link ErrorReasons#RTM_NOT_FOUND}：必須能機械區分「批次不存在」與「批次存在但沒有追溯報告」）。 */
    public NotFoundException(String message, String reason, Map<String, Object> details) {
        super(message, reason, details);
    }

    public static NotFoundException of(String resource, UUID id) {
        return new NotFoundException(resource + "不存在或已刪除：" + id);
    }
}
