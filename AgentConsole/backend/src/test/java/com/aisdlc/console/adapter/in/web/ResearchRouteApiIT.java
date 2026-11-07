package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.ResearchP1Fixtures;
import com.aisdlc.minibridge.MiniResearch.Call;
import com.aisdlc.minibridge.MiniResearch.Reply;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 分流端點（API-RP-14；TCS-ResearchToPRD-P1 AC-961-14、AT-961-15-E-1、AT-961-16-4、AT-961-11-E-1）。為什麼重要：確認分流會建 Console 專案列、同步呼叫 Bridge 最長 300 秒、失敗要補償到
 * 安全態——順序（先建後呼）、補償（ARCHIVED、稽核、通知 Bridge、不清理）與機密（GitHub token 只在單次請求、不落地）任一錯了，使用者不是留下孤兒專案，就是外洩憑證。
 */
class ResearchRouteApiIT extends AbstractResearchIT {


    private ResearchP1Fixtures p1;

    @org.junit.jupiter.api.BeforeEach
    void p1() {
        p1 = new ResearchP1Fixtures(jdbc);
    }

    private static Map<String, Object> trackA() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("track", "A");
        body.put("targetModule", "agentconsole");
        return body;
    }

    private static Map<String, Object> trackB(String name) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("track", "B");
        body.put("projectName", name);
        body.put("stackTemplate", "python-fastapi");
        body.put("repoName", name);
        body.put("owner", "acme");
        body.put("createGithub", false);
        return body;
    }

    private String url(UUID id, String suffix) {
        return RESEARCH + "/projects/" + id + suffix;
    }

    private Map<String, Long> tableCounts() {
        Map<String, Long> out = new LinkedHashMap<>();
        for (String table : List.of("projects", "research_projects", "research_route_decisions", "research_route_steps", "research_scr", "research_decompositions",
                "research_artifacts", "research_events")) {
            out.put(table, rows(table));
        }
        return out;
    }

    private String countRouteCalls(String verb) {
        return String.valueOf(bridge().calls.stream().filter(c -> c.path().endsWith(":" + verb)).count());
    }

    // ── AT-961-14-1 ──────────────────────────────────────────────────────────────────────

    @Test
    void AT_961_14_1_previewIsOperatorUpGatesBeforeTheBridgePassesMissingItemsThroughAndWritesNothing() {
        UUID id = p1.project("r14-1", "UNDECIDED");
        Map<String, Long> before = tableCounts();

        Resp ok = api.post(operator(), url(id, "/route/preview"), trackA());

        assertThat(ok.status()).isEqualTo(200);
        assertThat(ok.<String>read("$.data.executionPath")).startsWith("/e2e/route/");
        assertThat(ok.<String>read("$.data.implFsmProject")).isEqualTo("agentconsole-r14-1");
        assertThat(ok.<String>read("$.data.actions[0].action")).isEqualTo("validate_target");
        assertThat(ok.<Boolean>read("$.data.actions[0].touchesExternal")).isFalse();
        assertThat(ok.has("$.data.expectedTrackedFiles")).isTrue();
        assertThat(ok.has("$.data.warnings")).isTrue();
        assertThat(ok.has("$.data.prd")).isTrue();
        assertThat(tableCounts()).as("預演零寫入（D-108）").isEqualTo(before);

        long calls = bridge().calls.size();
        List<Map<String, Object>> bad = new ArrayList<>();
        Map<String, Object> branch = trackA();
        branch.put("branchName", "feature/Bad");
        bad.add(branch);
        Map<String, Object> repo = trackB("demo-app");
        repo.put("repoName", "x");
        bad.add(repo);
        Map<String, Object> visibility = trackB("demo-app");
        visibility.put("visibility", "INTERNAL");
        bad.add(visibility);
        Map<String, Object> reason = trackA();
        reason.put("scopeDiffersReason", "字".repeat(201));
        bad.add(reason);
        for (Map<String, Object> body : bad) {
            Resp resp = api.post(operator(), url(id, "/route/preview"), body);
            assertThat(resp.status()).as(body.toString()).isEqualTo(400);
            assertThat(resp.<String>read("$.reason")).isEqualTo("invalid_request");
            assertThat(resp.errorFields()).isNotEmpty();
        }
        assertThat(bridge().calls.size()).as("輸入閘先於 Bridge：零請求").isEqualTo((int) calls);

        assertThat(api.post(viewer(), url(id, "/route/preview"), trackA()).status()).isEqualTo(403);
        assertThat(api.post(null, url(id, "/route/preview"), trackA()).status()).isEqualTo(401);

        bridge().next("route-preview", Reply.error(422, "route_unsupported_in_deployment", "details",
                Map.of("missing", List.of(Map.of("item", "gh", "reason", "找不到 gh")))));
        Resp missing = api.post(operator(), url(id, "/route/preview"), trackA());
        assertThat(missing.status()).isEqualTo(422);
        assertThat(missing.<String>read("$.reason")).isEqualTo("route_unsupported_in_deployment");
        assertThat(missing.<String>read("$.details.missing[0].item")).isEqualTo("gh");
    }

    // ── AT-961-14-2 ──────────────────────────────────────────────────────────────────────

    @Test
    void AT_961_14_2_confirmIsAdminOnlyAndARejectedCallTouchesNeitherTheBridgeNorProjects() {
        UUID id = p1.project("r14-2", "UNDECIDED");
        long projectsBefore = rows("projects");

        assertThat(api.post(operator(), url(id, "/route"), trackA()).status()).isEqualTo(403);
        assertThat(api.post(viewer(), url(id, "/route"), trackA()).status()).isEqualTo(403);
        assertThat(api.post(null, url(id, "/route"), trackA()).status()).isEqualTo(401);

        assertThat(bridge().calls).isEmpty();
        assertThat(rows("projects")).isEqualTo(projectsBefore);
        assertThat(rows("research_route_decisions")).isZero();
        assertThat(api.post(admin(), url(id, "/route"), trackA()).status()).isEqualTo(200);
    }

    // ── AT-961-14-3、11-E-1 ──────────────────────────────────────────────────────────────

    @Test
    void AT_961_14_3_theProjectRowExistsBeforeTheBridgeRouteCallAndARebindOfTheSamePathAndKeyIsRefused() {
        UUID id = p1.project("r14-3", "UNDECIDED");
        AtomicReference<Map<String, Object>> seen = new AtomicReference<>();
        bridge().onRoute = body -> {
            Map<String, Object> row = jdbc.queryForMap("select execution_path, sdd_project, signed_off, status from console.projects where id = ?::uuid",
                    String.valueOf(body.get("console_project_id")));
            seen.set(row);
        };

        Resp ok = api.post(admin(), url(id, "/route"), trackB("demo-app"));

        assertThat(ok.status()).isEqualTo(200);
        assertThat(seen.get()).as("收到 :route 時 projects 列已存在").containsEntry("execution_path", "/e2e/route/demo-app")
                .containsEntry("sdd_project", "demo-app").containsEntry("signed_off", false).containsEntry("status", "DRAFT");
        assertThat(ok.<String>read("$.data.status")).isEqualTo("SUCCEEDED");
        assertThat(ok.has("$.data.publishedDocs")).isTrue();
        assertThat(ok.<String>read("$.data.consoleProjectId")).isNotBlank();
        Map<String, Object> request = bridge().calls.stream().filter(c -> c.path().endsWith(":route")).findFirst().orElseThrow().body();
        assertThat(request).containsKey("console_project_id").containsEntry("approver", "admin");

        UUID other = p1.project("r14-3b", "UNDECIDED");
        long projects = rows("projects");
        long routeCalls = bridge().calls.stream().filter(c -> c.path().endsWith(":route")).count();
        Resp conflict = api.post(admin(), url(other, "/route"), trackB("demo-app"));
        assertThat(conflict.status()).isEqualTo(409);
        assertThat(rows("projects")).as("重綁被拒：未新增 projects 列").isEqualTo(projects);
        assertThat(bridge().calls.stream().filter(c -> c.path().endsWith(":route")).count()).as("衝突時 :route 請求數不增").isEqualTo(routeCalls);
    }

    @Test
    void AT_961_11_E_1_anExecutionPathThatFailsTheSafetyCheckIsRefusedBeforeAnyProjectRowIsWritten() {
        UUID id = p1.project("r11-e1", "UNDECIDED");
        bridge().executionPathOverride = "relative/not-absolute";
        long projects = rows("projects");

        Resp resp = api.post(admin(), url(id, "/route"), trackB("demo-app"));

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo("sanitization_failed");
        assertThat(rows("projects")).isEqualTo(projects);
        assertThat(countRouteCalls("route")).isEqualTo("0");

        bridge().executionPathOverride = null;
        assertThat(api.post(admin(), url(id, "/route"), trackB("demo-app")).status()).isEqualTo(200);
    }

    // ── AT-961-14-4 ──────────────────────────────────────────────────────────────────────

    @Test
    void AT_961_14_4_aFailedRouteCompensatesTheProjectToArchivedAuditsItNotifiesTheBridgeAndCleansNothing() {
        UUID id = p1.project("r14-4", "UNDECIDED");
        UUID routeId = UUID.randomUUID();
        bridge().onRoute = body -> p1.route(routeId, id, "FAILED", UUID.fromString(String.valueOf(body.get("console_project_id"))));
        bridge().next("route", Reply.error(502, "route_step_failed", "details", Map.of("route_id", routeId.toString(), "failure_step", "GIT_SWITCH")));

        Resp failed = api.post(admin(), url(id, "/route"), trackB("demo-app"));

        assertThat(failed.status()).isEqualTo(502);
        assertThat(failed.<String>read("$.reason")).isEqualTo("route_step_failed");
        assertThat(failed.<String>read("$.details.failure_step")).isEqualTo("GIT_SWITCH");
        assertThat(jdbc.queryForList("select status from console.projects where execution_path = '/e2e/route/demo-app'", String.class)).containsExactly("ARCHIVED");
        assertThat(jdbc.queryForObject("select status from console.research_route_decisions where id = ?", String.class, routeId)).isEqualTo("COMPENSATED");
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log where entity_type = 'project' and path like '%/route' and http_status = 502", Long.class))
                .as("補償的稽核標註").isGreaterThanOrEqualTo(1L);
        List<String> writes = bridge().calls.stream().filter(c -> !"GET".equals(c.method())).map(Call::path).map(p -> p.substring(p.indexOf(':'))).toList();
        assertThat(writes).as("只有預演、確認與補償通知，沒有清理類請求").containsExactly(":route-preview", ":route", ":route-compensated");
    }

    @Test
    void AT_961_14_4_aTimeoutWhileTheBridgeStillRunsArchivesTheProjectAndTheBridgeRefusesTheCompensationWithoutHidingIt() {
        UUID id = p1.project("r14-4t", "UNDECIDED");
        UUID routeId = UUID.randomUUID();
        bridge().onRoute = body -> p1.route(routeId, id, "RUNNING", UUID.fromString(String.valueOf(body.get("console_project_id"))));
        bridge().routeDelayMillis = 3000;
        readTimeout.cap(Duration.ofSeconds(1));

        Resp timedOut = api.post(admin(), url(id, "/route"), trackB("demo-app"));

        assertThat(timedOut.status()).isEqualTo(504);
        assertThat(timedOut.<String>read("$.reason")).isEqualTo("bridge_timeout");
        assertThat(jdbc.queryForList("select status from console.projects where execution_path = '/e2e/route/demo-app'", String.class)).containsExactly("ARCHIVED");
        assertThat(jdbc.queryForObject("select status from console.research_route_decisions where id = ?", String.class, routeId))
                .as("Bridge 驗該列非 FAILED＝409，狀態不被改").isEqualTo("RUNNING");
        assertThat(countRouteCalls("route-compensated")).isEqualTo("1");
        assertThat(countRouteCalls("route")).as("POST 不重試").isEqualTo("1");
    }

    // ── AT-961-14-5 ──────────────────────────────────────────────────────────────────────

    @Test
    void AT_961_14_5_routeConflictIsRefusedBeforeAnyProjectRowAndAFailedRouteMayBeRetried() {
        long projects = rows("projects");
        for (String status : List.of("PENDING", "RUNNING", "SUCCEEDED")) {
            UUID id = p1.project("r14-5-" + status.toLowerCase(), "UNDECIDED");
            p1.route(id, status, null);
            Resp resp = api.post(admin(), url(id, "/route"), trackA());
            assertThat(resp.status()).as(status).isEqualTo(409);
            assertThat(resp.<String>read("$.reason")).isEqualTo("route_conflict");
        }
        assertThat(rows("projects")).isEqualTo(projects);
        assertThat(bridge().calls).as("route_conflict 先於預演：零 Bridge 請求").isEmpty();

        UUID failed = p1.project("r14-5-failed", "UNDECIDED");
        p1.route(failed, "FAILED", null);
        assertThat(api.post(admin(), url(failed, "/route"), trackA()).status()).isEqualTo(200);
    }

    // ── AT-961-14-6 ──────────────────────────────────────────────────────────────────────

    @Test
    void AT_961_14_6_theGithubTokenTravelsOnlyInTheSingleBridgeRequestAndLeaksNowhere() {
        // 假 token 依機密掃描規則在執行期拼接（不寫成形狀像真值的字面）
        String token = "gh" + "p_" + "FAKE" + "R2P1".repeat(8);
        Resp put = api.put(admin(), "/api/v1/settings/research/github_token", Map.of("value", token, "confirm", true));
        assertThat(put.status()).as("ADMIN 經設定頁寫入加密鍵（V20 種子列、ConfigCatalog 登記）").isEqualTo(200);
        assertThat(api.put(operator(), "/api/v1/settings/research/github_token", Map.of("value", "x", "confirm", true)).status()).as("僅 ADMIN 可寫").isEqualTo(403);
        assertThat(api.get(admin(), "/api/v1/settings").body()).as("GET 設定不回明文").doesNotContain(token);
        assertThat(api.get(admin(), "/api/v1/settings/research").body()).doesNotContain(token);
        UUID with = p1.project("r14-6a", "UNDECIDED");
        UUID without = p1.project("r14-6b", "UNDECIDED");
        Map<String, Object> github = trackB("app-one");
        github.put("createGithub", true);

        Resp resp = api.post(admin(), url(with, "/route"), github);
        Resp plain = api.post(admin(), url(without, "/route"), trackB("app-two"));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(plain.status()).isEqualTo(200);
        List<Call> routeCalls = bridge().calls.stream().filter(c -> c.path().endsWith(":route")).toList();
        assertThat(routeCalls.get(0).body()).containsEntry("github_token", token);
        assertThat(routeCalls.get(1).body()).as("createGithub 為假：本文不含 github_token").doesNotContainKey("github_token");
        assertThat(bridge().calls.stream().filter(c -> c.path().endsWith(":route-preview")).allMatch(c -> !c.body().containsKey("github_token"))).isTrue();
        assertThat(resp.body()).doesNotContain(token);
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log where cast(audit_log.* as text) like ?", Long.class, "%" + token + "%")).isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.projects where cast(projects.* as text) like ?", Long.class, "%" + token + "%")).isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.research_route_decisions where cast(research_route_decisions.* as text) like ?", Long.class,
                "%" + token + "%")).isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.audit_log where cast(audit_log.* as text) like ?", Long.class, "%zzz-not-there%"))
                .as("掃描器負控：範圍非空且真的會比對").isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.projects where cast(projects.* as text) like ?", Long.class, "%app-one%"))
                .as("掃描器範圍非空").isGreaterThan(0L);
    }

    // ── AT-961-14-7 ──────────────────────────────────────────────────────────────────────

    @Test
    void AT_961_14_7_getRouteReturnsTheLatestRouteWithStepsOrNullWhenThereIsNone() {
        UUID id = p1.project("r14-7", "UNDECIDED");
        UUID none = p1.project("r14-7b", "UNDECIDED");
        UUID route = p1.route(id, "SUCCEEDED", null);
        p1.routeStep(route, 1, "VALIDATE_TARGET", "OK");
        p1.routeStep(route, 2, "GIT_SWITCH", "OK");

        Resp resp = api.get(viewer(), url(id, "/route"));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.routeId")).isEqualTo(route.toString());
        assertThat(resp.<String>read("$.data.track")).isEqualTo("A");
        assertThat(resp.<String>read("$.data.targetModule")).isEqualTo("monorepo");
        assertThat(resp.<String>read("$.data.status")).isEqualTo("SUCCEEDED");
        assertThat(resp.<List<String>>read("$.data.steps[*].step")).containsExactly("VALIDATE_TARGET", "GIT_SWITCH");
        assertThat(resp.<String>read("$.data.steps[0].argvRedacted")).isEqualTo("git worktree add");
        assertThat(resp.has("$.data.publishedDocs")).isTrue();
        Resp empty = api.get(viewer(), url(none, "/route"));
        assertThat(empty.status()).isEqualTo(200);
        assertThat(empty.<Object>read("$.data")).isNull();
        assertThat(api.get(viewer(), url(UUID.randomUUID(), "/route")).status()).isEqualTo(404);
    }

    // ── AT-961-14-E-1／E-2 ───────────────────────────────────────────────────────────────

    @Test
    void AT_961_14_E_1_scopeDiffersReasonIsRequiredOnlyWhenTheTrackDiffersFromThePrdTargetScope() {
        UUID module = p1.project("r14e1-m", "AISDLC_MODULE");
        UUID standalone = p1.project("r14e1-s", "STANDALONE_PROJECT");
        long calls = bridge().calls.size();

        Resp missing = api.post(operator(), url(module, "/route/preview"), trackB("demo-app"));
        assertThat(missing.status()).isEqualTo(422);
        assertThat(missing.<String>read("$.reason")).isEqualTo("invalid_request");
        assertThat(missing.<String>read("$.details.violations[0].rule")).isEqualTo("scope_differs_reason_required");
        assertThat(bridge().calls.size()).isEqualTo((int) calls);

        Map<String, Object> reasoned = trackB("demo-app");
        reasoned.put("scopeDiffersReason", "改為獨立專案");
        assertThat(api.post(operator(), url(module, "/route/preview"), reasoned).status()).isEqualTo(200);
        assertThat(api.post(operator(), url(module, "/route/preview"), trackA()).status()).as("相同不要求").isEqualTo(200);
        assertThat(api.post(operator(), url(standalone, "/route/preview"), trackA()).status()).isEqualTo(422);
    }

    @Test
    void AT_961_14_E_2_approverComesOnlyFromTheJwtSubjectAndKeysAreSnakeCaseTowardsTheBridge() {
        UUID id = p1.project("r14e2", "UNDECIDED");
        Map<String, Object> body = trackB("demo-app");
        body.put("approver", "mallory");
        body.put("confirmRepoName", "demo-app");
        body.put("dockerCompose", true);
        body.put("ci", false);

        Resp resp = api.post(adminAs("alice@example.com"), url(id, "/route"), body);

        assertThat(resp.status()).isEqualTo(200);
        Map<String, Object> sent = bridge().calls.stream().filter(c -> c.path().endsWith(":route")).findFirst().orElseThrow().body();
        assertThat(sent).containsEntry("approver", "alice@example.com").containsKeys("stack_template", "repo_name", "confirm_repo_name", "create_github",
                "docker_compose", "ci", "console_project_id", "project_name");
        assertThat(sent.keySet()).allSatisfy(key -> assertThat(key).doesNotContainPattern("[A-Z]"));
        assertThat(resp.<Object>read("$.data.routeId")).isNotNull();
    }

    // ── AT-961-15-E-1 ────────────────────────────────────────────────────────────────────

    @Test
    void AT_961_15_E_1_bridgeStructuredErrorsPassThroughVerbatimAndPostsAreNeverRetried() {
        UUID id = p1.project("r15e1", "UNDECIDED");
        String[][] cases = {{"route-preview", "409", "branch_exists"}, {"route-preview", "422", "target_not_empty"},
                {"route-preview", "422", "public_confirmation_required"}, {"route-preview", "409", "route_conflict"}};
        for (String[] c : cases) {
            bridge().calls.clear();
            bridge().next(c[0], Reply.error(Integer.parseInt(c[1]), c[2], "details", Map.of("marker", "m-" + c[2])));
            Resp resp = api.post(operator(), url(id, "/route/preview"), trackA());
            assertThat(resp.status()).as(c[2]).isEqualTo(Integer.parseInt(c[1]));
            assertThat(resp.<String>read("$.reason")).isEqualTo(c[2]);
            assertThat(resp.<String>read("$.details.marker")).isEqualTo("m-" + c[2]);
            assertThat(bridge().calls.stream().filter(call -> call.path().endsWith(":route-preview")).count()).as("不重試").isEqualTo(1);
        }
    }

    // ── AT-961-16-4 ──────────────────────────────────────────────────────────────────────

    @Test
    void AT_961_16_4_capabilitiesProjectsTheP1KeysInCamelCaseAndCachesForThirtySeconds() {
        Resp first = api.get(viewer(), RESEARCH + "/capabilities");
        Resp second = api.get(viewer(), RESEARCH + "/capabilities");

        assertThat(first.status()).isEqualTo(200);
        assertThat(first.has("$.data.ghCli.authenticated")).isTrue();
        assertThat(first.has("$.data.scaffoldTemplates")).isTrue();
        assertThat(first.has("$.data.repoWritable")).isTrue();
        assertThat(second.status()).isEqualTo(200);
        assertThat(bridge().countCalls("GET", "/research/capabilities")).as("30 秒內第二次不打 Bridge").isEqualTo(1);
    }
}
