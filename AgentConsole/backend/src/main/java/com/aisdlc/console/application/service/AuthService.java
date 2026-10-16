package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.AuthUseCase;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.PasswordVerifier;
import com.aisdlc.console.application.port.out.RefreshTokenRevocations;
import com.aisdlc.console.application.port.out.TokenIssuer;
import com.aisdlc.console.application.port.out.TokenIssuer.IssuedTokens;
import com.aisdlc.console.application.port.out.UserDirectory;
import com.aisdlc.console.application.port.out.UserDirectory.UserAccount;
import com.aisdlc.console.domain.exception.UnauthorizedException;
import org.springframework.stereotype.Service;

import java.util.Optional;

/** 認證用例實作（ADR-001 D4；v1.4 D-19：refresh token 輪替撤銷與登出）。 */
@Service
public class AuthService implements AuthUseCase {

    /**
     * 帳號不存在時仍對這個「格式合法的 BCrypt 雜湊」做一次完整比對，讓「帳號不存在」與「密碼錯誤」
     * 的回應時間相近（避免以回應時間列舉有效帳號）。它不是任何人的密碼雜湊。
     */
    private static final String TIMING_EQUALIZER_HASH =
            "$2a$10$KHAY9cC.ZMlf5zQQhv3cO.7HbASio6Nfb1guUYkOCnxS1DXnk4DYa";

    private final UserDirectory users;
    private final PasswordVerifier passwords;
    private final TokenIssuer tokens;
    private final RefreshTokenRevocations revocations;
    private final AuditTrail audit;

    public AuthService(UserDirectory users, PasswordVerifier passwords, TokenIssuer tokens,
                       RefreshTokenRevocations revocations, AuditTrail audit) {
        this.users = users;
        this.passwords = passwords;
        this.tokens = tokens;
        this.revocations = revocations;
        this.audit = audit;
    }

    @Override
    public TokenPair login(String username, String password) {
        Optional<UserAccount> account = username == null || username.isBlank()
                ? Optional.empty() : users.findByUsername(username.strip());
        String hash = account.map(UserAccount::passwordHash).orElse(TIMING_EQUALIZER_HASH);
        boolean matches = passwords.matches(password == null ? "" : password, hash);
        if (account.isEmpty() || !matches) {
            throw new UnauthorizedException("帳號或密碼錯誤", "INVALID_CREDENTIALS");
        }
        return pairFor(account.get());
    }

    /**
     * 驗證（簽章、用途、期限、有 {@code jti}）→ <b>{@code tryRevoke}</b>（原子；回 false＝已被撤銷：登出過，或另一個併發換新搶先）→ 查帳號 →
     * 簽發新的一對（契約 §1.9.2）。撤銷先於簽發：同一個 refresh token 的兩個併發換新只有一個拿得到新 token。
     */
    @Override
    public TokenPair refresh(String refreshToken) {
        var identity = tokens.verifyRefreshToken(refreshToken).orElseThrow(AuthService::invalidRefreshToken);
        if (!revocations.tryRevoke(identity.tokenId(), identity.expiresAt())) {
            throw invalidRefreshToken();
        }
        // 以目錄中「目前」的帳號為準：帳號被移除或角色被改，續期時立即生效。
        UserAccount account = users.findByUsername(identity.username()).orElseThrow(AuthService::invalidRefreshToken);
        return pairFor(account);
    }

    @Override
    public void logout(String refreshToken) {
        audit.note("auth.logout", "auth", null);
        tokens.verifyRefreshToken(refreshToken)
                .ifPresent(identity -> revocations.tryRevoke(identity.tokenId(), identity.expiresAt()));
    }

    private static UnauthorizedException invalidRefreshToken() {
        return new UnauthorizedException("refresh token 無效或已過期", "INVALID_REFRESH_TOKEN");
    }

    private TokenPair pairFor(UserAccount account) {
        IssuedTokens issued = tokens.issue(account.username(), account.role());
        return new TokenPair(issued.accessToken(), issued.refreshToken(), issued.expiresInSeconds(),
                account.role().name());
    }
}
