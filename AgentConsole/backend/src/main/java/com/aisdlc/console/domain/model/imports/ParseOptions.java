package com.aisdlc.console.domain.model.imports;

import java.util.UUID;

/**
 * 解析選項（契約 §1.1.3）。同時是 {@code import_records.parse_options}（V8，C-10）保存的形狀：進入 PARSING 時把「最近一次
 * parse 請求」的選項存下（不論該次成敗），重開記錄時前端據此還原選項。
 *
 * <p>v1.5（D-115-14、S-04；契約 §3.3.2 v1.5 補充第 2 點）的三個選填欄位只對路徑 A 有意義：{@code specFile}、{@code sddProject}、
 * {@code targetProjectId}。<b>帶 {@code targetProjectId} 的 parse，{@code executionPath}／{@code sddProject}／{@code specDir}／{@code specFile}
 * 一律取自目標專案</b>（目標專案某欄位為 NULL 時以請求值為準），存進記錄的是<b>解析後的有效選項</b>——confirm 據此判斷「綁定在 parse 與 confirm
 * 之間有沒有被改過」（契約 §1.10.8：兩次各驗一次）。
 *
 * @param autonomyLevel   1～10；用例驗證後存入的是已套用預設（3）的值，也成為落庫專案的 autonomyLevel
 * @param specDir         明示的 SDD 規格目錄；null／空白＝以 executionPath 探測
 * @param specFile        要編譯的規格檔：相對 {@code specDir} 的 POSIX 路徑，或 {@code specDir} 之下的絕對路徑（同一目錄有多份 TCS 時用）；
 *                        須與明示的 {@code specDir} 並用
 * @param sddProject      FSM 專案名的<b>有效值</b>（可以是原名；Console 不淨化，由 Bridge 的淨化鏡像處理）
 * @param targetProjectId 併入既有專案（Console 專案是錨）；null＝維持「建立新專案」
 */
public record ParseOptions(String executionPath, Integer autonomyLevel, String additionalPrompt, String specDir,
                           String specFile, String sddProject, UUID targetProjectId) {

    /** v1.4 的四欄（沒有路徑 A 的選檔、專案鍵與併入目標）。 */
    public ParseOptions(String executionPath, Integer autonomyLevel, String additionalPrompt, String specDir) {
        this(executionPath, autonomyLevel, additionalPrompt, specDir, null, null, null);
    }
}
