package com.aisdlc.console.infrastructure.persistence;

import com.aisdlc.console.support.SharedPostgres;
import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.MigrationVersion;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Flyway V24（{@code console.research_watch_sources}；TCS-ResearchRegistry AT-965-1-1～1-7、1-E-1；契約 §5A.1）。為什麼重要：追蹤來源是自我進化抓取的唯一來源，
 * 表的約束與受控更新守衛若有洞（可改 url、可刪列、接受 IP 字面或 IDNA），Console 與根層就會對「該抓什麼」各說各話；種子若與舊表不逐字一致，遷移就悄悄改變了抓取行為。
 */
class ResearchWatchSourceSchemaIT {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final String SEED_TIME = "2026-11-10T00:00:00+00:00";
    private static final String GUARD = "23";

    /** 通用守衛（V16）的九個既有允許清單條目，抄自 V16 的 CASE（逐條逐欄含順序；TCS §2 的 GUARD_ARMS_V16）。 */
    private static final Map<String, List<String>> GUARD_ARMS_V16 = new LinkedHashMap<>();

    static {
        GUARD_ARMS_V16.put("research_projects", List.of("title", "topic", "scope", "scope_rev", "depth_level", "target_scope", "fsm_project",
                "fsm_generation", "flow_step", "flow_phase", "flow_status", "flow_detail", "console_project_id", "last_event_seq", "updated_at",
                "archived_at"));
        GUARD_ARMS_V16.put("research_stage_runs", List.of("status", "tokens_used", "exit_reason", "started_at", "finished_at"));
        GUARD_ARMS_V16.put("research_sources", List.of("verification"));
        GUARD_ARMS_V16.put("research_review_defects", List.of("status", "fixed_in_version_no", "waived_by", "waiver_reason", "resolved_at"));
        GUARD_ARMS_V16.put("research_allowlist_entries", List.of("enabled", "disabled_by", "disabled_at"));
        GUARD_ARMS_V16.put("research_route_decisions", List.of("status", "failure_step", "finished_at", "repo_url", "published_docs",
                "console_project_id", "impl_fsm_project", "impl_state_dir"));
        GUARD_ARMS_V16.put("research_route_steps", List.of("status", "exit_code", "stdout_tail", "stderr_tail", "finished_at"));
        GUARD_ARMS_V16.put("research_decompositions", List.of("status", "draft_id", "import_record_id", "tcs_rel_path", "tcs_sha256", "tasks_count",
                "gate_rejection"));
        GUARD_ARMS_V16.put("research_scr", List.of("status", "prd_to_version_no", "successor_research_id", "impl_fsm_actions", "decided_by",
                "decided_at"));
    }

    // ── 夾具 ─────────────────────────────────────────────────────────────────────────────────

    private static String createDatabase() {
        String name = "watch_src_" + UUID.randomUUID().toString().replace("-", "");
        try (Connection admin = DriverManager.getConnection(SharedPostgres.INSTANCE.getJdbcUrl(), SharedPostgres.INSTANCE.getUsername(),
                SharedPostgres.INSTANCE.getPassword()); Statement statement = admin.createStatement()) {
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
        var configuration = Flyway.configure().dataSource(urlOf(database), SharedPostgres.INSTANCE.getUsername(), SharedPostgres.INSTANCE.getPassword())
                .schemas("console").defaultSchema("console").locations("classpath:db/migration");
        if (targetVersion != null) {
            configuration.target(MigrationVersion.fromVersion(targetVersion));
        }
        return configuration.load();
    }

    private static JdbcTemplate jdbcOf(String database) {
        return new JdbcTemplate(new DriverManagerDataSource(urlOf(database), SharedPostgres.INSTANCE.getUsername(), SharedPostgres.INSTANCE.getPassword()));
    }

    private static JdbcTemplate migrated() {
        String database = createDatabase();
        flyway(database, null).migrate();
        return jdbcOf(database);
    }

    private static byte[] resource(String name) {
        try (InputStream in = ResearchWatchSourceSchemaIT.class.getResourceAsStream("/research-registry/" + name)) {
            assertThat(in).as("測試資源 research-registry/%s 存在", name).isNotNull();
            return in.readAllBytes();
        } catch (IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    private static String sha256(byte[] bytes) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    /** 以合法欄位值 INSERT 一列追蹤來源（{@code slug}、{@code url} 與覆寫欄位由呼叫端給）。 */
    private static void insert(JdbcTemplate jdbc, String slug, String url, Map<String, Object> over) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("slug", slug);
        row.put("url", url);
        row.put("kind", "docs");
        row.put("extract", "標題清單");
        row.put("layer", "INDUSTRY");
        row.put("added_by", "t:fixture");
        row.putAll(over);
        String columns = String.join(", ", row.keySet());
        String marks = String.join(", ", row.keySet().stream().map(k -> "?").toList());
        jdbc.update("insert into console.research_watch_sources (" + columns + ") values (" + marks + ")", row.values().toArray());
    }

    private static void insert(JdbcTemplate jdbc, String slug, String url) {
        insert(jdbc, slug, url, Map.of());
    }

    private static String sqlState(Runnable action) {
        try {
            action.run();
            return null;
        } catch (DataAccessException e) {
            Throwable cause = e.getCause();
            return cause instanceof SQLException sql ? sql.getSQLState() : "?";
        }
    }

    /** 時間欄以 UTC 與秒精度的固定文字取出（不受 JVM 與連線時區影響）。 */
    private static String utc(String column) {
        return "to_char(" + column + " at time zone 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"+00:00\"')";
    }

    private static List<Map<String, Object>> allRows(JdbcTemplate jdbc) {
        return jdbc.queryForList("select slug, url, kind, extract, layer, expand_mode, expand_prefix, expand_max, enabled, added_by, "
                + "" + utc("added_at") + " as added_at, disabled_by, " + utc("disabled_at") + " as disabled_at from console.research_watch_sources order by slug collate \"C\"");
    }

    // ── AT-965-1-1 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_1_1_columnsTypesAndEveryCheckHold() {
        JdbcTemplate jdbc = migrated();
        List<Map<String, Object>> columns = jdbc.queryForList("select column_name, data_type, is_nullable, character_maximum_length, column_default "
                + "from information_schema.columns where table_schema = 'console' and table_name = 'research_watch_sources' order by ordinal_position");
        assertThat(columns).extracting(c -> c.get("column_name")).containsExactly("slug", "url", "kind", "extract", "layer", "expand_mode",
                "expand_prefix", "expand_max", "enabled", "added_by", "added_at", "disabled_by", "disabled_at");
        Map<String, Map<String, Object>> by = new LinkedHashMap<>();
        columns.forEach(c -> by.put((String) c.get("column_name"), c));
        assertThat(by.get("slug")).containsEntry("character_maximum_length", 32);
        assertThat(by.get("url")).containsEntry("character_maximum_length", 500).containsEntry("is_nullable", "NO");
        assertThat(by.get("kind")).containsEntry("character_maximum_length", 9);
        assertThat(by.get("extract")).containsEntry("character_maximum_length", 200);
        assertThat(by.get("layer")).containsEntry("character_maximum_length", 9);
        assertThat(by.get("expand_mode")).containsEntry("character_maximum_length", 7).containsEntry("is_nullable", "YES");
        assertThat(by.get("expand_prefix")).containsEntry("character_maximum_length", 200);
        assertThat(by.get("expand_max")).containsEntry("data_type", "smallint");
        assertThat(by.get("enabled")).containsEntry("data_type", "boolean");
        assertThat(by.get("added_at")).containsEntry("data_type", "timestamp with time zone").containsEntry("is_nullable", "NO");
        assertThat(String.valueOf(by.get("added_at").get("column_default"))).containsIgnoringCase("now");
        assertThat(jdbc.queryForList("select a.attname from pg_index i join pg_attribute a on a.attrelid = i.indrelid and a.attnum = any(i.indkey) "
                + "where i.indrelid = 'console.research_watch_sources'::regclass and i.indisprimary", String.class)).containsExactly("slug");

        // 列舉：每個合法值可 INSERT、緊鄰的非法值被擋（SQLSTATE 23514）
        int n = 0;
        for (String kind : List.of("changelog", "docs", "release", "blog", "sitemap", "search")) {
            insert(jdbc, "k-" + n++, "https://example.org/k", Map.of("kind", kind));
        }
        for (String layer : List.of("ACADEMIC", "INDUSTRY", "OSS", "COMMUNITY")) {
            insert(jdbc, "l-" + n++, "https://example.org/l", Map.of("layer", layer));
        }
        for (String mode : List.of("links", "sitemap")) {
            insert(jdbc, "m-" + n++, "https://example.org/m", Map.of("expand_mode", mode, "expand_prefix", "/x/", "expand_max", 1));
        }
        for (int max : List.of(1, 2, 3)) {
            insert(jdbc, "x-" + n++, "https://example.org/x", Map.of("expand_mode", "links", "expand_prefix", "/x/", "expand_max", max));
        }
        for (Map.Entry<String, Object> bad : Map.<String, Object>of("kind", "rss", "layer", "ACADEMICS").entrySet()) {
            assertThat(sqlState(() -> insert(jdbc, "bad-" + bad.getKey(), "https://example.org/b", Map.of(bad.getKey(), bad.getValue()))))
                    .as(bad.getKey()).isEqualTo("23514");
        }
        for (int max : List.of(0, 4)) {
            assertThat(sqlState(() -> insert(jdbc, "bad-max-" + max, "https://example.org/b",
                    Map.of("expand_mode", "links", "expand_prefix", "/x/", "expand_max", max)))).as("expand_max=" + max).isEqualTo("23514");
        }
        assertThat(sqlState(() -> insert(jdbc, "bad-mode", "https://example.org/b", Map.of("expand_mode", "rss", "expand_prefix", "/x/", "expand_max", 1))))
                .isEqualTo("23514");
        // expand_* 三欄全空或全非空：六種混合形態皆被擋
        List<Map<String, Object>> mixes = List.of(Map.of("expand_mode", "links"), Map.of("expand_prefix", "/x/"), Map.of("expand_max", 1),
                Map.of("expand_mode", "links", "expand_prefix", "/x/"), Map.of("expand_mode", "links", "expand_max", 1),
                Map.of("expand_prefix", "/x/", "expand_max", 1));
        for (int i = 0; i < mixes.size(); i++) {
            Map<String, Object> mix = mixes.get(i);
            String slug = "mix-" + i;
            assertThat(sqlState(() -> insert(jdbc, slug, "https://example.org/mix", mix))).as("混合形態 %s", mix).isEqualTo("23514");
        }
        // 停用欄 CHECK
        assertThat(sqlState(() -> insert(jdbc, "off-1", "https://example.org/o", Map.of("enabled", false)))).as("停用卻沒有 disabled_by／disabled_at").isEqualTo("23514");
        assertThat(sqlState(() -> insert(jdbc, "off-2", "https://example.org/o", Map.of("enabled", false, "disabled_by", "x")))).isEqualTo("23514");
        // extract
        List<String> badExtracts = List.of("", "a\u0001b", "a\nb", "a\u007fb");
        for (int i = 0; i < badExtracts.size(); i++) {
            String bad = badExtracts.get(i);
            String slug = "ex-bad-" + i;
            assertThat(sqlState(() -> insert(jdbc, slug, "https://example.org/e", Map.of("extract", bad)))).as("extract #%d", i).isEqualTo("23514");
        }
        insert(jdbc, "ex-200", "https://example.org/e", Map.of("extract", "x".repeat(200)));
        assertThat(sqlState(() -> insert(jdbc, "ex-201", "https://example.org/e", Map.of("extract", "x".repeat(201))))).isEqualTo("22001");
        // slug
        assertThat(sqlState(() -> insert(jdbc, "-bad", "https://example.org/s"))).isEqualTo("23514");
        assertThat(sqlState(() -> insert(jdbc, "Bad", "https://example.org/s"))).isEqualTo("23514");
        insert(jdbc, "a".repeat(32), "https://example.org/s");
        assertThat(sqlState(() -> insert(jdbc, "a".repeat(33), "https://example.org/s"))).isEqualTo("22001");
        // added_at 預設為現在且帶時區
        assertThat(jdbc.queryForObject("select added_at is not null and abs(extract(epoch from (now() - added_at))) < 60 from console.research_watch_sources "
                + "where slug = 'k-0'", Boolean.class)).isTrue();
    }

    // ── AT-965-1-2 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_1_2_theGuardAllowsOnlyThreeColumnsAndRefusesDelete() {
        JdbcTemplate jdbc = migrated();
        insert(jdbc, "t-on", "https://example.org/on", Map.of("expand_mode", "links", "expand_prefix", "/x/", "expand_max", 2));
        insert(jdbc, "t-off", "https://example.org/off", Map.of("enabled", false, "disabled_by", "t:fix", "disabled_at", java.sql.Timestamp.valueOf("2026-11-10 00:00:00")));
        List<Map<String, Object>> before = allRows(jdbc);
        Map<String, String> setters = new LinkedHashMap<>();
        setters.put("url", "url = 'https://example.org/other'");
        setters.put("kind", "kind = 'blog'");
        setters.put("extract", "extract = '另一句'");
        setters.put("layer", "layer = 'OSS'");
        setters.put("expand_mode", "expand_mode = 'sitemap'");
        setters.put("expand_prefix", "expand_prefix = '/y/'");
        setters.put("expand_max", "expand_max = 3");
        setters.put("added_by", "added_by = 'someone'");
        setters.put("added_at", "added_at = now()");
        setters.put("slug", "slug = 't-renamed'");
        setters.forEach((column, set) -> {
            assertThat(sqlState(() -> jdbc.update("update console.research_watch_sources set " + set + " where slug = 't-on'"))).as(column).startsWith(GUARD);
            assertThatThrownBy(() -> jdbc.update("update console.research_watch_sources set " + set + " where slug = 't-on'")).hasMessageContaining("research_watch_sources");
        });
        assertThat(sqlState(() -> jdbc.update("update console.research_watch_sources set enabled = false, url = 'https://example.org/x', "
                + "disabled_by = 'a', disabled_at = now() where slug = 't-on'"))).as("同句夾帶非允許欄整句被擋").startsWith(GUARD);
        assertThat(sqlState(() -> jdbc.update("delete from console.research_watch_sources where slug = 't-on'"))).as("DELETE").startsWith(GUARD);
        assertThat(allRows(jdbc)).as("被拒的語句不留任何改動").isEqualTo(before);

        assertThat(jdbc.update("update console.research_watch_sources set enabled = false, disabled_by = 'a', disabled_at = now() where slug = 't-on'")).isEqualTo(1);
        assertThat(jdbc.update("update console.research_watch_sources set enabled = true, disabled_by = null, disabled_at = null where slug = 't-off'")).isEqualTo(1);
        Map<String, Object> reenabled = jdbc.queryForMap("select enabled, disabled_by, disabled_at from console.research_watch_sources where slug = 't-off'");
        assertThat(reenabled).containsEntry("enabled", true).containsEntry("disabled_by", null).containsEntry("disabled_at", null);
        assertThat(jdbc.update("update console.research_watch_sources set disabled_by = 'x' where slug = 't-off'"))
                .as("enabled=true 而 disabled_by 非空：CHECK 不擋（Bridge 規則才負責清空）").isEqualTo(1);
    }

    // ── AT-965-1-3 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_1_3_seventeenSeedRowsAndFifteenOfThemEqualTheOldSiTableVerbatim() {
        byte[] fixture = resource("seed_si_sources.json");
        assertThat(sha256(fixture)).as("夾具 sha256（防漂移）").isEqualTo("6201d066799e7f13c18053f3474f6883fddd8091baf0ab24e3a4b1c0d348e26f");
        JsonNode sources = JSON.readTree(new String(fixture, StandardCharsets.UTF_8)).get("sources");
        JdbcTemplate jdbc = migrated();
        List<Map<String, Object>> rows = allRows(jdbc);
        assertThat(rows).hasSize(17);
        Map<String, Map<String, Object>> bySlug = new LinkedHashMap<>();
        rows.forEach(r -> bySlug.put((String) r.get("slug"), r));
        assertThat(sources.size()).isEqualTo(15);
        for (JsonNode source : sources) {
            String id = source.get("id").asString();
            Map<String, Object> row = bySlug.get(id);
            assertThat(row).as("夾具 id %s 在表內", id).isNotNull();
            assertThat(row.get("url")).as("%s url", id).isEqualTo(source.get("url").asString());
            assertThat(row.get("kind")).as("%s kind", id).isEqualTo(source.get("kind").asString());
            assertThat(row.get("extract")).as("%s extract", id).isEqualTo(source.get("extract").asString());
            boolean retired = source.has("retired") && source.get("retired").asBoolean();
            boolean expectEnabled = !retired && !"anthropic-engineering".equals(id);
            assertThat(row.get("enabled")).as("%s enabled", id).isEqualTo(expectEnabled);
            assertThat(row.get("added_by")).as("%s added_by", id).isEqualTo("migration:V24（SI research_sources.json 匯入）");
        }
        Map<String, Object> research = bySlug.get("anthropic-research");
        assertThat(research).containsEntry("kind", "sitemap").containsEntry("expand_mode", "sitemap").containsEntry("expand_prefix", "/research/")
                .containsEntry("enabled", true).containsEntry("added_by", "migration:V24（研究來源單一化種子）");
        assertThat(((Number) research.get("expand_max")).intValue()).isEqualTo(3);
        Map<String, Object> arxiv = bySlug.get("arxiv-agents");
        assertThat(arxiv).containsEntry("kind", "search").containsEntry("layer", "ACADEMIC").containsEntry("enabled", true)
                .containsEntry("expand_mode", null).containsEntry("added_by", "migration:V24（研究來源單一化種子）");
        assertThat(arxiv.get("url")).isEqualTo("https://export.arxiv.org/api/query?search_query=%28abs:%22self-improving%22+OR+abs:%22self-evolving%22+OR"
                + "+abs:%22agent+memory%22%29+AND+%28cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.SE%29&sortBy=submittedDate&sortOrder=descending&max_results=10");
        assertThat(rows.stream().filter(r -> Boolean.TRUE.equals(r.get("enabled"))).count()).as("啟用恰 10").isEqualTo(10);
        List<Object> disabled = rows.stream().filter(r -> Boolean.FALSE.equals(r.get("enabled"))).map(r -> r.get("slug")).toList();
        assertThat(disabled).as("停用恰 7（6 個 retired 加 anthropic-engineering）").hasSize(7).contains("anthropic-engineering");
        assertThat(bySlug.get("anthropic-engineering").get("disabled_by")).isEqualTo("migration:V24（以 anthropic-research 取代）");
        for (Map<String, Object> row : rows) {
            assertThat(row.get("added_at")).as("%s added_at", row.get("slug")).isEqualTo(SEED_TIME);
            if (Boolean.FALSE.equals(row.get("enabled"))) {
                assertThat(row.get("disabled_at")).isEqualTo(SEED_TIME);
            }
        }
        assertThat(SEED_TIME).isEqualTo("2026-11-10T00:00:00+00:00");
    }

    // ── AT-965-1-4 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_1_4_exactlyFourFetchDomainsAreSeededAndWebIsUntouched() {
        String database = createDatabase();
        flyway(database, "23").migrate();
        JdbcTemplate jdbc = jdbcOf(database);
        List<Map<String, Object>> before = jdbc.queryForList("select list_kind, host from console.research_allowlist_entries order by 1, 2");
        flyway(database, null).migrate();
        List<Map<String, Object>> after = jdbc.queryForList("select list_kind, host, layer, min_interval_seconds, enabled, tos_acknowledged, added_by, "
                + utc("added_at") + " as added_at from console.research_allowlist_entries order by 1, 2");
        assertThat(after).hasSize(before.size() + 4);
        assertThat(after.stream().filter(r -> "WEB".equals(r.get("list_kind"))).count()).as("WEB 零新增").isZero();
        Map<String, String> expected = Map.of("www.anthropic.com", "INDUSTRY", "github.com", "OSS", "code.claude.com", "INDUSTRY",
                "developers.openai.com", "INDUSTRY");
        Map<String, Map<String, Object>> seeded = new LinkedHashMap<>();
        after.stream().filter(r -> expected.containsKey(r.get("host"))).forEach(r -> seeded.put((String) r.get("host"), r));
        assertThat(seeded.keySet()).containsExactlyInAnyOrderElementsOf(expected.keySet());
        seeded.forEach((host, row) -> {
            assertThat(row).containsEntry("list_kind", "FETCH").containsEntry("layer", expected.get(host)).containsEntry("enabled", true)
                    .containsEntry("tos_acknowledged", false).containsEntry("added_by", "migration:V24（自我進化研究來源種子）")
                    .containsEntry("added_at", SEED_TIME);
            assertThat(((Number) row.get("min_interval_seconds")).intValue()).isEqualTo(5);
        });
        List<Object> hosts = after.stream().map(r -> r.get("host")).toList();
        assertThat(hosts).doesNotContain("raw.githubusercontent.com", "platform.openai.com", "export.arxiv.org");
        List<String> base = List.of("export.arxiv.org", "api.semanticscholar.org", "api.github.com", "api.stackexchange.com", "arxiv.org");
        for (Map<String, Object> row : allRows(jdbc)) {
            if (Boolean.TRUE.equals(row.get("enabled"))) {
                String url = (String) row.get("url");
                String host = url.substring("https://".length()).split("[/?]", 2)[0];
                assertThat(seeded.containsKey(host) || base.contains(host)).as("啟用的種子追蹤來源 %s 的 host %s 在種子網域或部署基底內", row.get("slug"), host).isTrue();
            }
        }
    }

    // ── AT-965-1-5 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_1_5_theSeedInsertStatementsAreIdempotent() throws IOException {
        String sql = new String(new org.springframework.core.io.ClassPathResource("db/migration/V24__research_watch_sources.sql").getInputStream().readAllBytes(),
                StandardCharsets.UTF_8);
        Matcher matcher = Pattern.compile("INSERT INTO console\\.research_[\\s\\S]*?;\\n").matcher(sql);
        List<String> statements = new ArrayList<>();
        while (matcher.find()) {
            statements.add(matcher.group());
        }
        assertThat(statements).as("擷取範圍非空：兩段種子 INSERT").hasSize(2);
        assertThat(statements).allSatisfy(s -> assertThat(s).contains("ON CONFLICT"));
        assertThat("INSERT INTO console.research_watch_sources ... ;\n").as("負控：擷取式對不含種子的字串不命中").doesNotContain("ON CONFLICT");

        String database = createDatabase();
        Flyway flyway = flyway(database, null);
        flyway.migrate();
        JdbcTemplate jdbc = jdbcOf(database);
        jdbc.update("update console.research_watch_sources set enabled = false, disabled_by = 'manual', disabled_at = now() where slug = 'cc-releases'");
        int watch = jdbc.queryForObject("select count(*) from console.research_watch_sources", Integer.class);
        int domains = jdbc.queryForObject("select count(*) from console.research_allowlist_entries", Integer.class);
        for (String statement : statements) {
            jdbc.execute(statement);
        }
        assertThat(jdbc.queryForObject("select count(*) from console.research_watch_sources", Integer.class)).isEqualTo(watch);
        assertThat(jdbc.queryForObject("select count(*) from console.research_allowlist_entries", Integer.class)).isEqualTo(domains);
        assertThat(jdbc.queryForObject("select enabled from console.research_watch_sources where slug = 'cc-releases'", Boolean.class))
                .as("被手動停用的列保持停用（ON CONFLICT DO NOTHING 不覆寫）").isFalse();
        assertThat(flyway.migrate().migrationsExecuted).as("再跑一次沒有新遷移").isZero();
    }

    // ── AT-965-1-6 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_1_6_theRedefinedGuardKeepsTheNineExistingArmsAndAddsTheTenth() {
        JdbcTemplate jdbc = migrated();
        String source = jdbc.queryForObject("select pg_get_functiondef('console.research_controlled_update_guard'::regproc)", String.class);
        Matcher matcher = Pattern.compile("WHEN '(\\w+)' THEN ARRAY\\[(.*?)\\]", Pattern.DOTALL).matcher(source);
        Map<String, List<String>> arms = new LinkedHashMap<>();
        while (matcher.find()) {
            List<String> columns = new ArrayList<>();
            Matcher quoted = Pattern.compile("'(\\w+)'").matcher(matcher.group(2));
            while (quoted.find()) {
                columns.add(quoted.group(1));
            }
            arms.put(matcher.group(1), columns);
        }
        assertThat(arms).as("條目恰十條").hasSize(10);
        List<String> names = new ArrayList<>(arms.keySet());
        GUARD_ARMS_V16.forEach((table, columns) -> assertThat(arms.get(table)).as("既有條目 %s 逐欄逐序相等", table).containsExactlyElementsOf(columns));
        assertThat(names.subList(0, 9)).as("前九條與 V16 同序").containsExactlyElementsOf(GUARD_ARMS_V16.keySet());
        assertThat(arms.get("research_watch_sources")).containsExactly("enabled", "disabled_by", "disabled_at");
        assertThat(source).contains("TG_OP = 'DELETE'").contains("allowed IS NULL").contains("to_jsonb(NEW) - allowed").contains("IS DISTINCT FROM");
    }

    // ── AT-965-1-7 ───────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_1_7_theUrlCheckEqualsTheConColumnOfAppendixDRowByRow() {
        byte[] table = resource("appendix-d.txt");
        assertThat(sha256(table)).as("附錄 D 複本 sha256").isEqualTo("25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89");
        JdbcTemplate jdbc = migrated();
        int index = 0;
        List<String> mismatches = new ArrayList<>();
        for (String line : new String(table, StandardCharsets.UTF_8).split("\n")) {
            if (line.isEmpty()) {
                continue;
            }
            String[] cells = line.split("\t");
            String url = cells[0];
            boolean con = "T".equals(cells[2]);
            String slug = "p-" + index++;
            String state = sqlState(() -> insert(jdbc, slug, url));
            if (con && state != null) {
                mismatches.add("CON=T 卻被擋（" + state + "）：" + url);
            }
            if (!con && !"23514".equals(state)) {
                mismatches.add("CON=F 卻未被 CHECK 擋（" + state + "）：" + url);
            }
        }
        assertThat(mismatches).as("附錄 D 逐列").isEmpty();
        assertThat(index).isEqualTo(42);
        String base = "https://x.com/";
        insert(jdbc, "len-500", base + "a".repeat(500 - base.length()));
        assertThat(sqlState(() -> insert(jdbc, "len-501", base + "a".repeat(501 - base.length())))).as("501 字元（欄位長度）").isEqualTo("22001");
    }

    // ── AT-965-1-E-1 ─────────────────────────────────────────────────────────────────────────

    @Test
    void AT_965_1_E_1_theUpgradeLeavesEveryExistingResearchTableGuardedAndUntouched() {
        String database = createDatabase();
        flyway(database, "23").migrate();
        JdbcTemplate jdbc = jdbcOf(database);
        List<String> tables = jdbc.queryForList("select table_name from information_schema.tables where table_schema = 'console' and table_name like "
                + "'research\\_%' and table_type = 'BASE TABLE' order by 1", String.class);
        assertThat(tables).as("V23 時十八張 research_ 表").hasSize(18);
        String before = snapshot(jdbc, tables);
        flyway(database, null).migrate();
        assertThat(snapshot(jdbc, tables)).as("既有十八張表（除刻意多四列種子網域的 allowlist 外）的列數前後一致").isEqualTo(before);
        for (String table : tables) {
            int count = jdbc.queryForObject("select count(*) from console." + table, Integer.class);
            if (count > 0) {
                assertThat(sqlState(() -> jdbc.update("delete from console." + table))).as("%s DELETE", table).startsWith(GUARD);
            }
        }
    }

    private static String snapshot(JdbcTemplate jdbc, List<String> tables) {
        StringBuilder out = new StringBuilder();
        for (String table : tables) {
            if ("research_allowlist_entries".equals(table)) {
                continue;                                               // V24 刻意多四列種子網域
            }
            out.append(table).append('=').append(jdbc.queryForObject("select count(*) from console." + table, Integer.class)).append(';');
        }
        return out.toString();
    }
}
