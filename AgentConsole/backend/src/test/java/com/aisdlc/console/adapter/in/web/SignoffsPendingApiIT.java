package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@code GET /api/v1/signoffs/pending}（API-SGN-05／US-E-07；契約 §1.8.1；D-18；E2E-16 第 3、4 列的後端面）。為什麼重要：儀表板「待人工審批」卡
 * 的徽章與清單以前是前端用專案與目標 API 另外組的近似——沒有任務、沒有匯入記錄、也沒有「已簽專案底下的草案」，所以頂列徽章的數字大於點得到的項目。
 * 這支端點與通知摘要的 {@code pendingSignoffs} 共用同一組述詞，這裡把五條不變量寫成會失敗的測試：總數相等、四個計數各自相等、limit 不影響計數、
 * 簽一筆就少一筆、不該計入的（已簽、已軟刪、非終態以外的匯入狀態）都不出現。期望值一律由<b>測試自己的獨立 SQL</b>算（不重用 {@code PendingSignoffSql}）。
 */
class SignoffsPendingApiIT extends AbstractApiIT {

    private static final String PENDING = "/api/v1/signoffs/pending";

    // ── 夾具 ────────────────────────────────────────────────────────────────

    private String draftProject(String name) {
        return createProject(Map.of("name", name, "executionPath", "/work/" + name, "passCriteria", "- ok", "draft", true));
    }

    private String draftGoal(String projectId, String name) {
        Resp resp = api.post(operator(), "/api/v1/projects/" + projectId + "/goals",
                Map.of("name", name, "passCriteria", "- ok", "draft", true));
        assertThat(resp.status()).isEqualTo(201);
        return resp.id();
    }

    private String draftTask(String goalId, String name) {
        Resp resp = api.post(operator(), "/api/v1/goals/" + goalId + "/tasks",
                Map.of("name", name, "passCriteria", "- ok", "draft", true));
        assertThat(resp.status()).isEqualTo(201);
        return resp.id();
    }

    /** 直接寫一筆匯入記錄（建立時間由測試指定，才能驗排序）；{@code fileName} 為 null＝貼上文字。 */
    private String importRecord(String status, String fileName, boolean signedOff, String createdAt) {
        UUID id = UUID.randomUUID();
        jdbc.update("insert into console.import_records (id, source_type, source_file_name, source_content, status, "
                + "signed_off, created_at) values (?, 'MARKDOWN', ?, '# 內容', ?, ?, ?::timestamptz)", id, fileName,
                status, signedOff, createdAt);
        return id.toString();
    }

    private void stamp(String table, String id, String createdAt) {
        jdbc.update("update console." + table + " set created_at = ?::timestamptz where id = ?", createdAt,
                UUID.fromString(id));
    }

    private Resp pending(String query) {
        return api.get(viewer(), PENDING + query);
    }

    private int summaryPendingSignoffs() {
        return api.get(viewer(), "/api/v1/notifications/summary").<Integer>read("$.data.pendingSignoffs");
    }

    // ── 獨立的期望值（與實作的 SQL 寫法刻意不同）──────────────────────────────────

    private int oracleProjects() {
        return jdbc.queryForObject("select count(*) from console.projects where signed_off = false "
                + "and coalesce(is_deleted, false) = false", Integer.class);
    }

    private int oracleGoals() {
        return jdbc.queryForObject("select count(*) from console.goals g where g.signed_off = false "
                + "and coalesce(g.is_deleted, false) = false and g.project_id in (select id from console.projects "
                + "where coalesce(is_deleted, false) = false)", Integer.class);
    }

    private int oracleTasks() {
        return jdbc.queryForObject("select count(*) from console.tasks t where t.signed_off = false "
                + "and coalesce(t.is_deleted, false) = false and t.goal_id in (select g.id from console.goals g "
                + "where coalesce(g.is_deleted, false) = false and g.project_id in (select id from console.projects "
                + "where coalesce(is_deleted, false) = false))", Integer.class);
    }

    private int oracleImports() {
        return jdbc.queryForObject("select count(*) from console.import_records where status in ('PARSED', 'REVIEWING') "
                + "and signed_off = false", Integer.class);
    }

    /** 一組含五種「該計入」與一大堆「不該計入」的資料（契約不變量⑤）；回傳該計入的五個 id。 */
    private Fixture fixture() {
        String project = draftProject("alpha");
        String goal = draftGoal(project, "goal-one");
        String task = draftTask(goal, "task-one");
        String parsedImport = importRecord("PARSED", "需求文件.md", false, "2026-10-15T01:00:00Z");
        String pastedImport = importRecord("REVIEWING", null, false, "2026-10-15T05:00:00Z");
        stamp("projects", project, "2026-10-15T02:00:00Z");
        stamp("goals", goal, "2026-10-15T03:00:00Z");
        stamp("tasks", task, "2026-10-15T04:00:00Z");

        // 不該計入：已簽的專案（連同它底下已簽的目標與任務）、專案已軟刪但其目標與任務未軟刪、存活專案裡單獨軟刪的目標與任務、
        // 非 PARSED／REVIEWING 的匯入記錄、已簽的 PARSED 匯入
        String signedProject = createProject("signed-one");
        String signedGoal = createGoal(signedProject, "signed-goal");
        createTask(signedGoal, "signed-task");
        String deletedProject = draftProject("deleted-project");
        String goalUnderDeleted = draftGoal(deletedProject, "goal-under-deleted-project");
        draftTask(goalUnderDeleted, "task-under-deleted-project");
        jdbc.update("update console.projects set is_deleted = true where id = ?", UUID.fromString(deletedProject));
        String deletedGoal = draftGoal(project, "deleted-goal");
        String taskUnderDeletedGoal = draftTask(deletedGoal, "task-under-deleted-goal");
        jdbc.update("update console.goals set is_deleted = true where id = ?", UUID.fromString(deletedGoal));
        String deletedTask = draftTask(goal, "deleted-task");
        jdbc.update("update console.tasks set is_deleted = true where id = ?", UUID.fromString(deletedTask));
        for (String status : List.of("UPLOADED", "PARSING", "IMPORTED", "REJECTED")) {
            importRecord(status, status + ".md", false, "2026-10-15T00:30:00Z");
        }
        importRecord("PARSED", "already-signed.md", true, "2026-10-15T00:40:00Z");
        assertThat(taskUnderDeletedGoal).isNotBlank();
        return new Fixture(project, goal, task, parsedImport, pastedImport);
    }

    private record Fixture(String project, String goal, String task, String parsedImport, String pastedImport) {
    }

    // ── 清單與欄位（E2E-16 第 3 列）────────────────────────────────────────────

    @Test
    void itListsEveryKindOfDraftOldestFirstWithTheDocumentedFields() {
        Fixture f = fixture();

        Resp resp = pending("");

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<Integer>read("$.data.counts.projects")).isEqualTo(1);
        assertThat(resp.<Integer>read("$.data.counts.goals")).isEqualTo(1);
        assertThat(resp.<Integer>read("$.data.counts.tasks")).isEqualTo(1);
        assertThat(resp.<Integer>read("$.data.counts.imports")).isEqualTo(2);
        assertThat(resp.<Integer>read("$.data.counts.total")).isEqualTo(5);
        assertThat(resp.<List<String>>read("$.data.items[*].kind"))
                .containsExactly("IMPORT", "PROJECT", "GOAL", "TASK", "IMPORT");
        assertThat(resp.<List<String>>read("$.data.items[*].id"))
                .containsExactly(f.parsedImport(), f.project(), f.goal(), f.task(), f.pastedImport());
        assertThat(resp.<List<String>>read("$.data.items[*].createdAt").stream().map(Instant::parse).toList())
                .as("created_at 升冪（UTC）").containsExactly(Instant.parse("2026-10-15T01:00:00Z"),
                        Instant.parse("2026-10-15T02:00:00Z"), Instant.parse("2026-10-15T03:00:00Z"),
                        Instant.parse("2026-10-15T04:00:00Z"), Instant.parse("2026-10-15T05:00:00Z"));

        Map<String, Object> project = resp.read("$.data.items[1]");
        assertThat(project).containsEntry("projectId", f.project()).containsEntry("projectName", "alpha")
                .containsEntry("parentId", null).containsEntry("title", "alpha");
        Map<String, Object> goal = resp.read("$.data.items[2]");
        assertThat(goal).containsEntry("projectId", f.project()).containsEntry("projectName", "alpha")
                .containsEntry("parentId", f.project()).containsEntry("title", "goal-one");
        Map<String, Object> task = resp.read("$.data.items[3]");
        assertThat(task).containsEntry("projectId", f.project()).containsEntry("projectName", "alpha")
                .containsEntry("parentId", f.goal()).containsEntry("title", "task-one");
        Map<String, Object> file = resp.read("$.data.items[0]");
        assertThat(file).as("IMPORT 項沒有專案：三個欄位為 null").containsEntry("projectId", null)
                .containsEntry("projectName", null).containsEntry("parentId", null).containsEntry("title", "需求文件.md");
        Map<String, Object> pasted = resp.read("$.data.items[4]");
        assertThat(pasted).containsEntry("title", "貼上文字").containsEntry("projectId", null);
    }

    @Test
    void nothingThatIsSignedDeletedOrNotYetReviewableShowsUp() {
        Fixture f = fixture();

        Resp resp = pending("");

        List<String> titles = resp.read("$.data.items[*].title");
        assertThat(titles).as("已簽、已軟刪（含專案已軟刪而其目標任務未軟刪）、其他匯入狀態、已簽的 PARSED 都不出現")
                .containsExactlyInAnyOrder("需求文件.md", "alpha", "goal-one", "task-one", "貼上文字");
        assertThat(f.project()).isNotBlank();
    }

    @Test
    void anEmptySystemHasZeroCountsAndNoItems() {
        Resp resp = pending("");

        assertThat(resp.<Integer>read("$.data.counts.total")).isZero();
        assertThat(resp.<List<Object>>read("$.data.items")).isEmpty();
        assertThat(summaryPendingSignoffs()).isZero();
    }

    // ── 不變量（契約 §1.8.1）────────────────────────────────────────────────────

    @Test
    void totalEqualsTheSummaryAndEachCountEqualsItsOwnPredicate() {
        for (int step = 0; step < 3; step++) {
            if (step == 1) {
                fixture();
            }
            if (step == 2) {
                jdbc.update("update console.import_records set signed_off = true where status = 'REVIEWING'");
            }
            Resp resp = pending("");

            assertThat(resp.<Integer>read("$.data.counts.total")).as("step " + step).isEqualTo(summaryPendingSignoffs());
            assertThat(resp.<Integer>read("$.data.counts.projects")).as("step " + step).isEqualTo(oracleProjects());
            assertThat(resp.<Integer>read("$.data.counts.goals")).as("step " + step).isEqualTo(oracleGoals());
            assertThat(resp.<Integer>read("$.data.counts.tasks")).as("step " + step).isEqualTo(oracleTasks());
            assertThat(resp.<Integer>read("$.data.counts.imports")).as("step " + step).isEqualTo(oracleImports());
        }
    }

    @Test
    void limitOnlyTruncatesTheItemsToTheOldestOnesAndNeverTheCounts() {
        Fixture f = fixture();

        Resp two = pending("?limit=2");

        assertThat(two.status()).isEqualTo(200);
        assertThat(two.<List<String>>read("$.data.items[*].id")).containsExactly(f.parsedImport(), f.project());
        assertThat(two.<Integer>read("$.data.counts.total")).as("limit 不影響 counts").isEqualTo(5);
        assertThat(pending("?limit=1").<List<String>>read("$.data.items[*].id")).containsExactly(f.parsedImport());
        assertThat(pending("?limit=200").<List<Object>>read("$.data.items")).hasSize(5);
        assertThat(pending("").<List<Object>>read("$.data.items")).as("預設 50").hasSize(5);
    }

    @Test
    void theDefaultLimitIsFiftyAndTheCountsStillSayHowManyThereAre() {
        for (int i = 0; i < 55; i++) {
            importRecord("PARSED", "bulk-" + i + ".md", false, "2026-10-15T00:00:00Z");
        }

        Resp resp = pending("");

        assertThat(resp.<List<Object>>read("$.data.items")).hasSize(50);
        assertThat(resp.<Integer>read("$.data.counts.imports")).isEqualTo(55);
        assertThat(resp.<Integer>read("$.data.counts.total")).isEqualTo(55).isEqualTo(summaryPendingSignoffs());
        assertThat(pending("?limit=200").<List<Object>>read("$.data.items")).hasSize(55);
    }

    @Test
    void itemsWithTheSameCreationTimeAreOrderedByIdSoThePageIsDeterministic() {
        for (int i = 0; i < 6; i++) {
            importRecord("PARSED", "same-" + i + ".md", false, "2026-10-15T00:00:00Z");
        }

        List<String> ids = pending("").read("$.data.items[*].id");

        assertThat(ids).hasSize(6).isSorted();
        assertThat(pending("?limit=3").<List<String>>read("$.data.items[*].id")).isEqualTo(ids.subList(0, 3));
    }

    @Test
    void signingOneOffAnyKindRemovesExactlyThatItemAndLowersTheTotalByOne() {
        Fixture f = fixture();
        assertThat(pending("").<Integer>read("$.data.counts.total")).isEqualTo(5);

        assertThat(api.post(operator(), "/api/v1/tasks/" + f.task() + "/signoff", Map.of("approver", "alice")).status())
                .isEqualTo(200);
        Resp afterTask = pending("");
        assertThat(afterTask.<Integer>read("$.data.counts.total")).isEqualTo(4);
        assertThat(afterTask.<Integer>read("$.data.counts.tasks")).isZero();
        assertThat(afterTask.<List<String>>read("$.data.items[*].id")).doesNotContain(f.task());

        assertThat(api.post(operator(), "/api/v1/goals/" + f.goal() + "/signoff", Map.of("approver", "alice")).status())
                .isEqualTo(200);
        assertThat(api.post(operator(), "/api/v1/projects/" + f.project() + "/signoff", Map.of("approver", "alice"))
                .status()).isEqualTo(200);
        jdbc.update("update console.import_records set signed_off = true where id = ?", UUID.fromString(f.parsedImport()));

        Resp end = pending("");
        assertThat(end.<Integer>read("$.data.counts.total")).isEqualTo(1);
        assertThat(end.<List<String>>read("$.data.items[*].id")).containsExactly(f.pastedImport());
        assertThat(summaryPendingSignoffs()).isEqualTo(1);
    }

    @Test
    void aGoalOrTaskOfASignedProjectIsStillPendingBecauseTheJudgementIsPerRow() {
        String project = createProject("signed-parent");
        String goal = draftGoal(project, "draft-goal-of-a-signed-project");
        draftTask(goal, "draft-task-of-a-signed-project");

        Resp resp = pending("");

        assertThat(resp.<Integer>read("$.data.counts.projects")).as("專案已簽：不計").isZero();
        assertThat(resp.<List<String>>read("$.data.items[*].kind")).as("但它底下的草案要出現（舊的前端清單漏列這種）")
                .containsExactly("GOAL", "TASK");
        assertThat(resp.<List<String>>read("$.data.items[*].projectName")).containsOnly("signed-parent");
    }

    // ── 驗證與權限（E2E-16 第 4 列）──────────────────────────────────────────────

    @Test
    void aLimitThatIsNotAnIntegerOrOutsideOneToTwoHundredIs400WithTheLimitField() {
        for (String query : List.of("?limit=0", "?limit=201", "?limit=-1", "?limit=abc", "?limit=1.5")) {
            Resp resp = pending(query);

            assertThat(resp.status()).as(query).isEqualTo(400);
            assertThat(resp.errorFields()).as(query).containsExactly("limit");
        }
    }

    @Test
    void everyRoleMayReadAndAnAnonymousCallerIs401() {
        for (String token : List.of(viewer(), operator(), admin())) {
            assertThat(api.get(token, PENDING).status()).isEqualTo(200);
        }
        assertThat(api.get(null, PENDING).status()).isEqualTo(401);
        assertThat(api.post(operator(), PENDING, new LinkedHashMap<String, Object>()).status())
                .as("只讀端點，沒有寫入方法").isEqualTo(405);
    }
}
