package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SiWriteUseCase.Receipt;
import io.swagger.v3.oas.annotations.media.Schema;

/**
 * 三個寫入 POST 的成功收據（TCS-SelfImprovingDecide-P2b W11、AT-950-6-3）：{@code data} 鍵集合恰為這五個；<b>沒有 body 與 mac</b>。
 * 201 的意思是「稽核檔已落地、Console 稽核列已寫」，<b>不是</b>「已入帳」——入帳由主機端根層 CLI 以 {@code --carrier console --audit-ref <auditRef>} 做。
 */
@Schema(name = "SiWriteReceipt", description = "稽核檔已落地的收據；待入帳，由主機端根層 CLI 驗簽入帳")
public record SiWriteReceiptResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, format = "uuid", description = "稽核編號（小寫正規 UUID；入帳指令的 --audit-ref）") String auditRef,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, allowableValues = {"decide", "obs-add", "obs-close"}) String kind,
        @Schema(nullable = true, description = "decide＝PROP 號（resume 為 RUN 號）、obs-close＝OBS 號、obs-add＝null（入帳後才知道新列號）") String subject,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "稽核 body 的 time（秒精度、±HH:MM，UTC 為 +00:00）") String time,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "簽章金鑰的 sha256 前 8 碼") String keyId) {

    public static SiWriteReceiptResponse from(Receipt receipt) {
        return new SiWriteReceiptResponse(receipt.auditRef(), receipt.kind(), receipt.subject(), receipt.time(), receipt.keyId());
    }
}
