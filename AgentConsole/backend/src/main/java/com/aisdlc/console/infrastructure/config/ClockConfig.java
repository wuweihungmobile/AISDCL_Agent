package com.aisdlc.console.infrastructure.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Clock;

/** 時間來源：一律 UTC（時間戳一律帶 tz，不持久化 naive 本地時間）；測試可替換此 Bean。 */
@Configuration(proxyBeanMethods = false)
public class ClockConfig {

    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
