package com.aisdlc.console.adapter.in.web.dto.research;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * 分流預演結果（契約 §1.3；API-RP-14）：Bridge 的 snake_case 本文轉 camelCase。預演<b>零副作用</b>（D-108：所有 {@code research_*} 表與 {@code projects} 前後列數相同）。
 * 動作清單與確認執行共用同一份規範形狀；{@code executionPath}、{@code implStateDir}、{@code implFsmProject} 由 Bridge 導出（console-api 先建 {@code projects} 列時取用）。
 */
@Schema(name = "RoutePreviewResult", description = "分流預演結果：動作清單（動作、目標、是否觸及外部系統）、導出的執行路徑與內環鍵、警示")
public record RoutePreviewResult(
        @NotNull String researchId,
        @NotNull String track,
        @NotNull @Schema(description = "PRD 摘要：versionNo、semver、sha256、targetScope、scopeDiffers") Map<String, Object> prd,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String implFsmProject,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String implStateDir,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "Bridge 導出的內環專案根（絕對路徑）") String executionPath,
        @NotNull List<ActionDto> actions,
        @NotNull @Schema(description = "僅軌道 B：初始 commit 預期入版控的檔案集合；軌道 A 為空陣列") List<String> expectedTrackedFiles,
        @NotNull List<Map<String, Object>> warnings,
        @NotNull boolean scopeDiffers) {

    /** 一個預演動作。 */
    @Schema(name = "RouteActionDto")
    public record ActionDto(@NotNull int seq, @NotNull String action, @NotNull String step, @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String target,
                            @NotNull boolean touchesExternal, @NotNull String detail) {
    }

    public static RoutePreviewResult from(Map<String, Object> body) {
        List<ActionDto> actions = new ArrayList<>();
        for (Object item : Iso.list(body.get("actions"))) {
            Map<String, Object> a = Iso.map(item);
            Integer seq = Iso.integer(a.get("seq"));
            actions.add(new ActionDto(seq == null ? 0 : seq, Iso.text(a.get("action"), ""), Iso.text(a.get("step"), ""), Iso.text(a.get("target")),
                    Iso.flag(a.get("touches_external")), Iso.text(a.get("detail"), "")));
        }
        List<Map<String, Object>> warnings = new ArrayList<>();
        for (Object item : Iso.list(body.get("warnings"))) {
            warnings.add(Iso.camelKeys(Iso.map(item)));
        }
        Map<String, Object> prd = Iso.camelKeys(Iso.map(body.get("prd")));
        return new RoutePreviewResult(Iso.text(body.get("research_id"), ""), Iso.text(body.get("track"), ""), prd, Iso.text(body.get("impl_fsm_project")),
                Iso.text(body.get("impl_state_dir")), Iso.text(body.get("execution_path")), List.copyOf(actions), Iso.strings(body.get("expected_tracked_files")),
                List.copyOf(warnings), Iso.flag(body.get("scope_differs")) || Iso.flag(prd.get("scopeDiffers")));
    }
}
