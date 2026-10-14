package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.exception.IllegalStateTransitionException;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.task.TaskStatus;

import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

/**
 * 專案／目標／任務的狀態機（PRD 附錄 B.1～B.3；Architecture §4.1 domain/service）。
 *
 * <p>轉移表逐列對照 PRD 附錄 B 的「可轉移至」欄。「自己轉自己」不在任何一列內，因此一律非法
 * （呼叫端若想表達「沒變」就不要呼叫轉移）。非法轉移丟 {@link IllegalStateTransitionException}（409）。
 */
public final class StateMachines {

    private static final Map<ProjectStatus, Set<ProjectStatus>> PROJECT = new EnumMap<>(ProjectStatus.class);
    private static final Map<GoalStatus, Set<GoalStatus>> GOAL = new EnumMap<>(GoalStatus.class);
    private static final Map<TaskStatus, Set<TaskStatus>> TASK = new EnumMap<>(TaskStatus.class);

    static {
        // B.1 專案狀態
        PROJECT.put(ProjectStatus.DRAFT, EnumSet.of(ProjectStatus.READY, ProjectStatus.ARCHIVED));
        PROJECT.put(ProjectStatus.READY,
                EnumSet.of(ProjectStatus.EXECUTING, ProjectStatus.DRAFT, ProjectStatus.ARCHIVED));
        PROJECT.put(ProjectStatus.EXECUTING,
                EnumSet.of(ProjectStatus.COMPLETED, ProjectStatus.FAILED, ProjectStatus.READY));
        PROJECT.put(ProjectStatus.COMPLETED, EnumSet.of(ProjectStatus.ARCHIVED));
        PROJECT.put(ProjectStatus.FAILED, EnumSet.of(ProjectStatus.READY, ProjectStatus.ARCHIVED));
        PROJECT.put(ProjectStatus.ARCHIVED, EnumSet.noneOf(ProjectStatus.class));

        // B.2 目標狀態
        GOAL.put(GoalStatus.PENDING, EnumSet.of(GoalStatus.IN_PROGRESS, GoalStatus.SKIPPED));
        GOAL.put(GoalStatus.IN_PROGRESS, EnumSet.of(GoalStatus.COMPLETED, GoalStatus.FAILED));
        GOAL.put(GoalStatus.COMPLETED, EnumSet.noneOf(GoalStatus.class));
        GOAL.put(GoalStatus.FAILED, EnumSet.of(GoalStatus.PENDING));
        GOAL.put(GoalStatus.SKIPPED, EnumSet.noneOf(GoalStatus.class));

        // B.3 任務狀態
        TASK.put(TaskStatus.PENDING, EnumSet.of(TaskStatus.QUEUED));
        TASK.put(TaskStatus.QUEUED, EnumSet.of(TaskStatus.RUNNING, TaskStatus.BLOCKED));
        TASK.put(TaskStatus.BLOCKED, EnumSet.of(TaskStatus.QUEUED));
        TASK.put(TaskStatus.RUNNING, EnumSet.of(TaskStatus.VALIDATING, TaskStatus.FAILED,
                TaskStatus.PAUSED, TaskStatus.CANCELLED));
        TASK.put(TaskStatus.VALIDATING, EnumSet.of(TaskStatus.COMPLETED, TaskStatus.FAILED));
        TASK.put(TaskStatus.COMPLETED, EnumSet.noneOf(TaskStatus.class));
        TASK.put(TaskStatus.FAILED, EnumSet.of(TaskStatus.QUEUED, TaskStatus.ESCALATED));
        TASK.put(TaskStatus.ESCALATED, EnumSet.of(TaskStatus.QUEUED, TaskStatus.SKIPPED));
        TASK.put(TaskStatus.PAUSED, EnumSet.of(TaskStatus.QUEUED));
        TASK.put(TaskStatus.SKIPPED, EnumSet.noneOf(TaskStatus.class));
        TASK.put(TaskStatus.CANCELLED, EnumSet.noneOf(TaskStatus.class));
    }

    private StateMachines() {
    }

    public static Set<ProjectStatus> allowedFrom(ProjectStatus from) {
        return Set.copyOf(PROJECT.get(from));
    }

    public static Set<GoalStatus> allowedFrom(GoalStatus from) {
        return Set.copyOf(GOAL.get(from));
    }

    public static Set<TaskStatus> allowedFrom(TaskStatus from) {
        return Set.copyOf(TASK.get(from));
    }

    public static boolean canTransition(ProjectStatus from, ProjectStatus to) {
        return PROJECT.get(from).contains(to);
    }

    public static boolean canTransition(GoalStatus from, GoalStatus to) {
        return GOAL.get(from).contains(to);
    }

    public static boolean canTransition(TaskStatus from, TaskStatus to) {
        return TASK.get(from).contains(to);
    }

    public static void requireTransition(ProjectStatus from, ProjectStatus to) {
        if (!canTransition(from, to)) {
            throw new IllegalStateTransitionException("專案", from.name(), to.name());
        }
    }

    public static void requireTransition(GoalStatus from, GoalStatus to) {
        if (!canTransition(from, to)) {
            throw new IllegalStateTransitionException("目標", from.name(), to.name());
        }
    }

    public static void requireTransition(TaskStatus from, TaskStatus to) {
        if (!canTransition(from, to)) {
            throw new IllegalStateTransitionException("任務", from.name(), to.name());
        }
    }
}
