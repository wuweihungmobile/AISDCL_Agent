package com.aisdlc.console.application.port.out;

import java.util.List;

/**
 * 監控報表的 PDF 轉譯埠（契約 §1.3.7，C-4）。application 層只決定「要印什麼」——標題、說明行、與 CSV 相同的四個區段
 * （欄名與儲存格文字，null 已換成顯示用的破折號）；版面、字型與分頁由實作負責（{@code adapter.out.document}，Apache PDFBox 3，
 * 內嵌 OFL 授權的 CJK 字型）。實作<b>不得</b>因字型缺字而失敗：沒有的字元一律以 {@code ?} 取代。
 */
public interface ReportPdfRenderer {

    /** 轉成一份 PDF 檔（位元組）。 */
    byte[] render(Document document);

    /**
     * @param title      標題（專案名稱＋「監控報表」）
     * @param infoLines  標題下方的說明行（時間範圍、範圍、產生時間）
     * @param sections   依序輸出的區段（與 CSV 同序：summary／runs／tasks／alerts）
     */
    record Document(String title, List<String> infoLines, List<Section> sections) {
    }

    /**
     * 一個區段（表格）。
     *
     * @param name    區段名稱（{@code summary}／{@code runs}／{@code tasks}／{@code alerts}），原樣印成區段標題
     * @param headers 欄名（與 CSV 同欄同序）
     * @param rows    資料列；每列的儲存格數等於欄數，儲存格文字原樣印出（不做 CSV 的注入防護引號）
     */
    record Section(String name, List<String> headers, List<List<String>> rows) {
    }
}
