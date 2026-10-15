package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.config.ConfigHistoryEntry;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

/** 參數修改歷史（契約 §1.5.8；changedAt 由新到舊）。加密參數的 oldValue／newValue 一律是遮罩 {@code ••••••••}。 */
public record ConfigHistoryResponse(
        @NotNull UUID id,
        @NotNull UUID configId,
        @NotNull String category,
        @NotNull String key,
        String oldValue,
        @NotNull String newValue,
        @NotNull Instant changedAt,
        String changedBy) {

    public static ConfigHistoryResponse from(ConfigHistoryEntry e) {
        return new ConfigHistoryResponse(e.id(), e.configId(), e.category(), e.key(), e.oldValue(), e.newValue(),
                e.changedAt(), e.changedBy());
    }
}
