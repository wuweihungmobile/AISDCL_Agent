package com.aisdlc.console.domain.model.task;

/**
 * 建立任務的輸入值。
 *
 * @param passCriteriaSpec 結構化通過標準（JSON 文字；domain 不解析，只原樣保存）
 * @param maxRetries       null 取預設 3
 * @param draft            true＝草案：signedOff=false；預設 false＝手動建立 signedOff=true
 */
public record NewTask(String name, String description, String passCriteria, String evaluatorCommand,
                      String expectedOutputRegex, String passCriteriaSpec, Long estimatedTokens,
                      Integer maxRetries, boolean draft) {
}
