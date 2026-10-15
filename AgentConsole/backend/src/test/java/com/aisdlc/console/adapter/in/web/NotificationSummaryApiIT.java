package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.support.AbstractApiIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 通知與待辦計數（API-NTF-01；契約 §1.4.1）。為什麼重要：頂列通知鈴與 signoff 佇列徽章是掌舵者「有什麼等我批准」的唯一提醒——
 * 少算（漏掉草案、或把已軟刪的算成待辦）會讓人沒發現要簽核的東西，多算會讓徽章永遠消不掉；
 * 四個來源（專案、目標、任務、匯入記錄）各自的納入條件都要有證據。
 */
class NotificationSummaryApiIT extends AbstractApiIT {

    private static final String URL = "/api/v1/notifications/summary";

    private Resp summary() {
        Resp resp = api.get(viewer(), URL);
        assertThat(resp.status()).isEqualTo(200);
        return resp;
    }

    private int pendingSignoffs() {
        return summary().<Integer>read("$.data.pendingSignoffs");
    }

    private String draftProject() {
        return createProject(Map.of("name", "草案專案", "executionPath", "/work/draft", "passCriteria", "- 全部通過",
                "draft", true));
    }

    private String draftGoal(String projectId) {
        return api.post(operator(), "/api/v1/projects/" + projectId + "/goals",
                Map.of("name", "草案目標", "passCriteria", "- 完成", "draft", true)).id();
    }

    private String draftTask(String goalId) {
        return api.post(operator(), "/api/v1/goals/" + goalId + "/tasks",
                Map.of("name", "草案任務", "passCriteria", "- 完成", "draft", true)).id();
    }

    private String importRecord() {
        Resp resp = api.post(operator(), "/api/v1/import/text", Map.of("content", "做一個待辦清單"));
        assertThat(resp.status()).isEqualTo(201);
        return resp.id();
    }

    private void setImportState(String id, String status, boolean signedOff) {
        jdbc.update("update console.import_records set status = ?, signed_off = ? where id = ?", status, signedOff,
                UUID.fromString(id));
    }

    @Test
    void anEmptySystemReportsZerosAndNoBridgeProbeYet() {
        Resp resp = summary();
        assertThat(resp.<Integer>read("$.data.pendingSignoffs")).isZero();
        assertThat(resp.<Integer>read("$.data.pendingReviews")).isZero();
        assertThat(resp.<Integer>read("$.data.unacknowledgedAlerts")).isZero();
        assertThat(resp.<Object>read("$.data.bridgeConnected")).as("探測環還不存在：缺席或 null").isNull();
        assertThat(resp.<Object>read("$.data.bridgeCheckedAt")).isNull();
    }

    @Test
    void unsignedProjectsGoalsAndTasksAreEachCountedAndSignoffRemovesThemOneByOne() {
        String project = draftProject();
        String goal = draftGoal(project);
        String task = draftTask(goal);
        assertThat(pendingSignoffs()).as("專案＋目標＋任務各一").isEqualTo(3);

        assertThat(api.post(operator(), "/api/v1/tasks/" + task + "/signoff", Map.of("approver", "Alice")).status())
                .isEqualTo(200);
        assertThat(pendingSignoffs()).isEqualTo(2);
        assertThat(api.post(operator(), "/api/v1/goals/" + goal + "/signoff", Map.of("approver", "Alice")).status())
                .isEqualTo(200);
        assertThat(pendingSignoffs()).isEqualTo(1);
        assertThat(api.post(operator(), "/api/v1/projects/" + project + "/signoff", Map.of("approver", "Alice"))
                .status()).isEqualTo(200);
        assertThat(pendingSignoffs()).isZero();
    }

    @Test
    void manuallyCreatedSignedOffItemsAreNotPending() {
        String project = createProject("已簽專案");
        String goal = createGoal(project, "已簽目標");
        createTask(goal, "已簽任務");
        assertThat(pendingSignoffs()).isZero();
    }

    @Test
    void softDeletedItemsAreNeverCountedEvenThoughTheirRowsStillExist() {
        String project = draftProject();
        String goal = draftGoal(project);
        draftTask(goal);
        assertThat(pendingSignoffs()).isEqualTo(3);

        assertThat(api.delete(operator(), "/api/v1/projects/" + project).status()).isEqualTo(204);
        assertThat(pendingSignoffs()).isZero();
        assertThat(jdbc.queryForObject("select count(*) from console.tasks where signed_off = false", Integer.class))
                .as("列還在（軟刪），只是不再算待辦").isEqualTo(1);
    }

    @Test
    void aSoftDeletedGoalHidesItsOwnTasksFromTheCountToo() {
        String project = draftProject();
        String goal = draftGoal(project);
        draftTask(goal);
        assertThat(api.post(operator(), "/api/v1/projects/" + project + "/signoff", Map.of("approver", "Alice"))
                .status()).isEqualTo(200);
        assertThat(pendingSignoffs()).isEqualTo(2);

        assertThat(api.delete(operator(), "/api/v1/goals/" + goal).status()).isEqualTo(204);
        assertThat(pendingSignoffs()).isZero();
    }

    @Test
    void importRecordsCountOnlyWhileParsedOrReviewingAndNotYetSignedOff() {
        String upload = importRecord();
        assertThat(pendingSignoffs()).as("UPLOADED 還沒有草案可簽").isZero();

        setImportState(upload, "PARSED", false);
        assertThat(pendingSignoffs()).isEqualTo(1);
        setImportState(upload, "REVIEWING", false);
        assertThat(pendingSignoffs()).isEqualTo(1);

        setImportState(upload, "REVIEWING", true);
        assertThat(pendingSignoffs()).as("已簽、等 confirm 的不算待簽").isZero();

        for (String status : new String[] {"UPLOADED", "PARSING", "IMPORTED", "REJECTED"}) {
            setImportState(upload, status, false);
            assertThat(pendingSignoffs()).as(status).isZero();
        }

        String second = importRecord();
        setImportState(upload, "PARSED", false);
        setImportState(second, "PARSED", false);
        assertThat(pendingSignoffs()).isEqualTo(2);
    }

    @Test
    void pendingReviewsAndUnacknowledgedAlertsComeFromTheirOwnTables() {
        String project = createProject("監控專案");
        UUID runId = UUID.randomUUID();
        jdbc.update("insert into console.execution_runs (id, project_id, run_number, status, autonomy_level, scope) "
                + "values (?, ?, 1, 'RUNNING', 3, '{\"mode\":\"ALL\"}'::jsonb)", runId, UUID.fromString(project));
        jdbc.update("insert into console.review_requests (run_id, kind, status) values (?, 'TASK_CONFIRM', 'PENDING')",
                runId);
        jdbc.update("insert into console.review_requests (run_id, kind, status) values (?, 'ESCALATED', 'PENDING')",
                runId);
        jdbc.update("insert into console.review_requests (run_id, kind, status) values (?, 'GOAL_CONFIRM', "
                + "'APPROVED')", runId);
        jdbc.update("insert into console.alerts (project_id, run_id, rule, severity, message) values "
                + "(?, ?, 'TOKEN_BUDGET_WARNING', 'WARNING', '預算 80%')", UUID.fromString(project), runId);
        jdbc.update("insert into console.alerts (project_id, rule, severity, message, acknowledged) values "
                + "(?, 'CONSECUTIVE_FAILURES', 'CRITICAL', '連續失敗', true)", UUID.fromString(project));

        Resp resp = summary();
        assertThat(resp.<Integer>read("$.data.pendingReviews")).as("只算 PENDING").isEqualTo(2);
        assertThat(resp.<Integer>read("$.data.unacknowledgedAlerts")).as("只算未確認").isEqualTo(1);
        assertThat(resp.<Integer>read("$.data.pendingSignoffs")).isZero();
    }

    @Test
    void anyAuthenticatedRoleMayReadItAndAnonymousMayNot() {
        for (String token : new String[] {viewer(), operator(), admin()}) {
            assertThat(api.get(token, URL).status()).isEqualTo(200);
        }
        assertThat(api.get(null, URL).status()).isEqualTo(401);
    }

    @Test
    void theSummaryIsCrossProjectAndSumsEverySource() {
        String first = draftProject();
        draftGoal(first);
        String second = draftProject();
        String upload = importRecord();
        setImportState(upload, "PARSED", false);

        assertThat(pendingSignoffs()).as("2 個專案＋1 個目標＋1 筆匯入").isEqualTo(4);
        assertThat(second).isNotEqualTo(first);
    }
}
