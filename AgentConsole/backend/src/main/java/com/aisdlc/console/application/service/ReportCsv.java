package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.MonitorUseCase.MetricValueView;
import com.aisdlc.console.application.port.in.MonitorUseCase.MetricsView;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * 監控報表的 CSV 組裝（契約 §1.3.7；純函式）：UTF-8 含 BOM、行尾 CRLF、欄位依 RFC 4180 引號跳脫；
 * <b>CSV 注入防護</b>：任何以 {@code =}、{@code +}、{@code -}、{@code @} 開頭的<b>文字</b>欄位在前面補一個單引號
 * （數字、時間與布林欄位不是文字，不受影響）。內容為連續的區段，每段以 {@code #section,<名稱>} 行起頭、下一行是欄名、
 * 之後是資料列，段與段之間空一行。
 */
final class ReportCsv {

    private static final String EOL = "\r\n";
    private static final String BOM = "\uFEFF";

    /** 批次一列（{@code runs} 區段）。 */
    record RunRow(int runNumber, UUID runId, String status, int autonomyLevel, Instant startedAt, Instant completedAt,
                  long durationSec, long totalTokensUsed, Long tokenBudget, int tasksTotal, int tasksCompleted,
                  int tasksFailed) {
    }

    /** 任務一列（{@code tasks} 區段）。 */
    record TaskRow(String goalName, String taskName, String status, int retryCount, int maxRetries, long actualTokens,
                   Instant startedAt, Instant completedAt, Double durationSec) {
    }

    /** 告警一列（{@code alerts} 區段）。 */
    record AlertRow(Instant createdAt, String severity, String rule, String subject, String message,
                    boolean acknowledged, String acknowledgedBy, Instant acknowledgedAt) {
    }

    private ReportCsv() {
    }

    static byte[] build(String projectName, Instant from, Instant to, UUID runId, MetricsView m, List<RunRow> runs,
                        List<TaskRow> tasks, List<AlertRow> alerts) {
        StringBuilder out = new StringBuilder(BOM);
        line(out, "#report", text(projectName), from.toString(), to.toString(), runId == null ? "ALL" : runId.toString());
        line(out, "#section", "summary");
        line(out, "metric", "value", "previousValue", "delta", "unit");
        metric(out, "taskCompletionRate", m.taskCompletionRate(), "PERCENT");
        metric(out, "taskSuccessRate", m.taskSuccessRate(), "PERCENT");
        metric(out, "retryRate", m.retryRate(), "PERCENT");
        metric(out, "totalTokens", m.totalTokens(), "TOKENS");
        metric(out, "tokenBudgetUsageRate", m.tokenBudgetUsageRate(), "PERCENT");
        metric(out, "averageRetryCount", m.averageRetryCount(), "COUNT");
        metric(out, "projectCompletionRate", m.projectCompletionRate(), "PERCENT");
        metric(out, "goalAchievementRate", m.goalAchievementRate(), "PERCENT");
        metric(out, "averageTaskDurationSec", m.averageTaskDurationSec(), "SECONDS");
        metric(out, "agentAvailability", m.agentAvailability(), "PERCENT");
        out.append(EOL);

        line(out, "#section", "runs");
        line(out, "runNumber", "runId", "status", "autonomyLevel", "startedAt", "completedAt", "durationSec",
                "totalTokensUsed", "tokenBudget", "tasksTotal", "tasksCompleted", "tasksFailed");
        for (RunRow r : runs) {
            line(out, num(r.runNumber()), r.runId().toString(), text(r.status()), num(r.autonomyLevel()),
                    time(r.startedAt()), time(r.completedAt()), num(r.durationSec()), num(r.totalTokensUsed()),
                    num(r.tokenBudget()), num(r.tasksTotal()), num(r.tasksCompleted()), num(r.tasksFailed()));
        }
        out.append(EOL);

        line(out, "#section", "tasks");
        line(out, "goalName", "taskName", "status", "retryCount", "maxRetries", "actualTokens", "startedAt",
                "completedAt", "durationSec");
        for (TaskRow t : tasks) {
            line(out, text(t.goalName()), text(t.taskName()), text(t.status()), num(t.retryCount()),
                    num(t.maxRetries()), num(t.actualTokens()), time(t.startedAt()), time(t.completedAt()),
                    num(t.durationSec()));
        }
        out.append(EOL);

        line(out, "#section", "alerts");
        line(out, "createdAt", "severity", "rule", "subject", "message", "acknowledged", "acknowledgedBy",
                "acknowledgedAt");
        for (AlertRow a : alerts) {
            line(out, time(a.createdAt()), text(a.severity()), text(a.rule()), text(a.subject()), text(a.message()),
                    Boolean.toString(a.acknowledged()), text(a.acknowledgedBy()), time(a.acknowledgedAt()));
        }
        return out.toString().getBytes(StandardCharsets.UTF_8);
    }

    private static void metric(StringBuilder out, String name, MetricValueView v, String unit) {
        line(out, name, num(v.value()), num(v.previousValue()), num(v.delta()), unit);
    }

    /** 一行：欄位已是最終文字（{@link #text}／{@link #num}／{@link #time} 的輸出），這裡只做 RFC 4180 的引號與分隔。 */
    private static void line(StringBuilder out, String... fields) {
        List<String> quoted = new ArrayList<>(fields.length);
        for (String f : fields) {
            quoted.add(quote(f));
        }
        out.append(String.join(",", quoted)).append(EOL);
    }

    /** RFC 4180：含逗號、雙引號或換行的欄位以雙引號包起、內部雙引號加倍。 */
    static String quote(String field) {
        if (field == null) {
            return "";
        }
        if (field.indexOf(',') >= 0 || field.indexOf('"') >= 0 || field.indexOf('\n') >= 0
                || field.indexOf('\r') >= 0) {
            return '"' + field.replace("\"", "\"\"") + '"';
        }
        return field;
    }

    /** 文字欄位的注入防護：以 {@code =}、{@code +}、{@code -}、{@code @} 開頭者補一個單引號。 */
    static String text(String value) {
        if (value == null || value.isEmpty()) {
            return "";
        }
        char first = value.charAt(0);
        return first == '=' || first == '+' || first == '-' || first == '@' ? "'" + value : value;
    }

    private static String num(Number value) {
        return value == null ? "" : value.toString();
    }

    private static String time(Instant value) {
        return value == null ? "" : value.toString();
    }
}
