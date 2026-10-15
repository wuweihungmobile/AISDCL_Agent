package com.aisdlc.console.domain.service;

/**
 * 步驟 prompt 樣板（契約 §3.4.3）：一個任務在引擎 playbook 裡的 {@code tasks[].prompt}。
 *
 * <pre>
 * ## 任務 &lt;stepId&gt;：&lt;task.name&gt;
 * 所屬目標：&lt;goal.name&gt;
 *
 * &lt;task.description&gt;
 *
 * ## 通過標準
 * &lt;task.passCriteria&gt;
 * </pre>
 *
 * <p>行以 {@code \n} 連接；{@code description} 去空白後為空時，描述那一段（連同它前後的空行）整段省略。
 * 加入 stepId 與任務名稱是為了讓每步 prompt 互不為子字串（Bridge 以「步驟 prompt 是否出現在引擎啟動行」辨識步驟邊界）。
 * {@code description}／{@code passCriteria} 的 Markdown 原文原樣帶入，不另轉義。
 *
 * <p>長度以 Java {@code String.length()}（UTF-16 code unit）計，上限 {@link #MAX_LENGTH}（Windows 整條命令列上限
 * 32,767 字元，Architecture §12 L-9）。匯入階段用它做 {@code prompt_too_long} 閘；執行階段由 B2 重用同一支。
 */
public final class StepPrompt {

    /** 單一步驟 prompt 的字元上限（含）。 */
    public static final int MAX_LENGTH = 20_000;

    private StepPrompt() {
    }

    public static String build(String stepId, String taskName, String goalName, String description,
                               String passCriteria) {
        StringBuilder out = new StringBuilder();
        out.append("## 任務 ").append(stepId).append('：').append(nullToEmpty(taskName)).append('\n');
        out.append("所屬目標：").append(nullToEmpty(goalName)).append('\n');
        if (description != null && !description.isBlank()) {
            out.append('\n').append(description).append('\n').append('\n');
        }
        out.append("## 通過標準").append('\n').append(nullToEmpty(passCriteria));
        return out.toString();
    }

    private static String nullToEmpty(String value) {
        return value == null ? "" : value;
    }
}
