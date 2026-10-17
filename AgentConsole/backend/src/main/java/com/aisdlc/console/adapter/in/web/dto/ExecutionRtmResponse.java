package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.execution.ExecutionRtm;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;

/**
 * {@code GET /api/v1/executions/{runId}/rtm} 的 {@code data}（契約 §1.10.3；G-05）。Bridge 同名欄位的投影，鍵轉 camelCase、值原樣。
 * <b>諮詢視圖</b>：「AT 通過」只代表評估指令與驗收 regex 皆通過，不等於規格被滿足；SCG-4 的人工審查才是真閘，所以 {@code advisory} 恆為 true。
 */
@Schema(name = "ExecutionRtmResponse", description = "執行追溯覆蓋（v1.5，G-05）。Bridge 同名欄位的投影，鍵轉 camelCase、值原樣。諮詢視圖：AT 通過不等於規格被滿足；"
        + "有無法歸屬 AC 的 AT（unmappedAtIds 非空）時，它們仍計入 at.total、at.passed／failedAtIds，但不計入任何 AC，且 fullyCovered 恆為 false")
public record ExecutionRtmResponse(
        @NotNull @Schema(description = "場景；缺則空字串") String scenario,
        @NotNull @Schema(description = "編譯規格的摘要（sha256:<hex>）；缺則空字串") String specDigest,
        @NotNull AtCoverage at,
        @NotNull AcCoverage ac,
        @NotNull @Schema(description = "未通過的 AT（Bridge 已排序；沒有為空陣列；含無法歸屬者）") List<String> failedAtIds,
        @NotNull @Schema(description = "驗收 regex 偏弱（轉譯保真度警訊）的 AT；沒有為空陣列") List<String> weakRegexAtIds,
        @NotNull @Schema(description = "逆向還原後無法歸屬 AC 的 AT（已排序；舊報告缺欄為空陣列）。與 POST /sdd/compile 回應的同名 unmapped_at_ids"
                + "（規格宣告位置出現卻沒編成步驟）是兩個不同層的欄位，不得混用") List<String> unmappedAtIds,
        @NotNull @Schema(description = "ac.total>0 且 AC 全數覆蓋，且 unmappedAtIds 為空（SCG-5 的機器判斷，仍是諮詢）") boolean fullyCovered,
        // 契約 yaml 寫 const: true；springdoc 的 allowableValues 對 boolean 會產出字串 enum "true"（與 type 不符，型別產生器會讀錯），所以只用說明表達
        @NotNull @Schema(description = "恆為 true（契約：const true）；前端必須標示「諮詢視圖」") boolean advisory) {

    public static ExecutionRtmResponse from(ExecutionRtm rtm) {
        return new ExecutionRtmResponse(rtm.scenario(), rtm.specDigest(),
                new AtCoverage(rtm.at().passed(), rtm.at().total(), rtm.at().unmapped(), rtm.at().pct()),
                new AcCoverage(rtm.ac().covered(), rtm.ac().total(), rtm.ac().pct()), rtm.failedAtIds(),
                rtm.weakRegexAtIds(), rtm.unmappedAtIds(), rtm.fullyCovered(), rtm.advisory());
    }

    /** AT 層的覆蓋：{@code total}、{@code passed} 含無法歸屬 AC 的 AT（ADR-XPLAT-016 §8.5：AT 級指標不假裝它不存在）。 */
    @Schema(name = "RtmAtCoverage", description = "AT 層的覆蓋（v1.5）。total、passed 含無法歸屬 AC 的 AT")
    public record AtCoverage(
            @NotNull @Schema(minimum = "0") int passed,
            @NotNull @Schema(minimum = "0") int total,
            @NotNull @Schema(minimum = "0", description = "逆向還原後無法歸屬 AC 的 AT 個數（舊報告缺欄為 0）；已計入 total，不計入任何 AC") int unmapped,
            @NotNull @Schema(minimum = "0", maximum = "100", description = "百分比（0～100，1 位小數；Bridge 原值）") double pct) {
    }

    /** AC 層的覆蓋：無法歸屬的 AT 不進任何 AC 桶（分母口徑與 AT 層不同，不可互推）。 */
    @Schema(name = "RtmAcCoverage", description = "AC 層的覆蓋（v1.5）。無法歸屬的 AT 不進任何 AC 桶")
    public record AcCoverage(
            @NotNull @Schema(minimum = "0") int covered,
            @NotNull @Schema(minimum = "0") int total,
            @NotNull @Schema(minimum = "0", maximum = "100", description = "百分比（0～100，1 位小數；Bridge 原值）") double pct) {
    }
}
