package com.aisdlc.console.adapter.out.persistence.research;

import com.aisdlc.console.support.BridgeSource;
import org.junit.jupiter.api.Test;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/** 遮蔽器與 Python 端同夾具對拍（AT-962-7-3、7-E-3）；邊界 299／300／301 字元與補充平面字元（excerpt 以 code point 計）。 */
class HealingExcerptMaskerTest {

    private static final String FIXTURE = "healing_redaction_cases.json";
    private static final JsonMapper JSON = JsonMapper.builder().build();

    private static List<Map<String, Object>> cases() {
        return JSON.readValue(BridgeSource.fixture("fixtures", "research", FIXTURE), new TypeReference<List<Map<String, Object>>>() { });
    }

    @Test
    void AT_962_7_3_theJavaMaskerEqualsTheFixtureExpectedValueForEveryCase() {
        List<Map<String, Object>> all = cases();
        assertThat(all).as("夾具不得為空").isNotEmpty();
        for (Map<String, Object> c : all) {
            assertThat(HealingExcerptMasker.mask((String) c.get("input"))).as("input=%s", c.get("input")).isEqualTo(c.get("expected"));
        }
        assertThat(all).as("夾具須含誤殺負控（keep）").anyMatch(c -> Boolean.TRUE.equals(c.get("keep")));
    }

    @Test
    void AT_962_7_3_theFixtureExistsExactlyOnceInTheRepository() throws IOException {
        try (Stream<Path> walk = Files.walk(Path.of("..", "engine-bridge", "tests"))) {
            assertThat(walk.filter(p -> p.getFileName().toString().equals(FIXTURE)).count()).isEqualTo(1);
        }
    }

    @Test
    void AT_962_7_E_3_theTestSourceDoesNotInlineASecondExpectedTable() throws IOException {
        String self = Files.readString(Path.of("src", "test", "java", "com", "aisdlc", "console", "adapter", "out", "persistence", "research",
                "HealingExcerptMaskerTest.java"));
        String ghPrefix = "gh" + "p_";
        assertThat(self).as("測試不內嵌 token 樣式字面").doesNotContain(ghPrefix);
        assertThat(self).contains("fixtures\", \"research\", FIXTURE");
    }

    @Test
    void excerptMasksFirstThenKeepsTheLast300CodePoints() {
        String token = "gh" + "p_AbCdEf0123456789xyZ0";
        String longText = "x".repeat(400) + token;
        String out = HealingExcerptMasker.excerpt(longText);
        assertThat(out).doesNotContain(token).endsWith("***").hasSize(300);
        for (int n : new int[] {299, 300, 301}) {
            assertThat(HealingExcerptMasker.excerpt("y".repeat(n)).length()).isEqualTo(Math.min(n, 300));
        }
        String astral = "😀".repeat(301);
        assertThat(HealingExcerptMasker.excerpt(astral).codePointCount(0, HealingExcerptMasker.excerpt(astral).length())).isEqualTo(300);
    }

    @Test
    void awsAccessKeyIdIsMaskedWholeButLowercaseOrTooShortIsNotAkiaOnlyCountsWithSixteenUppercaseAlphanumerics() {
        assertThat(HealingExcerptMasker.mask("key AKIAIOSFODNN7EXAMPLE leaked")).as("正控：整段換成 ***").isEqualTo("key *** leaked");
        assertThat(HealingExcerptMasker.mask("key akiaiosfodnn7example leaked")).as("負控：小寫不遮").isEqualTo("key akiaiosfodnn7example leaked");
        assertThat(HealingExcerptMasker.mask("key AKIAIOSFODNN7EXAMPL leaked")).as("負控：AKIA 後只有 15 位不遮").isEqualTo("key AKIAIOSFODNN7EXAMPL leaked");
        assertThat(HealingExcerptMasker.excerpt("x".repeat(400) + " AKIAIOSFODNN7EXAMPLE")).doesNotContain("AKIA").endsWith("***");
    }
}
