package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.application.port.out.TokenIssuer;
import com.aisdlc.console.domain.model.auth.Role;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jws;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.Optional;
import java.util.UUID;

/**
 * JWT（HS256）簽發與驗證（ADR-001 D4）。
 *
 * <p>access 與 refresh 用同一把密鑰，靠自訂 claim {@code token_use} 區分用途——驗證時一律要求「用途相符」，
 * 因此 refresh token 不能拿來當 access token 呼叫 API，反之亦然。演算法固定 HS256（驗證時明確檢查 header，
 * 不接受其他演算法）。時間來源注入 {@link Clock}，測試可造出「已過期」的 token。
 */
@Component
public class JwtTokenService implements TokenIssuer {

    /** 自訂 claim：角色名稱。 */
    static final String CLAIM_ROLE = "role";
    /** 自訂 claim：token 用途（access／refresh）。不用 header 的 typ，那個欄位慣例上固定為 JWT。 */
    static final String CLAIM_USE = "token_use";
    public static final String USE_ACCESS = "access";
    public static final String USE_REFRESH = "refresh";
    private static final String ALGORITHM = "HS256";
    static final int MIN_SECRET_BYTES = 32;

    /** 驗證結果；EXPIRED 只在「簽章正確但已過期」時出現，讓前端知道該走 refresh 流程。 */
    public enum Outcome { VALID, EXPIRED, INVALID }

    /**
     * @param tokenId   token 的 {@code jti}（簽發時一律寫入；沒有為 null）
     * @param expiresAt token 的 {@code exp}（沒有為 null）
     */
    public record Verification(Outcome outcome, String username, Role role, String tokenId, Instant expiresAt) {
        static Verification valid(String username, Role role, String tokenId, Instant expiresAt) {
            return new Verification(Outcome.VALID, username, role, tokenId, expiresAt);
        }

        static Verification of(Outcome outcome) {
            return new Verification(outcome, null, null, null, null);
        }
    }

    private final SecretKey key;
    private final Duration accessTtl;
    private final Duration refreshTtl;
    private final Clock clock;

    @Autowired
    public JwtTokenService(ConsoleAuthProperties properties, Clock clock) {
        this(properties.jwtSecret(), properties.accessTokenTtl(), properties.refreshTokenTtl(), clock);
    }

    public JwtTokenService(String secret, Duration accessTtl, Duration refreshTtl, Clock clock) {
        if (secret == null || secret.getBytes(StandardCharsets.UTF_8).length < MIN_SECRET_BYTES) {
            throw new IllegalStateException("JWT_SECRET 必須至少 " + MIN_SECRET_BYTES + " 字元（HS256 需要 256 bits）");
        }
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.accessTtl = accessTtl;
        this.refreshTtl = refreshTtl;
        this.clock = clock;
    }

    @Override
    public IssuedTokens issue(String username, Role role) {
        Instant now = clock.instant();
        return new IssuedTokens(build(username, role, USE_ACCESS, now, accessTtl),
                build(username, role, USE_REFRESH, now, refreshTtl), accessTtl.toSeconds());
    }

    /**
     * 驗證 refresh token 並取出撤銷名單要用的 {@code jti} 與 {@code exp}（契約 §1.9.2）。<b>沒有 {@code jti}（或沒有 {@code exp}）的 refresh
     * token 視為無效</b>——本服務簽發的每個 token 都有這兩個 claim，沒有的只可能來自更早的程式版本或偽造，無從撤銷，使用者重新登入即可。
     */
    @Override
    public Optional<RefreshIdentity> verifyRefreshToken(String token) {
        Verification result = verify(token, USE_REFRESH);
        if (result.outcome() != Outcome.VALID || result.tokenId() == null || result.tokenId().isBlank()
                || result.expiresAt() == null) {
            return Optional.empty();
        }
        return Optional.of(new RefreshIdentity(result.username(), result.role(), result.tokenId(), result.expiresAt()));
    }

    /** 驗證 token：簽章、期限、演算法、用途與角色都必須合格。 */
    public Verification verify(String token, String expectedUse) {
        if (token == null || token.isBlank()) {
            return Verification.of(Outcome.INVALID);
        }
        try {
            Jws<Claims> jws = Jwts.parser()
                    .verifyWith(key)
                    .clock(() -> Date.from(clock.instant()))
                    .build()
                    .parseSignedClaims(token);
            if (!ALGORITHM.equals(jws.getHeader().getAlgorithm())) {
                return Verification.of(Outcome.INVALID);
            }
            Claims claims = jws.getPayload();
            String roleName = claims.get(CLAIM_ROLE, String.class);
            if (!expectedUse.equals(claims.get(CLAIM_USE, String.class)) || claims.getSubject() == null
                    || roleName == null) {
                return Verification.of(Outcome.INVALID);
            }
            Date expiration = claims.getExpiration();
            return Verification.valid(claims.getSubject(), Role.valueOf(roleName), claims.getId(),
                    expiration == null ? null : expiration.toInstant());
        } catch (ExpiredJwtException e) {
            return Verification.of(Outcome.EXPIRED);
        } catch (JwtException | IllegalArgumentException e) {
            return Verification.of(Outcome.INVALID);
        }
    }

    private String build(String username, Role role, String use, Instant now, Duration ttl) {
        return Jwts.builder()
                .subject(username)
                .claim(CLAIM_ROLE, role.name())
                .claim(CLAIM_USE, use)
                .id(UUID.randomUUID().toString())
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plus(ttl)))
                .signWith(key, Jwts.SIG.HS256)
                .compact();
    }
}
