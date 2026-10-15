package com.aisdlc.console.adapter.out.document;

import com.aisdlc.console.application.port.out.DocumentTextExtractor;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.encryption.InvalidPasswordException;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.poi.xwpf.usermodel.IBodyElement;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFTable;
import org.apache.poi.xwpf.usermodel.XWPFTableCell;
import org.apache.poi.xwpf.usermodel.XWPFTableRow;
import org.springframework.stereotype.Component;

import java.io.ByteArrayInputStream;
import java.io.IOException;

/**
 * {@link DocumentTextExtractor} 的 PDFBox 3.x／POI（XWPF）實作（契約 §1.1.1）。
 *
 * <ul>
 *   <li>PDF：逐頁抽文字；需要密碼（或禁止抽取內容）→ {@code ENCRYPTED}；其餘解析例外 → {@code CORRUPT}。
 *       掃描檔沒有文字層，抽出空字串，由用例回 {@code 無法從檔案擷取文字}。</li>
 *   <li>DOCX：依文件順序抽段落與表格儲存格文字（儲存格以 tab 分隔、段落與列以換行）；任何解析例外 → {@code CORRUPT}。</li>
 * </ul>
 */
@Component
class DocumentTextExtractorAdapter implements DocumentTextExtractor {

    @Override
    public String extractPdf(byte[] content) {
        try (PDDocument document = Loader.loadPDF(content)) {
            if (document.isEncrypted() && !document.getCurrentAccessPermission().canExtractContent()) {
                throw new ExtractionException(ExtractionException.Kind.ENCRYPTED, "PDF 禁止抽取內容", null);
            }
            return new PDFTextStripper().getText(document);
        } catch (ExtractionException e) {
            throw e;
        } catch (InvalidPasswordException e) {
            throw new ExtractionException(ExtractionException.Kind.ENCRYPTED, "PDF 需要密碼", e);
        } catch (IOException | RuntimeException e) {
            throw new ExtractionException(ExtractionException.Kind.CORRUPT, "PDF 無法解析", e);
        }
    }

    @Override
    public String extractDocx(byte[] content) {
        try (XWPFDocument document = new XWPFDocument(new ByteArrayInputStream(content))) {
            StringBuilder out = new StringBuilder();
            for (IBodyElement element : document.getBodyElements()) {
                if (element instanceof XWPFParagraph paragraph) {
                    out.append(paragraph.getText()).append('\n');
                } else if (element instanceof XWPFTable table) {
                    for (XWPFTableRow row : table.getRows()) {
                        boolean first = true;
                        for (XWPFTableCell cell : row.getTableCells()) {
                            if (!first) {
                                out.append('\t');
                            }
                            first = false;
                            out.append(cell.getText());
                        }
                        out.append('\n');
                    }
                }
            }
            return out.toString();
        } catch (IOException | RuntimeException e) {
            throw new ExtractionException(ExtractionException.Kind.CORRUPT, "DOCX 無法解析", e);
        }
    }
}
