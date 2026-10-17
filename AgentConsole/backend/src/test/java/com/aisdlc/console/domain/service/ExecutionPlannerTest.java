package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.execution.DagSnapshot.EdgeKind;
import com.aisdlc.console.domain.model.execution.DagSnapshot.NodeKind;
import com.aisdlc.console.domain.model.execution.RunLimits;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.ScopeMode;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.domain.service.ExecutionPlanner.GoalWithTasks;
import com.aisdlc.console.domain.service.ExecutionPlanner.Plan;
import com.aisdlc.console.domain.service.ExecutionPlanner.Strategy;
import com.aisdlc.console.support.DomainFixtures;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static com.aisdlc.console.support.DomainFixtures.goal;
import static com.aisdlc.console.support.DomainFixtures.task;
import static com.aisdlc.console.support.DomainFixtures.with;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 範圍解析、分層 Kahn 排序與 step_id 編號（契約 §1.2.1 第 6～8 項、§3.4.4）。
 * 重點是「為什麼」：step_id 必須整份 playbook 唯一（Bridge 以 prompt 辨識步驟邊界），所以用批次內位置而不是 sortOrder
 * （sortOrder 可重複，會撞 id）；同層策略只影響同一層，不得違反依賴。
 */
class ExecutionPlannerTest {

    private final UUID projectId = UUID.randomUUID();

    /** PRJ-A：G1（T1、T2）→ G2（T3）。 */
    private final Goal g1 = goal(projectId, "基礎", 0);
    private final Goal g2 = goal(projectId, "核心", 1, g1.id());
    private final Task t1 = task(g1.id(), "T1", 0);
    private final Task t2 = task(g1.id(), "T2", 1);
    private final Task t3 = task(g2.id(), "T3", 0);
    private final List<GoalWithTasks> prjA = List.of(with(g1, t1, t2), with(g2, t3));

    private static Map<UUID, Set<UUID>> graph(List<GoalWithTasks> goals) {
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>();
        goals.forEach(g -> graph.put(g.goal().id(), g.goal().dependsOn()));
        return graph;
    }

    private Plan plan(List<GoalWithTasks> goals, RunScope scope) {
        return ExecutionPlanner.plan(goals, graph(goals), scope, Strategy.TOPOLOGICAL, true);
    }

    @Test
    void allScopeFlattensGoalsInDependencyOrderWithPositionBasedStepIds() {
        Plan plan = plan(prjA, RunScope.all());

        assertThat(plan.tasks()).extracting(p -> p.stepId()).containsExactly("G1-T1", "G1-T2", "G2-T1");
        assertThat(plan.tasks()).extracting(p -> p.sequence()).containsExactly(1, 2, 3);
        assertThat(plan.tasks()).extracting(p -> p.task().id()).containsExactly(t1.id(), t2.id(), t3.id());
        assertThat(plan.goals()).containsExactly(g1, g2);
    }

    @Test
    void theFrozenDagHasGoalAndTaskNodesWithOneDependencyEdgeAndOneContainsEdgePerTask() {
        Plan plan = plan(prjA, RunScope.all());

        assertThat(plan.dag().nodes()).hasSize(5);
        assertThat(plan.dag().nodes().stream().filter(n -> n.kind() == NodeKind.GOAL)).hasSize(2);
        assertThat(plan.dag().taskNodes()).extracting(n -> n.stepId()).containsExactly("G1-T1", "G1-T2", "G2-T1");
        assertThat(plan.dag().taskNodes()).extracting(n -> n.goalId()).containsExactly(g1.id(), g1.id(), g2.id());
        assertThat(plan.dag().edges().stream().filter(e -> e.kind() == EdgeKind.DEPENDENCY)).singleElement()
                .satisfies(e -> {
                    assertThat(e.from()).isEqualTo(g1.id());
                    assertThat(e.to()).isEqualTo(g2.id());
                });
        assertThat(plan.dag().edges().stream().filter(e -> e.kind() == EdgeKind.CONTAINS)).hasSize(3);
        assertThat(plan.dag().isLastOfGoal(2)).isTrue();
        assertThat(plan.dag().isLastOfGoal(1)).isFalse();
        assertThat(plan.dag().firstPositionOfGoal(g2.id())).contains(3);
    }

    @Test
    void renamingStepIdsRewritesBothTheStepsAndTheFrozenDagButNothingElse() {
        Plan plan = plan(prjA, RunScope.all());

        Plan renamed = plan.withStepIds(Map.of(t1.id(), "sdd-greenfield-at-001-1-1", t3.id(), "sdd-greenfield-at-002-1-1"));

        assertThat(renamed.tasks()).extracting(p -> p.stepId()).as("沒列在映射裡的任務維持 G<g>-T<t>")
                .containsExactly("sdd-greenfield-at-001-1-1", "G1-T2", "sdd-greenfield-at-002-1-1");
        assertThat(renamed.dag().taskNodes()).extracting(n -> n.stepId())
                .containsExactly("sdd-greenfield-at-001-1-1", "G1-T2", "sdd-greenfield-at-002-1-1");
        assertThat(renamed.tasks()).extracting(p -> p.sequence()).as("位置與目標位置的規則不變").containsExactly(1, 2, 3);
        assertThat(renamed.tasks()).extracting(p -> p.goalPosition()).containsExactly(1, 1, 2);
        assertThat(renamed.dag().edges()).isEqualTo(plan.dag().edges());
        assertThat(renamed.dag().taskByStepId("sdd-greenfield-at-002-1-1")).get().extracting(n -> n.id())
                .isEqualTo(t3.id());
        assertThat(plan.tasks()).extracting(p -> p.stepId()).as("原計畫不變（record 不可變）")
                .containsExactly("G1-T1", "G1-T2", "G2-T1");
    }

    @Test
    void completedAndSkippedTasksAreLeftOutAndAGoalWithNothingLeftDisappears() {
        Task done = task(g1.id(), "D", 0, TaskStatus.COMPLETED);
        Task skipped = task(g1.id(), "S", 1, TaskStatus.SKIPPED);
        Goal finished = goal(projectId, "已完成", 5, GoalStatus.COMPLETED);
        Task finishedTask = task(finished.id(), "F", 0, TaskStatus.COMPLETED);
        List<GoalWithTasks> goals = List.of(with(g1, done, skipped, t2), with(finished, finishedTask), with(g2, t3));

        Plan plan = plan(goals, RunScope.all());

        assertThat(plan.tasks()).extracting(p -> p.task().id()).containsExactly(t2.id(), t3.id());
        assertThat(plan.tasks()).extracting(p -> p.stepId()).containsExactly("G1-T1", "G2-T1");
        assertThat(plan.goals()).extracting(Goal::id).containsExactly(g1.id(), g2.id());
    }

    @Test
    void selectedScopeTakesTheGoalsExecutableTasksUnionTheSelectedTasks() {
        Goal g3 = goal(projectId, "第三", 2);
        Task t4 = task(g3.id(), "T4", 0);
        Task t5 = task(g3.id(), "T5", 1);
        List<GoalWithTasks> goals = List.of(with(g1, t1, t2), with(g2, t3), with(g3, t4, t5));
        RunScope scope = new RunScope(ScopeMode.SELECTED, List.of(g1.id()), List.of(t4.id()), RunLimits.NONE, null);

        Plan plan = ExecutionPlanner.plan(goals, graph(goals), scope, Strategy.TOPOLOGICAL, true);

        assertThat(plan.tasks()).extracting(p -> p.task().id()).containsExactly(t1.id(), t2.id(), t4.id());
        assertThat(plan.tasks()).extracting(p -> p.stepId()).containsExactly("G1-T1", "G1-T2", "G2-T1");
    }

    @Test
    void sortOrderCollisionsCannotMakeTwoStepsShareAnId() {
        Goal a = goal(projectId, "A", 0);
        Goal b = goal(projectId, "B", 0);
        Task a1 = task(a.id(), "A1", 0);
        Task b1 = task(b.id(), "B1", 0);

        Plan plan = plan(List.of(with(a, a1), with(b, b1)), RunScope.all());

        assertThat(plan.tasks()).extracting(p -> p.stepId()).doesNotHaveDuplicates().containsExactly("G1-T1", "G2-T1");
    }

    // ── 同層策略（execution.dagSchedulerStrategy）──────────────────────────────

    private List<GoalWithTasks> threeIndependentGoalsAndOneDependent() {
        Goal a = goal(projectId, "A", 2);
        Goal b = goal(projectId, "B", 1);
        Goal c = goal(projectId, "C", 3);
        Goal d = goal(projectId, "D", 0, a.id());
        return List.of(
                with(a, DomainFixtures.taskWith(a.id(), "a1", 0, "x", null, null, 1, 10L)),
                with(b, DomainFixtures.taskWith(b.id(), "b1", 0, "x", null, null, 1, 500L)),
                with(c, DomainFixtures.taskWith(c.id(), "c1", 0, "x", null, null, 1, 1L)),
                with(d, DomainFixtures.taskWith(d.id(), "d1", 0, "x", null, null, 1, 5L)));
    }

    @Test
    void topologicalAndPriorityOrderEachLayerBySortOrderAndNeverPutADependentBeforeItsPrerequisite() {
        List<GoalWithTasks> goals = threeIndependentGoalsAndOneDependent();
        for (Strategy strategy : List.of(Strategy.TOPOLOGICAL, Strategy.PRIORITY)) {
            Plan plan = ExecutionPlanner.plan(goals, graph(goals), RunScope.all(), strategy, true);
            // 第一層 {A(2)、B(1)、C(3)} 依 sortOrder＝B、A、C；D（sortOrder 0 最小）依賴 A，必須在第二層
            assertThat(plan.goals()).extracting(Goal::name).as(strategy.name()).containsExactly("B", "A", "C", "D");
        }
    }

    @Test
    void shortestFirstOrdersEachLayerByTheEstimatedTokenSumOfTheGoalsTasks() {
        List<GoalWithTasks> goals = threeIndependentGoalsAndOneDependent();

        Plan plan = ExecutionPlanner.plan(goals, graph(goals), RunScope.all(), Strategy.SHORTEST_FIRST, true);

        assertThat(plan.goals()).extracting(Goal::name).containsExactly("C", "A", "B", "D");
    }

    @Test
    void shortestFirstTreatsMissingEstimatesAsZeroAndBreaksTiesBySortOrder() {
        Goal a = goal(projectId, "A", 2);
        Goal b = goal(projectId, "B", 1);
        List<GoalWithTasks> goals = List.of(with(a, task(a.id(), "a1", 0)), with(b, task(b.id(), "b1", 0)));

        Plan plan = ExecutionPlanner.plan(goals, graph(goals), RunScope.all(), Strategy.SHORTEST_FIRST, true);

        assertThat(plan.goals()).extracting(Goal::name).containsExactly("B", "A");
    }

    @Test
    void anUnknownStrategyNameFallsBackToTopological() {
        assertThat(Strategy.parse("bogus")).isEqualTo(Strategy.TOPOLOGICAL);
        assertThat(Strategy.parse(null)).isEqualTo(Strategy.TOPOLOGICAL);
        assertThat(Strategy.parse("SHORTEST_FIRST")).isEqualTo(Strategy.SHORTEST_FIRST);
    }

    // ── 驗證順序的各項（細節鍵逐字取自契約）────────────────────────────────────

    private DomainException thrown(List<GoalWithTasks> goals, RunScope scope) {
        return (DomainException) catchThrowable(() -> plan(goals, scope));
    }

    private static Throwable catchThrowable(Runnable runnable) {
        try {
            runnable.run();
            return null;
        } catch (RuntimeException e) {
            return e;
        }
    }

    @Test
    void foreignIdsAreAValidation400NamingTheInvalidOnes() {
        UUID foreignGoal = UUID.randomUUID();
        UUID foreignTask = UUID.randomUUID();
        RunScope scope = new RunScope(ScopeMode.SELECTED, List.of(foreignGoal), List.of(foreignTask), RunLimits.NONE,
                null);

        DomainException e = thrown(prjA, scope);

        assertThat(e).isInstanceOf(ValidationException.class);
        assertThat(e.reason()).isEqualTo(ErrorReasons.SCOPE_INVALID);
        assertThat(e.details()).containsEntry("invalidGoalIds", List.of(foreignGoal.toString()))
                .containsEntry("invalidTaskIds", List.of(foreignTask.toString()));
    }

    @Test
    void selectingFinishedGoalsOrTasksIsA409ListingThem() {
        Task done = task(g1.id(), "D", 2, TaskStatus.COMPLETED);
        Goal finished = goal(projectId, "已完成", 5, GoalStatus.COMPLETED);
        List<GoalWithTasks> goals = List.of(with(g1, t1, done), with(finished, task(finished.id(), "F", 0)));
        RunScope scope = new RunScope(ScopeMode.SELECTED, List.of(finished.id()), List.of(done.id()), RunLimits.NONE,
                null);

        DomainException e = thrown(goals, scope);

        assertThat(e).isInstanceOf(ConflictException.class);
        assertThat(e.reason()).isEqualTo(ErrorReasons.SCOPE_ALREADY_DONE);
        assertThat(e.details()).containsEntry("goalIds", List.of(finished.id().toString()))
                .containsEntry("taskIds", List.of(done.id().toString()));
    }

    @Test
    void aSelectedGoalWhosePrerequisiteIsNeitherSelectedNorFinishedIs409ButAFinishedOneIsFine() {
        RunScope onlyG2 = new RunScope(ScopeMode.SELECTED, List.of(g2.id()), List.of(), RunLimits.NONE, null);

        DomainException e = thrown(prjA, onlyG2);
        assertThat(e.reason()).isEqualTo(ErrorReasons.SCOPE_MISSING_DEPENDENCIES);
        assertThat(e.details()).containsEntry("missingGoalIds", List.of(g1.id().toString()));

        Goal finishedG1 = goal(projectId, "基礎", 0, GoalStatus.COMPLETED);
        Goal dependent = goal(projectId, "核心", 1, finishedG1.id());
        List<GoalWithTasks> goals = List.of(with(finishedG1, task(finishedG1.id(), "T1", 0, TaskStatus.COMPLETED)),
                with(dependent, task(dependent.id(), "T3", 0)));
        Plan plan = plan(goals, new RunScope(ScopeMode.SELECTED, List.of(dependent.id()), List.of(), RunLimits.NONE,
                null));
        assertThat(plan.tasks()).hasSize(1);
    }

    @Test
    void followUpBatchesSkipTheDependencyCompletenessCheck() {
        RunScope onlyG2 = new RunScope(ScopeMode.SELECTED, List.of(), List.of(t3.id()), RunLimits.NONE, null);

        Plan plan = ExecutionPlanner.plan(prjA, graph(prjA), onlyG2, Strategy.TOPOLOGICAL, false);

        assertThat(plan.tasks()).extracting(p -> p.stepId()).containsExactly("G1-T1");
        assertThat(plan.tasks()).extracting(p -> p.task().id()).containsExactly(t3.id());
    }

    @Test
    void nothingExecutableIsA409() {
        List<GoalWithTasks> goals = List.of(with(g1, task(g1.id(), "D", 0, TaskStatus.COMPLETED)));

        DomainException e = thrown(goals, RunScope.all());

        assertThat(e).isInstanceOf(ConflictException.class);
        assertThat(e.reason()).isEqualTo(ErrorReasons.NOTHING_TO_EXECUTE);
    }

    @Test
    void aDependencyCycleThatSlippedPastPhaseTwoIsA409WithTheCycle() {
        Goal a = goal(projectId, "A", 0);
        Goal b = goal(projectId, "B", 1, a.id());
        Map<UUID, Set<UUID>> cyclic = new LinkedHashMap<>();
        cyclic.put(a.id(), Set.of(b.id()));
        cyclic.put(b.id(), Set.of(a.id()));
        List<GoalWithTasks> goals = List.of(with(a, task(a.id(), "a1", 0)), with(b, task(b.id(), "b1", 0)));

        assertThatThrownBy(() -> ExecutionPlanner.plan(goals, cyclic, RunScope.all(), Strategy.TOPOLOGICAL, true))
                .isInstanceOfSatisfying(ConflictException.class, e -> {
                    assertThat(e.reason()).isEqualTo(ErrorReasons.DEPENDENCY_CYCLE);
                    assertThat(e.details()).containsKey("cycle");
                });
    }
}
