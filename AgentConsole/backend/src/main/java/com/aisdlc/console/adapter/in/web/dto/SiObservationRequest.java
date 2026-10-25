package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SiWriteUseCase.ObservationInput;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * {@code POST /api/v1/si/observations}（新增觀察列）與 {@code POST /api/v1/si/observations/validate}（預檢）共用的請求本文
 * （TCS-SelfImprovingDecide-P2b W12、表 M-O；PRD AC-SI-35-1）。<b>刻意不含 {@code marks_extra}</b>：Console 只產生 {@code corrects} 對應的
 * {@code rel=corrects:<ID>} 標記，其餘標記由主控手寫入帳。刻意沒有 Bean Validation（同 {@link SiDecideRequest}）。
 */
@Schema(name = "SiObservationRequest", description = "新增觀察列（或預檢）。三個字串欄各 1～300 個 code point、UTF-8 位元組和不得超過 700（必要條件；"
        + "權威是預檢與根層 CLI 的列位元組上限），且不得含豎線與控制字元（觀察列是 Markdown 九欄表）")
public record SiObservationRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, minLength = 1, maxLength = 300, description = "情境") String context,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, minLength = 1, maxLength = 300, description = "症狀") String symptom,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, minLength = 1, maxLength = 300,
                description = "證據座標（須含可定位座標，由根層 CLI 判）") String evidence,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"process", "bug", "tooling", "doc", "decision"}) String category,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"P1", "P2", "P3", "P4"}) String severity,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"守衛", "產品", "文件", "流程"}) String face,
        @Schema(allowableValues = {"a", "b", "c", "無"}, description = "face 為守衛時必填、否則不可帶") String exposure,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "是否外部衍生（表單預設 false）") Boolean externalDerived,
        @Schema(pattern = "^OBS-SI-[0-9]{3,}$", description = "被更正的觀察列（選填；是否存在由根層 CLI 判）") String corrects) {

    public ObservationInput toInput() {
        return new ObservationInput(context, symptom, evidence, category, severity, face, exposure, externalDerived, corrects);
    }
}
