package com.aisdlc.console.adapter.in.web.dto.research;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;
import java.util.Map;

/**
 * 研究能力探針（契約 §1.3 {@code CapabilitiesDto}；API-RP-01）：Bridge {@code GET /research/capabilities} 的 camelCase 投影，console-api 快取 30 秒。
 * 無 {@code BRIDGE_DB_DSN} 時仍 200、{@code db:false}（§0.2 第 4 列 503 規則的唯一例外）；{@code mode=mock-only} 時 UI 停用「啟動深研」（伺服器端不拒絕）。
 * Bridge 本文缺的鍵一律給預設值（{@code mode}＝local、布林＝false、清單＝空、路徑＝空字串或 null），不丟例外。
 */
@Schema(name = "CapabilitiesDto", description = "研究面能力探針（Bridge GET /research/capabilities 的 camelCase 投影；快取 30 秒）")
public record CapabilitiesDto(
        @NotNull @Schema(description = "local｜mock-only") String mode,
        @NotNull boolean db,
        @NotNull ToolDto claudeCli,
        @NotNull GhCliDto ghCli,
        @NotNull ToolDto git,
        @NotNull @Schema(description = "研究工作區根（Bridge 的 research_root；舊版 Bridge 以 root 回）") String researchRoot,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED, description = "分流用的腳手架根；未設為 null") String scaffoldRoot,
        @NotNull List<String> scaffoldTemplates,
        @NotNull boolean repoWritable,
        @NotNull @Schema(description = "Web 層（產業層檢索）是否啟用；false 時建立請求不可勾 industry") boolean webLayerEnabled,
        @NotNull List<String> fetchHosts) {

    /** 外部工具的狀態（claude CLI、git）。 */
    @Schema(name = "CapabilityToolDto")
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record ToolDto(@NotNull boolean ok, String version) {
    }

    /** gh CLI 的狀態。 */
    @Schema(name = "CapabilityGhCliDto")
    public record GhCliDto(@NotNull boolean ok, @NotNull boolean authenticated) {
    }

    public static CapabilitiesDto from(Map<String, Object> body) {
        Map<String, Object> claude = Iso.map(body.get("claude_cli"));
        Map<String, Object> gh = Iso.map(body.get("gh_cli"));
        Map<String, Object> git = Iso.map(body.get("git"));
        String root = Iso.text(body.get("research_root"), Iso.text(body.get("root"), ""));
        return new CapabilitiesDto(Iso.text(body.get("mode"), "local"), Iso.flag(body.get("db")),
                new ToolDto(Iso.flag(claude.get("ok")), Iso.text(claude.get("version"))),
                new GhCliDto(Iso.flag(gh.get("ok")), Iso.flag(gh.get("authenticated"))),
                new ToolDto(Iso.flag(git.get("ok")), Iso.text(git.get("version"))), root, Iso.text(body.get("scaffold_root")),
                Iso.strings(body.get("scaffold_templates")), Iso.flag(body.get("repo_writable")), Iso.flag(body.get("web_layer_enabled")),
                Iso.strings(body.get("fetch_hosts")));
    }
}
