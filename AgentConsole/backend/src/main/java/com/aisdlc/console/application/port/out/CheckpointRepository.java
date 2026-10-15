package com.aisdlc.console.application.port.out;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 斷點唯讀埠（{@code checkpoints}；Bridge 於每個步驟完成時自行記錄歷史快照，append-only）。
 * {@code stepIdx}／{@code stepId} 取自 {@code state_snapshot} 的 {@code step_idx}／{@code step_id}（＝還原後下一個要跑的步驟）。
 */
public interface CheckpointRepository {

    /**
     * @param stepIdx           還原後下一個要跑的步驟位置（0 起算）
     * @param stepId            還原後下一個步驟的 step_id；已跑完為空字串
     * @param completedStepIds  快照內已完成的 step_id（restore 後重設任務狀態用）
     */
    record CheckpointRow(UUID id, UUID runId, String name, Instant createdAt, boolean automatic, int stepIdx,
                         String stepId, List<String> completedStepIds) {

        public CheckpointRow {
            completedStepIds = completedStepIds == null ? List.of() : List.copyOf(completedStepIds);
        }

        public int completedSteps() {
            return completedStepIds.size();
        }
    }

    /** 該批次全部斷點（舊→新）。 */
    List<CheckpointRow> findByRun(UUID runId);

    Optional<CheckpointRow> findById(UUID id);
}
