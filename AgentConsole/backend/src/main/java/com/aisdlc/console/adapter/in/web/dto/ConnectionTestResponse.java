package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SettingsUseCase.ConnectionTestResult;
import jakarta.validation.constraints.NotNull;

/**
 * 測試連線的結果（契約 §1.5.7）：只要實際嘗試過連線，成功或失敗都是 200；政策拒絕是 422（沒有任何連線）。
 *
 * @param latencyMs    送出請求到收到回應標頭的毫秒數；無回應為 null
 * @param resolvedHost URL 的 host（小寫）
 */
public record ConnectionTestResponse(
        @NotNull boolean success,
        Long latencyMs,
        @NotNull String message,
        String resolvedHost,
        Integer httpStatus) {

    public static ConnectionTestResponse from(ConnectionTestResult r) {
        return new ConnectionTestResponse(r.success(), r.latencyMs(), r.message(), r.resolvedHost(),
                r.httpStatus());
    }
}
