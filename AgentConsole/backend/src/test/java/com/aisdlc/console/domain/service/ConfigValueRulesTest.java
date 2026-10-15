package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.config.ConfigCatalog;
import com.aisdlc.console.domain.model.config.ConfigSpec;
import com.aisdlc.console.domain.model.config.ConfigValueType;
import com.aisdlc.console.domain.model.config.SystemConfig;
import com.aisdlc.console.domain.service.ConfigValueRules.Failure;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 設定值的型別、validation_rule、範圍與選項校驗（契約 §1.5.3 第 2 項、附錄 C）。為什麼重要：設定值最終會被物化成引擎的
 * 命令列與 config（例如 {@code claude.command}）；型別寬鬆放行等於把任意字串送進引擎。規則與範圍逐字取自附錄 C。
 */
class ConfigValueRulesTest {

    private static SystemConfig config(String category, String key, ConfigValueType type, String rule) {
        return new SystemConfig(UUID.randomUUID(), category, key, "", type, "", "d", type == ConfigValueType.ENCRYPTED,
                rule, null, null, null);
    }

    private static Optional<Failure> check(String category, String key, ConfigValueType type, String rule,
                                           String value) {
        ConfigSpec spec = ConfigCatalog.find(category, key).orElseThrow();
        return ConfigValueRules.check(config(category, key, type, rule), spec, value);
    }

    private static final String COMPACT_RULE = "^([1-9]|[1-9][0-9])$";
    private static final String HALT_RULE = "^([2-9]|[1-9][0-9]|100)$";
    private static final String REFRESH_RULE = "^(1[0-9]{4}|[2-5][0-9]{4}|60000)$";

    @ParameterizedTest(name = "compactThresholdPct={0} → {1}")
    @CsvSource({"1,true", "70,true", "99,true", "0,false", "100,false", "-5,false", "abc,false", "7.5,false",
            "07,false", "' 70',false", "'',false"})
    void integerRulesAndRangesApplyToTheCompactThreshold(String value, boolean valid) {
        assertThat(check("execution", "compactThresholdPct", ConfigValueType.INTEGER, COMPACT_RULE, value).isEmpty())
                .isEqualTo(valid);
    }

    @ParameterizedTest(name = "haltThresholdPct={0} → {1}")
    @CsvSource({"2,true", "95,true", "100,true", "1,false", "101,false", "0,false", "-1,false", "9.9,false"})
    void integerRulesAndRangesApplyToTheHaltThreshold(String value, boolean valid) {
        assertThat(check("execution", "haltThresholdPct", ConfigValueType.INTEGER, HALT_RULE, value).isEmpty())
                .isEqualTo(valid);
    }

    @Test
    void theRefreshIntervalHasATenSecondFloorSoOnePageCannotExhaustTheRateLimit() {
        assertThat(check("monitor", "refreshIntervalMs", ConfigValueType.INTEGER, REFRESH_RULE, "10000")).isEmpty();
        assertThat(check("monitor", "refreshIntervalMs", ConfigValueType.INTEGER, REFRESH_RULE, "15000")).isEmpty();
        assertThat(check("monitor", "refreshIntervalMs", ConfigValueType.INTEGER, REFRESH_RULE, "60000")).isEmpty();
        assertThat(check("monitor", "refreshIntervalMs", ConfigValueType.INTEGER, REFRESH_RULE, "900")).isPresent();
        assertThat(check("monitor", "refreshIntervalMs", ConfigValueType.INTEGER, REFRESH_RULE, "9999")).isPresent();
        assertThat(check("monitor", "refreshIntervalMs", ConfigValueType.INTEGER, REFRESH_RULE, "60001")).isPresent();
    }

    @Test
    void theFailureMessageStatesTheRangeSoTheFormCanShowIt() {
        Failure failure = check("agent", "defaultAutonomyLevel", ConfigValueType.INTEGER, "^([1-9]|10)$", "11")
                .orElseThrow();
        assertThat(failure.message()).isEqualTo("需為整數（1～10）");
    }

    @ParameterizedTest(name = "temperature={0} → {1}")
    @CsvSource({"0,true", "0.3,true", "1.99,true", "2,true", "2.5,false", "2.0001,false", "-1,false", "abc,false",
            "0.,false", ".5,false"})
    void floatsFollowTheirRuleAndRange(String value, boolean valid) {
        // 規則 ^[0-9](\.[0-9]+)?$ 只容許單一整數位；範圍 0～2（含）
        boolean expected = valid;
        assertThat(check("model", "temperature", ConfigValueType.FLOAT, "^[0-9](\\.[0-9]+)?$", value).isEmpty())
                .isEqualTo(expected);
    }

    @Test
    void floatThresholdsUseTheDocumentedBounds() {
        String rule = "^0\\.[0-9]{1,2}$";
        assertThat(check("execution", "tokenBudgetWarningThreshold", ConfigValueType.FLOAT, rule, "0.8")).isEmpty();
        assertThat(check("execution", "tokenBudgetWarningThreshold", ConfigValueType.FLOAT, rule, "0.01")).isEmpty();
        assertThat(check("execution", "tokenBudgetWarningThreshold", ConfigValueType.FLOAT, rule, "0.99")).isEmpty();
        assertThat(check("execution", "tokenBudgetWarningThreshold", ConfigValueType.FLOAT, rule, "0.00")).isPresent();
        assertThat(check("execution", "tokenBudgetWarningThreshold", ConfigValueType.FLOAT, rule, "1.0")).isPresent();
    }

    @Test
    void booleansAreLowerCaseTrueOrFalseOnly() {
        for (String ok : new String[] {"true", "false"}) {
            assertThat(check("model", "enableKernelBrain", ConfigValueType.BOOLEAN, "^(true|false)$", ok)).isEmpty();
        }
        for (String bad : new String[] {"True", "FALSE", "1", "0", "yes", "", " true"}) {
            assertThat(check("model", "enableKernelBrain", ConfigValueType.BOOLEAN, "^(true|false)$", bad))
                    .as(bad).isPresent();
        }
    }

    @Test
    void enumsMustBeOneOfTheCatalogOptionsCaseSensitively() {
        String rule = "^(TOPOLOGICAL|PRIORITY|SHORTEST_FIRST)$";
        assertThat(check("execution", "dagSchedulerStrategy", ConfigValueType.ENUM, rule, "PRIORITY")).isEmpty();
        Failure failure = check("execution", "dagSchedulerStrategy", ConfigValueType.ENUM, rule, "priority")
                .orElseThrow();
        assertThat(failure.message()).contains("TOPOLOGICAL", "PRIORITY", "SHORTEST_FIRST");
        assertThat(check("autoclaude", "dualReadResolution", ConfigValueType.ENUM, "^(yaml_wins|db_wins|fail_loud)$",
                "yaml_wins")).isEmpty();
    }

    @ParameterizedTest(name = "claudeCommand={0} → {1}")
    @ValueSource(strings = {"claude", "C:\\repo\\.venv\\Scripts\\aisdlc-mock-claude.exe", "/opt/bin/aisdlc-mock-claude",
            "C:/repo/.venv/Scripts/aisdlc-mock-claude.exe"})
    void claudeCommandAllowsWindowsAbsolutePathsAndExe(String value) {
        assertThat(check("autoclaude", "claudeCommand", ConfigValueType.STRING, "^[A-Za-z0-9_.\\-/\\\\:]{1,200}$",
                value)).isEmpty();
    }

    @ParameterizedTest(name = "claudeCommand={0} is refused")
    @ValueSource(strings = {"C:\\Program Files\\claude.exe", "claude --dangerously", "claude;rm", "claude|x",
            "$(whoami)", "claude\nx", ""})
    void claudeCommandRefusesWhitespaceAndShellMetacharacters(String value) {
        assertThat(check("autoclaude", "claudeCommand", ConfigValueType.STRING, "^[A-Za-z0-9_.\\-/\\\\:]{1,200}$",
                value)).as(value).isPresent();
    }

    @Test
    void encryptedValuesMayBeEmptyToClearButNotLongerThan512() {
        assertThat(check("model", "apiKey", ConfigValueType.ENCRYPTED, "^.{0,512}$", "")).isEmpty();
        assertThat(check("model", "apiKey", ConfigValueType.ENCRYPTED, "^.{0,512}$", "sk-" + "a".repeat(509)))
                .isEmpty();
        Failure tooLong = check("model", "apiKey", ConfigValueType.ENCRYPTED, "^.{0,512}$", "a".repeat(513))
                .orElseThrow();
        assertThat(tooLong.message()).contains("512");
    }

    @Test
    void nullNulAndOversizedValuesAreRefusedBeforeAnyRule() {
        assertThat(check("model", "name", ConfigValueType.STRING, "^[A-Za-z0-9._:/\\-]{1,100}$", null)).isPresent();
        assertThat(check("model", "name", ConfigValueType.STRING, null, "a\0b")).isPresent();
        assertThat(check("autoclaude", "playbookPath", ConfigValueType.STRING, null, "p".repeat(4001))).isPresent();
        assertThat(check("autoclaude", "playbookPath", ConfigValueType.STRING, null, "p".repeat(4000))).isEmpty();
    }

    @Test
    void aMissingRuleMeansOnlyTheTypeChecksApply() {
        assertThat(check("agent", "maxRetries", ConfigValueType.INTEGER, null, "5")).isEmpty();
        assertThat(check("agent", "maxRetries", ConfigValueType.INTEGER, null, "21")).as("範圍仍然生效").isPresent();
        assertThat(check("agent", "maxRetries", ConfigValueType.INTEGER, null, "x")).isPresent();
    }

    @Test
    void largeLongValuesAreComparedExactlyWithoutOverflow() {
        String rule = "^[1-9][0-9]{0,11}$";
        assertThat(check("execution", "globalTokenBudget", ConfigValueType.LONG, rule, "999999999999")).isEmpty();
        // 範圍上限是 999999999999（12 位數）：與同一列的規則 {0,11} 一致（契約 v1.2 更正，B1-1；
        // v1.1 寫的 1000000000000 有 13 位，與規則矛盾）。
        assertThat(check("execution", "globalTokenBudget", ConfigValueType.LONG, rule, "1000000000000"))
                .as("13 位數被 validation_rule 擋下").isPresent();
        assertThat(check("execution", "globalTokenBudget", ConfigValueType.LONG, rule, "999999999999999"))
                .as("超過 12 位數").isPresent();
        assertThat(check("execution", "globalTokenBudget", ConfigValueType.LONG, rule, "0")).isPresent();
    }
}
