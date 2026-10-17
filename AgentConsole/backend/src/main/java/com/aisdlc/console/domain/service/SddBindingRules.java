package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.Violations;

import java.util.regex.Pattern;

/**
 * 專案 SDD 綁定三欄的值規則（契約 §0.5 V12、§1.10.7；純 Java）。
 *
 * <p>🔴 Backend <b>不淨化</b> FSM 專案名（淨化鏡像只有 Bridge 有；ADR-XPLAT-016 §7.4）：這裡只驗長度與控制字元，
 * 值原樣保存、原樣交給 Bridge。
 */
public final class SddBindingRules {

    /** {@code projects.sdd_project} 的長度上限（V12 {@code VARCHAR(100)}）。 */
    public static final int MAX_PROJECT_KEY = 100;
    /** {@code projects.sdd_spec_dir}／{@code sdd_spec_file} 的長度上限（V12 {@code VARCHAR(500)}，與 {@code execution_path} 同）。 */
    public static final int MAX_PATH = 500;

    /** U+0000～U+001F 與 U+007F。 */
    private static final Pattern CONTROL_CHARS = Pattern.compile("\\p{Cntrl}");

    private SddBindingRules() {
    }

    /**
     * FSM 專案鍵的儲存形式：{@code null}＝清除（回到「用預設」＝專案名），不是違規；非 null 時去前後空白後須 1～100 字元且不含控制字元
     * （空白字串是違規，不是清除）。有違規時記進 {@code v} 並回 null。
     */
    public static String storedProject(Violations v, String field, String value) {
        if (value == null) {
            return null;
        }
        String text = value.strip();
        if (text.isEmpty()) {
            v.add(field, "FSM 專案不可為空白；要清除請傳 null");
            return null;
        }
        if (text.length() > MAX_PROJECT_KEY) {
            v.add(field, "FSM 專案長度不可超過 " + MAX_PROJECT_KEY + " 字元");
            return null;
        }
        if (CONTROL_CHARS.matcher(text).find()) {
            v.add(field, "FSM 專案不可包含控制字元");
            return null;
        }
        return text;
    }

    /** 路徑 A 解析選項／{@code GET /engines/sdd} 的 FSM 專案名「有效值」上限（專案名上限；值可以是原名，不必是標準鍵）。 */
    public static final int MAX_EFFECTIVE_PROJECT = 200;

    /**
     * 路徑 A 解析選項的 {@code sddProject}（有效值，可以是原名；契約 §3.3.2 第 2 點）：null 或空白＝沒帶（回 null）；其餘去前後空白，
     * 須 ≤ 200 字元且不含控制字元。Console 不淨化、不檢查 Windows 禁用字元：值原樣交給 Bridge 的淨化鏡像。
     */
    public static String requestedProject(Violations v, String field, String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String text = value.strip();
        if (text.length() > MAX_EFFECTIVE_PROJECT) {
            v.add(field, "FSM 專案長度不可超過 " + MAX_EFFECTIVE_PROJECT + " 字元");
            return null;
        }
        if (CONTROL_CHARS.matcher(text).find()) {
            v.add(field, "FSM 專案不可包含控制字元");
            return null;
        }
        return text;
    }

    /** 規格目錄／規格檔路徑的儲存形式：null 或空白＝沒有（回 null）；其餘去前後空白，須 ≤ 500 字元且不含控制字元。 */
    public static String storedPath(Violations v, String field, String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String text = value.strip();
        if (text.length() > MAX_PATH) {
            v.add(field, "規格路徑長度不可超過 " + MAX_PATH + " 字元");
            return null;
        }
        if (CONTROL_CHARS.matcher(text).find()) {
            v.add(field, "規格路徑不可包含控制字元");
            return null;
        }
        return text;
    }
}
