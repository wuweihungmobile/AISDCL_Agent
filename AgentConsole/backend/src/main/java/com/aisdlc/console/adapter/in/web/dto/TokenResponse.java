package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.AuthUseCase.TokenPair;
import jakarta.validation.constraints.NotNull;

/**
 * 登入／續期回應（ADR-001 D4）：{@code {accessToken,refreshToken,expiresIn,role}}。
 *
 * @param expiresIn access token 有效秒數
 * @param role      ADMIN／OPERATOR／VIEWER
 */
public record TokenResponse(
        @NotNull String accessToken,
        @NotNull String refreshToken,
        @NotNull long expiresIn,
        @NotNull String role) {

    public static TokenResponse from(TokenPair pair) {
        return new TokenResponse(pair.accessToken(), pair.refreshToken(), pair.expiresIn(), pair.role());
    }
}
