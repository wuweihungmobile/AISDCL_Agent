package com.aisdlc.console.domain.model.config;

/** 參數值型別（PRD §5.5.2；{@code value} 在 API 與資料庫一律是字串）。 */
public enum ConfigValueType {
    STRING,
    INTEGER,
    LONG,
    FLOAT,
    BOOLEAN,
    ENUM,
    ENCRYPTED
}
