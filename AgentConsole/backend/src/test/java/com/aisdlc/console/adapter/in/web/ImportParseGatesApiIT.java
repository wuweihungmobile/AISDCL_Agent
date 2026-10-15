package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractOutboundIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.FakeHttpServer.Response;
import com.aisdlc.console.support.ImportFixtures;
import com.aisdlc.console.support.OutboundFakes;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 匯入解析的有界閘、模型端失敗與編輯消毒（契約 §1.1.3、§1.1.4、§3.3.5、E2E-01 的變體表）。為什麼重要（US-I-10）：
 * 上限由後端閘守住，而且「完整顯示、不截斷、不修剪」——違規時使用者必須一次看到全部原因與位置，記錄回到 UPLOADED 可重試；
 * 失敗的重新解析不得吃掉先前成功解析的內容；人工編輯與 AI 輸出走同一套檢查，不能成為繞過閘的後門。
 */
class ImportParseGatesApiIT extends AbstractOutboundIT {

    private static final String IMPORT = "/api/v1/import";
    private static final String GATE_REASON = "解析結果未通過有界閘";
    private static final String COMMAND_REASON = "命令含禁用字元";

    // ── 夾具 ─────────────────────────────────────────────────────────────────

    private static String treeWithTasks(int count, int blankDescriptionAt) {
        List<Map<String, Object>> tasks = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            Map<String, Object> task = ImportFixtures.doneTask("任務 " + (i + 1), i + 1);
            if (i == blankDescriptionAt) {
                task.put("description", "  ");
            }
            tasks.add(task);
        }
        return ImportFixtures.treeJson("E2E 匯入專案", List.of(ImportFixtures.goal("g1", "基礎", List.of(), tasks)));
    }

    private static String cyclicTree() {
        return ImportFixtures.treeJson("E2E 匯入專案", List.of(
                ImportFixtures.goal("g1", "基礎", List.of("g2"), List.of(ImportFixtures.doneTask("甲", 1))),
                ImportFixtures.goal("g2", "核心", List.of("g1"), List.of(ImportFixtures.doneTask("乙", 2)))));
    }

    private static String treeWithTask(Map<String, Object> task) {
        return ImportFixtures.treeJson("E2E 匯入專案",
                List.of(ImportFixtures.goal("g1", "基礎", List.of(), List.of(task))));
    }

    /** 文件含 {@code marker} 時回 {@code response}（先註冊先比對）；預設回正常的 S-OK。 */
    private static void stubOnMarker(String marker, Response response) {
        OutboundFakes.LLM.on(r -> r.method().equals("POST") && r.body().contains(marker), response);
    }

    private static void stubDefaultOk() {
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                Response.json(200, ImportFixtures.chatCompletion(ImportFixtures.okTree())));
    }

    private String createDocument(String marker) {
        Resp created = api.post(operator(), IMPORT + "/text", Map.of("content",
                ImportFixtures.markdownDocument(marker), "sourceType", "MARKDOWN"));
        assertThat(created.status()).isEqualTo(201);
        return created.id();
    }

    private Resp parse(String id) {
        return api.post(operator(), IMPORT + "/" + id + "/parse",
                Map.of("autonomyLevel", 3, "executionPath", "/work/proj-import"));
    }

    private Resp putTree(String id, Map<String, Object> tree) {
        return api.put(operator(), IMPORT + "/" + id + "/result", Map.of("parsedResult", tree));
    }

    /** 建立、解析成功並（選擇性）簽核的記錄，回其 id。 */
    private String parsedRecord(boolean signedOff) {
        configureFakeModel();
        stubDefaultOk();
        String id = createDocument(null);
        assertThat(parse(id).status()).isEqualTo(200);
        if (signedOff) {
            assertThat(api.post(operator(), IMPORT + "/" + id + "/signoff", Map.of("approver", "a")).status())
                    .isEqualTo(200);
        }
        return id;
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

    // ── 有界閘變體（契約 E2E-01 變體表）──────────────────────────────────────────

    /** marker、stub 回應、預期的 [gate, location(可為 null)] 清單、detail 應含的字樣。 */
    private record GateCase(String marker, Response response, List<String[]> expected, List<String> detailContains) {

        @Override
        public String toString() {
            return marker;
        }
    }

    private static Response ok(String treeJson) {
        return Response.json(200, ImportFixtures.chatCompletion(treeJson));
    }

    static Stream<GateCase> gateCases() {
        return Stream.of(
                new GateCase("GATE_MAX", ok(treeWithTasks(25, -1)),
                        List.<String[]>of(new String[] {"max_steps", "goals[0].tasks"}), List.of("25", "24")),
                new GateCase("GATE_CYCLE", ok(cyclicTree()),
                        List.<String[]>of(new String[] {"cycle", "goals[0].dependsOn"}), List.of("->")),
                new GateCase("GATE_EMPTY", ok(treeWithTasks(2, 1)),
                        List.<String[]>of(new String[] {"empty_prompt", "goals[0].tasks[1].description"}), List.of()),
                new GateCase("GATE_EMPTY_NAME", ok(treeWithTask(taskNamed("  "))),
                        List.<String[]>of(new String[] {"empty_prompt", "goals[0].tasks[0].name"}), List.of()),
                new GateCase("GATE_LONG", ok(treeWithTask(taskWithDescription("字".repeat(20_500)))),
                        List.<String[]>of(new String[] {"prompt_too_long", "goals[0].tasks[0]"}), List.of("20")),
                new GateCase("GATE_MULTI", ok(treeWithTasks(25, 3)),
                        List.<String[]>of(new String[] {"empty_prompt", "goals[0].tasks[3].description"},
                                new String[] {"max_steps", "goals[0].tasks"}), List.of()),
                new GateCase("GATE_BADJSON", ok("not json"),
                        List.<String[]>of(new String[] {"brain_failed", null}), List.of()),
                new GateCase("GATE_HTTP500", Response.json(500, "{\"error\":\"boom sk-e2e-dummy\"}"),
                        List.<String[]>of(new String[] {"brain_failed", null}), List.of("500")));
    }

    private static Map<String, Object> taskNamed(String name) {
        Map<String, Object> task = ImportFixtures.doneTask("x", 1);
        task.put("name", name);
        return task;
    }

    private static Map<String, Object> taskWithDescription(String description) {
        Map<String, Object> task = ImportFixtures.doneTask("長任務", 1);
        task.put("description", description);
        return task;
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("gateCases")
    void aGateViolationIs422ListsEverythingRevertsToUploadedAndIsClearedByASuccessfulReparse(GateCase gate) {
        configureFakeModel();
        stubOnMarker(gate.marker(), gate.response());
        stubDefaultOk();
        String id = createDocument(gate.marker());

        Resp resp = parse(id);

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(GATE_REASON);
        assertThat(resp.<String>read("$.details.path")).isEqualTo("LLM");
        List<String> gates = resp.read("$.errors[*].gate");
        assertThat(gates).containsExactlyElementsOf(gate.expected().stream().map(e -> e[0]).toList());
        for (int i = 0; i < gate.expected().size(); i++) {
            String location = gate.expected().get(i)[1];
            Map<String, Object> error = resp.read("$.errors[" + i + "]");
            if (location == null) {
                assertThat(error).as("沒有位置的閘不帶 location").doesNotContainKey("location");
                assertThat(error.get("field")).as("field 退回閘名稱").isEqualTo(gate.expected().get(i)[0]);
            } else {
                assertThat(error).containsEntry("location", location).containsEntry("field", location);
            }
            assertThat(error.get("message")).isEqualTo(error.get("detail"));
        }
        List<String> details = resp.read("$.errors[*].detail");
        for (String expectedText : gate.detailContains()) {
            assertThat(details).anySatisfy(d -> assertThat(d).contains(expectedText));
        }
        assertThat(resp.body()).as("錯誤不得含金鑰").doesNotContain("sk-e2e-dummy");

        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<String>read("$.data.status")).isEqualTo("UPLOADED");
        assertThat(record.<List<String>>read("$.data.lastParseErrors[*].gate"))
                .containsExactlyElementsOf(gates);
        assertThat(record.<Object>read("$.data.parsedResult")).as("失敗不寫 parsedResult").isNull();
        assertThat(record.<Object>read("$.data.parsePath")).as("失敗不寫 parsePath").isNull();
        assertThat(record.<Object>read("$.data.aiModel")).isNull();
        assertThat(record.<Boolean>read("$.data.signedOff")).isFalse();

        // 改用正常的模型回應重新解析：成功並清空 lastParseErrors
        OutboundFakes.LLM.reset();
        stubDefaultOk();
        Resp retry = parse(id);
        assertThat(retry.status()).isEqualTo(200);
        Resp after = api.get(viewer(), IMPORT + "/" + id);
        assertThat(after.<String>read("$.data.status")).isEqualTo("PARSED");
        assertThat(after.<Object>read("$.data.lastParseErrors")).isNull();
        assertThat(after.<String>read("$.data.parsePath")).isEqualTo("LLM");
    }

    @Test
    void theFailedParseListsEveryViolationAtOnceInTheFixedOrder() {
        configureFakeModel();
        // 25 個任務、其中兩個描述為空、另有目標依賴成環：四道閘一次全列，順序 empty_prompt → max_steps → cycle
        List<Map<String, Object>> tasks = new ArrayList<>();
        for (int i = 0; i < 25; i++) {
            Map<String, Object> task = ImportFixtures.doneTask("任務 " + i, i);
            if (i == 2 || i == 7) {
                task.put("description", "");
            }
            tasks.add(task);
        }
        String tree = ImportFixtures.treeJson("E2E 匯入專案", List.of(
                ImportFixtures.goal("g1", "基礎", List.of("g2"), tasks),
                ImportFixtures.goal("g2", "核心", List.of("g1"), List.of(ImportFixtures.doneTask("乙", 2)))));
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH, ok(tree));
        String id = createDocument(null);

        Resp resp = parse(id);

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<List<String>>read("$.errors[*].gate")).containsExactly("empty_prompt", "empty_prompt",
                "max_steps", "cycle");
        assertThat(resp.<List<String>>read("$.errors[*].location")).containsExactly(
                "goals[0].tasks[2].description", "goals[0].tasks[7].description", "goals[0].tasks", "goals[0].dependsOn");
        assertThat(api.get(viewer(), IMPORT + "/" + id).<Integer>read("$.data.lastParseErrors.length()"))
                .isEqualTo(4);
    }

    @Test
    void exactlyTheHardLimitPassesTheGate() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH, ok(treeWithTasks(24, -1)));
        String id = createDocument(null);
        Resp resp = parse(id);
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.parsedResult.goals[0].tasks.length()")).isEqualTo(24);
    }

    // ── 模型端失敗 ─────────────────────────────────────────────────────────────

    private void assertBrainGate(Resp resp, String gate, String detailContains) {
        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<String>read("$.reason")).isEqualTo(GATE_REASON);
        assertThat(resp.<List<String>>read("$.errors[*].gate")).containsExactly(gate);
        assertThat(resp.<String>read("$.errors[0].detail")).contains(detailContains);
        assertThat(resp.has("$.errors[0].location")).isFalse();
    }

    @Test
    void withoutAnApiKeyTheLlmPathIsBrainUnsupportedAndNothingIsSent() {
        putSetting("model", "apiUrl", OutboundFakes.LLM.url(OutboundFakes.CHAT_PATH), false);
        stubDefaultOk();
        String id = createDocument(null);

        Resp resp = parse(id);

        assertBrainGate(resp, "brain_unsupported", "model.apiKey");
        assertThat(OutboundFakes.LLM.received()).isEmpty();
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<String>read("$.data.status")).isEqualTo("UPLOADED");
        assertThat(record.<List<String>>read("$.data.lastParseErrors[*].gate")).containsExactly("brain_unsupported");
    }

    @Test
    void aStoredApiUrlThatNoLongerPassesTheOutboundPolicyIsRefusedAtUseTimeToo() {
        configureFakeModel();
        stubDefaultOk();
        // 繞過 API 的儲存時檢查，直接把庫內值改成私網位址（例如舊資料或被竄改）
        jdbc.update("update console.system_configs set value = 'http://10.0.0.5/v1/chat/completions' "
                + "where category = 'model' and key = 'apiUrl'");
        String id = createDocument(null);

        Resp resp = parse(id);

        assertBrainGate(resp, "brain_unsupported", "private_ip");
        assertThat(OutboundFakes.LLM.received()).isEmpty();
    }

    @Test
    void aNameInTheAllowlistThatResolvesToAPrivateAddressIsRefusedBeforeAnyConnection() {
        configureFakeModel();
        putSetting("model", "apiUrl", "http://rebind.e2e.test:" + OutboundFakes.LLM.port() + "/v1/chat/completions",
                false);
        stubDefaultOk();
        String id = createDocument(null);

        Resp resp = parse(id);

        assertThat(resp.status()).isEqualTo(422);
        assertThat(resp.<List<String>>read("$.errors[*].gate")).containsExactly("brain_unsupported");
        assertThat(resp.<String>read("$.errors[0].detail")).contains("dns_rebinding");
        assertThat(OutboundFakes.LLM.received()).as("DNS 解析到私網：連線前就拒絕").isEmpty();
    }

    @Test
    void aModelThatRedirectsIsNotFollowed() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                Response.redirect(OutboundFakes.TARGET.url("/stolen")));
        OutboundFakes.TARGET.on("POST", "/stolen", Response.json(200, ImportFixtures.chatCompletion(
                ImportFixtures.okTree())));
        String id = createDocument(null);

        Resp resp = parse(id);

        assertBrainGate(resp, "brain_failed", "302");
        assertThat(OutboundFakes.TARGET.received()).as("重導向目標的請求數必須是 0").isEmpty();
    }

    @Test
    void aSlowModelIsCutOffAtTheConfiguredTimeoutAndReportedAsAFailureNotAHang() {
        configureFakeModel();
        putSetting("model", "timeout", "1", false);
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                ok(ImportFixtures.okTree()).delayed(4_000));
        String id = createDocument(null);

        long started = System.nanoTime();
        Resp resp = parse(id);
        long elapsedMillis = (System.nanoTime() - started) / 1_000_000;

        assertBrainGate(resp, "brain_failed", "逾時");
        assertThat(elapsedMillis).as("在 model.timeout（1 秒）附近返回，而不是等滿模型的 4 秒").isLessThan(3_500);
        assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.status")).isEqualTo("UPLOADED");
    }

    @Test
    void anAuthFailureFromTheModelIsReportedWithoutLeakingTheKey() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH, Response.json(401,
                "{\"error\":{\"message\":\"bad key sk-e2e-dummy\"}}"));
        String id = createDocument(null);

        Resp resp = parse(id);

        assertBrainGate(resp, "brain_failed", "401");
        assertThat(resp.body()).doesNotContain("sk-e2e-dummy").doesNotContain("127.0.0.1");
    }

    // ── 重新解析 ───────────────────────────────────────────────────────────────

    @Test
    void aFailedReparseKeepsThePreviousResultButTheRecordGoesBackToUploaded() {
        String id = parsedRecord(false);
        Map<String, Object> tree = currentTree(id);
        goals(tree).get(0).put("name", "使用者編輯過的目標名");
        assertThat(putTree(id, tree).status()).isEqualTo(200);

        OutboundFakes.LLM.reset();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH, ok(treeWithTasks(25, -1)));
        Resp failed = parse(id);

        assertThat(failed.status()).isEqualTo(422);
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<String>read("$.data.status")).isEqualTo("UPLOADED");
        assertThat(record.<String>read("$.data.parsedResult.goals[0].name")).as("先前成功且被編輯過的內容保留")
                .isEqualTo("使用者編輯過的目標名");
        assertThat(record.<String>read("$.data.parsePath")).isEqualTo("LLM");
        assertThat(record.<List<String>>read("$.data.lastParseErrors[*].gate")).containsExactly("max_steps");
        assertThat(putTree(id, tree).status()).as("回到 UPLOADED：要繼續編輯須再成功解析一次").isEqualTo(409);

        OutboundFakes.LLM.reset();
        stubDefaultOk();
        assertThat(parse(id).status()).isEqualTo(200);
        Resp healed = api.get(viewer(), IMPORT + "/" + id);
        assertThat(healed.<Object>read("$.data.lastParseErrors")).isNull();
        assertThat(healed.<String>read("$.data.parsedResult.goals[0].name")).as("成功的重新解析以新結果覆寫")
                .isEqualTo("基礎");
    }

    @Test
    void aSuccessfulReparseRevokesNothingBecauseSignedOffDraftsCannotBeReparsedAtAll() {
        String id = parsedRecord(true);
        Resp resp = parse(id);
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo("已 signoff，不可重新解析");
        assertThat(OutboundFakes.LLM.received()).as("只有第一次解析打過模型").hasSize(1);
    }

    @Test
    void aSecondParseWhileTheFirstIsStillRunningIs409AndTheFirstStillSucceeds() throws Exception {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH, ok(ImportFixtures.okTree()).delayed(1_500));
        String id = createDocument(null);

        AtomicReference<Resp> first = new AtomicReference<>();
        Thread runner = new Thread(() -> first.set(parse(id)));
        runner.start();
        long deadline = System.currentTimeMillis() + 5_000;
        while (OutboundFakes.LLM.received().isEmpty() && System.currentTimeMillis() < deadline) {
            Thread.sleep(20);
        }
        assertThat(OutboundFakes.LLM.received()).as("第一個 parse 已送出模型請求").hasSize(1);

        Resp concurrent = parse(id);
        assertThat(concurrent.status()).isEqualTo(409);
        assertThat(concurrent.<String>read("$.reason")).isEqualTo("解析中，請稍候");
        assertThat(concurrent.<String>read("$.details.status")).isEqualTo("PARSING");
        assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.status")).isEqualTo("PARSING");
        assertThat(api.post(operator(), IMPORT + "/" + id + "/reject").status()).as("解析中不可放棄").isEqualTo(409);

        runner.join();
        assertThat(first.get().status()).isEqualTo(200);
        assertThat(OutboundFakes.LLM.received()).as("第二個 parse 沒有外呼").hasSize(1);
        assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.status")).isEqualTo("PARSED");
    }

    // ── 編輯（PUT result）：消毒與閘 ─────────────────────────────────────────────

    @Test
    void anUnsafeEvaluatorCommandOrAnUncompilableRegexIs400WithTheViolationsNamed() {
        String id = parsedRecord(false);
        Map<String, Object> tree = currentTree(id);
        Map<String, Object> task = tasks(goals(tree).get(0)).get(0);

        task.put("evaluatorCommand", "pytest -q; echo done");
        Resp semicolon = putTree(id, tree);
        assertThat(semicolon.status()).isEqualTo(400);
        assertThat(semicolon.<String>read("$.reason")).isEqualTo(COMMAND_REASON);
        assertThat(semicolon.<List<String>>read("$.details.violations")).containsExactly(";");
        assertThat(semicolon.<String>read("$.errors[0].field"))
                .isEqualTo("parsedResult.goals[0].tasks[0].evaluatorCommand");

        task.put("evaluatorCommand", "echo $(whoami) > out");
        assertThat(putTree(id, tree).<List<String>>read("$.details.violations")).containsExactly("$", ">");
        task.put("evaluatorCommand", "pytest -q\necho second line");
        Resp newline = putTree(id, tree);
        assertThat(newline.status()).as("換行等同命令分隔").isEqualTo(400);
        assertThat(newline.<String>read("$.reason")).isEqualTo(COMMAND_REASON);

        task.put("evaluatorCommand", "pytest -q");
        task.put("expectedOutputRegex", "([");
        Resp regex = putTree(id, tree);
        assertThat(regex.status()).isEqualTo(400);
        assertThat(regex.<String>read("$.errors[0].field"))
                .isEqualTo("parsedResult.goals[0].tasks[0].expectedOutputRegex");

        task.put("expectedOutputRegex", "\\[T1_DONE\\]");
        assertThat(putTree(id, tree).status()).isEqualTo(200);
    }

    @Test
    void theSameSanitizationAppliesInsideTheStructuredPassCriteriaSpec() {
        String id = parsedRecord(false);
        Map<String, Object> tree = currentTree(id);
        Map<String, Object> task = tasks(goals(tree).get(0)).get(0);
        task.put("passCriteriaSpec", Map.of("all", List.of(Map.of("evaluatorCommand", "ls; rm -rf /"))));

        Resp resp = putTree(id, tree);

        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo(COMMAND_REASON);
        assertThat(resp.<String>read("$.errors[0].field")).contains("passCriteriaSpec.all[0].evaluatorCommand");
    }

    @Test
    void sanitizationComesBeforeTheBoundedGates() {
        String id = parsedRecord(false);
        Map<String, Object> tree = currentTree(id);
        List<Map<String, Object>> many = new ArrayList<>();
        for (int i = 0; i < 25; i++) {
            many.add(ImportFixtures.doneTask("任務 " + i, i));
        }
        many.get(0).put("evaluatorCommand", "a; b");
        goals(tree).get(0).put("tasks", many);

        Resp resp = putTree(id, tree);

        assertThat(resp.status()).as("400 消毒先於 422 閘").isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo(COMMAND_REASON);
    }

    @Test
    void aBlankTaskNameOrDescriptionIsAGate422ButAMissingOrNullOneIsAStructural400() {
        String id = parsedRecord(false);

        Map<String, Object> blankName = currentTree(id);
        tasks(goals(blankName).get(0)).get(0).put("name", "  ");
        Resp blank = putTree(id, blankName);
        assertThat(blank.status()).isEqualTo(422);
        assertThat(blank.<String>read("$.reason")).isEqualTo(GATE_REASON);
        assertThat(blank.<List<String>>read("$.errors[*].gate")).containsExactly("empty_prompt");
        assertThat(blank.<String>read("$.errors[0].location")).isEqualTo("goals[0].tasks[0].name");

        Map<String, Object> blankDescription = currentTree(id);
        tasks(goals(blankDescription).get(1)).get(0).put("description", "\t\n ");
        assertThat(putTree(id, blankDescription).<String>read("$.errors[0].location"))
                .isEqualTo("goals[1].tasks[0].description");

        Map<String, Object> nullName = currentTree(id);
        tasks(goals(nullName).get(0)).get(0).put("name", null);
        Resp nulled = putTree(id, nullName);
        assertThat(nulled.status()).isEqualTo(400);
        assertThat(nulled.<List<String>>read("$.errors[*].field"))
                .contains("parsedResult.goals[0].tasks[0].name");

        Map<String, Object> missingDescription = currentTree(id);
        tasks(goals(missingDescription).get(0)).get(0).remove("description");
        Resp missing = putTree(id, missingDescription);
        assertThat(missing.status()).isEqualTo(400);
        assertThat(missing.<List<String>>read("$.errors[*].field"))
                .contains("parsedResult.goals[0].tasks[0].description");
    }

    @Test
    void structuralProblemsAreReportedAs400WithTheFieldPath() {
        String id = parsedRecord(false);
        Map<String, Map<String, Object>> cases = new LinkedHashMap<>();

        Map<String, Object> noGoals = currentTree(id);
        noGoals.put("goals", List.of());
        cases.put("parsedResult.goals", noGoals);

        Map<String, Object> noTasks = currentTree(id);
        goals(noTasks).get(0).put("tasks", List.of());
        cases.put("parsedResult.goals[0].tasks", noTasks);

        Map<String, Object> blankCriteria = currentTree(id);
        tasks(goals(blankCriteria).get(0)).get(0).put("passCriteria", " ");
        cases.put("parsedResult.goals[0].tasks[0].passCriteria", blankCriteria);

        Map<String, Object> blankGoalName = currentTree(id);
        goals(blankGoalName).get(0).put("name", "");
        cases.put("parsedResult.goals[0].name", blankGoalName);

        Map<String, Object> blankKey = currentTree(id);
        goals(blankKey).get(0).put("key", "");
        cases.put("parsedResult.goals[0].key", blankKey);

        Map<String, Object> noProject = currentTree(id);
        noProject.remove("project");
        cases.put("parsedResult.project", noProject);

        Map<String, Object> blankProjectName = currentTree(id);
        @SuppressWarnings("unchecked")
        Map<String, Object> project = (Map<String, Object>) blankProjectName.get("project");
        project.put("name", " ");
        cases.put("parsedResult.project.name", blankProjectName);

        Map<String, Object> badAutonomy = currentTree(id);
        @SuppressWarnings("unchecked")
        Map<String, Object> badProject = (Map<String, Object>) badAutonomy.get("project");
        badProject.put("autonomyLevel", 11);
        cases.put("parsedResult.project.autonomyLevel", badAutonomy);

        Map<String, Object> tooManyRetries = currentTree(id);
        tasks(goals(tooManyRetries).get(0)).get(0).put("maxRetries", 21);
        cases.put("parsedResult.goals[0].tasks[0].maxRetries", tooManyRetries);

        Map<String, Object> negativeTokens = currentTree(id);
        tasks(goals(negativeTokens).get(0)).get(0).put("estimatedTokens", -1);
        cases.put("parsedResult.goals[0].tasks[0].estimatedTokens", negativeTokens);

        cases.forEach((field, tree) -> {
            Resp resp = putTree(id, tree);
            assertThat(resp.status()).as(field).isEqualTo(400);
            assertThat(resp.<List<String>>read("$.errors[*].field")).as(field).contains(field);
        });
        assertThat(api.put(operator(), IMPORT + "/" + id + "/result", Map.of()).status()).isEqualTo(400);
        assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.status")).as("全部 400 都沒改狀態")
                .isEqualTo("PARSED");
    }

    @Test
    void dependencyProblemsInAnEditAreCycleGates() {
        String id = parsedRecord(false);

        Map<String, Object> selfDependency = currentTree(id);
        goals(selfDependency).get(0).put("dependsOn", List.of("g1"));
        Resp self = putTree(id, selfDependency);
        assertThat(self.status()).isEqualTo(422);
        assertThat(self.<List<String>>read("$.errors[*].gate")).containsExactly("cycle");
        assertThat(self.<String>read("$.errors[0].location")).isEqualTo("goals[0].dependsOn");

        Map<String, Object> unknown = currentTree(id);
        goals(unknown).get(1).put("dependsOn", List.of("g9"));
        Resp ghost = putTree(id, unknown);
        assertThat(ghost.status()).isEqualTo(422);
        assertThat(ghost.<String>read("$.errors[0].detail")).contains("g9");

        Map<String, Object> duplicate = currentTree(id);
        goals(duplicate).get(1).put("key", "g1");
        goals(duplicate).get(1).put("dependsOn", List.of());
        Resp dup = putTree(id, duplicate);
        assertThat(dup.status()).isEqualTo(422);
        assertThat(dup.<String>read("$.errors[0].detail")).contains("g1");
        assertThat(dup.<String>read("$.errors[0].location")).isEqualTo("goals[1].key");
    }

    @Test
    void aRejectedEditChangesNothingNotEvenAnExistingSignoff() {
        String id = parsedRecord(true);
        Map<String, Object> tree = currentTree(id);
        goals(tree).get(0).put("dependsOn", List.of("g1"));

        Resp resp = putTree(id, tree);

        assertThat(resp.status()).isEqualTo(422);
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<Boolean>read("$.data.signedOff")).as("被拒絕的編輯不撤銷既有 signoff").isTrue();
        assertThat(record.<String>read("$.data.status")).isEqualTo("PARSED");
        assertThat(record.<List<String>>read("$.data.parsedResult.goals[0].dependsOn")).isEmpty();
    }

    @Test
    void aPlaceholderPassCriteriaInAnEditedTreeIsWarnedAboutAgain() {
        String id = parsedRecord(false);
        Map<String, Object> tree = currentTree(id);
        tasks(goals(tree).get(0)).get(1).put("passCriteria", "（AI 解析未提供通過標準，請於 signoff 前補齊）");

        Resp resp = putTree(id, tree);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<String>>read("$.data.warnings[*].code")).containsExactly("passcriteria_placeholder");
        assertThat(resp.<List<String>>read("$.data.warnings[*].location")).containsExactly("goals[0].tasks[1]");
    }

    @Test
    void placeholderPassCriteriaFromTheModelAreFilledAndWarnedAtParseTime() {
        configureFakeModel();
        Map<String, Object> bare = ImportFixtures.task("初始化", "請輸出 [T1_DONE]", "");
        Map<String, Object> goal = ImportFixtures.goal("g1", "基礎", List.of(), List.of(bare));
        goal.put("passCriteria", "");
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH, ok(ImportFixtures.treeJson("無標準專案", List.of(goal))
                .replace("\"passCriteria\":\"全部目標完成\"", "\"passCriteria\":\"\"")));
        String id = createDocument(null);

        Resp resp = parse(id);

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<String>>read("$.data.warnings[*].code")).containsOnly("passcriteria_placeholder");
        assertThat(resp.<List<String>>read("$.data.warnings[*].location")).containsExactlyInAnyOrder("project",
                "goals[0]", "goals[0].tasks[0]");
        assertThat(resp.<String>read("$.data.parsedResult.goals[0].tasks[0].passCriteria"))
                .isEqualTo("（AI 解析未提供通過標準，請於 signoff 前補齊）");
    }
}
