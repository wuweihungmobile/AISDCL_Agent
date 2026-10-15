package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.imports.ParseOptions;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** 觸發 AI 解析的選項（契約 §1.1.3）。{@code executionPath} 的絕對路徑格式由用例驗（400）；Bridge 的 allowlist 在執行時才驗。 */
@Schema(name = "ParseOptions")
public record ParseOptionsRequest(
        @Min(value = 1, message = "自治等級必須介於 1 到 10") @Max(value = 10, message = "自治等級必須介於 1 到 10")
        @Schema(description = "預設 3；也成為落庫專案的 autonomyLevel", defaultValue = "3") Integer autonomyLevel,
        @NotBlank(message = "執行路徑不能為空") @Size(max = 500, message = "執行路徑長度不可超過 500 字元")
        @Schema(description = "專案執行路徑（絕對路徑格式：POSIX、磁碟機代號或 UNC）") String executionPath,
        @Size(max = 4000, message = "補充說明長度不可超過 4000 字元") String additionalPrompt,
        @Size(max = 500, message = "specDir 長度不可超過 500 字元")
        @Schema(description = "明示的 SDD 規格目錄（絕對路徑）；省略則以 executionPath 探測") String specDir) {

    public ParseOptions toDomain() {
        return new ParseOptions(executionPath, autonomyLevel, additionalPrompt, specDir);
    }

    /** 回應用：匯入記錄詳情的 {@code parseOptions}（契約 §1.1.9，C-10）——最近一次 parse 請求的選項，形狀與請求相同。 */
    public static ParseOptionsRequest from(ParseOptions options) {
        return new ParseOptionsRequest(options.autonomyLevel(), options.executionPath(), options.additionalPrompt(),
                options.specDir());
    }
}
