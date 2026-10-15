package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.CurrentStepView;
import com.aisdlc.console.application.port.in.ExecutionStreamUseCase;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeEvent;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AlertRepository;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.ExecutionStepRepository;
import com.aisdlc.console.application.port.out.ExecutionStepRepository.StepRow;
import com.aisdlc.console.application.port.out.ReviewRequestRepository;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.application.port.out.TokenSampleRepository;
import com.aisdlc.console.application.port.out.TokenSampleRepository.Sample;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.DagSnapshot;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.RunStatus;
import com.aisdlc.console.domain.model.monitor.Alert;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.model.task.TaskStatus;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 前端 SSE 的開啟、重播與去重（契約 §2；{@code API-SSE-01～03}）。
 *
 * <p>{@code /logs}：{@code Last-Event-ID} 之後的事件＝Bridge {@code GET …/events}（逐頁；Bridge 環 5,000 則、更舊的自動掃
 * {@code events.jsonl}，所以任何歷史位置都可重播）套用 §2.7 的對映，加上 Console 自產的審核項與告警（依
 * {@code event_seq／event_sub}），合併後依 {@code (seq, n)} 排序；沒有 {@code Last-Event-ID} 時先重播最後 {@code tail} 則。
 * {@code /metrics}：三則皆為狀態快照（latest-wins）→ <b>收斂快照</b>：每次連線先送各一則最新快照，id 互異且嚴格遞增
 * （{@code <S>.1} progress、{@code <S>.2} token、{@code <S>.3} metric），之後才是即時事件。
 * Bridge 暫時不可達：串流<b>不關閉</b>，送一則不帶 id 的 {@code BRIDGE_UNREACHABLE} 告警；Bridge 回 404 → {@code BRIDGE_RUN_UNKNOWN} 後關閉。
 */
@Service
public class StreamService implements ExecutionStreamUseCase {

    private static final Logger LOG = LoggerFactory.getLogger(StreamService.class);
    private static final Pattern LAST_EVENT_ID = Pattern.compile("^([0-9]+)(?:\\.([0-9]+))?$");
    private static final int DEFAULT_TAIL = 200;
    private static final int MAX_TAIL = 5_000;
    private static final int PAGE = 500;

    private final ExecutionRunRepository runs;
    private final ExecutionStepRepository steps;
    private final TaskRepository tasks;
    private final TokenSampleRepository samples;
    private final ReviewRequestRepository reviews;
    private final AlertRepository alerts;
    private final AgentBridge bridge;
    private final RunEventHub hub;
    private final RunRegistry registry;
    private final RuntimeSettings settings;
    private final TransactionTemplate readTx;
    private final Clock clock;

    @SuppressWarnings("java:S107")
    public StreamService(ExecutionRunRepository runs, ExecutionStepRepository steps, TaskRepository tasks,
                         TokenSampleRepository samples, ReviewRequestRepository reviews, AlertRepository alerts,
                         AgentBridge bridge, RunEventHub hub, RunRegistry registry, RuntimeSettings settings,
                         PlatformTransactionManager transactions, Clock clock) {
        this.runs = runs;
        this.steps = steps;
        this.tasks = tasks;
        this.samples = samples;
        this.reviews = reviews;
        this.alerts = alerts;
        this.bridge = bridge;
        this.hub = hub;
        this.registry = registry;
        this.settings = settings;
        this.readTx = new TransactionTemplate(transactions);
        this.readTx.setReadOnly(true);
        this.clock = clock;
    }

    @Override
    public StreamSettings settings() {
        return new StreamSettings(Duration.ofSeconds(Math.max(1, settings.sseKeepAliveSeconds())),
                settings.sseQueueSize());
    }

    @Override
    public Optional<Subscription> open(UUID runId, Kind kind, String lastEventId, Integer tail, Sink sink) {
        ExecutionRun first = readTx.execute(status -> runs.findById(runId)
                .orElseThrow(() -> NotFoundException.of("執行批次", runId)));
        Long lastKey = parseLastEventId(lastEventId);
        StreamSettings cfg = settings();
        StreamConnection connection = new StreamConnection(runId, kind, sink, cfg.queueSize(), cfg.keepAlive(), hub);
        hub.subscribe(runId, connection);
        boolean keep = false;
        try {
            Replay replay = kind == Kind.LOGS ? logsReplay(first, lastKey, tail) : metricsReplay(first, lastKey);
            if (replay.noContent()) {
                return Optional.empty();
            }
            connection.startWriter();
            connection.deliverReplay(replay.frames(), replay.closeAfter());
            keep = true;
            return Optional.of(connection);
        } finally {
            if (!keep) {
                connection.close();
            }
        }
    }

    // ── Last-Event-ID ──────────────────────────────────────────────────────────

    /** 解析成 {@code orderOf(seq, n)}；格式不合視為沒有帶（不回 400，契約 §2.3 第 1 點）。 */
    static Long parseLastEventId(String raw) {
        if (raw == null) {
            return null;
        }
        Matcher m = LAST_EVENT_ID.matcher(raw.strip());
        if (!m.matches()) {
            return null;
        }
        try {
            int seq = Integer.parseInt(m.group(1));
            int sub = m.group(2) == null ? 0 : Integer.parseInt(m.group(2));
            return Frame.orderOf(seq, sub);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private record Replay(List<Frame> frames, boolean closeAfter, boolean noContent) {

        static Replay none() {
            return new Replay(List.of(), true, true);
        }
    }

    // ── /logs ──────────────────────────────────────────────────────────────────

    private Replay logsReplay(ExecutionRun run, Long lastKey, Integer tail) {
        UUID runId = run.id();
        int afterSeq = lastKey == null ? 0 : (int) (lastKey / 1_000_000L);
        int afterSub = lastKey == null ? 0 : (int) (lastKey % 1_000_000L);
        List<Frame> frames = new ArrayList<>();
        try {
            ReplayMapper mapper = new ReplayMapper(run);
            int cursor = afterSeq;
            while (true) {
                List<BridgeEvent> page = bridge.listEvents(runId, cursor, PAGE);
                if (page.isEmpty()) {
                    break;
                }
                page.forEach(e -> mapper.map(e, frames));
                cursor = page.get(page.size() - 1).seq();
                if (page.size() < PAGE) {
                    break;
                }
            }
        } catch (BridgeRejectedException e) {
            if (e.status() == 404) {
                frames.add(StreamFrames.connectionAlert(run.consoleLastSeq(), "BRIDGE_RUN_UNKNOWN",
                        "Engine Bridge 已無此執行（工作區可能已清除）", clock.instant()));
                return new Replay(frames, true, false);
            }
            LOG.warn("重播批次 {} 的 Bridge 事件被拒：{} {}", runId, e.status(), e.reason());
        } catch (UpstreamException e) {
            frames.add(StreamFrames.connectionAlert(run.consoleLastSeq(), "BRIDGE_UNREACHABLE",
                    "Engine Bridge 暫時無法連線，將自動重試", clock.instant()));
        }
        readTx.executeWithoutResult(status -> {
            reviews.findAnchoredAfter(runId, afterSeq, afterSub).forEach(r -> frames.add(
                    StreamFrames.review(r, StreamFrames.reviewView(r, run.dag()))));
            alerts.findAnchoredAfter(runId, afterSeq, afterSub).forEach(a -> frames.add(
                    StreamFrames.consoleAlert(a, a.createdAt() == null ? clock.instant() : a.createdAt())));
        });
        List<Frame> keyed = new ArrayList<>(frames.stream().filter(Frame::hasId)
                .filter(f -> lastKey == null || f.order() > lastKey).toList());
        List<Frame> unkeyed = frames.stream().filter(f -> !f.hasId()).toList();
        keyed.sort(Comparator.comparingLong(Frame::order));
        if (lastKey == null) {
            int wanted = tail == null ? DEFAULT_TAIL : Math.max(0, Math.min(tail, MAX_TAIL));
            keyed = new ArrayList<>(keyed.subList(Math.max(0, keyed.size() - wanted), keyed.size()));
        }
        keyed.addAll(unkeyed);
        // 重連一個已終態的 run：重播集合為空 → 204；否則送完重播後關閉（契約 §2.4）
        ExecutionRun current = readTx.execute(status -> runs.findById(runId).orElse(run));
        boolean terminal = current.status().terminal();
        if (terminal && keyed.isEmpty()) {
            return Replay.none();
        }
        return new Replay(keyed, terminal, false);
    }

    /** 把 Bridge 事件（REST 重播形狀，已正規化成 {@link BridgeEvent}）對映成 {@code /logs} 的框架（契約 §2.7）。 */
    private final class ReplayMapper {

        private final ExecutionRun run;
        /** Bridge 告警事件的持久化鏡像（{@code event_sub=0}），以 Bridge seq 為鍵：重播時補上 {@code alertId}／{@code rule}。 */
        private final Map<Integer, Alert> engineAlerts = new HashMap<>();
        private String currentStepId;

        ReplayMapper(ExecutionRun run) {
            this.run = run;
            readTx.executeWithoutResult(status -> alerts.findByRun(run.id()).stream().filter(a -> a.eventSub() == 0)
                    .forEach(a -> engineAlerts.put(a.eventSeq(), a)));
        }

        void map(BridgeEvent e, List<Frame> out) {
            DagSnapshot dag = run.dag();
            switch (e.event()) {
                case "status" -> BridgeStatus.parse(e.text("status")).ifPresent(st -> out.add(
                        StreamFrames.statusChange(e, st, e.text("reason"))));
                case "log" -> {
                    Node node = currentStepId == null ? null : dag.taskByStepId(currentStepId).orElse(null);
                    out.add(StreamFrames.engineLog(e, node, currentStepId));
                }
                case "step" -> mapStep(e, dag, out);
                case "alert" -> {
                    String code = e.text("code");
                    Alert persisted = "ESCALATION".equals(code) || "TOKEN_HALT".equals(code)
                            ? engineAlerts.get(e.seq()) : null;
                    out.add(StreamFrames.engineAlert(e, persisted, persisted == null ? null : persisted.subject()));
                }
                default -> { }
            }
        }

        private void mapStep(BridgeEvent e, DagSnapshot dag, List<Frame> out) {
            String stepId = e.text("step_id");
            String status = e.text("status") == null ? "" : e.text("status");
            int position = e.integer("step_number") == null ? 0 : e.integer("step_number");
            int attempt = e.integer("attempt") == null ? 1 : e.integer("attempt");
            Node node = dag.taskByStepId(stepId).orElse(null);
            Long tokens = null;
            String error = null;
            if (node != null && "COMPLETED".equals(status)) {
                tokens = readTx.execute(s -> samples.sumDeltaForTask(run.id(), node.id()));
            }
            if (node != null && "FAILED".equals(status)) {
                error = readTx.execute(s -> steps.findLatest(run.id(), stepId, "FAILED")
                        .map(StepRow::errorMessage).orElse(null));
            }
            out.add(StreamFrames.stepLog(e, node, stepId, status, position, attempt, tokens, error));
            if ("STARTED".equals(status) || "RETRYING".equals(status)) {
                currentStepId = stepId;
            } else if ("COMPLETED".equals(status) || "FAILED".equals(status)) {
                currentStepId = null;
            }
        }
    }

    // ── /metrics ───────────────────────────────────────────────────────────────

    private Replay metricsReplay(ExecutionRun run, Long lastKey) {
        ExecutionRun current = readTx.execute(status -> runs.findById(run.id()).orElse(run));
        int s = current.consoleLastSeq();
        boolean terminal = current.status().terminal();
        if (terminal && lastKey != null && lastKey >= Frame.orderOf(s, 3)) {
            return Replay.none();
        }
        List<Frame> frames = readTx.execute(status -> snapshot(current, s));
        return new Replay(frames, terminal, false);
    }

    /** 收斂快照：{@code <S>.1} progress、{@code <S>.2} token、{@code <S>.3} metric。 */
    private List<Frame> snapshot(ExecutionRun run, int s) {
        Instant now = clock.instant();
        Map<UUID, Task> taskMap = new HashMap<>();
        tasks.findByIds(run.dag().taskNodes().stream().map(Node::id).toList()).forEach(t -> taskMap.put(t.id(), t));
        int completed = (int) run.dag().taskNodes().stream().map(n -> taskMap.get(n.id()))
                .filter(t -> t != null && t.status() == TaskStatus.COMPLETED).count();
        int failed = (int) run.dag().taskNodes().stream().map(n -> taskMap.get(n.id()))
                .filter(t -> t != null && (t.status() == TaskStatus.FAILED || t.status() == TaskStatus.ESCALATED))
                .count();
        RunRegistry.Runtime rt = registry.runtime(run.id());
        BridgeStatus status = rt.bridgeStatus != null ? rt.bridgeStatus : bridgeStatusOf(run.status());
        CurrentStepView current = null;
        if (rt.currentStepId != null) {
            Node node = run.dag().taskByStepId(rt.currentStepId).orElse(null);
            if (node != null) {
                current = new CurrentStepView(node.stepId(), node.sequence(), node.id(), node.label(), node.goalId(),
                        Math.max(rt.currentAttempt, 1));
            }
        }
        Sample last = samples.latest(run.id()).orElse(null);
        long tokens = last == null ? run.totalTokensUsed() : last.tokensUsed();
        List<StepRow> rows = steps.findAllByRun(run.id());
        Set<UUID> started = new HashSet<>();
        Set<UUID> retried = new HashSet<>();
        int retryEvents = 0;
        for (StepRow row : rows) {
            if ("STARTED".equals(row.status())) {
                started.add(row.taskId());
            } else if ("RETRYING".equals(row.status())) {
                retried.add(row.taskId());
                retryEvents++;
            }
        }
        double average = started.isEmpty() ? 0.0 : StreamFrames.round2((double) retryEvents / started.size());
        long elapsed = run.startedAt() == null ? 0 : Math.max(0, Duration.between(run.startedAt(),
                run.completedAt() != null && run.status().terminal() ? run.completedAt() : now).getSeconds());
        String ts = now.toString();
        List<Frame> frames = new ArrayList<>();
        frames.add(StreamFrames.progress(s, 1, ts, status, completed, run.dag().totalSteps(), current));
        frames.add(StreamFrames.token(s, 2, ts, tokens, last == null ? tokens : last.delta(),
                last == null || last.contextPct() == null ? 0.0 : last.contextPct(), run.tokenBudget(),
                last == null ? null : last.taskId()));
        frames.add(StreamFrames.metric(s, 3, ts, completed, failed, run.dag().totalSteps(), retried.size(), average,
                tokens, run.tokenBudget(), elapsed));
        return frames;
    }

    private static BridgeStatus bridgeStatusOf(RunStatus status) {
        return switch (status) {
            case INITIALIZING -> BridgeStatus.INITIALIZING;
            case RUNNING -> BridgeStatus.RUNNING;
            case PAUSED -> BridgeStatus.PAUSED;
            case COMPLETED -> BridgeStatus.COMPLETED;
            case FAILED -> BridgeStatus.FAILED;
            case CANCELLED -> BridgeStatus.CANCELLED;
        };
    }
}
