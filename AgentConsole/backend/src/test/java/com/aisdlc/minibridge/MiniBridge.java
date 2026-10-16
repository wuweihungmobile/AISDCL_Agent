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
    /** {@code GET run} 快照的 {@code resources} 怎麼回（契約 §3.1.2）。預設 {@link ResourcesMode#SAMPLE}（對照真 Bridge）。 */
    public volatile ResourcesMode resourcesMode = ResourcesMode.SAMPLE;
    /** {@link ResourcesMode#SAMPLE} 回的樣本：欄位名與型別同真 Bridge 的 {@code ResourcesOut}；{@code sampled_at} 刻意用 {@code +00:00}（非 {@code Z}）以驗「原樣帶出」。 */
    public volatile Map<String, Object> resourcesSample = map("cpu_percent", 12.3, "rss_bytes", 361758720L,
            "process_count", 3, "sampled_at", "2026-10-16T03:21:45.123456+00:00");

    /** 快照的 {@code resources}：{@code SAMPLE}＝引擎行程樹存活（RUNNING／PAUSING／CANCELLING）時回一筆樣本、其餘（暫停、終態）回 null；{@code NULL}＝恆回 null；{@code OMIT}＝不帶這個鍵（舊版 Bridge）。 */
    public enum ResourcesMode {
        SAMPLE, NULL, OMIT
    }

    /** {@code GET /health/deep} 怎麼回（契約 §3.1.1；v1.4 起 console-api 的探測環預設打它，D-17）。預設 {@link DeepHealthMode#HEALTHY}。 */
    public volatile DeepHealthMode deepHealthMode = DeepHealthMode.HEALTHY;

    /**
     * 深度探針的三種回法。注意 {@code sdd} 檢查<b>只當資訊</b>（契約 §3.1.1；主控裁決 Q4）：它失敗時整體仍是 200，
     * 只有前四項（git／autoclaude／workspace／db）任一失敗才是 503 degraded。
     */
    public enum DeepHealthMode {
        /** 200，五項檢查都通過（{@code checks.sdd.ok=true}）。 */
        HEALTHY,
        /** 503 {@code degraded}：引擎自檢未通過（git 找不到），Bridge 行程本身是活的。 */
        DEGRADED,
        /** 200，但 {@code checks.sdd.ok=false}：SDD 目錄有問題不影響 Bridge 可用，所以不是 503。 */
        SDD_NOT_OK
    }

    /** {@code /sdd/version}、{@code /sdd/fsm}、{@code /sdd/fsm/{project}} 的夾具（契約 §3.1.3；測試直接改它的欄位）。 */
    public final Sdd sdd = new Sdd();

    /**
     * AISDLC_SDD 唯讀查詢的假資料（欄位名與型別同真 Bridge 的 {@code routers/sdd.py}：snake_case 的本文、404 {@code fsm_not_found}、
     * 422 {@code fsm_state_unreadable}、503 {@code sdd_unavailable}）。{@link #reset()} 回到預設夾具：兩個專案
     * {@code e2e-alpha}（IMPLEMENTATION、三筆重試歷史）與 {@code e2e-bravo}（HUMAN_PENDING、待人工 1 筆），另有兩個讀不動的檔名。
     */
    public static final class Sdd {

        /** true＝三個路由都回 503 {@code sdd_unavailable}（{@code SDD_ROOT} 無效）。 */
        public volatile boolean unavailable;
        /** 每個 {@code /sdd/*} 回應前先睡這麼久（毫秒）：用來造讀取逾時（console-api 的讀取逾時 3 秒）。 */
        public volatile long delayMillis;
        /** SDD 版本目錄名與 Bridge 看到的路徑（{@code /sdd/version}）。 */
        public volatile String latest = "AISDLC_SDD_v9.99";
        public volatile String root = "/sdd/AISDLC_SDD_v9.99";
        /** {@code /sdd/fsm} 的 {@code projects[]}（Bridge 形狀：project／source／current_state／updated_at）。 */
        public final List<Map<String, Object>> projects = new CopyOnWriteArrayList<>();
        /** {@code /sdd/fsm} 的 {@code errors[]}（讀不動的檔名）。 */
        public final List<String> errors = new CopyOnWriteArrayList<>();
        /** {@code /sdd/fsm/{project}} 的本文（Bridge 形狀，snake_case）。沒有的 project → 404 {@code fsm_not_found}。 */
        public final Map<String, Map<String, Object>> states = new ConcurrentHashMap<>();
        /** 這些 project 的 {@code /sdd/fsm/{project}} 回 422 {@code fsm_state_unreadable}（檔在、內容讀不動）。 */
        public final Set<String> unreadable = ConcurrentHashMap.newKeySet();

        Sdd() {
            reset();
        }

        public void reset() {
            unavailable = false;
            delayMillis = 0;
            latest = "AISDLC_SDD_v9.99";
            root = "/sdd/AISDLC_SDD_v9.99";
            projects.clear();
            errors.clear();
            states.clear();
            unreadable.clear();
            addProject("e2e-alpha", "IMPLEMENTATION", 2, "sid-alpha", "2026-10-16T01:02:03+00:00",
                    new SddRetry(3, map("gate", "PR_REVIEW", "attempt", 1, "date", "2026-10-16T00:30:00+00:00",
                            "failure_reason", "review rejected", "scg_gate", "SCG-4")),
                    map("count", 0, "items", List.of()));
            addProject("e2e-bravo", "HUMAN_PENDING", 1, "sid-bravo", "2026-10-15T08:00:00+00:00", new SddRetry(0, null),
                    map("count", 1, "items", List.of(map("entered_at", "2026-10-15T08:00:00+00:00",
                            "reminder_sent_at", null, "reminder_hours", 72, "escalation_hours", 168))));
            errors.add("FSM-STATE-e2e-broken.yaml");
            errors.add("FSM-STATE-bad name.yaml");
        }

        /** {@code retry_history} 投影：{@code count} 與最近一筆（已含 {@code gate} 欄）；沒有為 null。 */
        public record SddRetry(int count, Map<String, Object> last) {
        }

        /** 加一個專案：同時進 {@code /sdd/fsm} 的清單與 {@code /sdd/fsm/{project}} 的本文（五筆決策軌跡 r3～r7，舊→新）。 */
        public void addProject(String project, String currentState, int sprint, String sessionId, String updatedAt,
                               SddRetry retry, Map<String, Object> humanPending) {
            String source = "FSM-STATE-" + project + ".yaml";
            projects.add(map("project", project, "source", source, "current_state", currentState, "updated_at", updatedAt));
            List<Map<String, Object>> trace = new ArrayList<>();
            for (int i = 3; i <= 7; i++) {
                trace.add(map("ts", "2026-10-16T00:0" + i + ":00+00:00", "from", "S" + (i - 1), "to", "S" + i,
                        "reason", "r" + i, "spec_refs", List.of("SPEC-" + i), "agents_consulted", List.of("sa"),
                        "trigger", "auto"));
            }
            states.put(project, map("project", project, "current_state", currentState, "current_sprint", sprint,
                    "session_id", sessionId, "updated_at", updatedAt, "frozen_stages", List.of(map("stage", "SCG-0")),
                    "decision_trace", trace, "source", source, "human_pending", humanPending,
                    "retry_history", map("count", retry.count(), "last", retry.last()), "rtm_coverage", null));
        }
    }

    private final ConfigurableApplicationContext context;
    private final JdbcTemplate jdbc;
    private final int port;
    private final Map<UUID, MiniRun> runs = new ConcurrentHashMap<>();
    private final Map<String, UUID> locks = new ConcurrentHashMap<>();
    private final Map<String, ConcurrentLinkedQueue<Injected>> injected = new ConcurrentHashMap<>();
    private final List<String> requestLog = new CopyOnWriteArrayList<>();
    private final List<Traced> traced = new CopyOnWriteArrayList<>();
    private final AtomicInteger streamGeneration = new AtomicInteger();
    private final AtomicInteger openStreams = new AtomicInteger();

    /** 預先設好的錯誤回應（見 {@link #failNext}）。 */
    record Injected(int status, Map<String, Object> body) {
    }

    /** 迷你 Bridge 收到的一個請求（{@code METHOD /path}，不含查詢字串）與它帶的 {@code X-Trace-Id}（null＝沒帶；契約 §3.1.1）。 */
    public record Traced(String request, String traceId) {
    }

    private MiniBridge(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
        SpringApplication app = new SpringApplication(MiniBridgeApp.class);
        app.setWebApplicationType(WebApplicationType.SERVLET);
        // 🔴 不可設 logging.level.root：Logback 的狀態是整個 JVM 共用的，迷你 Bridge 的 SpringApplication 啟動時會把 root 壓成 WARN，
        // 其後在同一個測試 JVM 裡跑的 Console 整合測試就一律看不到 INFO（例如 AuditLogIT 靠 INFO 的 audit 日誌行斷言）；
        // 誰先在哪個 fork 啟動取決於測試排程，所以症狀是「新增一支測試類別就讓不相干的測試變紅」。只壓迷你 Bridge 自己的套件。
        app.setDefaultProperties(Map.of("spring.main.banner-mode", "off", "logging.level.com.aisdlc.minibridge", "WARN",
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

    /** 每個收到的請求與它帶的 {@code X-Trace-Id}（依到達順序；SSE 串流請求在建立連線時就記下）。 */
    public List<Traced> traced() {
        return List.copyOf(traced);
    }

    public void reset() {
        runs.values().forEach(MiniRun::shutdown);
        runs.clear();
        locks.clear();
        injected.clear();
        requestLog.clear();
        traced.clear();
        failStepIds.clear();
        stepMillis = 40;
        tokensPerAttempt = 1240;
        manualSteps = false;
        completionDelayMillis = 0;
        keepAliveMillis = 500;
        resourcesMode = ResourcesMode.SAMPLE;
        deepHealthMode = DeepHealthMode.HEALTHY;
        sdd.reset();
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

    void recordTrace(String request, String traceId) {
        traced.add(new Traced(request, traceId));
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
