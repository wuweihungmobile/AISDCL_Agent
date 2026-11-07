package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.adapter.in.web.dto.SddFsmPhaseDto;
import com.aisdlc.console.adapter.in.web.dto.SddHumanPendingDto;
import com.aisdlc.console.adapter.in.web.dto.SddRecoveryDto;
import com.aisdlc.console.application.port.in.ResearchQueryUseCase.FsmView;
import com.aisdlc.console.application.port.out.ResearchBridge.GateCount;
import com.aisdlc.console.domain.model.engine.SddFsmState;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 研究面的外環 FSM 視圖（API-RP-13；D-59(4)）＝既有 {@code SddFsmState}（{@code SddFsmStateDto}）的<b>全部欄位、形狀與值原樣、只增不減</b>
 * （最外層鍵 camelCase，巢狀內容保留 FSM 檔的 snake_case 鍵），再加兩個研究面專屬欄位：{@code retryHistory.gates}（各閘 {@code currentCount}、{@code entries}）與
 * {@code humanReturnCount}（目前 {@code fsm_generation} 內 Gate 0 人工退回的筆數，console-api 讀 DB 計得）。既有的 {@code SddFsmState}、{@code SddRetryHistory}
 * 結構描述與它們的 {@code required} 不動（本類別是獨立的結構描述，不是改動既有的那一個）。
 */
@Schema(name = "ResearchFsmViewDto", description = "研究面 FSM 視圖：SddFsmState 全部欄位原樣，retryHistory 多 gates 三閘分項，另加 humanReturnCount（D-59(4)）")
public record ResearchFsmViewDto(
        @NotNull String project,
        @Schema(description = "current_state（例 INIT、HUMAN_PENDING、ESCALATION）", nullable = true) String currentState,
        @Schema(description = "current_sprint", nullable = true) Integer currentSprint,
        @Schema(description = "session_id", nullable = true) String sessionId,
        @Schema(description = "updated_at（ISO-8601 字串，原樣、不轉型）", nullable = true) String updatedAt,
        @NotNull @Schema(description = "frozen_stages（原樣；缺則空陣列）") List<Map<String, Object>> frozenStages,
        @NotNull @ArraySchema(maxItems = 5, arraySchema = @Schema(description = "decision_trace 的尾 5 筆（舊→新，原樣）"))
        List<Map<String, Object>> decisionTrace,
        @NotNull @Schema(description = "檔名（FSM-STATE-<project>.yaml）") String source,
        @NotNull SddHumanPendingDto humanPending,
        @NotNull RetryHistory retryHistory,
        @Schema(description = "fsm_state.rtm_coverage：有就原樣帶出，沒有就 null", nullable = true) Object rtmCoverage,
        @Schema(description = "由 current_state 純函式投影出的階段資訊；舊版缺鍵為 null", nullable = true) SddFsmPhaseDto phase,
        @ArraySchema(maxItems = 5, arraySchema = @Schema(description = "escalation_history 的尾 5 筆（舊→新，原樣）；缺則空陣列"))
        List<Map<String, Object>> escalationHistory,
        @Schema(description = "escalation_provenance 原樣；缺或不是映射為 null", nullable = true) Map<String, Object> escalationProvenance,
        @Schema(description = "狀態檔名裡淨化後的標準鍵（外環鍵 research-<slug>[-g<N>]）", nullable = true) String fsmProject,
        @Schema(description = "僅 currentState 為 ESCALATION／ESCALATION_FINAL 時由 Bridge 回；其餘為 null", nullable = true) SddRecoveryDto recovery,
        @NotNull @Schema(minimum = "0", description = "目前 fsm_generation 內 research_gate_decisions 中 gate=GATE0、decision=CHANGES 的筆數（舊世代的鍵不計）")
        int humanReturnCount,
        @NotNull @Schema(description = "內環鍵的 frozen_stages 是否含 Stage-2（TCS 已凍結；D-125：只由 frozenStages 導出，不另存第二份狀態）") boolean stage2Frozen) {

    /** 三個重試閘（FSM 的 SCG_VALIDATION、PR_REVIEW、RTM_VERIFY），回應<b>恰含</b>這三閘（Bridge 沒給的閘補 0）。 */
    public static final List<String> GATES = List.of("SCG_VALIDATION", "PR_REVIEW", "RTM_VERIFY");

    /** 既有 {@code retryHistory} 的 {@code count}、{@code last}（原樣）加各閘分項 {@code gates}。 */
    @Schema(name = "ResearchRetryHistory", description = "重試歷史：count、last 同 SddRetryHistory；gates＝各重試閘的 currentCount 與 entries")
    public record RetryHistory(
            @NotNull @Schema(minimum = "0") int count,
            @NotNull @Schema(description = "最近一筆（原樣再加 gate 欄）；沒有為 null", nullable = true) Map<String, Object> last,
            @NotNull @Schema(description = "SCG_VALIDATION｜PR_REVIEW｜RTM_VERIFY 三閘各為 {currentCount, entries}") Map<String, GateRetry> gates) {
    }

    /** 單一閘的重試計數：{@code currentCount}＝該閘 {@code current_count}；{@code entries}＝該閘 {@code history} 筆數。 */
    @Schema(name = "ResearchGateRetry")
    public record GateRetry(@NotNull @Schema(minimum = "0") int currentCount, @NotNull @Schema(minimum = "0") int entries) {
    }

    public static ResearchFsmViewDto from(FsmView view) {
        SddFsmState s = view.fsm().state();
        Map<String, GateRetry> gates = new LinkedHashMap<>();
        for (String gate : GATES) {
            GateCount count = view.fsm().gates().get(gate);
            gates.put(gate, count == null ? new GateRetry(0, 0) : new GateRetry(count.currentCount(), count.entries()));
        }
        RetryHistory retry = new RetryHistory(s.retryHistory().count(), s.retryHistory().last(), gates);
        return new ResearchFsmViewDto(s.project(), s.currentState(), s.currentSprint(), s.sessionId(), s.updatedAt(), s.frozenStages(),
                s.decisionTrace(), s.source(), SddHumanPendingDto.from(s.humanPending()), retry, s.rtmCoverage(), SddFsmPhaseDto.from(s.phase()),
                s.escalationHistory(), s.escalationProvenance(), s.fsmProject(), SddRecoveryDto.from(s.recovery()), view.humanReturnCount(),
                com.aisdlc.console.domain.service.ResearchFlowPolicy.stage2Frozen(s.frozenStages()));
    }
}
