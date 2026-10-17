package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@code GET /api/v1/engines/sdd}（API-ENG-01；契約 §1.7.1；D-16；E2E-15 的後端面），對<b>真的 HTTP</b> 迷你 Bridge 驗映射表的每一列。
 * 為什麼重要：這支端點是 Console 對 FSM 狀態的唯一消費點（NFR-OBS-01：FSM 檔 ↔ API ↔ 畫面逐值相等），而且引擎不可用也要回 200——
 * 前端靠 {@code available}／{@code reason} 畫「不可用」，若這裡把 Bridge 的錯誤轉成 502，監控頁的 SDD 卡就會變成錯誤頁。
 * 只能 E2E 的部分（磁碟上真實的 FSM 檔、畫面 DOM、乾淨 clone 與 Docker 全棧）見 {@code rtm_backfill_W7BE.md}。
 */
class EnginesApiIT extends AbstractExecutionIT {

    private static final String SDD = "/api/v1/engines/sdd";

    private Resp get(String query) {
        return api.get(viewer(), SDD + query);
    }

    private long sddRequests() {
        return MINI.requests().stream().filter(r -> r.startsWith("GET /sdd")).count();
    }

    // ── 可用：清單（E2E-15 第 1 列）、單一專案（第 2、3 列）──────────────────────────────────────

    @Test
    void withoutAProjectItListsTheProjectsInTheBridgeOrderAndHasNoFsm() {
        Resp resp = get("");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<Object>read("$.data.reason")).as("沒問題時 reason 為 null（鍵固定出現）").isNull();
        assertThat(resp.<String>read("$.data.version.latest")).isEqualTo("AISDLC_SDD_v9.99");
        assertThat(resp.<String>read("$.data.version.root")).isEqualTo("/sdd/AISDLC_SDD_v9.99");
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).containsExactly("e2e-alpha", "e2e-bravo");
        assertThat(resp.<List<String>>read("$.data.projects[*].source"))
                .containsExactly("FSM-STATE-e2e-alpha.yaml", "FSM-STATE-e2e-bravo.yaml");
        assertThat(resp.<List<String>>read("$.data.projects[*].currentState"))
                .containsExactly("IMPLEMENTATION", "HUMAN_PENDING");
        assertThat(resp.<List<String>>read("$.data.projects[*].updatedAt"))
                .containsExactly("2026-10-16T01:02:03+00:00", "2026-10-15T08:00:00+00:00");
        assertThat(resp.<Object>read("$.data.fsm")).as("未帶 project：fsm=null 且不帶 reason").isNull();
        assertThat(resp.<String>read("$.data.checkedAt")).endsWith("Z");
        assertThat(resp.body()).as("Bridge 的 errors[]（讀不動的檔名）只記日誌，不轉發")
                .doesNotContain("e2e-broken").doesNotContain("bad name");
        assertThat(MINI.requests()).containsExactly("GET /sdd/version", "GET /sdd/fsm");
    }

    @Test
    void aProjectNameReturnsItsStateWithNestedContentVerbatim() {
        Map<String, Object> expected = MINI.sdd.states.get("e2e-alpha");

        Resp resp = get("?project=e2e-alpha");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<Object>read("$.data.reason")).isNull();
        assertThat(resp.<String>read("$.data.fsm.project")).isEqualTo("e2e-alpha");
        assertThat(resp.<String>read("$.data.fsm.currentState")).isEqualTo("IMPLEMENTATION");
        assertThat(resp.<Integer>read("$.data.fsm.currentSprint")).isEqualTo(2);
        assertThat(resp.<String>read("$.data.fsm.sessionId")).isEqualTo("sid-alpha");
        assertThat(resp.<String>read("$.data.fsm.updatedAt")).as("原樣的字串，不轉型").isEqualTo("2026-10-16T01:02:03+00:00");
        assertThat(resp.<String>read("$.data.fsm.source")).isEqualTo("FSM-STATE-e2e-alpha.yaml");
        assertThat(resp.<List<Object>>read("$.data.fsm.frozenStages")).isEqualTo(expected.get("frozen_stages"));
        assertThat(resp.<List<Object>>read("$.data.fsm.decisionTrace")).as("尾 5 筆、舊→新、巢狀鍵保留 snake_case，逐值相等")
                .isEqualTo(expected.get("decision_trace")).hasSize(5);
        assertThat(resp.<Object>read("$.data.fsm.decisionTrace[0].spec_refs")).isEqualTo(List.of("SPEC-3"));
        assertThat(resp.<Object>read("$.data.fsm.decisionTrace[4].agents_consulted")).isEqualTo(List.of("sa"));
        assertThat(resp.<Integer>read("$.data.fsm.humanPending.count")).isZero();
        assertThat(resp.<List<Object>>read("$.data.fsm.humanPending.items")).isEmpty();
        assertThat(resp.<Integer>read("$.data.fsm.retryHistory.count")).isEqualTo(3);
        assertThat(resp.<Map<String, Object>>read("$.data.fsm.retryHistory.last")).as("原筆再加 gate 欄")
                .containsEntry("gate", "PR_REVIEW").containsEntry("attempt", 1)
                .containsEntry("failure_reason", "review rejected");
        assertThat(resp.<Object>read("$.data.fsm.rtmCoverage")).as("現行 FSM-STATE 沒有 RTM 覆蓋數值：恆為 null").isNull();
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).containsExactly("e2e-alpha", "e2e-bravo");
        assertThat(MINI.requests()).containsExactly("GET /sdd/version", "GET /sdd/fsm", "GET /sdd/fsm/e2e-alpha");
    }

    @Test
    void aProjectWaitingForAHumanShowsTheEnteredAtVerbatim() {
        Resp resp = get("?project=e2e-bravo");

        assertThat(resp.<String>read("$.data.fsm.currentState")).isEqualTo("HUMAN_PENDING");
        assertThat(resp.<Integer>read("$.data.fsm.humanPending.count")).isEqualTo(1);
        assertThat(resp.<String>read("$.data.fsm.humanPending.items[0].entered_at"))
                .isEqualTo("2026-10-15T08:00:00+00:00");
        assertThat(resp.<Integer>read("$.data.fsm.humanPending.items[0].reminder_hours")).isEqualTo(72);
        assertThat(resp.<Integer>read("$.data.fsm.retryHistory.count")).isZero();
        assertThat(resp.<Object>read("$.data.fsm.retryHistory.last")).isNull();
    }

    @Test
    void anEmptyFsmDirectoryIsAnAvailableEngineWithNoProjectsAndNoReason() {
        MINI.sdd.projects.clear();
        MINI.sdd.states.clear();
        MINI.sdd.errors.clear();

        Resp resp = get("");

        assertThat(resp.<Boolean>read("$.data.available")).as("乾淨 clone 沒有 FSM 狀態檔：available=true、projects=[]").isTrue();
        assertThat(resp.<Object>read("$.data.reason")).isNull();
        assertThat(resp.<List<Object>>read("$.data.projects")).isEmpty();
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
    }

    // ── 專案層級的問題：引擎仍可用（E2E-15 第 4 列）──────────────────────────────────────────

    @Test
    void anUnknownProjectKeepsTheEngineAvailableWithNotFoundAndTheListIntact() {
        Resp resp = get("?project=nope");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("fsm_not_found");
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
        assertThat(resp.<String>read("$.data.version.latest")).isEqualTo("AISDLC_SDD_v9.99");
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).containsExactly("e2e-alpha", "e2e-bravo");
    }

    @Test
    void anUnreadableFsmFileKeepsTheEngineAvailableWithTheUnreadableReason() {
        MINI.sdd.unreadable.add("e2e-broken");

        Resp resp = get("?project=e2e-broken");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("fsm_state_unreadable");
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).hasSize(2);
        assertThat(resp.body()).as("Bridge 的 detail 不外露").doesNotContain("while scanning");
    }

    // ── project 驗證（v1.5：1～200 字元、不含控制字元；其餘原樣交給 Bridge 的淨化鏡像）──────────────────

    @Test
    void anEmptyTooLongOrControlCharNameIs400AndNeverReachesTheBridge() {
        // 注意：MockMvc 會把範本字串裡的 % 再編一次碼，所以這裡寫真實字元（換行、tab、DEL、NUL），不寫 %0A 這類跳脫
        for (String query : List.of("?project=", "?project=" + "x".repeat(201), "?project=a\nb", "?project=a\tb",
                "?project=a\u007fb", "?project=a\u0000b")) {
            Resp resp = get(query);

            assertThat(resp.status()).as(query.length() + "").isEqualTo(400);
            assertThat(resp.errorFields()).as(query.length() + "").containsExactly("project");
        }
        assertThat(sddRequests()).as("驗證在任何 Bridge 呼叫之前").isZero();
    }

    @Test
    void anyOtherNameGoesToTheBridgeRawAndItsMirrorFindsTheCanonicalKey() {
        MINI.sdd.addProject("a:b", "IMPLEMENTATION", 1, "sid-colon", "2026-10-16T02:00:00+00:00",
                new MiniBridge.Sdd.SddRetry(0, null), Map.of("count", 0, "items", List.of()));

        Resp raw = get("?project=a:b");
        Resp spaced = get("?project=a b");

        assertThat(raw.status()).isEqualTo(200);
        assertThat(raw.<String>read("$.data.fsm.project")).as("檔內原名").isEqualTo("a:b");
        assertThat(raw.<String>read("$.data.fsm.fsmProject")).as("淨化後的標準鍵（不能拿 project 當鍵）").isEqualTo("a_b");
        assertThat(raw.<List<String>>read("$.data.projects[*].project")).contains("a_b");
        assertThat(spaced.<String>read("$.data.reason")).as("原名 a b 淨化後是 a b，沒有這個檔").isEqualTo("fsm_not_found");
        assertThat(MINI.requests()).as("Console 沒有改寫名稱").contains("GET /sdd/fsm/a:b", "GET /sdd/fsm/a b");
    }

    // ── v1.5：fsm 的新欄位（契約 §1.10.4）──────────────────────────────────────────────────

    @Test
    void theV15FieldsAreVerbatimAndRecoveryIsAbsentOutsideAnEscalation() {
        Resp resp = get("?project=e2e-alpha");

        assertThat(resp.<Map<String, Object>>read("$.data.fsm.phase")).containsEntry("name", "IMPLEMENTATION")
                .containsEntry("order", 5).containsEntry("blocking", false).containsEntry("observation", false);
        assertThat(resp.<List<Object>>read("$.data.fsm.escalationHistory")).isEmpty();
        assertThat(resp.<Object>read("$.data.fsm.escalationProvenance")).isNull();
        assertThat(resp.<String>read("$.data.fsm.fsmProject")).isEqualTo("e2e-alpha");
        assertThat(resp.<Object>read("$.data.fsm.recovery")).as("非 ESCALATION：null（鍵固定出現）").isNull();
    }

    @Test
    void anEscalationCarriesHistoryProvenanceAndRecoveryVerbatim() {
        MINI.sdd.addProject("e2e-esc", "ESCALATION", 1, "sid-esc", "2026-10-17T09:12:40+00:00",
                new MiniBridge.Sdd.SddRetry(0, null), Map.of("count", 0, "items", List.of()));
        Map<String, Object> state = MINI.sdd.states.get("e2e-esc");
        state.put("escalation_history", List.of(Map.of("triggered_at", "2026-10-17T09:12:40+00:00", "source",
                "autoclaude_delegated_failed", "resolved_at", "")));
        state.put("escalation_provenance", Map.of("rule_id", "unknown", "source", "autoclaude_delegated_failed",
                "reason", "console-run ENGINE-ESCALATION"));

        Resp resp = get("?project=e2e-esc");

        assertThat(resp.<Map<String, Object>>read("$.data.fsm.phase")).containsEntry("name", "BLOCKED")
                .containsEntry("order", 0).containsEntry("blocking", true);
        assertThat(resp.<String>read("$.data.fsm.escalationHistory[0].triggered_at")).as("巢狀鍵保留 snake_case")
                .isEqualTo("2026-10-17T09:12:40+00:00");
        assertThat(resp.<String>read("$.data.fsm.escalationProvenance.source")).isEqualTo("autoclaude_delegated_failed");
        assertThat(resp.<String>read("$.data.fsm.recovery.target")).isEqualTo("IMPLEMENTATION");
        assertThat(resp.<String>read("$.data.fsm.recovery.powershell")).startsWith("Push-Location ").endsWith("Pop-Location")
                .contains("<人工原因>");
        assertThat(resp.<String>read("$.data.fsm.recovery.posix")).contains("resume-from-escalation")
                .contains("<人工原因>");
    }

    @Test
    void aBridgeThatLacksTheV15KeysYieldsTheDefaultsInsteadOfFailing() {
        Map<String, Object> state = MINI.sdd.states.get("e2e-alpha");
        for (String key : List.of("phase", "escalation_history", "escalation_provenance", "fsm_project", "recovery")) {
            state.remove(key);
        }

        Resp resp = get("?project=e2e-alpha");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<Object>read("$.data.fsm.phase")).isNull();
        assertThat(resp.<List<Object>>read("$.data.fsm.escalationHistory")).isEmpty();
        assertThat(resp.<Object>read("$.data.fsm.escalationProvenance")).isNull();
        assertThat(resp.<Object>read("$.data.fsm.fsmProject")).isNull();
        assertThat(resp.<Object>read("$.data.fsm.recovery")).isNull();
    }

    // ── v1.5：projectId（root 取自專案的 executionPath）──────────────────────────────────────

    private String projectAt(String name, String path) {
        return createProject(Map.of("name", name, "executionPath", path, "passCriteria", "- 通過"));
    }

    @Test
    void aProjectIdSendsTheProjectsRootToBothCallsAndDefaultsToTheProjectName() {
        String id = projectAt("e2e-alpha", "/work/e2e-alpha");

        Resp resp = get("?projectId=" + id);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.fsm.project")).isEqualTo("e2e-alpha");
        assertThat(MINI.sdd.rootsSeen).extracting(MiniBridge.Sdd.RootSeen::request, MiniBridge.Sdd.RootSeen::root)
                .containsExactly(org.assertj.core.groups.Tuple.tuple("GET /sdd/fsm", "/work/e2e-alpha"),
                        org.assertj.core.groups.Tuple.tuple("GET /sdd/fsm/e2e-alpha", "/work/e2e-alpha"));
        assertThat(MINI.countRequests("GET /sdd/version")).as("version 不帶 root").isEqualTo(1);
    }

    @Test
    void aBoundSddProjectBeatsTheProjectNameAndAnExplicitProjectBeatsBoth() {
        String id = projectAt("Some Other Name", "/work/bound");
        jdbc.update("update console.projects set sdd_project = 'e2e-bravo' where id = ?::uuid", id);

        assertThat(get("?projectId=" + id).<String>read("$.data.fsm.project")).isEqualTo("e2e-bravo");
        assertThat(get("?projectId=" + id + "&project=e2e-alpha").<String>read("$.data.fsm.project"))
                .isEqualTo("e2e-alpha");
        assertThat(MINI.sdd.rootsSeen).extracting(MiniBridge.Sdd.RootSeen::root).containsOnly("/work/bound");
    }

    @Test
    void anUnknownOrDeletedProjectIdIs404AndNeverReachesTheBridge() {
        String unknown = java.util.UUID.randomUUID().toString();
        Resp missing = get("?projectId=" + unknown);
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.<String>read("$.message")).isEqualTo("專案不存在或已刪除：" + unknown);
        assertThat(missing.has("$.reason")).as("一般 404 沒有 reason").isFalse();

        String gone = projectAt("gone", "/work/gone");
        assertThat(api.delete(operator(), "/api/v1/projects/" + gone).status()).isEqualTo(204);
        assertThat(get("?projectId=" + gone).status()).isEqualTo(404);
        assertThat(sddRequests()).isZero();
    }

    @Test
    void aBadProjectIdIs400AndAnInvalidProjectParamBeatsAnUnknownId() {
        Resp notUuid = get("?projectId=not-a-uuid");
        assertThat(notUuid.status()).isEqualTo(400);
        assertThat(notUuid.errorFields()).containsExactly("projectId");

        Resp both = get("?projectId=" + java.util.UUID.randomUUID() + "&project=a\nb");
        assertThat(both.status()).as("project 的 400 先於 projectId 的 404").isEqualTo(400);
        assertThat(both.errorFields()).containsExactly("project");
        assertThat(sddRequests()).isZero();
    }

    @Test
    void anEmptyRootIsNoErrorAndSkipsTheThirdCallForTheDefaultProject() {
        MINI.sdd.emptyRoots.add("/work/fresh");
        String id = projectAt("fresh", "/work/fresh");

        Resp resp = get("?projectId=" + id);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<Object>read("$.data.reason")).as("尚無 FSM 狀態檔：不是錯誤").isNull();
        assertThat(resp.<List<Object>>read("$.data.projects")).isEmpty();
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
        assertThat(MINI.requests()).containsExactly("GET /sdd/version", "GET /sdd/fsm");
    }

    @Test
    void aRootTheBridgeRejectsIsAvailableWithSddRootRejectedAndNoProjects() {
        MINI.sdd.rejectedRoots.add("/work/outside");
        String id = projectAt("outside", "/work/outside");

        Resp resp = get("?projectId=" + id);

        assertThat(resp.status()).as("不是 422／502").isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("sdd_root_rejected");
        assertThat(resp.<List<Object>>read("$.data.projects")).isEmpty();
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
        assertThat(resp.<String>read("$.data.version.latest")).as("version 保留").isEqualTo("AISDLC_SDD_v9.99");
    }

    @Test
    void aRootRejectedOnTheThirdCallIsAlsoSddRootRejected() {
        MINI.failNext("sddFsm", 422, Map.of("code", 422, "reason", "sanitization_failed", "violations",
                List.of(Map.of("field", "root", "rule", "not_found"))));
        String id = projectAt("e2e-alpha", "/work/e2e-alpha");

        Resp resp = get("?projectId=" + id);

        assertThat(resp.<String>read("$.data.reason")).isEqualTo("sdd_root_rejected");
        assertThat(resp.<List<Object>>read("$.data.projects")).isEmpty();
        assertThat(resp.<Boolean>read("$.data.available")).isTrue();
    }

    // ── 引擎層級的不可用：200＋available=false（第 7、8 列）──────────────────────────────────

    @Test
    void anUnreachableBridgeIs200BridgeUnreachableWithNothingElse() {
        setting("sdd", "engineUrl", "http://127.0.0.1:1");

        Resp resp = get("?project=e2e-alpha");

        assertThat(resp.status()).as("不是 502").isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isFalse();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("bridge_unreachable");
        assertThat(resp.<Object>read("$.data.version")).isNull();
        assertThat(resp.<List<Object>>read("$.data.projects")).isEmpty();
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
        assertThat(resp.<String>read("$.data.checkedAt")).endsWith("Z");
    }

    @Test
    void aBridgeThatAnswersTooSlowlyIsAlsoBridgeUnreachable() {
        MINI.sdd.delayMillis = 3_600;

        long started = System.nanoTime();
        Resp resp = get("");
        long elapsedMillis = (System.nanoTime() - started) / 1_000_000;

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isFalse();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("bridge_unreachable");
        assertThat(elapsedMillis).as("讀取逾時 3 秒、不重試（重試會讓這裡超過 9 秒）").isBetween(2_500L, 8_000L);
        assertThat(MINI.countRequests("GET /sdd/version")).as("只打一次，失敗即短路").isEqualTo(1);
    }

    @Test
    void anInvalidSddRootIs200SddUnavailableAndTheLaterCallsAreNeverMade() {
        MINI.sdd.unavailable = true;

        Resp resp = get("?project=e2e-alpha");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.available")).isFalse();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("sdd_unavailable");
        assertThat(resp.<Object>read("$.data.version")).isNull();
        assertThat(resp.<List<Object>>read("$.data.projects")).isEmpty();
        assertThat(MINI.requests()).as("第一個呼叫就失敗：後面的不再發").containsExactly("GET /sdd/version");
    }

    @Test
    void aServerErrorOrAWrongShapeIsBridgeErrorAndKeepsTheVersion() {
        MINI.failNext("sddVersion", 500, Map.of("code", 500, "reason", "boom"));
        Resp first = get("");
        assertThat(first.status()).isEqualTo(200);
        assertThat(first.<Boolean>read("$.data.available")).isFalse();
        assertThat(first.<String>read("$.data.reason")).isEqualTo("bridge_error");
        assertThat(first.<Object>read("$.data.version")).isNull();

        MINI.failNext("sddFsmList", 200, Map.of("unexpected", true));
        Resp second = get("");
        assertThat(second.<Boolean>read("$.data.available")).isFalse();
        assertThat(second.<String>read("$.data.reason")).as("2xx 但形狀不對").isEqualTo("bridge_error");
        assertThat(second.<String>read("$.data.version.latest")).as("第二個呼叫失敗：保留版本").isEqualTo("AISDLC_SDD_v9.99");
        assertThat(second.<List<Object>>read("$.data.projects")).isEmpty();
    }

    @Test
    void aThirdCallFailureMakesTheEngineUnavailableButKeepsTheList() {
        MINI.failNext("sddFsm", 500, Map.of("code", 500, "reason", "boom"));

        Resp resp = get("?project=e2e-alpha");

        assertThat(resp.<Boolean>read("$.data.available")).isFalse();
        assertThat(resp.<String>read("$.data.reason")).isEqualTo("bridge_error");
        assertThat(resp.<Object>read("$.data.fsm")).isNull();
        assertThat(resp.<String>read("$.data.version.latest")).isEqualTo("AISDLC_SDD_v9.99");
        assertThat(resp.<List<String>>read("$.data.projects[*].project")).containsExactly("e2e-alpha", "e2e-bravo");
    }

    // ── 不快取、唯讀、標頭與權限 ────────────────────────────────────────────────────────────

    @Test
    void everyRequestHitsTheBridgeAndCarriesTheTraceIdOfItsOwnRequest() {
        Resp first = get("");
        Resp second = get("");

        assertThat(MINI.countRequests("GET /sdd/version")).as("這支端點不快取").isEqualTo(2);
        assertThat(first.header("X-Trace-Id")).isNotBlank().isNotEqualTo(second.header("X-Trace-Id"));
        assertThat(MINI.traced().stream().filter(t -> t.request().startsWith("GET /sdd")).toList())
                .extracting(MiniBridge.Traced::traceId)
                .containsExactly(first.header("X-Trace-Id"), first.header("X-Trace-Id"), second.header("X-Trace-Id"),
                        second.header("X-Trace-Id"));
    }

    @Test
    void onlyAnAuthenticatedUserMayReadAndEveryRoleMay() {
        assertThat(api.get(null, SDD).status()).isEqualTo(401);
        for (String token : List.of(viewer(), operator(), admin())) {
            assertThat(api.get(token, SDD).status()).isEqualTo(200);
        }
        assertThat(api.post(operator(), SDD, Map.of()).status()).as("沒有任何寫入方法：只讀端點").isEqualTo(405);
    }
}
