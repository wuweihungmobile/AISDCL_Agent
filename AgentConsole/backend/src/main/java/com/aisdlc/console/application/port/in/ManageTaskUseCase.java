package com.aisdlc.console.application.port.in;

import com.aisdlc.console.domain.model.task.NewTask;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskUpdate;

import java.util.List;
import java.util.UUID;

/** 任務管理用例（PRD §5.1.3／§7.1.3）。找不到（含已軟刪除）一律 NotFoundException（404）。 */
public interface ManageTaskUseCase {

    Task create(UUID goalId, NewTask spec);

    List<Task> list(UUID goalId);

    Task get(UUID taskId);

    Task update(UUID taskId, TaskUpdate update);

    void delete(UUID taskId);

    /** 手動重試：只允許 FAILED／ESCALATED；retryCount+1、狀態轉 QUEUED。 */
    Task retry(UUID taskId);

    Task signoff(UUID taskId, String approver);
}
