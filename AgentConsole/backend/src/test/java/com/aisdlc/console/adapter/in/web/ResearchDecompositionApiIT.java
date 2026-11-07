package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.model.auth.Role;
import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.ResearchP1Fixtures;
import com.aisdlc.minibridge.MiniResearch.Reply;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 拆解簽核與執行閘（AC-961-11；AT-961-15-2）。為什麼重要：簽核是人工硬閘的研究版——覆蓋沒清零不能簽、簽了才落成正式目標任務；之後內環 run 的啟動必須被「SCR 開啟、拆解過期、
 * TCS 未凍結」三道守衛二次校驗（前端停用按鈕只是體驗），而且非研究專案完全不受影響。
 */
class ResearchDecompositionApiIT extends AbstractResearchIT {

    private static final String SHA = "a".repeat(64);
    private static final String OTHER_SHA = "d".repeat(64);

    private ResearchP1Fixtures p1;

    private String url(UUID id, String suffix) {
        return RESEARCH + "/projects/" + id + suffix;
    }

    /** 研究專案（已過 Gate 0，凍結 PRD 摘要＝SHA）與其綁定的 Console 專案（草案：未簽核）。 */
    private record Rig(UUID research, String project) {
    }

    private Rig rig(String slug) {
        p1 = new ResearchP1Fixtures(jdbc);
        UUID research = p1.project(slug, "UNDECIDED");
        fx.decision(research, "GATE0", "APPROVED", "research-" + slug, "Gate-0", "{\"01_specs/PRD-v1.0.0.md\":\"sha256:" + SHA + "\"}");
        String project = createProject(Map.of("name", "p1-" + slug, "executionPath", "/work/p1-" + slug, "passCriteria", "- 全部通過", "draft", true));
        p1.bind(research, UUID.fromString(project));
        return new Rig(research, project);
    }

    /** 已簽核專案（含已簽核的目標與任務）綁研究專案，供執行守衛案例使用。 */
    private Rig signedRig(String slug) {
        p1 = new ResearchP1Fixtures(jdbc);
        UUID research = p1.project(slug, "UNDECIDED");
        fx.decision(research, "GATE0", "APPROVED", "research-" + slug, "Gate-0", "{\"01_specs/PRD-v1.0.0.md\":\"sha256:" + SHA + "\"}");
        Fixture fixture = prjA("p1g-" + slug, 3);
        p1.bind(research, UUID.fromString(fixture.projectId()));
        return new Rig(research, fixture.projectId());
    }

    private void stage2(String projectName, boolean frozen) {
        Map<String, Object> state = new LinkedHashMap<>();
        state.put("project", projectName);
        state.put("current_state", frozen ? "SPEC_FROZEN" : "SPEC_DRAFTING");
        state.put("frozen_stages", frozen ? List.of(Map.of("stage", "Stage-1"), Map.of("stage", "Stage-2")) : List.of(Map.of("stage", "Stage-1")));
        state.put("source", "FSM-STATE-" + projectName + ".yaml");
        state.put("fsm_project", projectName);
        MINI.sdd.states.put(projectName, state);
    }

    private static String full() {
        return ResearchP1Fixtures.content(SHA, "[]", 2, 2);
    }

    // ── AT-961-11-1／11-2 ────────────────────────────────────────────────────────────────

    @Test
    void AT_961_11_1_signoffGoesThroughTheExistingImportPathAndLandsGoalsAndTasksOrIsRefusedWhenCoverageIsOpen() {
        Rig ok = rig("d11-1");
        UUID decomposition = p1.decomposition(ok.research, "DRAFTED", SHA, full());

        Resp resp = api.post(operator(), url(ok.research, "/decomposition/signoff"), Map.of());

        assertThat(resp.status()).as(resp.body()).isEqualTo(200);
        assertThat(jdbc.queryForObject("select count(*) from console.goals where project_id = ?::uuid", Long.class, ok.project)).isEqualTo(1L);
        assertThat(jdbc.queryForObject("select count(*) from console.tasks t join console.goals g on g.id = t.goal_id where g.project_id = ?::uuid", Long.class, ok.project))
                .isEqualTo(2L);
        assertThat(jdbc.queryForObject("select signed_off from console.projects where id = ?::uuid", Boolean.class, ok.project)).isTrue();
        assertThat(jdbc.queryForObject("select signed_off_by from console.projects where id = ?::uuid", String.class, ok.project)).isEqualTo("operator");
        assertThat(jdbc.queryForObject("select count(*) from console.tasks t join console.goals g on g.id = t.goal_id where g.project_id = ?::uuid and t.signed_off", Long.class,
                ok.project)).isEqualTo(2L);
        Map<String, Object> sent = bridge().calls.stream().filter(c -> c.path().endsWith(":decomposition-signoff")).findFirst().orElseThrow().body();
        assertThat(sent).containsEntry("decomposition_id", decomposition.toString()).containsEntry("console_project_id", ok.project).containsEntry("approver", "operator")
                .containsKey("import_record_id");
        // D-143(3)／F-02：簽核本文帶 imported_tasks_count，值＝匯入落成的正式 tasks 數（同一專案 DB 實數 2）
        assertThat(sent.get("imported_tasks_count")).as("imported_tasks_count 必須是整數").isInstanceOf(Integer.class).isEqualTo(2);
        assertThat(jdbc.queryForObject("select status from console.research_decompositions where id = ?", String.class, decomposition)).isEqualTo("SIGNED_OFF");
        assertThat(resp.<String>read("$.data.status")).isEqualTo("SIGNED_OFF");

        Rig open = rig("d11-1b");
        p1.decomposition(open.research, "DRAFTED", SHA, ResearchP1Fixtures.content(SHA, "[\"AC-001-3\"]", 3, 2));
        Resp refused = api.post(operator(), url(open.research, "/decomposition/signoff"), Map.of());
        assertThat(refused.status()).isEqualTo(422);
        assertThat(refused.<String>read("$.reason")).isEqualTo("invalid_request");
        assertThat(refused.<String>read("$.details.violations[0].rule")).isEqualTo("uncovered_ac");
        assertThat(refused.body()).contains("AC-001-3");
        assertThat(jdbc.queryForObject("select count(*) from console.goals where project_id = ?::uuid", Long.class, open.project)).isZero();
        assertThat(bridge().calls.stream().filter(c -> c.path().endsWith(":decomposition-signoff")).count()).as("零簽核請求（只有先前那一次）").isEqualTo(1L);

        Resp waived = api.post(operator(), url(open.research, "/decomposition/signoff"),
                Map.of("waivers", List.of(Map.of("ac", "AC-001-3", "reason", "本期不做，已由掌舵者同意"))));
        assertThat(waived.status()).as(waived.body()).isEqualTo(200);
    }

    @Test
    void AT_961_11_2_signoffRolesAndApproverComeFromTheJwtSubjectOnly() {
        Rig rig = rig("d11-2");
        p1.decomposition(rig.research, "DRAFTED", SHA, full());
        String path = url(rig.research, "/decomposition/signoff");

        assertThat(api.post(viewer(), path, Map.of()).status()).isEqualTo(403);
        assertThat(api.post(null, path, Map.of()).status()).isEqualTo(401);
        Resp noSubject = api.post(jwt.issue("", Role.OPERATOR).accessToken(), path, Map.of());
        assertThat(noSubject.status()).as("空 subject：安全層先把它當未認證（401）；服務層另有 400 的最後一道網（TCS 勘誤候選）").isIn(400, 401);
        assertThat(bridge().calls).as("被拒者零 Bridge 請求").isEmpty();
        assertThat(rows("goals")).isZero();

        Resp admin = api.post(admin(), path, Map.of("approver", "mallory"));
        assertThat(admin.status()).as(admin.body()).isEqualTo(200);
        assertThat(jdbc.queryForObject("select signed_off_by from console.projects where id = ?::uuid", String.class, rig.project)).isEqualTo("admin");
        assertThat(bridge().lastCall().body()).containsEntry("approver", "admin");
    }

    // ── 執行守衛 AT-961-11-3～6、E-2 ─────────────────────────────────────────────────────

    @Test
    void AT_961_11_3_anUnsignedDraftOfAResearchBoundProjectIsStillRefusedWithTheExistingReason() {
        Rig rig = signedRig("d11-3");
        jdbc.update("update console.projects set signed_off = false where id = ?::uuid", rig.project);

        Resp resp = execute(rig.project, Map.of());

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.body()).contains("未經人工審批的草案不可執行");
        assertThat(countRuns(rig.project)).isZero();
    }

    @Test
    void AT_961_11_4_aStaleDecompositionRefusesExecutionAndAFreshSignedOneLetsItThrough() {
        Rig rig = signedRig("d11-4");
        p1.decomposition(rig.research, "SIGNED_OFF", OTHER_SHA, ResearchP1Fixtures.content(OTHER_SHA, "[]", 2, 2));
        stage2("p1g-d11-4", true);

        Resp stale = execute(rig.project, Map.of());

        assertThat(stale.status()).isEqualTo(409);
        assertThat(stale.<String>read("$.reason")).isEqualTo("decomposition_stale");
        assertThat(stale.<String>read("$.details.expected_sha256")).isEqualTo(SHA);
        assertThat(stale.<String>read("$.details.actual_sha256")).isEqualTo(OTHER_SHA);
        assertThat(countRuns(rig.project)).isZero();

        p1.decomposition(rig.research, "SIGNED_OFF", SHA, ResearchP1Fixtures.content(SHA, "[]", 2, 2));
        assertThat(execute(rig.project, Map.of()).status()).as("重新拆解並簽核後放行").isEqualTo(201);
    }

    @Test
    void AT_961_11_4_aDecompositionInStatusStaleRefusesExecutionEvenWhenItsShaStillMatchesTheFrozenOne() {
        Rig rig = signedRig("d11-4s");
        stage2("p1g-d11-4s", true);
        // 摘要與凍結摘要相同：只剩「狀態 STALE」這一條成因（F-12：STALE_STATUSES 去掉 "STALE" 必紅）
        p1.decomposition(rig.research, "STALE", SHA, ResearchP1Fixtures.content(SHA, "[]", 2, 2));
        int before = bridge().calls.size();

        Resp stale = execute(rig.project, Map.of());

        assertThat(stale.status()).isEqualTo(409);
        assertThat(stale.<String>read("$.reason")).isEqualTo("decomposition_stale");
        assertThat(countRuns(rig.project)).isZero();
        assertThat(bridge().calls.size()).as("守衛在 FSM 查詢之前拒絕：Bridge 零新請求").isEqualTo(before);

        p1.decomposition(rig.research, "SIGNED_OFF", SHA, ResearchP1Fixtures.content(SHA, "[]", 2, 2));
        assertThat(execute(rig.project, Map.of()).status()).as("對照：SIGNED_OFF 放行").isEqualTo(201);
    }

    @Test
    void AT_961_11_5_anOpenScrRefusesExecutionAndItsEndLetsItThrough() {
        Rig rig = signedRig("d11-5");
        stage2("p1g-d11-5", true);
        p1.scr(rig.research, 1, "MINOR", "OPEN");

        Resp refused = execute(rig.project, Map.of());

        assertThat(refused.status()).isEqualTo(409);
        assertThat(refused.<String>read("$.reason")).isEqualTo("scr_open");
        assertThat(countRuns(rig.project)).isZero();
        jdbc.update("update console.research_scr set status = 'APPLIED' where research_id = ?", rig.research);
        assertThat(execute(rig.project, Map.of()).status()).isEqualTo(201);
    }

    @Test
    void AT_961_11_6_executionIsRefusedUntilTheInnerKeyHasFrozenStageTwoAndTheOrderIsScrThenStaleThenFsm() {
        Rig rig = signedRig("d11-6");
        stage2("p1g-d11-6", false);

        Resp unfrozen = execute(rig.project, Map.of());
        assertThat(unfrozen.status()).isEqualTo(409);
        assertThat(unfrozen.<String>read("$.reason")).isEqualTo("fsm_state_conflict");
        assertThat(unfrozen.<String>read("$.details.current_state")).isEqualTo("SPEC_DRAFTING");
        assertThat(countRuns(rig.project)).isZero();

        p1.scr(rig.research, 1, "MINOR", "OPEN");
        p1.decomposition(rig.research, "SIGNED_OFF", OTHER_SHA, ResearchP1Fixtures.content(OTHER_SHA, "[]", 2, 2));
        assertThat(execute(rig.project, Map.of()).<String>read("$.reason")).as("先中者定案：scr_open 先於 decomposition_stale 與 fsm_state_conflict").isEqualTo("scr_open");
        jdbc.update("update console.research_scr set status = 'REJECTED' where research_id = ?", rig.research);
        assertThat(execute(rig.project, Map.of()).<String>read("$.reason")).isEqualTo("decomposition_stale");

        stage2("p1g-d11-6", true);
        p1.decomposition(rig.research, "SIGNED_OFF", SHA, ResearchP1Fixtures.content(SHA, "[]", 2, 2));
        assertThat(execute(rig.project, Map.of()).status()).isEqualTo(201);
    }

    @Test
    void AT_961_11_E_2_aNonResearchProjectIsCompletelyUnaffectedByTheGuard() {
        Fixture fixture = prjA("plain-project", 3);

        Resp resp = execute(fixture.projectId(), Map.of());

        assertThat(resp.status()).isEqualTo(201);
        assertThat(bridge().calls).as("非研究專案：研究 Bridge 零請求").isEmpty();
    }

    // ── AT-961-11-7 ──────────────────────────────────────────────────────────────────────

    @Test
    void AT_961_11_7_triggerIsOperatorUpAndStructuredBridgeErrorsPassThroughWithoutRetry() {
        UUID id = new ResearchP1Fixtures(jdbc).project("d11-7", "UNDECIDED");
        String path = url(id, "/decomposition");

        Resp ok = api.post(operator(), path, Map.of());
        assertThat(ok.status()).isEqualTo(200);
        assertThat(ok.<String>read("$.data.status")).isEqualTo("DRAFTED");
        assertThat(ok.has("$.data.decompositionId")).isTrue();
        assertThat(ok.has("$.data.coverage.uncovered")).isTrue();
        assertThat(api.post(viewer(), path, Map.of()).status()).isEqualTo(403);
        assertThat(api.post(null, path, Map.of()).status()).isEqualTo(401);

        bridge().calls.clear();
        bridge().next("decompose", Reply.error(422, "invalid_request", "violations", List.of(Map.of("field", "goals", "rule", "max_steps", "message", "步驟過多"))));
        Resp gate = api.post(operator(), path, Map.of());
        assertThat(gate.status()).isEqualTo(422);
        assertThat(gate.<String>read("$.details.violations[0].rule")).isEqualTo("max_steps");
        bridge().next("decompose", Reply.error(409, "scr_open"));
        assertThat(api.post(operator(), path, Map.of()).<String>read("$.reason")).isEqualTo("scr_open");
        assertThat(bridge().calls.stream().filter(c -> c.path().endsWith(":decompose")).count()).as("每個 POST 恰一次").isEqualTo(2L);
        assertThat(Duration.ofSeconds(330)).isGreaterThan(Duration.ofSeconds(300));
    }

    // ── AT-961-15-2 ──────────────────────────────────────────────────────────────────────

    @Test
    void AT_961_15_2_getDecompositionReturnsTheEffectiveOneWithCoverageWaiversAndStaleOrNull() {
        Rig a = rig("d15-2a");
        p1.decomposition(a.research, "SIGNED_OFF", SHA, ResearchP1Fixtures.content(SHA, "[\"AC-001-3\"]", 3, 2).replace("\"waivers\":[]",
                "\"waivers\":[{\"ac\":\"AC-001-3\",\"reason\":\"豁免\",\"by\":\"operator\"}]"));
        Rig b = rig("d15-2b");
        p1.decomposition(b.research, "STALE", OTHER_SHA, full());
        UUID none = new ResearchP1Fixtures(jdbc).project("d15-2c", "UNDECIDED");

        Resp valid = api.get(viewer(), url(a.research, "/decomposition"));
        assertThat(valid.status()).isEqualTo(200);
        assertThat(valid.<String>read("$.data.status")).isEqualTo("SIGNED_OFF");
        assertThat(valid.<Boolean>read("$.data.stale")).isFalse();
        assertThat(valid.<Integer>read("$.data.coverage.total")).isEqualTo(3);
        assertThat(valid.<List<String>>read("$.data.coverage.uncovered")).containsExactly("AC-001-3");
        assertThat(valid.<String>read("$.data.waivers[0].ac")).isEqualTo("AC-001-3");
        assertThat(valid.<String>read("$.data.goals[0].tasks[0].taskId")).isEqualTo("T-1");
        assertThat(valid.<String>read("$.data.prdSha256")).isEqualTo(SHA);
        Resp stale = api.get(viewer(), url(b.research, "/decomposition"));
        assertThat(stale.<Boolean>read("$.data.stale")).isTrue();
        Resp empty = api.get(viewer(), url(none, "/decomposition"));
        assertThat(empty.status()).isEqualTo(200);
        assertThat(empty.<Object>read("$.data")).isNull();
    }

    @Test
    void AT_961_11_idempotent_aRetryAfterABridgeSignoffFailureReusesTheImportRecordAndDoesNotDuplicateGoalsOrTasks() {
        Rig rig = rig("d11-idem");
        UUID decomposition = p1.decomposition(rig.research, "DRAFTED", SHA, full());
        String path = url(rig.research, "/decomposition/signoff");
        String name = "research-decomposition:" + decomposition;
        bridge().next("decomposition-signoff", Reply.error(502, "bridge_broke"));

        Resp failed = api.post(operator(), path, Map.of());

        assertThat(failed.status()).as("匯入已落庫、Bridge 簽核失敗").isEqualTo(502);
        assertThat(jdbc.queryForObject("select count(*) from console.import_records where source_file_name = ?", Long.class, name)).isEqualTo(1L);
        assertThat(jdbc.queryForObject("select count(*) from console.tasks t join console.goals g on g.id = t.goal_id where g.project_id = ?::uuid", Long.class, rig.project))
                .isEqualTo(2L);
        assertThat(jdbc.queryForObject("select status from console.research_decompositions where id = ?", String.class, decomposition)).isEqualTo("DRAFTED");

        Resp retried = api.post(operator(), path, Map.of());

        assertThat(retried.status()).as(retried.body()).isEqualTo(200);
        assertThat(jdbc.queryForObject("select count(*) from console.import_records where source_file_name = ?", Long.class, name)).as("匯入記錄數不增").isEqualTo(1L);
        assertThat(jdbc.queryForObject("select count(*) from console.goals where project_id = ?::uuid", Long.class, rig.project)).isEqualTo(1L);
        assertThat(jdbc.queryForObject("select count(*) from console.tasks t join console.goals g on g.id = t.goal_id where g.project_id = ?::uuid", Long.class, rig.project))
                .as("目標任務數不增").isEqualTo(2L);
        assertThat(jdbc.queryForObject("select status from console.research_decompositions where id = ?", String.class, decomposition)).isEqualTo("SIGNED_OFF");
        assertThat(jdbc.queryForObject("select import_record_id is not null from console.research_decompositions where id = ?", Boolean.class, decomposition)).isTrue();
    }
}
