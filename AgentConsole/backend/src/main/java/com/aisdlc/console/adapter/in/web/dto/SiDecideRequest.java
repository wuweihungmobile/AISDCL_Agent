package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SiWriteUseCase.DecideInput;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * {@code POST /api/v1/si/proposals/{id}/decide} 的請求本文（TCS-SelfImprovingDecide-P2b W12、表 M-D；PRD AC-SI-33-1）。路徑 {@code id} 是 PROP 號
 * （{@code resume} 為 RUN 號）。<b>刻意沒有 Bean Validation</b>：違規一律 422（頂層 reason {@code invalid_request}、
 * {@code details.violations[{field,message}]}、一次全列），先授權（403）與停用檢查（503）再驗輸入；下面的 {@code @Schema} 只供 OpenAPI 文件。
 */
@Schema(name = "SiDecideRequest", description = "對待決提案（或暫停的運轉）下決定。九種動詞：approve、reject、return、promote、decline-promote、"
        + "rollback、unblock、resume、ack-handoff；各動詞必填與禁止的欄位見表 M-D（多帶或缺帶一律 422，一次全列）。沒有批次核准")
public record SiDecideRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"approve", "reject", "return", "promote",
                "decline-promote", "rollback", "unblock", "resume", "ack-handoff"}, description = "動詞")
        String dkind,
        @Schema(pattern = "^sha256:[0-9a-f]{64}$", description = "開啟決定當下看到的卡面 digest（綁定它，過期由根層 CLI 以 STALE-CARD 拒收）。"
                + "approve、reject、return、promote、decline-promote、ack-handoff 必填；rollback、unblock、resume 不可帶")
        String digest,
        @Schema(minLength = 1, maxLength = 500, description = "理由（1～500 個 code point 的單行字串，不含控制字元）。reject、decline-promote、return、"
                + "rollback、resume 必填；其餘不可帶")
        String reason,
        @Schema(allowableValues = {"證據不足", "風險過高", "工件類別錯", "已被涵蓋", "範圍外", "卡面不清", "未說明"},
                description = "理由類別。reject、decline-promote、return 必填；其餘不可帶")
        String reasonClass,
        @Schema(description = "晉升後式（verdict 為 NE 的晉升）的勾選；true 只准 promote，稽核 body 的 flags 因此帶 unverified_ack")
        Boolean unverifiedAck) {

    public DecideInput toInput() {
        return new DecideInput(dkind, digest, reason, reasonClass, unverifiedAck);
    }
}
