package com.aisdlc.console.infrastructure.persistence;

import com.aisdlc.console.support.AbstractIntegrationTest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Flyway 遷移（V1～V6）與 JPA schema 驗證（ADR-001 D5）。
 *
 * <p>能啟動本 context 本身就代表 {@code ddl-auto=validate} 通過（13 個實體與 Flyway 建出的表一致）；
 * 這裡另外把「為什麼重要」寫成斷言：DDL 必須由 Flyway 擁有、表必須全在 console schema（不與 AutoClaude 的
 * public.checkpoints 等同名表撞名）、種子要齊、關鍵 CHECK／UNIQUE／partial index 要真的存在。
 *
 * <p>契約 §0.8 的既有測試同步：V5（九個新鍵、impact_note、parse_path／last_parse_errors、預設校正）與
 * V6（audit_log）落地後，種子計數、加密鍵數與版本清單的「真值」改變，測試的意圖不變。
 */
class SchemaMigrationIT extends AbstractIntegrationTest {

    private static final Set<String> CONSOLE_TABLES = Set.of(
            "projects", "goals", "goal_dependencies", "tasks", "execution_runs", "execution_steps",
            "checkpoints", "import_records", "system_configs", "system_config_history",
            "review_requests", "alerts", "audit_log", "run_token_samples");

    @Autowired
    JdbcTemplate jdbc;

    @Autowired
    Environment env;

    @Test
    void ddlIsOwnedByFlywayAndJpaOnlyValidates() {
        assertThat(env.getProperty("spring.jpa.hibernate.ddl-auto")).isEqualTo("validate");
        assertThat(env.getProperty("spring.jpa.properties.hibernate.default_schema")).isEqualTo("console");
        assertThat(env.getProperty("spring.flyway.default-schema")).isEqualTo("console");
    }

    @Test
    void allFourteenTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic() {
        List<String> inConsole = jdbc.queryForList(
                "select table_name from information_schema.tables where table_schema = 'console' "
                        + "and table_type = 'BASE TABLE'", String.class);
        assertThat(inConsole).containsAll(CONSOLE_TABLES).contains("flyway_schema_history");

        List<String> leaked = jdbc.queryForList(
                "select table_name from information_schema.tables where table_schema = 'public'", String.class);
        assertThat(leaked).as("Console 的表不可出現在 public（會與 AutoClaude 的同名表撞名）")
                .doesNotContainAnyElementsOf(CONSOLE_TABLES);
    }

    @Test
    void flywayAppliedVersionsOneToNineSuccessfully() {
        List<Map<String, Object>> history = jdbc.queryForList(
                "select version, success from console.flyway_schema_history where version is not null "
                        + "order by installed_rank");
        assertThat(history).extracting(row -> row.get("version"))
                .containsExactly("1", "2", "3", "4", "5", "6", "7", "8", "9");
        assertThat(history).allSatisfy(row -> assertThat(row.get("success")).isEqualTo(true));
    }

    /** V9（契約 §0.5；C-3）：專案、目標、任務的軟刪除時間，加上專案軟刪除前的狀態；「已刪除」清單用的 partial index。 */
    @Test
    void v9AddsTheSoftDeleteTimestampsTheStatusBeforeDeleteAndThePartialIndexOnDeletedProjects() {
        for (String table : List.of("projects", "goals", "tasks")) {
            Map<String, Object> column = jdbc.queryForMap("select data_type, is_nullable from information_schema.columns "
                    + "where table_schema = 'console' and table_name = ? and column_name = 'deleted_at'", table);
            assertThat(column).as(table + ".deleted_at").containsEntry("data_type", "timestamp with time zone")
                    .containsEntry("is_nullable", "YES");
        }
        Map<String, Object> before = jdbc.queryForMap("select data_type, is_nullable, character_maximum_length from "
                + "information_schema.columns where table_schema = 'console' and table_name = 'projects' "
                + "and column_name = 'status_before_delete'");
        assertThat(before).containsEntry("data_type", "character varying").containsEntry("is_nullable", "YES")
                .containsEntry("character_maximum_length", 20);
        String index = jdbc.queryForObject("select indexdef from pg_indexes where schemaname = 'console' "
                + "and indexname = 'idx_projects_deleted_at'", String.class);
        assertThat(index).contains("deleted_at").containsIgnoringCase("WHERE").containsIgnoringCase("is_deleted");
    }

    /** V8（契約 §0.5；C-10）：匯入記錄補 warnings（NOT NULL、預設 []）與 parse_options（可 NULL）。 */
    @Test
    void v8AddsTheNonNullWarningsDefaultingToAnEmptyArrayAndTheNullableParseOptions() {
        Map<String, Object> warnings = jdbc.queryForMap("select data_type, is_nullable, column_default from "
                + "information_schema.columns where table_schema = 'console' and table_name = 'import_records' "
                + "and column_name = 'warnings'");
        assertThat(warnings).containsEntry("data_type", "jsonb").containsEntry("is_nullable", "NO");
        assertThat((String) warnings.get("column_default")).startsWith("'[]'::jsonb");
        Map<String, Object> options = jdbc.queryForMap("select data_type, is_nullable, column_default from "
                + "information_schema.columns where table_schema = 'console' and table_name = 'import_records' "
                + "and column_name = 'parse_options'");
        assertThat(options).containsEntry("data_type", "jsonb").containsEntry("is_nullable", "YES")
                .containsEntry("column_default", null);
    }

    /** V7（契約 §0.5）：重播錨點、console_last_seq、token 樣本表與「未確認不重複」的 partial unique index。 */
    @Test
    void v7AddsTheEventAnchorsTheConsoleOffsetTheTokenSamplesAndTheOpenAlertUniqueIndex() {
        for (String table : List.of("review_requests", "alerts")) {
            List<String> columns = jdbc.queryForList("select column_name from information_schema.columns "
                    + "where table_schema = 'console' and table_name = ? order by column_name", String.class, table);
            assertThat(columns).as(table).contains("event_seq", "event_sub");
        }
        assertThat(jdbc.queryForObject("select column_default from information_schema.columns where "
                + "table_schema = 'console' and table_name = 'review_requests' and column_name = 'event_sub'",
                String.class)).isEqualTo("1");
        assertThat(jdbc.queryForObject("select column_default from information_schema.columns where "
                + "table_schema = 'console' and table_name = 'execution_runs' and column_name = 'console_last_seq'",
                String.class)).isEqualTo("0");
        assertThat(jdbc.queryForList("select column_name from information_schema.columns where "
                + "table_schema = 'console' and table_name = 'run_token_samples'", String.class))
                .containsExactlyInAnyOrder("run_id", "seq", "ts", "tokens_used", "delta", "context_pct", "task_id");
        String indexDef = jdbc.queryForObject("select indexdef from pg_indexes where schemaname = 'console' "
                + "and indexname = 'uq_alerts_open_rule_subject'", String.class);
        assertThat(indexDef).contains("UNIQUE").contains("project_id, rule, subject").contains("acknowledged = false");
    }

    @Test
    void seedHasAllSixCategoriesWithTheDocumentedParameterCounts() {
        Map<String, Integer> counts = new java.util.HashMap<>();
        jdbc.query("select category, count(*) as n from console.system_configs group by category",
                rs -> {
                    counts.put(rs.getString("category"), rs.getInt("n"));
                });
        // 契約附錄 C：10＋9＋10＋6＋11＋4＝50（V5 補 model.enableKernelBrain、execution 兩個 token_guard 續跑鍵、autoclaude 六個）
        assertThat(counts).containsExactlyInAnyOrderEntriesOf(Map.of(
                "model", 10, "agent", 9, "execution", 10, "monitor", 6, "autoclaude", 11, "sdd", 4));
        assertThat(counts.values().stream().mapToInt(Integer::intValue).sum()).isEqualTo(50);
    }

    @Test
    void dalBackendDefaultsToFileNotPostgresqlPerAdr001D13() {
        String value = jdbc.queryForObject(
                "select value from console.system_configs where category = 'autoclaude' and key = 'dalBackend'",
                String.class);
        String defaultValue = jdbc.queryForObject(
                "select default_value from console.system_configs where category = 'autoclaude' and key = 'dalBackend'",
                String.class);
        assertThat(value).isEqualTo("FILE");
        assertThat(defaultValue).isEqualTo("FILE");
    }

    @Test
    void onlyTheApiKeyAndTheDbDsnAreEncryptedAndBothValuesAreEmpty() {
        List<Map<String, Object>> encrypted = jdbc.queryForList(
                "select category, key, value, value_type from console.system_configs where is_encrypted "
                        + "order by category, key");
        // V5 後 autoclaude.dbDsn 是第二把加密鍵（附錄 C：model.apiKey 與 autoclaude.dbDsn 皆 ENCRYPTED）。
        assertThat(encrypted).hasSize(2);
        assertThat(encrypted.get(0)).containsEntry("category", "autoclaude").containsEntry("key", "dbDsn")
                .containsEntry("value", "").containsEntry("value_type", "ENCRYPTED");
        assertThat(encrypted.get(1)).containsEntry("category", "model").containsEntry("key", "apiKey")
                .containsEntry("value", "").containsEntry("value_type", "ENCRYPTED");
    }

    @Test
    void v5CorrectsTheThreeSeedDefaultsToTheEngineAndPollingFloorValues() {
        assertThat(setting("model", "apiUrl", "value")).isEqualTo("https://api.minimax.io/v1/text/chatcompletion_v2");
        assertThat(setting("model", "apiUrl", "default_value"))
                .isEqualTo("https://api.minimax.io/v1/text/chatcompletion_v2");
        assertThat(setting("model", "name", "default_value")).isEqualTo("MiniMax-M2.7");
        assertThat(setting("monitor", "refreshIntervalMs", "default_value")).isEqualTo("10000");
        assertThat(setting("monitor", "refreshIntervalMs", "value")).as("輪詢地板 10 秒（AR-06）").isEqualTo("10000");
    }

    @Test
    void everySeededValueAndDefaultSatisfiesItsOwnValidationRule() {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "select category, key, value, default_value, validation_rule from console.system_configs");
        assertThat(rows).hasSize(50);
        for (Map<String, Object> row : rows) {
            String label = row.get("category") + "." + row.get("key");
            assertThat(row.get("validation_rule")).as(label + " 必須有 validation_rule").isNotNull();
            java.util.regex.Pattern rule = java.util.regex.Pattern.compile((String) row.get("validation_rule"));
            // 加密鍵的預設值是空字串（沒有值），其規則也允許空字串。
            assertThat(rule.matcher((String) row.get("value")).matches()).as(label + " value").isTrue();
            assertThat(rule.matcher((String) row.get("default_value")).matches()).as(label + " default").isTrue();
        }
    }

    @Test
    void theEightKeyParametersCarryAnImpactNote() {
        for (String key : List.of("agent.defaultAutonomyLevel", "execution.globalTokenBudget",
                "execution.compactThresholdPct", "execution.haltThresholdPct", "model.apiUrl", "model.apiKey",
                "autoclaude.dalBackend", "autoclaude.claudeCommand")) {
            String[] parts = key.split("\\.");
            assertThat(setting(parts[0], parts[1], "impact_note")).as(key).isNotBlank();
        }
    }

    @Test
    void importRecordsGainParsePathAndLastParseErrorsAndSystemConfigsGainImpactNote() {
        List<String> importColumns = jdbc.queryForList(
                "select column_name from information_schema.columns where table_schema = 'console' "
                        + "and table_name = 'import_records'", String.class);
        assertThat(importColumns).contains("parse_path", "last_parse_errors");
        assertThat(jdbc.queryForObject("select data_type from information_schema.columns where table_schema = "
                + "'console' and table_name = 'import_records' and column_name = 'last_parse_errors'",
                String.class)).isEqualTo("jsonb");
        assertThat(jdbc.queryForObject("select count(*) from information_schema.columns where table_schema = "
                + "'console' and table_name = 'system_configs' and column_name = 'impact_note'",
                Integer.class)).isEqualTo(1);
    }

    private String setting(String category, String key, String column) {
        return jdbc.queryForObject("select " + column + " from console.system_configs where category = ? and key = ?",
                String.class, category, key);
    }

    @Test
    void tokenGuardSeedKeepsHaltAboveCompact() {
        int compact = Integer.parseInt(jdbc.queryForObject(
                "select value from console.system_configs where category = 'execution' and key = 'compactThresholdPct'",
                String.class));
        int halt = Integer.parseInt(jdbc.queryForObject(
                "select value from console.system_configs where category = 'execution' and key = 'haltThresholdPct'",
                String.class));
        assertThat(halt).as("NFR-SEC-05：halt 必須大於 compact").isGreaterThan(compact);
    }

    @Test
    void listIndexesAreSoftDeleteAwarePartialIndexes() {
        for (String index : List.of("idx_goals_project_id", "idx_tasks_goal_id")) {
            String def = jdbc.queryForObject(
                    "select indexdef from pg_indexes where schemaname = 'console' and indexname = ?",
                    String.class, index);
            assertThat(def).as(index).containsIgnoringCase("WHERE").containsIgnoringCase("is_deleted");
        }
    }

    @Test
    void databaseItselfRejectsSelfDependencyDuplicateEdgeAndUnknownStatus() {
        UUID project = UUID.randomUUID();
        UUID goalA = UUID.randomUUID();
        UUID goalB = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria) values (?,?,?,?)",
                project, "p", "/x", "c");
        for (UUID g : List.of(goalA, goalB)) {
            jdbc.update("insert into console.goals (id, project_id, name, pass_criteria) values (?,?,?,?)",
                    g, project, "g", "c");
        }
        try {
            assertThatThrownBy(() -> jdbc.update(
                    "insert into console.goal_dependencies (id, goal_id, depends_on_goal_id) values (?,?,?)",
                    UUID.randomUUID(), goalA, goalA)).isInstanceOf(DataIntegrityViolationException.class);

            jdbc.update("insert into console.goal_dependencies (id, goal_id, depends_on_goal_id) values (?,?,?)",
                    UUID.randomUUID(), goalA, goalB);
            assertThatThrownBy(() -> jdbc.update(
                    "insert into console.goal_dependencies (id, goal_id, depends_on_goal_id) values (?,?,?)",
                    UUID.randomUUID(), goalA, goalB)).isInstanceOf(DataIntegrityViolationException.class);

            assertThatThrownBy(() -> jdbc.update(
                    "insert into console.projects (id, name, execution_path, pass_criteria, status) values (?,?,?,?,?)",
                    UUID.randomUUID(), "bad", "/x", "c", "BOGUS")).isInstanceOf(DataIntegrityViolationException.class);
        } finally {
            // goal_dependencies 以 ON DELETE CASCADE 隨目標一起清；目標需先於專案刪除（FK）。
            jdbc.update("delete from console.goals where project_id = ?", project);
            jdbc.update("delete from console.projects where id = ?", project);
        }
    }
}
