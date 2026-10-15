package com.aisdlc.console.infrastructure.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

import java.time.Duration;

/**
 * 監控的程序層設定（{@code console.monitor.*}）。
 *
 * @param backgroundEnabled 是否啟動背景工作（啟動探測、啟動對帳、30 秒排程 tick）；整合測試 profile 關閉
 * @param tickInterval      健康探測與純時間型告警的排程間隔（契約 §3.1／§3.7：30 秒）
 * @param probeCapacity     健康探測環的容量（2,880 筆＝24 小時，契約 §3.1）
 */
@ConfigurationProperties(prefix = "console.monitor")
public record MonitorProperties(@DefaultValue("true") boolean backgroundEnabled,
                                @DefaultValue("30s") Duration tickInterval,
                                @DefaultValue("2880") int probeCapacity) {
}
