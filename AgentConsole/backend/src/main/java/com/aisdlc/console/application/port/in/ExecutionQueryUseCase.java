package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.EngineCapabilities;
import com.aisdlc.console.domain.model.execution.ExecutionRtm;
import com.aisdlc.console.domain.model.execution.ExecutionWarning;
import com.aisdlc.console.domain.model.execution.ResourceUsage;
import com.aisdlc.console.domain.model.execution.ReviewDecision;
import com.aisdlc.console.domain.model.execution.ReviewKind;
import com.aisdlc.console.domain.model.execution.ReviewStatus;
import com.aisdlc.console.domain.model.execution.RunScope;
import com.aisdlc.console.domain.model.execution.RunStatus;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * 執行批次的讀取用例（契約 §1.2.2～§1.2.9）：批次詳情（DB 列合併 Bridge 快照）、列表、步驟分頁、DAG、斷點。
 * 回傳的是「視圖」record，由 web 層轉成 DTO（欄位名與契約的 schema 一致）。
 */
public interface ExecutionQueryUseCase {

    /** {@link #taskHistory} 的上限：一個任務的歷史不得讓詳情回應無界成長。 */
    int TASK_HISTORY_LIMIT = 200;

    /**
     * {@code ExecutionRunResponse}：批次快照。{@code bridgeStatus} 為 Bridge 原值（PAUSING／CANCELLING 在此可見）。
     *
     * @param engineCapabilities spawn 時 Console 送進引擎的能力狀態（讀自 DB，建立時凍結；契約 §1.2.1）；null＝V10 之前的批次
     * @param warnings           v1.5（契約 §1.10.6）：<b>只有 execute 的 201</b> 帶（SDD 治理未啟用的 {@code sdd_governance_inactive}、Bridge 轉入的
     *                           {@code sdd_frozen_digest_absent}）；其餘端點一律空（回應不輸出 {@code warnings} 鍵）
     */
    record RunView(UUID id, UUID projectId, int runNumber, RunStatus status, BridgeStatus bridgeStatus,
                   int autonomyLevel, RunScope scope, long totalTokensUsed, Long tokenBudget, Instant startedAt,
                   Instant completedAt, EngineCapabilities engineCapabilities, List<ExecutionWarning> warnings) {

        public RunView {
            warnings = warnings == null ? List.of() : List.copyOf(warnings);
        }

        /** 沒有警告（execute 以外的所有端點）。 */
        public RunView(UUID id, UUID projectId, int runNumber, RunStatus status, BridgeStatus bridgeStatus,
                       int autonomyLevel, RunScope scope, long totalTokensUsed, Long tokenBudget, Instant startedAt,
                       Instant completedAt, EngineCapabilities engineCapabilities) {
            this(id, projectId, runNumber, status, bridgeStatus, autonomyLevel, scope, totalTokensUsed, tokenBudget,
                    startedAt, completedAt, engineCapabilities, List.of());
        }
    }

    /** {@code CurrentStep}：{@code stepNumber} 是步驟在批次 playbook 內的位置（1 起），不是事件 seq。 */
    record CurrentStepView(String stepId, int stepNumber, UUID taskId, String taskName, UUID goalId, int attempt) {
    }

    /**
     * {@code BridgeInfo}：Bridge 不可達時 {@code connected=false}、{@code status} 與 {@code resources} 為 null。
     *
     * @param resources 引擎行程樹的資源取樣（v1.3，D-12；契約 §3.1.2），來自同一次 {@code GET run} 的回應；引擎行程不存活、
     *                  還沒有樣本、樣本過期、Bridge 不可達或不認得該 run、回應缺這個鍵（舊版 Bridge）時為 null
     */
    record BridgeInfoView(boolean connected, String instance, BridgeStatus status, Boolean runKnown,
                          Instant checkedAt, ResourceUsage resources) {
    }

    /** {@code ReviewRequestResponse}：{@code stepId} 是佐證步驟列 {@code execution_steps.id}（UUID，不是 playbook 的 step_id）。 */
    record ReviewView(UUID id, UUID runId, ReviewKind kind, ReviewStatus status, UUID stepId, UUID taskId,
                      UUID goalId, String taskName, String goalName, String reason, Instant requestedAt,
                      String decidedBy, Instant decidedAt, String comment, List<ReviewDecision> allowedDecisions) {
    }

    /** {@code ExecutionRunDetailResponse}。 */
    record RunDetailView(RunView run, CurrentStepView currentStep, int completedSteps, int totalSteps,
                         Integer lastEventSeq, String reason, long elapsedSec, List<ReviewView> pendingReviews,
                         BridgeInfoView bridge) {
    }

    /**
     * {@code ExecutionRunSummaryResponse}。{@code bridgeStatus}（v1.2，C-11）與 {@link RunView#bridgeStatus} 同義，但列表不為它
     * 逐批呼叫 Bridge：取記憶體內最近一則 status 事件的值，沒有就以 DB 狀態同名值補；DB 為 {@code RUNNING} 又沒有記憶體值時為 null。
     */
    record RunSummaryView(UUID id, UUID projectId, int runNumber, RunStatus status, BridgeStatus bridgeStatus,
                          int autonomyLevel, String scopeMode, long totalTokensUsed, Long tokenBudget,
                          Instant startedAt, Instant completedAt, long durationSec, int tasksTotal, int tasksCompleted,
                          int tasksFailed, Double successRate) {
    }

    /** {@code ExecutionStepResponse}：{@code stepNumber} 是該 step 事件的 Bridge seq，{@code stepId} 才是 playbook 的 step_id。 */
    record StepView(UUID id, UUID runId, UUID taskId, String taskName, UUID goalId, int stepNumber, String stepId,
                    Integer attempt, String action, String status, Long tokensUsed, String errorMessage, String output,
                    Instant timestamp) {
    }

    /**
     * 任務詳情的「執行歷史」單筆（{@code ExecutionStepBrief}；US-T-02）：{@code stepNumber} 同 {@link StepView}（該 step 事件的 Bridge seq，
     * 每個批次各自起算）；{@code tokensUsed} 只有結束的步驟（COMPLETED／FAILED）才有，是該任務在該批次的 Token 歸因累計。
     */
    record TaskStepView(UUID id, int stepNumber, String action, String status, Long tokensUsed, String errorMessage,
                        Instant timestamp) {
    }

    /** {@code DagNode}：{@code status} 是讀取當下目標／任務的現況。 */
    record DagNodeView(UUID id, DagSnapshot.NodeKind kind, String label, String status, UUID goalId, String stepId,
                       Integer sequence) {
    }

    /** {@code DagResponse}。 */
    record DagView(UUID runId, List<DagNodeView> nodes, List<DagSnapshot.Edge> edges, Instant statusAsOf) {
    }

    /** {@code CheckpointResponse}。 */
    record CheckpointView(UUID id, UUID runId, String name, Instant createdAt, boolean automatic, int stepIdx,
                          String stepId, int completedSteps) {
    }

    /** 批次列表的查詢條件（排序鍵 {@code startedAt}／{@code runNumber}）。 */
    record RunListQuery(RunStatus status, boolean byRunNumber, boolean ascending, int page, int size) {
    }

    RunDetailView get(UUID runId);

    PageResult<RunSummaryView> list(UUID projectId, RunListQuery query);

    PageResult<StepView> steps(UUID runId, int afterSeq, int page, int size);

    /** 某任務跨批次的步驟歷史：最近 {@value #TASK_HISTORY_LIMIT} 筆，依時間升冪（任務不存在由呼叫端先擋；這裡查不到就回空）。 */
    List<TaskStepView> taskHistory(UUID taskId);

    DagView dag(UUID runId);

    List<CheckpointView> checkpoints(UUID runId);

    /**
     * 執行追溯覆蓋（v1.5，G-05；契約 §1.10.3）：Bridge {@code GET /autoclaude/runs/{id}/rtm} 的投影（諮詢視圖，{@code advisory} 恆 true）。
     * 批次不在資料庫 → {@code NotFoundException}（無 reason）；批次存在但沒有報告（沒啟用 SDD 治理、尚未結束、非正常走完、工作區已清除，或 Bridge
     * 404 {@code rtm_not_found}）→ {@code NotFoundException}（reason {@code rtm_not_found}，{@code details={runId}}）；報告壞掉（422
     * {@code rtm_unreadable}）→ 422「引擎拒絕此請求」；Bridge 連不上／逾時 → 502／504。不輪詢、不快取。
     */
    ExecutionRtm rtm(UUID runId);
}
