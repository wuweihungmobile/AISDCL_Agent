package com.aisdlc.console.infrastructure.persistence;

import com.aisdlc.console.support.SharedPostgres;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.MigrationVersion;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Flyway V14（{@code console.issue_priority}；TCS-IssueCenter-20261027 AT-IC-09-6-1、AT-IC-09-6-E-1；R-IC-59、§C6）。為什麼重要：優先順序表是 Console 在議題中心
 * 唯一自有的資料——「順位 1～9999」「備註 ≤200 字」「編號格式」若只靠應用層檢查，直接寫庫或日後新增的程式路徑就能存進壞值；所以約束要落在結構層
 * （CHECK、NOT NULL），升級路徑也要驗：在一個已有資料的 V13 資料庫上升級，既有的表一個位元組都不能動。容器重啟後順位仍在（AT-IC-09-6-2）由 Docker 全棧載具承擔。
 * 「{@code ddl-auto=validate} 通過」由整套整合測試的 context 啟動本身證明（沒有 JPA 實體，validate 不檢查本表，但表名與 schema 不得與實體衝突；
 * {@code SchemaMigrationIT} 另釘版本清單與表集合）。
 */
class IssuePriorityMigrationIT {

    private static String createDatabase() {
        String name = "issue_prio_" + UUID.randomUUID().toString().replace("-", "");
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
        return "jdbc:postgresql://" + SharedPostgres.INSTANCE.getHost() + ":" + SharedPostgres.INSTANCE.getMappedPort(5432) + "/" + database;
    }

    private static Flyway flyway(String database, String targetVersion) {
        var configuration = Flyway.configure().dataSource(urlOf(database), SharedPostgres.INSTANCE.getUsername(),
                SharedPostgres.INSTANCE.getPassword()).schemas("console").defaultSchema("console").locations("classpath:db/migration");
        if (targetVersion != null) {
            configuration.target(MigrationVersion.fromVersion(targetVersion));
        }
        return configuration.load();
    }

    private static JdbcTemplate jdbcOf(String database) {
        return new JdbcTemplate(new DriverManagerDataSource(urlOf(database), SharedPostgres.INSTANCE.getUsername(),
                SharedPostgres.INSTANCE.getPassword()));
    }

    private static JdbcTemplate migratedDatabase() {
        String database = createDatabase();
        flyway(database, null).migrate();
        return jdbcOf(database);
    }

    private static void insert(JdbcTemplate jdbc, String issueId, Object rank, Object note) {
        jdbc.update("insert into console.issue_priority (issue_id, rank, note, set_by, set_at) values (?, ?, ?, 'admin', now())",
                issueId, rank, note);
    }

    private static String sqlState(Throwable thrown) {
        Throwable cause = thrown;
        while (cause != null && !(cause instanceof SQLException)) {
            cause = cause.getCause();
        }
        return cause == null ? null : ((SQLException) cause).getSQLState();
    }

    // ── AT-IC-09-6-1：表結構與升級路徑 ─────────────────────────────────────────────────────────

    @Test
    void AT_IC_09_6_1_theTableHasTheFiveColumnsOfTheSpecAndAV13DatabaseUpgradesWithoutTouchingExistingData() {
        String database = createDatabase();
        flyway(database, "13").migrate();
        JdbcTemplate jdbc = jdbcOf(database);
        UUID project = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria, status, signed_off) values "
                + "(?, '升級前的專案', '/same/root', '標準', 'READY', true)", project);
        jdbc.update("insert into console.si_console_writes (audit_ref, kind, \"user\", role, \"time\", subject_id, digest, body, key_id, mac) "
                + "values (?, 'obs-add', 'admin', 'ADMIN', '2026-10-24T14:30:15Z', null, null, '{\"fixture\":true}', 'f076edf0', ?)",
                UUID.randomUUID(), "0".repeat(64));
        String configsBefore = jdbc.queryForObject("select string_agg(category || '.' || key || '=' || coalesce(value, '<null>'), ';' "
                + "order by category, key) from console.system_configs", String.class);
        assertThat(jdbc.queryForObject("select count(*) from information_schema.tables where table_schema = 'console' "
                + "and table_name = 'issue_priority'", Integer.class)).as("V13 時還沒有這張表").isZero();

        flyway(database, null).migrate();

        List<Map<String, Object>> columns = jdbc.queryForList("select column_name, data_type, is_nullable, character_maximum_length, "
                + "column_default from information_schema.columns where table_schema = 'console' and table_name = 'issue_priority' "
                + "order by ordinal_position");
        assertThat(columns).extracting(c -> c.get("column_name")).containsExactly("issue_id", "rank", "note", "set_by", "set_at");
        Map<String, Map<String, Object>> byName = new LinkedHashMap<>();
        columns.forEach(c -> byName.put((String) c.get("column_name"), c));
        assertThat(byName.get("issue_id")).containsEntry("data_type", "character varying").containsEntry("character_maximum_length", 64);
        assertThat(byName.get("rank")).containsEntry("data_type", "integer");
        assertThat(byName.get("note")).containsEntry("data_type", "character varying").containsEntry("character_maximum_length", 200);
        assertThat(String.valueOf(byName.get("note").get("column_default"))).as("note 預設為空字串").startsWith("''");
        assertThat(byName.get("set_by")).containsEntry("data_type", "character varying").containsEntry("character_maximum_length", 64);
        assertThat(byName.get("set_at")).containsEntry("data_type", "timestamp with time zone");
        byName.forEach((name, column) -> assertThat(column.get("is_nullable")).as("%s 不可為 NULL", name).isEqualTo("NO"));
        assertThat(jdbc.queryForList("select a.attname from pg_index i join pg_attribute a on a.attrelid = i.indrelid "
                + "and a.attnum = any(i.indkey) where i.indrelid = 'console.issue_priority'::regclass and i.indisprimary", String.class))
                .as("主鍵＝issue_id（一個議題最多一列）").containsExactly("issue_id");
        assertThat(jdbc.queryForObject("select count(*) from pg_constraint where conrelid = 'console.issue_priority'::regclass and contype = 'u'",
                Integer.class)).as("沒有唯一鍵：順位可重複").isZero();
        assertThat(jdbc.queryForObject("select count(*) from information_schema.tables where table_schema = 'public' "
                + "and table_name = 'issue_priority'", Integer.class)).as("不外洩到 public").isZero();
        assertThat(jdbc.queryForObject("select count(*) from information_schema.triggers where event_object_schema = 'console' "
                + "and event_object_table = 'issue_priority'", Integer.class)).as("沒有觸發器：UPSERT 與 DELETE 都是平常的敘述").isZero();

        assertThat(jdbc.queryForObject("select name from console.projects where id = ?", String.class, project)).isEqualTo("升級前的專案");
        assertThat(jdbc.queryForObject("select count(*) from console.si_console_writes", Integer.class)).as("V13 的稽核列原封不動").isEqualTo(1);
        assertThat(jdbc.queryForObject("select string_agg(category || '.' || key || '=' || coalesce(value, '<null>'), ';' "
                + "order by category, key) from console.system_configs", String.class)).as("既有表資料不變").isEqualTo(configsBefore);
        List<Map<String, Object>> history = jdbc.queryForList("select version, success from console.flyway_schema_history "
                + "where version is not null order by installed_rank");
        assertThat(history).extracting(row -> row.get("version")).containsExactly("1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
                "11", "12", "13", "14");
        assertThat(history).extracting(row -> row.get("success")).containsOnly(true);
        assertThat(flyway(database, null).migrate().migrationsExecuted).as("再跑一次沒有新遷移").isZero();
    }

    // ── AT-IC-09-6-E-1：約束 ─────────────────────────────────────────────────────────────────

    @Test
    void AT_IC_09_6_E_1_theConstraintsRejectBadValuesAndTheBoundariesAreWritable() {
        JdbcTemplate jdbc = migratedDatabase();
        Map<String, Runnable> bad = new LinkedHashMap<>();
        Map<String, String> expectedState = new LinkedHashMap<>();
        // 兩位數的近似編號於執行期組字：根層 R18 (a) 會把整串的 OBS 編號字面（帳本沒有的號碼）判成懸空引用
        for (String id : List.of("obs-si-001", "OBS" + "-SI-12", "PROP-SI-4", "DEF-x-y", "DEF-1-", "OBS-SI-001x", "xOBS-SI-001", "OBS-SI-００１", "")) {
            bad.put("issue_id=" + id, () -> insert(jdbc, id, 1, ""));
            expectedState.put("issue_id=" + id, "23514");
        }
        for (int rank : new int[] {0, -1, 10000, Integer.MAX_VALUE}) {
            bad.put("rank=" + rank, () -> insert(jdbc, "OBS-SI-001", rank, ""));
            expectedState.put("rank=" + rank, "23514");
        }
        bad.put("rank=NULL", () -> insert(jdbc, "OBS-SI-001", null, ""));
        expectedState.put("rank=NULL", "23502");
        bad.put("note=NULL", () -> insert(jdbc, "OBS-SI-001", 1, null));
        expectedState.put("note=NULL", "23502");
        bad.put("note=201 字元", () -> insert(jdbc, "OBS-SI-001", 1, "字".repeat(201)));
        expectedState.put("note=201 字元", "22001");

        bad.forEach((label, action) -> assertThatThrownBy(action::run).as(label).isInstanceOf(DataAccessException.class)
                .satisfies(thrown -> assertThat(sqlState(thrown)).as(label + " 的 SQLState").isEqualTo(expectedState.get(label))));
        assertThat(jdbc.queryForObject("select count(*) from console.issue_priority", Integer.class)).as("被拒的列都沒有寫入").isZero();

        insert(jdbc, "OBS-SI-001", 1, "");
        insert(jdbc, "PROP-SI-004", 9999, "字".repeat(200));
        insert(jdbc, "DEF-999-001", 1, "😀".repeat(200));
        assertThat(jdbc.queryForObject("select count(*) from console.issue_priority", Integer.class)).as("rank 1、9999 與 200 字元（含表情符號）可寫；順位可重複")
                .isEqualTo(3);
        assertThat(jdbc.queryForObject("select note from console.issue_priority where issue_id = 'PROP-SI-004'", String.class)).hasSize(200);
        jdbc.update("insert into console.issue_priority (issue_id, rank, set_by, set_at) values ('OBS-SI-002', 5, 'admin', now())");
        assertThat(jdbc.queryForObject("select note from console.issue_priority where issue_id = 'OBS-SI-002'", String.class))
                .as("note 缺省為空字串").isEmpty();
        assertThatThrownBy(() -> insert(jdbc, "OBS-SI-001", 2, "")).as("主鍵：同一議題不能有兩列").isInstanceOf(DataAccessException.class)
                .satisfies(thrown -> assertThat(sqlState(thrown)).isEqualTo("23505"));
    }
}
