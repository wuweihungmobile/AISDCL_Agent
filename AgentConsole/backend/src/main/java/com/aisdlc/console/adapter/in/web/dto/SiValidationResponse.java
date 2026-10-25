package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.si.SiValidation;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.List;

/**
 * {@code POST /api/v1/si/observations/validate} 的回應（TCS-SelfImprovingDecide-P2b W4、W11、AT-950-6-3）：Bridge 預檢物件（根層
 * {@code obs-add --dry-run}）的原樣轉遞，只做 snake_case→camelCase；{@code ok=false} 仍是 200（findings 說明哪裡不合）。不落檔、不寫資料庫。
 */
@Schema(name = "SiValidation", description = "觀察列預檢結果（obs-add --dry-run）：預覽列、位元組數與根層的拒收原因")
public record SiValidationResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) boolean ok,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "預覽列全文（通過才有；否則空字串）；audit_ref 以等長的全零 UUID 佔位") String row,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, format = "int64", description = "預覽列的 UTF-8 位元組數（等於入帳列的位元組數）") long rowBytes,
        @Schema(nullable = true, format = "int64", description = "根層協定參數檔的列位元組上限；根層量不到時為 null") Long rowMaxBytes,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED) List<Finding> findings) {

    /** 一筆不合的原因（{@code code} 是根層 CLI 的拒收碼，{@code detail} 逐字）。 */
    @Schema(name = "SiValidationFinding")
    public record Finding(@Schema(requiredMode = Schema.RequiredMode.REQUIRED) String code,
                          @Schema(requiredMode = Schema.RequiredMode.REQUIRED) String detail) {
    }

    public static SiValidationResponse from(SiValidation validation) {
        return new SiValidationResponse(validation.ok(), validation.row(), validation.rowBytes(), validation.rowMaxBytes(),
                validation.findings().stream().map(f -> new Finding(f.code(), f.detail())).toList());
    }
}
