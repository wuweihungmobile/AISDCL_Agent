package com.aisdlc.console.adapter.in.web.dto;

import jakarta.validation.constraints.NotNull;
import org.slf4j.MDC;

import java.time.OffsetDateTime;

/**
 * 統一成功回應封包（PRD §7.2）：{@code {code,message:"success",data,timestamp,traceId}}。
 *
 * @param code      HTTP 狀態碼（200／201）
 * @param timestamp ISO-8601 且帶 offset
 * @param traceId   每請求 UUID，與回應標頭 X-Trace-Id 相同
 */
public record ApiResult<T>(
        @NotNull int code,
        @NotNull String message,
        @NotNull T data,
        @NotNull OffsetDateTime timestamp,
        @NotNull String traceId) {

    public static <T> ApiResult<T> ok(T data) {
        return of(200, data);
    }

    public static <T> ApiResult<T> created(T data) {
        return of(201, data);
    }

    private static <T> ApiResult<T> of(int code, T data) {
        return new ApiResult<>(code, "success", data, OffsetDateTime.now(), MDC.get("traceId"));
    }
}
