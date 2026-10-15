package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.support.AbstractIntegrationTest;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.TestPropertySource;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 對照組：沒有縮小可信代理（Tomcat 預設信任所有私網位址與 loopback）時，來自 127.0.0.1 的測試 client 轉送的 {@code X-Forwarded-For}
 * 被採信，每個偽造的位址各得一個新桶——未認證限流因此可被繞過（QA O-20 的原始症狀）。這支測試存在的理由：
 * 它讓 {@link RemoteIpNarrowedProxiesIT} 的結論有鑑別力（若這裡也 429，代表那支測試根本沒在測可信代理）；
 * 同時記錄 e2e／本機 profile「刻意不縮小」的行為（e2e 的測試 client 在 loopback，需要被信任）。
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@TestPropertySource(properties = {
        "console.security.rate-limit.enabled=true",
        "console.security.rate-limit.requests-per-minute=5",
        "console.security.rate-limit.trust-forwarded-for=true",
        "server.forward-headers-strategy=native"})
class RemoteIpDefaultProxiesIT extends AbstractIntegrationTest {

    @LocalServerPort
    private int port;

    @Test
    void aForwardedForFromALoopbackClientIsTrustedByTomcatsDefaultSoEachFakeAddressGetsItsOwnBucket() throws Exception {
        List<Integer> statuses = RemoteIpProbe.statusesWithDistinctForwardedFor(port, 6);

        assertThat(statuses).as("沒縮小可信代理：偽造 X-Forwarded-For 繞過限流").containsOnly(401);
    }
}
