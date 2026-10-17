package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.exception.Violations;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.function.BiFunction;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 專案 SDD 綁定三欄的值規則（契約 §0.5 V12、§1.10.7）。為什麼重要：這是 Backend 對 FSM 專案名唯一做的檢查——它刻意<b>不淨化</b>
 * （淨化鏡像只有 Bridge 有），所以這裡只准有「長度」與「控制字元」兩種判準；任何多做的檢查（例如白名單）都會把 Bridge 接受的名稱擋在門外。
 */
class SddBindingRulesTest {

    private static List<String> violationsOf(BiFunction<Violations, String, String> rule, String value) {
        Violations v = new Violations();
        rule.apply(v, value);
        try {
            v.throwIfAny();
        } catch (ValidationException e) {
            return e.violations().stream().map(Violation::field).toList();
        }
        return List.of();
    }

    @Test
    void aStoredProjectIsNullToClearOtherwiseStrippedAndOneToOneHundredChars() {
        Violations v = new Violations();
        assertThat(SddBindingRules.storedProject(v, "sddProject", null)).as("null＝清除，不是違規").isNull();
        assertThat(SddBindingRules.storedProject(v, "sddProject", "  my key 專案  ")).isEqualTo("my key 專案");
        assertThat(SddBindingRules.storedProject(v, "sddProject", "x".repeat(100))).hasSize(100);
        assertThat(SddBindingRules.storedProject(v, "sddProject", "a/b:c*?")).as("不檢查 Windows 禁用字元").isEqualTo("a/b:c*?");
        assertThat(v.isEmpty()).isTrue();
    }

    @Test
    void aBlankLongOrControlCharStoredProjectIsAViolationOnItsField() {
        for (String bad : new String[] {"", "   ", "x".repeat(101), "a\nb", "a\tb", "a\u0000b", "a\u007fb"}) {
            assertThat(violationsOf((v, value) -> SddBindingRules.storedProject(v, "sddProject", value), bad))
                    .as("[" + bad.length() + "]").containsExactly("sddProject");
        }
    }

    @Test
    void aRequestedProjectTreatsBlankAsAbsentAndCapsAtTwoHundred() {
        Violations v = new Violations();
        assertThat(SddBindingRules.requestedProject(v, "sddProject", null)).isNull();
        assertThat(SddBindingRules.requestedProject(v, "sddProject", "   ")).as("空白＝沒帶").isNull();
        assertThat(SddBindingRules.requestedProject(v, "sddProject", " My Project ")).isEqualTo("My Project");
        assertThat(SddBindingRules.requestedProject(v, "sddProject", "x".repeat(200))).hasSize(200);
        assertThat(v.isEmpty()).isTrue();
        for (String bad : new String[] {"x".repeat(201), "a\nb", "a\u007fb"}) {
            assertThat(violationsOf((vio, value) -> SddBindingRules.requestedProject(vio, "sddProject", value), bad))
                    .containsExactly("sddProject");
        }
    }

    @Test
    void aStoredPathIsNullWhenBlankOtherwiseStrippedAndAtMostFiveHundredChars() {
        Violations v = new Violations();
        assertThat(SddBindingRules.storedPath(v, "sddSpecDir", null)).isNull();
        assertThat(SddBindingRules.storedPath(v, "sddSpecDir", "  ")).isNull();
        assertThat(SddBindingRules.storedPath(v, "sddSpecDir", "  /work/spec  ")).isEqualTo("/work/spec");
        assertThat(SddBindingRules.storedPath(v, "sddSpecDir", "/" + "x".repeat(499))).hasSize(500);
        assertThat(v.isEmpty()).isTrue();
        for (String bad : new String[] {"/" + "x".repeat(500), "/a\nb", "/a\u0000b"}) {
            assertThat(violationsOf((vio, value) -> SddBindingRules.storedPath(vio, "sddSpecFile", value), bad))
                    .containsExactly("sddSpecFile");
        }
    }
}
