package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunStatus;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.time.Clock;
import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * console-api 啟動後的背景工作（{@link RuntimeSettings#backgroundEnabled}＝false 時整個不啟動，整合測試預設如此）：
 *
 * <ol>
 *   <li><b>啟動探測</b>：立即對 Bridge 探測一次（契約 §3.1），供頂列連線燈；</li>
 *   <li><b>啟動對帳</b>（契約 §3.5.4、§3.4.5 第 6 點）：對每個 DB 狀態為 {@code RUNNING}／{@code PAUSED} 的批次問 Bridge
 *       {@code GET run}——404 → 只寫 WARN 日誌、DB 不動（狀態欄由 Bridge 擁有）；Bridge 不可達 → 仍啟動消費者（由連線層重試）；
 *       可達 → 以 {@code console_last_seq} 為位移啟動消費者。{@code INITIALIZING} 且建立逾 60 秒的列：Bridge 回 404 → 視同補償刪除。
 *       另補一條（契約只寫非終態，這裡多做）：<b>批次在 DB 已是終態、專案卻仍是 {@code EXECUTING}</b>＝console-api 停機期間 Bridge 把 run
 *       跑完了、終態事件沒被消費（Bridge 先寫 DB 欄位、Console 的讀模型靠事件），同樣以 {@code console_last_seq} 為位移補處理；</li>
 *   <li><b>30 秒排程 tick</b>：健康探測，加上純時間型告警規則（{@link TimeRuleEvaluator}）。</li>
 * </ol>
 */
@Component
public class MonitorTicker {

    private static final Logger LOG = LoggerFactory.getLogger(MonitorTicker.class);
    private static final Duration STALE_INITIALIZING = Duration.ofSeconds(60);

    private final RuntimeSettings settings;
    private final ExecutionRunRepository runs;
    private final AgentBridge bridge;
    private final RunConsumers consumers;
    private final BridgeHealthMonitor health;
    private final TimeRuleEvaluator timeRules;
    private final RunLauncher launcher;
    private final Clock clock;
    private ScheduledExecutorService scheduler;

    @SuppressWarnings("java:S107")
    public MonitorTicker(RuntimeSettings settings, ExecutionRunRepository runs, AgentBridge bridge,
                         RunConsumers consumers, BridgeHealthMonitor health, TimeRuleEvaluator timeRules,
                         RunLauncher launcher, Clock clock) {
        this.settings = settings;
        this.runs = runs;
        this.bridge = bridge;
        this.consumers = consumers;
        this.health = health;
        this.timeRules = timeRules;
        this.launcher = launcher;
        this.clock = clock;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onReady() {
        if (!settings.backgroundEnabled()) {
            LOG.info("背景工作未啟用（console.monitor.background-enabled=false）：不做啟動對帳、探測與排程 tick");
            return;
        }
        start();
    }

    /** 啟動對帳與排程（可由測試直接呼叫）。 */
    public synchronized void start() {
        if (scheduler != null) {
            return;
        }
        health.probeNow();
        reconcile();
        scheduler = Executors.newSingleThreadScheduledExecutor(task -> {
            Thread thread = new Thread(task, "monitor-ticker");
            thread.setDaemon(true);
            return thread;
        });
        long millis = Math.max(1, settings.monitorTickInterval().toMillis());
        scheduler.scheduleWithFixedDelay(this::tick, millis, millis, TimeUnit.MILLISECONDS);
    }

    @PreDestroy
    public synchronized void stop() {
        if (scheduler != null) {
            scheduler.shutdownNow();
            scheduler = null;
        }
    }

    /** 一次 tick：健康探測＋時間型告警（排程呼叫；測試可直接呼叫）。 */
    public void tick() {
        try {
            health.probeNow();
            timeRules.evaluateAll();
        } catch (RuntimeException e) {
            LOG.warn("排程 tick 失敗：{}", e.toString());
        }
    }

    /** 啟動對帳（可重複呼叫）。 */
    public void reconcile() {
        for (ExecutionRun run : runs.findByStatuses(List.of(RunStatus.RUNNING, RunStatus.PAUSED))) {
            reconcileOne(run);
        }
        for (ExecutionRun run : runs.findTerminalOfExecutingProjects()) {
            LOG.warn("啟動對帳：批次 {} 在 Bridge 已是終態（{}），但專案仍是 EXECUTING——補處理停機期間漏掉的終態事件", run.id(),
                    run.status());
            reconcileOne(run);
        }
        for (ExecutionRun run : runs.findByStatuses(List.of(RunStatus.INITIALIZING))) {
            if (run.startedAt() != null && Duration.between(run.startedAt(), clock.instant())
                    .compareTo(STALE_INITIALIZING) > 0) {
                reconcileStaleInitializing(run);
            }
        }
    }

    private void reconcileOne(ExecutionRun run) {
        UUID id = run.id();
        try {
            bridge.getRun(id);
            consumers.start(id, run.consoleLastSeq());
        } catch (AgentBridge.BridgeRejectedException e) {
            if (e.status() == 404) {
                LOG.warn("啟動對帳：Bridge 已不認得批次 {}（狀態 {}；工作區可能已清除）——DB 不動，不啟動消費者", id, run.status());
            } else {
                LOG.warn("啟動對帳：Bridge 拒絕查詢批次 {}：{} {}", id, e.status(), e.reason());
            }
        } catch (RuntimeException e) {
            LOG.warn("啟動對帳：Bridge 不可達，仍啟動批次 {} 的消費者（由連線層重試）：{}", id, e.toString());
            consumers.start(id, run.consoleLastSeq());
        }
    }

    private void reconcileStaleInitializing(ExecutionRun run) {
        try {
            bridge.getRun(run.id());
            consumers.start(run.id(), run.consoleLastSeq());
        } catch (AgentBridge.BridgeRejectedException e) {
            if (e.status() == 404) {
                LOG.warn("啟動對帳：INITIALIZING 的批次 {} 在 Bridge 不存在，視同補償刪除", run.id());
                launcher.compensate(run.id());
            }
        } catch (RuntimeException e) {
            LOG.warn("啟動對帳：無法確認 INITIALIZING 批次 {} 的狀態：{}", run.id(), e.toString());
        }
    }
}
