package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.imports.ParseWarning;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * 非阻擋提示的 API 形狀（契約 §3.3.6）。
 *
 * @param code     {@code evaluator_command_dropped}／{@code regex_dropped}／{@code passcriteria_placeholder}；v1.5 新增
 *                 {@code at_unmapped}、{@code frozen_digest_absent}、{@code state_dir_not_ignored}（皆黃色提示、不阻擋）
 * @param location 位置，例如 {@code goals[0].tasks[1]}；可缺席
 */
@Schema(name = "ParseWarning", description = "非阻擋提示（例如不安全的 evaluatorCommand 被清空）")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ParseWarningDto(
        @NotNull @Schema(description = "例：evaluator_command_dropped、regex_dropped、passcriteria_placeholder；v1.5 新增 at_unmapped"
                + "（規格宣告位置出現但未編成步驟的 AT；location=specDir）、frozen_digest_absent（規格凍結時沒有記錄內容摘要，無法偵測凍結後改檔；"
                + "location=specDir）、state_dir_not_ignored（專案根的 build/reports/fsm/ 未被 git 忽略；Bridge 回報，location=executionPath）"
                + "——皆為黃色提示、不阻擋") String code,
        @NotNull String detail,
        String location) {

    public static ParseWarningDto from(ParseWarning warning) {
        return new ParseWarningDto(warning.code(), warning.detail(), warning.location());
    }
}
