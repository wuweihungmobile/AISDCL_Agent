package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.domain.model.auth.Role;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;
import org.springframework.validation.annotation.Validated;

import java.time.Duration;
import java.util.List;

/**
 * 認證設定（application.yml 的 {@code console.auth.*}；ADR-001 D4）。
 *
 * <p>🔴 {@code jwtSecret} 讀環境變數 JWT_SECRET，缺或短於 32 字元＝啟動失敗（綁定驗證不過，
 * Spring 直接中止啟動），不會退回弱預設密鑰。
 *
 * @param jwtSecret       HS256 密鑰（≥ 32 字元）
 * @param accessTokenTtl  access token 有效期（預設 30 分鐘，PRD §9.2）
 * @param refreshTokenTtl refresh token 有效期（預設 7 天）
 * @param users           使用者清單（admin／operator／viewer；密碼為 BCrypt 雜湊）
 */
@Validated
@ConfigurationProperties(prefix = "console.auth")
public record ConsoleAuthProperties(
        @NotBlank(message = "環境變數 JWT_SECRET 必填") @Size(min = 32, message = "JWT_SECRET 長度必須至少 32 字元")
        String jwtSecret,
        @NotNull @DefaultValue("30m") Duration accessTokenTtl,
        @NotNull @DefaultValue("7d") Duration refreshTokenTtl,
        @NotEmpty(message = "console.auth.users 至少要有一組使用者") List<@Valid UserProperties> users) {

    /** 單一使用者；passwordHash 為 BCrypt 雜湊（開發預設密碼見 backend/README.md）。 */
    public record UserProperties(@NotBlank String username, @NotBlank String passwordHash, @NotNull Role role) {
    }
}
