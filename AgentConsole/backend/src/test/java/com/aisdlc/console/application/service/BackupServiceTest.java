package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.BackupJobUseCase;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.BackupControlPort;
import com.aisdlc.console.application.port.out.BackupJobRepository;
import com.aisdlc.console.application.port.out.BackupJobRepository.Job;
import com.aisdlc.console.application.port.out.BackupJobRepository.Status;
import com.aisdlc.console.application.port.out.BackupSettings;
import com.aisdlc.console.application.port.out.WalArchiveStatsPort;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.support.FakeBackupRunner;
import com.aisdlc.console.support.MutableClock;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.reflect.Constructor;
import java.lang.reflect.Proxy;
import java.nio.file.Path;
import java.sql.ResultSet;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TimeZone;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 備份服務層（無 Spring；假埠加可變專屬時鐘）：{@code BackupCron}、{@code BackupOverdue}、{@code BackupQueryService}、{@code BackupJobService}、
 * {@code BackupJobReconciler}（TCS-SysAdminBackup-20261027 的 BV 載具十五個 AT）。為什麼重要：這一層決定「畫面上看到的是不是真相」——逾期判錯會讓
 * 掌舵者以為昨晚備份成功（或對成功的備份誤報逾期）；對帳與兜底判錯會讓唯一索引被一個永遠不結束的工作鎖死、之後再也按不了備份；
 * 資料庫讀取失敗若被吞成「沒有進行中的工作」，會在背景還有工作時放行第二個。時間一律取自專屬時鐘 {@link MutableClock}。
 */
class BackupServiceTest {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final ZoneId TAIPEI = ZoneId.of("Asia/Taipei");
    private static final Instant T0 = Instant.parse("2026-10-27T02:00:00Z");

    // ── 假埠 ─────────────────────────────────────────────────────────────────────────────────

    private static final class FakeSettings implements BackupSettings {
        Path exportDir = Path.of("fake-export");
        Path requestDir = Path.of("fake-request");

        @Override
        public Path exportDir() {
            return exportDir;
        }

        @Override
        public Path requestDir() {
            return requestDir;
        }

        @Override
        public int requestTtlSeconds() {
            return 120;
        }

        @Override
        public int jobMaxSeconds() {
            return 21600;
        }

        @Override
        public long reconcileIntervalMs() {
            return 5000;
        }

        @Override
        public int overdueGraceMinutes() {
            return 30;
        }

        @Override
        public long minFullIntervalSeconds() {
            return 86400;
        }

        @Override
        public long minDiffIntervalSeconds() {
            return 3600;
        }
    }

    private static final class FakeControl implements BackupControlPort {
        final Map<String, String> files = new ConcurrentHashMap<>();
        final AtomicInteger reads = new AtomicInteger();
        final List<String> calls;
        final List<UUID> deleted = new CopyOnWriteArrayList<>();
        final List<Request> written = new CopyOnWriteArrayList<>();
        Runnable beforeWriteFails;
        boolean writeFails;
        boolean unreadableResults;

        FakeControl(List<String> calls) {
            this.calls = calls;
        }

        @Override
        public Optional<String> read(String relativePath) {
            reads.incrementAndGet();
            if (unreadableResults && relativePath.startsWith("results/")) {
                throw new UncheckedIOException(new IOException("results 暫時讀不到"));
            }
            return Optional.ofNullable(files.get(relativePath));
        }

        @Override
        public void writeRequest(Request request) throws IOException {
            calls.add("writeRequest");
            if (beforeWriteFails != null) {
                beforeWriteFails.run();
            }
            if (writeFails) {
                throw new IOException("寫入失敗（模擬）");
            }
            written.add(request);
        }

        @Override
        public boolean deleteRequest(UUID id) {
            deleted.add(id);
            return true;
        }

        @Override
        public int deleteStaleRequests(Instant olderThan) {
            return 0;
        }
    }

    private static final class FakeRepo implements BackupJobRepository {
        final Map<UUID, Job> rows = new LinkedHashMap<>();
        final List<String> calls;
        final List<String> statements = new ArrayList<>();
        int findActiveFailures;
        boolean duplicateOnInsert;

        FakeRepo(List<String> calls) {
            this.calls = calls;
        }

        @Override
        public synchronized List<Job> findActive() {
            calls.add("findActive");
            if (findActiveFailures > 0) {
                findActiveFailures--;
                throw new DataAccessResourceFailureException("模擬資料庫失敗");
            }
            return rows.values().stream().filter(job -> job.status().isActive()).toList();
        }

        @Override
        public synchronized void insertQueued(Job job) {
            calls.add("insertQueued");
            if (duplicateOnInsert) {
                throw new DuplicateKeyException("ux_backup_jobs_one_active");
            }
            rows.put(job.id(), job);
        }

        @Override
        public synchronized boolean markRunningIfQueued(UUID id, Instant startedAt) {
            statements.add("markRunningIfQueued WHERE status='QUEUED'");
            Job job = rows.get(id);
            if (job == null || job.status() != Status.QUEUED) {
                return false;
            }
            rows.put(id, new Job(id, job.type(), Status.RUNNING, job.requestedBy(), job.requestedAt(), startedAt, null, null, null, ""));
            return true;
        }

        @Override
        public synchronized boolean markTerminalIfActive(UUID id, Status status, Integer exitCode, String reason, Instant startedAt,
                                                         Instant finishedAt, String detail) {
            statements.add("markTerminalIfActive WHERE status IN ('QUEUED','RUNNING')");
            Job job = rows.get(id);
            if (job == null || !job.status().isActive()) {
                return false;
            }
            rows.put(id, new Job(id, job.type(), status, job.requestedBy(), job.requestedAt(),
                    startedAt != null ? startedAt : job.startedAt(), finishedAt, exitCode, reason, detail));
            return true;
        }

        @Override
        public synchronized boolean markExpiredIfQueued(UUID id, Instant finishedAt) {
            statements.add("markExpiredIfQueued WHERE status='QUEUED'");
            Job job = rows.get(id);
            if (job == null || job.status() != Status.QUEUED) {
                return false;
            }
            rows.put(id, new Job(id, job.type(), Status.EXPIRED, job.requestedBy(), job.requestedAt(), job.startedAt(), finishedAt,
                    null, "expired", ""));
            return true;
        }

        @Override
        public synchronized Optional<Job> findById(UUID id) {
            return Optional.ofNullable(rows.get(id));
        }

        @Override
        public synchronized List<Job> findPage(Instant before, int limit) {
            return rows.values().stream().filter(job -> before == null || job.requestedAt().isBefore(before))
                    .sorted((a, b) -> b.requestedAt().compareTo(a.requestedAt())).limit(limit).toList();
        }
    }

    private static final class RecordingAudit implements AuditTrail {
        final List<String> systemEvents = new CopyOnWriteArrayList<>();
        final List<String> notes = new CopyOnWriteArrayList<>();

        @Override
        public void note(String action, String entityType, String entityId) {
            notes.add(action + ":" + entityType + ":" + entityId);
        }

        @Override
        public void note(String action, String entityType, String entityId, Map<String, Object> extra) {
            note(action, entityType, entityId);
        }

        @Override
        public void event(String action, Map<String, Object> details) {
            // 本測試不用
        }

        @Override
        public void system(String action, String entityType, String entityId, Map<String, Object> details) {
            systemEvents.add(action + ":" + entityType + ":" + entityId);
        }
    }

    /** 一組接好的服務與假埠（每個情境各建一組，互不污染）。 */
    private static final class Fixture {
        final List<String> calls = new CopyOnWriteArrayList<>();
        final FakeSettings settings = new FakeSettings();
        final FakeControl control = new FakeControl(calls);
        final FakeRepo repo = new FakeRepo(calls);
        final RecordingAudit audit = new RecordingAudit();
        final MutableClock clock = new MutableClock(T0);
        WalArchiveStatsPort wal = () -> new WalArchiveStatsPort.Stats(null, 0, null);
        final BackupJobReconciler reconciler = new BackupJobReconciler(settings, control, repo, clock, audit);
        final BackupQueryService query;
        final BackupJobService jobs = new BackupJobService(settings, control, repo, clock, audit);

        Fixture() {
            query = new BackupQueryService(settings, control, repo, (WalArchiveStatsPort) () -> wal.read(), clock, reconciler);
            healthy(FakeBackupRunner.fixture("info-2repo.json"));
        }

        /** 健康的控制面：info（給定的 pgBackRest 輸出）、logical、schedule、新鮮心跳；沒有任何 jobs 檔。 */
        void healthy(String infoArray) {
            put("export/info.json", FakeBackupRunner.infoJson(clock.instant().minusSeconds(10).toString(), infoArray,
                    FakeBackupRunner.RETENTION_DEFAULT, FakeBackupRunner.REPOS_BOTH_LOCAL));
            put("export/logical.json", FakeBackupRunner.logicalJson(clock.instant().minusSeconds(10).toString(), "[]"));
            put("export/schedule.json", FakeBackupRunner.scheduleJson("Asia/Taipei"));
            heartbeat(3, false);
        }

        void put(String path, String content) {
            control.files.put(path, content);
        }

        void heartbeat(long ageSeconds, boolean lockHeld) {
            put("export/heartbeat", FakeBackupRunner.heartbeat(clock.instant().minusSeconds(ageSeconds), lockHeld));
        }

        Map<String, Object> overview(boolean admin) {
            return query.overview(admin);
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Object value) {
        return (Map<String, Object>) value;
    }

    @SuppressWarnings("unchecked")
    private static List<String> warnings(Map<String, Object> overview) {
        return (List<String>) map(overview.get("control")).get("warnings");
    }

    private static Instant taipei(String text) {
        String normalized = text.replace(' ', 'T');
        return LocalDateTime.parse(normalized.length() == 16 ? normalized + ":00" : normalized).atZone(TAIPEI).toInstant();
    }

    // ── AT-BK-03-3-1：BackupCron.next ────────────────────────────────────────────────────────

    @Test
    void AT_BK_03_3_1_nextRunIsStrictlyLaterThanNowComputedInTheScheduleZoneAndIgnoresTheJvmZone() {
        Instant now = taipei("2026-10-27 10:00");
        Map<String, String> crons = new LinkedHashMap<>();
        crons.put("0 2 * * 0", "2026-10-31T18:00:00Z");       // full：週日 02:00（11-01）
        crons.put("0 2 * * 1-6", "2026-10-27T18:00:00Z");      // diff：週一至週六 02:00（10-28）
        crons.put("30 2 * * *", "2026-10-27T18:30:00Z");       // dump
        crons.put("0 4 * * 3", "2026-10-27T20:00:00Z");        // verify：週三 04:00（10-28）
        crons.put("0 3 * * *", "2026-10-27T19:00:00Z");        // expire
        crons.put("30 3 * * *", "2026-10-27T19:30:00Z");       // wal_clean
        TimeZone original = TimeZone.getDefault();
        try {
            for (String jvmZone : List.of("UTC", "America/Los_Angeles", "Asia/Tokyo")) {
                TimeZone.setDefault(TimeZone.getTimeZone(jvmZone));
                crons.forEach((cron, expected) -> assertThat(BackupCron.next(cron, TAIPEI, now))
                        .as("%s（JVM 預設時區 %s 不得影響結果）", cron, TimeZone.getDefault().getID()).contains(Instant.parse(expected)));
            }
        } finally {
            TimeZone.setDefault(original);
        }
        // 星期欄 0 為週日：週六 10:00 的下一個全備是隔天 02:00（+08）
        assertThat(BackupCron.next("0 2 * * 0", TAIPEI, taipei("2026-10-31 10:00"))).contains(Instant.parse("2026-10-31T18:00:00Z"));
        assertThat(BackupCron.next("0 2 * * 0", TAIPEI, taipei("2026-11-01 01:59:59"))).contains(Instant.parse("2026-10-31T18:00:00Z"));
        // 恰為觸發時刻：嚴格晚於 now ⇒ 下一個在下週
        assertThat(BackupCron.next("0 2 * * 0", TAIPEI, taipei("2026-11-01 02:00:00"))).contains(Instant.parse("2026-11-07T18:00:00Z"));
        // 時區參數生效：同一個 cron 在 UTC 算出不同的瞬間
        assertThat(BackupCron.next("0 2 * * 1-6", ZoneId.of("UTC"), now)).contains(Instant.parse("2026-10-28T02:00:00Z"));
        // 解析不了：回空、不丟例外
        assertThat(BackupCron.next("0 2 * * 1-6/0", TAIPEI, now)).isEmpty();
        assertThat(BackupCron.next("not a cron", TAIPEI, now)).isEmpty();
        assertThat(BackupCron.next("", TAIPEI, now)).isEmpty();
        assertThat(BackupCron.next(null, TAIPEI, now)).isEmpty();
    }

    // ── AT-BK-04-3-1：BackupOverdue 的 OVERDUE_CASES ────────────────────────────────────────

    /** 一列 OVERDUE_CASES（§5.5）：時間為台北時間；「無」＝清單端不提供（空清單）；「—」＝該 repo 沒有符合的備份（null）。 */
    private record Case(String row, String cron, String now, String stateSuccess, List<String> repoLatest, boolean running,
                        String lastDueUtc, boolean overdue, boolean never) {
    }

    private static final String FULL = "0 2 * * 0";
    private static final String DIFF = "0 2 * * 1-6";
    private static final String DUMP = "30 2 * * *";
    private static final String VERIFY = "0 4 * * 3";

    private static List<Case> overdueCases() {
        List<String> none = List.of();
        return List.of(
                new Case("O1", DIFF, "2026-10-31 04:00", "2026-10-31 02:00:30", none, false, "2026-10-30T18:00:00Z", false, false),
                new Case("O2", DIFF, "2026-11-01 04:00", "2026-10-31 02:00:30", none, false, "2026-10-30T18:00:00Z", false, false),
                new Case("O3", FULL, "2026-11-01 04:00", "2026-11-01 02:00:30", none, false, "2026-10-31T18:00:00Z", false, false),
                new Case("O4", DIFF, "2026-11-02 02:15", "2026-10-31 02:00:30", none, false, "2026-11-01T18:00:00Z", false, false),
                new Case("O5", DIFF, "2026-11-02 02:31", "2026-10-31 02:00:30", none, false, "2026-11-01T18:00:00Z", true, false),
                new Case("O6", FULL, "2026-11-01 02:31", "2026-10-25 02:00:30", none, false, "2026-10-31T18:00:00Z", true, false),
                new Case("O7", DIFF, "2026-11-02 02:30:00", "2026-10-31 02:00:30", none, false, "2026-11-01T18:00:00Z", false, false),
                new Case("O8", DIFF, "2026-11-02 02:30:01", "2026-10-31 02:00:30", none, false, "2026-11-01T18:00:00Z", true, false),
                new Case("O9", DIFF, "2026-11-02 02:31", "2026-10-31 02:00:30", none, true, "2026-11-01T18:00:00Z", false, false),
                new Case("O10", DIFF, "2026-11-02 02:31", null, none, false, "2026-11-01T18:00:00Z", false, true),
                new Case("O11", DIFF, "2026-11-02 02:31", "2026-10-31 02:00:30", List.of("2026-11-02 02:02:00", "2026-11-02 02:03:00"), false,
                        "2026-11-01T18:00:00Z", false, false),
                new Case("O12", DIFF, "2026-11-02 02:31", "2026-10-31 02:00:30", List.of("2026-11-02 02:02:00", "2026-10-31 02:03:00"), false,
                        "2026-11-01T18:00:00Z", true, false),
                new Case("O13", DIFF, "2026-11-02 02:31", "2026-10-31 02:00:30", java.util.Arrays.asList("2026-11-02 02:02:00", null), false,
                        "2026-11-01T18:00:00Z", true, false),
                new Case("O14", FULL, "2026-10-27 10:00", null, List.of("2026-10-26 02:10:00", "2026-10-26 02:12:00"), false,
                        "2026-10-24T18:00:00Z", false, false),
                new Case("O15", DUMP, "2026-10-28 03:01", "2026-10-27 02:31:00", none, false, "2026-10-27T18:30:00Z", true, false),
                new Case("O16", VERIFY, "2026-10-28 04:31", "2026-10-21 04:05:00", none, false, "2026-10-27T20:00:00Z", true, false),
                new Case("O17", VERIFY, "2026-10-28 04:29", "2026-10-21 04:05:00", none, false, "2026-10-27T20:00:00Z", false, false),
                new Case("O18", FULL, "2026-11-01 02:00:00", "2026-10-25 02:00:30", none, false, "2026-10-31T18:00:00Z", false, false),
                new Case("O19", VERIFY, "2026-10-28 04:31", null, none, false, "2026-10-27T20:00:00Z", false, true),
                new Case("O20", VERIFY, "2026-10-29 10:00", "2026-10-28 04:05:00", none, false, "2026-10-27T20:00:00Z", false, false));
    }

    @Test
    void AT_BK_04_3_1_everyOverdueCaseRowMatchesLastDueOverdueAndNever() {
        List<Case> cases = overdueCases();
        assertThat(cases).as("防反空轉：O1～O20 全部在表中").hasSize(20);
        for (Case c : cases) {
            List<Instant> repoLatest = new ArrayList<>();
            for (String latest : c.repoLatest()) {
                repoLatest.add(latest == null ? null : taipei(latest));
            }
            BackupOverdue.Result result = BackupOverdue.evaluate(c.cron(), TAIPEI, taipei(c.now()), Duration.ofMinutes(30),
                    c.stateSuccess() == null ? null : taipei(c.stateSuccess()), repoLatest, c.running());
            assertThat(result.lastDueAt()).as("%s lastDueAt", c.row()).isEqualTo(Instant.parse(c.lastDueUtc()));
            assertThat(result.overdue()).as("%s overdue", c.row()).isEqualTo(c.overdue());
            assertThat(result.never()).as("%s never", c.row()).isEqualTo(c.never());
        }
        // 補：成功時間與最近一次應跑時間的邊界（O1～O20 沒有逐秒的相等列）——恰等於 lastDueAt ＝已履行；早一秒才是沒履行（now 已超過 30 分鐘寬限）
        BackupOverdue.Result onTheDot = BackupOverdue.evaluate("0 2 * * 1-6", TAIPEI, taipei("2026-11-02 02:31"), Duration.ofMinutes(30),
                taipei("2026-11-02 02:00:00"), List.of(), false);
        assertThat(onTheDot.lastDueAt()).isEqualTo(taipei("2026-11-02 02:00:00"));
        assertThat(onTheDot.overdue()).as("成功時間恰等於 lastDueAt ⇒ 已履行").isFalse();
        BackupOverdue.Result oneSecondShort = BackupOverdue.evaluate("0 2 * * 1-6", TAIPEI, taipei("2026-11-02 02:31"), Duration.ofMinutes(30),
                taipei("2026-11-02 01:59:59"), List.of(), false);
        assertThat(oneSecondShort.overdue()).as("成功時間早 lastDueAt 一秒 ⇒ 沒履行").isTrue();
        // cron 解析不了：lastDueAt 為 null、overdue 為 false、標記 cronUnparsable（算不出＝量不到，不是逾期）
        BackupOverdue.Result unparsable = BackupOverdue.evaluate("0 2 * * 1-6/0", TAIPEI, taipei("2026-11-02 02:31"), Duration.ofMinutes(30),
                taipei("2026-10-31 02:00:30"), List.of(), false);
        assertThat(unparsable.lastDueAt()).isNull();
        assertThat(unparsable.overdue()).isFalse();
        assertThat(unparsable.cronUnparsable()).isTrue();
    }

    @Test
    void theLastDueLookbackWindowIsEightDaysSoARarelyFiringScheduleStillHasALastDueWithinIt() {
        // 每月 1 日 02:00（Asia/Taipei）：8 日 14:00 時最近一次應跑在 7.5 天前——8 天窗找得到；9 日 03:00 時在 8 天又 1 小時前——超出窗、回空
        // （呼叫端把空轉成 lastDueAt:null、overdue:false）。釘住回溯窗的兩端：改成 7 天或 9 天都會紅
        assertThat(BackupCron.lastDue("0 2 1 * *", TAIPEI, taipei("2026-11-08 14:00"))).contains(taipei("2026-11-01 02:00"));
        assertThat(BackupCron.lastDue("0 2 1 * *", TAIPEI, taipei("2026-11-09 03:00"))).isEmpty();
    }

    // ── AT-BK-04-6-2：真實的 WalArchiveStatsAdapter 接 JdbcTemplate 替身 ──────────────────────

    /** 只回一列的 ResultSet 替身（{@code getLong("failed_count")} 與兩個時間欄）。 */
    private static ResultSet oneRow(long failed, Instant archived, Instant failedAt) {
        return (ResultSet) Proxy.newProxyInstance(BackupServiceTest.class.getClassLoader(), new Class<?>[] {ResultSet.class},
                (proxy, method, args) -> switch (method.getName()) {
                    case "getLong" -> failed;
                    case "getObject" -> {
                        Instant value = "last_archived_time".equals(args[0]) ? archived : failedAt;
                        yield value == null ? null : OffsetDateTime.ofInstant(value, ZoneOffset.UTC);
                    }
                    case "wasNull" -> false;
                    default -> throw new UnsupportedOperationException(method.getName());
                });
    }

    private static WalArchiveStatsPort realAdapterOver(JdbcTemplate jdbc) throws ReflectiveOperationException {
        Constructor<?> constructor = Class.forName("com.aisdlc.console.adapter.out.persistence.WalArchiveStatsAdapter")
                .getDeclaredConstructor(JdbcTemplate.class);
        constructor.setAccessible(true);
        return (WalArchiveStatsPort) constructor.newInstance(jdbc);
    }

    /** 依序回應的 JdbcTemplate 替身：每個元素是「一列」或「要丟的例外」。 */
    private static JdbcTemplate scripted(List<Object> script) {
        AtomicInteger next = new AtomicInteger();
        return new JdbcTemplate() {
            @Override
            public <T> T queryForObject(String sql, RowMapper<T> rowMapper) throws DataAccessException {
                Object step = script.get(next.getAndIncrement());
                if (step instanceof RuntimeException failure) {
                    throw failure;
                }
                try {
                    return rowMapper.mapRow((ResultSet) step, 0);
                } catch (java.sql.SQLException e) {
                    throw new IllegalStateException(e);
                }
            }
        };
    }

    @Test
    void AT_BK_04_6_2_walArchiveReadFailuresDegradeOnlyThatBlockAndNeverTurnIntoZero() throws ReflectiveOperationException {
        Instant archived = Instant.parse("2026-10-27T01:59:00Z");
        Instant failedAt = archived.plus(Duration.ofMinutes(5));
        Fixture f = new Fixture();
        f.put("export/jobs/full.json", FakeBackupRunner.jobRunning("full", "scheduled", "2026-10-27T01:50:00Z", null));
        f.heartbeat(5, true);
        WalArchiveStatsPort adapter = realAdapterOver(scripted(List.of(oneRow(0, archived, null), oneRow(3, archived, failedAt),
                new DataAccessResourceFailureException("連線中斷"), new IllegalStateException("意外"))));
        f.wal = adapter;

        Map<String, Object> first = f.overview(true);
        assertThat(map(first.get("walArchive"))).containsEntry("failedCount", 0L).containsEntry("lastArchivedAt", archived.toString())
                .containsEntry("lastFailedAt", null);
        Map<String, Object> second = f.overview(true);
        assertThat(map(second.get("walArchive"))).containsEntry("failedCount", 3L).containsEntry("lastFailedAt", failedAt.toString());

        for (int i = 0; i < 2; i++) {
            Map<String, Object> degraded = f.overview(true);
            assertThat(degraded.get("walArchive")).as("讀不到＝null，不是 0 計數的物件（adapter 吞例外回零物件即紅）").isNull();
            assertThat(warnings(degraded)).contains("db_unavailable");
            assertThat(degraded.get("cards")).as("其餘區塊完整").isNotNull();
            assertThat(degraded.get("backups")).isNotNull();
            assertThat(degraded.get("schedule")).isNotNull();
            assertThat(degraded.get("repos")).isNotNull();
            assertThat(map(degraded.get("control")).get("canTrigger")).as("僅 walArchive 失敗時 canTrigger 不受影響")
                    .isEqualTo(map(first.get("control")).get("canTrigger")).isEqualTo(true);
            assertThat(degraded.get("activeJob")).as("activeJob 與第一案逐值相同").isEqualTo(first.get("activeJob"));
            assertThat(map(degraded.get("activeJob"))).containsEntry("type", "full").containsEntry("status", "RUNNING");
        }
    }

    // ── AT-BK-05-1-E-1／E-2：設定與優先序 ───────────────────────────────────────────────────

    private static Map<String, Object> triggerBody(String type) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("type", type);
        body.put("confirm", true);
        return body;
    }

    @Test
    void AT_BK_05_1_E_1_getOnlyNeedsTheExportDirAndPostAlsoNeedsTheRequestDir() {
        Fixture f = new Fixture();
        f.settings.requestDir = null;

        Map<String, Object> overview = f.overview(true);
        Map<String, Object> control = map(overview.get("control"));
        assertThat(control).containsEntry("available", true).containsEntry("canTrigger", false).containsEntry("reason", null);
        assertThat(overview.get("cards")).isNotNull();
        assertThat(overview.get("backups")).isNotNull();

        assertThatThrownBy(() -> f.jobs.trigger("admin", triggerBody("full"))).isInstanceOfSatisfying(ServiceUnavailableException.class,
                e -> assertThat(e.reason()).isEqualTo(ErrorReasons.BACKUP_CONTROL_UNAVAILABLE));
        assertThat(f.repo.rows).as("不建列").isEmpty();
        assertThat(f.control.written).as("不寫檔").isEmpty();

        // 反方向：request-dir 有設而 export-dir 未設 ⇒ 概覽為 not_configured、POST 亦 503
        f.settings.requestDir = Path.of("fake-request");
        f.settings.exportDir = null;
        assertThat(map(f.overview(true).get("control"))).containsEntry("reason", "not_configured").containsEntry("available", false);
        assertThatThrownBy(() -> f.jobs.trigger("admin", triggerBody("full"))).isInstanceOf(ServiceUnavailableException.class);
        assertThat(f.repo.rows).isEmpty();
    }

    @Test
    void AT_BK_05_1_E_2_notConfiguredWinsOverEverythingAndTheControlPortIsNeverTouched() {
        Fixture f = new Fixture();
        f.settings.exportDir = null;
        // 壞快照：schema_rev=2 加截斷 JSON——若優先序錯誤（先讀檔），會得到 schema_mismatch／export_unreadable
        f.put("export/info.json", "{\"schema_rev\":2,\"generated_at\":\"2026-10-27T0");
        f.put("export/heartbeat", "{\"schema_rev\":2");
        f.control.reads.set(0);

        Map<String, Object> overview = f.overview(true);

        assertThat(map(overview.get("control"))).containsEntry("reason", "not_configured").containsEntry("available", false)
                .containsEntry("canTrigger", false).containsEntry("heartbeatAgeSeconds", null)
                .containsEntry("exportAgeSeconds", null).containsEntry("exportGeneratedAt", null);
        assertThat(overview).containsEntry("timezone", null).containsEntry("activeJob", null).containsEntry("cards", null)
                .containsEntry("backups", null).containsEntry("schedule", null).containsEntry("repos", null)
                .containsEntry("walArchive", null);
        assertThat(f.control.reads.get()).as("優先序 not_configured＞schema_mismatch＞export_unreadable＞runner_offline：假埠讀取次數＝0").isZero();
    }

    // ── AT-BK-05-5-E-1：兩個資料庫讀取各自降級 ──────────────────────────────────────────────

    @Test
    void AT_BK_05_5_E_1_aFailingJobsReadDegradesTheActiveJobButDoesNotTakeWalArchiveDownWithIt() {
        Fixture f = new Fixture();
        f.put("export/jobs/full.json", FakeBackupRunner.jobRunning("full", "scheduled", "2026-10-27T01:50:00Z", null));
        f.heartbeat(5, true);
        f.repo.findActiveFailures = 100; // 資料庫整段時間都壞（GET 順帶的對帳與總覽自己的讀取都失敗）
        f.wal = () -> new WalArchiveStatsPort.Stats(Instant.parse("2026-10-27T01:59:00Z"), 0, null);

        Map<String, Object> overview = f.overview(true);

        Map<String, Object> control = map(overview.get("control"));
        assertThat(warnings(overview)).contains("db_unavailable");
        assertThat(control).as("DB 失敗時不可觸發").containsEntry("canTrigger", false);
        assertThat(map(overview.get("activeJob"))).as("activeJob 只由匯出的鎖狀態導出").containsEntry("id", null)
                .containsEntry("type", "full").containsEntry("status", "RUNNING").containsEntry("trigger", "scheduled");
        assertThat(overview.get("walArchive")).as("兩個 DB 讀取獨立降級，互不連坐").isNotNull();
        assertThatCode(() -> f.overview(true)).as("概覽不丟例外").doesNotThrowAnyException();
    }

    // ── AT-BK-06-3-1：先插列、後寫檔 ────────────────────────────────────────────────────────

    @Test
    void AT_BK_06_3_1_theSuccessPathInsertsTheRowBeforeItWritesTheRequestFile() {
        Fixture f = new Fixture();
        f.control.beforeWriteFails = () -> assertThat(f.repo.rows).as("writeRequest 被呼叫的當下，假 Repository 已含該列").hasSize(1);

        BackupJobUseCase.Accepted accepted = f.jobs.trigger("admin", triggerBody("full"));

        assertThat(f.calls).containsExactly("findActive", "insertQueued", "writeRequest");
        assertThat(accepted.status()).isEqualTo("QUEUED");
        assertThat(accepted.type()).isEqualTo("full");
        assertThat(accepted.requestedAt()).isEqualTo(T0);
        BackupControlPort.Request request = f.control.written.get(0);
        assertThat(request.id().toString()).isEqualTo(accepted.id());
        assertThat(request.requestedAt()).isEqualTo(T0);
        assertThat(request.expiresAt()).as("expires_at＝requested_at＋request-ttl-seconds").isEqualTo(T0.plusSeconds(120));
        assertThat(f.audit.notes).containsExactly("backup.trigger:backup:" + accepted.id());
    }

    // ── AT-BK-06-4-E-1：併發輸家 ────────────────────────────────────────────────────────────

    @Test
    void AT_BK_06_4_E_1_aDuplicateKeyFromTheUniqueIndexBecomesTheSameConflictNotA500() {
        Fixture f = new Fixture();
        f.repo.duplicateOnInsert = true;

        assertThatThrownBy(() -> f.jobs.trigger("admin", triggerBody("diff"))).isInstanceOfSatisfying(ConflictException.class,
                e -> assertThat(e.reason()).isEqualTo(ErrorReasons.BACKUP_JOB_IN_PROGRESS));

        assertThat(f.control.written).as("不寫請求檔").isEmpty();
        assertThat(f.repo.rows).as("沒有留下半成品列").isEmpty();
    }

    // ── 對帳的共用夾具：一列 QUEUED／RUNNING ───────────────────────────────────────────────

    private static Job row(Status status, Instant requestedAt, Instant startedAt) {
        return new Job(UUID.randomUUID(), "diff", status, "admin", requestedAt, startedAt, null, null, null, "");
    }

    private static String resultFile(Job job, String status, String reason, Integer rc) {
        return FakeBackupRunner.resultJson(job.id().toString(), job.type(), status, reason, rc, T0.toString(),
                "running".equals(status) ? null : T0.plusSeconds(5).toString(), "stub");
    }

    // ── AT-BK-06-6-2：runner 存活時 console-api 不自行標 EXPIRED ────────────────────────────

    @Test
    void AT_BK_06_6_2_aLiveRunnerExpiresTheRequestItselfAndTheReconcilerOnlyMirrorsIt() {
        Fixture f = new Fixture();
        Job queued = row(Status.QUEUED, T0, null);
        f.repo.rows.put(queued.id(), queued);
        f.clock.set(T0.plusSeconds(121));
        f.heartbeat(3, false);

        assertThat(f.reconciler.reconcileOnce()).isZero();
        assertThat(f.repo.rows.get(queued.id()).status()).as("runner 存活（心跳新鮮）：自己會寫 rejected／expired，console-api 不自行標").isEqualTo(Status.QUEUED);

        f.put("results/" + queued.id() + ".json", resultFile(queued, "rejected", "expired", null));
        assertThat(f.reconciler.reconcileOnce()).isEqualTo(1);
        Job done = f.repo.rows.get(queued.id());
        assertThat(done.status()).isEqualTo(Status.EXPIRED);
        assertThat(done.reason()).isEqualTo("expired");
        assertThat(done.finishedAt()).isNotNull();
    }

    // ── AT-BK-06-6-3：runner 離線時條件式標 EXPIRED ────────────────────────────────────────

    @Test
    void AT_BK_06_6_3_anOfflineRunnerLetsTheConsoleExpireAQueuedRowOnlyAfterStrictlyMoreThanTheTtl() {
        Fixture f = new Fixture();
        Job queued = row(Status.QUEUED, T0, null);
        f.repo.rows.put(queued.id(), queued);
        f.clock.set(T0.plusSeconds(119));
        f.heartbeat(31, false);
        assertThat(f.reconciler.reconcileOnce()).as("未逾 120 秒：不標").isZero();
        assertThat(f.repo.rows.get(queued.id()).status()).isEqualTo(Status.QUEUED);
        f.clock.set(T0.plusSeconds(120));
        f.heartbeat(31, false);
        assertThat(f.reconciler.reconcileOnce()).as("恰 120 秒：嚴格大於才標").isZero();

        f.clock.set(T0.plusSeconds(121));
        f.heartbeat(31, false);
        assertThat(f.reconciler.reconcileOnce()).isEqualTo(1);

        Job expired = f.repo.rows.get(queued.id());
        assertThat(expired.status()).isEqualTo(Status.EXPIRED);
        assertThat(expired.reason()).isEqualTo("expired");
        assertThat(f.control.deleted).as("標後刪請求檔").contains(queued.id());
        assertThat(f.repo.statements).anyMatch(s -> s.startsWith("markExpiredIfQueued") && s.contains("WHERE status='QUEUED'"));
        assertThat(f.audit.systemEvents).containsExactly("backup.finished:backup:" + queued.id());
    }

    // ── AT-BK-06-6-5：2×TTL 絕對上限 ──────────────────────────────────────────────────────

    @Test
    void AT_BK_06_6_5_aQueuedRowWithoutResultsIsExpiredAtStrictlyMoreThanTwiceTheTtlEvenWithAFreshHeartbeat() {
        Fixture f = new Fixture();
        Job queued = row(Status.QUEUED, T0, null);
        f.repo.rows.put(queued.id(), queued);

        f.clock.set(T0.plusSeconds(240));
        f.heartbeat(3, false);
        assertThat(f.reconciler.reconcileOnce()).as("恰 240 秒：不動").isZero();
        assertThat(f.repo.rows.get(queued.id()).status()).isEqualTo(Status.QUEUED);

        f.clock.set(T0.plusSeconds(241));
        f.heartbeat(3, false);
        assertThat(f.reconciler.reconcileOnce()).as("241 秒：不論心跳新鮮，標 EXPIRED").isEqualTo(1);
        assertThat(f.repo.rows.get(queued.id()).status()).isEqualTo(Status.EXPIRED);
        assertThat(f.control.deleted).contains(queued.id());
        assertThat(f.repo.findActive()).as("唯一索引釋放：不再有進行中的列").isEmpty();
    }

    // ── AT-BK-06-8-3：timeout 要「逾時且心跳過期」 ──────────────────────────────────────────

    @Test
    void AT_BK_06_8_3_aRunningRowTimesOutOnlyWhenStrictlyOverTheMaximumAndTheHeartbeatIsStale() {
        // (a) 逾時且心跳過期 ⇒ FAILED／timeout
        Fixture a = new Fixture();
        Job running = row(Status.RUNNING, T0, T0);
        a.repo.rows.put(running.id(), running);
        a.clock.set(T0.plusSeconds(21601));
        a.heartbeat(100, true);
        assertThat(a.reconciler.reconcileOnce()).isEqualTo(1);
        assertThat(a.repo.rows.get(running.id()).status()).isEqualTo(Status.FAILED);
        assertThat(a.repo.rows.get(running.id()).reason()).isEqualTo("timeout");

        // (b) 逾時但心跳新鮮（控制面有回應＝長驗證不算逾時）⇒ 保持 RUNNING
        Fixture b = new Fixture();
        Job stillRunning = row(Status.RUNNING, T0, T0);
        b.repo.rows.put(stillRunning.id(), stillRunning);
        b.clock.set(T0.plusSeconds(21601));
        b.heartbeat(2, true);
        assertThat(b.reconciler.reconcileOnce()).isZero();
        assertThat(b.repo.rows.get(stillRunning.id()).status()).isEqualTo(Status.RUNNING);

        // (c) 恰 21600 秒且心跳過期：邊界為嚴格大於 ⇒ 保持 RUNNING
        Fixture c = new Fixture();
        Job atBoundary = row(Status.RUNNING, T0, T0);
        c.repo.rows.put(atBoundary.id(), atBoundary);
        c.clock.set(T0.plusSeconds(21600));
        c.heartbeat(100, true);
        assertThat(c.reconciler.reconcileOnce()).isZero();
        assertThat(c.repo.rows.get(atBoundary.id()).status()).isEqualTo(Status.RUNNING);
    }

    // ── AT-BK-06-8-4：排程不因一次例外而死亡 ─────────────────────────────────────────────────

    @Test
    void AT_BK_06_8_4_aFailingRoundIsSwallowedAndTheNextRoundStillRuns() {
        Fixture f = new Fixture();
        Job running = row(Status.RUNNING, T0, T0);
        f.repo.rows.put(running.id(), running);
        f.put("results/" + running.id() + ".json", resultFile(running, "succeeded", null, 0));
        f.repo.findActiveFailures = 1;

        assertThatCode(f.reconciler::runOnceQuietly).as("第一輪的例外只記 WARN、不外洩").doesNotThrowAnyException();
        assertThat(f.repo.rows.get(running.id()).status()).as("第一輪沒做成").isEqualTo(Status.RUNNING);

        f.reconciler.runOnceQuietly();

        assertThat(f.repo.rows.get(running.id()).status()).as("第二輪照常執行並更新列").isEqualTo(Status.SUCCEEDED);
        assertThat(f.audit.systemEvents).hasSize(1);
    }

    // ── AT-BK-06-9-E-1：補償是條件式 UPDATE ─────────────────────────────────────────────────

    @Test
    void AT_BK_06_9_E_1_aFailedRequestFileCompensatesOnlyAQueuedRowAndNeverOverwritesAnExpiredOne() {
        // 一般情況：該列為 QUEUED ⇒ FAILED(control_write_failed)，回 503
        Fixture f = new Fixture();
        f.control.writeFails = true;
        assertThatThrownBy(() -> f.jobs.trigger("admin", triggerBody("verify"))).isInstanceOfSatisfying(ServiceUnavailableException.class,
                e -> assertThat(e.reason()).isEqualTo(ErrorReasons.BACKUP_CONTROL_UNAVAILABLE));
        Job compensated = f.repo.rows.values().iterator().next();
        assertThat(compensated.status()).isEqualTo(Status.FAILED);
        assertThat(compensated.reason()).isEqualTo("control_write_failed");
        assertThat(compensated.finishedAt()).isNotNull();
        assertThat(f.repo.findActive()).as("唯一索引釋放，可立即重試").isEmpty();

        // 競態：寫檔失敗之前該列已被別處改成 EXPIRED ⇒ 補償不覆蓋（條件式 UPDATE 找不到 QUEUED／RUNNING 的列）
        Fixture raced = new Fixture();
        raced.control.writeFails = true;
        raced.control.beforeWriteFails = () -> {
            Job queued = raced.repo.rows.values().iterator().next();
            raced.repo.markExpiredIfQueued(queued.id(), T0);
        };
        assertThatThrownBy(() -> raced.jobs.trigger("admin", triggerBody("verify"))).isInstanceOf(ServiceUnavailableException.class);
        Job expired = raced.repo.rows.values().iterator().next();
        assertThat(expired.status()).as("已被改成 EXPIRED 的列不被補償覆蓋").isEqualTo(Status.EXPIRED);
        assertThat(expired.reason()).isEqualTo("expired");
    }

    // ── AT-BK-06-10-1：頻率上限 ─────────────────────────────────────────────────────────────

    /** 組出一份 pgBackRest 的 info 輸出：每個 repo 各指定最近全備與最近差異備份的 stop（null＝該 repo 沒有該類備份）。 */
    private static String info(Instant repo1Full, Instant repo2Full, Instant repo1Diff, Instant repo2Diff) {
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

    private static Fixture frequencyFixture(String info) {
        Fixture f = new Fixture();
        f.clock.set(Instant.parse("2026-10-27T12:00:00Z"));
        f.healthy(info);
        return f;
    }

    private static void assertAllowed(String type, String info, String label) {
        Fixture f = frequencyFixture(info);
        assertThat(f.jobs.trigger("admin", triggerBody(type)).status()).as(label).isEqualTo("QUEUED");
    }

    private static void assertTooFrequent(String type, String info, String nextAllowedAt, String label) {
        Fixture f = frequencyFixture(info);
        assertThatThrownBy(() -> f.jobs.trigger("admin", triggerBody(type))).as(label).isInstanceOfSatisfying(ConflictException.class, e -> {
            assertThat(e.reason()).isEqualTo(ErrorReasons.BACKUP_TOO_FREQUENT);
            assertThat(e.details()).containsEntry("type", type).containsEntry("nextAllowedAt", nextAllowedAt);
        });
        assertThat(f.repo.rows).as(label + "：零列").isEmpty();
        assertThat(f.control.written).as(label + "：零檔").isEmpty();
    }

    @Test
    void AT_BK_06_10_1_theFrequencyLimitLooksAtEveryConfiguredRepoWithStrictBoundaries() {
        Instant now = Instant.parse("2026-10-27T12:00:00Z");
        Instant old = now.minus(Duration.ofDays(3));
        // (a) 兩 repo 皆在 24 小時內 ⇒ 409，nextAllowedAt＝各 repo（最近全備＋86400 秒）的最小值
        assertTooFrequent("full", info(Instant.parse("2026-10-27T11:00:00Z"), Instant.parse("2026-10-27T11:30:00Z"), old, old),
                "2026-10-28T11:00:00Z", "(a)");
        // (b) 任一 repo 較舊（24 小時零 1 秒前）⇒ 允許
        assertAllowed("full", info(Instant.parse("2026-10-27T11:00:00Z"), Instant.parse("2026-10-26T11:59:59Z"), old, old), "(b)");
        // (c) 兩 repo 皆恰 24 小時前 ⇒ 允許（恰 24 小時不算「24 小時內」）
        assertAllowed("full", info(Instant.parse("2026-10-26T12:00:00Z"), Instant.parse("2026-10-26T12:00:00Z"), old, old), "(c)");
        // (d) repo2 沒有任何全備 ⇒ 允許（缺席視為較舊，不是「剛備份過」）
        assertAllowed("full", info(Instant.parse("2026-10-27T11:30:00Z"), null, old, old), "(d)");
        // (e) 23 小時 59 分 59 秒前 ⇒ 409，nextAllowedAt＝2026-10-27T12:00:01Z
        assertTooFrequent("full", info(Instant.parse("2026-10-26T12:00:01Z"), Instant.parse("2026-10-26T12:00:02Z"), old, old),
                "2026-10-27T12:00:01Z", "(e)");
        // 增備：門檻 3600 秒，以各 repo 最近一份「差異」備份判定
        assertTooFrequent("diff", info(old, old, Instant.parse("2026-10-27T11:00:01Z"), Instant.parse("2026-10-27T11:00:02Z")),
                "2026-10-27T12:00:01Z", "diff 59 分 59 秒前");
        assertAllowed("diff", info(old, old, Instant.parse("2026-10-27T11:00:00Z"), Instant.parse("2026-10-27T11:00:00Z")), "diff 恰 60 分");
        assertAllowed("diff", info(Instant.parse("2026-10-27T11:59:00Z"), Instant.parse("2026-10-27T11:59:00Z"), old, old),
                "增備看差異備份、不看全備：全備才剛做完也允許");
        // 驗證：無論多近都允許（只受單工限制）
        assertAllowed("verify", info(Instant.parse("2026-10-27T11:59:00Z"), Instant.parse("2026-10-27T11:59:00Z"),
                Instant.parse("2026-10-27T11:59:00Z"), Instant.parse("2026-10-27T11:59:00Z")), "verify 不設上限");
        // 沒有任何 stanza（info 為空陣列）⇒ 沒有已設定的 repo：不是「皆在門檻內」，允許
        assertAllowed("full", "[]", "無 stanza");
        // info 是 ok:false（合法檔）⇒ 評估不了，依主控裁決不擋
        Fixture failed = frequencyFixture("[]");
        failed.put("export/info.json", FakeBackupRunner.infoFailedJson("2026-10-27T11:59:50Z"));
        assertThat(failed.jobs.trigger("admin", triggerBody("full")).status()).isEqualTo("QUEUED");
    }

    // ── 驗證序：type 先於 confirm（BackupJobService 的入口閘，無 Spring）──────────────────────

    @Test
    void theGateOrderChecksTypeBeforeConfirmAndNeverTouchesTheRepositoryOnAnEarlyFailure() {
        Fixture f = new Fixture();
        Map<String, Object> both = new LinkedHashMap<>();
        assertThatThrownBy(() -> f.jobs.trigger("admin", both)).as("兩者皆不合：type 先於 confirm（422）")
                .hasMessageContaining("請求欄位未通過檢查");
        assertThat(f.calls).as("前序失敗零呼叫").isEmpty();
        Map<String, Object> noConfirm = new LinkedHashMap<>(Map.of("type", "full", "confirm", "true"));
        assertThatThrownBy(() -> f.jobs.trigger("admin", noConfirm)).as("字串 \"true\" 不是布林 true").hasMessage(BackupJobService.CONFIRM_REQUIRED_MESSAGE);
        assertThat(f.calls).isEmpty();
    }
}
