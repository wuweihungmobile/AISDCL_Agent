package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchViews.PrdVersion;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;

/**
 * PRD 版本（契約 §1.3 {@code PrdVersionDto}）。{@code content} <b>只有單筆端點</b>（{@code GET …/prd/versions/{n}}）回；清單與存檔回應不含（省略該鍵）。
 * {@code semver} 含 v 前綴（例 {@code v0.3.0-draft}、{@code v1.0.0}）。
 */
@Schema(name = "PrdVersionDto", description = "PRD 版本（content 只有單筆端點回）")
public record PrdVersionDto(
        @NotNull int versionNo,
        @NotNull String semver,
        @NotNull @Schema(description = "DRAFT｜BASELINE") String kind,
        @NotNull @Schema(description = "AGENT｜HUMAN") String authorKind,
        @NotNull @Schema(description = "agent id 或 JWT subject") String author,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) Integer parentVersionNo,
        @NotNull String sha256,
        @NotNull int bytes,
        @NotNull @Schema(description = "PRD 內 [E-NNN] 引用") List<String> evidenceRefs,
        @NotNull String changeSummary,
        @NotNull String createdAt,
        @JsonInclude(JsonInclude.Include.NON_NULL) @Schema(description = "PRD 全文（僅單筆端點；其餘端點省略這個鍵）") String content) {

    /** 單筆（含全文）。 */
    public static PrdVersionDto from(PrdVersion version) {
        return of(version, version.content());
    }

    /** 清單與存檔回應（不含全文）。 */
    public static PrdVersionDto withoutContent(PrdVersion version) {
        return of(version, null);
    }

    private static PrdVersionDto of(PrdVersion version, String content) {
        return new PrdVersionDto(version.versionNo(), version.semver(), version.kind(), version.authorKind(), version.author(),
                version.parentVersionNo(), version.sha256(), version.bytes(), version.evidenceRefs(), version.changeSummary(),
                Iso.of(version.createdAt()), content);
    }
}
