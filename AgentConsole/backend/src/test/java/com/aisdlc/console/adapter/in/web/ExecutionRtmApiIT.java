package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 執行追溯覆蓋 {@code GET /api/v1/executions/{runId}/rtm}（契約 §1.10.3；API-EXE-16；G-05），對真的 HTTP 迷你 Bridge 驗。為什麼重要：
 * 它是 Console 對 A 軌逆向回寫（{@code RtmWritebackPlugin}）的唯一消費點，而且是<b>諮詢視圖</b>——{@code advisory} 恆為 true、有無法歸屬 AC 的 AT 時
 * {@code fullyCovered} 必為 false、AT 與 AC 的分母口徑不同不得被「修正」；「批次不存在」與「批次存在但沒有報告」要能被機器區分
 * （前者無 reason、後者 {@code rtm_not_found}），前端靠它決定顯示「沒有報告」還是錯誤。
 */
class ExecutionRtmApiIT extends AbstractExecutionIT {

    private static final String EXECUTIONS = "/api/v1/executions";

    private String finishedRun() {
        Fixture fixture = prjA("rtm-" + UUID.randomUUID().toString().substring(0, 8), 4);
        String runId = startRun(fixture.projectId());
        assertThat(awaitProjected(runId, "COMPLETED")).as("批次走完（自治等級 4 沒有審核閘）").isTrue();
        return runId;
    }

    private Resp rtm(String token, String runId) {
        return api.get(token, EXECUTIONS + "/" + runId + "/rtm");
    }

    private Resp rtm(String runId) {
        return rtm(viewer(), runId);
    }

    // ── 成功：欄位逐值、advisory 恆 true ─────────────────────────────────────────

    @Test
    void theReportIsProjectedFieldByFieldWithCamelCaseKeysAndAdvisoryAlwaysTrue() {
        String runId = finishedRun();
        MINI.sdd.rtmReports.put(UUID.fromString(runId), MiniBridge.rtmReport("greenfield", 4, 4, 0, 100.0, 2, 2, 100.0,
                List.of(), List.of(), List.of(), true));

        Resp resp = rtm(runId);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.scenario")).isEqualTo("greenfield");
        assertThat(resp.<String>read("$.data.specDigest")).startsWith("sha256:").hasSize("sha256:".length() + 64);
        assertThat(resp.<Integer>read("$.data.at.passed")).isEqualTo(4);
        assertThat(resp.<Integer>read("$.data.at.total")).isEqualTo(4);
        assertThat(resp.<Integer>read("$.data.at.unmapped")).isZero();
        assertThat(resp.<Double>read("$.data.at.pct")).isEqualTo(100.0);
        assertThat(resp.<Integer>read("$.data.ac.covered")).isEqualTo(2);
        assertThat(resp.<Integer>read("$.data.ac.total")).isEqualTo(2);
        assertThat(resp.<Double>read("$.data.ac.pct")).isEqualTo(100.0);
        assertThat(resp.<List<Object>>read("$.data.failedAtIds")).isEmpty();
        assertThat(resp.<List<Object>>read("$.data.weakRegexAtIds")).isEmpty();
        assertThat(resp.<List<Object>>read("$.data.unmappedAtIds")).isEmpty();
        assertThat(resp.<Boolean>read("$.data.fullyCovered")).isTrue();
        assertThat(resp.<Boolean>read("$.data.advisory")).isTrue();
        assertThat(resp.body()).as("鍵一律 camelCase").doesNotContain("failed_at_ids").doesNotContain("spec_digest")
                .doesNotContain("fully_covered");
        assertThat(MINI.requests()).contains("GET /autoclaude/runs/" + runId + "/rtm");
        assertThat(MINI.authed().stream().filter(a -> a.request().endsWith("/rtm")).toList())
                .as("唯讀、不需權杖").extracting(MiniBridge.Authed::token).containsOnlyNulls();
    }

    @Test
    void unmappedAtsStayInTheAtTotalsButNeverInAnAcBucketAndFullyCoveredIsFalse() {
        String runId = finishedRun();
        MINI.sdd.rtmReports.put(UUID.fromString(runId), MiniBridge.rtmReport("greenfield", 5, 6, 1, 83.3, 2, 2, 100.0,
                List.of("AT-X-1"), List.of("AT-001-1-1"), List.of("AT-X-1"), false));

        Resp resp = rtm(runId);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.at.total")).as("AT 級指標含無法歸屬者（口徑與 AC 不同，不得互推）").isEqualTo(6);
        assertThat(resp.<Integer>read("$.data.at.unmapped")).isEqualTo(1);
        assertThat(resp.<Integer>read("$.data.ac.total")).isEqualTo(2);
        assertThat(resp.<List<String>>read("$.data.failedAtIds")).containsExactly("AT-X-1");
        assertThat(resp.<List<String>>read("$.data.weakRegexAtIds")).containsExactly("AT-001-1-1");
        assertThat(resp.<List<String>>read("$.data.unmappedAtIds")).containsExactly("AT-X-1");
        assertThat(resp.<Boolean>read("$.data.fullyCovered")).isFalse();
        assertThat(resp.<Boolean>read("$.data.advisory")).isTrue();
    }

    @Test
    void anOldReportWithoutTheNewKeysGetsTheDefaultsInsteadOfFailing() {
        String runId = finishedRun();
        Map<String, Object> old = MiniBridge.rtmReport("greenfield", 3, 3, 0, 100.0, 1, 1, 100.0, List.of(), List.of(),
                List.of(), true);
        ((Map<String, Object>) old.get("at")).remove("unmapped");
        old.remove("unmapped_at_ids");
        old.remove("weak_regex_at_ids");
        old.remove("scenario");
        MINI.sdd.rtmReports.put(UUID.fromString(runId), old);

        Resp resp = rtm(runId);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.at.unmapped")).as("舊報告缺欄為 0").isZero();
        assertThat(resp.<List<Object>>read("$.data.unmappedAtIds")).as("舊報告缺欄為 []").isEmpty();
        assertThat(resp.<List<Object>>read("$.data.weakRegexAtIds")).isEmpty();
        assertThat(resp.<String>read("$.data.scenario")).as("缺則空字串").isEmpty();
    }

    // ── 404：批次不存在（無 reason）與批次存在但沒有報告（rtm_not_found）────────────────────

    @Test
    void anUnknownRunIs404WithoutAReasonAndNeverReachesTheBridge() {
        String unknown = UUID.randomUUID().toString();

        Resp resp = rtm(unknown);

        assertThat(resp.status()).isEqualTo(404);
        assertThat(resp.<String>read("$.message")).isEqualTo("執行批次不存在或已刪除：" + unknown);
        assertThat(resp.has("$.reason")).as("一般 404 沒有 reason").isFalse();
        assertThat(MINI.requests()).isEmpty();
    }

    @Test
    void aRunWithoutAReportIs404RtmNotFoundWithTheRunId() {
        String runId = finishedRun();

        Resp resp = rtm(runId);

        assertThat(resp.status()).isEqualTo(404);
        assertThat(resp.<String>read("$.reason")).isEqualTo("rtm_not_found");
        assertThat(resp.<String>read("$.details.runId")).isEqualTo(runId);
    }

    @Test
    void aBridgeThatNoLongerKnowsTheRunIsAlsoRtmNotFound() {
        String runId = finishedRun();
        MINI.failNext("rtm", 404, Map.of("code", 404, "reason", "run_not_found", "run_id", runId));

        Resp resp = rtm(runId);

        assertThat(resp.status()).as("工作區已清除：對前端同樣是「沒有追溯報告」").isEqualTo(404);
        assertThat(resp.<String>read("$.reason")).isEqualTo("rtm_not_found");
        assertThat(resp.<String>read("$.details.runId")).isEqualTo(runId);
    }

    @Test
    void aNonUuidRunIdIs400OnRunId() {
        Resp resp = rtm("not-a-uuid");

        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.errorFields()).containsExactly("runId");
        assertThat(resp.<String>read("$.message")).isEqualTo("參數 runId 的值格式不正確");
    }

    // ── 422 與上游失敗 ─────────────────────────────────────────────────────────────

    @Test
    void anUnreadableReportIs422EngineRefusalWithTheBridgeReason() {
        String runId = finishedRun();
        MINI.sdd.rtmUnreadable.add(UUID.fromString(runId));

        Resp resp = rtm(runId);

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo("引擎拒絕此請求");
        assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo("rtm_unreadable");
        assertThat(resp.<List<Object>>read("$.details.violations")).isEmpty();
    }

    @Test
    void aServerErrorAndAnUnreachableBridgeAreBothBadGatewayNoRetry() {
        String runId = finishedRun();
        MINI.failNext("rtm", 500, Map.of("code", 500, "reason", "boom"));

        Resp failed = rtm(runId);
        assertThat(failed.status()).isEqualTo(502);
        assertThat(failed.<Integer>read("$.details.bridgeStatus")).isEqualTo(500);
        assertThat(MINI.countRequests("GET /autoclaude/runs/" + runId + "/rtm")).as("不重試").isEqualTo(1);

        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        setting("autoclaude", "engineUrl", "http://127.0.0.1:1");
        assertThat(rtm(runId).status()).isEqualTo(502);
    }

    // ── 權限 ─────────────────────────────────────────────────────────────────────

    @Test
    void everyRoleMayReadAndAnonymousIs401() {
        String runId = finishedRun();
        MINI.sdd.rtmReports.put(UUID.fromString(runId), MiniBridge.rtmReport("greenfield", 1, 1, 0, 100.0, 1, 1, 100.0,
                List.of(), List.of(), List.of(), true));

        assertThat(rtm(null, runId).status()).isEqualTo(401);
        for (String token : List.of(viewer(), operator(), admin())) {
            assertThat(rtm(token, runId).status()).isEqualTo(200);
        }
        assertThat(api.post(operator(), EXECUTIONS + "/" + runId + "/rtm", Map.of()).status())
                .as("只讀端點：沒有寫入方法").isEqualTo(405);
    }
}
