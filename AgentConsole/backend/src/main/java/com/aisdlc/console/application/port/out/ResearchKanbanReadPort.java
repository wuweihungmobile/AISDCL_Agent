package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.research.ResearchP2Views.GateRow;
import com.aisdlc.console.domain.model.research.ResearchP2Views.PendingReview;
import com.aisdlc.console.domain.model.research.ResearchP2Views.TaskCounts;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** 看板投影的<b>唯讀</b>埠（JDBC；新查詢不改既有 {@code ReviewRequestRepositoryAdapter} 方法）。 */
public interface ResearchKanbanReadPort {

    /** 專案最新 run 的 id（無 run＝empty）。 */
    Optional<UUID> latestRunId(UUID consoleProjectId);

    TaskCounts taskCounts(UUID consoleProjectId);

    /** 專案所有 run 的 PENDING 待審，建立時間遞增。 */
    List<PendingReview> pendingReviews(UUID consoleProjectId);

    /** SCG4、SCG5、SCG6 各最近 {@code perGate} 筆（decidedAt 新到舊；先依 gate 再依時間）。 */
    List<GateRow> gateDecisions(UUID researchId, int perGate);

    /** 該專案最新事件時間（execution 事件帳 {@code execution_steps.timestamp} 的最大值；無則 empty）。 */
    Optional<OffsetDateTime> latestEventAt(UUID consoleProjectId);

    /** 該研究專案最新決定時間（任何 gate；無則 empty）。 */
    Optional<OffsetDateTime> latestDecisionAt(UUID researchId);
}
