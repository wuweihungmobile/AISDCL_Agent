package com.aisdlc.console.application.port.out;

import java.time.Duration;
import java.util.Map;

/**
 * 外呼 HTTP 埠（NFR-SEC-04）：所有「由使用者可設定的 URL」發出的連線（測試連線、匯入路徑 B 的 LLM）都走這裡。
 *
 * <p>實作必須（契約 §1.5.7 連線實作、AR-10）：先過 SEC-04 規則 1～6（任一不過丟
 * {@code OutboundUrlPolicy.Rejected}，<b>且未發出任何連線</b>）；通過後把連線<b>釘死在已驗證的 IP</b>
 * （解析一次、驗證全部位址、就用這批位址連線，沒有第二次 DNS 查詢）；以原 host 作 Host 標頭與 TLS SNI／主機名驗證；
 * 不自動跟隨 redirect（3xx 原樣回傳）。
 */
public interface OutboundHttp {

    /**
     * @param latencyMs    送出請求到收到回應標頭的毫秒數
     * @param resolvedHost URL 的 host（小寫）
     */
    record HttpResult(int status, String body, long latencyMs, String resolvedHost) {
    }

    /** 網路層失敗（政策拒絕不在此列，那是 {@code OutboundUrlPolicy.Rejected}）。 */
    final class OutboundIoException extends RuntimeException {

        private static final long serialVersionUID = 1L;

        /** TIMEOUT＝連線或讀取逾時；CONNECT＝拒絕連線／無法解析；OTHER＝其他 I/O。 */
        public enum Kind { TIMEOUT, CONNECT, OTHER }

        private final Kind kind;

        public OutboundIoException(Kind kind, String message) {
            super(message);
            this.kind = kind;
        }

        public Kind kind() {
            return kind;
        }
    }

    /**
     * {@code POST <url>} 一則 JSON。回應本文以 UTF-8 讀取、上限 4 MB（超過截斷）。
     *
     * @param totalTimeout 從送出到讀完回應的總逾時
     */
    HttpResult postJson(String url, Map<String, String> headers, String jsonBody, Duration connectTimeout,
                        Duration totalTimeout);
}
