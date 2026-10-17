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

    /** 軟刪除專案可復原的天數（{@code console.retention.soft-delete-days}，預設 30、≥ 1；契約 §1.6.5）。 */
    int softDeleteRetentionDays();

    /**
     * 是否註冊每日清除排程（{@code console.retention.purge-enabled}，<b>預設 false</b>）：實體刪除不可逆，部署者必須明確開啟；
     * 未開啟時軟刪除資料只會累積、不會消失。
     */
    boolean purgeEnabled();

    /**
     * backend 是否設定了 SDD 寫入權杖（{@code console.bridge.sdd-write-token}，環境變數 {@code BRIDGE_SDD_WRITE_TOKEN}；v1.5，
     * ADR-XPLAT-016 §9）。<b>只回有沒有設、不回值</b>：權杖值只有 Bridge 出站介面卡持有，application 層永遠看不到它。
     * 未設＝SDD 寫入面停用：核准凍結回 503 {@code sdd_write_disabled}；execute 不送 {@code sdd} 區塊並以
     * {@code token_not_configured} 警告（契約 §1.10.5）。
     */
    boolean sddWriteTokenConfigured();
}
