package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.imports.ParseWarning;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * 非阻擋提示的 API 形狀（契約 §3.3.6）。
 *
 * @param code     {@code evaluator_command_dropped}／{@code regex_dropped}／{@code passcriteria_placeholder}
 * @param location 位置，例如 {@code goals[0].tasks[1]}；可缺席
 */
@Schema(name = "ParseWarning")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ParseWarningDto(
        @NotNull @Schema(description = "evaluator_command_dropped／regex_dropped／passcriteria_placeholder") String code,
        @NotNull String detail,
        String location) {

    public static ParseWarningDto from(ParseWarning warning) {
        return new ParseWarningDto(warning.code(), warning.detail(), warning.location());
    }
}
