package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.ResearchP1Fixtures;
import com.aisdlc.minibridge.MiniResearch.Reply;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 規格變更請求端點（API-RP-15；AT-961-15-1）。為什麼重要：SCR 是「規格變了、內環要跟著變」的唯一入口——輸入閘擋掉壞請求（零 Bridge 請求）、發起前先停進行中的 run
 * （否則內環一邊改規格一邊還在跑舊規格）、Bridge 的上限與狀態衝突逐字透傳，使用者才知道該做什麼。
 */
class ResearchScrApiIT extends AbstractResearchIT {

    private static Map<String, Object> body(String kind, String source, String reason) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("kind", kind);
        body.put("sourceKind", source);
        body.put("reason", reason);
        body.put("reasonClass", "AC 模糊");
        body.put("affectedSections", List.of("§5 AC"));
        return body;
    }

    private String url(UUID id) {
        return RESEARCH + "/projects/" + id + "/scr";
    }

    @Test
    void AT_961_15_1_openScrGatesTheInputPassesBridgeAnswersThroughAndListsInScrNoOrder() {
        ResearchP1Fixtures p1 = new ResearchP1Fixtures(jdbc);
        UUID id = p1.project("scr1", "UNDECIDED");

        Resp minor = api.post(operator(), url(id), body("MINOR", "HUMAN", "AC-3 描述模糊"));
        assertThat(minor.status()).isEqualTo(202);
        assertThat(minor.<Integer>read("$.data.scrNo")).isEqualTo(1);
        assertThat(minor.<String>read("$.data.status")).isEqualTo("OPEN");
        Map<String, Object> sent = bridge().calls.stream().filter(c -> c.path().endsWith(":scr")).findFirst().orElseThrow().body();
        assertThat(sent).containsEntry("kind", "MINOR").containsEntry("source_kind", "HUMAN").containsEntry("reason_class", "AC_VAGUE")
                .containsEntry("requested_by", "operator").containsKey("affected_sections");

        long calls = bridge().calls.size();
        assertThat(api.post(operator(), url(id), body("MEDIUM", "HUMAN", "x")).status()).isEqualTo(400);
        assertThat(api.post(operator(), url(id), body("MINOR", "OTHER", "x")).status()).isEqualTo(400);
        assertThat(api.post(operator(), url(id), body("MINOR", "HUMAN", "字".repeat(501))).status()).isEqualTo(400);
        Map<String, Object> blank = body("MINOR", "HUMAN", "x");
        blank.put("affectedSections", List.of(""));
        Resp rejected = api.post(operator(), url(id), blank);
        assertThat(rejected.status()).isEqualTo(400);
        assertThat(rejected.errorFields()).isNotEmpty();
        assertThat(bridge().calls.size()).as("輸入閘：零 Bridge 請求").isEqualTo((int) calls);
        assertThat(api.post(viewer(), url(id), body("MINOR", "HUMAN", "x")).status()).isEqualTo(403);

        Resp major = api.post(operator(), url(id), body("MAJOR", "REVIEW_FINDING", "需求大改"));
        assertThat(major.status()).isEqualTo(202);
        assertThat(major.<String>read("$.data.successorResearchId")).isNotBlank();
        Resp healing = api.post(operator(), url(id), body("MINOR", "HEALING_FAILED", "自癒耗盡"));
        assertThat(healing.<String>read("$.data.recovery.target")).isEqualTo("SPEC_DRAFTING");
        assertThat(healing.has("$.data.recovery.powershell")).isTrue();

        Resp list = api.get(viewer(), url(id));
        assertThat(list.status()).isEqualTo(200);
        assertThat(list.<List<Integer>>read("$.data[*].scrNo")).containsExactly(1, 2);
        assertThat(list.<String>read("$.data[0].reasonClass")).isEqualTo("AC_VAGUE");
        assertThat(list.has("$.data[0].implFsmActions")).isTrue();

        bridge().next("scr", Reply.error(409, "scr_open", "details", Map.of("scr_no", 1)));
        Resp open = api.post(operator(), url(id), body("MINOR", "HUMAN", "再來一次"));
        assertThat(open.status()).isEqualTo(409);
        assertThat(open.<String>read("$.reason")).isEqualTo("scr_open");
        bridge().next("scr", Reply.error(409, "scr_limit"));
        assertThat(api.post(operator(), url(id), body("MINOR", "HUMAN", "第三次")).<String>read("$.reason")).isEqualTo("scr_limit");
        bridge().next("scr", Reply.error(422, "invalid_request", "violations", List.of(Map.of("field", "reason", "rule", "x", "message", "m"))));
        assertThat(api.post(operator(), url(id), body("MINOR", "HUMAN", "壞")).status()).isEqualTo(422);
    }

    @Test
    void AT_961_15_1_applyIsAdminOnlyAndForwardsTheScrNoWithTheJwtSubjectAsApprover() {
        UUID id = new ResearchP1Fixtures(jdbc).project("scr2", "UNDECIDED");
        String apply = RESEARCH + "/projects/" + id + "/scr/1/apply";

        assertThat(api.post(operator(), apply, Map.of()).status()).isEqualTo(403);
        assertThat(api.post(viewer(), apply, Map.of()).status()).isEqualTo(403);
        assertThat(bridge().calls).isEmpty();
        Resp ok = api.post(adminAs("alice"), apply, Map.of());
        assertThat(ok.status()).isEqualTo(200);
        assertThat(ok.<String>read("$.data.status")).isEqualTo("APPLIED");
        assertThat(bridge().lastCall().body()).containsEntry("scr_no", 1).containsEntry("approver", "alice");
        assertThat(api.post(admin(), RESEARCH + "/projects/" + id + "/scr/0/apply", Map.of()).status()).isEqualTo(400);
    }
}
