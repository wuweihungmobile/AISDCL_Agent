package com.aisdlc.console.application.port.out;

/**
 * 檔案文字擷取埠（匯入 upload；契約 §1.1.1）。呼叫端已驗副檔名、大小與魔術位元組；
 * 實作只負責把二進位文件轉成純文字（可能是空字串，是否算「無法擷取文字」由用例判斷）。
 */
public interface DocumentTextExtractor {

    /** 擷取失敗：加密的 PDF 或損毀的檔案。 */
    final class ExtractionException extends RuntimeException {

        private static final long serialVersionUID = 1L;

        /** ENCRYPTED＝PDF 需要密碼；CORRUPT＝解析例外。 */
        public enum Kind { ENCRYPTED, CORRUPT }

        private final Kind kind;

        public ExtractionException(Kind kind, String message, Throwable cause) {
            super(message, cause);
            this.kind = kind;
        }

        public Kind kind() {
            return kind;
        }
    }

    /** PDF：逐頁抽文字（PDFBox）。 */
    String extractPdf(byte[] content);

    /** DOCX：依序抽段落與表格儲存格文字（POI XWPF）；儲存格以 tab 分隔、段落以換行。 */
    String extractDocx(byte[] content);
}
