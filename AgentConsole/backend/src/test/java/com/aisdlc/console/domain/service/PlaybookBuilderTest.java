package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.SddTaskSpec;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.service.ExecutionPlanner.GoalWithTasks;
import com.aisdlc.console.domain.service.ExecutionPlanner.Plan;
import com.aisdlc.console.domain.service.ExecutionPlanner.Strategy;
import com.aisdlc.console.domain.service.PlaybookBuilder.Playbook;
import com.aisdlc.console.support.DomainFixtures;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 計畫 → Playbook 與 execute 驗證表第 9a～9f 項（契約 §3.4.1、§3.4.3、§1.2.1）。
 * 為什麼重要：Bridge 的 {@code PlaybookIn} 是 extra=forbid（多送欄位整個 422），prompt 超過 20,000 字元在 Windows 會讓引擎
 * 的命令列 spawn 失敗，評估指令是會被真的執行的字串。
 */
class PlaybookBuilderTest {

    private final Project project = DomainFixtures.project("E2E 匯入專案");
    private final Goal g1 = DomainFixtures.goal(project.id(), "基礎", 0);
    private final Goal g2 = DomainFixtures.goal(project.id(), "核心", 1, g1.id());

    private Plan planOf(Task... tasks) {
        Map<UUID, List<Task>> byGoal = new LinkedHashMap<>();
        for (Task t : tasks) {
            byGoal.computeIfAbsent(t.goalId(), k -> new ArrayList<>()).add(t);
        }
        List<GoalWithTasks> goals = new ArrayList<>();
        for (Goal g : List.of(g1, g2)) {
            if (byGoal.containsKey(g.id())) {
                goals.add(new GoalWithTasks(g, byGoal.get(g.id())));
            }
        }
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>();
        goals.forEach(g -> graph.put(g.goal().id(), g.goal().dependsOn()));
        return ExecutionPlanner.plan(goals, graph, RunScope.all(), Strategy.TOPOLOGICAL, true);
    }

    private Playbook build(Task... tasks) {
        return PlaybookBuilder.build(project, planOf(tasks), 3, PlaybookBuilder.DEFAULT_EVALUATOR_ALLOWLIST);
    }

    private DomainException failure(Task... tasks) {
        Plan plan = planOf(tasks);
        return (DomainException) org.junit.jupiter.api.Assertions.assertThrows(DomainException.class,
                () -> PlaybookBuilder.build(project, plan, 3, PlaybookBuilder.DEFAULT_EVALUATOR_ALLOWLIST));
    }

    @Test
    @SuppressWarnings("unchecked")
    void theMapHasExactlyTheFieldsOfTheBridgesPlaybookInAndNeverACommand() {
        Task t1 = DomainFixtures.task(g1.id(), "T1", 0);
        Task t2 = DomainFixtures.taskWith(g1.id(), "T2", 1, "請輸出 [T2_DONE]", "pytest -q", "\\[T2_DONE\\]", 2, null);

        Map<String, Object> playbook = build(t1, t2).toMap();

        assertThat(playbook.keySet()).containsExactly("version", "project", "global_goal", "global_invariants", "tasks");
        assertThat(playbook).containsEntry("version", "1.0").containsEntry("project", "E2E_匯入專案")
                .containsEntry("global_goal", "全部完成");
        assertThat((Map<String, Object>) playbook.get("global_invariants")).containsOnly(
                Map.entry("max_retries_per_step", 3));
        List<Map<String, Object>> tasks = (List<Map<String, Object>>) playbook.get("tasks");
        assertThat(tasks).hasSize(2);
        assertThat(tasks.get(0)).containsEntry("step_id", "G1-T1").containsEntry("name", "T1")
                .containsEntry("goal_task_id", t1.id().toString()).containsEntry("max_retries", 1)
                .containsEntry("expected_output_regex", "\\[T1_DONE\\]").doesNotContainKeys("command",
                        "evaluator_command", "maintain_context");
        assertThat(tasks.get(1)).containsEntry("evaluator_command", "pytest -q").containsEntry("max_retries", 2)
                .containsEntry("step_id", "G1-T2");
        assertThat(tasks.get(0).get("prompt").toString()).startsWith("## 任務 G1-T1：T1\n所屬目標：基礎\n");
    }

    @Test
    void everyStepPromptIsDistinctAndNeverASubstringOfAnother() {
        Task a = DomainFixtures.task(g1.id(), "T1", 0);
        Task b = DomainFixtures.task(g1.id(), "T1", 1);

        List<String> prompts = build(a, b).tasks().stream().map(t -> t.prompt()).toList();

        assertThat(prompts.get(0)).isNotEqualTo(prompts.get(1)).doesNotContain(prompts.get(1));
        assertThat(prompts.get(1)).doesNotContain(prompts.get(0));
    }

    @Test
    void projectNamesAreSanitizedClippedAndNeverEmpty() {
        assertThat(PlaybookBuilder.sanitizeProjectName(DomainFixtures.project("a b/c:d？e"))).isEqualTo("a_b_c_d_e");
        assertThat(PlaybookBuilder.sanitizeProjectName(DomainFixtures.project("x".repeat(300)))).hasSize(200);
        Project empty = DomainFixtures.project("");
        assertThat(PlaybookBuilder.sanitizeProjectName(empty)).isEqualTo("project-" + empty.id().toString().substring(0, 8));
        assertThat(PlaybookBuilder.sanitizeProjectName(DomainFixtures.project("@@@"))).isEqualTo("___");
    }

    @Test
    void aPromptOfExactlyTwentyThousandCharsPassesAndTwentyThousandAndOneIsA422() {
        int base = StepPrompt.build("G1-T1", "T1", "基礎", "x", "通過").length();
        Task exact = DomainFixtures.taskWith(g1.id(), "T1", 0, "x".repeat(StepPrompt.MAX_LENGTH - base + 1), null,
                null, 1, null);
        assertThat(build(exact).tasks().get(0).prompt()).hasSize(StepPrompt.MAX_LENGTH);

        Task tooLong = DomainFixtures.taskWith(g1.id(), "T1", 0, "x".repeat(StepPrompt.MAX_LENGTH - base + 2), null,
                null, 1, null);
        DomainException e = failure(tooLong);
        assertThat(e).isInstanceOf(UnprocessableException.class);
        assertThat(e.reason()).isEqualTo(ErrorReasons.PROMPT_TOO_LONG);
        assertThat(e.details()).containsEntry("taskId", tooLong.id().toString()).containsEntry("stepId", "G1-T1")
                .containsEntry("length", StepPrompt.MAX_LENGTH + 1).containsEntry("limit", StepPrompt.MAX_LENGTH);
    }

    @Test
    void evaluatorCommandsAreCheckedForDeniedCharsThenTheExecutableAllowlist() {
        Task denied = DomainFixtures.taskWith(g1.id(), "T1", 0, "d", "pytest -q; echo hi", null, 1, null);
        DomainException e = failure(denied);
        assertThat(e.reason()).isEqualTo(ErrorReasons.EVALUATOR_DENIED_CHARS);
        assertThat(e.details()).containsEntry("taskId", denied.id().toString()).containsEntry("chars", List.of(";"));

        Task notListed = DomainFixtures.taskWith(g1.id(), "T1", 0, "d", "bash run.sh", null, 1, null);
        e = failure(notListed);
        assertThat(e.reason()).isEqualTo(ErrorReasons.EVALUATOR_NOT_ALLOWED);
        assertThat(e.details()).containsEntry("executable", "bash");
    }

    @Test
    void theExecutableIsTheFirstTokenWithoutPathOrWindowsExtensionIgnoringCase() {
        assertThat(PlaybookBuilder.executableOf("C:\\Tools\\PyTest.EXE -q")).isEqualTo("pytest");
        assertThat(PlaybookBuilder.executableOf("/usr/bin/python3 -m pytest")).isEqualTo("python3");
        assertThat(PlaybookBuilder.executableOf("  GRADLEW.bat test")).isEqualTo("gradlew");
        assertThat(PlaybookBuilder.executableOf("")).isEmpty();
        Task windowsPath = DomainFixtures.taskWith(g1.id(), "T1", 0, "d", "C:\\Python\\python.exe -m pytest", null, 1,
                null);
        assertThat(build(windowsPath).tasks()).hasSize(1);
    }

    @Test
    void aCustomAllowlistReplacesTheDefault() {
        Task t = DomainFixtures.taskWith(g1.id(), "T1", 0, "d", "bash run.sh", null, 1, null);
        Plan plan = planOf(t);

        assertThat(PlaybookBuilder.build(project, plan, 3, Set.of("bash")).tasks()).hasSize(1);
        assertThatThrownBy(() -> PlaybookBuilder.build(project, plan, 3, Set.of("pytest")))
                .isInstanceOf(UnprocessableException.class);
    }

    @Test
    void anUncompilableRegexAndAnOverLimitRetryCountAreEach422() {
        Task badRegex = DomainFixtures.taskWith(g1.id(), "T1", 0, "d", null, "([", 1, null);
        DomainException e = failure(badRegex);
        assertThat(e.reason()).isEqualTo(ErrorReasons.REGEX_NOT_COMPILABLE);
        assertThat(e.details()).containsEntry("taskId", badRegex.id().toString());

        Task tooManyRetries = DomainFixtures.taskWith(g1.id(), "T1", 0, "d", null, null, 25, null);
        e = failure(tooManyRetries);
        assertThat(e.reason()).isEqualTo(ErrorReasons.MAX_RETRIES_EXCEEDED);
        assertThat(e.details()).containsEntry("maxRetries", 25).containsEntry("limit", 20);
    }

    @Test
    void moreThanFiveHundredTasksInOneBatchIsA422() {
        Task[] tasks = new Task[PlaybookBuilder.MAX_TASKS + 1];
        for (int i = 0; i < tasks.length; i++) {
            tasks[i] = DomainFixtures.task(g1.id(), "T" + i, i);
        }

        DomainException e = failure(tasks);

        assertThat(e.reason()).isEqualTo(ErrorReasons.TOO_MANY_TASKS);
        assertThat(e.details()).containsEntry("count", 501).containsEntry("limit", 500);
    }

    // ── v1.5：SDD 批次的 playbook（契約 §3.4.1 的 SDD 補充）──────────────────────────────────

    private Plan sddPlan(Task... tasks) {
        Plan plan = planOf(tasks);
        Map<UUID, String> stepIds = new LinkedHashMap<>();
        for (Task task : tasks) {
            stepIds.put(task.id(), "sdd-greenfield-at-" + task.name().toLowerCase());
        }
        return plan.withStepIds(stepIds);
    }

    @Test
    @SuppressWarnings("unchecked")
    void aSddBatchUsesTheSddStepIdsAndAddsOnlyTheThreeSddFieldsThatHaveValues() {
        Task a = DomainFixtures.sddTask(g1.id(), "AT-001", 0, "x", null);
        Task b = DomainFixtures.sddTask(g1.id(), "AT-002", 1, "x", null);
        Plan plan = sddPlan(a, b);
        String digest = "sha256:" + "a".repeat(64);
        Map<UUID, SddTaskSpec> specs = Map.of(
                a.id(), new SddTaskSpec("sdd", "sdd-greenfield-at-at-001", digest, true, Boolean.TRUE),
                b.id(), new SddTaskSpec("sdd", "sdd-greenfield-at-at-002", digest, false, null));

        Playbook playbook = PlaybookBuilder.build(project, plan, 3, PlaybookBuilder.DEFAULT_EVALUATOR_ALLOWLIST, specs);

        List<Map<String, Object>> tasks = (List<Map<String, Object>>) playbook.toMap().get("tasks");
        assertThat(tasks.get(0)).containsEntry("step_id", "sdd-greenfield-at-at-001").containsEntry("spec_digest", digest)
                .containsEntry("weak_regex", true).containsEntry("maintain_context", true)
                .containsEntry("max_retries", 5).containsEntry("goal_task_id", a.id().toString())
                .doesNotContainKey("command");
        assertThat(tasks.get(1)).containsEntry("step_id", "sdd-greenfield-at-at-002").containsEntry("weak_regex", false)
                .as("maintainContext 缺就不送這個鍵").doesNotContainKey("maintain_context");
        assertThat(playbook.tasks().get(0).prompt()).as("prompt 樣板不變，但帶的是 SDD step_id（邊界辨識要互不為子字串）")
                .startsWith("## 任務 sdd-greenfield-at-at-001：AT-001\n");
    }

    @Test
    @SuppressWarnings("unchecked")
    void aBatchWithoutSddSpecsIsByteForByteTheV14ShapeWithNoSddKeys() {
        Task t = DomainFixtures.taskWith(g1.id(), "T1", 0, "請輸出 [T1_DONE]", "pytest -q", "\\[T1_DONE\\]", 2, null);

        Map<String, Object> first = PlaybookBuilder.build(project, planOf(t), 3,
                PlaybookBuilder.DEFAULT_EVALUATOR_ALLOWLIST).toMap();
        Map<String, Object> second = PlaybookBuilder.build(project, planOf(t), 3,
                PlaybookBuilder.DEFAULT_EVALUATOR_ALLOWLIST, Map.of()).toMap();

        List<Map<String, Object>> tasks = (List<Map<String, Object>>) first.get("tasks");
        assertThat(tasks.get(0).keySet()).containsExactly("step_id", "name", "prompt", "expected_output_regex",
                "evaluator_command", "max_retries", "goal_task_id");
        assertThat(second).as("兩個多載同形").isEqualTo(first);
    }

    @Test
    @SuppressWarnings("unchecked")
    void aBlankSpecDigestIsNotSentAndTheSddFieldsAreNeverInvented() {
        Task t = DomainFixtures.sddTask(g1.id(), "AT-001", 0, "x", null);
        Plan plan = sddPlan(t);

        Playbook playbook = PlaybookBuilder.build(project, plan, 3, PlaybookBuilder.DEFAULT_EVALUATOR_ALLOWLIST,
                Map.of(t.id(), new SddTaskSpec("sdd", "sdd-greenfield-at-at-001", " ", null, null)));

        assertThat(((List<Map<String, Object>>) playbook.toMap().get("tasks")).get(0))
                .doesNotContainKeys("spec_digest", "weak_regex", "maintain_context");
    }

    @Test
    void sddTasksKeepTheirOwnMaxRetriesAndTheUsualValidationsStillReject() {
        Task ok = DomainFixtures.sddTask(g1.id(), "AT-001", 0, "x", null);
        SddTaskSpec spec = new SddTaskSpec("sdd", "sdd-greenfield-at-at-001", "sha256:" + "a".repeat(64), false, null);

        assertThat(PlaybookBuilder.build(project, sddPlan(ok), 3, PlaybookBuilder.DEFAULT_EVALUATOR_ALLOWLIST,
                Map.of(ok.id(), spec)).tasks()).as("路徑 A 填的 5（SCG-4 型）或 2（SCG-5 型）照常沿用 task.maxRetries")
                .singleElement().satisfies(task -> assertThat(task.maxRetries()).isEqualTo(5));

        Task unlisted = DomainFixtures.taskWith(g1.id(), "AT-001", 0, "d", "bash run.sh", null, 5, null);
        Plan plan = sddPlan(unlisted);
        assertThatThrownBy(() -> PlaybookBuilder.build(project, plan, 3, PlaybookBuilder.DEFAULT_EVALUATOR_ALLOWLIST,
                Map.of(unlisted.id(), spec))).isInstanceOfSatisfying(UnprocessableException.class,
                e -> assertThat(e.reason()).isEqualTo(ErrorReasons.EVALUATOR_NOT_ALLOWED));
    }

    @Test
    void theChecksRunOneAtATimeAcrossAllTasksSoTheFirstFailingKindWins() {
        // 第 1 個任務正則壞掉（9d）、第 2 個任務評估指令含禁用字元（9b）：9b 先於 9d
        Task badRegex = DomainFixtures.taskWith(g1.id(), "T1", 0, "d", null, "([", 1, null);
        Task denied = DomainFixtures.taskWith(g1.id(), "T2", 1, "d", "pytest &", null, 1, null);

        assertThat(failure(badRegex, denied).reason()).isEqualTo(ErrorReasons.EVALUATOR_DENIED_CHARS);
    }
}
