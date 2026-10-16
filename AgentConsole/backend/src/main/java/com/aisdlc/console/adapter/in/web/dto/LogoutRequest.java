package com.aisdlc.console.adapter.in.web.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

/** {@code POST /api/v1/auth/logout} 的請求本文（契約 §1.9.1；D-19）。 */
@Schema(name = "LogoutRequest", description = "POST /api/v1/auth/logout 的請求本文（v1.4，D-19）")
public record LogoutRequest(
        @NotBlank(message = "refreshToken 不能為空")
        @Schema(description = "要撤銷的 refresh token（目前 session 的那一個）", minLength = 1) String refreshToken) {
}
