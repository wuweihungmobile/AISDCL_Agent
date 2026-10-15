package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.CurrentStepView;
import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.ReviewView;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.RunStatus;

import java.time.Duration;
import java.util.Optional;
import java.util.UUID;

/**
 * 前端 SSE 的用例（契約 §2）：{@code /logs}（{@code log}／{@code status-change}／{@code review-request}／{@code alert}）與
 * {@code /metrics}（{@code progress-update}／{@code token-update}／{@code metric-update}）。
 *
 * <p>用例負責「訂閱、重播、去重、佇列、keep-alive、終態關閉」；web 層只提供一個 {@link Sink}（把框架寫進 {@code SseEmitter}）。
 * 這樣 id 規則、{@code Last-Event-ID} 重播與慢速訂閱者的處置都在純 Java／Spring 層、可不經 HTTP 單元測試。
 */
public interface ExecutionStreamUseCase {

    enum Kind { LOGS, METRICS }

    /**
     * 一個要送給前端的 SSE 框架。{@code sub}：{@code 0}＝Bridge 事件（id＝{@code <seq>}）、{@code ≥1}＝Console 自產（id＝{@code <seq>.<sub>}）、
     * {@code -1}＝不帶 {@code id:} 行（連線層的暫態告警，契約 §2.2）。{@code data} 是契約 §2.5／§2.6 的事件資料 record。
     */
    record Frame(Kind kind, int seq, int sub, String event, Object data) {

        public static final int NO_ID = -1;

        public boolean hasId() {
            return sub != NO_ID;
        }

        /** SSE 的 {@code id:} 值（{@code 41} 或 {@code 41.1}）；沒有 id 回 null。 */
        public String id() {
            if (sub == NO_ID) {
                return null;
            }
            return sub == 0 ? Integer.toString(seq) : seq + "." + sub;
        }

        /** 排序／去重用的鍵：{@code (seq, sub)} 字典序（{@code 41 < 41.1 < 41.2 < 42}）。 */
        public long order() {
            return orderOf(seq, Math.max(sub, 0));
        }

        public static long orderOf(int seq, int sub) {
            return (long) seq * 1_000_000L + sub;
        }
    }

    /** 前端連線的寫出端（web 層以 {@code SseEmitter} 實作）。回傳 false＝客戶端已斷線，用例會結束該連線。 */
    interface Sink {

        boolean send(Frame frame);

        /** 註解行（{@code :keep-alive}）。 */
        boolean comment(String text);

        /** 正常結束串流（終態、或伺服器主動關閉慢速訂閱者）。 */
        void close();
    }

    /** 開啟的連線；{@code close()} 取消訂閱、停止該連線的背景執行緒。 */
    interface Subscription extends AutoCloseable {

        @Override
        void close();
    }

    record StreamSettings(Duration keepAlive, int queueSize) {
    }

    StreamSettings settings();

    /**
     * 開啟串流。回 empty＝應回 HTTP 204（run 已終態且沒有可重播／可送的內容，契約 §2.4）。查無 run 丟 NotFoundException。
     *
     * @param lastEventId 客戶端的 {@code Last-Event-ID}；格式不合視為沒有帶（不回 400，契約 §2.3 第 1 點）
     * @param tail        {@code /logs} 沒有 Last-Event-ID 時先重播最後幾則（預設 200，0＝只收新事件，上限 5,000）
     */
    Optional<Subscription> open(UUID runId, Kind kind, String lastEventId, Integer tail, Sink sink);

    // ── 事件資料（契約 §2.5、§2.6；欄位名即 JSON 鍵）────────────────────────────────

    /** {@code log}：{@code source} 為 {@code ENGINE}（引擎 stdout 一行）或 {@code STEP}（由 step 事件衍生）。 */
    record LogEventData(int seq, String ts, String source, String level, String message, String stepId,
                        Integer stepNumber, UUID taskId, String taskName, UUID goalId, Integer attempt,
                        String stepStatus, Long tokensUsed) {
    }

    /** {@code status-change}：{@code runStatus} 為六態折疊值，{@code bridgeStatus} 為 Bridge 原值。 */
    record StatusChangeEventData(int seq, String ts, RunStatus runStatus, BridgeStatus bridgeStatus, String reason) {
    }

    /** {@code review-request}：id＝{@code <seq>.<sub>}（{@code sub ≥ 1}）。 */
    record ReviewRequestEventData(int seq, int sub, String ts, ReviewView review) {
    }

    /**
     * {@code alert}：{@code origin=ENGINE}（Bridge alert，id＝seq）或 {@code CONSOLE}（規則告警 id＝{@code <seq>.<sub>}；
     * 連線告警不帶 id）。{@code severity}：{@code INFO／WARNING／CRITICAL}。
     */
    record AlertEventData(int seq, Integer sub, String ts, String origin, UUID alertId, String rule, String code,
                          String severity, String subject, String message, String stepId) {
    }

    /** {@code progress-update}。 */
    record ProgressUpdateEventData(int seq, String ts, RunStatus runStatus, BridgeStatus bridgeStatus,
                                   int completedSteps, int totalSteps, double progressPct,
                                   CurrentStepView currentStep) {
    }

    /** {@code token-update}：{@code contextPct} 是引擎回報的 context 視窗使用 %，不是預算 %。 */
    record TokenUpdateEventData(int seq, String ts, long tokensUsed, long delta, double contextPct, Long tokenBudget,
                                Double budgetUsageRate, UUID taskId) {
    }

    /** {@code metric-update}：範圍＝本批次。 */
    record MetricUpdateEventData(int seq, int sub, String ts, int completedTasks, int failedTasks, int totalTasks,
                                 int retriedTasks, double averageRetryCount, long totalTokensUsed,
                                 Double tokenBudgetUsageRate, long elapsedSec) {
    }
}
