package com.aisdlc.console.application.service;

import org.springframework.stereotype.Component;

import java.time.Clock;

/**
 * 告警閾值（契約 §3.7：「閾值每次評估時讀系統參數，快取不超過 5 秒」）。事件處理很密集，每則事件都查六個設定太浪費，
 * 所以快取 5 秒；測試改了設定後呼叫 {@link #invalidate()} 立即生效。
 */
@Component
public class AlertThresholds {

    private static final long TTL_MILLIS = 5_000;

    /** 一次評估要用到的全部閾值。 */
    public record Values(double tokenWarning, int consecutiveFailures, int agentTimeoutSec, double durationMultiplier,
                         int taskTimeoutSec) {
    }

    private final SettingsReader settings;
    private final Clock clock;
    private volatile Values cached;
    private volatile long loadedAt;

    public AlertThresholds(SettingsReader settings, Clock clock) {
        this.settings = settings;
        this.clock = clock;
    }

    public Values current() {
        Values values = cached;
        long now = clock.millis();
        if (values == null || now - loadedAt > TTL_MILLIS) {
            values = new Values(settings.doubleValue("execution", "tokenBudgetWarningThreshold"),
                    settings.intValue("monitor", "alertConsecutiveFailures"),
                    settings.intValue("monitor", "alertAgentTimeoutSec"),
                    settings.doubleValue("monitor", "alertTaskDurationMultiplier"),
                    settings.intValue("agent", "taskTimeout"));
            cached = values;
            loadedAt = now;
        }
        return values;
    }

    public void invalidate() {
        cached = null;
    }
}
