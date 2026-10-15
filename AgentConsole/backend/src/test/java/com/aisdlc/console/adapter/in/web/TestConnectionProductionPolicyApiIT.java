package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * production／docker 的外呼政策（{@code allow-loopback=false}；契約 §1.5.7「放行規則一覽」、E2E-10 末段）。
 * 為什麼重要：e2e 為了讓假伺服器綁 127.0.0.1 而放行 loopback，但那個旗標一旦在正式環境意外生效，
 * 整個 SSRF 防線就破了。這裡用「allowlist 內刻意放了 127.0.0.1 與 localhost、旗標預設關閉」的設定，證明：
 * 列在 allowlist 內也不能讓 loopback 通過；名稱解析到 loopback 同樣被當成 DNS rebinding；私網任何設定都拒。
 * 不連真正的網路：被拒的請求在連線前就被擋下。
 */
@TestPropertySource(properties = "console.security.outbound-allowlist=127.0.0.1,localhost,api.minimax.io")
class TestConnectionProductionPolicyApiIT extends AbstractApiIT {

    private static final String URL = "/api/v1/settings/test-connection";
    private static final String OUTBOUND = "目標位址未通過 SSRF／allowlist 檢查";

    private Resp test(String apiUrl) {
        return api.post(admin(), URL, Map.of("apiUrl", apiUrl, "apiKey", "sk-secret-xyz"));
    }

    private void assertRefused(String apiUrl, String violation) {
        Resp resp = test(apiUrl);
        assertThat(resp.status()).as(apiUrl).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(OUTBOUND);
        assertThat(resp.<String>read("$.details.violation")).as(apiUrl).isEqualTo(violation);
        assertThat(resp.body()).doesNotContain("sk-secret-xyz");
    }

    @Test
    void aLoopbackLiteralIsRefusedEvenWhenItIsListedOnTheAllowlist() {
        assertRefused("http://127.0.0.1:8080/v1/chat/completions", "loopback");
        assertRefused("http://[::1]:8080/v1/chat/completions", "loopback");
    }

    @Test
    void anAllowlistedNameThatResolvesToLoopbackIsRefusedAsDnsRebinding() {
        assertRefused("http://localhost:8080/v1/chat/completions", "dns_rebinding");
    }

    @Test
    void privateAndLinkLocalAddressesAreRefusedHereToo() {
        assertRefused("http://10.0.0.5/v1", "private_ip");
        assertRefused("http://169.254.169.254/latest/meta-data", "link_local");
        assertRefused("https://example.com/v1", "not_in_allowlist");
    }

    @Test
    void savingModelApiUrlAppliesTheSameStaticRulesWithoutAnyDnsLookup() {
        Resp loopback = api.put(admin(), "/api/v1/settings/model/apiUrl",
                Map.of("value", "http://127.0.0.1:8080/v1/chat/completions"));
        assertThat(loopback.status()).isEqualTo(400);
        assertThat(loopback.<String>read("$.details.violation")).isEqualTo("loopback");

        Resp named = api.put(admin(), "/api/v1/settings/model/apiUrl",
                Map.of("value", "http://localhost:8080/v1/chat/completions"));
        assertThat(named.status()).as("儲存時不做 DNS：名稱在 allowlist 內就放行，連線前才檢查解析結果").isEqualTo(200);
    }
}
