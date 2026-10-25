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

    /**
     * 連線失敗（拒絕連線、DNS、連線逾時）→ 502 {@code 引擎橋接服務無法連線}。
     *
     * <p>另帶 {@link #deliveryUncertain()}（SelfImproving 寫入的補償判準，TCS-SelfImprovingDecide-P2b W11）：<b>連線階段</b>的失敗
     * （請求不可能被 Bridge 收到）為 {@code false}；<b>送出之後</b>的通訊失敗（連線被重設、提前 EOF）為 {@code true}——Bridge 可能已處理
     * 請求，結果不明。預設（單參數建構）為 {@code false}。
     */
    public static final class Unavailable extends UpstreamException {

        private final boolean deliveryUncertain;

        public Unavailable(String message) {
            this(message, false, Map.of());
        }

        public Unavailable(String message, boolean deliveryUncertain, Map<String, Object> details) {
            super(message, ErrorReasons.BRIDGE_UNREACHABLE, details);
            this.deliveryUncertain = deliveryUncertain;
        }

        /** {@code true}＝請求可能已送達（送出後的通訊失敗）；{@code false}＝確定沒有送達（連線階段失敗）。 */
        public boolean deliveryUncertain() {
            return deliveryUncertain;
        }
    }

    /** 讀取逾時 → 504 {@code 引擎橋接服務逾時}（請求已送出，結果不明）。 */
    public static final class TimedOut extends UpstreamException {
        public TimedOut(String message) {
            this(message, Map.of());
        }

        public TimedOut(String message, Map<String, Object> details) {
            super(message, ErrorReasons.BRIDGE_TIMEOUT, details);
        }
    }

    /** 其餘 5xx 或無法理解的回應 → 502 {@code 引擎橋接服務錯誤}，details 帶 {@code bridgeStatus}／{@code bridgeReason}。 */
    public static final class Failure extends UpstreamException {
        public Failure(String message, Map<String, Object> details) {
            super(message, ErrorReasons.BRIDGE_ERROR, details);
        }
    }
}
