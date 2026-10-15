package com.aisdlc.console.adapter.out.document;

import com.aisdlc.console.application.port.out.DocumentTextExtractor.ExtractionException;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.encryption.AccessPermission;
import org.apache.pdfbox.pdmodel.encryption.StandardProtectionPolicy;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.apache.pdfbox.pdmodel.font.Standard14Fonts;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFTable;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 檔案文字擷取（契約 §1.1.1）。測試檔在測試期用 PDFBox／POI 現場產生（不入庫二進位檔）。
 * 為什麼重要：匯入的原文就是之後 AI 解析的唯一輸入——表格內容漏抽、順序錯亂、加密／損毀檔無聲變成空字串，
 * 都會讓使用者拿到一份「看起來解析成功、其實少了一半需求」的草案。
 */
class DocumentTextExtractorAdapterTest {

    private final DocumentTextExtractorAdapter extractor = new DocumentTextExtractorAdapter();

    private static byte[] pdfWith(String... lines) throws IOException {
        try (PDDocument document = new PDDocument()) {
            PDPage page = new PDPage();
            document.addPage(page);
            try (PDPageContentStream stream = new PDPageContentStream(document, page)) {
                stream.beginText();
                stream.setFont(new PDType1Font(Standard14Fonts.FontName.HELVETICA), 12);
                stream.setLeading(16f);
                stream.newLineAtOffset(50, 700);
                for (String line : lines) {
                    stream.showText(line);
                    stream.newLine();
                }
                stream.endText();
            }
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            document.save(out);
            return out.toByteArray();
        }
    }

    private static byte[] pdfWithPasswords(String owner, String user, boolean allowExtraction) throws IOException {
        try (PDDocument document = new PDDocument()) {
            document.addPage(new PDPage());
            AccessPermission permission = new AccessPermission();
            permission.setCanExtractContent(allowExtraction);
            StandardProtectionPolicy policy = new StandardProtectionPolicy(owner, user, permission);
            policy.setEncryptionKeyLength(128);
            document.protect(policy);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            document.save(out);
            return out.toByteArray();
        }
    }

    // ── PDF ──────────────────────────────────────────────────────────────────

    @Test
    void aPdfYieldsItsTextInReadingOrder() throws IOException {
        String text = extractor.extractPdf(pdfWith("Requirement One", "Requirement Two"));
        assertThat(text).contains("Requirement One").contains("Requirement Two");
        assertThat(text.indexOf("Requirement One")).isLessThan(text.indexOf("Requirement Two"));
    }

    @Test
    void aPdfWithoutATextLayerYieldsBlankTextForTheUseCaseToReject() throws IOException {
        try (PDDocument document = new PDDocument()) {
            document.addPage(new PDPage());
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            document.save(out);
            assertThat(extractor.extractPdf(out.toByteArray()).isBlank()).isTrue();
        }
    }

    @Test
    void aPasswordProtectedPdfIsReportedAsEncrypted() throws IOException {
        byte[] encrypted = pdfWithPasswords("owner-pw", "user-pw", true);
        assertThatThrownBy(() -> extractor.extractPdf(encrypted)).isInstanceOfSatisfying(ExtractionException.class,
                e -> assertThat(e.kind()).isEqualTo(ExtractionException.Kind.ENCRYPTED));
    }

    @Test
    void aPdfThatForbidsExtractingContentIsReportedAsEncrypted() throws IOException {
        byte[] restricted = pdfWithPasswords("owner-pw", "", false);
        assertThatThrownBy(() -> extractor.extractPdf(restricted)).isInstanceOfSatisfying(ExtractionException.class,
                e -> assertThat(e.kind()).isEqualTo(ExtractionException.Kind.ENCRYPTED));
    }

    @Test
    void aBrokenPdfIsReportedAsCorrupt() {
        byte[] broken = "%PDF-1.7\nthis is definitely not a pdf body".getBytes(StandardCharsets.UTF_8);
        assertThatThrownBy(() -> extractor.extractPdf(broken)).isInstanceOfSatisfying(ExtractionException.class,
                e -> assertThat(e.kind()).isEqualTo(ExtractionException.Kind.CORRUPT));
    }

    // ── DOCX ─────────────────────────────────────────────────────────────────

    @Test
    void aDocxYieldsParagraphsAndTableCellsInDocumentOrderWithTabsBetweenCells() throws IOException {
        try (XWPFDocument document = new XWPFDocument()) {
            XWPFParagraph first = document.createParagraph();
            first.createRun().setText("需求標題");
            XWPFTable table = document.createTable(2, 2);
            table.getRow(0).getCell(0).setText("功能");
            table.getRow(0).getCell(1).setText("優先級");
            table.getRow(1).getCell(0).setText("登入");
            table.getRow(1).getCell(1).setText("P0");
            document.createParagraph().createRun().setText("結尾段落");
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            document.write(out);

            String text = extractor.extractDocx(out.toByteArray());

            assertThat(text).isEqualTo("需求標題\n功能\t優先級\n登入\tP0\n結尾段落\n");
        }
    }

    @Test
    void aDocxWithOnlyEmptyParagraphsYieldsBlankText() throws IOException {
        try (XWPFDocument document = new XWPFDocument()) {
            document.createParagraph();
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            document.write(out);
            assertThat(extractor.extractDocx(out.toByteArray()).isBlank()).isTrue();
        }
    }

    @Test
    void aBrokenDocxIsReportedAsCorrupt() {
        byte[] broken = {'P', 'K', 3, 4, 1, 2, 3, 4, 5, 6, 7, 8};
        assertThatThrownBy(() -> extractor.extractDocx(broken)).isInstanceOfSatisfying(ExtractionException.class,
                e -> assertThat(e.kind()).isEqualTo(ExtractionException.Kind.CORRUPT));
    }
}
