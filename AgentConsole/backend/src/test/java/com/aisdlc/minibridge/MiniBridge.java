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

    /**
     * 迷你 Bridge 與 console-api 共用的 SDD 寫入權杖（契約 §3.1.4 共通規則 2；Spring 屬性 {@code console.bridge.sdd-write-token}）。
     * 一律是「假」值：≥ 32 字元（console-api 與 Bridge 的啟動驗證下限）、含 {@code mock}（根層機密掃描把它當佔位）。
     */
    public static final String SDD_TOKEN = "mock-bridge-sdd-write-token-for-tests-0123456789";

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

    /** {@code /si/*} 六個唯讀 GET 的夾具（TCS-SelfImprovingMirror-P1b §5.3；測試直接改它的欄位）。預設回放狀態 A 的 snake_case 黃金檔。 */
    public final Si si = new Si();

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

        /**
         * Bridge 端的寫入權杖（契約 §3.1.4 共通規則 2）：預設＝{@link MiniBridge#SDD_TOKEN}；{@code null}＝Bridge 沒設權杖＝寫入動詞整個停用
         * （503 {@code sdd_write_disabled}）；其他值＝與 console-api 附的不符（403 {@code sdd_write_forbidden}）。
         */
        public volatile String writeToken;
        /** 帶 {@code root} 的讀取回 422 {@code sanitization_failed}（{@code violations[].field=root}）的專案根（不在 allowlist 或已不存在）。 */
        public final Set<String> rejectedRoots = ConcurrentHashMap.newKeySet();
        /** 存在、但 {@code build/reports/fsm} 沒有任何狀態檔的專案根：清單回 200 空清單、任何 {@code GET /sdd/fsm/{名稱}} 回 404 {@code fsm_not_found}。 */
        public final Set<String> emptyRoots = ConcurrentHashMap.newKeySet();
        /** {@code :freeze} 的 {@code docs[i]} 要回 422 {@code not_found} 的相對路徑（迷你 Bridge 沒有檔案系統）。 */
        public final Set<String> missingDocs = ConcurrentHashMap.newKeySet();
        /** 各 doc 的「現檔摘要」覆蓋值（沒有就是 {@link #digestOf}）：用來造 {@code expected_vs_file} 的 409。 */
        public final Map<String, String> docDigests = new ConcurrentHashMap<>();
        /** 帶 {@code sdd} 的 {@code POST /autoclaude/runs} 成功時 201 另帶的 {@code warnings[]}（例：{@code sdd_frozen_digest_absent}）。 */
        public final List<Map<String, Object>> createWarnings = new CopyOnWriteArrayList<>();
        /** 每個 run 的 RTM 報告本文（不含 {@code advisory}，迷你 Bridge 自己加）；沒有 → 404 {@code rtm_not_found}。 */
        public final Map<UUID, Map<String, Object>> rtmReports = new ConcurrentHashMap<>();
        /** 這些 run 的 {@code /rtm} 回 422 {@code rtm_unreadable}。 */
        public final Set<UUID> rtmUnreadable = ConcurrentHashMap.newKeySet();
        /** 每個收到的 {@code :freeze}（依到達順序）。 */
        public final List<Freeze> freezes = new CopyOnWriteArrayList<>();
        /** 每個帶 {@code root} 或不帶的 {@code GET /sdd/fsm*} 請求與它的 {@code root}（null＝沒帶）。 */
        public final List<RootSeen> rootsSeen = new CopyOnWriteArrayList<>();

        /** 一個收到的 {@code :freeze}：路徑參數（解碼後）、{@code X-Bridge-Token} 標頭（null＝沒帶）與請求本文。 */
        public record Freeze(String project, String token, Map<String, Object> body) {
        }

        /** 一個收到的讀取請求與它帶的 {@code root}（null＝沒帶）。 */
        public record RootSeen(String request, String root) {
        }

        Sdd() {
            reset();
        }

        public void reset() {
            unavailable = false;
            delayMillis = 0;
            latest = "AISDLC_SDD_v9.99";
            root = "/sdd/AISDLC_SDD_v9.99";
            writeToken = SDD_TOKEN;
            rejectedRoots.clear();
            emptyRoots.clear();
            missingDocs.clear();
            docDigests.clear();
            createWarnings.clear();
            rtmReports.clear();
            rtmUnreadable.clear();
            freezes.clear();
            rootsSeen.clear();
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

        /**
         * 加一個專案：同時進 {@code /sdd/fsm} 的清單與 {@code /sdd/fsm/{project}} 的本文（五筆決策軌跡 r3～r7，舊→新）。
         * {@code project} 是檔內原名；檔名與清單用它淨化後的標準鍵 {@link MiniBridge#canonical}（e2e 夾具的名稱本來就是標準鍵，兩者相同）。
         * v1.5 的欄位也一併帶上：{@code phase}（由狀態對映）、{@code escalation_history}（空）、{@code escalation_provenance}（null）、
         * {@code fsm_project}（標準鍵），ESCALATION 狀態另帶 {@code recovery}。
         */
        public void addProject(String project, String currentState, int sprint, String sessionId, String updatedAt,
                               SddRetry retry, Map<String, Object> humanPending) {
            String key = canonical(project);
            String source = "FSM-STATE-" + key + ".yaml";
            projects.add(map("project", key, "source", source, "current_state", currentState, "updated_at", updatedAt));
            List<Map<String, Object>> trace = new ArrayList<>();
            for (int i = 3; i <= 7; i++) {
                trace.add(map("ts", "2026-10-16T00:0" + i + ":00+00:00", "from", "S" + (i - 1), "to", "S" + i,
                        "reason", "r" + i, "spec_refs", List.of("SPEC-" + i), "agents_consulted", List.of("sa"),
                        "trigger", "auto"));
            }
            Map<String, Object> state = map("project", project, "current_state", currentState, "current_sprint", sprint,
                    "session_id", sessionId, "updated_at", updatedAt, "frozen_stages", List.of(map("stage", "SCG-0")),
                    "decision_trace", trace, "source", source, "human_pending", humanPending,
                    "retry_history", map("count", retry.count(), "last", retry.last()), "rtm_coverage", null,
                    "phase", phaseOf(currentState), "escalation_history", List.of(), "escalation_provenance", null,
                    "fsm_project", key);
            if (currentState.startsWith("ESCALATION")) {
                state.put("recovery", map("target", "IMPLEMENTATION",
                        "powershell", "Push-Location \"<SDD 版本目錄>\"; & \"<python>\" -m tools.fsm_runtime.fsm_runtime "
                                + "resume-from-escalation --project \"" + key + "\" --to IMPLEMENTATION --reason \"<人工原因>\"; "
                                + "Pop-Location",
                        "posix", "cd \"<SDD 版本目錄>\" && \"<python>\" -m tools.fsm_runtime.fsm_runtime "
                                + "resume-from-escalation --project \"" + key + "\" --to IMPLEMENTATION --reason \"<人工原因>\""));
            }
            states.put(key, state);
        }
    }

    /**
     * SelfImproving 唯讀鏡像的假資料（欄位名與型別同真 Bridge 的 {@code routers/si.py}：snake_case 的本文、404 {@code si_not_found}、
     * 422 {@code invalid_request}、503 {@code si_unavailable}）。{@link #reset()} 回到預設：回放狀態 A 的黃金檔
     * （{@code src/test/resources/si/A.snake.json}，真 CLI 輸出的凍結複本），沒有任何失敗旋鈕開著。
     */
    public static final class Si {

        /**
         * 回應本文（Bridge 形狀）：鍵為 {@code observations}、{@code events}、{@code proposals}、{@code runs}、{@code status} 與 {@code proposal:<id>}；
         * 議題中心（TCS-IssueCenter-20261027 D-C12）另有 {@code issues}（清單，預設為黃金檔的 {@code issues} 鍵）與 {@code issue:<id>}（單筆；
         * 預設沒有，測試自己放——沒有放的 id 回 404 {@code si_not_found}）。
         */
        public final Map<String, Map<String, Object>> payloads = new ConcurrentHashMap<>();
        /** 非空（鍵 {@code cause}、{@code detail}）＝全部 {@code /si/*} 回 503 {@code si_unavailable}。 */
        public volatile Map<String, String> unavailable = Map.of();
        /** 對這些 id 的 {@code GET /si/proposals/{id}} 回 404 {@code si_not_found}（帶 {@code id}）。 */
        public final Set<String> notFoundIds = ConcurrentHashMap.newKeySet();
        /** 非空＝全部 {@code /si/*} 回 422 {@code invalid_request} 並帶這些 {@code violations}。 */
        public volatile List<Map<String, Object>> invalid = List.of();
        /** true＝全部 {@code /si/*} 回 500。 */
        public volatile boolean status500;
        /** 非 null＝回 200 但本文為這個純文字。 */
        public volatile String garbage;
        /** true＝回 200 但本文為 JSON 陣列。 */
        public volatile boolean arrayBody;
        /** 每個 {@code /si/*} 回應前先睡這麼久（毫秒）：用來造讀取逾時（console-api 的讀取逾時 20 秒）。 */
        public volatile long delayMillis;
        /** 每個收到的請求的<b>原始</b> URI（未解碼的路徑）與原始查詢字串（null＝沒帶）：供 id 編碼與參數轉發的斷言。 */
        public final List<Seen> seen = new CopyOnWriteArrayList<>();

        /** 一個收到的 {@code /si/*} 請求：原始路徑與原始查詢字串。 */
        public record Seen(String uri, String query) {
        }

        // ── P2b：稽核檔落地與預檢（TCS-SelfImprovingDecide-P2b §5.4；對照 routers/si.py 的三個寫入 POST 與 :validate）──

        /** 每個收到的寫入請求（依到達順序；含預檢）：原始路徑、{@code X-Bridge-Token} 標頭（null＝沒帶）與請求本文位元組。 */
        public final List<Write> writes = new CopyOnWriteArrayList<>();

        /** 一個收到的 {@code POST /si/...}：原始（未解碼）路徑、權杖標頭與請求本文位元組。 */
        public record Write(String path, String token, byte[] raw) {

            /** 請求本文的 UTF-8 文字。 */
            public String text() {
                return new String(raw, java.nio.charset.StandardCharsets.UTF_8);
            }
        }

        /**
         * 寫入端點回應的覆蓋；{@code null}＝預設 201 與兩鍵本文（audit_ref 取自請求本文、stored 恆為 true）。{@code body} 逐字送出
         * （以左大括號或左中括號起頭視為 JSON，其餘為純文字）。
         */
        public volatile WriteReply writeReply;
        /** 預檢（{@code :validate}）失敗時的回應；{@code null}＝回 {@link #validateReply}（200）。 */
        public volatile WriteReply validateFailure;
        /** 每個寫入請求回應前先睡這麼久（毫秒）：造讀取逾時。 */
        public volatile long writeDelayMillis;
        /** 收到寫入請求的<b>當下</b>（回應之前）的回呼：AT-933-2-1 在這裡以 JDBC 讀稽核列。 */
        public volatile java.util.function.Consumer<Write> onWrite;
        /** 預檢成功的回應物件（Bridge 形狀）：預設 ok 為 true、row_bytes 287、row_max_bytes 700、findings 空。 */
        public volatile Map<String, Object> validateReply;

        /** 一個固定的回應：狀態碼與逐字本文。 */
        public record WriteReply(int status, String body) {

            /** Bridge 的錯誤封包 {@code {code, reason, …extra}}。 */
            public static WriteReply error(int status, String reason, Object... extra) {
                Map<String, Object> body = map("code", status, "reason", reason);
                for (int i = 0; i < extra.length; i += 2) {
                    body.put((String) extra[i], extra[i + 1]);
                }
                return new WriteReply(status, JSON.writeValueAsString(body));
            }
        }

        public static Map<String, Object> defaultValidateReply() {
            return map("ok", true, "row", "| 預覽列（測試替身）|", "row_bytes", 287, "row_max_bytes", 700, "findings", List.of());
        }

        Si() {
            reset();
        }

        public void reset() {
            unavailable = Map.of();
            notFoundIds.clear();
            invalid = List.of();
            status500 = false;
            garbage = null;
            arrayBody = false;
            delayMillis = 0;
            seen.clear();
            writes.clear();
            writeReply = null;
            validateFailure = null;
            writeDelayMillis = 0;
            onWrite = null;
            validateReply = defaultValidateReply();
            payloads.clear();
            Map<String, Map<String, Object>> golden = golden("A.snake");
            payloads.put("observations", golden.get("observations"));
            payloads.put("events", golden.get("events"));
            payloads.put("proposals", golden.get("proposals"));
            payloads.put("runs", golden.get("runs"));
            payloads.put("status", golden.get("status"));
            payloads.put("proposal:PROP-SI-004", golden.get("proposal_one"));
            payloads.put("issues", golden.get("issues"));
        }

        /** 黃金檔 {@code src/test/resources/si/<name>.json}（{@code A.snake}｜{@code B.snake}）：鍵為各端點名稱，值為完整回應物件。 */
        public static Map<String, Map<String, Object>> golden(String name) {
            try (java.io.InputStream in = MiniBridge.class.getResourceAsStream("/si/" + name + ".json")) {
                if (in == null) {
                    throw new IllegalStateException("找不到黃金檔 si/" + name + ".json");
                }
                return JSON.readValue(in, new tools.jackson.core.type.TypeReference<Map<String, Map<String, Object>>>() { });
            } catch (java.io.IOException e) {
                throw new java.io.UncheckedIOException(e);
            }
        }
    }

    /**
     * 淨化鏡像（契約 §3.1.4 (b)；簡化版，足以區分「原名」與「標準鍵」）：NFC → strip → {@code <>:"?*\/|} 與控制字元換 {@code _} →
     * 截 80 → {@code rstrip(" .")}（空則 {@code untitled}）。冪等，所以傳原名與傳標準鍵等價。
     */
    public static String canonical(String name) {
        String text = java.text.Normalizer.normalize(name, java.text.Normalizer.Form.NFC).strip();
        text = text.replaceAll("[<>:\"?*\\\\/|\\p{Cntrl}]", "_");
        if (text.length() > 80) {
            text = text.substring(0, 80);
        }
        text = text.replaceAll("[ .]+$", "");
        return text.isEmpty() ? "untitled" : text;
    }

    /** 由 {@code current_state} 投影的階段資訊（契約 §3.1.5 的子集：夠測試用）。 */
    static Map<String, Object> phaseOf(String state) {
        return switch (state) {
            case "INIT", "SPEC_DRAFTING" -> map("name", "SPECIFICATION", "order", 2, "blocking", false, "observation", false);
            case "HUMAN_PENDING" -> map("name", "HUMAN_GATE", "order", 3, "blocking", false, "observation", false);
            case "SPEC_FROZEN" -> map("name", "FROZEN", "order", 4, "blocking", false, "observation", false);
            case "IMPLEMENTATION", "TEST_CONTRACT_NEGOTIATED" ->
                    map("name", "IMPLEMENTATION", "order", 5, "blocking", false, "observation", false);
            case "AUTOCLAUDE_DELEGATED" -> map("name", "IMPLEMENTATION", "order", 5, "blocking", false, "observation", true);
            case "ESCALATION", "ESCALATION_FINAL", "TERMINATED" -> map("name", "BLOCKED", "order", 0, "blocking", true,
                    "observation", false);
            default -> map("name", "UNKNOWN", "order", 0, "blocking", false, "observation", false);
        };
    }

    /** 迷你 Bridge 對某個 doc 路徑的「現檔摘要」：路徑字串的 sha256（確定性、與檔案系統無關）。 */
    public static String digestOf(String path) {
        try {
            byte[] hash = java.security.MessageDigest.getInstance("SHA-256")
                    .digest(path.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return "sha256:" + java.util.HexFormat.of().formatHex(hash);
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    /** RTM 報告本文（契約 §3.1.4 (f) 的形狀，不含 {@code advisory}）。 */
    public static Map<String, Object> rtmReport(String scenario, int passedAt, int totalAt, int unmappedAt, double atPct,
                                                int coveredAc, int totalAc, double acPct, List<String> failedAtIds,
                                                List<String> weakRegexAtIds, List<String> unmappedAtIds,
                                                boolean fullyCovered) {
        return map("scenario", scenario, "spec_digest", "sha256:" + "0123456789abcdef".repeat(4),
                "at", map("passed", passedAt, "total", totalAt, "unmapped", unmappedAt, "pct", atPct),
                "ac", map("covered", coveredAc, "total", totalAc, "pct", acPct), "failed_at_ids", failedAtIds,
                "weak_regex_at_ids", weakRegexAtIds, "unmapped_at_ids", unmappedAtIds, "fully_covered", fullyCovered);
    }

    private final ConfigurableApplicationContext context;
    private final JdbcTemplate jdbc;
    private final int port;
    private final Map<UUID, MiniRun> runs = new ConcurrentHashMap<>();
    private final Map<String, UUID> locks = new ConcurrentHashMap<>();
    private final Map<String, ConcurrentLinkedQueue<Injected>> injected = new ConcurrentHashMap<>();
    private final List<String> requestLog = new CopyOnWriteArrayList<>();
    private final List<Traced> traced = new CopyOnWriteArrayList<>();
    private final List<Authed> authed = new CopyOnWriteArrayList<>();
    private final AtomicInteger streamGeneration = new AtomicInteger();
    private final AtomicInteger openStreams = new AtomicInteger();

    /** 預先設好的錯誤回應（見 {@link #failNext}）。 */
    record Injected(int status, Map<String, Object> body) {
    }

    /** 迷你 Bridge 收到的一個請求（{@code METHOD /path}，不含查詢字串）與它帶的 {@code X-Trace-Id}（null＝沒帶；契約 §3.1.1）。 */
    public record Traced(String request, String traceId) {
    }

    /** 迷你 Bridge 收到的一個請求（同 {@link Traced}）與它帶的 {@code X-Bridge-Token}（null＝沒帶；契約 §3.1.4 共通規則 2）。 */
    public record Authed(String request, String token) {
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

    /** 每個收到的請求與它帶的 {@code X-Bridge-Token}（依到達順序）：測試斷言「權杖只出現在那四個呼叫上」。 */
    public List<Authed> authed() {
        return List.copyOf(authed);
    }

    public void reset() {
        runs.values().forEach(MiniRun::shutdown);
        runs.clear();
        locks.clear();
        injected.clear();
        requestLog.clear();
        traced.clear();
        authed.clear();
        failStepIds.clear();
        stepMillis = 40;
        tokensPerAttempt = 1240;
        manualSteps = false;
        completionDelayMillis = 0;
        keepAliveMillis = 500;
        resourcesMode = ResourcesMode.SAMPLE;
        deepHealthMode = DeepHealthMode.HEALTHY;
        sdd.reset();
        si.reset();
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

    void recordToken(String request, String token) {
        authed.add(new Authed(request, token));
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
