package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.application.port.out.BackupSettings;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Component;

import java.nio.file.Path;

/** {@link BackupSettings} 的實作：把 Spring 屬性（application 層不認得 {@code infrastructure}）轉成埠。 */
@Component
@EnableConfigurationProperties(BackupProperties.class)
class BackupSettingsAdapter implements BackupSettings {

    private final BackupProperties properties;

    BackupSettingsAdapter(BackupProperties properties) {
        this.properties = properties;
    }

    @Override
    public Path exportDir() {
        return properties.exportDir() == null ? null : Path.of(properties.exportDir());
    }

    @Override
    public Path requestDir() {
        return properties.requestDir() == null ? null : Path.of(properties.requestDir());
    }

    @Override
    public int requestTtlSeconds() {
        return properties.requestTtlSeconds();
    }

    @Override
    public int jobMaxSeconds() {
        return properties.jobMaxSeconds();
    }

    @Override
    public long reconcileIntervalMs() {
        return properties.reconcileIntervalMs();
    }

    @Override
    public int overdueGraceMinutes() {
        return properties.overdueGraceMinutes();
    }

    @Override
    public long minFullIntervalSeconds() {
        return properties.minFullIntervalSeconds();
    }

    @Override
    public long minDiffIntervalSeconds() {
        return properties.minDiffIntervalSeconds();
    }
}
