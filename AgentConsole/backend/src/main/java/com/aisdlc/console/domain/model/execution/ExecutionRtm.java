package com.aisdlc.console.domain.model.execution;

import java.util.List;

/**
 * 執行批次的追溯覆蓋（Bridge {@code GET /autoclaude/runs/{id}/rtm} 的投影；契約 §1.10.3；G-05）。<b>諮詢視圖</b>：「AT 通過」只代表
 * 評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘，所以 {@link #advisory()} 恆為 true。
 *
 * <p>有無法歸屬 AC 的 AT 時（{@code unmappedAtIds} 非空）：它們仍計入 {@code at.total}、{@code at.passed}／{@code failedAtIds}，
 * 但不進任何 AC 桶，且 {@code fullyCovered} 恆為 false（ADR-XPLAT-016 §8.5）。🔴 {@code unmappedAtIds} 與
 * {@code POST /sdd/compile} 回應的同名欄位是<b>兩個不同層</b>（規格宣告位置出現卻沒編成步驟）的欄位，不得混用。
 *
 * @param scenario       場景；缺則空字串
 * @param specDigest     編譯規格的摘要（{@code sha256:<hex>}）；缺則空字串
 * @param at             AT 層覆蓋
 * @param ac             AC 層覆蓋
 * @param failedAtIds    未通過的 AT（Bridge 已排序；含無法歸屬者）
 * @param weakRegexAtIds 驗收 regex 偏弱的 AT
 * @param unmappedAtIds  逆向還原後無法歸屬 AC 的 AT（舊報告缺欄為空）
 * @param fullyCovered   {@code ac.total>0} 且 AC 全數覆蓋，<b>且</b> {@code unmappedAtIds} 為空（Bridge 原值）
 */
public record ExecutionRtm(String scenario, String specDigest, At at, Ac ac, List<String> failedAtIds,
                           List<String> weakRegexAtIds, List<String> unmappedAtIds, boolean fullyCovered) {

    /** 恆為 true：本視圖永遠是諮詢性質（Bridge 自己也加，但 Console 不依賴它）。 */
    public boolean advisory() {
        return true;
    }

    /**
     * AT 層的覆蓋：{@code total}、{@code passed} <b>含</b>無法歸屬 AC 的 AT。
     *
     * @param unmapped 無法歸屬 AC 的個數（舊報告缺欄為 0）
     * @param pct      百分比（0～100，1 位小數；Bridge 原值）
     */
    public record At(int passed, int total, int unmapped, double pct) {
    }

    /** AC 層的覆蓋：無法歸屬的 AT 不進任何 AC 桶（分母口徑與 {@link At#total()} 不同，不可互推）。 */
    public record Ac(int covered, int total, double pct) {
    }

    public ExecutionRtm {
        failedAtIds = failedAtIds == null ? List.of() : List.copyOf(failedAtIds);
        weakRegexAtIds = weakRegexAtIds == null ? List.of() : List.copyOf(weakRegexAtIds);
        unmappedAtIds = unmappedAtIds == null ? List.of() : List.copyOf(unmappedAtIds);
        scenario = scenario == null ? "" : scenario;
        specDigest = specDigest == null ? "" : specDigest;
    }
}
