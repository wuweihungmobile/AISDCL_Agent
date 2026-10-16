package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@code POST /projects/{projectId}/execute}（契約 §1.2.1；E2E-02、E2E-03 的啟動段；API-EXE-01、11、12、13）：
 * 驗證順序 1→10 逐列斷言（第 3～9f 項<b>不呼叫 Bridge</b>）、Bridge 失敗的補償刪除、成功時的讀模型與送給 Bridge 的請求。
 */
class ExecuteProjectApiIT extends AbstractExecutionIT {

    private static String executePath(String projectId) {
        return "/api/v1/projects/" + projectId + "/execute";
    }

    private static Map<String, Object> scope(String mode, List<String> goalIds, List<String> taskIds) {
        Map<String, Object> scope = new LinkedHashMap<>();
        scope.put("mode", mode);
        scope.put("goalIds", goalIds);
        scope.put("taskIds", taskIds);
        return Map.of("scope", scope);
    }

    // ── 1～2：專案存在、請求欄位 ──────────────────────────────────────────────────

    @Test
    void step1_anUnknownProjectIs404EvenWhenTheBodyIsAlsoInvalid() {
        String unknown = UUID.randomUUID().toString();
        Resp resp = execute(unknown, Map.of("autonomyLevel", 99));
        assertThat(resp.status()).isEqualTo(404);
        assertThat(resp.<String>read("$.message")).isEqualTo("專案不存在或已刪除：" + unknown);
        assertThat(MINI.countRequests("POST /autoclaude/runs")).isZero();
    }

    @Test
    void step2_everyBadRequestFieldIsReportedWithItsOwnFieldName() {
        Fixture f = prjA("fields", 4);
        Resp resp = execute(f.projectId(), Map.of("autonomyLevel", 11, "tokenBudget", 0,
                "scope", Map.of("mode", "FOO", "limits", Map.of("taskTokens", 0, "goalTokens", 0))));
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.errorFields()).contains("autonomyLevel", "tokenBudget", "scope.mode",
                "scope.limits.taskTokens", "scope.limits.goalTokens");
        assertThat(MINI.countRequests("POST /autoclaude/runs")).isZero();
    }

    @Test
    void step2_modeAllRejectsIdsAndSelectedNeedsAtLeastOne() {
        Fixture f = prjA("modes", 4);
        Resp allWithIds = execute(f.projectId(), scope("ALL", List.of(f.g1()), List.of()));
        assertThat(allWithIds.status()).isEqualTo(400);
        assertThat(allWithIds.errorFields()).contains("scope");
        Resp selectedEmpty = execute(f.projectId(), scope("SELECTED", List.of(), List.of()));
        assertThat(selectedEmpty.status()).isEqualTo(400);
        assertThat(selectedEmpty.errorFields()).contains("scope");
    }

    // ── 3～4：專案狀態 ────────────────────────────────────────────────────────────

    @Test
    void step3_anExecutingProjectIs409WithTheActiveRunIdWhenThereIsOne() {
        Fixture f = prjA("busy", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        Resp second = execute(f.projectId(), Map.of());
        assertThat(second.status()).isEqualTo(409);
        assertThat(second.<String>read("$.reason")).isEqualTo(ErrorReasons.PROJECT_EXECUTING);
        assertThat(second.<String>read("$.details.projectId")).isEqualTo(f.projectId());
        assertThat(second.<String>read("$.details.runId")).isEqualTo(run);
        assertThat(MINI.countRequests("POST /autoclaude/runs")).as("第二次沒有到 Bridge").isEqualTo(1);
    }

    @Test
    void step3_anExecutingProjectWithoutAnyRunOmitsTheRunId() {
        Fixture f = prjA("busy-no-run", 4);
        setProjectStatus(f.projectId(), "EXECUTING");
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.PROJECT_EXECUTING);
        assertThat(resp.has("$.details.runId")).as("details 不輸出 null").isFalse();
    }

    @Test
    void step4_anArchivedProjectIs409() {
        Fixture f = prjA("archived", 4);
        setProjectStatus(f.projectId(), "ARCHIVED");
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.PROJECT_STATE_NOT_EXECUTABLE);
        assertThat(resp.<String>read("$.details.status")).isEqualTo("ARCHIVED");
    }

    // ── 5：人工 signoff 硬閘（E2E-02）─────────────────────────────────────────────

    @Test
    void step5_aDraftProjectIsRefusedAndTheMessageIsThePrdWording() {
        String projectId = createProject(Map.of("name", "draft", "executionPath", "/e2e/draft", "passCriteria", "- ok",
                "draft", true));
        Resp resp = execute(projectId, Map.of());
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.message")).isEqualTo("草案未經人工審批，禁止執行");
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.UNSIGNED_DRAFT);
        assertThat(resp.<String>read("$.details.unsignedProjectId")).isEqualTo(projectId);
        assertThat(resp.<List<String>>read("$.details.unsignedGoalIds")).isEmpty();
        assertThat(resp.<List<String>>read("$.details.unsignedTaskIds")).isEmpty();
        assertThat(MINI.countRequests("POST /autoclaude/runs")).isZero();
        assertThat(countRuns(projectId)).isZero();
    }

    @Test
    void step5_unsignedGoalsAndTasksAreListedAndTheProjectIdIsOmittedWhenItIsSignedOff() {
        Fixture f = prjA("unsigned", 4);
        Resp draftGoal = api.post(operator(), "/api/v1/projects/" + f.projectId() + "/goals",
                Map.of("name", "草稿目標", "passCriteria", "- x", "draft", true));
        assertThat(draftGoal.status()).isEqualTo(201);
        Resp draftTask = api.post(operator(), "/api/v1/goals/" + f.g1() + "/tasks",
                Map.of("name", "草稿任務", "passCriteria", "- x", "draft", true));
        assertThat(draftTask.status()).isEqualTo(201);

        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.UNSIGNED_DRAFT);
        assertThat(resp.has("$.details.unsignedProjectId")).as("專案本身已 signoff 時省略").isFalse();
        assertThat(resp.<List<String>>read("$.details.unsignedGoalIds")).containsExactly(draftGoal.id());
        assertThat(resp.<List<String>>read("$.details.unsignedTaskIds")).containsExactly(draftTask.id());
    }

    @Test
    void step5_theSignoffCheckComesBeforeTheScopeCheck() {
        Fixture f = prjA("order", 4);
        Resp draftGoal = api.post(operator(), "/api/v1/projects/" + f.projectId() + "/goals",
                Map.of("name", "草稿目標", "passCriteria", "- x", "draft", true));
        assertThat(draftGoal.status()).isEqualTo(201);
        Resp resp = execute(f.projectId(), scope("SELECTED", List.of(UUID.randomUUID().toString()), List.of()));
        assertThat(resp.status()).as("未 signoff 先於範圍檢查（E2E-02 步驟 5）").isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.UNSIGNED_DRAFT);
    }

    // ── 6～8：範圍 ────────────────────────────────────────────────────────────────

    @Test
    void step6_aScopeIdThatDoesNotBelongToTheProjectIs400() {
        Fixture f = prjA("foreign", 4);
        Fixture other = prjA("other", 4);
        Resp resp = execute(f.projectId(), scope("SELECTED", List.of(other.g1()), List.of(other.t1())));
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.SCOPE_INVALID);
        assertThat(resp.<List<String>>read("$.details.invalidGoalIds")).containsExactly(other.g1());
        assertThat(resp.<List<String>>read("$.details.invalidTaskIds")).containsExactly(other.t1());
        assertThat(MINI.countRequests("POST /autoclaude/runs")).isZero();
    }

    @Test
    void step7a_aSelectedTaskThatIsAlreadyCompletedIs409() {
        Fixture f = prjA("done", 4);
        setTaskStatus(f.t1(), "COMPLETED");
        Resp resp = execute(f.projectId(), scope("SELECTED", List.of(), List.of(f.t1())));
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.SCOPE_ALREADY_DONE);
        assertThat(resp.<List<String>>read("$.details.taskIds")).containsExactly(f.t1());
    }

    @Test
    void step7b_selectingAGoalWhoseUnselectedPrerequisiteIsNotDoneIs409() {
        Fixture f = prjA("deps", 4);
        Resp resp = execute(f.projectId(), scope("SELECTED", List.of(f.g2()), List.of()));
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.SCOPE_MISSING_DEPENDENCIES);
        assertThat(resp.<List<String>>read("$.details.missingGoalIds")).containsExactly(f.g1());
    }

    @Test
    void step7b_aPrerequisiteThatIsAlreadyCompletedDoesNotBlockTheSelection() {
        Fixture f = prjA("deps-done", 4);
        jdbc.update("update console.goals set status = 'COMPLETED' where id = ?", UUID.fromString(f.g1()));
        setTaskStatus(f.t1(), "COMPLETED");
        setTaskStatus(f.t2(), "COMPLETED");
        Resp resp = execute(f.projectId(), scope("SELECTED", List.of(f.g2()), List.of()));
        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<List<String>>read("$.data.scope.goalIds")).containsExactly(f.g2());
    }

    @Test
    void step7c_nothingLeftToExecuteIs409() {
        Fixture f = prjA("nothing", 4);
        f.taskIds().forEach(id -> setTaskStatus(id, "COMPLETED"));
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.NOTHING_TO_EXECUTE);
        assertThat(MINI.countRequests("POST /autoclaude/runs")).isZero();
    }

    // ── 9a～9f：物化（皆 422、不呼叫 Bridge）──────────────────────────────────────

    @Test
    void step9a_aPromptOver20000CharactersIs422() {
        Fixture f = prjA("long", 4);
        Resp task = api.post(operator(), "/api/v1/goals/" + f.g1() + "/tasks",
                Map.of("name", "超長", "passCriteria", "- x", "description", "字".repeat(20_100)));
        assertThat(task.status()).isEqualTo(201);
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.PROMPT_TOO_LONG);
        assertThat(resp.<String>read("$.details.taskId")).isEqualTo(task.id());
        assertThat(resp.<Integer>read("$.details.limit")).isEqualTo(20_000);
        assertThat(resp.<Integer>read("$.details.length")).isGreaterThan(20_000);
        assertThat(resp.<String>read("$.details.stepId")).startsWith("G1-T");
        assertThat(MINI.countRequests("POST /autoclaude/runs")).isZero();
    }

    @Test
    void step9b_anEvaluatorCommandWithADeniedCharacterIs422EvenWhenItWasWrittenBehindTheApi() {
        Fixture f = prjA("deny", 4);
        jdbc.update("update console.tasks set evaluator_command = 'pytest -q; rm -rf /' where id = ?",
                UUID.fromString(f.t2()));
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.EVALUATOR_DENIED_CHARS);
        assertThat(resp.<String>read("$.details.taskId")).isEqualTo(f.t2());
        assertThat(resp.<List<String>>read("$.details.chars")).contains(";");
    }

    @Test
    void step9c_anExecutableOutsideTheAllowlistIs422AndAPathPrefixAndExeSuffixAreStripped() {
        Fixture f = prjA("allow", 4);
        jdbc.update("update console.tasks set evaluator_command = 'bash -c x' where id = ?", UUID.fromString(f.t1()));
        Resp denied = execute(f.projectId(), Map.of());
        assertThat(denied.status()).isEqualTo(422);
        assertThat(denied.<String>read("$.reason")).isEqualTo(ErrorReasons.EVALUATOR_NOT_ALLOWED);
        assertThat(denied.<String>read("$.details.executable")).isEqualTo("bash");

        jdbc.update("update console.tasks set evaluator_command = 'C:\\tools\\PyTest.EXE -q' where id = ?",
                UUID.fromString(f.t1()));
        MINI.manualSteps = true;
        assertThat(execute(f.projectId(), Map.of()).status()).as("去路徑與 .exe、不分大小寫").isEqualTo(201);
    }

    @Test
    void step9d_anExpectedOutputRegexThatDoesNotCompileIs422() {
        Fixture f = prjA("regex", 4);
        jdbc.update("update console.tasks set expected_output_regex = '[' where id = ?", UUID.fromString(f.t3()));
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.REGEX_NOT_COMPILABLE);
        assertThat(resp.<String>read("$.details.taskId")).isEqualTo(f.t3());
    }

    @Test
    void step9e_moreThan500TasksInTheScopeIs422() {
        Fixture f = prjA("many", 4);
        jdbc.update("insert into console.tasks (id, goal_id, name, pass_criteria, signed_off) "
                + "select gen_random_uuid(), ?, 'bulk-' || g, 'c', true from generate_series(1, 499) g",
                UUID.fromString(f.g1()));
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.TOO_MANY_TASKS);
        assertThat(resp.<Integer>read("$.details.count")).isEqualTo(502);
        assertThat(resp.<Integer>read("$.details.limit")).isEqualTo(500);
    }

    @Test
    void step9f_aTaskMaxRetriesOver20IsTheSecondLineOfDefence() {
        Fixture f = prjA("retries", 4);
        jdbc.update("update console.tasks set max_retries = 21 where id = ?", UUID.fromString(f.t2()));
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.MAX_RETRIES_EXCEEDED);
        assertThat(resp.<String>read("$.details.taskId")).isEqualTo(f.t2());
        assertThat(resp.<Integer>read("$.details.maxRetries")).isEqualTo(21);
        assertThat(resp.<Integer>read("$.details.limit")).isEqualTo(20);
    }

    // ── 10：Bridge（失敗一律補償刪除，專案與任務狀態不動）─────────────────────────

    @Test
    void step10_aBusyLockAtTheBridgeIs409WithTheHolderAndTheNewRunRowIsCompensated() {
        Fixture first = prjA("same-path", 4);
        MINI.manualSteps = true;
        String holder = startRun(first.projectId());

        Fixture second = prjA("same-path", 4);
        Resp resp = execute(second.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.LOCK_HELD);
        assertThat(resp.<String>read("$.details.holderRunId")).isEqualTo(holder);
        assertCompensated(second, 1);
        assertThat(consumers.isRunning(UUID.fromString(holder))).as("持鎖者的消費者不受影響").isTrue();
    }

    @Test
    void step10_aBridgeValidationRejectionIs422WithTheViolationsPassedThroughVerbatim() {
        Fixture f = prjA("rejected", 4);
        MINI.failNext("start", 422, Map.of("code", 422, "reason", "invalid_request", "violations",
                List.of(Map.of("field", "playbook.tasks[1].prompt", "rule", "forbidden_chars", "message", "含禁用字元"))));
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_REJECTED);
        assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo("invalid_request");
        assertThat(resp.<List<Map<String, Object>>>read("$.details.violations")).hasSize(1);
        assertThat(resp.<String>read("$.details.violations[0].field")).isEqualTo("playbook.tasks[1].prompt");
        assertCompensated(f);
    }

    @Test
    void step10_aBridgeServerErrorIs502AndTheEmptyRunWhichTheBridgeAlreadyMarkedFailedIsStillDeleted() {
        Fixture f = prjA("boom", 4);
        MINI.failNext("start", 500, Map.of("code", 500, "reason", "spawn_failed"));
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(502);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_ERROR);
        assertCompensated(f);
    }

    @Test
    void step10_anUnreachableBridgeIs502AndLeavesNoTrace() {
        Fixture f = prjA("down", 4);
        setting("autoclaude", "engineUrl", "http://127.0.0.1:1");
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(502);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.BRIDGE_UNREACHABLE);
        assertCompensated(f);
    }

    private void assertCompensated(Fixture f) {
        assertCompensated(f, 0);
    }

    /** 補償刪除之後：沒有 run 列、專案仍是建立時的狀態、任務仍是 PENDING、沒有為它啟動的事件消費者（別的 run 的除外）。 */
    private void assertCompensated(Fixture f, int otherActiveConsumers) {
        assertThat(countRuns(f.projectId())).as("補償刪除剛建的 execution_runs 列").isZero();
        assertThat(projectStatus(f.projectId())).isEqualTo("DRAFT");
        f.taskIds().forEach(id -> assertThat(taskStatus(id)).isEqualTo("PENDING"));
        assertThat(consumers.activeCount()).isEqualTo(otherActiveConsumers);
    }

    // ── 成功 ──────────────────────────────────────────────────────────────────────

    @Test
    void aSuccessfulExecuteReturns201WithTheContractShapeAndTheDefaultsAreApplied() {
        Fixture f = prjA("success", 2);
        MINI.manualSteps = true;
        Resp resp = execute(f.projectId(), Map.of());
        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<Integer>read("$.code")).isEqualTo(201);
        assertThat(resp.<String>read("$.data.projectId")).isEqualTo(f.projectId());
        assertThat(resp.<Integer>read("$.data.runNumber")).isEqualTo(1);
        assertThat(resp.<String>read("$.data.status")).isEqualTo("RUNNING");
        assertThat(resp.<String>read("$.data.bridgeStatus")).isEqualTo("RUNNING");
        assertThat(resp.<Integer>read("$.data.autonomyLevel")).as("預設取專案的自治等級").isEqualTo(2);
        assertThat(resp.<String>read("$.data.scope.mode")).isEqualTo("ALL");
        assertThat(resp.<List<String>>read("$.data.scope.goalIds")).isEmpty();
        assertThat(resp.<Integer>read("$.data.totalTokensUsed")).isZero();
        assertThat(resp.<Integer>read("$.data.tokenBudget")).as("預設取 execution.globalTokenBudget").isPositive();
        assertThat(resp.<String>read("$.data.startedAt")).isNotBlank();
        assertThat(resp.has("$.data.completedAt")).isFalse();
        assertThat(resp.has("$.data.scope.limits")).as("沒有限額就不輸出").isFalse();
        assertThat(resp.header("X-Trace-Id")).isNotBlank();
        // v1.3（D-11）：沒有金鑰、等級 2、旗標全 false → 沒人要求任何引擎能力，如實回 OFF／OFF（契約 §1.2.1 的範例）
        assertThat(resp.<String>read("$.data.engineCapabilities.autoMutation")).isEqualTo("OFF");
        assertThat(resp.<String>read("$.data.engineCapabilities.selfEvolution")).isEqualTo("OFF");
    }

    @Test
    void theRunRowTheProjectAndTheTasksAreSetUpBeforeTheResponseReturns() {
        Fixture f = prjA("readmodel", 3);
        MINI.manualSteps = true;
        String run = startRun(f.projectId(), Map.of("autonomyLevel", 5, "tokenBudget", 5000,
                "scope", Map.of("mode", "ALL", "limits", Map.of("taskTokens", 2000, "goalTokens", 4000))));
        Map<String, Object> row = jdbc.queryForMap("select autonomy_level, token_budget, scope::text as scope, "
                + "dag::text as dag, console_last_seq from console.execution_runs where id = ?", UUID.fromString(run));
        assertThat(row.get("autonomy_level")).isEqualTo(5);
        assertThat(row.get("token_budget")).isEqualTo(5000L);
        assertThat((String) row.get("scope")).contains("2000").contains("4000");
        assertThat((String) row.get("dag")).contains("G1-T1").contains("G1-T2").contains("G2-T1");
        assertThat(projectStatus(f.projectId())).isEqualTo("EXECUTING");
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1()))))
                .as("第一個任務在 STARTED 事件投影後轉 RUNNING").isTrue();
        assertThat(taskStatus(f.t2())).isEqualTo("QUEUED");
        assertThat(taskStatus(f.t3())).isEqualTo("QUEUED");
        assertThat(consumers.isRunning(UUID.fromString(run))).isTrue();
    }

    @Test
    void theBridgeRequestCarriesTheFlattenedPlaybookWithGoalTaskIdsAndNoSecretsInConfigOverrides() {
        Fixture f = prjA("playbook", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        Map<String, Object> request = mini(run).request;
        assertThat(request.get("run_id")).isEqualTo(run);
        assertThat(request.get("project")).isEqualTo("playbook");
        assertThat(request.get("execution_path")).isEqualTo("/e2e/playbook");
        @SuppressWarnings("unchecked")
        Map<String, Object> playbook = (Map<String, Object>) request.get("playbook");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> tasks = (List<Map<String, Object>>) playbook.get("tasks");
        assertThat(tasks).extracting(t -> t.get("step_id")).containsExactly("G1-T1", "G1-T2", "G2-T1");
        assertThat(tasks).extracting(t -> t.get("goal_task_id")).containsExactly(f.t1(), f.t2(), f.t3());
        assertThat(tasks).extracting(t -> t.get("max_retries")).containsOnly(1);
        assertThat((String) tasks.get(0).get("prompt")).contains("請輸出 [T1_DONE]");
        assertThat(tasks.get(0).get("expected_output_regex")).isEqualTo("\\[T1_DONE\\]");
        assertThat(request.toString()).doesNotContain("MINIMAX_API_KEY");
    }

    @Test
    void selectedScopeByTaskIdsRunsOnlyThoseTasksInDependencyOrder() {
        Fixture f = prjA("selected", 4);
        MINI.manualSteps = true;
        Resp resp = execute(f.projectId(), scope("SELECTED", List.of(), List.of(f.t3(), f.t1())));
        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<String>read("$.data.scope.mode")).isEqualTo("SELECTED");
        assertThat(resp.<List<String>>read("$.data.scope.taskIds")).containsExactlyInAnyOrder(f.t1(), f.t3());
        @SuppressWarnings("unchecked")
        Map<String, Object> playbook = (Map<String, Object>) mini(resp.id()).request.get("playbook");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> tasks = (List<Map<String, Object>>) playbook.get("tasks");
        assertThat(tasks).extracting(t -> t.get("goal_task_id")).containsExactly(f.t1(), f.t3());
    }

    @Test
    void aFinishedProjectCanBeExecutedAgainAfterANewTaskAndTheRunNumberIncrements() {
        Fixture f = prjA("again", 4);
        String first = startRun(f.projectId());
        assertThat(awaitProjected(first, "COMPLETED")).isTrue();
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "COMPLETED".equals(projectStatus(f.projectId())))).isTrue();

        createFixtureTask(f.g2(), "新增", 4);
        Resp second = execute(f.projectId(), Map.of());
        assertThat(second.status()).isEqualTo(201);
        assertThat(second.<Integer>read("$.data.runNumber")).isEqualTo(2);
        assertThat(second.<String>read("$.data.scope.mode")).isEqualTo("ALL");
        assertThat(awaitProjected(second.id(), "COMPLETED")).isTrue();
    }

    @Test
    void executeNeedsOperatorOrAbove() {
        Fixture f = prjA("rbac", 4);
        assertThat(api.post(viewer(), executePath(f.projectId()), Map.of()).status()).isEqualTo(403);
        assertThat(api.post(null, executePath(f.projectId()), Map.of()).status()).isEqualTo(401);
        assertThat(MINI.countRequests("POST /autoclaude/runs")).isZero();
    }
}
