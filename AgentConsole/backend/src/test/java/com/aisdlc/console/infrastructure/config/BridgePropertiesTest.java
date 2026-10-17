package com.aisdlc.console.infrastructure.config;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Bridge 屬性（契約附錄 D.2、ADR-XPLAT-016 §9）：位址的兜底與 SDD 寫入權杖的啟動驗證。為什麼重要：權杖設錯卻靜默退回「停用」，
 * 部署者會以為 SDD 迴圈開著、實際上每個批次都悄悄走非治理路徑；所以短了或佔位一律啟動即失敗，並且錯誤訊息與 toString 都不能洩漏值。
 */
class BridgePropertiesTest {

    private static final String TOKEN_64 = "0123456789abcdef".repeat(4);

    // 顯示名刻意不帶參數值：空白、tab 與角括號都不該進報告的檔案路徑（Windows 路徑字元與長度）
    @ParameterizedTest(name = "未設權杖（第 {index} 組）＝停用")
    @NullAndEmptySource
    @ValueSource(strings = {"   ", "\t"})
    void aBlankTokenMeansTheWriteSurfaceIsDisabled(String blank) {
        BridgeProperties properties = new BridgeProperties("http://bridge:8081", blank);

        assertThat(properties.sddWriteToken()).isNull();
        assertThat(properties.sddWriteTokenConfigured()).isFalse();
    }

    @Test
    void aTokenOfAtLeastThirtyTwoCharactersIsAcceptedAndStripped() {
        assertThat(new BridgeProperties(null, "x".repeat(32)).sddWriteTokenConfigured()).isTrue();
        BridgeProperties padded = new BridgeProperties(null, "  " + TOKEN_64 + "\n");

        assertThat(padded.sddWriteToken()).isEqualTo(TOKEN_64);
    }

    @Test
    void aTokenShorterThanThirtyTwoCharactersFailsStartupWithoutLeakingIt() {
        String shortToken = "s3cr3t-short-token-0123456789";   // 29 字元

        assertThatThrownBy(() -> new BridgeProperties(null, shortToken)).isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("29").hasMessageContaining("32").hasMessageNotContaining(shortToken);
        assertThatThrownBy(() -> new BridgeProperties(null, "x".repeat(31))).isInstanceOf(IllegalArgumentException.class);
    }

    @ParameterizedTest(name = "佔位第 {index} 組啟動即失敗")
    @ValueSource(strings = {"<YOUR_BRIDGE_SDD_WRITE_TOKEN_MIN_32_CHARS>", "<changeme-but-long-enough-for-thirty-two>"})
    void anExampleEnvPlaceholderFailsStartupEvenWhenLongEnough(String placeholder) {
        assertThat(placeholder.length()).as("佔位本身夠長，不能只靠長度檢查擋下它").isGreaterThanOrEqualTo(32);

        assertThatThrownBy(() -> new BridgeProperties(null, placeholder)).isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("佔位").hasMessageNotContaining(placeholder);
    }

    @Test
    void toStringNeverShowsTheTokenValue() {
        String shown = new BridgeProperties("http://bridge:8081", TOKEN_64).toString();

        assertThat(shown).doesNotContain(TOKEN_64).contains("http://bridge:8081").contains("<set>");
        assertThat(new BridgeProperties("http://bridge:8081", null).toString()).contains("<unset>");
    }

    @Test
    void theUrlFallsBackToTheLocalDefaultWhenBlank() {
        assertThat(new BridgeProperties(" ", null).url()).isEqualTo(BridgeProperties.LOCAL_DEFAULT);
        assertThat(new BridgeProperties(" http://x:1 ", null).url()).isEqualTo("http://x:1");
    }
}
