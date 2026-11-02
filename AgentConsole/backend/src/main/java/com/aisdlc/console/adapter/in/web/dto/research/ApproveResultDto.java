package com.aisdlc.console.adapter.in.web.dto.research;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Gate 0 核准結果（契約 §1.3 {@code ApproveResult}；API-RP-12）：Bridge 回 {@code {gate_decision_id, stage, spec_doc_digests, fsm_state}}，轉成 camelCase。
 * {@code specDocDigests} 的鍵是相對 POSIX 路徑（值原樣，不轉鍵）。
 */
@Schema(name = "ApproveResult", description = "Gate 0 核准結果（決定列 id、凍結階段、凍結檔摘要、核准後 FSM 現態）")
public record ApproveResultDto(
        @NotNull String gateDecisionId,
        @NotNull @Schema(description = "凍結的階段名（Gate-0；SCR 進行中時為 Gate-0-SCR<n>）") String stage,
        @NotNull @Schema(description = "相對 POSIX 路徑 → 凍結當下的摘要（與 FSM show 的 frozen_stages[-1].spec_doc_digests 逐位元相同）") Map<String, String> specDocDigests,
        @NotNull String fsmState) {

    public static ApproveResultDto from(Map<String, Object> body) {
        Map<String, String> digests = new LinkedHashMap<>();
        Iso.map(body.get("spec_doc_digests")).forEach((path, digest) -> digests.put(path, Iso.text(digest, "")));
        return new ApproveResultDto(Iso.text(body.get("gate_decision_id"), ""), Iso.text(body.get("stage"), ""), digests,
                Iso.text(body.get("fsm_state"), ""));
    }
}
