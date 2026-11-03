package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.SiKeyNames;
import com.aisdlc.console.adapter.in.web.dto.research.CapabilitiesDto;
import com.aisdlc.console.adapter.in.web.dto.research.ReconcileResultDto;
import com.aisdlc.console.support.BridgeSource;
import com.aisdlc.minibridge.MiniResearch;
import org.junit.jupiter.api.Test;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * console-api 與迷你 Bridge 對<b>真 Bridge 回應形狀</b>的源頭鎖（ResearchToPRD P0 修復棒；INT-01／03／08）。三個缺陷同一個根因：DTO 與迷你 Bridge 各自照「自己猜的」形狀寫
 * （{@code name} 對 {@code id}、snake_case 對 camelCase、少讀五個鍵），兩端互相印證而都錯，只有 Docker 全棧才現形。這裡把期望值的來源換成 Bridge 的 Python 原始碼
 * （{@link BridgeSource}：只讀文字）：Bridge 宣告了什麼鍵，迷你 Bridge 就逐鍵照做，DTO 就逐鍵讀得到——Bridge 改了形狀而這邊沒跟，這支測試當場紅。
 *
 * <p>為什麼不另存黃金檔：黃金檔是某一刻的快照，Bridge 改了不會有任何東西變紅；原始碼才是 Bridge 自己也得遵守的單一出處（Bridge 端以
 * {@code tests/test_research_reconcile.py}、{@code tests/test_research_settings.py} 釘住同一份宣告）。
 */
class ResearchBridgeShapeTest {

    private static final String[] RECONCILE = {"research", "gates", "reconcile.py"};
    private static final String[] SETTINGS = {"research", "settings.py"};
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };

    @Test
    void theMiniBridgeReconcileBodyHasExactlyTheKeysTheBridgeSourceDeclares() {
        Map<String, Object> body = MiniResearch.reconcileBody(MiniResearch.consistentReconcileChecks());

        assertThat(body.keySet()).as("對帳回應的頂層鍵（reconcile_result）").containsExactlyElementsOf(BridgeSource.returnedKeys("reconcile_result", RECONCILE));
        List<Map<String, Object>> checks = checksOf(body);
        assertThat(checks).extracting(check -> check.get("id")).as("對帳項的識別與順序（CHECK_IDS）")
                .containsExactlyElementsOf(BridgeSource.constants("CHECK_IDS", RECONCILE));
        List<String> checkKeys = BridgeSource.returnedKeys("absent_check", RECONCILE);
        assertThat(checkKeys).as("識別鍵是 id，不是 name（INT-01）").contains("id").doesNotContain("name");
        assertThat(checks).allSatisfy(check -> assertThat(check.keySet()).containsExactlyElementsOf(checkKeys));
        Map<String, Object> drift = MiniResearch.reconcileDrift("PRD", "01_specs/PRD-v1.0.0.md", "a".repeat(64), null);
        assertThat(drift.keySet()).as("漂移列的鍵（_drift）：兩個摘要欄是 camelCase").containsExactlyElementsOf(BridgeSource.returnedKeys("_drift", RECONCILE));
        assertThat(drift.keySet()).contains("expectedSha256", "actualSha256");
    }

    @Test
    void theReconcileDtoReadsTheBridgeIdAndBothCamelCaseDigestsOfEveryDriftRow() {
        List<Map<String, Object>> checks = new ArrayList<>(MiniResearch.consistentReconcileChecks());
        checks.set(1, MiniResearch.reconcileCheck("prd_sha256", "drift", true, "",
                List.of(MiniResearch.reconcileDrift("PRD", "01_specs/PRD-v1.0.0.md", "a".repeat(64), "b".repeat(64)))));

        ReconcileResultDto dto = ReconcileResultDto.from(MiniResearch.reconcileBody(checks));

        assertThat(dto.consistent()).isFalse();
        assertThat(dto.checks()).extracting(ReconcileResultDto.CheckDto::name).as("name 取自 Bridge 的 id、一項不漏").containsExactlyElementsOf(BridgeSource.constants("CHECK_IDS", RECONCILE));
        ReconcileResultDto.DriftDto row = dto.checks().get(1).drift().get(0);
        assertThat(row.expectedSha256()).isEqualTo("a".repeat(64));
        assertThat(row.actualSha256()).isEqualTo("b".repeat(64));
    }

    @Test
    void theMiniBridgeCapabilitiesBodyHasExactlyTheInfoKeysPlusTheContractKeysTheBridgeSourceDeclares() {
        List<String> declared = new ArrayList<>(BridgeSource.constants("INFO_KEYS", SETTINGS));
        declared.addAll(BridgeSource.constants("CAPABILITY_EXTRA_KEYS", SETTINGS));

        Map<String, Object> body = MiniResearch.capabilitiesBody("local", true, true, MiniResearch.FETCH_HOSTS);

        assertThat(body.keySet()).as("能力探針本文的鍵集合與順序：research_info 八個加契約 §2.1 的五個（D-76(1)）").containsExactlyElementsOf(declared);
    }

    @Test
    void theCapabilitiesDtoHasAFieldForEveryKeyTheBridgeSendsAndFillsItFromTheBridgeValue() {
        Map<String, Object> body = MiniResearch.capabilitiesBody("mock-only", false, true, List.of("api.github.com"));

        Map<String, Object> out = JSON.convertValue(CapabilitiesDto.from(body), OBJECT);

        for (String key : body.keySet()) {
            // root 是 research_root 的舊名：兩者同值、DTO 只有 researchRoot 一個欄位
            String field = "root".equals(key) ? "researchRoot" : SiKeyNames.camel(key);
            assertThat(out).as("Bridge 的鍵 %s 在 CapabilitiesDto 沒有對應欄位 %s（INT-08：少讀的鍵會讓前端永遠看到預設值）", key, field).containsKey(field);
        }
        assertThat(out).containsEntry("mode", "mock-only").containsEntry("db", false).containsEntry("webLayerEnabled", true)
                .containsEntry("sddRoot", MiniResearch.SDD_ROOT).containsEntry("researchRoot", MiniResearch.RESEARCH_ROOT)
                .containsEntry("repoWritable", true).containsEntry("fetchHosts", List.of("api.github.com"));
        assertThat(out.get("scaffoldRoot")).isNull();
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> checksOf(Map<String, Object> body) {
        return (List<Map<String, Object>>) body.get("checks");
    }
}
