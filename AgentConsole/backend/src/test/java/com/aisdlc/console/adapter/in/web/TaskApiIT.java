package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.ValueSource;
import com.aisdlc.console.domain.model.task.TaskStatus;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpMethod;

import static org.assertj.core.api.Assertions.assertThat;

/** 任務 API（PRD §5.1.3／§7.1.3、§7.1.4.1 任務 signoff）與 NFR-SEC-03 輸入消毒。 */
class TaskApiIT extends AbstractApiIT {

    private String goal;

    @BeforeEach
    void createParentGoal() {
        goal = createGoal(createProject("Tasks parent"), "G");
    }

    private String tasksUrl() {
        return "/api/v1/goals/" + goal + "/tasks";
    }

    private Map<String, Object> task(String name) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("name", name);
        body.put("passCriteria", "- 完成 " + name);
        return body;
    }

    // ---------------- 建立／列表／詳情 ----------------

    @Test
    void createReturns201WithDocumentedDefaults() {
        Resp resp = api.post(operator(), tasksUrl(), task("T1"));
        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<String>read("$.data.status")).isEqualTo("PENDING");
        assertThat(resp.<Integer>read("$.data.retryCount")).isZero();
        assertThat(resp.<Integer>read("$.data.maxRetries")).as("PRD：預設 3").isEqualTo(3);
        assertThat(resp.<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(resp.<Integer>read("$.data.sortOrder")).isZero();
        assertThat(resp.<String>read("$.data.goalId")).isEqualTo(goal);
        assertThat(api.post(operator(), tasksUrl(), task("T2")).<Integer>read("$.data.sortOrder")).isEqualTo(1);
    }

    @Test
    void createAcceptsTheMachineReadablePassCriteriaAndStoresTheSpecAsAJsonbObject() {
        Map<String, Object> body = task("Full");
        body.put("evaluatorCommand", "pytest -q tests/");
        body.put("expectedOutputRegex", "^OK \\d+$");
        body.put("estimatedTokens", 1200);
        body.put("maxRetries", 5);
        body.put("passCriteriaSpec", Map.of("kind", "composite", "checks", List.of(Map.of("name", "unit"))));
        Resp resp = api.post(operator(), tasksUrl(), body);
        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<String>read("$.data.evaluatorCommand")).isEqualTo("pytest -q tests/");
        assertThat(resp.<String>read("$.data.expectedOutputRegex")).isEqualTo("^OK \\d+$");
        assertThat(resp.<Integer>read("$.data.estimatedTokens")).isEqualTo(1200);
        assertThat(resp.<Integer>read("$.data.maxRetries")).isEqualTo(5);
        assertThat(resp.<String>read("$.data.passCriteriaSpec.kind")).isEqualTo("composite");
        assertThat(resp.<String>read("$.data.passCriteriaSpec.checks[0].name")).isEqualTo("unit");
        assertThat(jdbc.queryForObject("select jsonb_typeof(pass_criteria_spec) from console.tasks where id = ?",
                String.class, UUID.fromString(resp.id()))).as("jsonb 物件，不是被引號包住的字串").isEqualTo("object");
    }

    @Test
    void draftTaskIsNotSignedOffAndInvalidInputIs400() {
        Map<String, Object> draft = task("Draft");
        draft.put("draft", true);
        assertThat(api.post(operator(), tasksUrl(), draft).<Boolean>read("$.data.signedOff")).isFalse();

        Map<String, Object> bad = new LinkedHashMap<>();
        bad.put("name", "");
        bad.put("passCriteria", " ");
        bad.put("maxRetries", -1);
        bad.put("estimatedTokens", -5);
        Resp resp = api.post(operator(), tasksUrl(), bad);
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.errorFields()).containsExactlyInAnyOrder("name", "passCriteria", "maxRetries",
                "estimatedTokens");
    }

    /**
     * 契約 §0.8／AR-14：最大重試次數上限 20（Phase 3 的匯入草案與 Phase 4 的執行都以此為界；引擎無上限會讓失敗步驟重試到天荒地老）。
     * 邊界兩側都要有證據：20 可以、21 不行、負數不行。
     */
    @Test
    void maxRetriesIsCappedAtTwentyOnCreateAndUpdate() {
        for (int ok : new int[] {0, 1, 20}) {
            Map<String, Object> body = task("Retries " + ok);
            body.put("maxRetries", ok);
            Resp created = api.post(operator(), tasksUrl(), body);
            assertThat(created.status()).as("maxRetries=" + ok).isEqualTo(201);
            assertThat(created.<Integer>read("$.data.maxRetries")).isEqualTo(ok);
        }
        for (int bad : new int[] {21, 25, 1000, -1}) {
            Map<String, Object> body = task("Too many " + bad);
            body.put("maxRetries", bad);
            Resp rejected = api.post(operator(), tasksUrl(), body);
            assertThat(rejected.status()).as("maxRetries=" + bad).isEqualTo(400);
            assertThat(rejected.errorFields()).containsExactly("maxRetries");
        }

        String id = createTask(goal, "Updatable");
        assertThat(api.put(operator(), "/api/v1/tasks/" + id, Map.of("maxRetries", 20)).status()).isEqualTo(200);
        Resp tooMany = api.put(operator(), "/api/v1/tasks/" + id, Map.of("maxRetries", 25));
        assertThat(tooMany.status()).isEqualTo(400);
        assertThat(tooMany.errorFields()).containsExactly("maxRetries");
        assertThat(api.get(viewer(), "/api/v1/tasks/" + id).<Integer>read("$.data.maxRetries"))
                .as("被拒絕的更新沒有改值").isEqualTo(20);
    }

    @Test
    void createUnderAMissingGoalIs404() {
        assertThat(api.post(operator(), "/api/v1/goals/" + UUID.randomUUID() + "/tasks", task("T")).status())
                .isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/goals/" + UUID.randomUUID() + "/tasks").status()).isEqualTo(404);
    }

    @Test
    void listIsOrderedAndHidesDeletedTasks() {
        String t1 = createTask(goal, "T1");
        String t2 = createTask(goal, "T2");
        String t3 = createTask(goal, "T3");
        api.delete(operator(), "/api/v1/tasks/" + t2);
        Resp list = api.get(viewer(), tasksUrl());
        assertThat(list.status()).isEqualTo(200);
        assertThat(list.<List<String>>read("$.data[*].id")).containsExactly(t1, t3);
        assertThat(list.<String>read("$.data[0].status")).isEqualTo("PENDING");
        assertThat(list.has("$.data[0].updatedAt")).isTrue();
    }

    @Test
    void detailCarriesTheExecutionLogAndAnEmptyExecutionHistory() {
        String id = createTask(goal, "Logged");
        jdbc.update("update console.tasks set execution_log = ? where id = ?", "[14:32:05] 開始執行",
                UUID.fromString(id));
        Resp detail = api.get(viewer(), "/api/v1/tasks/" + id);
        assertThat(detail.status()).isEqualTo(200);
        assertThat(detail.<String>read("$.data.executionLog")).isEqualTo("[14:32:05] 開始執行");
        assertThat(detail.<List<Object>>read("$.data.executionHistory")).isEmpty();
        assertThat(api.get(viewer(), "/api/v1/tasks/" + UUID.randomUUID()).status()).isEqualTo(404);
    }

    // ---------------- NFR-SEC-03 消毒 ----------------

    @ParameterizedTest(name = "evaluatorCommand 含 [{0}] 被擋")
    @ValueSource(strings = {"!", "`", ">", "<", "~", "$", "&", ";"})
    void everyBlacklistedCharacterIsRejectedOnCreateAndUpdateAndNamedInTheResponse(String badChar) {
        Map<String, Object> body = task("Sanitize");
        body.put("evaluatorCommand", "echo hi " + badChar + " there");
        Resp create = api.post(operator(), tasksUrl(), body);
        assertThat(create.status()).isEqualTo(400);
        assertThat(create.errorFields()).containsExactly("evaluatorCommand");
        assertThat(create.<String>read("$.errors[0].message")).contains(badChar);
        assertThat(create.<List<String>>read("$.details.violations")).containsExactly(badChar);

        String id = createTask(goal, "Clean");
        Resp update = api.put(operator(), "/api/v1/tasks/" + id, Map.of("evaluatorCommand", "echo " + badChar));
        assertThat(update.status()).isEqualTo(400);
        assertThat(update.<List<String>>read("$.details.violations")).containsExactly(badChar);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + id).<Object>read("$.data.evaluatorCommand")).isNull();
    }

    @Test
    void severalViolationsAreAllListedAndNewlinesAreRejectedToo() {
        Map<String, Object> body = task("Many");
        body.put("evaluatorCommand", "a; b && c $d");
        Resp resp = api.post(operator(), tasksUrl(), body);
        assertThat(resp.<List<String>>read("$.details.violations")).containsExactly(";", "&", "$");

        body.put("evaluatorCommand", "echo ok\nrm -rf x");
        assertThat(api.post(operator(), tasksUrl(), body).status()).isEqualTo(400);
    }

    @Test
    void anUncompilableRegexOrTooLongFieldsAreRejected() {
        Map<String, Object> body = task("Regex");
        body.put("expectedOutputRegex", "([a-z");
        Resp regex = api.post(operator(), tasksUrl(), body);
        assertThat(regex.status()).isEqualTo(400);
        assertThat(regex.errorFields()).containsExactly("expectedOutputRegex");

        Map<String, Object> tooLong = task("Long");
        tooLong.put("evaluatorCommand", "x".repeat(1001));
        assertThat(api.post(operator(), tasksUrl(), tooLong).status()).isEqualTo(400);
    }

    @Test
    void theSameRulesApplyInsideTheStructuredPassCriteriaSpec() {
        Map<String, Object> dirty = task("Spec dirty");
        dirty.put("passCriteriaSpec", Map.of("all", List.of(Map.of("evaluatorCommand", "ok; rm -rf /"))));
        Resp resp = api.post(operator(), tasksUrl(), dirty);
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.errorFields()).containsExactly("passCriteriaSpec.all[0].evaluatorCommand");

        Map<String, Object> badRegex = task("Spec regex");
        badRegex.put("passCriteriaSpec", Map.of("expectedOutputRegex", "(("));
        assertThat(api.post(operator(), tasksUrl(), badRegex).status()).isEqualTo(400);

        Map<String, Object> clean = task("Spec clean");
        clean.put("passCriteriaSpec", Map.of("evaluatorCommand", "pytest -q", "note", "含 ; 的說明文字不是命令"));
        assertThat(api.post(operator(), tasksUrl(), clean).status()).as("只有 evaluatorCommand 欄位受消毒").isEqualTo(201);
    }

    @Test
    void thePassCriteriaSpecMustBeAJsonObject() {
        String body = "{\"name\":\"T\",\"passCriteria\":\"c\",\"passCriteriaSpec\":[1,2]}";
        assertThat(api.raw(operator(), HttpMethod.POST, tasksUrl(), body).status())
                .isEqualTo(400);
    }

    // ---------------- 更新 ----------------

    @Test
    void updateChangesProvidedFieldsAndBlankClearsOptionalOnes() {
        Map<String, Object> body = task("To update");
        body.put("evaluatorCommand", "pytest -q");
        body.put("expectedOutputRegex", "^OK$");
        body.put("passCriteriaSpec", Map.of("a", 1));
        String id = api.post(operator(), tasksUrl(), body).id();

        Resp resp = api.put(operator(), "/api/v1/tasks/" + id, Map.of("name", "Renamed", "maxRetries", 7,
                "description", "說明", "passCriteria", "新標準", "estimatedTokens", 900));
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.name")).isEqualTo("Renamed");
        assertThat(resp.<Integer>read("$.data.maxRetries")).isEqualTo(7);
        assertThat(resp.<String>read("$.data.evaluatorCommand")).isEqualTo("pytest -q");

        Map<String, Object> clear = new LinkedHashMap<>();
        clear.put("evaluatorCommand", "");
        clear.put("expectedOutputRegex", " ");
        clear.put("passCriteriaSpec", Map.of());
        Resp cleared = api.put(operator(), "/api/v1/tasks/" + id, clear);
        assertThat(cleared.<Object>read("$.data.evaluatorCommand")).isNull();
        assertThat(cleared.<Object>read("$.data.expectedOutputRegex")).isNull();
        assertThat(cleared.<Object>read("$.data.passCriteriaSpec")).isNull();
        assertThat(api.put(operator(), "/api/v1/tasks/" + id, Map.of("name", "")).status()).isEqualTo(400);
        assertThat(api.put(operator(), "/api/v1/tasks/" + UUID.randomUUID(), Map.of("name", "x")).status())
                .isEqualTo(404);
    }

    // ---------------- 刪除 ----------------

    @Test
    void aRunningTaskCannotBeDeletedButAnyOtherCanBe() {
        String running = createTask(goal, "Running");
        setTaskStatus(running, "RUNNING");
        Resp blocked = api.delete(operator(), "/api/v1/tasks/" + running);
        assertThat(blocked.status()).isEqualTo(409);
        assertThat(blocked.<String>read("$.reason")).contains("RUNNING");
        assertThat(api.get(viewer(), "/api/v1/tasks/" + running).status()).isEqualTo(200);

        String idle = createTask(goal, "Idle");
        assertThat(api.delete(operator(), "/api/v1/tasks/" + idle).status()).isEqualTo(204);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + idle).status()).isEqualTo(404);
        assertThat(jdbc.queryForObject("select is_deleted from console.tasks where id = ?", Boolean.class,
                UUID.fromString(idle))).isTrue();
        assertThat(api.delete(operator(), "/api/v1/tasks/" + idle).status()).isEqualTo(404);
    }

    // ---------------- retry ----------------

    @ParameterizedTest(name = "{0} 的任務可手動重試")
    @EnumSource(value = TaskStatus.class, names = {"FAILED", "ESCALATED"})
    void retryFromFailedOrEscalatedIncrementsRetryCountAndRequeues(TaskStatus from) {
        String id = createTask(goal, "Retry me");
        setTaskStatus(id, from.name());
        Resp resp = api.post(operator(), "/api/v1/tasks/" + id + "/retry");
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.status")).isEqualTo("QUEUED");
        assertThat(resp.<Integer>read("$.data.retryCount")).isEqualTo(1);
        assertThat(api.post(operator(), "/api/v1/tasks/" + id + "/retry").status())
                .as("QUEUED 不可再重試").isEqualTo(409);
    }

    @ParameterizedTest(name = "{0} 的任務不可重試（409）")
    @EnumSource(value = TaskStatus.class, mode = EnumSource.Mode.EXCLUDE, names = {"FAILED", "ESCALATED"})
    void retryFromAnyOtherStatusIsConflictAndChangesNothing(TaskStatus from) {
        String id = createTask(goal, "No retry");
        setTaskStatus(id, from.name());
        Resp resp = api.post(operator(), "/api/v1/tasks/" + id + "/retry");
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("目前狀態不可重試");
        Resp after = api.get(viewer(), "/api/v1/tasks/" + id);
        assertThat(after.<String>read("$.data.status")).isEqualTo(from.name());
        assertThat(after.<Integer>read("$.data.retryCount")).isZero();
    }

    @Test
    void retryOfAnUnknownTaskIs404() {
        assertThat(api.post(operator(), "/api/v1/tasks/" + UUID.randomUUID() + "/retry").status()).isEqualTo(404);
    }

    // ---------------- signoff ----------------

    @Test
    void taskSignoffFollowsTheSameRulesAsProjectsAndGoals() {
        Map<String, Object> draft = task("Draft");
        draft.put("draft", true);
        String id = api.post(operator(), tasksUrl(), draft).id();

        Resp missing = api.post(operator(), "/api/v1/tasks/" + id + "/signoff", Map.of());
        assertThat(missing.status()).isEqualTo(400);
        assertThat(missing.errorFields()).containsExactly("approver");

        Resp ok = api.post(operator(), "/api/v1/tasks/" + id + "/signoff", Map.of("approver", "Carol"));
        assertThat(ok.status()).isEqualTo(200);
        assertThat(ok.<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(ok.<String>read("$.data.signedOffBy")).isEqualTo("Carol");
        assertThat(api.post(operator(), "/api/v1/tasks/" + id + "/signoff", Map.of("approver", "Dave")).status())
                .isEqualTo(409);
        assertThat(api.post(operator(), "/api/v1/tasks/" + UUID.randomUUID() + "/signoff",
                Map.of("approver", "x")).status()).isEqualTo(404);
    }
}
