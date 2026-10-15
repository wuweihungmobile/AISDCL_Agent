package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecuteProjectUseCase.Command;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 啟動執行的請求（契約 §1.2.1）。全部欄位可省略（body 可為 {@code {}}）：等級預設取專案的 {@code autonomyLevel}、預算預設取
 * 系統參數 {@code execution.globalTokenBudget}、範圍預設 {@code ALL}。
 *
 * <p>🔴 刻意<b>不</b>加 Bean Validation：欄位驗證要排在「專案存在」之後（契約 §1.2.1 驗證順序 1→2，QA 依序斷言），
 * 由用例按序驗證並回帶欄位名的 400；min／max 只用於文件。
 */
@Schema(name = "StartExecutionRequest", description = "全部欄位可省略（body 可為 {}）。Architecture §11.2 把三者標必填，"
        + "這裡放寬並給預設（Markdown 契約 §6 D-10）")
public record StartExecutionRequest(
        @Schema(minimum = "1", maximum = "10", description = "預設取專案的 autonomyLevel") Integer autonomyLevel,
        @Schema(minimum = "1", description = "預設取系統參數 execution.globalTokenBudget") Long tokenBudget,
        ExecutionScopeDto scope) {

    public Command toCommand() {
        ExecutionScopeDto s = scope;
        ExecutionScopeDto.Limits limits = s == null ? null : s.limits();
        return new Command(autonomyLevel, tokenBudget, s == null ? null : s.mode(), s == null ? null : s.goalIds(),
                s == null ? null : s.taskIds(), limits == null ? null : limits.taskTokens(),
                limits == null ? null : limits.goalTokens());
    }
}
