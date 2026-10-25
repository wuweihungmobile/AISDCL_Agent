package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.application.port.out.SiWriteSettings;
import com.aisdlc.console.domain.model.si.SiAuditKeyRing;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.List;

/** {@link SiWriteSettings} 的實作：把 Spring 屬性（application 層不認得 {@code infrastructure}）轉成埠。 */
@Component
@EnableConfigurationProperties(SiWriteProperties.class)
class SiWriteSettingsAdapter implements SiWriteSettings {

    private final SiWriteProperties si;
    private final BridgeProperties bridge;

    SiWriteSettingsAdapter(SiWriteProperties si, BridgeProperties bridge) {
        this.si = si;
        this.bridge = bridge;
    }

    @Override
    public List<String> deciders() {
        return si.deciders();
    }

    @Override
    public SiAuditKeyRing keyRing() {
        return si.keyRing();
    }

    @Override
    public boolean bridgeWriteTokenConfigured() {
        return bridge.siWriteTokenConfigured();
    }
}
