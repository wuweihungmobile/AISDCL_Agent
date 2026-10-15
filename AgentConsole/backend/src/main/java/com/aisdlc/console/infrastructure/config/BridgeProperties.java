package com.aisdlc.console.infrastructure.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Engine Bridge 位址的程序層預設（{@code console.bridge.url}，環境變數 {@code ENGINE_BRIDGE_URL}，預設
 * {@value #LOCAL_DEFAULT}——本機 bootRun 搭本機的 Bridge）。
 *
 * <p>解析順序（契約 §3.1、§5.0.1）：<b>管理員在設定頁改過的 {@code autoclaude.engineUrl}／{@code sdd.engineUrl}</b>
 * （值不等於出廠預設才算「改過」）優先；否則用本屬性——e2e 的 {@code http://127.0.0.1:18081}、compose 的
 * {@code http://engine-bridge:8081} 都由環境變數提供，設定頁沒動它們時不會被種子的出廠預設蓋掉。
 *
 * @param url 空白時退回 {@link #LOCAL_DEFAULT}
 */
@ConfigurationProperties(prefix = "console.bridge")
public record BridgeProperties(String url) {

    /** 本機開發位址。 */
    public static final String LOCAL_DEFAULT = "http://localhost:8081";

    public BridgeProperties {
        url = url == null || url.isBlank() ? LOCAL_DEFAULT : url.strip();
    }
}
