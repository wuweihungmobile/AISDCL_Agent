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
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Flyway V13（{@code console.si_console_writes}；TCS-SelfImprovingDecide-P2b AT-950-8-1、8-E-1、8-E-2；W13）。為什麼重要：這張表是 Console 對帳的
 * 獨立證據——有人（或有 bug 的程式）能改掉一列的 body、mac 或時間，「Console 決定過什麼」就不可信了；所以「列不可改」要落在資料庫（觸發器），
 * 而不是只靠應用層自律。升級路徑也要驗：在一個已經有資料的 V12 資料庫上升級，既有的表一個位元組都不能動。
 */
class SiConsoleWritesMigrationIT {

    private static final String BODY = "{\"schema_rev\":1,\"fixture\":true}";
    private static final String KEY_ID = "f076edf0";
    private static final String MAC = "0".repeat(64);

    private static String createDatabase() {
        String name = "si_writes_" + UUID.randomUUID().toString().replace("-", "");
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
        return "jdbc:postgresql://" + SharedPostgres.INSTANCE.getHost() + ":" + SharedPostgres.INSTANCE.getMappedPort(5432) + "/"
                + database;
    }

    private static Flyway flyway(String database, String targetVersion) {
        var configuration = Flyway.configure().dataSource(urlOf(database), SharedPostgres.INSTANCE.getUsername(),
                SharedPostgres.INSTANCE.getPassword()).schemas("console").defaultSchema("console")
                .locations("classpath:db/migration");
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

    private static void insert(JdbcTemplate jdbc, UUID ref, String subjectId) {
        jdbc.update("insert into console.si_console_writes (audit_ref, kind, \"user\", role, \"time\", subject_id, digest, body, "
                + "key_id, mac) values (?, 'obs-add', 'admin', 'ADMIN', '2026-10-24T14:30:15Z', ?, null, ?, ?, ?)", ref, subjectId,
                BODY, KEY_ID, MAC);
    }

    // ── AT-950-8-1：表結構與升級路徑 ───────────────────────────────────────────────────────────────

    @Test
    void AT_950_8_1_theTableHasTheTenColumnsOfTheSpecAndAV12DatabaseUpgradesWithoutTouchingExistingData() {
        String database = createDatabase();
        flyway(database, "12").migrate();
        JdbcTemplate jdbc = jdbcOf(database);
        UUID project = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria, status, signed_off) values "
                + "(?, '升級前的專案', '/same/root', '標準', 'READY', true)", project);
        String configsBefore = jdbc.queryForObject("select string_agg(category || '.' || key || '=' || coalesce(value, '<null>'), ';' "
                + "order by category, key) from console.system_configs", String.class);
        assertThat(jdbc.queryForObject("select count(*) from information_schema.tables where table_schema = 'console' "
                + "and table_name = 'si_console_writes'", Integer.class)).as("V12 時還沒有這張表").isZero();

        flyway(database, null).migrate();

        List<Map<String, Object>> columns = jdbc.queryForList("select column_name, data_type, is_nullable, "
                + "character_maximum_length from information_schema.columns where table_schema = 'console' "
                + "and table_name = 'si_console_writes' order by ordinal_position");
        assertThat(columns).extracting(c -> c.get("column_name")).containsExactly("audit_ref", "kind", "user", "role", "time",
                "subject_id", "digest", "body", "key_id", "mac");
        Map<String, Map<String, Object>> byName = new java.util.LinkedHashMap<>();
        columns.forEach(c -> byName.put((String) c.get("column_name"), c));
        assertThat(byName.get("audit_ref")).containsEntry("data_type", "uuid");
        assertThat(byName.get("time")).containsEntry("data_type", "timestamp with time zone");
        assertThat(byName.get("key_id")).containsEntry("character_maximum_length", 8);
        assertThat(byName.get("mac")).containsEntry("character_maximum_length", 64);
        assertThat(byName.get("kind")).containsEntry("character_maximum_length", 12);
        assertThat(byName.get("digest")).containsEntry("character_maximum_length", 71);
        assertThat(byName.get("subject_id")).containsEntry("character_maximum_length", 64);
        for (Map.Entry<String, Map<String, Object>> column : byName.entrySet()) {
            boolean nullable = "subject_id".equals(column.getKey()) || "digest".equals(column.getKey());
            assertThat(column.getValue().get("is_nullable")).as("%s 的可空性", column.getKey()).isEqualTo(nullable ? "YES" : "NO");
        }
        assertThat(jdbc.queryForList("select a.attname from pg_index i join pg_attribute a on a.attrelid = i.indrelid "
                + "and a.attnum = any(i.indkey) where i.indrelid = 'console.si_console_writes'::regclass and i.indisprimary",
                String.class)).as("主鍵").containsExactly("audit_ref");
        assertThat(jdbc.queryForList("select pg_get_constraintdef(oid) from pg_constraint where conrelid = "
                + "'console.si_console_writes'::regclass and contype = 'c'", String.class))
                .anySatisfy(def -> assertThat(def).contains("decide").contains("obs-add").contains("obs-close"));
        assertThat(jdbc.queryForObject("select count(*) from pg_indexes where schemaname = 'console' and indexname = "
                + "'idx_si_console_writes_time'", Integer.class)).as("time 上有索引").isEqualTo(1);
        assertThat(jdbc.queryForObject("select count(*) from information_schema.tables where table_schema = 'public' "
                + "and table_name = 'si_console_writes'", Integer.class)).as("不外洩到 public（會與其他系統的同名表撞名）").isZero();

        assertThat(jdbc.queryForObject("select name from console.projects where id = ?", String.class, project)).isEqualTo("升級前的專案");
        assertThat(jdbc.queryForObject("select string_agg(category || '.' || key || '=' || coalesce(value, '<null>'), ';' "
                + "order by category, key) from console.system_configs", String.class)).as("既有表資料不變").isEqualTo(configsBefore);
        List<Map<String, Object>> history = jdbc.queryForList("select version, success from console.flyway_schema_history "
                + "where version is not null order by installed_rank");
        assertThat(history).extracting(row -> row.get("version")).containsExactly("1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
                "11", "12", "13", "14");
        assertThat(history).extracting(row -> row.get("success")).containsOnly(true);
        assertThat(flyway(database, null).migrate().migrationsExecuted).as("再跑一次沒有新遷移").isZero();
    }

    // ── AT-950-8-E-1：列不可改 ─────────────────────────────────────────────────────────────────────

    @Test
    void AT_950_8_E_1_noColumnCanBeChangedExceptSubjectIdFillingFromNullAndDeleteStillWorks() {
        JdbcTemplate jdbc = migratedDatabase();
        UUID ref = UUID.randomUUID();
        insert(jdbc, ref, null);
        Map<String, Object[]> changes = new java.util.LinkedHashMap<>();
        changes.put("audit_ref = ?::uuid", new Object[] {UUID.randomUUID().toString()});
        changes.put("kind = ?", new Object[] {"decide"});
        changes.put("\"user\" = ?", new Object[] {"someone_else"});
        changes.put("role = ?", new Object[] {"VIEWER"});
        changes.put("\"time\" = ?::timestamptz", new Object[] {"2026-10-25T00:00:00Z"});
        changes.put("digest = ?", new Object[] {"sha256:" + "a".repeat(64)});
        changes.put("body = ?", new Object[] {"{\"tampered\":true}"});
        changes.put("key_id = ?", new Object[] {"deadbeef"});
        changes.put("mac = ?", new Object[] {"f".repeat(64)});

        changes.forEach((assignment, args) -> assertThatThrownBy(() -> jdbc.update("update console.si_console_writes set " + assignment
                + " where audit_ref = ?", append(args, ref))).as(assignment).isInstanceOf(DataAccessException.class)
                .hasMessageContaining("不可改"));

        assertThat(jdbc.update("update console.si_console_writes set subject_id = ? where audit_ref = ?", "OBS-SI-013", ref))
                .as("NULL 改為值：成功（對帳回填）").isEqualTo(1);
        assertThatThrownBy(() -> jdbc.update("update console.si_console_writes set subject_id = ? where audit_ref = ?", "OBS-SI-014",
                ref)).as("值改為另一值").isInstanceOf(DataAccessException.class).hasMessageContaining("不可改");
        assertThatThrownBy(() -> jdbc.update("update console.si_console_writes set subject_id = null where audit_ref = ?", ref))
                .as("值改回 NULL").isInstanceOf(DataAccessException.class).hasMessageContaining("不可改");
        assertThat(jdbc.update("update console.si_console_writes set subject_id = ? where audit_ref = ?", "OBS-SI-013", ref))
                .as("同值再寫（沒有變動）不算違規").isEqualTo(1);
        assertThat(jdbc.queryForObject("select body from console.si_console_writes where audit_ref = ?", String.class, ref))
                .as("被拒的 UPDATE 沒有留下任何改動").isEqualTo(BODY);

        assertThat(jdbc.update("delete from console.si_console_writes where audit_ref = ?", ref)).as("DELETE 可行（補償路徑）").isEqualTo(1);
        assertThat(jdbc.queryForObject("select count(*) from console.si_console_writes", Integer.class)).isZero();
    }

    private static Object[] append(Object[] args, Object extra) {
        Object[] out = java.util.Arrays.copyOf(args, args.length + 1);
        out[args.length] = extra;
        return out;
    }

    // ── AT-950-8-E-2：約束 ─────────────────────────────────────────────────────────────────────────

    @Test
    void AT_950_8_E_2_duplicateRefsUnknownKindsBadLengthsAndEmptyBodiesAreRejected() {
        JdbcTemplate jdbc = migratedDatabase();
        UUID ref = UUID.randomUUID();
        insert(jdbc, ref, null);
        String insert = "insert into console.si_console_writes (audit_ref, kind, \"user\", role, \"time\", subject_id, digest, body, "
                + "key_id, mac) values (?, ?, 'admin', 'ADMIN', '2026-10-24T14:30:15Z', null, null, ?, ?, ?)";

        assertThatThrownBy(() -> jdbc.update(insert, ref, "obs-add", BODY, KEY_ID, MAC)).as("重複 audit_ref")
                .isInstanceOf(DataAccessException.class);
        assertThatThrownBy(() -> jdbc.update(insert, UUID.randomUUID(), "delete", BODY, KEY_ID, MAC)).as("kind 非法")
                .isInstanceOf(DataAccessException.class);
        assertThatThrownBy(() -> jdbc.update(insert, UUID.randomUUID(), "obs-add", BODY, "f076edf", MAC)).as("key_id 為 7 字元")
                .isInstanceOf(DataAccessException.class);
        assertThatThrownBy(() -> jdbc.update(insert, UUID.randomUUID(), "obs-add", BODY, KEY_ID, "0".repeat(63))).as("mac 為 63 字元")
                .isInstanceOf(DataAccessException.class);
        assertThatThrownBy(() -> jdbc.update(insert, UUID.randomUUID(), "obs-add", null, KEY_ID, MAC)).as("body 為 NULL")
                .isInstanceOf(DataAccessException.class);
        assertThatThrownBy(() -> jdbc.update(insert, UUID.randomUUID(), "obs-add", BODY, "F076EDF0", MAC)).as("key_id 不是小寫十六進位")
                .isInstanceOf(DataAccessException.class);
        assertThatThrownBy(() -> jdbc.update(insert, UUID.randomUUID(), "obs-add", BODY, KEY_ID, "g".repeat(64))).as("mac 不是十六進位")
                .isInstanceOf(DataAccessException.class);

        assertThat(jdbc.queryForObject("select count(*) from console.si_console_writes", Integer.class)).as("表內仍恰一列").isEqualTo(1);
    }
}
