package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.domain.model.auth.Role;
import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

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

    // ── v1.4（D-19；契約 §1.9）：refresh token 輪替撤銷與登出 ─────────────────────────────────────────
    // 為什麼重要：沒有撤銷名單時，登出只清本機——被竊的 refresh token 在登出之後仍可換新到過期（最長 7 天）；
    // 換新不撤銷舊的，則一個 token 可以無限次換出新的一對。這裡用預設的測試設定（沒設 Redis＝純記憶體名單）走完整 filter chain 驗行為，
    // Redis 實作與降級另見 RefreshRevocationRedisIT／RefreshRevocationRedisDownIT。

    private Resp refresh(String refreshToken) {
        return api.post(null, "/api/v1/auth/refresh", Map.of("refreshToken", refreshToken));
    }

    private Resp logout(String refreshToken) {
        return api.post(null, "/api/v1/auth/logout", Map.of("refreshToken", refreshToken));
    }

    @Test
    void rotationRejectsTheOldTokenAndKeepsTheNewOne() {
        String rt1 = login("operator", "Operator#Dev2026").read("$.data.refreshToken");

        Resp second = refresh(rt1);
        assertThat(second.status()).isEqualTo(200);
        String rt2 = second.read("$.data.refreshToken");
        assertThat(rt2).isNotEqualTo(rt1);

        Resp replay = refresh(rt1);
        assertThat(replay.status()).as("舊的已在換新時被撤銷").isEqualTo(401);
        assertThat(replay.<String>read("$.reason")).isEqualTo("INVALID_REFRESH_TOKEN");

        Resp third = refresh(rt2);
        assertThat(third.status()).as("新的有效，並再換出下一個").isEqualTo(200);
        assertThat(third.<String>read("$.data.refreshToken")).isNotIn(rt1, rt2);
        assertThat(refresh(rt2).status()).as("rt2 換過一次也被撤銷").isEqualTo(401);
    }

    @Test
    void aRevokedRefreshTokenAsABearerIsStillTokenInvalid() {
        String rt1 = login("operator", "Operator#Dev2026").read("$.data.refreshToken");
        refresh(rt1);

        Resp asBearer = api.get(rt1, "/api/v1/projects");

        assertThat(asBearer.status()).isEqualTo(401);
        assertThat(asBearer.<String>read("$.reason")).as("與撤銷無關：refresh token 本來就不能當 access 用").isEqualTo("TOKEN_INVALID");
    }

    @Test
    void afterLogoutTheRefreshTokenCanNoLongerBeExchanged() {
        String rt = login("viewer", "Viewer#Dev2026").read("$.data.refreshToken");

        assertThat(logout(rt).status()).isEqualTo(204);

        Resp resp = refresh(rt);
        assertThat(resp.status()).isEqualTo(401);
        assertThat(resp.<String>read("$.reason")).isEqualTo("INVALID_REFRESH_TOKEN");
    }

    @Test
    void loggingOutOneSessionLeavesTheOtherSessionsOfTheSameUserAlone() {
        String sessionA = login("operator", "Operator#Dev2026").read("$.data.refreshToken");
        String sessionB = login("operator", "Operator#Dev2026").read("$.data.refreshToken");

        logout(sessionA);

        assertThat(refresh(sessionA).status()).isEqualTo(401);
        assertThat(refresh(sessionB).status()).as("名單以 token 的 jti 為鍵，不是以使用者為鍵").isEqualTo(200);
    }

    @Test
    void logoutAnswers204WhateverTheTokenIs() {
        Resp login = login("operator", "Operator#Dev2026");
        String rt = login.read("$.data.refreshToken");
        String access = login.read("$.data.accessToken");
        JwtTokenService past = new JwtTokenService(secret, Duration.ofMinutes(30), Duration.ofDays(7),
                Clock.fixed(Instant.now().minus(Duration.ofDays(8)), ZoneOffset.UTC));
        String expired = past.issue("operator", Role.OPERATOR).refreshToken();
        logout(rt);

        for (String token : new String[] {"not-a-jwt", "a.b.c", expired, access, rt, "   x   "}) {
            assertThat(logout(token).status()).as("[" + token + "]").isEqualTo(204);
        }
        assertThat(api.get(access, "/api/v1/projects").status()).as("登出不撤銷 access token（無狀態，最長 30 分鐘後自然失效）")
                .isEqualTo(200);
    }

    @Test
    void logoutWithoutARefreshTokenFieldIs400WithTheFieldName() {
        for (Object body : new Object[] {Map.of(), Map.of("refreshToken", ""), Map.of("refreshToken", "   ")}) {
            Resp resp = api.post(null, "/api/v1/auth/logout", body);
            assertThat(resp.status()).as(body.toString()).isEqualTo(400);
            assertThat(resp.errorFields()).containsExactly("refreshToken");
        }
    }

    @Test
    void anExpiredRefreshTokenIsRejectedByRefreshAndSilentlyAcceptedByLogout() {
        JwtTokenService past = new JwtTokenService(secret, Duration.ofMinutes(30), Duration.ofDays(7),
                Clock.fixed(Instant.now().minus(Duration.ofDays(8)), ZoneOffset.UTC));
        String expired = past.issue("operator", Role.OPERATOR).refreshToken();

        Resp resp = refresh(expired);
        assertThat(resp.status()).isEqualTo(401);
        assertThat(resp.<String>read("$.reason")).isEqualTo("INVALID_REFRESH_TOKEN");
        assertThat(logout(expired).status()).isEqualTo(204);
    }

    @Test
    void aRefreshTokenWithoutAJtiCannotBeExchangedBecauseItCouldNeverBeRevoked() {
        SecretKey key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        String noJti = Jwts.builder().subject("operator").claim("role", "OPERATOR").claim("token_use", "refresh")
                .expiration(Date.from(Instant.now().plus(Duration.ofDays(1)))).signWith(key, Jwts.SIG.HS256).compact();

        Resp resp = refresh(noJti);

        assertThat(resp.status()).isEqualTo(401);
        assertThat(resp.<String>read("$.reason")).isEqualTo("INVALID_REFRESH_TOKEN");
    }

    @Test
    void ofTwoConcurrentRefreshesOfTheSameTokenExactlyOneSucceeds() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            for (int round = 0; round < 25; round++) {
                String rt = login("operator", "Operator#Dev2026").read("$.data.refreshToken");
                CyclicBarrier start = new CyclicBarrier(2);
                List<Future<Integer>> statuses = new ArrayList<>();
                for (int i = 0; i < 2; i++) {
                    statuses.add(pool.submit(() -> {
                        start.await(5, TimeUnit.SECONDS);
                        return refresh(rt).status();
                    }));
                }
                List<Integer> result = new ArrayList<>();
                for (Future<Integer> status : statuses) {
                    result.add(status.get(20, TimeUnit.SECONDS));
                }
                assertThat(result).as("round " + round).containsExactlyInAnyOrder(200, 401);
            }
        } finally {
            pool.shutdownNow();
        }
    }

    @Test
    @ExtendWith(OutputCaptureExtension.class)
    void aLogoutIsAuditedWithAnEmptyAnonymousSubject(
            CapturedOutput output) {
        String rt = login("operator", "Operator#Dev2026").read("$.data.refreshToken");
        jdbc.execute("TRUNCATE console.audit_log");

        assertThat(logout(rt).status()).isEqualTo(204);

        List<Map<String, Object>> rows = jdbc.queryForList("select subject, role, method, entity_type, entity_id, "
                + "http_status from console.audit_log where path = '/api/v1/auth/logout'");
        assertThat(rows).singleElement().satisfies(row -> assertThat(row).containsEntry("subject", null)
                .containsEntry("method", "POST").containsEntry("entity_type", "auth").containsEntry("http_status", 204));
        assertThat(output.getAll()).as("日誌行帶語意標註 action").contains("\"action\":\"auth.logout\"")
                .contains("\"entity\":\"auth\"");
        assertThat(output.getAll()).as("日誌與審計都不含 token").doesNotContain(rt);
    }
}
