package com.aisdlc.console.infrastructure.security;

import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.NotBlank;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

import java.util.Base64;

/**
 * 敏感參數加密金鑰（{@code console.encryption.key}，環境變數 {@code CONSOLE_ENCRYPTION_KEY}；AES-256-GCM）。
 *
 * <p>🔴 與 JWT_SECRET 同款 fail-fast：金鑰缺少、不是合法的 base64、或解碼後不是剛好 32 bytes＝<b>啟動失敗</b>
 * （綁定驗證不過，Spring 直接中止啟動，錯誤訊息點名此環境變數），不會退回弱預設或靜默停用加密。
 * 產生金鑰：{@code openssl rand -base64 32}。
 *
 * @param key base64 編碼的 32 bytes
 */
@Validated
@ConfigurationProperties(prefix = "console.encryption")
public record EncryptionProperties(
        @NotBlank(message = "環境變數 CONSOLE_ENCRYPTION_KEY 必填（base64 編碼的 32 bytes，可用 openssl rand -base64 32 產生）")
        String key) {

    /** AES-256 的金鑰長度。 */
    public static final int KEY_BYTES = 32;

    @AssertTrue(message = "環境變數 CONSOLE_ENCRYPTION_KEY 必須是 base64 編碼的 32 bytes（AES-256）")
    public boolean isKeyLengthValid() {
        if (key == null || key.isBlank()) {
            return true;       // 缺少的情形交給 @NotBlank 報告，避免同一個問題出現兩則訊息
        }
        try {
            return Base64.getDecoder().decode(key.strip()).length == KEY_BYTES;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    /** 解碼後的金鑰位元組（呼叫前提：已通過驗證）。 */
    public byte[] keyBytes() {
        return Base64.getDecoder().decode(key.strip());
    }
}
