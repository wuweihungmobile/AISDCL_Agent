package com.aisdlc.console.adapter.out.http;

import com.aisdlc.console.application.port.out.OutboundHttp.HttpResult;
import com.aisdlc.console.application.port.out.OutboundHttp.OutboundIoException;
import com.aisdlc.console.domain.service.OutboundUrlPolicy;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.HostResolver;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.Rejected;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.Violation;
import com.aisdlc.console.support.FakeHttpServer;
import com.aisdlc.console.support.FakeHttpServer.Response;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.net.InetAddress;
import java.net.UnknownHostException;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 外呼 HTTP（NFR-SEC-04；契約 §1.5.7「連線實作」、AR-10）。為什麼重要：SSRF 防護的本質是「驗證過的 IP 就是實際連線的
 * IP」——解析一次、驗全部、就用那批位址連線（沒有第二次 DNS 查詢可被 rebinding）；3xx 不跟隨（否則重導向能把請求帶進內網）；
 * 政策拒絕時<b>一個封包都不能送出</b>。這裡用真的本機 HTTP 伺服器驗行為，而不是 mock。
 */
class PinnedOutboundHttpTest {

    private FakeHttpServer server;

    @BeforeEach
    void startServer() {
        server = FakeHttpServer.start();
    }

    @AfterEach
    void stopServer() {
        server.close();
    }

    private static HostResolver system() {
        return host -> List.of(InetAddress.getAllByName(host));
    }

    private PinnedOutboundHttp http(boolean allowLoopback, HostResolver resolver) {
        return new PinnedOutboundHttp(new OutboundUrlPolicy(List.of("127.0.0.1", "localhost", "rebind.test"),
                allowLoopback), resolver);
    }

    private HttpResult post(PinnedOutboundHttp http, String url, long totalMillis) {
        return http.postJson(url, Map.of("Authorization", "Bearer sk-test", "Content-Type", "application/json"),
                "{\"ping\":1}", Duration.ofSeconds(2), Duration.ofMillis(totalMillis));
    }

    @Test
    void aPostReachesTheServerWithTheHeadersAndBodyAndReturnsStatusBodyAndLatency() {
        server.on("POST", "/v1/chat/completions", Response.json(200, "{\"ok\":true}"));
        HttpResult result = post(http(true, system()), server.url("/v1/chat/completions"), 5_000);

        assertThat(result.status()).isEqualTo(200);
        assertThat(result.body()).isEqualTo("{\"ok\":true}");
        assertThat(result.resolvedHost()).isEqualTo("127.0.0.1");
        assertThat(result.latencyMs()).isGreaterThanOrEqualTo(0);
        assertThat(server.received()).singleElement().satisfies(request -> {
            assertThat(request.method()).isEqualTo("POST");
            assertThat(request.body()).isEqualTo("{\"ping\":1}");
            assertThat(request.headers()).containsEntry("authorization", "Bearer sk-test");
            assertThat(request.headers().get("content-type")).startsWith("application/json");
        });
    }

    @Test
    void theHostHeaderKeepsTheOriginalNameEvenThoughTheConnectionIsPinnedToTheValidatedAddress() {
        server.on("POST", "/x", Response.json(200, "{}"));
        // 名稱 host：resolver 回 127.0.0.1（e2e 的 allowlist 含 localhost 且 allow-loopback）
        post(http(true, system()), "http://localhost:" + server.port() + "/x", 5_000);
        assertThat(server.received()).singleElement().satisfies(request ->
                assertThat(request.headers().get("host")).isEqualTo("localhost:" + server.port()));
    }

    @Test
    void aRedirectIsNeverFollowedAndIsReturnedAsIs() {
        server.on("POST", "/start", Response.redirect(server.url("/redirected")));
        server.on("GET", "/redirected", Response.json(200, "{}"));
        server.on("POST", "/redirected", Response.json(200, "{}"));

        HttpResult result = post(http(true, system()), server.url("/start"), 5_000);

        assertThat(result.status()).isEqualTo(302);
        assertThat(server.receivedAt("/redirected")).as("3xx 不跟隨：重導向目標一個請求都不該收到").isEmpty();
    }

    @Test
    void nonSuccessStatusesAreReturnedNotThrown() {
        server.on("POST", "/auth", Response.json(401, "{\"error\":\"bad key\"}"));
        server.on("POST", "/boom", Response.json(503, "{\"error\":\"down\"}"));
        PinnedOutboundHttp http = http(true, system());
        assertThat(post(http, server.url("/auth"), 5_000).status()).isEqualTo(401);
        assertThat(post(http, server.url("/boom"), 5_000).status()).isEqualTo(503);
        assertThat(post(http, server.url("/missing"), 5_000).status()).isEqualTo(404);
    }

    @Test
    void aSlowServerBecomesATimeoutWithinRoughlyTheConfiguredTotal() {
        server.on("POST", "/slow", Response.json(200, "{}").delayed(8_000));
        long started = System.nanoTime();
        assertThatThrownBy(() -> post(http(true, system()), server.url("/slow"), 1_000))
                .isInstanceOfSatisfying(OutboundIoException.class,
                        e -> assertThat(e.kind()).isEqualTo(OutboundIoException.Kind.TIMEOUT));
        assertThat(Duration.ofNanos(System.nanoTime() - started)).isLessThan(Duration.ofSeconds(4));
    }

    @Test
    void aRefusedConnectionIsAConnectFailureWithoutLeakingTheUrl() {
        int closedPort = server.port();
        server.close();
        assertThatThrownBy(() -> post(http(true, system()), "http://127.0.0.1:" + closedPort + "/x", 2_000))
                .isInstanceOfSatisfying(OutboundIoException.class, e -> {
                    assertThat(e.kind()).isEqualTo(OutboundIoException.Kind.CONNECT);
                    assertThat(e.getMessage()).doesNotContain("127.0.0.1").doesNotContain("http");
                });
        server = FakeHttpServer.start();       // 讓 @AfterEach 的 close 對得上
    }

    @Test
    void anUnresolvableNameIsAConnectFailureNotAPolicyViolation() {
        HostResolver unresolvable = host -> {
            throw new UnknownHostException(host);
        };
        assertThatThrownBy(() -> post(http(true, unresolvable), "http://rebind.test/x", 2_000))
                .isInstanceOfSatisfying(OutboundIoException.class,
                        e -> assertThat(e.kind()).isEqualTo(OutboundIoException.Kind.CONNECT));
    }

    @Test
    void whenThePolicyRefusesNoRequestIsEverSent() {
        // allow-loopback＝false：127.0.0.1 在 allowlist 內也拒絕（production／docker 的設定）
        assertThatThrownBy(() -> post(http(false, system()), server.url("/v1/chat/completions"), 2_000))
                .isInstanceOfSatisfying(Rejected.class, r -> assertThat(r.violation()).isEqualTo(Violation.LOOPBACK));
        assertThat(server.received()).as("政策拒絕時未發出任何連線").isEmpty();
    }

    @Test
    void aNameResolvingToAPrivateAddressIsRefusedBeforeAnyConnection() {
        HostResolver rebinding = host -> List.of(InetAddress.getByName("10.0.0.5"));
        assertThatThrownBy(() -> post(http(true, rebinding), "http://rebind.test:" + server.port() + "/x", 2_000))
                .isInstanceOfSatisfying(Rejected.class,
                        r -> assertThat(r.violation()).isEqualTo(Violation.DNS_REBINDING));
        assertThat(server.received()).isEmpty();
    }

    @Test
    void theConnectionIsPinnedToTheFirstResolutionSoALaterRebindingCannotRedirectIt() {
        // 第一次解析回 127.0.0.1（合法）、之後每次都回私網位址：若實作在連線時又解析一次，就會連到 10.0.0.5 而失敗。
        AtomicInteger calls = new AtomicInteger();
        HostResolver flipping = host -> calls.getAndIncrement() == 0
                ? List.of(InetAddress.getByName("127.0.0.1")) : List.of(InetAddress.getByName("10.0.0.5"));
        server.on("POST", "/x", Response.json(200, "{\"pinned\":true}"));

        HttpResult result = post(http(true, flipping), "http://rebind.test:" + server.port() + "/x", 5_000);

        assertThat(result.status()).isEqualTo(200);
        assertThat(result.body()).contains("pinned");
        assertThat(calls.get()).as("整個呼叫只解析一次，沒有第二次 DNS 查詢可被 rebinding").isEqualTo(1);
        assertThat(server.received().get(0).headers().get("host")).isEqualTo("rebind.test:" + server.port());
    }
}
