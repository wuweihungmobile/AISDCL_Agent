package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchDecompositionUseCase.View;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Decomposition;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 拆解（API-RP-16；IFACE §3.1；D-120）：有效拆解（已簽核且摘要相符的最新一筆，否則最新一筆）。{@code GET …/decomposition} 尚無拆解回 200 的 {@code null}。
 * 覆蓋對映取 Bridge 寫入的內容（D-121：console-api 不重算，只判定簽核能不能過）；{@code stale}＝狀態 STALE 或其 PRD 摘要與現行凍結摘要不符。
 */
@Schema(name = "DecompositionDto", description = "拆解：狀態、任務數、覆蓋（total、covered、uncovered）、PRD 摘要、stale、TCS 發佈資訊、目標任務樹與豁免")
public record DecompositionDto(
        @NotNull String id,
        @NotNull @Schema(description = "DRAFTED｜SCG_PASSED｜FROZEN｜SIGNED_OFF｜REJECTED｜STALE（IMPORTED 於 P1 不使用，D-113）") String status,
        @NotNull int tasksCount,
        @NotNull CoverageDto coverage,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "拆解綁定的凍結 PRD sha256") String prdSha256,
        @NotNull boolean stale,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) TcsDto tcs,
        @NotNull @Schema(description = "目標與任務樹（goal_id、name、pass_criteria、depends_on、tasks[{task_id、name、prompt、covers_us、covers_ac…}]；鍵 camelCase）") List<Map<String, Object>> goals,
        @NotNull List<WaiverDto> waivers) {

    /** 覆蓋對映。 */
    @Schema(name = "DecompositionCoverage")
    public record CoverageDto(@NotNull int total, @NotNull int covered, @NotNull List<String> uncovered) {
    }

    /** TCS 草擬後的發佈資訊（沒有則整個 {@code tcs} 為 null）。 */
    @Schema(name = "DecompositionTcs")
    public record TcsDto(@Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String relPath,
                         @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String sha256) {
    }

    /** 人工豁免。 */
    @Schema(name = "DecompositionWaiver")
    public record WaiverDto(@NotNull String ac, @NotNull String reason) {
    }

    public static DecompositionDto from(View view) {
        Decomposition d = view.decomposition();
        List<Map<String, Object>> goals = new ArrayList<>();
        view.goals().forEach(goal -> goals.add(Iso.camelKeys(goal)));
        TcsDto tcs = d.tcsRelPath() == null && d.tcsSha256() == null ? null : new TcsDto(d.tcsRelPath(), d.tcsSha256());
        return new DecompositionDto(d.id().toString(), d.status(), d.tasksCount(),
                new CoverageDto(view.coverage().total(), view.coverage().covered(), view.coverage().uncovered()), d.prdSha256(), view.stale(), tcs,
                List.copyOf(goals), view.waivers().stream().map(w -> new WaiverDto(w.ac(), w.reason())).toList());
    }
}
