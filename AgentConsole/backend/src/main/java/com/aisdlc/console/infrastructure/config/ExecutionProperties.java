package com.aisdlc.console.infrastructure.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

import java.time.Duration;
import java.util.Map;

/**
 * 執行相關的程序層設定（{@code console.execution.*}；契約附錄 D.2）。
 *
 * <p>🔴 {@code mockEnv} 只在 e2e／test profile 載入：附加到 Bridge 請求 {@code env} 的 {@code MOCK_CLAUDE_*}
 * （例 {@code MOCK_CLAUDE_DELAY}、{@code MOCK_CLAUDE_FAIL_REGEX}）；production 與 docker profile 不得出現這個屬性，預設空，
 * 所以 production 永遠不會把任何 mock 旋鈕送進引擎。
 *
 * @param mockEnv  測試旗標映射（鍵＝環境變數名）
 * @param consumer 事件消費者的連線調校
 */
@ConfigurationProperties(prefix = "console.execution")
public record ExecutionProperties(@DefaultValue Map<String, String> mockEnv, @DefaultValue Consumer consumer) {

    /**
     * @param idleTimeout    事件串流閒置多久視為斷線（Bridge 每 15 秒送 keep-alive，契約 §3.1 取 45 秒）
     * @param backoffInitial 重連退避起點
     * @param backoffMax     重連退避上限
     */
    public record Consumer(@DefaultValue("45s") Duration idleTimeout, @DefaultValue("1s") Duration backoffInitial,
                           @DefaultValue("30s") Duration backoffMax) {
    }
}
