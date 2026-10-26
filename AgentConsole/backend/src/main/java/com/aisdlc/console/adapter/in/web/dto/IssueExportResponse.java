package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.si.SiExport;
import com.fasterxml.jackson.annotation.JsonValue;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.Map;

/**
 * {@code GET /api/v1/issues}、{@code GET /api/v1/issues/{id}} 的 {@code data}（TCS-IssueCenter-20261027 R-IC-49、R-IC-50、§C1）：Bridge 對根層
 * {@code si export --kind issues} 輸出的原樣轉遞，整棵樹所有層級的物件鍵經 {@link SiKeyNames}（snake_case→camelCase），<b>值一律不動</b>；
 * 每筆議題最後另有 Console 自有的 {@code priority}、{@code priorityNote}（由查詢用例合併，見 {@code IssueQueryService}）。
 *
 * <p>為什麼是「一棵樹」而不是具型別欄位：同 {@link SiExportResponse}——缺鍵（單筆沒有 {@code legend}、{@code summary}：不適用）與 {@code null}
 * （量不到）的語意不同，具型別的 DTO 會把兩者都變成 {@code null}；日後根層加的鍵也不得被靜默丟掉。欄位形狀見契約檔
 * {@code API_Contract_IssueCenter.md}（根層半的匯出形狀 §C1）。
 */
@Schema(name = "IssueExportResponse", type = "object", additionalProperties = Schema.AdditionalPropertiesValue.TRUE,
        description = "Bridge 對根層 si export --kind issues 輸出的原樣轉遞：所有層級的物件鍵經 snake_case→camelCase，值不動（null 與缺鍵的區別保留）。"
                + "最外層固定有 schemaRev、kind（issues）、generatedAt、headSha（可為 null）、items、nextSince（可為 null）、truncated、ne、problems；"
                + "清單另有 legend、summary（單筆沒有）；單筆的 items 恰一筆（另含 raw、timeline）。每筆議題最後多 Console 自有的 priority"
                + "（整數或 null）、priorityNote（字串或 null）：僅 rankable 為真且有順位列才有值。欄位形狀見契約檔 API_Contract_IssueCenter.md")
public final class IssueExportResponse {

    private final Map<String, Object> tree;

    private IssueExportResponse(Map<String, Object> tree) {
        this.tree = tree;
    }

    @SuppressWarnings("unchecked")
    public static IssueExportResponse from(SiExport export) {
        return new IssueExportResponse((Map<String, Object>) SiKeyNames.camelKeys(export.raw()));
    }

    /** 序列化的內容就是這棵樹本身（鍵序保留、{@code null} 照寫）。 */
    @JsonValue
    public Map<String, Object> tree() {
        return tree;
    }
}
