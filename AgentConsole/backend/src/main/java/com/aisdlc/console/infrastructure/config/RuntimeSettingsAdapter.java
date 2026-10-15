package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.application.port.out.RuntimeSettings;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/** {@link RuntimeSettings} 的實作：把 Spring 屬性（application 層不認得 {@code infrastructure}）轉成埠。 */
@Component
@EnableConfigurationProperties({ExecutionProperties.class, SseProperties.class, MonitorProperties.class})
class RuntimeSettingsAdapter implements RuntimeSettings {

    private final ConsoleSecurityProperties security;
    private final ExecutionProperties execution;
    private final SseProperties sse;
    private final MonitorProperties monitor;

    RuntimeSettingsAdapter(ConsoleSecurityProperties security, ExecutionProperties execution, SseProperties sse,
                           MonitorProperties monitor) {
        this.security = security;
        this.execution = execution;
        this.sse = sse;
        this.monitor = monitor;
    }

    @Override
    public Set<String> evaluatorAllowlist() {
        return security.evaluatorAllowlist().stream().map(s -> s.strip().toLowerCase(Locale.ROOT))
                .filter(s -> !s.isEmpty()).collect(Collectors.toUnmodifiableSet());
    }

    @Override
    public Map<String, String> mockEnv() {
        return Map.copyOf(execution.mockEnv());
    }

    @Override
    public int sseKeepAliveSeconds() {
        return sse.keepAliveSeconds();
    }

    @Override
    public int sseQueueSize() {
        return sse.queueSize();
    }

    @Override
    public Duration consumerIdleTimeout() {
        return execution.consumer().idleTimeout();
    }

    @Override
    public Duration consumerBackoffInitial() {
        return execution.consumer().backoffInitial();
    }

    @Override
    public Duration consumerBackoffMax() {
        return execution.consumer().backoffMax();
    }

    @Override
    public Duration monitorTickInterval() {
        return monitor.tickInterval();
    }

    @Override
    public int healthProbeCapacity() {
        return monitor.probeCapacity();
    }

    @Override
    public boolean backgroundEnabled() {
        return monitor.backgroundEnabled();
    }
}
