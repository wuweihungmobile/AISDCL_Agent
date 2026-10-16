package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.application.port.out.TokenIssuer.IssuedTokens;
import com.aisdlc.console.domain.model.auth.Role;
import com.aisdlc.console.infrastructure.security.JwtTokenService.Outcome;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.Test;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.Date;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** JWT 簽發／驗證／過期（ADR-001 D4；NFR-9.2-01：access 30 分鐘、refresh 7 天）。 */
class JwtTokenServiceTest {

    private static final String SECRET = "unit-test-only-secret-with-at-least-32-chars";
    private static final Instant NOW = Instant.parse("2026-10-14T10:00:00Z");
    private static final Duration ACCESS = Duration.ofMinutes(30);
    private static final Duration REFRESH = Duration.ofDays(7);

    private static JwtTokenService serviceAt(Instant now) {
        return new JwtTokenService(SECRET, ACCESS, REFRESH, Clock.fixed(now, ZoneOffset.UTC));
    }

    private static String payloadJson(String jwt) {
        return new String(Base64.getUrlDecoder().decode(jwt.split("\\.")[1]), StandardCharsets.UTF_8);
    }

    @Test
    void issuedTokensCarryTheDocumentedLifetimesAndExpiresInSeconds() {
        IssuedTokens tokens = serviceAt(NOW).issue("operator", Role.OPERATOR);
        assertThat(tokens.expiresInSeconds()).isEqualTo(1800);
        assertThat(payloadJson(tokens.accessToken()))
                .contains("\"exp\":" + NOW.plus(ACCESS).getEpochSecond())
                .contains("\"iat\":" + NOW.getEpochSecond())
                .contains("\"sub\":\"operator\"").contains("\"role\":\"OPERATOR\"")
                .contains("\"token_use\":\"access\"");
        assertThat(payloadJson(tokens.refreshToken()))
                .contains("\"exp\":" + NOW.plus(REFRESH).getEpochSecond()).contains("\"token_use\":\"refresh\"");
    }

    @Test
    void validAccessAndRefreshTokensVerifyForTheirOwnUseOnly() {
        JwtTokenService service = serviceAt(NOW);
        IssuedTokens tokens = service.issue("admin", Role.ADMIN);

        JwtTokenService.Verification access = service.verify(tokens.accessToken(), JwtTokenService.USE_ACCESS);
        assertThat(access.outcome()).isEqualTo(Outcome.VALID);
        assertThat(access.username()).isEqualTo("admin");
        assertThat(access.role()).isEqualTo(Role.ADMIN);
        assertThat(service.verifyRefreshToken(tokens.refreshToken())).hasValueSatisfying(identity -> {
            assertThat(identity.username()).isEqualTo("admin");
            assertThat(identity.role()).isEqualTo(Role.ADMIN);
        });

        assertThat(service.verify(tokens.refreshToken(), JwtTokenService.USE_ACCESS).outcome())
                .as("refresh 不能當 access").isEqualTo(Outcome.INVALID);
        assertThat(service.verifyRefreshToken(tokens.accessToken())).as("access 不能當 refresh").isEmpty();
    }

    @Test
    void accessTokenExpiresExactlyAfterThirtyMinutesButRefreshStillLives() {
        IssuedTokens tokens = serviceAt(NOW).issue("viewer", Role.VIEWER);
        JwtTokenService justBefore = serviceAt(NOW.plus(ACCESS).minusSeconds(1));
        JwtTokenService justAfter = serviceAt(NOW.plus(ACCESS).plusSeconds(1));
        assertThat(justBefore.verify(tokens.accessToken(), JwtTokenService.USE_ACCESS).outcome())
                .isEqualTo(Outcome.VALID);
        assertThat(justAfter.verify(tokens.accessToken(), JwtTokenService.USE_ACCESS).outcome())
                .isEqualTo(Outcome.EXPIRED);
        assertThat(justAfter.verifyRefreshToken(tokens.refreshToken())).isPresent();
        assertThat(serviceAt(NOW.plus(REFRESH).plusSeconds(1)).verifyRefreshToken(tokens.refreshToken())).isEmpty();
    }

    @Test
    void aTokenSignedWithAnotherKeyOrTamperedIsInvalidNotExpired() {
        String foreign = new JwtTokenService("another-secret-with-at-least-32-characters!!", ACCESS, REFRESH,
                Clock.fixed(NOW, ZoneOffset.UTC)).issue("admin", Role.ADMIN).accessToken();
        assertThat(serviceAt(NOW).verify(foreign, JwtTokenService.USE_ACCESS).outcome()).isEqualTo(Outcome.INVALID);

        String valid = serviceAt(NOW).issue("viewer", Role.VIEWER).accessToken();
        String[] parts = valid.split("\\.");
        String forgedPayload = Base64.getUrlEncoder().withoutPadding().encodeToString(
                payloadJson(valid).replace("VIEWER", "ADMIN").getBytes(StandardCharsets.UTF_8));
        String forged = parts[0] + "." + forgedPayload + "." + parts[2];
        assertThat(serviceAt(NOW).verify(forged, JwtTokenService.USE_ACCESS).outcome()).isEqualTo(Outcome.INVALID);
    }

    @Test
    void anExpiredAndTamperedTokenIsInvalidBecauseTheSignatureIsCheckedFirst() {
        String old = serviceAt(NOW).issue("viewer", Role.VIEWER).accessToken();
        String tampered = old.substring(0, old.length() - 3) + "abc";
        assertThat(serviceAt(NOW.plus(Duration.ofHours(5))).verify(tampered, JwtTokenService.USE_ACCESS).outcome())
                .isEqualTo(Outcome.INVALID);
    }

    @Test
    void onlyHs256IsAcceptedEvenWithTheCorrectKey() {
        // HS512 需要 ≥ 64 bytes 的金鑰；用同一把 64 bytes 金鑰簽 HS512，驗證端必須因演算法不是 HS256 而拒絕。
        String longSecret = "long-secret-for-hs512-".repeat(4);
        SecretKey key = Keys.hmacShaKeyFor(longSecret.getBytes(StandardCharsets.UTF_8));
        String hs512 = Jwts.builder().subject("admin").claim("role", "ADMIN").claim("token_use", "access")
                .expiration(Date.from(NOW.plus(ACCESS))).signWith(key, Jwts.SIG.HS512).compact();
        JwtTokenService service = new JwtTokenService(longSecret, ACCESS, REFRESH, Clock.fixed(NOW, ZoneOffset.UTC));
        assertThat(service.verify(hs512, JwtTokenService.USE_ACCESS).outcome()).isEqualTo(Outcome.INVALID);
        // 對照組：同一把金鑰簽 HS256 則通過，證明上面的拒絕確實是因為演算法。
        assertThat(service.verify(service.issue("admin", Role.ADMIN).accessToken(), JwtTokenService.USE_ACCESS)
                .outcome()).isEqualTo(Outcome.VALID);
    }

    @Test
    void unsignedAlgNoneTokensAreRejected() {
        String unsigned = Jwts.builder().subject("admin").claim("role", "ADMIN").claim("token_use", "access")
                .expiration(Date.from(NOW.plus(ACCESS))).compact();
        assertThat(serviceAt(NOW).verify(unsigned, JwtTokenService.USE_ACCESS).outcome()).isEqualTo(Outcome.INVALID);
    }

    @Test
    void tokensMissingRoleSubjectOrWithAnUnknownRoleAreInvalid() {
        SecretKey key = Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));
        String noRole = Jwts.builder().subject("admin").claim("token_use", "access")
                .expiration(Date.from(NOW.plus(ACCESS))).signWith(key, Jwts.SIG.HS256).compact();
        String badRole = Jwts.builder().subject("admin").claim("role", "ROOT").claim("token_use", "access")
                .expiration(Date.from(NOW.plus(ACCESS))).signWith(key, Jwts.SIG.HS256).compact();
        String noSubject = Jwts.builder().claim("role", "ADMIN").claim("token_use", "access")
                .expiration(Date.from(NOW.plus(ACCESS))).signWith(key, Jwts.SIG.HS256).compact();
        for (String token : new String[] {noRole, badRole, noSubject}) {
            assertThat(serviceAt(NOW).verify(token, JwtTokenService.USE_ACCESS).outcome()).isEqualTo(Outcome.INVALID);
        }
    }

    @Test
    void garbageNullAndBlankTokensAreInvalid() {
        for (String token : new String[] {null, "", "   ", "garbage", "a.b.c", "Bearer x"}) {
            assertThat(serviceAt(NOW).verify(token, JwtTokenService.USE_ACCESS).outcome()).as(String.valueOf(token))
                    .isEqualTo(Outcome.INVALID);
        }
        assertThat(serviceAt(NOW).verifyRefreshToken(null)).isEmpty();
    }

    @Test
    void aSecretShorterThan256BitsIsRefusedAtConstruction() {
        assertThatThrownBy(() -> new JwtTokenService("too-short", ACCESS, REFRESH, Clock.systemUTC()))
                .isInstanceOf(IllegalStateException.class).hasMessageContaining("JWT_SECRET");
        assertThatThrownBy(() -> new JwtTokenService(null, ACCESS, REFRESH, Clock.systemUTC()))
                .isInstanceOf(IllegalStateException.class);
        assertThatThrownBy(() -> new JwtTokenService("x".repeat(31), ACCESS, REFRESH, Clock.systemUTC()))
                .isInstanceOf(IllegalStateException.class);
        assertThat(new JwtTokenService("x".repeat(32), ACCESS, REFRESH, Clock.systemUTC())).isNotNull();
    }

    @Test
    void everyIssuedTokenIsUnique() {
        JwtTokenService service = serviceAt(NOW);
        assertThat(service.issue("admin", Role.ADMIN).accessToken())
                .isNotEqualTo(service.issue("admin", Role.ADMIN).accessToken());
    }

    // ── v1.4（D-19；契約 §1.9.2）：撤銷名單用 refresh token 的 jti 與 exp ───────────────────────────────

    @Test
    void aRefreshTokenExposesItsJtiAndExpiryForTheRevocationList() {
        JwtTokenService service = serviceAt(NOW);
        IssuedTokens tokens = service.issue("operator", Role.OPERATOR);

        assertThat(service.verifyRefreshToken(tokens.refreshToken())).hasValueSatisfying(identity -> {
            assertThat(identity.tokenId()).isNotBlank().hasSize(36);
            assertThat(identity.expiresAt()).isEqualTo(NOW.plus(REFRESH));
        });
    }

    @Test
    void everyRefreshTokenHasItsOwnJtiSoOneRevocationNeverTouchesAnother() {
        JwtTokenService service = serviceAt(NOW);

        String first = service.verifyRefreshToken(service.issue("admin", Role.ADMIN).refreshToken()).orElseThrow().tokenId();
        String second = service.verifyRefreshToken(service.issue("admin", Role.ADMIN).refreshToken()).orElseThrow().tokenId();

        assertThat(first).isNotEqualTo(second);
    }

    @Test
    void aRefreshTokenWithoutJtiOrExpIsInvalid() {
        SecretKey key = Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));
        String noJti = Jwts.builder().subject("admin").claim("role", "ADMIN").claim("token_use", "refresh")
                .expiration(Date.from(NOW.plus(REFRESH))).signWith(key, Jwts.SIG.HS256).compact();
        String noExpiry = Jwts.builder().subject("admin").claim("role", "ADMIN").claim("token_use", "refresh")
                .id("some-jti").signWith(key, Jwts.SIG.HS256).compact();

        assertThat(serviceAt(NOW).verifyRefreshToken(noJti)).as("沒有 jti（來自更早的程式版本或偽造）").isEmpty();
        assertThat(serviceAt(NOW).verifyRefreshToken(noExpiry)).as("沒有 exp：永遠有效且無法定下名單項目的壽命").isEmpty();
        assertThat(serviceAt(NOW).verify(noJti, JwtTokenService.USE_REFRESH).outcome()).as("簽章與用途都對，只是不能撤銷")
                .isEqualTo(Outcome.VALID);
    }
}
