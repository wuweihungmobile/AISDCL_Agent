package com.aisdlc.console.adapter.out.document;

import com.aisdlc.console.application.port.out.ReportPdfRenderer.Document;
import com.aisdlc.console.application.port.out.ReportPdfRenderer.Section;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.pdfbox.text.TextPosition;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 監控報表的 PDF 轉譯（契約 §1.3.7，C-4）。為什麼重要：報表是給人看、給人存檔的——中文專案名稱與告警訊息若變成亂碼或空白就失去意義；
 * 寬表格若畫出頁面右緣，使用者看到的是被截斷的數字；一個字型沒有的字元（emoji）若讓整份報表失敗，使用者就拿不到任何報表。
 * 測試以 PDFBox 把產出的檔案再讀回來（文字擷取＋逐字位置），驗證的是「使用者實際看得到什麼」，不是內部畫了幾個指令。
 */
class PdfBoxReportRendererTest {

    private static final float PAGE_WIDTH = 841.89f;
    private static final float MARGIN = 36f;

    private final PdfBoxReportRenderer renderer = new PdfBoxReportRenderer();

    private static Section section(String name, List<String> headers, List<List<String>> rows) {
        return new Section(name, headers, rows);
    }

    private static Document document(Section... sections) {
        return new Document("監控專案 Alpha 監控報表",
                List.of("時間範圍：2026-10-13T00:00:00Z ～ 2026-10-15T00:00:00Z", "範圍：全部批次",
                        "產生時間（UTC）：2026-10-15T08:00:00Z"),
                List.of(sections));
    }

    private static Section summary() {
        return section("summary", List.of("metric", "value", "previousValue", "delta", "unit"),
                List.of(List.of("taskCompletionRate", "100.0", "0.0", "100.0", "PERCENT"),
                        List.of("totalTokens", "5720", "0", "5720", "TOKENS"),
                        List.of("tokenBudgetUsageRate", "31.8", "—", "—", "PERCENT")));
    }

    private static String text(byte[] pdf) throws IOException {
        try (PDDocument document = Loader.loadPDF(pdf)) {
            return new PDFTextStripper().getText(document);
        }
    }

    private static String squeezed(String text) {
        return text.replaceAll("\\s+", "");
    }

    // ── 內容看得見 ────────────────────────────────────────────────────────────────

    @Test
    void theOutputIsAPdfWhoseExtractedTextCarriesTheChineseTitleTheSectionNamesAndTheValues() throws IOException {
        Section tasks = section("tasks", List.of("goalName", "taskName", "status"),
                List.of(List.of("基礎", "初始化專案骨架", "COMPLETED")));

        byte[] pdf = renderer.render(document(summary(), tasks));

        assertThat(new String(pdf, 0, 5, StandardCharsets.US_ASCII)).isEqualTo("%PDF-");
        String extracted = text(pdf);
        assertThat(extracted).contains("監控專案 Alpha 監控報表").contains("時間範圍：").contains("全部批次")
                .contains("產生時間（UTC）：2026-10-15T08:00:00Z");
        assertThat(extracted).contains("summary").contains("tasks");
        assertThat(extracted).contains("metric").contains("previousValue").contains("totalTokens").contains("5720")
                .contains("31.8");
        assertThat(extracted).contains("基礎").contains("初始化專案骨架").contains("COMPLETED");
        assertThat(extracted).as("null 的破折號原樣顯示").contains("—");
    }

    @Test
    void theFileCarriesOnlyTheGlyphsItUsesNotTheWholeSevenMegabyteFont() {
        byte[] pdf = renderer.render(document(summary()));

        assertThat(pdf.length).as("子集嵌入：只帶用到的字形").isLessThan(600_000);
    }

    @Test
    void aPageIsA4LandscapeAndAnEmptySectionStillShowsItsHeaderAndANoDataMarker() throws IOException {
        Section empty = section("alerts", List.of("createdAt", "severity", "message"), List.of());

        byte[] pdf = renderer.render(document(empty));

        try (PDDocument loaded = Loader.loadPDF(pdf)) {
            assertThat(loaded.getNumberOfPages()).isEqualTo(1);
            assertThat(loaded.getPage(0).getMediaBox().getWidth()).isGreaterThan(loaded.getPage(0).getMediaBox().getHeight());
            assertThat(loaded.getDocumentInformation().getTitle()).isEqualTo("監控專案 Alpha 監控報表");
        }
        String extracted = text(pdf);
        assertThat(extracted).contains("alerts").contains("createdAt").contains("severity").contains("message");
        assertThat(extracted).contains(PdfBoxReportRenderer.EMPTY_SECTION);
    }

    // ── 不因字元而失敗 ─────────────────────────────────────────────────────────────

    @Test
    void charactersTheFontLacksAndControlCharactersBecomeQuestionMarksAndNeverFailTheReport() throws IOException {
        String emoji = new String(Character.toChars(0x1F600));
        String control = String.valueOf((char) 1);
        Section alerts = section("alerts", List.of("subject", "message"),
                List.of(List.of("run:1", "前" + emoji + "後"), List.of("run:2", "a" + control + "b"),
                        List.of("run:3", "tab\tseparated")));

        byte[] pdf = renderer.render(document(alerts));

        String extracted = squeezed(text(pdf));
        assertThat(extracted).contains("前?後").contains("a?b").contains("tabseparated");
        assertThat(extracted).doesNotContain(emoji);
    }

    @Test
    void aLineBreakInsideACellStartsANewLineInsideThatCellAndNothingElseMoves() throws IOException {
        Section tasks = section("tasks", List.of("taskName", "status"),
                List.of(List.of("第一行\r\n第二行\n第三行", "FAILED"), List.of("下一列", "COMPLETED")));

        String extracted = text(renderer.render(document(tasks)));

        assertThat(extracted).contains("第一行").contains("第二行").contains("第三行").contains("下一列");
        assertThat(extracted.indexOf("第三行")).isLessThan(extracted.indexOf("下一列"));
    }

    // ── 版面 ───────────────────────────────────────────────────────────────────────

    /** 逐字記錄文字畫在頁面的哪個範圍。 */
    private static final class Extent extends PDFTextStripper {

        private float left = Float.MAX_VALUE;
        private float right;

        Extent() throws IOException {
            super();
        }

        @Override
        protected void writeString(String text, List<TextPosition> positions) throws IOException {
            for (TextPosition position : positions) {
                left = Math.min(left, position.getXDirAdj());
                right = Math.max(right, position.getXDirAdj() + position.getWidthDirAdj());
            }
            super.writeString(text, positions);
        }
    }

    private static Extent extentOf(byte[] pdf) throws IOException {
        try (PDDocument document = Loader.loadPDF(pdf)) {
            Extent extent = new Extent();
            extent.getText(document);
            return extent;
        }
    }

    @Test
    void aWideTableWithALongMessageNeverDrawsOutsideThePageMargins() throws IOException {
        String uuid = "22222222-2222-2222-2222-222222222222";
        Section runs = section("runs", List.of("runNumber", "runId", "status", "autonomyLevel", "startedAt",
                        "completedAt", "durationSec", "totalTokensUsed", "tokenBudget", "tasksTotal", "tasksCompleted",
                        "tasksFailed"),
                List.of(List.of("1", uuid, "COMPLETED", "4", "2026-10-13T09:00:00.123456789Z",
                        "2026-10-13T11:00:00.123456789Z", "7200", "123456789012", "999999999999", "500", "500", "0")));
        String longMessage = ("引擎升級（ESCALATION）：連續失敗 " + "boom ".repeat(120)).trim();
        Section alerts = section("alerts", List.of("createdAt", "severity", "rule", "subject", "message",
                        "acknowledged", "acknowledgedBy", "acknowledgedAt"),
                List.of(List.of("2026-10-13T10:30:30Z", "CRITICAL", "ENGINE_ESCALATION", "step:G1-T2", longMessage,
                        "true", "operator", "2026-10-13T12:00:00Z")));

        byte[] pdf = renderer.render(document(runs, alerts));

        Extent extent = extentOf(pdf);
        assertThat(extent.left).isGreaterThanOrEqualTo(MARGIN - 0.5f);
        assertThat(extent.right).as("最右邊的字不得超出頁面右緣的邊界").isLessThanOrEqualTo(PAGE_WIDTH - MARGIN + 0.5f);
        String extracted = squeezed(text(pdf));
        assertThat(extracted).as("折行不是截斷，而且同一個儲存格的文字連續").contains(squeezed(longMessage));
        assertThat(extracted).contains(uuid).contains("123456789012").contains("999999999999");
    }

    @Test
    void aLongTableBreaksAcrossPagesAndRepeatsItsHeaderOnEveryPage() throws IOException {
        List<List<String>> rows = new ArrayList<>();
        for (int i = 1; i <= 150; i++) {
            rows.add(List.of(String.valueOf(i), "任務 " + i, "COMPLETED"));
        }
        Section tasks = section("tasks", List.of("seq", "taskName", "status"), rows);

        byte[] pdf = renderer.render(document(tasks));

        try (PDDocument loaded = Loader.loadPDF(pdf)) {
            assertThat(loaded.getNumberOfPages()).isGreaterThanOrEqualTo(3);
            for (int page = 1; page <= loaded.getNumberOfPages(); page++) {
                PDFTextStripper stripper = new PDFTextStripper();
                stripper.setStartPage(page);
                stripper.setEndPage(page);
                String pageText = stripper.getText(loaded);
                assertThat(pageText).as("第 " + page + " 頁").contains("seq").contains("taskName").contains("status");
            }
        }
        String all = text(pdf);
        assertThat(all).contains("任務 1").contains("任務 150");
        assertThat(all.indexOf("任務 75")).isLessThan(all.indexOf("任務 76"));
    }

    @Test
    void aSingleRowTallerThanAPageFlowsOntoTheNextPageInsteadOfOverflowing() throws IOException {
        String huge = ("很長的說明 " + "x".repeat(30) + " ").repeat(400);
        Section alerts = section("alerts", List.of("subject", "message"), List.of(List.of("run:1", huge)));

        byte[] pdf = renderer.render(document(alerts));

        try (PDDocument loaded = Loader.loadPDF(pdf)) {
            assertThat(loaded.getNumberOfPages()).isGreaterThanOrEqualTo(2);
        }
        String extracted = text(pdf);
        assertThat(extracted.split("很長的說明", -1).length - 1).as("四百段一段不少（換頁處只多出重複的表頭）").isEqualTo(400);
    }

    @Test
    void anOverlyLongTitleWrapsInsteadOfRunningOffThePage() throws IOException {
        Document longTitle = new Document("極長的專案名稱".repeat(40) + " 監控報表", List.of("範圍：全部批次"), List.of(summary()));

        byte[] pdf = renderer.render(longTitle);

        assertThat(extentOf(pdf).right).isLessThanOrEqualTo(PAGE_WIDTH - MARGIN + 0.5f);
        assertThat(squeezed(text(pdf))).contains(squeezed("極長的專案名稱".repeat(40) + " 監控報表"));
    }
}
