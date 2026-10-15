package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import org.springframework.stereotype.Component;

/**
 * Engine Bridge 的基底位址解析（契約 §3.1）：管理員在設定頁改過的 {@code autoclaude.engineUrl}／{@code sdd.engineUrl}
 * 優先，否則取 {@code ENGINE_BRIDGE_URL}（{@link BridgeProperties}，預設 {@value BridgeProperties#LOCAL_DEFAULT}）。
 * 每次呼叫都重新解析：設定改了，下一個 Bridge 呼叫就走新位址。
 */
@Component
public class BridgeEndpoints {

    static final String DEFAULT_HEALTH_PATH = "/health";

    private final SettingValues settings;
    private final BridgeProperties properties;

    public BridgeEndpoints(SettingValues settings, BridgeProperties properties) {
        this.settings = settings;
        this.properties = properties;
    }

    /** {@code /autoclaude/*} 的基底位址（不含結尾斜線）。 */
    public String autoclaudeBase() {
        return base("autoclaude");
    }

    /** {@code /sdd/*} 的基底位址（不含結尾斜線）。 */
    public String sddBase() {
        return base("sdd");
    }

    /** 健康探測路徑（{@code autoclaude.healthCheckPath}，預設 {@code /health}）。 */
    public String healthPath() {
        String path = settings.find("autoclaude", "healthCheckPath").orElse(DEFAULT_HEALTH_PATH);
        return path.startsWith("/") ? path : "/" + path;
    }

    private String base(String category) {
        String url = settings.findCustomized(category, "engineUrl").orElse(properties.url());
        return url.replaceAll("/+$", "");
    }
}
