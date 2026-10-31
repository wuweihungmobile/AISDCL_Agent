package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.BackupClock;
import com.aisdlc.console.application.port.out.BackupControlPort;
import com.aisdlc.console.application.port.out.BackupJobRepository;
import com.aisdlc.console.application.port.out.BackupJobRepository.Job;
import com.aisdlc.console.application.port.out.BackupJobRepository.Status;
import com.aisdlc.console.application.port.out.BackupSettings;
import com.aisdlc.console.domain.model.backup.BackupJobReason;
import com.aisdlc.console.domain.model.backup.BackupMasker;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

import java.io.UncheckedIOException;
import java.math.BigInteger;
import java.time.DateTimeException;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * 手動工作的終態對帳（TCS-SysAdminBackup-20261027 R-BK-34、R-BK-36、R-BK-56；sidecar 的 {@code results/<id>.json} → {@code console.backup_jobs}）。
 * 排程輪詢（{@code reconcile-interval-ms}）加每次 GET 順帶，可並行：資料庫的條件式 UPDATE 讓並發的兩方只有一方生效，
 * <b>只有「更新到列」的那一次</b>在交易提交之後才補一筆 {@code backup.finished} 系統審計（沒有更新到列＝別人已處理，不再補）。
 *
 * <p>映射（sidecar 的 results 詞彙 → 資料庫）：{@code running} → 該列 RUNNING（撿取）；{@code succeeded} → SUCCEEDED；{@code failed} → FAILED
 * （{@code reason} 限 {@code script_failed}／{@code interrupted}／{@code lock_timeout}，<b>詞彙外一律 {@code script_failed}</b>）；
 * {@code rejected} 的 {@code busy}／{@code rejected_invalid} → REJECTED、{@code expired} → EXPIRED。輸出尾段再遮罩一次（不信任 sidecar）。
 *
 * <p>兩個 console-api 自己的收尾：<b>過期</b>——runner 存活（心跳新鮮）時由 runner 對過期請求寫 {@code rejected／expired}、這裡只對帳；runner 離線
 * （心跳過期）且 QUEUED 逾 {@code request-ttl-seconds}（嚴格大於）才由這裡以條件式 UPDATE 標 EXPIRED；<b>絕對上限</b>——不論心跳，QUEUED 逾
 * 2 倍 TTL 仍無 results 者同樣標 EXPIRED（results 不可寫時 runner 不處理請求，否則該列永遠 QUEUED 而鎖死唯一索引）；<b>逾時</b>——RUNNING 逾
 * {@code job-max-seconds}（嚴格大於）<b>且</b>心跳過期才標 FAILED／{@code timeout}（控制面有回應＝長驗證不算逾時）。
 *
 * <p>本輪任何例外都只記 WARN、不得外洩（{@link #runOnceQuietly()}）：排程一旦丟出例外，之後每一輪都會被取消、對帳就此靜默死亡。
 * 啟動時另清請求卷內逾 24 小時的殘檔（只記 WARN；sidecar 對該卷是唯讀掛載，殘檔只能由這一端清）。
 */
@Component
public class BackupJobReconciler {

    private static final Logger LOG = LoggerFactory.getLogger(BackupJobReconciler.class);
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final Duration STALE_REQUEST_AGE = Duration.ofHours(24);
    private static final Set<String> FAILED_REASONS = Set.of(BackupJobReason.SCRIPT_FAILED.value(),
            BackupJobReason.INTERRUPTED.value(), BackupJobReason.LOCK_TIMEOUT.value());

    private final BackupSettings settings;
    private final BackupControlPort control;
    private final BackupJobRepository jobs;
    private final BackupClock clock;
    private final AuditTrail audit;
    private final BackupQueryService.ExportReader reader;
    private ScheduledExecutorService scheduler;

    BackupJobReconciler(BackupSettings settings, BackupControlPort control, BackupJobRepository jobs, BackupClock clock,
                        AuditTrail audit) {
        this.settings = settings;
        this.control = control;
        this.jobs = jobs;
        this.clock = clock;
        this.audit = audit;
        this.reader = new BackupQueryService.ExportReader(settings, control, clock);
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onReady() {
        cleanStaleRequests();
        start();
    }

    /** 依設定註冊對帳排程；回傳是否真的註冊了。控制面未設定（任一目錄未設）＝不註冊；重複呼叫只註冊一次。 */
    public synchronized boolean start() {
        if (settings.exportDir() == null || settings.requestDir() == null) {
            LOG.info("備份控制面未設定（console.backup.export-dir／request-dir）：不註冊手動工作的對帳排程");
            return false;
        }
        if (scheduler != null) {
            return true;
        }
        scheduler = Executors.newSingleThreadScheduledExecutor(task -> {
            Thread thread = new Thread(task, "backup-job-reconcile");
            thread.setDaemon(true);
            return thread;
        });
        long interval = settings.reconcileIntervalMs();
        scheduler.scheduleWithFixedDelay(this::runOnceQuietly, interval, interval, TimeUnit.MILLISECONDS);
        LOG.info("備份工作對帳排程已啟用：每 {} 毫秒一次", interval);
        return true;
    }

    @PreDestroy
    public synchronized void stop() {
        if (scheduler != null) {
            scheduler.shutdownNow();
            scheduler = null;
        }
    }

    /** 啟動時清請求卷內逾 24 小時的殘檔；只記 WARN，失敗不影響啟動。 */
    void cleanStaleRequests() {
        if (settings.requestDir() == null) {
            return;
        }
        try {
            int removed = control.deleteStaleRequests(clock.instant().minus(STALE_REQUEST_AGE));
            if (removed > 0) {
                LOG.warn("已清除請求卷內 {} 份逾 24 小時的殘留請求檔", removed);
            }
        } catch (RuntimeException e) {
            LOG.warn("清除請求卷殘檔失敗（不影響啟動）：{}", BackupMasker.mask(e.toString()));
        }
    }

    /** 排程與 GET 順帶實際呼叫的入口：本輪任何例外只記 WARN。 */
    void runOnceQuietly() {
        reconcileQuietly();
    }

    /** 同上（總覽與工作端點的 GET 順帶呼叫）。 */
    void reconcileQuietly() {
        try {
            reconcileOnce();
        } catch (RuntimeException e) {
            LOG.warn("備份工作對帳本輪失敗（下一輪會再試）：{}", BackupMasker.mask(e.toString()));
        }
    }

    /**
     * 對帳一輪（排程、GET 順帶與測試共用）。
     *
     * @return 本輪實際更新到列的次數
     */
    public int reconcileOnce() {
        if (settings.exportDir() == null) {
            return 0;
        }
        List<Job> active = jobs.findActive();
        if (active.isEmpty()) {
            return 0;
        }
        Instant now = clock.instant();
        BackupQueryService.Heartbeat heartbeat = reader.heartbeat();
        int changed = 0;
        for (Job row : active) {
            try {
                changed += reconcile(row, now, heartbeat);
            } catch (RuntimeException e) {
                LOG.warn("對帳工作 {} 失敗（其他工作照常）：{}", row.id(), BackupMasker.mask(e.toString()));
            }
        }
        return changed;
    }

    private int reconcile(Job row, Instant now, BackupQueryService.Heartbeat heartbeat) {
        Optional<Map<String, Object>> result = readResult(row);
        if (result.isPresent()) {
            Map<String, Object> r = result.get();
            Object status = r.get("status");
            if ("succeeded".equals(status)) {
                return finish(row, Status.SUCCEEDED, intOrNull(r.get("rc")), null, r, now);
            }
            if ("failed".equals(status)) {
                Object reason = r.get("reason");
                String checked = reason instanceof String text && FAILED_REASONS.contains(text) ? text
                        : BackupJobReason.SCRIPT_FAILED.value();
                return finish(row, Status.FAILED, intOrNull(r.get("rc")), checked, r, now);
            }
            if ("rejected".equals(status)) {
                if (BackupJobReason.EXPIRED.value().equals(r.get("reason"))) {
                    return finish(row, Status.EXPIRED, null, BackupJobReason.EXPIRED.value(), r, now);
                }
                String reason = BackupJobReason.BUSY.value().equals(r.get("reason")) ? BackupJobReason.BUSY.value()
                        : BackupJobReason.REJECTED_INVALID.value();
                return finish(row, Status.REJECTED, null, reason, r, now);
            }
            if ("running".equals(status) && row.status() == Status.QUEUED) {
                Instant picked = instantOr(r.get("started_at"), now);
                return jobs.markRunningIfQueued(row.id(), picked) ? 1 : 0;
            }
        } else if (row.status() == Status.QUEUED) {
            return expireIfDue(row, now, heartbeat);
        }
        return row.status() == Status.RUNNING ? timeoutIfDue(row, now, heartbeat) : 0;
    }

    /** QUEUED、沒有 results：runner 離線且逾 TTL，或不論心跳逾 2 倍 TTL ⇒ 條件式標 EXPIRED。 */
    private int expireIfDue(Job row, Instant now, BackupQueryService.Heartbeat heartbeat) {
        long ttl = settings.requestTtlSeconds();
        boolean pastTtl = now.isAfter(row.requestedAt().plusSeconds(ttl));
        boolean pastAbsolute = now.isAfter(row.requestedAt().plusSeconds(2 * ttl));
        if (!(pastTtl && !heartbeat.fresh()) && !pastAbsolute) {
            return 0;
        }
        if (!jobs.markExpiredIfQueued(row.id(), now)) {
            return 0;
        }
        afterFinish(row, Status.EXPIRED, BackupJobReason.EXPIRED.value(), null);
        return 1;
    }

    /** RUNNING 逾 job-max-seconds（嚴格大於）且心跳過期 ⇒ FAILED／timeout。 */
    private int timeoutIfDue(Job row, Instant now, BackupQueryService.Heartbeat heartbeat) {
        if (row.startedAt() == null || heartbeat.fresh()
                || !now.isAfter(row.startedAt().plusSeconds(settings.jobMaxSeconds()))) {
            return 0;
        }
        if (!jobs.markTerminalIfActive(row.id(), Status.FAILED, null, BackupJobReason.TIMEOUT.value(), null, now, "")) {
            return 0;
        }
        afterFinish(row, Status.FAILED, BackupJobReason.TIMEOUT.value(), null);
        return 1;
    }

    private int finish(Job row, Status status, Integer exitCode, String reason, Map<String, Object> r, Instant now) {
        Object tail = r.get("detail_tail");
        String detail = BackupMasker.maskedTail(tail instanceof String text ? text : "", BackupMasker.TAIL_MAX);
        Instant started = instantOr(r.get("started_at"), null);
        Instant finished = instantOr(r.get("finished_at"), now);
        if (!jobs.markTerminalIfActive(row.id(), status, exitCode, reason, started, finished, detail)) {
            return 0;
        }
        afterFinish(row, status, reason, exitCode);
        return 1;
    }

    /** 更新到列之後（交易已提交）才補審計與刪請求檔；審計的 details <b>不含</b>輸出尾段。 */
    private void afterFinish(Job row, Status status, String reason, Integer exitCode) {
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("type", row.type());
        details.put("status", status.name());
        if (reason != null) {
            details.put("reason", reason);
        }
        if (exitCode != null) {
            details.put("exitCode", exitCode);
        }
        audit.system("backup.finished", "backup", row.id().toString(), details);
        control.deleteRequest(row.id());
    }

    /** 讀 results；缺席、讀不出、壞檔、id 不符一律當作「尚無結果」（壞檔不能讓對帳卡死）。 */
    private Optional<Map<String, Object>> readResult(Job row) {
        Optional<String> text;
        try {
            text = control.read("results/" + row.id() + ".json");
        } catch (UncheckedIOException e) {
            LOG.warn("results/{}.json 讀取失敗：{}", row.id(), BackupMasker.mask(e.toString()));
            return Optional.empty();
        }
        if (text.isEmpty() || text.get().isBlank()) {
            return Optional.empty();
        }
        try {
            Object parsed = JSON.readValue(text.get(), Object.class);
            if (parsed instanceof Map<?, ?> map && isRevOne(map.get("schema_rev")) && row.id().toString().equals(map.get("id"))) {
                @SuppressWarnings("unchecked")
                Map<String, Object> object = (Map<String, Object>) map;
                return Optional.of(object);
            }
        } catch (RuntimeException e) {
            LOG.warn("results/{}.json 不是合法 JSON：{}", row.id(), BackupMasker.mask(e.toString()));
        }
        return Optional.empty();
    }

    private static boolean isRevOne(Object value) {
        return value instanceof Integer i && i == 1 || value instanceof Long l && l == 1L
                || value instanceof BigInteger b && b.equals(BigInteger.ONE);
    }

    private static Integer intOrNull(Object value) {
        return value instanceof Integer || value instanceof Long ? Integer.valueOf(((Number) value).intValue()) : null;
    }

    private static Instant instantOr(Object value, Instant fallback) {
        if (value instanceof String text) {
            try {
                return OffsetDateTime.parse(text).toInstant();
            } catch (DateTimeException e) {
                return fallback;
            }
        }
        return fallback;
    }
}
