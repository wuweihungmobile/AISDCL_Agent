package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractOutboundIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.FakeHttpServer.Received;
import com.aisdlc.console.support.FakeHttpServer.Response;
import com.aisdlc.console.support.ImportFixtures;
import com.aisdlc.console.support.OutboundFakes;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 匯入主流程（Phase 3；契約 §1.1、E2E-01）：貼文字 → AI 解析（路徑 B）→ 編輯 → signoff → confirm → 專案全部 signedOff。
 * 為什麼重要：這是 PRD 的核心硬閘——AI 草案在人工 signoff 之前不可成為可執行的專案。每一步都驗「之後的狀態」而不只是狀態碼：
 * 未 signoff 的 confirm 不得留下任何專案；編輯會撤銷既有 signoff；confirm 建立的專案／目標／任務全部承襲同一個簽核者與時間。
 */
class ImportFlowApiIT extends AbstractOutboundIT {

    private static final String IMPORT = "/api/v1/import";
    private static final String EXEC_PATH = "/work/proj-import";
    private static final String APPROVER = "e2e-approver";

    private void stubOkModel() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                Response.json(200, ImportFixtures.chatCompletion(ImportFixtures.okTree())));
    }

    private String createMarkdown() {
        Resp created = api.post(operator(), IMPORT + "/text", Map.of("content", ImportFixtures.markdownDocument(null),
                "sourceFileName", "e2e-brd.md", "sourceType", "MARKDOWN"));
        assertThat(created.status()).isEqualTo(201);
        return created.id();
    }

    private Resp parse(String id) {
        return api.post(operator(), IMPORT + "/" + id + "/parse", Map.of("autonomyLevel", 3, "executionPath",
                EXEC_PATH, "additionalPrompt", "盡量少於 5 個任務"));
    }

    private Resp signoff(String id) {
        return api.post(operator(), IMPORT + "/" + id + "/signoff", Map.of("approver", APPROVER));
    }

    private Map<String, Object> currentTree(String id) {
        return api.get(operator(), IMPORT + "/" + id).read("$.data.parsedResult");
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> goals(Map<String, Object> tree) {
        return (List<Map<String, Object>>) tree.get("goals");
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> tasks(Map<String, Object> goal) {
        return (List<Map<String, Object>>) goal.get("tasks");
    }

    private Resp putTree(String id, Map<String, Object> tree) {
        return api.put(operator(), IMPORT + "/" + id + "/result", Map.of("parsedResult", tree));
    }

    private int projectsNamed(String name) {
        return jdbc.queryForObject("select count(*) from console.projects where name = ?", Integer.class, name);
    }

    // ── E2E-01 主流程 ───────────────────────────────────────────────────────────

    @Test
    void pastedMarkdownIsParsedEditedSignedOffAndConfirmedIntoAFullySignedOffProject() {
        stubOkModel();

        // 1. 建立
        Resp created = api.post(operator(), IMPORT + "/text", Map.of("content", ImportFixtures.markdownDocument(null),
                "sourceFileName", "e2e-brd.md", "sourceType", "MARKDOWN"));
        assertThat(created.status()).isEqualTo(201);
        assertThat(created.<String>read("$.data.status")).isEqualTo("UPLOADED");
        assertThat(created.<Boolean>read("$.data.signedOff")).isFalse();
        assertThat(created.<String>read("$.data.sourceType")).isEqualTo("MARKDOWN");
        assertThat(created.<String>read("$.data.sourceFileName")).isEqualTo("e2e-brd.md");
        assertThat(created.body()).as("列表／建立回應不帶原文與解析結果").doesNotContain("sourceContent")
                .doesNotContain("parsedResult");
        String id = created.id();

        // 2. parse
        Resp parsed = parse(id);
        assertThat(parsed.status()).isEqualTo(200);
        assertThat(parsed.<String>read("$.data.status")).isEqualTo("PARSED");
        assertThat(parsed.<String>read("$.data.path")).isEqualTo("LLM");
        assertThat(parsed.<String>read("$.data.aiModel")).isEqualTo("e2e-model");
        assertThat(parsed.<Integer>read("$.data.tokenUsed")).isEqualTo(1152);
        assertThat(parsed.<Boolean>read("$.data.signedOff")).isFalse();
        assertThat(parsed.<List<Object>>read("$.data.errors")).isEmpty();
        assertThat(parsed.<List<Object>>read("$.data.warnings")).isEmpty();
        assertThat(parsed.<List<Object>>read("$.data.parsedResult.goals")).hasSize(2);
        assertThat(parsed.<Integer>read("$.data.parsedResult.goals[0].tasks.length()")).isEqualTo(2);
        assertThat(parsed.<Integer>read("$.data.parsedResult.goals[1].tasks.length()")).isEqualTo(1);
        assertThat(parsed.<List<String>>read("$.data.parsedResult.goals[1].dependsOn")).containsExactly("g1");
        assertThat(parsed.<String>read("$.data.parsedResult.project.executionPath"))
                .as("LLM 建議的 /ignored 被丟棄").isEqualTo(EXEC_PATH);
        assertThat(parsed.<Integer>read("$.data.parsedResult.project.autonomyLevel")).isEqualTo(3);

        // 假模型端收到的請求
        assertThat(OutboundFakes.LLM.received()).hasSize(1);
        FakeLlmRequest request = new FakeLlmRequest(OutboundFakes.LLM.received().get(0));
        assertThat(request.method()).isEqualTo("POST");
        assertThat(request.path()).as("路徑就是 model.apiUrl 的路徑，後端沒有補任何路徑").isEqualTo("/v1/chat/completions");
        assertThat(request.header("authorization")).isEqualTo("Bearer sk-e2e-dummy");
        assertThat(request.string("$.model")).isEqualTo("e2e-model");
        assertThat(request.bool("$.stream")).isFalse();
        assertThat(request.string("$.response_format.type")).isEqualTo("json_object");
        assertThat(request.string("$.messages[0].role")).isEqualTo("system");
        assertThat(request.string("$.messages[1].content")).contains("自治等級: 3").contains("補充說明: 盡量少於 5 個任務")
                .contains(ImportFixtures.markdownDocument(null));

        // 3. 詳情
        Resp detail = api.get(viewer(), IMPORT + "/" + id);
        assertThat(detail.status()).isEqualTo(200);
        assertThat(detail.<String>read("$.data.sourceContent")).isEqualTo(ImportFixtures.markdownDocument(null));
        assertThat(detail.<String>read("$.data.parsePath")).isEqualTo("LLM");
        assertThat(detail.<Object>read("$.data.lastParseErrors")).isNull();
        assertThat(detail.<Object>read("$.data.parsedResult")).isEqualTo(parsed.<Object>read("$.data.parsedResult"));

        // 4. 編輯：g1 改名、g2 新增一個任務；請求帶的伺服器欄位被忽略
        Map<String, Object> tree = currentTree(id);
        goals(tree).get(0).put("name", "基礎建設");
        tasks(goals(tree).get(1)).add(ImportFixtures.doneTask("擴充", 4));
        tree.put("path", "SDD");
        tree.put("aiModel", "hacker-model");
        tree.put("tokenUsed", 1);
        Resp edited = putTree(id, tree);
        assertThat(edited.status()).isEqualTo(200);
        assertThat(edited.<String>read("$.data.status")).isEqualTo("REVIEWING");
        assertThat(edited.<Boolean>read("$.data.signedOff")).isFalse();
        assertThat(edited.<List<Integer>>read("$.data.parsedResult.goals[*].sortOrder")).containsExactly(0, 1);
        assertThat(edited.<List<Integer>>read("$.data.parsedResult.goals[1].tasks[*].sortOrder"))
                .containsExactly(0, 1);
        assertThat(edited.<String>read("$.data.path")).as("伺服器欄位以庫內值為準").isEqualTo("LLM");
        assertThat(edited.<String>read("$.data.aiModel")).isEqualTo("e2e-model");
        assertThat(edited.<Integer>read("$.data.tokenUsed")).isEqualTo(1152);

        // 5. 未 signoff 就 confirm
        Resp early = api.post(operator(), IMPORT + "/" + id + "/confirm");
        assertThat(early.status()).isEqualTo(409);
        assertThat(early.<String>read("$.reason")).isEqualTo("草案尚未 signoff，不可確認匯入");
        assertThat(early.<String>read("$.details.status")).isEqualTo("REVIEWING");
        assertThat(early.<Boolean>read("$.details.signedOff")).isFalse();
        assertThat(projectsNamed("E2E 匯入專案")).as("沒有任何專案被建立").isZero();

        // 6. 匿名 signoff
        Resp anonymous = api.post(operator(), IMPORT + "/" + id + "/signoff", Map.of("approver", "  "));
        assertThat(anonymous.status()).isEqualTo(400);
        assertThat(anonymous.<String>read("$.errors[0].field")).isEqualTo("approver");
        assertThat(api.post(operator(), IMPORT + "/" + id + "/signoff", Map.of()).status()).isEqualTo(400);

        // 7. signoff
        Resp signed = signoff(id);
        assertThat(signed.status()).isEqualTo(200);
        assertThat(signed.<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(signed.<String>read("$.data.signedOffBy")).isEqualTo(APPROVER);
        assertThat(signed.<String>read("$.data.signedOffAt")).isNotBlank();
        assertThat(signed.<String>read("$.data.status")).as("signoff 只批准、不落庫").isEqualTo("REVIEWING");
        assertThat(projectsNamed("E2E 匯入專案")).isZero();

        // 8. 重複 signoff
        Resp again = signoff(id);
        assertThat(again.status()).isEqualTo(409);
        assertThat(again.<String>read("$.reason")).isEqualTo("已 signoff");
        assertThat(again.<String>read("$.details.signedOffBy")).isEqualTo(APPROVER);

        // 9. 編輯撤銷 signoff
        Map<String, Object> second = currentTree(id);
        tasks(goals(second).get(0)).get(0).put("description", "請輸出 [T1_DONE]（已修訂）");
        Resp revoked = putTree(id, second);
        assertThat(revoked.status()).isEqualTo(200);
        assertThat(revoked.<Boolean>read("$.data.signedOff")).isFalse();
        Resp afterEdit = api.get(viewer(), IMPORT + "/" + id);
        assertThat(afterEdit.<Object>read("$.data.signedOffBy")).isNull();
        assertThat(afterEdit.<Object>read("$.data.signedOffAt")).isNull();
        assertThat(api.post(operator(), IMPORT + "/" + id + "/confirm").status()).as("撤銷後不可 confirm").isEqualTo(409);

        // 10. 重新 signoff
        assertThat(signoff(id).status()).isEqualTo(200);

        // 11. confirm
        Resp confirmed = api.post(operator(), IMPORT + "/" + id + "/confirm");
        assertThat(confirmed.status()).isEqualTo(201);
        assertThat(confirmed.<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(confirmed.<String>read("$.data.signedOffBy")).isEqualTo(APPROVER);
        assertThat(confirmed.<String>read("$.data.status")).isEqualTo("DRAFT");
        assertThat(confirmed.<Integer>read("$.data.goalsCount")).isEqualTo(2);
        assertThat(confirmed.<Integer>read("$.data.tasksCount")).isEqualTo(4);
        assertThat(confirmed.<Integer>read("$.data.autonomyLevel")).isEqualTo(3);
        assertThat(confirmed.<String>read("$.data.executionPath")).isEqualTo(EXEC_PATH);
        assertThat(confirmed.<String>read("$.data.name")).isEqualTo("E2E 匯入專案");
        assertThat(confirmed.<String>read("$.data.createdBy")).isEqualTo("operator");
        String projectId = confirmed.id();

        // 12. Phase 2 讀回：全部 signedOff、依賴正確、簽核時間一致
        Resp goalList = api.get(viewer(), "/api/v1/projects/" + projectId + "/goals");
        assertThat(goalList.<List<String>>read("$.data[*].name")).containsExactly("基礎建設", "核心");
        assertThat(goalList.<List<Boolean>>read("$.data[*].signedOff")).containsOnly(true);
        List<String> goalIds = goalList.read("$.data[*].id");
        Resp core = api.get(viewer(), "/api/v1/goals/" + goalIds.get(1));
        assertThat(core.<List<String>>read("$.data.dependsOn")).containsExactly(goalIds.get(0));
        assertThat(core.<String>read("$.data.signedOffBy")).isEqualTo(APPROVER);
        int taskCount = 0;
        for (String goalId : goalIds) {
            Resp taskList = api.get(viewer(), "/api/v1/goals/" + goalId + "/tasks");
            assertThat(taskList.<List<Boolean>>read("$.data[*].signedOff")).containsOnly(true);
            assertThat(taskList.<List<Integer>>read("$.data[*].sortOrder")).isSorted();
            taskCount += taskList.<List<Object>>read("$.data").size();
        }
        assertThat(taskCount).isEqualTo(4);
        assertThat(jdbc.queryForObject("select count(distinct signed_off_at) from ("
                + "select signed_off_at from console.projects where id = ?::uuid "
                + "union all select signed_off_at from console.goals where project_id = ?::uuid "
                + "union all select t.signed_off_at from console.tasks t join console.goals g on g.id = t.goal_id "
                + "where g.project_id = ?::uuid "
                + "union all select signed_off_at from console.import_records where id = ?::uuid) s",
                Integer.class, projectId, projectId, projectId, id))
                .as("專案、目標、任務與匯入記錄的簽核時間完全相同").isEqualTo(1);
        assertThat(jdbc.queryForObject("select count(*) from console.projects p where p.id = ?::uuid and "
                + "p.signed_off_by = ?", Integer.class, projectId, APPROVER)).isEqualTo(1);

        // 13. 匯入記錄的終態
        Resp done = api.get(viewer(), IMPORT + "/" + id);
        assertThat(done.<String>read("$.data.status")).isEqualTo("IMPORTED");
        assertThat(done.<String>read("$.data.projectId")).isEqualTo(projectId);
        Resp reconfirm = api.post(operator(), IMPORT + "/" + id + "/confirm");
        assertThat(reconfirm.status()).isEqualTo(409);
        assertThat(reconfirm.<String>read("$.reason")).isEqualTo("已匯入");
        assertThat(reconfirm.<String>read("$.details.projectId")).isEqualTo(projectId);
        Resp reject = api.post(operator(), IMPORT + "/" + id + "/reject");
        assertThat(reject.status()).isEqualTo(409);
        assertThat(reject.<String>read("$.reason")).isEqualTo("匯入記錄狀態不允許此操作");
        assertThat(reject.<String>read("$.details.action")).isEqualTo("reject");
        assertThat(projectsNamed("E2E 匯入專案")).as("重複 confirm 不會再建一個專案").isEqualTo(1);

        // 14. 歷史列表
        Resp history = api.get(viewer(), IMPORT + "?status=IMPORTED&sort=createdAt,desc");
        assertThat(history.<List<String>>read("$.data.content[*].id")).contains(id);
        assertThat(history.<List<String>>read("$.data.content[?(@.id=='" + id + "')].projectId"))
                .containsExactly(projectId);
    }

    @Test
    void parseOptionsDecideTheProjectsAutonomyLevelAndExecutionPath() {
        stubOkModel();
        String id = createMarkdown();
        Resp parsed = api.post(operator(), IMPORT + "/" + id + "/parse", Map.of("autonomyLevel", 7,
                "executionPath", "C:\\work\\proj"));
        assertThat(parsed.status()).isEqualTo(200);
        assertThat(signoff(id).status()).isEqualTo(200);

        Resp confirmed = api.post(operator(), IMPORT + "/" + id + "/confirm");
        assertThat(confirmed.<Integer>read("$.data.autonomyLevel")).isEqualTo(7);
        assertThat(confirmed.<String>read("$.data.executionPath")).isEqualTo("C:\\work\\proj");
    }

    @Test
    void theAutonomyLevelDefaultsToThreeWhenNotGiven() {
        stubOkModel();
        String id = createMarkdown();
        Resp parsed = api.post(operator(), IMPORT + "/" + id + "/parse", Map.of("executionPath", EXEC_PATH));
        assertThat(parsed.status()).isEqualTo(200);
        assertThat(parsed.<Integer>read("$.data.parsedResult.project.autonomyLevel")).isEqualTo(3);
        assertThat(OutboundFakes.LLM.received().get(0).body()).contains("自治等級: 3").contains("補充說明: （無）");
    }

    @Test
    void confirmingCopiesEveryTaskFieldAndAppliesTheDefaultsOfTheOtherCreationPath() {
        stubOkModel();
        String id = createMarkdown();
        assertThat(parse(id).status()).isEqualTo(200);
        Map<String, Object> tree = currentTree(id);
        Map<String, Object> first = tasks(goals(tree).get(0)).get(0);
        first.put("evaluatorCommand", "pytest -q");
        first.put("expectedOutputRegex", "\\[T1_DONE\\]");
        first.put("estimatedTokens", 1234);
        first.put("maxRetries", 5);
        first.put("passCriteriaSpec", Map.of("source", "manual", "note", "x"));
        assertThat(putTree(id, tree).status()).isEqualTo(200);
        assertThat(signoff(id).status()).isEqualTo(200);

        Resp confirmed = api.post(operator(), IMPORT + "/" + id + "/confirm");
        assertThat(confirmed.status()).isEqualTo(201);
        String goalId = api.get(viewer(), "/api/v1/projects/" + confirmed.id() + "/goals").<List<String>>read(
                "$.data[*].id").get(0);
        String taskId = api.get(viewer(), "/api/v1/goals/" + goalId + "/tasks").<List<String>>read("$.data[*].id")
                .get(0);
        Resp task = api.get(viewer(), "/api/v1/tasks/" + taskId);
        assertThat(task.<String>read("$.data.name")).isEqualTo("初始化");
        assertThat(task.<String>read("$.data.description")).isEqualTo("請輸出 [T1_DONE]");
        assertThat(task.<String>read("$.data.passCriteria")).isEqualTo("輸出含 [T1_DONE]");
        assertThat(task.<String>read("$.data.evaluatorCommand")).isEqualTo("pytest -q");
        assertThat(task.<String>read("$.data.expectedOutputRegex")).isEqualTo("\\[T1_DONE\\]");
        assertThat(task.<Integer>read("$.data.estimatedTokens")).isEqualTo(1234);
        assertThat(task.<Integer>read("$.data.maxRetries")).isEqualTo(5);
        assertThat(task.<String>read("$.data.passCriteriaSpec.source")).isEqualTo("manual");
        assertThat(task.<String>read("$.data.status")).isEqualTo("PENDING");
        assertThat(task.<Boolean>read("$.data.signedOff")).isTrue();

        String second = api.get(viewer(), "/api/v1/goals/" + goalId + "/tasks").<List<String>>read("$.data[*].id")
                .get(1);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + second).<Integer>read("$.data.maxRetries"))
                .as("沒給 maxRetries 時取預設 3").isEqualTo(3);
    }

    @Test
    void aFailedConfirmRollsBackEverythingAndLeavesTheRecordConfirmable() {
        stubOkModel();
        String id = createMarkdown();
        assertThat(parse(id).status()).isEqualTo(200);
        assertThat(signoff(id).status()).isEqualTo(200);
        // 模擬落庫前才發現不合法的資料（直接改庫繞過編輯端點的消毒）：第二個目標的任務名稱超過 200 字元
        jdbc.update("update console.import_records set parsed_result = jsonb_set(parsed_result, "
                + "'{goals,1,tasks,0,name}', to_jsonb(repeat('x', 201))) where id = ?::uuid", id);

        Resp failed = api.post(operator(), IMPORT + "/" + id + "/confirm");

        assertThat(failed.status()).isEqualTo(400);
        assertThat(failed.<String>read("$.errors[0].field")).as("欄位名補上樹內位置前綴（契約 §1.1.6）")
                .isEqualTo("parsedResult.goals[1].tasks[0].name");
        assertThat(projectsNamed("E2E 匯入專案")).as("單一交易：失敗時第一個目標建好的專案也一併回滾").isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.goals", Integer.class)).isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.tasks", Integer.class)).isZero();
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<String>read("$.data.status")).isEqualTo("PARSED");
        assertThat(record.<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(record.<Object>read("$.data.projectId")).isNull();
    }

    // ── 建立（text）的驗證 ─────────────────────────────────────────────────────

    @Test
    void createFromTextDefaultsToPlainTextAndValidatesItsFields() {
        Resp plain = api.post(operator(), IMPORT + "/text", Map.of("content", "做一個待辦清單"));
        assertThat(plain.status()).isEqualTo(201);
        assertThat(plain.<String>read("$.data.sourceType")).isEqualTo("PLAIN_TEXT");
        assertThat(plain.<Object>read("$.data.sourceFileName")).as("省略時存 null").isNull();

        Resp blank = api.post(operator(), IMPORT + "/text", Map.of("content", "   \n  "));
        assertThat(blank.status()).isEqualTo(400);
        assertThat(blank.<String>read("$.errors[0].field")).isEqualTo("content");
        assertThat(blank.<String>read("$.errors[0].message")).isEqualTo("內容不可為空");

        assertThat(api.post(operator(), IMPORT + "/text", Map.of("content", "x".repeat(2_000_001))).status())
                .isEqualTo(400);
        assertThat(api.post(operator(), IMPORT + "/text", Map.of("content", "x".repeat(2_000_000))).status())
                .isEqualTo(201);
        assertThat(api.post(operator(), IMPORT + "/text", Map.of("content", "x", "sourceFileName", "n".repeat(501)))
                .status()).isEqualTo(400);

        Resp pdf = api.post(operator(), IMPORT + "/text", Map.of("content", "x", "sourceType", "PDF"));
        assertThat(pdf.status()).as("PDF／DOCX 只能由 upload 產生").isEqualTo(400);
        assertThat(pdf.<String>read("$.errors[0].field")).isEqualTo("sourceType");
        assertThat(api.post(operator(), IMPORT + "/text", Map.of("content", "x", "sourceType", "FOO")).status())
                .isEqualTo(400);
        assertThat(api.post(operator(), IMPORT + "/text", Map.of()).status()).isEqualTo(400);
    }

    @Test
    void surroundingWhitespaceOfTheSourceFileNameIsStrippedAndABlankNameBecomesNull() {
        Resp named = api.post(operator(), IMPORT + "/text", Map.of("content", "x", "sourceFileName", "  剪貼簿  "));
        assertThat(named.<String>read("$.data.sourceFileName")).isEqualTo("剪貼簿");
        Resp blank = api.post(operator(), IMPORT + "/text", Map.of("content", "x", "sourceFileName", "   "));
        assertThat(blank.<Object>read("$.data.sourceFileName")).isNull();
    }

    @Test
    void parseOptionsAreValidatedBeforeAnythingIsCalledOrChanged() {
        String id = createMarkdown();
        for (Object[] c : new Object[][] {
                {Map.of("autonomyLevel", 3), "executionPath"},
                {Map.of("executionPath", "  "), "executionPath"},
                {Map.of("executionPath", "work/relative"), "executionPath"},
                {Map.of("executionPath", EXEC_PATH, "autonomyLevel", 11), "autonomyLevel"},
                {Map.of("executionPath", EXEC_PATH, "autonomyLevel", 0), "autonomyLevel"},
                {Map.of("executionPath", EXEC_PATH, "additionalPrompt", "p".repeat(4001)), "additionalPrompt"},
                {Map.of("executionPath", EXEC_PATH, "specDir", "d".repeat(501)), "specDir"},
                {Map.of("executionPath", "/" + "d".repeat(500)), "executionPath"}}) {
            @SuppressWarnings("unchecked")
            Map<String, Object> body = (Map<String, Object>) c[0];
            Resp resp = api.post(operator(), IMPORT + "/" + id + "/parse", body);
            assertThat(resp.status()).as(body.toString()).isEqualTo(400);
            assertThat(resp.<List<String>>read("$.errors[*].field")).contains((String) c[1]);
        }
        assertThat(OutboundFakes.LLM.received()).isEmpty();
        assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.status")).isEqualTo("UPLOADED");
    }

    // ── 狀態機 ────────────────────────────────────────────────────────────────

    private String recordIn(String status, boolean signedOff) {
        String id = api.post(operator(), IMPORT + "/text", Map.of("content", ImportFixtures.markdownDocument(null),
                "sourceType", "MARKDOWN")).id();
        jdbc.update("update console.import_records set status = ?, signed_off = ?, signed_off_by = ?, "
                + "signed_off_at = ? where id = ?::uuid", status, signedOff, signedOff ? "someone" : null,
                signedOff ? Timestamp.from(Instant.parse("2026-10-15T01:02:03Z")) : null, id);
        return id;
    }

    private void assertNotAllowed(Resp resp, String action, String status) {
        assertThat(resp.status()).as(action + " @ " + status).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("匯入記錄狀態不允許此操作");
        assertThat(resp.<String>read("$.details.action")).isEqualTo(action);
        assertThat(resp.<String>read("$.details.status")).isEqualTo(status);
    }

    private Resp parseRequest(String id) {
        return api.post(operator(), IMPORT + "/" + id + "/parse", Map.of("executionPath", EXEC_PATH));
    }

    private Resp putRequest(String id) {
        Map<String, Object> tree = new LinkedHashMap<>();
        tree.put("project", Map.of("name", "P", "executionPath", EXEC_PATH, "passCriteria", "c"));
        tree.put("goals", List.of(ImportFixtures.goal("g1", "G", List.of(),
                List.of(ImportFixtures.doneTask("T", 1)))));
        return api.put(operator(), IMPORT + "/" + id + "/result", Map.of("parsedResult", tree));
    }

    @Test
    void everyForbiddenActionInEveryStateIs409WithTheActionAndStatusNamed() {
        // UPLOADED：只有 parse、reject 可以
        String uploaded = recordIn("UPLOADED", false);
        assertNotAllowed(putRequest(uploaded), "editResult", "UPLOADED");
        assertNotAllowed(api.post(operator(), IMPORT + "/" + uploaded + "/signoff", Map.of("approver", "a")),
                "signoff", "UPLOADED");
        assertNotAllowed(api.post(operator(), IMPORT + "/" + uploaded + "/confirm"), "confirm", "UPLOADED");

        // PARSING：一律不可（parse 另有專屬 reason）
        String parsing = recordIn("PARSING", false);
        Resp parseWhileParsing = parseRequest(parsing);
        assertThat(parseWhileParsing.status()).isEqualTo(409);
        assertThat(parseWhileParsing.<String>read("$.reason")).isEqualTo("解析中，請稍候");
        assertThat(parseWhileParsing.<String>read("$.details.status")).isEqualTo("PARSING");
        assertNotAllowed(putRequest(parsing), "editResult", "PARSING");
        assertNotAllowed(api.post(operator(), IMPORT + "/" + parsing + "/signoff", Map.of("approver", "a")),
                "signoff", "PARSING");
        assertNotAllowed(api.post(operator(), IMPORT + "/" + parsing + "/confirm"), "confirm", "PARSING");
        assertNotAllowed(api.post(operator(), IMPORT + "/" + parsing + "/reject"), "reject", "PARSING");

        // IMPORTED、REJECTED：終態
        for (String terminal : new String[] {"IMPORTED", "REJECTED"}) {
            String id = recordIn(terminal, false);
            assertNotAllowed(parseRequest(id), "parse", terminal);
            assertNotAllowed(putRequest(id), "editResult", terminal);
            assertNotAllowed(api.post(operator(), IMPORT + "/" + id + "/signoff", Map.of("approver", "a")),
                    "signoff", terminal);
            assertNotAllowed(api.post(operator(), IMPORT + "/" + id + "/reject"), "reject", terminal);
            Resp confirm = api.post(operator(), IMPORT + "/" + id + "/confirm");
            if (terminal.equals("IMPORTED")) {
                assertThat(confirm.status()).isEqualTo(409);
                assertThat(confirm.<String>read("$.reason")).isEqualTo("已匯入");
            } else {
                assertNotAllowed(confirm, "confirm", terminal);
            }
        }
        assertThat(OutboundFakes.LLM.received()).as("狀態不允許時不得外呼").isEmpty();
        assertThat(OutboundFakes.BRIDGE.received()).isEmpty();
    }

    @Test
    void aSignedOffDraftCannotBeReparsedAndRejectingAnUploadedRecordIsAllowed() {
        String signed = recordIn("REVIEWING", true);
        Resp resp = parseRequest(signed);
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("已 signoff，不可重新解析");
        assertThat(resp.<String>read("$.details.signedOffBy")).isEqualTo("someone");
        assertThat(resp.<String>read("$.details.signedOffAt")).isNotBlank();

        String uploaded = recordIn("UPLOADED", false);
        Resp rejected = api.post(operator(), IMPORT + "/" + uploaded + "/reject");
        assertThat(rejected.status()).isEqualTo(200);
        assertThat(rejected.<String>read("$.data.status")).isEqualTo("REJECTED");
        assertThat(OutboundFakes.BRIDGE.received()).as("reject 不呼叫 Bridge").isEmpty();
    }

    @Test
    void parsedAndReviewingDraftsCanBeRejected() {
        for (String status : new String[] {"PARSED", "REVIEWING"}) {
            String id = recordIn(status, false);
            Resp resp = api.post(operator(), IMPORT + "/" + id + "/reject");
            assertThat(resp.status()).as(status).isEqualTo(200);
            assertThat(resp.<String>read("$.data.status")).isEqualTo("REJECTED");
        }
    }

    @Test
    void anUnknownImportRecordIs404AndABadIdIs400ForEveryEndpoint() {
        UUID missing = UUID.randomUUID();
        assertThat(api.get(viewer(), IMPORT + "/" + missing).status()).isEqualTo(404);
        assertThat(parseRequest(missing.toString()).status()).isEqualTo(404);
        assertThat(putRequest(missing.toString()).status()).isEqualTo(404);
        assertThat(api.post(operator(), IMPORT + "/" + missing + "/signoff", Map.of("approver", "a")).status())
                .isEqualTo(404);
        assertThat(api.post(operator(), IMPORT + "/" + missing + "/confirm").status()).isEqualTo(404);
        assertThat(api.post(operator(), IMPORT + "/" + missing + "/reject").status()).isEqualTo(404);
        assertThat(api.get(viewer(), IMPORT + "/not-a-uuid").status()).isEqualTo(400);
        assertThat(api.get(viewer(), IMPORT + "/" + missing).<String>read("$.message")).contains(missing.toString());
    }

    // ── 角色 ─────────────────────────────────────────────────────────────────

    @Test
    void viewersCanOnlyReadAndAnonymousCallersAreRejectedEverywhere() {
        String id = recordIn("REVIEWING", false);
        assertThat(api.post(viewer(), IMPORT + "/text", Map.of("content", "x")).status()).isEqualTo(403);
        assertThat(api.multipart(viewer(), IMPORT + "/upload", "file", "a.md", "text/markdown",
                "# a".getBytes(StandardCharsets.UTF_8)).status()).isEqualTo(403);
        assertThat(api.post(viewer(), IMPORT + "/" + id + "/parse", Map.of("executionPath", EXEC_PATH)).status())
                .isEqualTo(403);
        assertThat(api.put(viewer(), IMPORT + "/" + id + "/result", Map.of()).status()).isEqualTo(403);
        assertThat(api.post(viewer(), IMPORT + "/" + id + "/signoff", Map.of("approver", "a")).status())
                .isEqualTo(403);
        assertThat(api.post(viewer(), IMPORT + "/" + id + "/confirm").status()).isEqualTo(403);
        assertThat(api.post(viewer(), IMPORT + "/" + id + "/reject").status()).isEqualTo(403);
        assertThat(api.get(viewer(), IMPORT).status()).isEqualTo(200);
        assertThat(api.get(viewer(), IMPORT + "/" + id).status()).isEqualTo(200);

        assertThat(api.get(null, IMPORT).status()).isEqualTo(401);
        assertThat(api.get(null, IMPORT + "/" + id).status()).isEqualTo(401);
        assertThat(api.post(null, IMPORT + "/text", Map.of("content", "x")).status()).isEqualTo(401);
        assertThat(api.post(null, IMPORT + "/" + id + "/confirm").status()).isEqualTo(401);
        assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.status")).as("403 不改任何狀態")
                .isEqualTo("REVIEWING");
    }

    // ── 查詢 ─────────────────────────────────────────────────────────────────

    private String textRecord(String fileName) {
        return api.post(operator(), IMPORT + "/text", Map.of("content", "x", "sourceFileName", fileName)).id();
    }

    @Test
    void theHistoryIsPagedSortedAndFilteredAndNeverCarriesTheBulkyFields() {
        String alpha = textRecord("alpha-brd.md");
        String beta = textRecord("Beta_PRD.md");
        String gamma = textRecord("gamma%.md");
        jdbc.update("update console.import_records set status = 'PARSED' where id = ?::uuid", alpha);
        jdbc.update("update console.import_records set status = 'REJECTED' where id = ?::uuid", gamma);

        Resp newestFirst = api.get(viewer(), IMPORT);
        assertThat(newestFirst.<List<String>>read("$.data.content[*].id")).containsExactly(gamma, beta, alpha);
        assertThat(newestFirst.<Integer>read("$.data.totalElements")).isEqualTo(3);
        assertThat(newestFirst.body()).doesNotContain("sourceContent").doesNotContain("parsedResult");
        assertThat(api.get(viewer(), IMPORT + "?sort=createdAt,asc").<List<String>>read("$.data.content[*].id"))
                .containsExactly(alpha, beta, gamma);
        assertThat(api.get(viewer(), IMPORT + "?sort=status,asc").<List<String>>read("$.data.content[*].status"))
                .containsExactly("PARSED", "REJECTED", "UPLOADED");
        assertThat(api.get(viewer(), IMPORT + "?sort=status,desc").<List<String>>read("$.data.content[*].status"))
                .containsExactly("UPLOADED", "REJECTED", "PARSED");

        Resp page = api.get(viewer(), IMPORT + "?page=1&size=2&sort=createdAt,asc");
        assertThat(page.<List<String>>read("$.data.content[*].id")).containsExactly(gamma);
        assertThat(page.<Integer>read("$.data.totalPages")).isEqualTo(2);

        assertThat(api.get(viewer(), IMPORT + "?status=PARSED").<List<String>>read("$.data.content[*].id"))
                .containsExactly(alpha);
        assertThat(api.get(viewer(), IMPORT + "?q=ALPHA").<List<String>>read("$.data.content[*].id"))
                .as("不分大小寫").containsExactly(alpha);
        // MockMvc 會對 URL 樣板編碼（% → %25），所以這裡寫字面的 %，伺服器端收到的 q 就是單一個 %。
        assertThat(api.get(viewer(), IMPORT + "?q=%").<List<String>>read("$.data.content[*].id"))
                .as("% 視為字面").containsExactly(gamma);
        assertThat(api.get(viewer(), IMPORT + "?q=_").<List<String>>read("$.data.content[*].id"))
                .as("_ 視為字面").containsExactly(beta);
        assertThat(api.get(viewer(), IMPORT + "?q=nomatch").<Integer>read("$.data.totalElements")).isZero();
        assertThat(api.get(viewer(), IMPORT + "?status=PARSED&q=beta").<Integer>read("$.data.totalElements"))
                .isZero();
    }

    @Test
    void badListParametersAreRejected() {
        for (String query : new String[] {"?status=BOGUS", "?sort=bogus,asc", "?sort=createdAt,sideways",
                "?size=0", "?size=101", "?page=-1", "?page=abc"}) {
            Resp resp = api.get(viewer(), IMPORT + query);
            assertThat(resp.status()).as(query).isEqualTo(400);
        }
        assertThat(api.get(viewer(), IMPORT + "?size=100").status()).isEqualTo(200);
        assertThat(api.get(viewer(), IMPORT + "?sort=STATUS").status()).as("欄位名不分大小寫").isEqualTo(200);
    }

    // ── 小工具 ───────────────────────────────────────────────────────────────

    /** 假模型端收到的請求（JsonPath 取本文欄位）。 */
    private record FakeLlmRequest(Received received) {

        String method() {
            return received.method();
        }

        String path() {
            return received.path();
        }

        String header(String name) {
            return received.headers().get(name);
        }

        String string(String path) {
            return JsonPath.read(received.body(), path);
        }

        boolean bool(String path) {
            return JsonPath.<Boolean>read(received.body(), path);
        }
    }
}
