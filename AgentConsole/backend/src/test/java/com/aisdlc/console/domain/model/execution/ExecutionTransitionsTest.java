package com.aisdlc.console.domain.model.execution;

import com.aisdlc.console.domain.exception.IllegalStateTransitionException;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.domain.service.DagService;
import com.aisdlc.console.domain.service.GoalDerivation;
import com.aisdlc.console.support.DomainFixtures;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 執行事件與審核決定造成的「系統重設」（契約 §3.5.2／§3.5.3）。WHY：PRD 附錄 B 沒有 QUEUED→CANCELLED、
 * CANCELLED／COMPLETED→QUEUED 等轉移，但 cancel／restore／重新執行必須有這些結果；解法是領域層專用方法直接設定，
 * 手動轉移表（{@code StateMachines}）一個字都不改——所以手動路徑仍然被擋。
 */
class ExecutionTransitionsTest {

    private static final Instant NOW = Instant.parse("2026-10-15T09:00:00Z");
    private final UUID goalId = UUID.randomUUID();

    private Task queued() {
        Task t = DomainFixtures.task(goalId, "T", 0, TaskStatus.PENDING);
        t.queueForRun(NOW);
        return t;
    }

    @Test
    void aTaskWalksQueuedRunningValidatingCompletedAndKeepsTheFirstStartTime() {
        Task t = queued();
        assertThat(t.status()).isEqualTo(TaskStatus.QUEUED);

        t.markRunning("AutoClaude", NOW);
        assertThat(t.status()).isEqualTo(TaskStatus.RUNNING);
        assertThat(t.startedAt()).isEqualTo(NOW);
        assertThat(t.assignedAgent()).isEqualTo("AutoClaude");

        Instant later = NOW.plusSeconds(5);
        t.markCompleted(later);
        assertThat(t.status()).isEqualTo(TaskStatus.COMPLETED);
        assertThat(t.completedAt()).isEqualTo(later);
        assertThat(t.startedAt()).isEqualTo(NOW);

        t.markCompleted(later.plusSeconds(1));
        assertThat(t.completedAt()).as("已完成者不動").isEqualTo(later);
    }

    @Test
    void startingFromAnyOtherStatusFirstResetsToQueuedLikeARestoreOfACompletedTask() {
        Task t = DomainFixtures.task(goalId, "T", 0, TaskStatus.COMPLETED);

        t.markRunning("AutoClaude", NOW);

        assertThat(t.status()).isEqualTo(TaskStatus.RUNNING);
        assertThat(t.completedAt()).isNull();
    }

    @Test
    void failureThenEscalationWalksFailedThenEscalated() {
        Task t = queued();
        t.markRunning("AutoClaude", NOW);
        t.countRetry(NOW);
        t.markFailed(NOW);
        assertThat(t.status()).isEqualTo(TaskStatus.FAILED);
        assertThat(t.retryCount()).isEqualTo(1);

        t.markEscalated(NOW);
        assertThat(t.status()).isEqualTo(TaskStatus.ESCALATED);
        t.markFailed(NOW);
        assertThat(t.status()).as("已升級的任務不被降回 FAILED").isEqualTo(TaskStatus.ESCALATED);
    }

    @Test
    void cancelAndRestoreNeedTheSystemResetBecauseTheManualTableForbidsThem() {
        Task running = queued();
        running.markRunning("AutoClaude", NOW);
        assertThatThrownBy(() -> running.transitionTo(TaskStatus.QUEUED, NOW))
                .as("手動轉移表仍不允許 RUNNING→QUEUED").isInstanceOf(IllegalStateTransitionException.class);

        running.systemReset(TaskStatus.CANCELLED, NOW);
        assertThat(running.status()).isEqualTo(TaskStatus.CANCELLED);
        running.queueForRun(NOW);
        assertThat(running.status()).as("重新執行：CANCELLED→QUEUED").isEqualTo(TaskStatus.QUEUED);

        Task escalated = DomainFixtures.task(goalId, "T", 1, TaskStatus.ESCALATED);
        escalated.queueForRun(NOW);
        assertThat(escalated.status()).as("ESCALATED→QUEUED 屬附錄 B.3").isEqualTo(TaskStatus.QUEUED);
    }

    @Test
    void skipComesFromEscalatedByTheStateMachineAndFromAnythingElseByReset() {
        Task escalated = DomainFixtures.task(goalId, "T", 0, TaskStatus.ESCALATED);
        escalated.skip(NOW);
        assertThat(escalated.status()).isEqualTo(TaskStatus.SKIPPED);

        Task failed = DomainFixtures.task(goalId, "T", 1, TaskStatus.FAILED);
        failed.skip(NOW);
        assertThat(failed.status()).isEqualTo(TaskStatus.SKIPPED);
    }

    @Test
    void tokensAccumulateAcrossBatchesAndNonPositiveDeltasAreIgnored() {
        Task t = queued();
        t.addActualTokens(1240, NOW);
        t.addActualTokens(1240, NOW);
        t.addActualTokens(0, NOW);
        t.addActualTokens(-5, NOW);

        assertThat(t.actualTokens()).isEqualTo(2480L);
    }

    @Test
    void theExecutionLogKeepsTheTailWhenItOverflows() {
        Task t = queued();
        t.appendExecutionLog("12345", 8, NOW);
        t.appendExecutionLog("abcdef", 8, NOW);

        assertThat(t.executionLog()).hasSize(8).endsWith("abcdef");
        t.resetExecutionLog(NOW);
        assertThat(t.executionLog()).isNull();
    }

    @Test
    void goalStatusIsDerivedByRGoalInTheDocumentedOrder() {
        assertThat(GoalDerivation.derive(List.of())).isEqualTo(GoalStatus.PENDING);
        assertThat(GoalDerivation.derive(List.of(TaskStatus.QUEUED, TaskStatus.PENDING))).isEqualTo(GoalStatus.PENDING);
        assertThat(GoalDerivation.derive(List.of(TaskStatus.COMPLETED, TaskStatus.QUEUED)))
                .isEqualTo(GoalStatus.IN_PROGRESS);
        assertThat(GoalDerivation.derive(List.of(TaskStatus.RUNNING, TaskStatus.QUEUED)))
                .isEqualTo(GoalStatus.IN_PROGRESS);
        assertThat(GoalDerivation.derive(List.of(TaskStatus.COMPLETED, TaskStatus.ESCALATED, TaskStatus.PENDING)))
                .as("有失敗者即 FAILED，優先於 IN_PROGRESS").isEqualTo(GoalStatus.FAILED);
        assertThat(GoalDerivation.derive(List.of(TaskStatus.COMPLETED, TaskStatus.SKIPPED)))
                .isEqualTo(GoalStatus.COMPLETED);
        assertThat(GoalDerivation.derive(List.of(TaskStatus.SKIPPED, TaskStatus.SKIPPED)))
                .isEqualTo(GoalStatus.SKIPPED);
        assertThat(GoalDerivation.derive(List.of(TaskStatus.CANCELLED, TaskStatus.CANCELLED)))
                .as("取消後沒有進度").isEqualTo(GoalStatus.PENDING);
    }

    @Test
    void goalsAndProjectsAcceptSystemSetStatusWhereTheManualMachineRefuses() {
        Project project = DomainFixtures.project("p");
        project.systemSetStatus(ProjectStatus.EXECUTING, NOW);
        assertThat(project.status()).isEqualTo(ProjectStatus.EXECUTING);

        Project completed = Project.restore(UUID.randomUUID(), "p", "/x", "ok", null, ProjectStatus.COMPLETED, 3, true,
                null, null, false, NOW, NOW, "t", null, null);
        assertThatThrownBy(() -> completed.transitionTo(ProjectStatus.EXECUTING, NOW))
                .isInstanceOf(IllegalStateTransitionException.class);
        completed.startExecuting(NOW);
        assertThat(completed.status()).as("COMPLETED→EXECUTING 是系統重設").isEqualTo(ProjectStatus.EXECUTING);

        Project draft = DomainFixtures.project("d");
        draft.startExecuting(NOW);
        assertThat(draft.status()).as("DRAFT 先內部轉 READY 再轉 EXECUTING").isEqualTo(ProjectStatus.EXECUTING);

        Goal goal = DomainFixtures.goal(UUID.randomUUID(), "g", 0, GoalStatus.FAILED);
        goal.systemSetStatus(GoalStatus.IN_PROGRESS, NOW);
        assertThat(goal.status()).as("附錄 B.2 沒有 FAILED→IN_PROGRESS").isEqualTo(GoalStatus.IN_PROGRESS);
        Instant updated = goal.updatedAt();
        goal.systemSetStatus(GoalStatus.IN_PROGRESS, NOW.plusSeconds(9));
        assertThat(goal.updatedAt()).as("狀態沒變不動 updatedAt").isEqualTo(updated);
    }

    @Test
    void layeredKahnTakesAWholeLayerBeforeMovingOnAndOrdersEachLayerByTheTieBreaker() {
        UUID a = UUID.fromString("00000000-0000-0000-0000-00000000000a");
        UUID b = UUID.fromString("00000000-0000-0000-0000-00000000000b");
        UUID c = UUID.fromString("00000000-0000-0000-0000-00000000000c");
        UUID d = UUID.fromString("00000000-0000-0000-0000-00000000000d");
        Map<UUID, Set<UUID>> graph = new LinkedHashMap<>();
        graph.put(d, Set.of(a));
        graph.put(a, Set.of());
        graph.put(b, Set.of());
        graph.put(c, Set.of());

        List<UUID> descending = DagService.layeredOrder(graph, Comparator.<UUID>naturalOrder().reversed());
        assertThat(descending).containsExactly(c, b, a, d);

        List<UUID> inputOrder = DagService.layeredOrder(graph, null);
        assertThat(inputOrder).containsExactly(a, b, c, d);
    }

    @Test
    void layeredKahnReportsACycleLikeTheOtherEntryPoints() {
        UUID a = UUID.randomUUID();
        UUID b = UUID.randomUUID();
        Map<UUID, Set<UUID>> graph = Map.of(a, Set.of(b), b, Set.of(a));

        assertThatThrownBy(() -> DagService.layeredOrder(graph, null))
                .hasMessageContaining("依賴成環");
    }
}
