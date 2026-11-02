package com.aisdlc.console.application.port.out;

import java.time.Duration;

/**
 * 研究事件串流的程序層設定（{@code console.research.stream.*}；契約 API_Contract_ResearchToPRD §1.4 API-RP-05／06）。application 層不認得
 * {@code infrastructure}，所以經這支埠取值；實作是 {@code ResearchStreamSettingsAdapter}。
 */
public interface ResearchStreamSettings {

    /** 尾隨事件帳的輪詢間隔（預設 250 毫秒）。 */
    Duration pollInterval();

    /** 重連時最多重播最新幾筆事件（預設 1,000）；更舊的缺口以 {@code research.replay_gap} 告知、改走 REST {@code afterSeq} 回補。 */
    int replayWindow();

    /** heartbeat 間隔（沿用 {@code console.sse.keep-alive-seconds}；預設 15 秒，整合測試 profile 為 2 秒）。 */
    Duration heartbeat();
}
