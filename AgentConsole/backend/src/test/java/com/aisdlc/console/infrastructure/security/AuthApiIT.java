package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.domain.model.auth.Role;
import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Value;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** 登入、續期與 token 驗證（ADR-001 D4；NFR-9.2-01：JWT 30 分鐘＋Refresh）。走完整 filter chain。 */
class AuthApiIT extends AbstractApiIT {

    @Value("${console.auth.jwt-secret}")
    String secret;

    private Resp login(String username, String password) {
        return api.post(null, "/api/v1/auth/login", Map.of("username", username, "password", password));
    }

    @Test
    void eachConfiguredUserLogsInAndReceivesTheirRoleAndAThirtyMinuteToken() {
        for (Map.Entry<String, String> user : Map.of("admin", "ADMIN", "operator", "OPERATOR", "viewer", "VIEWER")
                .entrySet()) {
            Resp resp = login(user.getKey(), user.getKey().substring(0, 1).toUpperCase() + user.getKey().substring(1)
                    + "#Dev2026");
            assertThat(resp.status()).as(user.getKey()).isEqualTo(200);
            assertThat(resp.<Integer>read("$.code")).isEqualTo(200);
            assertThat(resp.<String>read("$.message")).isEqualTo("success");
            assertThat(resp.<String>read("$.data.role")).isEqualTo(user.getValue());
            assertThat(resp.<Integer>read("$.data.expiresIn")).isEqualTo(1800);
            assertThat(resp.<String>read("$.data.accessToken")).isNotBlank().contains(".");
            assertThat(resp.<String>read("$.data.refreshToken")).isNotBlank().isNotEqualTo(
                    resp.<String>read("$.data.accessToken"));
        }
    }

    @Test
    void wrongPasswordAndUnknownUserGetTheSameFourZeroOneSoAccountsCannotBeEnumerated() {
        Resp wrongPassword = login("admin", "not-the-password");
        Resp unknownUser = login("nobody", "whatever");
        assertThat(wrongPassword.status()).isEqualTo(401);
        assertThat(unknownUser.status()).isEqualTo(401);
        assertThat(wrongPassword.<String>read("$.message")).isEqualTo(unknownUser.<String>read("$.message"));
        assertThat(wrongPassword.<String>read("$.reason")).isEqualTo("INVALID_CREDENTIALS");
        assertThat(unknownUser.<String>read("$.reason")).isEqualTo("INVALID_CREDENTIALS");
        assertThat(wrongPassword.body()).doesNotContain("not-the-password");
    }

    @Test
    void missingFieldsAreRejectedWithFieldLevelErrors() {
        Resp resp = api.post(null, "/api/v1/auth/login", Map.of("username", " "));
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.errorFields()).containsExactlyInAnyOrder("username", "password");
    }

    @Test
    void refreshTokenIssuesAFreshWorkingPair() {
        Resp first = login("operator", "Operator#Dev2026");
        Resp refreshed = api.post(null, "/api/v1/auth/refresh",
                Map.of("refreshToken", first.<String>read("$.data.refreshToken")));
        assertThat(refreshed.status()).isEqualTo(200);
        assertThat(refreshed.<String>read("$.data.role")).isEqualTo("OPERATOR");
        assertThat(refreshed.<String>read("$.data.accessToken")).isNotEqualTo(first.<String>read("$.data.accessToken"));
        assertThat(api.get(refreshed.read("$.data.accessToken"), "/api/v1/projects").status()).isEqualTo(200);
    }

    @Test
    void anAccessTokenCannotBeUsedAsARefreshTokenAndViceVersa() {
        Resp first = login("operator", "Operator#Dev2026");
        Resp refreshWithAccess = api.post(null, "/api/v1/auth/refresh",
                Map.of("refreshToken", first.<String>read("$.data.accessToken")));
        assertThat(refreshWithAccess.status()).isEqualTo(401);
        assertThat(refreshWithAccess.<String>read("$.reason")).isEqualTo("INVALID_REFRESH_TOKEN");

        Resp callWithRefresh = api.get(first.read("$.data.refreshToken"), "/api/v1/projects");
        assertThat(callWithRefresh.status()).isEqualTo(401);
        assertThat(callWithRefresh.<String>read("$.reason")).isEqualTo("TOKEN_INVALID");
    }

    @Test
    void anExpiredAccessTokenIsToldApartFromAnInvalidOne() {
        Instant twoHoursAgo = Instant.now().minus(Duration.ofHours(2));
        JwtTokenService past = new JwtTokenService(secret, Duration.ofMinutes(30), Duration.ofDays(7),
                Clock.fixed(twoHoursAgo, ZoneOffset.UTC));
        String expired = past.issue("operator", Role.OPERATOR).accessToken();
        Resp resp = api.get(expired, "/api/v1/projects");
        assertThat(resp.status()).isEqualTo(401);
        assertThat(resp.<String>read("$.reason")).isEqualTo("TOKEN_EXPIRED");
    }

    @Test
    void tamperedWrongKeyAndAlgNoneTokensAreAllRejected() {
        String valid = login("operator", "Operator#Dev2026").read("$.data.accessToken");
        String tampered = valid.substring(0, valid.length() - 2) + (valid.endsWith("AA") ? "BB" : "AA");

        JwtTokenService otherKey = new JwtTokenService("another-secret-another-secret-another-secret",
                Duration.ofMinutes(30), Duration.ofDays(7), Clock.systemUTC());
        String wrongKey = otherKey.issue("admin", Role.ADMIN).accessToken();

        String header = Base64.getUrlEncoder().withoutPadding().encodeToString("{\"alg\":\"none\"}".getBytes());
        String payload = Base64.getUrlEncoder().withoutPadding().encodeToString(
                ("{\"sub\":\"admin\",\"role\":\"ADMIN\",\"token_use\":\"access\",\"exp\":"
                        + (Instant.now().getEpochSecond() + 3600) + "}").getBytes());
        String algNone = header + "." + payload + ".";

        for (String bad : new String[] {tampered, wrongKey, algNone, "not-a-jwt"}) {
            Resp resp = api.get(bad, "/api/v1/projects");
            assertThat(resp.status()).as(bad).isEqualTo(401);
            assertThat(resp.<String>read("$.reason")).as(bad).isEqualTo("TOKEN_INVALID");
        }
    }

    @Test
    void noTokenAtAllIsUnauthenticatedWithATraceId() {
        Resp resp = api.get(null, "/api/v1/projects");
        assertThat(resp.status()).isEqualTo(401);
        assertThat(resp.<String>read("$.reason")).isEqualTo("UNAUTHENTICATED");
        assertThat(resp.<String>read("$.traceId")).isEqualTo(resp.header("X-Trace-Id"));
    }
}
