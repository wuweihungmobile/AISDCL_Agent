package com.aisdlc.console.adapter.in.web.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** 更新單一參數（契約 §1.5.3）。{@code value} 一律是字串（BOOLEAN 為 true／false，FLOAT 用小數點）。 */
public record UpdateConfigRequest(
        @NotNull(message = "value 不可缺漏") @Size(max = 4000, message = "value 長度不可超過 4000 字元")
        @Schema(description = "一律字串；加密參數給空字串表示清除") String value,
        @Schema(description = "加密（敏感）參數須明確帶 true，否則 409") Boolean confirm) {

    public boolean confirmed() {
        return Boolean.TRUE.equals(confirm);
    }
}
