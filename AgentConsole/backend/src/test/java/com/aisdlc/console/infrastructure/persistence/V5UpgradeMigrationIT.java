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

/**
 * V5／V6 對「已經在跑的資料庫」的升級（契約 §0.5、AR-06／AR-09）。為什麼重要：新資料庫從零遷移很容易對，
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

        // 既有匯入記錄不變；新欄位是 NULL
        Map<String, Object> record = jdbc.queryForMap("select status, source_content, parse_path, last_parse_errors "
                + "from console.import_records where id = ?", importId);
        assertThat(record).containsEntry("status", "REVIEWING").containsEntry("source_content", "# 升級前的匯入")
                .containsEntry("parse_path", null).containsEntry("last_parse_errors", null);

        // 歷史保留；V6 的審計表存在且是空的
        assertThat(jdbc.queryForObject("select count(*) from console.system_config_history where changed_by = "
                + "'old-admin'", Integer.class)).isEqualTo(1);
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log", Integer.class)).isZero();

        List<Map<String, Object>> history = jdbc.queryForList("select version, success from "
                + "console.flyway_schema_history where version is not null order by installed_rank");
        assertThat(history).extracting(row -> row.get("version")).containsExactly("1", "2", "3", "4", "5", "6");
        assertThat(history).extracting(row -> row.get("success")).containsOnly(true);
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
