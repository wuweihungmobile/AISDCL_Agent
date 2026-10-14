package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.IllegalStateTransitionException;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.task.TaskStatus;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.Arrays;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * 狀態機轉移表（PRD 附錄 B.1～B.3）。
 *
 * <p>期望值「獨立」逐列抄自 PRD 附錄 B 的「可轉移至」欄，刻意不從被測的轉移表衍生——
 * 否則實作與測試會一起錯而測試仍綠（測試要能在業務規則被改動時失敗）。
 * 每一個「來源×目標」組合都驗：合法者通過、非法者丟 409 型例外（含自己轉自己）。
 */
class StateMachinesTest {

    private static final Map<ProjectStatus, Set<ProjectStatus>> B1 = Map.of(
            ProjectStatus.DRAFT, Set.of(ProjectStatus.READY, ProjectStatus.ARCHIVED),
            ProjectStatus.READY, Set.of(ProjectStatus.EXECUTING, ProjectStatus.DRAFT, ProjectStatus.ARCHIVED),
            ProjectStatus.EXECUTING, Set.of(ProjectStatus.COMPLETED, ProjectStatus.FAILED, ProjectStatus.READY),
            ProjectStatus.COMPLETED, Set.of(ProjectStatus.ARCHIVED),
            ProjectStatus.FAILED, Set.of(ProjectStatus.READY, ProjectStatus.ARCHIVED),
            ProjectStatus.ARCHIVED, Set.of());

    private static final Map<GoalStatus, Set<GoalStatus>> B2 = Map.of(
            GoalStatus.PENDING, Set.of(GoalStatus.IN_PROGRESS, GoalStatus.SKIPPED),
            GoalStatus.IN_PROGRESS, Set.of(GoalStatus.COMPLETED, GoalStatus.FAILED),
            GoalStatus.COMPLETED, Set.of(),
            GoalStatus.FAILED, Set.of(GoalStatus.PENDING),
            GoalStatus.SKIPPED, Set.of());

    private static final Map<TaskStatus, Set<TaskStatus>> B3 = Map.ofEntries(
            Map.entry(TaskStatus.PENDING, Set.of(TaskStatus.QUEUED)),
            Map.entry(TaskStatus.QUEUED, Set.of(TaskStatus.RUNNING, TaskStatus.BLOCKED)),
            Map.entry(TaskStatus.BLOCKED, Set.of(TaskStatus.QUEUED)),
            Map.entry(TaskStatus.RUNNING,
                    Set.of(TaskStatus.VALIDATING, TaskStatus.FAILED, TaskStatus.PAUSED, TaskStatus.CANCELLED)),
            Map.entry(TaskStatus.VALIDATING, Set.of(TaskStatus.COMPLETED, TaskStatus.FAILED)),
            Map.entry(TaskStatus.COMPLETED, Set.of()),
            Map.entry(TaskStatus.FAILED, Set.of(TaskStatus.QUEUED, TaskStatus.ESCALATED)),
            Map.entry(TaskStatus.ESCALATED, Set.of(TaskStatus.QUEUED, TaskStatus.SKIPPED)),
            Map.entry(TaskStatus.PAUSED, Set.of(TaskStatus.QUEUED)),
            Map.entry(TaskStatus.SKIPPED, Set.of()),
            Map.entry(TaskStatus.CANCELLED, Set.of()));

    static Stream<Arguments> projectPairs() {
        return Arrays.stream(ProjectStatus.values()).flatMap(from -> Arrays.stream(ProjectStatus.values())
                .map(to -> Arguments.of(from, to, B1.get(from).contains(to))));
    }

    static Stream<Arguments> goalPairs() {
        return Arrays.stream(GoalStatus.values()).flatMap(from -> Arrays.stream(GoalStatus.values())
                .map(to -> Arguments.of(from, to, B2.get(from).contains(to))));
    }

    static Stream<Arguments> taskPairs() {
        return Arrays.stream(TaskStatus.values()).flatMap(from -> Arrays.stream(TaskStatus.values())
                .map(to -> Arguments.of(from, to, B3.get(from).contains(to))));
    }

    @ParameterizedTest(name = "專案 {0} -> {1}：合法={2}")
    @MethodSource("projectPairs")
    void projectTransitionsFollowAppendixB1(ProjectStatus from, ProjectStatus to, boolean legal) {
        assertThat(StateMachines.canTransition(from, to)).isEqualTo(legal);
        assertOutcome(legal, () -> StateMachines.requireTransition(from, to));
    }

    @ParameterizedTest(name = "目標 {0} -> {1}：合法={2}")
    @MethodSource("goalPairs")
    void goalTransitionsFollowAppendixB2(GoalStatus from, GoalStatus to, boolean legal) {
        assertThat(StateMachines.canTransition(from, to)).isEqualTo(legal);
        assertOutcome(legal, () -> StateMachines.requireTransition(from, to));
    }

    @ParameterizedTest(name = "任務 {0} -> {1}：合法={2}")
    @MethodSource("taskPairs")
    void taskTransitionsFollowAppendixB3(TaskStatus from, TaskStatus to, boolean legal) {
        assertThat(StateMachines.canTransition(from, to)).isEqualTo(legal);
        assertOutcome(legal, () -> StateMachines.requireTransition(from, to));
    }

    @Test
    void terminalStatesHaveNoOutgoingTransitions() {
        assertThat(StateMachines.allowedFrom(ProjectStatus.ARCHIVED)).isEmpty();
        assertThat(StateMachines.allowedFrom(GoalStatus.COMPLETED)).isEmpty();
        assertThat(StateMachines.allowedFrom(GoalStatus.SKIPPED)).isEmpty();
        assertThat(StateMachines.allowedFrom(TaskStatus.COMPLETED)).isEmpty();
        assertThat(StateMachines.allowedFrom(TaskStatus.SKIPPED)).isEmpty();
        assertThat(StateMachines.allowedFrom(TaskStatus.CANCELLED)).isEmpty();
    }

    @Test
    void illegalTransitionExceptionCarriesStructuredDetailsAndMapsToConflict() {
        assertThatThrownBy(() -> StateMachines.requireTransition(TaskStatus.COMPLETED, TaskStatus.RUNNING))
                .isInstanceOf(ConflictException.class)
                .isInstanceOfSatisfying(IllegalStateTransitionException.class, e -> {
                    assertThat(e.reason()).isEqualTo("非法狀態轉移");
                    assertThat(e.details()).containsEntry("from", "COMPLETED").containsEntry("to", "RUNNING")
                            .containsEntry("entity", "任務");
                });
    }

    private static void assertOutcome(boolean legal, Runnable transition) {
        if (legal) {
            assertThatCode(transition::run).doesNotThrowAnyException();
        } else {
            assertThatThrownBy(transition::run).isInstanceOf(IllegalStateTransitionException.class);
        }
    }
}
