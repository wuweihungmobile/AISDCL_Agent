package com.aisdlc.minibridge;

import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

import static com.aisdlc.minibridge.MiniBridge.map;
import static com.aisdlc.minibridge.MiniBridge.now;
import static com.aisdlc.minibridge.MiniBridge.odt;

/**
 * 迷你 Bridge 的一個 run：事件環、狀態、checkpoint 與「引擎」的腳本化執行（見 {@link MiniBridge}）。
 * 狀態名與欄位沿用真 Bridge（八態、{@code status／step／token／alert／log} 事件的欄位）。
 */
public final class MiniRun {

    /** playbook 的一個步驟。 */
    record Step(String stepId, String name, String goalTaskId, int maxRetries) {
    }

    /** 一個歷史快照（{@code step_idx}＝還原後下一個步驟的 0 起算位置）。 */
    record Checkpoint(UUID id, String name, Instant createdAt, int stepIdx, String stepId, List<String> completed) {
    }

    private final MiniBridge bridge;
    final UUID id;
    final String project;
    final String executionPath;
    final String lockKey;
    final List<Step> steps;
    /** 建立請求本文（測試驗 env、config_overrides、playbook 用）。 */
    public final Map<String, Object> request;
    final Semaphore gate = new Semaphore(0);
    final List<Checkpoint> checkpoints = new ArrayList<>();
    private final List<Map<String, Object>> events = new ArrayList<>();
    private final List<String> completed = new ArrayList<>();

    private volatile String status = "INITIALIZING";
    private volatile String reason = "";
    private volatile boolean pauseRequested;
    private volatile boolean stopRequested;
    private volatile boolean shuttingDown;
    private volatile Thread worker;
    private int seq;
    private long tokens;
    private int nextIdx;
    private String currentStep;
    private Integer currentStepNumber;
    private int attempt;
    private Instant startedAt;
    private Instant completedAt;

    MiniRun(MiniBridge bridge, UUID id, String project, String executionPath, String lockKey, List<Step> steps,
            Map<String, Object> request) {
        this.bridge = bridge;
        this.id = id;
        this.project = project;
        this.executionPath = executionPath;
        this.lockKey = lockKey;
        this.steps = List.copyOf(steps);
        this.request = request;
    }

    // ── 測試用觀測／控制 ───────────────────────────────────────────────────────

    public String status() {
        return status;
    }

    public String reason() {
        return reason;
    }

    public synchronized long tokens() {
        return tokens;
    }

    public synchronized int lastSeq() {
        return seq;
    }

    /** 全部事件（含 {@code event} 鍵的信封，與 events.jsonl 同形）。 */
    public synchronized List<Map<String, Object>> events() {
        return new ArrayList<>(events);
    }

    /**
     * 目前所有 checkpoint 的 id（建立順序）：測試要 restore 時用。{@code AgentBridge.listCheckpoints} 已刪除（它在 {@code src/main} 沒有呼叫者，
     * Console 的斷點清單與審核 RETRY 都走資料庫；完整性審查 I-07），測試改直接問迷你 Bridge 自己建了哪些 checkpoint。
     */
    public synchronized List<UUID> checkpointIds() {
        return checkpoints.stream().map(Checkpoint::id).toList();
    }

    /** 目前所有 checkpoint 的名稱（建立順序，例 {@code after-G1-T1}）。 */
    public synchronized List<String> checkpointNames() {
        return checkpoints.stream().map(Checkpoint::name).toList();
    }

    /** 目前所有 checkpoint 的 {@code step_idx}（建立順序）。 */
    public synchronized List<Integer> checkpointStepIndexes() {
        return checkpoints.stream().map(Checkpoint::stepIdx).toList();
    }

    /** 放行 manual 模式下的 {@code n} 個步驟。 */
    public void release(int n) {
        gate.release(n);
    }

    /** 等到狀態達到 {@code expected}（逾時回 false）。 */
    public boolean awaitStatus(String expected, Duration timeout) {
        long deadline = System.nanoTime() + timeout.toNanos();
        while (System.nanoTime() < deadline) {
            if (expected.equals(status)) {
                return true;
            }
            sleep(20);
        }
        return expected.equals(status);
    }

    /** 直接在事件環裡塞一則自訂事件（例：自訂 alert、或測試「不認得的事件」）。 */
    public synchronized Map<String, Object> inject(String event, Map<String, Object> payload) {
        return emit(event, payload);
    }

    void shutdown() {
        shuttingDown = true;
        stopRequested = true;
        gate.release(1000);
        Thread thread = worker;
        if (thread != null) {
            thread.interrupt();
        }
    }

    // ── 事件環 ──────────────────────────────────────────────────────────────────

    synchronized Map<String, Object> emit(String event, Map<String, Object> payload) {
        seq++;
        Map<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("seq", seq);
        envelope.put("ts", now());
        envelope.put("event", event);
        envelope.putAll(payload);
        events.add(envelope);
        notifyAll();
        return envelope;
    }

    synchronized List<Map<String, Object>> eventsAfter(int after, int limit) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> e : events) {
            if (((Number) e.get("seq")).intValue() > after) {
                out.add(e);
                if (out.size() >= limit) {
                    break;
                }
            }
        }
        return out;
    }

    /** 等到有 {@code after} 之後的新事件或逾時；回傳目前是否為終態且游標已追上。 */
    synchronized void awaitEvents(int after, long millis) throws InterruptedException {
        if (seq <= after) {
            wait(millis);
        }
    }

    boolean terminal() {
        return "COMPLETED".equals(status) || "FAILED".equals(status) || "CANCELLED".equals(status);
    }

    private void setStatus(String newStatus, String why) {
        emit("status", map("status", newStatus, "reason", why));
        status = newStatus;
        reason = why;
        mirrorStatus();
    }

    synchronized Map<String, Object> snapshot() {
        Map<String, Object> snap = new LinkedHashMap<>();
        snap.put("run_id", id.toString());
        snap.put("status", status);
        snap.put("pid", terminal() || "PAUSED".equals(status) ? null : 4242);
        snap.put("started_at", startedAt == null ? null : odt(startedAt).toString());
        snap.put("completed_at", completedAt == null ? null : odt(completedAt).toString());
        snap.put("exit_code", terminal() ? ("COMPLETED".equals(status) ? 0 : 1) : null);
        snap.put("current_step", currentStep);
        snap.put("completed_steps", completed.size());
        snap.put("total_steps", steps.size());
        snap.put("tokens_used", tokens);
        snap.put("last_event_seq", seq);
        snap.put("reason", reason);
        snap.put("project", project);
        snap.put("execution_path", executionPath);
        snap.put("bridge_instance", bridge.bridgeInstance);
        snap.put("current_step_number", currentStepNumber);
        snap.put("attempt", attempt);
        // 資源取樣（契約 §3.1.2）：真 Bridge 只在引擎行程樹存活時回值（暫停會終止整棵樹、終態沒有行程），其餘為 null
        switch (bridge.resourcesMode) {
            case OMIT -> { }
            case NULL -> snap.put("resources", null);
            case SAMPLE -> snap.put("resources", processTreeAlive() ? new LinkedHashMap<>(bridge.resourcesSample) : null);
            default -> throw new IllegalStateException("未知的 resourcesMode：" + bridge.resourcesMode);
        }
        return snap;
    }

    /** 引擎行程樹是否存活：RUNNING、PAUSING、CANCELLING（INITIALIZING 尚未 spawn；PAUSED 與終態沒有行程）。 */
    private boolean processTreeAlive() {
        return "RUNNING".equals(status) || "PAUSING".equals(status) || "CANCELLING".equals(status);
    }

    // ── 對外操作（與真 Bridge 同前置狀態、同錯誤）───────────────────────────────

    void start() {
        startedAt = Instant.now();
        setStatus("INITIALIZING", "run 已建立，準備啟動引擎");
        spawn();
    }

    private void spawn() {
        setStatus("RUNNING", "引擎已啟動（pid=4242，第 1 次 spawn）");
        Thread thread = Thread.ofVirtual().name("mini-run-" + id).unstarted(this::play);
        worker = thread;
        thread.start();
    }

    /** @return 新狀態；前置狀態不符回 empty（呼叫端回 409 invalid_state）。 */
    synchronized Optional<String> pause() {
        if ("PAUSING".equals(status)) {
            return Optional.of("PAUSING");
        }
        if (!"RUNNING".equals(status)) {
            return Optional.empty();
        }
        pauseRequested = true;
        setStatus("PAUSING", "已要求暫停：下一個步驟邊界生效");
        return Optional.of("PAUSING");
    }

    synchronized Optional<String> stop() {
        if ("CANCELLING".equals(status)) {
            return Optional.of("CANCELLING");
        }
        if ("RUNNING".equals(status) || "PAUSING".equals(status)) {
            stopRequested = true;
            gate.release(1000);
            setStatus("CANCELLING", "已要求取消：終止引擎行程樹");
            return Optional.of("CANCELLING");
        }
        if ("PAUSED".equals(status)) {
            setStatus("CANCELLING", "已要求取消（暫停中，無行程）");
            completedAt = Instant.now();
            setStatus("CANCELLED", "使用者取消");
            bridge.releaseLock(lockKey, id);
            return Optional.of("CANCELLING");
        }
        return Optional.empty();
    }

    synchronized Optional<String> resume() {
        if (!"PAUSED".equals(status)) {
            return Optional.empty();
        }
        pauseRequested = false;
        spawn();
        return Optional.of("RUNNING");
    }

    /** @return empty＝前置狀態不符；否則 Optional 內是錯誤原因（null＝成功），由控制器轉成 HTTP。 */
    synchronized Optional<String> restore(UUID checkpointId) {
        if (!"PAUSED".equals(status) && !terminal()) {
            return Optional.empty();
        }
        Checkpoint checkpoint = checkpoints.stream().filter(c -> c.id().equals(checkpointId)).findFirst().orElse(null);
        if (checkpoint == null) {
            return Optional.of("checkpoint_not_found");
        }
        if (terminal()) {
            UUID holder = bridge.acquireLock(lockKey, id);
            if (holder != null) {
                return Optional.of("advisory_lock_held:" + holder);
            }
        }
        completed.clear();
        completed.addAll(checkpoint.completed());
        nextIdx = checkpoint.stepIdx();
        completedAt = null;
        pauseRequested = false;
        stopRequested = false;
        currentStep = null;
        currentStepNumber = null;
        attempt = 0;
        mirrorCompletedAt();
        emit("alert", map("level", "info", "code", "RESTORE", "message", "從 checkpoint「" + checkpoint.name()
                + "」（step_idx=" + checkpoint.stepIdx() + "）還原並續跑", "checkpoint_id", checkpointId.toString()));
        spawn();
        return Optional.of("");
    }

    // ── 「引擎」的腳本化執行 ─────────────────────────────────────────────────────

    private void play() {
        try {
            int spawnCompleted = 0;
            while (nextIdx < steps.size()) {
                if (stopRequested) {
                    finishCancelled();
                    return;
                }
                if (pauseRequested && spawnCompleted >= 1) {
                    finishPause();
                    return;
                }
                Step step = steps.get(nextIdx);
                int position = nextIdx + 1;
                currentStep = step.stepId();
                currentStepNumber = position;
                attempt = 1;
                emitStep("STARTED", step, position, 1, null);
                if (bridge.manualSteps) {
                    // 步驟「執行中」直到測試放行：pause／stop 在這段時間內到達，才會在步驟邊界／當場生效
                    gate.acquire();
                } else {
                    pause(bridge.stepMillis);
                }
                if (stopRequested) {
                    finishCancelled();
                    return;
                }
                boolean fails = bridge.failStepIds.contains(step.stepId());
                int attempts = fails ? step.maxRetries() + 1 : 1;
                for (int a = 1; a <= attempts; a++) {
                    synchronized (this) {
                        tokens += bridge.tokensPerAttempt;
                    }
                    emit("token", map("pct", 0.6, "tokens_used", tokens()));
                    mirrorTokens();
                    if (fails && a < attempts) {
                        attempt = a + 1;
                        emitStep("RETRYING", step, position, a + 1, null);
                        pause(Math.min(bridge.stepMillis, 20));
                    }
                }
                if (fails) {
                    String detail = "任務「" + step.name() + "」重試 " + step.maxRetries() + " 次仍失敗";
                    emitStep("FAILED", step, position, attempts, detail);
                    emit("alert", map("level", "error", "code", "ESCALATION", "message", detail, "step_id",
                            step.stepId()));
                    completedAt = Instant.now();
                    currentStep = null;
                    currentStepNumber = null;
                    attempt = 0;
                    setStatus("FAILED", "引擎升級（ESCALATION）：" + detail);
                    bridge.releaseLock(lockKey, id);
                    return;
                }
                if (bridge.completionDelayMillis > 0) {
                    // 真引擎的 token 事件先於同一步的 COMPLETED；這段延遲讓「Console 對 token 事件的反應（例如 :pause）」
                    // 決定性地趕在這一步完成之前到達，暫停就落在這一步之後的邊界（沒有它，誰先到取決於毫秒級的競速）
                    pause(bridge.completionDelayMillis);
                }
                completed.add(step.stepId());
                currentStep = null;
                currentStepNumber = null;
                attempt = 0;
                emitStep("COMPLETED", step, position, 1, null);
                recordCheckpoint(step);
                nextIdx++;
                spawnCompleted++;
            }
            completedAt = Instant.now();
            setStatus("COMPLETED", "引擎正常結束");
            bridge.releaseLock(lockKey, id);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private void finishPause() {
        String next = nextIdx < steps.size() ? steps.get(nextIdx).stepId() : "（已無下一步）";
        currentStep = null;
        currentStepNumber = null;
        attempt = 0;
        setStatus("PAUSED", "在步驟邊界暫停（已完成 " + completed.size() + " 步，續跑點：" + next + "）");
    }

    private void finishCancelled() {
        completedAt = Instant.now();
        if (shuttingDown) {
            return;
        }
        setStatus("CANCELLED", "使用者取消");
        bridge.releaseLock(lockKey, id);
    }

    private void emitStep(String stepStatus, Step step, int position, int attemptNo, String error) {
        Map<String, Object> envelope = emit("step", map("step_id", step.stepId(), "step_number", position,
                "status", stepStatus, "attempt", attemptNo, "name", step.name(), "total_steps", steps.size()));
        mirrorStep(((Number) envelope.get("seq")).intValue(), step, position, stepStatus, attemptNo, error);
    }

    private void recordCheckpoint(Step step) {
        String nextId = nextIdx + 1 < steps.size() ? steps.get(nextIdx + 1).stepId() : "";
        Checkpoint checkpoint = new Checkpoint(UUID.randomUUID(), "after-" + step.stepId(), Instant.now(), nextIdx + 1,
                nextId, List.copyOf(completed));
        synchronized (this) {
            checkpoints.add(checkpoint);
        }
        mirrorCheckpoint(checkpoint);
    }

    private static void pause(long millis) throws InterruptedException {
        Thread.sleep(millis);
    }

    private static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    // ── 鏡射進 PostgreSQL（沒給 JdbcTemplate 就略過）────────────────────────────

    private void mirrorStatus() {
        if (bridge.jdbc() == null) {
            return;
        }
        String dbStatus = switch (status) {
            case "PAUSING", "CANCELLING" -> "RUNNING";
            default -> status;
        };
        try {
            bridge.jdbc().update("update console.execution_runs set status = ?, bridge_instance = ?, "
                    + "total_tokens_used = ?, completed_at = ? where id = ?", dbStatus, bridge.bridgeInstance, tokens(),
                    completedAt == null ? null : odt(completedAt), id);
        } catch (RuntimeException e) {
            // 與真 Bridge 相同：鏡射是 best-effort
        }
    }

    private void mirrorTokens() {
        if (bridge.jdbc() == null) {
            return;
        }
        try {
            bridge.jdbc().update("update console.execution_runs set total_tokens_used = ? where id = ?", tokens(), id);
        } catch (RuntimeException e) {
            // best-effort
        }
    }

    private void mirrorCompletedAt() {
        if (bridge.jdbc() == null) {
            return;
        }
        try {
            bridge.jdbc().update("update console.execution_runs set completed_at = null where id = ?", id);
        } catch (RuntimeException e) {
            // best-effort
        }
    }

    private void mirrorStep(int eventSeq, Step step, int position, String stepStatus, int attemptNo, String error) {
        if (bridge.jdbc() == null || step.goalTaskId() == null) {
            return;
        }
        try {
            bridge.jdbc().update("insert into console.execution_steps (id, run_id, task_id, step_number, action, "
                    + "status, input, error_message) values (?, ?, ?, ?, ?, ?, ?::jsonb, ?)", UUID.randomUUID(), id,
                    UUID.fromString(step.goalTaskId()), eventSeq, step.stepId() + ": " + step.name(), stepStatus,
                    "{\"step_id\":\"" + step.stepId() + "\",\"position\":" + position + ",\"attempt\":" + attemptNo + "}",
                    error);
        } catch (RuntimeException e) {
            // best-effort
        }
    }

    private void mirrorCheckpoint(Checkpoint checkpoint) {
        if (bridge.jdbc() == null) {
            return;
        }
        try {
            StringBuilder ids = new StringBuilder("[");
            for (int i = 0; i < checkpoint.completed().size(); i++) {
                ids.append(i == 0 ? "" : ",").append('"').append(checkpoint.completed().get(i)).append('"');
            }
            ids.append(']');
            String snapshot = "{\"step_idx\":" + checkpoint.stepIdx() + ",\"step_id\":\"" + checkpoint.stepId()
                    + "\",\"total_steps\":" + steps.size() + ",\"completed_step_ids\":" + ids + "}";
            bridge.jdbc().update("insert into console.checkpoints (id, run_id, name, state_snapshot, created_at, "
                    + "is_automatic) values (?, ?, ?, ?::jsonb, ?, true)", checkpoint.id(), id, checkpoint.name(),
                    snapshot, odt(checkpoint.createdAt()));
        } catch (RuntimeException e) {
            // best-effort
        }
    }

    /** 等待時鐘小幫手（給控制器的 keep-alive 迴圈）。 */
    static void await(long millis) throws InterruptedException {
        TimeUnit.MILLISECONDS.sleep(millis);
    }

    /** 給測試的快捷：把 DB 的 execution_runs 列刪掉（模擬 Console 補償刪除之後的狀態）。 */
    Map<String, Object> debug() {
        return new LinkedHashMap<>(snapshot());
    }
}
