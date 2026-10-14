package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.AuthUseCase;
import com.aisdlc.console.application.port.out.PasswordVerifier;
import com.aisdlc.console.application.port.out.TokenIssuer;
import com.aisdlc.console.application.port.out.TokenIssuer.IssuedTokens;
import com.aisdlc.console.application.port.out.UserDirectory;
import com.aisdlc.console.application.port.out.UserDirectory.UserAccount;
import com.aisdlc.console.domain.exception.UnauthorizedException;
import org.springframework.stereotype.Service;

import java.util.Optional;

/** 認證用例實作（ADR-001 D4）。 */
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

    public AuthService(UserDirectory users, PasswordVerifier passwords, TokenIssuer tokens) {
        this.users = users;
        this.passwords = passwords;
        this.tokens = tokens;
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

    @Override
    public TokenPair refresh(String refreshToken) {
        var identity = tokens.verifyRefreshToken(refreshToken)
                .orElseThrow(() -> new UnauthorizedException("refresh token 無效或已過期", "INVALID_REFRESH_TOKEN"));
        // 以目錄中「目前」的帳號為準：帳號被移除或角色被改，續期時立即生效。
        UserAccount account = users.findByUsername(identity.username())
                .orElseThrow(() -> new UnauthorizedException("refresh token 無效或已過期", "INVALID_REFRESH_TOKEN"));
        return pairFor(account);
    }

    private TokenPair pairFor(UserAccount account) {
        IssuedTokens issued = tokens.issue(account.username(), account.role());
        return new TokenPair(issued.accessToken(), issued.refreshToken(), issued.expiresInSeconds(),
                account.role().name());
    }
}
