package com.aisdlc.console.adapter.in.web.dto;

import io.swagger.v3.oas.annotations.media.Schema;

/**
 * {@code PUT /api/v1/issues/{id}/priority} 的請求本文（TCS-IssueCenter-20261027 §C4.3）：{@code {"rank": 1～9999, "note": "…"}}。
 *
 * <p>這個 record <b>只供 OpenAPI 文件</b>：控制器以 {@code Map} 收本文，型別與值域一律由輸入閘一次判完（{@code rank} 為字串、小數、布林、
 * {@code null}、缺鍵都是 422，不是 400，也不是「清除」）——具型別的綁定會在型別不符時先回 400（{@code IssuePriorityGates} 的說明）。
 */
@Schema(name = "IssuePriorityRequest", description = "設定議題的優先順序（僅 ADMIN）。rank 必填、整數 1～9999（null、缺鍵、0、負數、小數、字串、布林、陣列、物件、"
        + "超過 9999 一律 422，不當清除）；note 選填（缺鍵＝空字串；null 與數字 422）、至多 200 個字元（code point）、不含控制字元。要清除順位請用 DELETE")
public record IssuePriorityRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, minimum = "1", maximum = "9999", description = "順位（1 最先；可與其他議題重複）") int rank,
        @Schema(requiredMode = Schema.RequiredMode.NOT_REQUIRED, maxLength = 200, description = "備註（缺鍵＝空字串）") String note) {
}
