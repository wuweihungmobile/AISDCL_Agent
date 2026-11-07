package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchScrUseCase.ScrInput;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.List;

/** 發起規格變更請求的本文（契約 API-RP-15；PRD AC-R2P-19-5）。{@code requestedBy} 不在本文：一律取 JWT subject。 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "ScrOpenRequest", description = "發起 SCR：kind（MINOR｜MAJOR）、sourceKind、reason（1～500 字）、reasonClass（中文五分類或其 DB 碼）、affectedSections")
public record ScrOpenRequest(
        @Schema(allowableValues = {"MINOR", "MAJOR"}) String kind,
        @Schema(allowableValues = {"HUMAN", "REVIEW_FINDING", "SCG4", "HEALING_FAILED"}) String sourceKind,
        @Schema(description = "理由，1～500 字") String reason,
        @Schema(description = "PRD 缺漏證據｜AC 模糊｜需求變更｜技術不可行｜其他（亦接受 EVIDENCE｜AC_VAGUE｜REQ_CHANGE｜INFEASIBLE｜OTHER）；缺＝其他") String reasonClass,
        @Schema(description = "受影響的 PRD 章節（每項 1～200 字，至多 20 項）") List<String> affectedSections,
        @Schema(description = "證據連結（選填；https:// 開頭、至多 500 字）；缺或空字串視同未提供") String evidenceUrl) {

    public ScrInput toInput() {
        return new ScrInput(kind, sourceKind, reason, reasonClass, affectedSections, evidenceUrl);
    }
}
