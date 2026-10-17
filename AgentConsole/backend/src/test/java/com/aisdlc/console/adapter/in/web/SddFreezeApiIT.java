package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 核准凍結 {@code POST /api/v1/projects/{id}/sdd/freeze}（契約 §1.10.2；API-SGN-06；D-115-03、D-115-14），對<b>真的 HTTP</b> 迷你 Bridge 驗。
 * 為什麼重要：這是 Console 對 FSM 唯一的寫入動詞（人工閘）——approver 必須是登入者而不是 client 說的人；衝突必須在<b>任何</b> Bridge 寫入之前
 * 發現（不然 FSM 已被寫入才發現兩個專案認領同一個 FSM 專案）；Bridge 的每一種拒絕都要對映成契約指定的狀態碼與 reason，前端靠它們顯示對的話；
 * 權杖只出現在寫入呼叫上、絕不外洩到任何回應。
 */
class SddFreezeApiIT extends AbstractExecutionIT {

    private static final String PROJECTS = "/api/v1/projects";
    private static final String ROOT = "/work/e2e-bravo";
    private static final String DOC = "docs/03_testing/contracts/TCS-Alpha-20261017.md";
    private static final String REASON = "規格已由 SDD session 走完 SCG-0～3，核准凍結";

    // ── 夾具 ─────────────────────────────────────────────────────────────────

    /** 迷你 Bridge 預設夾具的 {@code e2e-bravo} 停在 HUMAN_PENDING；Console 專案同名同根，有效 FSM 專案＝專案名。 */
    private String bravo() {
        return createProject(Map.of("name", "e2e-bravo", "executionPath", ROOT, "passCriteria", "- 通過"));
    }

    private static Map<String, Object> body(String reason, String... docs) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("reason", reason);
        if (docs.length > 0) {
            body.put("docs", List.of(docs));
        }
        return body;
    }

    private Resp freeze(String token, String projectId, Object body) {
        return api.post(token, PROJECTS + "/" + projectId + "/sdd/freeze", body);
    }

    private Resp freeze(String projectId, Object body) {
        return freeze(operator(), projectId, body);
    }

    private Map<String, Object> binding(String projectId) {
        return jdbc.queryForMap("select sdd_project, sdd_spec_dir, sdd_spec_file from console.projects where id = ?",
                UUID.fromString(projectId));
    }

    private void bind(String projectId, String sddProject, String specDir, String specFile) {
        jdbc.update("update console.projects set sdd_project = ?, sdd_spec_dir = ?, sdd_spec_file = ? where id = ?",
                sddProject, specDir, specFile, UUID.fromString(projectId));
    }

    private long freezeRequests() {
        return MINI.countRequests("POST /sdd/fsm");
    }

    // ── 成功路徑 ──────────────────────────────────────────────────────────────

    @Test
    void freezeSendsRootDocsTheJwtSubjectAndTheTokenAndReturnsTheFrozenState() {
        String id = bravo();
        Map<String, Object> request = body(REASON, DOC);
        request.put("stage", "Stage-1");

        Resp resp = freeze(id, request);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.currentState")).isEqualTo("SPEC_FROZEN");
        assertThat(resp.<String>read("$.data.project")).isEqualTo("e2e-bravo");
        assertThat(resp.<String>read("$.data.fsmProject")).isEqualTo("e2e-bravo");
        assertThat(resp.<String>read("$.data.phase.name")).isEqualTo("FROZEN");
        List<Map<String, Object>> stages = resp.read("$.data.frozenStages");
        assertThat(stages).hasSize(2);
        Map<String, Object> last = stages.get(stages.size() - 1);
        assertThat(last).containsEntry("stage", "Stage-1").containsEntry("approved_by", "operator");
        assertThat(last).as("巢狀鍵保留 snake_case，原樣帶出").containsKey("spec_doc_digests").containsKey("frozen_at");

        assertThat(MINI.sdd.freezes).singleElement().satisfies(sent -> {
            assertThat(sent.project()).as("送的是 Bridge 回的標準鍵").isEqualTo("e2e-bravo");
            assertThat(sent.token()).isEqualTo(MiniBridge.SDD_TOKEN);
            assertThat(sent.body()).containsEntry("root", ROOT).containsEntry("docs", List.of(DOC))
                    .containsEntry("approver", "operator").containsEntry("reason", REASON)
                    .containsEntry("stage", "Stage-1");
            assertThat(sent.body()).as("沒帶 expectedDigests 就不送這個鍵").doesNotContainKey("expected_digests");
        });
        assertThat(resp.body()).as("權杖絕不外洩到回應").doesNotContain(MiniBridge.SDD_TOKEN);
    }

    @Test
    void theTokenIsOnlyOnTheFreezeCallAndTheReadOnlyLookupHasNone() {
        String id = bravo();

        assertThat(freeze(id, body(REASON, DOC)).status()).isEqualTo(200);

        assertThat(MINI.authed()).extracting(MiniBridge.Authed::request, MiniBridge.Authed::token).containsExactly(
                org.assertj.core.groups.Tuple.tuple("GET /sdd/fsm/e2e-bravo", null),
                org.assertj.core.groups.Tuple.tuple("POST /sdd/fsm/e2e-bravo:freeze", MiniBridge.SDD_TOKEN));
        assertThat(MINI.sdd.rootsSeen).extracting(MiniBridge.Sdd.RootSeen::root).containsExactly(ROOT);
    }

    @Test
    void freezeWritesBackTheCanonicalKeyBeforeTheBridgeWrite() {
        String id = bravo();
        assertThat(binding(id).get("sdd_project")).isNull();

        assertThat(freeze(id, body(REASON, DOC)).status()).isEqualTo(200);

        assertThat(binding(id).get("sdd_project")).as("第一次使用時固定專案鍵").isEqualTo("e2e-bravo");
        assertThat(api.get(viewer(), PROJECTS + "/" + id).<String>read("$.data.sddProject")).isEqualTo("e2e-bravo");
    }

    @Test
    void theFrozenStateIsWhatTheEnginesEndpointReportsNext() {
        String id = bravo();
        assertThat(freeze(id, body(REASON, DOC)).status()).isEqualTo(200);

        Resp engines = api.get(viewer(), "/api/v1/engines/sdd?projectId=" + id);

        assertThat(engines.<String>read("$.data.fsm.currentState")).isEqualTo("SPEC_FROZEN");
        assertThat(engines.<String>read("$.data.fsm.phase.name")).isEqualTo("FROZEN");
        assertThat(engines.<List<String>>read("$.data.projects[*].currentState")).contains("SPEC_FROZEN");
    }

    @Test
    void docsDefaultToTheBoundSpecFileRelativeToTheProjectRoot() {
        String id = bravo();
        bind(id, null, ROOT + "/docs", ROOT + "/docs/TCS-Bound.md");

        Resp resp = freeze(id, Map.of("reason", REASON));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(MINI.sdd.freezes.get(0).body()).containsEntry("docs", List.of("docs/TCS-Bound.md"));
    }

    @Test
    void anExpectedDigestThatMatchesPassesAndIsForwardedUnderTheNormalizedKey() {
        String id = bravo();
        Map<String, Object> request = body(REASON, DOC);
        request.put("expectedDigests", Map.of("./" + DOC, MiniBridge.digestOf(DOC)));

        Resp resp = freeze(id, request);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(MINI.sdd.freezes.get(0).body()).containsEntry("expected_digests", Map.of(DOC, MiniBridge.digestOf(DOC)));
    }

    @Test
    void theApproverIsAlwaysTheJwtSubjectEvenWhenTheBodyClaimsAnotherPerson() {
        String id = bravo();
        Map<String, Object> request = body(REASON, DOC);
        request.put("approver", "mallory");

        assertThat(freeze(admin(), id, request).status()).isEqualTo(200);

        assertThat(MINI.sdd.freezes.get(0).body()).containsEntry("approver", "admin");
    }

    @Test
    void aRawNameIsLookedUpAsIsAndFrozenUnderTheCanonicalKey() {
        MINI.sdd.addProject("a:b", "HUMAN_PENDING", 1, "sid-colon", "2026-10-17T00:00:00+00:00",
                new MiniBridge.Sdd.SddRetry(0, null), Map.of("count", 1, "items", List.of(Map.of("entered_at", "x"))));
        String id = createProject(Map.of("name", "a:b", "executionPath", "/work/colon", "passCriteria", "- 通過"));

        Resp resp = freeze(id, body(REASON, DOC));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(MINI.requests()).contains("GET /sdd/fsm/a:b", "POST /sdd/fsm/a_b:freeze");
        assertThat(binding(id).get("sdd_project")).as("寫回的是標準鍵，不是原名").isEqualTo("a_b");
    }

    @Test
    void aBindingTheUserTypedIsKeptAndNeverOverwrittenByTheCanonicalKey() {
        MINI.sdd.addProject("a:b", "HUMAN_PENDING", 1, "sid-colon", "2026-10-17T00:00:00+00:00",
                new MiniBridge.Sdd.SddRetry(0, null), Map.of("count", 1, "items", List.of(Map.of("entered_at", "x"))));
        String id = createProject(Map.of("name", "Whatever", "executionPath", "/work/colon", "passCriteria", "- 通過"));
        bind(id, "a:b", null, null);

        assertThat(freeze(id, body(REASON, DOC)).status()).isEqualTo(200);

        assertThat(MINI.requests()).contains("GET /sdd/fsm/a:b", "POST /sdd/fsm/a_b:freeze");
        assertThat(binding(id).get("sdd_project")).isEqualTo("a:b");
    }

    // ── 驗證順序：404 → 400 → 503 → 唯讀 → 唯一性 → 寫入 ──────────────────────────────────

    @Test
    void anUnknownOrDeletedProjectIs404EvenWithAnInvalidBody() {
        String unknown = UUID.randomUUID().toString();
        Resp missing = freeze(unknown, Map.of("reason", ""));
        assertThat(missing.status()).as("404 先於 400").isEqualTo(404);
        assertThat(missing.<String>read("$.message")).isEqualTo("專案不存在或已刪除：" + unknown);
        assertThat(missing.has("$.reason")).isFalse();

        String gone = createProject("gone");
        assertThat(api.delete(operator(), PROJECTS + "/" + gone).status()).isEqualTo(204);
        assertThat(freeze(gone, body(REASON, DOC)).status()).isEqualTo(404);
        assertThat(MINI.requests()).isEmpty();
    }

    @Test
    void everyInvalidFieldIs400NamingTheFieldAndNeverReachesTheBridge() {
        String id = bravo();
        Map<String, Map<String, Object>> cases = new LinkedHashMap<>();
        cases.put("reason", Map.of("reason", "   ", "docs", List.of(DOC)));
        cases.put("reason ", Map.of("reason", "x".repeat(501), "docs", List.of(DOC)));
        cases.put("reason  ", Map.of("reason", "第一行\n第二行", "docs", List.of(DOC)));
        cases.put("stage", Map.of("reason", REASON, "stage", "bad stage!", "docs", List.of(DOC)));
        cases.put("docs", Map.of("reason", REASON, "docs", List.of()));
        cases.put("docs ", Map.of("reason", REASON, "docs", java.util.Collections.nCopies(21, DOC)));
        cases.put("docs[0]", Map.of("reason", REASON, "docs", List.of("/etc/passwd")));
        cases.put("docs[0] ", Map.of("reason", REASON, "docs", List.of("C:\\Windows\\x.md")));
        cases.put("docs[0]  ", Map.of("reason", REASON, "docs", List.of("../outside/TCS-X.md")));
        cases.put("docs[0]   ", Map.of("reason", REASON, "docs", List.of("a/../../b.md")));
        cases.put("docs[0]    ", Map.of("reason", REASON, "docs", List.of("  ")));
        cases.put("docs    ", Map.of("reason", REASON));
        cases.put("expectedDigests", Map.of("reason", REASON, "docs", List.of(DOC),
                "expectedDigests", Map.of("docs/other.md", "sha256:" + "a".repeat(64))));
        cases.put("expectedDigests ", Map.of("reason", REASON, "docs", List.of(DOC),
                "expectedDigests", Map.of(DOC, "sha256:NOT-HEX")));
        for (Map.Entry<String, Map<String, Object>> row : cases.entrySet()) {
            Resp resp = freeze(id, row.getValue());

            assertThat(resp.status()).as(row.getKey()).isEqualTo(400);
            assertThat(resp.errorFields().get(0)).as(row.getKey()).isEqualTo(row.getKey().strip());
        }
        assertThat(MINI.requests()).as("驗證在任何 Bridge 呼叫之前").isEmpty();
        assertThat(binding(id).get("sdd_project")).isNull();
    }

    @Test
    void aBoundSpecFileMustBeInDocsAndAnOutsideSpecFileCannotBeDefaulted() {
        String id = bravo();
        bind(id, null, ROOT + "/docs", ROOT + "/docs/TCS-Bound.md");

        Resp notIncluded = freeze(id, body(REASON, DOC));
        assertThat(notIncluded.status()).isEqualTo(400);
        assertThat(notIncluded.errorFields()).containsExactly("docs");

        bind(id, null, "/elsewhere/spec", "/elsewhere/spec/TCS-Out.md");
        Resp outside = freeze(id, Map.of("reason", REASON));
        assertThat(outside.status()).isEqualTo(400);
        assertThat(outside.errorFields()).containsExactly("docs");
        assertThat(MINI.requests()).isEmpty();
    }

    @Test
    void aMissingRequestBodyIs400() {
        String id = bravo();

        Resp resp = api.raw(operator(), org.springframework.http.HttpMethod.POST, PROJECTS + "/" + id + "/sdd/freeze", "");

        assertThat(resp.status()).isEqualTo(400);
        assertThat(MINI.requests()).isEmpty();
    }

    // ── Bridge 失敗對映（契約 §1.10.2）──────────────────────────────────────────────────

    @Test
    void aStateOtherThanHumanPendingIs409WithBothStatesAndAPersistedBinding() {
        String id = createProject(Map.of("name", "e2e-alpha", "executionPath", "/work/e2e-alpha", "passCriteria", "- 通過"));

        Resp resp = freeze(id, body(REASON, DOC));

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("sdd_fsm_state_conflict");
        assertThat(resp.<String>read("$.details.currentState")).isEqualTo("IMPLEMENTATION");
        assertThat(resp.<String>read("$.details.expectedState")).isEqualTo("HUMAN_PENDING");
        assertThat(binding(id).get("sdd_project")).as("第 6 項之後失敗不回滾第 5 項的寫回").isEqualTo("e2e-alpha");
    }

    @Test
    void aSecondFreezeIsRefusedBecauseTheFirstAlreadyFroze() {
        String id = bravo();
        assertThat(freeze(id, body(REASON, DOC)).status()).isEqualTo(200);

        Resp second = freeze(id, body(REASON, DOC));

        assertThat(second.status()).as("非冪等").isEqualTo(409);
        assertThat(second.<String>read("$.reason")).isEqualTo("sdd_fsm_state_conflict");
        assertThat(second.<String>read("$.details.currentState")).isEqualTo("SPEC_FROZEN");
    }

    @Test
    void aProjectWithoutAStateFileIs409SddFsmNotFoundAndNothingIsWritten() {
        String id = createProject(Map.of("name", "ghost", "executionPath", "/work/ghost", "passCriteria", "- 通過"));

        Resp resp = freeze(id, body(REASON, DOC));

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("sdd_fsm_not_found");
        assertThat(resp.<String>read("$.details.sddProject")).as("送出的有效 FSM 專案名").isEqualTo("ghost");
        assertThat(freezeRequests()).isZero();
        assertThat(binding(id).get("sdd_project")).as("填錯的名字不留下綁定").isNull();
    }

    @Test
    void anExpectedDigestThatDiffersIs409WithBothDigests() {
        String id = bravo();
        Map<String, Object> request = body(REASON, DOC);
        String stale = "sha256:" + "0".repeat(64);
        request.put("expectedDigests", Map.of(DOC, stale));

        Resp resp = freeze(id, request);

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("sdd_spec_digest_changed");
        assertThat(resp.<String>read("$.details.pair")).isEqualTo("expected_vs_file");
        assertThat(resp.<String>read("$.details.doc")).isEqualTo(DOC);
        assertThat(resp.<String>read("$.details.expectedDigest")).isEqualTo(stale);
        assertThat(resp.<String>read("$.details.currentDigest")).isEqualTo(MiniBridge.digestOf(DOC));
        assertThat(MINI.sdd.states.get("e2e-bravo")).containsEntry("current_state", "HUMAN_PENDING");
    }

    @Test
    void bridgeSanitizationRefusalsAre422EngineRefusalWithTheViolationsVerbatim() {
        String id = bravo();
        MINI.sdd.missingDocs.add(DOC);

        Resp missing = freeze(id, body(REASON, DOC));
        assertThat(missing.status()).isEqualTo(422);
        assertThat(missing.<String>read("$.reason")).isEqualTo("引擎拒絕此請求");
        assertThat(missing.<String>read("$.details.bridgeReason")).isEqualTo("sanitization_failed");
        assertThat(missing.<String>read("$.details.violations[0].field")).isEqualTo("docs[0]");
        assertThat(missing.<String>read("$.details.violations[0].rule")).isEqualTo("not_found");

        MINI.sdd.missingDocs.clear();
        Resp noTcs = freeze(id, body(REASON, "docs/README.md"));
        assertThat(noTcs.status()).isEqualTo(422);
        assertThat(noTcs.<String>read("$.details.violations[0].rule")).isEqualTo("missing_tcs");
    }

    @Test
    void aRootTheBridgeRejectsOnTheLookupIs422AndNoFreezeIsAttempted() {
        MINI.sdd.rejectedRoots.add(ROOT);
        String id = bravo();

        Resp resp = freeze(id, body(REASON, DOC));

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo("引擎拒絕此請求");
        assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo("sanitization_failed");
        assertThat(freezeRequests()).isZero();
        assertThat(binding(id).get("sdd_project")).isNull();
    }

    @Test
    void anUnreadableStateFileIs422EngineRefusal() {
        MINI.sdd.unreadable.add("e2e-bravo");
        MINI.sdd.states.remove("e2e-bravo");
        String id = bravo();

        Resp resp = freeze(id, body(REASON, DOC));

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo("fsm_state_unreadable");
    }

    @Test
    void aBridgeWithoutTheTokenIs503AndAMismatchIs502WithTheStatusOnly() {
        String id = bravo();
        MINI.sdd.writeToken = null;
        Resp disabled = freeze(id, body(REASON, DOC));
        assertThat(disabled.status()).isEqualTo(503);
        assertThat(disabled.<String>read("$.reason")).isEqualTo("sdd_write_disabled");

        MINI.sdd.writeToken = "mock-a-different-token-value-0123456789abcdef";
        Resp forbidden = freeze(id, body(REASON, DOC));
        assertThat(forbidden.status()).isEqualTo(502);
        assertThat(forbidden.<String>read("$.reason")).isEqualTo("引擎橋接服務錯誤");
        assertThat(forbidden.<Integer>read("$.details.bridgeStatus")).isEqualTo(403);
        assertThat(forbidden.<String>read("$.details.bridgeReason")).isEqualTo("sdd_write_forbidden");
        assertThat(forbidden.body()).as("兩端的權杖值都不外洩").doesNotContain(MiniBridge.SDD_TOKEN)
                .doesNotContain("a-different-token");
        assertThat(binding(id).get("sdd_project")).as("寫回已發生、不回滾").isEqualTo("e2e-bravo");
    }

    @Test
    void aBridgeServerErrorIs502AndAnUnreachableBridgeIs502WithoutAnyWrite() {
        String id = bravo();
        MINI.failNext("freeze", 502, Map.of("code", 502, "reason", "sdd_cli_failed", "detail", "boom"));

        Resp failed = freeze(id, body(REASON, DOC));
        assertThat(failed.status()).isEqualTo(502);
        assertThat(failed.<String>read("$.reason")).isEqualTo("引擎橋接服務錯誤");
        assertThat(failed.<Integer>read("$.details.bridgeStatus")).isEqualTo(502);
        assertThat(failed.<String>read("$.details.bridgeReason")).isEqualTo("sdd_cli_failed");

        setting("sdd", "engineUrl", "http://127.0.0.1:1");
        Resp unreachable = freeze(id, body(REASON, DOC));
        assertThat(unreachable.status()).isEqualTo(502);
    }

    // ── 綁定唯一性：先檢查、後寫入 ─────────────────────────────────────────────────────────

    @Test
    void aKeyHeldByAnotherProjectUnderTheSameRootIs409BeforeAnyBridgeWrite() {
        String holder = createProject(Map.of("name", "holder", "executionPath", ROOT, "passCriteria", "- 通過"));
        bind(holder, "e2e-bravo", null, null);
        String claimant = bravo();

        Resp resp = freeze(claimant, body(REASON, DOC));

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("sdd_binding_conflict");
        assertThat(resp.<String>read("$.details.cause")).isEqualTo("already_bound_elsewhere");
        assertThat(resp.<String>read("$.details.sddProject")).isEqualTo("e2e-bravo");
        assertThat(resp.<String>read("$.details.holderProjectId")).isEqualTo(holder);
        assertThat(freezeRequests()).as("不呼叫 Bridge 的寫入端點").isZero();
        assertThat(MINI.sdd.states.get("e2e-bravo")).containsEntry("current_state", "HUMAN_PENDING");
    }

    // ── 權限與稽核 ───────────────────────────────────────────────────────────────────

    @Test
    void viewersAreForbiddenAnonymousIs401AndNothingReachesTheBridge() {
        String id = bravo();

        Resp viewer = freeze(viewer(), id, body(REASON, DOC));
        assertThat(viewer.status()).isEqualTo(403);
        assertThat(viewer.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
        assertThat(freeze(null, id, body(REASON, DOC)).status()).isEqualTo(401);
        assertThat(MINI.requests()).isEmpty();
    }

    @Test
    void everyFreezeRequestIsAuditedWithTheSubjectAndTheOutcome() {
        String id = bravo();
        jdbc.execute("TRUNCATE console.audit_log");

        assertThat(freeze(id, body(REASON, DOC)).status()).isEqualTo(200);
        assertThat(freeze(id, body(REASON, DOC)).status()).isEqualTo(409);

        List<Map<String, Object>> rows = jdbc.queryForList("select subject, role, method, path, entity_type, entity_id, "
                + "http_status from console.audit_log order by occurred_at");
        assertThat(rows).hasSize(2);
        assertThat(rows.get(0)).containsEntry("subject", "operator").containsEntry("role", "OPERATOR")
                .containsEntry("method", "POST").containsEntry("path", PROJECTS + "/" + id + "/sdd/freeze")
                .containsEntry("entity_type", "project").containsEntry("entity_id", id).containsEntry("http_status", 200);
        assertThat(rows.get(1)).containsEntry("http_status", 409);
    }
}
