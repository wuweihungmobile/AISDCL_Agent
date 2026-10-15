package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.goal.GoalStatus;
import com.aisdlc.console.domain.model.task.TaskStatus;

import java.util.Collection;

/**
 * R-goal：由目標下未軟刪任務的狀態推導目標狀態（契約 §3.5.3；每個重算點都套用）。純 Java。
 *
 * <ol>
 *   <li>T 非空且全為 {@code COMPLETED／SKIPPED}：全為 {@code SKIPPED}→{@code SKIPPED}，否則→{@code COMPLETED}；</li>
 *   <li>否則若有任一 {@code FAILED／ESCALATED}→{@code FAILED}；</li>
 *   <li>否則若有任一 {@code RUNNING／VALIDATING／COMPLETED}→{@code IN_PROGRESS}；</li>
 *   <li>否則→{@code PENDING}。</li>
 * </ol>
 * 人工判定（被 REJECT 的 {@code GOAL_COMPLETED} 審核項所指的目標）優先於本推導：呼叫端「先重算、再套人工判定」（AR-11）。
 */
public final class GoalDerivation {

    private GoalDerivation() {
    }

    public static GoalStatus derive(Collection<TaskStatus> taskStatuses) {
        if (!taskStatuses.isEmpty() && taskStatuses.stream().allMatch(GoalDerivation::done)) {
            return taskStatuses.stream().allMatch(s -> s == TaskStatus.SKIPPED) ? GoalStatus.SKIPPED
                    : GoalStatus.COMPLETED;
        }
        if (taskStatuses.stream().anyMatch(s -> s == TaskStatus.FAILED || s == TaskStatus.ESCALATED)) {
            return GoalStatus.FAILED;
        }
        if (taskStatuses.stream().anyMatch(s -> s == TaskStatus.RUNNING || s == TaskStatus.VALIDATING
                || s == TaskStatus.COMPLETED)) {
            return GoalStatus.IN_PROGRESS;
        }
        return GoalStatus.PENDING;
    }

    private static boolean done(TaskStatus status) {
        return status == TaskStatus.COMPLETED || status == TaskStatus.SKIPPED;
    }
}
