package com.aisdlc.console.infrastructure.security;

import com.aisdlc.console.application.port.out.SecretCipher;
import org.springframework.stereotype.Component;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Base64;

/**
 * AES-256-GCM 的 {@link SecretCipher}（金鑰來自 {@code CONSOLE_ENCRYPTION_KEY}，啟動時驗證）。
 *
 * <p>密文字串格式 {@code v1:<iv base64>:<ciphertext base64>}：{@code v1} 是格式版本（日後換演算法或金鑰輪替時用來區分）；
 * IV 每次加密隨機產生 12 bytes（GCM 對同一把金鑰重複 IV 是災難性的，所以絕不重用）；密文尾端含 128 位元驗證標籤，
 * 任何竄改或金鑰不對都會在解密時失敗（不會回傳亂碼）。
 */
@Component
class AesGcmSecretCipher implements SecretCipher {

    private static final String VERSION = "v1";
    private static final String TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int IV_BYTES = 12;
    private static final int TAG_BITS = 128;

    private final SecretKey key;
    private final SecureRandom random = new SecureRandom();

    AesGcmSecretCipher(EncryptionProperties properties) {
        this.key = new SecretKeySpec(properties.keyBytes(), "AES");
    }

    @Override
    public String encrypt(String plainText) {
        try {
            byte[] iv = new byte[IV_BYTES];
            random.nextBytes(iv);
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
            byte[] encrypted = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
            Base64.Encoder encoder = Base64.getEncoder();
            return VERSION + ":" + encoder.encodeToString(iv) + ":" + encoder.encodeToString(encrypted);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("敏感參數加密失敗", e);
        }
    }

    @Override
    public String decrypt(String stored) {
        String[] parts = stored == null ? new String[0] : stored.split(":", -1);
        if (parts.length != 3 || !VERSION.equals(parts[0])) {
            throw new IllegalStateException("敏感參數的儲存格式不符（預期 v1:<iv>:<密文>）");
        }
        try {
            byte[] iv = Base64.getDecoder().decode(parts[1]);
            byte[] encrypted = Base64.getDecoder().decode(parts[2]);
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
            return new String(cipher.doFinal(encrypted), StandardCharsets.UTF_8);
        } catch (GeneralSecurityException | IllegalArgumentException e) {
            // 不把原因（可能含部分金鑰資訊的錯誤訊息）放進訊息；只留例外鏈供除錯
            throw new IllegalStateException("敏感參數解密失敗：金鑰不對或資料被竄改", e);
        }
    }
}
