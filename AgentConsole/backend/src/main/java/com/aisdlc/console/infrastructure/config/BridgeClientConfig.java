package com.aisdlc.console.infrastructure.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

/**
 * Engine Bridge 出站呼叫的裝配（W3-B1；W3-B2 在同一介面加 runs 系列時沿用）：
 * 綁定 {@code console.bridge.*}，並提供 Bridge 專用的 {@link RestClient.Builder}。
 * 刻意是獨立 Bean：測試以 {@code @Primary} 的同型 Bean 換成綁了 {@code MockRestServiceServer} 的 Builder。
 */
@Configuration(proxyBeanMethods = false)
@EnableConfigurationProperties(BridgeProperties.class)
public class BridgeClientConfig {

    @Bean
    RestClient.Builder bridgeRestClientBuilder() {
        return RestClient.builder();
    }
}
