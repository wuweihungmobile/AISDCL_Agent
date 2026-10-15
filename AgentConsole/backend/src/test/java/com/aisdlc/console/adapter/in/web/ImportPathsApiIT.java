package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractOutboundIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.FakeHttpServer;
import com.aisdlc.console.support.FakeHttpServer.Received;
import com.aisdlc.console.support.FakeHttpServer.Response;
import com.aisdlc.console.support.ImportFixtures;
import com.aisdlc.console.support.OutboundFakes;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 匯入的路徑 A（凍結 SDD 規格）與路徑 C（高階目標 → Bridge decompose）整合測試，以假 Bridge 驗證（契約 §3.1～§3.3；
 * E2E-01「不在本 E2E 的範圍」那一段指定由本層覆蓋）。為什麼重要：這兩條路徑把「資料送去哪、被拒時怎麼辦」交給外部引擎——
 * 規格存在卻被拒必須 fail-closed 而不是悄悄退回 LLM；30 個合約不能因為數量多就永遠 422；signoff 必須真的通知 Bridge，
 * 通知失敗時絕不能留下「看似已簽、其實沒簽」的狀態；管理員改過的 Bridge 位址要立刻生效。
 */
class ImportPathsApiIT extends AbstractOutboundIT {

    private static final String IMPORT = "/api/v1/import";
    private static final String EXEC_PATH = "/work/proj-import";
    private static final String SPEC_REJECTED = "SDD 規格檢查未通過";
    private static final String GATE_REASON = "解析結果未通過有界閘";
    private static final String APPROVER = "e2e-approver";
    private static final String DIGEST = "0123456789abcdef0123456789abcdef";

    // ── 夾具 ─────────────────────────────────────────────────────────────────

    private static void bridgeCompiles(String scenario, int contracts) {
        OutboundFakes.BRIDGE.on("POST", "/sdd/compile",
                Response.json(200, ImportFixtures.sddCompileResponse(scenario, contracts)));
    }

    private static void bridgeCompileFails(int status, String reason, String detail) {
        OutboundFakes.BRIDGE.on("POST", "/sdd/compile",
                Response.json(status, ImportFixtures.bridgeError(status, reason, null, detail)));
    }

    private static List<Map<String, Object>> steps(int count) {
        List<Map<String, Object>> list = new ArrayList<>();
        for (int i = 1; i <= count; i++) {
            list.add(ImportFixtures.decomposeStep("s" + i, "步驟 " + i, "請做第 " + i + " 步", "pytest -q"));
        }
        return list;
    }

    private static void bridgeDecomposes(String draftId, List<Map<String, Object>> steps) {
        OutboundFakes.BRIDGE.on("POST", "/autoclaude/decompose",
                Response.json(200, ImportFixtures.decomposeResponse(draftId, "先拆再做", steps)));
    }

    private static void bridgeDecomposeFails(int status, String reason, String gate, String detail) {
        OutboundFakes.BRIDGE.on("POST", "/autoclaude/decompose",
                Response.json(status, ImportFixtures.bridgeError(status, reason, gate, detail)));
    }

    private static void bridgeHasNoSpec() {
        bridgeCompileFails(422, "spec_not_found", "找不到規格");
    }

    private String createText(String content, String type) {
        Resp created = api.post(operator(), IMPORT + "/text", Map.of("content", content, "sourceType", type));
        assertThat(created.status()).isEqualTo(201);
        return created.id();
    }

    private String createGoalText() {
        return createText("做一個待辦清單\n要能新增與刪除", "PLAIN_TEXT");
    }

    private Resp parse(String id, String specDir) {
        Map<String, Object> options = new LinkedHashMap<>();
        options.put("executionPath", EXEC_PATH);
        options.put("autonomyLevel", 3);
        if (specDir != null) {
            options.put("specDir", specDir);
        }
        return api.post(operator(), IMPORT + "/" + id + "/parse", options);
    }

    private Resp signoff(String id) {
        return api.post(operator(), IMPORT + "/" + id + "/signoff", Map.of("approver", APPROVER));
    }

    private void pointBridgeAtNowhere() {
        putSetting("autoclaude", "engineUrl", "http://127.0.0.1:1", false);
        putSetting("sdd", "engineUrl", "http://127.0.0.1:1", false);
    }

    private static String bodyField(Received received, String path) {
        return JsonPath.read(received.body(), path);
    }

    private void assertRecordBackToUploadedWithoutGateErrors(String id) {
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<String>read("$.data.status")).isEqualTo("UPLOADED");
        assertThat(record.<Object>read("$.data.lastParseErrors")).as("非有界閘的失敗不寫 lastParseErrors").isNull();
        assertThat(record.<Object>read("$.data.parsedResult")).isNull();
    }

    // ── 路徑 A ────────────────────────────────────────────────────────────────

    @Test
    void anExplicitSpecDirIsCompiledByTheBridgeIntoAOneGoalDraftWhoseTasksAreTheContracts() {
        bridgeCompiles("購物車", 3);
        String id = createText("# 一份文件\n內容", "MARKDOWN");

        Resp resp = parse(id, "/spec/frozen");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.path")).isEqualTo("SDD");
        assertThat(resp.<Object>read("$.data.aiModel")).isNull();
        assertThat(resp.<Object>read("$.data.tokenUsed")).isNull();
        assertThat(resp.<String>read("$.data.parsedResult.specDigest")).isEqualTo(DIGEST);
        assertThat(resp.<List<Object>>read("$.data.warnings")).isEmpty();
        assertThat(resp.<String>read("$.data.parsedResult.project.name")).isEqualTo("購物車");
        assertThat(resp.<String>read("$.data.parsedResult.project.passCriteria"))
                .isEqualTo("規格「購物車」的全部合約驗收通過");
        assertThat(resp.<String>read("$.data.parsedResult.project.description"))
                .isEqualTo("由凍結 SDD 規格匯入（/spec/cart.yaml；digest 0123456789ab）");
        assertThat(resp.<String>read("$.data.parsedResult.project.executionPath")).isEqualTo(EXEC_PATH);
        assertThat(resp.<List<String>>read("$.data.parsedResult.goals[*].name")).containsExactly("購物車");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].passCriteria"))
                .isEqualTo("全部 3 個合約的驗收標準通過");
        assertThat(resp.<List<String>>read("$.data.parsedResult.goals[0].tasks[*].name"))
                .containsExactly("合約 1", "合約 2", "合約 3");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[0].description")).isEqualTo("請實作合約 1");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[0].evaluatorCommand"))
                .isEqualTo("pytest -q tests/test1");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[0].expectedOutputRegex"))
                .isEqualTo("OK-1\\d+");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[0].passCriteria"))
                .isEqualTo("輸出符合 OK-1\\d+");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[0].passCriteriaSpec.source"))
                .isEqualTo("sdd");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[1].passCriteriaSpec.stepId"))
                .isEqualTo("C2");
        assertThat(resp.<Boolean>read("$.data.parsedResult.goals[0].tasks[1].passCriteriaSpec.weakRegex"))
                .isFalse();

        assertThat(OutboundFakes.BRIDGE.receivedAt("/sdd/compile")).hasSize(1);
        assertThat(bodyField(OutboundFakes.BRIDGE.receivedAt("/sdd/compile").get(0), "$.spec_dir"))
                .isEqualTo("/spec/frozen");
        assertThat(OutboundFakes.LLM.received()).as("路徑 A 不呼叫任何模型").isEmpty();
        assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.parsePath")).isEqualTo("SDD");
    }

    @Test
    void aSpecDraftNeedsNoBridgeApprovalAndConfirmsIntoTasksWithTheirEvaluators() {
        bridgeCompiles("購物車", 2);
        String id = createText("# 文件", "MARKDOWN");
        assertThat(parse(id, "/spec/frozen").status()).isEqualTo(200);

        assertThat(signoff(id).status()).isEqualTo(200);
        assertThat(OutboundFakes.BRIDGE.received().stream().filter(r -> r.path().contains(":approve")).toList())
                .as("路徑 A 沒有 draftIds，signoff 不呼叫 :approve").isEmpty();

        Resp confirmed = api.post(operator(), IMPORT + "/" + id + "/confirm");
        assertThat(confirmed.status()).isEqualTo(201);
        assertThat(confirmed.<String>read("$.data.name")).isEqualTo("購物車");
        assertThat(confirmed.<Integer>read("$.data.tasksCount")).isEqualTo(2);
        String goalId = api.get(viewer(), "/api/v1/projects/" + confirmed.id() + "/goals")
                .<List<String>>read("$.data[*].id").get(0);
        String taskId = api.get(viewer(), "/api/v1/goals/" + goalId + "/tasks").<List<String>>read("$.data[*].id")
                .get(0);
        Resp task = api.get(viewer(), "/api/v1/tasks/" + taskId);
        assertThat(task.<String>read("$.data.evaluatorCommand")).isEqualTo("pytest -q tests/test1");
        assertThat(task.<String>read("$.data.expectedOutputRegex")).isEqualTo("OK-1\\d+");
        assertThat(task.<String>read("$.data.passCriteriaSpec.specDigest")).isEqualTo(DIGEST);
    }

    @Test
    void thirtyContractsAreSplitIntoTwentyFourPlusSixAndChainedByDependencies() {
        bridgeCompiles("購物車", 30);
        String id = createText("# 文件", "MARKDOWN");

        Resp resp = parse(id, "/spec/frozen");

        assertThat(resp.status()).as("合約數多不會被 max_steps 永遠擋成 422").isEqualTo(200);
        assertThat(resp.<List<String>>read("$.data.parsedResult.goals[*].name")).containsExactly("購物車（第 1 批）",
                "購物車（第 2 批）");
        assertThat(resp.<Integer>read("$.data.parsedResult.goals[0].tasks.length()")).isEqualTo(24);
        assertThat(resp.<Integer>read("$.data.parsedResult.goals[1].tasks.length()")).isEqualTo(6);
        assertThat(resp.<List<String>>read("$.data.parsedResult.goals[0].dependsOn")).isEmpty();
        assertThat(resp.<List<String>>read("$.data.parsedResult.goals[1].dependsOn")).containsExactly("g1");
        assertThat(resp.<String>read("$.data.parsedResult.goals[1].tasks[0].name")).as("保持編譯順序")
                .isEqualTo("合約 25");

        assertThat(signoff(id).status()).isEqualTo(200);
        Resp confirmed = api.post(operator(), IMPORT + "/" + id + "/confirm");
        assertThat(confirmed.status()).isEqualTo(201);
        assertThat(confirmed.<Integer>read("$.data.goalsCount")).isEqualTo(2);
        assertThat(confirmed.<Integer>read("$.data.tasksCount")).isEqualTo(30);
        assertThat(jdbc.queryForObject("select count(*) from console.goal_dependencies", Integer.class)).isEqualTo(1);
    }

    @Test
    void anExplicitSpecDirThatTheBridgeRejectsIs422WithTheBridgesReasonAndTheRecordIsRetryable() {
        for (String reason : List.of("spec_not_frozen", "spec_tainted", "spec_format_version_unsupported",
                "spec_ambiguous", "spec_not_found", "sanitization_failed")) {
            OutboundFakes.resetAll();
            bridgeCompileFails(422, reason, "規格有問題：" + reason);
            String id = createText("# 文件", "MARKDOWN");

            Resp resp = parse(id, "/spec/frozen");

            assertThat(resp.status()).as(reason).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).isEqualTo(SPEC_REJECTED);
            assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo(reason);
            assertThat(resp.<String>read("$.details.detail")).isEqualTo("規格有問題：" + reason);
            assertThat(resp.<String>read("$.errors[0].field")).isEqualTo("specDir");
            assertRecordBackToUploadedWithoutGateErrors(id);
            assertThat(OutboundFakes.LLM.received()).isEmpty();
        }
    }

    @Test
    void aSpecThatCompilesToNoContractsIsRejectedInsteadOfCreatingAnEmptyDraft() {
        OutboundFakes.BRIDGE.on("POST", "/sdd/compile", Response.json(200, ImportFixtures.sddCompileResponse("空規格", 0)));
        String id = createText("# 文件", "MARKDOWN");

        Resp resp = parse(id, "/spec/frozen");

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(SPEC_REJECTED);
        assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo("no_tasks");
    }

    @Test
    void withoutASpecDirTheExecutionPathIsProbedAndAFrozenSpecWinsEvenForAShortGoal() {
        bridgeCompiles("購物車", 2);
        String id = createGoalText();

        Resp resp = parse(id, null);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.path")).isEqualTo("SDD");
        assertThat(bodyField(OutboundFakes.BRIDGE.receivedAt("/sdd/compile").get(0), "$.spec_dir"))
                .isEqualTo(EXEC_PATH);
        assertThat(OutboundFakes.BRIDGE.receivedAt("/autoclaude/decompose")).isEmpty();
        assertThat(OutboundFakes.LLM.received()).isEmpty();
    }

    @Test
    void whenNoSpecExistsAShortGoalIsDecomposedAndADocumentGoesToTheLlm() {
        for (String reason : List.of("spec_not_found", "sanitization_failed")) {
            OutboundFakes.resetAll();
            bridgeCompileFails(422, reason, "沒有規格");
            bridgeDecomposes("d-1", steps(2));
            OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                    Response.json(200, ImportFixtures.chatCompletion(ImportFixtures.okTree())));
            configureFakeModel();

            Resp goal = parse(createGoalText(), null);
            assertThat(goal.status()).as(reason).isEqualTo(200);
            assertThat(goal.<String>read("$.data.path")).isEqualTo("DECOMPOSE");

            Resp document = parse(createText(ImportFixtures.markdownDocument(null), "MARKDOWN"), null);
            assertThat(document.status()).as(reason).isEqualTo(200);
            assertThat(document.<String>read("$.data.path")).isEqualTo("LLM");
            assertThat(OutboundFakes.BRIDGE.receivedAt("/sdd/compile")).as("每筆各探測一次").hasSize(2);
        }
    }

    @Test
    void aSpecThatExistsButIsRejectedDuringTheProbeFailsClosedAndNeverFallsBackToGuessing() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                Response.json(200, ImportFixtures.chatCompletion(ImportFixtures.okTree())));
        for (String reason : List.of("spec_not_frozen", "spec_tainted", "spec_format_version_unsupported",
                "spec_ambiguous")) {
            OutboundFakes.BRIDGE.reset();
            bridgeCompileFails(422, reason, "規格有問題");
            bridgeDecomposes("d-1", steps(2));
            String id = createText(ImportFixtures.markdownDocument(null), "MARKDOWN");

            Resp resp = parse(id, null);

            assertThat(resp.status()).as(reason).isEqualTo(422);
            assertThat(resp.<String>read("$.reason")).isEqualTo(SPEC_REJECTED);
            assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo(reason);
            assertThat(OutboundFakes.LLM.received()).as("不得退回 LLM").isEmpty();
            assertThat(OutboundFakes.BRIDGE.receivedAt("/autoclaude/decompose")).as("也不得退回拆解").isEmpty();
            assertRecordBackToUploadedWithoutGateErrors(id);
        }
    }

    @Test
    void aBridgeThatFailsDuringTheProbeIsSkippedSoTheDocumentStillGoesToTheLlm() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                Response.json(200, ImportFixtures.chatCompletion(ImportFixtures.okTree())));

        bridgeCompileFails(500, "internal_error", null);
        Resp fiveHundred = parse(createText(ImportFixtures.markdownDocument(null), "MARKDOWN"), null);
        assertThat(fiveHundred.status()).isEqualTo(200);
        assertThat(fiveHundred.<String>read("$.data.path")).isEqualTo("LLM");

        pointBridgeAtNowhere();
        Resp unreachable = parse(createText(ImportFixtures.markdownDocument(null), "MARKDOWN"), null);
        assertThat(unreachable.status()).isEqualTo(200);
        assertThat(unreachable.<String>read("$.data.path")).isEqualTo("LLM");
    }

    @Test
    void anUnexpectedClientErrorFromTheProbeIsAlsoSkipped() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                Response.json(200, ImportFixtures.chatCompletion(ImportFixtures.okTree())));
        bridgeCompileFails(400, "bad_request", null);

        Resp resp = parse(createText(ImportFixtures.markdownDocument(null), "MARKDOWN"), null);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.path")).isEqualTo("LLM");
    }

    @Test
    void anExplicitSpecDirNeedsTheBridgeSoAnUnreachableOneIs502() {
        pointBridgeAtNowhere();
        String id = createText("# 文件", "MARKDOWN");

        Resp resp = parse(id, "/spec/frozen");

        assertThat(resp.status()).isEqualTo(502);
        assertThat(resp.<String>read("$.reason")).isEqualTo("引擎橋接服務無法連線");
        assertRecordBackToUploadedWithoutGateErrors(id);
    }

    @Test
    void anExplicitSpecDirWithABridgeServerErrorIs502WithTheBridgeStatus() {
        bridgeCompileFails(500, "internal_error", null);
        String id = createText("# 文件", "MARKDOWN");

        Resp resp = parse(id, "/spec/frozen");

        assertThat(resp.status()).isEqualTo(502);
        assertThat(resp.<String>read("$.reason")).isEqualTo("引擎橋接服務錯誤");
        assertThat(resp.<Integer>read("$.details.bridgeStatus")).isEqualTo(500);
        assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo("internal_error");
    }

    @Test
    void anAdministratorsBridgeUrlTakesEffectImmediatelyAndResettingItRestoresTheDeploymentDefault() {
        FakeHttpServer other = OutboundFakes.TARGET;
        other.on("POST", "/sdd/compile", Response.json(200, ImportFixtures.sddCompileResponse("改過位址", 1)));
        bridgeCompiles("部署預設", 1);
        putSetting("sdd", "engineUrl", "http://127.0.0.1:" + other.port(), false);

        Resp custom = parse(createText("# 文件", "MARKDOWN"), "/spec/frozen");
        assertThat(custom.<String>read("$.data.parsedResult.project.name")).isEqualTo("改過位址");
        assertThat(other.receivedAt("/sdd/compile")).hasSize(1);
        assertThat(OutboundFakes.BRIDGE.receivedAt("/sdd/compile")).isEmpty();

        putSetting("sdd", "engineUrl", "http://127.0.0.1:" + other.port() + "/", false);
        assertThat(parse(createText("# 文件", "MARKDOWN"), "/spec/frozen").<String>read(
                "$.data.parsedResult.project.name")).as("尾端斜線不影響").isEqualTo("改過位址");

        assertThat(api.post(admin(), "/api/v1/settings/sdd/engineUrl/reset").status()).isEqualTo(200);
        Resp restored = parse(createText("# 文件", "MARKDOWN"), "/spec/frozen");
        assertThat(restored.<String>read("$.data.parsedResult.project.name")).isEqualTo("部署預設");
        assertThat(OutboundFakes.BRIDGE.receivedAt("/sdd/compile")).hasSize(1);
    }

    @Test
    void aPlainTextGoalWithAHeadingOrOverTwoThousandCharsIsADocumentNotAGoal() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                Response.json(200, ImportFixtures.chatCompletion(ImportFixtures.okTree())));
        bridgeHasNoSpec();
        bridgeDecomposes("d-1", steps(1));

        Resp heading = parse(createText("# 標題\n做一個待辦清單", "PLAIN_TEXT"), null);
        assertThat(heading.<String>read("$.data.path")).isEqualTo("LLM");
        Resp longText = parse(createText("需求描述".repeat(500), "PLAIN_TEXT"), null);
        assertThat(longText.<String>read("$.data.path")).isEqualTo("LLM");
        Resp markdownGoal = parse(createText("做一個待辦清單", "MARKDOWN"), null);
        assertThat(markdownGoal.<String>read("$.data.path")).as("MARKDOWN 一律不走 C").isEqualTo("LLM");
        Resp shortGoal = parse(createText("需求描述".repeat(499), "PLAIN_TEXT"), null);
        assertThat(shortGoal.<String>read("$.data.path")).as("1996 字元＜2000 且無標題").isEqualTo("DECOMPOSE");
    }

    // ── 路徑 C ────────────────────────────────────────────────────────────────

    @Test
    void aShortGoalIsDecomposedAndEveryStepBecomesATaskWithTheContractsPassCriteriaRules() {
        bridgeHasNoSpec();
        List<Map<String, Object>> steps = new ArrayList<>();
        steps.add(ImportFixtures.decomposeStep("s1", "建立骨架", "請建立專案骨架", "pytest -q"));
        steps.add(ImportFixtures.decomposeStep("s2", "", "請寫文件", null));
        steps.add(ImportFixtures.decomposeStep("s3", "跑測試", "請跑測試", "ls; rm -rf /"));
        bridgeDecomposes("d-77", steps);
        String id = createGoalText();

        Resp resp = parse(id, null);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.path")).isEqualTo("DECOMPOSE");
        assertThat(resp.<String>read("$.data.reasoning")).isEqualTo("先拆再做");
        assertThat(resp.<Object>read("$.data.aiModel")).isNull();
        assertThat(resp.<Object>read("$.data.tokenUsed")).isNull();
        assertThat(resp.<List<String>>read("$.data.parsedResult.draftIds")).containsExactly("d-77");
        assertThat(resp.<String>read("$.data.parsedResult.project.name")).isEqualTo("做一個待辦清單");
        assertThat(resp.<String>read("$.data.parsedResult.project.passCriteria"))
                .isEqualTo("做一個待辦清單\n要能新增與刪除");
        assertThat(resp.<String>read("$.data.parsedResult.project.description")).isEqualTo("先拆再做");
        assertThat(resp.<List<String>>read("$.data.parsedResult.goals[*].key")).containsExactly("g1");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].passCriteria")).isEqualTo("拆解出的全部步驟依序完成");
        assertThat(resp.<List<String>>read("$.data.parsedResult.goals[0].tasks[*].name"))
                .containsExactly("建立骨架", "s2", "跑測試");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[0].passCriteria")).isEqualTo("評估指令通過");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[0].evaluatorCommand")).isEqualTo("pytest -q");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[1].passCriteria"))
                .isEqualTo("（AI 解析未提供通過標準，請於 signoff 前補齊）");
        assertThat(resp.<Object>read("$.data.parsedResult.goals[0].tasks[2].evaluatorCommand")).isNull();
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[2].passCriteriaSpec.draftId"))
                .isEqualTo("d-77");
        assertThat(resp.<List<String>>read("$.data.warnings[*].code")).containsExactly("passcriteria_placeholder",
                "evaluator_command_dropped", "passcriteria_placeholder");
        assertThat(resp.<List<String>>read("$.data.warnings[*].location")).containsExactly("goals[0].tasks[1]",
                "goals[0].tasks[2]", "goals[0].tasks[2]");
        assertThat(OutboundFakes.LLM.received()).isEmpty();
    }

    @Test
    void theDecomposeRequestCarriesTheGoalContextAndMiniMaxOverridesOnlyWhenAnApiKeyIsSet() {
        bridgeHasNoSpec();
        bridgeDecomposes("d-1", steps(1));

        String withoutKey = createGoalText();
        assertThat(api.post(operator(), IMPORT + "/" + withoutKey + "/parse", Map.of("executionPath", EXEC_PATH,
                "additionalPrompt", "盡量少於 5 個任務")).status()).isEqualTo(200);
        Received plain = OutboundFakes.BRIDGE.receivedAt("/autoclaude/decompose").get(0);
        assertThat(bodyField(plain, "$.goal")).isEqualTo("做一個待辦清單\n要能新增與刪除");
        assertThat(bodyField(plain, "$.context")).isEqualTo("盡量少於 5 個任務");
        assertThat(bodyField(plain, "$.project")).isEqualTo("做一個待辦清單");
        assertThat(JsonPath.<Integer>read(plain.body(), "$.max_steps")).isEqualTo(24);
        assertThat(plain.body()).as("沒有金鑰就不帶 minimax 區段").doesNotContain("config_overrides");

        OutboundFakes.BRIDGE.reset();
        bridgeHasNoSpec();
        bridgeDecomposes("d-1", steps(1));
        configureFakeModel();
        String withKey = createGoalText();
        assertThat(parse(withKey, null).status()).isEqualTo(200);
        Received keyed = OutboundFakes.BRIDGE.receivedAt("/autoclaude/decompose").get(0);
        assertThat(bodyField(keyed, "$.config_overrides.minimax.base_url"))
                .isEqualTo(OutboundFakes.LLM.url(OutboundFakes.CHAT_PATH));
        assertThat(bodyField(keyed, "$.config_overrides.minimax.model")).isEqualTo("e2e-model");
        assertThat(JsonPath.<Integer>read(keyed.body(), "$.config_overrides.minimax.timeout_seconds")).isEqualTo(30);
        assertThat(bodyField(keyed, "$.context")).as("沒有補充說明時為空字串").isEmpty();
        assertThat(keyed.body()).as("金鑰絕不經由請求本文送給 Bridge").doesNotContain("sk-e2e-dummy").doesNotContain("api_key");
    }

    @Test
    void signoffApprovesTheDraftAtTheBridgeBeforeSigningAndConfirmKeepsTheEvaluatorsAndTheDraftReference() {
        bridgeHasNoSpec();
        bridgeDecomposes("d-77", steps(2));
        OutboundFakes.BRIDGE.on("POST", "/autoclaude/decompose/d-77:approve", Response.json(200, "{}"));
        String id = createGoalText();
        assertThat(parse(id, null).status()).isEqualTo(200);
        assertThat(OutboundFakes.BRIDGE.receivedAt("/autoclaude/decompose/d-77:approve")).isEmpty();

        Resp signed = signoff(id);

        assertThat(signed.status()).isEqualTo(200);
        assertThat(signed.<Boolean>read("$.data.signedOff")).isTrue();
        List<Received> approvals = OutboundFakes.BRIDGE.receivedAt("/autoclaude/decompose/d-77:approve");
        assertThat(approvals).hasSize(1);
        assertThat(bodyField(approvals.get(0), "$.approver")).isEqualTo(APPROVER);

        Resp confirmed = api.post(operator(), IMPORT + "/" + id + "/confirm");
        assertThat(confirmed.status()).isEqualTo(201);
        String goalId = api.get(viewer(), "/api/v1/projects/" + confirmed.id() + "/goals")
                .<List<String>>read("$.data[*].id").get(0);
        List<String> taskIds = api.get(viewer(), "/api/v1/goals/" + goalId + "/tasks")
                .read("$.data[*].id");
        Resp task = api.get(viewer(), "/api/v1/tasks/" + taskIds.get(1));
        assertThat(task.<String>read("$.data.evaluatorCommand")).isEqualTo("pytest -q");
        assertThat(task.<String>read("$.data.passCriteriaSpec.source")).isEqualTo("decompose");
        assertThat(task.<String>read("$.data.passCriteriaSpec.draftId")).isEqualTo("d-77");
        assertThat(task.<String>read("$.data.passCriteriaSpec.stepId")).isEqualTo("s2");
        assertThat(task.<Boolean>read("$.data.signedOff")).isTrue();
    }

    @Test
    void anAlreadySignedOffDraftAtTheBridgeCountsAsSuccess() {
        bridgeHasNoSpec();
        bridgeDecomposes("d-77", steps(1));
        OutboundFakes.BRIDGE.on("POST", "/autoclaude/decompose/d-77:approve", Response.json(409,
                ImportFixtures.bridgeError(409, "already_signed_off", null, "草案已簽署")));
        String id = createGoalText();
        assertThat(parse(id, null).status()).isEqualTo(200);

        Resp signed = signoff(id);

        assertThat(signed.status()).isEqualTo(200);
        assertThat(signed.<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(signed.<String>read("$.data.signedOffBy")).isEqualTo(APPROVER);
    }

    private void assertSignoffRefusedAndNothingSigned(String id, Resp resp, int status, String reason) {
        assertThat(resp.status()).isEqualTo(status);
        assertThat(resp.<String>read("$.reason")).isEqualTo(reason);
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<Boolean>read("$.data.signedOff")).as("Bridge 沒批准就不留下任何簽核").isFalse();
        assertThat(record.<Object>read("$.data.signedOffBy")).isNull();
        assertThat(record.<Object>read("$.data.signedOffAt")).isNull();
        assertThat(record.<String>read("$.data.status")).isEqualTo("PARSED");
        assertThat(api.post(operator(), IMPORT + "/" + id + "/confirm").status()).as("未簽核不可 confirm")
                .isEqualTo(409);
    }

    @Test
    void aDraftThatTheBridgeNoLongerKnowsIs409AndNothingIsSigned() {
        bridgeHasNoSpec();
        bridgeDecomposes("d-77", steps(1));
        OutboundFakes.BRIDGE.on("POST", "/autoclaude/decompose/d-77:approve", Response.json(404,
                ImportFixtures.bridgeError(404, "draft_not_found", null, "工作區已清除")));
        String id = createGoalText();
        assertThat(parse(id, null).status()).isEqualTo(200);

        Resp resp = signoff(id);

        assertSignoffRefusedAndNothingSigned(id, resp, 409, "草案已失效，請重新解析");
        assertThat(resp.<String>read("$.details.draftId")).isEqualTo("d-77");
    }

    @Test
    void aBridgeServerErrorWhileApprovingIs502AndNothingIsSigned() {
        bridgeHasNoSpec();
        bridgeDecomposes("d-77", steps(1));
        OutboundFakes.BRIDGE.on("POST", "/autoclaude/decompose/d-77:approve", Response.json(500,
                ImportFixtures.bridgeError(500, "internal_error", null, null)));
        String id = createGoalText();
        assertThat(parse(id, null).status()).isEqualTo(200);

        Resp resp = signoff(id);

        assertSignoffRefusedAndNothingSigned(id, resp, 502, "引擎橋接服務錯誤");
        assertThat(resp.<Integer>read("$.details.bridgeStatus")).isEqualTo(500);
    }

    @Test
    void aBridgeThatCannotBeReachedWhileApprovingIs502AndNothingIsSigned() {
        bridgeHasNoSpec();
        bridgeDecomposes("d-77", steps(1));
        String id = createGoalText();
        assertThat(parse(id, null).status()).isEqualTo(200);
        pointBridgeAtNowhere();

        Resp resp = signoff(id);

        assertSignoffRefusedAndNothingSigned(id, resp, 502, "引擎橋接服務無法連線");
    }

    @Test
    void aBridgeGateRejectionBecomesTheBoundedGateErrorWithoutALocationAndIsStored() {
        bridgeHasNoSpec();
        bridgeDecomposeFails(422, "max_steps", "max_steps", "拆出 30 步，超過上限 24");
        String id = createGoalText();

        Resp resp = parse(id, null);

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(GATE_REASON);
        assertThat(resp.<String>read("$.details.path")).isEqualTo("DECOMPOSE");
        assertThat(resp.<List<String>>read("$.errors[*].gate")).containsExactly("max_steps");
        assertThat(resp.<String>read("$.errors[0].detail")).isEqualTo("拆出 30 步，超過上限 24");
        assertThat(resp.has("$.errors[0].location")).isFalse();
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<String>read("$.data.status")).isEqualTo("UPLOADED");
        assertThat(record.<List<String>>read("$.data.lastParseErrors[*].gate")).containsExactly("max_steps");
    }

    @Test
    void theOtherBridgeGatesPassThroughVerbatimIncludingMissingBrainConfiguration() {
        for (String[] gate : new String[][] {{"cycle", "步驟依賴成環"}, {"empty_prompt", "步驟 s2 的 prompt 為空"},
                {"brain_failed", "Brain 回傳 None"},
                {"brain_unsupported", "無法建立 Brain：缺少 MINIMAX_API_KEY"}}) {
            OutboundFakes.BRIDGE.reset();
            bridgeHasNoSpec();
            bridgeDecomposeFails(422, gate[0], gate[0], gate[1]);
            Resp resp = parse(createGoalText(), null);
            assertThat(resp.status()).as(gate[0]).isEqualTo(422);
            assertThat(resp.<List<String>>read("$.errors[*].gate")).containsExactly(gate[0]);
            assertThat(resp.<String>read("$.errors[0].detail")).isEqualTo(gate[1]);
        }
    }

    @Test
    void aBridgeRejectionWithoutAGateIsTheEngineRefusingTheRequestNotAGate() {
        bridgeHasNoSpec();
        OutboundFakes.BRIDGE.on("POST", "/autoclaude/decompose", Response.json(422,
                "{\"code\":422,\"reason\":\"invalid_request\",\"violations\":[{\"field\":\"goal\","
                        + "\"rule\":\"max_length\",\"message\":\"太長\"}]}"));
        String id = createGoalText();

        Resp resp = parse(id, null);

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo("引擎拒絕此請求");
        assertThat(resp.<String>read("$.details.bridgeReason")).isEqualTo("invalid_request");
        assertThat(resp.<String>read("$.details.violations[0].field")).isEqualTo("goal");
        assertRecordBackToUploadedWithoutGateErrors(id);
    }

    @Test
    void theBackendNeverTrustsTheBridgesAnswerAndRechecksTheBoundedGates() {
        bridgeHasNoSpec();
        bridgeDecomposes("d-1", steps(26));
        String id = createGoalText();

        Resp resp = parse(id, null);

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<List<String>>read("$.errors[*].gate")).containsExactly("max_steps");
        assertThat(resp.<String>read("$.errors[0].location")).isEqualTo("goals[0].tasks");
        assertThat(resp.<String>read("$.details.path")).isEqualTo("DECOMPOSE");
    }

    @Test
    void aDecompositionWithoutStepsIsBrainFailed() {
        bridgeHasNoSpec();
        bridgeDecomposes("d-1", List.of());
        String id = createGoalText();

        Resp resp = parse(id, null);

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<List<String>>read("$.errors[*].gate")).containsExactly("brain_failed");
        assertThat(resp.<String>read("$.errors[0].detail")).contains("no_steps");
    }

    @Test
    void aBridgeThatFailsOrCannotBeReachedDuringDecomposeIs502AndTheRecordIsRetryable() {
        bridgeHasNoSpec();
        bridgeDecomposeFails(500, "internal_error", null, null);
        String failing = createGoalText();
        Resp serverError = parse(failing, null);
        assertThat(serverError.status()).isEqualTo(502);
        assertThat(serverError.<String>read("$.reason")).isEqualTo("引擎橋接服務錯誤");
        assertThat(serverError.<Integer>read("$.details.bridgeStatus")).isEqualTo(500);
        assertRecordBackToUploadedWithoutGateErrors(failing);

        putSetting("autoclaude", "engineUrl", "http://127.0.0.1:1", false);
        String unreachable = createGoalText();
        Resp down = parse(unreachable, null);
        assertThat(down.status()).isEqualTo(502);
        assertThat(down.<String>read("$.reason")).isEqualTo("引擎橋接服務無法連線");
        assertRecordBackToUploadedWithoutGateErrors(unreachable);

        // 修好位址、Bridge 恢復後，同一筆記錄可以直接重新解析
        assertThat(api.post(admin(), "/api/v1/settings/autoclaude/engineUrl/reset").status()).isEqualTo(200);
        OutboundFakes.BRIDGE.reset();
        bridgeHasNoSpec();
        bridgeDecomposes("d-1", steps(1));
        assertThat(parse(unreachable, null).status()).isEqualTo(200);
    }
}
