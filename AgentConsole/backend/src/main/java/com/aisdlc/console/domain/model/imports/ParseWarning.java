package com.aisdlc.console.domain.model.imports;

/**
 * 非阻擋提示（契約 §3.3.6）：例如不安全的 evaluatorCommand 被清空。
 *
 * @param code     {@code evaluator_command_dropped}／{@code regex_dropped}／{@code passcriteria_placeholder}
 * @param location 位置，例如 {@code goals[0].tasks[1]}；可為 null
 */
public record ParseWarning(String code, String detail, String location) {

    public static final String EVALUATOR_COMMAND_DROPPED = "evaluator_command_dropped";
    public static final String REGEX_DROPPED = "regex_dropped";
    public static final String PASSCRITERIA_PLACEHOLDER = "passcriteria_placeholder";

    /** AI 沒給通過標準時填入的佔位字串（契約 §3.3.3）；signoff 前須由人補齊。 */
    public static final String PASSCRITERIA_PLACEHOLDER_TEXT = "（AI 解析未提供通過標準，請於 signoff 前補齊）";
}
