package com.aisdlc.console.domain.model.execution;

import java.util.List;
import java.util.UUID;

/**
 * 批次範圍（{@code execution_runs.scope} 的內容；契約 §1.2.1）。{@code followUpOfRunId} 只出現在後續批次
 * （審核 SKIP／無還原點的 RETRY 另開的批次），指向它接續的原批次。
 */
public record RunScope(ScopeMode mode, List<UUID> goalIds, List<UUID> taskIds, RunLimits limits,
                       UUID followUpOfRunId) {

    public RunScope {
        mode = mode == null ? ScopeMode.ALL : mode;
        goalIds = goalIds == null ? List.of() : List.copyOf(goalIds);
        taskIds = taskIds == null ? List.of() : List.copyOf(taskIds);
        limits = limits == null ? RunLimits.NONE : limits;
    }

    public static RunScope all() {
        return new RunScope(ScopeMode.ALL, List.of(), List.of(), RunLimits.NONE, null);
    }

    public RunScope withFollowUpOf(UUID originalRunId) {
        return new RunScope(mode, goalIds, taskIds, limits, originalRunId);
    }
}
