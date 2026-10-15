package com.aisdlc.console.adapter.out.document;

import com.aisdlc.console.application.port.out.ReportPdfRenderer;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDDocumentInformation;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.font.PDType0Font;
import org.springframework.stereotype.Component;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * {@link ReportPdfRenderer} 的 Apache PDFBox 3 實作（契約 §1.3.7，C-4）：A4 橫向、純文字表格，四個區段依序輸出，
 * 長表格自動換頁並重複表頭，過長的儲存格在欄內折行（儲存格的文字連續輸出，複製貼上與文字擷取都讀得到完整的一段）。
 *
 * <p><b>字型</b>：內嵌 Noto Sans TC Regular（SIL OFL 1.1；檔案與授權文字在 {@code resources/fonts/}），以
 * {@link PDType0Font#load} 的子集嵌入載入——PDF 只帶實際用到的字形，繁體中文專案名稱與告警訊息可正常顯示與被文字擷取。
 * 字型沒有的字元（例如 emoji）與控制字元一律印成 {@code ?}，<b>不會讓整份報表失敗</b>；內嵌字型資源缺失則是打包錯誤，
 * 大聲失敗（{@link IllegalStateException}）而不是悄悄退回別的字型。
 */
@Component
class PdfBoxReportRenderer implements ReportPdfRenderer {

    static final String FONT_RESOURCE = "/fonts/NotoSansTC-Regular.ttf";
    static final String REPLACEMENT = "?";
    static final String EMPTY_SECTION = "（無資料）";

    private static final PDRectangle PAGE = new PDRectangle(PDRectangle.A4.getHeight(), PDRectangle.A4.getWidth());
    private static final float MARGIN = 36f;
    private static final float TITLE_SIZE = 16f;
    private static final float INFO_SIZE = 9f;
    private static final float HEADING_SIZE = 11f;
    /** 表格內文：runs 區段有 12 欄（含 36 字元的 UUID 與兩個 ISO 時間），7pt 讓典型資料不必折行就放得進 A4 橫向。 */
    private static final float BODY_SIZE = 7f;
    private static final float CELL_PAD = 3f;
    private static final float LEADING = 1.35f;
    private static final float SECTION_GAP = 10f;
    /** 浮點數的量測誤差容忍：恰好等於自然寬度的文字不應該被誤判成「超出」而多折一個字。 */
    private static final float WRAP_EPSILON = 0.05f;

    @Override
    public byte[] render(Document document) {
        try (PDDocument pdf = new PDDocument(); InputStream fontStream = openFont()) {
            PDDocumentInformation info = pdf.getDocumentInformation();
            info.setTitle(document.title());
            info.setCreator("AISDLC Agent Console");
            PDType0Font font = PDType0Font.load(pdf, fontStream, true);
            new Layout(pdf, font).draw(document);
            ByteArrayOutputStream out = new ByteArrayOutputStream(64 * 1024);
            pdf.save(out);
            return out.toByteArray();
        } catch (IOException e) {
            throw new IllegalStateException("監控報表 PDF 產生失敗", e);
        }
    }

    private static InputStream openFont() {
        InputStream stream = PdfBoxReportRenderer.class.getResourceAsStream(FONT_RESOURCE);
        if (stream == null) {
            throw new IllegalStateException("找不到內嵌字型資源 " + FONT_RESOURCE + "（打包錯誤：PDF 報表需要它）");
        }
        return stream;
    }

    /** 一份文件的版面狀態：目前頁的內容串流與游標，以及字元可否編碼／寬度的快取。 */
    private static final class Layout {

        private final PDDocument pdf;
        private final PDType0Font font;
        private final Map<Integer, Boolean> encodable = new HashMap<>();
        private final Map<Integer, Float> glyphWidth = new HashMap<>();
        private PDPageContentStream cs;
        private float y;
        /** 目前表格的表頭（換頁時重畫）；沒有表格進行中為 null。 */
        private List<List<String>> repeatHeader;
        private float[] repeatWidths;
        private boolean drawingHeader;

        Layout(PDDocument pdf, PDType0Font font) {
            this.pdf = pdf;
            this.font = font;
        }

        void draw(Document document) throws IOException {
            newPage();
            try {
                paragraph(document.title(), TITLE_SIZE);
                for (String line : document.infoLines()) {
                    paragraph(line, INFO_SIZE);
                }
                for (Section section : document.sections()) {
                    y -= SECTION_GAP;
                    table(section);
                }
            } finally {
                cs.close();
            }
        }

        // ── 頁面 ───────────────────────────────────────────────────────────────

        private void newPage() throws IOException {
            if (cs != null) {
                cs.close();
            }
            PDPage page = new PDPage(PAGE);
            pdf.addPage(page);
            cs = new PDPageContentStream(pdf, page);
            y = PAGE.getHeight() - MARGIN;
        }

        /** 目前頁剩下的高度不夠 {@code needed} 就換頁（表格進行中則在新頁重畫表頭）。 */
        private void ensureRoom(float needed) throws IOException {
            if (y - needed >= MARGIN) {
                return;
            }
            newPage();
            if (repeatHeader != null && !drawingHeader) {
                drawingHeader = true;
                drawRow(repeatHeader, repeatWidths, true);
                drawingHeader = false;
            }
        }

        private static float contentWidth() {
            return PAGE.getWidth() - 2 * MARGIN;
        }

        private static float leading(float size) {
            return size * LEADING;
        }

        // ── 段落與表格 ─────────────────────────────────────────────────────────

        private void paragraph(String text, float size) throws IOException {
            for (String line : wrap(text, contentWidth(), size)) {
                ensureRoom(leading(size));
                drawLines(List.of(line), 0, 1, MARGIN, y, size);
                y -= leading(size);
            }
        }

        private void table(Section section) throws IOException {
            float[] widths = columnWidths(section);
            List<List<String>> header = wrapCells(section.headers(), widths);
            int headerLines = header.stream().mapToInt(List::size).max().orElse(1);
            ensureRoom(leading(HEADING_SIZE) + (headerLines + 1) * leading(BODY_SIZE));
            paragraph(section.name(), HEADING_SIZE);
            drawRow(header, widths, true);
            repeatHeader = header;
            repeatWidths = widths;
            try {
                if (section.rows().isEmpty()) {
                    ensureRoom(leading(BODY_SIZE));
                    drawLines(List.of(clean(EMPTY_SECTION)), 0, 1, MARGIN + CELL_PAD, y, BODY_SIZE);
                    y -= leading(BODY_SIZE);
                }
                for (List<String> row : section.rows()) {
                    drawRow(wrapCells(row, widths), widths, false);
                }
            } finally {
                repeatHeader = null;
                repeatWidths = null;
            }
        }

        /**
         * 一列：{@code cells} 是每欄折行後的行。過高的列可以跨頁——每頁取「放得下的行數」為一塊，同一塊內<b>逐欄</b>輸出
         * （每個儲存格的文字連續，不與別欄交錯）；表頭列加底色，整列結束後畫一條細線。
         */
        private void drawRow(List<List<String>> cells, float[] widths, boolean header) throws IOException {
            float lead = leading(BODY_SIZE);
            float tableWidth = 0;
            for (float w : widths) {
                tableWidth += w;
            }
            int total = cells.stream().mapToInt(List::size).max().orElse(1);
            int done = 0;
            while (done < total) {
                ensureRoom(lead);
                int chunk = Math.min(Math.max(1, (int) ((y - MARGIN) / lead)), total - done);
                if (header) {
                    cs.setNonStrokingColor(0.88f);
                    cs.addRect(MARGIN, y - chunk * lead, tableWidth, chunk * lead);
                    cs.fill();
                    cs.setNonStrokingColor(0f);
                }
                float x = MARGIN;
                for (int c = 0; c < cells.size(); c++) {
                    drawLines(cells.get(c), done, Math.min(done + chunk, cells.get(c).size()), x + CELL_PAD, y,
                            BODY_SIZE);
                    x += widths[c];
                }
                y -= chunk * lead;
                done += chunk;
            }
            cs.setStrokingColor(0.7f);
            cs.setLineWidth(0.4f);
            cs.moveTo(MARGIN, y);
            cs.lineTo(MARGIN + tableWidth, y);
            cs.stroke();
            y -= 1.5f;
        }

        /** 把 {@code lines[from, to)} 連續畫成一個文字物件（第一行的頂端在 {@code top}）；行文字須已經過 {@link #clean}。 */
        private void drawLines(List<String> lines, int from, int to, float x, float top, float size)
                throws IOException {
            if (from >= to) {
                return;
            }
            cs.beginText();
            cs.setFont(font, size);
            cs.newLineAtOffset(x, top - size);
            for (int i = from; i < to; i++) {
                if (i > from) {
                    cs.newLineAtOffset(0, -leading(size));
                }
                if (!lines.get(i).isEmpty()) {
                    cs.showText(lines.get(i));
                }
            }
            cs.endText();
        }

        // ── 欄寬與折行 ─────────────────────────────────────────────────────────

        /**
         * 欄寬：每欄至少是<b>表頭文字的寬度</b>（欄名不被攔腰折斷），再往上到「內容的自然寬度」為止；總寬超過頁面時，
         * 超出表頭的那部分「需求」以注水法分配（需求不超過均分額的欄如數滿足，其餘欄平分剩下的寬度）——
         * 長文字欄被折行，短欄不被犧牲。
         */
        private float[] columnWidths(Section section) {
            int n = section.headers().size();
            float[] floor = new float[n];
            float[] want = new float[n];
            for (int c = 0; c < n; c++) {
                floor[c] = naturalWidth(section.headers().get(c));
                want[c] = floor[c];
            }
            for (List<String> row : section.rows()) {
                for (int c = 0; c < n && c < row.size(); c++) {
                    want[c] = Math.max(want[c], naturalWidth(row.get(c)));
                }
            }
            float available = contentWidth();
            float floorSum = sum(floor);
            float[] widths = new float[n];
            if (floorSum >= available) {
                for (int c = 0; c < n; c++) {
                    widths[c] = floor[c] * available / floorSum;
                }
                return widths;
            }
            float[] demand = new float[n];
            for (int c = 0; c < n; c++) {
                demand[c] = want[c] - floor[c];
            }
            float budget = available - floorSum;
            if (sum(demand) <= budget) {
                return want;
            }
            float[] granted = waterFill(demand, budget);
            for (int c = 0; c < n; c++) {
                widths[c] = floor[c] + granted[c];
            }
            return widths;
        }

        /** 注水：需求不超過目前均分額的項目如數滿足並退出，其餘項目依各自需求的比例分剩下的額度。 */
        private static float[] waterFill(float[] demand, float budget) {
            int n = demand.length;
            float[] granted = new float[n];
            boolean[] settled = new boolean[n];
            float remaining = budget;
            int open = n;
            boolean changed = true;
            while (changed && open > 0) {
                changed = false;
                float share = remaining / open;
                for (int c = 0; c < n; c++) {
                    if (!settled[c] && demand[c] <= share) {
                        granted[c] = demand[c];
                        settled[c] = true;
                        remaining -= demand[c];
                        open--;
                        changed = true;
                    }
                }
            }
            float openDemand = 0;
            for (int c = 0; c < n; c++) {
                if (!settled[c]) {
                    openDemand += demand[c];
                }
            }
            for (int c = 0; c < n; c++) {
                if (!settled[c]) {
                    granted[c] = remaining * demand[c] / openDemand;
                }
            }
            return granted;
        }

        private static float sum(float[] values) {
            float total = 0;
            for (float v : values) {
                total += v;
            }
            return total;
        }

        private float naturalWidth(String text) {
            float widest = 0;
            for (String line : clean(text).split("\n", -1)) {
                widest = Math.max(widest, textWidth(line, BODY_SIZE));
            }
            return widest + 2 * CELL_PAD;
        }

        private List<List<String>> wrapCells(List<String> cells, float[] widths) {
            List<List<String>> wrapped = new ArrayList<>(widths.length);
            for (int c = 0; c < widths.length; c++) {
                wrapped.add(wrap(c < cells.size() ? cells.get(c) : "", widths[c] - 2 * CELL_PAD, BODY_SIZE));
            }
            return wrapped;
        }

        /** 依寬度折行：明確的換行先切開，其餘貪婪填滿，盡量在空白處斷行，沒有空白就在任意字元處斷（CJK 本來就沒有空白）。 */
        private List<String> wrap(String text, float maxWidth, float size) {
            List<String> lines = new ArrayList<>();
            for (String logical : clean(text).split("\n", -1)) {
                StringBuilder line = new StringBuilder();
                float lineWidth = 0;
                int lastSpace = -1;
                for (int i = 0; i < logical.length(); ) {
                    int cp = logical.codePointAt(i);
                    i += Character.charCount(cp);
                    float cw = charWidth(cp) * size / 1000f;
                    if (lineWidth + cw > maxWidth + WRAP_EPSILON && line.length() > 0) {
                        if (lastSpace > 0 && cp != ' ') {
                            String rest = line.substring(lastSpace);
                            lines.add(line.substring(0, lastSpace).stripTrailing());
                            line = new StringBuilder(rest);
                            lineWidth = textWidth(rest, size);
                        } else {
                            lines.add(line.toString());
                            line = new StringBuilder();
                            lineWidth = 0;
                        }
                        lastSpace = -1;
                    }
                    line.appendCodePoint(cp);
                    lineWidth += cw;
                    if (cp == ' ') {
                        lastSpace = line.length();
                    }
                }
                lines.add(line.toString());
            }
            return lines;
        }

        // ── 字元 ───────────────────────────────────────────────────────────────

        /** 換行統一為 {@code \n}、tab 變空白、其他控制字元與字型沒有的字元一律變 {@code ?}。 */
        private String clean(String raw) {
            if (raw == null) {
                return "";
            }
            StringBuilder out = new StringBuilder(raw.length());
            int i = 0;
            while (i < raw.length()) {
                int cp = raw.codePointAt(i);
                i += Character.charCount(cp);
                if (cp == '\r') {
                    if (i < raw.length() && raw.charAt(i) == '\n') {
                        i++;
                    }
                    out.append('\n');
                } else if (cp == '\n') {
                    out.append('\n');
                } else if (cp == '\t') {
                    out.append(' ');
                } else if (Character.isISOControl(cp) || !isEncodable(cp)) {
                    out.append(REPLACEMENT);
                } else {
                    out.appendCodePoint(cp);
                }
            }
            return out.toString();
        }

        private boolean isEncodable(int codePoint) {
            return encodable.computeIfAbsent(codePoint, cp -> {
                try {
                    font.encode(new String(Character.toChars(cp)));
                    return true;
                } catch (IllegalArgumentException | IOException e) {
                    return false;
                }
            });
        }

        /** 單一字元寬度（1/1000 em）。 */
        private float charWidth(int codePoint) {
            return glyphWidth.computeIfAbsent(codePoint, cp -> {
                try {
                    return font.getStringWidth(new String(Character.toChars(cp)));
                } catch (IllegalArgumentException | IOException e) {
                    return 0f;
                }
            });
        }

        private float textWidth(String text, float size) {
            float total = 0;
            for (int i = 0; i < text.length(); ) {
                int cp = text.codePointAt(i);
                i += Character.charCount(cp);
                total += charWidth(cp);
            }
            return total * size / 1000f;
        }
    }
}
