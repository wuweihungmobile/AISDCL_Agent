package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.auth.Role;

import java.time.Instant;
import java.util.Optional;

/** JWT 簽發與 refresh token 驗證埠（實作：JJWT／HS256）。 */
public interface TokenIssuer {

    record IssuedTokens(String accessToken, String refreshToken, long expiresInSeconds) {
    }

    /**
     * 已驗證的 refresh token 身分。
     *
     * @param tokenId   token 的 {@code jti}（撤銷名單的鍵，契約 §1.9.2）；沒有 {@code jti} 的 refresh token 視為無效，不會出現在這裡
     * @param expiresAt token 的 {@code exp}（撤銷名單的項目保留到這個時間為止）
     */
    record RefreshIdentity(String username, Role role, String tokenId, Instant expiresAt) {
    }

    IssuedTokens issue(String username, Role role);

    /** 驗證 refresh token（簽章、期限、必須是 refresh 用途、必須有 {@code jti}）；任何不合格回 empty。 */
    Optional<RefreshIdentity> verifyRefreshToken(String token);
}
