package com.aisdlc.console.domain.model.task;

/**
 * 更新任務的輸入值；所有欄位選填，null＝不變更；
 * evaluatorCommand／expectedOutputRegex／passCriteriaSpec 給空白字串＝清除。
 */
public record TaskUpdate(String name, String description, String passCriteria, Integer maxRetries,
                         String evaluatorCommand, String expectedOutputRegex, String passCriteriaSpec,
                         Integer sortOrder, Long estimatedTokens) {
}
