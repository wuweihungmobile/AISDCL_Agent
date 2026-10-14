package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/** 目標 API（PRD §5.1.2／§7.1.2、§7.1.4.1 目標 signoff）：CRUD、重排、依賴 Kahn 防環。 */
class GoalApiIT extends AbstractApiIT {

    private String goalsUrl(String projectId) {
        return "/api/v1/projects/" + projectId + "/goals";
    }

    private List<String> dependsOnOf(String goalId) {
        return api.get(viewer(), "/api/v1/goals/" + goalId).read("$.data.dependsOn");
    }

    // ---------------- 建立／列表／詳情 ----------------

    @Test
    void createReturns201AssignsSortOrderAtTheEndAndStartsPendingSignedOff() {
        String project = createProject("Goals");
        Resp first = api.post(operator(), goalsUrl(project), Map.of("name", "G1", "passCriteria", "c1"));
        Resp second = api.post(operator(), goalsUrl(project), Map.of("name", "G2", "passCriteria", "c2"));
        assertThat(first.status()).isEqualTo(201);
        assertThat(first.<String>read("$.data.status")).isEqualTo("PENDING");
        assertThat(first.<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(first.<String>read("$.data.projectId")).isEqualTo(project);
        assertThat(first.<Integer>read("$.data.sortOrder")).isZero();
        assertThat(second.<Integer>read("$.data.sortOrder")).isEqualTo(1);
    }

    @Test
    void draftGoalIsNotSignedOffAndInvalidInputIs400() {
        String project = createProject("Draft goals");
        Resp draft = api.post(operator(), goalsUrl(project), Map.of("name", "D", "passCriteria", "c", "draft", true));
        assertThat(draft.<Boolean>read("$.data.signedOff")).isFalse();

        Resp bad = api.post(operator(), goalsUrl(project), Map.of("name", " ", "passCriteria", ""));
        assertThat(bad.status()).isEqualTo(400);
        assertThat(bad.errorFields()).containsExactlyInAnyOrder("name", "passCriteria");
    }

    @Test
    void createUnderAMissingOrDeletedProjectIs404() {
        assertThat(api.post(operator(), goalsUrl(UUID.randomUUID().toString()),
                Map.of("name", "G", "passCriteria", "c")).status()).isEqualTo(404);
        String project = createProject("Soon gone");
        api.delete(operator(), "/api/v1/projects/" + project);
        assertThat(api.post(operator(), goalsUrl(project), Map.of("name", "G", "passCriteria", "c")).status())
                .isEqualTo(404);
        assertThat(api.get(viewer(), goalsUrl(project)).status()).isEqualTo(404);
    }

    @Test
    void listShowsTaskCountsAndCompletionRatioInSortOrder() {
        String project = createProject("List goals");
        String g1 = createGoal(project, "有任務");
        String g2 = createGoal(project, "沒任務");
        String t1 = createTask(g1, "T1");
        createTask(g1, "T2");
        createTask(g1, "T3");
        setTaskStatus(t1, "COMPLETED");
        String gone = createGoal(project, "已刪除");
        api.delete(operator(), "/api/v1/goals/" + gone);

        Resp list = api.get(viewer(), goalsUrl(project));
        assertThat(list.status()).isEqualTo(200);
        assertThat(list.<List<String>>read("$.data[*].id")).containsExactly(g1, g2);
        assertThat(list.<Integer>read("$.data[0].taskCount")).isEqualTo(3);
        assertThat(list.<Integer>read("$.data[0].completedTaskCount")).isEqualTo(1);
        assertThat(list.<Double>read("$.data[0].completionRatio")).isCloseTo(1.0 / 3, within(1e-9));
        assertThat(list.<Integer>read("$.data[1].taskCount")).isZero();
        assertThat(list.<Double>read("$.data[1].completionRatio")).isZero();
    }

    @Test
    void detailListsTaskTitlesAndDependencies() {
        String project = createProject("Detail goals");
        String base = createGoal(project, "基礎");
        String goal = createGoal(project, "主目標", base);
        String t1 = createTask(goal, "任務一");
        createTask(goal, "任務二");
        setTaskStatus(t1, "COMPLETED");

        Resp detail = api.get(viewer(), "/api/v1/goals/" + goal);
        assertThat(detail.status()).isEqualTo(200);
        assertThat(detail.<List<String>>read("$.data.dependsOn")).containsExactly(base);
        assertThat(detail.<List<String>>read("$.data.tasks[*].name")).containsExactly("任務一", "任務二");
        assertThat(detail.<String>read("$.data.tasks[0].status")).isEqualTo("COMPLETED");
        assertThat(detail.<Integer>read("$.data.taskCount")).isEqualTo(2);
        assertThat(detail.<Integer>read("$.data.completedTaskCount")).isEqualTo(1);
        assertThat(detail.<Double>read("$.data.completionRatio")).isEqualTo(0.5);
        assertThat(api.get(viewer(), "/api/v1/goals/" + UUID.randomUUID()).status()).isEqualTo(404);
    }

    // ---------------- 更新／刪除 ----------------

    @Test
    void updateChangesOnlyProvidedFields() {
        String project = createProject("Update goal");
        String goal = createGoal(project, "舊名稱");
        Resp resp = api.put(operator(), "/api/v1/goals/" + goal,
                Map.of("name", "新名稱", "passCriteria", "新標準", "sortOrder", 5, "description", "說明"));
        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<String>read("$.data.name")).isEqualTo("新名稱");
        assertThat(resp.<String>read("$.data.passCriteria")).isEqualTo("新標準");
        assertThat(resp.<Integer>read("$.data.sortOrder")).isEqualTo(5);
        assertThat(resp.<String>read("$.data.description")).isEqualTo("說明");

        Resp cleared = api.put(operator(), "/api/v1/goals/" + goal, Map.of("description", ""));
        assertThat(cleared.<Object>read("$.data.description")).isNull();
        assertThat(cleared.<String>read("$.data.name")).isEqualTo("新名稱");
        assertThat(api.put(operator(), "/api/v1/goals/" + goal, Map.of("name", " ")).status()).isEqualTo(400);
        assertThat(api.put(operator(), "/api/v1/goals/" + goal, Map.of("sortOrder", -1)).status()).isEqualTo(400);
        assertThat(api.put(operator(), "/api/v1/goals/" + UUID.randomUUID(), Map.of("name", "x")).status())
                .isEqualTo(404);
    }

    @Test
    void deleteIsSoftAndTakesItsTasksWithIt() {
        String project = createProject("Delete goal");
        String goal = createGoal(project, "G");
        String task = createTask(goal, "T");
        assertThat(api.delete(operator(), "/api/v1/goals/" + goal).status()).isEqualTo(204);
        assertThat(api.get(viewer(), "/api/v1/goals/" + goal).status()).isEqualTo(404);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + task).status()).isEqualTo(404);
        assertThat(jdbc.queryForObject("select is_deleted from console.goals where id = ?", Boolean.class,
                UUID.fromString(goal))).isTrue();
        assertThat(jdbc.queryForObject("select is_deleted from console.tasks where id = ?", Boolean.class,
                UUID.fromString(task))).isTrue();
        assertThat(api.get(viewer(), "/api/v1/projects/" + project).<Integer>read("$.data.goalsCount")).isZero();
        assertThat(api.delete(operator(), "/api/v1/goals/" + goal).status()).as("已刪除再刪").isEqualTo(404);
    }

    @Test
    void aGoalWithARunningTaskCannotBeDeleted() {
        String project = createProject("Busy goal");
        String goal = createGoal(project, "G");
        String task = createTask(goal, "T");
        setTaskStatus(task, "RUNNING");
        Resp resp = api.delete(operator(), "/api/v1/goals/" + goal);
        assertThat(resp.status()).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).contains("RUNNING");
        assertThat(api.get(viewer(), "/api/v1/goals/" + goal).status()).isEqualTo(200);
        assertThat(api.get(viewer(), "/api/v1/tasks/" + task).status()).isEqualTo(200);
    }

    // ---------------- 重排 ----------------

    @Test
    void reorderRewritesSortOrderToMatchTheGivenSequence() {
        String project = createProject("Reorder");
        String a = createGoal(project, "A");
        String b = createGoal(project, "B");
        String c = createGoal(project, "C");
        Resp resp = api.put(operator(), "/api/v1/goals/reorder", Map.of("projectId", project,
                "orderedGoalIds", List.of(c, a, b)));
        assertThat(resp.status()).isEqualTo(204);
        assertThat(resp.body()).isEmpty();
        Resp list = api.get(viewer(), goalsUrl(project));
        assertThat(list.<List<String>>read("$.data[*].id")).containsExactly(c, a, b);
        assertThat(list.<List<Integer>>read("$.data[*].sortOrder")).containsExactly(0, 1, 2);
    }

    @Test
    void reorderRejectsIncompleteUnknownDuplicateAndForeignIds() {
        String project = createProject("Reorder bad");
        String a = createGoal(project, "A");
        String b = createGoal(project, "B");
        String other = createGoal(createProject("Other project"), "X");

        Resp missing = api.put(operator(), "/api/v1/goals/reorder", Map.of("projectId", project,
                "orderedGoalIds", List.of(a)));
        assertThat(missing.status()).isEqualTo(400);
        assertThat(missing.<List<String>>read("$.details.missingIds")).containsExactly(b);

        Resp foreign = api.put(operator(), "/api/v1/goals/reorder", Map.of("projectId", project,
                "orderedGoalIds", List.of(a, b, other)));
        assertThat(foreign.status()).isEqualTo(400);
        assertThat(foreign.<List<String>>read("$.details.unknownIds")).containsExactly(other);

        assertThat(api.put(operator(), "/api/v1/goals/reorder", Map.of("projectId", project,
                "orderedGoalIds", List.of(a, a, b))).status()).isEqualTo(400);
        assertThat(api.put(operator(), "/api/v1/goals/reorder", Map.of("projectId", project,
                "orderedGoalIds", List.of())).status()).isEqualTo(400);
        assertThat(api.raw(operator(), HttpMethod.PUT, "/api/v1/goals/reorder",
                "{\"projectId\":\"" + project + "\"}").status()).isEqualTo(400);
        assertThat(api.put(operator(), "/api/v1/goals/reorder", Map.of("projectId", UUID.randomUUID().toString(),
                "orderedGoalIds", List.of(a))).status()).isEqualTo(404);
        assertThat(api.get(viewer(), goalsUrl(project)).<List<String>>read("$.data[*].id")).containsExactly(a, b);
    }

    // ---------------- 依賴（Kahn 防環） ----------------

    @Test
    void dependenciesKeepTheOrderGivenAndUpdateReplacesTheWholeSet() {
        String project = createProject("Deps");
        String a = createGoal(project, "A");
        String b = createGoal(project, "B");
        String c = createGoal(project, "C");
        String d = createGoal(project, "D", c, a, b);
        assertThat(dependsOnOf(d)).containsExactly(c, a, b);

        api.put(operator(), "/api/v1/goals/" + d, Map.of("dependsOn", List.of(b)));
        assertThat(dependsOnOf(d)).containsExactly(b);

        api.put(operator(), "/api/v1/goals/" + d, Map.of("name", "D renamed"));
        assertThat(dependsOnOf(d)).as("沒帶 dependsOn＝不變").containsExactly(b);

        api.put(operator(), "/api/v1/goals/" + d, Map.of("dependsOn", List.of()));
        assertThat(dependsOnOf(d)).as("空陣列＝清除").isEmpty();
    }

    @Test
    void aDiamondShapedGraphIsAccepted() {
        String project = createProject("Diamond");
        String a = createGoal(project, "A");
        String b = createGoal(project, "B", a);
        String c = createGoal(project, "C", a);
        String d = createGoal(project, "D", b, c);
        assertThat(dependsOnOf(d)).containsExactly(b, c);
    }

    @Test
    void aGoalCannotDependOnItself() {
        String project = createProject("Self");
        String a = createGoal(project, "A");
        Resp resp = api.put(operator(), "/api/v1/goals/" + a, Map.of("dependsOn", List.of(a)));
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo("自依賴");
        assertThat(dependsOnOf(a)).isEmpty();
    }

    @Test
    void aTwoGoalCycleIsRejectedWithTheCyclePathAndNothingIsPersisted() {
        String project = createProject("Cycle2");
        String a = createGoal(project, "A");
        String b = createGoal(project, "B", a);
        Resp resp = api.put(operator(), "/api/v1/goals/" + a, Map.of("dependsOn", List.of(b)));
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<String>read("$.reason")).isEqualTo("依賴成環");
        List<String> cycle = resp.read("$.details.cycle");
        assertThat(cycle).contains(a, b);
        assertThat(cycle.get(0)).isEqualTo(cycle.get(cycle.size() - 1));
        assertThat(resp.errorFields()).containsExactly("dependsOn");
        assertThat(dependsOnOf(a)).as("成環的修改不可落庫").isEmpty();
        assertThat(dependsOnOf(b)).containsExactly(a);
    }

    @Test
    void aThreeGoalCycleThroughATransitiveChainIsRejected() {
        String project = createProject("Cycle3");
        String a = createGoal(project, "A");
        String b = createGoal(project, "B", a);
        String c = createGoal(project, "C", b);
        Resp resp = api.put(operator(), "/api/v1/goals/" + a, Map.of("dependsOn", List.of(c)));
        assertThat(resp.status()).isEqualTo(400);
        assertThat(resp.<List<String>>read("$.details.cycle")).contains(a, b, c);
    }

    @Test
    void crossProjectAndMissingAndDeletedDependenciesAreRejected() {
        String project = createProject("Deps owner");
        String mine = createGoal(project, "mine");
        String foreign = createGoal(createProject("Foreign"), "foreign");
        String deleted = createGoal(project, "deleted");
        api.delete(operator(), "/api/v1/goals/" + deleted);
        String ghost = UUID.randomUUID().toString();

        Resp cross = api.put(operator(), "/api/v1/goals/" + mine, Map.of("dependsOn", List.of(foreign)));
        assertThat(cross.status()).isEqualTo(400);
        assertThat(cross.<String>read("$.reason")).isEqualTo("跨專案依賴");
        assertThat(cross.<List<String>>read("$.details.crossProjectIds")).containsExactly(foreign);

        Resp missing = api.put(operator(), "/api/v1/goals/" + mine, Map.of("dependsOn", List.of(ghost)));
        assertThat(missing.status()).isEqualTo(400);
        assertThat(missing.<String>read("$.reason")).isEqualTo("依賴目標不存在");

        assertThat(api.put(operator(), "/api/v1/goals/" + mine, Map.of("dependsOn", List.of(deleted))).status())
                .as("已軟刪除的目標不能被依賴").isEqualTo(400);
        assertThat(api.post(operator(), goalsUrl(project), Map.of("name", "new", "passCriteria", "c",
                "dependsOn", List.of(foreign))).status()).as("建立時同樣檢查").isEqualTo(400);
        assertThat(dependsOnOf(mine)).isEmpty();
    }

    @Test
    void deletingADependencyRemovesItFromDependentsViews() {
        String project = createProject("Dead edge");
        String a = createGoal(project, "A");
        String b = createGoal(project, "B", a);
        api.delete(operator(), "/api/v1/goals/" + a);
        assertThat(dependsOnOf(b)).as("被依賴的目標已刪除，邊視為不存在").isEmpty();
    }

    // ---------------- signoff ----------------

    @Test
    void goalSignoffFollowsTheSameRulesAsProjects() {
        String project = createProject("Goal signoff");
        String draft = api.post(operator(), goalsUrl(project),
                Map.of("name", "D", "passCriteria", "c", "draft", true)).id();

        assertThat(api.post(operator(), "/api/v1/goals/" + draft + "/signoff", Map.of("approver", "")).status())
                .isEqualTo(400);
        Resp ok = api.post(operator(), "/api/v1/goals/" + draft + "/signoff", Map.of("approver", "Bob"));
        assertThat(ok.status()).isEqualTo(200);
        assertThat(ok.<Boolean>read("$.data.signedOff")).isTrue();
        assertThat(ok.<String>read("$.data.signedOffBy")).isEqualTo("Bob");
        assertThat(api.post(operator(), "/api/v1/goals/" + draft + "/signoff", Map.of("approver", "Eve")).status())
                .isEqualTo(409);

        Map<String, Object> manual = new LinkedHashMap<>();
        manual.put("approver", "Bob");
        String signedAlready = createGoal(project, "manual");
        assertThat(api.post(operator(), "/api/v1/goals/" + signedAlready + "/signoff", manual).status())
                .as("手動建立的目標一開始就是 signedOff=true").isEqualTo(409);
        assertThat(api.post(operator(), "/api/v1/goals/" + UUID.randomUUID() + "/signoff", manual).status())
                .isEqualTo(404);
    }
}
