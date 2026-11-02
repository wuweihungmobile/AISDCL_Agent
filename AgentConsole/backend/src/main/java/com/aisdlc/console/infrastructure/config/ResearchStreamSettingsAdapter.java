package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.application.port.out.ResearchStreamSettings;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Component;

import java.time.Duration;

/** {@link ResearchStreamSettings} 的實作：把 Spring 屬性（application 層不認得 {@code infrastructure}）轉成埠；heartbeat 間隔沿用 {@code console.sse.keep-alive-seconds}。 */
@Component
@EnableConfigurationProperties(ResearchStreamProperties.class)
class ResearchStreamSettingsAdapter implements ResearchStreamSettings {

    private final ResearchStreamProperties research;
    private final SseProperties sse;

    ResearchStreamSettingsAdapter(ResearchStreamProperties research, SseProperties sse) {
        this.research = research;
        this.sse = sse;
    }

    @Override
    public Duration pollInterval() {
        return Duration.ofMillis(research.pollMillis());
    }

    @Override
    public int replayWindow() {
        return research.replayWindow();
    }

    @Override
    public Duration heartbeat() {
        return Duration.ofSeconds(Math.max(1, sse.keepAliveSeconds()));
    }
}
