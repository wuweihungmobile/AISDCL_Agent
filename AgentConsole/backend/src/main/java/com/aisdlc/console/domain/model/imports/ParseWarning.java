package com.aisdlc.console.domain.model.imports;

/**
 * 非阻擋提示（契約 §3.3.6、§3.3.2 v1.5 補充第 6 點）：例如不安全的 evaluatorCommand 被清空。
 *
 * @param code     {@code evaluator_command_dropped}／{@code regex_dropped}／{@code passcriteria_placeholder}；
 *                 v1.5 路徑 A 另有 {@code at_unmapped}／{@code frozen_digest_absent}／{@code state_dir_not_ignored}
 * @param location 位置，例如 {@code goals[0].tasks[1]}、{@code specDir}、{@code executionPath}；可為 null
 */
public record ParseWarning(String code, String detail, String location) {

    public static final String EVALUATOR_COMMAND_DROPPED = "evaluator_command_dropped";
    public static final String REGEX_DROPPED = "regex_dropped";
    public static final String PASSCRITERIA_PLACEHOLDER = "passcriteria_placeholder";
    /** 規格<b>宣告位置</b>出現、卻沒被編成步驟的 AT（{@code unmapped_at_ids} 非空）；已編成的 AT 照常產出任務；{@code location=specDir}。 */
    public static final String AT_UNMAPPED = "at_unmapped";
    /** 規格凍結時沒有記錄內容摘要（舊狀態檔）：放行，但無法偵測凍結後改檔；{@code location=specDir}。 */
    public static final String FROZEN_DIGEST_ABSENT = "frozen_digest_absent";
    /** 專案根的 {@code build/reports/fsm/} 未被 git 忽略（Bridge 回報，原樣轉入）；{@code location=executionPath}。 */
    public static final String STATE_DIR_NOT_IGNORED = "state_dir_not_ignored";

    /** AI 沒給通過標準時填入的佔位字串（契約 §3.3.3）；signoff 前須由人補齊。 */
    public static final String PASSCRITERIA_PLACEHOLDER_TEXT = "（AI 解析未提供通過標準，請於 signoff 前補齊）";

    /**
     * 路徑 A 的三個規格層級提示（與可由人編輯的任務內容無關）：PUT result 重算提示時保留它們（它們「仍成立」）。
     * 刻意是靜態方法而不是 {@code isXxx()} 實例方法：這個 record 會被序列化成 JSONB，bean 風格的 getter 會多出一個欄位。
     */
    public static boolean isSpecLevel(ParseWarning warning) {
        String code = warning.code();
        return AT_UNMAPPED.equals(code) || FROZEN_DIGEST_ABSENT.equals(code) || STATE_DIR_NOT_IGNORED.equals(code);
    }
}
