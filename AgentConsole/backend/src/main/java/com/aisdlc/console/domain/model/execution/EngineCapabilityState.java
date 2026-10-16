package com.aisdlc.console.domain.model.execution;

import java.util.Optional;

/**
 * 引擎能力的狀態（契約 §3.4.2；D-11）。它描述的是「這個批次 spawn 時 Console <b>實際送進引擎</b>的與引擎因此會做的」，
 * 不是使用者設了什麼。
 *
 * <ul>
 *   <li>{@link #ENABLED}：已送進引擎且引擎會做；</li>
 *   <li>{@link #OFF}：沒有人要求（或有金鑰且明確送了 {@code enable_kernel_brain=false}）；</li>
 *   <li>{@link #UNAVAILABLE_NO_API_KEY}：有人要求（旗標或自治等級），但 Console 沒有金鑰可送——Console 不送
 *       {@code minimax.*}（送了引擎會啟動失敗），批次照常執行，只是沒有 Brain。</li>
 * </ul>
 * 宣告順序與契約的列舉順序（{@code ENABLED}、{@code OFF}、{@code UNAVAILABLE_NO_API_KEY}）一致。
 */
public enum EngineCapabilityState {
    ENABLED, OFF, UNAVAILABLE_NO_API_KEY;

    /**
     * 讀回資料庫時的解析：不認得的值（含 null、非字串）回 empty——前向相容，呼叫端把它當成「該鍵缺席」，不丟例外
     * （契約 §0.5 V10 寫入規則③）。
     */
    public static Optional<EngineCapabilityState> parse(Object raw) {
        if (raw instanceof String text) {
            for (EngineCapabilityState state : values()) {
                if (state.name().equals(text)) {
                    return Optional.of(state);
                }
            }
        }
        return Optional.empty();
    }
}
