package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.support.AbstractIntegrationTest;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.TestPropertySource;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * docker profile 的可信代理縮小之後，Tomcat 是否真的不再採信「不在子網內」的來源轉送的 {@code X-Forwarded-For}（QA O-20；契約 §0.4 第 4 點、附錄 D.2）。
 * 這支測試以 docker profile 的同一組屬性（{@code forward-headers-strategy=native}＋可信代理只限 compose 子網）起真的 Tomcat，
 * 測試 client 在 127.0.0.1（不在子網內）：偽造不同的 X-Forwarded-For 連打，限流必須仍視為同一個來源——第 N+1 次得 429。
 * 沒縮小時的對照見 {@link RemoteIpDefaultProxiesIT}（同樣的請求不會 429＝繞過）。
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@TestPropertySource(properties = {
        "console.security.rate-limit.enabled=true",
        "console.security.rate-limit.requests-per-minute=5",
        "console.security.rate-limit.trust-forwarded-for=true",
        "server.forward-headers-strategy=native",
        "server.tomcat.remoteip.internal-proxies=172\\.31\\.250\\.(?:[2-9]|[1-9]\\d|1\\d\\d|2[0-4]\\d|25[0-4])"})
class RemoteIpNarrowedProxiesIT extends AbstractIntegrationTest {

    @LocalServerPort
    private int port;

    @Test
    void aForwardedForFromAnUntrustedSourceIsIgnoredSoFiveFreeRequestsThenTheSixthIs429() throws Exception {
        List<Integer> statuses = RemoteIpProbe.statusesWithDistinctForwardedFor(port, 6);

        assertThat(statuses).as("每次都換一個偽造的 X-Forwarded-For，仍是同一個桶（127.0.0.1）").containsExactly(401, 401, 401, 401, 401, 429);
    }
}
