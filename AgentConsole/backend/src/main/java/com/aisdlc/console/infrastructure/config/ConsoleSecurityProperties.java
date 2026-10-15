package com.aisdlc.console.infrastructure.config;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotEmpty;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;
import org.springframework.validation.annotation.Validated;

import java.util.List;
import java.util.Map;

/**
 * 安全相關設定（application.yml 的 {@code console.security.*}；契約附錄 D.2）。
 *
 * <p>🔴 {@code allowLoopback}、{@code testDnsOverrides} 只在 e2e／test profile 載入：production 與 docker profile
 * 不得出現這兩個屬性（預設 false／空）。{@code link_local}／{@code private_ip} 沒有任何旗標能放行（D-47）。
 *
 * @param outboundAllowlist SEC-04 外呼 host 白名單（精確比對）；預設與 Bridge 的 MiniMax 兩個網域對齊（AR-09、D-53），
 *                          要用其他供應商須由部署者明確加入，且 Bridge 的 {@code BRIDGE_OUTBOUND_ALLOWLIST} 也要含該 host
 * @param allowLoopback     是否放行「列在 allowlist 內」的 loopback（e2e 的假伺服器綁在 127.0.0.1）
 * @param testDnsOverrides  測試用 DNS 覆寫（{@code host: ip}），讓 {@code dns_rebinding} 可決定性重現
 */
@Validated
@ConfigurationProperties(prefix = "console.security")
public record ConsoleSecurityProperties(
        @NotEmpty(message = "console.security.outbound-allowlist 至少要有一個 host")
        @DefaultValue({"api.minimax.io", "api.minimax.chat"}) List<String> outboundAllowlist,
        @DefaultValue("false") boolean allowLoopback,
        @DefaultValue Map<String, String> testDnsOverrides,
        @Valid @DefaultValue RateLimit rateLimit) {

    /**
     * 限流（NFR-9.2-06；契約 §0.4 第 4 點）。
     *
     * @param enabled          開關（預設 true；單元／整合測試 profile 為 false，但必須有一支測試開著它打 101 次）
     * @param requestsPerMinute 每個使用者（JWT subject；未認證才以客戶端 IP）每 60 秒的上限
     * @param trustForwardedFor docker／e2e 為 true：搭配 {@code server.forward-headers-strategy=native}，限流取處理後的
     *                          {@code getRemoteAddr()}（不自行解析 X-Forwarded-For）；production 直連維持 false
     */
    public record RateLimit(
            @DefaultValue("true") boolean enabled,
            @Min(1) @Max(100000) @DefaultValue("100") int requestsPerMinute,
            @DefaultValue("false") boolean trustForwardedFor) {
    }
}
