package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/** 任務儲存埠。查詢一律排除已軟刪除的任務。 */
public interface TaskRepository {

    Task save(Task task);

    Optional<Task> findById(UUID id);

    /** 目標下全部任務，依 sortOrder、createdAt 排序。 */
    List<Task> findByGoalId(UUID goalId);

    /** 目標內下一個 sortOrder（現有最大值＋1；沒有任務為 0）。 */
    int nextSortOrder(UUID goalId);

    boolean existsByGoalIdAndStatus(UUID goalId, TaskStatus status);

    /** 軟刪除目標下全部任務；回傳受影響筆數。 */
    int softDeleteByGoalId(UUID goalId, Instant now);

    /** 軟刪除專案下全部任務（經由其目標）；回傳受影響筆數。 */
    int softDeleteByProjectId(UUID projectId, Instant now);
}
