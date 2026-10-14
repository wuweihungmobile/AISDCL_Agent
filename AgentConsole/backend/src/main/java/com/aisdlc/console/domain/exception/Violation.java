package com.aisdlc.console.domain.exception;

/**
 * 單一欄位的違規明細（對應 PRD §7.2 錯誤格式的 {@code errors[{field,message}]}）。
 *
 * @param field   欄位名稱（camelCase，與 API 欄位一致）
 * @param message 給人看的繁體中文說明
 */
public record Violation(String field, String message) implements java.io.Serializable {
}
