package com.aisdlc.console.infrastructure.persistence;

import com.aisdlc.console.support.AbstractIntegrationTest;
import com.aisdlc.console.support.SharedPostgres;
import org.assertj.core.api.SoftAssertions;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.MigrationVersion;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.transaction.support.TransactionTemplate;

import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.UUID;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Flyway V16～V19（V16～V18 為研究到規格的 13 張表，V19 為 P1 加上的分流／SCR／拆解／交付五表與自癒視圖；TCS-ResearchToPRD-P0-20261102 AC-960-1 的全部資料庫 AT；DDL 全文見 Architecture §11.3′ 的 K.1～K.3）。
 *
 * <p>為什麼重要：掌舵者要拿這些資料去簽 Gate 0——證據列被事後改寫、審查輪被改成「通過」、缺陷被悄悄關掉、來源查證層級被降級，
 * 簽核就失去意義。所以「不可變、單向、值域」這幾條規則必須落在資料庫（觸發器、CHECK、部分唯一索引），不能只靠 Bridge 寫入器自律：
 * 寫入器有 bug、日後有人另開一條寫入路徑、或有人直接連庫，資料庫仍要擋下。每個 CHECK 與觸發器都以「最小對照」驗：
 * 合法基準列成功，只改一個欄位的違規列失敗，所以失敗必然歸因於被測的那一條規則，而不是別的條件碰巧也不成立。
 *
 * <p>斷言 SQLSTATE（CHECK 23514、UNIQUE 23505、外鍵 23503、NOT NULL 23502、守衛觸發器 23000、欄寬 22001），守衛類另核對訊息帶表名與欄名，不比對訊息全文。
 * 需要寫入的測試各用自己的拋棄式資料庫（建庫、遷到最新版、測後 DROP），因為 append-only 的列清不掉；只讀系統目錄的兩個測試
 * （Flyway 歷史、時間欄型別）直接讀本類別 Spring context 的資料庫。各子情境以 {@link SoftAssertions} 彙整，任何一個子情境失敗時訊息都會指出是哪一個。
 * {@code ddl-auto=validate} 通過由本類別的 Spring context 能啟動本身證明（本功能沒有 JPA 實體，validate 不檢查這些表）。
 */
class ResearchSchemaMigrationIT extends AbstractIntegrationTest {

    private static final String CHECK = "23514";
    private static final String UNIQUE = "23505";
    private static final String FOREIGN_KEY = "23503";
    private static final String NOT_NULL = "23502";
    private static final String GUARD = "23000";
    private static final String TOO_LONG = "22001";

    private static final List<String> APPEND_ONLY_TABLES = List.of("research_events", "research_artifacts", "research_fetches",
            "research_evidence_items", "research_prd_versions", "research_review_rounds", "research_review_scores",
            "research_gate_decisions");
    private static final List<String> CONTROLLED_TABLES = List.of("research_projects", "research_stage_runs", "research_sources",
            "research_review_defects", "research_allowlist_entries");
    private static final List<String> RESEARCH_TABLES = List.of("research_projects", "research_events", "research_stage_runs",
            "research_artifacts", "research_sources", "research_fetches", "research_evidence_items", "research_allowlist_entries",
            "research_prd_versions", "research_review_rounds", "research_review_scores", "research_review_defects",
            "research_gate_decisions");

    /** V19（P1）新增的五張表；P0 的兩個常數維持原值，V19 另立（TCS-P1 §4 第 34 列）。 */
    private static final List<String> V19_TABLES = List.of("research_route_decisions", "research_route_steps", "research_scr",
            "research_decompositions", "research_deliveries");
    /** V19 的四張受控可更新表（research_deliveries 是 append-only，不在其中）。 */
    private static final List<String> V19_CONTROLLED_TABLES = List.of("research_route_decisions", "research_route_steps",
            "research_scr", "research_decompositions");
    private static final String V19_VIEW = "v_research_healing_attempts";

    private static final Set<String> JSONB_COLUMNS = Set.of("scope", "payload", "prompt_manifest", "allowlist_snapshot",
            "precheck_detail", "frozen_digests", "result_urls", "f5_applicability");
    private static final Set<String> ARRAY_COLUMNS = Set.of("f4_risk_tags", "evidence_refs");

    /** 受控可更新欄位表（TCS §5.1 的 CONTROLLED_UPDATE_COLUMNS）：欄位 → 把它改成另一個合法值的 SET 片段（CHECK 要求成組的欄位同句更新）。 */
    private static final Map<String, Map<String, String>> CONTROLLED_UPDATE_COLUMNS = Map.of(
            "research_projects", ordered(
                    "title", "title = '新標題'",
                    "topic", "topic = '新議題'",
                    "scope", "scope = '{\"stack\":[\"java\"]}'::jsonb",
                    "scope_rev", "scope_rev = 2",
                    "depth_level", "depth_level = 'DEEP'",
                    "target_scope", "target_scope = 'STANDALONE_PROJECT'",
                    "fsm_project", "fsm_project = 'research-chain-g2'",
                    "fsm_generation", "fsm_generation = 2",
                    "flow_step", "flow_step = 'studio'",
                    "flow_phase", "flow_phase = 'DRAFTING'",
                    "flow_status", "flow_status = 'RUNNING'",
                    "flow_detail", "flow_detail = '進行中'",
                    "console_project_id", "console_project_id = '%CP%'",
                    "last_event_seq", "last_event_seq = 5",
                    "updated_at", "updated_at = now() + interval '1 minute'",
                    "archived_at", "archived_at = now()"),
            "research_stage_runs", ordered(
                    "status", "status = 'RUNNING'",
                    "tokens_used", "tokens_used = 100",
                    "exit_reason", "exit_reason = 'done'",
                    "started_at", "started_at = now()",
                    "finished_at", "finished_at = now()"),
            "research_sources", ordered(
                    "verification", "verification = 'V3'"),
            "research_review_defects", ordered(
                    "status", "status = 'FIXED', resolved_at = now()",
                    "fixed_in_version_no", "fixed_in_version_no = 1",
                    "waived_by", "waived_by = 'admin'",
                    "waiver_reason", "waiver_reason = '理由'",
                    "resolved_at", "resolved_at = now()"),
            "research_allowlist_entries", ordered(
                    "enabled", "enabled = false, disabled_by = 'admin', disabled_at = now()",
                    "disabled_by", "disabled_by = 'admin'",
                    "disabled_at", "disabled_at = now()"));

    private static final OffsetDateTime T0 = OffsetDateTime.parse("2026-11-02T00:00:00Z");
    private static final OffsetDateTime T1 = OffsetDateTime.parse("2026-11-02T00:05:00Z");
    private static final String HEX64 = "a".repeat(64);
    private static final Pattern QUOTED = Pattern.compile("'([^']*)'");

    @Autowired
    JdbcTemplate springJdbc;

    @Autowired
    Environment env;

    private final List<String> scratchDatabases = new ArrayList<>();

    @AfterEach
    void dropScratchDatabases() {
        try (Connection admin = DriverManager.getConnection(SharedPostgres.INSTANCE.getJdbcUrl(),
                SharedPostgres.INSTANCE.getUsername(), SharedPostgres.INSTANCE.getPassword());
             Statement statement = admin.createStatement()) {
            for (String name : scratchDatabases) {
                statement.execute("drop database if exists " + name + " with (force)");
            }
        } catch (SQLException e) {
            throw new IllegalStateException("無法刪除測試資料庫", e);
        }
        scratchDatabases.clear();
    }

    // ── 基礎設施：拋棄式資料庫、結果型別、斷言與逐列寫入小工具 ───────────────────────────────────────────

    /** 一個拋棄式資料庫：每次呼叫都開新連線（自動提交）；{@link #tx} 供「獨立交易、結束即回滾」的情境使用。 */
    private static final class Db {
        private final JdbcTemplate jdbc;
        private final TransactionTemplate tx;

        private Db(String name) {
            DriverManagerDataSource dataSource = new DriverManagerDataSource(urlOf(name), SharedPostgres.INSTANCE.getUsername(),
                    SharedPostgres.INSTANCE.getPassword());
            this.jdbc = new JdbcTemplate(dataSource);
            this.tx = new TransactionTemplate(new DataSourceTransactionManager(dataSource));
        }
    }

    /** 一句（或一組）敘述的結果：成功時 {@code sqlState} 為 null（{@code value} 是讀回的值），失敗時是 SQLSTATE 與伺服器訊息首行。 */
    private record Outcome(Object value, String sqlState, String message) {
        boolean ok() {
            return sqlState == null;
        }
    }

    /** 伺服端運算式（不經參數綁定）：用來構造 1 MiB 級的內容，避免把大字串送過連線。 */
    private record Sql(String text) {
    }

    /** 一個研究專案與其 PRD 版本 1、一個 REVIEW stage run、一輪失敗的審查（多數 AT 共用的最小夾具鏈）。 */
    private record Chain(UUID project, UUID run, UUID round) {
    }

    private static String urlOf(String database) {
        return "jdbc:postgresql://" + SharedPostgres.INSTANCE.getHost() + ":" + SharedPostgres.INSTANCE.getMappedPort(5432) + "/"
                + database;
    }

    private Db newDatabase() {
        return databaseAt(null);
    }

    private Db databaseAt(String targetVersion) {
        String name = "research_schema_" + UUID.randomUUID().toString().replace("-", "");
        try (Connection admin = DriverManager.getConnection(SharedPostgres.INSTANCE.getJdbcUrl(),
                SharedPostgres.INSTANCE.getUsername(), SharedPostgres.INSTANCE.getPassword());
             Statement statement = admin.createStatement()) {
            statement.execute("create database " + name);
        } catch (SQLException e) {
            throw new IllegalStateException("無法建立測試資料庫", e);
        }
        scratchDatabases.add(name);
        var configuration = Flyway.configure().dataSource(urlOf(name), SharedPostgres.INSTANCE.getUsername(),
                SharedPostgres.INSTANCE.getPassword()).schemas("console").defaultSchema("console").locations("classpath:db/migration");
        if (targetVersion != null) {
            configuration.target(MigrationVersion.fromVersion(targetVersion));
        }
        configuration.load().migrate();
        return new Db(name);
    }

    private static Map<String, String> ordered(String... keyValues) {
        Map<String, String> map = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            map.put(keyValues[i], keyValues[i + 1]);
        }
        return map;
    }

    private static Map<String, Object> row(Object... keyValues) {
        Map<String, Object> row = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            row.put((String) keyValues[i], keyValues[i + 1]);
        }
        return row;
    }

    private static Map<String, Object> with(Map<String, Object> base, Object... keyValues) {
        Map<String, Object> copy = new LinkedHashMap<>(base);
        copy.putAll(row(keyValues));
        return copy;
    }

    private static Map<String, Object> without(Map<String, Object> base, String... columns) {
        Map<String, Object> copy = new LinkedHashMap<>(base);
        for (String column : columns) {
            copy.remove(column);
        }
        return copy;
    }

    private static Sql sql(String text) {
        return new Sql(text);
    }

    private static void insert(JdbcTemplate jdbc, String table, Map<String, Object> row) {
        List<String> columns = new ArrayList<>();
        List<String> marks = new ArrayList<>();
        List<Object> args = new ArrayList<>();
        row.forEach((column, value) -> {
            columns.add(column);
            if (value instanceof Sql expression) {
                marks.add(expression.text());
            } else if (JSONB_COLUMNS.contains(column)) {
                marks.add("?::jsonb");
                args.add(value);
            } else if (ARRAY_COLUMNS.contains(column)) {
                marks.add("?::text[]");
                args.add(value);
            } else {
                marks.add("?");
                args.add(value);
            }
        });
        jdbc.update("insert into console." + table + " (" + String.join(", ", columns) + ") values (" + String.join(", ", marks) + ")",
                args.toArray());
    }

    /** 自動提交地執行一組敘述：成功保留效果；失敗（單句失敗不留任何效果）回報 SQLSTATE。 */
    private static Outcome run(Db db, Function<JdbcTemplate, Object> work) {
        try {
            return new Outcome(work.apply(db.jdbc), null, null);
        } catch (DataAccessException e) {
            return new Outcome(null, String.valueOf(sqlStateOf(e)), messageOf(e));
        }
    }

    /** 在獨立交易內執行並於結束時回滾：用於會成功的敘述（要保持夾具不變）與逐一嘗試的組合。 */
    private static Outcome rolledBack(Db db, Function<JdbcTemplate, Object> work) {
        return db.tx.execute(status -> {
            status.setRollbackOnly();
            return run(db, work);
        });
    }

    private static Outcome tryInsert(Db db, String table, Map<String, Object> row) {
        return rolledBack(db, jdbc -> {
            insert(jdbc, table, row);
            return null;
        });
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> mapOf(Object value) {
        return (Map<String, Object>) value;
    }

    private static String sqlStateOf(Throwable thrown) {
        Throwable cause = thrown;
        while (cause != null && !(cause instanceof SQLException)) {
            cause = cause.getCause();
        }
        return cause == null ? null : ((SQLException) cause).getSQLState();
    }

    private static String messageOf(Throwable thrown) {
        Throwable cause = thrown;
        while (cause != null && !(cause instanceof SQLException)) {
            cause = cause.getCause();
        }
        String raw = String.valueOf(cause == null ? thrown.getMessage() : cause.getMessage());
        return raw.lines().findFirst().orElse(raw).replaceFirst("^ERROR: ", "");
    }

    private static void expectState(SoftAssertions soft, String label, Outcome outcome, String sqlState) {
        soft.assertThat(outcome.sqlState()).as("%s：應丟 %s，實際 %s", label, sqlState, outcome).isEqualTo(sqlState);
    }

    private static void expectOk(SoftAssertions soft, String label, Outcome outcome) {
        soft.assertThat(outcome.ok()).as("%s：應成功，實際 %s", label, outcome).isTrue();
    }

    /** 守衛觸發器的拒絕：SQLSTATE 23000，且訊息含指定片段（表名、欄名、append-only…）。 */
    private static void expectGuard(SoftAssertions soft, String label, Outcome outcome, String... messageParts) {
        expectState(soft, label, outcome, GUARD);
        for (String part : messageParts) {
            soft.assertThat(String.valueOf(outcome.message())).as("%s：訊息應含 %s", label, part).contains(part);
        }
    }

    private static String snapshot(JdbcTemplate jdbc, String table) {
        return jdbc.queryForObject("select coalesce(jsonb_agg(to_jsonb(t) order by to_jsonb(t)::text), '[]'::jsonb)::text "
                + "from console." + table + " t", String.class);
    }

    private static Set<String> baseTables(JdbcTemplate jdbc) {
        return new TreeSet<>(jdbc.queryForList("select table_name from information_schema.tables where table_schema = 'console' "
                + "and table_type = 'BASE TABLE'", String.class));
    }

    private static Map<String, Map<String, Object>> columnsOf(JdbcTemplate jdbc, String table) {
        Map<String, Map<String, Object>> columns = new LinkedHashMap<>();
        jdbc.queryForList("select column_name, data_type, is_nullable, character_maximum_length, numeric_precision, numeric_scale, "
                + "column_default from information_schema.columns where table_schema = 'console' and table_name = ? "
                + "order by ordinal_position", table).forEach(column -> columns.put((String) column.get("column_name"), column));
        return columns;
    }

    /** 單一欄位上的「IN (…)」CHECK 所允許的字面值集合（讓列舉的「恰為這幾個值」能逐一核對，而不只是抽樣）。 */
    private static Set<String> allowedLiterals(JdbcTemplate jdbc, String table, String column) {
        List<String> definitions = jdbc.queryForList("select pg_get_constraintdef(c.oid) from pg_constraint c "
                + "join pg_attribute a on a.attrelid = c.conrelid and a.attnum = any (c.conkey) "
                + "where c.conrelid = ?::regclass and c.contype = 'c' and a.attname = ? and cardinality(c.conkey) = 1 "
                + "and pg_get_constraintdef(c.oid) like '%ANY%'", String.class, "console." + table, column);
        assertThat(definitions).as("%s.%s 上應恰有一條單欄的列舉 CHECK", table, column).hasSize(1);
        Set<String> literals = new TreeSet<>();
        Matcher matcher = QUOTED.matcher(definitions.get(0));
        while (matcher.find()) {
            literals.add(matcher.group(1));
        }
        return literals;
    }

    private static void expectEnum(SoftAssertions soft, JdbcTemplate jdbc, String table, String column, String... expected) {
        soft.assertThat(allowedLiterals(jdbc, table, column)).as("%s.%s 的列舉恰為", table, column)
                .containsExactlyInAnyOrder(expected);
    }

    // ── 夾具：各表的合法基準列（只含 NOT NULL 且無預設值的欄位；測試以 with／without 改成違規列）──────────

    private static Map<String, Object> projectRow(UUID id, String slug) {
        return row("id", id, "slug", slug, "title", "研究 " + slug, "topic", "議題 " + slug, "workspace_path", "/ws/" + slug,
                "fsm_project", "research-" + slug, "fsm_state_dir", "/ws/" + slug + "/build/reports/fsm", "created_by", "admin");
    }

    private static Map<String, Object> stageRunRow(UUID id, UUID project, String stage, int roundNo, int attempt, String status) {
        return row("id", id, "research_id", project, "stage", stage, "round_no", roundNo, "attempt", attempt, "status", status,
                "requested_by", "admin");
    }

    private static Map<String, Object> eventRow(UUID project, long seq) {
        return row("research_id", project, "seq", seq, "event_type", "research.step", "step", "topic", "actor", "bridge");
    }

    private static Map<String, Object> artifactRow(UUID project, String kind, int version) {
        return row("research_id", project, "kind", kind, "version", version, "rel_path", "00_research/" + kind + "-v" + version,
                "sha256", HEX64, "bytes", 10L, "origin", "BRIDGE", "created_by", "bridge");
    }

    private static Map<String, Object> sourceRow(UUID id, UUID project, String no, String url) {
        return row("id", id, "research_id", project, "source_no", no, "layer", "ACADEMIC", "tier", "T1", "verification", "V2",
                "anchor_kind", "URL", "url", url, "title", "來源 " + no, "first_fetched_at", T0);
    }

    private static Map<String, Object> fetchRow(UUID project, String no) {
        return row("research_id", project, "layer", "ACADEMIC", "fetch_no", no, "fetch_method", "API", "observed_by", "BRIDGE",
                "url", "https://export.arxiv.org/api/" + no, "host", "export.arxiv.org", "outcome", "OK");
    }

    /** 宣告型搜尋列（WEB_SEARCH）：沒有單一網址，url 與 host 皆為 NULL。 */
    private static Map<String, Object> searchRow(UUID project, String no) {
        return row("research_id", project, "layer", "INDUSTRY", "fetch_no", no, "fetch_method", "WEB_SEARCH",
                "observed_by", "AGENT_DECLARED", "outcome", "OK");
    }

    private static Map<String, Object> evidenceRow(UUID project, UUID source, int matrixVersion, String no) {
        return row("research_id", project, "matrix_version", matrixVersion, "evidence_no", no, "source_id", source,
                "claim", "論點", "f1_mechanism", "機制", "f2_evidence", "證據", "f3_critique", "批判",
                "f5_applicability", "{\"feasibility\":\"A\"}", "f6_limits", "限制", "f7_verification", "V2");
    }

    private static Map<String, Object> allowlistRow(String host) {
        return row("list_kind", "FETCH", "host", host, "layer", "ACADEMIC", "min_interval_seconds", 3, "added_by", "admin");
    }

    private static Map<String, Object> prdRow(UUID project, int versionNo) {
        return row("research_id", project, "version_no", versionNo, "semver", "v0." + versionNo + ".0-draft", "kind", "DRAFT",
                "author_kind", "AGENT", "author", "spec-engineer", "content", "# PRD v" + versionNo, "rel_path", "01_specs/PRD.md",
                "sha256", HEX64, "bytes", 10);
    }

    /** 通過的輪：W100＝8500（85.00）、最低維度 60、無未結 P1、預檢通過、verdict PASS；AUTO 觸發的通過輪必有 gate PASS。 */
    private static Map<String, Object> passingRound(UUID project, UUID run, int roundNo) {
        return row("research_id", project, "round_no", roundNo, "prd_version_no", 1, "trigger_kind", "AUTO",
                "precheck_passed", true, "weighted_score", new BigDecimal("85.00"), "min_dimension_score", 60, "open_p1_count", 0,
                "passed", true, "verdict", "PASS", "fsm_gate_result", "PASS", "fsm_retry_count", 0, "escalated", false,
                "stage_run_id", run, "started_at", T0, "finished_at", T1);
    }

    /** 未通過的輪：84.95 與最低維度 59 皆不達標、verdict REVISE；未通過的輪必有 gate FAIL。 */
    private static Map<String, Object> failingRound(UUID project, UUID run, int roundNo) {
        return row("research_id", project, "round_no", roundNo, "prd_version_no", 1, "trigger_kind", "AUTO",
                "precheck_passed", true, "weighted_score", new BigDecimal("84.95"), "min_dimension_score", 59, "open_p1_count", 0,
                "passed", false, "verdict", "REVISE", "fsm_gate_result", "FAIL", "fsm_retry_count", 1, "escalated", false,
                "stage_run_id", run, "started_at", T0, "finished_at", T1);
    }

    private static Map<String, Object> scoreRow(UUID round, String dimension) {
        return row("round_id", round, "dimension", dimension, "weight", new BigDecimal("0.300"), "score", 80,
                "agent_id", "sd-architect", "agent_yaml_path", "agent/core/05.sd-architect-zh.yaml", "agent_yaml_sha256", HEX64,
                "persona_sha256", HEX64, "raw_rel_path", "02_governance/reviews/r1.json", "raw_sha256", HEX64);
    }

    private static Map<String, Object> defectRow(UUID id, UUID round, String no) {
        return row("id", id, "round_id", round, "defect_no", no, "dimension", "QA", "severity", "P2", "code", "SLV-001",
                "description", "缺陷說明");
    }

    private static Map<String, Object> decisionRow(UUID project, String gate, String decision) {
        return row("research_id", project, "gate", gate, "decision", decision, "decided_by", "admin", "decided_at", T0,
                "fsm_project", "research-chain");
    }

    private static UUID project(Db db, String slug) {
        UUID id = UUID.randomUUID();
        insert(db.jdbc, "research_projects", projectRow(id, slug));
        return id;
    }

    private static Chain chain(Db db) {
        UUID project = project(db, "chain");
        UUID run = UUID.randomUUID();
        UUID round = UUID.randomUUID();
        insert(db.jdbc, "research_prd_versions", prdRow(project, 1));
        insert(db.jdbc, "research_stage_runs", stageRunRow(run, project, "REVIEW", 1, 1, "SUCCEEDED"));
        insert(db.jdbc, "research_review_rounds", with(failingRound(project, run, 1), "id", round));
        return new Chain(project, run, round);
    }

    // ── AT_960_1_1：歷史、物件與守衛接線 ───────────────────────────────────────────────────────────

    @Test
    void AT_960_1_1_flywayHistoryObjectsAndGuardWiring() {
        List<Map<String, Object>> history = springJdbc.queryForList("select version, description, success from "
                + "console.flyway_schema_history where version is not null order by installed_rank");
        Map<String, Object> descriptions = new LinkedHashMap<>();
        history.forEach(row -> descriptions.put((String) row.get("version"), row.get("description")));
        // 表集合取自拋棄式資料庫（遷到 19、18、15）：同一 JVM 內別的整合測試會暫時改名或暫建表，不能拿共用的 Spring 資料庫來算「多出」
        Set<String> afterV19 = baseTables(newDatabase().jdbc);
        Set<String> afterV18 = baseTables(databaseAt("18").jdbc);
        Set<String> afterV15 = baseTables(databaseAt("15").jdbc);
        Set<String> added = new TreeSet<>(afterV18);
        added.removeAll(afterV15);
        Set<String> addedByV19 = new TreeSet<>(afterV19);
        addedByV19.removeAll(afterV18);
        Integer leaked = springJdbc.queryForObject("select count(*) from information_schema.tables where table_schema = 'public' "
                + "and table_name like 'research\\_%'", Integer.class);
        List<String> sequences = springJdbc.queryForList("select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                + "where c.relkind = 'S' and n.nspname = 'console'", String.class);
        Map<String, String> functions = new LinkedHashMap<>();
        springJdbc.queryForList("select p.proname, pg_get_function_result(p.oid) as result from pg_proc p "
                + "join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'console' and p.proname like 'research\\_%'")
                .forEach(function -> functions.put((String) function.get("proname"), (String) function.get("result")));
        Map<String, String> indexes = new LinkedHashMap<>();
        springJdbc.queryForList("select indexname, tablename, indexdef from pg_indexes where schemaname = 'console' "
                + "and tablename like 'research\\_%'").forEach(index -> indexes.put(index.get("indexname") + "@" + index.get("tablename"),
                        (String) index.get("indexdef")));
        Map<String, List<String>> guardsByTable = new LinkedHashMap<>();
        springJdbc.queryForList("select c.relname as tbl, p.proname as fn from pg_trigger t join pg_class c on c.oid = t.tgrelid "
                + "join pg_namespace n on n.oid = c.relnamespace join pg_proc p on p.oid = t.tgfoid where n.nspname = 'console' "
                + "and c.relname like 'research\\_%' and not t.tgisinternal order by c.relname, t.tgname")
                .forEach(trigger -> guardsByTable.computeIfAbsent((String) trigger.get("tbl"), key -> new ArrayList<>())
                        .add((String) trigger.get("fn")));

        SoftAssertions.assertSoftly(soft -> {
            soft.assertThat(env.getProperty("spring.jpa.hibernate.ddl-auto")).as("ddl-auto=validate（本 context 能啟動即代表 validate 通過）")
                    .isEqualTo("validate");
            soft.assertThat(history).extracting(row -> row.get("version")).as("Flyway 歷史依序為 1 至 19")
                    .containsExactly("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20");
            soft.assertThat(history).extracting(row -> row.get("success")).as("每一版都成功").containsOnly(true);
            soft.assertThat(descriptions).containsEntry("16", "research core").containsEntry("17", "research evidence")
                    .containsEntry("18", "research prd review gate").containsEntry("19", "research route scr delivery").containsEntry("20", "research github token config");
            soft.assertThat(afterV18).as("V16～V19 沒有拿掉任何既有的表").containsAll(afterV15).containsAll(afterV18);
            soft.assertThat(added).as("V16～V18 在 console 內恰多出 13 張表（P0 集合不退步）").containsExactlyInAnyOrderElementsOf(RESEARCH_TABLES);
            soft.assertThat(addedByV19).as("V19 在 console 內恰多出 5 張表").containsExactlyInAnyOrderElementsOf(V19_TABLES);
            soft.assertThat(leaked).as("research_ 的表不得外洩到 public").isZero();
            soft.assertThat(sequences).as("RP 編號序列").contains("research_rp_seq");
            soft.assertThat(functions).as("編號函式與兩個通用守衛函式").containsEntry("research_next_rp_no", "text")
                    .containsEntry("research_append_only_guard", "trigger").containsEntry("research_controlled_update_guard", "trigger");

            soft.assertThat(indexes).as("索引齊備").containsKeys("ux_research_projects_slug_active@research_projects",
                    "ux_research_projects_console_project@research_projects", "idx_research_projects_flow@research_projects",
                    "idx_research_events_type@research_events", "idx_research_stage_runs_status@research_stage_runs",
                    "ux_research_stage_runs_active@research_stage_runs", "idx_research_fetches_research@research_fetches",
                    "ux_research_fetches_search_no@research_fetches", "idx_research_evidence_source@research_evidence_items",
                    "idx_research_gate_research@research_gate_decisions", "idx_research_defects_open@research_review_defects");
            soft.assertThat(indexes.get("ux_research_projects_slug_active@research_projects")).as("slug 的部分唯一索引")
                    .containsIgnoringCase("UNIQUE").containsIgnoringCase("WHERE").contains("archived_at IS NULL");
            soft.assertThat(indexes.get("ux_research_projects_console_project@research_projects")).as("console_project_id 的部分唯一索引")
                    .containsIgnoringCase("UNIQUE").containsIgnoringCase("WHERE").contains("console_project_id IS NOT NULL");
            soft.assertThat(indexes.get("ux_research_fetches_search_no@research_fetches")).as("search_no 的部分唯一索引")
                    .containsIgnoringCase("UNIQUE").containsIgnoringCase("WHERE").contains("search_no IS NOT NULL");
            soft.assertThat(indexes.get("ux_research_stage_runs_active@research_stage_runs")).as("進行中 stage run 的部分唯一索引")
                    .containsIgnoringCase("UNIQUE").containsIgnoringCase("WHERE").contains("QUEUED").contains("RUNNING");
            soft.assertThat(indexes.get("idx_research_defects_open@research_review_defects")).as("未結缺陷的部分索引")
                    .containsIgnoringCase("WHERE").contains("OPEN");

            List<String> allResearchTables = new ArrayList<>(RESEARCH_TABLES);
            allResearchTables.addAll(V19_TABLES);
            soft.assertThat(guardsByTable.keySet()).as("18 張表（P0 十三加 V19 五）都有守衛觸發器、沒有別的表")
                    .containsExactlyInAnyOrderElementsOf(allResearchTables);
            for (String table : V19_CONTROLLED_TABLES) {
                soft.assertThat(guardsByTable.get(table)).as("%s 只掛受控更新通用守衛", table).containsExactly("research_controlled_update_guard");
            }
            soft.assertThat(guardsByTable.get("research_deliveries")).as("research_deliveries 只掛 append-only 守衛")
                    .containsExactly("research_append_only_guard");
            for (String table : APPEND_ONLY_TABLES) {
                soft.assertThat(guardsByTable.get(table)).as("%s 只掛 append-only 守衛", table)
                        .containsExactly("research_append_only_guard");
            }
            for (String table : List.of("research_projects", "research_stage_runs", "research_allowlist_entries")) {
                soft.assertThat(guardsByTable.get(table)).as("%s 只掛受控更新通用守衛", table)
                        .containsExactly("research_controlled_update_guard");
            }
            for (String table : List.of("research_review_defects", "research_sources")) {
                soft.assertThat(guardsByTable.get(table)).as("%s 掛通用守衛，另加一個專用守衛", table).hasSize(2)
                        .contains("research_controlled_update_guard").doesNotContain("research_append_only_guard");
            }
        });
    }

    // ── AT_960_1_2：八張 append-only 表 ────────────────────────────────────────────────────────────

    @Test
    void AT_960_1_2_appendOnlyTablesRejectUpdateAndDelete() {
        Db db = newDatabase();
        Chain chain = chain(db);
        UUID source = UUID.randomUUID();
        insert(db.jdbc, "research_sources", sourceRow(source, chain.project(), "S-001", "https://example.org/s1"));
        insert(db.jdbc, "research_events", eventRow(chain.project(), 1));
        insert(db.jdbc, "research_artifacts", artifactRow(chain.project(), "ISSUE_SCOPE", 1));
        insert(db.jdbc, "research_fetches", fetchRow(chain.project(), "F-0001"));
        insert(db.jdbc, "research_evidence_items", evidenceRow(chain.project(), source, 1, "E-001"));
        insert(db.jdbc, "research_review_scores", scoreRow(chain.round(), "ARCHITECTURE"));
        insert(db.jdbc, "research_gate_decisions", decisionRow(chain.project(), "GATE0", "CHANGES"));
        // research_prd_versions 與 research_review_rounds 的一列已由夾具鏈建好

        Map<String, String> touchedColumn = ordered("research_events", "actor", "research_artifacts", "bytes",
                "research_fetches", "duration_ms", "research_evidence_items", "claim", "research_prd_versions", "change_summary",
                "research_review_rounds", "fsm_generation", "research_review_scores", "summary", "research_gate_decisions", "reason");
        Map<String, String> changedValue = ordered("research_events", "'someone'", "research_artifacts", "bytes + 1",
                "research_fetches", "5", "research_evidence_items", "'改寫'", "research_prd_versions", "'改寫'",
                "research_review_rounds", "2", "research_review_scores", "'改寫'", "research_gate_decisions", "'改寫'");

        SoftAssertions.assertSoftly(soft -> {
            for (String table : APPEND_ONLY_TABLES) {
                String column = touchedColumn.get(table);
                String before = snapshot(db.jdbc, table);
                soft.assertThat(before).as("%s 夾具列存在", table).isNotEqualTo("[]");
                Outcome update = run(db, jdbc -> jdbc.update("update console." + table + " set " + column + " = "
                        + changedValue.get(table)));
                expectGuard(soft, table + " UPDATE", update, table, "append-only");
                Outcome sameValue = run(db, jdbc -> jdbc.update("update console." + table + " set " + column + " = " + column));
                expectGuard(soft, table + " 同值 UPDATE 也被拒（append-only 不是「值沒變就放行」）", sameValue, table, "append-only");
                Outcome delete = run(db, jdbc -> jdbc.update("delete from console." + table));
                expectGuard(soft, table + " DELETE", delete, table, "append-only");
                soft.assertThat(snapshot(db.jdbc, table)).as("%s 被拒之後逐欄與插入時完全相同", table).isEqualTo(before);
            }

            // append-only 擋的是改與刪，不是追加：每張表再追加一列都成功
            insert(db.jdbc, "research_events", eventRow(chain.project(), 2));
            insert(db.jdbc, "research_artifacts", artifactRow(chain.project(), "ISSUE_SCOPE", 2));
            insert(db.jdbc, "research_fetches", fetchRow(chain.project(), "F-0002"));
            insert(db.jdbc, "research_evidence_items", evidenceRow(chain.project(), source, 1, "E-002"));
            insert(db.jdbc, "research_prd_versions", prdRow(chain.project(), 2));
            insert(db.jdbc, "research_review_rounds", failingRound(chain.project(), chain.run(), 2));
            insert(db.jdbc, "research_review_scores", scoreRow(chain.round(), "PRODUCT"));
            insert(db.jdbc, "research_gate_decisions", decisionRow(chain.project(), "GATE0", "REJECTED"));
            for (String table : APPEND_ONLY_TABLES) {
                soft.assertThat(db.jdbc.queryForObject("select count(*) from console." + table, Integer.class))
                        .as("%s 追加後共兩列（原列仍在、新列已追加）", table).isEqualTo(2);
            }
            // 追加仍須守值域與鍵：事件序號從 1 起、同專案不重複、必須屬於既有專案
            expectState(soft, "events seq 為 0", tryInsert(db, "research_events", eventRow(chain.project(), 0)), CHECK);
            expectState(soft, "events 同 (research_id, seq) 重複", tryInsert(db, "research_events", eventRow(chain.project(), 1)), UNIQUE);
            expectState(soft, "events 屬於不存在的研究專案", tryInsert(db, "research_events", eventRow(UUID.randomUUID(), 1)), FOREIGN_KEY);
        });
    }

    // ── AT_960_1_3：來源表 ─────────────────────────────────────────────────────────────────────────

    @Test
    void AT_960_1_3_sourcesChecksAndVerificationUpgrade() {
        Db db = newDatabase();
        UUID project = project(db, "src");
        UUID source = UUID.randomUUID();
        insert(db.jdbc, "research_sources", sourceRow(source, project, "S-001", "https://example.org/base"));
        Map<String, Object> before = db.jdbc.queryForMap("select * from console.research_sources where id = ?", source);

        SoftAssertions.assertSoftly(soft -> {
            Outcome upgrade = run(db, jdbc -> jdbc.update("update console.research_sources set verification = 'V3' where id = ?", source));
            expectOk(soft, "verification V2→V3", upgrade);
            Map<String, Object> after = db.jdbc.queryForMap("select * from console.research_sources where id = ?", source);
            soft.assertThat(after.get("verification")).as("查證層級已升為 V3").isEqualTo("V3");
            before.forEach((column, value) -> {
                if (!"verification".equals(column)) {
                    soft.assertThat(after.get(column)).as("升級後除 verification 外 %s 不變", column).isEqualTo(value);
                }
            });
            expectGuard(soft, "DELETE 來源", run(db, jdbc -> jdbc.update("delete from console.research_sources where id = ?", source)),
                    "research_sources");

            String commit40 = "a".repeat(40);
            expectState(soft, "tier T3 而 clue_only 為假", tryInsert(db, "research_sources",
                    with(src(project, "S-101"), "tier", "T3", "clue_only", false)), CHECK);
            expectState(soft, "anchor_kind DOI 而 doi 為 NULL", tryInsert(db, "research_sources",
                    with(src(project, "S-102"), "anchor_kind", "DOI", "doi", null)), CHECK);
            expectState(soft, "anchor_kind COMMIT 而 git_commit 為 NULL（NULL 不得靜默通過）", tryInsert(db, "research_sources",
                    with(src(project, "S-103"), "anchor_kind", "COMMIT", "git_commit", null)), CHECK);
            expectState(soft, "COMMIT 而 git_commit 為 39 位", tryInsert(db, "research_sources",
                    with(src(project, "S-104"), "anchor_kind", "COMMIT", "git_commit", "a".repeat(39))), CHECK);
            expectState(soft, "COMMIT 而 git_commit 為 41 位", tryInsert(db, "research_sources",
                    with(src(project, "S-105"), "anchor_kind", "COMMIT", "git_commit", "a".repeat(41))), CHECK);
            expectState(soft, "COMMIT 而 git_commit 含大寫十六進位字元", tryInsert(db, "research_sources",
                    with(src(project, "S-106"), "anchor_kind", "COMMIT", "git_commit", "A" + "a".repeat(39))), CHECK);
            expectState(soft, "COMMIT 而 git_commit 含 g", tryInsert(db, "research_sources",
                    with(src(project, "S-107"), "anchor_kind", "COMMIT", "git_commit", "g" + "a".repeat(39))), CHECK);
            expectState(soft, "verification 為 V0", tryInsert(db, "research_sources",
                    with(src(project, "S-108"), "verification", "V0")), CHECK);
            expectState(soft, "source_no 為 S-1", tryInsert(db, "research_sources", src(project, "S-1")), CHECK);
            expectState(soft, "同 research_id 同 url 的第二筆", tryInsert(db, "research_sources",
                    with(src(project, "S-109"), "url", "https://example.org/base")), UNIQUE);
            expectState(soft, "url 為 http", tryInsert(db, "research_sources",
                    with(src(project, "S-110"), "url", "http://example.com/a")), CHECK);
            expectState(soft, "url 為 ftp", tryInsert(db, "research_sources",
                    with(src(project, "S-111"), "url", "ftp://example.com/a")), CHECK);
            expectState(soft, "url 沒有協定", tryInsert(db, "research_sources",
                    with(src(project, "S-112"), "url", "example.com/a")), CHECK);
            expectState(soft, "同 research_id 同 source_no 的第二筆", tryInsert(db, "research_sources", src(project, "S-001")), UNIQUE);
            expectState(soft, "layer 為列舉外值", tryInsert(db, "research_sources", with(src(project, "S-121"), "layer", "WEB")), CHECK);
            expectState(soft, "tier 為列舉外值", tryInsert(db, "research_sources", with(src(project, "S-122"), "tier", "T4")), CHECK);
            expectState(soft, "anchor_kind 為列舉外值", tryInsert(db, "research_sources",
                    with(src(project, "S-123"), "anchor_kind", "ISBN")), CHECK);
            expectState(soft, "source_type 為列舉外值", tryInsert(db, "research_sources",
                    with(src(project, "S-124"), "source_type", "BLOG")), CHECK);
            expectState(soft, "來源屬於不存在的研究專案", tryInsert(db, "research_sources", src(UUID.randomUUID(), "S-125")), FOREIGN_KEY);
            expectEnum(soft, db.jdbc, "research_sources", "layer", "ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY");
            expectEnum(soft, db.jdbc, "research_sources", "tier", "T1", "T2", "T3");
            expectEnum(soft, db.jdbc, "research_sources", "verification", "V1", "V2", "V3");
            expectEnum(soft, db.jdbc, "research_sources", "anchor_kind", "URL", "DOI", "COMMIT");
            expectEnum(soft, db.jdbc, "research_sources", "source_type", "PAPER", "PREPRINT", "ENG_BLOG", "WHITEPAPER", "PATENT",
                    "REPO", "ISSUE_PR", "FORUM", "DOC", "OTHER");

            expectOk(soft, "tier T3 且 clue_only 為真", tryInsert(db, "research_sources",
                    with(src(project, "S-201"), "tier", "T3", "clue_only", true)));
            expectOk(soft, "COMMIT 且 git_commit 為 40 位小寫十六進位", tryInsert(db, "research_sources",
                    with(src(project, "S-202"), "anchor_kind", "COMMIT", "git_commit", commit40)));
            expectOk(soft, "DOI 且 doi 非空", tryInsert(db, "research_sources",
                    with(src(project, "S-203"), "anchor_kind", "DOI", "doi", "10.1000/xyz123")));
        });
    }

    private static Map<String, Object> src(UUID project, String no) {
        return without(sourceRow(UUID.randomUUID(), project, no, "https://example.org/" + no.toLowerCase()), "id");
    }

    // ── AT_960_1_4：allowlist ──────────────────────────────────────────────────────────────────────

    @Test
    void AT_960_1_4_allowlistImmutableColumnsAndChecks() {
        Db db = newDatabase();
        UUID entry = UUID.randomUUID();
        insert(db.jdbc, "research_allowlist_entries", with(allowlistRow("export.arxiv.org"), "id", entry));
        Map<String, String> immutableSets = ordered("host", "host = 'other.example.org'", "layer", "layer = 'OSS'",
                "purpose", "purpose = '改過'", "tos_note", "tos_note = '改過'", "min_interval_seconds", "min_interval_seconds = 4",
                "tos_acknowledged", "tos_acknowledged = true", "added_by", "added_by = 'someone'",
                "added_at", "added_at = now() + interval '1 day'");
        String before = snapshot(db.jdbc, "research_allowlist_entries");

        SoftAssertions.assertSoftly(soft -> {
            immutableSets.forEach((column, set) -> expectGuard(soft, "不可變欄 " + column,
                    run(db, jdbc -> jdbc.update("update console.research_allowlist_entries set " + set + " where id = ?", entry)),
                    "research_allowlist_entries", "enabled", "disabled_by", "disabled_at"));
            soft.assertThat(snapshot(db.jdbc, "research_allowlist_entries")).as("被拒之後列不變").isEqualTo(before);

            expectState(soft, "停用而缺 disabled_by", rolledBack(db, jdbc -> jdbc.update(
                    "update console.research_allowlist_entries set enabled = false, disabled_at = now() where id = ?", entry)), CHECK);
            expectState(soft, "停用而缺 disabled_at", rolledBack(db, jdbc -> jdbc.update(
                    "update console.research_allowlist_entries set enabled = false, disabled_by = 'admin' where id = ?", entry)), CHECK);
            expectGuard(soft, "DELETE 條目", run(db, jdbc -> jdbc.update(
                    "delete from console.research_allowlist_entries where id = ?", entry)), "research_allowlist_entries");

            for (String host : List.of("reddit.com", "old.reddit.com", "redd.it")) {
                expectState(soft, host + " 未確認條款", tryInsert(db, "research_allowlist_entries", allowlistRow(host)), CHECK);
                expectOk(soft, host + " 已確認條款", tryInsert(db, "research_allowlist_entries",
                        with(allowlistRow(host), "tos_acknowledged", true)));
            }
            expectOk(soft, "名稱近似但不是 Reddit 的網域不需確認條款", tryInsert(db, "research_allowlist_entries",
                    allowlistRow("notreddit.com")));
            for (String host : List.of("Arxiv.org", "https://a.com", "a.com/x")) {
                expectState(soft, "壞 host " + host, tryInsert(db, "research_allowlist_entries", allowlistRow(host)), CHECK);
            }
            expectState(soft, "min_interval_seconds 為 0", tryInsert(db, "research_allowlist_entries",
                    with(allowlistRow("zero.example.org"), "min_interval_seconds", 0)), CHECK);
            expectOk(soft, "min_interval_seconds 為 1", tryInsert(db, "research_allowlist_entries",
                    with(allowlistRow("one.example.org"), "min_interval_seconds", 1)));
            expectOk(soft, "min_interval_seconds 為 3600", tryInsert(db, "research_allowlist_entries",
                    with(allowlistRow("max.example.org"), "min_interval_seconds", 3600)));
            expectState(soft, "min_interval_seconds 為 3601", tryInsert(db, "research_allowlist_entries",
                    with(allowlistRow("over.example.org"), "min_interval_seconds", 3601)), CHECK);
            expectState(soft, "同 (list_kind, host) 的第二筆", tryInsert(db, "research_allowlist_entries",
                    allowlistRow("export.arxiv.org")), UNIQUE);
            expectOk(soft, "同 host 但 list_kind 不同", tryInsert(db, "research_allowlist_entries",
                    with(allowlistRow("export.arxiv.org"), "list_kind", "WEB")));
            expectState(soft, "list_kind 為列舉外值", tryInsert(db, "research_allowlist_entries",
                    with(allowlistRow("kind.example.org"), "list_kind", "OTHER")), CHECK);
            expectState(soft, "layer 為列舉外值", tryInsert(db, "research_allowlist_entries",
                    with(allowlistRow("layer.example.org"), "layer", "WEB")), CHECK);
            expectEnum(soft, db.jdbc, "research_allowlist_entries", "list_kind", "FETCH", "WEB");
            expectEnum(soft, db.jdbc, "research_allowlist_entries", "layer", "ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY");
        });

        // 允許的更新：停用（帶 disabled_by 與 disabled_at）成功，且其餘欄位不變
        Map<String, Object> beforeRow = db.jdbc.queryForMap("select * from console.research_allowlist_entries where id = ?", entry);
        db.jdbc.update("update console.research_allowlist_entries set enabled = false, disabled_by = 'admin', disabled_at = now() "
                + "where id = ?", entry);
        Map<String, Object> afterRow = db.jdbc.queryForMap("select * from console.research_allowlist_entries where id = ?", entry);
        SoftAssertions.assertSoftly(soft -> {
            soft.assertThat(afterRow).as("允許的更新：停用").containsEntry("enabled", false).containsEntry("disabled_by", "admin");
            beforeRow.forEach((column, value) -> {
                if (!List.of("enabled", "disabled_by", "disabled_at").contains(column)) {
                    soft.assertThat(afterRow.get(column)).as("停用後 %s 不變", column).isEqualTo(value);
                }
            });
        });
    }

    // ── AT_960_1_5：研究專案 ───────────────────────────────────────────────────────────────────────

    @Test
    void AT_960_1_5_projectsSequenceSlugAndUniqueness() {
        Db db = newDatabase();
        List<String> rpNos = new ArrayList<>();
        for (String slug : List.of("one", "two", "three")) {
            UUID id = project(db, slug);
            rpNos.add(db.jdbc.queryForObject("select rp_no from console.research_projects where id = ?", String.class, id));
        }
        db.jdbc.queryForObject("select setval('console.research_rp_seq', 9999)", Long.class);
        UUID big = project(db, "big");
        String bigRpNo = db.jdbc.queryForObject("select rp_no from console.research_projects where id = ?", String.class, big);

        UUID consoleProject = UUID.randomUUID();
        db.jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria) values (?,?,?,?)",
                consoleProject, "console-p", "/x", "c");
        UUID holder = UUID.randomUUID();
        insert(db.jdbc, "research_projects", with(projectRow(holder, "holder"), "console_project_id", consoleProject));

        SoftAssertions.assertSoftly(soft -> {
            soft.assertThat(rpNos).as("未指定 rp_no 時依序配號").containsExactly("RP-0001", "RP-0002", "RP-0003");
            soft.assertThat(bigRpNo).as("超過 4 位數不截斷").isEqualTo("RP-10000");
            expectState(soft, "slug 為大寫 Abc", tryInsert(db, "research_projects", projectRow(UUID.randomUUID(), "Abc")), CHECK);
            expectState(soft, "slug 以連字號起頭", tryInsert(db, "research_projects", projectRow(UUID.randomUUID(), "-a")), CHECK);
            expectState(soft, "slug 含底線", tryInsert(db, "research_projects", projectRow(UUID.randomUUID(), "a_b")), CHECK);
            expectState(soft, "slug 為 31 字元（欄寬 VARCHAR(30) 先擋）", tryInsert(db, "research_projects",
                    projectRow(UUID.randomUUID(), "a".repeat(31))), TOO_LONG);
            expectOk(soft, "slug 為 30 字元", tryInsert(db, "research_projects", projectRow(UUID.randomUUID(), "a".repeat(30))));

            Outcome duplicate = tryInsert(db, "research_projects", projectRow(UUID.randomUUID(), "one"));
            expectState(soft, "與未封存專案同 slug", duplicate, UNIQUE);
            soft.assertThat(duplicate.message()).as("是部分唯一索引擋下的").contains("ux_research_projects_slug_active");
            expectOk(soft, "原列封存後可再插同 slug", rolledBack(db, jdbc -> {
                jdbc.update("update console.research_projects set archived_at = now() where slug = 'one'");
                insert(jdbc, "research_projects", projectRow(UUID.randomUUID(), "one"));
                return null;
            }));

            Outcome sameConsoleProject = tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "twin"), "console_project_id", consoleProject));
            expectState(soft, "非 NULL 的 console_project_id 重複", sameConsoleProject, UNIQUE);
            soft.assertThat(sameConsoleProject.message()).contains("ux_research_projects_console_project");
            expectOk(soft, "console_project_id 皆為 NULL 的多列並存", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "nulls"), "console_project_id", null)));
            expectState(soft, "console_project_id 指向不存在的專案", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "ghost"), "console_project_id", UUID.randomUUID())), FOREIGN_KEY);

            expectState(soft, "flow_step 列舉外值", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "e1"), "flow_step", "plan")), CHECK);
            expectState(soft, "flow_phase 列舉外值", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "e2"), "flow_phase", "UNKNOWN")), CHECK);
            expectState(soft, "flow_status 列舉外值", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "e3"), "flow_status", "PAUSED")), CHECK);
            expectState(soft, "depth_level 列舉外值", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "e4"), "depth_level", "EXTREME")), CHECK);
            expectState(soft, "target_scope 列舉外值", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "e5"), "target_scope", "OTHER")), CHECK);
            expectOk(soft, "五個列舉欄皆取合法值", tryInsert(db, "research_projects", with(projectRow(UUID.randomUUID(), "ok1"),
                    "flow_step", "studio", "flow_phase", "REVIEWING", "flow_status", "WAITING_HUMAN", "depth_level", "DEEP",
                    "target_scope", "AISDLC_MODULE")));
            expectState(soft, "topic 為 501 字元", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "t501"), "topic", "x".repeat(501))), CHECK);
            expectOk(soft, "topic 為 500 字元", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "t500"), "topic", "x".repeat(500))));
            expectState(soft, "直接指定 rp_no 為 RP-12", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "r1"), "rp_no", "RP-12")), CHECK);
            expectState(soft, "直接指定 rp_no 為 RP-123（3 位數＝低於 4 位的下限）", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "r1b"), "rp_no", "RP-123")), CHECK);
            expectOk(soft, "直接指定 rp_no 為 RP-1234（4 位數＝下限）", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "r1c"), "rp_no", "RP-1234")));
            expectState(soft, "直接指定 rp_no 為 XX-0001", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "r2"), "rp_no", "XX-0001")), CHECK);
            expectState(soft, "直接指定的 rp_no 與既有的重複", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "r3"), "rp_no", "RP-0001")), UNIQUE);
            expectState(soft, "parent_research_id 指向不存在的研究專案", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "orphan"), "parent_research_id", UUID.randomUUID())), FOREIGN_KEY);
            expectOk(soft, "parent_research_id 指向既有的研究專案", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "child"), "parent_research_id", holder)));
            expectState(soft, "scope_rev 為 0", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "s0"), "scope_rev", 0)), CHECK);
            expectState(soft, "fsm_generation 為 0", tryInsert(db, "research_projects",
                    with(projectRow(UUID.randomUUID(), "g0"), "fsm_generation", 0)), CHECK);

            expectEnum(soft, db.jdbc, "research_projects", "flow_step", "topic", "studio", "route", "build", "deliver");
            expectEnum(soft, db.jdbc, "research_projects", "flow_phase", "INGESTED", "RESEARCHING", "EVIDENCE_READY", "DRAFTING",
                    "REVIEWING", "REVISING", "GATE0_PENDING", "FROZEN", "ROUTING", "ROUTED", "TCS_DRAFTING", "TCS_PENDING", "SCR_OPEN");
            expectEnum(soft, db.jdbc, "research_projects", "flow_status", "IDLE", "RUNNING", "WAITING_HUMAN", "BLOCKED",
                    "ESCALATED", "FAILED", "CANCELLED", "COMPLETED");
            expectEnum(soft, db.jdbc, "research_projects", "depth_level", "QUICK", "STANDARD", "DEEP");
            expectEnum(soft, db.jdbc, "research_projects", "target_scope", "UNDECIDED", "AISDLC_MODULE", "STANDALONE_PROJECT");
        });
    }

    // ── AT_960_1_6：審查輪的精確分數與通過旗標 ─────────────────────────────────────────────────────

    @Test
    void AT_960_1_6_reviewRoundsExactNumericsAndPassedCheck() {
        Db db = newDatabase();
        UUID project = project(db, "rounds");
        UUID run = UUID.randomUUID();
        insert(db.jdbc, "research_prd_versions", prdRow(project, 1));
        insert(db.jdbc, "research_stage_runs", stageRunRow(run, project, "REVIEW", 1, 1, "SUCCEEDED"));

        Map<String, Map<String, Object>> columns = columnsOf(db.jdbc, "research_review_rounds");
        Map<String, Object> passing = passingRound(project, run, 1);
        Map<String, Object> failing = failingRound(project, run, 1);
        SoftAssertions.assertSoftly(soft -> {
            soft.assertThat(columns).as("輪列只在輪有結果時一次寫入，沒有進行中的 status").doesNotContainKey("status");
            soft.assertThat(columns.get("weighted_score")).as("weighted_score 欄位定義（精確數值型別）").containsEntry("data_type", "numeric")
                    .containsEntry("numeric_precision", 5).containsEntry("numeric_scale", 2).containsEntry("is_nullable", "YES");
            soft.assertThat(columns.get("threshold")).as("threshold 欄位定義").containsEntry("data_type", "numeric")
                    .containsEntry("numeric_precision", 5).containsEntry("numeric_scale", 2).containsEntry("is_nullable", "NO")
                    .containsEntry("column_default", "85.00");
            soft.assertThat(columns.get("floor_score")).as("floor_score 欄位定義").containsEntry("data_type", "integer")
                    .containsEntry("is_nullable", "NO").containsEntry("column_default", "60");
            soft.assertThat(columns.get("min_dimension_score")).as("min_dimension_score 欄位定義").containsEntry("data_type", "integer");
            for (String notNull : List.of("precheck_passed", "passed", "verdict", "stage_run_id", "started_at", "finished_at")) {
                soft.assertThat(columns.get(notNull)).as("%s 為 NOT NULL", notNull).containsEntry("is_nullable", "NO");
            }

            expectState(soft, "通過旗標為真而 84.99", tryInsert(db, "research_review_rounds",
                    with(passing, "weighted_score", new BigDecimal("84.99"))), CHECK);
            expectState(soft, "通過旗標為真而 84.95（不四捨五入成 85）", tryInsert(db, "research_review_rounds",
                    with(passing, "weighted_score", new BigDecimal("84.95"))), CHECK);
            expectState(soft, "通過旗標為真而 90.00 但最低維度 59", tryInsert(db, "research_review_rounds",
                    with(passing, "weighted_score", new BigDecimal("90.00"), "min_dimension_score", 59)), CHECK);
            expectState(soft, "通過旗標為真而未結 P1 為 1", tryInsert(db, "research_review_rounds",
                    with(passing, "open_p1_count", 1)), CHECK);
            expectState(soft, "通過旗標為真而預檢未過", tryInsert(db, "research_review_rounds",
                    with(passing, "precheck_passed", false)), CHECK);
            expectState(soft, "通過旗標為真而 verdict 為 REVISE", tryInsert(db, "research_review_rounds",
                    with(passing, "verdict", "REVISE")), CHECK);
            expectState(soft, "通過旗標為真而 weighted_score 為 NULL（NULL 不得靜默通過）", tryInsert(db, "research_review_rounds",
                    with(passing, "weighted_score", null)), CHECK);

            Outcome valid = rolledBack(db, jdbc -> {
                insert(jdbc, "research_review_rounds", passing);
                return jdbc.queryForObject("select weighted_score from console.research_review_rounds where round_no = 1", BigDecimal.class);
            });
            expectOk(soft, "合法通過列", valid);
            soft.assertThat(valid.value()).as("讀回精確值").isEqualTo(new BigDecimal("85.00"));
            Outcome revise = rolledBack(db, jdbc -> {
                insert(jdbc, "research_review_rounds", failing);
                return jdbc.queryForObject("select weighted_score from console.research_review_rounds where round_no = 1", BigDecimal.class);
            });
            expectOk(soft, "未通過列（84.95、最低維度 59、REVISE）", revise);
            soft.assertThat(revise.value()).as("未通過列的 84.95 不被改寫成 85.00").isEqualTo(new BigDecimal("84.95"));
            expectOk(soft, "未通過列（ESCALATE 且 escalated 為真）", tryInsert(db, "research_review_rounds",
                    with(failing, "verdict", "ESCALATE", "escalated", true)));
            expectOk(soft, "顯式 floor_score 為 50 而最低維度 55（CHECK 比對的是 floor_score 欄，不是常數）", tryInsert(db,
                    "research_review_rounds", with(passing, "floor_score", 50, "min_dimension_score", 55)));

            expectState(soft, "passed 為 NULL", tryInsert(db, "research_review_rounds", with(failing, "passed", null)), NOT_NULL);
            expectState(soft, "precheck_passed 為 NULL", tryInsert(db, "research_review_rounds",
                    with(failing, "precheck_passed", null)), NOT_NULL);
            expectState(soft, "verdict 為 NULL", tryInsert(db, "research_review_rounds", with(failing, "verdict", null)), NOT_NULL);
            expectState(soft, "weighted_score 為 100.01", tryInsert(db, "research_review_rounds",
                    with(failing, "weighted_score", new BigDecimal("100.01"))), CHECK);
            expectState(soft, "min_dimension_score 為 101", tryInsert(db, "research_review_rounds",
                    with(failing, "min_dimension_score", 101)), CHECK);
            expectState(soft, "open_p1_count 為 -1", tryInsert(db, "research_review_rounds", with(failing, "open_p1_count", -1)), CHECK);
            expectState(soft, "round_no 為 0（輪號從 1 起）", tryInsert(db, "research_review_rounds", with(failing, "round_no", 0)), CHECK);
            expectState(soft, "verdict 為列舉外值 INVALID", tryInsert(db, "research_review_rounds",
                    with(failing, "verdict", "INVALID")), CHECK);
            expectState(soft, "verdict 為 REVIEW_INVALID（不是輪的 verdict；欄寬 VARCHAR(8) 先擋）", tryInsert(db,
                    "research_review_rounds", with(failing, "verdict", "REVIEW_INVALID")), TOO_LONG);
            expectState(soft, "trigger_kind 為 CRON", tryInsert(db, "research_review_rounds",
                    with(failing, "trigger_kind", "CRON")), CHECK);
            expectState(soft, "fsm_gate_result 為 SKIP", tryInsert(db, "research_review_rounds",
                    with(failing, "fsm_gate_result", "SKIP")), CHECK);
            expectState(soft, "prd_version_no 指向不存在的版本", tryInsert(db, "research_review_rounds",
                    with(failing, "prd_version_no", 99)), FOREIGN_KEY);
            expectState(soft, "stage_run_id 指向不存在的 stage run", tryInsert(db, "research_review_rounds",
                    with(failing, "stage_run_id", UUID.randomUUID())), FOREIGN_KEY);
            expectEnum(soft, db.jdbc, "research_review_rounds", "verdict", "PASS", "REVISE", "ESCALATE");
            expectEnum(soft, db.jdbc, "research_review_rounds", "trigger_kind", "AUTO", "MANUAL", "POST_HUMAN");
            expectEnum(soft, db.jdbc, "research_review_rounds", "fsm_gate_result", "PASS", "FAIL");

            insert(db.jdbc, "research_review_rounds", passing);
            soft.assertThat(db.jdbc.queryForObject("select weighted_score from console.research_review_rounds where round_no = 1",
                    BigDecimal.class)).as("提交的合法列讀回精確值").isEqualByComparingTo("85.00");
            expectState(soft, "同 (research_id, round_no) 的第二筆", tryInsert(db, "research_review_rounds",
                    with(failing, "round_no", 1)), UNIQUE);
        });
    }

    // ── AT_960_1_7：分數、缺陷、Gate 0 決定、PRD 版本 ─────────────────────────────────────────────

    @Test
    void AT_960_1_7_scoresDefectsDecisionsAndPrdVersions() {
        Db db = newDatabase();
        Chain chain = chain(db);
        insert(db.jdbc, "research_review_scores", scoreRow(chain.round(), "ARCHITECTURE"));
        UUID defect = UUID.randomUUID();
        insert(db.jdbc, "research_review_defects", defectRow(defect, chain.round(), "D-1-001"));

        SoftAssertions.assertSoftly(soft -> {
            Map<String, Object> score = scoreRow(chain.round(), "PRODUCT");
            expectState(soft, "weight 為 0", tryInsert(db, "research_review_scores", with(score, "weight", new BigDecimal("0.000"))), CHECK);
            expectState(soft, "weight 為 1.001", tryInsert(db, "research_review_scores",
                    with(score, "weight", new BigDecimal("1.001"))), CHECK);
            expectState(soft, "score 為 -1", tryInsert(db, "research_review_scores", with(score, "score", -1)), CHECK);
            expectState(soft, "score 為 101", tryInsert(db, "research_review_scores", with(score, "score", 101)), CHECK);
            expectState(soft, "dimension 為 DESIGN", tryInsert(db, "research_review_scores", with(score, "dimension", "DESIGN")), CHECK);
            expectState(soft, "同 (round_id, dimension) 重複", tryInsert(db, "research_review_scores",
                    scoreRow(chain.round(), "ARCHITECTURE")), UNIQUE);
            expectState(soft, "assist_agent_id 有值而 assist_agent_yaml_sha256 為 NULL", tryInsert(db, "research_review_scores",
                    with(score, "assist_agent_id", "compliance-officer")), CHECK);
            expectState(soft, "assist_agent_yaml_sha256 有值而 assist_agent_id 為 NULL", tryInsert(db, "research_review_scores",
                    with(score, "assist_agent_yaml_sha256", HEX64)), CHECK);
            expectState(soft, "agent_yaml_sha256 為 63 位", tryInsert(db, "research_review_scores",
                    with(score, "agent_yaml_sha256", "a".repeat(63))), CHECK);
            expectState(soft, "raw_sha256 為 63 位", tryInsert(db, "research_review_scores",
                    with(score, "raw_sha256", "a".repeat(63))), CHECK);
            expectOk(soft, "weight 為 1.000", tryInsert(db, "research_review_scores", with(score, "weight", new BigDecimal("1.000"))));
            expectOk(soft, "assist 兩欄皆有值", tryInsert(db, "research_review_scores",
                    with(score, "assist_agent_id", "compliance-officer", "assist_agent_yaml_sha256", HEX64)));
            expectOk(soft, "assist 兩欄皆為 NULL", tryInsert(db, "research_review_scores", score));
            expectState(soft, "persona_sha256 為 63 位", tryInsert(db, "research_review_scores",
                    with(score, "persona_sha256", "a".repeat(63))), CHECK);
            expectState(soft, "assist_agent_yaml_sha256 為 63 位", tryInsert(db, "research_review_scores",
                    with(score, "assist_agent_id", "compliance-officer", "assist_agent_yaml_sha256", "a".repeat(63))), CHECK);
            expectState(soft, "分數屬於不存在的輪", tryInsert(db, "research_review_scores", scoreRow(UUID.randomUUID(), "PRODUCT")),
                    FOREIGN_KEY);
            expectEnum(soft, db.jdbc, "research_review_scores", "dimension", "ARCHITECTURE", "PRODUCT", "QA", "SECURITY");

            Map<String, Object> defectBase = without(defectRow(UUID.randomUUID(), chain.round(), "D-1-002"), "id");
            expectState(soft, "severity 為 P5", tryInsert(db, "research_review_defects", with(defectBase, "severity", "P5")), CHECK);
            expectState(soft, "status 為列舉外值", tryInsert(db, "research_review_defects", with(defectBase, "status", "CLOSED")), CHECK);
            Map<String, Object> waived = with(defectBase, "status", "WAIVED", "waived_by", "admin", "waiver_reason", "已接受風險",
                    "resolved_at", T1);
            expectOk(soft, "WAIVED 三欄齊備", tryInsert(db, "research_review_defects", waived));
            expectState(soft, "WAIVED 缺 waived_by", tryInsert(db, "research_review_defects", with(waived, "waived_by", null)), CHECK);
            expectState(soft, "WAIVED 缺 waiver_reason", tryInsert(db, "research_review_defects",
                    with(waived, "waiver_reason", null)), CHECK);
            expectState(soft, "WAIVED 缺 resolved_at", tryInsert(db, "research_review_defects",
                    with(waived, "resolved_at", null)), CHECK);
            expectState(soft, "FIXED 缺 resolved_at", tryInsert(db, "research_review_defects", with(defectBase, "status", "FIXED")), CHECK);
            expectState(soft, "SUPERSEDED 缺 resolved_at", tryInsert(db, "research_review_defects",
                    with(defectBase, "status", "SUPERSEDED")), CHECK);
            expectOk(soft, "FIXED 帶 resolved_at", tryInsert(db, "research_review_defects",
                    with(defectBase, "status", "FIXED", "resolved_at", T1)));
            expectOk(soft, "REGRESSED 不要求 resolved_at", tryInsert(db, "research_review_defects",
                    with(defectBase, "status", "REGRESSED")));
            expectState(soft, "同 (round_id, defect_no) 重複", tryInsert(db, "research_review_defects",
                    with(defectBase, "defect_no", "D-1-001")), UNIQUE);
            expectState(soft, "dimension 為 DESIGN", tryInsert(db, "research_review_defects", with(defectBase, "dimension", "DESIGN")), CHECK);
            expectState(soft, "缺陷屬於不存在的輪", tryInsert(db, "research_review_defects", with(defectBase, "round_id", UUID.randomUUID())),
                    FOREIGN_KEY);
            expectEnum(soft, db.jdbc, "research_review_defects", "status", "OPEN", "FIXED", "WAIVED", "SUPERSEDED", "REGRESSED");
            expectEnum(soft, db.jdbc, "research_review_defects", "severity", "P1", "P2", "P3", "P4");
            expectEnum(soft, db.jdbc, "research_review_defects", "dimension", "ARCHITECTURE", "PRODUCT", "QA", "SECURITY");

            Map<String, Object> approved = with(decisionRow(chain.project(), "GATE0", "APPROVED"),
                    "frozen_digests", "{\"01_specs/PRD.md\":\"" + HEX64 + "\"}", "fsm_stage", "Gate-0");
            expectOk(soft, "GATE0 核准帶 digests 與 fsm_stage", tryInsert(db, "research_gate_decisions", approved));
            expectState(soft, "GATE0 核准而 frozen_digests 為空物件", tryInsert(db, "research_gate_decisions",
                    with(approved, "frozen_digests", "{}")), CHECK);
            expectState(soft, "GATE0 核准而 fsm_stage 為 NULL", tryInsert(db, "research_gate_decisions",
                    with(approved, "fsm_stage", null)), CHECK);
            expectOk(soft, "GATE0 的 CHANGES 決定可帶空 digests", tryInsert(db, "research_gate_decisions",
                    decisionRow(chain.project(), "GATE0", "CHANGES")));
            expectOk(soft, "非 GATE0 的核准不受 digests 規則限制", tryInsert(db, "research_gate_decisions",
                    decisionRow(chain.project(), "SCR", "APPROVED")));
            expectState(soft, "gate 為列舉外值", tryInsert(db, "research_gate_decisions",
                    decisionRow(chain.project(), "GATE9", "CHANGES")), CHECK);
            expectState(soft, "decision 為列舉外值", tryInsert(db, "research_gate_decisions",
                    decisionRow(chain.project(), "GATE0", "MAYBE")), CHECK);
            expectState(soft, "決定屬於不存在的研究專案", tryInsert(db, "research_gate_decisions",
                    decisionRow(UUID.randomUUID(), "GATE0", "CHANGES")), FOREIGN_KEY);
            expectEnum(soft, db.jdbc, "research_gate_decisions", "gate", "GATE0", "SCR", "ROUTE", "STAGE2", "SCG4", "SCG5",
                    "ABANDON_KEY");
            expectEnum(soft, db.jdbc, "research_gate_decisions", "decision", "APPROVED", "REJECTED", "CHANGES", "ABANDONED");

            Map<String, Object> prd = prdRow(chain.project(), 2);
            expectState(soft, "semver 為 1.0.0（缺 v 前綴）", tryInsert(db, "research_prd_versions", with(prd, "semver", "1.0.0")), CHECK);
            expectState(soft, "semver 為 v1.0", tryInsert(db, "research_prd_versions", with(prd, "semver", "v1.0")), CHECK);
            expectState(soft, "semver 為 v1.0.0-rc1", tryInsert(db, "research_prd_versions", with(prd, "semver", "v1.0.0-rc1")), CHECK);
            expectOk(soft, "semver 為 v0.3.0-draft", tryInsert(db, "research_prd_versions", with(prd, "semver", "v0.3.0-draft")));
            expectOk(soft, "semver 為 v1.0.0", tryInsert(db, "research_prd_versions", with(prd, "semver", "v1.0.0", "kind", "BASELINE")));
            expectState(soft, "content 為 1048577 位元組", tryInsert(db, "research_prd_versions",
                    with(prd, "content", sql("repeat('a', 1048577)"))), CHECK);
            expectState(soft, "content 為 349526 個三位元組字元（1048578 位元組；位元組不是字元數）", tryInsert(db, "research_prd_versions",
                    with(prd, "content", sql("repeat('中', 349526)"))), CHECK);
            expectOk(soft, "content 為 1048576 位元組", tryInsert(db, "research_prd_versions",
                    with(prd, "content", sql("repeat('a', 1048576)"))));
            expectOk(soft, "content 為 349525 個三位元組字元（1048575 位元組）", tryInsert(db, "research_prd_versions",
                    with(prd, "content", sql("repeat('中', 349525)"))));
            expectState(soft, "sha256 非 64 位十六進位", tryInsert(db, "research_prd_versions", with(prd, "sha256", "g".repeat(64))), CHECK);
            expectState(soft, "parent_version_no 指向不存在的版本", tryInsert(db, "research_prd_versions",
                    with(prd, "parent_version_no", 99)), FOREIGN_KEY);
            expectOk(soft, "parent_version_no 指向既有版本", tryInsert(db, "research_prd_versions", with(prd, "parent_version_no", 1)));
            expectState(soft, "kind 為列舉外值", tryInsert(db, "research_prd_versions", with(prd, "kind", "RELEASE")), CHECK);
            expectState(soft, "同 (research_id, version_no) 重複", tryInsert(db, "research_prd_versions", prdRow(chain.project(), 1)), UNIQUE);
            expectState(soft, "version_no 為 0", tryInsert(db, "research_prd_versions", with(prd, "version_no", 0)), CHECK);
            expectState(soft, "bytes 為 -1", tryInsert(db, "research_prd_versions", with(prd, "bytes", -1)), CHECK);
            expectState(soft, "author_kind 為列舉外值", tryInsert(db, "research_prd_versions", with(prd, "author_kind", "ROBOT")), CHECK);
            expectState(soft, "PRD 版本屬於不存在的研究專案", tryInsert(db, "research_prd_versions", prdRow(UUID.randomUUID(), 1)),
                    FOREIGN_KEY);
            expectEnum(soft, db.jdbc, "research_prd_versions", "kind", "DRAFT", "BASELINE");
            expectEnum(soft, db.jdbc, "research_prd_versions", "author_kind", "AGENT", "HUMAN");
        });
    }

    // ── AT_960_1_8：時間欄一律帶時區 ───────────────────────────────────────────────────────────────

    @Test
    void AT_960_1_8_everyTimeColumnHasTimeZone() {
        String tables = "'" + String.join("', '", RESEARCH_TABLES) + "'";
        Map<String, String> timeColumns = new LinkedHashMap<>();
        springJdbc.queryForList("select table_name || '.' || column_name as col, data_type from information_schema.columns "
                + "where table_schema = 'console' and table_name in (" + tables + ") "
                + "and (column_name like '%\\_at' or column_name in ('occurred_at', 'fetched_at')) order by 1")
                .forEach(column -> timeColumns.put((String) column.get("col"), (String) column.get("data_type")));
        Integer withoutZone = springJdbc.queryForObject("select count(*) from information_schema.columns where table_schema = 'console' "
                + "and table_name in (" + tables + ") and data_type = 'timestamp without time zone'", Integer.class);

        Map<String, String> expected = new LinkedHashMap<>();
        for (String column : List.of("research_projects.created_at", "research_projects.updated_at", "research_projects.archived_at",
                "research_events.occurred_at", "research_stage_runs.created_at", "research_stage_runs.started_at",
                "research_stage_runs.finished_at", "research_artifacts.created_at", "research_sources.first_fetched_at",
                "research_fetches.fetched_at", "research_allowlist_entries.added_at", "research_allowlist_entries.disabled_at",
                "research_prd_versions.created_at", "research_review_rounds.started_at", "research_review_rounds.finished_at",
                "research_review_defects.created_at", "research_review_defects.resolved_at", "research_gate_decisions.decided_at")) {
            expected.put(column, "timestamp with time zone");
        }
        expected.put("research_sources.published_at", "date");
        SoftAssertions.assertSoftly(soft -> {
            soft.assertThat(timeColumns).as("十三張表的時間欄：一律 timestamp with time zone；出版日期 published_at 是 date（非事件時間）")
                    .containsAllEntriesOf(expected);
            timeColumns.forEach((column, type) -> soft.assertThat(type).as(column).isIn("timestamp with time zone", "date"));
            soft.assertThat(withoutZone).as("不存在 timestamp without time zone 欄").isZero();
        });
    }

    // ── AT_960_1_9：stage run 與檔案登記 ───────────────────────────────────────────────────────────

    @Test
    void AT_960_1_9_stageRunsArtifactsAndTheActiveRunIndex() {
        Db db = newDatabase();
        UUID project = project(db, "alpha");
        UUID other = project(db, "beta");
        UUID first = UUID.randomUUID();
        insert(db.jdbc, "research_stage_runs", stageRunRow(first, project, "RESEARCH", 0, 1, "SUCCEEDED"));
        insert(db.jdbc, "research_artifacts", artifactRow(project, "ISSUE_SCOPE", 1));

        SoftAssertions.assertSoftly(soft -> {
            Map<String, Object> queued = stageRunRow(UUID.randomUUID(), project, "DRAFT", 0, 1, "QUEUED");
            expectState(soft, "stage 為 PLAN", tryInsert(db, "research_stage_runs", with(queued, "stage", "PLAN")), CHECK);
            expectState(soft, "round_no 為 -1", tryInsert(db, "research_stage_runs", with(queued, "round_no", -1)), CHECK);
            expectState(soft, "attempt 為 0", tryInsert(db, "research_stage_runs", with(queued, "attempt", 0)), CHECK);
            expectState(soft, "scope_rev 為 0", tryInsert(db, "research_stage_runs", with(queued, "scope_rev", 0)), CHECK);
            expectState(soft, "status 為 PAUSED", tryInsert(db, "research_stage_runs", with(queued, "status", "PAUSED")), CHECK);
            expectState(soft, "playbook_sha256 為 63 位（CHAR(64) 補空白後不合）", tryInsert(db, "research_stage_runs",
                    with(queued, "playbook_sha256", "a".repeat(63))), CHECK);
            expectState(soft, "config_sha256 為 64 位但含 g", tryInsert(db, "research_stage_runs",
                    with(queued, "config_sha256", "g".repeat(64))), CHECK);
            expectState(soft, "同 (research_id, stage, round_no, attempt) 的第二筆", tryInsert(db, "research_stage_runs",
                    stageRunRow(UUID.randomUUID(), project, "RESEARCH", 0, 1, "FAILED")), UNIQUE);
            expectOk(soft, "合法列（BLOCKED_DB）", tryInsert(db, "research_stage_runs", with(queued, "status", "BLOCKED_DB")));
            expectState(soft, "stage run 屬於不存在的研究專案", tryInsert(db, "research_stage_runs",
                    stageRunRow(UUID.randomUUID(), UUID.randomUUID(), "DRAFT", 0, 1, "QUEUED")), FOREIGN_KEY);
            expectEnum(soft, db.jdbc, "research_stage_runs", "stage", "RESEARCH", "DRAFT", "REVIEW", "REVISE", "TCS_DRAFT");
            expectEnum(soft, db.jdbc, "research_stage_runs", "status", "QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED",
                    "BLOCKED_DB");

            Map<String, Object> artifact = artifactRow(project, "ISSUE_SCOPE", 2);
            expectState(soft, "kind 為列舉外值", tryInsert(db, "research_artifacts", with(artifact, "kind", "PRD")), CHECK);
            expectState(soft, "version 為 0", tryInsert(db, "research_artifacts", with(artifact, "version", 0)), CHECK);
            expectState(soft, "sha256 為 63 位", tryInsert(db, "research_artifacts", with(artifact, "sha256", "a".repeat(63))), CHECK);
            expectState(soft, "bytes 為 -1", tryInsert(db, "research_artifacts", with(artifact, "bytes", -1L)), CHECK);
            expectState(soft, "origin 為 USER", tryInsert(db, "research_artifacts", with(artifact, "origin", "USER")), CHECK);
            expectState(soft, "同 (research_id, kind, version) 的第二筆", tryInsert(db, "research_artifacts",
                    artifactRow(project, "ISSUE_SCOPE", 1)), UNIQUE);
            expectState(soft, "content 為 1048577 位元組", tryInsert(db, "research_artifacts",
                    with(artifact, "content", sql("repeat('a', 1048577)"))), CHECK);
            expectState(soft, "content 為 349526 個三位元組字元（1048578 位元組）", tryInsert(db, "research_artifacts",
                    with(artifact, "content", sql("repeat('中', 349526)"))), CHECK);
            expectState(soft, "檔案登記屬於不存在的研究專案", tryInsert(db, "research_artifacts",
                    artifactRow(UUID.randomUUID(), "ISSUE_SCOPE", 1)), FOREIGN_KEY);
            expectState(soft, "檔案登記的 stage_run_id 指向不存在的 stage run", tryInsert(db, "research_artifacts",
                    with(artifact, "stage_run_id", UUID.randomUUID())), FOREIGN_KEY);
            expectOk(soft, "合法列（content 為 NULL）", tryInsert(db, "research_artifacts", artifact));
            expectOk(soft, "content 恰 1048576 位元組", tryInsert(db, "research_artifacts",
                    with(artifact, "content", sql("repeat('a', 1048576)"))));
            expectOk(soft, "content 為 349525 個三位元組字元（1048575 位元組）", tryInsert(db, "research_artifacts",
                    with(artifact, "content", sql("repeat('中', 349525)"))));
            expectEnum(soft, db.jdbc, "research_artifacts", "kind", "ISSUE_SCOPE", "EVIDENCE_ITEMS", "EVIDENCE_MATRIX", "PRD_DRAFT",
                    "PRD_BASELINE", "ADR_DRAFT", "REVIEW_CARD", "ROUTE_DECISION", "STATE_EXPORT", "TASK_DECOMPOSITION", "TCS",
                    "HEALING_LOG");
            expectEnum(soft, db.jdbc, "research_artifacts", "origin", "AGENT", "HUMAN", "BRIDGE");

            // 同一研究專案同時至多一個 QUEUED 或 RUNNING 的 stage run（部分唯一索引；並行上限 1 由資料庫守）
            UUID active = UUID.randomUUID();
            insert(db.jdbc, "research_stage_runs", stageRunRow(active, project, "DRAFT", 0, 1, "QUEUED"));
            activeIndexRejects(soft, db, "已有 QUEUED 時再插 RUNNING", stageRunRow(UUID.randomUUID(), project, "DRAFT", 0, 2, "RUNNING"));
            activeIndexRejects(soft, db, "已有 QUEUED 時再插 QUEUED", stageRunRow(UUID.randomUUID(), project, "DRAFT", 0, 3, "QUEUED"));
            db.jdbc.update("update console.research_stage_runs set status = 'RUNNING' where id = ?", active);
            activeIndexRejects(soft, db, "已有 RUNNING 時再插 QUEUED", stageRunRow(UUID.randomUUID(), project, "DRAFT", 0, 4, "QUEUED"));
            activeIndexRejects(soft, db, "已有 RUNNING 時再插 RUNNING", stageRunRow(UUID.randomUUID(), project, "DRAFT", 0, 5, "RUNNING"));
            expectOk(soft, "已有 RUNNING 時插 SUCCEEDED 終態列", tryInsert(db, "research_stage_runs",
                    stageRunRow(UUID.randomUUID(), project, "DRAFT", 0, 6, "SUCCEEDED")));
            expectOk(soft, "已有 RUNNING 時插 BLOCKED_DB 終態列", tryInsert(db, "research_stage_runs",
                    stageRunRow(UUID.randomUUID(), project, "DRAFT", 0, 7, "BLOCKED_DB")));
            expectOk(soft, "另一個研究專案可有自己的 RUNNING", tryInsert(db, "research_stage_runs",
                    stageRunRow(UUID.randomUUID(), other, "DRAFT", 0, 1, "RUNNING")));
            db.jdbc.update("update console.research_stage_runs set status = 'SUCCEEDED' where id = ?", active);
            expectOk(soft, "原 RUNNING 轉 SUCCEEDED 後可再插 RUNNING", tryInsert(db, "research_stage_runs",
                    stageRunRow(UUID.randomUUID(), project, "DRAFT", 0, 8, "RUNNING")));
        });
    }

    private static void activeIndexRejects(SoftAssertions soft, Db db, String label, Map<String, Object> run) {
        Outcome outcome = tryInsert(db, "research_stage_runs", run);
        expectState(soft, label, outcome, UNIQUE);
        soft.assertThat(outcome.message()).as("%s：是進行中 stage run 的部分唯一索引擋下的", label).contains("ux_research_stage_runs_active");
    }

    // ── AT_960_1_E_3：抓取紀錄與證據列 ─────────────────────────────────────────────────────────────

    @Test
    void AT_960_1_E_3_fetchesAndEvidenceItemsChecks() {
        Db db = newDatabase();
        UUID project = project(db, "evidence");
        UUID source = UUID.randomUUID();
        insert(db.jdbc, "research_sources", sourceRow(source, project, "S-001", "https://example.org/s1"));
        insert(db.jdbc, "research_evidence_items", evidenceRow(project, source, 1, "E-001"));

        Map<String, Map<String, Object>> evidenceColumns = columnsOf(db.jdbc, "research_evidence_items");
        Map<String, Map<String, Object>> fetchColumns = columnsOf(db.jdbc, "research_fetches");
        Map<String, Map<String, Object>> artifactColumns = columnsOf(db.jdbc, "research_artifacts");

        SoftAssertions.assertSoftly(soft -> {
            soft.assertThat(evidenceColumns.get("unanchored")).as("unanchored 欄位定義：boolean、NOT NULL、預設 false（D-51）")
                    .containsEntry("data_type", "boolean").containsEntry("is_nullable", "NO").containsEntry("column_default", "false");
            soft.assertThat(evidenceColumns.get("candidate")).as("candidate 可為 NULL").containsEntry("is_nullable", "YES");
            soft.assertThat(fetchColumns.get("fetch_no")).as("fetch_no 欄位定義").containsEntry("data_type", "character varying")
                    .containsEntry("is_nullable", "NO").containsEntry("character_maximum_length", 10);
            soft.assertThat(fetchColumns.get("search_no")).as("search_no 欄位定義").containsEntry("data_type", "integer")
                    .containsEntry("is_nullable", "YES");
            soft.assertThat(fetchColumns.get("result_urls")).as("result_urls 欄位定義").containsEntry("data_type", "jsonb")
                    .containsEntry("is_nullable", "NO");
            soft.assertThat(fetchColumns.get("host")).as("host 可為 NULL（WEB_SEARCH 列無單一網址）").containsEntry("is_nullable", "YES");
            soft.assertThat(fetchColumns.get("url")).as("url 可為 NULL（WEB_SEARCH 列無單一網址）").containsEntry("is_nullable", "YES");
            soft.assertThat(artifactColumns.get("content")).as("content 欄位定義").containsEntry("data_type", "text")
                    .containsEntry("is_nullable", "YES");

            Map<String, Object> fetch = fetchRow(project, "F-0001");
            expectState(soft, "layer 為列舉外值", tryInsert(db, "research_fetches", with(fetch, "layer", "WEB")), CHECK);
            expectState(soft, "fetch_method 為列舉外值", tryInsert(db, "research_fetches", with(fetch, "fetch_method", "CURL")), CHECK);
            expectState(soft, "observed_by 為列舉外值", tryInsert(db, "research_fetches", with(fetch, "observed_by", "USER")), CHECK);
            expectState(soft, "outcome 為列舉外值", tryInsert(db, "research_fetches", with(fetch, "outcome", "FAILED")), CHECK);
            expectState(soft, "raw_sha256 為 63 位", tryInsert(db, "research_fetches", with(fetch, "raw_sha256", "a".repeat(63))), CHECK);
            expectState(soft, "raw_bytes 為 -1", tryInsert(db, "research_fetches", with(fetch, "raw_bytes", -1L)), CHECK);
            expectOk(soft, "被拒外呼：DENIED_PRIVATE_IP 且 raw_sha256 為 NULL", tryInsert(db, "research_fetches",
                    with(fetch, "outcome", "DENIED_PRIVATE_IP", "raw_sha256", null)));
            expectState(soft, "抓取紀錄屬於不存在的研究專案", tryInsert(db, "research_fetches", fetchRow(UUID.randomUUID(), "F-0001")),
                    FOREIGN_KEY);
            expectState(soft, "抓取紀錄的 source_id 指向不存在的來源", tryInsert(db, "research_fetches",
                    with(fetch, "source_id", UUID.randomUUID())), FOREIGN_KEY);
            expectState(soft, "抓取紀錄的 stage_run_id 指向不存在的 stage run", tryInsert(db, "research_fetches",
                    with(fetch, "stage_run_id", UUID.randomUUID())), FOREIGN_KEY);
            expectEnum(soft, db.jdbc, "research_fetches", "layer", "ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY");
            expectEnum(soft, db.jdbc, "research_fetches", "fetch_method", "API", "WEB_FETCH", "WEB_SEARCH", "MANUAL");
            expectEnum(soft, db.jdbc, "research_fetches", "observed_by", "BRIDGE", "AGENT_DECLARED");
            expectEnum(soft, db.jdbc, "research_fetches", "outcome", "OK", "DENIED_ALLOWLIST", "DENIED_PRIVATE_IP", "HTTP_ERROR",
                    "TIMEOUT", "TOO_LARGE", "PARSE_ERROR", "RATE_LIMITED");

            Map<String, Object> evidence = evidenceRow(project, source, 2, "E-002");
            expectState(soft, "evidence_no 為 E-1", tryInsert(db, "research_evidence_items", with(evidence, "evidence_no", "E-1")), CHECK);
            expectState(soft, "matrix_version 為 0", tryInsert(db, "research_evidence_items", with(evidence, "matrix_version", 0)), CHECK);
            expectState(soft, "scope_rev 為 0", tryInsert(db, "research_evidence_items", with(evidence, "scope_rev", 0)), CHECK);
            expectState(soft, "f7_verification 為 V0", tryInsert(db, "research_evidence_items",
                    with(evidence, "f7_verification", "V0")), CHECK);
            expectState(soft, "strength 為列舉外值", tryInsert(db, "research_evidence_items", with(evidence, "strength", "ULTRA")), CHECK);
            expectState(soft, "同 (research_id, matrix_version, evidence_no) 的第二筆", tryInsert(db, "research_evidence_items",
                    evidenceRow(project, source, 1, "E-001")), UNIQUE);
            expectState(soft, "證據列的 source_id 指向不存在的來源", tryInsert(db, "research_evidence_items",
                    with(evidence, "source_id", UUID.randomUUID())), FOREIGN_KEY);
            expectOk(soft, "合法列", tryInsert(db, "research_evidence_items", evidence));
            expectEnum(soft, db.jdbc, "research_evidence_items", "f7_verification", "V1", "V2", "V3");
            expectEnum(soft, db.jdbc, "research_evidence_items", "strength", "STRONG", "MEDIUM", "WEAK", "CANDIDATE");

            Outcome unspecified = rolledBack(db, jdbc -> {
                insert(jdbc, "research_evidence_items", evidence);
                return jdbc.queryForMap("select unanchored, strength, candidate from console.research_evidence_items "
                        + "where matrix_version = 2");
            });
            expectOk(soft, "未指定 unanchored、strength 與 candidate", unspecified);
            if (unspecified.ok()) {
                soft.assertThat(mapOf(unspecified.value())).as("預設值：unanchored 為 false、strength 為 WEAK、candidate 可為 NULL")
                        .containsEntry("unanchored", false).containsEntry("strength", "WEAK").containsEntry("candidate", null);
            }
            expectState(soft, "unanchored 為 NULL", tryInsert(db, "research_evidence_items",
                    with(evidence, "unanchored", null)), NOT_NULL);
            Outcome anchored = rolledBack(db, jdbc -> {
                insert(jdbc, "research_evidence_items", with(evidence, "unanchored", true, "candidate", null));
                return jdbc.queryForObject("select unanchored from console.research_evidence_items where matrix_version = 2",
                        Boolean.class);
            });
            expectOk(soft, "unanchored 為 TRUE（且 candidate 為 NULL）", anchored);
            soft.assertThat(anchored.value()).as("讀回 unanchored").isEqualTo(true);
        });
    }

    // ── AT_960_1_E_4：缺陷 status 只准單向轉移 ─────────────────────────────────────────────────────

    @Test
    void AT_960_1_E_4_defectStatusIsOneWay() {
        Db db = newDatabase();
        Chain chain = chain(db);
        List<String> statuses = List.of("OPEN", "FIXED", "WAIVED", "SUPERSEDED", "REGRESSED");
        Map<String, UUID> defectIds = new LinkedHashMap<>();
        for (int i = 0; i < statuses.size(); i++) {
            String status = statuses.get(i);
            UUID id = UUID.randomUUID();
            defectIds.put(status, id);
            Map<String, Object> defect = with(defectRow(id, chain.round(), "D-1-00" + (i + 1)), "status", status);
            if (!"OPEN".equals(status)) {
                defect = with(defect, "resolved_at", T1);
            }
            if ("WAIVED".equals(status)) {
                defect = with(defect, "waived_by", "admin", "waiver_reason", "已接受風險");
            }
            insert(db.jdbc, "research_review_defects", defect);
        }
        Set<String> allowedMoves = Set.of("OPEN>FIXED", "OPEN>WAIVED", "OPEN>SUPERSEDED", "FIXED>REGRESSED", "REGRESSED>FIXED");
        String before = snapshot(db.jdbc, "research_review_defects");

        SoftAssertions.assertSoftly(soft -> {
            for (String from : statuses) {
                for (String to : statuses) {
                    StringBuilder set = new StringBuilder("status = '" + to + "'");
                    if (Set.of("FIXED", "WAIVED", "SUPERSEDED").contains(to)) {
                        set.append(", resolved_at = now()");
                    }
                    if ("WAIVED".equals(to)) {
                        set.append(", waived_by = 'admin', waiver_reason = '已接受風險'");
                    }
                    Outcome outcome = rolledBack(db, jdbc -> jdbc.update("update console.research_review_defects set " + set
                            + " where id = ?", defectIds.get(from)));
                    String move = from + "→" + to;
                    if (from.equals(to) || allowedMoves.contains(from + ">" + to)) {
                        expectOk(soft, move, outcome);
                    } else {
                        expectGuard(soft, move, outcome, "research_review_defects", "status");
                    }
                }
            }
            UUID open = defectIds.get("OPEN");
            expectOk(soft, "OPEN 列只更新 resolved_at（status 不變，不受單向守衛限制）", rolledBack(db, jdbc -> jdbc.update(
                    "update console.research_review_defects set resolved_at = now() where id = ?", open)));
            expectState(soft, "OPEN→FIXED 而缺 resolved_at", rolledBack(db, jdbc -> jdbc.update(
                    "update console.research_review_defects set status = 'FIXED' where id = ?", open)), CHECK);
            expectState(soft, "OPEN→SUPERSEDED 而缺 resolved_at", rolledBack(db, jdbc -> jdbc.update(
                    "update console.research_review_defects set status = 'SUPERSEDED' where id = ?", open)), CHECK);
            expectState(soft, "OPEN→WAIVED 而缺 waived_by", rolledBack(db, jdbc -> jdbc.update("update console.research_review_defects "
                    + "set status = 'WAIVED', waiver_reason = '理由', resolved_at = now() where id = ?", open)), CHECK);
            expectState(soft, "OPEN→WAIVED 而缺 waiver_reason", rolledBack(db, jdbc -> jdbc.update("update console.research_review_defects "
                    + "set status = 'WAIVED', waived_by = 'admin', resolved_at = now() where id = ?", open)), CHECK);
            expectState(soft, "OPEN→WAIVED 而缺 resolved_at", rolledBack(db, jdbc -> jdbc.update("update console.research_review_defects "
                    + "set status = 'WAIVED', waived_by = 'admin', waiver_reason = '理由' where id = ?", open)), CHECK);
            soft.assertThat(snapshot(db.jdbc, "research_review_defects")).as("全部組合之後 defect_no、dimension、severity、code 等欄位與插入時相同")
                    .isEqualTo(before);
        });
    }

    // ── AT_960_1_E_5：來源查證層級只升不降 ─────────────────────────────────────────────────────────

    @Test
    void AT_960_1_E_5_sourceVerificationOnlyGoesUp() {
        Db db = newDatabase();
        UUID project = project(db, "verify");
        List<String> levels = List.of("V1", "V2", "V3");
        Map<String, UUID> sourceIds = new LinkedHashMap<>();
        for (int i = 0; i < levels.size(); i++) {
            UUID id = UUID.randomUUID();
            sourceIds.put(levels.get(i), id);
            insert(db.jdbc, "research_sources", with(sourceRow(id, project, "S-00" + (i + 1), "https://example.org/v" + (i + 1)),
                    "verification", levels.get(i)));
        }
        String before = snapshot(db.jdbc, "research_sources");

        SoftAssertions.assertSoftly(soft -> {
            for (String from : levels) {
                Map<String, Object> original = db.jdbc.queryForMap("select * from console.research_sources where id = ?",
                        sourceIds.get(from));
                for (String to : levels) {
                    Outcome outcome = rolledBack(db, jdbc -> {
                        jdbc.update("update console.research_sources set verification = ? where id = ?", to, sourceIds.get(from));
                        return jdbc.queryForMap("select * from console.research_sources where id = ?", sourceIds.get(from));
                    });
                    String move = from + "→" + to;
                    if (to.compareTo(from) >= 0) {
                        expectOk(soft, move + (to.equals(from) ? "（不變，不算降級）" : "（升級）"), outcome);
                        if (outcome.ok()) {
                            Map<?, ?> after = (Map<?, ?>) outcome.value();
                            soft.assertThat(after.get("verification")).as("%s 之後的查證層級", move).isEqualTo(to);
                            original.forEach((column, value) -> {
                                if (!"verification".equals(column)) {
                                    soft.assertThat(after.get(column)).as("%s：只有 verification 改變，%s 不變", move, column).isEqualTo(value);
                                }
                            });
                        }
                    } else {
                        expectGuard(soft, move + "（降級）", outcome, "research_sources", "verification");
                    }
                }
            }
            soft.assertThat(snapshot(db.jdbc, "research_sources")).as("被拒的降級沒有留下任何變動").isEqualTo(before);
        });
    }

    // ── AT_960_1_E_6：受控可更新表的通用守衛 ───────────────────────────────────────────────────────

    @Test
    void AT_960_1_E_6_controlledUpdateGuardMatrix() {
        Db db = newDatabase();
        Chain chain = chain(db);
        UUID consoleProject = UUID.randomUUID();
        db.jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria) values (?,?,?,?)",
                consoleProject, "console-p", "/x", "c");
        UUID source = UUID.randomUUID();
        insert(db.jdbc, "research_sources", sourceRow(source, chain.project(), "S-001", "https://example.org/s1"));
        UUID defect = UUID.randomUUID();
        insert(db.jdbc, "research_review_defects", defectRow(defect, chain.round(), "D-1-001"));
        UUID entry = UUID.randomUUID();
        insert(db.jdbc, "research_allowlist_entries", with(allowlistRow("export.arxiv.org"), "id", entry));
        Map<String, UUID> rowIds = new LinkedHashMap<>();
        rowIds.put("research_projects", chain.project());
        rowIds.put("research_stage_runs", chain.run());
        rowIds.put("research_sources", source);
        rowIds.put("research_review_defects", defect);
        rowIds.put("research_allowlist_entries", entry);

        SoftAssertions.assertSoftly(soft -> {
            for (String table : CONTROLLED_TABLES) {
                checkControlledTable(soft, db, table, rowIds.get(table), consoleProject);
            }
            checkReviewRoundsAreAppendOnly(soft, db, chain.round());
        });

        List<Map<String, Object>> wiring = db.jdbc.queryForList("select c.relname, (t.tgtype & 1) <> 0 as is_row, "
                + "(t.tgtype & 2) <> 0 as is_before, (t.tgtype & 4) <> 0 as on_insert, (t.tgtype & 8) <> 0 as on_delete, "
                + "(t.tgtype & 16) <> 0 as on_update from pg_trigger t join pg_class c on c.oid = t.tgrelid "
                + "join pg_proc p on p.oid = t.tgfoid join pg_namespace n on n.oid = p.pronamespace "
                + "where n.nspname = 'console' and p.proname = 'research_controlled_update_guard' and not t.tgisinternal");
        List<String> allControlled = new ArrayList<>(CONTROLLED_TABLES);
        allControlled.addAll(V19_CONTROLLED_TABLES);
        assertThat(wiring).extracting(trigger -> trigger.get("relname")).as("引用通用守衛的表恰為九張（P0 五張加 V19 四張；不含審查輪表與 research_deliveries）")
                .containsExactlyInAnyOrderElementsOf(allControlled);
        assertThat(wiring).allSatisfy(trigger -> {
            assertThat(trigger).as("BEFORE、FOR EACH ROW、涵蓋 UPDATE 與 DELETE、不含 INSERT")
                    .containsEntry("is_row", true).containsEntry("is_before", true).containsEntry("on_update", true)
                    .containsEntry("on_delete", true).containsEntry("on_insert", false);
        });
    }

    private static void checkControlledTable(SoftAssertions soft, Db db, String table, UUID id, UUID consoleProject) {
        Map<String, String> allowed = CONTROLLED_UPDATE_COLUMNS.get(table);
        String before = snapshot(db.jdbc, table);
        String companion = allowed.values().iterator().next().replace("%CP%", consoleProject.toString());

        // （一）每個允許欄各自更新成功，且列真的變了
        allowed.forEach((column, set) -> {
            Outcome outcome = rolledBack(db, jdbc -> {
                jdbc.update("update console." + table + " set " + set.replace("%CP%", consoleProject.toString()) + " where id = ?", id);
                return snapshot(jdbc, table);
            });
            expectOk(soft, table + " 允許欄 " + column, outcome);
            if (outcome.ok()) {
                soft.assertThat(outcome.value()).as("%s 更新 %s 之後列確實改變", table, column).isNotEqualTo(before);
            }
        });

        for (Map<String, Object> column : db.jdbc.queryForList("select column_name, data_type from information_schema.columns "
                + "where table_schema = 'console' and table_name = ? order by ordinal_position", table)) {
            String name = (String) column.get("column_name");
            if (allowed.containsKey(name)) {
                continue;
            }
            String different = differentValueExpr(name, (String) column.get("data_type"));
            // （二）非允許欄：訊息含表名與允許欄清單
            Outcome alone = run(db, jdbc -> jdbc.update("update console." + table + " set " + name + " = " + different
                    + " where id = ?", id));
            expectGuard(soft, table + " 非允許欄 " + name, alone, table);
            // （三）同一句夾帶允許欄：整句被擋
            Outcome together = run(db, jdbc -> jdbc.update("update console." + table + " set " + companion + ", " + name + " = "
                    + different + " where id = ?", id));
            expectGuard(soft, table + " 允許欄夾帶非允許欄 " + name, together, table);
            for (String allowedColumn : allowed.keySet()) {
                soft.assertThat(String.valueOf(alone.message())).as("%s 的拒絕訊息列出允許欄 %s", table, allowedColumn)
                        .contains(allowedColumn);
            }
            // （四）非允許欄但值與原值相同：不算更新該欄
            expectOk(soft, table + " 非允許欄 " + name + " 值不變", rolledBack(db, jdbc -> jdbc.update("update console." + table
                    + " set " + name + " = " + name + " where id = ?", id)));
        }

        // （五）任何 DELETE 都被拒，列仍在
        expectGuard(soft, table + " DELETE", run(db, jdbc -> jdbc.update("delete from console." + table + " where id = ?", id)), table);
        soft.assertThat(snapshot(db.jdbc, table)).as("%s 全程列不變（被拒的語句沒有留下任何效果）", table).isEqualTo(before);
    }

    /** （六）審查輪表不在受控清單內：任一欄位的 UPDATE（含同值）與 DELETE 都被 append-only 守衛拒絕。 */
    private static void checkReviewRoundsAreAppendOnly(SoftAssertions soft, Db db, UUID round) {
        String before = snapshot(db.jdbc, "research_review_rounds");
        for (Map<String, Object> column : db.jdbc.queryForList("select column_name, data_type from information_schema.columns "
                + "where table_schema = 'console' and table_name = 'research_review_rounds' order by ordinal_position")) {
            String name = (String) column.get("column_name");
            String different = differentValueExpr(name, (String) column.get("data_type"));
            expectGuard(soft, "審查輪表 UPDATE " + name, run(db, jdbc -> jdbc.update("update console.research_review_rounds set "
                    + name + " = " + different + " where id = ?", round)), "research_review_rounds", "append-only");
            expectGuard(soft, "審查輪表同值 UPDATE " + name, run(db, jdbc -> jdbc.update("update console.research_review_rounds set "
                    + name + " = " + name + " where id = ?", round)), "research_review_rounds", "append-only");
        }
        expectGuard(soft, "審查輪表 DELETE", run(db, jdbc -> jdbc.update("delete from console.research_review_rounds where id = ?",
                round)), "research_review_rounds", "append-only");
        soft.assertThat(snapshot(db.jdbc, "research_review_rounds")).as("審查輪列不變").isEqualTo(before);
    }

    /** 依欄位型別組出「一定與目前值不同」的伺服端運算式；只求型別正確（守衛在 CHECK 與外鍵之前就拒絕）。 */
    private static String differentValueExpr(String column, String dataType) {
        return switch (dataType) {
            case "uuid" -> "gen_random_uuid()";
            case "character varying", "character", "text" -> "case when " + column + "::text = 'zz' then 'yy' else 'zz' end";
            case "integer", "bigint", "smallint", "numeric" -> "coalesce(" + column + ", 0) + 7";
            case "boolean" -> "not coalesce(" + column + ", false)";
            case "timestamp with time zone" -> "coalesce(" + column + ", now()) + interval '1 day'";
            case "date" -> "coalesce(" + column + ", current_date) + 1";
            case "jsonb" -> "coalesce(" + column + ", '{}'::jsonb) || '{\"zz\":1}'::jsonb";
            case "ARRAY" -> "coalesce(" + column + "::text[], '{}'::text[]) || 'zz'::text";
            default -> throw new IllegalStateException("未處理的欄位型別 " + dataType + "（" + column + "）");
        };
    }

    // ── AT_960_1_E_7：審查輪的 CHECK 群 ────────────────────────────────────────────────────────────

    @Test
    void AT_960_1_E_7_reviewRoundCheckGroup() {
        Db db = newDatabase();
        UUID project = project(db, "checks");
        UUID run = UUID.randomUUID();
        insert(db.jdbc, "research_prd_versions", prdRow(project, 1));
        insert(db.jdbc, "research_stage_runs", stageRunRow(run, project, "REVIEW", 1, 1, "SUCCEEDED"));

        SoftAssertions.assertSoftly(soft -> {
            // 通過的輪（取 AUTO／MANUAL／POST_HUMAN 與 gate 結果組合）與未通過的輪；gate 結果帶 retry_count，NULL 則兩者同為 NULL
            round(soft, db, "一 POST_HUMAN 通過、gate 為 NULL", gatedPassing(project, run, "POST_HUMAN", null), null);
            round(soft, db, "二 POST_HUMAN 通過、gate 為 PASS", gatedPassing(project, run, "POST_HUMAN", "PASS"), CHECK);
            round(soft, db, "三 AUTO 通過、gate 為 PASS", gatedPassing(project, run, "AUTO", "PASS"), null);
            round(soft, db, "四 AUTO 通過、gate 為 NULL", gatedPassing(project, run, "AUTO", null), CHECK);
            round(soft, db, "五 MANUAL 通過、gate 為 NULL", gatedPassing(project, run, "MANUAL", null), CHECK);
            round(soft, db, "六 MANUAL 通過、gate 為 PASS", gatedPassing(project, run, "MANUAL", "PASS"), null);

            Map<String, Object> precheckFailed = with(gatedFailing(project, run, "AUTO", "FAIL"), "precheck_passed", false,
                    "weighted_score", null, "min_dimension_score", null);
            round(soft, db, "七 預檢未過、不計分、gate 為 FAIL", precheckFailed, null);
            round(soft, db, "八 預檢未過而 weighted_score 非 NULL", with(precheckFailed, "weighted_score", new BigDecimal("84.95")), CHECK);
            round(soft, db, "九 預檢未過而 min_dimension_score 非 NULL", with(precheckFailed, "min_dimension_score", 59), CHECK);
            round(soft, db, "十 預檢未過而通過旗標為真", with(gatedPassing(project, run, "AUTO", "PASS"), "precheck_passed", false), CHECK);

            round(soft, db, "十一 POST_HUMAN 未通過、gate 為 FAIL（再審未通過仍呼叫 gate FAIL）", gatedFailing(project, run, "POST_HUMAN", "FAIL"), null);
            round(soft, db, "十二 AUTO 未通過、gate 為 FAIL", gatedFailing(project, run, "AUTO", "FAIL"), null);
            round(soft, db, "十三 AUTO 未通過、gate 為 NULL", gatedFailing(project, run, "AUTO", null), CHECK);
            round(soft, db, "十四 MANUAL 未通過、gate 為 PASS", gatedFailing(project, run, "MANUAL", "PASS"), CHECK);
            round(soft, db, "十五 POST_HUMAN 未通過、gate 為 NULL", gatedFailing(project, run, "POST_HUMAN", null), CHECK);

            Map<String, Object> autoPass = gatedPassing(project, run, "AUTO", "PASS");
            Map<String, Object> autoFail = gatedFailing(project, run, "AUTO", "FAIL");
            round(soft, db, "十六 finished_at 早於 started_at", with(autoPass, "started_at", T1, "finished_at", T0), CHECK);
            round(soft, db, "十七 finished_at 為 NULL", with(autoPass, "finished_at", null), NOT_NULL);
            round(soft, db, "十七 started_at 為 NULL", with(autoPass, "started_at", null), NOT_NULL);
            round(soft, db, "十七 stage_run_id 為 NULL", with(autoPass, "stage_run_id", null), NOT_NULL);
            round(soft, db, "十八 未通過而 verdict 為 PASS", with(autoFail, "verdict", "PASS"), CHECK);
            round(soft, db, "十九 通過而 verdict 為 REVISE", with(autoPass, "verdict", "REVISE"), CHECK);
            round(soft, db, "二十 escalated 為真而 verdict 為 REVISE", with(autoFail, "escalated", true), CHECK);
            round(soft, db, "二十一 verdict 為 ESCALATE 而 escalated 為假", with(autoFail, "verdict", "ESCALATE"), CHECK);
            round(soft, db, "二十二 verdict 為 ESCALATE、escalated 為真", with(autoFail, "verdict", "ESCALATE", "escalated", true), null);
            round(soft, db, "二十三 gate 為 FAIL 而 fsm_retry_count 為 NULL", with(autoFail, "fsm_retry_count", null), CHECK);
            round(soft, db, "二十四 POST_HUMAN 通過、gate 為 NULL 而 fsm_retry_count 為 0",
                    with(gatedPassing(project, run, "POST_HUMAN", null), "fsm_retry_count", 0), CHECK);

            round(soft, db, "二十五 threshold 為 49.99", with(autoFail, "threshold", new BigDecimal("49.99")), CHECK);
            round(soft, db, "二十五 threshold 為 100.01", with(autoFail, "threshold", new BigDecimal("100.01")), CHECK);
            round(soft, db, "二十五 threshold 為 0", with(autoFail, "threshold", new BigDecimal("0.00")), CHECK);
            round(soft, db, "二十五 threshold 為 50.00", with(autoFail, "threshold", new BigDecimal("50.00")), null);
            round(soft, db, "二十五 threshold 為 100.00", with(autoFail, "threshold", new BigDecimal("100.00")), null);

            round(soft, db, "二十六 floor_score 為 0（每維度地板被架空）", with(autoPass, "floor_score", 0, "min_dimension_score", 10), CHECK);
            round(soft, db, "二十六 floor_score 為 49", with(autoPass, "floor_score", 49, "min_dimension_score", 60), CHECK);
            round(soft, db, "二十六 floor_score 為 101", with(autoFail, "floor_score", 101), CHECK);
            round(soft, db, "二十六 floor_score 為 50", with(autoPass, "floor_score", 50, "min_dimension_score", 60), null);
            round(soft, db, "二十六 floor_score 為 100", with(autoPass, "floor_score", 100, "min_dimension_score", 100), null);

            insert(db.jdbc, "research_review_rounds", gatedPassing(project, run, "AUTO", "PASS"));
            soft.assertThat(db.jdbc.queryForObject("select count(*) from console.research_review_rounds where round_no = 1",
                    Integer.class)).as("被拒的列不占用輪號：之後以同輪號插入合法列成功").isEqualTo(1);
        });
    }

    private static void round(SoftAssertions soft, Db db, String label, Map<String, Object> row, String expectedState) {
        Outcome outcome = tryInsert(db, "research_review_rounds", row);
        if (expectedState == null) {
            expectOk(soft, label, outcome);
        } else {
            expectState(soft, label, outcome, expectedState);
        }
    }

    /** 通過旗標為真的輪，帶指定觸發種類與 gate 結果（gate 為 NULL 時 fsm_retry_count 亦為 NULL）。 */
    private static Map<String, Object> gatedPassing(UUID project, UUID run, String trigger, String gate) {
        return with(passingRound(project, run, 1), "trigger_kind", trigger, "fsm_gate_result", gate,
                "fsm_retry_count", gate == null ? null : 0);
    }

    /** 通過旗標為假的輪，帶指定觸發種類與 gate 結果（gate 為 NULL 時 fsm_retry_count 亦為 NULL）。 */
    private static Map<String, Object> gatedFailing(UUID project, UUID run, String trigger, String gate) {
        return with(failingRound(project, run, 1), "trigger_kind", trigger, "fsm_gate_result", gate,
                "fsm_retry_count", gate == null ? null : 1);
    }

    // ── AT_960_1_E_8：抓取紀錄的編號、唯一性與 WEB_SEARCH 互斥 ─────────────────────────────────────

    @Test
    void AT_960_1_E_8_fetchNumberingAndWebSearchMutualExclusion() {
        Db db = newDatabase();
        UUID alpha = project(db, "alpha");
        UUID beta = project(db, "beta");
        UUID run = UUID.randomUUID();
        insert(db.jdbc, "research_stage_runs", stageRunRow(run, alpha, "RESEARCH", 0, 1, "RUNNING"));
        insert(db.jdbc, "research_fetches", with(fetchRow(alpha, "F-0001"), "stage_run_id", run));
        insert(db.jdbc, "research_fetches", with(searchRow(alpha, "F-0002"), "search_no", 1, "stage_run_id", run));

        SoftAssertions.assertSoftly(soft -> {
            Map<String, Object> fetch = fetchRow(alpha, "F-0100");
            for (String badNo : List.of("F-1", "F-001", "f-0001", "F-0001x")) {
                expectState(soft, "fetch_no 為 " + badNo, tryInsert(db, "research_fetches", with(fetch, "fetch_no", badNo)), CHECK);
            }
            expectState(soft, "fetch_no 為 NULL", tryInsert(db, "research_fetches", with(fetch, "fetch_no", null)), NOT_NULL);
            expectOk(soft, "fetch_no 超過四位數不受限", tryInsert(db, "research_fetches", with(fetch, "fetch_no", "F-10000")));
            expectState(soft, "甲內同 fetch_no 的第二筆", tryInsert(db, "research_fetches", fetchRow(alpha, "F-0001")), UNIQUE);
            expectOk(soft, "乙內同 fetch_no（唯一性以研究專案為界）", tryInsert(db, "research_fetches", fetchRow(beta, "F-0001")));

            expectState(soft, "WEB_SEARCH 而 url 非 NULL", tryInsert(db, "research_fetches",
                    with(searchRow(alpha, "F-0101"), "url", "https://example.org/q")), CHECK);
            expectState(soft, "WEB_SEARCH 而僅 host 非 NULL", tryInsert(db, "research_fetches",
                    with(searchRow(alpha, "F-0102"), "host", "example.org")), CHECK);
            for (String method : List.of("WEB_FETCH", "API", "MANUAL")) {
                expectState(soft, method + " 而 url 與 host 皆為 NULL", tryInsert(db, "research_fetches",
                        with(fetch, "fetch_method", method, "url", null, "host", null)), CHECK);
            }
            expectState(soft, "WEB_FETCH 而僅 url 為 NULL", tryInsert(db, "research_fetches",
                    with(fetch, "fetch_method", "WEB_FETCH", "url", null)), CHECK);
            expectState(soft, "WEB_FETCH 而僅 host 為 NULL", tryInsert(db, "research_fetches",
                    with(fetch, "fetch_method", "WEB_FETCH", "host", null)), CHECK);
            expectState(soft, "WEB_FETCH 而 host 為空字串", tryInsert(db, "research_fetches",
                    with(fetch, "fetch_method", "WEB_FETCH", "host", "")), CHECK);
            expectOk(soft, "解析不出 host 的被拒外呼取保留字 (unparsed)", tryInsert(db, "research_fetches",
                    with(fetch, "fetch_method", "WEB_FETCH", "host", "(unparsed)", "url", "file:///etc/passwd",
                            "outcome", "DENIED_ALLOWLIST")));

            expectState(soft, "search_no 為 0", tryInsert(db, "research_fetches", with(searchRow(alpha, "F-0103"), "search_no", 0)), CHECK);
            expectState(soft, "search_no 為 -1", tryInsert(db, "research_fetches", with(searchRow(alpha, "F-0104"), "search_no", -1)), CHECK);
            Outcome duplicateSearch = tryInsert(db, "research_fetches", with(searchRow(alpha, "F-0105"), "search_no", 1));
            expectState(soft, "甲內同 search_no 的第二筆", duplicateSearch, UNIQUE);
            soft.assertThat(duplicateSearch.message()).as("是 search_no 的部分唯一索引擋下的").contains("ux_research_fetches_search_no");
            expectOk(soft, "乙內同 search_no", tryInsert(db, "research_fetches", with(searchRow(beta, "F-0106"), "search_no", 1)));
            expectOk(soft, "兩列 search_no 皆為 NULL 並存", rolledBack(db, jdbc -> {
                insert(jdbc, "research_fetches", searchRow(alpha, "F-0107"));
                insert(jdbc, "research_fetches", searchRow(alpha, "F-0108"));
                return null;
            }));
            expectState(soft, "observed_by 為 BRIDGE 而 search_no 為 1", tryInsert(db, "research_fetches",
                    with(fetchRow(beta, "F-0300"), "search_no", 1)), CHECK);

            for (String badUrls : List.of("{}", "\"x\"", "1", "null")) {
                expectState(soft, "result_urls 為 JSON " + badUrls, tryInsert(db, "research_fetches",
                        with(fetch, "result_urls", badUrls)), CHECK);
            }
            expectState(soft, "result_urls 為 SQL NULL", tryInsert(db, "research_fetches", with(fetch, "result_urls", null)), NOT_NULL);
            Outcome unspecified = rolledBack(db, jdbc -> {
                insert(jdbc, "research_fetches", fetch);
                return jdbc.queryForObject("select result_urls::text from console.research_fetches where fetch_no = 'F-0100' "
                        + "and research_id = ?", String.class, alpha);
            });
            expectOk(soft, "未指定 result_urls", unspecified);
            soft.assertThat(unspecified.value()).as("預設為空陣列").isEqualTo("[]");

            Outcome declared = rolledBack(db, jdbc -> {
                insert(jdbc, "research_fetches", with(searchRow(alpha, "F-0109"), "search_no", 2, "query_text", "三層深研 搜尋",
                        "result_urls", "[\"https://b.example/2\",\"https://a.example/1\"]"));
                return jdbc.queryForList("select e from console.research_fetches f, jsonb_array_elements_text(f.result_urls) "
                        + "with ordinality as t(e, n) where f.fetch_no = 'F-0109' and f.research_id = ? order by n", String.class, alpha);
            });
            expectOk(soft, "宣告型搜尋列（WEB_SEARCH、AGENT_DECLARED、url 與 host 皆 NULL）", declared);
            soft.assertThat(declared.value()).as("result_urls 讀回與插入值逐元素相等且順序不變")
                    .isEqualTo(List.of("https://b.example/2", "https://a.example/1"));
            expectOk(soft, "WEB_FETCH、BRIDGE、url 與 host 皆有值", tryInsert(db, "research_fetches",
                    with(fetch, "fetch_method", "WEB_FETCH")));
        });
    }

    // ═════════════════════════════════════════════════════════════════════════════════════════════
    // V19（P1；PKG-DB-P1；TCS-ResearchToPRD-P1-20261107 AC-961-1）：分流、SCR、拆解、交付五表與自癒視圖
    // 為什麼重要：分流決策是「PRD 變成哪個程式碼庫」的稽核帳，同一研究專案不得同時有兩條有效分流（部分唯一索引是最後防線）、
    // 公開倉庫只准獨立專案（軌道 B）；SCR 與交付紀錄一旦寫下不可被事後改寫；受控表只准改狀態類欄位，不准改「做了什麼決定」。
    // 這些全落在資料庫，Bridge 寫入器自律不足以擔保。
    // ═════════════════════════════════════════════════════════════════════════════════════════════

    private static Map<String, Object> routeRow(UUID project, String track) {
        return "A".equals(track)
                ? row("research_id", project, "track", "A", "target_kind", "MODULE", "target_module", "agentconsole",
                        "target_path", "AgentConsole", "decided_by", "admin")
                : row("research_id", project, "track", "B", "target_kind", "STANDALONE", "target_path", "/ws/standalone",
                        "decided_by", "admin");
    }

    private static Map<String, Object> routeStepRow(UUID route, int stepNo, String step, String status) {
        return row("route_id", route, "step_no", stepNo, "step", step, "status", status);
    }

    private static Map<String, Object> scrRow(UUID project, int scrNo) {
        return row("research_id", project, "scr_no", scrNo, "kind", "MINOR", "source_kind", "HUMAN", "reason", "理由",
                "requested_by", "admin");
    }

    private static Map<String, Object> decompositionRow(UUID project, String path) {
        return row("research_id", project, "path", path, "created_by", "admin");
    }

    private static Map<String, Object> deliveryRow(UUID project, String kind, String ref, String status) {
        return row("research_id", project, "kind", kind, "ref", ref, "status", status, "created_by", "admin");
    }

    private static UUID v19Project(Db db) {
        UUID id = UUID.randomUUID();
        insert(db.jdbc, "research_projects", projectRow(id, "v19-" + id.toString().substring(0, 8)));
        return id;
    }

    private static UUID v19Route(Db db, UUID project, String status) {
        UUID id = UUID.randomUUID();
        insert(db.jdbc, "research_route_decisions", with(routeRow(project, "A"), "id", id, "status", status));
        return id;
    }

    private static void expectMessage(SoftAssertions soft, String label, Outcome outcome, String... parts) {
        for (String part : parts) {
            soft.assertThat(String.valueOf(outcome.message())).as("%s：訊息應含 %s", label, part).contains(part);
        }
    }

    @Test
    void AT_961_1_1_flywayHistoryReachesNineteenWithFiveTablesAndTheViewOnlyInConsole() {
        Db db = newDatabase();
        Db at18 = databaseAt("18");
        List<Map<String, Object>> history = db.jdbc.queryForList("select version, description, success from "
                + "console.flyway_schema_history where version is not null order by installed_rank");
        Set<String> added = new TreeSet<>(baseTables(db.jdbc));
        added.removeAll(baseTables(at18.jdbc));
        String viewSql = "select table_name from information_schema.views where table_schema = 'console' "
                + "and table_name like 'v\\_research\\_%'";
        List<String> viewsAfter19 = db.jdbc.queryForList(viewSql, String.class);
        List<String> viewsAfter18 = at18.jdbc.queryForList(viewSql, String.class);
        Integer leaked = db.jdbc.queryForObject("select count(*) from information_schema.tables where table_schema = 'public' "
                + "and (table_name like 'research\\_%' or table_name like 'v\\_research\\_%')", Integer.class);
        String v19Tables = "'" + String.join("', '", V19_TABLES) + "'";
        Map<String, String> timeColumns = new TreeMap<>();
        db.jdbc.queryForList("select table_name || '.' || column_name as col, data_type from information_schema.columns "
                + "where table_schema = 'console' and table_name in (" + v19Tables + ") and data_type like 'timestamp%'")
                .forEach(column -> timeColumns.put((String) column.get("col"), (String) column.get("data_type")));

        SoftAssertions.assertSoftly(soft -> {
            soft.assertThat(env.getProperty("spring.jpa.hibernate.ddl-auto")).as("ddl-auto=validate（本 context 能啟動即代表 validate 通過）")
                    .isEqualTo("validate");
            soft.assertThat(history).extracting(row -> row.get("version")).as("Flyway 歷史依序為 1 至 19")
                    .containsExactly("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20");
            soft.assertThat(history).extracting(row -> row.get("success")).as("每一版都成功").containsOnly(true);
            soft.assertThat(history.get(history.size() - 2).get("description")).as("V19 描述").isEqualTo("research route scr delivery");
            soft.assertThat(added).as("V19 在 console 內恰多出五張表").containsExactlyInAnyOrderElementsOf(V19_TABLES);
            soft.assertThat(viewsAfter18).as("V18 時還沒有視圖").isEmpty();
            soft.assertThat(viewsAfter19).as("V19 在 console 內恰多出一個視圖").containsExactly(V19_VIEW);
            soft.assertThat(leaked).as("public schema 零新物件").isZero();
            Map<String, String> expected = new TreeMap<>();
            for (String column : List.of("research_route_decisions.created_at", "research_route_decisions.finished_at",
                    "research_route_steps.started_at", "research_route_steps.finished_at", "research_scr.requested_at",
                    "research_scr.decided_at", "research_decompositions.created_at", "research_deliveries.created_at")) {
                expected.put(column, "timestamp with time zone");
            }
            soft.assertThat(timeColumns).as("V19 五表的 timestamp 欄逐欄皆 timestamp with time zone（沒有 without time zone）")
                    .isEqualTo(expected);
        });
    }

    @Test
    void AT_961_1_2_routeDecisionsChecks() {
        Db db = newDatabase();
        UUID base = v19Project(db);
        UUID q = v19Project(db);
        UUID baseRoute = UUID.randomUUID();
        insert(db.jdbc, "research_route_decisions", with(routeRow(base, "A"), "id", baseRoute));
        Map<String, Object> a = routeRow(q, "A");
        Map<String, Object> b = routeRow(q, "B");
        String table = "research_route_decisions";

        SoftAssertions.assertSoftly(soft -> {
            expectState(soft, "track 為 C", tryInsert(db, table, with(a, "track", "C")), CHECK);
            expectState(soft, "軌道 A 配 STANDALONE", tryInsert(db, table, with(a, "target_kind", "STANDALONE")), CHECK);
            expectState(soft, "軌道 A 缺 target_module", tryInsert(db, table, without(a, "target_module")), CHECK);
            expectState(soft, "軌道 B 帶 target_module", tryInsert(db, table, with(b, "target_module", "sdd")), CHECK);
            expectState(soft, "軌道 B 配 MODULE", tryInsert(db, table, with(b, "target_kind", "MODULE")), CHECK);
            expectState(soft, "target_module 為 other", tryInsert(db, table, with(a, "target_module", "other")), CHECK);
            // TCS 字面值 INTERNAL（8 字元）超過 VARCHAR(7) 欄寬會得 22001 而非 23514，改用欄寬內的非法值 OPEN（TCS §5.1 越界值構造規則；勘誤候選）
            expectState(soft, "repo_visibility 為 OPEN", tryInsert(db, table, with(b, "repo_visibility", "OPEN")), CHECK);
            expectState(soft, "repo_visibility 為 INTERNAL（欄寬超界：22001）", tryInsert(db, table, with(b, "repo_visibility", "INTERNAL")), TOO_LONG);
            Outcome publicA = tryInsert(db, table, with(a, "repo_visibility", "PUBLIC"));
            expectState(soft, "軌道 A 配 PUBLIC", publicA, CHECK);
            expectMessage(soft, "軌道 A 配 PUBLIC", publicA, "violates check constraint", table);
            expectState(soft, "status 為 DONE", tryInsert(db, table, with(a, "status", "DONE")), CHECK);
            expectState(soft, "target_path 為 NULL", tryInsert(db, table, with(a, "target_path", null)), NOT_NULL);
            expectState(soft, "decided_by 為 NULL", tryInsert(db, table, with(a, "decided_by", null)), NOT_NULL);
            expectState(soft, "git_branch 201 字元（欄寬超界不是 CHECK）", tryInsert(db, table,
                    with(a, "git_branch", "x".repeat(201))), TOO_LONG);
            expectOk(soft, "git_branch 恰 200 字元", tryInsert(db, table, with(a, "git_branch", "x".repeat(200))));
            expectState(soft, "console_project_id 指向不存在的專案", tryInsert(db, table,
                    with(a, "console_project_id", UUID.randomUUID())), FOREIGN_KEY);
            expectState(soft, "research_id 指向不存在的研究專案", tryInsert(db, table, routeRow(UUID.randomUUID(), "A")), FOREIGN_KEY);

            for (String module : List.of("autoclaude", "agentconsole", "sdd", "monorepo")) {
                expectOk(soft, "軌道 A 模組 " + module, tryInsert(db, table, with(a, "target_module", module)));
            }
            for (String status : List.of("PENDING", "RUNNING", "SUCCEEDED", "FAILED", "COMPENSATED")) {
                expectOk(soft, "狀態 " + status, tryInsert(db, table, with(a, "status", status)));
            }
            expectOk(soft, "PUBLIC 搭軌道 B", tryInsert(db, table, with(b, "repo_visibility", "PUBLIC")));
            expectOk(soft, "PRIVATE 搭軌道 A", tryInsert(db, table, with(a, "repo_visibility", "PRIVATE")));
            expectOk(soft, "軌道 B 基準列", tryInsert(db, table, b));

            expectEnum(soft, db.jdbc, table, "track", "A", "B");
            expectEnum(soft, db.jdbc, table, "target_kind", "MODULE", "STANDALONE");
            expectEnum(soft, db.jdbc, table, "target_module", "autoclaude", "agentconsole", "sdd", "monorepo");
            expectEnum(soft, db.jdbc, table, "repo_visibility", "PUBLIC", "PRIVATE");
            expectEnum(soft, db.jdbc, table, "status", "PENDING", "RUNNING", "SUCCEEDED", "FAILED", "COMPENSATED");
            soft.assertThat(db.jdbc.queryForObject("select published_docs::text from console.research_route_decisions where id = ?",
                    String.class, baseRoute)).as("published_docs 預設 {}").isEqualTo("{}");
            soft.assertThat(db.jdbc.queryForObject("select status from console.research_route_decisions where id = ?", String.class,
                    baseRoute)).as("status 預設 PENDING").isEqualTo("PENDING");
        });
    }

    @Test
    void AT_961_1_3_activeRoutePartialUniqueIndex() {
        Db db = newDatabase();
        UUID p = v19Project(db);
        UUID other = v19Project(db);
        String table = "research_route_decisions";
        UUID pending = UUID.randomUUID();
        UUID succeeded = UUID.randomUUID();

        SoftAssertions.assertSoftly(soft -> {
            expectOk(soft, "第一筆 FAILED", run(db, jdbc -> {
                insert(jdbc, table, with(routeRow(p, "A"), "status", "FAILED"));
                return null;
            }));
            expectOk(soft, "第二筆 FAILED（可並存）", run(db, jdbc -> {
                insert(jdbc, table, with(routeRow(p, "A"), "status", "FAILED"));
                return null;
            }));
            expectOk(soft, "一筆 PENDING", run(db, jdbc -> {
                insert(jdbc, table, with(routeRow(p, "A"), "id", pending, "status", "PENDING"));
                return null;
            }));
            Outcome running = run(db, jdbc -> {
                insert(jdbc, table, with(routeRow(p, "A"), "status", "RUNNING"));
                return null;
            });
            expectState(soft, "PENDING 在時再插 RUNNING", running, UNIQUE);
            expectMessage(soft, "PENDING 在時再插 RUNNING", running, "ux_research_route_active");
            expectState(soft, "PENDING 在時再插 SUCCEEDED", rolledBack(db, jdbc -> {
                insert(jdbc, table, with(routeRow(p, "A"), "status", "SUCCEEDED"));
                return null;
            }), UNIQUE);
            expectState(soft, "PENDING 在時再插 PENDING", rolledBack(db, jdbc -> {
                insert(jdbc, table, routeRow(p, "A"));
                return null;
            }), UNIQUE);
            expectOk(soft, "PENDING 改 FAILED", run(db, jdbc -> jdbc.update("update console." + table
                    + " set status = 'FAILED' where id = ?", pending)));
            expectOk(soft, "離開有效集合後可插入 SUCCEEDED", run(db, jdbc -> {
                insert(jdbc, table, with(routeRow(p, "A"), "id", succeeded, "status", "SUCCEEDED"));
                return null;
            }));
            expectOk(soft, "SUCCEEDED 改 COMPENSATED", run(db, jdbc -> jdbc.update("update console." + table
                    + " set status = 'COMPENSATED' where id = ?", succeeded)));
            expectOk(soft, "補償後可重新分流（PENDING）", run(db, jdbc -> {
                insert(jdbc, table, routeRow(p, "A"));
                return null;
            }));
            expectOk(soft, "另一個研究專案互不影響", run(db, jdbc -> {
                insert(jdbc, table, routeRow(other, "A"));
                return null;
            }));
            soft.assertThat(db.jdbc.queryForObject("select count(*) from console." + table + " where research_id = ? and status in "
                    + "('PENDING','RUNNING','SUCCEEDED')", Integer.class, p)).as("同一研究專案有效分流恰一筆").isEqualTo(1);
            String indexDef = db.jdbc.queryForObject("select indexdef from pg_indexes where schemaname = 'console' "
                    + "and indexname = 'ux_research_route_active'", String.class);
            soft.assertThat(indexDef).containsIgnoringCase("UNIQUE").containsIgnoringCase("WHERE").contains("PENDING")
                    .contains("RUNNING").contains("SUCCEEDED").doesNotContain("FAILED").doesNotContain("COMPENSATED");
        });
    }

    @Test
    void AT_961_1_4_routeStepsChecksAndCompositeKey() {
        Db db = newDatabase();
        UUID project = v19Project(db);
        UUID route = v19Route(db, project, "PENDING");
        String table = "research_route_steps";
        insert(db.jdbc, table, routeStepRow(route, 1, "VALIDATE_TARGET", "OK"));

        SoftAssertions.assertSoftly(soft -> {
            expectState(soft, "step_no 為 0", tryInsert(db, table, routeStepRow(route, 0, "VALIDATE_TARGET", "OK")), CHECK);
            expectState(soft, "step_no 為 -1", tryInsert(db, table, routeStepRow(route, -1, "VALIDATE_TARGET", "OK")), CHECK);
            expectState(soft, "(route_id, step_no) 重複", tryInsert(db, table, routeStepRow(route, 1, "GIT_SWITCH", "OK")), UNIQUE);
            expectState(soft, "step 為 GIT_PUSH", tryInsert(db, table, routeStepRow(route, 2, "GIT_PUSH", "OK")), CHECK);
            expectState(soft, "status 為 DONE", tryInsert(db, table, routeStepRow(route, 2, "GIT_SWITCH", "DONE")), CHECK);
            List<String> steps = List.of("VALIDATE_TARGET", "GIT_SWITCH", "SCAFFOLD_FILES", "GIT_INIT", "GIT_COMMIT", "GH_REPO_CREATE",
                    "PUBLISH_DOCS", "COPY_WORKSPACE", "REGISTER_STUB", "IMPL_KEY_INIT", "BASELINE_ADOPT");
            for (int i = 0; i < steps.size(); i++) {
                expectOk(soft, "步驟名 " + steps.get(i), tryInsert(db, table, routeStepRow(route, 10 + i, steps.get(i), "OK")));
            }
            for (String status : List.of("RUNNING", "OK", "FAILED", "SKIPPED", "COMPENSATED")) {
                expectOk(soft, "步驟狀態 " + status, tryInsert(db, table, routeStepRow(route, 2, "GIT_SWITCH", status)));
            }
            expectOk(soft, "stdout_tail 恰 2000 字元", tryInsert(db, table,
                    with(routeStepRow(route, 2, "GIT_SWITCH", "OK"), "stdout_tail", sql("repeat('x', 2000)"))));
            expectState(soft, "stdout_tail 2001 字元", tryInsert(db, table,
                    with(routeStepRow(route, 2, "GIT_SWITCH", "OK"), "stdout_tail", sql("repeat('x', 2001)"))), TOO_LONG);
            expectState(soft, "stderr_tail 2001 字元", tryInsert(db, table,
                    with(routeStepRow(route, 2, "GIT_SWITCH", "OK"), "stderr_tail", sql("repeat('x', 2001)"))), TOO_LONG);
            expectState(soft, "route_id 不存在", tryInsert(db, table, routeStepRow(UUID.randomUUID(), 1, "GIT_SWITCH", "OK")),
                    FOREIGN_KEY);
            expectEnum(soft, db.jdbc, table, "step", "VALIDATE_TARGET", "GIT_SWITCH", "SCAFFOLD_FILES", "GIT_INIT", "GIT_COMMIT",
                    "GH_REPO_CREATE", "PUBLISH_DOCS", "COPY_WORKSPACE", "REGISTER_STUB", "IMPL_KEY_INIT", "BASELINE_ADOPT");
            expectEnum(soft, db.jdbc, table, "status", "RUNNING", "OK", "FAILED", "SKIPPED", "COMPENSATED");
            Map<String, Object> defaults = db.jdbc.queryForMap("select argv_redacted, stdout_tail, stderr_tail from console."
                    + table + " where route_id = ? and step_no = 1", route);
            soft.assertThat(defaults).as("argv_redacted／stdout_tail／stderr_tail 預設空字串")
                    .containsEntry("argv_redacted", "").containsEntry("stdout_tail", "").containsEntry("stderr_tail", "");
            List<String> pk = db.jdbc.queryForList("select a.attname from pg_index i join pg_attribute a on a.attrelid = i.indrelid "
                    + "and a.attnum = any (i.indkey) where i.indrelid = 'console.research_route_steps'::regclass and i.indisprimary "
                    + "order by array_position(i.indkey::int2[], a.attnum)", String.class);
            soft.assertThat(pk).as("主鍵為 (route_id, step_no)").containsExactly("route_id", "step_no");
        });
    }

    @Test
    void AT_961_1_5_scrChecksAndUniqueKey() {
        Db db = newDatabase();
        UUID project = v19Project(db);
        String table = "research_scr";
        insert(db.jdbc, table, scrRow(project, 1));

        SoftAssertions.assertSoftly(soft -> {
            // TCS 字面值 MEDIUM（6 字元）超過 VARCHAR(5) 欄寬：改用欄寬內的非法值 MID（勘誤候選）
            expectState(soft, "kind 為 MID", tryInsert(db, table, with(scrRow(project, 2), "kind", "MID")), CHECK);
            expectState(soft, "kind 為 MEDIUM（欄寬超界：22001）", tryInsert(db, table, with(scrRow(project, 2), "kind", "MEDIUM")), TOO_LONG);
            expectState(soft, "source_kind 為 OTHER", tryInsert(db, table, with(scrRow(project, 2), "source_kind", "OTHER")), CHECK);
            expectState(soft, "reason_class 為 BUG", tryInsert(db, table, with(scrRow(project, 2), "reason_class", "BUG")), CHECK);
            expectState(soft, "status 為 CLOSED", tryInsert(db, table, with(scrRow(project, 2), "status", "CLOSED")), CHECK);
            expectState(soft, "scr_no 為 0", tryInsert(db, table, scrRow(project, 0)), CHECK);
            expectState(soft, "scr_no 重複", tryInsert(db, table, scrRow(project, 1)), UNIQUE);
            expectState(soft, "requested_by 為 NULL", tryInsert(db, table, with(scrRow(project, 2), "requested_by", null)), NOT_NULL);
            expectState(soft, "reason 為 NULL", tryInsert(db, table, with(scrRow(project, 2), "reason", null)), NOT_NULL);
            for (String kind : List.of("MINOR", "MAJOR")) {
                expectOk(soft, "kind " + kind, tryInsert(db, table, with(scrRow(project, 2), "kind", kind)));
            }
            for (String source : List.of("HUMAN", "REVIEW_FINDING", "SCG4", "HEALING_FAILED")) {
                expectOk(soft, "source_kind " + source, tryInsert(db, table, with(scrRow(project, 2), "source_kind", source)));
            }
            for (String reasonClass : List.of("EVIDENCE", "AC_VAGUE", "REQ_CHANGE", "INFEASIBLE", "OTHER")) {
                expectOk(soft, "reason_class " + reasonClass, tryInsert(db, table, with(scrRow(project, 2), "reason_class", reasonClass)));
            }
            for (String status : List.of("OPEN", "APPROVED", "REJECTED", "APPLIED", "SUPERSEDED")) {
                expectOk(soft, "status " + status, tryInsert(db, table, with(scrRow(project, 2), "status", status)));
            }
            expectState(soft, "successor_research_id 不存在", tryInsert(db, table,
                    with(scrRow(project, 2), "successor_research_id", UUID.randomUUID())), FOREIGN_KEY);
            expectEnum(soft, db.jdbc, table, "kind", "MINOR", "MAJOR");
            expectEnum(soft, db.jdbc, table, "source_kind", "HUMAN", "REVIEW_FINDING", "SCG4", "HEALING_FAILED");
            expectEnum(soft, db.jdbc, table, "reason_class", "EVIDENCE", "AC_VAGUE", "REQ_CHANGE", "INFEASIBLE", "OTHER");
            expectEnum(soft, db.jdbc, table, "status", "OPEN", "APPROVED", "REJECTED", "APPLIED", "SUPERSEDED");
            Map<String, Object> defaults = db.jdbc.queryForMap("select reason_class, affected_sections::text as sections, "
                    + "impl_fsm_actions::text as actions, status from console.research_scr where scr_no = 1");
            soft.assertThat(defaults).as("省略欄位時的預設值").containsEntry("reason_class", "OTHER")
                    .containsEntry("sections", "{}").containsEntry("actions", "[]").containsEntry("status", "OPEN");
        });
    }

    @Test
    void AT_961_1_6_decompositionsChecks() {
        Db db = newDatabase();
        UUID project = v19Project(db);
        String table = "research_decompositions";
        UUID base = UUID.randomUUID();
        insert(db.jdbc, table, with(decompositionRow(project, "C"), "id", base));
        String upper = "A".repeat(64);

        SoftAssertions.assertSoftly(soft -> {
            for (String path : List.of("A", "B", "C")) {
                expectOk(soft, "path " + path, tryInsert(db, table, decompositionRow(project, path)));
            }
            expectState(soft, "path 為 D", tryInsert(db, table, decompositionRow(project, "D")), CHECK);
            for (String column : List.of("tcs_sha256", "prd_sha256")) {
                expectOk(soft, column + " 64 位小寫十六進位", tryInsert(db, table, with(decompositionRow(project, "A"), column, HEX64)));
                expectOk(soft, column + " 為 NULL", tryInsert(db, table, with(decompositionRow(project, "A"), column, null)));
                expectState(soft, column + " 63 位", tryInsert(db, table,
                        with(decompositionRow(project, "A"), column, "a".repeat(63))), CHECK);
                expectState(soft, column + " 64 位含大寫", tryInsert(db, table, with(decompositionRow(project, "A"), column, upper)), CHECK);
            }
            expectState(soft, "tasks_count 為 -1", tryInsert(db, table, with(decompositionRow(project, "A"), "tasks_count", -1)), CHECK);
            expectOk(soft, "tasks_count 為 0", tryInsert(db, table, with(decompositionRow(project, "A"), "tasks_count", 0)));
            for (String status : List.of("DRAFTED", "SCG_PASSED", "FROZEN", "IMPORTED", "SIGNED_OFF", "REJECTED", "STALE")) {
                expectOk(soft, "status " + status, tryInsert(db, table, with(decompositionRow(project, "A"), "status", status)));
            }
            expectState(soft, "status 為 DONE", tryInsert(db, table, with(decompositionRow(project, "A"), "status", "DONE")), CHECK);
            expectState(soft, "import_record_id 不存在", tryInsert(db, table,
                    with(decompositionRow(project, "A"), "import_record_id", UUID.randomUUID())), FOREIGN_KEY);
            expectState(soft, "stage_run_id 不存在", tryInsert(db, table,
                    with(decompositionRow(project, "A"), "stage_run_id", UUID.randomUUID())), FOREIGN_KEY);
            expectState(soft, "created_by 為 NULL", tryInsert(db, table, with(decompositionRow(project, "A"), "created_by", null)),
                    NOT_NULL);
            expectEnum(soft, db.jdbc, table, "path", "A", "B", "C");
            expectEnum(soft, db.jdbc, table, "status", "DRAFTED", "SCG_PASSED", "FROZEN", "IMPORTED", "SIGNED_OFF", "REJECTED", "STALE");
            Map<String, Object> defaults = db.jdbc.queryForMap("select status, tasks_count from console.research_decompositions "
                    + "where id = ?", base);
            soft.assertThat(defaults).as("省略 status 與 tasks_count 的預設").containsEntry("status", "DRAFTED").containsEntry("tasks_count", 0);
        });
    }

    @Test
    void AT_961_1_7_deliveriesChecksUniqueAndAppendOnly() {
        Db db = newDatabase();
        UUID project = v19Project(db);
        String table = "research_deliveries";
        insert(db.jdbc, table, deliveryRow(project, "RELEASE_TAG", "v1.0.0", "CREATED"));
        String before = snapshot(db.jdbc, table);

        SoftAssertions.assertSoftly(soft -> {
            for (String kind : List.of("RELEASE_TAG", "PULL_REQUEST", "RELEASE_NOTE")) {
                expectOk(soft, "kind " + kind, tryInsert(db, table, deliveryRow(project, kind, "r-" + kind, "CREATED")));
            }
            // TCS 字面值 RELEASE_NOTES（13 字元）超過 VARCHAR(12) 欄寬：改用恰 12 字元的非法值 RELEASE_TAGS（勘誤候選）
            expectState(soft, "kind 為 RELEASE_TAGS", tryInsert(db, table, deliveryRow(project, "RELEASE_TAGS", "r", "CREATED")), CHECK);
            expectState(soft, "kind 為 RELEASE_NOTES（欄寬超界：22001）", tryInsert(db, table, deliveryRow(project, "RELEASE_NOTES", "r", "CREATED")), TOO_LONG);
            expectOk(soft, "status FAILED", tryInsert(db, table, deliveryRow(project, "PULL_REQUEST", "42", "FAILED")));
            expectState(soft, "status 為 PENDING", tryInsert(db, table, deliveryRow(project, "PULL_REQUEST", "42", "PENDING")), CHECK);
            expectOk(soft, "commit_sha 40 位小寫十六進位", tryInsert(db, table,
                    with(deliveryRow(project, "RELEASE_TAG", "v2", "CREATED"), "commit_sha", "a".repeat(40))));
            expectState(soft, "commit_sha 39 位", tryInsert(db, table,
                    with(deliveryRow(project, "RELEASE_TAG", "v2", "CREATED"), "commit_sha", "a".repeat(39))), CHECK);
            expectState(soft, "commit_sha 含大寫", tryInsert(db, table,
                    with(deliveryRow(project, "RELEASE_TAG", "v2", "CREATED"), "commit_sha", "A".repeat(40))), CHECK);
            expectState(soft, "同 (research_id, kind, ref) 兩次", tryInsert(db, table,
                    deliveryRow(project, "RELEASE_TAG", "v1.0.0", "FAILED")), UNIQUE);
            expectOk(soft, "同 ref 不同 kind", tryInsert(db, table, deliveryRow(project, "PULL_REQUEST", "v1.0.0", "CREATED")));
            expectState(soft, "rtm_run_id 不存在", tryInsert(db, table,
                    with(deliveryRow(project, "RELEASE_TAG", "v3", "CREATED"), "rtm_run_id", UUID.randomUUID())), FOREIGN_KEY);
            expectEnum(soft, db.jdbc, table, "kind", "RELEASE_TAG", "PULL_REQUEST", "RELEASE_NOTE");
            expectEnum(soft, db.jdbc, table, "status", "CREATED", "FAILED");

            for (String column : List.of("ref", "status", "detail", "url", "created_by", "commit_sha")) {
                String set = switch (column) {
                    case "status" -> "status = 'FAILED'";
                    case "commit_sha" -> "commit_sha = '" + "b".repeat(40) + "'";
                    default -> column + " = 'changed'";
                };
                expectGuard(soft, "UPDATE " + column, run(db, jdbc -> jdbc.update("update console." + table + " set " + set)),
                        table, "append-only");
            }
            expectGuard(soft, "同值 UPDATE 也被拒", run(db, jdbc -> jdbc.update("update console." + table + " set ref = ref")),
                    table, "append-only");
            expectGuard(soft, "DELETE", run(db, jdbc -> jdbc.update("delete from console." + table)), table, "append-only");
            soft.assertThat(snapshot(db.jdbc, table)).as("被拒之後列內容不變").isEqualTo(before);
            soft.assertThat(db.jdbc.queryForObject("select count(*) from pg_trigger t join pg_proc p on p.oid = t.tgfoid where t.tgrelid = "
                    + "'console.research_deliveries'::regclass and not t.tgisinternal and p.proname = 'research_controlled_update_guard'",
                    Integer.class)).as("research_deliveries 不在受控清單").isZero();
        });
    }

    @Test
    void AT_961_1_8_v19ControlledTablesGuardAllowedColumnsAgainstTheV16Function() {
        Db db = newDatabase();
        UUID consoleProject = UUID.randomUUID();
        db.jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria) values (?,?,?,?)",
                consoleProject, "console-p", "/x", "c");
        UUID importRecord = UUID.randomUUID();
        db.jdbc.update("insert into console.import_records (id, source_type, source_content) values (?, 'MARKDOWN', 'x')", importRecord);
        UUID project = v19Project(db);
        UUID successor = v19Project(db);
        UUID route = v19Route(db, project, "PENDING");
        insert(db.jdbc, "research_route_steps", routeStepRow(route, 1, "VALIDATE_TARGET", "RUNNING"));
        UUID scr = UUID.randomUUID();
        insert(db.jdbc, "research_scr", with(scrRow(project, 1), "id", scr));
        UUID decomposition = UUID.randomUUID();
        insert(db.jdbc, "research_decompositions", with(decompositionRow(project, "C"), "id", decomposition));

        String functionDefinition = db.jdbc.queryForObject("select pg_get_functiondef('console.research_controlled_update_guard'::regproc)",
                String.class);
        Map<String, List<String>> allowedByFunction = new LinkedHashMap<>();
        Matcher entry = Pattern.compile("WHEN '(\\w+)' THEN ARRAY\\[(.*?)\\]", Pattern.DOTALL).matcher(functionDefinition);
        while (entry.find()) {
            List<String> columns = new ArrayList<>();
            Matcher quoted = QUOTED.matcher(entry.group(2));
            while (quoted.find()) {
                columns.add(quoted.group(1));
            }
            allowedByFunction.put(entry.group(1), columns);
        }

        // 欄位 → SET 片段（TCS AT-961-1-8 逐表逐欄；本 AT 自備列定位，不使用 P0 的 rowIds 與 CONTROLLED_UPDATE_COLUMNS）
        Map<String, Map<String, String>> allowedSets = new LinkedHashMap<>();
        allowedSets.put("research_route_decisions", ordered(
                "status", "status = 'RUNNING'", "failure_step", "failure_step = 'GIT_SWITCH'", "finished_at", "finished_at = now()",
                "repo_url", "repo_url = 'https://example.org/r.git'", "published_docs", "published_docs = '{\"docs/a.md\":\"x\"}'::jsonb",
                "console_project_id", "console_project_id = '" + consoleProject + "'", "impl_fsm_project", "impl_fsm_project = 'agentconsole-demo'",
                "impl_state_dir", "impl_state_dir = '/s/build/reports/fsm'"));
        allowedSets.put("research_route_steps", ordered(
                "status", "status = 'OK'", "exit_code", "exit_code = 0", "stdout_tail", "stdout_tail = 'o'", "stderr_tail", "stderr_tail = 'e'",
                "finished_at", "finished_at = now()"));
        allowedSets.put("research_scr", ordered(
                "status", "status = 'APPROVED'", "prd_to_version_no", "prd_to_version_no = 2",
                "successor_research_id", "successor_research_id = '" + successor + "'", "impl_fsm_actions", "impl_fsm_actions = '[\"show\"]'::jsonb",
                "decided_by", "decided_by = 'admin'", "decided_at", "decided_at = now()"));
        allowedSets.put("research_decompositions", ordered(
                "status", "status = 'SCG_PASSED'", "draft_id", "draft_id = 'd-1'", "import_record_id", "import_record_id = '" + importRecord + "'",
                "tcs_rel_path", "tcs_rel_path = '03_execution/TCS-x.md'", "tcs_sha256", "tcs_sha256 = '" + HEX64 + "'", "tasks_count", "tasks_count = 3",
                "gate_rejection", "gate_rejection = 'cycle'"));
        Map<String, Map<String, String>> disallowedSets = new LinkedHashMap<>();
        disallowedSets.put("research_route_decisions", ordered("track", "track = 'B'", "target_path", "target_path = '/other'",
                "scope_differs_reason", "scope_differs_reason = 'x'", "decided_by", "decided_by = 'someone'"));
        disallowedSets.put("research_route_steps", ordered("step", "step = 'GIT_INIT'", "argv_redacted", "argv_redacted = 'x'"));
        disallowedSets.put("research_scr", ordered("reason", "reason = 'new'", "kind", "kind = 'MAJOR'", "requested_by", "requested_by = 'someone'"));
        disallowedSets.put("research_decompositions", ordered("prd_sha256", "prd_sha256 = '" + "b".repeat(64) + "'", "path", "path = 'B'",
                "created_by", "created_by = 'someone'"));
        Map<String, String> where = Map.of(
                "research_route_decisions", "id = '" + route + "'",
                "research_route_steps", "route_id = '" + route + "' and step_no = 1",
                "research_scr", "id = '" + scr + "'",
                "research_decompositions", "id = '" + decomposition + "'");

        SoftAssertions.assertSoftly(soft -> {
            soft.assertThat(V19_CONTROLLED_TABLES).as("V19_CONTROLLED_TABLES 恰四表").hasSize(4);
            List<String> v19InFunction = new ArrayList<>(allowedByFunction.keySet());
            v19InFunction.removeAll(CONTROLLED_TABLES);
            soft.assertThat(v19InFunction).as("V16 守衛函式的 V19 條目逐表等於 V19_CONTROLLED_TABLES")
                    .containsExactlyInAnyOrderElementsOf(V19_CONTROLLED_TABLES);
            soft.assertThat(db.jdbc.queryForList("select c.relname from pg_trigger t join pg_class c on c.oid = t.tgrelid "
                    + "join pg_proc p on p.oid = t.tgfoid join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'console' "
                    + "and p.proname = 'research_controlled_update_guard' and c.relname in ('research_route_decisions', "
                    + "'research_route_steps', 'research_scr', 'research_decompositions') and not t.tgisinternal", String.class))
                    .as("四張 V19 受控表皆掛通用守衛").containsExactlyInAnyOrderElementsOf(V19_CONTROLLED_TABLES);
            for (String table : V19_CONTROLLED_TABLES) {
                soft.assertThat(allowedSets.get(table).keySet()).as("%s 測試取用的允許欄＝V16 函式內的字面清單", table)
                        .containsExactlyElementsOf(allowedByFunction.get(table));
                String locator = where.get(table);
                String before = snapshot(db.jdbc, table);
                allowedSets.get(table).forEach((column, set) -> {
                    Outcome outcome = rolledBack(db, jdbc -> {
                        jdbc.update("update console." + table + " set " + set + " where " + locator);
                        return snapshot(jdbc, table);
                    });
                    expectOk(soft, table + " 允許欄 " + column, outcome);
                    if (outcome.ok()) {
                        soft.assertThat(outcome.value()).as("%s 更新 %s 之後列確實改變", table, column).isNotEqualTo(before);
                    }
                });
                String companion = allowedSets.get(table).values().iterator().next();
                disallowedSets.get(table).forEach((column, set) -> {
                    Outcome alone = run(db, jdbc -> jdbc.update("update console." + table + " set " + set + " where " + locator));
                    expectGuard(soft, table + " 非允許欄 " + column, alone, table);
                    for (String allowedColumn : allowedByFunction.get(table)) {
                        expectMessage(soft, table + " 非允許欄 " + column, alone, allowedColumn);
                    }
                    expectGuard(soft, table + " 允許欄夾帶非允許欄 " + column, run(db, jdbc -> jdbc.update("update console." + table
                            + " set " + companion + ", " + set + " where " + locator)), table);
                });
                expectGuard(soft, table + " DELETE", run(db, jdbc -> jdbc.update("delete from console." + table + " where " + locator)), table);
                soft.assertThat(snapshot(db.jdbc, table)).as("%s 全程列不變（被拒的語句沒有留下任何效果）", table).isEqualTo(before);
            }
            soft.assertThat(allowedByFunction).as("research_deliveries 不在受控清單").doesNotContainKey("research_deliveries");
        });
    }

    @Test
    void AT_961_1_9_healingViewShowsOnlyRetryingAndFailedStepsOfBoundProjects() {
        Db db = newDatabase();
        UUID consoleProject = UUID.randomUUID();
        db.jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria) values (?,?,?,?)",
                consoleProject, "console-p", "/x", "c");
        UUID goal = UUID.randomUUID();
        db.jdbc.update("insert into console.goals (id, project_id, name, pass_criteria) values (?,?,?,?)", goal, consoleProject, "g", "c");
        UUID task = UUID.randomUUID();
        db.jdbc.update("insert into console.tasks (id, goal_id, name, pass_criteria) values (?,?,?,?)", task, goal, "t", "c");
        UUID run = UUID.randomUUID();
        db.jdbc.update("insert into console.execution_runs (id, project_id, run_number, autonomy_level, scope) values (?,?,7,1,'{}'::jsonb)",
                run, consoleProject);
        int stepNumber = 1;
        for (String status : List.of("SUCCESS", "RETRYING", "FAILED", "PENDING")) {
            db.jdbc.update("insert into console.execution_steps (run_id, task_id, step_number, action, status, tokens_used, error_message) "
                    + "values (?,?,?,?,?,?,?)", run, task, stepNumber, "action-" + status, status, 10L * stepNumber, "err-" + status);
            stepNumber++;
        }
        UUID bound = UUID.randomUUID();
        insert(db.jdbc, "research_projects", with(projectRow(bound, "bound"), "console_project_id", consoleProject));
        UUID unbound = project(db, "unbound");

        List<String> columns = db.jdbc.queryForList("select column_name from information_schema.columns where table_schema = 'console' "
                + "and table_name = 'v_research_healing_attempts' order by ordinal_position", String.class);
        List<Map<String, Object>> rows = db.jdbc.queryForList("select research_id, run_id, run_number, step_number, status, action, "
                + "error_message, tokens_used from console." + V19_VIEW + " order by step_number");
        Outcome insertView = run(db, jdbc -> jdbc.update("insert into console." + V19_VIEW + " (research_id) values (gen_random_uuid())"));
        Outcome updateView = run(db, jdbc -> jdbc.update("update console." + V19_VIEW + " set status = 'FAILED'"));
        Outcome deleteView = run(db, jdbc -> jdbc.update("delete from console." + V19_VIEW));

        SoftAssertions.assertSoftly(soft -> {
            soft.assertThat(columns).as("視圖欄位恰為十個").containsExactly("research_id", "run_id", "run_number", "task_id",
                    "step_number", "action", "status", "error_message", "tokens_used", "occurred_at");
            soft.assertThat(rows).as("只回 RETRYING 與 FAILED 兩筆").extracting(r -> r.get("status")).containsExactly("RETRYING", "FAILED");
            soft.assertThat(rows).extracting(r -> r.get("research_id")).as("research_id 為經 console_project_id 綁定的研究專案")
                    .containsOnly(bound);
            soft.assertThat(rows).extracting(r -> r.get("run_id")).containsOnly(run);
            soft.assertThat(rows).extracting(r -> r.get("run_number")).containsOnly(7);
            soft.assertThat(rows).extracting(r -> r.get("error_message")).containsExactly("err-RETRYING", "err-FAILED");
            soft.assertThat(db.jdbc.queryForObject("select count(*) from console." + V19_VIEW + " where research_id = ?", Integer.class,
                    unbound)).as("未綁定 Console 專案的研究專案零列").isZero();
            expectState(soft, "對視圖 INSERT", insertView, "55000");
            expectState(soft, "對視圖 UPDATE", updateView, "55000");
            expectState(soft, "對視圖 DELETE", deleteView, "55000");
            soft.assertThat(db.jdbc.queryForObject("select count(*) from pg_trigger where tgrelid = 'console.v_research_healing_attempts'::regclass "
                    + "and not tgisinternal", Integer.class)).as("視圖上零觸發器（沒有 INSTEAD OF）").isZero();
            soft.assertThat(db.jdbc.queryForObject("select count(*) from pg_rules where schemaname = 'console' "
                    + "and tablename = 'v_research_healing_attempts'", Integer.class)).as("視圖上零使用者規則").isZero();
            soft.assertThat(db.jdbc.queryForObject("select count(*) from console.execution_steps", Integer.class)).as("視圖沒有動到底表")
                    .isEqualTo(4);
        });
    }

    @Test
    void AT_961_1_E_1_everyResearchTableRejectsDeleteWithAClassTwentyThreeError() {
        Db db = newDatabase();
        Chain chain = chain(db);
        UUID source = UUID.randomUUID();
        insert(db.jdbc, "research_sources", sourceRow(source, chain.project(), "S-001", "https://example.org/s1"));
        insert(db.jdbc, "research_events", eventRow(chain.project(), 1));
        insert(db.jdbc, "research_artifacts", artifactRow(chain.project(), "ISSUE_SCOPE", 1));
        insert(db.jdbc, "research_fetches", fetchRow(chain.project(), "F-0001"));
        insert(db.jdbc, "research_evidence_items", evidenceRow(chain.project(), source, 1, "E-001"));
        insert(db.jdbc, "research_review_scores", scoreRow(chain.round(), "ARCHITECTURE"));
        insert(db.jdbc, "research_gate_decisions", decisionRow(chain.project(), "GATE0", "CHANGES"));
        insert(db.jdbc, "research_review_defects", defectRow(UUID.randomUUID(), chain.round(), "D-1-001"));
        insert(db.jdbc, "research_allowlist_entries", allowlistRow("export.arxiv.org"));
        UUID route = v19Route(db, chain.project(), "PENDING");
        insert(db.jdbc, "research_route_steps", routeStepRow(route, 1, "VALIDATE_TARGET", "OK"));
        insert(db.jdbc, "research_scr", scrRow(chain.project(), 1));
        insert(db.jdbc, "research_decompositions", decompositionRow(chain.project(), "A"));
        insert(db.jdbc, "research_deliveries", deliveryRow(chain.project(), "RELEASE_TAG", "v1", "CREATED"));

        List<String> tables = db.jdbc.queryForList("select table_name from information_schema.tables where table_schema = 'console' "
                + "and table_type = 'BASE TABLE' and table_name like 'research\\_%' order by 1", String.class);
        List<String> unguarded = db.jdbc.queryForList("select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                + "where n.nspname = 'console' and c.relkind = 'r' and c.relname like 'research\\_%' and not exists (select 1 from pg_trigger t "
                + "join pg_proc p on p.oid = t.tgfoid where t.tgrelid = c.oid and not t.tgisinternal and p.proname in "
                + "('research_append_only_guard', 'research_controlled_update_guard') and (t.tgtype & 8) <> 0) order by 1", String.class);

        SoftAssertions.assertSoftly(soft -> {
            List<String> expectedTables = new ArrayList<>(RESEARCH_TABLES);
            expectedTables.addAll(V19_TABLES);
            soft.assertThat(tables).as("表清單取 information_schema：恰十八張（P0 十三加 V19 五）").hasSize(18)
                    .containsExactlyInAnyOrderElementsOf(expectedTables);
            soft.assertThat(unguarded).as("表清單減去「掛有涵蓋 DELETE 的守衛」之表為空（新增第十九張而未掛守衛即紅）").isEmpty();
            for (String table : tables) {
                int before = db.jdbc.queryForObject("select count(*) from console." + table, Integer.class);
                soft.assertThat(before).as("%s 至少一列", table).isGreaterThanOrEqualTo(1);
                Outcome delete = run(db, jdbc -> jdbc.update("delete from console." + table));
                soft.assertThat(delete.sqlState()).as("%s DELETE 的 SQLSTATE 類別為 23：%s", table, delete).isNotNull().startsWith("23");
                expectMessage(soft, table + " DELETE", delete, table);
                soft.assertThat(db.jdbc.queryForObject("select count(*) from console." + table, Integer.class))
                        .as("%s 刪除前後列數相同", table).isEqualTo(before);
            }
        });
    }

    @Test
    void AT_961_1_E_3_v19JsonbColumnsHaveObjectAndArrayDefaults() {
        Db db = newDatabase();
        UUID project = v19Project(db);
        UUID route = UUID.randomUUID();
        UUID scr = UUID.randomUUID();
        insert(db.jdbc, "research_route_decisions", with(routeRow(project, "A"), "id", route));
        insert(db.jdbc, "research_scr", with(scrRow(project, 1), "id", scr));
        Map<String, Object> published = columnsOf(db.jdbc, "research_route_decisions").get("published_docs");
        Map<String, Object> actions = columnsOf(db.jdbc, "research_scr").get("impl_fsm_actions");

        SoftAssertions.assertSoftly(soft -> {
            soft.assertThat(published).containsEntry("data_type", "jsonb").containsEntry("column_default", "'{}'::jsonb")
                    .containsEntry("is_nullable", "NO");
            soft.assertThat(actions).containsEntry("data_type", "jsonb").containsEntry("column_default", "'[]'::jsonb")
                    .containsEntry("is_nullable", "NO");
            soft.assertThat(db.jdbc.queryForObject("select published_docs::text from console.research_route_decisions where id = ?",
                    String.class, route)).as("省略時讀回 {}").isEqualTo("{}");
            soft.assertThat(db.jdbc.queryForObject("select impl_fsm_actions::text from console.research_scr where id = ?",
                    String.class, scr)).as("省略時讀回 []").isEqualTo("[]");
            // DDL 不擋非陣列 JSON：形狀由 Bridge 寫入器保證（Architecture K.4 未要求此 CHECK；TCS ⚖P1-9），此處以註記斷言固定現況
            expectOk(soft, "impl_fsm_actions 寫入非陣列 JSON：DDL 不擋、應用層擋", rolledBack(db, jdbc -> jdbc.update(
                    "update console.research_scr set impl_fsm_actions = '{\"a\":1}'::jsonb where id = ?", scr)));
        });
    }
}
