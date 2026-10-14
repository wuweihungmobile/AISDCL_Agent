package com.aisdlc.console.domain.model.project;

/**
 * 建立專案的輸入值（domain 層的值物件；Controller 的 CreateProjectRequest 轉成它）。
 *
 * @param autonomyLevel null 取預設 3
 * @param draft         true＝草案：signedOff=false（讓 AI／E2E 能走 signoff 流程）；預設 false＝手動建立 signedOff=true
 */
public record NewProject(String name, String executionPath, String passCriteria, String description,
                         Integer autonomyLevel, boolean draft) {
}
