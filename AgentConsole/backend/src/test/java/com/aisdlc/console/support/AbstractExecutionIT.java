package com.aisdlc.console.support;

import com.aisdlc.console.application.service.AlertThresholds;
import com.aisdlc.console.application.service.BridgeHealthMonitor;
import com.aisdlc.console.application.service.MonitorTicker;
import com.aisdlc.console.application.service.RunConsumers;
import com.aisdlc.console.support.ApiClient.Resp;
import com.aisdlc.minibridge.MiniBridge;
import com.aisdlc.minibridge.MiniRun;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.BooleanSupplier;

/**
 * 執行與監控整合測試的共同基底（契約 §5）：完整 Spring Boot context（<b>RANDOM_PORT</b> 的真 HTTP 伺服器，SSE 用得到；MockMvc 照常可用）
 * ＋ Testcontainers PostgreSQL 18 ＋ <b>迷你 Bridge</b>（{@link MiniBridge}：一個真的 HTTP／SSE 伺服器，事件序列由腳本旋鈕決定，
 * 並把狀態／Token／步驟列／checkpoint 鏡射進同一顆資料庫，與真 Bridge 同欄位）。
 *
 * <p>所有子類別共用同一個 context 與同一個迷你 Bridge；每個測試結束後停掉事件消費者、重設迷你 Bridge 與告警閾值快取，
 * 下一個測試（{@link AbstractApiIT} 的 {@code @BeforeEach}）才能安全地 TRUNCATE 資料。
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public abstract class AbstractExecutionIT extends AbstractApiIT {

    /** 整個 JVM 一個迷你 Bridge（隨機埠）；鏡射用的資料來源不經 Spring（Bridge 本來就是另一個行程）。 */
    protected static final MiniBridge MINI = MiniBridge.start(new JdbcTemplate(new DriverManagerDataSource(
            SharedPostgres.INSTANCE.getJdbcUrl(), SharedPostgres.INSTANCE.getUsername(),
            SharedPostgres.INSTANCE.getPassword())));

    @DynamicPropertySource
    static void miniBridge(DynamicPropertyRegistry registry) {
        registry.add("console.bridge.url", MINI::url);
    }

    @LocalServerPort
    protected int port;

    @Autowired
    protected RunConsumers consumers;
    @Autowired
    protected AlertThresholds thresholds;
    @Autowired
    protected BridgeHealthMonitor health;
    @Autowired
    protected MonitorTicker ticker;

    @BeforeEach
    void resetMiniBridge() {
        MINI.reset();
    }

    @AfterEach
    void stopEventConsumers() {
        consumers.stopAll();
        MINI.reset();
        thresholds.invalidate();
    }

    protected String baseUrl() {
        return "http://127.0.0.1:" + port;
    }

    // ── 夾具（契約 §5.0.3）──────────────────────────────────────────────────────

    /** PRJ-A：G1「基礎」含 T1「初始化」、T2「設定」；G2「核心」（依賴 G1）含 T3「實作」；任務 maxRetries=1。 */
    public record Fixture(String projectId, String g1, String g2, String t1, String t2, String t3) {

        public List<String> taskIds() {
            return List.of(t1, t2, t3);
        }
    }

    protected Fixture prjA(String name, int autonomyLevel) {
        String projectId = createProject(Map.of("name", name, "executionPath", "/e2e/" + name,
                "passCriteria", "- 全部通過", "autonomyLevel", autonomyLevel));
        String g1 = createGoal(projectId, "基礎");
        String g2 = createGoal(projectId, "核心", g1);
        String t1 = createFixtureTask(g1, "初始化", 1);
        String t2 = createFixtureTask(g1, "設定", 2);
        String t3 = createFixtureTask(g2, "實作", 3);
        return new Fixture(projectId, g1, g2, t1, t2, t3);
    }

    /** 任務 {@code description}＝{@code 請輸出 [T<n>_DONE]}、{@code expectedOutputRegex}＝{@code \[T<n>_DONE\]}、{@code maxRetries=1}。 */
    protected String createFixtureTask(String goalId, String name, int n) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("name", name);
        body.put("description", "請輸出 [T" + n + "_DONE]");
        body.put("passCriteria", "輸出含 [T" + n + "_DONE]");
        body.put("expectedOutputRegex", "\\[T" + n + "_DONE\\]");
        body.put("maxRetries", 1);
        Resp resp = api.post(operator(), "/api/v1/goals/" + goalId + "/tasks", body);
        if (resp.status() != 201) {
            throw new IllegalStateException("建立夾具任務失敗：" + resp.status() + " " + resp.body());
        }
        return resp.id();
    }

    // ── 啟動與等待 ──────────────────────────────────────────────────────────────

    protected Resp execute(String projectId, Map<String, Object> body) {
        return api.post(operator(), "/api/v1/projects/" + projectId + "/execute", body);
    }

    /** 啟動並要求 201，回 runId。 */
    protected String startRun(String projectId) {
        return startRun(projectId, Map.of());
    }

    protected String startRun(String projectId, Map<String, Object> body) {
        Resp resp = execute(projectId, body);
        if (resp.status() != 201) {
            throw new IllegalStateException("execute 失敗：" + resp.status() + " " + resp.body());
        }
        return resp.id();
    }

    protected MiniRun mini(String runId) {
        return MINI.run(UUID.fromString(runId));
    }

    /** 以 viewer 身分讀 {@code GET run}（不吃 operator 的額度；測試 profile 本來就關閉限流）。 */
    protected Resp getRun(String runId) {
        return api.get(viewer(), "/api/v1/executions/" + runId);
    }

    protected boolean awaitUntil(Duration timeout, BooleanSupplier condition) {
        long deadline = System.nanoTime() + timeout.toNanos();
        while (System.nanoTime() < deadline) {
            if (condition.getAsBoolean()) {
                return true;
            }
            sleep(40);
        }
        return condition.getAsBoolean();
    }

    /** DB 的批次狀態（六態）等於 {@code status}。 */
    protected boolean awaitRunStatus(String runId, String status) {
        return awaitUntil(Duration.ofSeconds(30), () -> status.equals(runStatus(runId)));
    }

    /** 批次狀態達 {@code status} 且事件消費者已把該批次已鏡射的事件處理完（console_last_seq ＝ Bridge 最後一則 seq）。 */
    protected boolean awaitProjected(String runId, String status) {
        return awaitUntil(Duration.ofSeconds(30), () -> {
            if (!status.equals(runStatus(runId))) {
                return false;
            }
            MiniRun run = mini(runId);
            return run != null && consoleLastSeq(runId) >= run.lastSeq();
        });
    }

    protected String runStatus(String runId) {
        List<String> rows = jdbc.queryForList("select status from console.execution_runs where id = ?", String.class,
                UUID.fromString(runId));
        return rows.isEmpty() ? null : rows.get(0);
    }

    protected int consoleLastSeq(String runId) {
        Integer seq = jdbc.queryForObject("select console_last_seq from console.execution_runs where id = ?",
                Integer.class, UUID.fromString(runId));
        return seq == null ? 0 : seq;
    }

    protected String taskStatus(String taskId) {
        return jdbc.queryForObject("select status from console.tasks where id = ?", String.class,
                UUID.fromString(taskId));
    }

    protected String goalStatus(String goalId) {
        return jdbc.queryForObject("select status from console.goals where id = ?", String.class,
                UUID.fromString(goalId));
    }

    protected String projectStatus(String projectId) {
        return jdbc.queryForObject("select status from console.projects where id = ?", String.class,
                UUID.fromString(projectId));
    }

    protected long countRuns(String projectId) {
        Long count = jdbc.queryForObject("select count(*) from console.execution_runs where project_id = ?",
                Long.class, UUID.fromString(projectId));
        return count == null ? 0 : count;
    }

    /** admin 改系統參數（非加密鍵）。 */
    protected void setting(String category, String key, String value) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("value", value);
        Resp resp = api.put(admin(), "/api/v1/settings/" + category + "/" + key, body);
        if (resp.status() != 200) {
            throw new IllegalStateException("設定 " + category + "." + key + " 失敗：" + resp.status() + " "
                    + resp.body());
        }
        thresholds.invalidate();
    }

    /**
     * 測試用假金鑰。刻意不以 {@code sk-} 開頭：根層 pre-commit 的機密掃描會把 openai／minimax 形態的字串當真值擋下 commit
     * （迷你 Bridge 不驗金鑰格式，真引擎的 {@code MinimaxClient} 建構時也只擋空字串）。
     */
    protected static final String FAKE_API_KEY = "your_api_key_here_test_fixture_0123456789";

    /** admin 設定 {@code model.apiKey}（加密參數須 {@code confirm=true}）；傳空字串＝清掉金鑰。 */
    protected void putApiKey(String value) {
        Resp resp = api.put(admin(), "/api/v1/settings/model/apiKey", Map.of("value", value, "confirm", true));
        if (resp.status() != 200) {
            throw new IllegalStateException("設定 model.apiKey 失敗：" + resp.status());
        }
    }

    /** 目前待決的審核項（來自 {@code GET run} 的 {@code pendingReviews}）。 */
    protected List<Map<String, Object>> pendingReviews(String runId) {
        return getRun(runId).read("$.data.pendingReviews");
    }

    /** 等到該批次出現一個待決審核項並回傳它的 id。 */
    protected String awaitPendingReview(String runId) {
        assertThatEventually(Duration.ofSeconds(30), () -> !pendingReviews(runId).isEmpty(),
                "批次 " + runId + " 一直沒有出現待決的審核項");
        return (String) pendingReviews(runId).get(0).get("id");
    }

    protected void assertThatEventually(Duration timeout, BooleanSupplier condition, String message) {
        if (!awaitUntil(timeout, condition)) {
            throw new AssertionError(message);
        }
    }

    protected Resp review(String runId, String reviewId, String decision) {
        return api.post(operator(), "/api/v1/executions/" + runId + "/review/" + reviewId,
                Map.of("decision", decision));
    }

    protected static void sleep(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
