package com.aisdlc.console.application.port.out;

import java.util.Map;

/**
 * 審計軌跡埠（NFR-9.2-07；契約 §0.4 第 5 點）。寫入請求的審計列由安全層的 {@code AuditLoggingFilter} 統一產生；
 * 用例透過本埠為「目前這個請求」補上語意標註（{@code action}、{@code entity}），讓日誌行與
 * {@code audit_log} 說得出「做了什麼、對什麼」，而不只是「PUT /api/v1/...」。
 *
 * <p>🔴 {@code extra} 與 {@code details} 絕不放金鑰、userinfo、請求本文或任何機密值。
 */
public interface AuditTrail {

    /** 標註目前的寫入請求（例：{@code import.signoff}、{@code settings.update}、{@code entity}＝{@code import:<id>}）。 */
    void note(String action, String entityType, String entityId);

    /** 同上，另附少量非機密的補充欄位（例：test-connection 的 host 與結果）。 */
    void note(String action, String entityType, String entityId, Map<String, Object> extra);

    /**
     * 獨立的審計事件（不是寫入請求的一部分，例如 {@code GET /settings?reveal=true} 揭露敏感參數）：
     * 直接輸出一行審計日誌並落 {@code audit_log}；失敗不得影響主請求。
     */
    void event(String action, Map<String, Object> details);
}
