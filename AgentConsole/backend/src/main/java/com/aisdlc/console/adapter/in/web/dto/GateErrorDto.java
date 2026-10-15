package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.imports.GateError;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * 單一有界閘違規的 API 形狀（契約 §3.3.5；{@code lastParseErrors}、{@code ParseResultResponse.errors} 共用）。
 * domain 的 {@link GateError} 不帶任何文件化註記（domain 不依賴 API 層），所以 OpenAPI 用的必填與列舉標記放在這裡。
 *
 * @param gate     閘名稱（逐字常數）
 * @param detail   給人看的完整原因（不截斷）
 * @param location 違規位置；沒有位置的閘（{@code brain_*}）缺席
 */
@Schema(name = "GateError")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record GateErrorDto(
        @NotNull @Schema(allowableValues = {"empty_prompt", "max_steps", "cycle", "prompt_too_long", "brain_unsupported",
                "brain_failed"}) String gate,
        @NotNull String detail,
        @Schema(description = "例：goals[0].tasks[3].description；沒有位置的閘（brain_*）缺席") String location) {

    public static GateErrorDto from(GateError error) {
        return new GateErrorDto(error.gate(), error.detail(), error.location());
    }
}
