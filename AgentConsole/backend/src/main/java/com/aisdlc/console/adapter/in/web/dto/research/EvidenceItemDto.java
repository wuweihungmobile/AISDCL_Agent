package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchViews.EvidenceItem;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;
import java.util.Map;

/** 證據項（契約 §1.3 {@code EvidenceItemDto}；E-NNN）：F1～F7 七欄加 Bridge 入庫時計算的 {@code unanchored}（PRD 不得引用）。 */
@Schema(name = "EvidenceItemDto", description = "證據項（E-NNN）")
public record EvidenceItemDto(
        @NotNull String evidenceNo,
        @NotNull String sourceNo,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "候選技術名；供技術優缺點矩陣分組") String candidate,
        @NotNull String claim,
        @NotNull String f1Mechanism,
        @NotNull String f2Evidence,
        @NotNull String f3Critique,
        @NotNull @Schema(description = "風險標籤") List<String> f4RiskTags,
        @NotNull @Schema(description = "適用性：軸 id → {grade: A｜M｜N, reason}") Map<String, Object> f5Applicability,
        @NotNull String f6Limits,
        @NotNull @Schema(description = "V1｜V2｜V3") String f7Verification,
        @NotNull @Schema(description = "STRONG｜MEDIUM｜WEAK｜CANDIDATE") String strength,
        @NotNull @Schema(description = "Bridge 入庫時計算；PRD 不得引用") boolean unanchored,
        @NotNull int matrixVersion,
        @NotNull int scopeRev) {

    public static EvidenceItemDto from(EvidenceItem item) {
        return new EvidenceItemDto(item.evidenceNo(), item.sourceNo(), item.candidate(), item.claim(), item.f1Mechanism(), item.f2Evidence(),
                item.f3Critique(), item.f4RiskTags(), item.f5Applicability(), item.f6Limits(), item.f7Verification(), item.strength(),
                item.unanchored(), item.matrixVersion(), item.scopeRev());
    }
}
