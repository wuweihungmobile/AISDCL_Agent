package com.aisdlc.console.domain.service;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 步驟 prompt 樣板（契約 §3.4.3）。為什麼重要：每步 prompt 必須互不為子字串（Bridge 以「prompt 是否出現在引擎啟動行」
 * 辨識步驟邊界），所以 stepId 與任務名稱是樣板的一部分；長度上限 20,000 是 Windows 命令列的硬限制。
 */
class StepPromptTest {

    @Test
    void theTemplateJoinsLinesWithNewlinesInTheDocumentedOrder() {
        assertThat(StepPrompt.build("G1-T2", "設定", "基礎", "請輸出 [T2_DONE]", "輸出含 [T2_DONE]")).isEqualTo(
                "## 任務 G1-T2：設定\n所屬目標：基礎\n\n請輸出 [T2_DONE]\n\n## 通過標準\n輸出含 [T2_DONE]");
    }

    @Test
    void aBlankDescriptionOmitsTheWholeParagraphIncludingItsSurroundingBlankLines() {
        String expected = "## 任務 G1-T1：初始化\n所屬目標：基礎\n## 通過標準\nPC";
        assertThat(StepPrompt.build("G1-T1", "初始化", "基礎", "", "PC")).isEqualTo(expected);
        assertThat(StepPrompt.build("G1-T1", "初始化", "基礎", "   \n  ", "PC")).isEqualTo(expected);
        assertThat(StepPrompt.build("G1-T1", "初始化", "基礎", null, "PC")).isEqualTo(expected);
    }

    @Test
    void markdownIsCarriedVerbatimWithoutEscapingOrTrimming() {
        String description = "  - 項目一\n  - 項目二 `code` *強調*\n";
        String prompt = StepPrompt.build("G2-T1", "實作", "核心", description, "- 通過");
        assertThat(prompt).contains("\n\n" + description + "\n\n## 通過標準\n- 通過");
    }

    @Test
    void differentStepIdsOrNamesNeverProduceSubstringPrompts() {
        String first = StepPrompt.build("G1-T1", "初始化", "基礎", "做事", "PC");
        String second = StepPrompt.build("G1-T10", "初始化", "基礎", "做事", "PC");
        assertThat(second).doesNotContain(first);
        assertThat(first).doesNotContain(second);
    }

    @Test
    void theLengthLimitIsTwentyThousandUtf16CodeUnits() {
        assertThat(StepPrompt.MAX_LENGTH).isEqualTo(20_000);
    }
}
