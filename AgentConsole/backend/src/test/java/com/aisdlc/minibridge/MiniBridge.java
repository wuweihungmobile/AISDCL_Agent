package com.aisdlc.minibridge;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.web.server.servlet.context.ServletWebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import tools.jackson.databind.json.JsonMapper;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.Semaphore;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * 測試用迷你 Engine Bridge（W3-B2 任務書：「Spring Boot 迷你 Bridge」）：一個真的 HTTP 伺服器（Spring MVC＋嵌入式 Tomcat，
 * 隨機埠），行為對照真 Bridge 的 {@code runner.py}／{@code routers/autoclaude.py}，但事件序列由腳本旋鈕決定：
 * 每步 STARTED → token → COMPLETED、{@link #failStepIds} 讓步驟重試後失敗（ESCALATION）、pause 在下一個步驟邊界生效
 * （被中止的下一步不發 STARTED）、{@code :resume}／restore 從 checkpoint 續跑、stop 取消。
 *
 * <p>和真 Bridge 一樣「事件先、欄位後」，並把狀態、Token、步驟列與 checkpoint 鏡射進同一顆 PostgreSQL
 * （{@code console.execution_runs}／{@code execution_steps}／{@code checkpoints}）——Console 的 REST 端點讀的就是這些。
 * 不是 WireMock：它依請求本文建 run、依腳本發事件，能驗投影、審核閘「提前一步」、重連回補、補償刪除與告警。
 *
 * <p>放在 {@code com.aisdlc.minibridge}（不在 {@code com.aisdlc.console} 之下），所以不會被 Console 的元件掃描撈進去。
 */
public final class MiniBridge implements AutoCloseable {

    static final JsonMapper JSON = JsonMapper.builder().build();

    /** 每步耗時（毫秒）；{@link #manualSteps} 為 true 時不用。 */
    public volatile long stepMillis = 40;
    /** 每個 attempt 的 Token（mock claude 固定 1,240）。 */
    public volatile int tokensPerAttempt = 1240;
    /** true＝每一步開始前要等 {@link MiniRun#release(int)} 放行（決定性控制時序）。 */
    public volatile boolean manualSteps = false;
    /** 讓這些 step_id 的步驟重試用盡後失敗（引擎升級 ESCALATION、run FAILED）。 */
    public final Set<String> failStepIds = ConcurrentHashMap.newKeySet();
    /** 每個成功步驟在「token 事件之後、COMPLETED 事件之前」的延遲（毫秒；預設 0＝不延遲，見 {@link MiniRun}）。 */
    public volatile long completionDelayMillis = 0;
    /** SSE 在多久沒有事件時送一行 keep-alive 註解（毫秒）。 */
    public volatile long keepAliveMillis = 500;
    public volatile String bridgeInstance = "mini-bridge";

    private final ConfigurableApplicationContext context;
    private final JdbcTemplate jdbc;
    private final int port;
    private final Map<UUID, MiniRun> runs = new ConcurrentHashMap<>();
    private final Map<String, UUID> locks = new ConcurrentHashMap<>();
    private final Map<String, ConcurrentLinkedQueue<Injected>> injected = new ConcurrentHashMap<>();
    private final List<String> requestLog = new CopyOnWriteArrayList<>();
    private final AtomicInteger streamGeneration = new AtomicInteger();
    private final AtomicInteger openStreams = new AtomicInteger();

    /** 預先設好的錯誤回應（見 {@link #failNext}）。 */
    record Injected(int status, Map<String, Object> body) {
    }

    private MiniBridge(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
        SpringApplication app = new SpringApplication(MiniBridgeApp.class);
        app.setWebApplicationType(WebApplicationType.SERVLET);
        app.setDefaultProperties(Map.of("spring.main.banner-mode", "off", "logging.level.root", "WARN",
                "spring.main.lazy-initialization", "false", "server.tomcat.threads.max", "64"));
        app.addInitializers(ctx -> ctx.getBeanFactory().registerSingleton("miniBridge", this));
        // 🔴 命令列引數的優先序高於 classpath 上 application.yml 的 server.port: 8080；放在 default properties 會被 yml 蓋掉，
        // 兩個測試 JVM fork（maxParallelForks = 2）就會搶同一個 8080。config.name 指向不存在的檔，迷你 Bridge 不載入 Console 的設定。
        this.context = app.run("--server.port=0", "--spring.config.name=minibridge");
        this.port = ((ServletWebServerApplicationContext) context).getWebServer().getPort();
    }

    public static MiniBridge start(JdbcTemplate jdbcOrNull) {
        return new MiniBridge(jdbcOrNull);
    }

    public String url() {
        return "http://127.0.0.1:" + port;
    }

    public int port() {
        return port;
    }

    @Override
    public void close() {
        runs.values().forEach(MiniRun::shutdown);
        context.close();
    }

    // ── 測試旋鈕與觀測 ─────────────────────────────────────────────────────────

    public MiniRun run(UUID id) {
        return runs.get(id);
    }

    public List<String> requests() {
        return List.copyOf(requestLog);
    }

    public long countRequests(String prefix) {
        return requestLog.stream().filter(r -> r.startsWith(prefix)).count();
    }

    public void reset() {
        runs.values().forEach(MiniRun::shutdown);
        runs.clear();
        locks.clear();
        injected.clear();
        requestLog.clear();
        failStepIds.clear();
        stepMillis = 40;
        tokensPerAttempt = 1240;
        manualSteps = false;
        completionDelayMillis = 0;
        keepAliveMillis = 500;
        dropStreams();
    }

    /**
     * 下一次符合 {@code route} 的請求回指定狀態與本文，只用一次。路由名：{@code start}（建立 run）、{@code pause}、
     * {@code resume}、{@code stop}、{@code restore}、{@code getRun}、{@code events}、{@code stream}。
     */
    public void failNext(String route, int status, Map<String, Object> body) {
        injected.computeIfAbsent(route, k -> new ConcurrentLinkedQueue<>()).add(new Injected(status, body));
    }

    /** 粗暴切斷目前所有開著的 SSE 連線（模擬網路中斷；Console 的消費者應退避重連並補齊）。 */
    public void dropStreams() {
        streamGeneration.incrementAndGet();
    }

    public int openStreams() {
        return openStreams.get();
    }

    // ── 控制器用的內部介面 ──────────────────────────────────────────────────────

    int generation() {
        return streamGeneration.get();
    }

    void streamOpened() {
        openStreams.incrementAndGet();
    }

    void streamClosed() {
        openStreams.decrementAndGet();
    }

    void record(String line) {
        requestLog.add(line);
    }

    Injected takeInjected(String route) {
        ConcurrentLinkedQueue<Injected> queue = injected.get(route);
        return queue == null ? null : queue.poll();
    }

    Map<UUID, MiniRun> runs() {
        return runs;
    }

    JdbcTemplate jdbc() {
        return jdbc;
    }

    /** 取鎖：同 project＋path 只能有一個進行中的 run；回傳目前持有者（沒有衝突回 null）。 */
    synchronized UUID acquireLock(String key, UUID runId) {
        UUID holder = locks.get(key);
        if (holder != null && !holder.equals(runId)) {
            return holder;
        }
        locks.put(key, runId);
        return null;
    }

    synchronized boolean holdsLock(String key, UUID runId) {
        return runId.equals(locks.get(key));
    }

    synchronized void releaseLock(String key, UUID runId) {
        locks.remove(key, runId);
    }

    static String now() {
        return OffsetDateTime.now(ZoneOffset.UTC).toString();
    }

    static OffsetDateTime odt(Instant instant) {
        return OffsetDateTime.ofInstant(instant, ZoneOffset.UTC);
    }

    static Map<String, Object> map(Object... keyValues) {
        Map<String, Object> map = new LinkedHashMap<>();
        for (int i = 0; i < keyValues.length; i += 2) {
            map.put((String) keyValues[i], keyValues[i + 1]);
        }
        return map;
    }

    /** 把 playbook 的 tasks 轉成腳本步驟。 */
    @SuppressWarnings("unchecked")
    static List<MiniRun.Step> stepsOf(Map<String, Object> playbook) {
        List<MiniRun.Step> steps = new ArrayList<>();
        Object tasks = playbook == null ? null : playbook.get("tasks");
        if (tasks instanceof List<?> list) {
            for (Object item : list) {
                Map<String, Object> task = (Map<String, Object>) item;
                Object retries = task.get("max_retries");
                steps.add(new MiniRun.Step((String) task.get("step_id"), (String) task.get("name"),
                        (String) task.get("goal_task_id"), retries instanceof Number n ? n.intValue() : 3));
            }
        }
        return steps;
    }

    static Map<String, Object> copy(Map<String, Object> source) {
        return new HashMap<>(source);
    }

    Semaphore newGate() {
        return new Semaphore(0);
    }
}
