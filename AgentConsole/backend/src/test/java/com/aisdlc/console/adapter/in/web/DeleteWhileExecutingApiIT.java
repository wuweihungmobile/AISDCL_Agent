package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.support.AbstractExecutionIT;
import com.aisdlc.console.support.ApiClient.Resp;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 執行中刪除目標／任務（C-8，QA O-05；契約 §1.6.3、E2E-13 第 8 列）。為什麼重要：批次進行中刪除「尚未開始」的目標或任務，
 * 引擎仍照原 playbook 跑完，畫面上已刪掉的東西卻照樣出現結果——使用者看到的與實際執行的對不上。所以專案有進行中批次
 * （INITIALIZING／RUNNING／PAUSED，含 Bridge 的 PAUSING／CANCELLING）時一律 409 {@code project_executing}，批次結束後才放行。
 */
class DeleteWhileExecutingApiIT extends AbstractExecutionIT {

    private void assertBlocked(Resp resp, String projectId, String runId, String what) {
        assertThat(resp.status()).as(what).isEqualTo(409);
        assertThat(resp.<String>read("$.reason")).as(what).isEqualTo(ErrorReasons.PROJECT_RUN_IN_PROGRESS);
        assertThat(resp.<String>read("$.details.projectId")).as(what).isEqualTo(projectId);
        assertThat(resp.<String>read("$.details.runId")).as(what).isEqualTo(runId);
    }

    private boolean deleted(String table, String id) {
        return Boolean.TRUE.equals(jdbc.queryForObject("select is_deleted from console." + table + " where id = ?",
                Boolean.class, UUID.fromString(id)));
    }

    @Test
    void theReasonIsTheEnglishIdentifierAndNotTheExecuteReasonWhichMeansSomethingElse() {
        assertThat(ErrorReasons.PROJECT_RUN_IN_PROGRESS).isEqualTo("project_executing");
        assertThat(ErrorReasons.PROJECT_EXECUTING).as("execute 被擋的 reason 是另一個常數，不可混用")
                .isEqualTo("專案正在執行中").isNotEqualTo(ErrorReasons.PROJECT_RUN_IN_PROGRESS);
    }

    @Test
    void whileARunIsRunningOrPausedDeletingAnyGoalOrTaskIs409UntilTheRunSettles() {
        Fixture f = prjA("del-exec", 4);
        MINI.manualSteps = true;
        String run = startRun(f.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(f.t1())))).isTrue();

        assertBlocked(api.delete(operator(), "/api/v1/goals/" + f.g2()), f.projectId(), run, "尚未開始的目標（RUNNING）");
        assertBlocked(api.delete(operator(), "/api/v1/tasks/" + f.t3()), f.projectId(), run, "尚未開始的任務（RUNNING）");
        // 與「任務本身 RUNNING」並存時先回 project_executing（它涵蓋更廣）
        assertBlocked(api.delete(operator(), "/api/v1/tasks/" + f.t1()), f.projectId(), run, "RUNNING 的任務");
        assertBlocked(api.delete(operator(), "/api/v1/goals/" + f.g1()), f.projectId(), run, "含 RUNNING 任務的目標");

        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/pause").status()).isEqualTo(200);
        mini(run).release(1);
        assertThat(awaitProjected(run, "PAUSED")).isTrue();
        assertBlocked(api.delete(operator(), "/api/v1/goals/" + f.g2()), f.projectId(), run, "尚未開始的目標（PAUSED）");
        assertBlocked(api.delete(operator(), "/api/v1/tasks/" + f.t3()), f.projectId(), run, "尚未開始的任務（PAUSED）");

        assertThat(deleted("goals", f.g2())).as("被擋下的刪除沒有改任何東西").isFalse();
        assertThat(deleted("tasks", f.t3())).isFalse();

        assertThat(api.post(operator(), "/api/v1/executions/" + run + "/cancel").status()).isEqualTo(200);
        assertThat(awaitProjected(run, "CANCELLED")).isTrue();
        assertThat(consumers.awaitIdle(Duration.ofSeconds(5))).isTrue();

        assertThat(api.delete(operator(), "/api/v1/tasks/" + f.t3()).status()).as("批次進入終態後放行").isEqualTo(204);
        assertThat(api.delete(operator(), "/api/v1/goals/" + f.g2()).status()).isEqualTo(204);
        assertThat(deleted("tasks", f.t3())).isTrue();
        assertThat(deleted("goals", f.g2())).isTrue();
    }

    @Test
    void aProjectWhoseRunsAllFinishedCanDeleteItsGoalsAndTasksAsBefore() {
        Fixture f = prjA("del-done", 4);
        assertThat(awaitProjected(startRun(f.projectId()), "COMPLETED")).isTrue();
        assertThat(consumers.awaitIdle(Duration.ofSeconds(5))).isTrue();

        assertThat(api.delete(operator(), "/api/v1/tasks/" + f.t3()).status()).isEqualTo(204);
        assertThat(api.delete(operator(), "/api/v1/goals/" + f.g2()).status()).isEqualTo(204);
    }

    @Test
    void aRunInAnotherProjectDoesNotBlockDeletingHere() {
        Fixture busy = prjA("del-busy", 4);
        Fixture other = prjA("del-other", 4);
        MINI.manualSteps = true;
        startRun(busy.projectId());
        assertThat(awaitUntil(Duration.ofSeconds(10), () -> "RUNNING".equals(taskStatus(busy.t1())))).isTrue();

        assertThat(api.delete(operator(), "/api/v1/tasks/" + other.t3()).status()).isEqualTo(204);
        assertThat(api.delete(operator(), "/api/v1/goals/" + other.g2()).status()).isEqualTo(204);
    }

    @Test
    void anUnknownGoalOrTaskIsStill404BeforeAnyRunCheckAndTheTaskOwnRunningRuleStillAppliesWithoutARun() {
        assertThat(api.delete(operator(), "/api/v1/goals/" + UUID.randomUUID()).status()).isEqualTo(404);
        assertThat(api.delete(operator(), "/api/v1/tasks/" + UUID.randomUUID()).status()).isEqualTo(404);

        Fixture f = prjA("del-own-rule", 4);
        setTaskStatus(f.t1(), "RUNNING");
        Resp task = api.delete(operator(), "/api/v1/tasks/" + f.t1());
        assertThat(task.status()).isEqualTo(409);
        assertThat(task.<String>read("$.reason")).as("沒有進行中批次：既有的規則照舊").isEqualTo("RUNNING 狀態的任務不可刪除");
        Resp goal = api.delete(operator(), "/api/v1/goals/" + f.g1());
        assertThat(goal.status()).isEqualTo(409);
        assertThat(goal.<String>read("$.reason")).isEqualTo("RUNNING 狀態的任務不可刪除");
    }
}
