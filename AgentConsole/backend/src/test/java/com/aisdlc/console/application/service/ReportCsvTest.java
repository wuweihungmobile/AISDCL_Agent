package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.MonitorUseCase.MetricValueView;
import com.aisdlc.console.application.port.in.MonitorUseCase.MetricsView;
import com.aisdlc.console.application.service.ReportCsv.AlertRow;
import com.aisdlc.console.application.service.ReportCsv.RunRow;
import com.aisdlc.console.application.service.ReportCsv.TaskRow;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 監控報表的 CSV（契約 §1.3.7）。為什麼重要：報表會被直接用 Excel 開啟——任何以 {@code = + - @} 開頭的文字欄位
 * （任務名稱、告警訊息都是使用者或引擎可控的字串）都會被當成公式執行（CSV 注入）；BOM 與 CRLF 決定 Excel 是否把中文讀成亂碼、
 * 一列是否被拆成兩列；區段順序與欄名是下游腳本解析的契約。
 */
class ReportCsvTest {

    private static final Instant FROM = Instant.parse("2026-10-15T00:00:00Z");
    private static final Instant TO = Instant.parse("2026-10-15T08:00:00Z");
    private static final UUID PROJECT = UUID.fromString("11111111-1111-1111-1111-111111111111");
    private static final UUID RUN = UUID.fromString("22222222-2222-2222-2222-222222222222");

    private static MetricValueView value(Number value, Number previous, Number delta) {
        return new MetricValueView(value, previous, delta);
    }

    private static MetricsView metrics() {
        MetricValueView none = value(0.0, null, null);
        return new MetricsView(PROJECT, null, FROM, TO, TO, none, none, value(100.0, 0.0, 100.0), value(100.0, null, null),
                none, none, value(3720L, 0L, 3720L), value(3.7, null, null), value(2.5, null, null),
                value(100.0, null, null), 100000L, Map.of(), List.of(), List.of());
    }

    private static String csv(String projectName, UUID runId, List<RunRow> runs, List<TaskRow> tasks,
                              List<AlertRow> alerts) {
        byte[] bytes = ReportCsv.build(projectName, FROM, TO, runId, metrics(), runs, tasks, alerts);
        return new String(bytes, StandardCharsets.UTF_8);
    }

    private static List<String> lines(String csv) {
        return List.of(csv.split("\r\n", -1));
    }

    @Test
    void itStartsWithAUtf8BomAndEveryLineEndsWithCrlf() {
        byte[] bytes = ReportCsv.build("專案", FROM, TO, null, metrics(), List.of(), List.of(), List.of());

        assertThat(bytes).startsWith((byte) 0xEF, (byte) 0xBB, (byte) 0xBF);
        String text = new String(bytes, StandardCharsets.UTF_8);
        assertThat(text.replace("\r\n", "")).as("沒有單獨的 LF 或 CR").doesNotContain("\n").doesNotContain("\r");
        assertThat(text).contains("專案");
    }

    @Test
    void theFourSectionsComeInTheDocumentedOrderEachWithItsHeaderRow() {
        String text = csv("P", RUN, List.of(), List.of(), List.of());
        List<String> lines = lines(text);

        assertThat(lines.get(0)).isEqualTo("﻿#report,P,2026-10-15T00:00:00Z,2026-10-15T08:00:00Z," + RUN);
        assertThat(text.indexOf("#section,summary")).isPositive()
                .isLessThan(text.indexOf("#section,runs"));
        assertThat(text.indexOf("#section,runs")).isLessThan(text.indexOf("#section,tasks"));
        assertThat(text.indexOf("#section,tasks")).isLessThan(text.indexOf("#section,alerts"));
        assertThat(lines).contains("metric,value,previousValue,delta,unit",
                "runNumber,runId,status,autonomyLevel,startedAt,completedAt,durationSec,totalTokensUsed,tokenBudget,"
                        + "tasksTotal,tasksCompleted,tasksFailed",
                "goalName,taskName,status,retryCount,maxRetries,actualTokens,startedAt,completedAt,durationSec",
                "createdAt,severity,rule,subject,message,acknowledged,acknowledgedBy,acknowledgedAt");
    }

    @Test
    void aReportWithoutARunFilterSaysAllAndTheSummaryCarriesTheUnitsWithBlankPreviousAndDeltaWhenUnknown() {
        String text = csv("P", null, List.of(), List.of(), List.of());

        assertThat(lines(text).get(0)).endsWith(",ALL");
        assertThat(lines(text)).contains("totalTokens,3720,0,3720,TOKENS", "taskCompletionRate,100.0,0.0,100.0,PERCENT",
                "taskSuccessRate,100.0,,,PERCENT", "tokenBudgetUsageRate,3.7,,,PERCENT",
                "averageTaskDurationSec,2.5,,,SECONDS", "agentAvailability,100.0,,,PERCENT",
                "averageRetryCount,0.0,,,COUNT", "retryRate,0.0,,,PERCENT", "projectCompletionRate,0.0,,,PERCENT",
                "goalAchievementRate,0.0,,,PERCENT");
    }

    @Test
    void textFieldsThatCouldBeReadAsSpreadsheetFormulasAreDefused() {
        List<TaskRow> tasks = List.of(
                new TaskRow("=HYPERLINK(\"http://evil\")", "+cmd|' /C calc'!A0", "COMPLETED", 0, 3, 1240, FROM, TO, 1.5),
                new TaskRow("-2+3", "@SUM(A1)", "FAILED", 1, 3, 0, null, null, null),
                new TaskRow("正常目標", "a=b", "COMPLETED", 0, 3, 1, FROM, TO, 2.0));
        List<AlertRow> alerts = List.of(new AlertRow(FROM, "WARNING", "HIGH_RETRY_RATE", "=run", "@引擎回報：-1", false,
                null, null));

        String text = csv("=evil()", RUN, List.of(), tasks, alerts);

        assertThat(text).contains("#report,'=evil(),");
        assertThat(lines(text)).contains(
                "\"'=HYPERLINK(\"\"http://evil\"\")\",'+cmd|' /C calc'!A0,COMPLETED,0,3,1240,2026-10-15T00:00:00Z,"
                        + "2026-10-15T08:00:00Z,1.5",
                "'-2+3,'@SUM(A1),FAILED,1,3,0,,,",
                "正常目標,a=b,COMPLETED,0,3,1,2026-10-15T00:00:00Z,2026-10-15T08:00:00Z,2.0");
        assertThat(lines(text)).contains("2026-10-15T00:00:00Z,WARNING,HIGH_RETRY_RATE,'=run,'@引擎回報：-1,false,,");
    }

    @Test
    void fieldsWithCommasQuotesOrLineBreaksAreQuotedPerRfc4180() {
        assertThat(ReportCsv.quote("plain")).isEqualTo("plain");
        assertThat(ReportCsv.quote("a,b")).isEqualTo("\"a,b\"");
        assertThat(ReportCsv.quote("say \"hi\"")).isEqualTo("\"say \"\"hi\"\"\"");
        assertThat(ReportCsv.quote("two\nlines")).isEqualTo("\"two\nlines\"");
        assertThat(ReportCsv.quote("cr\rhere")).isEqualTo("\"cr\rhere\"");
        assertThat(ReportCsv.quote(null)).isEmpty();
        assertThat(ReportCsv.quote("")).isEmpty();
    }

    @Test
    void textDefusingOnlyTouchesTheFirstCharacterOfTextFields() {
        assertThat(ReportCsv.text(null)).isEmpty();
        assertThat(ReportCsv.text("")).isEmpty();
        assertThat(ReportCsv.text("=1")).isEqualTo("'=1");
        assertThat(ReportCsv.text("+1")).isEqualTo("'+1");
        assertThat(ReportCsv.text("-1")).isEqualTo("'-1");
        assertThat(ReportCsv.text("@a")).isEqualTo("'@a");
        assertThat(ReportCsv.text("a=1")).isEqualTo("a=1");
        assertThat(ReportCsv.text(" =1")).as("前導空白不是公式起手式").isEqualTo(" =1");
    }

    @Test
    void runRowsAndAlertRowsKeepNumbersTimesAndBooleansUnquotedAndNullsBlank() {
        RunRow run = new RunRow(2, RUN, "COMPLETED", 4, FROM, TO, 28800, 3720, null, 3, 3, 0);
        AlertRow acked = new AlertRow(FROM, "CRITICAL", "TOKEN_BUDGET_EXCEEDED", "run", "超出預算", true, "operator", TO);

        List<String> lines = lines(csv("P", RUN, List.of(run), List.of(), List.of(acked)));

        assertThat(lines).contains("2," + RUN + ",COMPLETED,4,2026-10-15T00:00:00Z,2026-10-15T08:00:00Z,28800,3720,,3,3,0",
                "2026-10-15T00:00:00Z,CRITICAL,TOKEN_BUDGET_EXCEEDED,run,超出預算,true,operator,2026-10-15T08:00:00Z");
    }
}
