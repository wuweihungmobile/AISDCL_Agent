package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.engine.SddEngineStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;

/**
 * {@code GET /api/v1/engines/sdd} 的 {@code data}（契約 §1.7.1；D-16）。<b>引擎不可用也回 200</b>：回報的是「引擎現在的狀態」，
 * 不是「這次呼叫成不成功」。{@code reason} 是<b>回應欄位</b>，不是 {@code ApiError.reason}（契約 §0.3 第 7 點、附錄 B.4）。
 * 六個欄位都固定出現（沒有值時是 null 或空陣列），前端不必判斷鍵存不存在。
 */
@Schema(name = "SddEngineStatusResponse", description = "GET /api/v1/engines/sdd 的 data（v1.4，D-16）。引擎不可用也回 200：回報的是「引擎現在的狀態」，"
        + "不是「這次呼叫成不成功」。projects 的順序＝Bridge 清單順序（專案名不分大小寫升冪）；開發機上會含 SDD 測試套件留下的 test-<數字> 專案，照列")
public record SddEngineStatusResponse(
        @NotNull @Schema(description = "Bridge 的 GET /sdd/version 與 GET /sdd/fsm 都成功為 true；任一失敗為 false") boolean available,
        @NotNull @Schema(description = "available=true 且沒有問題時為 null。bridge_unreachable／sdd_unavailable／bridge_error 時 available=false；"
                + "fsm_not_found／fsm_state_unreadable 時 available=true、fsm=null（回應欄位的值，不是 ApiError.reason）",
                nullable = true,
                allowableValues = {"bridge_unreachable", "sdd_unavailable", "bridge_error", "fsm_not_found",
                        "fsm_state_unreadable"})
        String reason,
        @NotNull @Schema(description = "GET /sdd/version 失敗時為 null", nullable = true) SddVersionDto version,
        @NotNull @Schema(description = "available=false 時為空陣列（第三個呼叫失敗時保留前兩個呼叫已取得的值）；available=true 而為空表示 SDD 目錄存在但還沒有任何 FSM 狀態檔（正常狀態）")
        List<SddProjectEntryDto> projects,
        @NotNull @Schema(description = "帶了 project 且取得時有值；未帶 project、專案不存在、讀不動或引擎不可用時為 null", nullable = true)
        SddFsmStateDto fsm,
        @NotNull @Schema(description = "console-api 處理這次請求的時間（UTC）") Instant checkedAt) {

    public static SddEngineStatusResponse from(SddEngineStatus status) {
        return new SddEngineStatusResponse(status.available(), status.reason() == null ? null : status.reason().wire(),
                SddVersionDto.from(status.version()), status.projects().stream().map(SddProjectEntryDto::from).toList(),
                SddFsmStateDto.from(status.fsm()), status.checkedAt());
    }
}
