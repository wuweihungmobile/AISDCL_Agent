package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 編輯專案的 FSM 專案 {@code PUT /api/v1/projects/{id}/sdd-binding}（契約 §1.10.7；API-PRJ-08；ADR-XPLAT-016 §7.2）。為什麼重要：
 * 它是「沒有解除綁定端點、編輯它即改綁」的唯一入口——必須先檢查唯一性（兩個專案不能認領同一個 FSM 專案）、
 * 相同值再送不得製造稽核噪音、填錯的名字不能呼叫 Bridge 或留下任何寫入（只會讓 {@code GET /engines/sdd} 回 fsm_not_found），
 * 而且「鍵缺席」必須是 400——否則一個空本文 {@code {}} 會悄悄清掉綁定。
 */
class SddBindingApiIT extends AbstractExecutionIT {

    private static final String PROJECTS = "/api/v1/projects";

    private String project(String name, String path) {
        return createProject(Map.of("name", name, "executionPath", path, "passCriteria", "- 通過"));
    }

    private Resp put(String token, String projectId, Object body) {
        return api.put(token, PROJECTS + "/" + projectId + "/sdd-binding", body);
    }

    private Resp put(String projectId, Object body) {
        return put(operator(), projectId, body);
    }

    private static Map<String, Object> binding(String value) {
        Map<String, Object> body = new HashMap<>();
        body.put("sddProject", value);
        return body;
    }

    private String stored(String projectId) {
        return jdbc.queryForObject("select sdd_project from console.projects where id = ?", String.class,
                UUID.fromString(projectId));
    }

    private int auditRows() {
        return jdbc.queryForObject("select count(*) from console.audit_log", Integer.class);
    }

    // ── 成功與冪等 ────────────────────────────────────────────────────────────

    @Test
    void aValueIsStoredStrippedAndReturnedInTheProjectDetail() {
        String id = project("anchor", "/work/anchor");
        createGoal(id, "一個目標");

        Resp resp = put(id, binding("  e2e17-alpha  "));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.sddProject")).as("存入去前後空白後的值").isEqualTo("e2e17-alpha");
        assertThat(resp.<String>read("$.data.id")).isEqualTo(id);
        assertThat(resp.<List<Object>>read("$.data.goals")).as("回的是專案詳情（含目標摘要）").hasSize(1);
        assertThat(resp.<Object>read("$.data.sddSpecDir")).isNull();
        assertThat(stored(id)).isEqualTo("e2e17-alpha");
        assertThat(api.get(viewer(), PROJECTS + "/" + id).<String>read("$.data.sddProject")).isEqualTo("e2e17-alpha");
    }

    @Test
    void nullClearsTheBindingBackToTheDefaultAndTheProjectNameIsUsedAgain() {
        String id = project("anchor", "/work/anchor");
        assertThat(put(id, binding("my-key")).status()).isEqualTo(200);

        Resp cleared = put(id, binding(null));

        assertThat(cleared.status()).isEqualTo(200);
        assertThat(cleared.<Object>read("$.data.sddProject")).isNull();
        assertThat(stored(id)).isNull();
    }

    @Test
    void theSameValueAgainIsIdempotentAndWritesNoAuditRow() {
        String id = project("anchor", "/work/anchor");
        jdbc.execute("TRUNCATE console.audit_log");
        assertThat(put(id, binding("my-key")).status()).isEqualTo(200);
        int afterFirst = auditRows();
        Object updatedAt = jdbc.queryForObject("select updated_at::text from console.projects where id = ?", String.class,
                UUID.fromString(id));

        Resp again = put(id, binding(" my-key "));

        assertThat(again.status()).isEqualTo(200);
        assertThat(again.<String>read("$.data.sddProject")).isEqualTo("my-key");
        assertThat(afterFirst).as("每個寫入請求一列（filter）").isEqualTo(1);
        assertThat(jdbc.queryForObject("select updated_at::text from console.projects where id = ?", String.class,
                UUID.fromString(id))).as("沒有變更就不動 updatedAt").isEqualTo(updatedAt);
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log where http_status = 200 "
                + "and entity_type = 'project'", Integer.class)).as("只有第一次標註了 project.sdd.bind 的實體").isEqualTo(1);
    }

    @Test
    void aBindingIsNotCheckedAgainstTheBridgeAndNeverCallsIt() {
        String id = project("anchor", "/work/anchor");

        assertThat(put(id, binding("a-name-that-has-no-state-file")).status()).isEqualTo(200);

        assertThat(MINI.requests()).as("不檢查狀態檔是否存在、不呼叫 Bridge").isEmpty();
        Resp engines = api.get(viewer(), "/api/v1/engines/sdd?projectId=" + id);
        assertThat(engines.<String>read("$.data.reason")).as("填錯的名字只讓引擎卡回 fsm_not_found").isEqualTo("fsm_not_found");
    }

    // ── 唯一性 ────────────────────────────────────────────────────────────────

    @Test
    void aKeyHeldByAnotherLiveProjectUnderTheSameRootIs409WithTheHolder() {
        String holder = project("holder", "/work/shared");
        assertThat(put(holder, binding("shared-key")).status()).isEqualTo(200);
        String claimant = project("claimant", "/work/shared");

        Resp resp = put(claimant, binding("shared-key"));

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("sdd_binding_conflict");
        assertThat(resp.<String>read("$.details.cause")).isEqualTo("already_bound_elsewhere");
        assertThat(resp.<String>read("$.details.sddProject")).isEqualTo("shared-key");
        assertThat(resp.<String>read("$.details.holderProjectId")).isEqualTo(holder);
        assertThat(stored(claimant)).isNull();
    }

    @Test
    void theSameKeyUnderAnotherRootOrAfterTheHolderWasDeletedIsFine() {
        String holder = project("holder", "/work/shared");
        assertThat(put(holder, binding("shared-key")).status()).isEqualTo(200);

        String otherRoot = project("other-root", "/work/elsewhere");
        assertThat(put(otherRoot, binding("shared-key")).status()).as("唯一性是 (executionPath, sddProject)").isEqualTo(200);

        assertThat(api.delete(operator(), PROJECTS + "/" + holder).status()).isEqualTo(204);
        String successor = project("successor", "/work/shared");
        assertThat(put(successor, binding("shared-key")).status()).as("軟刪除的專案不算").isEqualTo(200);
    }

    // ── 驗證與權限 ────────────────────────────────────────────────────────────

    @Test
    void blankTooLongControlCharacterMissingAndNonStringValuesAre400OnTheField() {
        String id = project("anchor", "/work/anchor");
        List<Object> bodies = List.of(binding(""), binding("   "), binding("x".repeat(101)), binding("a\nb"),
                binding("a\u0000b"), Map.of(), Map.of("other", "x"), Map.of("sddProject", 12), Map.of("sddProject", List.of("a")));
        for (Object body : bodies) {
            Resp resp = put(id, body);

            assertThat(resp.status()).as(body.toString().length() + "").isEqualTo(400);
            assertThat(resp.errorFields()).containsExactly("sddProject");
        }
        assertThat(stored(id)).as("驗證失敗不改任何東西").isNull();
    }

    @Test
    void aMissingKeyDoesNotClearAnExistingBinding() {
        String id = project("anchor", "/work/anchor");
        assertThat(put(id, binding("keep-me")).status()).isEqualTo(200);

        assertThat(put(id, Map.of()).status()).isEqualTo(400);

        assertThat(stored(id)).isEqualTo("keep-me");
    }

    @Test
    void anUnknownOrDeletedProjectIs404() {
        String unknown = UUID.randomUUID().toString();
        Resp missing = put(unknown, binding("x"));
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.<String>read("$.message")).isEqualTo("專案不存在或已刪除：" + unknown);
        assertThat(missing.has("$.reason")).isFalse();

        String gone = project("gone", "/work/gone");
        assertThat(api.delete(operator(), PROJECTS + "/" + gone).status()).isEqualTo(204);
        assertThat(put(gone, binding("x")).status()).isEqualTo(404);
    }

    @Test
    void aFormatProblemBeatsAnUnknownProjectLikeBeanValidation() {
        String unknown = UUID.randomUUID().toString();

        for (Object body : List.of(binding("x".repeat(101)), binding(""), Map.of())) {
            Resp resp = put(unknown, body);

            assertThat(resp.status()).as("契約 §1.10.7 的 400 列是 Bean Validation：本文的格式問題先於資源查找（404）")
                    .isEqualTo(400);
            assertThat(resp.errorFields()).containsExactly("sddProject");
        }
    }

    @Test
    void viewersAreForbiddenAndAnonymousIs401() {
        String id = project("anchor", "/work/anchor");

        Resp viewer = put(viewer(), id, binding("x"));
        assertThat(viewer.status()).isEqualTo(403);
        assertThat(viewer.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
        assertThat(put(null, id, binding("x")).status()).isEqualTo(401);
        assertThat(put(admin(), id, binding("by-admin")).status()).isEqualTo(200);
        assertThat(stored(id)).isEqualTo("by-admin");
    }

    @Test
    void theChangeIsAuditedAsAProjectWriteWithTheSubject() {
        String id = project("anchor", "/work/anchor");
        jdbc.execute("TRUNCATE console.audit_log");

        assertThat(put(id, binding("audited-key")).status()).isEqualTo(200);

        List<Map<String, Object>> rows = jdbc.queryForList("select subject, role, method, path, entity_type, entity_id, "
                + "http_status from console.audit_log order by occurred_at");
        assertThat(rows).singleElement().satisfies(r -> assertThat(r).containsEntry("subject", "operator")
                .containsEntry("role", "OPERATOR").containsEntry("method", "PUT")
                .containsEntry("path", PROJECTS + "/" + id + "/sdd-binding").containsEntry("entity_type", "project")
                .containsEntry("entity_id", id).containsEntry("http_status", 200));
    }
}
