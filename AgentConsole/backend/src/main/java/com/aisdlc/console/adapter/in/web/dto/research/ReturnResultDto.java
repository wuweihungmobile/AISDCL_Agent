package com.aisdlc.console.adapter.in.web.dto.research;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

/**
 * 退回修改結果（契約 API-RP-21）：Bridge 回 {@code {gate_decision_id, fsm_retry_count, escalated}}，轉成 camelCase。退回與自動 FAIL 共用 3 次預算
 * （第 3 次＝ESCALATION，{@code escalated=true}）；FSM 維持 HUMAN_PENDING。
 */
@Schema(name = "ReturnResult", description = "退回修改結果（決定列 id、退回後的 retry 計數、是否升級）")
public record ReturnResultDto(
        @NotNull String gateDecisionId,
        @NotNull @Schema(description = "gate SCG_VALIDATION FAIL 之後的 retry_count") int fsmRetryCount,
        @NotNull @Schema(description = "第 3 次 FAIL 時為 true（FSM 進 ESCALATION）") boolean escalated) {

    public static ReturnResultDto from(Map<String, Object> body) {
        Integer retry = Iso.integer(body.get("fsm_retry_count"));
        return new ReturnResultDto(Iso.text(body.get("gate_decision_id"), ""), retry == null ? 0 : retry, Iso.flag(body.get("escalated")));
    }
}
