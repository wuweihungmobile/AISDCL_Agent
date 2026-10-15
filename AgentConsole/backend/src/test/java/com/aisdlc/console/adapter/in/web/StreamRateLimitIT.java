package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.model.auth.Role;
import com.aisdlc.console.infrastructure.security.JwtTokenService;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.SseProbe;
import com.aisdlc.console.support.SseProbe.Frame;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SSE 與限流（契約 §0.4 第 4 點、§2.1）：一條長連線只算<b>一次</b>請求——不是每個框架一次，連線結束時的 ASYNC dispatch 也不重複計；
 * 被限流的使用者不影響他已經開著的串流；{@code ?access_token=} 開的串流與標頭開的串流用同一個桶（鍵是 JWT subject）；
 * 429 對跨來源的前端仍讀得到 {@code Retry-After}（CORS exposed headers，契約 §0.7）。
 * 為什麼重要：若串流的每個框架或結束動作也扣額度，一條正常的長串流就會把使用者自己鎖在外面（所有 REST 輪詢都 429）。
 * 限流上限在這支測試調成 40（省掉 100 次請求）；每個測試用全新的 JWT subject，互不共用桶（視窗是固定的 60 秒）。
 */
@TestPropertySource(properties = {
        "console.security.rate-limit.enabled=true",
        "console.security.rate-limit.requests-per-minute=40"
})
class StreamRateLimitIT extends AbstractExecutionIT {

    private static final String PROJECTS = "/api/v1/projects";

    @Autowired
    private JwtTokenService jwt;

    private String freshToken() {
        return jwt.issue("rl-sse-" + UUID.randomUUID(), Role.VIEWER).accessToken();
    }

    private String logs(String run) {
        return baseUrl() + "/api/v1/stream/executions/" + run + "/logs";
    }

    @Test
    void anOpenStreamCountsAsExactlyOneRequestAndItsAsyncCompletionIsNotCounted() {
        Fixture f = prjA("rate-limit-count", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();

        String token = freshToken();
        SseProbe stream = SseProbe.open(logs(run) + "?tail=0", Map.of("Authorization", "Bearer " + token));
        try {
            assertThat(stream.status()).isEqualTo(200);
            for (int i = 1; i <= 30; i++) {
                Resp resp = api.get(token, "/api/v1/executions/" + run);
                assertThat(resp.status()).as("串流佔 1 次，第 %d 次一般請求", i).isEqualTo(200);
                assertThat(resp.header("X-RateLimit-Limit")).isEqualTo("40");
                assertThat(resp.header("X-RateLimit-Remaining")).as("第 %d 次一般請求之後", i)
                        .isEqualTo(Integer.toString(40 - 1 - i));
            }

            // 放行全部步驟：串流收到終態後由伺服器關閉，結束時 Servlet 容器會再做一次 ASYNC dispatch——這次不得扣額度
            mini(run).release(5);
            assertThat(stream.awaitEnd(Duration.ofSeconds(20))).isTrue();

            for (int i = 31; i <= 39; i++) {
                Resp resp = api.get(token, "/api/v1/executions/" + run);
                assertThat(resp.status()).as("串流結束後第 %d 次一般請求（若 ASYNC dispatch 被計入，第 39 次會先 429）", i)
                        .isEqualTo(200);
                assertThat(resp.header("X-RateLimit-Remaining")).isEqualTo(Integer.toString(40 - 1 - i));
            }
            Resp limited = api.get(token, "/api/v1/executions/" + run);
            assertThat(limited.status()).as("串流 1 次＋一般請求 39 次＝40 次，第 41 次才是 429").isEqualTo(429);
            assertThat(limited.<String>read("$.reason")).isEqualTo("超過每分鐘 100 次請求上限");
            assertThat(limited.<Integer>read("$.details.limit")).isEqualTo(40);
            assertThat(limited.header("Retry-After")).isNotBlank();
        } finally {
            stream.close();
        }
    }

    @Test
    void aUserWhoHitsTheLimitKeepsReceivingOnTheStreamHeAlreadyOpened() {
        Fixture f = prjA("rate-limit-live", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();

        String token = freshToken();
        SseProbe stream = SseProbe.open(logs(run) + "?tail=0", Map.of("Authorization", "Bearer " + token));
        try {
            for (int i = 1; i <= 39; i++) {
                assertThat(api.get(token, "/api/v1/executions/" + run).status()).isEqualTo(200);
            }
            assertThat(api.get(token, "/api/v1/executions/" + run).status()).as("額度用盡").isEqualTo(429);
            assertThat(stream.events()).as("tail=0：被限流之前沒有任何事件").isEmpty();

            mini(run).release(5);
            assertThat(stream.awaitEnd(Duration.ofSeconds(20))).as("已開著的串流不受限流影響，照常跑到終態").isTrue();

            List<Frame> statuses = stream.events("status-change");
            assertThat(statuses).isNotEmpty();
            assertThat(statuses.get(statuses.size() - 1).json().get("runStatus").asString()).isEqualTo("COMPLETED");
            assertThat(stream.events("log")).as("每一步都有日誌事件").isNotEmpty();
            assertThat(SseProbe.strictlyIncreasing(stream.events())).isTrue();
            assertThat(api.get(token, "/api/v1/executions/" + run).status()).as("視窗未過期，仍是 429").isEqualTo(429);
        } finally {
            stream.close();
        }
    }

    @Test
    void aStreamOpenedWithTheQueryTokenSharesTheBucketOfItsSubject() {
        Fixture f = prjA("rate-limit-query", 4);
        String run = startRun(f.projectId());
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        String token = freshToken();

        SseProbe viaQuery = SseProbe.open(logs(run) + "?access_token=" + token, Map.of());
        try {
            assertThat(viaQuery.status()).isEqualTo(200);
            assertThat(viaQuery.awaitEnd(Duration.ofSeconds(10))).isTrue();
        } finally {
            viaQuery.close();
        }
        Resp next = api.get(token, "/api/v1/executions/" + run);
        assertThat(next.header("X-RateLimit-Remaining")).as("query token 開的串流算在同一個 subject 的桶（1＋1＝2 次）")
                .isEqualTo("38");
    }

    @Test
    void aThrottledResponseExposesRetryAfterToACrossOriginFrontend() {
        String token = freshToken();
        for (int i = 0; i < 40; i++) {
            assertThat(api.get(token, PROJECTS).status()).isEqualTo(200);
        }
        Resp limited = api.send(token, MockMvcRequestBuilders.get(PROJECTS)
                .header(HttpHeaders.ORIGIN, "http://localhost:3000"));
        assertThat(limited.status()).isEqualTo(429);
        assertThat(limited.header(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)).isEqualTo("http://localhost:3000");
        assertThat(limited.header(HttpHeaders.ACCESS_CONTROL_EXPOSE_HEADERS)).contains("Retry-After", "X-Trace-Id");
        assertThat(limited.header("Retry-After")).isNotBlank();
    }
}
