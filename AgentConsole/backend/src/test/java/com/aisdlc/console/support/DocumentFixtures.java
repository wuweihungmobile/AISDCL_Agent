package com.aisdlc.console.support;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.encryption.AccessPermission;
import org.apache.pdfbox.pdmodel.encryption.StandardProtectionPolicy;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.apache.pdfbox.pdmodel.font.Standard14Fonts;
import org.apache.poi.xwpf.usermodel.XWPFDocument;

import java.io.ByteArrayOutputStream;
import java.io.IOException;

/** 在測試期用 PDFBox／POI 現場產生 PDF 與 DOCX（不入庫二進位檔）。 */
public final class DocumentFixtures {

    private DocumentFixtures() {
    }

    /** 單頁 PDF，每個字串一行（Helvetica：只放 ASCII，避免字型缺字）。 */
    public static byte[] pdfWith(String... lines) {
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
        } catch (IOException e) {
            throw new IllegalStateException("無法產生測試用 PDF", e);
        }
    }

    /** 有一頁、但沒有任何文字層的 PDF（等同掃描檔）。 */
    public static byte[] pdfWithoutText() {
        try (PDDocument document = new PDDocument()) {
            document.addPage(new PDPage());
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            document.save(out);
            return out.toByteArray();
        } catch (IOException e) {
            throw new IllegalStateException("無法產生測試用 PDF", e);
        }
    }

    /** 需要使用者密碼才能開啟的 PDF。 */
    public static byte[] passwordProtectedPdf(String userPassword) {
        try (PDDocument document = new PDDocument()) {
            document.addPage(new PDPage());
            StandardProtectionPolicy policy = new StandardProtectionPolicy("owner-pw", userPassword,
                    new AccessPermission());
            policy.setEncryptionKeyLength(128);
            document.protect(policy);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            document.save(out);
            return out.toByteArray();
        } catch (IOException e) {
            throw new IllegalStateException("無法產生測試用的加密 PDF", e);
        }
    }

    /** DOCX，每個字串一個段落。 */
    public static byte[] docxWith(String... paragraphs) {
        try (XWPFDocument document = new XWPFDocument()) {
            for (String paragraph : paragraphs) {
                document.createParagraph().createRun().setText(paragraph);
            }
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            document.write(out);
            return out.toByteArray();
        } catch (IOException e) {
            throw new IllegalStateException("無法產生測試用 DOCX", e);
        }
    }
}
