package com.aisdlc.console.adapter.in.web.dto.research;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.List;

/** 觸發拆解的選填本文（D-94）：{@code scope.usIds}＝只拆指定的 US；省略＝全部。{@code requestedBy} 不在本文：一律取 JWT subject。 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "DecompositionTriggerRequest", description = "觸發拆解：選填 scope.usIds（只拆指定的 US；省略＝全部）")
public record DecompositionTriggerRequest(@Schema(description = "範圍（選填）") Scope scope) {

    /** 拆解範圍。 */
    @Schema(name = "DecompositionScope")
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Scope(@Schema(description = "只拆這些 US（例 US-003）") List<String> usIds) {
    }

    public List<String> usIds() {
        return scope == null ? null : scope.usIds();
    }
}
