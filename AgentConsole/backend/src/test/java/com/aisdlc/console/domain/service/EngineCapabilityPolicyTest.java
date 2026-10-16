package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.execution.EngineCapabilities;
import com.aisdlc.console.domain.model.execution.EngineCapabilityState;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import static com.aisdlc.console.domain.model.execution.EngineCapabilityState.ENABLED;
import static com.aisdlc.console.domain.model.execution.EngineCapabilityState.OFF;
import static com.aisdlc.console.domain.model.execution.EngineCapabilityState.UNAVAILABLE_NO_API_KEY;
import static org.assertj.core.api.Assertions.assertThat;

/**
 * 引擎能力的決策表（契約 §3.4.2；D-11）。為什麼重要：這張表決定「批次回應與資料庫裡寫的能力」與「真的送給引擎的設定」——
 * 寫反一個格子，前端就會顯示引擎沒做的事（例如沒有金鑰卻標成已啟用），或把引擎要做的事標成關閉。
 * 完整的「等級 × 旗標 × 金鑰」矩陣與送出的 {@code minimax.*} 由 {@code ConfigMaterializerTest} 逐列驗；這裡只驗純決策函式本身。
 */
class EngineCapabilityPolicyTest {

    private static EngineCapabilities decide(int level, boolean autoMutation, boolean selfEvolution, boolean kernelBrain,
                                             boolean hasKey) {
        return EngineCapabilityPolicy.decide(level, autoMutation, selfEvolution, kernelBrain, hasKey);
    }

    /**
     * 決策表 8 列（等級 3，{@code agent.enableAutoMutation=false}：{@code brainRequested} 由 {@code model.enableKernelBrain} 製造、
     * {@code effSelfEvolution} 由 {@code agent.enableSelfEvolution} 製造）。欄位依序：列號、有金鑰、brainRequested、
     * effSelfEvolution、預期 autoMutation、預期 selfEvolution。
     *
     * <p>方法名與參數型別刻意取短（預期狀態以字串傳入再轉列舉）：Gradle 9.8 的 HTML 測試報告為參數化測試建一個以
     * 「方法名＋參數型別」命名的目錄，名稱過長會讓報告路徑逼近 Windows 的 260 字元上限。
     */
    @ParameterizedTest(name = "row {0}")
    @CsvSource({
            "1,true,true,true,ENABLED,ENABLED",
            "2,true,true,false,ENABLED,ENABLED",
            "3,true,false,true,OFF,ENABLED",
            "4,true,false,false,OFF,ENABLED",
            "5,false,true,true,UNAVAILABLE_NO_API_KEY,UNAVAILABLE_NO_API_KEY",
            "6,false,true,false,UNAVAILABLE_NO_API_KEY,OFF",
            "7,false,false,true,OFF,UNAVAILABLE_NO_API_KEY",
            "8,false,false,false,OFF,OFF"})
    void tableRow(int row, boolean hasKey, boolean brain, boolean evolution, String autoMutation,
                  String selfEvolution) {
        assertThat(decide(3, false, evolution, brain, hasKey)).as("列 " + row)
                .isEqualTo(new EngineCapabilities(EngineCapabilityState.valueOf(autoMutation),
                        EngineCapabilityState.valueOf(selfEvolution)));
    }

    @Test
    void levelSixAndSevenAreTheFirstToRequestEachCapability() {
        assertThat(EngineCapabilityPolicy.AUTO_MUTATION_FROM_LEVEL).isEqualTo(6);
        assertThat(EngineCapabilityPolicy.SELF_EVOLUTION_FROM_LEVEL).isEqualTo(7);

        // 有金鑰：5 沒人要求 Brain、6 起要求
        assertThat(decide(5, false, false, false, true).autoMutation()).isEqualTo(OFF);
        assertThat(decide(6, false, false, false, true).autoMutation()).isEqualTo(ENABLED);
        // 沒有金鑰：自動突變 6 起「有人要求但送不出去」；自演化 7 起
        assertThat(decide(5, false, false, false, false)).isEqualTo(new EngineCapabilities(OFF, OFF));
        assertThat(decide(6, false, false, false, false))
                .isEqualTo(new EngineCapabilities(UNAVAILABLE_NO_API_KEY, OFF));
        assertThat(decide(7, false, false, false, false))
                .isEqualTo(new EngineCapabilities(UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY));
        assertThat(decide(10, false, false, false, false))
                .isEqualTo(new EngineCapabilities(UNAVAILABLE_NO_API_KEY, UNAVAILABLE_NO_API_KEY));
    }

    @Test
    void aFalseFlagCannotSwitchOffWhatTheLevelForces() {
        // 契約 §3.4.2 誠實劃界 2：要關 Brain 校正請降等級或清掉金鑰，不是把旗標設成 false
        assertThat(decide(7, false, false, false, true)).isEqualTo(new EngineCapabilities(ENABLED, ENABLED));
        assertThat(decide(10, false, false, false, true)).isEqualTo(new EngineCapabilities(ENABLED, ENABLED));
    }

    @Test
    void bothBrainFlagsShareOneEngineKey() {
        for (boolean hasKey : new boolean[] {false, true}) {
            EngineCapabilities viaAutoMutation = decide(3, true, false, false, hasKey);
            EngineCapabilities viaKernelBrain = decide(3, false, false, true, hasKey);
            EngineCapabilities viaBoth = decide(3, true, false, true, hasKey);
            assertThat(viaKernelBrain).as("有金鑰=" + hasKey).isEqualTo(viaAutoMutation).isEqualTo(viaBoth);
        }
    }

    @Test
    void withAKeySelfEvolutionIsAlwaysEnabled() {
        for (int level = 1; level <= 10; level++) {
            for (int mask = 0; mask < 8; mask++) {
                assertThat(decide(level, (mask & 1) != 0, (mask & 2) != 0, (mask & 4) != 0, true).selfEvolution())
                        .as("等級 " + level + "、旗標 " + mask).isEqualTo(ENABLED);
            }
        }
    }

    @Test
    void withoutAKeyNothingIsReportedAsEnabled() {
        for (int level = 1; level <= 10; level++) {
            for (int mask = 0; mask < 8; mask++) {
                EngineCapabilities result = decide(level, (mask & 1) != 0, (mask & 2) != 0, (mask & 4) != 0, false);
                assertThat(result.autoMutation()).as("等級 " + level + "、旗標 " + mask).isNotEqualTo(ENABLED);
                assertThat(result.selfEvolution()).as("等級 " + level + "、旗標 " + mask).isNotEqualTo(ENABLED);
            }
        }
    }

    @Test
    void storedNamesParseBackAndUnknownIsNotAnError() {
        for (EngineCapabilityState state : EngineCapabilityState.values()) {
            assertThat(EngineCapabilityState.parse(state.name())).contains(state);
        }
        assertThat(EngineCapabilityState.parse("enabled")).as("區分大小寫：資料庫存的是列舉名稱").isEmpty();
        assertThat(EngineCapabilityState.parse("SOMETHING_NEW")).isEmpty();
        assertThat(EngineCapabilityState.parse(null)).isEmpty();
        assertThat(EngineCapabilityState.parse(1)).isEmpty();
    }
}
