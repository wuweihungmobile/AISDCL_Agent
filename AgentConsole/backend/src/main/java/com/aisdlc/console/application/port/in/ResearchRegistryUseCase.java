package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;

import java.util.List;
import java.util.Map;

/**
 * 研究來源單一化的追蹤來源用例（API-RP-29；API 契約 §5A.2；TCS-ResearchRegistry W-R5）：追蹤來源住 {@code console.research_watch_sources}，
 * <b>console-api 對它零寫入</b>——讀取與寫入都只轉 Bridge（寫入恰一次呼叫、不重試）。回傳的 Map 是 Bridge 的 snake_case 本文原樣（DTO 負責轉 camelCase）。
 *
 * <p>失敗序（契約 §0.2）：401→403（ADMIN 才能寫）→503 {@code research_write_disabled}→400／422 輸入閘→恰一次 Bridge 呼叫
 * （Bridge 的 404／409／422 reason 逐字透傳；連線失敗 502 {@code bridge_unreachable}、讀取逾時 504 {@code bridge_timeout}）。操作人（{@code added_by}、
 * {@code disabled_by}）一律取 JWT subject，請求本文沒有這兩個欄位。
 */
public interface ResearchRegistryUseCase {

    /** 全部追蹤來源（含停用；依 slug 位元組序；Bridge 的 {@code items}）。 */
    List<Map<String, Object>> watchSources();

    /** 新增一筆（輸入閘：400；單一閘 {@code host_not_allowed}、重複 slug、大小閘由 Bridge 回）。 */
    Map<String, Object> addWatchSource(Caller caller, Map<String, Object> body);

    /** 停用或重新啟用（只准 {@code enabled} 一鍵）。 */
    Map<String, Object> patchWatchSource(Caller caller, String slug, Map<String, Object> patch);
}
