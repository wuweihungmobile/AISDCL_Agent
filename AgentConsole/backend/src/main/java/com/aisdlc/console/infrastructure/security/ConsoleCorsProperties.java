package com.aisdlc.console.infrastructure.security;

import jakarta.validation.constraints.NotEmpty;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;
import org.springframework.validation.annotation.Validated;

import java.util.List;

/**
 * CORS 設定（NFR-9.2-05：只允許指定 Origin）。{@code console.cors.allowed-origins}，逗號分隔；
 * 預設只放行本機前端 http://localhost:3000。
 */
@Validated
@ConfigurationProperties(prefix = "console.cors")
public record ConsoleCorsProperties(
        @NotEmpty @DefaultValue("http://localhost:3000") List<String> allowedOrigins) {
}
