package com.aisdlc.console.application.port.out;

import java.time.Duration;
import java.util.Map;
import java.util.Set;

/**
 * 執行期的程序層設定（Spring 屬性，不是 {@code system_configs}）。application 層不認得 {@code infrastructure}，
 * 所以經這支埠取值：契約附錄 D.2 的 {@code console.security.evaluator-allowlist}、{@code console.execution.mock-env}、
 * {@code console.sse.*}，以及消費者與探測環的調校值。
 */
public interface RuntimeSettings {

    /** 評估指令可執行檔白名單（小寫；附錄 D.3，可由 {@code console.security.evaluator-allowlist} 覆寫）。 */
    Set<String> evaluatorAllowlist();

    /** 附加到 Bridge 請求 {@code env} 的 {@code MOCK_CLAUDE_*}；<b>只有 e2e／test profile 非空</b>，production 永遠空。 */
    Map<String, String> mockEnv();

    /** SSE keep-alive 間隔（秒；預設 15，e2e／test 為 2）。 */
    int sseKeepAliveSeconds();

    /** 每個 SSE 連線的送出佇列容量（框架數；預設 1,000）。 */
    int sseQueueSize();

    /** 事件串流閒置多久視為斷線（預設 45 秒，契約 §3.1）。 */
    Duration consumerIdleTimeout();

    /** 重連退避的起點與上限（預設 1 秒→30 秒，契約 §3.5.4）。 */
    Duration consumerBackoffInitial();

    Duration consumerBackoffMax();

    /** 健康探測與純時間型告警的排程間隔（預設 30 秒）。 */
    Duration monitorTickInterval();

    /** 健康探測環的容量（預設 2,880＝24 小時）。 */
    int healthProbeCapacity();

    /** 是否啟動背景工作（啟動對帳、探測、排程 tick）；整合測試預設關閉、需要時由測試明確開啟。 */
    boolean backgroundEnabled();
}
