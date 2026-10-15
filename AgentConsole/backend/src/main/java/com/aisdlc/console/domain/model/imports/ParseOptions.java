package com.aisdlc.console.domain.model.imports;

/**
 * 解析選項（契約 §1.1.3）。同時是 {@code import_records.parse_options}（V8，C-10）保存的形狀：進入 PARSING 時把「最近一次
 * parse 請求」的選項原樣存下（不論該次成敗），重開記錄時前端據此還原選項。
 *
 * @param autonomyLevel 1～10；用例驗證後存入的是已套用預設（3）的值，也成為落庫專案的 autonomyLevel
 * @param specDir       明示的 SDD 規格目錄；null／空白＝以 executionPath 探測
 */
public record ParseOptions(String executionPath, Integer autonomyLevel, String additionalPrompt, String specDir) {
}
