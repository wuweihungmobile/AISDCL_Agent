package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.task.NewTask;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.util.Map;

/** 建立任務請求（PRD §5.1.3）；目標 id 取自路徑。 */
public record CreateTaskRequest(
        @NotBlank(message = "名稱不能為空") @Size(max = 200, message = "名稱長度不可超過 200 字元") String name,
        String description,
        @NotBlank(message = "通過標準不能為空") String passCriteria,
        @Size(max = 1000, message = "驗證命令長度不可超過 1000 字元")
        @Schema(description = "NFR-SEC-03：不得含 ! ` > < ~ $ & ; 等字元或換行，命中回 400 並列出違規字元") String evaluatorCommand,
        @Size(max = 1000, message = "期望輸出正規表示式長度不可超過 1000 字元")
        @Schema(description = "須可被 Java Pattern.compile，否則回 400") String expectedOutputRegex,
        @Schema(description = "結構化通過標準（JSON 物件）") Map<String, Object> passCriteriaSpec,
        @Min(value = 0, message = "預估 Token 不可為負數") Long estimatedTokens,
        @Min(value = 0, message = "最大重試次數不可為負數") @Max(value = 20, message = "最大重試次數不可超過 20")
        @Schema(description = "預設 3；上限 20（Bridge PlaybookIn 的上限，契約 §0.8／AR-14）") Integer maxRetries,
        @Schema(description = "true＝草案（signedOff=false）；預設 false＝手動建立（signedOff=true）") Boolean draft) {

    public NewTask toDomain() {
        PassCriteriaSpecRules.validate(passCriteriaSpec);
        return new NewTask(name, description, passCriteria, evaluatorCommand, expectedOutputRegex,
                JsonSupport.toJson(passCriteriaSpec), estimatedTokens, maxRetries, Boolean.TRUE.equals(draft));
    }
}
