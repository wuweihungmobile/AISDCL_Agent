package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ProjectPurger;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * 軟刪除專案的每日清除排程（契約 §1.6.5，C-3；ADR-001 D19）。<b>預設關閉</b>（{@code console.retention.purge-enabled=false}）：
 * 實體刪除不可逆，部署者必須明確開啟；關閉時 {@link #start()} 什麼都不註冊（有單元測試釘住），軟刪除資料只會累積、不會消失。
 *
 * <p>每次清除：刪除 {@code deleted_at < 現在 − soft-delete-days} 的軟刪除專案及其整棵子資料（<b>只有專案層級</b>，
 * 存活專案內單獨軟刪的目標／任務不清）。每個專案一個交易；單一專案失敗只記 WARN、不影響其他專案；每清掉一個專案落一筆
 * {@code project.purge} 審計（主體 {@code system}）。清除條件與「復原視窗」是同一條線（早於它的專案已不可經 API 復原），
 * 所以清除不會刪到仍可復原的資料。時鐘可注入，測試不必等一天。
 */
@Component
public class SoftDeletePurge {

    private static final Logger LOG = LoggerFactory.getLogger(SoftDeletePurge.class);

    /** 啟動後多久做第一次清除，之後每 24 小時一次（時間由實作決定，契約 §1.6.5）。 */
    static final Duration INITIAL_DELAY = Duration.ofMinutes(10);
    static final Duration INTERVAL = Duration.ofDays(1);

    private final RuntimeSettings settings;
    private final ProjectPurger purger;
    private final AuditTrail audit;
    private final Clock clock;
    private final TransactionTemplate tx;
    private ScheduledExecutorService scheduler;

    public SoftDeletePurge(RuntimeSettings settings, ProjectPurger purger, AuditTrail audit, Clock clock,
                           PlatformTransactionManager transactions) {
        this.settings = settings;
        this.purger = purger;
        this.audit = audit;
        this.clock = clock;
        this.tx = new TransactionTemplate(transactions);
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onReady() {
        start();
    }

    /**
     * 依設定註冊每日排程；回傳是否真的註冊了。{@code purge-enabled=false}（預設）不註冊任何東西；重複呼叫只註冊一次。
     * 整合測試 profile 沒有特別關閉它——預設值本來就是關。
     */
    public synchronized boolean start() {
        if (!settings.purgeEnabled()) {
            LOG.info("軟刪除清除排程未啟用（console.retention.purge-enabled=false）：軟刪除資料只會累積、不會被實體刪除");
            return false;
        }
        if (scheduler != null) {
            return true;
        }
        scheduler = Executors.newSingleThreadScheduledExecutor(task -> {
            Thread thread = new Thread(task, "soft-delete-purge");
            thread.setDaemon(true);
            return thread;
        });
        scheduler.scheduleWithFixedDelay(this::runOnceQuietly, INITIAL_DELAY.toMillis(), INTERVAL.toMillis(),
                TimeUnit.MILLISECONDS);
        LOG.info("軟刪除清除排程已啟用：保留 {} 天，每 {} 小時清一次（首次 {} 分鐘後）", settings.softDeleteRetentionDays(),
                INTERVAL.toHours(), INITIAL_DELAY.toMinutes());
        return true;
    }

    /** 排程是否已註冊（測試用）。 */
    synchronized boolean isScheduled() {
        return scheduler != null;
    }

    @PreDestroy
    public synchronized void stop() {
        if (scheduler != null) {
            scheduler.shutdownNow();
            scheduler = null;
        }
    }

    /**
     * 排程實際呼叫的入口：本輪任何例外都只記 WARN、不得外洩——{@code scheduleWithFixedDelay} 的任務一旦拋出例外，
     * 之後的每一輪都會被取消，清除排程就此靜默死亡（套件可見，測試直接呼叫）。
     */
    void runOnceQuietly() {
        try {
            runOnce();
        } catch (RuntimeException e) {
            LOG.warn("軟刪除清除排程本輪失敗（下一輪會再試）：{}", e.toString());
        }
    }

    /**
     * 清除一輪（排程與測試共用）：每個過期專案一個交易，單一專案失敗只記 WARN。
     *
     * @return 本輪實際清掉的專案數
     */
    public int runOnce() {
        int days = settings.softDeleteRetentionDays();
        Instant cutoff = clock.instant().minus(Duration.ofDays(days));
        List<UUID> expired = purger.findExpired(cutoff);
        int purged = 0;
        for (UUID projectId : expired) {
            try {
                Boolean removed = tx.execute(status -> purger.purge(projectId));
                if (Boolean.TRUE.equals(removed)) {
                    purged++;
                    audit.system("project.purge", "project", projectId.toString(), Map.of("retentionDays", days));
                }
            } catch (RuntimeException e) {
                LOG.warn("清除專案 {} 失敗（整個專案原封不動，不影響其他專案）：{}", projectId, e.toString());
            }
        }
        if (!expired.isEmpty()) {
            LOG.info("軟刪除清除：逾 {} 天的專案 {} 個，已清除 {} 個", days, expired.size(), purged);
        }
        return purged;
    }
}
