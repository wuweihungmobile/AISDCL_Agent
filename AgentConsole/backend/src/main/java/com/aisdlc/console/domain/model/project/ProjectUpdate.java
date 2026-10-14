package com.aisdlc.console.domain.model.project;

/**
 * 更新專案的輸入值；所有欄位皆選填，null＝不變更（空白字串的 description＝清除）。
 *
 * @param status 手動狀態轉移的目標（本波只開放 DRAFT／READY，其餘由執行引擎事件驅動；限制在 application 層）
 */
public record ProjectUpdate(String name, String executionPath, String passCriteria, String description,
                            Integer autonomyLevel, ProjectStatus status) {
}
