package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.MonitorUseCase.MetricsView;
import com.aisdlc.console.application.port.out.ReportPdfRenderer.Document;
import com.aisdlc.console.application.port.out.ReportPdfRenderer.Section;
import com.aisdlc.console.application.service.ReportCsv.AlertRow;
import com.aisdlc.console.application.service.ReportCsv.RunRow;
import com.aisdlc.console.application.service.ReportCsv.SummaryLine;
import com.aisdlc.console.application.service.ReportCsv.TaskRow;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * 監控報表的 PDF 內容模型（契約 §1.3.7，C-4；純函式）。與 CSV 用同一組資料列、同樣四個區段、同欄同序
 * （欄名與 summary 的十個指標直接取自 {@link ReportCsv}），差別只在呈現：null 顯示 {@value #NULL_MARK}、
 * 純文字（<b>不做</b> CSV 的注入防護引號——PDF 不是試算表），另加標題（專案名稱＋「監控報表」）、時間範圍、
 * 範圍（{@code runId} 或「全部批次」）與產生時間（UTC）。
 */
final class ReportPdfModel {

    /** null（或空字串）在 PDF 裡的顯示。 */
    static final String NULL_MARK = "—";
    static final String TITLE_SUFFIX = " 監控報表";
    static final String ALL_RUNS = "全部批次";

    private ReportPdfModel() {
    }

    static Document of(String projectName, Instant from, Instant to, UUID runId, Instant generatedAt, MetricsView m,
                       List<RunRow> runs, List<TaskRow> tasks, List<AlertRow> alerts) {
        List<List<String>> summary = new ArrayList<>();
        for (SummaryLine s : ReportCsv.summary(m)) {
            summary.add(List.of(s.metric(), cell(s.value().value()), cell(s.value().previousValue()),
                    cell(s.value().delta()), s.unit()));
        }
        List<List<String>> runRows = new ArrayList<>();
        for (RunRow r : runs) {
            runRows.add(List.of(cell(r.runNumber()), r.runId().toString(), cell(r.status()), cell(r.autonomyLevel()),
                    cell(r.startedAt()), cell(r.completedAt()), cell(r.durationSec()), cell(r.totalTokensUsed()),
                    cell(r.tokenBudget()), cell(r.tasksTotal()), cell(r.tasksCompleted()), cell(r.tasksFailed())));
        }
        List<List<String>> taskRows = new ArrayList<>();
        for (TaskRow t : tasks) {
            taskRows.add(List.of(cell(t.goalName()), cell(t.taskName()), cell(t.status()), cell(t.retryCount()),
                    cell(t.maxRetries()), cell(t.actualTokens()), cell(t.startedAt()), cell(t.completedAt()),
                    cell(t.durationSec())));
        }
        List<List<String>> alertRows = new ArrayList<>();
        for (AlertRow a : alerts) {
            alertRows.add(List.of(cell(a.createdAt()), cell(a.severity()), cell(a.rule()), cell(a.subject()),
                    cell(a.message()), Boolean.toString(a.acknowledged()), cell(a.acknowledgedBy()),
                    cell(a.acknowledgedAt())));
        }
        return new Document(projectName + TITLE_SUFFIX,
                List.of("時間範圍：" + from + " ～ " + to,
                        "範圍：" + (runId == null ? ALL_RUNS : runId.toString()),
                        "產生時間（UTC）：" + generatedAt),
                List.of(new Section("summary", ReportCsv.SUMMARY_HEADER, summary),
                        new Section("runs", ReportCsv.RUNS_HEADER, runRows),
                        new Section("tasks", ReportCsv.TASKS_HEADER, taskRows),
                        new Section("alerts", ReportCsv.ALERTS_HEADER, alertRows)));
    }

    private static String cell(Number value) {
        return value == null ? NULL_MARK : value.toString();
    }

    private static String cell(Instant value) {
        return value == null ? NULL_MARK : value.toString();
    }

    private static String cell(String value) {
        return value == null || value.isEmpty() ? NULL_MARK : value;
    }
}
