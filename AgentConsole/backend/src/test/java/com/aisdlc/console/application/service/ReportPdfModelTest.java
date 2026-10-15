package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.MonitorUseCase.MetricValueView;
import com.aisdlc.console.application.port.in.MonitorUseCase.MetricsView;
import com.aisdlc.console.application.port.out.ReportPdfRenderer.Document;
import com.aisdlc.console.application.port.out.ReportPdfRenderer.Section;
import com.aisdlc.console.application.service.ReportCsv.AlertRow;
import com.aisdlc.console.application.service.ReportCsv.RunRow;
import com.aisdlc.console.application.service.ReportCsv.TaskRow;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * PDF 報表的內容模型（契約 §1.3.7，C-4）。為什麼重要：契約要求 PDF 與 CSV「同一組資料、同樣四個區段、同欄同序」——
 * 兩種格式若各算各的，使用者下載 CSV 與 PDF 會看到不同的數字；而 PDF 是純文字呈現，CSV 為了防試算表公式注入而加的單引號
 * 不能出現在 PDF 裡（那會讓人讀到一個多出來的 '）。
 */
class ReportPdfModelTest {

    private static final Instant FROM = Instant.parse("2026-10-15T00:00:00Z");
    private static final Instant TO = Instant.parse("2026-10-15T08:00:00Z");
    private static final Instant NOW = Instant.parse("2026-10-15T09:30:00Z");
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

    private static final List<RunRow> RUNS = List.of(new RunRow(2, RUN, "COMPLETED", 4, FROM, TO, 28800, 3720, null, 3,
            3, 0));
    private static final List<TaskRow> TASKS = List.of(
            new TaskRow("基礎", "初始化", "COMPLETED", 0, 3, 1240, FROM, TO, 1.5),
            new TaskRow("基礎", "=SUM(A1)", "FAILED", 1, 3, 0, null, null, null));
    private static final List<AlertRow> ALERTS = List.of(
            new AlertRow(FROM, "WARNING", "HIGH_RETRY_RATE", "=run", "@引擎回報：-1", false, null, null),
            new AlertRow(TO, "CRITICAL", "TOKEN_BUDGET_EXCEEDED", "run:x", "超出預算, 請處理", true, "operator", TO));

    private static Document model(UUID runId) {
        return ReportPdfModel.of("監控專案", FROM, TO, runId, NOW, metrics(), RUNS, TASKS, ALERTS);
    }

    private static Section section(Document document, String name) {
        return document.sections().stream().filter(s -> s.name().equals(name)).findFirst().orElseThrow();
    }

    @Test
    void theTitleIsTheProjectNameFollowedByMonitoringReportAndTheInfoLinesCarryRangeScopeAndGenerationTime() {
        Document all = model(null);
        Document one = model(RUN);

        assertThat(all.title()).isEqualTo("監控專案 監控報表");
        assertThat(all.infoLines()).containsExactly("時間範圍：2026-10-15T00:00:00Z ～ 2026-10-15T08:00:00Z",
                "範圍：全部批次", "產生時間（UTC）：2026-10-15T09:30:00Z");
        assertThat(one.infoLines().get(1)).isEqualTo("範圍：" + RUN);
    }

    @Test
    void theFourSectionsComeInCsvOrderWithTheSameHeadersAndEveryRowHasOneCellPerHeader() {
        Document document = model(RUN);

        assertThat(document.sections()).extracting(Section::name).containsExactly("summary", "runs", "tasks", "alerts");
        assertThat(section(document, "summary").headers()).isEqualTo(ReportCsv.SUMMARY_HEADER);
        assertThat(section(document, "runs").headers()).isEqualTo(ReportCsv.RUNS_HEADER);
        assertThat(section(document, "tasks").headers()).isEqualTo(ReportCsv.TASKS_HEADER);
        assertThat(section(document, "alerts").headers()).isEqualTo(ReportCsv.ALERTS_HEADER);
        for (Section section : document.sections()) {
            assertThat(section.rows()).as(section.name()).allSatisfy(row -> assertThat(row).hasSameSizeAs(section.headers()));
        }
    }

    @Test
    void theSummaryHasTheTenMetricsInContractOrderWithUnitsAndADashForUnknownValues() {
        List<List<String>> rows = section(model(null), "summary").rows();

        assertThat(rows).extracting(row -> row.get(0)).containsExactly("taskCompletionRate", "taskSuccessRate",
                "retryRate", "totalTokens", "tokenBudgetUsageRate", "averageRetryCount", "projectCompletionRate",
                "goalAchievementRate", "averageTaskDurationSec", "agentAvailability");
        assertThat(rows.get(3)).containsExactly("totalTokens", "3720", "0", "3720", "TOKENS");
        assertThat(rows.get(0)).containsExactly("taskCompletionRate", "100.0", "0.0", "100.0", "PERCENT");
        assertThat(rows.get(2)).as("前一視窗與差未知＝破折號").containsExactly("retryRate", "0.0", "—", "—", "PERCENT");
    }

    @Test
    void rowsAreMappedFieldForFieldAndNullsAndBlanksBecomeADash() {
        Document document = model(RUN);

        assertThat(section(document, "runs").rows()).containsExactly(List.of("2", RUN.toString(), "COMPLETED", "4",
                "2026-10-15T00:00:00Z", "2026-10-15T08:00:00Z", "28800", "3720", "—", "3", "3", "0"));
        assertThat(section(document, "tasks").rows()).containsExactly(
                List.of("基礎", "初始化", "COMPLETED", "0", "3", "1240", "2026-10-15T00:00:00Z", "2026-10-15T08:00:00Z",
                        "1.5"),
                List.of("基礎", "=SUM(A1)", "FAILED", "1", "3", "0", "—", "—", "—"));
        assertThat(section(document, "alerts").rows().get(0)).containsExactly("2026-10-15T00:00:00Z", "WARNING",
                "HIGH_RETRY_RATE", "=run", "@引擎回報：-1", "false", "—", "—");
        assertThat(section(document, "alerts").rows().get(1)).containsExactly("2026-10-15T08:00:00Z", "CRITICAL",
                "TOKEN_BUDGET_EXCEEDED", "run:x", "超出預算, 請處理", "true", "operator", "2026-10-15T08:00:00Z");
    }

    @Test
    void anEmptyStringIsShownAsADashJustLikeNull() {
        List<AlertRow> blank = List.of(new AlertRow(FROM, "WARNING", "HIGH_RETRY_RATE", "", "m", false, "", null));

        Document document = ReportPdfModel.of("p", FROM, TO, null, NOW, metrics(), List.of(), List.of(), blank);

        assertThat(section(document, "alerts").rows().get(0)).containsExactly("2026-10-15T00:00:00Z", "WARNING",
                "HIGH_RETRY_RATE", "—", "m", "false", "—", "—");
        assertThat(section(document, "runs").rows()).isEmpty();
    }

    @Test
    void itIsPlainTextWhereTheCsvDefusesFormulasWithAQuote() {
        String csv = new String(ReportCsv.build("監控專案", FROM, TO, RUN, metrics(), RUNS, TASKS, ALERTS),
                StandardCharsets.UTF_8);
        Document document = model(RUN);

        assertThat(csv).contains("'=SUM(A1)").contains("'=run").contains("'@引擎回報：-1");
        assertThat(section(document, "tasks").rows().get(1).get(1)).isEqualTo("=SUM(A1)");
        assertThat(section(document, "alerts").rows().get(0).get(3)).isEqualTo("=run");
        assertThat(section(document, "alerts").rows().get(0).get(4)).isEqualTo("@引擎回報：-1");
    }

    // ── 與 CSV 同源：同一組資料產出的兩種格式，逐區段逐列逐欄比對 ──────────────────────────────

    /** RFC 4180 的最小解析（夠用於本測試的資料：支援雙引號包起的欄位內含逗號與雙引號）。 */
    private static List<String> fields(String line) {
        List<String> out = new ArrayList<>();
        StringBuilder cur = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (quoted) {
                if (c == '"' && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    cur.append('"');
                    i++;
                } else if (c == '"') {
                    quoted = false;
                } else {
                    cur.append(c);
                }
            } else if (c == '"') {
                quoted = true;
            } else if (c == ',') {
                out.add(cur.toString());
                cur.setLength(0);
            } else {
                cur.append(c);
            }
        }
        out.add(cur.toString());
        return out;
    }

    /** CSV 欄位換算成 PDF 顯示：空字串→破折號；注入防護的前導單引號去掉。 */
    private static String asPdfCell(String csvField) {
        if (csvField.isEmpty()) {
            return ReportPdfModel.NULL_MARK;
        }
        if (csvField.length() > 1 && csvField.charAt(0) == '\'' && "=+-@".indexOf(csvField.charAt(1)) >= 0) {
            return csvField.substring(1);
        }
        return csvField;
    }

    @Test
    void sectionByRowByCellThePdfModelEqualsTheCsvOfTheSameData() {
        String csv = new String(ReportCsv.build("監控專案", FROM, TO, RUN, metrics(), RUNS, TASKS, ALERTS),
                StandardCharsets.UTF_8).substring(1);
        List<String> lines = List.of(csv.split("\r\n", -1));
        Document document = model(RUN);

        for (Section section : document.sections()) {
            int start = lines.indexOf("#section," + section.name());
            assertThat(start).as(section.name()).isGreaterThanOrEqualTo(0);
            assertThat(fields(lines.get(start + 1))).as(section.name() + " 欄名").isEqualTo(section.headers());
            List<List<String>> expected = new ArrayList<>();
            for (int i = start + 2; i < lines.size() && !lines.get(i).isEmpty(); i++) {
                expected.add(fields(lines.get(i)).stream().map(ReportPdfModelTest::asPdfCell).toList());
            }
            assertThat(section.rows()).as(section.name() + " 資料列").isEqualTo(expected);
        }
    }
}
