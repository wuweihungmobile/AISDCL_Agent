package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * backend 沒有設定 {@code console.bridge.sdd-write-token}（契約 §1.10.2 的 503、§1.10.5 資格第 2 項、ADR-XPLAT-016 §9）：這個類別自成一個
 * Spring context（以空字串覆蓋基底類別的權杖），其餘 SDD 整合測試都在「已設定」的 context 裡。為什麼重要：沒設權杖是<b>合法的部署形態</b>
 * （只用路徑 B／手動專案的人），整個 SDD 寫入面必須乾淨地停用——核准凍結明確回 503、SDD 任務的 execute 退回手動批次並出聲，
 * 而且 console-api <b>不能</b>為了「試試看」去敲 Bridge 的寫入端點（權杖缺漏只會換來 403，卻讓 Bridge 日誌多一筆誤導的拒絕）。
 */
@TestPropertySource(properties = "console.bridge.sdd-write-token=")
class SddWriteDisabledApiIT extends AbstractExecutionIT {

    private static final String PROJECTS = "/api/v1/projects";
    private static final String ROOT = "/work/e2e-bravo";
    private static final String DOC = "docs/03_testing/contracts/TCS-Alpha-20261017.md";

    private String bravo() {
        return createProject(Map.of("name", "e2e-bravo", "executionPath", ROOT, "passCriteria", "- 通過"));
    }

    private Resp freeze(String projectId, Object body) {
        return api.post(operator(), PROJECTS + "/" + projectId + "/sdd/freeze", body);
    }

    private long sddRequests() {
        return MINI.requests().stream().filter(r -> r.contains("/sdd/")).count();
    }

    @Test
    void freezeIs503BeforeAnyBridgeCallButTheEarlierChecksStillWin() {
        String id = bravo();
        Map<String, Object> valid = new LinkedHashMap<>();
        valid.put("reason", "規格已核准");
        valid.put("docs", List.of(DOC));

        assertThat(freeze(UUID.randomUUID().toString(), valid).status()).as("404 先於 503").isEqualTo(404);
        Resp invalid = freeze(id, Map.of());
        assertThat(invalid.status()).as("400 先於 503").isEqualTo(400);
        assertThat(invalid.errorFields()).contains("reason");

        Resp resp = freeze(id, valid);

        assertThat(resp.status()).isEqualTo(503);
        assertThat(resp.<String>read("$.reason")).isEqualTo("sdd_write_disabled");
        assertThat(resp.<String>read("$.message")).contains("BRIDGE_SDD_WRITE_TOKEN");
        assertThat(sddRequests()).as("連唯讀查標準鍵也沒做：根本不碰 Bridge").isZero();
        assertThat(jdbc.queryForObject("select sdd_project from console.projects where id = ?", String.class,
                UUID.fromString(id))).as("綁定沒有被寫回").isNull();
    }

    @Test
    void aSddTaskBatchFallsBackToAManualBatchWithTheTokenNotConfiguredWarning() {
        String projectId = createProject(Map.of("name", "sdd-no-token", "executionPath", "/e2e/sdd-no-token",
                "passCriteria", "- 全部通過", "autonomyLevel", 4));
        jdbc.update("update console.projects set sdd_spec_dir = ?, sdd_spec_file = ? where id = ?",
                "/e2e/sdd-no-token/docs", "/e2e/sdd-no-token/docs/TCS-A.md", UUID.fromString(projectId));
        String goal = createGoal(projectId, "規格目標");
        for (int i = 1; i <= 2; i++) {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("name", "AT-001-" + i + "-1");
            body.put("description", "請輸出 [T" + i + "_DONE]");
            body.put("passCriteria", "輸出含 [T" + i + "_DONE]");
            body.put("expectedOutputRegex", "\\[T" + i + "_DONE\\]");
            body.put("passCriteriaSpec", Map.of("source", "sdd", "specDigest", "sha256:" + "a".repeat(64), "stepId",
                    "sdd-greenfield-at-001-" + i + "-1"));
            assertThat(api.post(operator(), "/api/v1/goals/" + goal + "/tasks", body).status()).isEqualTo(201);
        }

        Resp resp = execute(projectId, Map.of());

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<List<String>>read("$.data.warnings[*].code")).containsExactly("sdd_governance_inactive");
        assertThat(resp.<String>read("$.data.warnings[0].cause")).isEqualTo("token_not_configured");
        assertThat(resp.<String>read("$.data.warnings[0].detail")).contains("BRIDGE_SDD_WRITE_TOKEN");
        Map<String, Object> request = mini(resp.id()).request;
        assertThat(request).doesNotContainKey("sdd");
        assertThat(request.get("playbook").toString()).as("step_id 維持 G<g>-T<t>").contains("G1-T1", "G1-T2")
                .doesNotContain("sdd-greenfield-at-001");
        assertThat(MINI.authed()).as("整個過程沒有任何請求帶權杖").filteredOn(a -> a.token() != null).isEmpty();
        assertThat(awaitProjected(resp.id(), "COMPLETED")).isTrue();
    }

    @Test
    void resumeSendsNoTokenHeaderWhenNoneIsConfigured() {
        Fixture f = prjA("no-token-resume", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/pause").status()).isEqualTo(200);
        mini(run).release(1);
        assertThat(awaitProjected(run, "PAUSED")).isTrue();

        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/resume").status()).isEqualTo(200);
        mini(run).release(5);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();

        assertThat(MINI.authed()).filteredOn(a -> a.request().endsWith(":resume")).extracting(MiniBridge.Authed::token)
                .containsOnlyNulls();
        assertThat(MINI.authed()).filteredOn(a -> a.token() != null).isEmpty();
    }

    @Test
    void theReadOnlyEngineQueriesNeedNoTokenAndKeepWorking() {
        Resp resp = api.get(viewer(), "/api/v1/engines/sdd");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).contains("e2e-alpha", "e2e-bravo");
    }
}
