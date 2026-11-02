package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchViews.Defect;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;

/**
 * 審查缺陷（契約 §1.3 {@code DefectDto}）。{@code resolvedIn} 是 {@code fixedInVersionNo} 所指版本的 semver（審查卡的 {@code resolved_in}）；
 * {@code waiver} 只有 status 為 WAIVED 時有值（{@code at} 對映 DB 的 {@code resolved_at}；三者在 DB 皆為必填）。
 */
@Schema(name = "DefectDto", description = "審查缺陷（D-<輪>-<序>）")
public record DefectDto(
        @NotNull String defectNo,
        @NotNull String dimension,
        @NotNull @Schema(description = "P1｜P2｜P3｜P4") String severity,
        @NotNull String code,
        @NotNull String prdAnchor,
        @NotNull String description,
        @NotNull String suggestion,
        @NotNull List<String> evidenceRefs,
        @NotNull @Schema(description = "OPEN｜FIXED｜WAIVED｜SUPERSEDED｜REGRESSED") String status,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) Integer fixedInVersionNo,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "該版本的 semver") String resolvedIn,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) WaiverDto waiver) {

    /** 豁免紀錄。 */
    @Schema(name = "DefectWaiverDto")
    public record WaiverDto(@NotNull String by, @NotNull String reason, @NotNull String at) {
    }

    public static DefectDto from(Defect defect) {
        WaiverDto waiver = "WAIVED".equals(defect.status()) && defect.waivedBy() != null
                ? new WaiverDto(defect.waivedBy(), defect.waiverReason() == null ? "" : defect.waiverReason(), Iso.of(defect.resolvedAt()))
                : null;
        return new DefectDto(defect.defectNo(), defect.dimension(), defect.severity(), defect.code(), defect.prdAnchor(), defect.description(),
                defect.suggestion(), defect.evidenceRefs(), defect.status(), defect.fixedInVersionNo(), defect.resolvedIn(), waiver);
    }
}
