package com.aisdlc.console.infrastructure.config;

import com.aisdlc.console.application.port.out.SiWriteSettings;
import com.aisdlc.console.domain.model.si.SiAuditKeyRing;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.ConfigDataApplicationContextInitializer;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Configuration;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * SelfImproving 寫入載體的設定（{@code console.si.*}、{@code console.bridge.si-write-token}；TCS-SelfImprovingDecide-P2b AT-950-5-1、
 * AT-950-5-E-1）。為什麼重要：金鑰與權杖設錯卻靜默退回「停用」，部署者會以為寫入面開著、實際上每個請求都被擋；而金鑰一旦進了錯誤訊息，
 * 容器日誌就成了金鑰外洩的通道——所以過短或佔位一律啟動即失敗，且訊息與 toString 都只講屬性名、第幾把與長度。
 */
class SiWritePropertiesTest {

    /** 隨機的金鑰字面（不含 {@code sk-} 形態；任何 8 字元子字串都不該出現在錯誤訊息）。 */
    private static final String K1 = "Zq7Xk93LmP2vB5Nn8Rt1Yh4Gd6Fs0JaW";
    private static final String K2 = "Hc3Vw9Ue5Ty1Oi7Pa2Sd6Fg8Jk4Lz0Xq";
    private static final String TOKEN_64 = "d41f9c0a7be2386a5c1e04d97b3f2a68e5c70b19a4d36f8e2b05c97a1d3e4f60";

    @Configuration
    @EnableConfigurationProperties({SiWriteProperties.class, BridgeProperties.class})
    static class PropsConfig {
    }

    private final ApplicationContextRunner runner = new ApplicationContextRunner().withUserConfiguration(PropsConfig.class);
    private final ApplicationContextRunner withYml = new ApplicationContextRunner()
            .withInitializer(new ConfigDataApplicationContextInitializer()).withUserConfiguration(PropsConfig.class);

    private static String rootMessage(Throwable failure) {
        Throwable cause = failure;
        while (cause.getCause() != null && cause.getCause() != cause) {
            cause = cause.getCause();
        }
        return String.valueOf(cause.getMessage());
    }

    /** 訊息不含 {@code secret} 的任何 8 字元以上子字串（NFR-P2b-4）。 */
    private static void assertNoLeak(String message, String secret) {
        for (int i = 0; i + 8 <= secret.length(); i++) {
            assertThat(message).as("訊息不得含祕密的子字串 %d", i).doesNotContain(secret.substring(i, i + 8));
        }
    }

    // ── AT-950-5-1：綁定與預設 ───────────────────────────────────────────────────────────────

    @Test
    void AT_950_5_1_decidersAreNormalizedTheRingKeepsItsOrderAndTheTokenIsBound() {
        runner.withPropertyValues("console.si.deciders=  admin , ops ,,admin", "console.si.audit-key=" + K1 + "," + K2,
                "console.bridge.si-write-token=" + TOKEN_64).run(context -> {
                    SiWriteProperties si = context.getBean(SiWriteProperties.class);
                    BridgeProperties bridge = context.getBean(BridgeProperties.class);

                    assertThat(si.deciders()).as("去空白、去空項、去重、保序").containsExactly("admin", "ops");
                    assertThat(si.keyRing().keys()).as("環序＝設定序；第一把簽章").containsExactly(K1, K2);
                    assertThat(si.keyRing().signingKey()).isEqualTo(K1);
                    assertThat(bridge.siWriteToken()).isEqualTo(TOKEN_64);
                    assertThat(bridge.siWriteTokenConfigured()).isTrue();
                    assertThat(bridge.sddWriteTokenConfigured()).as("兩個權杖互相獨立").isFalse();
                    SiWriteSettings settings = new SiWriteSettingsAdapter(si, bridge);
                    assertThat(settings.deciders()).containsExactly("admin", "ops");
                    assertThat(settings.keyRing().keys()).containsExactly(K1, K2);
                    assertThat(settings.bridgeWriteTokenConfigured()).isTrue();
                });
    }

    @Test
    void AT_950_5_1_theDefaultsDisableTheWriteSurfaceAndNameNoOne() {
        runner.run(context -> {
            SiWriteProperties si = context.getBean(SiWriteProperties.class);
            BridgeProperties bridge = context.getBean(BridgeProperties.class);

            assertThat(si.deciders()).as("預設空＝無人可寫").isEmpty();
            assertThat(si.auditKey()).isNull();
            assertThat(si.keyRing().isEmpty()).isTrue();
            assertThat(bridge.siWriteToken()).isNull();
            SiWriteSettings settings = new SiWriteSettingsAdapter(si, bridge);
            assertThat(settings.keyRing()).isEqualTo(SiAuditKeyRing.EMPTY);
            assertThat(settings.bridgeWriteTokenConfigured()).isFalse();
        });
        withYml.run(context -> {
            assertThat(context.getBean(SiWriteProperties.class).deciders()).as("出貨的 application.yml 也預設空").isEmpty();
            assertThat(context.getBean(SiWriteProperties.class).auditKey()).isNull();
            assertThat(context.getBean(BridgeProperties.class).siWriteToken()).isNull();
        });
    }

    @Test
    void AT_950_5_1_theDocumentedEnvironmentVariablesReachTheBoundProperties() {
        withYml.withSystemProperties("CONSOLE_SI_DECIDERS=admin,ops_admin", "CONSOLE_SI_AUDIT_KEY=" + K1 + "," + K2,
                "BRIDGE_SI_WRITE_TOKEN=" + TOKEN_64).run(context -> {
                    SiWriteProperties si = context.getBean(SiWriteProperties.class);

                    assertThat(si.deciders()).containsExactly("admin", "ops_admin");
                    assertThat(si.keyRing().keys()).containsExactly(K1, K2);
                    assertThat(context.getBean(BridgeProperties.class).siWriteToken()).isEqualTo(TOKEN_64);
                });
    }

    @Test
    void AT_950_5_1_toStringOnlyShowsSetOrUnsetForTheKeyAndTheToken() {
        SiWriteProperties withKey = new SiWriteProperties(List.of("admin"), K1 + "," + K2);
        BridgeProperties withToken = new BridgeProperties("http://bridge:8081", null, TOKEN_64);

        assertThat(withKey.toString()).contains("<set>").doesNotContain(K1).doesNotContain(K2).contains("admin");
        assertThat(new SiWriteProperties(null, null).toString()).contains("<unset>");
        assertThat(withKey.keyRing().toString()).as("金鑰環本身的 toString 也只講把數").doesNotContain(K1).contains("2");
        assertThat(withToken.toString()).contains("siWriteToken=<set>").doesNotContain(TOKEN_64);
        assertThat(new BridgeProperties("http://bridge:8081", null, null).toString()).contains("siWriteToken=<unset>");
    }

    @Test
    void AT_950_5_1_aBlankTokenAndABlankRingMeanDisabledNotAnError() {
        for (String blank : new String[] {"", "   ", "\t"}) {
            assertThat(new BridgeProperties(null, null, blank).siWriteToken()).as("空白權杖＝停用").isNull();
            assertThat(new SiWriteProperties(null, blank).auditKey()).as("空白環＝停用").isNull();
        }
        assertThat(new SiWriteProperties(null, " , , ").auditKey()).as("全為空項的環視同未設").isNull();
        assertThat(new BridgeProperties(null, null, "  " + TOKEN_64 + "\n").siWriteToken()).as("權杖去前後空白").isEqualTo(TOKEN_64);
    }

    // ── AT-950-5-E-1：啟動失敗，訊息只講長度與序號 ─────────────────────────────────────────────

    @Test
    void AT_950_5_E_1_aRingWithAShortKeyFailsStartupAndNamesOnlyTheOrdinalAndLength() {
        String shortKey = "Short-Key-0123456789";                // 20 字元
        runner.withPropertyValues("console.si.audit-key=" + K1 + "," + shortKey).run(context -> {
            assertThat(context).hasFailed();
            String message = rootMessage(context.getStartupFailure());

            assertThat(message).contains("console.si.audit-key").contains("第 2 把").contains("20").contains("32");
            assertNoLeak(message, shortKey);
            assertNoLeak(message, K1);
        });
        assertThatThrownBy(() -> new SiWriteProperties(List.of(), K1.substring(0, 31))).isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("31");
    }

    @Test
    void AT_950_5_E_1_aPlaceholderKeyFailsStartupEvenWhenLongEnough() {
        String placeholder = "<YOUR_CONSOLE_SI_AUDIT_KEY_MIN_32_CHARS>";
        assertThat(placeholder.length()).as("佔位本身夠長，不能只靠長度檢查擋下它").isGreaterThanOrEqualTo(32);

        assertThatThrownBy(() -> new SiWriteProperties(List.of(), placeholder)).isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("佔位").hasMessageContaining("第 1 把").hasMessageNotContaining(placeholder)
                .hasMessageNotContaining("YOUR_CONSOLE");
        assertThatThrownBy(() -> new SiWriteProperties(List.of(), "<YOUR_KEY>")).isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("佔位");
        runner.withPropertyValues("console.si.audit-key=" + placeholder).run(context -> assertThat(context).hasFailed());
    }

    @Test
    void AT_950_5_E_1_aShortOrPlaceholderBridgeTokenFailsStartupWithoutLeakingIt() {
        String shortToken = "s3cr3t-si-token-0123456789";         // 26 字元
        runner.withPropertyValues("console.bridge.si-write-token=" + shortToken).run(context -> {
            assertThat(context).hasFailed();
            String message = rootMessage(context.getStartupFailure());

            assertThat(message).contains("console.bridge.si-write-token").contains("BRIDGE_SI_WRITE_TOKEN").contains("26")
                    .contains("32");
            assertNoLeak(message, shortToken);
        });
        assertThatThrownBy(() -> new BridgeProperties(null, null, "x".repeat(31))).isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("31").hasMessageContaining("SelfImproving");
        assertThat(new BridgeProperties(null, null, "x".repeat(32)).siWriteTokenConfigured()).isTrue();
        String placeholder = "<YOUR_BRIDGE_SI_WRITE_TOKEN_MIN_32_CHARS>";
        assertThatThrownBy(() -> new BridgeProperties(null, null, placeholder)).isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("佔位").hasMessageNotContaining(placeholder);
    }

    @Test
    void AT_950_5_E_1_theTwoTokensAreValidatedIndependentlyAndTheSddMessageIsUnchanged() {
        assertThatThrownBy(() -> new BridgeProperties(null, "x".repeat(31), null)).isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("console.bridge.sdd-write-token").hasMessageContaining("SDD 寫入面")
                .hasMessageNotContaining("SelfImproving");
        BridgeProperties both = new BridgeProperties(null, "a".repeat(32), "b".repeat(32));
        assertThat(both.sddWriteToken()).isNotEqualTo(both.siWriteToken());
    }
}
