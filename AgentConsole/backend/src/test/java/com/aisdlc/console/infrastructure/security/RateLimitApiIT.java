package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.domain.model.auth.Role;
import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 限流（NFR-9.2-06；契約 §0.4 第 4 點、E2E-11）。測試 profile 預設關閉限流（否則整套 IT 共用同一批 token 會互相擠掉額度），
 * 這一支把它開著打 101 次。為什麼重要：限流是「防暴力與失控輪詢」的最後一道牆——鍵必須是使用者（不是連線位址，
 * 否則 nginx 後所有人共用一個桶）、超限者必須先得 429 而不是 401／403、偽造 X-Forwarded-For 不得繞過、
 * 並發請求不得多放行一個。每個測試用全新的 JWT subject／IP，互不共用桶（視窗是固定的 60 秒）。
 */
@TestPropertySource(properties = "console.security.rate-limit.enabled=true")
class RateLimitApiIT extends AbstractApiIT {

    private static final String PROJECTS = "/api/v1/projects";
    private static final String REASON = "超過每分鐘 100 次請求上限";

    @Autowired
    private JwtTokenService jwt;

    private String freshToken(Role role) {
        return jwt.issue("rl-" + UUID.randomUUID(), role).accessToken();
    }

    private static String freshIp() {
        int n = Math.floorMod(UUID.randomUUID().hashCode(), 250) + 1;
        int m = Math.floorMod(UUID.randomUUID().hashCode(), 250) + 1;
        return "203.0." + n + "." + m;
    }

    private static MockHttpServletRequestBuilder get(String url, String remoteAddr) {
        return MockMvcRequestBuilders.get(url).with(request -> {
            request.setRemoteAddr(remoteAddr);
            return request;
        });
    }

    private void consume(String token, int times) {
        for (int i = 0; i < times; i++) {
            assertThat(api.get(token, PROJECTS).status()).isEqualTo(200);
        }
    }

    // ── 每個使用者每 60 秒 100 次 ─────────────────────────────────────────────────

    @Test
    void theHundredAndFirstRequestOfAUserIs429AfterHundredSucceedWithADecreasingRemainingCount() {
        String token = freshToken(Role.VIEWER);

        for (int i = 1; i <= 100; i++) {
            Resp resp = api.get(token, PROJECTS);
            assertThat(resp.status()).as("第 %d 次", i).isEqualTo(200);
            assertThat(resp.header("X-RateLimit-Limit")).isEqualTo("100");
            assertThat(resp.header("X-RateLimit-Remaining")).as("第 %d 次", i).isEqualTo(Integer.toString(100 - i));
        }

        Resp limited = api.get(token, PROJECTS);
        assertThat(limited.status()).isEqualTo(429);
        assertThat(limited.<Integer>read("$.code")).isEqualTo(429);
        assertThat(limited.<String>read("$.reason")).isEqualTo(REASON);
        assertThat(limited.<Integer>read("$.details.limit")).isEqualTo(100);
        assertThat(limited.<Integer>read("$.details.windowSeconds")).isEqualTo(60);
        int retryAfter = limited.<Integer>read("$.details.retryAfterSeconds");
        assertThat(retryAfter).isBetween(1, 60);
        assertThat(limited.header("Retry-After")).isEqualTo(Integer.toString(retryAfter));
        assertThat(limited.header("X-RateLimit-Remaining")).isEqualTo("0");
        assertThat(limited.header("X-RateLimit-Limit")).isEqualTo("100");
        assertThat(limited.header("Content-Type")).startsWith("application/json");
        assertThat(limited.<String>read("$.traceId")).isNotBlank().isEqualTo(limited.header("X-Trace-Id"));

        assertThat(api.get(token, PROJECTS).status()).as("視窗未過期前一直是 429").isEqualTo(429);
    }

    @Test
    void anotherUserIsNotAffectedAndActuatorRequestsAreNeverCounted() {
        String limitedUser = freshToken(Role.VIEWER);
        consume(limitedUser, 100);
        assertThat(api.get(limitedUser, PROJECTS).status()).isEqualTo(429);

        String other = freshToken(Role.OPERATOR);
        Resp otherResp = api.get(other, PROJECTS);
        assertThat(otherResp.status()).as("桶以使用者隔離：同一個連線位址不影響").isEqualTo(200);
        assertThat(otherResp.header("X-RateLimit-Remaining")).isEqualTo("99");

        Resp health = api.get(limitedUser, "/actuator/health");
        assertThat(health.status()).as("被限流的使用者照樣可以讀健康檢查").isEqualTo(200);
        assertThat(health.header("X-RateLimit-Limit")).as("/actuator 不計入").isNull();
    }

    @Test
    void nonApiPathsAreNeverLimitedNoMatterHowOftenTheyAreCalled() {
        for (int i = 0; i < 150; i++) {
            Resp resp = api.get(null, "/actuator/health");
            assertThat(resp.status()).isEqualTo(200);
            assertThat(resp.header("X-RateLimit-Limit")).isNull();
        }
        assertThat(api.get(null, "/v3/api-docs").status()).isEqualTo(200);
    }

    @Test
    void everyKindOfRequestCountsIncludingWritesAndRejectedOnesButThrottledRequestsAreNotAudited() {
        String token = freshToken(Role.VIEWER);
        consume(token, 99);

        Resp forbidden = api.post(token, PROJECTS, Map.of("name", "x", "executionPath", "/x", "passCriteria", "c"));
        assertThat(forbidden.status()).as("第 100 次：被拒絕的寫入也算一次").isEqualTo(403);
        assertThat(forbidden.header("X-RateLimit-Remaining")).isEqualTo("0");

        Resp limited = api.post(token, PROJECTS, Map.of("name", "x", "executionPath", "/x", "passCriteria", "c"));
        assertThat(limited.status()).as("超限者先得 429，而不是 403").isEqualTo(429);

        String subject = jwt.verify(token, JwtTokenService.USE_ACCESS).username();
        List<Integer> statuses = jdbc.queryForList("select http_status from console.audit_log where subject = ? and "
                + "method = 'POST' order by occurred_at", Integer.class, subject);
        assertThat(statuses).as("授權層拒絕的寫入留審計；被限流的 429 不寫庫（避免限流變成寫入放大器）").containsExactly(403);
    }

    @Test
    void concurrentRequestsNeverSlipPastTheLimit() throws Exception {
        String token = freshToken(Role.VIEWER);
        ExecutorService pool = Executors.newFixedThreadPool(16);
        try {
            List<Callable<Integer>> calls = new ArrayList<>();
            for (int i = 0; i < 150; i++) {
                calls.add(() -> api.get(token, PROJECTS).status());
            }
            int ok = 0;
            int limited = 0;
            for (Future<Integer> future : pool.invokeAll(calls)) {
                int status = future.get();
                if (status == 200) {
                    ok++;
                } else if (status == 429) {
                    limited++;
                }
            }
            assertThat(ok).as("恰好 100 次通過").isEqualTo(100);
            assertThat(limited).as("其餘 50 次 429，沒有任何其他狀態").isEqualTo(50);
        } finally {
            pool.shutdownNow();
        }
    }

    // ── 未認證：以客戶端位址計 ────────────────────────────────────────────────────

    @Test
    void unauthenticatedRequestsAreCountedPerClientAddressAndTheHundredAndFirstGets429BeforeAnyAuthDecision() {
        String ip = freshIp();
        for (int i = 1; i <= 100; i++) {
            assertThat(api.send(null, get(PROJECTS, ip)).status()).as("第 %d 次", i).isEqualTo(401);
        }
        Resp limited = api.send(null, get(PROJECTS, ip));
        assertThat(limited.status()).as("限流在授權之前：超限者先得 429，不是 401").isEqualTo(429);
        assertThat(limited.<String>read("$.reason")).isEqualTo(REASON);

        assertThat(api.send(null, get(PROJECTS, freshIp())).status()).as("換一個位址就是另一個桶").isEqualTo(401);
        assertThat(api.get(freshToken(Role.VIEWER), PROJECTS).status()).as("不吃已認證使用者的額度").isEqualTo(200);
    }

    @Test
    void aForgedXForwardedForHeaderCannotEvadeTheLimit() {
        String ip = freshIp();
        for (int i = 1; i <= 100; i++) {
            Resp resp = api.send(null, get(PROJECTS, ip).header("X-Forwarded-For", "198.51.100." + (i % 250)));
            assertThat(resp.status()).isEqualTo(401);
        }
        Resp limited = api.send(null, get(PROJECTS, ip).header("X-Forwarded-For", "192.0.2.77"));
        assertThat(limited.status()).as("每次換一個偽造的 XFF 也一樣被擋：過濾器只看 getRemoteAddr()").isEqualTo(429);
    }

    @Test
    void anInvalidTokenIsTreatedAsUnauthenticatedAndCountedByAddress() {
        String ip = freshIp();
        for (int i = 1; i <= 100; i++) {
            Resp resp = api.send("garbage-token", get(PROJECTS, ip));
            assertThat(resp.status()).isEqualTo(401);
        }
        assertThat(api.send("garbage-token", get(PROJECTS, ip)).status()).isEqualTo(429);
    }

    @Test
    void theLoginEndpointIsCountedByAddressToo() {
        String ip = freshIp();
        Resp wrong = api.send(null, MockMvcRequestBuilders.post("/api/v1/auth/login")
                .contentType("application/json").content("{\"username\":\"nobody\",\"password\":\"wrong\"}")
                .with(request -> {
                    request.setRemoteAddr(ip);
                    return request;
                }));

        assertThat(wrong.status()).isEqualTo(401);
        assertThat(wrong.header("X-RateLimit-Limit")).isEqualTo("100");
        assertThat(wrong.header("X-RateLimit-Remaining")).isEqualTo("99");
    }
}
