package com.aisdlc.console.domain.model.si;

import java.util.Optional;

/**
 * Console 對 SelfImproving 帳本的三種寫入（稽核 JSON 外層的 {@code kind}；TCS-SelfImprovingDecide-P2b W7、W13）：
 * 決定（{@code decide}）、新增觀察列（{@code obs-add}）、關閉觀察列（{@code obs-close}）。{@link #wire()} 是線上與資料庫共用的字面值。
 */
public enum SiWriteKind {

    DECIDE("decide"),
    OBS_ADD("obs-add"),
    OBS_CLOSE("obs-close");

    private final String wire;

    SiWriteKind(String wire) {
        this.wire = wire;
    }

    /** 稽核 JSON 的 {@code kind}、{@code si_console_writes.kind} 與回應的 {@code kind}：恆為這個字面值。 */
    public String wire() {
        return wire;
    }

    public static Optional<SiWriteKind> fromWire(String value) {
        for (SiWriteKind kind : values()) {
            if (kind.wire.equals(value)) {
                return Optional.of(kind);
            }
        }
        return Optional.empty();
    }
}
