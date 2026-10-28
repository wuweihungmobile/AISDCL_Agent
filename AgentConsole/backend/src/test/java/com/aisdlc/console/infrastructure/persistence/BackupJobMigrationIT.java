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
 * Flyway V15（{@code console.backup_jobs}；TCS-SysAdminBackup-20261027 AT-BK-06-4-3、AT-BK-10-1-1、AT-BK-10-1-2；R-BK-32、R-BK-55、§C5）。為什麼重要：
 * 手動備份的「單工」最終靠資料庫的<b>部分唯一索引</b>（至多一個 QUEUED／RUNNING）擋下併發的第二個——應用層的檢查只是友善的 409，兩個同時通過檢查的 POST 由索引決勝；
 * 索引條件多漏一個狀態，就會有兩個備份同時跑（共用同一把維護鎖與暫存空間）；少一個，就會有「永遠不結束的工作」把按鈕鎖死。欄位與 CHECK 也要落在結構層
 * （{@code type} 只有 full／diff／verify、{@code status} 六值、{@code detail} 非空預設），直接寫庫或日後新增的程式路徑才存不進壞值；升級路徑要在已有資料的 V14 資料庫上驗，
 * 既有的表一個位元組都不能動。{@code ddl-auto=validate} 通過由整套整合測試的 context 啟動本身證明（沒有 JPA 實體，validate 不檢查本表）。
 */
class BackupJobMigrationIT {

    private static String createDatabase() {
        String name = "backup_jobs_" + UUID.randomUUID().toString().replace("-", "");
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

    private static void insert(JdbcTemplate jdbc, String type, String status) {
        jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at) values (?, ?, ?, 'admin', now())",
                UUID.randomUUID(), type, status);
    }

    private static String sqlState(Throwable thrown) {
        Throwable cause = thrown;
        while (cause != null && !(cause instanceof SQLException)) {
            cause = cause.getCause();
        }
        return cause == null ? null : ((SQLException) cause).getSQLState();
    }

    /** 既有表（除 backup_jobs 外）的欄位與約束快照：升級前後逐字相同＝零變動。 */
    private static String snapshotOfExistingTables(JdbcTemplate jdbc) {
        String columns = jdbc.queryForObject("select string_agg(table_name || '.' || column_name || ':' || data_type || ':' || is_nullable || ':' "
                + "|| coalesce(character_maximum_length::text, '-') || ':' || coalesce(column_default, '-'), ';' order by table_name, ordinal_position) "
                + "from information_schema.columns where table_schema = 'console' and table_name <> 'backup_jobs'", String.class);
        String constraints = jdbc.queryForObject("select string_agg(conrelid::regclass::text || '.' || conname || ':' || pg_get_constraintdef(oid), ';' "
                + "order by conrelid::regclass::text, conname) from pg_constraint where connamespace = 'console'::regnamespace "
                + "and conrelid::regclass::text <> 'console.backup_jobs'", String.class);
        return columns + "|" + constraints;
    }

    // ── AT-BK-10-1-1：表結構與升級路徑 ─────────────────────────────────────────────────────────

    @Test
    void AT_BK_10_1_1_theTableHasTheColumnsOfThePrdAndAV14DatabaseUpgradesWithoutTouchingExistingTables() {
        String database = createDatabase();
        flyway(database, "14").migrate();
        JdbcTemplate jdbc = jdbcOf(database);
        UUID project = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria, status, signed_off) values "
                + "(?, '升級前的專案', '/same/root', '標準', 'READY', true)", project);
        String before = snapshotOfExistingTables(jdbc);
        assertThat(jdbc.queryForObject("select count(*) from information_schema.tables where table_schema = 'console' and table_name = 'backup_jobs'",
                Integer.class)).as("V14 時還沒有這張表").isZero();

        flyway(database, null).migrate();

        List<Map<String, Object>> columns = jdbc.queryForList("select column_name, data_type, is_nullable, character_maximum_length, column_default "
                + "from information_schema.columns where table_schema = 'console' and table_name = 'backup_jobs' order by ordinal_position");
        assertThat(columns).extracting(c -> c.get("column_name")).containsExactly("id", "type", "status", "requested_by", "requested_at",
                "started_at", "finished_at", "exit_code", "reason", "detail");
        Map<String, Map<String, Object>> byName = new LinkedHashMap<>();
        columns.forEach(c -> byName.put((String) c.get("column_name"), c));
        assertThat(byName.get("id")).containsEntry("data_type", "uuid").containsEntry("is_nullable", "NO");
        assertThat(byName.get("type")).containsEntry("data_type", "character varying").containsEntry("character_maximum_length", 10).containsEntry("is_nullable", "NO");
        assertThat(byName.get("status")).containsEntry("character_maximum_length", 12).containsEntry("is_nullable", "NO");
        assertThat(byName.get("requested_by")).containsEntry("character_maximum_length", 100).containsEntry("is_nullable", "NO");
        assertThat(byName.get("requested_at")).containsEntry("data_type", "timestamp with time zone").containsEntry("is_nullable", "NO");
        for (String nullable : List.of("started_at", "finished_at")) {
            assertThat(byName.get(nullable)).as(nullable).containsEntry("data_type", "timestamp with time zone").containsEntry("is_nullable", "YES");
        }
        assertThat(byName.get("exit_code")).containsEntry("data_type", "integer").containsEntry("is_nullable", "YES");
        assertThat(byName.get("reason")).containsEntry("character_maximum_length", 30).containsEntry("is_nullable", "YES");
        assertThat(byName.get("detail")).containsEntry("character_maximum_length", 2000).containsEntry("is_nullable", "NO");
        assertThat(String.valueOf(byName.get("detail").get("column_default"))).as("detail 預設為空字串").startsWith("''");

        assertThat(jdbc.queryForList("select a.attname from pg_index i join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey) "
                + "where i.indrelid = 'console.backup_jobs'::regclass and i.indisprimary", String.class)).as("主鍵＝id").containsExactly("id");
        String unique = jdbc.queryForObject("select indexdef from pg_indexes where schemaname = 'console' and indexname = 'ux_backup_jobs_one_active'",
                String.class);
        assertThat(unique).as("部分唯一索引：運算式 (1)、條件 status IN ('QUEUED','RUNNING')").contains("CREATE UNIQUE INDEX").contains("((1))")
                .contains("WHERE").contains("QUEUED").contains("RUNNING");
        assertThat(jdbc.queryForObject("select indexdef from pg_indexes where schemaname = 'console' and indexname = 'idx_backup_jobs_requested_at'",
                String.class)).contains("requested_at DESC");

        // CHECK：type 只有 full／diff／verify，status 六值；其餘（incr、DONE、大小寫不符）被拒
        for (String badType : List.of("incr", "dump", "FULL", "")) {
            assertThatThrownBy(() -> insert(jdbc, badType, "SUCCEEDED")).as("type=" + badType).isInstanceOf(DataAccessException.class)
                    .satisfies(thrown -> assertThat(sqlState(thrown)).isEqualTo("23514"));
        }
        for (String badStatus : List.of("DONE", "queued", "CANCELLED", "")) {
            assertThatThrownBy(() -> insert(jdbc, "full", badStatus)).as("status=" + badStatus).isInstanceOf(DataAccessException.class)
                    .satisfies(thrown -> assertThat(sqlState(thrown)).isEqualTo("23514"));
        }
        for (String type : List.of("full", "diff", "verify")) {
            insert(jdbc, type, "SUCCEEDED");
        }
        assertThat(jdbc.queryForObject("select detail from console.backup_jobs where type = 'full'", String.class)).as("detail 缺省為空字串").isEmpty();
        assertThatThrownBy(() -> jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at, detail) "
                + "values (?, 'full', 'FAILED', 'admin', now(), ?)", UUID.randomUUID(), "x".repeat(2001))).as("detail 至多 2000 字元")
                .isInstanceOf(DataAccessException.class).satisfies(thrown -> assertThat(sqlState(thrown)).isEqualTo("22001"));

        assertThat(jdbc.queryForObject("select name from console.projects where id = ?", String.class, project)).isEqualTo("升級前的專案");
        assertThat(snapshotOfExistingTables(jdbc)).as("既有各表的欄位與約束 V15 前後逐項相同（零變動）").isEqualTo(before);
    }

    // ── AT-BK-10-1-2：版本與冪等 ────────────────────────────────────────────────────────────────

    @Test
    void AT_BK_10_1_2_theMigrationHistoryIsExactlyOneToFifteenAndRunningItAgainDoesNothing() {
        String database = createDatabase();
        flyway(database, null).migrate();
        JdbcTemplate jdbc = jdbcOf(database);

        List<Map<String, Object>> history = jdbc.queryForList("select version, success from console.flyway_schema_history "
                + "where version is not null order by installed_rank");
        assertThat(history).extracting(row -> row.get("version")).containsExactly("1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
                "11", "12", "13", "14", "15");
        assertThat(history).extracting(row -> row.get("success")).containsOnly(true);
        assertThat(flyway(database, null).migrate().migrationsExecuted).as("再跑一次沒有新遷移").isZero();
    }

    // ── AT-BK-06-4-3：部分唯一索引 ──────────────────────────────────────────────────────────────

    @Test
    void AT_BK_06_4_3_atMostOneQueuedOrRunningRowExistsAndTerminalRowsDoNotCount() {
        JdbcTemplate jdbc = migratedDatabase();

        insert(jdbc, "full", "QUEUED");
        for (String[] second : new String[][] {{"full", "QUEUED"}, {"diff", "QUEUED"}, {"verify", "RUNNING"}, {"diff", "RUNNING"}}) {
            assertThatThrownBy(() -> insert(jdbc, second[0], second[1])).as("已有進行中的列時再插 " + second[1] + "／" + second[0])
                    .isInstanceOf(DataAccessException.class).satisfies(thrown -> assertThat(sqlState(thrown)).as("違反 ux_backup_jobs_one_active").isEqualTo("23505"));
        }
        assertThat(jdbc.queryForObject("select count(*) from console.backup_jobs", Integer.class)).as("被拒的列都沒有寫入").isEqualTo(1);

        // 終態不佔索引：任意多筆 SUCCEEDED、FAILED、REJECTED、EXPIRED 並存仍可再插一個 QUEUED
        jdbc.update("update console.backup_jobs set status = 'RUNNING' where status = 'QUEUED'");
        assertThatThrownBy(() -> insert(jdbc, "diff", "QUEUED")).as("RUNNING 同樣佔索引").isInstanceOf(DataAccessException.class)
                .satisfies(thrown -> assertThat(sqlState(thrown)).isEqualTo("23505"));
        jdbc.update("update console.backup_jobs set status = 'SUCCEEDED' where status = 'RUNNING'");
        for (String terminal : List.of("SUCCEEDED", "FAILED", "REJECTED", "EXPIRED", "SUCCEEDED", "FAILED")) {
            insert(jdbc, "verify", terminal);
        }
        insert(jdbc, "full", "QUEUED");
        assertThat(jdbc.queryForObject("select count(*) from console.backup_jobs where status in ('QUEUED','RUNNING')", Integer.class)).isEqualTo(1);
        jdbc.update("update console.backup_jobs set status = 'SUCCEEDED' where status = 'QUEUED'");
        insert(jdbc, "diff", "QUEUED");
        assertThat(jdbc.queryForObject("select count(*) from console.backup_jobs where status = 'QUEUED'", Integer.class))
                .as("把該 QUEUED 改成終態後可再插一個").isEqualTo(1);
    }
}
