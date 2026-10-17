package com.aisdlc.console.domain.model.project;

/**
 * 建立專案的輸入值（domain 層的值物件；Controller 的 CreateProjectRequest 轉成它）。
 *
 * @param autonomyLevel null 取預設 3
 * @param draft         true＝草案：signedOff=false（讓 AI／E2E 能走 signoff 流程）；預設 false＝手動建立 signedOff=true
 * @param sddProject    SDD 綁定（V12；契約 §0.5 寫入規則②）：<b>只有路徑 A 的 confirm 會帶</b>（{@code POST／PUT /projects} 的請求不收這三欄，
 *                      帶了也不採用）；null＝尚未綁定。{@code sddProject} 是 Bridge 回的標準鍵
 * @param sddSpecDir    規格檔所在目錄（絕對路徑）；null＝尚未用路徑 A 匯入規格
 * @param sddSpecFile   規格檔（絕對路徑）；null＝尚未用路徑 A 匯入規格
 */
public record NewProject(String name, String executionPath, String passCriteria, String description,
                         Integer autonomyLevel, boolean draft, String sddProject, String sddSpecDir,
                         String sddSpecFile) {

    /** 一般建立專案（沒有 SDD 綁定）。 */
    public NewProject(String name, String executionPath, String passCriteria, String description,
                      Integer autonomyLevel, boolean draft) {
        this(name, executionPath, passCriteria, description, autonomyLevel, draft, null, null, null);
    }
}
