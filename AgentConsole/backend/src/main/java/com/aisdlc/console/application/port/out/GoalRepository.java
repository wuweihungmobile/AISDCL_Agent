package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.goal.Goal;

import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/** 目標儲存埠。查詢一律排除已軟刪除的目標；依賴邊只在兩端目標都未軟刪時才算數。 */
public interface GoalRepository {

    /** 一個目標底下的任務計數。 */
    record TaskCounts(int total, int completed) {
        public static final TaskCounts ZERO = new TaskCounts(0, 0);
    }

    /** 儲存目標；同時把 goal.dependsOn() 同步成 goal_dependencies 的邊（差異寫入）。 */
    Goal save(Goal goal);

    Optional<Goal> findById(UUID id);

    /** 專案下全部目標，依 sortOrder、createdAt 排序；dependsOn 已填入。 */
    List<Goal> findByProjectId(UUID projectId);

    /** 專案內的依賴圖：每個未軟刪目標 → 它的（未軟刪）前置依賴 id 集合。 */
    Map<UUID, Set<UUID>> dependencyGraph(UUID projectId);

    Map<UUID, TaskCounts> taskCountsFor(Collection<UUID> goalIds);

    /** 專案內下一個 sortOrder（現有最大值＋1；沒有目標為 0）。 */
    int nextSortOrder(UUID projectId);

    /** 軟刪除專案下全部目標；回傳受影響筆數。 */
    int softDeleteByProjectId(UUID projectId, Instant now);
}
