package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.BackupQueryUseCase;
import com.aisdlc.console.application.port.out.BackupClock;
import com.aisdlc.console.application.port.out.BackupControlPort;
import com.aisdlc.console.application.port.out.BackupJobRepository;
import com.aisdlc.console.application.port.out.BackupJobRepository.Job;
import com.aisdlc.console.application.port.out.BackupSettings;
import com.aisdlc.console.application.port.out.WalArchiveStatsPort;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.model.backup.BackupMasker;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;
import tools.jackson.databind.json.JsonMapper;

import java.io.UncheckedIOException;
import java.math.BigInteger;
import java.time.DateTimeException;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

/**
 * 備份頁的唯讀查詢（TCS-SysAdminBackup-20261027 §C3.1～§C3.3、D-BK-T5、D-BK-T6、D-BK-T9～T11、D-BK-T20；R-BK-04～R-BK-28）。
 *
 * <p><b>總覽的原則是 fail-loud</b>：每個請求讀 8 個控制面檔案（不快取）；控制面未設定、匯出檔不可讀、schema 不符時，所有資料區塊為 null 並以
 * {@code control.reason} 說明——<b>不當成「沒有備份」或 0</b>；個別來源（{@code ok:false}、cron 解析不了、資料庫讀取失敗）只降級該區塊並加
 * {@code control.warnings}。{@code reason} 的優先序：{@code not_configured} ＞ {@code schema_mismatch} ＞ {@code export_unreadable} ＞
 * {@code runner_offline}（前三者資料全 null；{@code runner_offline} 資料照回）。
 *
 * <p>時間一律取自 {@link BackupClock}、時區一律取自 {@code schedule.json.tz}（不依 JVM 預設時區）。本類別對 sidecar 只有檔案 I/O。
 * 輸出尾段與觸發者只給 ADMIN，且 API 端<b>不信任</b> sidecar 已遮罩——一律再遮罩一次、再取最後 2000 字元（R-BK-42）。
 */
@Service
public class BackupQueryService implements BackupQueryUseCase {

    /** 404 {@code backup_job_not_found} 的中文訊息（與契約表、前端 {@code BACKUP_REASONS} 逐字相同；雙向鎖住）。 */
    public static final String JOB_NOT_FOUND_MESSAGE = "查無此備份工作";

    private static final Logger LOG = LoggerFactory.getLogger(BackupQueryService.class);

    /** 心跳過期門檻（秒；嚴格大於才算離線，30 秒整仍正常）。 */
    static final int HEARTBEAT_STALE_SECONDS = 30;

    static final String NOT_CONFIGURED = "not_configured";
    static final String SCHEMA_MISMATCH = "schema_mismatch";
    static final String EXPORT_UNREADABLE = "export_unreadable";
    static final String RUNNER_OFFLINE = "runner_offline";

    private static final List<String> JOBS = List.of("full", "diff", "dump", "verify");
    private static final int DEFAULT_LIMIT = 20;
    private static final int MAX_LIMIT = 100;
    private static final Pattern DIGITS = Pattern.compile("[0-9]{1,9}");
    private static final Pattern CANONICAL_UUID = Pattern
            .compile("[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");

    private final BackupSettings settings;
    private final BackupJobRepository jobs;
    private final WalArchiveStatsPort walArchive;
    private final BackupClock clock;
    private final BackupJobReconciler reconciler;
    private final ExportReader reader;

    BackupQueryService(BackupSettings settings, BackupControlPort control, BackupJobRepository jobs,
                       WalArchiveStatsPort walArchive, BackupClock clock, BackupJobReconciler reconciler) {
        this.settings = settings;
        this.jobs = jobs;
        this.walArchive = walArchive;
        this.clock = clock;
        this.reconciler = reconciler;
        this.reader = new ExportReader(settings, control, clock);
    }

    // ── 總覽 ──────────────────────────────────────────────────────────────────────────────────

    @Override
    public Map<String, Object> overview(boolean admin) {
        if (settings.exportDir() != null && settings.requestDir() != null) {
            // 每次 GET 順帶對帳（R-BK-36）：失敗只記 WARN，不影響總覽
            reconciler.reconcileQuietly();
        }
        Export export = reader.read();
        Set<String> warnings = new LinkedHashSet<>();
        Map<String, Object> data = new LinkedHashMap<>();
        if (export.blocked()) {
            data.put("control", control(export, false, warnings));
            for (String block : List.of("timezone", "activeJob", "cards", "backups", "schedule", "repos", "walArchive")) {
                data.put(block, null);
            }
            return data;
        }

        // 兩個資料庫讀取各自降級，互不連坐（R-BK-27）
        List<Job> active = null;
        boolean jobsDbFailed = false;
        try {
            active = jobs.findActive();
        } catch (RuntimeException e) {
            jobsDbFailed = true;
            LOG.warn("備份工作表讀取失敗，總覽降級（activeJob 只取匯出的鎖狀態）：{}", BackupMasker.mask(e.toString()));
        }
        WalArchiveStatsPort.Stats wal = null;
        boolean walFailed = false;
        try {
            wal = walArchive.read();
        } catch (RuntimeException e) {
            walFailed = true;
            LOG.warn("WAL 歸檔統計讀取失敗，walArchive 降級為 null：{}", BackupMasker.mask(e.toString()));
        }

        if (!export.infoOk) {
            warnings.add("info_unavailable");
        }
        if (!export.logicalOk) {
            warnings.add("logical_unavailable");
        }
        ZoneId zone = ZoneId.of(export.tz);
        Job activeRow = active == null || active.isEmpty() ? null : active.get(0);
        List<Object> cards = cards(export, zone, activeRow, admin, warnings);
        Map<String, Object> schedule = schedule(export, zone, warnings);
        Map<String, Object> activeJob = activeJob(export, activeRow, admin);
        if (jobsDbFailed || walFailed) {
            warnings.add("db_unavailable");
        }
        boolean canTrigger = settings.requestDir() != null && export.reason == null && !jobsDbFailed;

        data.put("control", control(export, canTrigger, warnings));
        data.put("timezone", export.tz);
        data.put("activeJob", activeJob);
        data.put("cards", cards);
        data.put("backups", backups(export));
        data.put("schedule", schedule);
        data.put("repos", export.infoOk ? export.repos : null);
        data.put("walArchive", walFailed ? null : walArchive(wal));
        return data;
    }

    private static Map<String, Object> control(Export export, boolean canTrigger, Set<String> warnings) {
        Map<String, Object> control = new LinkedHashMap<>();
        control.put("available", !NOT_CONFIGURED.equals(export.reason));
        control.put("canTrigger", canTrigger);
        control.put("reason", export.reason);
        control.put("heartbeatAgeSeconds", export.heartbeatAgeSeconds);
        control.put("exportAgeSeconds", export.exportAgeSeconds());
        control.put("exportGeneratedAt", iso(export.generatedAt));
        control.put("warnings", new ArrayList<>(warnings));
        return control;
    }

    private static Map<String, Object> walArchive(WalArchiveStatsPort.Stats stats) {
        Map<String, Object> wal = new LinkedHashMap<>();
        wal.put("lastArchivedAt", iso(stats.lastArchivedAt()));
        wal.put("failedCount", stats.failedCount());
        wal.put("lastFailedAt", iso(stats.lastFailedAt()));
        return wal;
    }

    // ── cards ─────────────────────────────────────────────────────────────────────────────────

    private List<Object> cards(Export export, ZoneId zone, Job activeRow, boolean admin, Set<String> warnings) {
        List<Object> cards = new ArrayList<>();
        Duration grace = Duration.ofMinutes(settings.overdueGraceMinutes());
        for (String job : JOBS) {
            JobState state = export.jobStates.get(job);
            String status = export.derivedStatus(state);
            List<Instant> repoLatest = "full".equals(job) || "diff".equals(job)
                    ? export.repoLatest("full".equals(job) ? Set.of("full") : Set.of("diff", "full")) : List.of();
            BackupOverdue.Result evaluated = BackupOverdue.evaluate(export.cronOf(job), zone, export.now, grace,
                    state == null ? null : state.lastSuccessAt, repoLatest, "running".equals(status));
            if (evaluated.cronUnparsable()) {
                warnings.add("cron_unparsable:" + job);
            }
            Map<String, Object> card = new LinkedHashMap<>();
            card.put("job", job);
            card.put("status", status);
            card.put("trigger", state == null ? null : state.trigger);
            card.put("startedAt", iso(state == null ? null : state.startedAt));
            card.put("finishedAt", iso(state == null ? null : state.finishedAt));
            card.put("durationSeconds", state == null ? null : seconds(state.startedAt, state.finishedAt));
            card.put("lastSuccessAt", iso(evaluated.successAt()));
            card.put("lastDueAt", iso(evaluated.lastDueAt()));
            card.put("overdue", evaluated.overdue());
            card.put("never", evaluated.never());
            card.put("reason", cardReason(state, status));
            if ("full".equals(job) || "diff".equals(job)) {
                card.put("latestBackup", export.latestBackup("full".equals(job) ? Set.of("full") : Set.of("diff", "full")));
            }
            if (admin) {
                card.put("detailTail", state == null ? null : BackupMasker.maskedTail(state.detailTail, BackupMasker.TAIL_MAX));
                card.put("requestedBy", activeRow != null && activeRow.type().equals(job) ? activeRow.requestedBy() : null);
            }
            cards.add(card);
        }
        return cards;
    }

    private static String cardReason(JobState state, String status) {
        if (state == null) {
            return null;
        }
        if ("interrupted".equals(status) && !"interrupted".equals(state.status)) {
            return "interrupted";
        }
        return state.reason;
    }

    // ── activeJob ─────────────────────────────────────────────────────────────────────────────

    private static Map<String, Object> activeJob(Export export, Job activeRow, boolean admin) {
        Map<String, Object> active = new LinkedHashMap<>();
        if (activeRow != null) {
            active.put("id", activeRow.id().toString());
            active.put("type", activeRow.type());
            active.put("status", activeRow.status().name());
            active.put("trigger", "manual");
            active.put("requestedAt", iso(activeRow.requestedAt()));
            active.put("startedAt", iso(activeRow.startedAt()));
            if (admin) {
                active.put("requestedBy", activeRow.requestedBy());
            }
            return active;
        }
        if (!export.lockHeld) {
            return null;
        }
        // 匯出的鎖狀態：維護鎖有持有者，且某工作的狀態檔是 running（多個 running 時 started_at 最新者是持有者，其餘是殘留）
        String holder = null;
        JobState holderState = null;
        for (String job : JOBS) {
            JobState state = export.jobStates.get(job);
            if (state != null && "running".equals(export.derivedStatus(state))
                    && (holderState == null || state.startedAt.isAfter(holderState.startedAt))) {
                holder = job;
                holderState = state;
            }
        }
        if (holder == null) {
            return null;
        }
        active.put("id", null);
        active.put("type", holder);
        active.put("status", "RUNNING");
        active.put("trigger", holderState.trigger);
        active.put("requestedAt", null);
        active.put("startedAt", iso(holderState.startedAt));
        if (admin) {
            active.put("requestedBy", null);
        }
        return active;
    }

    // ── backups ───────────────────────────────────────────────────────────────────────────────

    private static List<Object> backups(Export export) {
        if (!export.infoOk && !export.logicalOk) {
            return null;
        }
        List<SortableRow> rows = new ArrayList<>();
        if (export.infoOk) {
            for (Backup b : export.backups) {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("kind", b.kind);
                row.put("label", b.label);
                row.put("location", "repo" + b.repoKey);
                row.put("startedAt", iso(b.start));
                row.put("finishedAt", iso(b.stop));
                row.put("durationSeconds", seconds(b.start, b.stop));
                row.put("databaseSizeBytes", b.databaseSize);
                row.put("repoSizeBytes", b.repoSize);
                row.put("baseLabel", "diff".equals(b.kind) ? b.prior : null);
                row.put("result", b.error ? "ok_with_errors" : "ok");
                rows.add(new SortableRow(b.stop, b.label, row));
            }
        }
        if (export.logicalOk) {
            for (Logical l : export.logical) {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("kind", "logical");
                row.put("label", l.name);
                row.put("location", "logical");
                row.put("startedAt", null);
                row.put("finishedAt", iso(l.modified));
                row.put("durationSeconds", null);
                row.put("databaseSizeBytes", null);
                row.put("repoSizeBytes", l.size);
                row.put("baseLabel", null);
                row.put("result", "ok");
                rows.add(new SortableRow(l.modified, l.name, row));
            }
        }
        // 新到舊；結束時間相同者依標籤字典序降冪（穩定：同一輸入兩次呼叫逐位元相同）
        rows.sort(Comparator.comparing(SortableRow::finishedAt).thenComparing(SortableRow::label).reversed());
        List<Object> sorted = new ArrayList<>();
        rows.forEach(row -> sorted.add(row.row()));
        return sorted;
    }

    /** 排序用：比的是瞬間（不是 ISO 字串），避免小數秒的字串序與時間序不一致。 */
    private record SortableRow(Instant finishedAt, String label, Map<String, Object> row) {
    }

    // ── schedule ──────────────────────────────────────────────────────────────────────────────

    private static Map<String, Object> schedule(Export export, ZoneId zone, Set<String> warnings) {
        List<Object> entries = new ArrayList<>();
        for (ScheduleEntry entry : export.entries) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("job", entry.job);
            row.put("cron", entry.cron);
            Optional<Instant> next = BackupCron.next(entry.cron, zone, export.now);
            if (BackupCron.parse(entry.cron).isEmpty()) {
                warnings.add("cron_unparsable:" + entry.job);
            }
            row.put("nextRunAt", iso(next.orElse(null)));
            entries.add(row);
        }
        Map<String, Object> retention = export.retention;
        if (retention == null && export.infoOk) {
            warnings.add("retention_unavailable");
        }
        Map<String, Object> schedule = new LinkedHashMap<>();
        schedule.put("entries", entries);
        schedule.put("retention", retention);
        return schedule;
    }

    // ── 工作紀錄 ──────────────────────────────────────────────────────────────────────────────

    @Override
    public JobPageView jobs(String limitText, String beforeText, boolean admin) {
        requireConfigured();
        int limit = DEFAULT_LIMIT;
        Instant before = null;
        List<Violation> violations = new ArrayList<>();
        if (limitText != null) {
            if (DIGITS.matcher(limitText).matches() && Integer.parseInt(limitText) >= 1
                    && Integer.parseInt(limitText) <= MAX_LIMIT) {
                limit = Integer.parseInt(limitText);
            } else {
                violations.add(new Violation("limit", "limit 須為 1 到 " + MAX_LIMIT + " 的整數"));
            }
        }
        if (beforeText != null) {
            try {
                before = OffsetDateTime.parse(beforeText).toInstant();
            } catch (DateTimeException e) {
                violations.add(new Violation("before", "before 須為 ISO-8601 的時間（例：2026-10-27T10:00:00Z）"));
            }
        }
        if (!violations.isEmpty()) {
            throw invalidRequest(violations);
        }
        if (settings.requestDir() != null) {
            reconciler.reconcileQuietly();
        }
        List<Job> rows;
        try {
            rows = jobs.findPage(before, limit + 1);
        } catch (DataAccessException e) {
            throw dbUnavailable(e);
        }
        boolean more = rows.size() > limit;
        List<Job> page = more ? rows.subList(0, limit) : rows;
        List<JobView> items = page.stream().map(job -> view(job, admin)).toList();
        return new JobPageView(items, more ? page.get(page.size() - 1).requestedAt() : null);
    }

    @Override
    public JobView job(String id, boolean admin) {
        requireConfigured();
        if (id == null || !CANONICAL_UUID.matcher(id).matches()) {
            throw notFound();
        }
        if (settings.requestDir() != null) {
            reconciler.reconcileQuietly();
        }
        Optional<Job> found;
        try {
            found = jobs.findById(UUID.fromString(id));
        } catch (DataAccessException e) {
            throw dbUnavailable(e);
        }
        return view(found.orElseThrow(BackupQueryService::notFound), admin);
    }

    private void requireConfigured() {
        if (settings.exportDir() == null) {
            throw new ServiceUnavailableException(BackupJobService.CONTROL_UNAVAILABLE_MESSAGE,
                    ErrorReasons.BACKUP_CONTROL_UNAVAILABLE);
        }
    }

    private static NotFoundException notFound() {
        return new NotFoundException(JOB_NOT_FOUND_MESSAGE, ErrorReasons.BACKUP_JOB_NOT_FOUND, Map.of());
    }

    private static ServiceUnavailableException dbUnavailable(RuntimeException cause) {
        LOG.warn("備份工作表讀取失敗：{}", BackupMasker.mask(cause.toString()));
        return new ServiceUnavailableException(BackupJobService.CONTROL_UNAVAILABLE_MESSAGE,
                ErrorReasons.BACKUP_CONTROL_UNAVAILABLE);
    }

    private static UnprocessableException invalidRequest(List<Violation> violations) {
        List<Map<String, Object>> asMaps = new ArrayList<>();
        for (Violation violation : violations) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("field", violation.field());
            item.put("message", violation.message());
            asMaps.add(item);
        }
        return new UnprocessableException("請求欄位未通過檢查（" + violations.size() + " 項）",
                BackupJobService.INVALID_REQUEST, List.of(), violations, Map.of("violations", asMaps));
    }

    /** DB 列 → 檢視；非 ADMIN 遮掉觸發者與輸出尾段；ADMIN 的尾段再遮罩一次、取最後 2000 字元。 */
    private static JobView view(Job job, boolean admin) {
        return new JobView(job.id().toString(), job.type(), job.status().name(), job.requestedAt(), job.startedAt(),
                job.finishedAt(), seconds(job.startedAt(), job.finishedAt()), job.exitCode(), job.reason(),
                admin ? job.requestedBy() : null,
                admin ? BackupMasker.maskedTail(job.detail(), BackupMasker.TAIL_MAX) : null);
    }

    // ── 小工具 ────────────────────────────────────────────────────────────────────────────────

    static String iso(Instant instant) {
        return instant == null ? null : instant.toString();
    }

    /** 兩個瞬間相差的整數秒（無條件捨去）；任一為 null 回 null。 */
    static Integer seconds(Instant from, Instant to) {
        if (from == null || to == null) {
            return null;
        }
        return (int) Math.max(0, Duration.between(from, to).getSeconds());
    }

    // ══════════════════════════════════════════════════════════════════════════════════════════
    // 以下是控制面匯出檔的讀取、分類與解讀（總覽、觸發、對帳共用；本類別的實作細節，不是獨立元件）
    // ══════════════════════════════════════════════════════════════════════════════════════════

    /** 一份 pgBackRest 備份（info.json 的 {@code info[].backup[]}）。 */
    record Backup(String kind, String label, int repoKey, Instant start, Instant stop, Long databaseSize, Long repoSize,
                  String prior, boolean error) {
    }

    /** 一個離站邏輯備份物件（logical.json 的 {@code objects[]}）。 */
    record Logical(String name, long size, Instant modified) {
    }

    /** schedule.json 的一條。 */
    record ScheduleEntry(String job, String cron) {
    }

    /** jobs/&lt;job&gt;.json 的一份狀態；{@code startedAt} 一律非 null（寫檔端保證）。 */
    record JobState(String trigger, String status, Integer rc, String reason, Instant startedAt, Instant finishedAt,
                    String detailTail, String note, Instant lastSuccessAt) {
    }

    /** 心跳（供對帳判斷控制面是否存活）。 */
    record Heartbeat(boolean present, Instant ts, boolean lockHeld, boolean fresh) {
    }

    /** 一次讀取的結果。{@code reason} 為 null＝控制面正常。 */
    static final class Export {

        final Instant now;
        String reason;
        Integer heartbeatAgeSeconds;
        boolean heartbeatFresh;
        boolean lockHeld;
        Instant heartbeatTs;
        Instant generatedAt;
        boolean infoOk;
        boolean logicalOk;
        final List<Backup> backups = new ArrayList<>();
        final List<Integer> repoKeys = new ArrayList<>();
        final List<Object> repos = new ArrayList<>();
        Map<String, Object> retention;
        final List<Logical> logical = new ArrayList<>();
        String tz;
        final List<ScheduleEntry> entries = new ArrayList<>();
        final Map<String, JobState> jobStates = new LinkedHashMap<>();

        Export(Instant now) {
            this.now = now;
        }

        /** 前三類 reason：所有資料區塊為 null。 */
        boolean blocked() {
            return NOT_CONFIGURED.equals(reason) || SCHEMA_MISMATCH.equals(reason) || EXPORT_UNREADABLE.equals(reason);
        }

        Long exportAgeSeconds() {
            return generatedAt == null ? null : Math.max(0, Duration.between(generatedAt, now).getSeconds());
        }

        String cronOf(String job) {
            return entries.stream().filter(entry -> entry.job.equals(job)).map(entry -> entry.cron).findFirst().orElse(null);
        }

        /**
         * 工作的狀態：沒有狀態檔＝{@code no_run}；狀態檔是 running 而心跳新鮮、心跳 {@code ts} 不早於工作開始（早於＝鎖資訊過時，不下結論）、
         * 且鎖未持有 ⇒ 防禦性導出 {@code interrupted}；心跳過期時不下結論（保持 running）。
         */
        String derivedStatus(JobState state) {
            if (state == null) {
                return "no_run";
            }
            if ("running".equals(state.status) && heartbeatFresh && heartbeatTs != null
                    && !heartbeatTs.isBefore(state.startedAt) && !lockHeld) {
                return "interrupted";
            }
            return state.status;
        }

        /** 各已設定 repo 中，符合 {@code kinds} 的最近一份備份的 stop（沒有符合者放 null）；info 不可用或無 stanza 回空清單。 */
        List<Instant> repoLatest(Set<String> kinds) {
            if (!infoOk || repoKeys.isEmpty()) {
                return List.of();
            }
            List<Instant> latest = new ArrayList<>();
            for (int key : repoKeys) {
                latest.add(backups.stream().filter(b -> b.repoKey == key && kinds.contains(b.kind)).map(b -> b.stop)
                        .max(Instant::compareTo).orElse(null));
            }
            return latest;
        }

        /** 符合 {@code kinds} 的各 repo 備份中 stop 最大者：{@code {label, finishedAt, source}}；沒有（或 info 不可用）回 null。 */
        Map<String, Object> latestBackup(Set<String> kinds) {
            if (!infoOk) {
                return null;
            }
            return backups.stream().filter(b -> kinds.contains(b.kind))
                    .max(Comparator.<Backup, Instant>comparing(b -> b.stop).thenComparing(b -> b.label)).map(b -> {
                        Map<String, Object> latest = new LinkedHashMap<>();
                        latest.put("label", b.label);
                        latest.put("finishedAt", iso(b.stop));
                        latest.put("source", "pgbackrest");
                        return latest;
                    }).orElse(null);
        }
    }

    /** 檔案分類（D-BK-T6）：缺席、可用、損毀（JSON 壞或空檔、I/O 失敗）、schema 不符（頂層不是物件、{@code schema_rev} 不是整數 1）。 */
    private enum Kind { MISSING, OK, CORRUPT, SCHEMA }

    private record Loaded(Kind kind, Map<String, Object> value) {
    }

    /** 內容與 schema 不合（在 {@code schema_rev} 正確的檔案內）：一律歸 {@code schema_mismatch}。 */
    private static final class SchemaProblem extends RuntimeException {
        private static final long serialVersionUID = 1L;

        SchemaProblem(String message) {
            super(message);
        }
    }

    /** 讀取、分類並解讀控制面匯出檔。無狀態；總覽、觸發、對帳各自建一個。 */
    static final class ExportReader {

        private static final JsonMapper JSON = JsonMapper.builder().build();

        private final BackupSettings settings;
        private final BackupControlPort control;
        private final BackupClock clock;

        ExportReader(BackupSettings settings, BackupControlPort control, BackupClock clock) {
            this.settings = settings;
            this.control = control;
            this.clock = clock;
        }

        /** 讀 8 個檔、決定 {@code reason}（優先序見類別說明）；<b>讀完所有檔才下結論</b>（兩類並存時 schema 優先，與讀檔先後無關）。 */
        Export read() {
            Export export = new Export(clock.instant());
            if (settings.exportDir() == null) {
                export.reason = NOT_CONFIGURED;
                return export;
            }
            boolean schemaBad = false;
            boolean unreadable = false;
            Loaded info = load("export/info.json");
            Loaded logical = load("export/logical.json");
            Loaded schedule = load("export/schedule.json");
            Loaded heartbeat = load("export/heartbeat");
            Map<String, Loaded> jobFiles = new LinkedHashMap<>();
            for (String job : JOBS) {
                jobFiles.put(job, load("export/jobs/" + job + ".json"));
            }
            List<Loaded> all = new ArrayList<>(List.of(info, logical, schedule, heartbeat));
            all.addAll(jobFiles.values());
            for (Loaded loaded : all) {
                schemaBad |= loaded.kind == Kind.SCHEMA;
                unreadable |= loaded.kind == Kind.CORRUPT;
            }
            unreadable |= info.kind == Kind.MISSING || logical.kind == Kind.MISSING || schedule.kind == Kind.MISSING;

            // 逐檔各自解讀（某檔損毀不阻止其他檔被檢查：schema 不符的優先序最高）
            schemaBad |= interpret(info, () -> interpretInfo(info.value, export));
            schemaBad |= interpret(logical, () -> interpretLogical(logical.value, export));
            schemaBad |= interpret(schedule, () -> interpretSchedule(schedule.value, export));
            schemaBad |= interpret(heartbeat, () -> interpretHeartbeat(heartbeat.value, export));
            for (Map.Entry<String, Loaded> entry : jobFiles.entrySet()) {
                Loaded file = entry.getValue();
                schemaBad |= interpret(file, () -> export.jobStates.put(entry.getKey(), interpretJob(file.value)));
            }

            if (schemaBad) {
                export.reason = SCHEMA_MISMATCH;
            } else if (unreadable) {
                export.reason = EXPORT_UNREADABLE;
            } else if (heartbeat.kind == Kind.MISSING || export.heartbeatAgeSeconds == null
                    || export.heartbeatAgeSeconds > HEARTBEAT_STALE_SECONDS) {
                export.reason = RUNNER_OFFLINE;
            }
            return export;
        }

        /** 只讀心跳（對帳判斷控制面是否存活）：缺席、損毀、schema 不符一律視為不新鮮。 */
        Heartbeat heartbeat() {
            Instant now = clock.instant();
            Loaded loaded = load("export/heartbeat");
            if (loaded.kind != Kind.OK) {
                return new Heartbeat(false, null, false, false);
            }
            try {
                Instant ts = instant(loaded.value.get("ts"), "heartbeat.ts");
                boolean held = bool(loaded.value.get("lock_held"), "heartbeat.lock_held");
                long age = Math.max(0, Duration.between(ts, now).getSeconds());
                return new Heartbeat(true, ts, held, age <= HEARTBEAT_STALE_SECONDS);
            } catch (SchemaProblem e) {
                return new Heartbeat(false, null, false, false);
            }
        }

        private static boolean interpret(Loaded loaded, Runnable action) {
            if (loaded.kind != Kind.OK) {
                return false;
            }
            try {
                action.run();
                return false;
            } catch (SchemaProblem e) {
                LOG.warn("控制面匯出檔內容不合（歸 schema_mismatch）：{}", BackupMasker.mask(e.getMessage()));
                return true;
            }
        }

        private Loaded load(String relativePath) {
            Optional<String> text;
            try {
                text = control.read(relativePath);
            } catch (UncheckedIOException e) {
                LOG.warn("控制面檔案讀取失敗（歸 export_unreadable）：{}：{}", relativePath, BackupMasker.mask(e.toString()));
                return new Loaded(Kind.CORRUPT, null);
            }
            if (text.isEmpty()) {
                return new Loaded(Kind.MISSING, null);
            }
            Object parsed;
            try {
                if (text.get().isBlank()) {
                    return new Loaded(Kind.CORRUPT, null);
                }
                parsed = JSON.readValue(text.get(), Object.class);
            } catch (RuntimeException e) {
                return new Loaded(Kind.CORRUPT, null);
            }
            if (!(parsed instanceof Map<?, ?> map)) {
                return new Loaded(Kind.SCHEMA, null);
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> object = (Map<String, Object>) map;
            return isRevOne(object.get("schema_rev")) ? new Loaded(Kind.OK, object) : new Loaded(Kind.SCHEMA, null);
        }

        private static boolean isRevOne(Object value) {
            return value instanceof Integer i && i == 1 || value instanceof Long l && l == 1L
                    || value instanceof BigInteger b && b.equals(BigInteger.ONE);
        }

        // ── 各檔的解讀 ──────────────────────────────────────────────────────────────────────

        private static void interpretInfo(Map<String, Object> map, Export export) {
            export.generatedAt = instant(map.get("generated_at"), "info.generated_at");
            export.infoOk = bool(map.get("ok"), "info.ok");
            if (!export.infoOk) {
                return;
            }
            List<Object> stanzas = list(map.get("info"), "info.info");
            Map<Integer, Map<String, Object>> endpoints = new LinkedHashMap<>();
            for (Object item : list(map.get("repos"), "info.repos")) {
                Map<String, Object> repo = object(item, "info.repos[]");
                int key = intValue(repo.get("repo"), "info.repos[].repo");
                str(repo.get("type"), "info.repos[].type");
                Map<String, Object> endpoint = new LinkedHashMap<>();
                endpoint.put("endpointHost", strOrNull(repo.get("endpoint_host"), "info.repos[].endpoint_host"));
                endpoint.put("local", bool(repo.get("local"), "info.repos[].local"));
                endpoints.put(key, endpoint);
            }
            for (Object stanza : stanzas) {
                Object backups = object(stanza, "info[]").get("backup");
                for (Object item : backups == null ? List.of() : list(backups, "info[].backup")) {
                    export.backups.add(backup(object(item, "info[].backup[]")));
                }
            }
            if (!stanzas.isEmpty()) {
                Object repoList = object(stanzas.get(0), "info[0]").get("repo");
                for (Object item : repoList == null ? List.of() : list(repoList, "info[0].repo")) {
                    Map<String, Object> repo = object(item, "info[0].repo[]");
                    int key = intValue(repo.get("key"), "info[0].repo[].key");
                    Map<String, Object> status = object(repo.get("status"), "info[0].repo[].status");
                    Map<String, Object> endpoint = endpoints.get(key);
                    if (endpoint == null) {
                        throw new SchemaProblem("info.repos 缺 repo " + key + " 的端點資訊");
                    }
                    Map<String, Object> api = new LinkedHashMap<>();
                    api.put("repo", key);
                    api.put("endpointHost", endpoint.get("endpointHost"));
                    api.put("local", endpoint.get("local"));
                    api.put("statusCode", intValue(status.get("code"), "info[0].repo[].status.code"));
                    api.put("statusMessage", str(status.get("message"), "info[0].repo[].status.message"));
                    export.repos.add(api);
                    export.repoKeys.add(key);
                }
            }
            Object retention = map.get("retention");
            if (retention != null) {
                export.retention = retention(object(retention, "info.retention"));
            }
        }

        private static Backup backup(Map<String, Object> b) {
            Map<String, Object> timestamp = object(b.get("timestamp"), "backup.timestamp");
            Map<String, Object> database = object(b.get("database"), "backup.database");
            Map<String, Object> info = object(b.get("info"), "backup.info");
            Map<String, Object> repository = object(info.get("repository"), "backup.info.repository");
            return new Backup(str(b.get("type"), "backup.type"), str(b.get("label"), "backup.label"),
                    intValue(database.get("repo-key"), "backup.database.repo-key"),
                    Instant.ofEpochSecond(longValue(timestamp.get("start"), "backup.timestamp.start")),
                    Instant.ofEpochSecond(longValue(timestamp.get("stop"), "backup.timestamp.stop")),
                    longValue(info.get("size"), "backup.info.size"), longValue(repository.get("size"), "backup.info.repository.size"),
                    strOrNull(b.get("prior"), "backup.prior"), Boolean.TRUE.equals(b.get("error")));
        }

        private static Map<String, Object> retention(Map<String, Object> raw) {
            Map<String, Object> retention = new LinkedHashMap<>();
            for (String repo : List.of("repo1", "repo2")) {
                Object value = raw.get(repo);
                Map<String, Object> limits = new LinkedHashMap<>();
                Map<String, Object> source = value == null ? Map.of() : object(value, "retention." + repo);
                limits.put("full", intOrNull(source.get("full"), "retention." + repo + ".full"));
                limits.put("diff", intOrNull(source.get("diff"), "retention." + repo + ".diff"));
                retention.put(repo, limits);
            }
            retention.put("logicalDays", intOrNull(raw.get("logical_days"), "retention.logical_days"));
            return retention;
        }

        private static void interpretLogical(Map<String, Object> map, Export export) {
            export.logicalOk = bool(map.get("ok"), "logical.ok");
            if (!export.logicalOk) {
                return;
            }
            for (Object item : list(map.get("objects"), "logical.objects")) {
                Map<String, Object> object = object(item, "logical.objects[]");
                export.logical.add(new Logical(str(object.get("name"), "logical.objects[].name"),
                        longValue(object.get("size"), "logical.objects[].size"),
                        instant(object.get("modified"), "logical.objects[].modified")));
            }
        }

        private static void interpretSchedule(Map<String, Object> map, Export export) {
            String tz = str(map.get("tz"), "schedule.tz");
            try {
                ZoneId.of(tz);
            } catch (DateTimeException e) {
                throw new SchemaProblem("schedule.tz 不是合法時區：" + tz);
            }
            export.tz = tz;
            for (Object item : list(map.get("entries"), "schedule.entries")) {
                Map<String, Object> entry = object(item, "schedule.entries[]");
                export.entries.add(new ScheduleEntry(str(entry.get("job"), "schedule.entries[].job"),
                        str(entry.get("cron"), "schedule.entries[].cron")));
            }
        }

        private static void interpretHeartbeat(Map<String, Object> map, Export export) {
            Instant ts = instant(map.get("ts"), "heartbeat.ts");
            export.lockHeld = bool(map.get("lock_held"), "heartbeat.lock_held");
            export.heartbeatTs = ts;
            long age = Math.max(0, Duration.between(ts, export.now).getSeconds());
            export.heartbeatAgeSeconds = (int) Math.min(Integer.MAX_VALUE, age);
            export.heartbeatFresh = age <= HEARTBEAT_STALE_SECONDS;
        }

        private static JobState interpretJob(Map<String, Object> map) {
            Map<String, Object> last = object(map.get("last"), "job.last");
            String status = str(last.get("status"), "job.last.status");
            if (!Set.of("running", "succeeded", "failed", "interrupted").contains(status)) {
                throw new SchemaProblem("job.last.status 不在值域內：" + status);
            }
            String trigger = str(last.get("trigger"), "job.last.trigger");
            if (!Set.of("scheduled", "manual").contains(trigger)) {
                throw new SchemaProblem("job.last.trigger 不在值域內：" + trigger);
            }
            Object finished = last.get("finished_at");
            Object success = map.get("last_success_at");
            Object tail = last.get("detail_tail");
            return new JobState(trigger, status, intOrNull(last.get("rc"), "job.last.rc"),
                    strOrNull(last.get("reason"), "job.last.reason"), instant(last.get("started_at"), "job.last.started_at"),
                    finished == null ? null : instant(finished, "job.last.finished_at"), tail == null ? "" : str(tail, "job.last.detail_tail"),
                    strOrNull(last.get("note"), "job.last.note"), success == null ? null : instant(success, "job.last_success_at"));
        }

        // ── 型別檢查（不合一律 SchemaProblem）────────────────────────────────────────────────

        @SuppressWarnings("unchecked")
        private static Map<String, Object> object(Object value, String what) {
            if (value instanceof Map<?, ?> map) {
                return (Map<String, Object>) map;
            }
            throw new SchemaProblem(what + " 不是物件");
        }

        @SuppressWarnings("unchecked")
        private static List<Object> list(Object value, String what) {
            if (value instanceof List<?> list) {
                return (List<Object>) list;
            }
            throw new SchemaProblem(what + " 不是陣列");
        }

        private static String str(Object value, String what) {
            if (value instanceof String text) {
                return text;
            }
            throw new SchemaProblem(what + " 不是字串");
        }

        private static String strOrNull(Object value, String what) {
            return value == null ? null : str(value, what);
        }

        private static boolean bool(Object value, String what) {
            if (value instanceof Boolean flag) {
                return flag;
            }
            throw new SchemaProblem(what + " 不是布林");
        }

        private static long longValue(Object value, String what) {
            if (value instanceof Integer || value instanceof Long) {
                return ((Number) value).longValue();
            }
            if (value instanceof BigInteger big && big.bitLength() < 64) {
                return big.longValue();
            }
            throw new SchemaProblem(what + " 不是整數");
        }

        private static int intValue(Object value, String what) {
            long number = longValue(value, what);
            if (number < Integer.MIN_VALUE || number > Integer.MAX_VALUE) {
                throw new SchemaProblem(what + " 超出整數範圍");
            }
            return (int) number;
        }

        private static Integer intOrNull(Object value, String what) {
            return value == null ? null : intValue(value, what);
        }

        private static Instant instant(Object value, String what) {
            String text = str(value, what);
            try {
                return OffsetDateTime.parse(text).toInstant();
            } catch (DateTimeException e) {
                throw new SchemaProblem(what + " 不是 ISO-8601 時間：" + text);
            }
        }
    }
}
