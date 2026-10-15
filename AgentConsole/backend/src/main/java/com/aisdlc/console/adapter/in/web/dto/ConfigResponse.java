package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.SettingsUseCase.ConfigView;
import com.aisdlc.console.domain.model.config.ConfigEffect;
import com.aisdlc.console.domain.model.config.ConfigSpec;
import com.aisdlc.console.domain.model.config.ConfigValueType;
import com.aisdlc.console.domain.model.config.SystemConfig;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 系統參數（契約 §1.5.1）。
 *
 * <p>🔴 {@code isEncrypted=true} 時 {@code value} 一律是遮罩字串 {@code ••••••••}（U+2022 共八個）；{@code hasValue}
 * 才表示有沒有值；ADMIN 以 {@code reveal=true} 揭露明文。JSON 欄位名必須是 {@code isEncrypted}（Java record 的
 * boolean 元件以 {@code @JsonProperty} 固定序列化名稱，否則 Jackson 會依 bean 慣例輸出 {@code encrypted}）。
 * {@code options}／{@code min}／{@code max}／{@code effect} 來自程式內的 {@code ConfigCatalog}（附錄 C），
 * {@code impactNote} 讀 {@code system_configs.impact_note}。
 */
public record ConfigResponse(
        @NotNull UUID id,
        @NotNull @Schema(allowableValues = {"model", "agent", "execution", "monitor", "autoclaude", "sdd"})
        String category,
        @NotNull String key,
        @NotNull String value,
        @NotNull ConfigValueType valueType,
        String defaultValue,
        String description,
        @JsonProperty("isEncrypted") @Schema(name = "isEncrypted") @NotNull boolean isEncrypted,
        @NotNull boolean hasValue,
        String validationRule,
        List<String> options,
        BigDecimal min,
        BigDecimal max,
        String impactNote,
        @NotNull ConfigEffect effect,
        Instant updatedAt,
        String updatedBy) {

    public static ConfigResponse from(ConfigView view) {
        SystemConfig c = view.config();
        ConfigSpec spec = view.spec();
        return new ConfigResponse(c.id(), c.category(), c.key(), view.displayValue(), c.valueType(), c.defaultValue(),
                c.description(), c.encrypted(), view.hasValue(), c.validationRule(),
                spec == null || spec.options().isEmpty() ? null : spec.options(), spec == null ? null : spec.min(),
                spec == null ? null : spec.max(), c.impactNote(), spec == null ? ConfigEffect.UNVERIFIED : spec.effect(),
                c.updatedAt(), c.updatedBy());
    }
}
