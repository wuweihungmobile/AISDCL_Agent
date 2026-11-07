package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.application.service.ResearchDeliveryService;
import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.BridgeSource;
import com.aisdlc.console.support.ResearchP1Fixtures;
import com.aisdlc.console.support.ResearchP2Fixtures;
import com.aisdlc.minibridge.MiniResearch.Call;
import com.aisdlc.minibridge.MiniResearch.Reply;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 交付端點（API-RP-17／28；TCS-ResearchToPRD-P2 AC-962-17、19～22）。為什麼重要：Release Tag 與 PR 是不可逆的外部動作——輸入不合、前置不成立、
 * 預覽未確認都必須在 console-api 就被擋下（零 Bridge 請求）；GitHub token 只能出現在 PR 的單次 Bridge 請求；每個請求都要有稽核列且與 Bridge 同一個 traceId。
 */
class ResearchDeliveryApiIT extends AbstractResearchIT {

    private ResearchP1Fixtures p1;
    private UUID research;

    @BeforeEach
    void fixtures() {
        p1 = new ResearchP1Fixtures(jdbc);
        research = p1.project("dlv-" + UUID.randomUUID().toString().substring(0, 8), "UNDECIDED");
    }

    private String url(String suffix) {
        return RESEARCH + "/projects/" + research + suffix;
    }

    private long deliveryCalls() {
        return bridge().calls.stream().filter(c -> c.path().contains(":tag") || c.path().contains(":pr")).count();
    }

    private static Map<String, Object> tag(String name) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("tagName", name);
        return body;
    }

    @Test
    void AT_962_19_2_unmetPreconditionsAreListedWith409AndZeroBridgeRequests() {
        p1.scr(research, 1, "MINOR", "OPEN");

        Resp resp = api.post(adminAs("alice"), url("/delivery/tag"), tag("v1.0.0"));

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("fsm_state_conflict");
        assertThat(resp.<List<String>>read("$.details.unmet")).containsExactly("no_console_project", "scr_open");
        assertThat(deliveryCalls()).isZero();
    }

    @Test
    void AT_962_19_3_tagNameFollowsTheSameSemverPatternAsTheBridgeAndLongOrMalformedNamesAreRejectedBeforeTheBridge() {
        String bridgeSource = BridgeSource.source("research", "gitops.py");
        assertThat(ResearchDeliveryService.TAG_NAME_PATTERN).as("兩端各持一份，字面逐位對拍").satisfies(pattern -> {
            assertThat(bridgeSource).contains("r\"^v?(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\"");
            assertThat(bridgeSource).contains("r\"(-[0-9A-Za-z.-]+)?(\\+[0-9A-Za-z.-]+)?$\"");
            assertThat(pattern).isEqualTo("^v?(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\\+[0-9A-Za-z.-]+)?$");
        });
        assertThat(bridgeSource).contains("TAG_MAX_CHARS = " + ResearchDeliveryService.TAG_NAME_MAX);
        String t = adminAs("alice");
        for (String bad : List.of("1.0", "v1.0.0 ", "-v1.0.0", "v01.0.0", "release", "v1.0.0-" + "a".repeat(60))) {
            Resp resp = api.post(t, url("/delivery/tag"), tag(bad));
            assertThat(resp.status()).as(bad).isEqualTo(422);
            assertThat(resp.<String>read("$.details.violations[0].rule")).isEqualTo("not_semver");
        }
        for (String good : List.of("v1.0.0", "1.2.3-rc.1", "v10.20.30+build.5")) {
            assertThat(api.post(t, url("/delivery/tag"), tag(good)).status()).as(good + " 通過輸入閘（前置才擋）").isEqualTo(409);
        }
        assertThat(deliveryCalls()).isZero();
    }

    @Test
    void AT_962_19_4_messageBoundaryIs200Pass201Rejected() {
        Map<String, Object> ok = tag("v1.0.0");
        ok.put("message", "字".repeat(200));
        assertThat(api.post(adminAs("alice"), url("/delivery/tag"), ok).status()).as("200 字通過輸入閘").isEqualTo(409);
        Map<String, Object> bad = tag("v1.0.0");
        bad.put("message", "字".repeat(201));
        Resp resp = api.post(adminAs("alice"), url("/delivery/tag"), bad);
        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.details.violations[0].rule")).isEqualTo("message_too_long");
    }

    @Test
    void AT_962_19_E_3_createGithubReleaseTrueIs422AndNeverReachesTheBridge() {
        Map<String, Object> body = tag("v1.0.0");
        body.put("createGithubRelease", true);

        Resp resp = api.post(adminAs("alice"), url("/delivery/tag"), body);

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo("invalid_request");
        assertThat(resp.<String>read("$.details.violations[0].rule")).isEqualTo("release_not_supported");
        assertThat(deliveryCalls()).isZero();
    }

    @Test
    void AT_962_20_E_2_bodyPreviewAckFalseOrMissingIs422WithZeroBridgeRequests() {
        for (Map<String, Object> body : List.of(Map.<String, Object>of("bodyPreviewAck", false), Map.<String, Object>of())) {
            Resp resp = api.post(adminAs("alice"), url("/delivery/pr"), body);
            assertThat(resp.status()).as(body.toString()).isEqualTo(422);
            assertThat(resp.<String>read("$.details.violations[0].rule")).isEqualTo("preview_ack_required");
        }
        assertThat(deliveryCalls()).isZero();
    }

    @Test
    void AT_962_20_8_thePrBridgeRequestCarriesAckApproverAndNoTokenWhenNoneIsConfiguredAndTheResponseCarriesNoSecret() {
        Resp resp = api.post(adminAs("alice"), url("/delivery/pr"), Map.of("bodyPreviewAck", true));

        assertThat(resp.status()).isEqualTo(200);
        Call call = bridge().calls.stream().filter(c -> c.path().endsWith(":pr")).findFirst().orElseThrow();
        assertThat(call.body()).containsEntry("body_preview_ack", true).containsEntry("approver", "alice").containsEntry("requested_by", "alice");
        assertThat(resp.body()).doesNotContain("github_token");
    }

    @Test
    void AT_962_17_7_traceabilityIsTypedViewerReadableAndRelaysAPrdNotFrozenConflict() {
        Resp ok = api.get(viewer(), url("/delivery/traceability"));
        assertThat(ok.status()).isEqualTo(200);
        assertThat(ok.has("$.data.rows")).isTrue();
        assertThat(ok.<Integer>read("$.data.totals.frTotal")).isZero();
        assertThat(ok.<Object>read("$.data.rtm")).isNull();

        bridge().next("traceability-preview", Reply.error(409, "fsm_state_conflict", "details", Map.of("unmet", List.of("prd_not_frozen"))));
        Resp conflict = api.get(viewer(), url("/delivery/traceability"));
        assertThat(conflict.status()).isEqualTo(409);
        assertThat(conflict.<List<String>>read("$.details.unmet")).containsExactly("prd_not_frozen");
    }

    @Test
    void AT_962_17_7_theTraceabilityRowShapeIsTypedWithNestedGherkinAndStringSources() {
        bridge().next("traceability-preview", new Reply(200, Map.of("rows", List.of(Map.of("ac", "AC-001-1", "userStory", "US-001 登入",
                "gherkinSummary", Map.of("given", "給定", "when", "當", "then", "則"), "unitStatus", "PASS", "e2eStatus", "NOT_RUN", "lastRunAt", "2026-11-08T00:00:00Z",
                "source", List.of("task:T-1", "RTM-COVERAGE-k.yaml"))), "totals", Map.of("acTotal", 1, "covered", 1, "uncovered", 0, "frTotal", 3),
                "rtm", Map.of("runId", "r1", "fullyCovered", true, "acPct", 100.0, "advisory", true), "generatedAt", "2026-11-08T00:00:00Z")));

        Resp resp = api.get(viewer(), url("/delivery/traceability"));

        assertThat(resp.<String>read("$.data.rows[0].gherkinSummary.when")).isEqualTo("當");
        assertThat(resp.<List<String>>read("$.data.rows[0].source")).containsExactly("task:T-1", "RTM-COVERAGE-k.yaml");
        assertThat(resp.<Integer>read("$.data.totals.frTotal")).isEqualTo(3);
        assertThat(resp.<Boolean>read("$.data.rtm.advisory")).isTrue();
    }

    @Test
    void AT_962_21_7_theOverviewHasTheFixedKeysAndViewerCanRead() {
        Resp resp = api.get(viewer(), url("/delivery"));

        assertThat(resp.status()).isEqualTo(200);
        for (String key : List.of("deliveries", "snapshot", "projectRoot", "containerMode", "preconditions", "releaseReady", "rtmFull", "scrOpen", "hasOrigin",
                "ghAvailable")) {
            assertThat(resp.body()).as(key).contains("\"" + key + "\":");
        }
        assertThat(resp.<Object>read("$.data.preconditions.hasOrigin")).isNull();
        assertThat(resp.<List<Object>>read("$.data.deliveries")).isEmpty();
    }

    @Test
    void AT_962_22_3_everyPrRequestLeavesAnAuditRowWithTheSameTraceIdAsTheBridgeEvent() {
        long before = rows("audit_log");
        Resp resp = api.post(adminAs("alice"), url("/delivery/pr"), Map.of("bodyPreviewAck", true));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(rows("audit_log")).isGreaterThan(before);
        Call call = bridge().calls.stream().filter(c -> c.path().endsWith(":pr")).findFirst().orElseThrow();
        assertThat(jdbc.queryForList("select trace_id from console.audit_log where path like ? and method = 'POST'", String.class, "%" + research + "/delivery/pr"))
                .containsExactly(call.traceId());
    }

    // ── D-159：前置（RELEASE_READY＋RTM 全覆蓋＋無 OPEN SCR）以迷你 Bridge 的 FSM／RTM 注入構造，Bridge 的正負控回應一律依 research_deliver.py／delivery.py 現碼形狀 ──

    private ResearchP2Fixtures p2() {
        return new ResearchP2Fixtures(jdbc, MINI);
    }

    private String tagUrl(ResearchP2Fixtures.Ready ready) {
        return RESEARCH + "/projects/" + ready.research() + "/delivery/tag";
    }

    private String prUrl(ResearchP2Fixtures.Ready ready) {
        return RESEARCH + "/projects/" + ready.research() + "/delivery/pr";
    }

    private Call lastCall(String verb) {
        return bridge().calls.stream().filter(c -> c.path().endsWith(":" + verb)).reduce((a, b) -> b).orElseThrow();
    }

    private long tableRows() {
        return rows("research_deliveries") + rows("research_gate_decisions") + rows("research_events");
    }

    @Test
    void AT_962_19_1_aReadyProjectSendsExactlyOneTagCallWithTheFixedBodyAndNoGithubTokenAndTheShapeIsTyped() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d191");
        Map<String, Object> request = tag("v1.0.0");
        request.put("message", "發佈");
        request.put("push", true);

        Resp resp = api.post(adminAs("alice"), tagUrl(ready), request);

        assertThat(resp.status()).as(resp.body()).isEqualTo(201);
        assertThat(bridge().calls.stream().filter(c -> c.path().endsWith(":tag")).count()).isEqualTo(1);
        assertThat(lastCall("tag").body()).containsEntry("tag_name", "v1.0.0").containsEntry("message", "發佈").containsEntry("push", true)
                .containsEntry("create_github_release", false).containsEntry("approver", "alice").containsEntry("requested_by", "alice").doesNotContainKey("github_token");
        assertThat(resp.<String>read("$.data.delivery.kind")).isEqualTo("RELEASE_TAG");
        assertThat(resp.<String>read("$.data.delivery.ref")).isEqualTo("v1.0.0");
        assertThat(resp.<String>read("$.data.delivery.snapshotSha256")).hasSize(64);
        assertThat(resp.<String>read("$.data.snapshot.relPath")).isEqualTo("03_execution/traceability_matrix.json");
        assertThat(resp.<String>read("$.data.flow.phase")).isEqualTo("DELIVERED");
        assertThat(resp.<String>read("$.data.fsmState")).isEqualTo("RELEASE");
    }

    @Test
    void AT_962_19_2_eachUnmetPreconditionNamesItselfWhenAProjectIsAlmostReady() {
        ResearchP2Fixtures.Ready wrongState = p2().ready("d192a");
        p2().fsm(wrongState, "PR_REVIEW", true);
        p2().rtm(wrongState, true, 100.0);
        assertThat(api.post(adminAs("alice"), tagUrl(wrongState), tag("v1.0.0")).<List<String>>read("$.details.unmet")).containsExactly("not_release_ready");

        ResearchP2Fixtures.Ready lowRtm = p2().ready("d192b");
        p2().fsm(lowRtm, "RELEASE_READY", true);
        p2().rtm(lowRtm, true, 99.99);
        assertThat(api.post(adminAs("alice"), tagUrl(lowRtm), tag("v1.0.0")).<List<String>>read("$.details.unmet")).containsExactly("rtm_below_100");

        ResearchP2Fixtures.Ready scrOpen = p2().releaseReady("d192c");
        p1.scr(scrOpen.research(), 1, "MINOR", "OPEN");
        assertThat(api.post(adminAs("alice"), tagUrl(scrOpen), tag("v1.0.0")).<List<String>>read("$.details.unmet")).containsExactly("scr_open");

        assertThat(deliveryCalls()).isZero();
    }

    @Test
    void AT_962_19_5_theBridgeRefusalsTagExistsAndDeliveryStepFailedAreRelayedVerbatim() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d195");
        bridge().next("tag", Reply.error(409, "tag_exists", "details", Map.of("ref", "v1.0.0")));
        Resp exists = api.post(adminAs("alice"), tagUrl(ready), tag("v1.0.0"));
        assertThat(exists.status()).isEqualTo(409);
        assertThat(exists.<String>read("$.reason")).isEqualTo("tag_exists");

        bridge().next("tag", Reply.error(502, "delivery_step_failed", "details", Map.of("failure_step", "GIT_PUSH_TAG")));
        Resp failed = api.post(adminAs("alice"), tagUrl(ready), tag("v1.0.1"));
        assertThat(failed.status()).isEqualTo(502);
        assertThat(failed.<String>read("$.reason")).isEqualTo("delivery_step_failed");
        assertThat(failed.<String>read("$.details.failure_step")).isEqualTo("GIT_PUSH_TAG");
    }

    @Test
    void AT_962_19_6_everyTagRequestLeavesAnAuditRowWithTheSameTraceIdAsTheBridgeCall() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d196");
        long before = rows("audit_log");

        assertThat(api.post(adminAs("alice"), tagUrl(ready), tag("v1.0.0")).status()).isEqualTo(201);

        assertThat(rows("audit_log")).isGreaterThan(before);
        assertThat(jdbc.queryForList("select trace_id from console.audit_log where path like ? and method = 'POST'", String.class, "%" + ready.research() + "/delivery/tag"))
                .containsExactly(lastCall("tag").traceId());
    }

    @Test
    void AT_962_19_E_4_aSlowBridgeIs504WithNoDeliveryRowAndTheAuditRowStillWritten() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d19e4");
        long before = tableRows();
        long auditBefore = rows("audit_log");
        readTimeout.cap(java.time.Duration.ofSeconds(1));
        bridge().delayMillis = 3000;

        Resp resp = api.post(adminAs("alice"), tagUrl(ready), tag("v1.0.0"));

        assertThat(resp.status()).as(resp.body()).isEqualTo(504);
        assertThat(resp.<String>read("$.reason")).isEqualTo("bridge_timeout");
        assertThat(tableRows()).isEqualTo(before);
        assertThat(rows("audit_log")).isGreaterThan(auditBefore);
    }

    @Test
    void AT_962_19_E_5_aDigestMismatchOnTagIsRelayedWithTheDriftListAndWritesNothing() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d19e5");
        long before = tableRows();
        bridge().next("tag", Reply.error(422, "digest_mismatch", "details", Map.of("drift", List.of(Map.of("path", "docs/a.md", "expected_sha256", "a".repeat(64),
                "actual_sha256", "b".repeat(64))))));

        Resp resp = api.post(adminAs("alice"), tagUrl(ready), tag("v1.0.0"));

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo("digest_mismatch");
        assertThat(resp.<String>read("$.details.drift[0].path")).isEqualTo("docs/a.md");
        assertThat(tableRows()).isEqualTo(before);
    }

    @Test
    void AT_962_19_E_6_theContainerModeRefusalComesFromTheBridgeAndConsoleNeverGuessesTheDeployment() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d19e6");
        bridge().next("tag", Reply.error(422, "route_unsupported_in_deployment", "details",
                Map.of("missing", List.of(Map.of("item", "repo_writable", "reason", "此部署無法寫入 monorepo")))));

        Resp resp = api.post(adminAs("alice"), tagUrl(ready), tag("v1.0.0"));

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo("route_unsupported_in_deployment");
        assertThat(resp.<String>read("$.details.missing[0].item")).isEqualTo("repo_writable");
        assertThat(bridge().calls.stream().filter(c -> c.path().endsWith(":tag")).count()).as("請求確實送到 Bridge，由它判斷部署能力").isEqualTo(1);
    }

    @Test
    void AT_962_20_1_aPullRequestSendsAckApproverAndBranchAndTheShapeIsTyped() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d201");
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("bodyPreviewAck", true);
        request.put("branch", "feature/issue-0001");

        Resp resp = api.post(adminAs("alice"), prUrl(ready), request);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(lastCall("pr").body()).containsEntry("body_preview_ack", true).containsEntry("branch", "feature/issue-0001").containsEntry("approver", "alice")
                .containsEntry("requested_by", "alice");
        assertThat(resp.<String>read("$.data.delivery.kind")).isEqualTo("PULL_REQUEST");
        assertThat(resp.<Boolean>read("$.data.created")).isTrue();
    }

    @Test
    void AT_962_20_2_aPullRequestForAnExistingBranchIsIdempotentAndReportsCreatedFalse() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d202");
        bridge().next("pr", new Reply(200, Map.of("delivery", Map.of("kind", "PULL_REQUEST", "ref", "7", "status", "CREATED", "created_by", "alice"), "created", false)));

        Resp resp = api.post(adminAs("alice"), prUrl(ready), Map.of("bodyPreviewAck", true));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.created")).isFalse();
        assertThat(resp.<String>read("$.data.delivery.ref")).isEqualTo("7");
    }

    @Test
    void AT_962_20_3_theGithubTokenIsOnlyInThePullRequestBridgeBodyNeverInTagGatesOrAnyResponse() {
        String token = "gh" + "p_" + "AbCdEf0123456789xyZ0";
        assertThat(api.put(admin(), "/api/v1/settings/research/github_token", Map.of("value", token, "confirm", true)).status()).isEqualTo(200);
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d203");

        Resp pr = api.post(adminAs("alice"), prUrl(ready), Map.of("bodyPreviewAck", true));
        Resp tag = api.post(adminAs("alice"), tagUrl(ready), tag("v1.0.0"));
        Resp gate = api.post(adminAs("alice"), RESEARCH + "/projects/" + ready.research() + "/gates", Map.of("gate", "RELEASE_READY", "result", "FAIL", "reason", "x"));

        assertThat(lastCall("pr").body()).containsEntry("github_token", token);
        assertThat(lastCall("tag").body()).doesNotContainKey("github_token");
        assertThat(lastCall("gates").body()).doesNotContainKey("github_token");
        assertThat(pr.body() + tag.body() + gate.body()).doesNotContain(token);
    }

    @Test
    void AT_962_20_4_aContainerModeRefusalOnPrIsRelayedFromTheBridge() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d204");
        bridge().next("pr", Reply.error(422, "route_unsupported_in_deployment", "details", Map.of("missing", List.of(Map.of("item", "gh", "reason", "找不到 gh")))));

        Resp resp = api.post(adminAs("alice"), prUrl(ready), Map.of("bodyPreviewAck", true));

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.details.missing[0].item")).isEqualTo("gh");
    }

    @Test
    void AT_962_20_5_aFailedPushStepIsRelayedAs502WithTheFailureStep() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d205");
        bridge().next("pr", Reply.error(502, "delivery_step_failed", "details", Map.of("failure_step", "GIT_PUSH_BRANCH")));

        Resp resp = api.post(adminAs("alice"), prUrl(ready), Map.of("bodyPreviewAck", true));

        assertThat(resp.status()).isEqualTo(502);
        assertThat(resp.<String>read("$.reason")).isEqualTo("delivery_step_failed");
        assertThat(resp.<String>read("$.details.failure_step")).isEqualTo("GIT_PUSH_BRANCH");
    }

    @Test
    void AT_962_20_6_aRouteThatNeverSucceededIsRelayedAs409FromTheBridge() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d206");
        bridge().next("pr", Reply.error(409, "fsm_state_conflict", "details", Map.of("cause", "route_not_succeeded")));

        Resp resp = api.post(adminAs("alice"), prUrl(ready), Map.of("bodyPreviewAck", true));

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.details.cause")).isEqualTo("route_not_succeeded");
    }

    @Test
    void AT_962_20_7_aSlowBridgeOnPrIs504AndNothingIsWrittenByConsoleApi() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d207");
        long before = tableRows();
        readTimeout.cap(java.time.Duration.ofSeconds(1));
        bridge().delayMillis = 3000;

        Resp resp = api.post(adminAs("alice"), prUrl(ready), Map.of("bodyPreviewAck", true));

        assertThat(resp.status()).isEqualTo(504);
        assertThat(tableRows()).isEqualTo(before);
    }

    @Test
    void AT_962_22_4_aGatesRequestIsAuditedWithTheSameTraceIdTheBridgeReceived() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d224");
        long before = rows("audit_log");

        Resp resp = api.post(adminAs("alice"), RESEARCH + "/projects/" + ready.research() + "/gates",
                Map.of("gate", "RELEASE_READY", "result", "FAIL", "reason", "回歸未過"));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(rows("audit_log")).isGreaterThan(before);
        assertThat(jdbc.queryForList("select trace_id from console.audit_log where path like ? and method = 'POST'", String.class, "%" + ready.research() + "/gates"))
                .containsExactly(lastCall("gates").traceId());
    }

    @Test
    void AT_962_22_E_1_aFailedTagLeavesNoDeliveryRowButStillExactlyOneAuditRow() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d22e1");
        bridge().next("tag", Reply.error(502, "delivery_step_failed", "details", Map.of("failure_step", "GIT_TAG")));
        long auditBefore = rows("audit_log");

        Resp resp = api.post(adminAs("alice"), tagUrl(ready), tag("v1.0.0"));

        assertThat(resp.status()).isEqualTo(502);
        assertThat(jdbc.queryForObject("select count(*) from console.research_deliveries where research_id = ?", Long.class, ready.research())).isZero();
        assertThat(rows("audit_log")).isEqualTo(auditBefore + 1);
    }

    @Test
    void AT_962_22_E_2_resendingTheSameTagMakesConsoleApiWriteNoDeliveryRowsTwiceBecauseBridgeOwnsTheRows() {
        ResearchP2Fixtures.Ready ready = p2().releaseReady("d22e2");

        assertThat(api.post(adminAs("alice"), tagUrl(ready), tag("v1.0.0")).status()).isEqualTo(201);
        assertThat(api.post(adminAs("alice"), tagUrl(ready), tag("v1.0.0")).status()).isEqualTo(201);

        assertThat(jdbc.queryForObject("select count(*) from console.research_deliveries where research_id = ?", Long.class, ready.research()))
                .as("console-api 零寫入（迷你 Bridge 也不寫交付列；重送冪等由 V21 的唯一約束與 Bridge 守）").isZero();
    }
}
