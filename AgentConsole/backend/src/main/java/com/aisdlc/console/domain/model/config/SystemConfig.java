package com.aisdlc.console.domain.model.config;

import java.time.Instant;
import java.util.UUID;

/**
 * 系統參數（PRD §5.5.2；一列＝一個鍵）。{@code value} 一律是字串；加密參數（{@code encrypted=true}）的 {@code value}
 * 是儲存形式 {@code v1:<iv>:<密文>}（空字串＝沒有值），明文只在服務層經 {@code SecretCipher} 取得。
 *
 * @param defaultValue 預設值（可為 null；加密鍵為空字串）
 * @param updatedBy    最後修改者；null＝種子寫入、尚未被任何使用者修改
 */
public record SystemConfig(UUID id, String category, String key, String value, ConfigValueType valueType,
                           String defaultValue, String description, boolean encrypted, String validationRule,
                           String impactNote, Instant updatedAt, String updatedBy) {

    /** 加密參數是否已有值（非加密參數恆等於 value 非空）。 */
    public boolean hasValue() {
        return value != null && !value.isEmpty();
    }

    public SystemConfig withValue(String newValue, Instant at, String by) {
        return new SystemConfig(id, category, key, newValue, valueType, defaultValue, description, encrypted,
                validationRule, impactNote, at, by);
    }

    public String fullKey() {
        return category + "." + key;
    }
}
