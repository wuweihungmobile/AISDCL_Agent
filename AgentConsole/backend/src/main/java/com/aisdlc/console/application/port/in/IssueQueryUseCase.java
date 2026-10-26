package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.si.SiExport;

/**
 * 議題中心的唯讀查詢（TCS-IssueCenter-20261027 R-IC-49、R-IC-50）：回應就是 Bridge 對根層 {@code si export --kind issues} 輸出的原樣轉遞，
 * 只在每筆議題上多加 Console 自有的 {@code priority}、{@code priority_note}（snake_case 的鍵，由回應邊界轉 camelCase）。backend <b>不重算</b>
 * （不歸類、不排序、不翻譯）、<b>不快取</b>（每個請求恰一次 Bridge 呼叫與一次順位表讀取）、<b>零寫入</b>。
 *
 * <p>失敗一律是領域例外、<b>沒有部分資料</b>：Bridge 的 503 {@code si_unavailable}→503、404 {@code si_not_found}→404（訊息「查無此議題」）、
 * 422→422（引擎拒絕此請求）、連線失敗／其餘 5xx→502、讀取逾時→504；順位表讀不到→5xx。{@code since} 須 ≥0、{@code limit} 須 ≥1，
 * 不合→400（不觸及 Bridge）。
 */
public interface IssueQueryUseCase {

    /**
     * {@code GET /issues}：議題清單（含 {@code legend}、{@code summary}）。{@code status}、{@code source} 是議題中心的中文篩選別名
     * （逗號分隔），<b>原樣</b>轉給 Bridge（空字串也照轉；別名的意義與合法值的單一真相在根層 CLI）；null＝不帶。
     */
    SiExport list(Integer since, Integer limit, String status, String source);

    /** {@code GET /issues/{id}}：單筆議題（含 {@code raw}、{@code timeline}；沒有 {@code legend}、{@code summary}）。{@code id} 的格式由 Bridge 判。 */
    SiExport one(String id);
}
