package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeEvent;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.Supplier;

/**
 * 事件消費者（契約 §3.5.4）：每個活躍 run 一條虛擬執行緒，讀 Bridge 的事件串流、逐則交給 {@link RunEventProcessor}，
 * 交易提交後把框架發給前端（{@link RunEventHub}）並執行 {@code :pause} 這類動作。
 *
 * <ul>
 *   <li><b>位移存資料庫</b>：{@code execution_runs.console_last_seq}（與事件處理同一交易推進），console-api 重啟不丟事件；</li>
 *   <li><b>重連</b>：連線失敗、閒置逾 45 秒（{@link RuntimeSettings#consumerIdleTimeout}）都視為斷線，指數退避 1→30 秒，
 *       以最後已處理的 seq 為 {@code after}；重連時先用 {@code GET …/events} 分頁回補缺口，再接串流（Bridge 的串流本身也會先重播
 *       {@code after} 之後的事件，所以兩者重疊處由 {@code seq ≤ console_last_seq} 的冪等略過）；</li>
 *   <li><b>Bridge 暫時不可達</b>：不結束，同一次中斷只對前端送一則不帶 {@code id:} 的 {@code BRIDGE_UNREACHABLE} 告警；
 *       Bridge 回 404 {@code run_not_found} 則送 {@code BRIDGE_RUN_UNKNOWN} 告警後結束（狀態欄由 Bridge 擁有，DB 不動）；</li>
 *   <li><b>結束</b>：處理完終態 {@code status} 事件（含其衍生的審核項、告警、專案與任務狀態）後結束並通知前端連線關閉；
 *       之後若 restore，由 {@code ExecutionControlService} 重啟。</li>
 * </ul>
 */
@Component
public class RunConsumers {

    private static final Logger LOG = LoggerFactory.getLogger(RunConsumers.class);
    private static final int CATCH_UP_PAGE = 500;

    private final AgentBridge bridge;
    private final ExecutionRunRepository runs;
    private final RunEventProcessor processor;
    private final RunEventHub hub;
    private final RunRegistry registry;
    private final RuntimeSettings settings;
    private final Clock clock;
    private final TransactionTemplate tx;
    private final Map<UUID, Consumer> consumers = new ConcurrentHashMap<>();

    @SuppressWarnings("java:S107")
    public RunConsumers(AgentBridge bridge, ExecutionRunRepository runs, RunEventProcessor processor, RunEventHub hub,
                        RunRegistry registry, RuntimeSettings settings, PlatformTransactionManager transactions,
                        Clock clock) {
        this.bridge = bridge;
        this.runs = runs;
        this.processor = processor;
        this.hub = hub;
        this.registry = registry;
        this.settings = settings;
        this.clock = clock;
        this.tx = new TransactionTemplate(transactions);
    }

    /**
     * 一個 run 的消費者。
     *
     * <p><b>停止時不打斷資料庫呼叫</b>：{@link #work} 在消費者碰資料庫（處理事件、讀位移、發連線告警）的整段期間被持有；
     * {@link RunConsumers#stopAll} 先設 {@code stopping}，再只在<b>拿得到 work 鎖</b>（＝沒有在碰資料庫）時才中斷執行緒。
     * 對正在 JDBC 呼叫中的執行緒下中斷，PostgreSQL 驅動會連同連線一起關掉（{@code Closed by interrupt}），交易被迫回滾。
     */
    private final class Consumer {

        final UUID runId;
        final Thread thread;
        final AtomicBoolean stopping = new AtomicBoolean(false);
        final ReentrantLock work = new ReentrantLock();
        volatile boolean ended;

        Consumer(UUID runId) {
            this.runId = runId;
            this.thread = Thread.ofVirtual().name("run-consumer-" + runId.toString().substring(0, 8))
                    .unstarted(this::loop);
        }

        /** 只在持有該 run 鎖的處理步驟內設為 true：終態事件已處理完。 */
        private final AtomicBoolean terminalSeen = new AtomicBoolean(false);

        /** 在 {@link #work} 鎖內做會碰資料庫的事；已要求停止就不開始（丟 {@link StopRequested}）。 */
        private <T> T working(Supplier<T> action) {
            work.lock();
            try {
                if (stopping.get()) {
                    throw new StopRequested();
                }
                return action.get();
            } finally {
                work.unlock();
            }
        }

        private void working(Runnable action) {
            working(() -> {
                action.run();
                return null;
            });
        }

        void loop() {
            Duration backoff = settings.consumerBackoffInitial();
            boolean firstConnection = true;
            try {
                while (!stopping.get() && !terminalSeen.get()) {
                    try {
                        if (!firstConnection) {
                            catchUp();
                        }
                        firstConnection = false;
                        if (terminalSeen.get()) {
                            break;
                        }
                        bridge.streamEvents(runId, lastSeq(), settings.consumerIdleTimeout(), this::handle);
                        backoff = settings.consumerBackoffInitial();
                        announceRecovered();
                        if (!terminalSeen.get() && !runStillActive()) {
                            break;
                        }
                        if (!terminalSeen.get()) {
                            // 伺服器在 run 還沒結束時就關了串流：稍等再重連，避免對一個一直秒斷的 Bridge 空轉
                            backoff = sleep(settings.consumerBackoffInitial());
                        }
                    } catch (BridgeRejectedException e) {
                        if (e.status() == 404) {
                            announceRunUnknown();
                            break;
                        }
                        LOG.warn("Bridge 拒絕事件串流（run={}）：{} {}", runId, e.status(), e.reason());
                        backoff = sleep(backoff);
                    } catch (UpstreamException e) {
                        announceUnreachable(e);
                        backoff = sleep(backoff);
                    } catch (RuntimeException e) {
                        if (stopping.get()) {
                            break;
                        }
                        LOG.error("事件消費者發生未預期的錯誤（run={}），稍後重試", runId, e);
                        backoff = sleep(backoff);
                    }
                }
            } finally {
                ended = true;
                consumers.remove(runId, this);
                LOG.info("批次 {} 的事件消費者結束（終態＝{}）", runId, terminalSeen.get());
            }
        }

        private int lastSeq() {
            return working(() -> runs.findById(runId).map(ExecutionRun::consoleLastSeq).orElse(0));
        }

        private boolean runStillActive() {
            return working(() -> runs.findById(runId).map(r -> !r.terminal()).orElse(false));
        }

        /** 用 {@code GET …/events} 分頁補齊缺口（重連時）。 */
        private void catchUp() {
            while (!stopping.get() && !terminalSeen.get()) {
                int cursor = lastSeq();
                List<BridgeEvent> page = bridge.listEvents(runId, cursor, CATCH_UP_PAGE);
                if (page.isEmpty()) {
                    return;
                }
                for (BridgeEvent event : page) {
                    handle(event);
                    if (terminalSeen.get()) {
                        return;
                    }
                }
            }
        }

        private void handle(BridgeEvent event) {
            working(() -> registry.locked(runId, () -> {
                RunEventProcessor.Outcome outcome = tx.execute(status -> processor.process(runId, event));
                if (outcome == null) {
                    return;
                }
                hub.publish(runId, outcome.frames());
                for (RunEventProcessor.Action action : outcome.actions()) {
                    execute(action);
                }
                if (outcome.terminal()) {
                    terminalSeen.set(true);
                    hub.complete(runId);
                }
            }));
        }

        private void execute(RunEventProcessor.Action action) {
            if (action instanceof RunEventProcessor.PauseAction pause) {
                try {
                    bridge.pauseRun(runId);
                    LOG.info("已要求暫停批次 {}（原因：{}）", runId, pause.why());
                } catch (BridgeRejectedException e) {
                    LOG.info("Bridge 拒絕暫停批次 {}（{}）：{}", runId, pause.why(), e.reason());
                    if ("gate".equals(pause.why())) {
                        registry.runtime(runId).gatePauseRequested = false;
                    }
                } catch (UpstreamException e) {
                    LOG.warn("暫停批次 {} 失敗（{}）：{}", runId, pause.why(), e.getMessage());
                }
            }
        }

        private void announceUnreachable(UpstreamException cause) {
            working(() -> registry.locked(runId, () -> {
                RunRegistry.Runtime rt = registry.runtime(runId);
                if (!rt.unreachableAnnounced) {
                    rt.unreachableAnnounced = true;
                    LOG.warn("Bridge 暫時無法連線（run={}）：{}", runId, cause.getMessage());
                    hub.publish(runId, List.of(StreamFrames.connectionAlert(lastSeq(), "BRIDGE_UNREACHABLE",
                            "Engine Bridge 暫時無法連線，將自動重試", clock.instant())));
                }
            }));
        }

        private void announceRecovered() {
            working(() -> registry.locked(runId, () -> registry.runtime(runId).unreachableAnnounced = false));
        }

        private void announceRunUnknown() {
            LOG.warn("Bridge 已不認得批次 {}（工作區可能已清除）；DB 不動，結束消費者", runId);
            hub.publish(runId, List.of(StreamFrames.connectionAlert(lastSeq(), "BRIDGE_RUN_UNKNOWN",
                    "Engine Bridge 已無此執行（工作區可能已清除）", clock.instant())));
            hub.complete(runId);
        }

        private Duration sleep(Duration current) {
            try {
                Thread.sleep(current.toMillis());
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                stopping.set(true);
            }
            Duration doubled = current.multipliedBy(2);
            return doubled.compareTo(settings.consumerBackoffMax()) > 0 ? settings.consumerBackoffMax() : doubled;
        }
    }

    /** 處理器要求結束串流（消費者被停止）。 */
    private static final class StopRequested extends RuntimeException {

        private static final long serialVersionUID = 1L;

        StopRequested() {
            super("consumer stopping", null, false, false);
        }
    }

    // ── 對外 ────────────────────────────────────────────────────────────────────

    /** 啟動某個 run 的消費者（已有活著的就不重複啟動）。{@code afterSeq} 僅供日誌；位移一律以 DB 的 {@code console_last_seq} 為準。 */
    public void start(UUID runId, int afterSeq) {
        Consumer fresh = new Consumer(runId);
        Consumer existing = consumers.putIfAbsent(runId, fresh);
        if (existing != null && !existing.ended) {
            return;
        }
        if (existing != null) {
            consumers.replace(runId, existing, fresh);
        }
        LOG.info("啟動批次 {} 的事件消費者（after={}）", runId, afterSeq);
        fresh.thread.start();
    }

    public boolean isRunning(UUID runId) {
        Consumer consumer = consumers.get(runId);
        return consumer != null && !consumer.ended;
    }

    public int activeCount() {
        return (int) consumers.values().stream().filter(c -> !c.ended).count();
    }

    /**
     * 停掉全部消費者（關閉程序、測試清理）；不等待 Bridge。先全部設 {@code stopping}，再逐一在「沒有碰資料庫」時才中斷
     * （見 {@link Consumer}）；最多等 5 秒，逾時仍在碰資料庫的消費者留給它自己在下一個檢查點結束。
     */
    @PreDestroy
    public void stopAll() {
        List<Consumer> all = List.copyOf(consumers.values());
        all.forEach(consumer -> consumer.stopping.set(true));
        long deadline = System.nanoTime() + Duration.ofSeconds(5).toNanos();
        for (Consumer consumer : all) {
            while (consumer.thread.isAlive() && System.nanoTime() < deadline) {
                if (consumer.work.tryLock()) {
                    try {
                        consumer.thread.interrupt();
                    } finally {
                        consumer.work.unlock();
                    }
                }
                try {
                    consumer.thread.join(Duration.ofMillis(25));
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }
        consumers.clear();
    }

    /** 等到沒有任何活著的消費者（測試用）。 */
    public boolean awaitIdle(Duration timeout) {
        long deadline = System.nanoTime() + timeout.toNanos();
        while (System.nanoTime() < deadline) {
            if (activeCount() == 0) {
                return true;
            }
            try {
                Thread.sleep(20);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
        return activeCount() == 0;
    }

    /** 目前某個 run 的消費者是否仍在（含已結束者）——測試判斷用。 */
    public Optional<Boolean> endedState(UUID runId) {
        return Optional.ofNullable(consumers.get(runId)).map(c -> c.ended);
    }
}
