package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchRouteViews.Scr;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;

/** 一筆規格變更請求（契約 §1.3 {@code Scr}；加 {@code reasonClass}、{@code implFsmActions}）。 */
@Schema(name = "ScrDto", description = "規格變更請求：型別、來源、理由與分類、受影響章節、狀態、PRD 版本、接續研究專案、實際呼叫過的 FSM 動詞序列")
public record ScrDto(
        @NotNull String id,
        @NotNull int scrNo,
        @NotNull @Schema(allowableValues = {"MINOR", "MAJOR"}) String kind,
        @NotNull String sourceKind,
        @NotNull String reason,
        @NotNull @Schema(description = "EVIDENCE｜AC_VAGUE｜REQ_CHANGE｜INFEASIBLE｜OTHER") String reasonClass,
        @NotNull List<String> affectedSections,
        @NotNull @Schema(description = "OPEN｜APPROVED｜REJECTED｜APPLIED｜SUPERSEDED") String status,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) Integer prdFromVersionNo,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) Integer prdToVersionNo,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "MAJOR：新研究專案 id") String successorResearchId,
        @NotNull @Schema(description = "實際呼叫過的 FSM 動詞序列（verb、args_redacted、result、at；稽核用，原樣）") List<Object> implFsmActions,
        @NotNull String requestedBy,
        @NotNull String requestedAt,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String decidedBy,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String decidedAt) {

    public static ScrDto from(Scr s) {
        return new ScrDto(s.id().toString(), s.scrNo(), s.kind(), s.sourceKind(), s.reason(), s.reasonClass(), s.affectedSections(), s.status(),
                s.prdFromVersionNo(), s.prdToVersionNo(), s.successorResearchId() == null ? null : s.successorResearchId().toString(), s.implFsmActions(),
                s.requestedBy(), Iso.of(s.requestedAt()), s.decidedBy(), Iso.of(s.decidedAt()));
    }
}
