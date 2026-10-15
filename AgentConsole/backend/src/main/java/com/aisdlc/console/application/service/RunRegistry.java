package com.aisdlc.console.application.service;

import com.aisdlc.console.domain.model.execution.BridgeStatus;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.Supplier;

/**
 * 每個 run 的「互斥鎖」與「記憶體內的執行期狀態」。
 *
 * <p>契約 §1.2：同一個 run 的<b>控制操作</b>（pause／resume／cancel／restore／審核）與<b>事件消費／讀模型更新</b>在 console-api 內
 * 以 per-run 互斥鎖序列化，避免還原或取消與事件處理互相踩踏。鎖是可重入的（審核決定在持鎖時會呼叫控制操作）。
 *
 * <p>{@link Runtime} 只放「由事件即可重建、遺失只會讓某個判定退回保守值」的狀態（目前步驟、閘點暫停旗標、重試統計），
 * 不是真相來源——真相在資料庫（{@code console_last_seq}、任務狀態）與 Bridge。
 */
@Component
public class RunRegistry {

    /** 一個 run 在記憶體內的執行期狀態；只在持有該 run 的鎖時存取。 */
    public static final class Runtime {

        /**
         * 最近一則 {@code status} 事件的 Bridge 狀態；null＝尚未看過（由呼叫端以 DB 狀態補）。{@code volatile}：批次列表
         * （{@link #knownBridgeStatus}）不取 per-run 鎖就讀它，只要看得到事件消費者最新寫入的值。
         */
        public volatile BridgeStatus bridgeStatus;
        /** 本輪已為「在該步驟之後停下」呼叫過 {@code :pause} 的步驟位置（每個 run＋步驟只呼叫一次，契約 §3.6.1）。 */
        public final Set<Integer> gatePausedPositions = new HashSet<>();
        /** 目前這次暫停是由審核閘造成的（PAUSED 時據此建審核項；手動 pause 與預算暫停不建）。 */
        public boolean gatePauseRequested;
        /** 目前尚未 COMPLETED／FAILED 的步驟（token 歸因與 ENGINE 日誌標註用）；null＝沒有。 */
        public String currentStepId;
        public int currentAttempt;
        /** 最近一次 {@code step FAILED} 的步驟與 attempt（run FAILED 時建 ESCALATED 審核項用）。 */
        public String lastFailedStepId;
        public int lastFailedAttempt;
        /** 最後一則 Bridge 事件的處理時間（{@code AGENT_UNRESPONSIVE} 判定用）。 */
        public Instant lastEventAt;
        /** 重試統計（HIGH_RETRY_RATE 與 metric-update）：本批次開始過的任務、發生過 RETRYING 的任務、RETRYING 事件數。 */
        public final Set<UUID> startedTasks = new HashSet<>();
        public final Set<UUID> retriedTasks = new HashSet<>();
        public int retryEvents;
        public boolean countersLoaded;
        /** 本次 Bridge 不可達是否已送過連線告警（同一次中斷只送一次，契約 §2.3 第 5 點）。 */
        public boolean unreachableAnnounced;
        /**
         * 這個 run 的 traceId（契約 §0.4 第 6 點，C-12）：啟動它的請求的 traceId；沒有（console-api 重啟後）就由第一個需要的背景呼叫新產
         * 一個並記住。只在記憶體、不入庫——背景消費者與啟動對帳呼叫 Bridge 時沿用它，使同一個 run 的 Bridge 日誌串得起來。
         */
        public final AtomicReference<String> traceId = new AtomicReference<>();
    }

    private final Map<UUID, ReentrantLock> locks = new ConcurrentHashMap<>();
    private final Map<UUID, Runtime> runtimes = new ConcurrentHashMap<>();

    /** 持有該 run 的鎖執行（可重入）。 */
    public <T> T locked(UUID runId, Supplier<T> action) {
        ReentrantLock lock = locks.computeIfAbsent(runId, id -> new ReentrantLock());
        lock.lock();
        try {
            return action.get();
        } finally {
            lock.unlock();
        }
    }

    public void locked(UUID runId, Runnable action) {
        locked(runId, () -> {
            action.run();
            return null;
        });
    }

    /** 該 run 的執行期狀態（不存在則建立）；呼叫端須持有該 run 的鎖。 */
    public Runtime runtime(UUID runId) {
        return runtimes.computeIfAbsent(runId, id -> new Runtime());
    }

    /**
     * 記憶體內最近一則 {@code status} 事件的 Bridge 狀態（批次列表的 {@code bridgeStatus}，契約 §1.2.2）。唯讀：不建立
     * {@link Runtime}、不取 per-run 鎖（列表不該為一頁批次逐一排隊等事件處理）；沒看過這個 run 的事件回 null。
     */
    public BridgeStatus knownBridgeStatus(UUID runId) {
        Runtime runtime = runtimes.get(runId);
        return runtime == null ? null : runtime.bridgeStatus;
    }

    /** 記住啟動這個 run 的請求的 traceId（{@code traceId} 為 null 不動）。 */
    public void bindTrace(UUID runId, String traceId) {
        if (traceId != null && !traceId.isBlank()) {
            runtimes.computeIfAbsent(runId, id -> new Runtime()).traceId.set(traceId);
        }
    }

    /**
     * 該 run 的 traceId（背景呼叫 Bridge 時使用）：啟動它的請求的 traceId；記憶體裡沒有就新產一個 UUID 並記住，之後同一個 run 的背景呼叫
     * （事件串流、回補、啟動對帳）沿用同一個值。不取 per-run 鎖（只動一個原子參照）。
     */
    public String traceIdOf(UUID runId) {
        AtomicReference<String> ref = runtimes.computeIfAbsent(runId, id -> new Runtime()).traceId;
        String known = ref.get();
        if (known != null) {
            return known;
        }
        ref.compareAndSet(null, UUID.randomUUID().toString());
        return ref.get();
    }

    /** 清掉某個 run 的執行期狀態（run 被補償刪除時）。 */
    public void forget(UUID runId) {
        runtimes.remove(runId);
        locks.remove(runId);
    }
}
