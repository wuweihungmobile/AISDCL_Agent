package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.Violations;

import java.util.regex.Pattern;

/**
 * 欄位層級的共用驗證規則（純 Java）。這是 domain 的最後一道防線——Controller 邊界的 Bean Validation
 * 先擋一次，但 domain 不能假設呼叫者一定走過 HTTP（例如日後匯入確認會直接建立聚合）。
 *
 * <p>所有方法把違規累積進 {@link Violations}（由呼叫端統一 {@code throwIfAny()}），回傳正規化後的值；
 * 有違規時回傳 null。
 */
public final class FieldRules {

    /** POSIX 絕對路徑、Windows 磁碟機代號路徑（C:\ 或 C:/）、UNC（\\server\share）。不碰檔案系統、與平台無關。 */
    private static final Pattern ABSOLUTE_PATH = Pattern.compile("^(?:/|[A-Za-z]:[\\\\/]|\\\\\\\\)\\S.*$");
    private static final Pattern CONTROL_CHARS = Pattern.compile("\\p{Cntrl}");

    private FieldRules() {
    }

    /** 必填單行文字：去頭尾空白後不可為空、不可超過 maxLength。 */
    public static String requiredText(Violations v, String field, String label, String value, int maxLength) {
        if (value == null || value.isBlank()) {
            v.add(field, label + "不能為空");
            return null;
        }
        String text = value.strip();
        if (text.length() > maxLength) {
            v.add(field, label + "長度不可超過 " + maxLength + " 字元");
            return null;
        }
        return text;
    }

    /** 必填 Markdown：只檢查非空白，內容原樣保留（不 strip，避免吃掉縮排）。 */
    public static String requiredMarkdown(Violations v, String field, String label, String value) {
        if (value == null || value.isBlank()) {
            v.add(field, label + "不能為空");
            return null;
        }
        return value;
    }

    /** 選填 Markdown：空白視為「沒有」（回 null），其餘原樣保留。 */
    public static String optionalMarkdown(String value) {
        return value == null || value.isBlank() ? null : value;
    }

    /** 選填單行文字：空白視為「沒有」；超長記違規。 */
    public static String optionalText(Violations v, String field, String label, String value, int maxLength) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String text = value.strip();
        if (text.length() > maxLength) {
            v.add(field, label + "長度不可超過 " + maxLength + " 字元");
            return null;
        }
        return text;
    }

    /** 專案執行路徑：必填、≤ 500、絕對路徑格式、無控制字元（NFR-SEC-03 第 1 層）。 */
    public static String executionPath(Violations v, String field, String value) {
        String text = requiredText(v, field, "執行路徑", value, 500);
        if (text == null) {
            return null;
        }
        if (!ABSOLUTE_PATH.matcher(text).matches()) {
            v.add(field, "執行路徑必須是絕對路徑（POSIX 的 / 開頭，或 Windows 的磁碟機代號／UNC 開頭）");
            return null;
        }
        if (CONTROL_CHARS.matcher(text).find()) {
            v.add(field, "執行路徑不可包含控制字元");
            return null;
        }
        return text;
    }

    /** 自治等級：null 取預設值，否則須在 1～10。 */
    public static Integer autonomyLevel(Violations v, String field, Integer value, int defaultValue) {
        if (value == null) {
            return defaultValue;
        }
        if (value < 1 || value > 10) {
            v.add(field, "自治等級必須介於 1 到 10");
            return null;
        }
        return value;
    }
}
