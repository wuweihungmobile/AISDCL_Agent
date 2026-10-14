package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ManageTaskUseCase;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.model.task.NewTask;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskUpdate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.util.List;
import java.util.UUID;

/** 任務管理用例實作（PRD §5.1.3）。NFR-SEC-03 的消毒與狀態機都收在 domain 的 Task。 */
@Service
@Transactional
public class TaskService implements ManageTaskUseCase {

    private final GoalRepository goals;
    private final TaskRepository tasks;
    private final Clock clock;

    public TaskService(GoalRepository goals, TaskRepository tasks, Clock clock) {
        this.goals = goals;
        this.tasks = tasks;
        this.clock = clock;
    }

    @Override
    public Task create(UUID goalId, NewTask spec) {
        goals.findById(goalId).orElseThrow(() -> NotFoundException.of("目標", goalId));
        Task task = Task.create(goalId, spec, tasks.nextSortOrder(goalId), clock.instant());
        return tasks.save(task);
    }

    @Override
    @Transactional(readOnly = true)
    public List<Task> list(UUID goalId) {
        goals.findById(goalId).orElseThrow(() -> NotFoundException.of("目標", goalId));
        return tasks.findByGoalId(goalId);
    }

    @Override
    @Transactional(readOnly = true)
    public Task get(UUID taskId) {
        return load(taskId);
    }

    @Override
    public Task update(UUID taskId, TaskUpdate update) {
        Task task = load(taskId);
        task.update(update, clock.instant());
        return tasks.save(task);
    }

    @Override
    public void delete(UUID taskId) {
        Task task = load(taskId);
        task.softDelete(clock.instant());
        tasks.save(task);
    }

    @Override
    public Task retry(UUID taskId) {
        Task task = load(taskId);
        task.retry(clock.instant());
        return tasks.save(task);
    }

    @Override
    public Task signoff(UUID taskId, String approver) {
        Task task = load(taskId);
        task.signoff(approver, clock.instant());
        return tasks.save(task);
    }

    private Task load(UUID taskId) {
        return tasks.findById(taskId).orElseThrow(() -> NotFoundException.of("任務", taskId));
    }
}
