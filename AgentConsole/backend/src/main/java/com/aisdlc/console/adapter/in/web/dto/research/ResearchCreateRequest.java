package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.CreateInput;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Layers;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Scope;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.List;

/**
 * 建立研究專案的請求本文（契約 API-RP-03、§1.2 輸入閘）。所有欄位在綁定階段都可為 null（缺欄位不在這裡失敗）：欄位級的 400（{@code errors[]} 與
 * {@code details.violations[{field,rule,message}]}）由輸入閘一次全列。身分欄位（{@code created_by}）不在請求本文：一律取 JWT subject。
 * 層開關四個布林至少一個為真；{@code industry} 為真須 {@code capabilities.webLayerEnabled=true}。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "ResearchCreateRequest", description = "建立研究專案：slug、title、topic、scope（層開關與檢索邊界）、depthLevel、targetScopeHint")
public record ResearchCreateRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, pattern = "^[a-z0-9][a-z0-9-]{0,29}$", description = "與未封存專案不重複（409 slug_in_use）") String slug,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, maxLength = 200) String title,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, maxLength = 500, description = "研究議題（≤500 字、無 NUL）") String topic,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) ScopeRequest scope,
        @Schema(allowableValues = {"QUICK", "STANDARD", "DEEP"}, defaultValue = "STANDARD") String depthLevel,
        @Schema(allowableValues = {"AISDLC_MODULE", "STANDALONE_PROJECT", "UNDECIDED"}, description = "落點提示；預設 UNDECIDED") String targetScopeHint) {

    /** 研究範圍（檢索邊界）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    @Schema(name = "ResearchCreateScope")
    public record ScopeRequest(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED) LayersRequest layers,
            @Schema(maxLength = 200, description = "技術棧（自由文字，不入任何指令）") String techStack,
            @Schema(description = "範圍內（≤20 項、每項 ≤200 字）") List<String> inScope,
            @Schema(description = "範圍外（≤20 項、每項 ≤200 字）") List<String> outOfScope,
            @Schema(minimum = "1", maximum = "3", description = "文獻新近度（年；整數 1、2 或 3）") Integer recencyYears,
            @Schema(description = "適用性軸（1～6 項、每項 ≤40 字）") List<String> applicabilityAxes) {

        Scope toInput() {
            Layers flags = layers == null ? null : new Layers(layers.academic(), layers.industry(), layers.oss(), layers.community());
            return new Scope(flags, techStack, inScope, outOfScope, recencyYears, applicabilityAxes);
        }
    }

    /** 四個檢索層開關（至少一個為真）。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    @Schema(name = "ResearchCreateLayers")
    public record LayersRequest(
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Boolean academic,
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "為真須 Web 層啟用（capabilities.webLayerEnabled）") Boolean industry,
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Boolean oss,
            @Schema(requiredMode = Schema.RequiredMode.REQUIRED) Boolean community) {
    }

    public CreateInput toInput() {
        return new CreateInput(slug, title, topic, scope == null ? null : scope.toInput(), depthLevel, targetScopeHint);
    }
}
