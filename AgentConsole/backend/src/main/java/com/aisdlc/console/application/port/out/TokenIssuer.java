package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.auth.Role;

import java.util.Optional;

/** JWT 簽發與 refresh token 驗證埠（實作：JJWT／HS256）。 */
public interface TokenIssuer {

    record IssuedTokens(String accessToken, String refreshToken, long expiresInSeconds) {
    }

    /** 已驗證的 refresh token 身分。 */
    record RefreshIdentity(String username, Role role) {
    }

    IssuedTokens issue(String username, Role role);

    /** 驗證 refresh token（簽章、期限、必須是 refresh 用途）；任何不合格回 empty。 */
    Optional<RefreshIdentity> verifyRefreshToken(String token);
}
