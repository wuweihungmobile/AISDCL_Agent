package com.aisdlc.console.domain.exception;

import java.util.Map;
import java.util.UUID;

/**
 * 資源不存在或已軟刪除（對映 HTTP 404）。一般 404 沒有 reason；帶 reason 的例外有兩個：{@code rtm_not_found}
 * 與 {@code si_not_found}（契約 §0.3 第 8 點；第二個例外由契約後繼檔 API_Contract_SelfImproving_P1b 載明）。
 */
public final class NotFoundException extends DomainException {

    public NotFoundException(String message) {
        super(message, null, Map.of());
    }

    /**
     * 帶 reason 的 404（目前兩個：{@link ErrorReasons#RTM_NOT_FOUND}——必須能機械區分「批次不存在」與「批次存在但沒有追溯報告」；
     * {@link ErrorReasons#SI_NOT_FOUND}——單筆提案不存在，與 503 {@code si_unavailable}（資料面壞了）語意分離）。
     */
    public NotFoundException(String message, String reason, Map<String, Object> details) {
        super(message, reason, details);
    }

    public static NotFoundException of(String resource, UUID id) {
        return new NotFoundException(resource + "不存在或已刪除：" + id);
    }
}
