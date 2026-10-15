package com.aisdlc.console.application.service;

import com.aisdlc.console.domain.model.execution.BridgeStatus;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
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

        /** 最近一則 {@code status} 事件的 Bridge 狀態；null＝尚未看過（由呼叫端以 DB 狀態補）。 */
        public BridgeStatus bridgeStatus;
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

    /** 清掉某個 run 的執行期狀態（run 被補償刪除時）。 */
    public void forget(UUID runId) {
        runtimes.remove(runId);
        locks.remove(runId);
    }
}
