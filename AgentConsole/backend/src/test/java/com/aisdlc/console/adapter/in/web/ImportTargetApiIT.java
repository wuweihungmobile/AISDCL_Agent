package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractOutboundIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.FakeHttpServer.Received;
import com.aisdlc.console.support.FakeHttpServer.Response;
import com.aisdlc.console.support.ImportFixtures;
import com.aisdlc.console.support.OutboundFakes;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 路徑 A 匯入併入既有專案與綁定回填（契約 §1.10.8、§3.3.2 v1.5 補充、§0.5 V12；API-IMP-12）。為什麼重要：這是「先凍結、後匯入」循環依賴的解法——
 * Console 專案是錨，匯入的目標與任務必須接在既有目標之後、而且<b>不得動到專案本身</b>（專案層簽核、名稱、說明）；綁定（規格目錄、規格檔、
 * FSM 專案鍵）只在 confirm 成功落庫時才回填，放棄的草稿不該產生綁定；parse 與 confirm 各驗一次，因為兩次之間綁定可能被改掉。
 */
class ImportTargetApiIT extends AbstractOutboundIT {

    private static final String IMPORT = "/api/v1/import";
    private static final String ROOT = "/work/proj-merge";
    private static final String SPEC_DIR = ROOT + "/spec";
    private static final String SPEC_FILE = SPEC_DIR + "/cart.md";
    private static final String KEY = "cart-key";
    private static final String APPROVER = "e2e-approver";
    private static final String CONFLICT = "sdd_binding_conflict";

    // ── 夾具 ─────────────────────────────────────────────────────────────────

    private static Map<String, Object> compileExtras(String specPath, String fsmProject) {
        Map<String, Object> extras = new LinkedHashMap<>();
        extras.put("spec_path", specPath);
        extras.put("spec_file", "cart.md");
        extras.put("fsm_project", fsmProject);
        extras.put("spec_format_version", "1.2");
        extras.put("frozen_digest", "verified");
        return extras;
    }

    private static void bridgeCompiles(int contracts) {
        bridgeCompiles(contracts, compileExtras(SPEC_FILE, KEY));
    }

    private static void bridgeCompiles(int contracts, Map<String, Object> extras) {
        OutboundFakes.BRIDGE.on("POST", "/sdd/compile",
                Response.json(200, ImportFixtures.sddCompileResponse("購物車", contracts, extras)));
    }

    private String createText() {
        Resp created = api.post(operator(), IMPORT + "/text", Map.of("content", "# 一份文件\n內容", "sourceType", "MARKDOWN"));
        assertThat(created.status()).isEqualTo(201);
        return created.id();
    }

    /** 以 API 建專案（預設已 signoff），再直接把 SDD 綁定三欄寫進資料庫（Console 沒有「建立時帶綁定」的請求欄位）。 */
    private String projectBoundTo(String name, String path, String sddProject, String specDir, String specFile) {
        String id = createProject(Map.of("name", name, "executionPath", path, "passCriteria", "- 全部通過"));
        bind(id, sddProject, specDir, specFile);
        return id;
    }

    private void bind(String projectId, String sddProject, String specDir, String specFile) {
        jdbc.update("update console.projects set sdd_project = ?, sdd_spec_dir = ?, sdd_spec_file = ? where id = ?",
                sddProject, specDir, specFile, UUID.fromString(projectId));
    }

    private Map<String, Object> binding(String projectId) {
        return jdbc.queryForMap("select sdd_project, sdd_spec_dir, sdd_spec_file from console.projects where id = ?",
                UUID.fromString(projectId));
    }

    private static Map<String, Object> options(String specDir, String target) {
        Map<String, Object> options = new LinkedHashMap<>();
        options.put("executionPath", ROOT);
        options.put("autonomyLevel", 3);
        if (specDir != null) {
            options.put("specDir", specDir);
        }
        if (target != null) {
            options.put("targetProjectId", target);
        }
        return options;
    }

    private Resp parse(String id, Map<String, Object> options) {
        return api.post(operator(), IMPORT + "/" + id + "/parse", options);
    }

    private Resp signoff(String id) {
        return api.post(operator(), IMPORT + "/" + id + "/signoff", Map.of("approver", APPROVER));
    }

    private Resp confirm(String id) {
        return api.post(operator(), IMPORT + "/" + id + "/confirm");
    }

    /** parse（帶目標）＋ signoff，回記錄 id。 */
    private String parsedAndSignedOff(String target) {
        String id = createText();
        assertThat(parse(id, options(SPEC_DIR, target)).status()).isEqualTo(200);
        assertThat(signoff(id).status()).isEqualTo(200);
        return id;
    }

    private static String bodyField(Received received, String path) {
        return JsonPath.read(received.body(), path);
    }

    private int countOf(String table, String projectId) {
        String where = table.equals("goals") ? "project_id = ?" : "goal_id in (select id from console.goals where project_id = ?)";
        return jdbc.queryForObject("select count(*) from console." + table + " where " + where, Integer.class,
                UUID.fromString(projectId));
    }

    // ── parse：目標專案的解析與衝突 ──────────────────────────────────────────────

    @Test
    void anUnknownTargetIs404AndTheRecordIsLeftUntouched() {
        bridgeCompiles(1);
        String id = createText();
        String unknown = UUID.randomUUID().toString();

        Resp resp = parse(id, options(SPEC_DIR, unknown));

        assertThat(resp.status()).isEqualTo(404);
        assertThat(resp.<String>read("$.message")).isEqualTo("專案不存在或已刪除：" + unknown);
        assertThat(resp.has("$.reason")).as("一般 404 沒有 reason").isFalse();
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<String>read("$.data.status")).as("404 發生在進入 PARSING 之前").isEqualTo("UPLOADED");
        assertThat(record.<Object>read("$.data.parseOptions")).isNull();
        assertThat(OutboundFakes.BRIDGE.receivedAt("/sdd/compile")).isEmpty();
    }

    @Test
    void aSoftDeletedTargetIs404Too() {
        bridgeCompiles(1);
        String target = createProject("gone");
        assertThat(api.delete(operator(), "/api/v1/projects/" + target).status()).isEqualTo(204);

        Resp resp = parse(createText(), options(SPEC_DIR, target));

        assertThat(resp.status()).isEqualTo(404);
        assertThat(resp.<String>read("$.message")).isEqualTo("專案不存在或已刪除：" + target);
    }

    @Test
    void eachRequestFieldThatDiffersFromTheTargetIs409NamingTheField() {
        bridgeCompiles(1);
        String target = projectBoundTo("anchor", ROOT, KEY, SPEC_DIR, SPEC_FILE);
        Map<String, Map<String, Object>> overrides = new LinkedHashMap<>();
        overrides.put("executionPath", Map.of("executionPath", "/work/somewhere-else"));
        overrides.put("sddProject", Map.of("sddProject", "other-key"));
        overrides.put("specDir", Map.of("specDir", "/work/proj-merge/other-spec"));
        overrides.put("specFile", Map.of("specFile", "other.md"));
        for (Map.Entry<String, Map<String, Object>> row : overrides.entrySet()) {
            String id = createText();
            Map<String, Object> options = options(null, target);
            options.putAll(row.getValue());

            Resp resp = parse(id, options);

            assertThat(resp.status()).as(row.getKey()).isEqualTo(409);
            assertThat(resp.<String>read("$.reason")).as(row.getKey()).isEqualTo(CONFLICT);
            assertThat(resp.<String>read("$.details.cause")).isEqualTo("request_differs_from_target");
            assertThat(resp.<String>read("$.details.field")).isEqualTo(row.getKey());
            assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.status")).isEqualTo("UPLOADED");
        }
        assertThat(OutboundFakes.BRIDGE.receivedAt("/sdd/compile")).as("衝突發生在呼叫 Bridge 之前").isEmpty();
    }

    @Test
    void aRequestEqualToTheTargetsBindingIsNotAConflictEvenInAnotherSpelling() {
        bridgeCompiles(1);
        String target = projectBoundTo("anchor", ROOT, KEY, SPEC_DIR, SPEC_FILE);
        Map<String, Object> options = options(SPEC_DIR + "/", target);
        options.put("sddProject", KEY);
        options.put("specFile", "./cart.md");

        assertThat(parse(createText(), options).status()).as("尾端斜線與 ./ 前綴不算不同").isEqualTo(200);
    }

    @Test
    void aTargetWithNothingBoundTakesTheRequestValuesAndItsNameAsTheProject() {
        bridgeCompiles(1);
        String target = createProject(Map.of("name", "Fresh Anchor", "executionPath", ROOT, "passCriteria", "- 通過"));
        String id = createText();

        Resp resp = parse(id, options(SPEC_DIR, target));

        assertThat(resp.status()).isEqualTo(200);
        Received compile = OutboundFakes.BRIDGE.receivedAt("/sdd/compile").get(0);
        assertThat(bodyField(compile, "$.spec_dir")).isEqualTo(SPEC_DIR);
        assertThat(bodyField(compile, "$.fsm_project")).as("沒有 sddProject：取專案名，原樣（Backend 不淨化）")
                .isEqualTo("Fresh Anchor");
        assertThat(compile.body()).as("沒有指定規格檔就不送 spec_file").doesNotContain("spec_file");
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<String>read("$.data.parseOptions.targetProjectId")).isEqualTo(target);
        assertThat(record.<String>read("$.data.parseOptions.sddProject")).isEqualTo("Fresh Anchor");
    }

    @Test
    void aBoundTargetSuppliesItsOwnBindingToTheCompileWhenTheRequestOmitsIt() {
        bridgeCompiles(1);
        String target = projectBoundTo("anchor", ROOT, KEY, SPEC_DIR, SPEC_FILE);

        Resp resp = parse(createText(), options(null, target));

        assertThat(resp.status()).isEqualTo(200);
        Received compile = OutboundFakes.BRIDGE.receivedAt("/sdd/compile").get(0);
        assertThat(bodyField(compile, "$.spec_dir")).isEqualTo(SPEC_DIR);
        assertThat(bodyField(compile, "$.spec_file")).isEqualTo(SPEC_FILE);
        assertThat(bodyField(compile, "$.fsm_project")).isEqualTo(KEY);
    }

    @Test
    void aSpecFileWithoutASpecDirIs400OnSpecFile() {
        bridgeCompiles(1);
        String id = createText();
        Map<String, Object> options = options(null, null);
        options.put("specFile", "cart.md");

        Resp resp = parse(id, options);

        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.errorFields()).containsExactly("specFile");
        assertThat(OutboundFakes.BRIDGE.receivedAt("/sdd/compile")).isEmpty();
        assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.status")).isEqualTo("UPLOADED");
    }

    @Test
    void theCompileCarriesTheSpecFileAndProjectOfTheRequestWithoutATarget() {
        bridgeCompiles(1);
        Map<String, Object> options = options(SPEC_DIR, null);
        options.put("specFile", "cart.md");
        options.put("sddProject", "  My Project 專案  ");

        Resp resp = parse(createText(), options);

        assertThat(resp.status()).isEqualTo(200);
        Received compile = OutboundFakes.BRIDGE.receivedAt("/sdd/compile").get(0);
        assertThat(bodyField(compile, "$.spec_file")).isEqualTo("cart.md");
        assertThat(bodyField(compile, "$.fsm_project")).as("去前後空白、其餘原樣").isEqualTo("My Project 專案");
    }

    @Test
    void theRequestValidatesTheNewOptionFieldsBeforeAnythingIsCalled() {
        bridgeCompiles(1);
        String id = createText();
        for (Map<String, Object> bad : List.<Map<String, Object>>of(Map.of("sddProject", "x".repeat(201)),
                Map.of("sddProject", "a\nb"), Map.of("sddProject", ""), Map.of("specFile", "y".repeat(501)),
                Map.of("targetProjectId", "not-a-uuid"))) {
            Map<String, Object> options = options(SPEC_DIR, null);
            options.putAll(bad);

            Resp resp = parse(id, options);

            assertThat(resp.status()).as(bad.toString()).isEqualTo(400);
            assertThat(resp.errorFields()).containsExactly(bad.keySet().iterator().next());
        }
        assertThat(OutboundFakes.BRIDGE.receivedAt("/sdd/compile")).isEmpty();
    }

    @Test
    void theParseResponseCarriesTheServerOwnedFieldsAndTheSpecLevelWarnings() {
        Map<String, Object> extras = compileExtras(SPEC_FILE, KEY);
        extras.put("frozen_digest", "absent");
        extras.put("unmapped_at_ids", List.of("AT-9"));
        extras.put("warnings", List.of(Map.of("code", "state_dir_not_ignored", "detail", "build/reports/fsm 未被 git 忽略")));
        bridgeCompiles(2, extras);

        Resp resp = parse(createText(), options(SPEC_DIR, null));

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.parsedResult.specFormatVersion")).isEqualTo("1.2");
        assertThat(resp.<String>read("$.data.parsedResult.sddProject")).isEqualTo(KEY);
        assertThat(resp.<String>read("$.data.parsedResult.sddSpecDir")).isEqualTo(SPEC_DIR);
        assertThat(resp.<String>read("$.data.parsedResult.sddSpecFile")).isEqualTo(SPEC_FILE);
        assertThat(resp.<List<String>>read("$.data.warnings[*].code")).containsExactly("at_unmapped",
                "frozen_digest_absent", "state_dir_not_ignored");
        assertThat(resp.<List<String>>read("$.data.warnings[*].location")).containsExactly("specDir", "specDir",
                "executionPath");
    }

    // ── PUT result：伺服器擁有的欄位與規格層級提示 ────────────────────────────────

    @Test
    void editingIgnoresTheServerFieldsAndKeepsOnlyTheSpecLevelWarnings() {
        Map<String, Object> extras = compileExtras(SPEC_FILE, KEY);
        extras.put("unmapped_at_ids", List.of("AT-9"));
        bridgeCompiles(2, extras);
        String id = createText();
        Resp parsed = parse(id, options(SPEC_DIR, null));
        Map<String, Object> tree = parsed.read("$.data.parsedResult");
        tree.put("sddProject", "hacked");
        tree.put("sddSpecDir", "/hacked");
        tree.put("sddSpecFile", "/hacked/x.md");
        tree.put("specFormatVersion", "9.9");

        Resp edited = api.put(operator(), IMPORT + "/" + id + "/result", Map.of("parsedResult", tree));

        assertThat(edited.status()).isEqualTo(200);
        assertThat(edited.<List<String>>read("$.data.warnings[*].code")).as("at_unmapped 說的是規格本身，編輯後仍成立")
                .containsExactly("at_unmapped");
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<String>read("$.data.parsedResult.sddProject")).isEqualTo(KEY);
        assertThat(record.<String>read("$.data.parsedResult.sddSpecDir")).isEqualTo(SPEC_DIR);
        assertThat(record.<String>read("$.data.parsedResult.sddSpecFile")).isEqualTo(SPEC_FILE);
        assertThat(record.<String>read("$.data.parsedResult.specFormatVersion")).isEqualTo("1.2");
        assertThat(record.<List<String>>read("$.data.warnings[*].code")).containsExactly("at_unmapped");
    }

    // ── confirm：併入既有專案 ─────────────────────────────────────────────────────

    @Test
    void aMergeAppendsGoalsAfterTheExistingOnesAndChainsOnlyTheNewOnes() {
        bridgeCompiles(30);
        String target = createProject(Map.of("name", "anchor", "executionPath", ROOT, "passCriteria", "- 通過"));
        String existingFirst = createGoal(target, "既有目標一");
        createGoal(target, "既有目標二", existingFirst);
        createTask(existingFirst, "既有任務");
        String id = parsedAndSignedOff(target);

        Resp confirmed = confirm(id);

        assertThat(confirmed.status()).as("成功仍回 201").isEqualTo(201);
        assertThat(confirmed.id()).as("回傳的是目標專案，不是新專案").isEqualTo(target);
        assertThat(confirmed.<Integer>read("$.data.goalsCount")).as("既有 2＋新 2").isEqualTo(4);
        assertThat(confirmed.<Integer>read("$.data.tasksCount")).as("既有 1＋新 30").isEqualTo(31);
        assertThat(jdbc.queryForObject("select count(*) from console.projects", Integer.class)).isEqualTo(1);
        List<Map<String, Object>> goals = jdbc.queryForList(
                "select name, sort_order from console.goals where project_id = ? order by sort_order",
                UUID.fromString(target));
        assertThat(goals).extracting(g -> g.get("name")).containsExactly("既有目標一", "既有目標二", "購物車（第 1 批）",
                "購物車（第 2 批）");
        assertThat(goals).extracting(g -> g.get("sort_order")).as("既有最大 sortOrder(1)＋1＋草稿內的序")
                .containsExactly(0, 1, 2, 3);
        assertThat(jdbc.queryForObject("select count(*) from console.goal_dependencies", Integer.class))
                .as("既有的一條＋草稿內的一條；不會指向既有目標").isEqualTo(2);
        assertThat(jdbc.queryForObject("select count(*) from console.goal_dependencies d join console.goals g "
                + "on g.id = d.goal_id join console.goals p on p.id = d.depends_on_goal_id "
                + "where g.name like '購物車%' and p.name not like '購物車%'", Integer.class)).isZero();
        Resp record = api.get(viewer(), IMPORT + "/" + id);
        assertThat(record.<String>read("$.data.status")).isEqualTo("IMPORTED");
        assertThat(record.<String>read("$.data.projectId")).isEqualTo(target);
        assertThat(jdbc.queryForObject("select count(*) from console.goals where project_id = ? and name like '購物車%' "
                + "and (signed_off = false or signed_off_by is distinct from ?)", Integer.class,
                UUID.fromString(target), APPROVER)).as("新建的目標承襲匯入記錄的簽核").isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.tasks t join console.goals g on g.id = t.goal_id "
                + "where g.project_id = ? and g.name like '購物車%' "
                + "and (t.signed_off = false or t.signed_off_by is distinct from ?)", Integer.class,
                UUID.fromString(target), APPROVER)).as("新建的任務同樣承襲").isZero();
    }

    @Test
    void aMergeWorksWhenTheTargetHasNoGoalsYetStartingFromZero() {
        bridgeCompiles(2);
        String target = createProject(Map.of("name", "empty-anchor", "executionPath", ROOT, "passCriteria", "- 通過"));

        assertThat(confirm(parsedAndSignedOff(target)).status()).isEqualTo(201);

        assertThat(jdbc.queryForObject("select min(sort_order) from console.goals where project_id = ?", Integer.class,
                UUID.fromString(target))).isZero();
    }

    @Test
    void aMergeLeavesTheProjectFieldsAndProjectLevelSignoffUntouched() {
        bridgeCompiles(2);
        String target = createProject(Map.of("name", "anchor", "executionPath", ROOT, "passCriteria", "- 原本的通過標準",
                "description", "原本的說明", "autonomyLevel", 7));
        jdbc.update("update console.projects set signed_off = false, signed_off_by = null, signed_off_at = null "
                + "where id = ?", UUID.fromString(target));
        Map<String, Object> before = jdbc.queryForMap("select name, execution_path, pass_criteria, description, "
                + "autonomy_level, status, signed_off, signed_off_by, signed_off_at, updated_at "
                + "from console.projects where id = ?", UUID.fromString(target));

        assertThat(confirm(parsedAndSignedOff(target)).status()).isEqualTo(201);

        Map<String, Object> after = jdbc.queryForMap("select name, execution_path, pass_criteria, description, "
                + "autonomy_level, status, signed_off, signed_off_by, signed_off_at, updated_at "
                + "from console.projects where id = ?", UUID.fromString(target));
        Map<String, Object> withoutTimestamp = new LinkedHashMap<>(after);
        withoutTimestamp.remove("updated_at");
        Map<String, Object> beforeWithoutTimestamp = new LinkedHashMap<>(before);
        beforeWithoutTimestamp.remove("updated_at");
        assertThat(withoutTimestamp).as("專案本身的欄位與專案層 signedOff 一律不動（只有綁定欄會被寫）")
                .isEqualTo(beforeWithoutTimestamp);
        assertThat(after.get("signed_off")).isEqualTo(false);
    }

    @Test
    void aMergeWritesBackTheBindingAndARepeatedMergeKeepsItUnchanged() {
        bridgeCompiles(1);
        String target = createProject(Map.of("name", "anchor", "executionPath", ROOT, "passCriteria", "- 通過"));
        assertThat(binding(target).values()).containsOnlyNulls();

        assertThat(confirm(parsedAndSignedOff(target)).status()).isEqualTo(201);

        Map<String, Object> bound = binding(target);
        assertThat(bound.get("sdd_project")).as("為 NULL 時寫入標準鍵").isEqualTo(KEY);
        assertThat(bound.get("sdd_spec_dir")).isEqualTo(SPEC_DIR);
        assertThat(bound.get("sdd_spec_file")).isEqualTo(SPEC_FILE);

        assertThat(confirm(parsedAndSignedOff(target)).status()).as("同一份規格再併入一次：冪等更新、不衝突")
                .isEqualTo(201);
        assertThat(binding(target)).isEqualTo(bound);
        assertThat(countOf("goals", target)).isEqualTo(2);
    }

    @Test
    void aBindingTheTargetAlreadyHasIsKeptEvenWhenItIsTheRawName() {
        bridgeCompiles(1, compileExtras(SPEC_FILE, "My_Proj"));
        String target = projectBoundTo("anchor", ROOT, "My Proj", null, null);
        String id = createText();
        assertThat(parse(id, options(SPEC_DIR, target)).status()).isEqualTo(200);
        assertThat(signoff(id).status()).isEqualTo(200);

        assertThat(confirm(id).status()).as("使用者輸入的原名與它的標準鍵是同一個綁定").isEqualTo(201);

        assertThat(binding(target).get("sdd_project")).as("不覆寫使用者輸入的值").isEqualTo("My Proj");
        assertThat(binding(target).get("sdd_spec_file")).isEqualTo(SPEC_FILE);
    }

    @Test
    void aBindingChangedBetweenParseAndConfirmIs409TargetBoundDifferently() {
        bridgeCompiles(1);
        String target = projectBoundTo("anchor", ROOT, KEY, null, null);
        String id = parsedAndSignedOff(target);
        bind(target, "somebody-elses-key", null, null);

        Resp resp = confirm(id);

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(CONFLICT);
        assertThat(resp.<String>read("$.details.cause")).isEqualTo("target_bound_differently");
        assertThat(resp.<String>read("$.details.sddProject")).isEqualTo("somebody-elses-key");
        assertThat(countOf("goals", target)).as("整個 confirm 回滾：沒有新目標").isZero();
        assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.status")).as("記錄仍可 confirm")
                .isEqualTo("PARSED");
    }

    @Test
    void aSpecRootOutsideTheTargetsExecutionPathIs409TargetBoundDifferently() {
        bridgeCompiles(1, compileExtras("/other/place/cart.md", KEY));
        String target = createProject(Map.of("name", "anchor", "executionPath", ROOT, "passCriteria", "- 通過"));
        String id = createText();
        assertThat(parse(id, options("/other/place", target)).status()).as("parse 只驗請求與目標一致").isEqualTo(200);
        assertThat(signoff(id).status()).isEqualTo(200);

        Resp resp = confirm(id);

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(CONFLICT);
        assertThat(resp.<String>read("$.details.cause")).isEqualTo("target_bound_differently");
        assertThat(binding(target).values()).as("不回填").containsOnlyNulls();
    }

    @Test
    void aTargetDeletedBetweenParseAndConfirmIs404AndNothingIsCreated() {
        bridgeCompiles(1);
        String target = createProject(Map.of("name", "anchor", "executionPath", ROOT, "passCriteria", "- 通過"));
        String id = parsedAndSignedOff(target);
        assertThat(api.delete(operator(), "/api/v1/projects/" + target).status()).isEqualTo(204);

        Resp resp = confirm(id);

        assertThat(resp.status()).isEqualTo(404);
        assertThat(resp.<String>read("$.message")).isEqualTo("專案不存在或已刪除：" + target);
        assertThat(jdbc.queryForObject("select count(*) from console.projects where is_deleted is not true",
                Integer.class)).isZero();
        assertThat(api.get(viewer(), IMPORT + "/" + id).<String>read("$.data.status")).isEqualTo("PARSED");
    }

    @Test
    void aMergeWhoseKeyIsHeldByAnotherProjectIs409AlreadyBoundElsewhere() {
        bridgeCompiles(1);
        String holder = projectBoundTo("holder", ROOT, KEY, null, null);
        String target = createProject(Map.of("name", "anchor", "executionPath", ROOT, "passCriteria", "- 通過"));
        String id = parsedAndSignedOff(target);

        Resp resp = confirm(id);

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(CONFLICT);
        assertThat(resp.<String>read("$.details.cause")).isEqualTo("already_bound_elsewhere");
        assertThat(resp.<String>read("$.details.sddProject")).isEqualTo(KEY);
        assertThat(resp.<String>read("$.details.holderProjectId")).isEqualTo(holder);
        assertThat(binding(target).values()).containsOnlyNulls();
        assertThat(countOf("goals", target)).isZero();
    }

    // ── confirm：不帶目標（建立新專案）也回填綁定 ──────────────────────────────────

    @Test
    void aNewProjectCarriesTheBindingFromTheCompileResponse() {
        bridgeCompiles(2);
        String id = createText();
        assertThat(parse(id, options(SPEC_DIR, null)).status()).isEqualTo(200);
        assertThat(signoff(id).status()).isEqualTo(200);

        Resp confirmed = confirm(id);

        assertThat(confirmed.status()).isEqualTo(201);
        Map<String, Object> bound = binding(confirmed.id());
        assertThat(bound.get("sdd_project")).isEqualTo(KEY);
        assertThat(bound.get("sdd_spec_dir")).isEqualTo(SPEC_DIR);
        assertThat(bound.get("sdd_spec_file")).isEqualTo(SPEC_FILE);
        Resp detail = api.get(viewer(), "/api/v1/projects/" + confirmed.id());
        assertThat(detail.<String>read("$.data.sddProject")).isEqualTo(KEY);
        assertThat(detail.<String>read("$.data.sddSpecDir")).isEqualTo(SPEC_DIR);
        assertThat(detail.<String>read("$.data.sddSpecFile")).isEqualTo(SPEC_FILE);
    }

    @Test
    void aSecondProjectWithTheSameKeyUnderTheSameRootIs409() {
        bridgeCompiles(1);
        String firstRecord = createText();
        assertThat(parse(firstRecord, options(SPEC_DIR, null)).status()).isEqualTo(200);
        assertThat(signoff(firstRecord).status()).isEqualTo(200);
        String holder = confirm(firstRecord).id();
        String secondRecord = createText();
        assertThat(parse(secondRecord, options(SPEC_DIR, null)).status()).isEqualTo(200);
        assertThat(signoff(secondRecord).status()).isEqualTo(200);

        Resp resp = confirm(secondRecord);

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(CONFLICT);
        assertThat(resp.<String>read("$.details.cause")).isEqualTo("already_bound_elsewhere");
        assertThat(resp.<String>read("$.details.holderProjectId")).isEqualTo(holder);
        assertThat(jdbc.queryForObject("select count(*) from console.projects", Integer.class))
                .as("第二個專案沒有建立").isEqualTo(1);
        assertThat(api.get(viewer(), IMPORT + "/" + secondRecord).<String>read("$.data.status")).isEqualTo("PARSED");
    }

    @Test
    void theSameKeyUnderAnotherRootIsAllowed() {
        bridgeCompiles(1);
        String first = createText();
        assertThat(parse(first, options(SPEC_DIR, null)).status()).isEqualTo(200);
        assertThat(signoff(first).status()).isEqualTo(200);
        assertThat(confirm(first).status()).isEqualTo(201);

        String second = createText();
        Map<String, Object> other = options("/work/proj-other/spec", null);
        other.put("executionPath", "/work/proj-other");
        bridgeCompiles(1, compileExtras("/work/proj-other/spec/cart.md", KEY));
        assertThat(parse(second, other).status()).isEqualTo(200);
        assertThat(signoff(second).status()).isEqualTo(200);

        assertThat(confirm(second).status()).as("唯一性是 (executionPath, sddProject)").isEqualTo(201);
    }

    @Test
    void aDraftFromANonSpecPathBindsNothing() {
        configureFakeModel();
        OutboundFakes.LLM.on("POST", OutboundFakes.CHAT_PATH,
                Response.json(200, ImportFixtures.chatCompletion(ImportFixtures.okTree())));
        OutboundFakes.BRIDGE.on("POST", "/sdd/compile", Response.json(422,
                ImportFixtures.bridgeError(422, "spec_not_found", null, "沒有規格")));
        String id = api.post(operator(), IMPORT + "/text", Map.of("content", ImportFixtures.markdownDocument(null),
                "sourceType", "MARKDOWN")).id();
        assertThat(parse(id, options(null, null)).<String>read("$.data.path")).isEqualTo("LLM");
        assertThat(signoff(id).status()).isEqualTo(200);

        Resp confirmed = confirm(id);

        assertThat(confirmed.status()).isEqualTo(201);
        assertThat(binding(confirmed.id()).values()).containsOnlyNulls();
    }
}
