package com.aisdlc.console.domain.exception;

import java.util.Map;

/**
 * 功能停用或資料面不可用（對映 HTTP 503）：{@link ErrorReasons#SDD_WRITE_DISABLED}——backend 或 Bridge 沒有設定寫入權杖，
 * SDD 的 FSM 寫入面整個停用（契約 §1.10.2、§3.2）；{@link ErrorReasons#SI_UNAVAILABLE}——Bridge 明確回報 SelfImproving 資料面
 * 不可用（帶 {@code cause}、{@code detail}；TCS-P1b R8）。與 {@link UpstreamException}（502／504）不同：這是 Bridge 或設定
 * 明確說出的狀態，不是「上游壞了、連話都沒說清楚」。
 */
public final class ServiceUnavailableException extends DomainException {

    public ServiceUnavailableException(String message, String reason) {
        super(message, reason, Map.of());
    }

    /** 帶結構化原因（例：{@code si_unavailable} 的 {@code cause}、{@code detail}；不得含 null 值）。 */
    public ServiceUnavailableException(String message, String reason, Map<String, Object> details) {
        super(message, reason, details);
    }
}
