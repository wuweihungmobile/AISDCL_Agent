package com.aisdlc.console.domain.model.execution;

import java.time.Instant;
import java.util.UUID;

/**
 * 執行批次（{@code execution_runs} 的一列；契約 §0.5、Architecture §7.1）。
 *
 * <p>欄位所有權：console-api 只在建立時寫
 * {@code id／projectId／runNumber／autonomyLevel／scope／tokenBudget／dag／startedAt／engineCapabilities}，
 * {@code consoleLastSeq} 由 Console 另以目標明確的 UPDATE 推進；{@code status／totalTokensUsed／completedAt／bridgeInstance}
 * 由 Engine Bridge 擁有，後端只讀。
 *
 * <p>{@code engineCapabilities}（V10；契約 §3.4.2）：spawn 時 Console 送進引擎的能力狀態，建立批次時與這一列同一次 INSERT
 * 寫入、之後不再更新（{@code resume}／{@code restore} 不重算——引擎設定檔在 spawn 時就凍結）；null＝V10 之前建立的批次。
 */
public record ExecutionRun(UUID id, UUID projectId, int runNumber, RunStatus status, int autonomyLevel, RunScope scope,
                           long totalTokensUsed, Long tokenBudget, Instant startedAt, Instant completedAt,
                           DagSnapshot dag, int consoleLastSeq, String bridgeInstance,
                           EngineCapabilities engineCapabilities) {

    public ExecutionRun {
        scope = scope == null ? RunScope.all() : scope;
        dag = dag == null ? DagSnapshot.EMPTY : dag;
        status = status == null ? RunStatus.INITIALIZING : status;
    }

    public boolean terminal() {
        return status.terminal();
    }

    public int totalSteps() {
        return dag.totalSteps();
    }
}
