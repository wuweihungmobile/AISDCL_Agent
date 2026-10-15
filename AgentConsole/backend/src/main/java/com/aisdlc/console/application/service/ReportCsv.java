package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.MonitorUseCase.MetricValueView;
import com.aisdlc.console.application.port.in.MonitorUseCase.MetricsView;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;

/**
 * 監控報表的 CSV 組裝（契約 §1.3.7；純函式）：UTF-8 含 BOM、行尾 CRLF、欄位依 RFC 4180 引號跳脫；
 * <b>CSV 注入防護</b>：任何以 {@code =}、{@code +}、{@code -}、{@code @} 開頭的<b>文字</b>欄位在前面補一個單引號
 * （數字、時間與布林欄位不是文字，不受影響）。內容為連續的區段，每段以 {@code #section,<名稱>} 行起頭、下一行是欄名、
 * 之後是資料列，段與段之間空一行。
 *
 * <p>四個區段的欄名與 summary 的十個指標（名稱、順序、單位）由本類別定義，PDF 報表（{@link ReportPdfModel}）直接取用同一份，
 * 兩種格式的欄與序因此天生同源。
 */
final class ReportCsv {

    private static final String EOL = "\r\n";
    private static final String BOM = "\uFEFF";

    static final List<String> SUMMARY_HEADER = List.of("metric", "value", "previousValue", "delta", "unit");
    static final List<String> RUNS_HEADER = List.of("runNumber", "runId", "status", "autonomyLevel", "startedAt",
            "completedAt", "durationSec", "totalTokensUsed", "tokenBudget", "tasksTotal", "tasksCompleted",
            "tasksFailed");
    static final List<String> TASKS_HEADER = List.of("goalName", "taskName", "status", "retryCount", "maxRetries",
            "actualTokens", "startedAt", "completedAt", "durationSec");
    static final List<String> ALERTS_HEADER = List.of("createdAt", "severity", "rule", "subject", "message",
            "acknowledged", "acknowledgedBy", "acknowledgedAt");

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

    /** {@code summary} 區段的一列：指標名、值（含前一視窗與差）、單位。 */
    record SummaryLine(String metric, MetricValueView value, String unit) {
    }

    private ReportCsv() {
    }

    /** summary 區段的十個 KPI（順序同契約 §1.3.1；unit ∈ PERCENT／COUNT／SECONDS／TOKENS）。 */
    static List<SummaryLine> summary(MetricsView m) {
        return List.of(
                new SummaryLine("taskCompletionRate", m.taskCompletionRate(), "PERCENT"),
                new SummaryLine("taskSuccessRate", m.taskSuccessRate(), "PERCENT"),
                new SummaryLine("retryRate", m.retryRate(), "PERCENT"),
                new SummaryLine("totalTokens", m.totalTokens(), "TOKENS"),
                new SummaryLine("tokenBudgetUsageRate", m.tokenBudgetUsageRate(), "PERCENT"),
                new SummaryLine("averageRetryCount", m.averageRetryCount(), "COUNT"),
                new SummaryLine("projectCompletionRate", m.projectCompletionRate(), "PERCENT"),
                new SummaryLine("goalAchievementRate", m.goalAchievementRate(), "PERCENT"),
                new SummaryLine("averageTaskDurationSec", m.averageTaskDurationSec(), "SECONDS"),
                new SummaryLine("agentAvailability", m.agentAvailability(), "PERCENT"));
    }

    static byte[] build(String projectName, Instant from, Instant to, UUID runId, MetricsView m, List<RunRow> runs,
                        List<TaskRow> tasks, List<AlertRow> alerts) {
        StringBuilder out = new StringBuilder(BOM);
        line(out, "#report", text(projectName), from.toString(), to.toString(), runId == null ? "ALL" : runId.toString());
        line(out, "#section", "summary");
        line(out, SUMMARY_HEADER);
        for (SummaryLine s : summary(m)) {
            line(out, s.metric(), num(s.value().value()), num(s.value().previousValue()), num(s.value().delta()),
                    s.unit());
        }
        out.append(EOL);

        line(out, "#section", "runs");
        line(out, RUNS_HEADER);
        for (RunRow r : runs) {
            line(out, num(r.runNumber()), r.runId().toString(), text(r.status()), num(r.autonomyLevel()),
                    time(r.startedAt()), time(r.completedAt()), num(r.durationSec()), num(r.totalTokensUsed()),
                    num(r.tokenBudget()), num(r.tasksTotal()), num(r.tasksCompleted()), num(r.tasksFailed()));
        }
        out.append(EOL);

        line(out, "#section", "tasks");
        line(out, TASKS_HEADER);
        for (TaskRow t : tasks) {
            line(out, text(t.goalName()), text(t.taskName()), text(t.status()), num(t.retryCount()),
                    num(t.maxRetries()), num(t.actualTokens()), time(t.startedAt()), time(t.completedAt()),
                    num(t.durationSec()));
        }
        out.append(EOL);

        line(out, "#section", "alerts");
        line(out, ALERTS_HEADER);
        for (AlertRow a : alerts) {
            line(out, time(a.createdAt()), text(a.severity()), text(a.rule()), text(a.subject()), text(a.message()),
                    Boolean.toString(a.acknowledged()), text(a.acknowledgedBy()), time(a.acknowledgedAt()));
        }
        return out.toString().getBytes(StandardCharsets.UTF_8);
    }

    /** 一行：欄位已是最終文字（{@link #text}／{@link #num}／{@link #time} 的輸出），這裡只做 RFC 4180 的引號與分隔。 */
    private static void line(StringBuilder out, String... fields) {
        line(out, Arrays.asList(fields));
    }

    private static void line(StringBuilder out, List<String> fields) {
        List<String> quoted = new ArrayList<>(fields.size());
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

    static String num(Number value) {
        return value == null ? "" : value.toString();
    }

    static String time(Instant value) {
        return value == null ? "" : value.toString();
    }
}
