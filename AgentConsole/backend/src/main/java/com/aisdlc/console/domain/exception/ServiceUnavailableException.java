package com.aisdlc.console.domain.exception;

import java.util.Map;

/**
 * 功能停用（對映 HTTP 503）：目前只有 {@link ErrorReasons#SDD_WRITE_DISABLED}——backend 或 Bridge 沒有設定寫入權杖，
 * SDD 的 FSM 寫入面整個停用（契約 §1.10.2、§3.2）。與 {@link UpstreamException}（502／504）不同：這是「設定決定的停用」，
 * 不是「上游壞了」。
 */
public final class ServiceUnavailableException extends DomainException {

    public ServiceUnavailableException(String message, String reason) {
        super(message, reason, Map.of());
    }
}
