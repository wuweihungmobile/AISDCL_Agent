package com.aisdlc.console.application.port.out;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

/** Token 樣本埠（{@code run_token_samples}；Console 擁有，Bridge 不寫 {@code execution_steps.tokens_used}，契約 §6 D-16）。 */
public interface TokenSampleRepository {

    /**
     * @param tokensUsed 本批次累計（Bridge token 事件的 {@code tokens_used}）
     * @param delta      與前一則的差
     * @param taskId     增量歸因的任務（目前尚未結束的步驟所屬任務）；沒有則為 null
     */
    record Sample(UUID runId, int seq, Instant ts, long tokensUsed, long delta, Double contextPct, UUID taskId) {
    }

    /** 冪等寫入（{@code (run_id, seq)} 重複則忽略）；回傳是否真的新增。 */
    boolean insert(Sample sample);

    /** 該批次最近一則樣本（seq 最大）。 */
    Optional<Sample> latest(UUID runId);

    /** 該任務在本批次累計的 Token 增量（{@code ExecutionStepResponse.tokensUsed}、{@code TASK_BUDGET} 判定用）。 */
    long sumDeltaForTask(UUID runId, UUID taskId);

    /** 該目標（其任務）在本批次累計的 Token 增量。 */
    long sumDeltaForGoal(UUID runId, UUID goalId);
}
