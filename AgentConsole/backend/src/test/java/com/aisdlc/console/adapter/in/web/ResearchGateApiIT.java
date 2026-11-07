package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.ResearchP1Fixtures;
import com.aisdlc.console.support.ResearchP2Fixtures;
import com.aisdlc.minibridge.MiniResearch.Reply;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 內環閘登錄（API-RP-23；TCS-ResearchToPRD-P2 AC-962-4）。為什麼重要：SCG-4／5／6 的決定是內環能不能往下走的人工證據——console-api 必須在零 Bridge 請求下擋掉
 * 前置不成立、輸入不合與 SCR 期間的登錄，必須把 Bridge 的漂移拒絕與 escalated 如實透傳而不是自己重算，並且絕不替審查者判斷獨立性。
 * 本類以「RELEASE_READY＋FAIL」為通過輸入閘後必達 Bridge 的載具（該組合沒有 RTM 前置）。
 */
class ResearchGateApiIT extends AbstractResearchIT {

    private ResearchP1Fixtures p1;

    @BeforeEach
    void p1() {
        p1 = new ResearchP1Fixtures(jdbc);
    }

    private UUID bound(String slug) {
        UUID research = p1.project(slug, "UNDECIDED");
        UUID console = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria, sdd_project) values (?, ?, ?, ?, ?)", console, "專案 " + slug, "/e2e/" + slug,
                "通過", "impl-" + slug);
        p1.bind(research, console);
        return research;
    }

    private String url(UUID id) {
        return RESEARCH + "/projects/" + id + "/gates";
    }

    private static Map<String, Object> body(String gate, String result, String reason, Boolean independent) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("gate", gate);
        body.put("result", result);
        if (reason != null) {
            body.put("reason", reason);
        }
        if (independent != null) {
            body.put("reviewerIndependent", independent);
        }
        return body;
    }

    private static Map<String, Object> releaseFail() {
        return body("RELEASE_READY", "FAIL", "回歸未過", null);
    }

    private long gateCalls() {
        return bridge().calls.stream().filter(c -> c.path().endsWith(":gates")).count();
    }

    private long researchRows() {
        return rows("research_gate_decisions") + rows("research_events") + rows("research_deliveries");
    }

    @Test
    void AT_962_4_1_adminRegistrationSendsExactlyOneGatesCallWithGeneratedDecisionIdAndJwtSubjectAndTheShapeIsFixed() {
        UUID id = bound("g41");
        long before = researchRows();

        Resp ok = api.post(adminAs("alice"), url(id), body("RELEASE_READY", "FAIL", "回歸未過", null));

        assertThat(ok.status()).isEqualTo(200);
        assertThat(gateCalls()).isEqualTo(1);
        Map<String, Object> sent = bridge().calls.stream().filter(c -> c.path().endsWith(":gates")).findFirst().orElseThrow().body();
        assertThat(UUID.fromString((String) sent.get("decision_id"))).isNotNull();
        assertThat(sent).containsEntry("approver", "alice").containsEntry("requested_by", "alice").containsEntry("gate", "RELEASE_READY")
                .containsEntry("result", "FAIL").containsKeys("reason", "review_report_ref", "reviewer_independent", "run_id").doesNotContainKey("github_token");
        for (String key : List.of("gateDecisionId", "gate", "result", "fsmStateBefore", "nextState", "escalated", "flow")) {
            assertThat(ok.has("$.data." + key)).as(key).isTrue();
        }
        assertThat(researchRows()).as("console-api 對 research_* 零寫入").isEqualTo(before);
    }

    @Test
    void AT_962_4_2_prReviewPreconditionsFailWith409UnmetListAndZeroBridgeRequests() {
        UUID id = bound("g42");

        Resp resp = api.post(adminAs("alice"), url(id), body("PR_REVIEW", "PASS", null, true));

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("fsm_state_conflict");
        assertThat(resp.<List<String>>read("$.details.unmet")).containsExactly("tasks_incomplete", "rtm_unavailable");
        assertThat(gateCalls()).isZero();
    }

    @Test
    void AT_962_4_3_rtmVerifyWithoutAnAvailableRtmIsRefusedBeforeTheBridge() {
        UUID id = bound("g43");

        Resp resp = api.post(adminAs("alice"), url(id), body("RTM_VERIFY", "PASS", null, null));

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<List<String>>read("$.details.unmet")).contains("rtm_unavailable");
        assertThat(gateCalls()).isZero();
    }

    @Test
    void AT_962_4_4_prReviewDemandsReviewerIndependentTrueAndOtherGatesDoNotAndConsoleNeverJudgesIndependence() {
        UUID id = bound("g44");
        for (Boolean independent : new Boolean[] {false, null}) {
            Resp resp = api.post(adminAs("alice"), url(id), body("PR_REVIEW", "PASS", null, independent));
            assertThat(resp.status()).as("PR_REVIEW independent=" + independent).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).isEqualTo("invalid_request");
            assertThat(resp.<String>read("$.details.violations[0].field")).isEqualTo("reviewerIndependent");
            assertThat(resp.<String>read("$.details.violations[0].rule")).isEqualTo("reviewer_independence_required");
        }
        Resp rtm = api.post(adminAs("alice"), url(id), body("RTM_VERIFY", "PASS", null, false));
        assertThat(rtm.status()).as("RTM_VERIFY 不要求獨立性（前置才擋）").isEqualTo(409);
        assertThat(api.post(adminAs("alice"), url(id), releaseFail()).status()).as("RELEASE_READY FAIL 不要求獨立性").isEqualTo(200);
        assertThat(gateCalls()).as("只有 RELEASE_READY FAIL 到達 Bridge").isEqualTo(1);
    }

    @Test
    void AT_962_4_5_fieldBoundariesOfReasonReportRefAndTheGateResultCombination() {
        UUID id = bound("g45");
        String t = adminAs("alice");
        long calls = gateCalls();
        for (Map<String, Object> bad : List.of(body("RELEASE_READY", "FAIL", "", null), body("RELEASE_READY", "FAIL", "字".repeat(501), null),
                body("RELEASE_READY", "FAIL", "x", null), body("NOPE", "PASS", null, null), body("RELEASE_READY", "PASS", null, null))) {
            if ("x".equals(bad.get("reason"))) {
                bad.put("reviewReportRef", "r".repeat(301));
            }
            Resp resp = api.post(t, url(id), bad);
            assertThat(resp.status()).as(bad.toString()).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).isEqualTo("invalid_request");
        }
        Resp releasePass = api.post(t, url(id), body("RELEASE_READY", "PASS", null, null));
        assertThat(releasePass.<String>read("$.details.violations[0].rule")).isEqualTo("release_pass_via_tag");
        assertThat(gateCalls()).as("被擋的輸入零 Bridge 請求").isEqualTo(calls);
        Map<String, Object> max = body("RELEASE_READY", "FAIL", "字".repeat(500), null);
        max.put("reviewReportRef", "r".repeat(300));
        assertThat(api.post(t, url(id), max).status()).as("500 與 300 字元邊界通過").isEqualTo(200);
    }

    @Test
    void AT_962_4_6_anOpenScrBlocksWith409AndEscalatedIsTheBridgeValueNotComputedHere() {
        UUID blocked = bound("g46a");
        p1.scr(blocked, 1, "MINOR", "OPEN");
        Resp scr = api.post(adminAs("alice"), url(blocked), releaseFail());
        assertThat(scr.status()).isEqualTo(409);
        assertThat(scr.<String>read("$.reason")).isEqualTo("scr_open");
        assertThat(gateCalls()).isZero();

        UUID id = bound("g46b");
        bridge().next("gates", new Reply(200, Map.of("gate_decision_id", UUID.randomUUID().toString(), "gate", "RELEASE_READY", "result", "FAIL",
                "fsm_state_before", "RELEASE_READY", "next_state", "ESCALATION_FINAL", "escalated", true, "flow", Map.of("step", "deliver"))));
        Resp escalated = api.post(adminAs("alice"), url(id), releaseFail());
        assertThat(escalated.status()).isEqualTo(200);
        assertThat(escalated.<Boolean>read("$.data.escalated")).isTrue();
        assertThat(escalated.<String>read("$.data.nextState")).isEqualTo("ESCALATION_FINAL");
    }

    @Test
    void AT_962_4_E_3_unknownProjectIs404AndAnUnboundProjectIs409WithNoConsoleProjectAndNeitherReachesTheBridge() {
        Resp missing = api.post(adminAs("alice"), url(UUID.randomUUID()), releaseFail());
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.<String>read("$.reason")).isEqualTo("research_not_found");

        UUID unbound = p1.project("g4e3", "UNDECIDED");
        Resp conflict = api.post(adminAs("alice"), url(unbound), releaseFail());
        assertThat(conflict.status()).isEqualTo(409);
        assertThat(conflict.<String>read("$.reason")).isEqualTo("fsm_state_conflict");
        assertThat(conflict.<List<String>>read("$.details.unmet")).contains("no_console_project");
        assertThat(gateCalls()).isZero();
    }

    @Test
    void AT_962_4_E_4_aSlowBridgeIs504WithNoPartialStateAndTheAuditRowStillWritten() {
        UUID id = bound("g4e4");
        long researchBefore = researchRows();
        long auditBefore = rows("audit_log");
        readTimeout.cap(Duration.ofSeconds(1));
        bridge().delayMillis = 3000;

        Resp resp = api.post(adminAs("alice"), url(id), releaseFail());

        assertThat(resp.status()).as(resp.body()).isEqualTo(504);
        assertThat(resp.<String>read("$.reason")).isEqualTo("bridge_timeout");
        assertThat(researchRows()).isEqualTo(researchBefore);
        assertThat(rows("audit_log")).as("AuditLoggingFilter 仍橫切一列").isGreaterThan(auditBefore);
    }

    @Test
    void AT_962_4_E_5_aDigestMismatchFromTheBridgeIsRelayedVerbatimWithDriftDetails() {
        UUID id = bound("g4e5");
        List<Map<String, Object>> drift = List.of(Map.of("path", "docs/03_testing/TCS.md", "expected_sha256", "a".repeat(64), "actual_sha256", "b".repeat(64)));
        bridge().next("gates", Reply.error(422, "digest_mismatch", "details", Map.of("drift", drift)));
        long auditBefore = rows("audit_log");
        long researchBefore = researchRows();

        Resp resp = api.post(adminAs("alice"), url(id), releaseFail());

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo("digest_mismatch");
        assertThat(resp.<String>read("$.details.drift[0].path")).isEqualTo("docs/03_testing/TCS.md");
        assertThat(resp.<String>read("$.details.drift[0].expected_sha256")).isEqualTo("a".repeat(64));
        assertThat(resp.<String>read("$.details.drift[0].actual_sha256")).isEqualTo("b".repeat(64));
        assertThat(rows("audit_log")).isEqualTo(auditBefore + 1);
        assertThat(researchRows()).isEqualTo(researchBefore);
    }

    // ── D-159：以迷你 Bridge 的 FSM 與 RTM 注入補齊前置案（4-1 最新 run id、4-2 三種前置、4-3 邊界）──

    private ResearchP2Fixtures p2() {
        return new ResearchP2Fixtures(jdbc, MINI);
    }

    private Map<String, Object> lastGateBody() {
        return bridge().calls.stream().filter(c -> c.path().endsWith(":gates")).reduce((a, b) -> b).orElseThrow().body();
    }

    @Test
    void AT_962_4_1_prReviewPassForwardsTheLatestRunIdWhenTasksAreDoneAndRtmIsFullyCovered() {
        ResearchP2Fixtures.Ready ready = p2().ready("g41r");
        // 較舊的 run 不得被當成「最新」：再插一個 run_number 2，並讓它成為有 RTM 的那個
        UUID newest = UUID.randomUUID();
        jdbc.update("insert into console.execution_runs (id, project_id, run_number, status, autonomy_level, scope) values (?, ?, 2, 'COMPLETED', 4, '{}'::jsonb)",
                newest, ready.console());
        MINI.rtmFor(newest, true, 100.0, 5, 5);

        Resp ok = api.post(adminAs("alice"), url(ready.research()), body("PR_REVIEW", "PASS", null, true));

        assertThat(ok.status()).as(ok.body()).isEqualTo(200);
        assertThat(gateCalls()).isEqualTo(1);
        assertThat(lastGateBody()).containsEntry("run_id", newest.toString()).containsEntry("gate", "PR_REVIEW").containsEntry("reviewer_independent", true)
                .containsEntry("approver", "alice").containsEntry("requested_by", "alice");
        assertThat(ok.<String>read("$.data.gate")).isEqualTo("PR_REVIEW");
        assertThat(ok.<String>read("$.data.result")).isEqualTo("PASS");
        assertThat(ok.<String>read("$.data.flow.step")).isEqualTo("deliver");
    }

    @Test
    void AT_962_4_2_eachUnmetPreconditionIsListedAndMultipleCanCoexistWithZeroBridgeRequests() {
        ResearchP2Fixtures.Ready tasksOpen = p2().ready("g42a");
        p2().task(tasksOpen, "RUNNING");
        p2().rtm(tasksOpen, true, 100.0);
        Resp a = api.post(adminAs("alice"), url(tasksOpen.research()), body("PR_REVIEW", "PASS", null, true));
        assertThat(a.status()).isEqualTo(409);
        assertThat(a.<List<String>>read("$.details.unmet")).containsExactly("tasks_incomplete");

        ResearchP2Fixtures.Ready notCovered = p2().ready("g42b");
        p2().rtm(notCovered, false, 100.0);
        Resp b = api.post(adminAs("alice"), url(notCovered.research()), body("PR_REVIEW", "PASS", null, true));
        assertThat(b.<List<String>>read("$.details.unmet")).containsExactly("rtm_below_100");

        ResearchP2Fixtures.Ready noRtm = p2().ready("g42c");
        Resp c = api.post(adminAs("alice"), url(noRtm.research()), body("PR_REVIEW", "PASS", null, true));
        assertThat(c.<List<String>>read("$.details.unmet")).containsExactly("rtm_unavailable");

        ResearchP2Fixtures.Ready both = p2().ready("g42d");
        p2().task(both, "FAILED");
        p2().rtm(both, false, 80.0);
        Resp d = api.post(adminAs("alice"), url(both.research()), body("PR_REVIEW", "PASS", null, true));
        assertThat(d.<List<String>>read("$.details.unmet")).containsExactly("tasks_incomplete", "rtm_below_100");

        for (Resp resp : List.of(a, b, c, d)) {
            assertThat(resp.<String>read("$.reason")).isEqualTo("fsm_state_conflict");
        }
        assertThat(gateCalls()).isZero();
    }

    @Test
    void AT_962_4_3_rtmVerifyForwardsOnlyAtExactly100AndRefuses99Point99WithZeroBridgeRequests() {
        ResearchP2Fixtures.Ready almost = p2().ready("g43a");
        p2().rtm(almost, true, 99.99);
        Resp refused = api.post(adminAs("alice"), url(almost.research()), body("RTM_VERIFY", "PASS", null, null));
        assertThat(refused.status()).isEqualTo(409);
        assertThat(refused.<List<String>>read("$.details.unmet")).contains("rtm_below_100");
        assertThat(gateCalls()).isZero();

        ResearchP2Fixtures.Ready full = p2().ready("g43b");
        p2().rtm(full, true, 100.0);
        Resp ok = api.post(adminAs("alice"), url(full.research()), body("RTM_VERIFY", "PASS", null, null));
        assertThat(ok.status()).isEqualTo(200);
        assertThat(gateCalls()).isEqualTo(1);
        assertThat(lastGateBody()).containsEntry("run_id", full.run().toString());
    }
}
