package com.aisdlc.console.domain.exception;

import java.util.Map;

/**
 * 研究呼叫的上游失敗（API 契約 API_Contract_ResearchToPRD §0.2 第 8 列；502／504）。與 {@link UpstreamException} 的差別只在 {@code reason}：既有端點的上游失敗
 * 沿用中文常數（{@link ErrorReasons#BRIDGE_UNREACHABLE} 等，前端 {@code lib/api/reasons.ts} 與凍結契約附錄 B 雙向鎖），研究端點的契約規定英文識別字
 * {@code bridge_unreachable}、{@code bridge_timeout}（{@link ErrorReasons#RESEARCH_BRIDGE_UNREACHABLE}、{@link ErrorReasons#RESEARCH_BRIDGE_TIMEOUT}），
 * 另外 Bridge 自己回報的上游失敗（501 {@code not_implemented}、502 {@code init_failed}）也以它帶 Bridge 的 reason 與 details 原樣轉出。
 * 對映 HTTP 狀態由 {@code ResearchExceptionHandler} 依 {@link Kind} 決定（既有的 {@code GlobalExceptionHandler} 不認得這個型別）。
 */
public final class ResearchBridgeException extends DomainException {

    private static final long serialVersionUID = 1L;

    /** 失敗的種類：連線階段（502）、讀取逾時（504）、Bridge 回報的上游失敗（502）。 */
    public enum Kind {
        UNREACHABLE,
        TIMEOUT,
        FAILURE
    }

    private final Kind kind;
    private final boolean deliveryUncertain;

    private ResearchBridgeException(Kind kind, String message, String reason, boolean deliveryUncertain, Map<String, Object> details) {
        super(message, reason, details);
        this.kind = kind;
        this.deliveryUncertain = deliveryUncertain;
    }

    /** 連線階段失敗（拒絕連線、DNS、連線逾時；{@code deliveryUncertain=false}）或送出後的通訊失敗（連線被重設、提前 EOF；{@code true}）→ 502 {@code bridge_unreachable}。 */
    public static ResearchBridgeException unreachable(String message, boolean deliveryUncertain) {
        return new ResearchBridgeException(Kind.UNREACHABLE, message, ErrorReasons.RESEARCH_BRIDGE_UNREACHABLE, deliveryUncertain, Map.of());
    }

    /** 讀取逾時（請求已送出、結果不明）→ 504 {@code bridge_timeout}。 */
    public static ResearchBridgeException timedOut(String message) {
        return new ResearchBridgeException(Kind.TIMEOUT, message, ErrorReasons.RESEARCH_BRIDGE_TIMEOUT, true, Map.of());
    }

    /**
     * Bridge 回報的上游失敗（5xx，reason 由 Bridge 給）→ 502，reason 與 details 原樣；{@code details} 內不得有 null 值（呼叫端先剝掉）。
     * {@code deliveryUncertain} 為 false：Bridge 有回應就表示請求已被明確處理（失敗結果是確定的）。
     */
    public static ResearchBridgeException failure(String message, String reason, Map<String, Object> details) {
        return new ResearchBridgeException(Kind.FAILURE, message, reason, false, details);
    }

    public Kind kind() {
        return kind;
    }

    /** {@code true}＝請求可能已送達（讀取逾時、送出後的通訊失敗）：結果不明。 */
    public boolean deliveryUncertain() {
        return deliveryUncertain;
    }
}
