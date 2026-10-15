package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.imports.GateError;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedProject;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedTask;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * 三道有界閘與 prompt_too_long（契約 §3.3.5；US-I-10「完整顯示、不截斷、不修剪」）。
 *
 * <p>為什麼重要：上游（LLM／Bridge／規格）不可信，三條路徑與編輯一律由同一支驗證器重新過閘；
 * 違規必須一次全列（使用者不必改一項才看到下一項）、順序固定（QA 逐項斷言）、輸入樹絕不被截斷或修剪。
 */
class ParsedResultValidatorTest {

    private final ParsedResultValidator validator = new ParsedResultValidator();

    private static ParsedTask task(String name, String description) {
        return new ParsedTask(name, description, "輸出含 [" + name + "]", 0, null, null, null, null, null);
    }

    private static ParsedGoal goal(String key, String name, List<String> dependsOn, ParsedTask... tasks) {
        return new ParsedGoal(key, name, "", "完成 " + name, 0, dependsOn, List.of(tasks));
    }

    private static ParsedResult tree(ParsedGoal... goals) {
        return ParsedResult.tree(new ParsedProject("專案", "/work/p", "完成", "說明", 3), List.of(goals));
    }

    private static List<ParsedTask> tasks(int count) {
        List<ParsedTask> tasks = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            tasks.add(task("任務" + i, "請做第 " + i + " 件事"));
        }
        return tasks;
    }

    private static ParsedGoal goalWithTasks(String key, String name, int taskCount) {
        return new ParsedGoal(key, name, "", "完成", 0, List.of(), tasks(taskCount));
    }

    @Test
    void aWellFormedTreePassesAllGates() {
        ParsedResult tree = tree(
                goal("g1", "基礎", List.of(), task("初始化", "請輸出 [T1_DONE]"), task("設定", "請輸出 [T2_DONE]")),
                goal("g2", "核心", List.of("g1"), task("實作", "請輸出 [T3_DONE]")));
        assertThat(validator.validate(tree)).isEmpty();
    }

    // ── max_steps ────────────────────────────────────────────────────────────

    @Test
    void twentyFourTasksInAGoalPassButTwentyFiveViolateMaxStepsWithTheDocumentedShape() {
        assertThat(validator.validate(tree(goalWithTasks("g1", "建立基礎架構", 24)))).isEmpty();

        List<GateError> errors = validator.validate(tree(goalWithTasks("g1", "建立基礎架構", 25)));
        assertThat(errors).singleElement().satisfies(error -> {
            assertThat(error.gate()).isEqualTo("max_steps");
            assertThat(error.location()).isEqualTo("goals[0].tasks");
            assertThat(error.detail()).isEqualTo("目標「建立基礎架構」的任務數 25 超過上限 24（不截斷、不修剪）");
        });
    }

    @Test
    void twentyFiveGoalsViolateMaxStepsAtTheGoalsLevel() {
        List<ParsedGoal> goals = new ArrayList<>();
        for (int i = 0; i < 25; i++) {
            goals.add(goalWithTasks("g" + i, "目標" + i, 1));
        }
        List<GateError> errors = validator.validate(ParsedResult.tree(
                new ParsedProject("專案", "/work/p", "完成", null, 3), goals));
        assertThat(errors).singleElement().satisfies(error -> {
            assertThat(error.gate()).isEqualTo("max_steps");
            assertThat(error.location()).isEqualTo("goals");
            assertThat(error.detail()).contains("25", "24", "不截斷、不修剪");
        });
    }

    @Test
    void theLimitCanBeLoweredButNeverRaisedAboveTwentyFour() {
        assertThat(new ParsedResultValidator(10).maxSteps()).isEqualTo(10);
        assertThat(new ParsedResultValidator(500).maxSteps()).as("可下調不可上調").isEqualTo(24);
        assertThat(new ParsedResultValidator(0).maxSteps()).as("至少 1").isEqualTo(1);
        assertThat(new ParsedResultValidator(10).validate(tree(goalWithTasks("g1", "G", 11))))
                .singleElement().satisfies(e -> assertThat(e.detail()).contains("11", "10"));
    }

    // ── cycle ────────────────────────────────────────────────────────────────

    @Test
    void aDependencyCycleIsReportedWithGoalNamesAndTheLocationOfTheFirstGoalInTheCycle() {
        List<GateError> errors = validator.validate(tree(
                goal("g1", "基礎", List.of("g2"), task("a", "做 a")),
                goal("g2", "核心", List.of("g1"), task("b", "做 b"))));
        assertThat(errors).singleElement().satisfies(error -> {
            assertThat(error.gate()).isEqualTo("cycle");
            assertThat(error.location()).isEqualTo("goals[0].dependsOn");
            assertThat(error.detail()).startsWith("目標依賴成環：").contains(" -> ", "基礎", "核心");
        });
    }

    @Test
    void aLongerCycleBehindAnAcyclicGoalIsStillFound() {
        List<GateError> errors = validator.validate(tree(
                goal("g1", "根", List.of(), task("a", "做 a")),
                goal("g2", "甲", List.of("g1", "g4"), task("b", "做 b")),
                goal("g3", "乙", List.of("g2"), task("c", "做 c")),
                goal("g4", "丙", List.of("g3"), task("d", "做 d"))));
        assertThat(errors).singleElement().satisfies(error -> {
            assertThat(error.gate()).isEqualTo("cycle");
            assertThat(error.detail()).contains("甲", "乙", "丙");
            assertThat(error.detail()).doesNotContain("根");
        });
    }

    @Test
    void selfDependencyDanglingDependencyAndDuplicateKeysAreAllCycleGateViolations() {
        List<GateError> errors = validator.validate(tree(
                goal("g1", "甲", List.of("g1"), task("a", "做 a")),
                goal("g2", "乙", List.of("nope"), task("b", "做 b")),
                goal("g2", "丙", List.of(), task("c", "做 c"))));
        assertThat(errors).extracting(GateError::gate).containsOnly("cycle");
        assertThat(errors).extracting(GateError::detail).anySatisfy(d -> assertThat(d).contains("不可依賴自己"))
                .anySatisfy(d -> assertThat(d).contains("不存在的目標 key：nope"))
                .anySatisfy(d -> assertThat(d).contains("目標 key 重複：g2"));
        assertThat(errors).extracting(GateError::location).contains("goals[0].dependsOn", "goals[1].dependsOn",
                "goals[2].key");
    }

    @Test
    void aGoalWithoutADependsOnListIsTreatedAsHavingNoEdges() {
        ParsedGoal noEdges = new ParsedGoal("g1", "甲", "", "完成", 0, null, List.of(task("a", "做 a")));
        assertThat(validator.validate(tree(noEdges))).isEmpty();
    }

    @Test
    void findCycleReturnsAClosedPathOrEmpty() {
        Map<String, Set<String>> acyclic = new LinkedHashMap<>();
        acyclic.put("a", Set.of());
        acyclic.put("b", Set.of("a"));
        assertThat(ParsedResultValidator.findCycle(acyclic)).isEmpty();

        Map<String, Set<String>> cyclic = new LinkedHashMap<>();
        cyclic.put("a", new LinkedHashSet<>(List.of("c")));
        cyclic.put("b", new LinkedHashSet<>(List.of("a")));
        cyclic.put("c", new LinkedHashSet<>(List.of("b")));
        List<String> cycle = ParsedResultValidator.findCycle(cyclic);
        assertThat(cycle).hasSize(4);
        assertThat(cycle.get(0)).isEqualTo(cycle.get(cycle.size() - 1));
        assertThat(cycle).containsAll(List.of("a", "b", "c"));
    }

    // ── empty_prompt ─────────────────────────────────────────────────────────

    @Test
    void blankDescriptionAndBlankNameAreEmptyPromptViolationsAtTheirOwnLocations() {
        List<GateError> errors = validator.validate(tree(goal("g1", "基礎", List.of(),
                task("   ", "有描述"), task("有名字", "  \t "), task("正常", "請輸出 [OK]"))));
        assertThat(errors).hasSize(2).allSatisfy(e -> assertThat(e.gate()).isEqualTo("empty_prompt"));
        assertThat(errors.get(0).location()).isEqualTo("goals[0].tasks[0].name");
        assertThat(errors.get(0).detail()).contains("（未命名）").contains("goals[0].tasks[0]");
        assertThat(errors.get(1).location()).isEqualTo("goals[0].tasks[1].description");
        assertThat(errors.get(1).detail()).isEqualTo("任務「有名字」的描述為空（goals[0].tasks[1]）");
    }

    @Test
    void aNullDescriptionIsAlsoEmptyBecauseTheGateDoesNotTrustTheCaller() {
        ParsedTask nullDescription = new ParsedTask("T", null, "c", 0, null, null, null, null, null);
        assertThat(validator.validate(tree(goal("g1", "G", List.of(), nullDescription))))
                .extracting(GateError::gate).containsExactly("empty_prompt");
    }

    // ── prompt_too_long ──────────────────────────────────────────────────────

    @Test
    void aPromptOfExactlyTwentyThousandCharactersPassesAndOneMoreFailsWithTheDocumentedShape() {
        String probe = StepPrompt.build("G1-T1", "實作", "目標", "x", "pc");
        int exact = 1 + (StepPrompt.MAX_LENGTH - probe.length());
        ParsedTask atLimit = new ParsedTask("實作", "x".repeat(exact), "pc", 0, null, null, null, null, null);
        ParsedTask overLimit = new ParsedTask("實作", "x".repeat(exact + 1), "pc", 0, null, null, null, null, null);
        ParsedGoal ok = new ParsedGoal("g1", "目標", "", "c", 0, List.of(), List.of(atLimit));
        ParsedGoal bad = new ParsedGoal("g1", "目標", "", "c", 0, List.of(), List.of(overLimit));

        assertThat(StepPrompt.build("G1-T1", "實作", "目標", atLimit.description(), "pc")).hasSize(20_000);
        assertThat(validator.validate(tree(ok))).isEmpty();
        List<GateError> errors = validator.validate(tree(bad));
        assertThat(errors).singleElement().satisfies(error -> {
            assertThat(error.gate()).isEqualTo("prompt_too_long");
            assertThat(error.location()).isEqualTo("goals[0].tasks[0]");
            assertThat(error.detail()).isEqualTo("任務「實作」的 prompt 長度 20001 超過上限 20000");
        });
    }

    // ── 全部一起 ─────────────────────────────────────────────────────────────

    @Test
    void everyViolationIsListedAtOnceInTheDocumentedGateOrderAndTheInputIsNeverTrimmed() {
        List<ParsedTask> many = new ArrayList<>(tasks(25));
        many.set(3, task("空描述", ""));
        String huge = "y".repeat(20_500);
        ParsedGoal first = new ParsedGoal("g1", "多任務", "", "c", 0, List.of("g2"), many);
        ParsedGoal second = new ParsedGoal("g2", "成環", "", "c", 1, List.of("g1"),
                List.of(new ParsedTask("長", huge, "c", 0, null, null, null, null, null)));
        ParsedResult input = tree(first, second);

        List<GateError> errors = validator.validate(input);

        assertThat(errors).extracting(GateError::gate).containsExactly("empty_prompt", "max_steps", "cycle",
                "prompt_too_long");
        assertThat(input.goals().get(0).tasks()).as("不截斷、不修剪").hasSize(25);
        assertThat(input.goals().get(1).tasks().get(0).description()).hasSize(20_500);
    }
}
