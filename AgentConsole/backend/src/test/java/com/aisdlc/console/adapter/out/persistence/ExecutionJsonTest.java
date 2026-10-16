package com.aisdlc.console.adapter.out.persistence;

import com.aisdlc.console.domain.model.execution.EngineCapabilities;
import com.aisdlc.console.domain.model.execution.EngineCapabilityState;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@code execution_runs.engine_capabilities}（JSONB；契約 §0.5 V10）的 JSON 互轉。為什麼重要：這個欄位在建立批次時寫一次、之後只讀；
 * 寫出的鍵名是契約固定的（前後版本、QA 直接查庫都靠它），而讀回時遇到缺鍵或不認得的值<b>不可丟例外</b>——
 * 否則一筆壞資料（或日後新增的狀態值）會讓整個批次詳情與列表端點 500。
 */
class ExecutionJsonTest {

    @Test
    void theCapabilitiesAreWrittenUnderTheFixedKeysWithTheEnumNames() {
        String json = ExecutionJson.capabilitiesToJson(new EngineCapabilities(EngineCapabilityState.ENABLED,
                EngineCapabilityState.UNAVAILABLE_NO_API_KEY));

        assertThat(json).isEqualTo("{\"autoMutation\":\"ENABLED\",\"selfEvolution\":\"UNAVAILABLE_NO_API_KEY\"}");
    }

    @Test
    void noCapabilitiesAreWrittenAsSqlNull() {
        assertThat(ExecutionJson.capabilitiesToJson(null)).isNull();
    }

    @Test
    void whatWasWrittenReadsBackUnchangedForEveryPairOfStates() {
        for (EngineCapabilityState autoMutation : EngineCapabilityState.values()) {
            for (EngineCapabilityState selfEvolution : EngineCapabilityState.values()) {
                EngineCapabilities original = new EngineCapabilities(autoMutation, selfEvolution);
                assertThat(ExecutionJson.capabilitiesFromJson(ExecutionJson.capabilitiesToJson(original)))
                        .isEqualTo(original);
            }
        }
    }

    @Test
    void anAbsentColumnOrAnEmptyValueMeansTheRunPredatesV10() {
        assertThat(ExecutionJson.capabilitiesFromJson(null)).isNull();
        assertThat(ExecutionJson.capabilitiesFromJson("")).isNull();
        assertThat(ExecutionJson.capabilitiesFromJson("   ")).isNull();
        assertThat(ExecutionJson.capabilitiesFromJson("{}")).isNull();
    }

    @Test
    void aMissingKeyOrUnknownValueMeansThatKeyIsAbsent() {
        assertThat(ExecutionJson.capabilitiesFromJson("{\"autoMutation\":\"ENABLED\"}"))
                .isEqualTo(new EngineCapabilities(EngineCapabilityState.ENABLED, null));
        assertThat(ExecutionJson.capabilitiesFromJson("{\"selfEvolution\":\"OFF\"}"))
                .isEqualTo(new EngineCapabilities(null, EngineCapabilityState.OFF));
        assertThat(ExecutionJson.capabilitiesFromJson("{\"autoMutation\":\"SOMETHING_NEW\",\"selfEvolution\":\"ENABLED\"}"))
                .as("日後新增的狀態值：只有它那一個鍵缺席").isEqualTo(new EngineCapabilities(null, EngineCapabilityState.ENABLED));
        assertThat(ExecutionJson.capabilitiesFromJson("{\"autoMutation\":\"BOGUS\",\"selfEvolution\":42}")).isNull();
        assertThat(ExecutionJson.capabilitiesFromJson("{\"autoMutation\":null,\"selfEvolution\":\"enabled\"}"))
                .as("區分大小寫").isNull();
    }

    @Test
    void aNonObjectValueIsTreatedAsNoCapabilities() {
        assertThat(ExecutionJson.capabilitiesFromJson("[\"ENABLED\"]")).isNull();
        assertThat(ExecutionJson.capabilitiesFromJson("\"ENABLED\"")).isNull();
        assertThat(ExecutionJson.capabilitiesFromJson("not json at all")).isNull();
    }
}
