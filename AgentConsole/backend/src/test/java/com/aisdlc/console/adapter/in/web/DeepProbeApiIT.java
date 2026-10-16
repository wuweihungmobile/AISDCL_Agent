package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge.DeepHealthMode;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 探測環打深度探針的整條鏈（契約 §3.1、§3.1.1；D-17；E2E-16 第 2 列的後端面）：迷你 Bridge 的 {@code GET /health/deep} →
 * 真的 {@code BridgeHttpAdapter} → {@code BridgeHealthMonitor} → 頂列的連線燈（{@code /notifications/summary}）與 Agent 可用率 KPI。
 * 為什麼重要：舊預設 {@code /health} 在 Bridge 的 git 或工作區壞掉時照回 200，Console 一直顯示「引擎正常」直到下一個批次失敗；
 * 深度探針的 503 要真的讓燈熄掉、讓可用率下降；而 {@code sdd} 檢查只是資訊——SDD 目錄的問題不能把與它無關的 AutoClaude 批次標成不可用。
 * 單元層各段（適配器只看狀態碼、監控環把 503 記成失敗）另有 {@code BridgeHttpAdapterTest}、{@code BridgeHealthMonitorTest} 釘住，
 * 這裡釘的是「接起來之後」的行為。
 */
class DeepProbeApiIT extends AbstractExecutionIT {

    /** 探測一次，回頂列的連線燈（{@code bridgeConnected}）。 */
    private boolean lightAfterProbe() {
        health.probeNow();
        return api.get(viewer(), "/api/v1/notifications/summary").<Boolean>read("$.data.bridgeConnected");
    }

    @Test
    void aDegradedBridgeTurnsTheLightOffAndAnInvalidSddDoesNot() {
        assertThat(lightAfterProbe()).as("全部通過").isTrue();

        MINI.deepHealthMode = DeepHealthMode.DEGRADED;
        assertThat(lightAfterProbe()).as("前四項之一失敗＝503 degraded＝不可用").isFalse();

        MINI.deepHealthMode = DeepHealthMode.SDD_NOT_OK;
        assertThat(lightAfterProbe()).as("200 而 checks.sdd.ok=false：只是資訊").isTrue();
        assertThat(MINI.requests()).filteredOn("GET /health/deep"::equals).hasSize(3);
        assertThat(MINI.requests()).as("預設路徑不是淺層探針").doesNotContain("GET /health");
    }

    @Test
    void theShallowPathMakesADegradedBridgeLookAliveAgain() {
        MINI.deepHealthMode = DeepHealthMode.DEGRADED;
        assertThat(lightAfterProbe()).isFalse();

        setting("autoclaude", "healthCheckPath", "/health");

        assertThat(lightAfterProbe()).as("同一個 Bridge，只改了探測路徑：行程活著就算可用").isTrue();
        assertThat(MINI.requests()).filteredOn("GET /health"::equals).hasSize(1);
    }

    @Test
    void failedDeepProbesLowerTheAgentAvailabilityKpi() {
        String project = createProject("deep-probe-kpi");
        Instant from = Instant.now();
        health.probeNow();
        health.probeNow();
        MINI.deepHealthMode = DeepHealthMode.DEGRADED;
        health.probeNow();
        health.probeNow();

        Resp metrics = api.get(viewer(), "/api/v1/monitor/projects/" + project + "/metrics?from=" + from + "&to="
                + Instant.now().plusSeconds(5));

        assertThat(metrics.status()).isEqualTo(200);
        assertThat(metrics.<Number>read("$.data.agentAvailability.value")).as("四筆探測兩筆是 503").isEqualTo(50.0);
    }
}
