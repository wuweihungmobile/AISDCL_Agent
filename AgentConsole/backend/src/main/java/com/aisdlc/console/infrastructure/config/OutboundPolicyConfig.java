package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.domain.service.OutboundUrlPolicy;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.HostResolver;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.net.InetAddress;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * SSRF 政策（NFR-SEC-04）的裝配：以 {@code console.security.*} 組出 {@link OutboundUrlPolicy}（allowlist、
 * {@code allow-loopback}）與 DNS 解析器（系統解析＋測試覆寫）。測試可替換這兩個 Bean（例：假 resolver 驗 rebinding）。
 */
@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(ConsoleSecurityProperties.class)
public class OutboundPolicyConfig {

    @Bean
    OutboundUrlPolicy outboundUrlPolicy(ConsoleSecurityProperties properties) {
        return new OutboundUrlPolicy(properties.outboundAllowlist(), properties.allowLoopback());
    }

    /**
     * 先查 {@code console.security.test-dns-overrides}（e2e／test 才會有值；production 為空），其餘走系統 DNS
     * （{@link InetAddress#getAllByName}：所有 A／AAAA）。
     */
    @Bean
    HostResolver hostResolver(ConsoleSecurityProperties properties) {
        Map<String, String> overrides = properties.testDnsOverrides();
        return host -> {
            String override = overrides == null ? null : overrides.get(host.toLowerCase(Locale.ROOT));
            if (override != null) {
                List<InetAddress> addresses = new ArrayList<>();
                for (String ip : override.split(",")) {
                    addresses.add(InetAddress.getByName(ip.strip()));
                }
                return addresses;
            }
            return List.of(InetAddress.getAllByName(host));
        };
    }
}
