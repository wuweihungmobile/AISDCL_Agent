package com.aisdlc.console.infrastructure.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.regex.Pattern;

/**
 * Engine Bridge 位址的程序層預設（{@code console.bridge.url}，環境變數 {@code ENGINE_BRIDGE_URL}，預設
 * {@value #LOCAL_DEFAULT}——本機 bootRun 搭本機的 Bridge）與兩個寫入權杖（{@code console.bridge.sdd-write-token}、
 * {@code console.bridge.si-write-token}）。
 *
 * <p>解析順序（契約 §3.1、§5.0.1）：<b>管理員在設定頁改過的 {@code autoclaude.engineUrl}／{@code sdd.engineUrl}</b>
 * （值不等於出廠預設才算「改過」）優先；否則用本屬性——e2e 的 {@code http://127.0.0.1:18081}、compose 的
 * {@code http://engine-bridge:8081} 都由環境變數提供，設定頁沒動它們時不會被種子的出廠預設蓋掉。
 *
 * <p><b>SDD 寫入權杖</b>（v1.5；契約附錄 D.2、ADR-XPLAT-016 §9）：環境變數 {@code BRIDGE_SDD_WRITE_TOKEN}（與 Bridge 同名同值），
 * 附在 {@code X-Bridge-Token} 標頭，只用於會觸發 FSM 寫入的四個呼叫（{@code :freeze}、帶 {@code sdd} 的建立批次、SDD run 的
 * {@code :resume}／{@code /restore}）。未設（空白）＝SDD 寫入面整個停用（預設值）；<b>有設但短於 32 字元，或仍是 {@code <…>} 佔位
 * ＝啟動即失敗</b>（fail-loud，不靜默退回停用）。
 *
 * <p><b>SelfImproving 寫入權杖</b>（P2b；TCS-SelfImprovingDecide-P2b W9）：環境變數 {@code BRIDGE_SI_WRITE_TOKEN}（與 Bridge 同名同值，
 * 與 SDD 權杖是兩個獨立的值），同一個標頭，只用於三個稽核檔落地的 POST（決定、新增觀察、關閉觀察；預檢不需權杖）。規則與
 * SDD 權杖相同（未設＝停用、過短或佔位＝啟動失敗）。
 *
 * <p>🔴 權杖值絕不進日誌、錯誤封包或 {@code details}：本類別的 {@link #toString()} 與驗證錯誤訊息都只講長度，不含值。
 *
 * @param url           空白時退回 {@link #LOCAL_DEFAULT}
 * @param sddWriteToken 空白＝null（停用）；非空白時已去前後空白並通過長度與佔位檢查
 * @param siWriteToken  同上（SelfImproving 寫入面）
 */
@ConfigurationProperties(prefix = "console.bridge")
public record BridgeProperties(String url, String sddWriteToken, String siWriteToken) {

    /** 本機開發位址。 */
    public static final String LOCAL_DEFAULT = "http://localhost:8081";
    /** 寫入權杖的最短長度（與 Bridge 一致；{@code openssl rand -hex 32} 產出 64 字元）。 */
    public static final int MIN_TOKEN_CHARS = 32;

    /** {@code <YOUR_BRIDGE_SDD_WRITE_TOKEN_MIN_32_CHARS>} 這類 {@code .env.example} 佔位。 */
    private static final Pattern PLACEHOLDER = Pattern.compile("^<[^<>]*>$");

    public BridgeProperties {
        url = url == null || url.isBlank() ? LOCAL_DEFAULT : url.strip();
        sddWriteToken = checkedToken(sddWriteToken, "console.bridge.sdd-write-token", "BRIDGE_SDD_WRITE_TOKEN",
                "SDD 寫入面");
        siWriteToken = checkedToken(siWriteToken, "console.bridge.si-write-token", "BRIDGE_SI_WRITE_TOKEN",
                "SelfImproving 寫入面");
    }

    /** backend 有設定 SDD 寫入權杖（SDD 寫入面啟用）。 */
    public boolean sddWriteTokenConfigured() {
        return sddWriteToken != null;
    }

    /** backend 有設定 SelfImproving 寫入權杖（寫入面另需稽核簽章金鑰才啟用）。 */
    public boolean siWriteTokenConfigured() {
        return siWriteToken != null;
    }

    private static String checkedToken(String raw, String property, String variable, String surface) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        String token = raw.strip();
        if (PLACEHOLDER.matcher(token).matches()) {
            throw new IllegalArgumentException(property + "（環境變數 " + variable + "）仍是 <…> 佔位，"
                    + "請換成至少 " + MIN_TOKEN_CHARS + " 字元的隨機值（例：openssl rand -hex 32），或留空以停用 " + surface);
        }
        if (token.length() < MIN_TOKEN_CHARS) {
            throw new IllegalArgumentException(property + "（環境變數 " + variable + "）只有 " + token.length()
                    + " 字元，至少需要 " + MIN_TOKEN_CHARS + " 字元（例：openssl rand -hex 32）；或留空以停用 " + surface);
        }
        return token;
    }

    /** 權杖值不外洩：只標示有沒有設。 */
    @Override
    public String toString() {
        return "BridgeProperties[url=" + url + ", sddWriteToken=" + (sddWriteToken == null ? "<unset>" : "<set>")
                + ", siWriteToken=" + (siWriteToken == null ? "<unset>" : "<set>") + "]";
    }
}
