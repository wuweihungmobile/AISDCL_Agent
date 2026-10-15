package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 軟刪除專案的復原與「已刪除」清單（C-3；契約 §1.6、E2E-13 第 2～3 列；NFR-9.3-04「所有刪除操作皆為軟刪除，支援 30 天內復原」）。
 * 為什麼重要：軟刪除如果只能「看起來刪了」而不能真的回來，它就只是比較慢的刪除；而「回來」要回得精準——專案回到刪除前的狀態、
 * 同一次刪除連帶軟刪的目標與任務一併回來，但使用者<b>先前就單獨刪掉</b>的目標不能因為專案復原而死灰復燃。
 */
class ProjectRestoreApiIT extends AbstractApiIT {

    private static final String PROJECTS = "/api/v1/projects";

    private Resp delete(String projectId) {
        return api.delete(operator(), PROJECTS + "/" + projectId);
    }

    private Resp restore(String token, String projectId) {
        return api.post(token, PROJECTS + "/" + projectId + "/restore");
    }

    private Map<String, Object> row(String table, String id) {
        return jdbc.queryForMap("select is_deleted, deleted_at, updated_at from console." + table + " where id = ?",
                UUID.fromString(id));
    }

    // ── 刪除時的記錄 ──────────────────────────────────────────────────────────────────

    @Test
    void deletingAProjectWritesTheSameDeletionTimeOnItAndOnEveryGoalAndTaskItTookAlongAndRemembersItsStatus() {
        String project = createProject("del-marks");
        String goal = createGoal(project, "G");
        String task = createTask(goal, "T");
        setProjectStatus(project, "COMPLETED");

        assertThat(delete(project).status()).isEqualTo(204);

        Map<String, Object> p = row("projects", project);
        assertThat(p.get("is_deleted")).isEqualTo(true);
        assertThat(p.get("deleted_at")).isNotNull();
        assertThat(jdbc.queryForObject("select status from console.projects where id = ?", String.class,
                UUID.fromString(project))).isEqualTo("ARCHIVED");
        assertThat(jdbc.queryForObject("select status_before_delete from console.projects where id = ?", String.class,
                UUID.fromString(project))).as("軟刪除把 status 改成 ARCHIVED，復原才知道要回到哪").isEqualTo("COMPLETED");
        assertThat(row("goals", goal).get("deleted_at")).as("連帶軟刪的目標與專案同一個時間").isEqualTo(p.get("deleted_at"));
        assertThat(row("tasks", task).get("deleted_at")).isEqualTo(p.get("deleted_at"));
    }

    @Test
    void deletingAGoalOrATaskOnItsOwnWritesItsOwnDeletionTime() {
        String project = createProject("own-delete");
        String goal = createGoal(project, "G");
        String task = createTask(goal, "T1");
        String other = createTask(goal, "T2");

        assertThat(api.delete(operator(), "/api/v1/tasks/" + task).status()).isEqualTo(204);
        assertThat(row("tasks", task).get("deleted_at")).isNotNull();
        assertThat(row("tasks", other).get("deleted_at")).isNull();

        assertThat(api.delete(operator(), "/api/v1/goals/" + goal).status()).isEqualTo(204);
        Object goalDeletedAt = row("goals", goal).get("deleted_at");
        assertThat(goalDeletedAt).isNotNull();
        assertThat(row("tasks", other).get("deleted_at")).as("目標連帶軟刪的任務與目標同一個時間").isEqualTo(goalDeletedAt);
        assertThat(row("projects", project).get("deleted_at")).as("專案沒被刪").isNull();
    }

    // ── 復原（E2E-13 第 2 列）─────────────────────────────────────────────────────────

    @Test
    void restoreBringsBackTheProjectAndTheGoalsAndTasksTakenAlongButNotTheOnesDeletedBeforeTheProject() {
        String project = createProject("restore-main");
        String g1 = createGoal(project, "G1");
        String g2 = createGoal(project, "G2", g1);
        String earlier = createGoal(project, "G3 先前單獨刪除");
        String t1 = createTask(g1, "T1");
        String t2 = createTask(g1, "T2");
        String t3 = createTask(g2, "T3");
        String earlierTask = createTask(earlier, "T4");
        setTaskStatus(t1, "COMPLETED");
        jdbc.update("update console.tasks set retry_count = 2, actual_tokens = 1240 where id = ?", UUID.fromString(t1));
        assertThat(api.delete(operator(), "/api/v1/goals/" + earlier).status()).isEqualTo(204);
        assertThat(api.delete(operator(), "/api/v1/tasks/" + t2).status()).as("專案刪除前就單獨刪除的任務").isEqualTo(204);
        assertThat(delete(project).status()).isEqualTo(204);
        assertThat(api.get(viewer(), PROJECTS + "/" + project).status()).as("刪除後讀不到").isEqualTo(404);

        Resp restored = restore(operator(), project);

        assertThat(restored.status()).isEqualTo(200);
        assertThat(restored.<String>read("$.data.id")).isEqualTo(project);
        assertThat(restored.<String>read("$.data.status")).as("刪除前是 DRAFT").isEqualTo("DRAFT");
        assertThat(restored.<List<String>>read("$.data.goals[*].id")).as("只含復原後未刪的目標")
                .containsExactlyInAnyOrder(g1, g2);
        assertThat(restored.<Integer>read("$.data.goalsCount")).isEqualTo(2);
        assertThat(restored.<Integer>read("$.data.tasksCount")).as("T1、T3；T2 先前就被單獨刪除").isEqualTo(2);

        assertThat(api.get(viewer(), PROJECTS + "/" + project).status()).isEqualTo(200);
        assertThat(api.get(viewer(), "/api/v1/goals/" + g1).status()).isEqualTo(200);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + t1).status()).isEqualTo(200);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + t3).status()).isEqualTo(200);
        assertThat(api.get(viewer(), "/api/v1/goals/" + earlier).status()).as("先前單獨刪除的目標不回來").isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + earlierTask).status()).isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + t2).status()).as("先前單獨刪除的任務不回來").isEqualTo(404);
        assertThat(api.get(viewer(), PROJECTS + "/" + project + "/goals").<List<String>>read("$.data[*].id"))
                .containsExactlyInAnyOrder(g1, g2);
        assertThat(api.get(viewer(), "/api/v1/goals/" + g2).<List<String>>read("$.data.dependsOn"))
                .as("goal_dependencies 不曾被刪，依賴原樣可見").containsExactly(g1);

        Map<String, Object> restoredTask = jdbc.queryForMap("select status, retry_count, actual_tokens, is_deleted, "
                + "deleted_at from console.tasks where id = ?", UUID.fromString(t1));
        assertThat(restoredTask).containsEntry("status", "COMPLETED").containsEntry("retry_count", 2)
                .containsEntry("actual_tokens", 1240L).containsEntry("is_deleted", false);
        assertThat(restoredTask.get("deleted_at")).isNull();
        assertThat(row("projects", project).get("deleted_at")).isNull();
        assertThat(jdbc.queryForObject("select status_before_delete from console.projects where id = ?", String.class,
                UUID.fromString(project))).isNull();
        assertThat(row("goals", earlier).get("is_deleted")).isEqualTo(true);
        assertThat(row("tasks", t2).get("is_deleted")).isEqualTo(true);
    }

    @Test
    void aRestoredProjectIsBackInTheNormalListAndOutOfTheDeletedListAndCanBeDeletedAgain() {
        String project = createProject("back-in-list");
        assertThat(delete(project).status()).isEqualTo(204);
        assertThat(api.get(operator(), PROJECTS).<List<String>>read("$.data.content[*].id")).doesNotContain(project);
        assertThat(api.get(operator(), PROJECTS + "?deleted=true").<List<String>>read("$.data.content[*].id"))
                .contains(project);

        assertThat(restore(operator(), project).status()).isEqualTo(200);

        assertThat(api.get(operator(), PROJECTS).<List<String>>read("$.data.content[*].id")).contains(project);
        assertThat(api.get(operator(), PROJECTS + "?deleted=true").<List<String>>read("$.data.content[*].id"))
                .doesNotContain(project);
        assertThat(delete(project).status()).as("復原後可以再刪、再復原").isEqualTo(204);
        assertThat(restore(operator(), project).status()).isEqualTo(200);
    }

    @ParameterizedTest(name = "刪除前是 {0}，復原後也是 {0}")
    @ValueSource(strings = {"DRAFT", "READY", "COMPLETED", "FAILED"})
    void theStatusBeforeTheDeletionComesBack(String status) {
        String project = createProject("status-" + status);
        setProjectStatus(project, status);
        assertThat(delete(project).status()).isEqualTo(204);

        Resp restored = restore(operator(), project);

        assertThat(restored.<String>read("$.data.status")).isEqualTo(status);
    }

    @Test
    void aProjectDeletedBeforeV9WithoutARecordedStatusComesBackAsDraftWhenUnsignedAndReadyWhenSigned() {
        String unsigned = createProject(Map.of("name", "legacy-draft", "executionPath", "/work/legacy-draft",
                "passCriteria", "- 通過", "draft", true));
        String signed = createProject("legacy-signed");
        for (String id : List.of(unsigned, signed)) {
            // 模擬升級前的資料：已軟刪、ARCHIVED、有 deleted_at（V9 以 updated_at 近似）但沒有 status_before_delete
            jdbc.update("update console.projects set is_deleted = true, status = 'ARCHIVED', deleted_at = now(), "
                    + "status_before_delete = null where id = ?", UUID.fromString(id));
        }

        assertThat(restore(operator(), unsigned).<String>read("$.data.status")).isEqualTo("DRAFT");
        assertThat(restore(operator(), signed).<String>read("$.data.status")).isEqualTo("READY");
    }

    // ── 錯誤路徑（E2E-13 第 3 列）─────────────────────────────────────────────────────

    @Test
    void restoringAProjectThatIsNotDeletedIs409ProjectNotDeletedWithItsStatus() {
        String project = createProject("not-deleted");
        setProjectStatus(project, "READY");

        Resp resp = restore(operator(), project);

        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).isEqualTo(ErrorReasons.PROJECT_NOT_DELETED).isEqualTo("project_not_deleted");
        assertThat(resp.<String>read("$.message")).isEqualTo("專案未被刪除，不需復原");
        assertThat(resp.<String>read("$.details.projectId")).isEqualTo(project);
        assertThat(resp.<String>read("$.details.status")).isEqualTo("READY");
    }

    @Test
    void aDeletionOlderThanTheRetentionIs409RestoreWindowExpiredAndTheBoundaryIsThirtyDays() {
        String old = createProject("window-old");
        String edge = createProject("window-edge");
        String inside = createProject("window-inside");
        for (String id : List.of(old, edge, inside)) {
            assertThat(delete(id).status()).isEqualTo(204);
        }
        backdateSoftDeletion(old, "31 days");
        backdateSoftDeletion(edge, "30 days 1 minute");
        backdateSoftDeletion(inside, "29 days 23 hours");

        Resp expired = restore(operator(), old);
        assertThat(expired.status()).isEqualTo(409);
        assertThat(expired.<String>read("$.reason")).isEqualTo(ErrorReasons.RESTORE_WINDOW_EXPIRED)
                .isEqualTo("restore_window_expired");
        assertThat(expired.<String>read("$.message")).isEqualTo("專案已刪除超過 30 天，不可復原");
        assertThat(expired.<String>read("$.details.projectId")).isEqualTo(old);
        assertThat(expired.<Integer>read("$.details.retentionDays")).isEqualTo(30);
        assertThat(expired.<String>read("$.details.deletedAt")).isNotBlank();
        assertThat(restore(operator(), edge).status()).as("超過 30 天 1 分鐘").isEqualTo(409);
        assertThat(restore(operator(), inside).status()).as("29 天 23 小時前刪的仍在保留期內").isEqualTo(200);

        assertThat(row("projects", old).get("is_deleted")).as("被擋下的復原沒有改任何東西").isEqualTo(true);
        assertThat(api.get(operator(), PROJECTS + "?deleted=true").<List<String>>read("$.data.content[*].id"))
                .as("保留期已過的專案仍列在已刪除清單（資料還在，清除排程預設又是關的）").contains(old, edge);
    }

    @Test
    void anUnknownProjectIs404WithTheDedicatedMessageAndAMalformedIdIs400() {
        String unknown = UUID.randomUUID().toString();
        Resp missing = restore(operator(), unknown);
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.<String>read("$.message")).isEqualTo("專案不存在或已清除：" + unknown);

        Resp malformed = api.post(operator(), PROJECTS + "/not-a-uuid/restore");
        assertThat(malformed.status()).isEqualTo(400);
        assertThat(malformed.<String>read("$.message")).isEqualTo("參數 id 的值格式不正確");
    }

    @Test
    void viewersCannotRestoreOrListDeletedProjectsAndAnonymousIs401() {
        String project = createProject("rbac");
        assertThat(delete(project).status()).isEqualTo(204);

        Resp viewerRestore = restore(viewer(), project);
        assertThat(viewerRestore.status()).isEqualTo(403);
        assertThat(viewerRestore.<String>read("$.reason")).isEqualTo("ACCESS_DENIED");
        Resp viewerList = api.get(viewer(), PROJECTS + "?deleted=true");
        assertThat(viewerList.status()).isEqualTo(403);
        assertThat(viewerList.<String>read("$.reason")).as("與安全層的角色不足同一個 reason").isEqualTo(ErrorReasons.ACCESS_DENIED)
                .isEqualTo("ACCESS_DENIED");
        assertThat(api.get(viewer(), PROJECTS + "?deleted=false").status()).as("deleted=false 仍是 VIEWER 以上").isEqualTo(200);
        assertThat(api.get(viewer(), PROJECTS).status()).isEqualTo(200);

        assertThat(restore(null, project).status()).isEqualTo(401);
        assertThat(api.get(null, PROJECTS + "?deleted=true").status()).isEqualTo(401);
        assertThat(restore(admin(), project).status()).as("ADMIN 也可以").isEqualTo(200);
        assertThat(row("projects", project).get("is_deleted")).isEqualTo(false);
    }

    @Test
    void twoConcurrentRestoresOfTheSameProjectLetExactlyOneSucceed() throws Exception {
        String project = createProject("race");
        assertThat(delete(project).status()).isEqualTo(204);
        ExecutorService pool = Executors.newFixedThreadPool(2);
        try {
            Callable<Integer> call = () -> restore(operator(), project).status();
            Future<Integer> first = pool.submit(call);
            Future<Integer> second = pool.submit(call);

            assertThat(List.of(first.get(), second.get())).containsExactlyInAnyOrder(200, 409);
        } finally {
            pool.shutdownNow();
        }
    }

    // ── 已刪除清單（C-3；契約 §1.6.2）─────────────────────────────────────────────────

    @Test
    void theDeletedListShowsOnlySoftDeletedProjectsWithTheirDeletionTimeAndTheNormalListNeverDoes() {
        String alive = createProject("alive-one");
        String gone = createProject("gone-one");
        createTask(createGoal(gone, "隨專案一起軟刪的目標"), "隨專案一起軟刪的任務");
        assertThat(delete(gone).status()).isEqualTo(204);

        Resp deleted = api.get(operator(), PROJECTS + "?deleted=true");

        assertThat(deleted.status()).isEqualTo(200);
        assertThat(deleted.<List<String>>read("$.data.content[*].id")).containsExactly(gone);
        assertThat(deleted.<String>read("$.data.content[0].deletedAt")).isNotBlank().endsWith("Z");
        assertThat(deleted.<String>read("$.data.content[0].status")).isEqualTo("ARCHIVED");
        assertThat(deleted.<Integer>read("$.data.totalElements")).isEqualTo(1);
        assertThat(deleted.<Integer>read("$.data.content[0].goalsCount")).as("子資料在刪除時都軟刪了，列表只算未刪的：已刪除清單的計數是 0")
                .isZero();
        assertThat(deleted.<Integer>read("$.data.content[0].tasksCount")).isZero();

        Resp normal = api.get(operator(), PROJECTS);
        assertThat(normal.<List<String>>read("$.data.content[*].id")).containsExactly(alive);
        assertThat(normal.has("$.data.content[0].deletedAt")).as("deletedAt 只在 deleted=true 的列表帶值").isFalse();
        assertThat(api.get(operator(), PROJECTS + "?deleted=false").<List<String>>read("$.data.content[*].id"))
                .containsExactly(alive);
    }

    @Test
    void theDeletedListSupportsTheSameFiltersSortingAndPagingAndDefaultsToTheMostRecentlyDeletedFirst() {
        String first = createProject("alpha-del");
        String second = createProject("beta-del");
        String third = createProject("gamma-del");
        for (String id : List.of(first, second, third)) {
            assertThat(delete(id).status()).isEqualTo(204);
        }

        assertThat(api.get(operator(), PROJECTS + "?deleted=true").<List<String>>read("$.data.content[*].id"))
                .as("預設 updatedAt,desc：軟刪除當下會更新 updated_at，所以最近刪除的在前").containsExactly(third, second, first);
        assertThat(api.get(operator(), PROJECTS + "?deleted=true&q=BETA").<List<String>>read("$.data.content[*].id"))
                .containsExactly(second);
        assertThat(api.get(operator(), PROJECTS + "?deleted=true&sort=name,asc").<List<String>>read("$.data.content[*].id"))
                .containsExactly(first, second, third);
        assertThat(api.get(operator(), PROJECTS + "?deleted=true&status=ARCHIVED&size=2&page=1")
                .<List<String>>read("$.data.content[*].id")).hasSize(1);
        assertThat(api.get(operator(), PROJECTS + "?deleted=true&status=READY").<Integer>read("$.data.totalElements"))
                .isZero();
    }

    @Test
    void aDeletedParameterThatIsNotABooleanIs400() {
        Resp resp = api.get(operator(), PROJECTS + "?deleted=abc");
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.errorFields()).containsExactly("deleted");
    }

    // ── 稽核 ───────────────────────────────────────────────────────────────────────

    @Test
    void aRestoreIsAuditedAsProjectRestoreAgainstTheProject() {
        String project = createProject("audited");
        assertThat(delete(project).status()).isEqualTo(204);
        jdbc.execute("TRUNCATE console.audit_log");

        assertThat(restore(operator(), project).status()).isEqualTo(200);

        List<Map<String, Object>> rows = jdbc.queryForList("select subject, role, method, path, entity_type, entity_id, "
                + "http_status from console.audit_log order by occurred_at");
        assertThat(rows).singleElement().satisfies(r -> {
            assertThat(r).containsEntry("subject", "operator").containsEntry("role", "OPERATOR")
                    .containsEntry("method", "POST").containsEntry("path", PROJECTS + "/" + project + "/restore")
                    .containsEntry("entity_type", "project").containsEntry("entity_id", project)
                    .containsEntry("http_status", 200);
        });
    }
}
