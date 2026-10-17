package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SDD 批次（契約 §1.10.5、§1.10.6、§3.4.1 v1.5 補充；API-EXE-15；D-115-06）：execute 依「範圍內任務」判定資格，成立才送 {@code sdd} 區塊
 * ＋權杖並沿用 {@code passCriteriaSpec.stepId}，不成立就走 {@code G<g>-T<t>} 並以 {@code warnings[]} 出聲；對<b>真的 HTTP</b> 迷你 Bridge 驗。
 * 為什麼重要：資格判錯，SDD 批次會悄悄失去 FSM 預檢與追溯報告，或手動專案被誤送 {@code sdd} 區塊；權杖只准出現在寫入呼叫上
 * （包含 resume／restore——Console 不記錄批次是否為 SDD，D-115-18）；Bridge 的每一種預檢拒絕都要補償刪除剛建的 run 列、專案與任務狀態不動。
 */
class ExecuteSddBatchApiIT extends AbstractExecutionIT {

    private static final String DIGEST = "sha256:" + "a".repeat(64);
    private static final String OTHER_DIGEST = "sha256:" + "b".repeat(64);
    private static final String APPROVER = "初審核准人";
    private static final String OTHER_TOKEN = "mock-a-different-token-value-0123456789abcdef";

    /** 一個含 {@code count} 個 SDD 任務的專案（自治等級 4：沒有審核閘，批次自己跑完）。 */
    private record SddProject(String projectId, String goalId, List<String> taskIds, List<String> stepIds) {
    }

    private static String stepIdOf(int index) {
        return "sdd-greenfield-at-001-" + index + "-1";
    }

    /** 專案名同時是資料夾名；{@code bound}＝已綁定規格（路徑 A 匯入過）。 */
    private String newProject(String name, boolean bound) {
        String projectId = createProject(Map.of("name", name, "executionPath", "/e2e/" + name,
                "passCriteria", "- 全部通過", "autonomyLevel", 4));
        if (bound) {
            jdbc.update("update console.projects set sdd_spec_dir = ?, sdd_spec_file = ? where id = ?",
                    "/e2e/" + name + "/docs", "/e2e/" + name + "/docs/TCS-A.md", UUID.fromString(projectId));
        }
        return projectId;
    }

    private String sddTask(String goalId, int index, String stepId, String digest) {
        Map<String, Object> spec = new LinkedHashMap<>();
        spec.put("source", "sdd");
        spec.put("specDigest", digest);
        spec.put("stepId", stepId);
        spec.put("weakRegex", index == 2);
        if (index == 1) {
            spec.put("maintainContext", true);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("name", "AT-001-" + index + "-1");
        body.put("description", "請輸出 [T" + index + "_DONE]");
        body.put("passCriteria", "輸出含 [T" + index + "_DONE]");
        body.put("expectedOutputRegex", "\\[T" + index + "_DONE\\]");
        body.put("maxRetries", 5);
        body.put("passCriteriaSpec", spec);
        Resp resp = api.post(operator(), "/api/v1/goals/" + goalId + "/tasks", body);
        assertThat(resp.status()).as(resp.body()).isEqualTo(201);
        return resp.id();
    }

    private SddProject sddProject(String name, int count, boolean bound) {
        String projectId = newProject(name, bound);
        String goalId = createGoal(projectId, "規格目標");
        List<String> taskIds = new ArrayList<>();
        List<String> stepIds = new ArrayList<>();
        for (int i = 1; i <= count; i++) {
            stepIds.add(stepIdOf(i));
            taskIds.add(sddTask(goalId, i, stepIdOf(i), DIGEST));
        }
        return new SddProject(projectId, goalId, taskIds, stepIds);
    }

    private void signedOffBy(String taskId, String approver) {
        jdbc.update("update console.tasks set signed_off_by = ? where id = ?", approver, UUID.fromString(taskId));
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> playbookTasks(Map<String, Object> request) {
        return (List<Map<String, Object>>) ((Map<String, Object>) request.get("playbook")).get("tasks");
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> sddBlock(Map<String, Object> request) {
        return (Map<String, Object>) request.get("sdd");
    }

    private static Map<String, Object> scopeOf(List<String> goalIds) {
        Map<String, Object> scope = new LinkedHashMap<>();
        scope.put("mode", "SELECTED");
        scope.put("goalIds", goalIds);
        scope.put("taskIds", List.of());
        return Map.of("scope", scope);
    }

    /** 迷你 Bridge 收到、請求路徑以 {@code suffix} 結尾的每個請求所帶的 {@code X-Bridge-Token}（沒帶＝字串 {@code null}）。 */
    private List<String> tokensOf(String suffix) {
        return MINI.authed().stream().filter(a -> a.request().endsWith(suffix)).map(a -> String.valueOf(a.token()))
                .toList();
    }

    // ── 資格成立 ──────────────────────────────────────────────────────────────

    @Test
    void aBoundSddBatchSendsTheSddBlockTheTokenAndTheSddStepIds() {
        SddProject p = sddProject("sdd-batch", 3, true);
        for (String taskId : p.taskIds()) {
            signedOffBy(taskId, APPROVER);
        }

        Resp resp = execute(p.projectId(), Map.of());

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.has("$.data.warnings")).as("沒有警告：維持 v1.4 的回應形狀").isFalse();
        String run = resp.id();
        Map<String, Object> request = mini(run).request;
        assertThat(sddBlock(request)).containsOnly(Map.entry("spec_dir", "/e2e/sdd-batch/docs"),
                Map.entry("spec_file", "/e2e/sdd-batch/docs/TCS-A.md"), Map.entry("fsm_project", "sdd-batch"),
                Map.entry("root", "/e2e/sdd-batch"), Map.entry("approver", APPROVER));
        List<Map<String, Object>> tasks = playbookTasks(request);
        assertThat(tasks).extracting(t -> t.get("step_id")).as("step_id 沿用 passCriteriaSpec.stepId")
                .containsExactlyElementsOf(p.stepIds());
        assertThat(tasks.get(0)).containsEntry("spec_digest", DIGEST).containsEntry("maintain_context", true)
                .containsEntry("weak_regex", false).containsEntry("max_retries", 5)
                .containsEntry("goal_task_id", p.taskIds().get(0));
        assertThat(tasks.get(1)).containsEntry("weak_regex", true).doesNotContainKey("maintain_context");
        assertThat(MINI.authed()).as("權杖只出現在建立批次的那一個寫入呼叫").filteredOn(a -> a.token() != null)
                .extracting(MiniBridge.Authed::request).containsOnly("POST /autoclaude/runs");
        assertThat(tokensOf("POST /autoclaude/runs")).containsExactly(MiniBridge.SDD_TOKEN);

        assertThat(awaitProjected(run, "COMPLETED")).as("事件消費者以 DAG 的 SDD step_id 對上任務").isTrue();
        assertThat(api.get(viewer(), "/api/v1/executions/" + run + "/dag")
                .<List<String>>read("$.data.nodes[?(@.kind=='TASK')].stepId")).as("dag.nodes[].stepId 同值")
                .containsExactlyElementsOf(p.stepIds());
        assertThat(api.get(viewer(), "/api/v1/executions/" + run + "/steps?size=200")
                .<List<String>>read("$.data.content[*].stepId")).as("步驟列也是 SDD step_id")
                .hasSameElementsAs(p.stepIds());
        p.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
        assertThat(resp.body()).doesNotContain(MiniBridge.SDD_TOKEN);
    }

    @Test
    void theEffectiveFsmProjectIsTheBoundKeyElseTheProjectName() {
        SddProject named = sddProject("Some Project 專案", 2, true);
        String first = execute(named.projectId(), Map.of()).id();
        assertThat(sddBlock(mini(first).request)).as("沒有綁定鍵：專案名原樣送出，Backend 不淨化")
                .containsEntry("fsm_project", "Some Project 專案").containsEntry("root", "/e2e/Some Project 專案");

        SddProject keyed = sddProject("keyed-project", 2, true);
        jdbc.update("update console.projects set sdd_project = 'Bound Key 鍵' where id = ?",
                UUID.fromString(keyed.projectId()));
        String second = execute(keyed.projectId(), Map.of()).id();
        assertThat(sddBlock(mini(second).request)).as("有綁定鍵就用綁定鍵").containsEntry("fsm_project", "Bound Key 鍵");

        assertThat(awaitProjected(first, "COMPLETED")).isTrue();
        assertThat(awaitProjected(second, "COMPLETED")).isTrue();
    }

    @Test
    void theApproverIsTheFirstSignedOffByInPlanOrderElseTheJwtSubject() {
        SddProject anonymous = sddProject("approver-anon", 2, true);
        String first = execute(anonymous.projectId(), Map.of()).id();
        assertThat(sddBlock(mini(first).request)).as("簽核人全空：永遠送具名人（觸發的人）")
                .containsEntry("approver", "operator");

        SddProject inherited = sddProject("approver-inherit", 3, true);
        signedOffBy(inherited.taskIds().get(1), "李四");
        signedOffBy(inherited.taskIds().get(2), "王五");
        String second = execute(inherited.projectId(), Map.of()).id();
        assertThat(sddBlock(mini(second).request)).as("排序最前的非空值").containsEntry("approver", "李四");

        assertThat(awaitProjected(first, "COMPLETED")).isTrue();
        assertThat(awaitProjected(second, "COMPLETED")).isTrue();
    }

    @Test
    void aScopeOfOnlySddTasksIsStillASddBatchInAMixedProject() {
        SddProject p = sddProject("sdd-narrow", 2, true);
        String manualGoal = createGoal(p.projectId(), "手動目標");
        createFixtureTask(manualGoal, "手動任務", 9);

        Resp resp = execute(p.projectId(), scopeOf(List.of(p.goalId())));

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.has("$.data.warnings")).isFalse();
        Map<String, Object> request = mini(resp.id()).request;
        assertThat(sddBlock(request)).as("資格以範圍內任務為準，不是整個專案").isNotNull();
        assertThat(playbookTasks(request)).extracting(t -> t.get("step_id")).containsExactlyElementsOf(p.stepIds());
        assertThat(awaitProjected(resp.id(), "COMPLETED")).isTrue();
    }

    @Test
    void aScopeOfOnlyManualTasksInAMixedProjectIsClassicAndSilent() {
        SddProject p = sddProject("sdd-silent", 2, true);
        String manualGoal = createGoal(p.projectId(), "手動目標");
        String manualTask = createFixtureTask(manualGoal, "手動任務", 9);

        Resp resp = execute(p.projectId(), scopeOf(List.of(manualGoal)));

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.has("$.data.warnings")).as("範圍內沒有 SDD 來源任務：不出聲").isFalse();
        Map<String, Object> request = mini(resp.id()).request;
        assertThat(request).doesNotContainKey("sdd");
        assertThat(playbookTasks(request)).hasSize(1);
        assertThat(playbookTasks(request).get(0)).containsEntry("goal_task_id", manualTask)
                .doesNotContainKeys("spec_digest", "weak_regex", "maintain_context");
        assertThat(tokensOf("POST /autoclaude/runs")).containsOnly("null");
        assertThat(awaitProjected(resp.id(), "COMPLETED")).isTrue();
    }

    @Test
    void theBridgesFrozenDigestAbsentWarningIsForwardedVerbatimWithoutACause() {
        SddProject p = sddProject("sdd-warn", 1, true);
        MINI.sdd.createWarnings.add(Map.of("code", "sdd_frozen_digest_absent", "detail", "舊狀態檔：凍結時沒有記錄內容摘要"));

        Resp resp = execute(p.projectId(), Map.of());

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<List<Object>>read("$.data.warnings")).hasSize(1);
        assertThat(resp.<String>read("$.data.warnings[0].code")).isEqualTo("sdd_frozen_digest_absent");
        assertThat(resp.<String>read("$.data.warnings[0].detail")).isEqualTo("舊狀態檔：凍結時沒有記錄內容摘要");
        assertThat(resp.has("$.data.warnings[0].cause")).as("Bridge 的警告沒有 cause").isFalse();
        assertThat(awaitProjected(resp.id(), "COMPLETED")).isTrue();
    }

    // ── 資格不成立：走 G<g>-T<t>、出聲、不帶權杖 ──────────────────────────────────────────

    private void assertClassicBatch(Resp resp, String cause, int taskCount) {
        assertThat(resp.status()).as(cause).isEqualTo(201);
        assertThat(resp.<List<String>>read("$.data.warnings[*].code")).containsExactly("sdd_governance_inactive");
        assertThat(resp.<String>read("$.data.warnings[0].cause")).isEqualTo(cause);
        assertThat(resp.<String>read("$.data.warnings[0].detail")).isNotBlank().contains("沒有啟用 SDD 治理");
        Map<String, Object> request = mini(resp.id()).request;
        assertThat(request).as(cause).doesNotContainKey("sdd");
        assertThat(playbookTasks(request)).extracting(t -> t.get("step_id")).as(cause + "：維持 G<g>-T<t>")
                .containsExactlyElementsOf(IntStream.rangeClosed(1, taskCount).mapToObj(i -> "G1-T" + i).toList());
        assertThat(playbookTasks(request)).as(cause).allSatisfy(t -> assertThat(t).doesNotContainKeys("spec_digest",
                "weak_regex", "maintain_context"));
        assertThat(tokensOf("POST /autoclaude/runs")).as(cause + "：沒有 sdd 就不需要權杖").containsOnly("null");
        assertThat(awaitProjected(resp.id(), "COMPLETED")).as(cause + "：任務照常對得上").isTrue();
    }

    @Test
    void anUnboundProjectWarnsNotBoundAndSendsAClassicBatch() {
        SddProject p = sddProject("sdd-unbound", 2, false);

        assertClassicBatch(execute(p.projectId(), Map.of()), "not_bound", 2);
    }

    @Test
    void aManualTaskInTheScopeWarnsMixedScope() {
        SddProject p = sddProject("sdd-mixed", 2, true);
        createFixtureTask(p.goalId(), "手動任務", 9);

        assertClassicBatch(execute(p.projectId(), Map.of()), "mixed_scope", 3);
    }

    @Test
    void aSddTaskWithoutAStepIdOrDigestAlsoWarnsMixedScope() {
        SddProject p = sddProject("sdd-nostep", 1, true);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("name", "缺 stepId");
        body.put("description", "d");
        body.put("passCriteria", "p");
        body.put("passCriteriaSpec", Map.of("source", "sdd", "specDigest", DIGEST));
        assertThat(api.post(operator(), "/api/v1/goals/" + p.goalId() + "/tasks", body).status()).isEqualTo(201);

        assertClassicBatch(execute(p.projectId(), Map.of()), "mixed_scope", 2);
    }

    @Test
    void tasksFromDifferentSpecDigestsWarnSpecMismatch() {
        String projectId = newProject("sdd-mismatch", true);
        String goal = createGoal(projectId, "目標");
        sddTask(goal, 1, stepIdOf(1), DIGEST);
        sddTask(goal, 2, stepIdOf(2), OTHER_DIGEST);

        assertClassicBatch(execute(projectId, Map.of()), "spec_mismatch", 2);
    }

    @Test
    void repeatedStepIdsWarnDuplicateStepId() {
        String projectId = newProject("sdd-dup", true);
        String goal = createGoal(projectId, "目標");
        sddTask(goal, 1, stepIdOf(1), DIGEST);
        sddTask(goal, 2, stepIdOf(1), DIGEST);

        Resp resp = execute(projectId, Map.of());

        assertClassicBatch(resp, "duplicate_step_id", 2);
        assertThat(resp.<String>read("$.data.warnings[0].detail")).contains(stepIdOf(1));
    }

    @Test
    void aManualProjectGetsNoSddBlockNoTokenAndNoWarningAtAll() {
        Fixture f = prjA("manual-sdd-free", 4);

        Resp resp = execute(f.projectId(), Map.of());

        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.has("$.data.warnings")).as("沒有任何 SDD 來源任務就不出聲").isFalse();
        Map<String, Object> request = mini(resp.id()).request;
        assertThat(request).doesNotContainKey("sdd");
        assertThat(playbookTasks(request)).extracting(t -> t.get("step_id")).containsExactly("G1-T1", "G1-T2", "G2-T1");
        assertThat(tokensOf("POST /autoclaude/runs")).containsOnly("null");
        assertThat(awaitProjected(resp.id(), "COMPLETED")).isTrue();
    }

    // ── Bridge 預檢拒絕：補償刪除、狀態不動 ────────────────────────────────────────────────

    private void assertNothingStarted(SddProject p) {
        assertThat(countRuns(p.projectId())).as("剛建的 run 列已補償刪除").isZero();
        assertThat(projectStatus(p.projectId())).as("專案仍是建立時的狀態").isEqualTo("DRAFT");
        p.taskIds().forEach(id -> assertThat(taskStatus(id)).as("任務維持 PENDING").isEqualTo("PENDING"));
        assertThat(consumers.activeCount()).as("沒有為它啟動事件消費者").isZero();
    }

    @Test
    void everyPrecheckRefusalIsTranslatedAndCompensatedWithStatesUntouched() {
        SddProject p = sddProject("sdd-refused", 2, true);

        MINI.failNext("start", 409, Map.of("code", 409, "reason", "fsm_state_conflict", "detail",
                Map.of("current_state", "ESCALATION", "expected_state", List.of("IMPLEMENTATION", "SPEC_FROZEN"))));
        Resp stateConflict = execute(p.projectId(), Map.of());
        assertThat(stateConflict.status()).isEqualTo(409);
        assertThat(stateConflict.<String>read("$.reason")).isEqualTo("sdd_fsm_state_conflict");
        assertThat(stateConflict.<String>read("$.details.currentState")).isEqualTo("ESCALATION");
        assertThat(stateConflict.<List<String>>read("$.details.expectedState")).containsExactly("IMPLEMENTATION",
                "SPEC_FROZEN");
        assertNothingStarted(p);

        MINI.failNext("start", 409, Map.of("code", 409, "reason", "fsm_state_conflict", "detail",
                Map.of("current_state", "AUTOCLAUDE_DELEGATED", "run_id", "older-run", "run_status", "RUNNING")));
        Resp active = execute(p.projectId(), Map.of());
        assertThat(active.<String>read("$.reason")).isEqualTo("sdd_fsm_state_conflict");
        assertThat(active.<String>read("$.details.runId")).isEqualTo("older-run");
        assertThat(active.<String>read("$.details.runStatus")).isEqualTo("RUNNING");
        assertNothingStarted(p);

        MINI.failNext("start", 409, Map.of("code", 409, "reason", "spec_digest_changed", "detail",
                Map.of("pair", "frozen_vs_file", "doc", "TCS-A.md", "frozen_digest", "sha256:1", "current_digest",
                        "sha256:2")));
        Resp digest = execute(p.projectId(), Map.of());
        assertThat(digest.status()).isEqualTo(409);
        assertThat(digest.<String>read("$.reason")).isEqualTo("sdd_spec_digest_changed");
        assertThat(digest.<String>read("$.details.pair")).isEqualTo("frozen_vs_file");
        assertThat(digest.<String>read("$.details.frozenDigest")).isEqualTo("sha256:1");
        assertThat(digest.<String>read("$.details.currentDigest")).isEqualTo("sha256:2");
        assertNothingStarted(p);

        MINI.failNext("start", 404, Map.of("code", 404, "reason", "fsm_not_found", "project", "from-bridge"));
        Resp missing = execute(p.projectId(), Map.of());
        assertThat(missing.status()).isEqualTo(409);
        assertThat(missing.<String>read("$.reason")).isEqualTo("sdd_fsm_not_found");
        assertThat(missing.<String>read("$.details.sddProject")).as("送出的有效 FSM 專案").isEqualTo("sdd-refused");
        assertNothingStarted(p);

        MINI.failNext("start", 422, Map.of("code", 422, "reason", "spec_not_frozen", "detail", "規格不在凍結清單內"));
        Resp notFrozen = execute(p.projectId(), Map.of());
        assertThat(notFrozen.status()).isEqualTo(422);
        assertThat(notFrozen.<String>read("$.reason")).isEqualTo(ErrorReasons.SDD_SPEC_REJECTED);
        assertThat(notFrozen.<String>read("$.details.bridgeReason")).isEqualTo("spec_not_frozen");
        assertThat(notFrozen.<String>read("$.details.detail")).isEqualTo("規格不在凍結清單內");
        assertNothingStarted(p);

        MINI.failNext("start", 422, Map.of("code", 422, "reason", "sdd_block_invalid", "violations",
                List.of(Map.of("field", "sdd.spec_dir", "rule", "outside_root"))));
        Resp invalidBlock = execute(p.projectId(), Map.of());
        assertThat(invalidBlock.status()).isEqualTo(422);
        assertThat(invalidBlock.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_REJECTED);
        assertThat(invalidBlock.<String>read("$.details.bridgeReason")).isEqualTo("sdd_block_invalid");
        assertThat(invalidBlock.<String>read("$.details.violations[0].field")).isEqualTo("sdd.spec_dir");
        assertNothingStarted(p);

        String holder = UUID.randomUUID().toString();
        MINI.failNext("start", 409, Map.of("code", 409, "reason", "advisory_lock_held", "holder_run_id", holder));
        Resp locked = execute(p.projectId(), Map.of());
        assertThat(locked.status()).as("非 SDD 專屬的拒絕照舊轉譯").isEqualTo(409);
        assertThat(locked.<String>read("$.reason")).isEqualTo(ErrorReasons.LOCK_HELD);
        assertThat(locked.<String>read("$.details.holderRunId")).isEqualTo(holder);
        assertNothingStarted(p);
    }

    @Test
    void aBridgeWithoutTheTokenIs503AndAMismatchedTokenIs502OnExecute() {
        SddProject p = sddProject("sdd-token", 2, true);

        MINI.sdd.writeToken = null;
        Resp disabled = execute(p.projectId(), Map.of());
        assertThat(disabled.status()).isEqualTo(503);
        assertThat(disabled.<String>read("$.reason")).isEqualTo("sdd_write_disabled");
        assertNothingStarted(p);

        MINI.sdd.writeToken = OTHER_TOKEN;
        Resp forbidden = execute(p.projectId(), Map.of());
        assertThat(forbidden.status()).isEqualTo(502);
        assertThat(forbidden.<Integer>read("$.details.bridgeStatus")).isEqualTo(403);
        assertThat(forbidden.<String>read("$.details.bridgeReason")).isEqualTo("sdd_write_forbidden");
        assertThat(forbidden.body()).doesNotContain(MiniBridge.SDD_TOKEN).doesNotContain("a-different-token");
        assertNothingStarted(p);
    }

    // ── resume／restore：權杖一律附上（Console 不記錄批次是否為 SDD）─────────────────────────

    /** manualSteps 下讓第一步完成並在步驟邊界暫停（呼叫端須已確認第一個任務 RUNNING）。 */
    private void pauseAfterTheFirstStep(String run) {
        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/pause").status()).isEqualTo(200);
        mini(run).release(1);
        assertThat(awaitProjected(run, "PAUSED")).isTrue();
    }

    @Test
    void resumeAndRestoreCarryTheTokenWhilePauseNeverDoes() {
        SddProject p = sddProject("sdd-resume", 3, true);
        MINI.manualSteps = true;
        String run = execute(p.projectId(), Map.of()).id();
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(p.taskIds().get(0))))).isTrue();
        pauseAfterTheFirstStep(run);

        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/resume").status()).isEqualTo(200);
        mini(run).release(2);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(consumers.awaitIdle(Duration.ofSeconds(5))).isTrue();
        String checkpoint = api.get(viewer(), "/api/v1/executions/" + run + "/checkpoints")
                .<List<String>>read("$.data[*].id").get(0);
        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/restore/" + checkpoint).status()).isEqualTo(200);
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(p.taskIds().get(1))))).isTrue();
        mini(run).release(2);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();

        assertThat(tokensOf(":resume")).containsExactly(MiniBridge.SDD_TOKEN);
        assertThat(tokensOf("/restore")).containsExactly(MiniBridge.SDD_TOKEN);
        assertThat(tokensOf(":pause")).as("pause 不是 FSM 寫入").containsOnly("null");
    }

    @Test
    void aSddRunResumeIsRefusedWithoutAValidTokenAndNothingChanges() {
        SddProject p = sddProject("sdd-resume-denied", 3, true);
        MINI.manualSteps = true;
        String run = execute(p.projectId(), Map.of()).id();
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(p.taskIds().get(0))))).isTrue();
        pauseAfterTheFirstStep(run);

        MINI.sdd.writeToken = null;
        Resp disabled = api.post(operator(), "/api/v1/executions/" + run + "/resume");
        assertThat(disabled.status()).isEqualTo(503);
        assertThat(disabled.<String>read("$.reason")).isEqualTo("sdd_write_disabled");

        MINI.sdd.writeToken = OTHER_TOKEN;
        Resp forbidden = api.post(operator(), "/api/v1/executions/" + run + "/resume");
        assertThat(forbidden.status()).isEqualTo(502);
        assertThat(forbidden.<String>read("$.details.bridgeReason")).isEqualTo("sdd_write_forbidden");
        assertThat(forbidden.body()).doesNotContain(MiniBridge.SDD_TOKEN).doesNotContain("a-different-token");

        assertThat(runStatus(run)).as("DB 狀態不變").isEqualTo("PAUSED");
        assertThat(projectStatus(p.projectId())).isEqualTo("READY");
        MINI.sdd.writeToken = MiniBridge.SDD_TOKEN;
        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/resume").status()).as("設定恢復後可續跑")
                .isEqualTo(200);
        mini(run).release(2);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
    }

    @Test
    void aSddResumeRefusedByThePrecheckIs409AndTheRunStaysPaused() {
        SddProject p = sddProject("sdd-resume-409", 3, true);
        MINI.manualSteps = true;
        String run = execute(p.projectId(), Map.of()).id();
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(p.taskIds().get(0))))).isTrue();
        pauseAfterTheFirstStep(run);

        MINI.failNext("resume", 409, Map.of("code", 409, "reason", "fsm_state_conflict", "detail",
                Map.of("current_state", "ESCALATION", "expected_state", "AUTOCLAUDE_DELEGATED")));
        Resp conflict = api.post(operator(), "/api/v1/executions/" + run + "/resume");
        assertThat(conflict.status()).isEqualTo(409);
        assertThat(conflict.<String>read("$.reason")).isEqualTo("sdd_fsm_state_conflict");
        assertThat(conflict.<String>read("$.details.currentState")).isEqualTo("ESCALATION");
        assertThat(conflict.<String>read("$.details.expectedState")).isEqualTo("AUTOCLAUDE_DELEGATED");

        MINI.failNext("resume", 409, Map.of("code", 409, "reason", "spec_digest_changed", "detail",
                Map.of("pair", "frozen_vs_file", "doc", "TCS-A.md", "frozen_digest", "sha256:1", "current_digest",
                        "sha256:2")));
        Resp digest = api.post(operator(), "/api/v1/executions/" + run + "/resume");
        assertThat(digest.status()).isEqualTo(409);
        assertThat(digest.<String>read("$.reason")).isEqualTo("sdd_spec_digest_changed");
        assertThat(digest.<String>read("$.details.pair")).isEqualTo("frozen_vs_file");

        assertThat(runStatus(run)).as("DB 狀態不變").isEqualTo("PAUSED");
        assertThat(projectStatus(p.projectId())).isEqualTo("READY");
        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/resume").status()).as("預檢過了就能續跑")
                .isEqualTo(200);
        mini(run).release(2);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
    }

    @Test
    void aManualRunResumesEvenWhenTheBridgeHasNoTokenAtAll() {
        Fixture f = prjA("manual-no-token", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();
        pauseAfterTheFirstStep(run);
        MINI.sdd.writeToken = null;

        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/resume").status())
                .as("不含 sdd 的 run：Bridge 不需要權杖").isEqualTo(200);
        mini(run).release(5);
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(tokensOf(":resume")).as("Console 不分 SDD 與否，有設就附").containsExactly(MiniBridge.SDD_TOKEN);
    }

    // ── 審核決定開的後續批次走同一條路徑 ────────────────────────────────────────────────

    @Test
    void aSkipFollowUpBatchIsAlsoASddBatchWithItsOwnApproverAndTheToken() {
        SddProject p = sddProject("sdd-follow-up", 3, true);
        signedOffBy(p.taskIds().get(0), APPROVER);
        signedOffBy(p.taskIds().get(2), "複審核准人");
        MINI.failStepIds.add(p.stepIds().get(1));
        String run = execute(p.projectId(), Map.of()).id();
        assertThat(sddBlock(mini(run).request)).containsEntry("approver", APPROVER);
        assertThat(awaitProjected(run, "FAILED")).isTrue();
        String item = (String) pendingReviews(run).get(0).get("id");
        MINI.failStepIds.clear();

        Resp skip = review(run, item, "SKIP");

        assertThat(skip.status()).isEqualTo(204);
        String followUp = skip.header("X-Follow-Up-Run-Id");
        assertThat(followUp).isNotBlank().isNotEqualTo(run);
        Map<String, Object> request = mini(followUp).request;
        assertThat(sddBlock(request)).as("後續批次依自己的範圍判資格與簽核人").containsEntry("approver", "複審核准人")
                .containsEntry("fsm_project", "sdd-follow-up");
        assertThat(playbookTasks(request)).extracting(t -> t.get("step_id")).containsExactly(p.stepIds().get(2));
        assertThat(tokensOf("POST /autoclaude/runs")).as("兩個批次都帶權杖").containsExactly(MiniBridge.SDD_TOKEN,
                MiniBridge.SDD_TOKEN);
        assertThat(awaitProjected(followUp, "COMPLETED")).isTrue();
    }

    @Test
    void aRefusedFollowUpBatchFailsTheDecisionAndLeavesTheReviewPending() {
        SddProject p = sddProject("sdd-follow-up-refused", 3, true);
        MINI.failStepIds.add(p.stepIds().get(1));
        String run = execute(p.projectId(), Map.of()).id();
        assertThat(awaitProjected(run, "FAILED")).isTrue();
        String item = (String) pendingReviews(run).get(0).get("id");
        MINI.failStepIds.clear();
        MINI.failNext("start", 409, Map.of("code", 409, "reason", "fsm_state_conflict", "detail",
                Map.of("current_state", "ESCALATION", "expected_state", List.of("IMPLEMENTATION", "SPEC_FROZEN"))));

        Resp refused = review(run, item, "SKIP");

        assertThat(refused.status()).as("後續批次被 FSM 預檢擋下，審核決定隨之失敗（原子性，契約 §1.2.11）").isEqualTo(409);
        assertThat(refused.<String>read("$.reason")).isEqualTo("sdd_fsm_state_conflict");
        assertThat(refused.<String>read("$.details.currentState")).isEqualTo("ESCALATION");
        assertThat(pendingReviews(run)).as("審核項仍待決").hasSize(1);
        assertThat(taskStatus(p.taskIds().get(1))).as("失敗的任務維持 ESCALATED").isEqualTo("ESCALATED");
        assertThat(countRuns(p.projectId())).as("沒有後續批次").isEqualTo(1);

        assertThat(review(run, item, "SKIP").status()).as("同一個決定在預檢通過後可再做").isEqualTo(204);
    }

    @Test
    void aRetryDecisionRestoresTheSddRunWithTheToken() {
        SddProject p = sddProject("sdd-retry", 3, true);
        MINI.failStepIds.add(p.stepIds().get(1));
        String run = execute(p.projectId(), Map.of()).id();
        assertThat(awaitProjected(run, "FAILED")).isTrue();
        String item = (String) pendingReviews(run).get(0).get("id");
        MINI.failStepIds.clear();

        Resp retry = review(run, item, "RETRY");

        assertThat(retry.status()).isEqualTo(204);
        assertThat(retry.header("X-Follow-Up-Run-Id")).as("restore 沿用同一個批次").isNull();
        assertThat(awaitProjected(run, "COMPLETED")).isTrue();
        assertThat(tokensOf("/restore")).containsExactly(MiniBridge.SDD_TOKEN);
        p.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("COMPLETED"));
    }
}
