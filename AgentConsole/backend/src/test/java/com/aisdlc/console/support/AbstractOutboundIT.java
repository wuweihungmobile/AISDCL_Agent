package com.aisdlc.console.support;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.TestPropertySource;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 需要「外呼」的整合測試共同基底：模擬 e2e profile 的外呼設定（契約 §5.0.1）——
 * <ul>
 *   <li>{@code allow-loopback=true}：列在 allowlist 內的 {@code 127.0.0.1} 才放行（假伺服器綁 loopback）；
 *       link-local／私網任何情形都拒；</li>
 *   <li>{@code rebind.e2e.test} 在 allowlist 內，但被 {@code test-dns-overrides} 解析到私網 {@code 10.0.0.5}——
 *       讓 {@code dns_rebinding} 可決定性重現；</li>
 *   <li>{@code console.bridge.url} 指向假 Bridge（{@link OutboundFakes#BRIDGE}）。</li>
 * </ul>
 * 全部子類別共用同一組屬性，因此 Spring 只會建立一個這種 context。
 */
@TestPropertySource(properties = {
        "console.security.allow-loopback=true",
        "console.security.outbound-allowlist=127.0.0.1,localhost,rebind.e2e.test,api.minimax.io",
        "console.security.test-dns-overrides[rebind.e2e.test]=10.0.0.5"
})
public abstract class AbstractOutboundIT extends AbstractApiIT {

    @DynamicPropertySource
    static void fakeBridge(DynamicPropertyRegistry registry) {
        registry.add("console.bridge.url", () -> OutboundFakes.BRIDGE.url(""));
    }

    @BeforeEach
    void resetFakeServers() {
        OutboundFakes.resetAll();
    }

    /** admin 把模型設定指向假 LLM 並設一把假金鑰（契約 §5.0.2；每個測試結束時 {@link AbstractApiIT} 會還原全部設定）。 */
    protected void configureFakeModel() {
        putSetting("model", "apiUrl", OutboundFakes.LLM.url(OutboundFakes.CHAT_PATH), false);
        putSetting("model", "apiKey", "sk-e2e-dummy", true);
        putSetting("model", "name", "e2e-model", false);
        putSetting("model", "timeout", "30", false);
    }

    protected void putSetting(String category, String key, String value, boolean confirm) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("value", value);
        if (confirm) {
            body.put("confirm", true);
        }
        ApiClient.Resp resp = api.put(admin(), "/api/v1/settings/" + category + "/" + key, body);
        if (resp.status() != 200) {
            throw new IllegalStateException("設定 " + category + "." + key + " 失敗：" + resp.status() + " "
                    + resp.body());
        }
    }
}
