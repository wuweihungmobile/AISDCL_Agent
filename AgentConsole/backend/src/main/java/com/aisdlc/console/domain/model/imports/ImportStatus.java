package com.aisdlc.console.domain.model.imports;

/**
 * 匯入記錄狀態機（API-IMP-10；契約 §1.1）：
 * UPLOADED→PARSING→PARSED→REVIEWING→IMPORTED／REJECTED；解析失敗時 PARSING 退回 UPLOADED。
 */
public enum ImportStatus {
    UPLOADED,
    PARSING,
    PARSED,
    REVIEWING,
    IMPORTED,
    REJECTED;

    /** PARSED／REVIEWING：有可編輯、可簽核的草案。 */
    public boolean hasDraft() {
        return this == PARSED || this == REVIEWING;
    }

    /** IMPORTED／REJECTED 為終態。 */
    public boolean terminal() {
        return this == IMPORTED || this == REJECTED;
    }
}
