package com.aisdlc.console.adapter.in.web.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * 統一錯誤回應封包（PRD §7.2）：{@code {code,message,errors[{field,message}],timestamp,traceId}}，
 * 另有兩個選填欄位：{@code reason}（PRD「409 附 reason」「reason:依賴成環」）與 {@code details}
 * （結構化補充，例：環路 id 清單、違規字元清單）。兩者沒有值時不輸出。
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

    /** 單一欄位的錯誤明細。 */
    public record FieldError(@NotNull String field, @NotNull String message) {
    }
}
