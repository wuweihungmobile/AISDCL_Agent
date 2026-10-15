package com.aisdlc.console.domain.model.imports;

/** 匯入來源類型（契約 §1.1）：{@code PDF}／{@code DOCX} 只能由 upload 產生；貼上文字為 PLAIN_TEXT 或 MARKDOWN。 */
public enum ImportSourceType {
    MARKDOWN,
    PDF,
    DOCX,
    PLAIN_TEXT
}
