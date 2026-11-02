package com.aisdlc.console.infrastructure.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/**
 * 研究事件串流的設定（{@code console.research.stream.*}；契約 API_Contract_ResearchToPRD §1.4 API-RP-05／06、ADR-003 D6）。<b>只作綁定</b>：服務層一律經
 * {@code application/port/out/ResearchStreamSettings} 取值（application 層不認得 {@code infrastructure}），實作是 {@link ResearchStreamSettingsAdapter}。
 *
 * @param pollMillis   尾隨 {@code research_events} 的輪詢間隔（毫秒；預設 250，整合測試 profile 縮短）；須 ≥ 1
 * @param replayWindow 重連時最多重播最新幾筆事件（預設 1,000）：{@code Last-Event-ID} 之後的事件多於這個數時，先送 {@code research.replay_gap}
 *                     再重播最新的這麼多筆，客戶端改以 REST {@code afterSeq} 回補；須 ≥ 1
 */
@ConfigurationProperties(prefix = "console.research.stream")
public record ResearchStreamProperties(@DefaultValue("250") long pollMillis, @DefaultValue("1000") int replayWindow) {

    public ResearchStreamProperties {
        if (pollMillis < 1) {
            throw new IllegalArgumentException("console.research.stream.poll-millis 必須 ≥ 1（目前為 " + pollMillis + "）");
        }
        if (replayWindow < 1) {
            throw new IllegalArgumentException("console.research.stream.replay-window 必須 ≥ 1（目前為 " + replayWindow + "）");
        }
    }
}
