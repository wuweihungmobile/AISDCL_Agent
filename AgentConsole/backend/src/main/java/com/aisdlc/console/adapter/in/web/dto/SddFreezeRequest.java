package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SddGovernanceUseCase.FreezeRequest;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.List;
import java.util.Map;

/**
 * {@code POST /api/v1/projects/{id}/sdd/freeze} 的請求本文（契約 §1.10.2；D-115-03、D-115-14）。<b>approver 不在請求內</b>：一律取 JWT subject
 * （人工 signoff 不可匿名，也不可由 client 指定）；<b>沒有 {@code binding} 欄</b>——Console 專案是錨，FSM 專案＝{@code sddProject}（NULL 時取專案名）。
 *
 * <p>刻意<b>沒有 Bean Validation</b>：契約的驗證順序是「專案存在（404）」先於「請求驗證（400）」，所以欄位規則由用例在專案載入之後驗
 * （{@code SddFreezeRules}），違規一律 400（{@code errors[].field} 是欄位名）。下面的 {@code @Schema} 只供 OpenAPI 文件。
 */
@Schema(name = "SddFreezeRequest", description = "核准凍結請求（v1.5，D-115-03、D-115-14）。approver 不在請求內（一律取 JWT subject）；"
        + "沒有 binding 欄——Console 專案是錨，FSM 專案＝sddProject（NULL 時取專案名）")
public record SddFreezeRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, minLength = 1, maxLength = 500,
                description = "去前後空白後 1～500 字元，不含控制字元（含換行）；不靜默截斷、不替換；寫進 FSM decision_trace "
                        + "（console-freeze approver=<approver>; reason=<理由>）與 Console 稽核")
        String reason,
        @Schema(pattern = "^[A-Za-z0-9._-]{1,64}$",
                description = "階段名；省略時 Bridge 用 Stage-<n>（n＝frozen_stages 筆數＋1）。階段名不要求唯一")
        String stage,
        @ArraySchema(minItems = 1, maxItems = 20, schema = @Schema(minLength = 1, maxLength = 500),
                arraySchema = @Schema(description = "要凍結並計摘要的規格文件，每項是相對專案 executionPath 的 POSIX 路徑（不得為絕對路徑、不得含 ..）；"
                        + "須含至少一份 TCS（TEST-CONTRACT-SPEC-* 或 TCS-*，由 Bridge 判定）。省略＝[sddSpecFile 換算成相對 executionPath 的路徑]"
                        + "（專案已有 sddSpecFile 時）；省略而專案沒有 sddSpecFile、或規格檔不在 executionPath 之下、或專案已有 sddSpecFile 而 docs 不含它 → 400"
                        + "（errors[0].field=docs）"))
        List<String> docs,
        @Schema(description = "選填：核准人當時看到的摘要 {<docs 內的相對路徑>: \"sha256:<64 位小寫 hex>\"}。有帶＝Bridge 逐一與現檔比對，"
                + "不符 → 409 sdd_spec_digest_changed（details.pair=expected_vs_file）；鍵須都在 docs 內，否則 400（errors[0].field=expectedDigests）。"
                + "v1.5 的畫面不送這欄，保留給 API 消費者",
                additionalPropertiesSchema = String.class)
        Map<String, String> expectedDigests) {

    public FreezeRequest toDomain() {
        return new FreezeRequest(reason, stage, docs, expectedDigests);
    }
}
