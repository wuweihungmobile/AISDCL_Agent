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
 * Flyway 遷移（V1～V4）與 JPA schema 驗證（ADR-001 D5）。
 *
 * <p>能啟動本 context 本身就代表 {@code ddl-auto=validate} 通過（12 個實體與 Flyway 建出的表一致）；
 * 這裡另外把「為什麼重要」寫成斷言：DDL 必須由 Flyway 擁有、表必須全在 console schema（不與 AutoClaude 的
 * public.checkpoints 等同名表撞名）、種子要齊、關鍵 CHECK／UNIQUE／partial index 要真的存在。
 */
class SchemaMigrationIT extends AbstractIntegrationTest {

    private static final Set<String> CONSOLE_TABLES = Set.of(
            "projects", "goals", "goal_dependencies", "tasks", "execution_runs", "execution_steps",
            "checkpoints", "import_records", "system_configs", "system_config_history",
            "review_requests", "alerts");

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
    void allTwelveTablesLiveInTheConsoleSchemaAndNoneLeakIntoPublic() {
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
    void flywayAppliedVersionsOneToFourSuccessfully() {
        List<Map<String, Object>> history = jdbc.queryForList(
                "select version, success from console.flyway_schema_history where version is not null "
                        + "order by installed_rank");
        assertThat(history).extracting(row -> row.get("version")).containsExactly("1", "2", "3", "4");
        assertThat(history).allSatisfy(row -> assertThat(row.get("success")).isEqualTo(true));
    }

    @Test
    void seedHasAllSixCategoriesWithTheDocumentedParameterCounts() {
        Map<String, Integer> counts = new java.util.HashMap<>();
        jdbc.query("select category, count(*) as n from console.system_configs group by category",
                rs -> {
                    counts.put(rs.getString("category"), rs.getInt("n"));
                });
        assertThat(counts).containsExactlyInAnyOrderEntriesOf(Map.of(
                "model", 9, "agent", 9, "execution", 8, "monitor", 6, "autoclaude", 5, "sdd", 4));
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
    void onlyTheApiKeyIsEncryptedAndItsValueIsEmpty() {
        List<Map<String, Object>> encrypted = jdbc.queryForList(
                "select category, key, value, value_type from console.system_configs where is_encrypted");
        assertThat(encrypted).hasSize(1);
        assertThat(encrypted.get(0)).containsEntry("category", "model").containsEntry("key", "apiKey")
                .containsEntry("value", "").containsEntry("value_type", "ENCRYPTED");
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
