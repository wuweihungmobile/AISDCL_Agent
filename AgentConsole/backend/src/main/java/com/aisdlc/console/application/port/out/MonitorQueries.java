package com.aisdlc.console.application.port.out;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 監控聚合用的唯讀查詢埠（契約 §3.8）。只回「事實列」，公式與視窗比較在 {@code MonitorService}（純 Java，可不經資料庫測）。
 */
public interface MonitorQueries {

    /**
     * 一列步驟事件（{@code execution_steps}；Bridge 寫入）。
     *
     * @param stepId  playbook 的 step_id（取自 {@code input.step_id}）
     * @param attempt 取自 {@code input.attempt}
     */
    record StepFact(UUID id, UUID runId, UUID taskId, String status, Instant timestamp, String stepId, Integer attempt,
                    String errorMessage) {
    }

    /** 一則 Token 樣本（{@code run_token_samples}），附所屬批次的預算與開始時間（趨勢的預算線取桶內最新批次）。 */
    record TokenFact(UUID runId, Instant ts, long delta, Long budget, Instant runStartedAt) {
    }

    /** 全域專案計數：{@code completed}＝{@code COMPLETED} 的專案數；{@code countable}＝非 {@code ARCHIVED} 且未軟刪的專案數。 */
    record ProjectCounts(long completed, long countable) {
    }

    /**
     * 全域任務總計的事實列（契約 §1.3.8，C-1）：{@code execution_steps} 在視窗內 {@code STARTED}／{@code COMPLETED}／
     * {@code FAILED}／{@code RETRYING} 的列數，與有貢獻列的專案數。
     */
    record TaskTotalsFact(long started, long completed, long failed, long retried, int projectsCounted) {
    }

    /**
     * 專案（可限單一批次）的步驟事件列，{@code timestamp ∈ [from, to)}（{@code from} 為 null＝不設下界），依
     * {@code (timestamp, id)} 升冪。
     */
    List<StepFact> steps(UUID projectId, UUID runIdOrNull, Instant fromInclusiveOrNull, Instant toExclusive);

    /** 專案（可限單一批次）在 {@code [from, to)} 內的 Token 樣本，依 {@code ts} 升冪。 */
    List<TokenFact> tokens(UUID projectId, UUID runIdOrNull, Instant fromInclusive, Instant toExclusive);

    ProjectCounts projectCounts();

    /**
     * 全域任務總計：跨全部<b>未封存且未軟刪除</b>的專案，步驟列 {@code timestamp ∈ [from, to)}。與 {@link #steps} 同一張表、
     * 同一判準——只計所屬任務與目標未軟刪的列（{@code task-trend} 的範圍任務也是這個集合），只是不分桶、不分專案。
     */
    TaskTotalsFact taskTotals(Instant fromInclusive, Instant toExclusive);
}
