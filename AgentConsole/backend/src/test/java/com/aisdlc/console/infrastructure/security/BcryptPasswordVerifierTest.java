package com.aisdlc.console.infrastructure.security;

import org.junit.jupiter.api.Test;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 密碼雜湊比對。backend/README.md 教人用 Docker 的 htpasswd 產生 {@code $2y$} 前綴的 BCrypt 雜湊貼進
 * CONSOLE_*_PASSWORD_HASH；這裡釘住「$2a／$2b／$2y 三種前綴都能被接受」，避免 README 的做法在升級後悄悄失效。
 */
class BcryptPasswordVerifierTest {

    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
    private final BcryptPasswordVerifier verifier = new BcryptPasswordVerifier(encoder);

    @Test
    void aFreshlyEncodedPasswordMatchesAndAWrongOneDoesNot() {
        String hash = encoder.encode("S3cret!pass");
        assertThat(verifier.matches("S3cret!pass", hash)).isTrue();
        assertThat(verifier.matches("s3cret!pass", hash)).isFalse();
        assertThat(verifier.matches("", hash)).isFalse();
    }

    @Test
    void theHtpasswdStyleVariantPrefixesAreAccepted() {
        String hash = encoder.encode("Sample#Pass123");
        for (String prefix : new String[] {"$2a$", "$2b$", "$2y$"}) {
            String variant = prefix + hash.substring(4);
            assertThat(verifier.matches("Sample#Pass123", variant)).as(prefix).isTrue();
            assertThat(verifier.matches("wrong", variant)).as(prefix + " wrong").isFalse();
        }
    }

    @Test
    void aMalformedHashNeverMatches() {
        assertThat(verifier.matches("anything", "not-a-bcrypt-hash")).isFalse();
        assertThat(verifier.matches("anything", "")).isFalse();
    }
}
