package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.engine.SddFsmState;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;
import java.util.Map;

/**
 * 單一 FSM 專案的狀態（Bridge {@code GET /sdd/fsm/{project}} 的投影；契約 §1.7.1；D-16）。<b>最外層鍵轉 camelCase，巢狀內容原樣</b>
 * （{@code frozenStages[]}、{@code decisionTrace[]}、{@code humanPending.items[]}、{@code retryHistory.last}、{@code rtmCoverage}
 * 保留 FSM 檔的 snake_case 鍵），使「FSM 檔 ↔ API ↔ 畫面」可逐值比對（NFR-OBS-01）。唯讀：Console 不寫 FSM-STATE（ADR-001 D22）。
 */
@Schema(name = "SddFsmState", description = "單一 FSM 專案的狀態（Bridge GET /sdd/fsm/{project} 的投影；v1.4，D-16）。最外層鍵轉 camelCase，"
        + "巢狀內容原樣（frozenStages[]、decisionTrace[]、humanPending.items[]、retryHistory.last、rtmCoverage 保留 FSM 檔的 snake_case 鍵），"
        + "使「FSM 檔 ↔ API ↔ 畫面」可逐值比對（NFR-OBS-01）。唯讀：Console 不寫 FSM-STATE（ADR-001 D22）")
public record SddFsmStateDto(
        @NotNull String project,
        @Schema(description = "current_state（例 INIT、HUMAN_PENDING、ESCALATION）", nullable = true) String currentState,
        @Schema(description = "current_sprint", nullable = true) Integer currentSprint,
        @Schema(description = "session_id", nullable = true) String sessionId,
        @Schema(description = "updated_at（ISO-8601 字串，原樣、不轉型）", nullable = true) String updatedAt,
        @NotNull @Schema(description = "frozen_stages（原樣；缺則空陣列）") List<Map<String, Object>> frozenStages,
        @NotNull @ArraySchema(maxItems = 5, arraySchema = @Schema(description = "decision_trace 的尾 5 筆（舊→新，原樣；"
                + "每筆 {ts, from, to, reason, spec_refs, agents_consulted, trigger}）"))
        List<Map<String, Object>> decisionTrace,
        @NotNull @Schema(description = "檔名（FSM-STATE-<project>.yaml）") String source,
        @NotNull SddHumanPendingDto humanPending,
        @NotNull SddRetryHistoryDto retryHistory,
        @Schema(description = "fsm_state.rtm_coverage：有就原樣帶出，沒有就 null。現行 FSM-STATE schema 沒有任何 RTM 覆蓋數值的鍵，"
                + "所以現況恆為 null（保留位；Console 卡片不顯示它）", nullable = true) Object rtmCoverage) {

    /** null（沒帶 project、專案不存在、讀不動或引擎不可用）→ null。 */
    public static SddFsmStateDto from(SddFsmState state) {
        if (state == null) {
            return null;
        }
        return new SddFsmStateDto(state.project(), state.currentState(), state.currentSprint(), state.sessionId(),
                state.updatedAt(), state.frozenStages(), state.decisionTrace(), state.source(),
                SddHumanPendingDto.from(state.humanPending()), SddRetryHistoryDto.from(state.retryHistory()),
                state.rtmCoverage());
    }
}
