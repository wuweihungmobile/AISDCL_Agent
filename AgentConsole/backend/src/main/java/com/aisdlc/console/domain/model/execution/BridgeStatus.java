package com.aisdlc.console.domain.model.execution;

import java.util.Locale;
import java.util.Optional;

/**
 * Bridge 的八態（{@code engine-bridge/app/models.py} 的 {@code RunStatus}）。{@code PAUSING}／{@code CANCELLING} 是過渡態，
 * 寫進 PG 與 Console 的 {@link RunStatus} 時折回 {@code RUNNING}（契約 §0.6），原值放在 {@code bridgeStatus}。
 */
public enum BridgeStatus {
    INITIALIZING, RUNNING, PAUSING, PAUSED, CANCELLING, COMPLETED, FAILED, CANCELLED;

    /** 折成 Console 的六態：PAUSING／CANCELLING → RUNNING，其餘同名。 */
    public RunStatus fold() {
        return switch (this) {
            case PAUSING, CANCELLING -> RunStatus.RUNNING;
            default -> RunStatus.valueOf(name());
        };
    }

    public boolean terminal() {
        return this == COMPLETED || this == FAILED || this == CANCELLED;
    }

    /** 解析 Bridge 回的狀態字串；無法辨識回 empty（呼叫端自行決定怎麼處理未知值）。 */
    public static Optional<BridgeStatus> parse(String raw) {
        if (raw == null) {
            return Optional.empty();
        }
        try {
            return Optional.of(valueOf(raw.strip().toUpperCase(Locale.ROOT)));
        } catch (IllegalArgumentException e) {
            return Optional.empty();
        }
    }
}
