package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.task.TaskUpdate;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;

import java.util.Map;

/**
 * 更新任務請求；所有欄位選填，未提供（null）＝不變更。evaluatorCommand／expectedOutputRegex 給空白字串＝清除；
 * passCriteriaSpec 給空物件 {} ＝清除。
 */
public record UpdateTaskRequest(
        @Size(max = 200, message = "名稱長度不可超過 200 字元") String name,
        @Schema(description = "給空白字串＝清除說明") String description,
        String passCriteria,
        @Min(value = 0, message = "最大重試次數不可為負數") @Max(value = 20, message = "最大重試次數不可超過 20")
        @Schema(description = "上限 20（Bridge PlaybookIn 的上限，契約 §0.8／AR-14）") Integer maxRetries,
        @Size(max = 1000, message = "驗證命令長度不可超過 1000 字元")
        @Schema(description = "NFR-SEC-03；給空白字串＝清除") String evaluatorCommand,
        @Size(max = 1000, message = "期望輸出正規表示式長度不可超過 1000 字元")
        @Schema(description = "須可 Pattern.compile；給空白字串＝清除") String expectedOutputRegex,
        @Schema(description = "結構化通過標準（JSON 物件）；給空物件 {} ＝清除") Map<String, Object> passCriteriaSpec,
        @Min(value = 0, message = "排序順序不可為負數") Integer sortOrder,
        @Min(value = 0, message = "預估 Token 不可為負數") Long estimatedTokens) {

    public TaskUpdate toDomain() {
        PassCriteriaSpecRules.validate(passCriteriaSpec);
        String specJson = passCriteriaSpec == null ? null
                : passCriteriaSpec.isEmpty() ? "" : JsonSupport.toJson(passCriteriaSpec);
        return new TaskUpdate(name, description, passCriteria, maxRetries, evaluatorCommand, expectedOutputRegex,
                specJson, sortOrder, estimatedTokens);
    }
}
