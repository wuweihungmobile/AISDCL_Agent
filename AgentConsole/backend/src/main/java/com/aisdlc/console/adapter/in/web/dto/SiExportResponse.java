package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.si.SiExport;
import com.fasterxml.jackson.annotation.JsonValue;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.Map;

/**
 * {@code GET /api/v1/si/**} 的 {@code data}（TCS-SelfImprovingMirror-P1b R9）：Bridge 對根層 {@code si export} 輸出的原樣轉遞，
 * 整棵樹所有層級的物件鍵經 {@link SiKeyNames}（snake_case→camelCase），<b>值一律不動</b>。
 *
 * <p>為什麼是「一棵樹」而不是每個 kind 一組具型別欄位：差分（AC-SI-32-1）要求頁面與回應「逐欄相同」，而 {@code export} 的語意靠
 * <b>缺鍵與 {@code null} 的區別</b>（壞列沒有 {@code id}、{@code head_sha} 為 {@code null} 代表 git 量不到、{@code cooldown} 為
 * {@code null} 代表沒有冷卻）；具型別的 DTO 把兩者都變成 {@code null}，等於替 Bridge 補了它沒說的話。未知的鍵（日後根層加的
 * {@code buckets}、{@code console_pending}…）同樣原樣出現、不得靜默丟棄。各 kind 的欄位形狀見契約後繼檔
 * {@code API_Contract_SelfImproving_P1b.md §1.7}（來源 PRD §9.2〈export --json 輸出〉）。
 *
 * <p>最外層固定有（Bridge 已驗 {@code schema_rev} 與 {@code kind}、{@code items} 為陣列）：{@code schemaRev}、{@code kind}、
 * {@code generatedAt}（Bridge 的值，不是 backend 的時鐘）、{@code headSha}（可為 {@code null}）、{@code items}、{@code nextSince}
 * （可為 {@code null}）、{@code truncated}、{@code ne}、{@code problems}。
 */
@Schema(name = "SiExportResponse", type = "object", additionalProperties = Schema.AdditionalPropertiesValue.TRUE,
        description = "Bridge 對根層 si export 輸出的原樣轉遞：所有層級的物件鍵經 snake_case→camelCase，值不動（null 與缺鍵的區別保留）。"
                + "最外層固定有 schemaRev、kind、generatedAt、headSha（可為 null）、items、nextSince（可為 null）、truncated、ne、problems；"
                + "未知的鍵原樣透傳。各 kind 的 items 形狀見契約後繼檔 API_Contract_SelfImproving_P1b.md §1.7")
public final class SiExportResponse {

    private final Map<String, Object> tree;

    private SiExportResponse(Map<String, Object> tree) {
        this.tree = tree;
    }

    @SuppressWarnings("unchecked")
    public static SiExportResponse from(SiExport export) {
        return new SiExportResponse((Map<String, Object>) SiKeyNames.camelKeys(export.raw()));
    }

    /** 序列化的內容就是這棵樹本身（鍵序保留、{@code null} 照寫）。 */
    @JsonValue
    public Map<String, Object> tree() {
        return tree;
    }
}
