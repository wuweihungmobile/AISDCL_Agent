package com.aisdlc.console.infrastructure.persistence;

import com.aisdlc.console.support.SharedPostgres;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.MigrationVersion;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * V5～V9 對「已經在跑的資料庫」的升級（契約 §0.5、AR-06／AR-09）。為什麼重要：新資料庫從零遷移很容易對，
 * 真正會出事的是升級——V5 的「預設值校正」只能在值仍等於舊預設時才改，絕不能蓋掉管理員改過的值；
 * 新增的欄位必須讓既有匯入記錄原封不動；新鍵不能與既有鍵重複。這裡在一個獨立資料庫上先遷到 V4、塞入「管理員改過的」資料，
 * 再遷到最新版，逐項核對。
 */
class V5UpgradeMigrationIT {

    private static String createDatabase() {
        String name = "v5_upgrade_" + UUID.randomUUID().toString().replace("-", "");
        try (Connection admin = DriverManager.getConnection(SharedPostgres.INSTANCE.getJdbcUrl(),
                SharedPostgres.INSTANCE.getUsername(), SharedPostgres.INSTANCE.getPassword());
             Statement statement = admin.createStatement()) {
            statement.execute("create database " + name);
        } catch (SQLException e) {
            throw new IllegalStateException("無法建立測試資料庫", e);
        }
        return name;
    }

    private static String urlOf(String database) {
        return "jdbc:postgresql://" + SharedPostgres.INSTANCE.getHost() + ":"
                + SharedPostgres.INSTANCE.getMappedPort(5432) + "/" + database;
    }

    private static Flyway flyway(String database, String targetVersion) {
        var configuration = Flyway.configure()
                .dataSource(urlOf(database), SharedPostgres.INSTANCE.getUsername(),
                        SharedPostgres.INSTANCE.getPassword())
                .schemas("console").defaultSchema("console").locations("classpath:db/migration");
        if (targetVersion != null) {
            configuration.target(MigrationVersion.fromVersion(targetVersion));
        }
        return configuration.load();
    }

    private static JdbcTemplate jdbcOf(String database) {
        return new JdbcTemplate(new DriverManagerDataSource(urlOf(database), SharedPostgres.INSTANCE.getUsername(),
                SharedPostgres.INSTANCE.getPassword()));
    }

    private static String value(JdbcTemplate jdbc, String category, String key, String column) {
        return jdbc.queryForObject("select " + column + " from console.system_configs where category = ? and key = ?",
                String.class, category, key);
    }

    @Test
    void anAdministratorsChangedValuesSurviveTheUpgradeWhileUntouchedOldDefaultsAreCorrected() {
        String database = createDatabase();
        flyway(database, "4").migrate();
        JdbcTemplate jdbc = jdbcOf(database);
        assertThat(jdbc.queryForObject("select count(*) from console.system_configs", Integer.class)).isEqualTo(41);

        // 升級前：管理員改過三個鍵；另有一筆既有的匯入記錄與一筆修改歷史
        jdbc.update("update console.system_configs set value = 'https://proxy.example.org/v1/chat' "
                + "where category = 'model' and key = 'apiUrl'");
        jdbc.update("update console.system_configs set value = '5000' where category = 'monitor' "
                + "and key = 'refreshIntervalMs'");
        jdbc.update("update console.system_configs set value = '70' where category = 'execution' "
                + "and key = 'compactThresholdPct'");
        jdbc.update("insert into console.system_config_history (config_id, old_value, new_value, changed_by) "
                + "select id, '3000', '5000', 'old-admin' from console.system_configs where key = 'refreshIntervalMs'");
        UUID importId = UUID.randomUUID();
        jdbc.update("insert into console.import_records (id, source_type, source_content, status) values "
                + "(?, 'MARKDOWN', '# 升級前的匯入', 'REVIEWING')", importId);

        flyway(database, null).migrate();

        // 管理員改過的值原封不動；舊預設（value 仍等於舊 default）才被校正
        assertThat(value(jdbc, "model", "apiUrl", "value")).isEqualTo("https://proxy.example.org/v1/chat");
        assertThat(value(jdbc, "model", "apiUrl", "default_value"))
                .isEqualTo("https://api.minimax.io/v1/text/chatcompletion_v2");
        assertThat(value(jdbc, "model", "name", "value")).isEqualTo("MiniMax-M2.7");
        assertThat(value(jdbc, "model", "name", "default_value")).isEqualTo("MiniMax-M2.7");
        assertThat(value(jdbc, "monitor", "refreshIntervalMs", "value")).as("管理員改成 5000：不被重設為 10000")
                .isEqualTo("5000");
        assertThat(value(jdbc, "monitor", "refreshIntervalMs", "default_value")).isEqualTo("10000");
        assertThat(value(jdbc, "execution", "compactThresholdPct", "value")).isEqualTo("70");

        // 九個新鍵、共 50 個鍵，且沒有重複
        assertThat(jdbc.queryForObject("select count(*) from console.system_configs", Integer.class)).isEqualTo(50);
        assertThat(jdbc.queryForObject("select count(distinct (category, key)) from console.system_configs",
                Integer.class)).isEqualTo(50);
        assertThat(jdbc.queryForList("select key from console.system_configs where category = 'autoclaude' "
                + "and key in ('claudeCommand','claudeExtraArgs','claudeContinueFlag','claudeEncoding','dbDsn',"
                + "'dualReadResolution')", String.class)).hasSize(6);
        assertThat(value(jdbc, "execution", "autoResume", "value")).isEqualTo("true");
        assertThat(value(jdbc, "execution", "maxAutoResumes", "value")).isEqualTo("10");
        assertThat(value(jdbc, "model", "enableKernelBrain", "value")).isEqualTo("false");
        assertThat(jdbc.queryForObject("select is_encrypted from console.system_configs where category = "
                + "'autoclaude' and key = 'dbDsn'", Boolean.class)).isTrue();

        // 規則與影響提示補齊：全部 50 個鍵
        assertThat(jdbc.queryForObject("select count(*) from console.system_configs where validation_rule is null",
                Integer.class)).isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.system_configs where impact_note is null",
                Integer.class)).isZero();

        // 既有匯入記錄不變；新欄位是 NULL（V8 的 warnings 是 NOT NULL，既有列取預設 []，parse_options 為 NULL）
        Map<String, Object> record = jdbc.queryForMap("select status, source_content, parse_path, last_parse_errors, "
                + "warnings::text as warnings, parse_options from console.import_records where id = ?", importId);
        assertThat(record).containsEntry("status", "REVIEWING").containsEntry("source_content", "# 升級前的匯入")
                .containsEntry("parse_path", null).containsEntry("last_parse_errors", null)
                .containsEntry("warnings", "[]").containsEntry("parse_options", null);

        // 歷史保留；V6 的審計表存在且是空的
        assertThat(jdbc.queryForObject("select count(*) from console.system_config_history where changed_by = "
                + "'old-admin'", Integer.class)).isEqualTo(1);
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log", Integer.class)).isZero();

        List<Map<String, Object>> history = jdbc.queryForList("select version, success from "
                + "console.flyway_schema_history where version is not null order by installed_rank");
        assertThat(history).extracting(row -> row.get("version"))
                .containsExactly("1", "2", "3", "4", "5", "6", "7", "8", "9");
        assertThat(history).extracting(row -> row.get("success")).containsOnly(true);
    }

    /**
     * V9（C-3）對「升級前就已軟刪」的資料：真正的刪除時間已不可考，以 updated_at 近似；專案刪除連帶軟刪的目標與任務與專案共用同一個
     * now，所以近似值仍相等（復原靠它辨識）；單獨先刪除的目標則是另一個時間；存活的列不受影響；status_before_delete 一律 NULL。
     */
    @Test
    void rowsSoftDeletedBeforeV9GetTheirUpdatedAtAsDeletedAtAndLiveRowsStayNull() {
        String database = createDatabase();
        flyway(database, "8").migrate();
        JdbcTemplate jdbc = jdbcOf(database);
        UUID liveProject = UUID.randomUUID();
        UUID deletedProject = UUID.randomUUID();
        UUID cascadedGoal = UUID.randomUUID();
        UUID earlierGoal = UUID.randomUUID();
        UUID cascadedTask = UUID.randomUUID();
        UUID liveGoal = UUID.randomUUID();
        UUID liveTask = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria) values (?, '存活', '/a', 'c')",
                liveProject);
        jdbc.update("insert into console.goals (id, project_id, name, pass_criteria) values (?, ?, '存活目標', 'c')",
                liveGoal, liveProject);
        jdbc.update("insert into console.tasks (id, goal_id, name, pass_criteria) values (?, ?, '存活任務', 'c')",
                liveTask, liveGoal);
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria, status, is_deleted, "
                + "updated_at) values (?, '已刪', '/b', 'c', 'ARCHIVED', true, '2026-09-01T08:00:00Z')", deletedProject);
        jdbc.update("insert into console.goals (id, project_id, name, pass_criteria, is_deleted, updated_at) values "
                + "(?, ?, '連帶', 'c', true, '2026-09-01T08:00:00Z')", cascadedGoal, deletedProject);
        jdbc.update("insert into console.goals (id, project_id, name, pass_criteria, is_deleted, updated_at) values "
                + "(?, ?, '更早單獨刪除', 'c', true, '2026-08-20T08:00:00Z')", earlierGoal, deletedProject);
        jdbc.update("insert into console.tasks (id, goal_id, name, pass_criteria, is_deleted, updated_at) values "
                + "(?, ?, '連帶任務', 'c', true, '2026-09-01T08:00:00Z')", cascadedTask, cascadedGoal);

        flyway(database, null).migrate();

        assertThat(jdbc.queryForObject("select deleted_at = updated_at from console.projects where id = ?",
                Boolean.class, deletedProject)).isTrue();
        assertThat(jdbc.queryForObject("select deleted_at = updated_at from console.goals where id = ?", Boolean.class,
                cascadedGoal)).isTrue();
        assertThat(jdbc.queryForObject("select deleted_at = updated_at from console.tasks where id = ?", Boolean.class,
                cascadedTask)).isTrue();
        assertThat(jdbc.queryForObject("select (select deleted_at from console.projects where id = ?) = "
                + "(select deleted_at from console.goals where id = ?)", Boolean.class, deletedProject, cascadedGoal))
                .as("連帶軟刪的目標與專案的 deleted_at 相等：復原據此辨識").isTrue();
        assertThat(jdbc.queryForObject("select (select deleted_at from console.projects where id = ?) = "
                + "(select deleted_at from console.goals where id = ?)", Boolean.class, deletedProject, earlierGoal))
                .as("更早單獨刪除的目標是另一個時間：復原時維持已刪除").isFalse();
        assertThat(jdbc.queryForObject("select status_before_delete from console.projects where id = ?", String.class,
                deletedProject)).isNull();
        assertThat(jdbc.queryForObject("select count(*) from console.projects where deleted_at is not null "
                + "and is_deleted = false", Integer.class)).as("存活的專案不受影響").isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.goals where id = ? and deleted_at is null",
                Integer.class, liveGoal)).isEqualTo(1);
        assertThat(jdbc.queryForObject("select count(*) from console.tasks where id = ? and deleted_at is null",
                Integer.class, liveTask)).isEqualTo(1);
    }

    @Test
    void existingRunsReviewItemsAndAlertsSurviveTheV7UpgradeWithTheDocumentedDefaults() {
        String database = createDatabase();
        flyway(database, "6").migrate();
        JdbcTemplate jdbc = jdbcOf(database);
        UUID project = UUID.randomUUID();
        UUID goal = UUID.randomUUID();
        UUID task = UUID.randomUUID();
        UUID run = UUID.randomUUID();
        UUID review = UUID.randomUUID();
        UUID alert = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria) values (?, '升級前的專案', "
                + "'/p', 'c')", project);
        jdbc.update("insert into console.goals (id, project_id, name, pass_criteria) values (?, ?, '目標', 'c')",
                goal, project);
        jdbc.update("insert into console.tasks (id, goal_id, name, pass_criteria) values (?, ?, '任務', 'c')", task, goal);
        jdbc.update("insert into console.execution_runs (id, project_id, run_number, status, autonomy_level, scope, "
                + "total_tokens_used) values (?, ?, 1, 'COMPLETED', 4, '{\"mode\":\"ALL\"}'::jsonb, 1240)", run, project);
        jdbc.update("insert into console.review_requests (id, run_id, task_id, goal_id, kind, status, reason) values "
                + "(?, ?, ?, ?, 'TASK_CONFIRM', 'APPROVED', '升級前的審核')", review, run, task, goal);
        jdbc.update("insert into console.alerts (id, project_id, run_id, rule, severity, subject, message) values "
                + "(?, ?, ?, 'HIGH_RETRY_RATE', 'WARNING', 'run', '升級前的告警')", alert, project, run);

        flyway(database, null).migrate();

        // 既有資料列原封不動；V7 新欄位取契約 §0.5 載明的預設（重播錨點 0／1、已處理到的事件 seq 0）
        assertThat(jdbc.queryForMap("select status, total_tokens_used, console_last_seq from console.execution_runs "
                + "where id = ?", run)).containsEntry("status", "COMPLETED").containsEntry("total_tokens_used", 1240L)
                .containsEntry("console_last_seq", 0);
        assertThat(jdbc.queryForMap("select reason, status, event_seq, event_sub from console.review_requests "
                + "where id = ?", review)).containsEntry("reason", "升級前的審核").containsEntry("status", "APPROVED")
                .containsEntry("event_seq", 0).containsEntry("event_sub", 1);
        assertThat(jdbc.queryForMap("select message, acknowledged, event_seq, event_sub from console.alerts "
                + "where id = ?", alert)).containsEntry("message", "升級前的告警").containsEntry("acknowledged", false)
                .containsEntry("event_seq", 0).containsEntry("event_sub", 1);
        assertThat(jdbc.queryForObject("select count(*) from console.run_token_samples", Integer.class)).isZero();

        // 「同一規則＋對象在確認前不重複」的部分唯一索引對升級後的資料同樣生效；確認之後才可再產生
        String duplicate = "insert into console.alerts (project_id, run_id, rule, severity, subject, message) values "
                + "(?, ?, 'HIGH_RETRY_RATE', 'WARNING', 'run', '重複')";
        assertThatThrownBy(() -> jdbc.update(duplicate, project, run)).hasMessageContaining("uq_alerts_open_rule_subject");
        jdbc.update("update console.alerts set acknowledged = true where id = ?", alert);
        assertThat(jdbc.update(duplicate, project, run)).isEqualTo(1);
    }

    @Test
    void aDatabaseThatStillHasEveryOldDefaultGetsTheCorrectedDefaultsAsItsValuesToo() {
        String database = createDatabase();
        flyway(database, "4").migrate();
        JdbcTemplate jdbc = jdbcOf(database);
        assertThat(value(jdbc, "model", "apiUrl", "value")).isEqualTo("https://api.anthropic.com");
        assertThat(value(jdbc, "monitor", "refreshIntervalMs", "value")).isEqualTo("3000");

        flyway(database, null).migrate();

        assertThat(value(jdbc, "model", "apiUrl", "value")).isEqualTo("https://api.minimax.io/v1/text/chatcompletion_v2");
        assertThat(value(jdbc, "model", "name", "value")).isEqualTo("MiniMax-M2.7");
        assertThat(value(jdbc, "monitor", "refreshIntervalMs", "value")).isEqualTo("10000");
        assertThat(jdbc.queryForObject("select count(*) from console.system_configs where value is distinct from "
                + "coalesce(default_value, '')", Integer.class)).as("乾淨升級後每個鍵的 value 都等於預設").isZero();
    }

    @Test
    void theUpgradeIsIdempotentAndAFreshDatabaseReachesTheSameState() {
        String upgraded = createDatabase();
        flyway(upgraded, "4").migrate();
        flyway(upgraded, null).migrate();
        assertThat(flyway(upgraded, null).migrate().migrationsExecuted).as("再跑一次沒有新遷移").isZero();

        String fresh = createDatabase();
        flyway(fresh, null).migrate();

        String query = "select category || '.' || key || '=' || coalesce(value, '<null>') || '|' || "
                + "coalesce(default_value, '<null>') || '|' || coalesce(validation_rule, '<null>') || '|' || "
                + "coalesce(impact_note, '<null>') || '|' || value_type from console.system_configs "
                + "order by category, key";
        assertThat(jdbcOf(upgraded).queryForList(query, String.class))
                .as("從 V4 升級與從零遷移，50 個鍵的狀態逐字相同").isEqualTo(jdbcOf(fresh).queryForList(query, String.class));
    }
}
