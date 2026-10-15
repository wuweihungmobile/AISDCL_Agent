package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.MonitorUseCase.MetricValueView;
import com.aisdlc.console.application.port.in.MonitorUseCase.MetricsView;
import com.aisdlc.console.application.port.in.MonitorUseCase.RetryBucketView;
import com.aisdlc.console.application.port.in.MonitorUseCase.TaskDurationView;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 專案指標（契約 §1.3.1、§3.8.1）：PRD §5.4.2 八項 KPI 全數提供，另含設計稿使用的 {@code taskCompletionRate}（卡片「完成率」）與
 * {@code retryRate}（卡片「重試率」），以及任務狀態分佈、執行時間分佈、重試次數分佈（ADR-001 G-13）。
 * 百分比一律 0～100 並四捨五入到小數 1 位；平均值四捨五入到小數 2 位；Token 為整數。
 */
@Schema(name = "ProjectMetricsResponse", description = "PRD §5.4.2 八項 KPI 全數提供，另含設計稿使用的 taskCompletionRate"
        + "（卡片「完成率」）與 retryRate（卡片「重試率」），以及任務狀態分佈、執行時間分佈、重試次數分佈（ADR-001 G-13）")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ProjectMetricsResponse(
        @NotNull UUID projectId,
        UUID runId,
        @NotNull Instant from,
        @NotNull Instant to,
        @NotNull Instant generatedAt,
        @NotNull MetricValue projectCompletionRate,
        @NotNull MetricValue goalAchievementRate,
        @NotNull MetricValue taskCompletionRate,
        @NotNull MetricValue taskSuccessRate,
        @NotNull MetricValue averageRetryCount,
        @NotNull MetricValue retryRate,
        @NotNull MetricValue totalTokens,
        @NotNull MetricValue tokenBudgetUsageRate,
        @NotNull MetricValue averageTaskDurationSec,
        @NotNull MetricValue agentAvailability,
        @JsonInclude(JsonInclude.Include.ALWAYS)
        @Schema(nullable = true, description = "視窗內各批次 tokenBudget 之和；無預算為 null") Long tokenBudget,
        @NotNull @Schema(description = "任務十一態的現況計數（key＝TaskStatus，缺的狀態為 0 且一律出現）")
        Map<String, Integer> taskStatusDistribution,
        @NotNull @Schema(description = "視窗內完成的任務，依耗時由長到短，最多 10 筆") List<TaskDurationItem> taskDurations,
        @NotNull List<RetryBucket> retryDistribution) {

    /** 一個 KPI 的數值與「緊鄰前一個等長視窗」的比較；無法計算者為 null（UI 顯示「—」）。 */
    @Schema(name = "MetricValue", description = "一個 KPI 的數值與「緊鄰前一個等長視窗」的比較；無法計算者為 null（UI 顯示「—」）")
    public record MetricValue(
            @NotNull @Schema(nullable = true, description = "百分比 0～100（小數 1 位）；平均值小數 2 位；Token 為整數") Number value,
            @Schema(nullable = true) Number previousValue,
            @Schema(nullable = true, description = "value−previousValue（百分比為百分點）") Number delta) {

        static MetricValue from(MetricValueView v) {
            return new MetricValue(v.value(), v.previousValue(), v.delta());
        }
    }

    @Schema(name = "TaskDurationItem")
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record TaskDurationItem(
            @NotNull UUID taskId,
            @NotNull String taskName,
            String goalName,
            @NotNull @Schema(description = "completedAt−startedAt（秒，小數 1 位）") double durationSec) {

        static TaskDurationItem from(TaskDurationView v) {
            return new TaskDurationItem(v.taskId(), v.taskName(), v.goalName(), v.durationSec());
        }
    }

    @Schema(name = "RetryBucket")
    public record RetryBucket(
            @NotNull @Schema(description = "重試次數（0、1、2…；≥5 併入 5）") int retries,
            @NotNull int tasks) {

        static RetryBucket from(RetryBucketView v) {
            return new RetryBucket(v.retries(), v.tasks());
        }
    }

    public static ProjectMetricsResponse from(MetricsView m) {
        return new ProjectMetricsResponse(m.projectId(), m.runId(), m.from(), m.to(), m.generatedAt(),
                MetricValue.from(m.projectCompletionRate()), MetricValue.from(m.goalAchievementRate()),
                MetricValue.from(m.taskCompletionRate()), MetricValue.from(m.taskSuccessRate()),
                MetricValue.from(m.averageRetryCount()), MetricValue.from(m.retryRate()),
                MetricValue.from(m.totalTokens()), MetricValue.from(m.tokenBudgetUsageRate()),
                MetricValue.from(m.averageTaskDurationSec()), MetricValue.from(m.agentAvailability()),
                m.tokenBudget(), m.taskStatusDistribution(),
                m.taskDurations().stream().map(TaskDurationItem::from).toList(),
                m.retryDistribution().stream().map(RetryBucket::from).toList());
    }
}
