package com.aisdlc.console.domain.exception;

import java.util.Map;

/**
 * 上游（Engine Bridge）無法連線、逾時或回了非預期的錯誤（對映 HTTP 502／504；契約 §3.2）。
 * 子類別以語意區分，HTTP 狀態由 adapter 層的統一錯誤處理決定。
 */
public abstract class UpstreamException extends DomainException {

    protected UpstreamException(String message, String reason, Map<String, Object> details) {
        super(message, reason, details);
    }

    /** 連線失敗（拒絕連線、DNS、連線逾時）→ 502 {@code 引擎橋接服務無法連線}。 */
    public static final class Unavailable extends UpstreamException {
        public Unavailable(String message) {
            super(message, ErrorReasons.BRIDGE_UNREACHABLE, Map.of());
        }
    }

    /** 讀取逾時 → 504 {@code 引擎橋接服務逾時}。 */
    public static final class TimedOut extends UpstreamException {
        public TimedOut(String message) {
            super(message, ErrorReasons.BRIDGE_TIMEOUT, Map.of());
        }
    }

    /** 其餘 5xx 或無法理解的回應 → 502 {@code 引擎橋接服務錯誤}，details 帶 {@code bridgeStatus}／{@code bridgeReason}。 */
    public static final class Failure extends UpstreamException {
        public Failure(String message, Map<String, Object> details) {
            super(message, ErrorReasons.BRIDGE_ERROR, details);
        }
    }
}
