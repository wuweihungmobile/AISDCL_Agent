package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import com.aisdlc.console.application.port.out.AlertRepository;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.ReviewRequestRepository;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.aisdlc.console.domain.model.monitor.Alert;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import com.aisdlc.console.domain.service.AlertRules;
import com.aisdlc.console.domain.service.AlertRules.Candidate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * 純時間型的告警規則（契約 §3.7；由 30 秒排程 tick 評估，事件型規則在 {@link RunEventProcessor}）：
 * {@code AGENT_UNRESPONSIVE}（逾 {@code monitor.alertAgentTimeoutSec} 無事件<b>且</b>最近一次健康探測失敗）、
 * {@code TASK_DURATION_EXCEEDED}（RUNNING 任務的已執行時間逾 {@code agent.taskTimeout × monitor.alertTaskDurationMultiplier}）。
 * 同一規則＋對象在被確認前不重複產生（DB 的 partial unique index 兜底），新增的告警即時發給前端。
 */
@Component
public class TimeRuleEvaluator {

    private static final Logger LOG = LoggerFactory.getLogger(TimeRuleEvaluator.class);

    private final ExecutionRunRepository runs;
    private final TaskRepository tasks;
    private final AlertRepository alerts;
    private final ReviewRequestRepository reviews;
    private final AlertThresholds thresholds;
    private final BridgeHealthMonitor health;
    private final RunRegistry registry;
    private final RunEventHub hub;
    private final TransactionTemplate tx;
    private final Clock clock;

    @SuppressWarnings("java:S107")
    public TimeRuleEvaluator(ExecutionRunRepository runs, TaskRepository tasks, AlertRepository alerts,
                             ReviewRequestRepository reviews, AlertThresholds thresholds, BridgeHealthMonitor health,
                             RunRegistry registry, RunEventHub hub, PlatformTransactionManager transactions,
                             Clock clock) {
        this.runs = runs;
        this.tasks = tasks;
        this.alerts = alerts;
        this.reviews = reviews;
        this.thresholds = thresholds;
        this.health = health;
        this.registry = registry;
        this.hub = hub;
        this.tx = new TransactionTemplate(transactions);
        this.clock = clock;
    }

    /** 評估所有進行中（DB 狀態 RUNNING；含 PAUSING／CANCELLING）的批次；回傳新增的告警數。 */
    public int evaluateAll() {
        int created = 0;
        for (ExecutionRun run : runs.findByStatuses(List.of(RunStatus.RUNNING))) {
            try {
                created += evaluate(run.id());
            } catch (RuntimeException e) {
                LOG.warn("評估批次 {} 的時間型告警失敗：{}", run.id(), e.toString());
            }
        }
        return created;
    }

    /** 評估單一批次（持該 run 的鎖，與事件處理互斥）。 */
    public int evaluate(UUID runId) {
        return registry.locked(runId, () -> {
            List<Frame> frames = new ArrayList<>();
            Integer created = tx.execute(status -> {
                Optional<ExecutionRun> found = runs.findById(runId);
                if (found.isEmpty() || found.get().status() != RunStatus.RUNNING) {
                    return 0;
                }
                ExecutionRun run = found.get();
                int count = 0;
                Instant now = clock.instant();
                AlertThresholds.Values th = thresholds.current();
                RunRegistry.Runtime rt = registry.runtime(runId);

                Instant lastEvent = rt.lastEventAt != null ? rt.lastEventAt : run.startedAt();
                long silent = lastEvent == null ? 0 : Duration.between(lastEvent, now).getSeconds();
                Optional<Candidate> unresponsive = AlertRules.agentUnresponsive(runId, silent, th.agentTimeoutSec(),
                        health.lastProbeFailed());
                if (unresponsive.isPresent() && emit(run, unresponsive.get(), now, frames)) {
                    count++;
                }
                for (Node node : run.dag().taskNodes()) {
                    Optional<Task> task = tasks.findById(node.id());
                    if (task.isEmpty() || task.get().status() != TaskStatus.RUNNING || task.get().startedAt() == null) {
                        continue;
                    }
                    long elapsed = Duration.between(task.get().startedAt(), now).getSeconds();
                    Optional<Candidate> slow = AlertRules.taskDurationExceeded(task.get().id(), task.get().name(),
                            elapsed, th.taskTimeoutSec(), th.durationMultiplier());
                    if (slow.isPresent() && emit(run, slow.get(), now, frames)) {
                        count++;
                    }
                }
                return count;
            });
            hub.publish(runId, frames);
            return created == null ? 0 : created;
        });
    }

    private boolean emit(ExecutionRun run, Candidate candidate, Instant now, List<Frame> frames) {
        int anchor = run.consoleLastSeq();
        int sub = reviews.nextEventSub(run.id(), anchor);
        Alert alert = new Alert(UUID.randomUUID(), run.projectId(), run.id(), candidate.rule(), candidate.severity(),
                candidate.subject(), candidate.message(), now, false, null, null, anchor, sub);
        Optional<Alert> inserted = alerts.insertIfAbsent(alert);
        inserted.ifPresent(a -> frames.add(StreamFrames.consoleAlert(a, now)));
        return inserted.isPresent();
    }
}
