package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/** 專案 API（PRD §5.1.1／§7.1.1、§7.1.4.1 專案 signoff）。 */
class ProjectApiIT extends AbstractApiIT {

    private static Map<String, Object> body(String name) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("name", name);
        body.put("executionPath", "/work/" + name.replace(' ', '-'));
        body.put("passCriteria", "- 測試通過率 >= 95%");
        return body;
    }

    // ---------------- 建立 ----------------

    @Test
    void manualCreateReturns201WithDraftStatusSignedOffTrueAndDefaults() {
        Resp resp = api.post(operator(), "/api/v1/projects", body("核心平台"));
        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<Integer>read("$.code")).isEqualTo(201);
        assertThat(resp.<String>read("$.data.name")).isEqualTo("核心平台");
        assertThat(resp.<String>read("$.data.status")).isEqualTo("DRAFT");
        assertThat(resp.<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(resp.<Integer>read("$.data.autonomyLevel")).isEqualTo(3);
        assertThat(resp.<String>read("$.data.createdBy")).isEqualTo("operator");
        assertThat(resp.<Integer>read("$.data.goalsCount")).isZero();
        assertThat(resp.<Integer>read("$.data.tasksCount")).isZero();
        assertThat(UUID.fromString(resp.id())).isNotNull();
    }

    /** v1.5（契約 §1.10.5）：ProjectResponse／ProjectDetailResponse 帶 SDD 綁定三欄（預設 null）；列表項（ProjectSummaryResponse）不帶；請求帶了也不採用。 */
    @Test
    void projectResponsesCarryNullSddBindingFieldsAndIgnoreThemOnInput() {
        Map<String, Object> request = body("綁定欄位");
        request.put("sddProject", "forged");
        request.put("sddSpecDir", "/forged");
        request.put("sddSpecFile", "/forged/TCS.md");
        Resp created = api.post(operator(), "/api/v1/projects", request);
        assertThat(created.status()).isEqualTo(201);
        for (String field : List.of("sddProject", "sddSpecDir", "sddSpecFile")) {
            assertThat(created.<Object>read("$.data." + field)).as("create " + field).isNull();
        }

        Resp detail = api.get(viewer(), "/api/v1/projects/" + created.id());
        Resp updated = api.put(operator(), "/api/v1/projects/" + created.id(), Map.of("description", "改說明"));
        for (String field : List.of("sddProject", "sddSpecDir", "sddSpecFile")) {
            assertThat(detail.<Object>read("$.data." + field)).as("detail " + field).isNull();
            assertThat(updated.<Object>read("$.data." + field)).as("update " + field).isNull();
        }
        assertThat(jdbc.queryForObject("select sdd_project from console.projects where id = ?::uuid", String.class,
                created.id())).as("POST /projects 不收這三欄（契約 §0.5 寫入規則②）").isNull();

        Resp list = api.get(viewer(), "/api/v1/projects");
        assertThat(list.<List<Map<String, Object>>>read("$.data.content").get(0)).doesNotContainKey("sddProject");
    }

    @Test
    void draftTrueCreatesAnUnsignedProjectAndCustomAutonomyIsKept() {
        Map<String, Object> draft = body("草案專案");
        draft.put("draft", true);
        draft.put("autonomyLevel", 7);
        Resp resp = api.post(operator(), "/api/v1/projects", draft);
        assertThat(resp.status()).isEqualTo(201);
        assertThat(resp.<Boolean>read("$.data.signedOff")).isFalse();
        assertThat(resp.<Integer>read("$.data.autonomyLevel")).isEqualTo(7);
    }

    @Test
    void invalidCreateInputIsRejectedWithFieldErrors() {
        Map<String, Object> bad = new LinkedHashMap<>();
        bad.put("name", " ");
        bad.put("executionPath", "relative/path");
        bad.put("passCriteria", "");
        bad.put("autonomyLevel", 11);
        Resp resp = api.post(operator(), "/api/v1/projects", bad);
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.message")).isEqualTo("Validation failed");
        assertThat(resp.errorFields()).contains("name", "passCriteria", "autonomyLevel");

        // Bean Validation 放行、由 domain 把關的規則（絕對路徑）也要是 400，且有欄位名。
        Map<String, Object> relativePath = body("路徑錯誤");
        relativePath.put("executionPath", "relative/path");
        Resp relative = api.post(operator(), "/api/v1/projects", relativePath);
        assertThat(relative.status()).isEqualTo(400);
        assertThat(relative.errorFields()).containsExactly("executionPath");
    }

    @Test
    void windowsAndUncAbsolutePathsAreAccepted() {
        for (String path : List.of("C:\\work\\proj", "D:/work/proj", "\\\\server\\share\\proj")) {
            Map<String, Object> b = body("path-" + Math.abs(path.hashCode()));
            b.put("executionPath", path);
            assertThat(api.post(operator(), "/api/v1/projects", b).status()).as(path).isEqualTo(201);
        }
    }

    // ---------------- 列表 ----------------

    @Test
    void listPaginatesAndReportsTotals() {
        for (int i = 1; i <= 12; i++) {
            createProject(String.format("分頁專案 %02d", i));
        }
        Resp first = api.get(viewer(), "/api/v1/projects?page=0&size=5&sort=name,asc");
        assertThat(first.status()).isEqualTo(200);
        assertThat(first.<Integer>read("$.data.page")).isZero();
        assertThat(first.<Integer>read("$.data.size")).isEqualTo(5);
        assertThat(first.<Integer>read("$.data.totalElements")).isEqualTo(12);
        assertThat(first.<Integer>read("$.data.totalPages")).isEqualTo(3);
        assertThat(first.<List<String>>read("$.data.content[*].name"))
                .containsExactly("分頁專案 01", "分頁專案 02", "分頁專案 03", "分頁專案 04", "分頁專案 05");

        Resp last = api.get(viewer(), "/api/v1/projects?page=2&size=5&sort=name,asc");
        assertThat(last.<List<String>>read("$.data.content[*].name")).containsExactly("分頁專案 11", "分頁專案 12");
    }

    @Test
    void defaultSortIsUpdatedAtDescendingAndNameSortsBothWays() throws InterruptedException {
        String older = createProject("Alpha");
        Thread.sleep(15);
        String newer = createProject("Beta");
        assertThat(api.get(viewer(), "/api/v1/projects").<List<String>>read("$.data.content[*].id"))
                .containsExactly(newer, older);
        assertThat(api.get(viewer(), "/api/v1/projects?sort=name,desc").<List<String>>read("$.data.content[*].name"))
                .containsExactly("Beta", "Alpha");
        assertThat(api.get(viewer(), "/api/v1/projects?sort=name").<List<String>>read("$.data.content[*].name"))
                .as("只給欄位時預設升冪").containsExactly("Alpha", "Beta");
        assertThat(api.get(viewer(), "/api/v1/projects?sort=createdAt,asc").<List<String>>read("$.data.content[*].id"))
                .containsExactly(older, newer);
    }

    @Test
    void nameSearchIsCaseInsensitiveAndTreatsWildcardCharactersLiterally() {
        createProject("Core Platform");
        createProject("core_v2");
        createProject("Other");
        assertThat(api.get(viewer(), "/api/v1/projects?q=CORE&sort=name").<List<String>>read("$.data.content[*].name"))
                .containsExactly("Core Platform", "core_v2");
        assertThat(api.get(viewer(), "/api/v1/projects?q=core_").<List<String>>read("$.data.content[*].name"))
                .as("_ 是字面底線，不是單字元萬用字元").containsExactly("core_v2");
        assertThat(api.get(viewer(), "/api/v1/projects?q=%25").<Integer>read("$.data.totalElements"))
                .as("% 是字面百分號").isZero();
    }

    @Test
    void sqlMetaCharactersInSearchTextAndNamesAreNeverInterpretedAsSql() {
        // NFR-9.2-04：全部經 JPA 參數化查詢。這些字串若被拼進 SQL，會刪表或讓條件恆真。
        createProject("Keep me");
        for (String payload : List.of("x'); DROP TABLE console.projects; --", "' OR '1'='1", "%' OR 1=1 --",
                "\\'; delete from console.projects; --")) {
            Resp resp = api.get(viewer(), "/api/v1/projects?q=" + URLEncoder.encode(payload, StandardCharsets.UTF_8));
            assertThat(resp.status()).as(payload).isEqualTo(200);
            assertThat(resp.<Integer>read("$.data.totalElements")).as(payload + "：不是名稱比對，也不是恆真條件").isZero();
        }
        assertThat(api.get(viewer(), "/api/v1/projects").<Integer>read("$.data.totalElements")).isEqualTo(1);

        String hostile = "Robert'); DROP TABLE console.projects;--";
        Map<String, Object> evil = body("placeholder");
        evil.put("name", hostile);
        String id = createProject(evil);
        assertThat(api.get(viewer(), "/api/v1/projects/" + id).<String>read("$.data.name")).isEqualTo(hostile);
        assertThat(jdbc.queryForObject("select count(*) from console.projects", Integer.class)).isEqualTo(2);
    }

    @Test
    void statusFilterAndInvalidQueryParametersAreHandled() {
        String ready = createProject("Ready One");
        createProject("Draft One");
        setProjectStatus(ready, "READY");
        assertThat(api.get(viewer(), "/api/v1/projects?status=READY").<List<String>>read("$.data.content[*].name"))
                .containsExactly("Ready One");
        assertThat(api.get(viewer(), "/api/v1/projects?status=BOGUS").status()).isEqualTo(400);
        assertThat(api.get(viewer(), "/api/v1/projects?sort=password,asc").status()).isEqualTo(400);
        assertThat(api.get(viewer(), "/api/v1/projects?sort=name,sideways").status()).isEqualTo(400);
        assertThat(api.get(viewer(), "/api/v1/projects?size=0").status()).isEqualTo(400);
        assertThat(api.get(viewer(), "/api/v1/projects?size=101").status()).isEqualTo(400);
        assertThat(api.get(viewer(), "/api/v1/projects?page=-1").status()).isEqualTo(400);
        assertThat(api.get(viewer(), "/api/v1/projects?page=abc").status()).isEqualTo(400);
    }

    @Test
    void listShowsOnlyLiveGoalAndTaskCounts() {
        String project = createProject("Counts");
        String g1 = createGoal(project, "G1");
        String g2 = createGoal(project, "G2");
        String t1 = createTask(g1, "T1");
        createTask(g1, "T2");
        createTask(g2, "T3");
        setTaskStatus(t1, "COMPLETED");
        api.delete(operator(), "/api/v1/tasks/" + createTask(g2, "T4-deleted"));
        api.delete(operator(), "/api/v1/goals/" + createGoal(project, "G3-deleted"));

        Resp list = api.get(viewer(), "/api/v1/projects?q=Counts");
        assertThat(list.<Integer>read("$.data.content[0].goalsCount")).isEqualTo(2);
        assertThat(list.<Integer>read("$.data.content[0].tasksCount")).isEqualTo(3);
        assertThat(list.<Integer>read("$.data.content[0].tasksDone")).isEqualTo(1);
        assertThat(list.has("$.data.content[0].updatedAt")).isTrue();
    }

    // ---------------- 詳情 ----------------

    @Test
    void detailIncludesGoalsWithTaskCountsInSortOrder() {
        String project = createProject("Detail");
        String g1 = createGoal(project, "第一個目標");
        String g2 = createGoal(project, "第二個目標");
        String t1 = createTask(g1, "T1");
        createTask(g1, "T2");
        setTaskStatus(t1, "COMPLETED");

        Resp resp = api.get(viewer(), "/api/v1/projects/" + project);
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.passCriteria")).isEqualTo("- 全部通過");
        assertThat(resp.<Integer>read("$.data.goalsCount")).isEqualTo(2);
        assertThat(resp.<Integer>read("$.data.tasksCount")).isEqualTo(2);
        assertThat(resp.<List<String>>read("$.data.goals[*].id")).containsExactly(g1, g2);
        assertThat(resp.<Integer>read("$.data.goals[0].taskCount")).isEqualTo(2);
        assertThat(resp.<Integer>read("$.data.goals[0].completedTaskCount")).isEqualTo(1);
        assertThat(resp.<Integer>read("$.data.goals[1].taskCount")).isZero();
        assertThat(resp.<Integer>read("$.data.goals[0].sortOrder")).isZero();
        assertThat(resp.<Integer>read("$.data.goals[1].sortOrder")).isEqualTo(1);
    }

    // ---------------- 更新 ----------------

    @Test
    void putUpdatesOnlyProvidedFieldsAndClearsDescriptionWithBlank() {
        Map<String, Object> create = body("Update me");
        create.put("description", "舊說明");
        String id = createProject(create);

        Resp resp = api.put(operator(), "/api/v1/projects/" + id,
                Map.of("name", "新名稱", "autonomyLevel", 9, "description", ""));
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.name")).isEqualTo("新名稱");
        assertThat(resp.<Integer>read("$.data.autonomyLevel")).isEqualTo(9);
        assertThat(resp.<Object>read("$.data.description")).isNull();
        assertThat(resp.<String>read("$.data.executionPath")).isEqualTo("/work/Update-me");
    }

    @Test
    void whileExecutingOnlyNameAndDescriptionCanChangeAndOtherChangesAre409WithReason() {
        String id = createProject("Running");
        setProjectStatus(id, "EXECUTING");

        Resp ok = api.put(operator(), "/api/v1/projects/" + id, Map.of("name", "Running renamed", "description", "新說明"));
        assertThat(ok.status()).isEqualTo(200);
        assertThat(ok.<String>read("$.data.name")).isEqualTo("Running renamed");

        Resp blocked = api.put(operator(), "/api/v1/projects/" + id,
                Map.of("executionPath", "/somewhere/else", "autonomyLevel", 8));
        assertThat(blocked.status()).isEqualTo(409);
        assertThat(blocked.<String>read("$.reason")).contains("EXECUTING");
        assertThat(blocked.<List<String>>read("$.details.fields")).containsExactly("executionPath", "autonomyLevel");
        assertThat(api.get(viewer(), "/api/v1/projects/" + id).<String>read("$.data.executionPath"))
                .as("409 不可留下半套修改").isEqualTo("/work/Running");
    }

    @Test
    void manualStatusChangeIsLimitedToDraftAndReadyAndFollowsTheStateMachine() {
        String id = createProject("Status");
        assertThat(api.put(operator(), "/api/v1/projects/" + id, Map.of("status", "READY")).<String>read("$.data.status"))
                .isEqualTo("READY");
        assertThat(api.put(operator(), "/api/v1/projects/" + id, Map.of("status", "DRAFT")).<String>read("$.data.status"))
                .isEqualTo("DRAFT");
        // 引擎驅動的狀態不能手動設，即使轉移圖上合法（READY→EXECUTING）。
        api.put(operator(), "/api/v1/projects/" + id, Map.of("status", "READY"));
        Resp toExecuting = api.put(operator(), "/api/v1/projects/" + id, Map.of("status", "EXECUTING"));
        assertThat(toExecuting.status()).isEqualTo(409);
        assertThat(toExecuting.<String>read("$.reason")).contains("不可手動轉移");
        // 狀態機本身不允許的轉移（DRAFT→COMPLETED）同樣 409。
        api.put(operator(), "/api/v1/projects/" + id, Map.of("status", "DRAFT"));
        assertThat(api.put(operator(), "/api/v1/projects/" + id, Map.of("status", "COMPLETED")).status()).isEqualTo(409);
    }

    // ---------------- 刪除 ----------------

    @Test
    void deleteIsSoftAndCascadesToGoalsAndTasks() {
        String project = createProject("To delete");
        String goal = createGoal(project, "G");
        String task = createTask(goal, "T");

        assertThat(api.delete(operator(), "/api/v1/projects/" + project).status()).isEqualTo(204);

        assertThat(api.get(viewer(), "/api/v1/projects/" + project).status()).isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/goals/" + goal).status()).isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + task).status()).isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/projects").<Integer>read("$.data.totalElements")).isZero();

        Map<String, Object> row = jdbc.queryForMap("select status, is_deleted from console.projects where id = ?",
                UUID.fromString(project));
        assertThat(row).containsEntry("status", "ARCHIVED").containsEntry("is_deleted", true);
        assertThat(jdbc.queryForObject("select is_deleted from console.goals where id = ?", Boolean.class,
                UUID.fromString(goal))).isTrue();
        assertThat(jdbc.queryForObject("select is_deleted from console.tasks where id = ?", Boolean.class,
                UUID.fromString(task))).isTrue();
    }

    @Test
    void executingProjectCannotBeDeleted() {
        String id = createProject("Busy");
        setProjectStatus(id, "EXECUTING");
        Resp resp = api.delete(operator(), "/api/v1/projects/" + id);
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).contains("EXECUTING");
        assertThat(api.get(viewer(), "/api/v1/projects/" + id).status()).isEqualTo(200);
    }

    // ---------------- signoff ----------------

    @Test
    void signoffOnADraftRecordsApproverAndUtcTime() {
        Map<String, Object> draft = body("Needs approval");
        draft.put("draft", true);
        String id = createProject(draft);

        Resp resp = api.post(operator(), "/api/v1/projects/" + id + "/signoff", Map.of("approver", "  Alice  "));
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(resp.<String>read("$.data.signedOffBy")).isEqualTo("Alice");
        assertThat(resp.<String>read("$.data.signedOffAt")).endsWith("Z");
    }

    @Test
    void signoffWithoutAnApproverIsFourHundred() {
        Map<String, Object> draft = body("No anonymous");
        draft.put("draft", true);
        String id = createProject(draft);
        for (String payload : List.of("{}", "{\"approver\":\"\"}", "{\"approver\":\"   \"}", "{\"approver\":null}")) {
            Resp resp = api.raw(operator(), HttpMethod.POST, "/api/v1/projects/" + id + "/signoff", payload);
            assertThat(resp.status()).as(payload).isEqualTo(400);
            assertThat(resp.errorFields()).as(payload).containsExactly("approver");
        }
        assertThat(api.get(viewer(), "/api/v1/projects/" + id).<Boolean>read("$.data.signedOff")).isFalse();
    }

    @Test
    void signingOffTwiceIsConflictAndKeepsTheFirstApprover() {
        Map<String, Object> draft = body("Twice");
        draft.put("draft", true);
        String id = createProject(draft);
        api.post(operator(), "/api/v1/projects/" + id + "/signoff", Map.of("approver", "Alice"));
        Resp second = api.post(operator(), "/api/v1/projects/" + id + "/signoff", Map.of("approver", "Mallory"));
        assertThat(second.status()).isEqualTo(409);
        assertThat(api.get(viewer(), "/api/v1/projects/" + id).<String>read("$.data.signedOffBy")).isEqualTo("Alice");
    }

    // ---------------- 404／格式錯誤 ----------------

    @Test
    void unknownIdsAre404AndMalformedIdsAre400() {
        String ghost = UUID.randomUUID().toString();
        assertThat(api.get(viewer(), "/api/v1/projects/" + ghost).status()).isEqualTo(404);
        assertThat(api.put(operator(), "/api/v1/projects/" + ghost, Map.of("name", "x")).status()).isEqualTo(404);
        assertThat(api.delete(operator(), "/api/v1/projects/" + ghost).status()).isEqualTo(404);
        assertThat(api.post(operator(), "/api/v1/projects/" + ghost + "/signoff", Map.of("approver", "a")).status())
                .isEqualTo(404);
        Resp malformed = api.get(viewer(), "/api/v1/projects/not-a-uuid");
        assertThat(malformed.status()).isEqualTo(400);
        assertThat(malformed.errorFields()).containsExactly("id");
    }

    @Test
    void malformedJsonBodyIsFourHundredNotFiveHundred() {
        Resp resp = api.raw(operator(), HttpMethod.POST, "/api/v1/projects", "{\"name\": ");
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo("MALFORMED_REQUEST_BODY");
    }
}
