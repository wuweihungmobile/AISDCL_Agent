package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.application.service.ResearchHealingNotifier;
import com.aisdlc.console.support.AbstractResearchIT;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.console.support.ResearchP1Fixtures;
import com.aisdlc.minibridge.MiniResearch.Reply;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 自癒歷史端點（API-RP-27；TCS-ResearchToPRD-P2 AC-962-7～9）。為什麼重要：自癒視圖是「系統自己修了幾次、有沒有修好」的唯一事實面——
 * 回應若洩漏 error_message 裡的機密、把歸因與補丁結果假造出來、或在 GET 時偷偷打 Bridge（有副作用），掌舵者看到的就不是真實狀態。
 */
class ResearchHealingApiIT extends AbstractResearchIT {

    private static final String LEAK = "gh" + "p_AbCdEf0123456789xyZ0";

    @Autowired
    private ResearchHealingNotifier notifier;
    private ResearchP1Fixtures p1;
    private UUID research;
    private UUID console;
    private UUID run;

    @BeforeEach
    void fixtures() {
        p1 = new ResearchP1Fixtures(jdbc);
        research = p1.project("heal-" + UUID.randomUUID().toString().substring(0, 8), "UNDECIDED");
        console = UUID.randomUUID();
        jdbc.update("insert into console.projects (id, name, execution_path, pass_criteria, sdd_project) values (?, '自癒專案', ?, '通過', ?)", console,
                "/e2e/" + console, "impl-" + console);
        p1.bind(research, console);
        run = UUID.randomUUID();
        jdbc.update("insert into console.execution_runs (id, project_id, run_number, status, autonomy_level, scope) values (?, ?, 1, 'RUNNING', 4, '{}'::jsonb)", run, console);
    }

    private UUID task(String status) {
        UUID goal = UUID.randomUUID();
        jdbc.update("insert into console.goals (id, project_id, name, pass_criteria) values (?, ?, ?, '通過')", goal, console, "目標 " + goal);
        UUID task = UUID.randomUUID();
        jdbc.update("insert into console.tasks (id, goal_id, name, pass_criteria, status) values (?, ?, ?, '通過', ?)", task, goal, "任務 " + task, status);
        return task;
    }

    private void step(UUID task, int number, String status, String error, String at) {
        jdbc.update("insert into console.execution_steps (id, run_id, task_id, step_number, action, status, error_message, \"timestamp\") "
                + "values (?, ?, ?, ?, '動作', ?, ?, ?::timestamptz)", UUID.randomUUID(), run, task, number, status, error, at);
    }

    private String healing() {
        return RESEARCH + "/projects/" + research + "/healing";
    }

    @Test
    void AT_962_9_1_rowsEqualTheViewWithWindowedAttemptAndViewerCanRead() {
        UUID task = task("RUNNING");
        step(task, 1, "RETRYING", "第一次錯誤", "2026-11-08T01:00:00Z");
        step(task, 2, "RETRYING", "第二次錯誤", "2026-11-08T01:01:00Z");
        step(task, 3, "FAILED", "第三次錯誤", "2026-11-08T01:02:00Z");

        Resp resp = api.get(viewer(), healing());

        assertThat(resp.status()).isEqualTo(200);
        assertThat(resp.<List<Object>>read("$.data.rows")).hasSize(3);
        assertThat(resp.<List<Integer>>read("$.data.rows[*].attempt")).containsExactly(1, 2, 3);
        assertThat(resp.<List<String>>read("$.data.rows[*].status")).containsExactly("RETRYING", "RETRYING", "FAILED");
        assertThat(resp.<List<String>>read("$.data.rows[*].excerpt")).containsExactly("第一次錯誤", "第二次錯誤", "第三次錯誤");
        assertThat(resp.<String>read("$.data.rows[0].taskId")).isEqualTo(task.toString());
        assertThat(resp.has("$.data.maxRetries")).isTrue();
        assertThat(resp.body()).as("可空鍵存在且為 null").contains("\"logSyncedThrough\":null");
        assertThat(bridge().calls).as("GET 零 Bridge 請求").isEmpty();
    }

    @Test
    void AT_962_9_2_maxRetriesComesFromTheAgentSystemParameter() {
        Resp before = api.get(viewer(), healing());
        assertThat(before.<Integer>read("$.data.maxRetries")).isEqualTo(3);
        try {
            jdbc.update("update console.system_configs set value = '5' where category = 'agent' and key = 'maxRetries'");
            Resp after = api.get(viewer(), healing());
            assertThat(after.<Integer>read("$.data.maxRetries")).as("改值後回 5（不快取）").isEqualTo(5);
        } finally {
            jdbc.update("update console.system_configs set value = '3' where category = 'agent' and key = 'maxRetries'");
        }
    }

    @Test
    void AT_962_9_2_attemptsAroundTheLimitAreAllReturnedWithTheirAttemptNumbersSoTheViewCanMarkExhausted() {
        UUID task = task("RUNNING");
        for (int n = 1; n <= 4; n++) {
            step(task, n, n < 4 ? "RETRYING" : "FAILED", "錯誤 " + n, "2026-11-08T01:0" + n + ":00Z");
        }

        Resp resp = api.get(viewer(), healing());

        assertThat(resp.<List<Integer>>read("$.data.rows[*].attempt")).as("上限 3 的減一、等於、加一三列都在；超過者也照列，不出現負的剩餘次數").containsExactly(1, 2, 3, 4);
        assertThat(resp.<Integer>read("$.data.maxRetries")).isEqualTo(3);
    }

    @Test
    void AT_962_9_3_resolvedAndEscalatedAreDerivedFromTheTaskStatus() {
        UUID fixed = task("COMPLETED");
        step(fixed, 1, "RETRYING", "重試中", "2026-11-08T01:00:00Z");
        UUID dead = task("ESCALATED");
        step(dead, 1, "RETRYING", "重試中", "2026-11-08T01:01:00Z");
        step(dead, 2, "FAILED", "耗盡", "2026-11-08T01:02:00Z");
        UUID going = task("RUNNING");
        step(going, 1, "RETRYING", "仍在重試", "2026-11-08T01:03:00Z");

        Resp resp = api.get(viewer(), healing());

        assertThat(resp.<List<Boolean>>read("$.data.rows[?(@.taskId=='" + fixed + "')].resolved")).containsOnly(true);
        assertThat(resp.<List<Boolean>>read("$.data.rows[?(@.taskId=='" + dead + "')].escalated")).containsExactly(false, true);
        assertThat(resp.<List<Boolean>>read("$.data.rows[?(@.taskId=='" + going + "')].resolved")).containsOnly(false);
        assertThat(resp.<List<Boolean>>read("$.data.rows[?(@.taskId=='" + going + "')].escalated")).containsOnly(false);
    }

    @Test
    void AT_962_9_4_attributionAndPatchResultAreAlwaysNullAndNeverInvented() {
        UUID task = task("RUNNING");
        step(task, 1, "RETRYING", "錯誤", "2026-11-08T01:00:00Z");

        Resp resp = api.get(viewer(), healing());

        assertThat(resp.body()).contains("\"attribution\":null").contains("\"patchResult\":null");
        assertThat(resp.<Object>read("$.data.rows[0].attribution")).isNull();
        assertThat(resp.<Object>read("$.data.rows[0].patchResult")).isNull();
    }

    @Test
    void AT_962_9_5_lagAndLogSyncedThroughComeFromTheCachedSyncAndAreNullWithoutOne() {
        UUID task = task("RUNNING");
        step(task, 1, "RETRYING", "a", "2026-11-08T01:00:00Z");
        step(task, 2, "RETRYING", "b", "2026-11-08T01:01:00Z");
        step(task, 3, "FAILED", "c", "2026-11-08T01:02:00Z");
        Resp none = api.get(viewer(), healing());
        assertThat(none.<Object>read("$.data.logSyncedThrough")).isNull();
        assertThat(none.<Integer>read("$.data.logLag")).isZero();

        bridge().next("healing-sync", new Reply(200, Map.of("view_rows", 3, "log_lines", 1, "appended", 0, "spec_change", List.of())));
        notifier.notify(run);   // 經 Notifier 觸發一次 sync（非同步）；等快取出現
        long deadline = System.nanoTime() + 5_000_000_000L;
        while (notifier.latest(research).isEmpty() && System.nanoTime() < deadline) {
            Thread.onSpinWait();
        }
        Resp synced = api.get(viewer(), healing());
        assertThat(synced.<Integer>read("$.data.logLag")).isEqualTo(2);
        assertThat(synced.<String>read("$.data.logSyncedThrough")).startsWith("2026-11-08T01:00");
    }

    @Test
    void AT_962_8_5_specChangeForbiddenIsTrueOnlyOnTheUnresolvedLastRowOfTheLatestRunWhenDriftWasSeen() {
        UUID task = task("RUNNING");
        step(task, 1, "RETRYING", "a", "2026-11-08T01:00:00Z");
        step(task, 2, "FAILED", "b", "2026-11-08T01:01:00Z");
        bridge().next("healing-sync", new Reply(200, Map.of("view_rows", 2, "log_lines", 2, "appended", 0,
                "spec_change", List.of(Map.of("path", "docs/03_testing/TCS.md", "expected", "x", "actual", "y")))));
        notifier.notify(run);
        long deadline = System.nanoTime() + 5_000_000_000L;
        while (notifier.latest(research).isEmpty() && System.nanoTime() < deadline) {
            Thread.onSpinWait();
        }

        Resp resp = api.get(viewer(), healing());

        assertThat(resp.<List<Boolean>>read("$.data.rows[*].specChangeForbidden")).containsExactly(false, true);
        assertThat(resp.<List<String>>read("$.data.specChange.paths")).containsExactly("docs/03_testing/TCS.md");
    }

    @Test
    void AT_962_9_E_3_unknownProjectIs404AndAnUnboundProjectGetsAnEmptyListWithMaxRetries() {
        Resp missing = api.get(viewer(), RESEARCH + "/projects/" + UUID.randomUUID() + "/healing");
        assertThat(missing.status()).isEqualTo(404);
        assertThat(missing.<String>read("$.reason")).isEqualTo("research_not_found");

        UUID unbound = p1.project("heal-unbound-" + UUID.randomUUID().toString().substring(0, 8), "UNDECIDED");
        Resp empty = api.get(viewer(), RESEARCH + "/projects/" + unbound + "/healing");
        assertThat(empty.status()).isEqualTo(200);
        assertThat(empty.<List<Object>>read("$.data.rows")).isEmpty();
        assertThat(empty.<Integer>read("$.data.maxRetries")).isEqualTo(3);
    }

    @Test
    void AT_962_7_5_theWholeResponseBodyContainsNoSecretAndTheExcerptIsTheMaskedLast300Characters() {
        UUID task = task("RUNNING");
        step(task, 1, "RETRYING", "x".repeat(400) + " token " + LEAK + " rejected", "2026-11-08T01:00:00Z");
        step(task, 2, "FAILED", "Authorization: Bearer abc.def-ghi_jkl123 refused", "2026-11-08T01:01:00Z");

        Resp resp = api.get(viewer(), healing());

        assertThat(resp.body()).doesNotContain(LEAK).doesNotContain("abc.def-ghi_jkl123");
        String excerpt = resp.<String>read("$.data.rows[0].excerpt");
        assertThat(excerpt.codePointCount(0, excerpt.length())).isEqualTo(300);
        assertThat(excerpt).endsWith("token *** rejected");
        assertThat(resp.<String>read("$.data.rows[1].excerpt")).isEqualTo("[REDACTED] refused");
    }

    @Test
    void AT_962_9_7_retryingStepsCountsOnlyRetryingRowsWithNoLaterNonRetryingRowOfTheSameTaskAndKanbanAgrees() {
        UUID recovered = task("COMPLETED");
        step(recovered, 1, "RETRYING", "a", "2026-11-08T01:00:00Z");
        step(recovered, 2, "COMPLETED", null, "2026-11-08T01:01:00Z");
        UUID stillRetrying = task("RUNNING");
        step(stillRetrying, 1, "RETRYING", "b", "2026-11-08T01:02:00Z");
        step(stillRetrying, 2, "RETRYING", "c", "2026-11-08T01:03:00Z");
        UUID failed = task("FAILED");
        step(failed, 1, "RETRYING", "d", "2026-11-08T01:04:00Z");
        step(failed, 2, "FAILED", "e", "2026-11-08T01:05:00Z");

        Resp heal = api.get(viewer(), healing());
        Resp kanban = api.get(viewer(), RESEARCH + "/projects/" + research + "/kanban");

        assertThat(heal.<Integer>read("$.data.retryingSteps")).as("只有 stillRetrying 的兩列 RETRYING 之後沒有非 RETRYING 列").isEqualTo(2);
        assertThat(kanban.<Integer>read("$.data.columns.healing.retryingSteps")).isEqualTo(heal.<Integer>read("$.data.retryingSteps"));
    }
}
