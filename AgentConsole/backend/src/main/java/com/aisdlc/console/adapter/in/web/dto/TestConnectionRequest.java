package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SettingsUseCase.TestConnectionCommand;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Size;

/**
 * 測試連線（契約 §1.5.7）。全部選填；省略的欄位取已儲存的 {@code model.*}。
 * 🔴 {@code apiKey} 僅寫入：不回顯、不寫日誌（{@link #toString()} 也刻意遮罩，避免被意外印進日誌）。
 */
public record TestConnectionRequest(
        @Size(max = 500, message = "apiUrl 長度不可超過 500 字元")
        @Schema(description = "完整的 chat-completions 端點 URL（與系統參數 model.apiUrl 同義；後端不補路徑）") String apiUrl,
        @Size(max = 512, message = "apiKey 長度不可超過 512 字元")
        @JsonProperty(access = JsonProperty.Access.WRITE_ONLY)
        @Schema(description = "不回顯、不寫日誌", accessMode = Schema.AccessMode.WRITE_ONLY) String apiKey,
        @Size(max = 100, message = "model 長度不可超過 100 字元") String model) {

    public TestConnectionCommand toDomain() {
        return new TestConnectionCommand(apiUrl, apiKey, model);
    }

    @Override
    public String toString() {
        return "TestConnectionRequest[apiUrl=<redacted>, apiKey=<redacted>, model=" + model + "]";
    }
}
