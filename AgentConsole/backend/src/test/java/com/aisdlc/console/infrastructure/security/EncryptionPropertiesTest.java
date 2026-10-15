package com.aisdlc.console.infrastructure.security;

import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;

import java.util.Base64;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 啟動期驗證：CONSOLE_ENCRYPTION_KEY 缺少、不是 base64、或解碼後不是 32 bytes＝啟動失敗（與 JWT_SECRET 同款 fail-fast）。
 * 為什麼重要：金鑰設錯卻照樣啟動，敏感參數就會被「用錯誤長度的弱金鑰」或「靜默不加密」存進資料庫。
 */
class EncryptionPropertiesTest {

    @Configuration
    @EnableConfigurationProperties(EncryptionProperties.class)
    static class PropsConfig {
    }

    private final ApplicationContextRunner runner = new ApplicationContextRunner().withUserConfiguration(PropsConfig.class);

    private static String base64Of(int bytes) {
        return Base64.getEncoder().encodeToString(new byte[bytes]);
    }

    @Test
    void aMissingKeyFailsStartupAndNamesTheEnvironmentVariable() {
        runner.run(context -> {
            assertThat(context).hasFailed();
            assertThat(context.getStartupFailure()).hasStackTraceContaining("CONSOLE_ENCRYPTION_KEY");
        });
    }

    @Test
    void aBlankKeyFailsStartup() {
        runner.withPropertyValues("console.encryption.key=").run(context -> {
            assertThat(context).hasFailed();
            assertThat(context.getStartupFailure()).hasStackTraceContaining("CONSOLE_ENCRYPTION_KEY");
        });
    }

    @Test
    void aKeyThatIsNotBase64FailsStartup() {
        runner.withPropertyValues("console.encryption.key=this is not base64!!!").run(context -> {
            assertThat(context).hasFailed();
            assertThat(context.getStartupFailure()).hasStackTraceContaining("base64");
        });
    }

    @Test
    void aThirtyOneOrThirtyThreeByteKeyFailsAndExactlyThirtyTwoPasses() {
        for (int wrong : new int[] {16, 24, 31, 33, 64}) {
            runner.withPropertyValues("console.encryption.key=" + base64Of(wrong)).run(context -> {
                assertThat(context).as(wrong + " bytes").hasFailed();
                assertThat(context.getStartupFailure()).hasStackTraceContaining("32 bytes");
            });
        }
        runner.withPropertyValues("console.encryption.key=" + base64Of(32)).run(context -> {
            assertThat(context).hasNotFailed();
            assertThat(context.getBean(EncryptionProperties.class).keyBytes()).hasSize(32);
        });
    }

    @Test
    void surroundingWhitespaceFromAnEnvFileIsTolerated() {
        runner.withPropertyValues("console.encryption.key= " + base64Of(32) + " ")
                .run(context -> assertThat(context).hasNotFailed());
    }
}
