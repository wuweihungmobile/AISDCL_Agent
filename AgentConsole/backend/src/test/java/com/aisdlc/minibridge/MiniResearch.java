package com.aisdlc.minibridge;

import org.springframework.jdbc.core.JdbcTemplate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static com.aisdlc.minibridge.MiniBridge.JSON;
import static com.aisdlc.minibridge.MiniBridge.map;

/**
 * 迷你 Bridge 的研究面（ResearchToPRD P0；TCS-ResearchToPRD-P0 §5：{@code MiniBridge} 研究擴充）。端點形狀與錯誤封包 {@code {code, reason, details?}} 對照真 Bridge 的
 * {@code routers/research.py}（PKG-BR-A）：寫入端點先驗權杖（{@link #writeToken}：預設 {@link #TOKEN}；null＝Bridge 沒設＝503 {@code research_write_disabled}；
 * 其他＝不符＝403 {@code research_write_forbidden}）再驗資料庫（{@link #db}＝false＝503 {@code research_requires_db}）；{@code GET /research/capabilities} 不受影響。
 * 迷你 Bridge 自己是 Bridge——<b>研究表的唯一寫入者</b>：建立專案、存 PRD、封存與復原都直接以 JDBC 寫進同一顆資料庫，console-api 之後讀得到。
 *
 * <p>預設行為對照契約 §2.2；測試以 {@link #next}／{@link #always} 針對某個路由鍵排入腳本回應（單次或持續）：{@code capabilities}、{@code allowlist.list}、
 * {@code allowlist.add}、{@code allowlist.patch}、{@code create}、{@code stage}（或 {@code stage:<名稱>}）、{@code prd}、{@code approve}、{@code return}、
 * {@code cancel}、{@code reconcile}、{@code archive}、{@code restore}、{@code reinit}（換世代另有 {@code reinit:next}）。每個收到的請求記在 {@link #calls}
 * （方法、原始路徑、權杖、追蹤碼、請求本文），供「請求數」、「approver 只取 JWT subject」、「POST 不重試」的斷言。
 */
public final class MiniResearch {

    /** 與 application-test.yml 的 {@code console.bridge.research-write-token} 同值（≥32 字元、含 mock）。 */
    public static final String TOKEN = "mock-bridge-research-write-token-for-tests-0123456789";
    /** 部署基底的 FETCH 清單（PRD：arXiv、Semantic Scholar、GitHub API、Stack Exchange API 四組主機）。 */
    public static final List<String> FETCH_HOSTS = List.of("export.arxiv.org", "api.semanticscholar.org", "api.github.com", "api.stackexchange.com");

    /** Bridge 端的寫入權杖：預設 {@link #TOKEN}；{@code null}＝沒設；其他值＝與 console-api 附的不符。 */
    public volatile String writeToken = TOKEN;
    /** false＝Bridge 沒有 DSN：寫入與 allowlist 讀取回 503 {@code research_requires_db}（能力探針仍 200、{@code db:false}）。 */
    public volatile boolean db = true;
    public volatile boolean webLayerEnabled = true;
    public volatile String mode = "local";
    /** 每個研究請求回應前先睡這麼久（毫秒）：造讀取逾時。 */
    public volatile long delayMillis;
    /** true＝{@code stages/*:start} 的兩個並發請求以閘門同步：第一個回 202、第二個回 409 {@code stage_conflict}（AT-960-4-5）。 */
    public volatile boolean stageRace;

    /** 每個收到的研究請求（依到達順序）。 */
    public final List<Call> calls = new CopyOnWriteArrayList<>();
    /** ADMIN 新增的 allowlist 條目（Bridge 形狀，snake_case）。 */
    public final List<Map<String, Object>> allowlist = new CopyOnWriteArrayList<>();

    private final Map<String, Queue<Reply>> scripted = new ConcurrentHashMap<>();
    private final Map<String, Reply> sticky = new ConcurrentHashMap<>();
    private final AtomicInteger raceArrivals = new AtomicInteger();
    private volatile CountDownLatch raceGate = new CountDownLatch(2);
    private final JdbcTemplate jdbc;

    /** 一個收到的請求：方法、原始路徑（含 {@code :動詞}）、{@code X-Bridge-Token}（null＝沒帶）、{@code X-Trace-Id} 與請求本文（沒有本文＝空 map）。 */
    public record Call(String method, String path, String token, String traceId, Map<String, Object> body) {
    }

    /** 一個固定的回應：狀態碼與本文（Bridge 形狀）。 */
    public record Reply(int status, Map<String, Object> body) {

        /** Bridge 的錯誤封包 {@code {code, reason, …extra}}（extra 為鍵值成對）。 */
        public static Reply error(int status, String reason, Object... extra) {
            Map<String, Object> body = map("code", status, "reason", reason);
            for (int i = 0; i < extra.length; i += 2) {
                body.put((String) extra[i], extra[i + 1]);
            }
            return new Reply(status, body);
        }

        public static Reply ok(int status, Object... keyValues) {
            return new Reply(status, map(keyValues));
        }
    }

    MiniResearch(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
        reset();
    }

    public void reset() {
        writeToken = TOKEN;
        db = true;
        webLayerEnabled = true;
        mode = "local";
        delayMillis = 0;
        stageRace = false;
        calls.clear();
        allowlist.clear();
        scripted.clear();
        sticky.clear();
        raceArrivals.set(0);
        raceGate = new CountDownLatch(2);
    }

    // ── 腳本 ─────────────────────────────────────────────────────────────────────────────

    /** 下一次符合 {@code route} 的請求回這個腳本回應，只用一次。 */
    public void next(String route, Reply reply) {
        scripted.computeIfAbsent(route, k -> new ConcurrentLinkedQueue<>()).add(reply);
    }

    /** {@code route} 的每個請求都回這個腳本回應，直到 {@link #reset()}。 */
    public void always(String route, Reply reply) {
        sticky.put(route, reply);
    }

    /** 取第一個有腳本的路由鍵的回應（單次優先於持續）；都沒有回 null。 */
    Reply script(String... routes) {
        for (String route : routes) {
            Queue<Reply> queue = scripted.get(route);
            Reply once = queue == null ? null : queue.poll();
            if (once != null) {
                return once;
            }
            Reply always = sticky.get(route);
            if (always != null) {
                return always;
            }
        }
        return null;
    }

    // ── 觀測 ─────────────────────────────────────────────────────────────────────────────

    /** 寫入請求（非 GET）的個數。 */
    public long writeCount() {
        return calls.stream().filter(call -> !"GET".equals(call.method())).count();
    }

    public long countCalls(String method, String pathPrefix) {
        return calls.stream().filter(call -> call.method().equals(method) && call.path().startsWith(pathPrefix)).count();
    }

    public Call lastCall() {
        return calls.isEmpty() ? null : calls.get(calls.size() - 1);
    }

    void record(Call call) {
        calls.add(call);
    }

    // ── 夾具與預設行為用的內部介面 ──────────────────────────────────────────────────────────

    JdbcTemplate jdbc() {
        return jdbc;
    }

    /** 兩個並發的 stage 啟動：回第幾個到達（1 或 2）；兩者都到齊才放行（逾時 10 秒視為只有一個）。 */
    int arriveAtRace() {
        int n = raceArrivals.incrementAndGet();
        CountDownLatch gate = raceGate;
        gate.countDown();
        try {
            gate.await(10, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        return n;
    }

    /** ENV 基底條目＋ADMIN 條目（Bridge 的 {@code GET /research/allowlist} 形狀）。 */
    Map<String, Object> allowlistBody() {
        List<Map<String, Object>> items = new ArrayList<>();
        for (String host : FETCH_HOSTS) {
            items.add(map("id", null, "list_kind", "FETCH", "host", host, "layer", null, "purpose", "", "tos_note", "", "min_interval_seconds", 3,
                    "enabled", true, "tos_acknowledged", false, "added_by", null, "added_at", null, "disabled_by", null, "disabled_at", null, "source", "ENV"));
        }
        items.addAll(allowlist);
        Map<String, Object> effective = new LinkedHashMap<>();
        effective.put("FETCH", new ArrayList<>(FETCH_HOSTS));
        effective.put("WEB", new ArrayList<String>());
        for (Map<String, Object> entry : allowlist) {
            if (Boolean.TRUE.equals(entry.get("enabled"))) {
                @SuppressWarnings("unchecked")
                List<String> hosts = (List<String>) effective.get((String) entry.get("list_kind"));
                if (!hosts.contains((String) entry.get("host"))) {
                    hosts.add((String) entry.get("host"));
                }
            }
        }
        return map("items", items, "effective", effective);
    }

    Map<String, Object> capabilitiesBody() {
        return map("mode", mode, "root", "/research-root", "db", db, "claude_cli", map("ok", true, "version", "2.1.0"),
                "gh_cli", map("ok", false, "authenticated", false), "git", map("ok", true, "version", "git version 2.39.5"),
                "scaffold_root", null, "scaffold_templates", List.of(), "repo_writable", true, "web_layer_enabled", webLayerEnabled,
                "fetch_hosts", FETCH_HOSTS);
    }

    // ── 事件帳（測試把迷你 Bridge 當事件的唯一寫入者）──────────────────────────────────────────

    /** 寫一筆事件（{@code seq} 由呼叫端給；允許不連續）並推進專案的 {@code last_event_seq}。 */
    public void event(UUID researchId, long seq, String eventType, Map<String, Object> payload) {
        jdbc.update("insert into console.research_events (research_id, seq, event_type, step, actor, payload) values (?, ?, ?, 'topic', 'bridge', ?::jsonb)",
                researchId, seq, eventType, JSON.writeValueAsString(payload));
        jdbc.update("update console.research_projects set last_event_seq = greatest(last_event_seq, ?) where id = ?", seq, researchId);
    }

    /**
     * 依固定節奏在背景推送 {@code fromSeq..toSeq} 的事件（每筆 payload 帶 {@code emitted_at}＝寫入前一刻的 epoch 毫秒），回傳「推送完成」的閘門。
     * 供延遲（P95）量測：接收時間減 {@code emitted_at}。
     */
    public CountDownLatch pushEvents(UUID researchId, long fromSeq, long toSeq, long intervalMillis) {
        CountDownLatch done = new CountDownLatch(1);
        Thread.ofVirtual().name("mini-research-pusher").start(() -> {
            try {
                for (long seq = fromSeq; seq <= toSeq; seq++) {
                    event(researchId, seq, "research.step", map("flowStep", "topic", "emitted_at", System.currentTimeMillis()));
                    Thread.sleep(intervalMillis);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } finally {
                done.countDown();
            }
        });
        return done;
    }
}
