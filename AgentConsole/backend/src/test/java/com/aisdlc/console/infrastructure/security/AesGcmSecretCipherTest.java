package com.aisdlc.console.infrastructure.security;

import org.junit.jupiter.api.Test;

import java.util.Base64;
import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * AES-256-GCM 的敏感參數加密（NFR-9.2「API Key 等使用 AES-256 加密儲存」）。為什麼重要：資料庫外洩時 API Key 不能是明文；
 * 且 GCM 的驗證標籤讓「被竄改的密文」在解密時失敗，而不是悄悄回傳亂碼給引擎當金鑰。
 */
class AesGcmSecretCipherTest {

    private static final String KEY_A = Base64.getEncoder().encodeToString("0123456789abcdef0123456789abcdef".getBytes());
    private static final String KEY_B = Base64.getEncoder().encodeToString("ffffffffffffffff0123456789abcdef".getBytes());

    private final AesGcmSecretCipher cipher = new AesGcmSecretCipher(new EncryptionProperties(KEY_A));

    @Test
    void aSecretRoundTripsIncludingUnicodeAndLongValues() {
        for (String plain : new String[] {"sk-abc123", "金鑰：密碼🔐", "x".repeat(512), "with:colons:inside", " "}) {
            assertThat(cipher.decrypt(cipher.encrypt(plain))).isEqualTo(plain);
        }
    }

    @Test
    void theStoredFormIsVersionIvCiphertextAndNeverContainsThePlaintext() {
        String stored = cipher.encrypt("sk-super-secret-value");
        String[] parts = stored.split(":");
        assertThat(parts).hasSize(3);
        assertThat(parts[0]).isEqualTo("v1");
        assertThat(Base64.getDecoder().decode(parts[1])).as("GCM 的 IV 為 12 bytes").hasSize(12);
        assertThat(stored).doesNotContain("sk-super-secret-value");
        assertThat(Base64.getDecoder().decode(parts[2])).as("密文含 128 位元驗證標籤").hasSizeGreaterThan(16);
    }

    @Test
    void everyEncryptionUsesAFreshRandomIvSoEqualSecretsNeverProduceEqualCiphertext() {
        Set<String> seen = new HashSet<>();
        for (int i = 0; i < 50; i++) {
            assertThat(seen.add(cipher.encrypt("same-secret"))).isTrue();
        }
    }

    @Test
    void aTamperedCiphertextFailsInsteadOfReturningGarbage() {
        String stored = cipher.encrypt("sk-real");
        String[] parts = stored.split(":");
        byte[] bytes = Base64.getDecoder().decode(parts[2]);
        bytes[0] ^= 0x01;
        String tampered = parts[0] + ":" + parts[1] + ":" + Base64.getEncoder().encodeToString(bytes);
        assertThatThrownBy(() -> cipher.decrypt(tampered)).isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("解密失敗").hasMessageNotContaining("sk-real");
    }

    @Test
    void aDifferentKeyCannotDecrypt() {
        String stored = cipher.encrypt("sk-real");
        AesGcmSecretCipher other = new AesGcmSecretCipher(new EncryptionProperties(KEY_B));
        assertThatThrownBy(() -> other.decrypt(stored)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    void malformedStoredValuesAreRefusedWithoutEchoingThem() {
        for (String bad : new String[] {null, "", "plaintext", "v1:onlytwo", "v2:aaaa:bbbb", "v1:!!!:???", "v1::",
                "v1:AAAA:BBBB:CCCC"}) {
            assertThatThrownBy(() -> cipher.decrypt(bad)).as(String.valueOf(bad))
                    .isInstanceOf(IllegalStateException.class);
        }
    }
}
