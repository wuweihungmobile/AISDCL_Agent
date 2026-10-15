package com.aisdlc.console.application.port.in;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 專案監控的讀取用例（Phase 5；契約 §1.3、§3.8）：八項 KPI 加設計稿的兩項、Token／任務趨勢、告警、結構化日誌與 CSV 報表。
 * 資料全來自 DB（唯一例外是 {@code agentAvailability}，取自 console-api 對 Bridge 的健康探測環）；不呼叫 Bridge。
 * 回傳「視圖」record，由 web 層轉成 DTO。
 */
public interface MonitorUseCase {

    /**
     * 共通查詢參數（契約 §1.3）。{@code from}／{@code to} 為 null 取預設（{@code to}＝現在、{@code from}＝{@code to}−24 小時）；
     * {@code bucket}（只用於趨勢）為 {@code HOUR}／{@code DAY}，null 依視窗長度決定（≤ 48 小時用 HOUR，否則 DAY）。
     */
    record Query(UUID projectId, UUID runId, Instant from, Instant to, String bucket) {
    }

    /** 一個 KPI 的數值與「緊鄰前一個等長視窗」的比較；無法計算者為 null（UI 顯示「—」）。{@code Number}：Token 為整數、其餘為小數。 */
    record MetricValueView(Number value, Number previousValue, Number delta) {
    }

    record TaskDurationView(UUID taskId, String taskName, String goalName, double durationSec) {
    }

    record RetryBucketView(int retries, int tasks) {
    }

    /** {@code ProjectMetricsResponse}。 */
    record MetricsView(UUID projectId, UUID runId, Instant from, Instant to, Instant generatedAt,
                       MetricValueView projectCompletionRate, MetricValueView goalAchievementRate,
                       MetricValueView taskCompletionRate, MetricValueView taskSuccessRate,
                       MetricValueView averageRetryCount, MetricValueView retryRate, MetricValueView totalTokens,
                       MetricValueView tokenBudgetUsageRate, MetricValueView averageTaskDurationSec,
                       MetricValueView agentAvailability, Long tokenBudget,
                       Map<String, Integer> taskStatusDistribution, List<TaskDurationView> taskDurations,
                       List<RetryBucketView> retryDistribution) {
    }

    record TokenTrendView(Instant bucketStart, long tokens, long cumulativeTokens, Long budget) {
    }

    record TaskTrendView(Instant bucketStart, int started, int completed, int failed, int retried) {
    }

    record AlertView(UUID id, UUID projectId, UUID runId, String rule, String severity, String subject, String message,
                     Instant createdAt, boolean acknowledged, String acknowledgedBy, Instant acknowledgedAt) {
    }

    record LogView(String id, Instant timestamp, String level, String source, String message, UUID runId, UUID taskId,
                   String stepId) {
    }

    /** 日誌查詢：共通視窗＋篩選（{@code level}：ALL／INFO／WARN／ERROR；{@code q}：訊息關鍵字，萬用字元視為字面）。 */
    record LogQuery(Query window, String level, UUID taskId, String q, boolean ascending, int page, int size) {
    }

    /** 報表檔案（{@code content} 已是最終位元組：UTF-8 含 BOM、CRLF）。 */
    record Report(String filename, String contentType, byte[] content) {
    }

    MetricsView metrics(Query query);

    List<TokenTrendView> tokenTrend(Query query);

    List<TaskTrendView> taskTrend(Query query);

    /** {@code limit}：1～200。{@code acknowledged}＝null 不篩。 */
    List<AlertView> alerts(UUID projectId, UUID runId, Boolean acknowledged, int limit);

    /** 確認告警（冪等：已確認者不改寫第一次的確認人與時間）。 */
    void acknowledge(UUID alertId, String actor);

    PageResult<LogView> logs(LogQuery query);

    /** {@code format}：{@code csv}（必做）｜{@code pdf}（W5 之前一律 501）。 */
    Report report(Query query, String format);
}
