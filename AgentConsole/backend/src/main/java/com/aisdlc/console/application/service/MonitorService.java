package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.MonitorUseCase;
import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.AlertRepository;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.MonitorQueries;
import com.aisdlc.console.application.port.out.MonitorQueries.ProjectCounts;
import com.aisdlc.console.application.port.out.MonitorQueries.StepFact;
import com.aisdlc.console.application.port.out.MonitorQueries.TokenFact;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ReviewRequestRepository;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.NotImplementedYetException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.model.execution.DagSnapshot.Node;
import com.aisdlc.console.domain.model.execution.ExecutionRun;
import com.aisdlc.console.domain.model.execution.ReviewRequest;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.GoalStatus;
import com.aisdlc.console.domain.model.monitor.Alert;
import com.aisdlc.console.domain.model.monitor.AlertSeverity;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.task.Task;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 專案監控（Phase 5；契約 §1.3、§3.8）。所有數字由 DB 事實列在純 Java 內算出（視窗 {@code W=[from,to)}、前一視窗
 * {@code W'=[from−(to−from), from)}），公式逐項對照契約 §3.8；日誌由既有資料衍生（不新增日誌表、不含引擎原始 stdout）。
 * 唯一不來自 DB 的數字是 {@code agentAvailability}（console-api 對 Bridge 的健康探測環）。
 */
@Service
@Transactional(readOnly = true)
public class MonitorService implements MonitorUseCase {

    private static final Duration DEFAULT_WINDOW = Duration.ofHours(24);
    private static final Duration MAX_WINDOW = Duration.ofDays(366);
    private static final Duration HOURLY_LIMIT = Duration.ofHours(48);
    private static final int MAX_BUCKETS = 1_000;
    private static final int MAX_ALERT_LIMIT = 200;
    private static final int MAX_LOG_SIZE = 200;
    private static final int MAX_KEYWORD = 200;
    private static final int TOP_DURATIONS = 10;
    private static final int RETRY_BUCKETS = 5;
    private static final List<String> TASK_STATUSES = List.of("PENDING", "QUEUED", "BLOCKED", "RUNNING", "VALIDATING",
            "COMPLETED", "FAILED", "ESCALATED", "PAUSED", "SKIPPED", "CANCELLED");
    private static final Set<String> LEVELS = Set.of("ALL", "INFO", "WARN", "ERROR");
    private static final DateTimeFormatter FILE_STAMP = DateTimeFormatter.ofPattern("yyyyMMdd-HHmm")
            .withZone(ZoneOffset.UTC);

    private final ProjectRepository projects;
    private final GoalRepository goals;
    private final TaskRepository tasks;
    private final ExecutionRunRepository runs;
    private final AlertRepository alerts;
    private final ReviewRequestRepository reviews;
    private final MonitorQueries queries;
    private final BridgeHealthMonitor health;
    private final AuditTrail audit;
    private final Clock clock;

    @SuppressWarnings("java:S107")
    public MonitorService(ProjectRepository projects, GoalRepository goals, TaskRepository tasks,
                          ExecutionRunRepository runs, AlertRepository alerts, ReviewRequestRepository reviews,
                          MonitorQueries queries, BridgeHealthMonitor health, AuditTrail audit, Clock clock) {
        this.projects = projects;
        this.goals = goals;
        this.tasks = tasks;
        this.runs = runs;
        this.alerts = alerts;
        this.reviews = reviews;
        this.queries = queries;
        this.health = health;
        this.audit = audit;
        this.clock = clock;
    }

    // ── 範圍與視窗 ─────────────────────────────────────────────────────────────

    /** 監控的資料範圍：專案（可限單一批次）的任務、目標與批次。 */
    private record Scope(Project project, ExecutionRun run, List<ExecutionRun> runs, List<Task> tasks,
                         List<Goal> goals, Map<UUID, String> goalNames) {

        UUID projectId() {
            return project.id();
        }

        UUID runId() {
            return run == null ? null : run.id();
        }

        Set<UUID> taskIds() {
            return tasks.stream().map(Task::id).collect(Collectors.toSet());
        }
    }

    private record Window(Instant from, Instant to) {

        Duration length() {
            return Duration.between(from, to);
        }
    }

    private Scope scope(UUID projectId, UUID runId) {
        Project project = projects.findById(projectId).orElseThrow(() -> NotFoundException.of("專案", projectId));
        ExecutionRun run = null;
        if (runId != null) {
            run = runs.findById(runId).filter(r -> r.projectId().equals(projectId))
                    .orElseThrow(() -> new NotFoundException("執行批次不存在或不屬於此專案：" + runId));
        }
        List<Task> allTasks = tasks.findByProjectId(projectId);
        List<Goal> allGoals = goals.findByProjectId(projectId);
        List<ExecutionRun> runScope;
        List<Task> taskScope = allTasks;
        List<Goal> goalScope = allGoals;
        if (run == null) {
            runScope = runs.findAllByProject(projectId);
        } else {
            runScope = List.of(run);
            Set<UUID> taskIds = run.dag().taskNodes().stream().map(Node::id).collect(Collectors.toSet());
            Set<UUID> goalIds = run.dag().goalNodes().stream().map(Node::id).collect(Collectors.toSet());
            taskScope = allTasks.stream().filter(t -> taskIds.contains(t.id())).toList();
            goalScope = allGoals.stream().filter(g -> goalIds.contains(g.id())).toList();
        }
        Map<UUID, String> goalNames = new HashMap<>();
        allGoals.forEach(g -> goalNames.put(g.id(), g.name()));
        return new Scope(project, run, runScope, taskScope, goalScope, goalNames);
    }

    private Window window(Query q) {
        Instant to = q.to() != null ? q.to() : clock.instant();
        Instant from = q.from() != null ? q.from() : to.minus(DEFAULT_WINDOW);
        if (!from.isBefore(to)) {
            throw invalidRange(from, to, "from 必須早於 to");
        }
        if (Duration.between(from, to).compareTo(MAX_WINDOW) > 0) {
            throw invalidRange(from, to, "時間視窗不可超過 366 天");
        }
        return new Window(from, to);
    }

    private static ValidationException invalidRange(Instant from, Instant to, String message) {
        return ValidationException.of("from", message, ErrorReasons.TIME_RANGE_INVALID,
                Map.of("from", from.toString(), "to", to.toString()));
    }

    private enum Bucket {
        HOUR(ChronoUnit.HOURS), DAY(ChronoUnit.DAYS);

        private final ChronoUnit unit;

        Bucket(ChronoUnit unit) {
            this.unit = unit;
        }

        Instant floor(Instant t) {
            return t.truncatedTo(unit);
        }

        /** 視窗 {@code [from, to)} 涵蓋的桶數。 */
        long span(Window w) {
            return unit.between(floor(w.from()), floor(w.to().minusNanos(1))) + 1;
        }
    }

    private Bucket bucket(Query q, Window w) {
        Bucket bucket;
        if (q.bucket() == null || q.bucket().isBlank()) {
            bucket = w.length().compareTo(HOURLY_LIMIT) <= 0 ? Bucket.HOUR : Bucket.DAY;
        } else {
            try {
                bucket = Bucket.valueOf(q.bucket().strip().toUpperCase(Locale.ROOT));
            } catch (IllegalArgumentException e) {
                throw ValidationException.of("bucket", "bucket 只能是 HOUR 或 DAY");
            }
        }
        long span = bucket.span(w);
        if (span > MAX_BUCKETS) {
            throw ValidationException.of("bucket", "視窗內桶數 " + span + " 超過 " + MAX_BUCKETS + "（請改用 DAY 或縮小視窗）",
                    ErrorReasons.TIME_RANGE_INVALID, Map.of("from", w.from().toString(), "to", w.to().toString(),
                            "bucket", bucket.name(), "buckets", span));
        }
        return bucket;
    }

    // ── KPI ────────────────────────────────────────────────────────────────────

    @Override
    public MetricsView metrics(Query query) {
        Scope s = scope(query.projectId(), query.runId());
        return compute(s, window(query));
    }

    private MetricsView compute(Scope s, Window w) {
        Instant prevFrom = w.from().minus(w.length());
        Set<UUID> inScope = s.taskIds();
        List<StepFact> steps = queries.steps(s.projectId(), s.runId(), null, w.to()).stream()
                .filter(f -> inScope.contains(f.taskId())).toList();
        List<TokenFact> tokens = queries.tokens(s.projectId(), s.runId(), prevFrom, w.to());

        long scopeSize = inScope.size();
        MetricValueView completion = ratio(pct(distinct(steps, "COMPLETED", null, w.to()).size(), scopeSize),
                pct(distinct(steps, "COMPLETED", null, w.from()).size(), scopeSize));
        Rates now = rates(steps, w.from(), w.to());
        Rates before = rates(steps, prevFrom, w.from());
        long tokensNow = tokens.stream().filter(t -> inWindow(t.ts(), w.from(), w.to())).mapToLong(TokenFact::delta).sum();
        long tokensBefore = tokens.stream().filter(t -> inWindow(t.ts(), prevFrom, w.from()))
                .mapToLong(TokenFact::delta).sum();

        long used = 0;
        long budget = 0;
        for (ExecutionRun r : s.runs()) {
            if (r.tokenBudget() != null && r.startedAt() != null && r.startedAt().isBefore(w.to())) {
                used += r.totalTokensUsed();
                budget += r.tokenBudget();
            }
        }
        Double usage = budget <= 0 ? null : StreamFrames.round1(used * 100.0 / budget);

        ProjectCounts counts = queries.projectCounts();
        long completedGoals = s.goals().stream().filter(g -> g.status() == GoalStatus.COMPLETED).count();
        Double availability = health.availability(w.from(), w.to()).map(StreamFrames::round1).orElse(null);

        return new MetricsView(s.projectId(), s.runId(), w.from(), w.to(), clock.instant(),
                single(pct(counts.completed(), counts.countable())), single(pct(completedGoals, s.goals().size())),
                completion, ratio(now.success(), before.success()),
                ratio(now.averageRetries(), before.averageRetries()), ratio(now.retry(), before.retry()),
                new MetricValueView(tokensNow, tokensBefore, tokensNow - tokensBefore), single(usage),
                ratio(averageDuration(s.tasks(), w.from(), w.to()), averageDuration(s.tasks(), prevFrom, w.from())),
                single(availability), budget <= 0 ? null : budget, statusDistribution(s.tasks()),
                topDurations(s, w), retryDistribution(s.tasks()));
    }

    private record Rates(Double success, Double retry, Double averageRetries) {
    }

    private static Rates rates(List<StepFact> steps, Instant from, Instant to) {
        long completed = distinct(steps, "COMPLETED", from, to).size();
        long failed = distinct(steps, "FAILED", from, to).size();
        long started = distinct(steps, "STARTED", from, to).size();
        long retried = distinct(steps, "RETRYING", from, to).size();
        long retryRows = steps.stream().filter(f -> "RETRYING".equals(f.status()) && inWindow(f.timestamp(), from, to))
                .count();
        return new Rates(pct(completed, completed + failed), pct(retried, started),
                started == 0 ? null : StreamFrames.round2((double) retryRows / started));
    }

    /** 視窗內有指定狀態步驟列的相異任務（{@code from} 為 null＝不設下界）。 */
    private static Set<UUID> distinct(List<StepFact> steps, String status, Instant from, Instant to) {
        Set<UUID> ids = new HashSet<>();
        for (StepFact f : steps) {
            if (status.equals(f.status()) && inWindow(f.timestamp(), from, to)) {
                ids.add(f.taskId());
            }
        }
        return ids;
    }

    private static boolean inWindow(Instant t, Instant from, Instant to) {
        return t != null && (from == null || !t.isBefore(from)) && t.isBefore(to);
    }

    private static Double pct(long numerator, long denominator) {
        return denominator <= 0 ? null : StreamFrames.round1(numerator * 100.0 / denominator);
    }

    private static Double averageDuration(List<Task> tasks, Instant from, Instant to) {
        double sum = 0;
        int count = 0;
        for (Task t : tasks) {
            if (t.startedAt() != null && t.completedAt() != null && inWindow(t.completedAt(), from, to)) {
                sum += seconds(t);
                count++;
            }
        }
        return count == 0 ? null : StreamFrames.round2(sum / count);
    }

    private static double seconds(Task t) {
        return Math.max(0, Duration.between(t.startedAt(), t.completedAt()).toMillis()) / 1000.0;
    }

    private static MetricValueView single(Double value) {
        return new MetricValueView(value, null, null);
    }

    private static MetricValueView ratio(Double value, Double previous) {
        Double delta = value != null && previous != null ? StreamFrames.round2(value - previous) : null;
        return new MetricValueView(value, previous, delta);
    }

    private static Map<String, Integer> statusDistribution(List<Task> tasks) {
        Map<String, Integer> counts = new LinkedHashMap<>();
        TASK_STATUSES.forEach(name -> counts.put(name, 0));
        tasks.forEach(t -> counts.merge(t.status().name(), 1, Integer::sum));
        return counts;
    }

    private List<TaskDurationView> topDurations(Scope s, Window w) {
        return s.tasks().stream()
                .filter(t -> t.startedAt() != null && t.completedAt() != null && inWindow(t.completedAt(), w.from(), w.to()))
                .sorted(Comparator.comparingDouble(MonitorService::seconds).reversed())
                .limit(TOP_DURATIONS)
                .map(t -> new TaskDurationView(t.id(), t.name(), s.goalNames().get(t.goalId()),
                        StreamFrames.round1(seconds(t))))
                .toList();
    }

    private static List<RetryBucketView> retryDistribution(List<Task> tasks) {
        int[] buckets = new int[RETRY_BUCKETS + 1];
        for (Task t : tasks) {
            buckets[Math.min(Math.max(t.retryCount(), 0), RETRY_BUCKETS)]++;
        }
        List<RetryBucketView> result = new ArrayList<>();
        for (int i = 0; i <= RETRY_BUCKETS; i++) {
            result.add(new RetryBucketView(i, buckets[i]));
        }
        return result;
    }

    // ── 趨勢 ───────────────────────────────────────────────────────────────────

    @Override
    public List<TokenTrendView> tokenTrend(Query query) {
        Scope s = scope(query.projectId(), query.runId());
        Window w = window(query);
        Bucket bucket = bucket(query, w);
        Map<Instant, List<TokenFact>> groups = new TreeMap<>();
        for (TokenFact f : queries.tokens(s.projectId(), s.runId(), w.from(), w.to())) {
            groups.computeIfAbsent(bucket.floor(f.ts()), k -> new ArrayList<>()).add(f);
        }
        List<TokenTrendView> points = new ArrayList<>();
        long cumulative = 0;
        for (Map.Entry<Instant, List<TokenFact>> entry : groups.entrySet()) {
            long sum = entry.getValue().stream().mapToLong(TokenFact::delta).sum();
            cumulative += sum;
            TokenFact latest = entry.getValue().stream().max(Comparator.comparing(TokenFact::runStartedAt,
                    Comparator.nullsFirst(Comparator.naturalOrder())).thenComparing(TokenFact::ts)).orElseThrow();
            points.add(new TokenTrendView(entry.getKey(), sum, cumulative, latest.budget()));
        }
        return points;
    }

    @Override
    public List<TaskTrendView> taskTrend(Query query) {
        Scope s = scope(query.projectId(), query.runId());
        Window w = window(query);
        Bucket bucket = bucket(query, w);
        Set<UUID> inScope = s.taskIds();
        Map<Instant, int[]> groups = new TreeMap<>();
        for (StepFact f : queries.steps(s.projectId(), s.runId(), w.from(), w.to())) {
            if (!inScope.contains(f.taskId())) {
                continue;
            }
            int[] counts = groups.computeIfAbsent(bucket.floor(f.timestamp()), k -> new int[4]);
            switch (f.status()) {
                case "STARTED" -> counts[0]++;
                case "COMPLETED" -> counts[1]++;
                case "FAILED" -> counts[2]++;
                case "RETRYING" -> counts[3]++;
                default -> { }
            }
        }
        return groups.entrySet().stream().map(e -> new TaskTrendView(e.getKey(), e.getValue()[0], e.getValue()[1],
                e.getValue()[2], e.getValue()[3])).toList();
    }

    // ── 告警 ───────────────────────────────────────────────────────────────────

    @Override
    public List<AlertView> alerts(UUID projectId, UUID runId, Boolean acknowledged, int limit) {
        scope(projectId, runId);
        if (limit < 1 || limit > MAX_ALERT_LIMIT) {
            throw ValidationException.of("limit", "limit 必須介於 1 到 " + MAX_ALERT_LIMIT);
        }
        return alerts.find(projectId, runId, acknowledged, limit).stream().map(MonitorService::view).toList();
    }

    private static AlertView view(Alert a) {
        return new AlertView(a.id(), a.projectId(), a.runId(), a.rule().name(), a.severity().name(), a.subject(),
                a.message(), a.createdAt(), a.acknowledged(), a.acknowledgedBy(), a.acknowledgedAt());
    }

    @Override
    @Transactional
    public void acknowledge(UUID alertId, String actor) {
        audit.note("monitor.acknowledge", "alert", alertId.toString());
        Alert alert = alerts.findById(alertId).orElseThrow(() -> new NotFoundException("告警不存在：" + alertId));
        if (!alert.acknowledged()) {
            alerts.acknowledge(alertId, actor, clock.instant());
        }
    }

    // ── 日誌（由既有資料衍生；契約 §3.8.3）───────────────────────────────────────

    @Override
    public PageResult<LogView> logs(LogQuery lq) {
        Query q = lq.window();
        Scope s = scope(q.projectId(), q.runId());
        String level = lq.level() == null ? "ALL" : lq.level().strip().toUpperCase(Locale.ROOT);
        Violations v = new Violations();
        if (!LEVELS.contains(level)) {
            v.add("level", "level 只能是 ALL、INFO、WARN、ERROR");
        }
        if (lq.q() != null && lq.q().length() > MAX_KEYWORD) {
            v.add("q", "q 最長 " + MAX_KEYWORD + " 字元");
        }
        if (lq.page() < 0) {
            v.add("page", "page 不可為負數");
        }
        if (lq.size() < 1 || lq.size() > MAX_LOG_SIZE) {
            v.add("size", "size 必須介於 1 到 " + MAX_LOG_SIZE);
        }
        v.throwIfAny();
        Window w = window(q);

        String needle = lq.q() == null || lq.q().isBlank() ? null : lq.q().strip().toLowerCase(Locale.ROOT);
        List<LogView> entries = derive(s, w, lq.taskId());
        Comparator<LogView> order = Comparator.comparing(LogView::timestamp).thenComparing(LogView::id);
        List<LogView> filtered = entries.stream()
                .filter(e -> "ALL".equals(level) || level.equals(e.level()))
                .filter(e -> needle == null || e.message().toLowerCase(Locale.ROOT).contains(needle))
                .sorted(lq.ascending() ? order : order.reversed()).toList();
        int from = (int) Math.min((long) lq.page() * lq.size(), filtered.size());
        int to = Math.min(from + lq.size(), filtered.size());
        return new PageResult<>(filtered.subList(from, to), lq.page(), lq.size(), filtered.size());
    }

    private List<LogView> derive(Scope s, Window w, UUID taskIdFilter) {
        List<LogView> entries = new ArrayList<>();
        Map<UUID, String> taskNames = new HashMap<>();
        s.tasks().forEach(t -> taskNames.put(t.id(), t.name()));
        Map<UUID, ExecutionRun> runById = new HashMap<>();
        s.runs().forEach(r -> runById.put(r.id(), r));

        for (StepFact f : queries.steps(s.projectId(), s.runId(), w.from(), w.to())) {
            if (taskIdFilter != null && !taskIdFilter.equals(f.taskId())) {
                continue;
            }
            String stepId = f.stepId() == null ? "-" : f.stepId();
            String name = taskNames.get(f.taskId());
            if (name == null) {
                ExecutionRun run = runById.get(f.runId());
                name = run == null ? stepId : run.dag().taskById(f.taskId()).map(Node::label).orElse(stepId);
            }
            entries.add(new LogView("step:" + f.id(), f.timestamp(), StreamFrames.stepLevel(f.status()), "STEP",
                    StreamFrames.stepMessage(f.status(), name, stepId, f.attempt() == null ? 1 : f.attempt(), null,
                            f.errorMessage()), f.runId(), f.taskId(), f.stepId()));
        }
        if (taskIdFilter != null) {
            return entries;
        }
        for (ExecutionRun r : s.runs()) {
            if (inWindow(r.startedAt(), w.from(), w.to())) {
                entries.add(new LogView("run:" + r.id() + ":started", r.startedAt(), "INFO", "RUN",
                        "Run #" + r.runNumber() + " 開始執行（自治等級 " + r.autonomyLevel() + "）", r.id(), null, null));
            }
            if (r.status().terminal() && inWindow(r.completedAt(), w.from(), w.to())) {
                entries.add(new LogView("run:" + r.id() + ":" + r.status().name(), r.completedAt(),
                        switch (r.status()) {
                            case COMPLETED -> "INFO";
                            case CANCELLED -> "WARN";
                            default -> "ERROR";
                        }, "RUN", "Run #" + r.runNumber() + switch (r.status()) {
                            case COMPLETED -> " 已完成";
                            case CANCELLED -> " 已取消";
                            default -> " 失敗";
                        }, r.id(), null, null));
            }
        }
        for (Alert a : alerts.find(s.projectId(), s.runId(), null, Integer.MAX_VALUE)) {
            if (inWindow(a.createdAt(), w.from(), w.to())) {
                entries.add(new LogView("alert:" + a.id(), a.createdAt(),
                        a.severity() == AlertSeverity.CRITICAL ? "ERROR" : "WARN", "ALERT", a.message(), a.runId(), null,
                        null));
            }
        }
        for (ReviewRequest r : reviews.findByProject(s.projectId(), s.runId())) {
            if (inWindow(r.requestedAt(), w.from(), w.to())) {
                entries.add(new LogView("review:" + r.id() + ":requested", r.requestedAt(), "INFO", "REVIEW",
                        "待審核：" + r.reason(), r.runId(), null, null));
            }
            if (r.decidedAt() != null && inWindow(r.decidedAt(), w.from(), w.to())) {
                entries.add(new LogView("review:" + r.id() + ":decided", r.decidedAt(), "INFO", "REVIEW",
                        "審核 " + r.status().name() + "：" + r.decidedBy(), r.runId(), null, null));
            }
        }
        return entries;
    }

    // ── 報表 ───────────────────────────────────────────────────────────────────

    @Override
    public Report report(Query query, String format) {
        Scope s = scope(query.projectId(), query.runId());
        String fmt = format == null || format.isBlank() ? "csv" : format.strip().toLowerCase(Locale.ROOT);
        if (!fmt.equals("csv") && !fmt.equals("pdf")) {
            throw ValidationException.of("format", "不支援的報表格式：" + format, ErrorReasons.REPORT_FORMAT_UNSUPPORTED,
                    Map.of("format", format, "supported", List.of("csv", "pdf")));
        }
        if (fmt.equals("pdf")) {
            throw new NotImplementedYetException("PDF 報表尚未提供（W5 之前一律回 501）", ErrorReasons.PDF_NOT_AVAILABLE);
        }
        Window w = window(query);
        MetricsView metrics = compute(s, w);
        Instant now = clock.instant();

        Set<UUID> inScope = s.taskIds();
        List<StepFact> steps = queries.steps(s.projectId(), s.runId(), null, w.to());
        List<ReportCsv.RunRow> runRows = new ArrayList<>();
        for (ExecutionRun r : s.runs()) {
            if (r.startedAt() != null && !r.startedAt().isBefore(w.to())) {
                continue;
            }
            Set<UUID> done = new HashSet<>();
            Set<UUID> failed = new HashSet<>();
            for (StepFact f : steps) {
                if (f.runId().equals(r.id())) {
                    if ("COMPLETED".equals(f.status())) {
                        done.add(f.taskId());
                    } else if ("FAILED".equals(f.status())) {
                        failed.add(f.taskId());
                    }
                }
            }
            Instant end = r.completedAt() != null ? r.completedAt() : now;
            long duration = r.startedAt() == null ? 0 : Math.max(0, Duration.between(r.startedAt(), end).getSeconds());
            runRows.add(new ReportCsv.RunRow(r.runNumber(), r.id(), r.status().name(), r.autonomyLevel(), r.startedAt(),
                    r.completedAt(), duration, r.totalTokensUsed(), r.tokenBudget(), r.dag().totalSteps(),
                    done.size(), failed.size()));
        }
        List<ReportCsv.TaskRow> taskRows = s.tasks().stream().filter(t -> inScope.contains(t.id()))
                .map(t -> new ReportCsv.TaskRow(s.goalNames().get(t.goalId()), t.name(), t.status().name(),
                        t.retryCount(), t.maxRetries(), t.actualTokens() == null ? 0 : t.actualTokens(), t.startedAt(),
                        t.completedAt(), t.startedAt() != null && t.completedAt() != null
                                ? Double.valueOf(StreamFrames.round1(seconds(t))) : null)).toList();
        List<ReportCsv.AlertRow> alertRows = alerts.find(s.projectId(), s.runId(), null, Integer.MAX_VALUE).stream()
                .filter(a -> inWindow(a.createdAt(), w.from(), w.to()))
                .sorted(Comparator.comparing(Alert::createdAt))
                .map(a -> new ReportCsv.AlertRow(a.createdAt(), a.severity().name(), a.rule().name(), a.subject(),
                        a.message(), a.acknowledged(), a.acknowledgedBy(), a.acknowledgedAt())).toList();
        byte[] content = ReportCsv.build(s.project().name(), w.from(), w.to(), s.runId(), metrics, runRows, taskRows,
                alertRows);
        String filename = "monitor-report-" + s.projectId().toString().substring(0, 8) + "-"
                + FILE_STAMP.format(now) + ".csv";
        return new Report(filename, "text/csv; charset=UTF-8", content);
    }
}
