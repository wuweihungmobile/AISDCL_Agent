package com.aisdlc.console.adapter.in.web;

import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aisdlc.console.application.port.out.BackupJobRepository;
import com.aisdlc.console.application.service.BackupJobReconciler;
import com.aisdlc.console.architecture.BackupReasonsContractTest;
import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.BackupSeam;
import com.aisdlc.console.support.FakeBackupRunner;
import com.aisdlc.console.support.FakeBackupRunner.Behavior;
import com.aisdlc.console.support.MutableClock;
import com.jayway.jsonpath.PathNotFoundException;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.Import;
import org.springframework.http.HttpMethod;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TimeZone;
import java.util.TreeSet;
import java.util.UUID;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 備份功能的 backend 面（{@code /api/v1/sysadmin/backups}：總覽、工作紀錄、單筆工作、僅 ADMIN 的手動觸發；TCS-SysAdminBackup-20261027 的 BQ 載具六十二個 AT），
 * 對真 PostgreSQL（Testcontainers）、真 Spring Security 鏈、可變專屬時鐘 {@link MutableClock} 與假 runner（{@link FakeBackupRunner}）驗映射的每一列。
 *
 * <p>為什麼重要：這支 API 決定掌舵者在畫面上看到的是不是真相——「量不到」被讀成「沒有」（空陣列、0）會讓人以為資料庫沒有備份而恐慌，或更糟地以為備份正常；
 * 逾期、離線、中斷判錯會讓真正的失敗被忽略；手動觸發若放行第二個併發工作、放行 OPERATOR、或寫檔失敗卻留一列永遠 QUEUED 的工作，備份本身就會被這個「控制面」弄壞。
 * 輸出尾段與觸發者只給 ADMIN、機密一律遮罩、整個回應與日誌與審計不含 DB 密碼與加密金鑰，是這個控制面不成為新攻擊面的底線。
 *
 * <p><b>時鐘（必讀）</b>：只撥專屬 {@code BackupClock}（{@link BackupSeam}）；全域 {@code Clock} 不動，所以 {@code AbstractApiIT} 的 JVM 靜態 token 照常使用，也不會因本類別先跑而讓
 * 同 fork 的其餘 IT 全部 401。<b>審計列</b>：{@code audit_log.occurred_at} 取自全域時鐘，測試不撥它，所以對審計列一律以 {@code method}、{@code path}、{@code http_status} 篩選比對，不依時間序。
 * 控制面檔案住 {@code @TempDir}（輸出卷與請求卷各一），由 {@code @DynamicPropertySource} 注入；對帳排程週期設成很大的值，使背景排程不與測試的明確呼叫賽跑。
 */
@Import(BackupSeam.class)
class BackupApiIT extends AbstractApiIT {

    private static final String BACKUPS = "/api/v1/sysadmin/backups";
    private static final String JOBS = BACKUPS + "/jobs";
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Instant NOW = BackupSeam.DEFAULT_NOW;
    private static final String LAST_MODIFIED_PATH = "Z";

    @TempDir
    static Path exportRoot;
    @TempDir
    static Path requestRoot;

    @DynamicPropertySource
    static void backupProperties(DynamicPropertyRegistry registry) {
        registry.add("console.backup.export-dir", () -> exportRoot.toString());
        registry.add("console.backup.request-dir", () -> requestRoot.toString());
        registry.add("console.backup.reconcile-interval-ms", () -> "3600000");
    }

    @Autowired
    MutableClock clock;
    @Autowired
    BackupJobReconciler reconciler;
    @Autowired
    BackupJobRepository repository;
    @Autowired
    BackupSeam.ObservedAuditTrail observed;
    @Autowired
    ApplicationContext context;
    @Value("${console.encryption.key}")
    String encryptionKey;

    private FakeBackupRunner runner;
    private TimeZone originalZone;

    @BeforeEach
    void resetControlPlane() throws IOException {
        originalZone = TimeZone.getDefault();
        runner = new FakeBackupRunner(exportRoot, requestRoot, clock);
        runner.stop();
        runner.clearDirectories();
        clock.set(NOW);
        jdbc.execute("TRUNCATE console.backup_jobs");
        observed.reset();
    }

    @AfterEach
    void restoreWorld() throws IOException {
        runner.stop();
        TimeZone.setDefault(originalZone);
        jdbc.execute("do $$ begin if to_regclass('console.backup_jobs_off') is not null and to_regclass('console.backup_jobs') is null "
                + "then alter table console.backup_jobs_off rename to backup_jobs; end if; end $$");
        if (!Files.isDirectory(requestRoot)) {
            Files.deleteIfExists(requestRoot);
            Files.createDirectories(requestRoot);
        }
    }

    // ── 夾具與小幫手 ────────────────────────────────────────────────────────────────────────

    private void write(String relativePath, String content) {
        try {
            runner.write(relativePath, content);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String iso(Instant instant) {
        return instant.toString();
    }

    /** 健康的控制面：INFO_2REPO＋LOGICAL_2、六條 cron（Asia/Taipei）、新鮮心跳；沒有 jobs 檔。 */
    private void seed() {
        seedInfo(FakeBackupRunner.fixture("info-2repo.json"), FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL);
        write("export/logical.json", FakeBackupRunner.fixture("logical-2.json").strip());
        write("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei"));
        heartbeat(3, false);
    }

    private void seedInfo(String infoArray, String retention, String repos) {
        write("export/info.json", FakeBackupRunner.infoJson(iso(clock.instant().minusSeconds(10)), infoArray, retention, repos));
    }

    private void heartbeat(long ageSeconds, boolean lockHeld) {
        write("export/heartbeat", FakeBackupRunner.heartbeat(clock.instant().minusSeconds(ageSeconds), lockHeld));
    }

    private void job(String name, String json) {
        write("export/jobs/" + name + ".json", json);
    }

    private Resp overview(String token) {
        return api.get(token, BACKUPS);
    }

    private Resp overview() {
        return overview(admin());
    }

    private Resp post(String token, Object body) {
        return api.post(token, JOBS, body);
    }

    private static Map<String, Object> request(String type) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("type", type);
        body.put("confirm", true);
        return body;
    }

    /** 讀 JsonPath；鍵不存在（缺席）與 null 等價，都回 null。 */
    private static Object opt(Resp resp, String path) {
        try {
            return resp.<Object>read(path);
        } catch (PathNotFoundException e) {
            return null;
        }
    }

    private long jobRows() {
        Long count = jdbc.queryForObject("select count(*) from console.backup_jobs", Long.class);
        return count == null ? 0 : count;
    }

    private List<String> requestFiles() {
        try (Stream<Path> files = Files.list(requestRoot)) {
            return files.map(p -> p.getFileName().toString()).sorted().toList();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** 只清請求目錄的檔案（保留已播種的匯出檔）。 */
    private void clearRequestFiles() {
        try (Stream<Path> files = Files.list(requestRoot)) {
            for (Path path : files.toList()) {
                Files.delete(path);
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private void assertNothingWritten(String label) {
        assertThat(jobRows()).as(label + "：backup_jobs 零列").isZero();
        assertThat(requestFiles()).as(label + "：請求目錄零檔（含無 .tmp）").isEmpty();
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> mapOf(Object value) {
        return (Map<String, Object>) value;
    }

    @SuppressWarnings("unchecked")
    private static List<String> stringsOf(Object value) {
        return (List<String>) value;
    }

    /** 改 INFO_2REPO 的第一個 stanza：{@code mutate} 收 backup 清單與 repo 清單。 */
    @SuppressWarnings("unchecked")
    private static String infoMutated(java.util.function.BiConsumer<List<Map<String, Object>>, List<Map<String, Object>>> mutate) {
        List<Map<String, Object>> stanzas = JSON.readValue(FakeBackupRunner.fixture("info-2repo.json"), List.class);
        Map<String, Object> stanza = stanzas.get(0);
        mutate.accept((List<Map<String, Object>>) stanza.get("backup"), (List<Map<String, Object>>) stanza.get("repo"));
        return JSON.writeValueAsString(stanzas);
    }

    /** 每個 repo 各指定最近全備與最近差異備份的 stop（null＝該 repo 沒有該類備份）。 */
    private static String infoStops(Instant repo1Full, Instant repo2Full, Instant repo1Diff, Instant repo2Diff) {
        List<Map<String, Object>> backups = new ArrayList<>();
        addBackup(backups, "full", 1, repo1Full);
        addBackup(backups, "full", 2, repo2Full);
        addBackup(backups, "diff", 1, repo1Diff);
        addBackup(backups, "diff", 2, repo2Diff);
        Map<String, Object> stanza = new LinkedHashMap<>();
        stanza.put("name", "aisdlc");
        stanza.put("repo", List.of(Map.of("key", 1, "status", Map.of("code", 0, "message", "ok")),
                Map.of("key", 2, "status", Map.of("code", 0, "message", "ok"))));
        stanza.put("backup", backups);
        return JSON.writeValueAsString(List.of(stanza));
    }

    private static void addBackup(List<Map<String, Object>> backups, String type, int repo, Instant stop) {
        if (stop == null) {
            return;
        }
        Map<String, Object> backup = new LinkedHashMap<>();
        backup.put("label", stop.getEpochSecond() + ("full".equals(type) ? "F" : "D") + repo);
        backup.put("type", type);
        backup.put("prior", null);
        backup.put("error", false);
        backup.put("database", Map.of("id", 1, "repo-key", repo));
        backup.put("timestamp", Map.of("start", stop.getEpochSecond() - 60, "stop", stop.getEpochSecond()));
        backup.put("info", Map.of("size", 1000, "delta", 1000, "repository", Map.of("size", 100, "delta", 100)));
        backups.add(backup);
    }

    private void waitFor(java.util.function.BooleanSupplier condition, String what) {
        long deadline = System.nanoTime() + Duration.ofSeconds(10).toNanos();
        while (System.nanoTime() < deadline) {
            if (condition.getAsBoolean()) {
                return;
            }
            try {
                Thread.sleep(20);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException(e);
            }
        }
        throw new AssertionError("逾時仍未等到：" + what);
    }

    private boolean resultExists(String id) {
        return Files.exists(exportRoot.resolve("results").resolve(id + ".json"));
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // FR-BK-02　備份清單
    // ══════════════════════════════════════════════════════════════════════════════════════════

    @Test
    void AT_BK_02_1_1_theListMergesPgBackRestAndLogicalBackupsNewestFirstWithEveryKey() {
        seed();

        Resp resp = overview();

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<String>>read("$.data.backups[*].label")).containsExactly("aisdlc-20261026-183000.dump",
                "20261026-020002F_20261027-020001D", "20261026-020000F_20261027-020000D", "aisdlc-20261025-183000.dump", "20261026-020002F",
                "20261026-020000F");
        List<Map<String, Object>> backups = resp.read("$.data.backups");
        assertThat(backups).hasSize(6);
        for (Map<String, Object> row : backups) {
            assertThat(row.keySet()).containsExactly("kind", "label", "location", "startedAt", "finishedAt", "durationSeconds", "databaseSizeBytes",
                    "repoSizeBytes", "baseLabel", "result");
        }
        Map<String, Map<String, Object>> byLabel = new LinkedHashMap<>();
        backups.forEach(row -> byLabel.put((String) row.get("label"), row));
        Map<String, Object> repo1Full = byLabel.get("20261026-020000F");
        assertThat(repo1Full).containsEntry("kind", "full").containsEntry("location", "repo1").containsEntry("finishedAt", "2026-10-25T18:10:00Z")
                .containsEntry("startedAt", "2026-10-25T18:00:00Z").containsEntry("durationSeconds", 600).containsEntry("databaseSizeBytes", 33554432)
                .containsEntry("repoSizeBytes", 4194304).containsEntry("baseLabel", null).containsEntry("result", "ok");
        assertThat(byLabel.get("20261026-020002F")).containsEntry("location", "repo2").containsEntry("finishedAt", "2026-10-25T18:12:00Z")
                .containsEntry("durationSeconds", 718);
        assertThat(byLabel.get("20261026-020000F_20261027-020000D")).containsEntry("kind", "diff").containsEntry("baseLabel", "20261026-020000F")
                .containsEntry("finishedAt", "2026-10-26T18:02:00Z").containsEntry("location", "repo1");
        assertThat(byLabel.get("20261026-020002F_20261027-020001D")).containsEntry("baseLabel", "20261026-020002F").containsEntry("location", "repo2")
                .containsEntry("finishedAt", "2026-10-26T18:03:00Z");
        Map<String, Object> logical = byLabel.get("aisdlc-20261026-183000.dump");
        assertThat(logical).containsEntry("kind", "logical").containsEntry("location", "logical").containsEntry("startedAt", null)
                .containsEntry("durationSeconds", null).containsEntry("databaseSizeBytes", null).containsEntry("baseLabel", null)
                .containsEntry("finishedAt", "2026-10-26T18:30:05Z").containsEntry("repoSizeBytes", 1049600).containsEntry("result", "ok");
        for (Map<String, Object> row : backups) {
            assertThat((String) row.get("finishedAt")).as("所有時間為帶 Z 的 ISO-8601").endsWith(LAST_MODIFIED_PATH);
        }
    }

    @Test
    void AT_BK_02_1_E_1_theOrderIsDeterministicEvenWhenTheFilesAreShuffledAndTiesBreakByLabelDescending() {
        seedInfo(infoMutated((backups, repos) -> {
            java.util.Collections.reverse(backups);
            Map<String, Object> incr = new LinkedHashMap<>(backups.get(0));
            incr.put("label", "20261026-020000F_20261027-100000I");
            incr.put("type", "incr");
            backups.add(incr);
            // 平手：repo1 全備與 repo2 全備的 stop 相同
            Map<String, Object> repo2Full = backups.stream().filter(b -> "20261026-020002F".equals(b.get("label"))).findFirst().orElseThrow();
            repo2Full.put("timestamp", Map.of("start", 1792951202, "stop", 1792951800));
        }), FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL);
        write("export/logical.json", FakeBackupRunner.logicalJson(iso(NOW), "[{\"name\":\"aisdlc-20261026-183000.dump\",\"size\":1049600,"
                + "\"modified\":\"2026-10-26T18:30:05Z\"},{\"name\":\"aisdlc-20261025-183000.dump\",\"size\":1048576,\"modified\":\"2026-10-25T18:30:05Z\"}]"));
        write("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei"));
        heartbeat(3, false);

        Resp first = overview();
        Resp second = overview();

        List<String> labels = first.read("$.data.backups[*].label");
        assertThat(labels).as("同一輸入兩次呼叫逐位元相同").isEqualTo(second.read("$.data.backups[*].label"));
        assertThat(first.<Object>read("$.data.backups")).isEqualTo(second.<Object>read("$.data.backups"));
        assertThat(labels.indexOf("20261026-020002F")).as("stop 相同者依 label 字典序降冪").isLessThan(labels.indexOf("20261026-020000F"));
        assertThat(labels.get(0)).as("新到舊：最新的是邏輯備份").isEqualTo("aisdlc-20261026-183000.dump");
        assertThat(first.<List<String>>read("$.data.backups[?(@.label=='20261026-020000F_20261027-100000I')].kind")).as("incr 不被歸成 diff")
                .containsExactly("incr");
    }

    @Test
    void AT_BK_02_2_1_aBackupWithPageChecksumErrorsIsOkWithErrorsAndAMissingErrorKeyIsOk() {
        seedInfo(infoMutated((backups, repos) -> backups.stream().filter(b -> "diff".equals(b.get("type")) && ((Map<?, ?>) b.get("database")).get("repo-key")
                .equals(1)).forEach(b -> b.put("error", true))), FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL);
        write("export/logical.json", FakeBackupRunner.logicalJson(iso(NOW), "[]"));
        write("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei"));
        heartbeat(3, false);

        Resp resp = overview();

        assertThat(resp.<List<String>>read("$.data.backups[?(@.label=='20261026-020000F_20261027-020000D')].result")).containsExactly("ok_with_errors");
        assertThat(resp.<List<String>>read("$.data.backups[?(@.label!='20261026-020000F_20261027-020000D')].result")).containsOnly("ok");

        seedInfo(infoMutated((backups, repos) -> backups.forEach(b -> b.remove("error"))), FakeBackupRunner.RETENTION_DEFAULT,
                FakeBackupRunner.REPOS_BOTH_LOCAL);
        assertThat(overview().<List<String>>read("$.data.backups[*].result")).as("缺 error 鍵視為 ok").containsOnly("ok").hasSize(4);
    }

    @Test
    void AT_BK_02_4_1_aBrokenRepoIsReportedAsABrokenRepoNotAsNoBackups() {
        seedInfo(infoMutated((backups, repos) -> {
            backups.removeIf(b -> ((Map<?, ?>) b.get("database")).get("repo-key").equals(2));
            repos.get(1).put("status", Map.of("code", 99, "message", "other"));
        }), FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL);
        write("export/logical.json", FakeBackupRunner.logicalJson(iso(NOW), "[]"));
        write("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei"));
        heartbeat(3, false);

        Resp resp = overview();

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Object>read("$.data.control.reason")).isNull();
        assertThat(resp.<List<Object>>read("$.data.repos")).hasSize(2);
        assertThat(resp.<Integer>read("$.data.repos[1].statusCode")).isEqualTo(99);
        assertThat(resp.<String>read("$.data.repos[1].statusMessage")).isEqualTo("other");
        assertThat(resp.<Integer>read("$.data.repos[0].statusCode")).isZero();
        assertThat(resp.<List<String>>read("$.data.backups[*].location")).as("只含 repo1 的備份，repo2 不補佔位列").containsOnly("repo1").hasSize(2);
    }

    @Test
    void AT_BK_02_5_1_aClusterWithNoBackupsIsALegalEmptyStateNotAnError() {
        seedInfo(infoMutated((backups, repos) -> backups.clear()), FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL);
        write("export/logical.json", FakeBackupRunner.logicalJson(iso(NOW), "[]"));
        write("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei"));
        heartbeat(3, false);

        Resp resp = overview();

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Object>read("$.data.control.reason")).isNull();
        assertThat(resp.<List<Object>>read("$.data.backups")).isEmpty();
        List<Map<String, Object>> cards = resp.read("$.data.cards");
        assertThat(cards).hasSize(4);
        for (Map<String, Object> card : cards) {
            assertThat(card).containsEntry("status", "no_run").containsEntry("never", true).containsEntry("overdue", false);
            assertThat(card.get("latestBackup")).as("%s 的 latestBackup", card.get("job")).isNull();
        }
    }

    @Test
    void AT_BK_02_5_E_1_aStanzaFreeInfoGivesEmptyReposAndNoRetentionInsteadOfInventedDefaults() {
        seedInfo("[]", "null", FakeBackupRunner.REPOS_BOTH_LOCAL);
        write("export/logical.json", FakeBackupRunner.logicalJson(iso(NOW), "[]"));
        write("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei"));
        heartbeat(3, false);

        Resp resp = overview();

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<Object>>read("$.data.backups")).isEmpty();
        assertThat(resp.<List<Object>>read("$.data.repos")).isEmpty();
        assertThat(resp.<Object>read("$.data.schedule.retention")).isNull();
        assertThat(resp.<List<String>>read("$.data.control.warnings")).contains("retention_unavailable");
    }

    @Test
    void AT_BK_02_6_E_1_theLocalFlagIsPassedThroughVerbatimAndAMissingOneIsASchemaMismatchNotAFalse() {
        String externalRepos = "[{\"repo\":1,\"type\":\"posix\",\"endpoint_host\":null,\"local\":true},"
                + "{\"repo\":2,\"type\":\"s3\",\"endpoint_host\":\"s3.amazonaws.com\",\"local\":false}]";
        seed();
        seedInfo(FakeBackupRunner.fixture("info-2repo.json"), FakeBackupRunner.RETENTION_DEFAULT, externalRepos);
        Resp external = overview();
        assertThat(external.<Boolean>read("$.data.repos[0].local")).isTrue();
        assertThat(external.<Boolean>read("$.data.repos[1].local")).isFalse();
        assertThat(external.<String>read("$.data.repos[1].endpointHost")).isEqualTo("s3.amazonaws.com");
        assertThat(external.<Object>read("$.data.repos[0].endpointHost")).isNull();

        seedInfo(FakeBackupRunner.fixture("info-2repo.json"), FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL);
        assertThat(overview().<Boolean>read("$.data.repos[1].local")).isTrue();

        seedInfo(FakeBackupRunner.fixture("info-2repo.json"), FakeBackupRunner.RETENTION_DEFAULT,
                "[{\"repo\":1,\"type\":\"posix\",\"endpoint_host\":null},{\"repo\":2,\"type\":\"s3\",\"endpoint_host\":\"minio\"}]");
        Resp missing = overview();
        assertThat(missing.status()).isEqualTo(200);
        assertThat(missing.<String>read("$.data.control.reason")).as("缺 local 鍵＝schema_mismatch，不預設成 false").isEqualTo("schema_mismatch");
        assertThat(missing.<Object>read("$.data.repos")).isNull();
        assertThat(missing.<Object>read("$.data.cards")).isNull();
        seedInfo(FakeBackupRunner.fixture("info-2repo.json"), FakeBackupRunner.RETENTION_DEFAULT,
                "[{\"repo\":1,\"type\":\"posix\",\"endpoint_host\":null,\"local\":\"yes\"},{\"repo\":2,\"type\":\"s3\",\"endpoint_host\":\"minio\",\"local\":true}]");
        assertThat(overview().<String>read("$.data.control.reason")).as("非布林的 local 同樣 schema_mismatch").isEqualTo("schema_mismatch");
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // FR-BK-03　排程與保留（唯讀）
    // ══════════════════════════════════════════════════════════════════════════════════════════

    private static final Map<String, String> NEXT_RUNS = Map.of("full", "2026-10-31T18:00:00Z", "diff", "2026-10-27T18:00:00Z",
            "dump", "2026-10-27T18:30:00Z", "verify", "2026-10-27T20:00:00Z", "expire", "2026-10-27T19:00:00Z", "wal_clean", "2026-10-27T19:30:00Z");

    @Test
    void AT_BK_03_3_2_nextRunAtIsComputedInTheScheduleZoneAndDoesNotFollowTheJvmZoneOrTheGlobalClock() {
        seed();
        TimeZone.setDefault(TimeZone.getTimeZone("America/Los_Angeles"));
        Resp resp = overview();

        assertThat(resp.<String>read("$.data.timezone")).isEqualTo("Asia/Taipei");
        List<Map<String, Object>> entries = resp.read("$.data.schedule.entries");
        assertThat(entries).hasSize(6);
        for (Map<String, Object> entry : entries) {
            assertThat(entry.get("nextRunAt")).as("%s 的 nextRunAt（UTC Z）", entry.get("job")).isEqualTo(NEXT_RUNS.get(entry.get("job")));
        }
        TimeZone.setDefault(TimeZone.getTimeZone("Asia/Tokyo"));
        List<Map<String, Object>> again = overview().read("$.data.schedule.entries");
        assertThat(again).as("JVM 預設時區改變後六值不變").isEqualTo(entries);

        assertThat(context.getBeansOfType(java.time.Clock.class)).as("全域 Clock 只有系統時鐘一個，沒被換成可變時鐘").hasSize(1);
        Instant globalNow = context.getBean(java.time.Clock.class).instant();
        assertThat(Duration.between(globalNow, Instant.now()).abs()).as("全域 Clock 仍是真實時間，不是 2026-10-27 的專屬時鐘").isLessThan(Duration.ofMinutes(5));
        clock.set(Instant.parse("2026-11-02T02:00:00Z"));
        heartbeat(3, false);
        assertThat(overview(admin()).status()).as("專屬時鐘撥到 2026-11-02 後，以 AbstractApiIT 既有的 admin token 呼叫仍 200（JWT、限流與審計吃全域 Clock）").isEqualTo(200);
    }

    @Test
    void AT_BK_03_3_E_1_theScheduleZoneIsHonouredAnUnparsableCronOnlyNullsItsOwnEntryAndABadZoneIsASchemaMismatch() {
        seed();
        write("export/schedule.json", FakeBackupRunner.scheduleJson("UTC"));
        assertThat(overview().<String>read("$.data.schedule.entries[1].nextRunAt")).as("(a) 以該時區計算").isEqualTo("2026-10-28T02:00:00Z");

        write("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei").replace("0 2 * * 1-6", "0 2 * * 1-6/0"));
        Resp unparsable = overview();
        assertThat(unparsable.status()).isEqualTo(200);
        assertThat(unparsable.<Object>read("$.data.schedule.entries[1].nextRunAt")).as("(b) 該條 nextRunAt 為 null").isNull();
        assertThat(unparsable.<String>read("$.data.schedule.entries[0].nextRunAt")).as("其餘五條照常").isEqualTo("2026-10-31T18:00:00Z");
        assertThat(unparsable.<List<String>>read("$.data.control.warnings")).contains("cron_unparsable:diff");
        assertThat(unparsable.<Object>read("$.data.cards[1].lastDueAt")).isNull();
        assertThat(unparsable.<Boolean>read("$.data.cards[1].overdue")).isFalse();

        write("export/schedule.json", FakeBackupRunner.scheduleJson("Mars/Base"));
        Resp badZone = overview();
        assertThat(badZone.status()).as("(c) 不丟 500").isEqualTo(200);
        assertThat(badZone.<String>read("$.data.control.reason")).isEqualTo("schema_mismatch");
        for (String block : List.of("timezone", "schedule", "cards", "backups", "repos")) {
            assertThat(badZone.<Object>read("$.data." + block)).as(block).isNull();
        }
    }

    @Test
    void AT_BK_03_4_E_1_aMissingOrNullRetentionIsNullWithAWarningNeverADefault() {
        seed();
        seedInfo(FakeBackupRunner.fixture("info-2repo.json"), "null", FakeBackupRunner.REPOS_BOTH_LOCAL);
        Resp asNull = overview();
        assertThat(asNull.status()).isEqualTo(200);
        assertThat(asNull.<Object>read("$.data.schedule.retention")).isNull();
        assertThat(asNull.<List<String>>read("$.data.control.warnings")).contains("retention_unavailable");
        assertThat(asNull.<List<Object>>read("$.data.schedule.entries")).as("entries 不受影響").hasSize(6);

        write("export/info.json", "{\"schema_rev\":1,\"generated_at\":\"" + iso(NOW.minusSeconds(10)) + "\",\"ok\":true,\"info\":"
                + FakeBackupRunner.fixture("info-2repo.json").strip() + ",\"repos\":" + FakeBackupRunner.REPOS_BOTH_LOCAL + "}");
        Resp missing = overview();
        assertThat(missing.<Object>read("$.data.schedule.retention")).as("缺鍵亦然").isNull();
        assertThat(missing.<List<String>>read("$.data.control.warnings")).contains("retention_unavailable");

        seedInfo(FakeBackupRunner.fixture("info-2repo.json"), FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL);
        Resp present = overview();
        assertThat(present.<Integer>read("$.data.schedule.retention.repo1.full")).isEqualTo(4);
        assertThat(present.<Integer>read("$.data.schedule.retention.repo1.diff")).isEqualTo(7);
        assertThat(present.<Integer>read("$.data.schedule.retention.repo2.full")).isEqualTo(4);
        assertThat(present.<Object>read("$.data.schedule.retention.repo2.diff")).isNull();
        assertThat(present.<Integer>read("$.data.schedule.retention.logicalDays")).isEqualTo(28);
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // FR-BK-04　最近狀態卡
    // ══════════════════════════════════════════════════════════════════════════════════════════

    @Test
    void AT_BK_04_1_1_fourCardsInFixedOrderCarryTheStateFilesAndOnlyFullAndDiffCarryTheLatestBackup() {
        seed();
        job("full", FakeBackupRunner.jobOk("full", "scheduled", "2026-10-26T18:00:00Z", "2026-10-26T18:10:00Z"));
        job("diff", FakeBackupRunner.jobOk("diff", "scheduled", "2026-10-26T18:00:00Z", "2026-10-26T18:02:30Z"));
        job("dump", FakeBackupRunner.jobOk("dump", "scheduled", "2026-10-26T18:30:00Z", "2026-10-26T18:30:40Z"));

        Resp resp = overview();

        assertThat(resp.<List<String>>read("$.data.cards[*].job")).containsExactly("full", "diff", "dump", "verify");
        for (int i = 0; i < 3; i++) {
            assertThat(resp.<String>read("$.data.cards[" + i + "].status")).isEqualTo("succeeded");
            assertThat(resp.<String>read("$.data.cards[" + i + "].trigger")).isEqualTo("scheduled");
        }
        assertThat(resp.<Integer>read("$.data.cards[0].durationSeconds")).isEqualTo(600);
        assertThat(resp.<String>read("$.data.cards[0].startedAt")).isEqualTo("2026-10-26T18:00:00Z");
        assertThat(resp.<String>read("$.data.cards[0].finishedAt")).isEqualTo("2026-10-26T18:10:00Z");
        assertThat(resp.<String>read("$.data.cards[0].lastSuccessAt")).isEqualTo("2026-10-26T18:10:00Z");
        assertThat(resp.<String>read("$.data.cards[1].lastSuccessAt")).isEqualTo("2026-10-26T18:02:30Z");
        assertThat(resp.<Integer>read("$.data.cards[2].durationSeconds")).isEqualTo(40);
        assertThat(resp.<String>read("$.data.cards[3].status")).isEqualTo("no_run");
        assertThat(resp.<Object>read("$.data.cards[3].trigger")).isNull();
        assertThat(resp.<Object>read("$.data.cards[3].startedAt")).isNull();
        assertThat(resp.<Object>read("$.data.cards[3].durationSeconds")).isNull();
        assertThat(resp.<Boolean>read("$.data.cards[3].never")).isTrue();

        assertThat(resp.<String>read("$.data.cards[0].latestBackup.label")).as("full 取全備中 stop 最大者").isEqualTo("20261026-020002F");
        assertThat(resp.<String>read("$.data.cards[0].latestBackup.source")).isEqualTo("pgbackrest");
        assertThat(resp.<String>read("$.data.cards[1].latestBackup.label")).as("diff 取差異或全備中最近者").isEqualTo("20261026-020002F_20261027-020001D");
        assertThat(opt(resp, "$.data.cards[2].latestBackup")).as("dump 卡不得有 latestBackup 物件").isNull();
        assertThat(opt(resp, "$.data.cards[3].latestBackup")).isNull();
    }

    @Test
    void AT_BK_04_1_E_1_aPgBackRestBackupWithoutAStateFileIsNotReportedAsNeverRun() {
        seed();

        Resp resp = overview();

        assertThat(resp.<String>read("$.data.cards[0].status")).isEqualTo("no_run");
        assertThat(resp.<Object>read("$.data.cards[0].trigger")).isNull();
        assertThat(resp.<Boolean>read("$.data.cards[0].never")).as("成功時間取自清單").isFalse();
        assertThat(resp.<String>read("$.data.cards[0].lastSuccessAt")).as("各 repo 最近全備的最舊者").isEqualTo("2026-10-25T18:10:00Z");
        assertThat(resp.<String>read("$.data.cards[0].latestBackup.label")).as("最近一份＝各 repo 最近者中 stop 最大者").isEqualTo("20261026-020002F");
        assertThat(resp.<String>read("$.data.cards[0].latestBackup.finishedAt")).isEqualTo("2026-10-25T18:12:00Z");
        assertThat(resp.<String>read("$.data.cards[0].latestBackup.source")).isEqualTo("pgbackrest");
    }

    @Test
    void AT_BK_04_2_1_aFailureDoesNotOverwriteTheEarlierSuccess() {
        clock.set(Instant.parse("2026-10-28T02:00:00Z"));
        seed();
        job("dump", FakeBackupRunner.jobJson("dump", "scheduled", "failed", 1, "script_failed", "2026-10-27T18:30:00Z", "2026-10-27T18:30:40Z", "boom",
                "2026-10-26T18:30:30Z"));

        Resp resp = overview();

        assertThat(resp.<String>read("$.data.cards[2].status")).isEqualTo("failed");
        assertThat(resp.<String>read("$.data.cards[2].reason")).isEqualTo("script_failed");
        assertThat(resp.<String>read("$.data.cards[2].lastSuccessAt")).as("失敗不覆蓋較早的成功").isEqualTo("2026-10-26T18:30:30Z");
        assertThat(resp.<String>read("$.data.cards[2].finishedAt")).isEqualTo("2026-10-27T18:30:40Z");
    }

    @Test
    void AT_BK_04_3_2_overdueIsEvaluatedOnTheServerAndARunningJobIsNeverOverdue() {
        Instant monday0231 = Instant.parse("2026-11-01T18:31:00Z");
        clock.set(monday0231);
        seedInfo(infoStops(Instant.parse("2026-10-25T18:10:00Z"), Instant.parse("2026-10-25T18:12:00Z"), Instant.parse("2026-10-30T18:02:00Z"),
                Instant.parse("2026-10-30T18:03:00Z")), FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL);
        write("export/logical.json", FakeBackupRunner.logicalJson(iso(monday0231), "[]"));
        write("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei"));
        heartbeat(3, false);
        job("diff", FakeBackupRunner.jobOk("diff", "scheduled", "2026-10-30T18:00:00Z", "2026-10-30T18:00:30Z"));

        Resp late = overview();
        assertThat(late.<Boolean>read("$.data.cards[1].overdue")).as("週一 02:31，增備未成功 ⇒ 逾期").isTrue();
        assertThat(late.<String>read("$.data.cards[1].lastDueAt")).isEqualTo("2026-11-01T18:00:00Z");
        assertThat(late.<Boolean>read("$.data.cards[1].never")).isFalse();

        clock.set(Instant.parse("2026-11-01T18:15:00Z"));
        heartbeat(3, false);
        assertThat(overview().<Boolean>read("$.data.cards[1].overdue")).as("週一 02:15 在寬限內").isFalse();

        clock.set(monday0231);
        heartbeat(2, true);
        job("diff", FakeBackupRunner.jobRunning("diff", "scheduled", iso(monday0231.minusSeconds(300)), "2026-10-30T18:00:30Z"));
        Resp running = overview();
        assertThat(running.<Boolean>read("$.data.cards[1].overdue")).as("進行中不逾期").isFalse();
        assertThat(running.<String>read("$.data.cards[1].status")).isEqualTo("running");
        for (Object lastDueAt : running.<List<Object>>read("$.data.cards[*].lastDueAt")) {
            assertThat(lastDueAt == null || lastDueAt.toString().endsWith(LAST_MODIFIED_PATH)).as("lastDueAt 為 UTC Z：%s", lastDueAt).isTrue();
        }
    }

    @Test
    void AT_BK_04_3_E_1_anUncomputableOverdueIsNotReportedAsOverdue() {
        Instant monday0231 = Instant.parse("2026-11-01T18:31:00Z");
        clock.set(monday0231);
        seed();
        write("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei").replace("0 2 * * 1-6", "@weird"));
        job("diff", FakeBackupRunner.jobOk("diff", "scheduled", "2026-10-30T18:00:00Z", "2026-10-30T18:00:30Z"));

        Resp resp = overview();

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Object>read("$.data.cards[1].lastDueAt")).isNull();
        assertThat(resp.<Boolean>read("$.data.cards[1].overdue")).as("算不出＝量不到，不是逾期").isFalse();
        assertThat(resp.<List<String>>read("$.data.control.warnings")).contains("cron_unparsable:diff");
    }

    @Test
    void AT_BK_04_4_2_aRunningFileWithAFreshHeartbeatThatSaysNoLockIsHeldIsReportedInterrupted() {
        seed();
        job("full", FakeBackupRunner.jobRunning("full", "scheduled", iso(NOW.minusSeconds(60)), null));
        heartbeat(5, false);

        Resp resp = overview();

        assertThat(resp.<String>read("$.data.cards[0].status")).isEqualTo("interrupted");
        assertThat(resp.<Object>read("$.data.activeJob")).as("中斷的工作不算進行中").isNull();
    }

    @Test
    void AT_BK_04_4_E_1_theInterruptedDerivationNeedsAFreshHeartbeatNoLockAndAHeartbeatNotOlderThanTheJob() {
        // (a) running、鎖被持有、心跳新鮮 ⇒ 仍是 running
        seed();
        job("full", FakeBackupRunner.jobRunning("full", "scheduled", iso(NOW.minusSeconds(60)), null));
        heartbeat(5, true);
        Resp a = overview();
        assertThat(a.<String>read("$.data.cards[0].status")).isEqualTo("running");
        assertThat(a.<String>read("$.data.activeJob.status")).isEqualTo("RUNNING");

        // (b) running、心跳過期（鎖資訊過期，不能斷言中斷）⇒ 保持 running、reason=runner_offline
        heartbeat(100, false);
        Resp b = overview();
        assertThat(b.<String>read("$.data.cards[0].status")).isEqualTo("running");
        assertThat(b.<String>read("$.data.control.reason")).isEqualTo("runner_offline");

        // (c) succeeded 且鎖未持有 ⇒ 不變成 interrupted
        job("full", FakeBackupRunner.jobOk("full", "scheduled", iso(NOW.minusSeconds(600)), iso(NOW.minusSeconds(300))));
        heartbeat(5, false);
        assertThat(overview().<String>read("$.data.cards[0].status")).isEqualTo("succeeded");

        // (d) 心跳 ts 早於工作開始＝鎖資訊過時 ⇒ 保持 running
        job("full", FakeBackupRunner.jobRunning("full", "scheduled", iso(NOW.minusSeconds(2)), null));
        heartbeat(4, false);
        assertThat(overview().<String>read("$.data.cards[0].status")).isEqualTo("running");

        // (e) 「新鮮」與 05-2 的離線判斷同界線：心跳年齡恰 30 秒仍新鮮（過期是嚴格大於 30）⇒ 導出 interrupted；31 秒＝過期 ⇒ 不下結論、保持 running
        job("full", FakeBackupRunner.jobRunning("full", "scheduled", iso(NOW.minusSeconds(100)), null));
        heartbeat(30, false);
        assertThat(overview().<String>read("$.data.cards[0].status")).as("心跳恰 30 秒").isEqualTo("interrupted");
        heartbeat(31, false);
        assertThat(overview().<String>read("$.data.cards[0].status")).as("心跳 31 秒").isEqualTo("running");
    }

    @Test
    void AT_BK_04_5_1_nonAdminsNeverSeeTheOutputTailOrTheRequesterAnywhereInTheResponse() {
        seed();
        job("dump", FakeBackupRunner.jobJson("dump", "scheduled", "failed", 1, "script_failed", "2026-10-26T18:30:00Z", "2026-10-26T18:30:40Z",
                "CANARY-TAIL-7f3a failed", "2026-10-25T18:30:30Z"));

        Resp admin = overview(admin());
        assertThat(admin.<String>read("$.data.cards[2].detailTail")).contains("CANARY-TAIL-7f3a");
        List<Map<String, Object>> adminCards = admin.read("$.data.cards");
        adminCards.forEach(card -> {
            card.remove("detailTail");
            card.remove("requestedBy");
        });
        for (String token : List.of(viewer(), operator())) {
            Resp resp = overview(token);
            assertThat(resp.status()).isEqualTo(200);
            assertThat(resp.body()).as("整段回應不含 canary").doesNotContain("CANARY-TAIL-7f3a");
            assertNoSensitiveKeys(JSON.readValue(resp.body(), Object.class));
            List<Map<String, Object>> cards = resp.read("$.data.cards");
            assertThat(cards).as("其餘欄位與 ADMIN 逐值相同").isEqualTo(adminCards);
        }
    }

    /** 遞迴掃描：所有名為 detailTail、requestedBy、detail 的鍵，其值皆為 null（或鍵不存在）。 */
    private static void assertNoSensitiveKeys(Object node) {
        if (node instanceof Map<?, ?> map) {
            map.forEach((key, value) -> {
                if ("detailTail".equals(key) || "requestedBy".equals(key) || "detail".equals(key)) {
                    assertThat(value).as("非 ADMIN 的 %s 必須為 null", key).isNull();
                }
                assertNoSensitiveKeys(value);
            });
        } else if (node instanceof List<?> list) {
            list.forEach(BackupApiIT::assertNoSensitiveKeys);
        }
    }

    @Test
    void AT_BK_04_5_2_theAdminTailIsExactlyTheLast2000CharactersOfTheMaskedText() {
        seed();
        String tail = "PAD-HEAD".repeat(63) + "y".repeat(1980) + "CANARY-TAIL-7f3a";
        assertThat(tail).hasSize(2500);
        job("dump", FakeBackupRunner.jobJson("dump", "scheduled", "failed", 1, "script_failed", "2026-10-26T18:30:00Z", "2026-10-26T18:30:40Z", tail,
                "2026-10-25T18:30:30Z"));

        String detailTail = overview().read("$.data.cards[2].detailTail");

        assertThat(detailTail).hasSize(2000).contains("CANARY-TAIL-7f3a").doesNotContain("PAD-HEAD");
        assertThat(tail).endsWith(detailTail);
    }

    @Test
    void AT_BK_04_5_3_theActiveJobRequesterIsHiddenFromNonAdmins() {
        seed();
        heartbeat(3, true);
        jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at, started_at, detail) values (?, 'diff', 'RUNNING', "
                + "'CANARY-REQ-9c1e', ?::timestamptz, ?::timestamptz, 'CANARY-DET-4b2d')", UUID.randomUUID(), iso(NOW.minusSeconds(60)), iso(NOW.minusSeconds(50)));

        for (String token : List.of(viewer(), operator())) {
            Resp resp = overview(token);
            assertThat(resp.<String>read("$.data.activeJob.status")).isEqualTo("RUNNING");
            assertThat(opt(resp, "$.data.activeJob.requestedBy")).isNull();
            assertThat(resp.body()).doesNotContain("CANARY-REQ-9c1e").doesNotContain("CANARY-DET-4b2d");
        }
        assertThat(overview(admin()).<String>read("$.data.activeJob.requestedBy")).isEqualTo("CANARY-REQ-9c1e");
    }

    @Test
    void AT_BK_04_5_S_1_whenSeveralStateFilesSayRunningTheNewestStartIsTheLockHolder() {
        // 補 AT（主控代決第 9 點；TCS 的 AT-BK-09-6-3 只鎖 sidecar 的清掃，console-api 的 activeJob 取「持有者」同規則卻無 AT）
        seed();
        job("full", FakeBackupRunner.jobRunning("full", "scheduled", iso(NOW.minusSeconds(600)), null));
        job("diff", FakeBackupRunner.jobRunning("diff", "scheduled", iso(NOW.minusSeconds(60)), null));
        heartbeat(2, true);
        assertThat(overview().<String>read("$.data.activeJob.type")).as("diff 的 started_at 較新 ⇒ 持有者").isEqualTo("diff");

        job("full", FakeBackupRunner.jobRunning("full", "scheduled", iso(NOW.minusSeconds(30)), null));
        assertThat(overview().<String>read("$.data.activeJob.type")).as("full 變成較新 ⇒ 持有者換人（不是固定取固定順序的第一個）").isEqualTo("full");
    }

    @Test
    void AT_BK_07_3_S_1_aRowWhoseDetailWasNeverMaskedIsMaskedAgainWhenAdminsReadIt() {
        // 補 AT：寫入端（對帳）遮罩之外，讀出端再遮罩一次的縱深防禦——資料列若被別的路徑寫成未遮罩，API 仍不外洩
        seed();
        UUID id = UUID.randomUUID();
        String unmasked = "restore failed\nconn postgres://backup:s3cr3t-CANARY-5d2f@db:5432/aisdlc\nkey AKIAABCDEFGHIJKLMNOP\napi_token=CANARY-TOKEN-8e1c"; // secret-scan-ok: 遮罩測試的合成探針（AWS key 形狀的假值），驗讀出端會遮罩
        jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at, finished_at, exit_code, reason, detail) values (?, 'diff', 'FAILED', "
                + "'admin', ?::timestamptz, ?::timestamptz, 1, 'script_failed', ?)", id, iso(NOW.minusSeconds(600)), iso(NOW.minusSeconds(500)), unmasked);

        String single = api.get(admin(), JOBS + "/" + id).<String>read("$.data.detail");
        String listed = api.get(admin(), JOBS).<String>read("$.data.items[0].detail");

        for (String detail : List.of(single, listed)) {
            assertThat(detail).doesNotContain("s3cr3t-CANARY-5d2f").doesNotContain("AKIAABCDEFGHIJKLMNOP").doesNotContain("CANARY-TOKEN-8e1c") // secret-scan-ok: 同上，斷言探針已被遮罩
                    .contains("restore failed").contains("***");
        }
    }

    @Test
    void AT_BK_04_5_E_1_theJobEndpointsApplyTheSameRuleToRequesterAndDetail() {
        seed();
        UUID id = UUID.randomUUID();
        jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at, finished_at, detail) values (?, 'diff', 'SUCCEEDED', "
                + "'CANARY-REQ-9c1e', ?::timestamptz, ?::timestamptz, 'CANARY-DET-4b2d')", id, iso(NOW.minusSeconds(600)), iso(NOW.minusSeconds(500)));

        for (String token : List.of(viewer(), operator())) {
            Resp list = api.get(token, JOBS);
            Resp single = api.get(token, JOBS + "/" + id);
            assertThat(list.status()).isEqualTo(200);
            assertThat(single.status()).isEqualTo(200);
            assertNoSensitiveKeys(JSON.readValue(list.body(), Object.class));
            assertNoSensitiveKeys(JSON.readValue(single.body(), Object.class));
            assertThat(list.body() + single.body()).doesNotContain("CANARY-REQ-9c1e").doesNotContain("CANARY-DET-4b2d");
        }
        assertThat(api.get(admin(), JOBS + "/" + id).<String>read("$.data.requestedBy")).isEqualTo("CANARY-REQ-9c1e");
    }

    @Test
    void AT_BK_04_6_1_aFreshClusterReportsARealZeroForWalArchivingNotADegradedBlock() {
        seed();

        Resp resp = overview();

        assertThat(resp.<Number>read("$.data.walArchive.failedCount").longValue()).isZero();
        assertThat(resp.<Object>read("$.data.walArchive.lastArchivedAt")).isNull();
        assertThat(resp.<Object>read("$.data.walArchive.lastFailedAt")).isNull();
        assertThat(resp.<List<String>>read("$.data.control.warnings")).doesNotContain("db_unavailable");
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // FR-BK-05　控制面健康與資料新鮮度
    // ══════════════════════════════════════════════════════════════════════════════════════════

    @Test
    void AT_BK_05_2_1_theHeartbeatIsStaleOnlyWhenStrictlyOlderThan30Seconds() {
        seed();

        heartbeat(30, false);
        Resp edge = overview();
        assertThat(edge.<Object>read("$.data.control.reason")).as("30 秒整仍正常").isNull();
        assertThat(edge.<Integer>read("$.data.control.heartbeatAgeSeconds")).isEqualTo(30);

        heartbeat(31, false);
        Resp stale = overview();
        assertThat(stale.status()).isEqualTo(200);
        assertThat(stale.<String>read("$.data.control.reason")).isEqualTo("runner_offline");
        assertThat(stale.<Integer>read("$.data.control.heartbeatAgeSeconds")).isEqualTo(31);
        assertThat(stale.<Boolean>read("$.data.control.canTrigger")).isFalse();
        assertThat(stale.<Object>read("$.data.backups")).as("離線時資料照回已知資料").isNotNull();
        assertThat(stale.<Object>read("$.data.cards")).isNotNull();
        assertThat(stale.<Object>read("$.data.activeJob")).isNull();

        runnerHeartbeatAbsent();
        Resp absent = overview();
        assertThat(absent.<String>read("$.data.control.reason")).isEqualTo("runner_offline");
        assertThat(absent.<Object>read("$.data.control.heartbeatAgeSeconds")).isNull();
    }

    private void runnerHeartbeatAbsent() {
        try {
            Files.deleteIfExists(exportRoot.resolve("export").resolve("heartbeat"));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    @Test
    void AT_BK_05_2_3_anOfflineRunnerRefusesTheTriggerWithNoRowAndNoFile() {
        seed();
        heartbeat(31, false);

        Resp resp = post(admin(), request("full"));

        assertThat(resp.status()).isEqualTo(503);
        assertThat(resp.<String>read("$.reason")).isEqualTo("backup_control_unavailable");
        assertNothingWritten("心跳過期");
    }

    @Test
    void AT_BK_05_2_E_1_aBusyJobIsNotAnExcuseForOfflineAndOfflineIsNotExcusedByABusyJob() {
        seed();
        job("full", FakeBackupRunner.jobRunning("full", "scheduled", iso(NOW.minusSeconds(60)), null));
        heartbeat(3, true);
        assertThat(overview().<Object>read("$.data.control.reason")).as("進行中的工作不會讓心跳變舊").isNull();

        heartbeat(31, true);
        assertThat(overview().<String>read("$.data.control.reason")).as("進行中不豁免").isEqualTo("runner_offline");
    }

    @Test
    void AT_BK_05_3_1_everySingleFaultIsClassifiedAndTheWholeResponseDropsItsDataBlocks() throws IOException {
        Map<String, String[]> faults = new LinkedHashMap<>();
        faults.put("info schema_rev=2", new String[] {"export/info.json", "{\"schema_rev\":2,\"generated_at\":\"2026-10-27T01:59:50Z\",\"ok\":false}", "schema_mismatch"});
        faults.put("info schema_rev=\"1\"", new String[] {"export/info.json", "{\"schema_rev\":\"1\",\"generated_at\":\"2026-10-27T01:59:50Z\",\"ok\":false}", "schema_mismatch"});
        faults.put("info 缺 schema_rev", new String[] {"export/info.json", "{\"generated_at\":\"2026-10-27T01:59:50Z\",\"ok\":false}", "schema_mismatch"});
        faults.put("info 截斷", new String[] {"export/info.json", "{\"schema_rev\":1,\"generated_at\":\"2026-10-27T01:5", "export_unreadable"});
        faults.put("logical schema_rev=2", new String[] {"export/logical.json", "{\"schema_rev\":2,\"ok\":false}", "schema_mismatch"});
        faults.put("schedule 空檔", new String[] {"export/schedule.json", "", "export_unreadable"});
        faults.put("jobs/dump.json 頂層是陣列", new String[] {"export/jobs/dump.json", "[]", "schema_mismatch"});
        faults.put("heartbeat 非 JSON", new String[] {"export/heartbeat", "this is not json", "export_unreadable"});
        faults.put("heartbeat schema_rev=2", new String[] {"export/heartbeat", "{\"schema_rev\":2,\"ts\":\"2026-10-27T01:59:57Z\",\"lock_held\":false}", "schema_mismatch"});
        for (Map.Entry<String, String[]> fault : faults.entrySet()) {
            runner.clearDirectories(); // 單一故障：上一輪植入的壞檔不得殘留
            seed();
            write(fault.getValue()[0], fault.getValue()[1]);

            Resp resp = overview();

            assertThat(resp.status()).as(fault.getKey()).isEqualTo(200);
            assertThat(resp.<String>read("$.data.control.reason")).as(fault.getKey()).isEqualTo(fault.getValue()[2]);
            assertThat(resp.<Boolean>read("$.data.control.canTrigger")).as(fault.getKey()).isFalse();
            for (String block : List.of("cards", "backups", "schedule", "repos", "walArchive", "activeJob")) {
                assertThat(resp.<Object>read("$.data." + block)).as("%s：%s 必須為 null（不顯示部分資料）", fault.getKey(), block).isNull();
            }
        }
    }

    @Test
    void AT_BK_05_3_E_1_aSourceThatReportsItsOwnFailureDegradesOnlyItsOwnBlocks() {
        seed();
        write("export/info.json", FakeBackupRunner.infoFailedJson(iso(NOW.minusSeconds(10))));
        Resp infoDown = overview();
        assertThat(infoDown.<Object>read("$.data.control.reason")).as("檔案本身合法：reason 仍為 null").isNull();
        assertThat(infoDown.<List<String>>read("$.data.control.warnings")).contains("info_unavailable");
        assertThat(infoDown.<Object>read("$.data.repos")).isNull();
        assertThat(infoDown.<List<String>>read("$.data.backups[*].kind")).as("backups 只含邏輯備份項").containsOnly("logical").hasSize(2);
        assertThat(infoDown.<Object>read("$.data.cards[0].latestBackup")).isNull();
        assertThat(infoDown.<Object>read("$.data.schedule.retention")).isNull();

        seed();
        write("export/logical.json", FakeBackupRunner.logicalFailedJson(iso(NOW.minusSeconds(10))));
        Resp logicalDown = overview();
        assertThat(logicalDown.<Object>read("$.data.control.reason")).isNull();
        assertThat(logicalDown.<List<String>>read("$.data.control.warnings")).contains("logical_unavailable");
        assertThat(logicalDown.<List<String>>read("$.data.backups[*].kind")).as("backups 只含 pgBackRest 項").doesNotContain("logical").hasSize(4);
        for (String warning : logicalDown.<List<String>>read("$.data.control.warnings")) {
            assertThat(warning).as("warnings 值域封閉").matches("db_unavailable|retention_unavailable|info_unavailable|logical_unavailable|cron_unparsable:[a-z_]+");
        }
    }

    @Test
    void AT_BK_05_3_E_2_whenFaultsCoexistTheSchemaMismatchWinsAndDataCorruptionBeatsAnOfflineRunner() {
        // (a) info schema_rev=2 且 logical 截斷
        seed();
        write("export/info.json", "{\"schema_rev\":2}");
        write("export/logical.json", "{\"schema_rev\":1,\"generated_at\":\"2026");
        assertThat(overview().<String>read("$.data.control.reason")).as("(a)").isEqualTo("schema_mismatch");
        // (a2) 反序
        seed();
        write("export/info.json", "{\"schema_rev\":1,\"generated_at\":\"2026");
        write("export/logical.json", "{\"schema_rev\":2}");
        assertThat(overview().<String>read("$.data.control.reason")).as("(a2) 與讀檔先後無關").isEqualTo("schema_mismatch");
        // (b) info 截斷且心跳 100 秒
        seed();
        write("export/info.json", "{\"schema_rev\":1,\"generated_at\":\"2026");
        heartbeat(100, false);
        Resp b = overview();
        assertThat(b.<String>read("$.data.control.reason")).as("(b) 資料損毀先於心跳").isEqualTo("export_unreadable");
        // (c) schedule schema_rev=2 且心跳檔缺席
        seed();
        write("export/schedule.json", "{\"schema_rev\":2}");
        runnerHeartbeatAbsent();
        Resp c = overview();
        assertThat(c.<String>read("$.data.control.reason")).as("(c)").isEqualTo("schema_mismatch");
        for (Resp resp : List.of(b, c)) {
            assertThat(resp.status()).isEqualTo(200);
            assertThat(resp.<Boolean>read("$.data.control.canTrigger")).isFalse();
            assertThat(resp.<Object>read("$.data.cards")).isNull();
        }
    }

    @Test
    void AT_BK_05_4_1_theExportAgeIsReportedAndAnOldExportDoesNotChangeTheReason() {
        seed();
        for (int age : new int[] {180, 181}) {
            write("export/info.json", FakeBackupRunner.infoJson(iso(NOW.minusSeconds(age)), FakeBackupRunner.fixture("info-2repo.json"),
                    FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL));
            Resp resp = overview();
            assertThat(resp.<Integer>read("$.data.control.exportAgeSeconds")).isEqualTo(age);
            assertThat(resp.<String>read("$.data.control.exportGeneratedAt")).isEqualTo(iso(NOW.minusSeconds(age)));
            assertThat(resp.<Object>read("$.data.control.reason")).as("匯出舊不改變 reason").isNull();
        }
    }

    @Test
    void AT_BK_05_5_1_aMissingJobTableDegradesOnlyTheActiveJobAndTheTriggerButNotTheOverview() {
        seed();
        job("full", FakeBackupRunner.jobRunning("full", "scheduled", iso(NOW.minusSeconds(60)), null));
        heartbeat(3, true);
        jdbc.execute("alter table console.backup_jobs rename to backup_jobs_off");
        try {
            Resp resp = overview();

            assertThat(resp.status()).isEqualTo(200);
            assertThat(resp.<List<String>>read("$.data.control.warnings")).contains("db_unavailable");
            for (String block : List.of("cards", "backups", "schedule", "repos")) {
                assertThat(resp.<Object>read("$.data." + block)).as(block + " 為檔案面資料").isNotNull();
            }
            assertThat(resp.<String>read("$.data.activeJob.type")).isEqualTo("full");
            assertThat(resp.<String>read("$.data.activeJob.status")).isEqualTo("RUNNING");
            assertThat(resp.<String>read("$.data.activeJob.trigger")).isEqualTo("scheduled");
            assertThat(resp.<Object>read("$.data.activeJob.id")).isNull();
            assertThat(resp.<Boolean>read("$.data.control.canTrigger")).isFalse();

            Resp trigger = post(admin(), request("verify"));
            assertThat(trigger.status()).isEqualTo(503);
            assertThat(trigger.<String>read("$.reason")).isEqualTo("backup_control_unavailable");
            assertThat(requestFiles()).as("DB 失敗時不寫請求檔").isEmpty();
        } finally {
            jdbc.execute("alter table console.backup_jobs_off rename to backup_jobs");
        }
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // FR-BK-06　手動觸發
    // ══════════════════════════════════════════════════════════════════════════════════════════

    @Test
    void AT_BK_06_2_1_invalidBodiesAreRejectedInTheFixedOrderWithoutAnySideEffect() {
        seed();
        String confirmRequired = "backup_confirm_required";
        Map<String, String[]> cases = new LinkedHashMap<>();
        cases.put("{\"type\":\"full\"}", new String[] {"400", confirmRequired});
        cases.put("{\"type\":\"full\",\"confirm\":false}", new String[] {"400", confirmRequired});
        cases.put("{\"type\":\"full\",\"confirm\":\"true\"}", new String[] {"400", confirmRequired});
        cases.put("{\"type\":\"full\",\"confirm\":1}", new String[] {"400", confirmRequired});
        cases.put("{\"type\":\"dump\",\"confirm\":true}", new String[] {"422", "invalid_request"});
        cases.put("{\"type\":\"incr\",\"confirm\":true}", new String[] {"422", "invalid_request"});
        cases.put("{\"type\":\"FULL\",\"confirm\":true}", new String[] {"422", "invalid_request"});
        cases.put("{\"confirm\":true}", new String[] {"422", "invalid_request"});
        cases.put("{\"type\":null,\"confirm\":true}", new String[] {"422", "invalid_request"});
        cases.put("{\"type\":7,\"confirm\":true}", new String[] {"422", "invalid_request"});
        cases.put("{}", new String[] {"422", "invalid_request"});
        cases.put("[]", new String[] {"400", "MALFORMED_REQUEST_BODY"});
        cases.put("\"x\"", new String[] {"400", "MALFORMED_REQUEST_BODY"});
        cases.put("{\"type\":\"full\",", new String[] {"400", "MALFORMED_REQUEST_BODY"});
        for (Map.Entry<String, String[]> entry : cases.entrySet()) {
            Resp resp = api.raw(admin(), HttpMethod.POST, JOBS, entry.getKey());

            assertThat(resp.status()).as(entry.getKey()).isEqualTo(Integer.parseInt(entry.getValue()[0]));
            assertThat(resp.<String>read("$.reason")).as(entry.getKey()).isEqualTo(entry.getValue()[1]);
            assertThat(resp.has("$.data")).as(entry.getKey() + "：回應無 data").isFalse();
            if ("invalid_request".equals(entry.getValue()[1])) {
                assertThat(resp.<List<String>>read("$.details.violations[*].field")).as(entry.getKey()).contains("type");
            }
            assertNothingWritten(entry.getKey());
        }
    }

    @Test
    void AT_BK_06_2_E_1_extraKeysAreIgnoredAndTheRequestFileIsBuiltOnlyFromServerValues() throws IOException {
        seed();
        Map<String, Object> body = request("verify");
        body.put("cmd", "touch /tmp/x");
        body.put("id", "not-honored");

        Resp resp = post(admin(), body);

        assertThat(resp.status()).isEqualTo(202);
        Map<String, Object> data = resp.data();
        assertThat(data.keySet()).containsExactly("id", "type", "status", "requestedAt");
        String id = (String) data.get("id");
        assertThat(id).isNotEqualTo("not-honored");
        UUID.fromString(id);
        assertThat(requestFiles()).containsExactly(id + ".json");
        Map<String, Object> file = JSON.readValue(Files.readString(requestRoot.resolve(id + ".json"), StandardCharsets.UTF_8), Map.class);
        assertThat(file.keySet()).containsExactly("schema_rev", "id", "type", "requested_at", "expires_at");
        assertThat(file).containsEntry("id", id).containsEntry("type", "verify");
        assertThat(file.toString()).doesNotContain("cmd").doesNotContain("touch");
    }

    @Test
    void AT_BK_06_3_2_aValidTriggerReturns202QueuedAndLeavesOneRowAndOneRequestFile() throws IOException {
        seed();
        runner.behavior(Behavior.SUCCEED);

        Resp resp = post(admin(), request("diff"));

        assertThat(resp.status()).isEqualTo(202);
        assertThat(resp.<Integer>read("$.code")).isEqualTo(202);
        Map<String, Object> data = resp.data();
        String id = (String) data.get("id");
        assertThat(data).containsEntry("type", "diff").containsEntry("status", "QUEUED").containsEntry("requestedAt", iso(NOW));
        Map<String, Object> row = jdbc.queryForMap("select status, requested_by, to_char(requested_at at time zone 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') "
                + "as at from console.backup_jobs where id = ?::uuid", id);
        assertThat(row).containsEntry("status", "QUEUED").containsEntry("requested_by", "admin").containsEntry("at", iso(NOW));
        assertThat(requestFiles()).containsExactly(id + ".json");
        Map<String, Object> file = JSON.readValue(Files.readString(requestRoot.resolve(id + ".json"), StandardCharsets.UTF_8), Map.class);
        assertThat(file).containsEntry("schema_rev", 1).containsEntry("type", "diff").containsEntry("requested_at", iso(NOW))
                .containsEntry("expires_at", iso(NOW.plusSeconds(120)));
    }

    @Test
    void AT_BK_06_3_3_reconcilingFollowsQueuedToRunningToSucceededAndRemovesTheRequestFile() {
        seed();
        runner.behavior(Behavior.HOLD).start();
        String id = (String) post(admin(), request("diff")).data().get("id");
        waitFor(() -> resultExists(id), "假 runner 寫出 running 標記");

        assertThat(reconciler.reconcileOnce()).isEqualTo(1);
        Resp running = api.get(admin(), JOBS + "/" + id);
        assertThat(running.<String>read("$.data.status")).isEqualTo("RUNNING");
        assertThat(running.<Object>read("$.data.startedAt")).isNotNull();

        runner.release();
        assertThat(reconciler.reconcileOnce()).isEqualTo(1);
        Resp done = api.get(admin(), JOBS + "/" + id);
        assertThat(done.<String>read("$.data.status")).isEqualTo("SUCCEEDED");
        assertThat(done.<Integer>read("$.data.exitCode")).isZero();
        assertThat(done.<Object>read("$.data.finishedAt")).isNotNull();
        assertThat(done.<Object>read("$.data.reason")).isNull();
        runner.stop();
        assertThat(overview().<Object>read("$.data.activeJob")).as("完成後不再有進行中的工作").isNull();
        assertThat(requestFiles()).as("終態後 console-api 刪自己的請求檔").isEmpty();
    }

    @Test
    void AT_BK_06_3_E_1_theSuccessStatusIsExactly202AndAlwaysQueued() {
        seed();

        Resp resp = post(admin(), request("verify"));

        assertThat(resp.status()).as("不是 200、不是 201").isEqualTo(202);
        assertThat(resp.<String>read("$.data.status")).isEqualTo("QUEUED");
    }

    @Test
    void AT_BK_06_4_1_anExistingQueuedOrRunningRowAnswers409AndNothingChanges() {
        seed();
        for (String status : List.of("RUNNING", "QUEUED")) {
            jdbc.execute("TRUNCATE console.backup_jobs");
            jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at) values (?, 'full', ?, 'someone', ?::timestamptz)",
                    UUID.randomUUID(), status, iso(NOW.minusSeconds(30)));

            Resp resp = post(admin(), request("verify"));

            assertThat(resp.status()).as(status).isEqualTo(409);
            assertThat(resp.<String>read("$.reason")).isEqualTo("backup_job_in_progress");
            assertThat(jobRows()).as(status + "：列數不變").isEqualTo(1);
            assertThat(requestFiles()).as(status + "：請求目錄仍為空").isEmpty();
        }
    }

    @Test
    void AT_BK_06_4_2_twoConcurrentTriggersYieldExactlyOneAcceptedAndOneConflictForTwentyRounds() throws Exception {
        seed();
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            for (int round = 0; round < 20; round++) {
                jdbc.execute("TRUNCATE console.backup_jobs");
                clearRequestFiles();
                CyclicBarrier barrier = new CyclicBarrier(2);
                List<Future<Resp>> futures = new ArrayList<>();
                for (int i = 0; i < 2; i++) {
                    futures.add(pool.submit(() -> {
                        barrier.await();
                        return post(admin(), request("verify"));
                    }));
                }
                List<Integer> statuses = new ArrayList<>();
                String accepted = null;
                for (Future<Resp> future : futures) {
                    Resp resp = future.get();
                    statuses.add(resp.status());
                    if (resp.status() == 202) {
                        accepted = (String) resp.data().get("id");
                    }
                }
                assertThat(statuses).as("第 %d 輪：恰為 {202, 409}（沒有 500、沒有兩個 202）", round).containsExactlyInAnyOrder(202, 409);
                assertThat(jobRows()).as("第 %d 輪：恰 1 列", round).isEqualTo(1);
                assertThat(jdbc.queryForObject("select status from console.backup_jobs", String.class)).isEqualTo("QUEUED");
                assertThat(requestFiles()).as("第 %d 輪：請求目錄恰 1 檔且 id 等於 202 的 id", round).containsExactly(accepted + ".json");
            }
        } finally {
            pool.shutdownNow();
        }
    }

    @Test
    void AT_BK_06_5_2_aBusyRefusalEndsAsRejectedBusyAndFreesTheUniqueIndex() {
        seed();
        runner.behavior(Behavior.BUSY).start();
        String id = (String) post(admin(), request("diff")).data().get("id");
        waitFor(() -> resultExists(id), "假 runner 寫出 rejected／busy");
        runner.stop();

        reconciler.reconcileOnce();
        reconciler.reconcileOnce();

        Map<String, Object> row = jdbc.queryForMap("select status, reason, exit_code, finished_at from console.backup_jobs where id = ?::uuid", id);
        assertThat(row).containsEntry("status", "REJECTED").containsEntry("reason", "busy").containsEntry("exit_code", null);
        assertThat(row.get("finished_at")).isNotNull();
        assertThat(post(admin(), request("diff")).status()).as("唯一索引釋放：立即再 POST 回 202").isEqualTo(202);
    }

    @Test
    void AT_BK_06_6_4_theConditionalUpdatesLetExactlyOneOfAPickupAndAnExpiryWin() throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            for (int round = 0; round < 20; round++) {
                boolean pickupFirst = round % 2 == 0;
                jdbc.execute("TRUNCATE console.backup_jobs");
                UUID id = UUID.randomUUID();
                jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at) values (?, 'diff', 'QUEUED', 'admin', ?::timestamptz)",
                        id, iso(NOW));
                // 兩個方向各 10 輪：先讓一方完成再讓另一方嘗試（確定性交錯），其餘輪次以柵欄同時放行
                boolean pickup;
                boolean expiry;
                if (round < 10) {
                    if (pickupFirst) {
                        pickup = repository.markRunningIfQueued(id, NOW.plusSeconds(1));
                        expiry = repository.markExpiredIfQueued(id, NOW.plusSeconds(2));
                    } else {
                        expiry = repository.markExpiredIfQueued(id, NOW.plusSeconds(2));
                        pickup = repository.markRunningIfQueued(id, NOW.plusSeconds(1));
                    }
                } else {
                    CyclicBarrier barrier = new CyclicBarrier(2);
                    Future<Boolean> a = pool.submit(() -> {
                        barrier.await();
                        return repository.markRunningIfQueued(id, NOW.plusSeconds(1));
                    });
                    Future<Boolean> b = pool.submit(() -> {
                        barrier.await();
                        return repository.markExpiredIfQueued(id, NOW.plusSeconds(2));
                    });
                    pickup = a.get();
                    expiry = b.get();
                }
                assertThat(pickup ^ expiry).as("第 %d 輪：恰有一方生效（撿取 %s、過期 %s）", round, pickup, expiry).isTrue();
                String status = jdbc.queryForObject("select status from console.backup_jobs where id = ?", String.class, id);
                assertThat(status).as("第 %d 輪的終態只可能是贏家的狀態，沒有非法終態", round).isEqualTo(pickup ? "RUNNING" : "EXPIRED");
            }
        } finally {
            pool.shutdownNow();
        }
    }

    @Test
    void AT_BK_06_7_1_onlyAdminMayTriggerAndEveryRefusalLeavesNothingBehind() {
        seed();
        for (String token : List.of(operator(), viewer())) {
            Resp resp = post(token, request("full"));
            assertThat(resp.status()).isEqualTo(403);
            assertThat(resp.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
            assertNothingWritten("403");
        }
        assertThat(post(null, request("full")).status()).as("無 token").isEqualTo(401);
        assertThat(post("garbage.token.value", request("full")).status()).as("亂碼 token").isEqualTo(401);
        assertNothingWritten("401");
    }

    @Test
    void AT_BK_06_8_1_everyResultsShapeMapsToItsTerminalStateWithTheClosedReasonVocabulary() throws IOException {
        seed();
        String tail = "stub ok pass=fake-pass-example-1";
        Object[][] cases = {
                {"succeeded", null, 0, "SUCCEEDED", null, 0},
                {"failed", null, 1, "FAILED", "script_failed", 1},
                {"failed", "lock_timeout", 75, "FAILED", "lock_timeout", 75},
                {"failed", "interrupted", null, "FAILED", "interrupted", null},
                {"failed", "weird", 2, "FAILED", "script_failed", 2},
                {"rejected", "busy", null, "REJECTED", "busy", null},
                {"rejected", "rejected_invalid", null, "REJECTED", "rejected_invalid", null},
                {"rejected", "expired", null, "EXPIRED", "expired", null}};
        Set<String> seenReasons = new TreeSet<>();
        for (Object[] c : cases) {
            jdbc.execute("TRUNCATE console.backup_jobs");
            runner.clearDirectories();
            seed();
            String id = (String) post(admin(), request("verify")).data().get("id");
            runner.writeResult(UUID.fromString(id), "verify", (String) c[0], (String) c[1], (Integer) c[2], tail);

            reconciler.reconcileOnce();

            Map<String, Object> row = jdbc.queryForMap("select status, reason, exit_code, finished_at, detail from console.backup_jobs where id = ?::uuid", id);
            String label = c[0] + "／" + c[1];
            assertThat(row).as(label).containsEntry("status", c[3]).containsEntry("reason", c[4]).containsEntry("exit_code", c[5]);
            assertThat(row.get("finished_at")).as(label + " finished_at").isNotNull();
            assertThat((String) row.get("detail")).as(label + " 的尾段是遮罩後的文字").isEqualTo("stub ok pass=***");
            if (row.get("reason") != null) {
                seenReasons.add((String) row.get("reason"));
            }
        }
        assertThat(BackupReasonsContractTest.jobMessages().keySet()).as("reason 值域恰為契約表的八個工作理由（含 timeout、control_write_failed 由 console-api 自己寫）")
                .containsAll(seenReasons);
    }

    @Test
    void AT_BK_06_8_2_concurrentReconcilesWriteTheFinishAuditExactlyOnceAndOnlyAfterTheRowIsCommitted() throws Exception {
        seed();
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            for (int round = 0; round < 20; round++) {
                jdbc.execute("TRUNCATE console.backup_jobs");
                runner.clearDirectories();
                seed();
                UUID id = UUID.randomUUID();
                jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at, started_at) values (?, 'diff', 'RUNNING', 'admin', "
                        + "?::timestamptz, ?::timestamptz)", id, iso(NOW.minusSeconds(30)), iso(NOW.minusSeconds(20)));
                runner.writeResult(id, "diff", "succeeded", null, 0, "stub done");
                CyclicBarrier barrier = new CyclicBarrier(2);
                List<Future<Integer>> futures = new ArrayList<>();
                for (int i = 0; i < 2; i++) {
                    futures.add(pool.submit(() -> {
                        barrier.await();
                        return reconciler.reconcileOnce();
                    }));
                }
                int total = 0;
                for (Future<Integer> future : futures) {
                    total += future.get();
                }
                assertThat(total).as("第 %d 輪：恰一次更新到列", round).isEqualTo(1);
                Long audits = jdbc.queryForObject("select count(*) from console.audit_log where path = 'system:backup.finished' and entity_type = 'backup' "
                        + "and entity_id = ? and subject = 'system' and method = 'SYSTEM' and http_status = 200", Long.class, id.toString());
                assertThat(audits).as("第 %d 輪：審計列恰 1 筆（不是 2）", round).isEqualTo(1L);
                assertThat(jdbc.queryForObject("select status from console.backup_jobs where id = ?", String.class, id)).isEqualTo("SUCCEEDED");
            }
            assertThat(observed.statusesSeenAtFinish()).as("審計在交易提交之後才寫：被呼叫當下讀到的列狀態").hasSize(20).containsOnly("SUCCEEDED");
        } finally {
            pool.shutdownNow();
        }
    }

    @Test
    void AT_BK_06_9_1_aFailedRequestFileWriteCompensatesTheRowAndTheNextTriggerWorks() throws IOException {
        seed();
        Files.delete(requestRoot);
        Files.writeString(requestRoot, "我是同名的一般檔案", StandardCharsets.UTF_8);
        String failedId;
        try {
            Resp first = post(admin(), request("verify"));

            assertThat(first.status()).isEqualTo(503);
            assertThat(first.<String>read("$.reason")).isEqualTo("backup_control_unavailable");
            Map<String, Object> row = jdbc.queryForMap("select id::text as id, status, reason, finished_at from console.backup_jobs");
            assertThat(row).containsEntry("status", "FAILED").containsEntry("reason", "control_write_failed");
            assertThat(row.get("finished_at")).isNotNull();
            failedId = (String) row.get("id");
        } finally {
            Files.delete(requestRoot);
            Files.createDirectories(requestRoot);
        }
        assertThat(requestFiles()).as("沒有殘留 .tmp").isEmpty();

        Resp second = post(admin(), request("verify"));

        assertThat(second.status()).as("目錄已還原、唯一索引已釋放：立即可重試").isEqualTo(202);
        assertThat(jdbc.queryForObject("select status from console.backup_jobs where id = ?::uuid", String.class, failedId)).as("第一次的列仍為 FAILED，不被重送")
                .isEqualTo("FAILED");
    }

    @Test
    void AT_BK_06_10_2_theServerEnforcesTheFrequencyLimitForFullButNotForDiffOrVerify() {
        Instant recent = NOW.minus(Duration.ofMinutes(30));
        Instant yesterday = NOW.minus(Duration.ofHours(25));
        seedInfo(infoStops(recent, recent, yesterday, yesterday), FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL);
        write("export/logical.json", FakeBackupRunner.logicalJson(iso(NOW), "[]"));
        write("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei"));
        heartbeat(3, false);

        Resp full = post(admin(), request("full"));
        assertThat(full.status()).isEqualTo(409);
        assertThat(full.<String>read("$.reason")).isEqualTo("backup_too_frequent");
        assertThat(full.<String>read("$.details.type")).isEqualTo("full");
        assertThat(full.<String>read("$.details.nextAllowedAt")).isEqualTo(iso(recent.plusSeconds(86400)));
        assertNothingWritten("409");

        assertThat(post(admin(), request("diff")).status()).as("增備：最近差異在 25 小時前，不受全備影響").isEqualTo(202);
        jdbc.execute("TRUNCATE console.backup_jobs");
        assertThat(post(admin(), request("verify")).status()).as("驗證不設頻率上限").isEqualTo(202);
    }

    @Test
    void AT_BK_06_10_E_1_whenTheFrequencyCannotBeEvaluatedTheAnswerIs503NotAnAcceptOrA409() {
        seed();
        write("export/info.json", "{\"schema_rev\":1,\"generated_at\":\"2026-10-27");
        Resp unreadable = post(admin(), request("full"));
        assertThat(unreadable.status()).isEqualTo(503);
        assertThat(unreadable.<String>read("$.reason")).isEqualTo("backup_control_unavailable");
        assertNothingWritten("info 不可讀");

        seed();
        heartbeat(31, false);
        Resp stale = post(admin(), request("full"));
        assertThat(stale.status()).isEqualTo(503);
        assertThat(stale.<String>read("$.reason")).isEqualTo("backup_control_unavailable");
        assertNothingWritten("心跳過期");
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // FR-BK-07　工作紀錄與遮罩
    // ══════════════════════════════════════════════════════════════════════════════════════════

    private void insertFinishedJobs(int count) {
        for (int i = 0; i < count; i++) {
            jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at, started_at, finished_at, exit_code, detail) "
                    + "values (?, 'diff', 'SUCCEEDED', 'admin', ?::timestamptz, ?::timestamptz, ?::timestamptz, 0, 'ok')", UUID.randomUUID(),
                    iso(NOW.minus(Duration.ofDays(2)).plus(Duration.ofMinutes(i))), iso(NOW.minus(Duration.ofDays(2)).plus(Duration.ofMinutes(i)).plusSeconds(5)),
                    iso(NOW.minus(Duration.ofDays(2)).plus(Duration.ofMinutes(i)).plusSeconds(65)));
        }
    }

    @Test
    void AT_BK_07_1_1_theJobLogPagesNewestFirstWithAStrictCursor() {
        seed();
        insertFinishedJobs(25);

        Resp first = api.get(admin(), JOBS);
        List<Map<String, Object>> items = first.read("$.data.items");
        assertThat(items).hasSize(20);
        List<String> requestedAts = new ArrayList<>();
        for (Map<String, Object> item : items) {
            assertThat(item.keySet()).containsExactly("id", "type", "status", "requestedAt", "startedAt", "finishedAt", "durationSeconds", "exitCode", "reason",
                    "requestedBy", "detail");
            requestedAts.add((String) item.get("requestedAt"));
        }
        assertThat(requestedAts).as("requestedAt 嚴格新到舊").isSortedAccordingTo(Comparator.reverseOrder()).doesNotHaveDuplicates();
        assertThat(items.get(0)).containsEntry("durationSeconds", 60).containsEntry("exitCode", 0).containsEntry("status", "SUCCEEDED");
        assertThat(first.<String>read("$.data.nextBefore")).isEqualTo(requestedAts.get(19));

        assertThat(api.get(admin(), JOBS + "?limit=5").<List<Object>>read("$.data.items")).hasSize(5);

        Resp rest = api.get(admin(), JOBS + "?before=" + requestedAts.get(19));
        List<String> restAts = rest.read("$.data.items[*].requestedAt");
        assertThat(restAts).as("剩餘 5 筆（嚴格早於游標，游標邊界列不重複）").hasSize(5).doesNotContain(requestedAts.get(19));
        assertThat(rest.<Object>read("$.data.nextBefore")).isNull();
    }

    @Test
    void AT_BK_07_1_2_illegalPagingParametersAre422AndNeverTouchTheTable() {
        seed();
        insertFinishedJobs(3);
        for (String query : List.of("?limit=0", "?limit=101", "?limit=abc", "?before=garbage", "?before=", "?limit=-1")) {
            Resp resp = api.get(admin(), JOBS + query);

            assertThat(resp.status()).as(query).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).as(query).isEqualTo("invalid_request");
            assertThat(resp.<List<String>>read("$.details.violations[*].field")).as(query).isNotEmpty();
            assertThat(resp.has("$.data")).isFalse();
        }
        assertThat(api.get(admin(), JOBS + "?limit=1").status()).isEqualTo(200);
        assertThat(api.get(admin(), JOBS + "?limit=100").status()).isEqualTo(200);
        assertThat(jobRows()).as("資料表不被改動").isEqualTo(3);
    }

    @Test
    void AT_BK_07_1_E_1_aScheduledJobNeverCreatesARowAndReadingWritesNothing() {
        seed();
        job("dump", FakeBackupRunner.jobOk("dump", "scheduled", "2026-10-26T18:30:00Z", "2026-10-26T18:30:40Z"));
        long before = jobRows();
        Long auditBefore = jdbc.queryForObject("select count(*) from console.audit_log", Long.class);

        Resp resp = api.get(admin(), JOBS);

        assertThat(resp.<List<Object>>read("$.data.items")).as("排程工作不在此表").isEmpty();
        assertThat(jobRows()).isEqualTo(before).isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log", Long.class)).as("GET 本身零寫入").isEqualTo(auditBefore);
    }

    @Test
    void AT_BK_07_2_1_theDetailIsTheMaskedLast2000CharactersAndOnlyAdminsGetItAlongWithTheRequester() {
        seed();
        String id = (String) post(admin(), request("verify")).data().get("id");
        String tail = "A".repeat(1500) + "\n" + "B".repeat(1500) + "\nEND-MARK";
        runner.writeResult(UUID.fromString(id), "verify", "succeeded", null, 0, tail);
        reconciler.reconcileOnce();
        String expected = tail.substring(tail.length() - 2000);

        Resp adminList = api.get(admin(), JOBS);
        Resp adminOne = api.get(admin(), JOBS + "/" + id);
        for (Resp resp : List.of(adminList, adminOne)) {
            String path = resp == adminList ? "$.data.items[0]." : "$.data.";
            assertThat(resp.<String>read(path + "detail")).hasSize(2000).isEqualTo(expected).endsWith("END-MARK");
            assertThat(resp.<String>read(path + "requestedBy")).isEqualTo("admin");
        }
        assertThat(jdbc.queryForObject("select length(detail) from console.backup_jobs where id = ?::uuid", Integer.class, id)).isLessThanOrEqualTo(2000);
        for (String token : List.of(operator(), viewer())) {
            Resp list = api.get(token, JOBS);
            Resp one = api.get(token, JOBS + "/" + id);
            assertNoSensitiveKeys(JSON.readValue(list.body(), Object.class));
            assertNoSensitiveKeys(JSON.readValue(one.body(), Object.class));
            assertThat(one.<String>read("$.data.status")).as("其餘欄位與 ADMIN 相同").isEqualTo(adminOne.<String>read("$.data.status"));
            assertThat(one.<String>read("$.data.finishedAt")).isEqualTo(adminOne.<String>read("$.data.finishedAt"));
        }
    }

    @Test
    void AT_BK_07_2_E_1_anUnknownOrMalformedJobIdIs404NotA500OrA422() {
        seed();
        for (String id : List.of(UUID.randomUUID().toString(), "abc", "1234", "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz", "1-1-1-1-1", UUID.randomUUID() + "x")) {
            Resp resp = api.get(admin(), JOBS + "/" + id);

            assertThat(resp.status()).as(id).isEqualTo(404);
            assertThat(resp.<String>read("$.reason")).as(id).isEqualTo("backup_job_not_found");
            assertThat(resp.<String>read("$.message")).isEqualTo(BackupReasonsContractTest.apiMessagesUnchecked().get("backup_job_not_found"));
            assertThat(resp.has("$.data")).isFalse();
        }
        // 路徑穿越字樣（TCS 例 `../x`）：字面的 `..` 段在進路由前就被 Servlet 容器正規化，編碼後的斜線被防火牆拒絕——
        // 兩者都到不了 {id} 路徑變數，所以這裡驗的是「不會是 500、不會洩漏 data」，而不是 backup_job_not_found（見交卷 (d)）
        for (String id : List.of("..%2Fx", "%2e%2e%2fx", "..%5Cx")) {
            Resp resp = api.get(admin(), JOBS + "/" + id);

            assertThat(resp.status()).as(id).isBetween(400, 499);
            assertThat(String.valueOf(resp.body())).as(id).doesNotContain("\"data\"");
        }
    }

    @Test
    void AT_BK_07_3_3_aSidecarThatForgotToMaskStillCannotLeakThroughTheApiTheDatabaseTheAuditOrTheLogs() throws IOException {
        seed();
        List<String> inputs = new ArrayList<>();
        List<String> secrets = new ArrayList<>();
        List<String> expectedOutputs = new ArrayList<>();
        for (String line : Files.readAllLines(Path.of("..", "docker", "pgbackrest", "tests", "fixtures", "mask-probes.txt"), StandardCharsets.UTF_8)) {
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }
            String[] columns = line.split("\t", -1);
            if (!columns[1].isEmpty()) {
                inputs.add(columns[0]);
                secrets.add(columns[1]);
                expectedOutputs.add(columns[2]);
            }
        }
        assertThat(inputs).as("防反空轉：正向探針").hasSizeGreaterThanOrEqualTo(10);
        String unmasked = String.join("\n", inputs);
        job("dump", FakeBackupRunner.jobJson("dump", "scheduled", "failed", 1, "script_failed", "2026-10-26T18:30:00Z", "2026-10-26T18:30:40Z", unmasked, null));
        String id = (String) post(admin(), request("verify")).data().get("id");
        runner.writeResult(UUID.fromString(id), "verify", "failed", "script_failed", 1, unmasked);
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        ch.qos.logback.classic.Logger root = (ch.qos.logback.classic.Logger) LoggerFactory.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME);
        root.addAppender(appender);
        try {
            reconciler.reconcileOnce();
            String detail = api.get(admin(), JOBS + "/" + id).read("$.data.detail");
            String cardTail = overview().read("$.data.cards[2].detailTail");
            String stored = jdbc.queryForObject("select detail from console.backup_jobs where id = ?::uuid", String.class, id);
            String audit = jdbc.queryForList("select * from console.audit_log").toString();
            StringBuilder logs = new StringBuilder();
            appender.list.forEach(event -> logs.append(event.getFormattedMessage()).append('\n'));
            for (String corpus : List.of(detail, cardTail, stored, audit, logs.toString())) {
                for (String secret : secrets) {
                    assertThat(corpus).as("機密片段 %s", secret).doesNotContain(secret);
                }
            }
            for (String corpus : List.of(detail, cardTail, stored)) {
                for (String expected : expectedOutputs) {
                    assertThat(corpus).as("期望輸出 %s", expected).contains(expected);
                }
            }
        } finally {
            root.detachAppender(appender);
        }
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // FR-BK-09／FR-BK-10　心跳不中斷、審計、權限、機密、OpenAPI
    // ══════════════════════════════════════════════════════════════════════════════════════════

    @Test
    void AT_BK_09_8_3_aLongRunningJobDoesNotMakeTheRunnerLookOfflineButAStoppedHeartbeatStillDoes() throws InterruptedException {
        seed();
        runner.behavior(Behavior.HOLD).start();
        waitFor(() -> Files.exists(exportRoot.resolve("export").resolve("heartbeat")), "假 runner 的第一筆心跳");
        String id = (String) post(admin(), request("diff")).data().get("id");
        waitFor(() -> resultExists(id), "假 runner 寫出 running 標記");

        for (int i = 0; i < 20; i++) {
            clock.advance(Duration.ofSeconds(1));
            Thread.sleep(40);
            Resp resp = overview();
            assertThat(resp.<Object>read("$.data.control.reason")).as("第 %d 次：心跳隨專屬時鐘更新，工作進行中不是離線", i).isNull();
            assertThat(resp.<String>read("$.data.activeJob.status")).isEqualTo("RUNNING");
        }
        runner.pauseHeartbeat();
        Thread.sleep(150);
        clock.advance(Duration.ofSeconds(31));
        Resp offline = overview();
        assertThat(offline.<String>read("$.data.control.reason")).as("進行中不是離線的豁免").isEqualTo("runner_offline");
        assertThat(offline.<String>read("$.data.activeJob.status")).isEqualTo("RUNNING");
    }

    @Test
    void AT_BK_10_2_1_aTriggerAndItsFinishEachLeaveExactlyTheAuditRowsTheSpecDescribes() {
        seed();
        runner.behavior(Behavior.SUCCEED).start();
        String id = (String) post(admin(), request("diff")).data().get("id");
        waitFor(() -> resultExists(id), "假 runner 寫出終態");
        runner.stop();
        reconciler.reconcileOnce();
        reconciler.reconcileOnce();
        reconciler.reconcileOnce();

        List<Map<String, Object>> triggerRows = jdbc.queryForList("select subject, role, method, path, entity_type, entity_id, http_status from console.audit_log "
                + "where path = '/api/v1/sysadmin/backups/jobs'");
        assertThat(triggerRows).hasSize(1);
        assertThat(triggerRows.get(0)).containsEntry("subject", "admin").containsEntry("role", "ADMIN").containsEntry("method", "POST")
                .containsEntry("entity_type", "backup").containsEntry("entity_id", id).containsEntry("http_status", 202);
        List<Map<String, Object>> finishRows = jdbc.queryForList("select subject, role, method, path, entity_type, entity_id, http_status from console.audit_log "
                + "where path like 'system:backup%'");
        assertThat(finishRows).as("對帳列恰一筆（再呼叫兩次 reconcileOnce 仍一筆）").hasSize(1);
        assertThat(finishRows.get(0)).containsEntry("subject", "system").containsEntry("role", null).containsEntry("method", "SYSTEM")
                .containsEntry("path", "system:backup.finished").containsEntry("entity_type", "backup").containsEntry("entity_id", id)
                .containsEntry("http_status", 200);
    }

    @Test
    void AT_BK_10_2_2_everyRefusedTriggerStillLeavesItsOwnAuditRowAndNeverAFinishRow() {
        seed();
        post(null, request("full"));
        post(operator(), request("full"));
        jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at) values (?, 'verify', 'RUNNING', 'x', ?::timestamptz)",
                UUID.randomUUID(), iso(NOW.minusSeconds(30)));
        post(admin(), request("verify"));
        jdbc.execute("TRUNCATE console.backup_jobs");
        post(admin(), Map.of("type", "dump", "confirm", true));

        List<Map<String, Object>> rows = jdbc.queryForList("select subject, role, http_status from console.audit_log where method = 'POST' and path = '/api/v1/sysadmin/backups/jobs'");
        Map<Integer, Map<String, Object>> byStatus = new LinkedHashMap<>();
        rows.forEach(row -> byStatus.put((Integer) row.get("http_status"), row));
        assertThat(rows).as("四次被拒的 POST 各留一列").hasSize(4);
        assertThat(byStatus.keySet()).containsExactlyInAnyOrder(401, 403, 409, 422);
        assertThat(byStatus.get(401)).containsEntry("subject", null);
        assertThat(byStatus.get(403)).containsEntry("role", "OPERATOR");
        assertThat(byStatus.get(409)).containsEntry("role", "ADMIN");
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log where path like 'system:backup%'", Long.class)).as("被拒的 POST 不留 backup.finished").isZero();
        assertThat(jobRows()).as("被拒的 POST 不建列").isZero();
    }

    @Test
    void AT_BK_10_2_E_1_pollingTheReadEndpointsNeverFloodsTheAuditTable() {
        seed();
        UUID id = UUID.randomUUID();
        jdbc.update("insert into console.backup_jobs (id, type, status, requested_by, requested_at) values (?, 'verify', 'SUCCEEDED', 'x', ?::timestamptz)", id,
                iso(NOW.minusSeconds(900)));
        for (int i = 0; i < 20; i++) {
            assertThat(overview().status()).isEqualTo(200);
            assertThat(api.get(admin(), JOBS).status()).isEqualTo(200);
            assertThat(api.get(admin(), JOBS + "/" + id).status()).isEqualTo(200);
        }
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log", Long.class)).as("審計只含寫入方法").isZero();
    }

    @Test
    void AT_BK_10_3_1_theRoleMatrixIsExactlyViewerForReadsAndAdminOnlyForTheTrigger() {
        seed();
        String unknown = JOBS + "/" + UUID.randomUUID();
        for (String url : List.of(BACKUPS, JOBS, unknown)) {
            assertThat(api.get(null, url).status()).as("無 token GET " + url).isEqualTo(401);
            for (String token : List.of(viewer(), operator(), admin())) {
                int expected = url.equals(unknown) ? 404 : 200;
                assertThat(api.get(token, url).status()).as("GET " + url).isEqualTo(expected);
            }
        }
        assertThat(post(null, request("verify")).status()).isEqualTo(401);
        assertThat(post(viewer(), request("verify")).status()).isEqualTo(403);
        assertThat(post(operator(), request("verify")).status()).isEqualTo(403);
        assertThat(post(admin(), request("verify")).status()).isEqualTo(202);
    }

    @Test
    void AT_BK_10_3_E_1_thereIsNoWritableApiForRetentionOrScheduleAndNoWriteMethodReturns2xx() {
        seed();
        UUID id = UUID.randomUUID();
        String single = JOBS + "/" + id;
        for (String url : List.of(JOBS, single, BACKUPS + "/retention", BACKUPS + "/schedule")) {
            for (HttpMethod method : List.of(HttpMethod.PUT, HttpMethod.PATCH, HttpMethod.DELETE)) {
                for (String token : List.of(admin(), operator())) {
                    int status = api.raw(token, method, url, "{}").status();
                    assertThat(status).as("%s %s（ADMIN／OPERATOR）沒有對映：404 或 405", method, url).isIn(404, 405);
                }
                assertThat(api.raw(viewer(), method, url, "{}").status()).as("%s %s（VIEWER）", method, url).isEqualTo(403);
            }
        }
        assertNothingWritten("寫入方法");
    }

    /** 洩漏掃描核心：回語料裡出現的機密（點名）；空＝乾淨。 */
    static List<String> leakProblems(List<String> corpus, List<String> secrets) {
        List<String> problems = new ArrayList<>();
        for (String secret : secrets) {
            for (String text : corpus) {
                if (text != null && text.contains(secret)) {
                    problems.add("語料含機密：" + secret);
                    break;
                }
            }
        }
        return problems;
    }

    @Test
    void AT_BK_10_4_1_noSecretReachesAnyResponseLogAuditRowOrFile() throws IOException {
        List<String> secrets = List.of("aisdlc-test", encryptionKey, "fake/secret+example/4", "fake-pass-example-1");
        seed();
        job("dump", FakeBackupRunner.jobJson("dump", "scheduled", "failed", 1, "script_failed", "2026-10-26T18:30:00Z", "2026-10-26T18:30:40Z",
                "AWS_SECRET_ACCESS_KEY=fake/secret+example/4\npass=fake-pass-example-1\nupload failed", null));
        ListAppender<ILoggingEvent> appender = new ListAppender<>();
        appender.start();
        ch.qos.logback.classic.Logger root = (ch.qos.logback.classic.Logger) LoggerFactory.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME);
        root.addAppender(appender);
        List<String> responses = new ArrayList<>();
        try {
            responses.add(overview().body());
            responses.add(api.get(viewer(), BACKUPS).body());
            responses.add(api.get(admin(), JOBS).body());
            Resp accepted = post(admin(), request("verify"));
            responses.add(accepted.body());
            String id = (String) accepted.data().get("id");
            runner.writeResult(UUID.fromString(id), "verify", "failed", "script_failed", 1, "pass=fake-pass-example-1\nAWS_SECRET_ACCESS_KEY=fake/secret+example/4");
            reconciler.reconcileOnce();
            responses.add(api.get(admin(), JOBS + "/" + id).body());
            responses.add(post(admin(), request("full")).body());
            responses.add(post(operator(), request("full")).body());
            responses.add(post(null, request("full")).body());
            responses.add(api.raw(admin(), HttpMethod.POST, JOBS, "{\"type\":").body());
            responses.add(api.get(admin(), JOBS + "/not-a-uuid").body());
            responses.add(api.get(admin(), JOBS + "?limit=x").body());
        } finally {
            root.detachAppender(appender);
        }
        List<String> logs = new ArrayList<>();
        appender.list.forEach(event -> {
            logs.add(event.getFormattedMessage());
            if (event.getArgumentArray() != null) {
                for (Object argument : event.getArgumentArray()) {
                    logs.add(String.valueOf(argument));
                }
            }
            if (event.getThrowableProxy() != null) {
                logs.add(String.valueOf(event.getThrowableProxy().getMessage()));
            }
        });
        List<String> audit = jdbc.queryForList("select * from console.audit_log").stream().map(Object::toString).toList();
        List<String> files = new ArrayList<>();
        try (Stream<Path> walk = Files.walk(requestRoot)) {
            for (Path path : walk.filter(Files::isRegularFile).toList()) {
                files.add(Files.readString(path, StandardCharsets.UTF_8));
            }
        }
        // 輸出目錄：植入機密的兩份檔（模擬「sidecar 漏遮罩」的 jobs/dump.json 與 results/）本來就含植入值，不在掃描範圍；其餘匯出檔（info、logical、schedule、
        // heartbeat 與另外的 jobs）是 sidecar 寫的、console-api 不改，必須不含 DB 密碼與加密金鑰
        try (Stream<Path> walk = Files.walk(exportRoot)) {
            for (Path path : walk.filter(Files::isRegularFile).filter(p -> !p.toString().replace('\\', '/').contains("/results/")
                    && !p.toString().replace('\\', '/').endsWith("/jobs/dump.json")).toList()) {
                files.add(Files.readString(path, StandardCharsets.UTF_8));
            }
        }

        // 防反空轉：每一種語料都有內容
        assertThat(responses).hasSizeGreaterThanOrEqualTo(10).allSatisfy(body -> assertThat(body).isNotBlank());
        assertThat(logs).as("日誌事件").isNotEmpty();
        assertThat(audit).as("審計列").isNotEmpty();
        assertThat(files).as("請求與 results 檔").isNotEmpty();

        List<String> corpus = new ArrayList<>();
        corpus.addAll(responses);
        corpus.addAll(logs);
        corpus.addAll(audit);
        corpus.addAll(files);
        assertThat(leakProblems(corpus, secrets)).as("植入值只可能以遮罩形 *** 出現").isEmpty();
        assertThat(responses.get(0)).as("ADMIN 看到的是遮罩後的尾段").contains("AWS_SECRET_ACCESS_KEY=***").contains("pass=***");
    }

    @Test
    void AT_BK_10_4_E_1_theLeakScannerFlagsEverySecretAndStaysQuietOnMaskedOrEmptyCorpora() {
        List<String> secrets = List.of("aisdlc-test", "KEY-VALUE-EXAMPLE", "fake-pass-example-1");
        assertThat(leakProblems(List.of("jdbc password aisdlc-test"), secrets)).as("(a)").anyMatch(p -> p.contains("aisdlc-test"));
        assertThat(leakProblems(List.of("key KEY-VALUE-EXAMPLE end"), secrets)).as("(b)").anyMatch(p -> p.contains("KEY-VALUE-EXAMPLE"));
        assertThat(leakProblems(List.of("pass=fake-pass-example-1"), secrets)).as("(c)").anyMatch(p -> p.contains("fake-pass-example-1"));
        assertThat(leakProblems(List.of("pass=***"), secrets)).as("(d) 只含遮罩形").isEmpty();
        assertThat(leakProblems(List.of(), secrets)).as("(e) 空語料").isEmpty();
    }

    @Test
    void AT_BK_10_5_1_theOverviewOperationIsDocumentedWithItsIdAndTag() {
        Resp docs = api.get(null, "/v3/api-docs");

        assertThat(docs.status()).isEqualTo(200);
        assertThat(docs.<String>read("$.paths['/api/v1/sysadmin/backups'].get.operationId")).isEqualTo("getBackupOverview");
        assertThat(docs.<List<String>>read("$.paths['/api/v1/sysadmin/backups'].get.tags")).contains("系統管理（資料庫備份）");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/sysadmin/backups']").keySet()).containsExactly("get");
    }

    @Test
    void AT_BK_10_5_2_theJobEndpointsAreDocumentedWithTheirOperationIdsAndErrorResponses() {
        Resp docs = api.get(null, "/v3/api-docs");

        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/sysadmin/backups/jobs']").keySet()).containsExactlyInAnyOrder("get", "post");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/sysadmin/backups/jobs/{id}']").keySet()).containsExactly("get");
        assertThat(docs.<String>read("$.paths['/api/v1/sysadmin/backups/jobs'].get.operationId")).isEqualTo("getBackupJobs");
        assertThat(docs.<String>read("$.paths['/api/v1/sysadmin/backups/jobs'].post.operationId")).isEqualTo("postBackupJob");
        assertThat(docs.<String>read("$.paths['/api/v1/sysadmin/backups/jobs/{id}'].get.operationId")).isEqualTo("getBackupJob");
        Set<String> postCodes = new HashSet<>(docs.<Map<String, Object>>read("$.paths['/api/v1/sysadmin/backups/jobs'].post.responses").keySet());
        assertThat(postCodes).contains("202", "400", "401", "403", "409", "422", "429", "503");
        assertThat(docs.<Map<String, Object>>read("$.paths['/api/v1/sysadmin/backups/jobs/{id}'].get.responses").keySet()).contains("404", "503");
    }

    @Test
    void AT_BK_10_5_E_1_noSysadminPathHasAPutPatchOrDelete() {
        Resp docs = api.get(null, "/v3/api-docs");
        Map<String, Object> paths = docs.read("$.paths");
        List<String> sysadmin = paths.keySet().stream().filter(p -> p.startsWith("/api/v1/sysadmin/")).sorted().toList();

        assertThat(sysadmin).containsExactly("/api/v1/sysadmin/backups", "/api/v1/sysadmin/backups/jobs", "/api/v1/sysadmin/backups/jobs/{id}");
        for (String path : sysadmin) {
            assertThat(docs.<Map<String, Object>>read("$.paths['" + path + "']").keySet()).as(path).doesNotContain("put", "patch", "delete");
        }
    }
}
