package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.si.SiExport;

/**
 * SelfImproving 的唯讀鏡像（TCS-SelfImprovingMirror-P1b R7～R9；PRD AC-SI-32-1～32-4）：Console 是顯示面、不是資料來源——
 * 回應就是 Bridge 對根層 {@code si export} 輸出的原樣轉遞，backend <b>不重算</b>（不折疊事件、不算 digest、不判 NE、不補
 * {@code generated_at}）、<b>不快取</b>（每個請求恰一次 Bridge 呼叫）、<b>零寫入</b>（本介面沒有任何寫入方法）。
 *
 * <p>失敗一律是領域例外、<b>沒有部分資料</b>：Bridge 的 503 {@code si_unavailable} → {@code ServiceUnavailableException}（503）；
 * 404 {@code si_not_found} → {@code NotFoundException}（帶 reason）；422 {@code invalid_request} → {@code UnprocessableException}；
 * 其餘 4xx、5xx、連線失敗與逾時 → 502／504。清單類的 {@code since} 須 ≥0、{@code limit} 須 ≥1，不合 → {@code ValidationException}
 * （400，不會觸及 Bridge）。
 */
public interface SiMirrorUseCase {

    /** {@code GET /si/status}：啟動事件偵測與狀態摘要（不分頁）。 */
    SiExport status();

    /** {@code GET /si/observations}：觀察帳本逐列（含無法解析的壞列）。 */
    SiExport observations(Integer since, Integer limit);

    /** {@code GET /si/events}：事件帳本逐行。 */
    SiExport events(Integer since, Integer limit);

    /** {@code GET /si/proposals}：提案（含卡面 {@code card} 字串）。 */
    SiExport proposals(Integer since, Integer limit);

    /**
     * {@code GET /si/proposals/{id}}：單筆提案。{@code id} 原樣交給 Bridge（格式的單一真相在 Bridge：不合為 422，合法而不存在為 404
     * {@code si_not_found}）；backend 只驗非空。
     */
    SiExport proposal(String id);

    /** {@code GET /si/runs}：運轉（開關與提案結果）。 */
    SiExport runs(Integer since, Integer limit);
}
