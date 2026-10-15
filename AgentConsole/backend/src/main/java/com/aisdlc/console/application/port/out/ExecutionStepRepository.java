package com.aisdlc.console.application.port.out;

import com.aisdlc.console.application.port.in.PageResult;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 執行步驟唯讀埠（{@code execution_steps}；整張表由 Engine Bridge 寫入，Console 只讀）。
 * 每個 {@code step} 事件一列：{@code step_number} 欄放事件 {@code seq}，位置與 attempt 放在 {@code input} JSON。
 */
public interface ExecutionStepRepository {

    /**
     * @param stepNumber 該 step 事件的 Bridge seq（不是步驟位置，契約 §0.6）
     * @param stepId     playbook 的 step_id（取自 {@code input.step_id}）
     * @param attempt    取自 {@code input.attempt}
     */
    record StepRow(UUID id, UUID runId, UUID taskId, int stepNumber, String action, String status, String stepId,
                   Integer attempt, String errorMessage, String output, Instant timestamp) {
    }

    /** 依 {@code step_number} 升冪；{@code afterSeq} 為嚴格大於。 */
    PageResult<StepRow> findPage(UUID runId, int afterSeq, int page, int size);

    /** 該批次是否已有任何步驟列（補償刪除的唯一守門，契約 §3.4.5）。 */
    boolean existsByRun(UUID runId);

    /** 某步驟（playbook step_id）最近一筆指定狀態的列（審核項的佐證步驟）。 */
    Optional<StepRow> findLatest(UUID runId, String stepId, String status);

    /** 該批次全部步驟列（升冪）。 */
    List<StepRow> findAllByRun(UUID runId);

    /** 該批次內某任務的全部步驟列（升冪）。 */
    List<StepRow> findByRunAndTask(UUID runId, UUID taskId);

    /** 某任務跨批次的步驟列（任務詳情的「執行歷史」）：取時間上最近的 {@code limit} 筆，依時間升冪回傳。 */
    List<StepRow> findRecentByTask(UUID taskId, int limit);
}
