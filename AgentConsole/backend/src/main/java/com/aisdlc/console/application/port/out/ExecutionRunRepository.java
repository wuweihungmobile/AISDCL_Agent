package com.aisdlc.console.application.port.out;

import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunStatus;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 執行批次儲存埠（{@code execution_runs}）。欄位所有權（Architecture §7.1）：本埠的 {@link #insert} 只寫 console 欄位
 * （{@code id／project_id／run_number／autonomy_level／scope／token_budget／dag／started_at}），{@code status} 等
 * Bridge 擁有的欄位讀取時才看得到；{@link #updateConsoleLastSeq} 是唯一的更新，且只動 {@code console_last_seq}。
 */
public interface ExecutionRunRepository {

    /** 建立批次列（Bridge 欄位留 DDL 預設：status＝INITIALIZING、total_tokens_used＝0）。 */
    ExecutionRun insert(ExecutionRun run);

    Optional<ExecutionRun> findById(UUID id);

    /** 專案內 {@code run_number} 最大的批次。 */
    Optional<ExecutionRun> findLatestByProject(UUID projectId);

    /** 下一個 {@code run_number}（現有最大值＋1；呼叫端須先鎖專案列以免競態）。 */
    int nextRunNumber(UUID projectId);

    /** 專案目前進行中（INITIALIZING／RUNNING）的批次 id（最新的一個）；沒有回 empty。 */
    Optional<UUID> findActiveRunId(UUID projectId);

    /**
     * 專案「進行中」的批次 id（最新的一個）；沒有回 empty。契約 §1.6.3（C-8）：進行中＝{@code INITIALIZING}／{@code RUNNING}／
     * {@code PAUSED}，即 Bridge 的 RUNNING／PAUSING／PAUSED／CANCELLING（PAUSING 與 CANCELLING 折為 RUNNING）。與
     * {@link #findActiveRunId} 不同：暫停中的批次還沒結束（可 resume），仍可能依原 playbook 繼續跑，所以也算。
     */
    Optional<UUID> findInProgressRunId(UUID projectId);

    /** 專案的批次分頁；{@code status} 為 null 不篩；排序鍵 {@code startedAt} 或 {@code runNumber}。 */
    PageResult<ExecutionRun> findPageByProject(UUID projectId, RunStatus status, boolean byRunNumber,
                                               boolean ascending, int page, int size);

    List<ExecutionRun> findByStatuses(Collection<RunStatus> statuses);

    /** 專案的全部批次，依 {@code run_number} 升冪（監控聚合與報表用）。 */
    List<ExecutionRun> findAllByProject(UUID projectId);

    /**
     * 批次在 DB 已是終態（Bridge 寫的），但專案的讀模型仍是 {@code EXECUTING}——console-api 停機期間 Bridge 把 run 跑完了，
     * 終態事件還沒被消費（只看「專案最新的批次」）。啟動對帳要補處理這些批次，否則專案與任務會永遠卡在執行中。
     */
    List<ExecutionRun> findTerminalOfExecutingProjects();

    /** 補償刪除（呼叫端須先確認該 run 尚無任何 execution_steps，契約 §3.4.5）；回傳是否真的刪到一列。 */
    boolean deleteById(UUID id);

    /** 推進 {@code console_last_seq}（只增不減；Console 擁有此欄）。 */
    void updateConsoleLastSeq(UUID id, int seq);
}
