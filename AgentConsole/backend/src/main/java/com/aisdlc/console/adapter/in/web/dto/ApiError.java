package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.imports.GateError;
import com.fasterxml.jackson.annotation.JsonInclude;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * 統一錯誤回應封包（PRD §7.2）：{@code {code,message,errors[{field,message}],timestamp,traceId}}，
 * 另有兩個選填欄位：{@code reason}（PRD「409 附 reason」「reason:依賴成環」）與 {@code details}
 * （結構化補充，例：環路 id 清單、違規字元清單）。兩者沒有值時不輸出；{@code details} 內<b>不輸出 null 值</b>
 * （沒有值的鍵一律省略，契約 §0.2）。
 *
 * @param code HTTP 狀態碼
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ApiError(
        @NotNull int code,
        @NotNull String message,
        String reason,
        @NotNull List<FieldError> errors,
        Map<String, Object> details,
        @NotNull OffsetDateTime timestamp,
        @NotNull String traceId) {

    /**
     * 單一欄位的錯誤明細。有界閘的 422（契約 §1.1.3、§3.3.5）另帶 {@code gate／detail／location}：
     * 項目＝{@code FieldError} 加上 {@link GateError} 的三個欄位，一般 client 把它當 FieldError 讀即可。
     */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record FieldError(@NotNull String field, @NotNull String message, String gate, String detail,
                             String location) {

        public FieldError(String field, String message) {
            this(field, message, null, null, null);
        }

        /** 有界閘違規 → 錯誤項目：{@code field＝location}（沒有位置的閘退回閘名稱）、{@code message＝detail}。 */
        public static FieldError ofGate(GateError error) {
            return new FieldError(error.location() != null ? error.location() : error.gate(), error.detail(),
                    error.gate(), error.detail(), error.location());
        }
    }
}
