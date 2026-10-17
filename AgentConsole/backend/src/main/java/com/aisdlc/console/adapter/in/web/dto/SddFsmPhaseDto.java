package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.engine.SddFsmState;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * FSM 階段資訊（v1.5，G-13；契約 §3.1.5）。{@code name} 是開放字串：Console 不維護字典，日後新增的值前端原樣顯示。
 */
@Schema(name = "SddFsmPhase", description = "FSM 階段資訊（v1.5，G-13）。name 主路徑值為 INTAKE、SPECIFICATION、HUMAN_GATE、FROZEN、IMPLEMENTATION、"
        + "REVIEW、VERIFICATION、RELEASE（order 1～8）；非主路徑為 BLOCKED／TRANSIENT／OBSERVATION／UNKNOWN（order 一律 0）。"
        + "前端的字典沒有的新 name 值要原樣顯示")
public record SddFsmPhaseDto(
        @NotNull String name,
        @NotNull @Schema(minimum = "0", maximum = "8") int order,
        @NotNull @Schema(description = "阻塞態（ESCALATION、ESCALATION_FINAL、TERMINATED、TOKEN_BUDGET_CRITICAL）為 true") boolean blocking,
        @NotNull @Schema(description = "觀測態（SDD OBSERVATION_STATES）為 true") boolean observation) {

    /** null（舊版 Bridge 缺鍵、或尚未接線）→ null。 */
    public static SddFsmPhaseDto from(SddFsmState.Phase phase) {
        return phase == null ? null : new SddFsmPhaseDto(phase.name(), phase.order(), phase.blocking(), phase.observation());
    }
}
