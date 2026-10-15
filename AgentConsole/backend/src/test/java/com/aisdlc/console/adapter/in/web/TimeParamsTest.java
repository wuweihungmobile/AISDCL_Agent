package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ValidationException;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 查詢參數裡的時間（{@code from}／{@code to}）。為什麼重要：URL 查詢字串裡沒編碼的 {@code +} 會被伺服器解成空白——
 * 帶 {@code +08:00} 的時間因此變成 {@code 16:40:00 08:00}，若直接回 400，使用者看到的是看不懂的錯誤，且視窗被悄悄換成預設值更糟。
 */
class TimeParamsTest {

    private static final Instant EXPECTED = Instant.parse("2026-10-15T08:40:00Z");

    @Test
    void absentOrBlankMeansUseTheDefault() {
        assertThat(TimeParams.parse("from", null)).isNull();
        assertThat(TimeParams.parse("from", "")).isNull();
        assertThat(TimeParams.parse("from", "   ")).isNull();
    }

    @Test
    void anIsoTimeWithAnOffsetIsConvertedToAnInstant() {
        assertThat(TimeParams.parse("to", "2026-10-15T08:40:00Z")).isEqualTo(EXPECTED);
        assertThat(TimeParams.parse("to", "2026-10-15T16:40:00+08:00")).isEqualTo(EXPECTED);
        assertThat(TimeParams.parse("to", "2026-10-15T08:40:00.250Z")).isEqualTo(EXPECTED.plusMillis(250));
        assertThat(TimeParams.parse("to", "  2026-10-15T08:40:00Z  ")).as("前後空白被修剪").isEqualTo(EXPECTED);
    }

    @Test
    void aPlusThatTheQueryStringTurnedIntoASpaceIsRestoredInsteadOfRejected() {
        assertThat(TimeParams.parse("from", "2026-10-15T16:40:00 08:00")).isEqualTo(EXPECTED);
        assertThat(TimeParams.parse("from", "2026-10-15T04:40:00-04:00")).as("負 offset 本來就正確，不受還原邏輯影響")
                .isEqualTo(EXPECTED);
    }

    @Test
    void aTimeWithoutAnOffsetOrWithGarbageIsA400NamingTheParameter() {
        for (String bad : new String[] {"2026-10-15T08:40:00", "2026-10-15", "yesterday", "2026-13-40T00:00:00Z",
                "1760517600"}) {
            assertThatThrownBy(() -> TimeParams.parse("from", bad)).as(bad).isInstanceOfSatisfying(
                    ValidationException.class, e -> assertThat(e.violations().get(0).field()).isEqualTo("from"));
        }
        assertThatThrownBy(() -> TimeParams.parse("to", "x")).hasMessageContaining("to 必須是帶 offset 的 ISO-8601 時間");
    }
}
