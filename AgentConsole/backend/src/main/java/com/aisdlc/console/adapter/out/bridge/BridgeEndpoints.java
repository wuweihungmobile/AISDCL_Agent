package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.SettingValues;
import com.aisdlc.console.infrastructure.config.BridgeProperties;
import org.springframework.stereotype.Component;

import java.util.Optional;

/**
 * Engine Bridge 的基底位址解析（契約 §3.1）：管理員在設定頁改過的 {@code autoclaude.engineUrl}／{@code sdd.engineUrl}
 * 優先，否則取 {@code ENGINE_BRIDGE_URL}（{@link BridgeProperties}，預設 {@value BridgeProperties#LOCAL_DEFAULT}）。
 * 每次呼叫都重新解析：設定改了，下一個 Bridge 呼叫就走新位址。
 */
@Component
public class BridgeEndpoints {

    /**
     * 設定缺席時的兜底健康探測路徑（契約 §0.5 V11、§3.1；D-17）：v1.4 起探測環打 Bridge 的深度探針 {@code /health/deep}
     * （git、autoclaude 匯入、工作區可寫、DB；v1.3 以前是淺層 {@code /health}，引擎壞了它照回 200）。種子預設與既有列的校正
     * 由 Flyway V11 負責；這個常數只在 {@code system_configs} 沒有該鍵時才用到。
     */
    static final String DEFAULT_HEALTH_PATH = "/health/deep";

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

    /**
     * {@code /si/*} 的基底位址（不含結尾斜線）：解析規則與 {@link #sddBase()} 相同（自訂的 {@code sdd.engineUrl} 優先，否則
     * {@code ENGINE_BRIDGE_URL}）。SelfImproving 沒有自己的 engineUrl 設定鍵——同一個 Bridge 服務所有路徑前綴（TCS-P1b ⚖14）。
     */
    public String siBase() {
        return base("sdd");
    }

    /** 健康探測路徑（{@code autoclaude.healthCheckPath}，預設 {@code /health/deep}）。 */
    public String healthPath() {
        String path = settings.find("autoclaude", "healthCheckPath").orElse(DEFAULT_HEALTH_PATH);
        return path.startsWith("/") ? path : "/" + path;
    }

    /**
     * SDD 寫入權杖（{@code console.bridge.sdd-write-token}；ADR-XPLAT-016 §9）：只給 Bridge 出站介面卡附 {@code X-Bridge-Token}
     * 標頭用，未設為空。🔴 值絕不進日誌、錯誤封包或 {@code details}。
     */
    public Optional<String> sddWriteToken() {
        return Optional.ofNullable(properties.sddWriteToken());
    }

    /**
     * SelfImproving 寫入權杖（{@code console.bridge.si-write-token}；TCS-SelfImprovingDecide-P2b W9）：只給 Bridge 出站介面卡附
     * {@code X-Bridge-Token} 標頭用（三個稽核檔落地的 POST；預檢不帶），未設為空。與 SDD 權杖是兩個獨立的值。
     * 🔴 值絕不進日誌、錯誤封包或 {@code details}。
     */
    public Optional<String> siWriteToken() {
        return Optional.ofNullable(properties.siWriteToken());
    }

    private String base(String category) {
        String url = settings.findCustomized(category, "engineUrl").orElse(properties.url());
        return url.replaceAll("/+$", "");
    }
}
