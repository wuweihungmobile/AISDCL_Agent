package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.ValidationException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** NFR-SEC-03 第 1 層：黑名單字元消毒與正規表示式可編譯性。 */
class PassCriteriaSanitizerTest {

    @Test
    void denyCharsAreExactlyTheSsotSetOfEightCharacters() {
        // SSOT：AutoClaude/autoclaude/utils/shell_deny_chars.py 的 BASE_DENY_CHARS = frozenset("!`><~$&;")
        assertThat(PassCriteriaSanitizer.DENY_CHARS)
                .hasSize(8)
                .containsExactlyInAnyOrderElementsOf(Set.of('!', '`', '>', '<', '~', '$', '&', ';'));
    }

    @ParameterizedTest(name = "單一違規字元 [{0}] 被擋並列出")
    @ValueSource(strings = {"!", "`", ">", "<", "~", "$", "&", ";"})
    void everyDenyCharIsRejectedAndNamedInTheError(String badChar) {
        String command = "echo ok " + badChar + " done";
        assertThatThrownBy(() -> PassCriteriaSanitizer.requireSafeCommand("evaluatorCommand", command))
                .isInstanceOfSatisfying(ValidationException.class, e -> {
                    assertThat(e.violations()).hasSize(1);
                    assertThat(e.violations().get(0).field()).isEqualTo("evaluatorCommand");
                    assertThat(e.violations().get(0).message()).contains(badChar);
                    assertThat(e.details().get("violations")).isEqualTo(List.of(badChar));
                });
    }

    @Test
    void multipleViolationsAreListedOncePerCharInOrderOfFirstOccurrence() {
        assertThat(PassCriteriaSanitizer.violationsOf("a; b && c $d ; e")).containsExactly(';', '&', '$');
        assertThatThrownBy(() -> PassCriteriaSanitizer.requireSafeCommand("evaluatorCommand", "a; b && c $d"))
                .isInstanceOfSatisfying(ValidationException.class,
                        e -> assertThat(e.details().get("violations")).isEqualTo(List.of(";", "&", "$")));
    }

    @ParameterizedTest
    @ValueSource(strings = {"pytest -q tests/", "npm run lint", "python -m pytest -k 'smoke' --maxfail=1",
            "./gradlew test", "git diff --exit-code"})
    void ordinaryCommandsPass(String command) {
        assertThatCode(() -> PassCriteriaSanitizer.requireSafeCommand("evaluatorCommand", command))
                .doesNotThrowAnyException();
    }

    @ParameterizedTest(name = "控制字元被擋：{index}")
    @ValueSource(strings = {"echo a\nrm -rf x", "echo a\rb", "echo a\tb", "echo a\u0000b"})
    void controlCharactersAreRejected(String command) {
        assertThatThrownBy(() -> PassCriteriaSanitizer.requireSafeCommand("evaluatorCommand", command))
                .isInstanceOfSatisfying(ValidationException.class,
                        e -> assertThat(e.violations().get(0).message()).contains("控制字元"));
    }

    @Test
    void nullAndBlankMeanNotProvidedAndPass() {
        assertThatCode(() -> PassCriteriaSanitizer.requireSafeCommand("evaluatorCommand", null))
                .doesNotThrowAnyException();
        assertThatCode(() -> PassCriteriaSanitizer.requireSafeCommand("evaluatorCommand", "   "))
                .doesNotThrowAnyException();
        assertThat(PassCriteriaSanitizer.violationsOf(null)).isEmpty();
    }

    @Test
    void validRegexPassesAndInvalidRegexIsRejectedWithTheFieldName() {
        assertThatCode(() -> PassCriteriaSanitizer.requireCompilableRegex("expectedOutputRegex", "^OK \\d+$"))
                .doesNotThrowAnyException();
        assertThatThrownBy(() -> PassCriteriaSanitizer.requireCompilableRegex("expectedOutputRegex", "([a-z"))
                .isInstanceOfSatisfying(ValidationException.class, e -> {
                    assertThat(e.violations().get(0).field()).isEqualTo("expectedOutputRegex");
                    assertThat(e.violations().get(0).message()).contains("正規表示式");
                });
        assertThatCode(() -> PassCriteriaSanitizer.requireCompilableRegex("expectedOutputRegex", ""))
                .doesNotThrowAnyException();
    }
}
