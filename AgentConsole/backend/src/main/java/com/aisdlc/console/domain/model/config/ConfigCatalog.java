package com.aisdlc.console.domain.model.config;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static com.aisdlc.console.domain.model.config.ConfigEffect.CONSOLE;
import static com.aisdlc.console.domain.model.config.ConfigEffect.ENGINE;
import static com.aisdlc.console.domain.model.config.ConfigEffect.STORED_ONLY;
import static com.aisdlc.console.domain.model.config.ConfigEffect.UNVERIFIED;

/**
 * 50 個設定鍵的程式內目錄（契約附錄 C；PRD §5.5.1）：分類順序、分類內順序、{@code effect}、數值範圍與 ENUM 選項。
 *
 * <p>順序是 API 的一部分（{@code GET /settings} 的分類順序 {@code model,agent,execution,monitor,autoclaude,sdd}，
 * 分類內依附錄 C 排序）。型別／預設／{@code validation_rule}／{@code impact_note} 住在資料庫（V2＋V5），
 * 本目錄與資料庫的一致性由 {@code SettingsApiIT} 逐鍵核對。
 */
public final class ConfigCatalog {

    /** 分類順序（API 輸出順序）。 */
    public static final List<String> CATEGORIES = List.of("model", "agent", "execution", "monitor", "autoclaude", "sdd");

    /** token_guard 群組（NFR-SEC-05）：兩鍵須滿足 {@code halt > compact}。 */
    public static final String TOKEN_GUARD_CATEGORY = "execution";
    public static final String COMPACT_KEY = "compactThresholdPct";
    public static final String HALT_KEY = "haltThresholdPct";
    public static final int COMPACT_MIN = 1;
    public static final int COMPACT_MAX = 99;
    public static final int HALT_MIN = 2;
    public static final int HALT_MAX = 100;

    private static final List<ConfigSpec> ALL = build();
    private static final Map<String, ConfigSpec> BY_FULL_KEY = index(ALL);
    private static final Map<String, Integer> ORDER = order(ALL);

    private ConfigCatalog() {
    }

    public static List<ConfigSpec> all() {
        return ALL;
    }

    public static Optional<ConfigSpec> find(String category, String key) {
        return Optional.ofNullable(BY_FULL_KEY.get(category + "." + key));
    }

    public static boolean isCategory(String category) {
        return CATEGORIES.contains(category);
    }

    /** 鍵在目錄中的位置（分類順序優先，再依分類內順序）；不在目錄內的排最後。 */
    public static int orderOf(String category, String key) {
        return ORDER.getOrDefault(category + "." + key, Integer.MAX_VALUE);
    }

    public static boolean isTokenGuardKey(String category, String key) {
        return TOKEN_GUARD_CATEGORY.equals(category) && (COMPACT_KEY.equals(key) || HALT_KEY.equals(key));
    }

    // ── 目錄本體（附錄 C.1～C.6）────────────────────────────────────────────────

    private static List<ConfigSpec> build() {
        List<ConfigSpec> specs = new ArrayList<>();
        // C.1 model（10）
        specs.add(spec("model", "provider", STORED_ONLY, null, null, "ANTHROPIC", "OPENAI", "LOCAL", "CUSTOM"));
        specs.add(spec("model", "apiUrl", ENGINE, null, null));
        specs.add(spec("model", "apiKey", ENGINE, null, null));
        specs.add(spec("model", "name", ENGINE, null, null));
        specs.add(spec("model", "maxTokensPerRequest", CONSOLE, "1", "200000"));
        specs.add(spec("model", "temperature", CONSOLE, "0", "2"));
        specs.add(spec("model", "topP", CONSOLE, "0", "1"));
        specs.add(spec("model", "timeout", ENGINE, "1", "600"));
        specs.add(spec("model", "rateLimitPerMinute", STORED_ONLY, "1", "10000"));
        specs.add(spec("model", "enableKernelBrain", ENGINE, null, null));
        // C.2 agent（9）
        specs.add(spec("agent", "defaultAutonomyLevel", CONSOLE, "1", "10"));
        specs.add(spec("agent", "maxConcurrentTasks", STORED_ONLY, "1", "32"));
        specs.add(spec("agent", "taskTimeout", ENGINE, "10", "86400"));
        specs.add(spec("agent", "maxRetries", ENGINE, "0", "20"));
        specs.add(spec("agent", "retryBackoffMs", STORED_ONLY, "0", "3600000"));
        specs.add(spec("agent", "retryBackoffMultiplier", STORED_ONLY, "1", "10"));
        specs.add(spec("agent", "checkpointInterval", STORED_ONLY, "1", "1000"));
        specs.add(spec("agent", "enableAutoMutation", UNVERIFIED, null, null));
        specs.add(spec("agent", "enableSelfEvolution", UNVERIFIED, null, null));
        // C.3 execution（10）
        // 上限 999999999999（12 位）：與 V5 的 validation_rule ^[1-9][0-9]{0,11}$ 一致（契約 v1.2 更正，B1-1；v1.1 寫的 13 位上限會讓 GET /settings 的 max 比規則多 1）
        specs.add(spec("execution", "globalTokenBudget", CONSOLE, "1", "999999999999"));
        specs.add(spec("execution", "tokenBudgetWarningThreshold", CONSOLE, "0.01", "0.99"));
        specs.add(spec("execution", "maxParallelGoals", STORED_ONLY, "1", "16"));
        specs.add(spec("execution", "dagSchedulerStrategy", CONSOLE, null, null,
                "TOPOLOGICAL", "PRIORITY", "SHORTEST_FIRST"));
        specs.add(spec("execution", "enableRollback", STORED_ONLY, null, null));
        specs.add(spec("execution", "logRetentionDays", CONSOLE, "1", "3650"));
        specs.add(spec("execution", COMPACT_KEY, ENGINE, "1", "99"));
        specs.add(spec("execution", HALT_KEY, ENGINE, "2", "100"));
        specs.add(spec("execution", "autoResume", ENGINE, null, null));
        specs.add(spec("execution", "maxAutoResumes", ENGINE, "1", "100"));
        // C.4 monitor（6）
        specs.add(spec("monitor", "refreshIntervalMs", CONSOLE, "10000", "60000"));
        specs.add(spec("monitor", "alertConsecutiveFailures", CONSOLE, "2", "20"));
        specs.add(spec("monitor", "alertAgentTimeoutSec", CONSOLE, "30", "86400"));
        specs.add(spec("monitor", "alertTaskDurationMultiplier", CONSOLE, "1", "20"));
        specs.add(spec("monitor", "enableEmailNotification", STORED_ONLY, null, null));
        specs.add(spec("monitor", "notificationEmail", STORED_ONLY, null, null));
        // C.5 autoclaude（11）
        specs.add(spec("autoclaude", "engineUrl", CONSOLE, null, null));
        specs.add(spec("autoclaude", "healthCheckPath", CONSOLE, null, null));
        specs.add(spec("autoclaude", "eventBusType", STORED_ONLY, null, null, "INTERNAL", "KAFKA", "RABBITMQ"));
        specs.add(spec("autoclaude", "dalBackend", STORED_ONLY, null, null, "FILE", "IN_MEMORY", "POSTGRESQL"));
        specs.add(spec("autoclaude", "playbookPath", STORED_ONLY, null, null));
        specs.add(spec("autoclaude", "claudeCommand", ENGINE, null, null));
        specs.add(spec("autoclaude", "claudeExtraArgs", ENGINE, null, null));
        specs.add(spec("autoclaude", "claudeContinueFlag", ENGINE, null, null));
        specs.add(spec("autoclaude", "claudeEncoding", ENGINE, null, null));
        specs.add(spec("autoclaude", "dbDsn", STORED_ONLY, null, null));
        specs.add(spec("autoclaude", "dualReadResolution", STORED_ONLY, null, null,
                "yaml_wins", "db_wins", "fail_loud"));
        // C.6 sdd（4）
        specs.add(spec("sdd", "engineUrl", CONSOLE, null, null));
        specs.add(spec("sdd", "specFormat", UNVERIFIED, null, null, "YAML", "JSON", "TOML"));
        specs.add(spec("sdd", "workflowEngine", UNVERIFIED, null, null, "STATIC", "DYNAMIC", "ADAPTIVE"));
        specs.add(spec("sdd", "validationLevel", UNVERIFIED, null, null, "LAX", "NORMAL", "STRICT"));
        return List.copyOf(specs);
    }

    private static ConfigSpec spec(String category, String key, ConfigEffect effect, String min, String max,
                                   String... options) {
        return new ConfigSpec(category, key, effect, min == null ? null : new BigDecimal(min),
                max == null ? null : new BigDecimal(max), List.of(options));
    }

    private static Map<String, ConfigSpec> index(List<ConfigSpec> specs) {
        Map<String, ConfigSpec> map = new HashMap<>();
        specs.forEach(s -> map.put(s.fullKey(), s));
        return Map.copyOf(map);
    }

    private static Map<String, Integer> order(List<ConfigSpec> specs) {
        Map<String, Integer> map = new LinkedHashMap<>();
        for (int i = 0; i < specs.size(); i++) {
            map.put(specs.get(i).fullKey(), i);
        }
        return Map.copyOf(map);
    }
}
