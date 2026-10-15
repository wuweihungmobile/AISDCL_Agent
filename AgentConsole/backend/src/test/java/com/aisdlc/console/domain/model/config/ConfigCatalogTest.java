package com.aisdlc.console.domain.model.config;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 設定鍵目錄（契約附錄 C）：50 個鍵、六個分類、API 輸出順序是契約的一部分。
 * 與資料庫（V2＋V5 種子）的逐鍵一致性由 {@code SettingsApiIT} 核對。
 */
class ConfigCatalogTest {

    @Test
    void thereAreFiftyKeysInTheDocumentedCategoryCounts() {
        Map<String, Long> counts = ConfigCatalog.all().stream()
                .collect(Collectors.groupingBy(ConfigSpec::category, Collectors.counting()));
        assertThat(ConfigCatalog.all()).hasSize(50);
        assertThat(counts).containsEntry("model", 10L).containsEntry("agent", 9L).containsEntry("execution", 10L)
                .containsEntry("monitor", 6L).containsEntry("autoclaude", 11L).containsEntry("sdd", 4L);
    }

    @Test
    void categoriesAreInTheDocumentedOrderAndTheCatalogFollowsIt() {
        assertThat(ConfigCatalog.CATEGORIES).containsExactly("model", "agent", "execution", "monitor", "autoclaude",
                "sdd");
        List<String> catalogCategories = ConfigCatalog.all().stream().map(ConfigSpec::category).distinct().toList();
        assertThat(catalogCategories).isEqualTo(ConfigCatalog.CATEGORIES);
        assertThat(ConfigCatalog.orderOf("model", "provider")).isLessThan(ConfigCatalog.orderOf("model", "apiUrl"));
        assertThat(ConfigCatalog.orderOf("model", "enableKernelBrain")).isLessThan(
                ConfigCatalog.orderOf("agent", "defaultAutonomyLevel"));
        assertThat(ConfigCatalog.orderOf("nope", "nope")).isEqualTo(Integer.MAX_VALUE);
    }

    @Test
    void everyEnumKeyHasOptionsAndOnlyEnumKeysDo() {
        for (ConfigSpec spec : ConfigCatalog.all()) {
            boolean enumKey = List.of("model.provider", "execution.dagSchedulerStrategy", "autoclaude.eventBusType",
                    "autoclaude.dalBackend", "autoclaude.dualReadResolution", "sdd.specFormat", "sdd.workflowEngine",
                    "sdd.validationLevel").contains(spec.fullKey());
            assertThat(!spec.options().isEmpty()).as(spec.fullKey()).isEqualTo(enumKey);
        }
    }

    @Test
    void theTokenGuardPairAndItsBoundsMatchTheDocumentedConstraints() {
        assertThat(ConfigCatalog.isTokenGuardKey("execution", "compactThresholdPct")).isTrue();
        assertThat(ConfigCatalog.isTokenGuardKey("execution", "haltThresholdPct")).isTrue();
        assertThat(ConfigCatalog.isTokenGuardKey("execution", "autoResume")).isFalse();
        assertThat(ConfigCatalog.isTokenGuardKey("model", "compactThresholdPct")).isFalse();
        ConfigSpec compact = ConfigCatalog.find("execution", "compactThresholdPct").orElseThrow();
        ConfigSpec halt = ConfigCatalog.find("execution", "haltThresholdPct").orElseThrow();
        assertThat(compact.min().intValue()).isEqualTo(ConfigCatalog.COMPACT_MIN);
        assertThat(compact.max().intValue()).isEqualTo(ConfigCatalog.COMPACT_MAX);
        assertThat(halt.min().intValue()).isEqualTo(ConfigCatalog.HALT_MIN);
        assertThat(halt.max().intValue()).isEqualTo(ConfigCatalog.HALT_MAX);
    }

    @Test
    void effectLabelsAreHonestAboutWhatReachesTheEngine() {
        assertThat(ConfigCatalog.find("autoclaude", "dalBackend").orElseThrow().effect())
                .as("Bridge 固定 yaml_only，此鍵不生效").isEqualTo(ConfigEffect.STORED_ONLY);
        assertThat(ConfigCatalog.find("agent", "enableSelfEvolution").orElseThrow().effect())
                .isEqualTo(ConfigEffect.UNVERIFIED);
        assertThat(ConfigCatalog.find("execution", "compactThresholdPct").orElseThrow().effect())
                .isEqualTo(ConfigEffect.ENGINE);
        assertThat(ConfigCatalog.find("agent", "defaultAutonomyLevel").orElseThrow().effect())
                .isEqualTo(ConfigEffect.CONSOLE);
    }

    @Test
    void unknownKeysAreAbsent() {
        assertThat(ConfigCatalog.find("model", "nope")).isEmpty();
        assertThat(ConfigCatalog.isCategory("nope")).isFalse();
        assertThat(ConfigCatalog.isCategory("sdd")).isTrue();
    }
}
