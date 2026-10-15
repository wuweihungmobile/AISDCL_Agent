package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.execution.ReviewRequest;
import com.aisdlc.console.domain.model.execution.ReviewStatus;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** 審核項儲存埠（{@code review_requests}；V3＋V7 的重播錨點欄位）。Console 擁有，Bridge 不寫。 */
public interface ReviewRequestRepository {

    ReviewRequest insert(ReviewRequest review);

    Optional<ReviewRequest> findById(UUID id);

    /** {@code SELECT … FOR UPDATE}：序列化並發雙擊的審核決定（契約 §1.2.11「審核項已處理」）。 */
    Optional<ReviewRequest> findByIdForUpdate(UUID id);

    /** 該批次指定狀態的審核項（{@code requested_at} 升冪）。 */
    List<ReviewRequest> findByRunAndStatus(UUID runId, ReviewStatus status);

    /** 該批次全部審核項（{@code requested_at} 升冪）。 */
    List<ReviewRequest> findByRun(UUID runId);

    /** 專案內「其他批次」仍 PENDING 的審核項（新批次建立時自動關閉，契約 §3.5.3）。 */
    List<ReviewRequest> findPendingOfOtherRuns(UUID projectId, UUID exceptRunId);

    /** 專案全部審核項（監控日誌衍生用；可限批次）。 */
    List<ReviewRequest> findByProject(UUID projectId, UUID runIdOrNull);

    /** 更新決定欄位（{@code status／decided_by／decided_at／comment}）。 */
    void update(ReviewRequest review);

    /** 事件錨點在 {@code (seq, sub)} 之後（嚴格大於）的審核項，依 {@code (event_seq, event_sub)} 升冪（{@code /logs} 重播用）。 */
    List<ReviewRequest> findAnchoredAfter(UUID runId, int seq, int sub);

    /** 同 run 同錨點下，{@code review_requests} 與 {@code alerts} 兩表 {@code event_sub} 的最大值＋1（契約 §2.2）。 */
    int nextEventSub(UUID runId, int anchorSeq);
}
