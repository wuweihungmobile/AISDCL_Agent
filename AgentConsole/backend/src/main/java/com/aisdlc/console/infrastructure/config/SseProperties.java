package com.aisdlc.console.infrastructure.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/**
 * 前端 SSE 的設定（{@code console.sse.*}；契約附錄 D.2）。
 *
 * @param keepAliveSeconds 連續多久沒有任何事件就送一行 keep-alive 註解；預設 15，<b>e2e／test profile 覆寫為 2</b>
 *                         （該覆寫只在 e2e／test profile 載入，production 與 docker profile 不得出現）
 * @param queueSize        每個連線的送出佇列容量（框架數）；佇列滿＝伺服器主動關閉該連線，客戶端以 {@code Last-Event-ID} 重連即補齊
 */
@ConfigurationProperties(prefix = "console.sse")
public record SseProperties(@DefaultValue("15") int keepAliveSeconds, @DefaultValue("1000") int queueSize) {
}
