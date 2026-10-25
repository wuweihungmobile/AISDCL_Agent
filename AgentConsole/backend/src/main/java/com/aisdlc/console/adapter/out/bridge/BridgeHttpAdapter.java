package com.aisdlc.console.adapter.out.bridge;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.engine.SddFsmList;
import com.aisdlc.console.domain.model.engine.SddFsmState;
import com.aisdlc.console.domain.model.engine.SddProjectEntry;
import com.aisdlc.console.domain.model.engine.SddVersion;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.ExecutionRtm;
import com.aisdlc.console.domain.model.execution.ExecutionWarning;
import com.aisdlc.console.domain.model.execution.ResourceUsage;
import com.aisdlc.console.domain.model.si.SiExport;
import com.aisdlc.console.domain.model.si.SiValidation;
import com.aisdlc.console.domain.model.si.SiWriteAck;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.ClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import tools.jackson.core.JacksonException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.io.UncheckedIOException;
import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.net.URI;
import java.net.UnknownHostException;
import java.net.http.HttpClient;
import java.net.http.HttpConnectTimeoutException;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;
import java.util.function.Function;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * {@link AgentBridge} 的 {@code RestClient} 實作（契約 §3.1／§3.2）。Bridge 只有 console-api 以服務身分呼叫
 * （內網、無認證）。每個呼叫各有逾時（{@link RequestFactoryProvider}）；本檔不重試（非冪等呼叫失敗即由上層決定）。
 *
 * <p>錯誤分流：連線失敗 → {@link UpstreamException.Unavailable}；讀取逾時 → {@link UpstreamException.TimedOut}；
 * 5xx → {@link UpstreamException.Failure}；4xx → {@link BridgeRejectedException}（Bridge 的
 * {@code {code,reason,gate?,detail?,violations?}} 封包原樣帶回，由用例依端點語意轉成 409／422…）。
 *
 * <p><b>traceId 貫穿</b>（契約 §0.4 第 6 點，C-12）：對 Bridge 的<b>每一個</b>請求（含 SSE 事件串流與健康探測）都帶標頭
 * {@value #TRACE_HEADER}。值取自目前執行緒 MDC 的 {@code traceId}（使用者請求由 {@code TraceIdFilter} 寫入；事件消費者與啟動對帳
 * 由用例層放入該 run 的 traceId）；執行緒上沒有時（探測環等背景工作）新產一個 UUID。同一次呼叫的重試沿用同一個值。
 */
@Component
class BridgeHttpAdapter implements AgentBridge {

    static final String TRACE_HEADER = "X-Trace-Id";
    /** SDD 寫入權杖標頭（ADR-XPLAT-016 §9）：只附在四個會觸發 FSM 寫入的呼叫。🔴 值絕不進日誌、錯誤封包或 details。 */
    static final String TOKEN_HEADER = "X-Bridge-Token";
    /** Bridge 在「SDD 寫入面停用」時回的 503 reason（它的 {@code BRIDGE_SDD_WRITE_TOKEN} 沒設）：不是 5xx 故障，而是設定決定的停用。 */
    private static final String SDD_WRITE_DISABLED = "sdd_write_disabled";
    /** Bridge 在「SelfImproving 資料面不可用」時回的 503 reason（TCS-P1b R4、R8）：與 4xx 同走 {@code BridgeRejectedException}，由用例轉成 503。 */
    private static final String SI_UNAVAILABLE = "si_unavailable";
    /**
     * Bridge 在「SelfImproving 寫入面停用」時回的 503 reason（它的 {@code BRIDGE_SI_WRITE_TOKEN} 或 {@code BRIDGE_SI_AUDIT_DIR} 沒設；
     * TCS-SelfImprovingDecide-P2b W3、W15）：同 {@code sdd_write_disabled}，是設定決定的明確拒絕、不是 5xx 故障。
     */
    private static final String SI_WRITE_DISABLED = "si_write_disabled";
    private static final String TRACE_MDC_KEY = "traceId";
    private static final Logger LOG = LoggerFactory.getLogger(BridgeHttpAdapter.class);
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final TypeReference<Map<String, Object>> OBJECT = new TypeReference<>() { };
    private static final Duration CONNECT_TIMEOUT = Duration.ofSeconds(2);
    /**
     * 健康探測的讀取逾時 8 秒（契約 §3.1；v1.4 D-17，v1.3 以前 3 秒）：探測改打深度探針後，Bridge 光是 {@code git --version}
     * 就最多等 5 秒，再加其餘各項；3 秒會把「Bridge 只是慢、並沒有壞」誤判成不可達。
     */
    private static final Duration HEALTH_READ_TIMEOUT = Duration.ofSeconds(8);
    /** 引擎狀態查詢（{@code /sdd/version}、{@code /sdd/fsm}、{@code /sdd/fsm/{project}}）：連線 2 秒、讀取 3 秒、不重試（契約 §3.1）。 */
    private static final Duration SDD_READ_TIMEOUT = Duration.ofSeconds(3);
    /**
     * SelfImproving（{@code /si/*}：P1b 唯讀鏡像，P2b 的稽核檔落地與預檢沿用同一組逾時）：連線 2 秒、讀取 20 秒、不重試（TCS-P1b R8；
     * ADR-SI-12；TCS-SelfImprovingDecide-P2b W11）。Bridge 的 {@code export}／{@code validate} 子行程逾時 15 秒
     * （{@code SI_CLI_TIMEOUT_SECONDS}）必須小於這個值，否則 Bridge 的 503 會被這裡的 504 蓋掉。
     */
    private static final Duration SI_READ_TIMEOUT = Duration.ofSeconds(20);
    private static final char[] HEX = "0123456789ABCDEF".toCharArray();
    private static final Duration APPROVE_READ_TIMEOUT = Duration.ofSeconds(10);
    private static final Duration COMPILE_READ_TIMEOUT = Duration.ofSeconds(15);
    // 契約 §3.1 呼叫總表：連線 2s，讀取逾時依呼叫而定
    private static final Duration START_READ_TIMEOUT = Duration.ofSeconds(30);
    /** 帶 {@code sdd} 的建立批次：含最多三次 FSM CLI 子行程（每次 ≤ 20 秒），所以 90 秒（契約 §3.1；一般批次維持 30 秒）。 */
    private static final Duration START_SDD_READ_TIMEOUT = Duration.ofSeconds(90);
    private static final Duration PAUSE_READ_TIMEOUT = Duration.ofSeconds(5);
    /**
     * resume／restore 的讀取逾時 30 秒（v1.5，原 15 秒；契約 §3.1）：SDD run 可能多一次 {@code delegate-enter}（CLI 單次最多 20 秒），
     * 15 秒會在 Bridge 還在工作時先讀取逾時而得到 504；console-api 分不出 SDD 與非 SDD run，兩者共用同一個值。
     */
    private static final Duration RESUME_READ_TIMEOUT = Duration.ofSeconds(30);
    private static final Duration STOP_READ_TIMEOUT = Duration.ofSeconds(10);
    private static final Duration RESTORE_READ_TIMEOUT = Duration.ofSeconds(30);
    /** 核准凍結：Bridge 經 CLI 子行程記錄凍結並重讀狀態檔（契約 §3.1：連線 2 秒／讀取 40 秒、不重試）。 */
    private static final Duration FREEZE_READ_TIMEOUT = Duration.ofSeconds(40);
    private static final Duration GET_READ_TIMEOUT = Duration.ofSeconds(3);
    private static final Duration EVENTS_READ_TIMEOUT = Duration.ofSeconds(10);
    private static final Duration STREAM_CONNECT_TIMEOUT = Duration.ofSeconds(3);
    private static final int GET_RETRIES = 2;
    private static final long GET_RETRY_BACKOFF_MS = 200;
    private static final int MAX_BODY_BYTES = 8 * 1024 * 1024;
    /** 狀態事件的 {@code reason} 與告警事件的 {@code message} 是 Bridge 的自由文字，可能帶 pid（{@link BridgeText}）。 */
    private static final List<String> FREE_TEXT_KEYS = List.of("reason", "message");
    /** SSE 閒置看門狗的共用排程器（daemon；每個串流各自 arm／disarm）。 */
    private static final ScheduledExecutorService WATCHDOG = Executors.newSingleThreadScheduledExecutor(task -> {
        Thread thread = new Thread(task, "bridge-sse-watchdog");
        thread.setDaemon(true);
        return thread;
    });

    private final RestClient.Builder builder;
    private final BridgeEndpoints endpoints;
    private final RequestFactoryProvider factories;

    BridgeHttpAdapter(RestClient.Builder bridgeRestClientBuilder, BridgeEndpoints endpoints,
                      RequestFactoryProvider factories) {
        this.builder = bridgeRestClientBuilder;
        this.endpoints = endpoints;
        this.factories = factories;
    }

    @Override
    public DecomposeResult decompose(DecomposeRequest request, Duration readTimeout) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("goal", request.goal());
        body.put("context", request.context());
        body.put("project", request.project());
        body.put("max_steps", request.maxSteps());
        if (request.minimaxOverrides() != null) {
            body.put("config_overrides", Map.of("minimax", request.minimaxOverrides()));
        }
        Map<String, Object> doc = postJson(endpoints.autoclaudeBase() + "/autoclaude/decompose", body, readTimeout);
        Map<String, Object> playbook = asMap(doc.get("playbook"));
        List<DraftStep> steps = new ArrayList<>();
        for (Object item : asList(playbook.get("tasks"))) {
            Map<String, Object> task = asMap(item);
            steps.add(new DraftStep(text(task.get("step_id")), text(task.get("name")), text(task.get("prompt")),
                    text(task.get("evaluator_command"))));
        }
        return new DecomposeResult(text(doc.get("draft_id")), text(doc.get("reasoning")), steps);
    }

    @Override
    public void approveDraft(String draftId, String approver) {
        postJson(endpoints.autoclaudeBase() + "/autoclaude/decompose/" + draftId + ":approve",
                Map.of("approver", approver), APPROVE_READ_TIMEOUT);
    }

    @Override
    public SddCompileResult sddCompile(String specDir, String specFile, String fsmProject) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("spec_dir", specDir);
        if (specFile != null && !specFile.isBlank()) {
            body.put("spec_file", specFile);
        }
        if (fsmProject != null && !fsmProject.isBlank()) {
            body.put("fsm_project", fsmProject);                 // 有效值原樣送出：Backend 不淨化（契約 §3.3.2 v1.5 補充第 1 點）
        }
        Map<String, Object> doc = postJson(endpoints.sddBase() + "/sdd/compile", body, COMPILE_READ_TIMEOUT);
        List<SddTask> tasks = new ArrayList<>();
        for (Object item : asList(doc.get("tasks"))) {
            Map<String, Object> task = asMap(item);
            tasks.add(new SddTask(text(task.get("step_id")), text(task.get("name")), text(task.get("prompt")),
                    text(task.get("expected_output_regex")), text(task.get("evaluator_command")),
                    Boolean.TRUE.equals(task.get("weak_regex")), intOrNull(task.get("max_retries")),
                    task.get("maintain_context") instanceof Boolean b ? b : null, text(task.get("spec_digest"))));
        }
        List<String> unmapped = new ArrayList<>();
        for (Object id : asList(doc.get("unmapped_at_ids"))) {
            unmapped.add(text(id));
        }
        List<SddCompileWarning> warnings = new ArrayList<>();
        for (Object item : asList(doc.get("warnings"))) {
            Map<String, Object> warning = asMap(item);
            if (text(warning.get("code")) != null) {
                warnings.add(new SddCompileWarning(text(warning.get("code")), text(warning.get("detail"))));
            }
        }
        return new SddCompileResult(text(doc.get("scenario")), text(doc.get("spec_path")), text(doc.get("digest")),
                tasks, text(doc.get("spec_file")), text(doc.get("fsm_project")), text(doc.get("frozen_digest")),
                text(doc.get("spec_format_version")), unmapped, warnings);
    }

    // ── v1.4（D-16）：AISDLC_SDD 唯讀查詢（契約 §3.1 三列、§3.1.3；連線 2s／讀取 3s、不重試）──────────────────

    @Override
    public SddVersion sddVersion() {
        Map<String, Object> doc = asMap(getJson(endpoints.sddBase() + "/sdd/version", Map.of(), SDD_READ_TIMEOUT, 0));
        String latest = text(doc.get("latest"));
        if (latest == null || latest.isBlank()) {
            throw malformed("GET /sdd/version");
        }
        String root = text(doc.get("root"));
        return new SddVersion(latest, root == null ? "" : root);
    }

    @Override
    public SddFsmList sddFsmList(String root) {
        Map<String, Object> variables = new LinkedHashMap<>();
        String template = endpoints.sddBase() + "/sdd/fsm";
        if (root != null) {
            template += "?root={root}";
            variables.put("root", root);
        }
        Map<String, Object> doc = asMap(getJson(template, variables, SDD_READ_TIMEOUT, 0));
        if (!(doc.get("projects") instanceof List<?> items)) {
            throw malformed("GET /sdd/fsm");
        }
        List<SddProjectEntry> projects = new ArrayList<>();
        for (Object item : items) {
            Map<String, Object> entry = asMap(item);
            String project = text(entry.get("project"));
            String source = text(entry.get("source"));
            if (project == null || project.isBlank() || source == null) {
                throw malformed("GET /sdd/fsm 的 projects[]");
            }
            projects.add(new SddProjectEntry(project, source, text(entry.get("current_state")),
                    text(entry.get("updated_at"))));
        }
        List<String> errors = new ArrayList<>();
        for (Object name : asList(doc.get("errors"))) {
            errors.add(text(name));
        }
        return new SddFsmList(text(doc.get("root")), projects, errors);
    }

    @Override
    public SddFsmState sddFsm(String project, String root) {
        // 有效值原樣交給 Bridge 的淨化鏡像：這裡只做 URI 變數的嚴格 percent-encode（CJK、空白、`:` 都安全）
        Map<String, Object> variables = new LinkedHashMap<>();
        variables.put("project", project);
        String template = endpoints.sddBase() + "/sdd/fsm/{project}";
        if (root != null) {
            template += "?root={root}";
            variables.put("root", root);
        }
        Map<String, Object> doc = asMap(getJson(template, variables, SDD_READ_TIMEOUT, 0));
        if (doc.isEmpty()) {
            throw malformed("GET /sdd/fsm/{project}");
        }
        return fsmStateOf(doc, project);
    }

    @Override
    public SddFsmState sddFreeze(String project, SddFreeze request) {
        Map<String, String> auth = writeToken();
        if (auth.isEmpty()) {
            // 呼叫端本來就該先檢查；這裡是最後一道網：沒有權杖就不發出請求（發了也只會被 Bridge 回 503／403）
            throw new ServiceUnavailableException("backend 沒有設定 SDD 寫入權杖（BRIDGE_SDD_WRITE_TOKEN），核准凍結已停用",
                    ErrorReasons.SDD_WRITE_DISABLED);
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("root", request.root());
        if (request.stage() != null && !request.stage().isBlank()) {
            body.put("stage", request.stage());
        }
        body.put("docs", request.docs());
        body.put("approver", request.approver());
        body.put("reason", request.reason());
        if (request.expectedDigests() != null && !request.expectedDigests().isEmpty()) {
            body.put("expected_digests", request.expectedDigests());
        }
        Map<String, Object> doc = postJson(endpoints.sddBase() + "/sdd/fsm/{project}:freeze", Map.of("project", project),
                body, FREEZE_READ_TIMEOUT, auth);
        if (doc.isEmpty()) {
            throw malformed("POST /sdd/fsm/{project}:freeze");
        }
        return fsmStateOf(doc, project);
    }

    /**
     * Bridge 的 FSM 狀態本文（{@code GET /sdd/fsm/{project}} 與 {@code :freeze} 成功回應共用）→ {@link SddFsmState}。最外層鍵轉 camelCase，
     * 巢狀內容（{@code frozen_stages}、{@code decision_trace}、{@code human_pending.items}、{@code retry_history.last}、{@code rtm_coverage}、
     * {@code escalation_history}、{@code escalation_provenance}）原樣；v1.5 的五個新欄位缺鍵一律補預設，不得失敗（舊版 Bridge 相容）。
     */
    static SddFsmState fsmStateOf(Map<String, Object> doc, String fallbackProject) {
        String name = text(doc.get("project"));
        List<Map<String, Object>> trace = objects(doc.get("decision_trace"));
        List<Map<String, Object>> escalations = objects(doc.get("escalation_history"));
        return new SddFsmState(name == null || name.isBlank() ? fallbackProject : name, text(doc.get("current_state")),
                intOrNull(doc.get("current_sprint")), text(doc.get("session_id")), text(doc.get("updated_at")),
                objects(doc.get("frozen_stages")), tail(trace, 5), text(doc.get("source")),
                humanPendingOf(doc.get("human_pending")), retryHistoryOf(doc.get("retry_history")),
                doc.get("rtm_coverage"), phaseOf(doc.get("phase")), tail(escalations, 5),
                doc.get("escalation_provenance") instanceof Map<?, ?> ? asMap(doc.get("escalation_provenance")) : null,
                text(doc.get("fsm_project")), recoveryOf(doc.get("recovery")));
    }

    private static <T> List<T> tail(List<T> items, int max) {
        return items.size() > max ? items.subList(items.size() - max, items.size()) : items;
    }

    /** {@code phase}：四個欄位型別正確才採用；缺鍵、null、形狀不對一律 null（前端顯示「—」，不猜測）。 */
    private static SddFsmState.Phase phaseOf(Object value) {
        if (value instanceof Map<?, ?> map && map.get("name") instanceof String name && !name.isBlank()
                && map.get("order") instanceof Number order) {
            return new SddFsmState.Phase(name, order.intValue(), Boolean.TRUE.equals(map.get("blocking")),
                    Boolean.TRUE.equals(map.get("observation")));
        }
        return null;
    }

    /** {@code recovery}：{@code target}／{@code powershell}／{@code posix} 三個字串都在才採用，否則 null（Bridge 無法判定目標時整個省略，Console 不猜）。 */
    private static SddFsmState.Recovery recoveryOf(Object value) {
        if (value instanceof Map<?, ?> map && map.get("target") instanceof String target && !target.isBlank()
                && map.get("powershell") instanceof String powershell && map.get("posix") instanceof String posix) {
            return new SddFsmState.Recovery(target, powershell, posix);
        }
        return null;
    }

    @Override
    public ExecutionRtm getRunRtm(UUID runId) {
        Map<String, Object> doc = asMap(getJson(runsBase() + "/autoclaude/runs/" + runId + "/rtm", Map.of(),
                GET_READ_TIMEOUT, 0));
        Map<String, Object> at = asMap(doc.get("at"));
        Map<String, Object> ac = asMap(doc.get("ac"));
        return new ExecutionRtm(text(doc.get("scenario")), text(doc.get("spec_digest")),
                new ExecutionRtm.At(intOrZero(at.get("passed")), intOrZero(at.get("total")),
                        intOrZero(at.get("unmapped")), decimalOrZero(at.get("pct"))),
                new ExecutionRtm.Ac(intOrZero(ac.get("covered")), intOrZero(ac.get("total")),
                        decimalOrZero(ac.get("pct"))),
                strings(doc.get("failed_at_ids")), strings(doc.get("weak_regex_at_ids")),
                strings(doc.get("unmapped_at_ids")), Boolean.TRUE.equals(doc.get("fully_covered")));
    }

    // ── SelfImproving：P1b 唯讀鏡像（TCS-SelfImprovingMirror-P1b R7、R8、R10）與 P2b 稽核檔落地、預檢（TCS-SelfImprovingDecide-P2b W3、W4、W11）；
    //    全部連線 2s／讀取 20s、不重試 ────────────────────────────────────────────────────────────────────

    @Override
    public SiExport siExport(String kind, Integer since, Integer limit, String id) {
        StringBuilder url = new StringBuilder(endpoints.siBase()).append("/si/").append(kind);
        if (id != null) {
            // 單筆：不帶 since／limit（Bridge 對 /si/proposals/{id} 的任何查詢參數一律 422）
            url.append('/').append(pathSegment(id));
        } else if (!"status".equals(kind)) {
            // /si/status 同樣不收任何查詢參數；清單類依序帶 since、limit（null 不進網址）
            String separator = "?";
            if (since != null) {
                url.append(separator).append("since=").append(since);
                separator = "&";
            }
            if (limit != null) {
                url.append(separator).append("limit=").append(limit);
            }
        }
        // 網址已是完整、已編碼的 URI：不再交給範本引擎（它會把已編好的 % 再編一次，也無法表達「整段為 .／.. 時點字元編成 %2E」）
        URI uri = URI.create(url.toString());
        Object doc = getJson(rest -> rest.get().uri(uri), SI_READ_TIMEOUT, 0);
        if (!(doc instanceof Map<?, ?>)) {
            throw malformed("GET /si/" + kind);
        }
        return new SiExport(asMap(doc));
    }

    @Override
    public SiWriteAck siWriteDecide(String id, String audit) {
        return siWrite("/si/proposals/" + pathSegment(id) + ":decide", audit);
    }

    @Override
    public SiWriteAck siWriteObservation(String audit) {
        return siWrite("/si/observations", audit);
    }

    @Override
    public SiWriteAck siWriteObservationClose(String id, String audit) {
        return siWrite("/si/observations/" + pathSegment(id) + ":close", audit);
    }

    /**
     * 稽核檔落地的共同路徑：附 {@code X-Bridge-Token}（沒有權杖就不發出請求）、本文為稽核 JSON 全文的 UTF-8 位元組、不重試。
     * 2xx 但本文不是 {@code {audit_ref, stored:true}} → {@link UpstreamException.Failure}（{@code bridgeStatus}＝200：檔可能已落地，結果不明）。
     */
    private SiWriteAck siWrite(String path, String audit) {
        Map<String, String> auth = siWriteToken();
        if (auth.isEmpty()) {
            // 呼叫端（SiConsoleWriteService）本來就該先檢查；這裡是最後一道網：沒有權杖就不發出請求（發了也只會被 Bridge 回 503／403）
            throw new ServiceUnavailableException("backend 沒有設定 SelfImproving 寫入權杖（BRIDGE_SI_WRITE_TOKEN），寫入面已停用",
                    ErrorReasons.SI_WRITE_DISABLED, Map.of("cause", "bridge_token_unset"));
        }
        Map<String, Object> doc = postRaw(URI.create(endpoints.siBase() + path), audit, SI_READ_TIMEOUT, auth);
        String ref = text(doc.get("audit_ref"));
        if (ref == null || ref.isBlank() || !Boolean.TRUE.equals(doc.get("stored"))) {
            throw malformed("POST /si 稽核檔落地");
        }
        return new SiWriteAck(ref, true);
    }

    @Override
    public SiValidation siValidateObservation(String body) {
        Map<String, Object> doc = postRaw(URI.create(endpoints.siBase() + "/si/observations:validate"), body, SI_READ_TIMEOUT,
                Map.of());
        if (!(doc.get("ok") instanceof Boolean ok) || !(doc.get("row") instanceof String row)
                || !(doc.get("row_bytes") instanceof Number rowBytes)) {
            throw malformed("POST /si/observations:validate");
        }
        List<SiValidation.Finding> findings = new ArrayList<>();
        for (Object item : asList(doc.get("findings"))) {
            Map<String, Object> finding = asMap(item);
            findings.add(new SiValidation.Finding(text(finding.get("code")), text(finding.get("detail"))));
        }
        Long rowMax = doc.get("row_max_bytes") instanceof Number max ? Long.valueOf(max.longValue()) : null;
        return new SiValidation(ok, row, rowBytes.longValue(), rowMax, findings);
    }

    /**
     * 把任意字串嚴格 percent-encode 成<b>單一路徑段</b>：只有 RFC 3986 的非保留字元（{@code A-Z a-z 0-9 - . _ ~}）原樣，其餘位元組（UTF-8）
     * 一律 {@code %XX}（大寫十六進位）——所以 {@code /}、{@code ?}、{@code #}、{@code ;}、{@code \}、{@code %} 與空白都不可能改變路徑結構。
     * 整段恰為 {@code .} 或 {@code ..} 時，點字元也編成 {@code %2E}：非保留字元的編碼等價於原字元，HTTP 堆疊可能把 {@code ..} 當路徑穿越
     * 正規化掉（TCS-P1b R7、⚖ 29）。
     */
    static String pathSegment(String raw) {
        StringBuilder out = new StringBuilder();
        for (byte b : raw.getBytes(StandardCharsets.UTF_8)) {
            int c = b & 0xFF;
            boolean unreserved = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')
                    || c == '-' || c == '.' || c == '_' || c == '~';
            if (unreserved) {
                out.append((char) c);
            } else {
                out.append('%').append(HEX[c >> 4]).append(HEX[c & 0xF]);
            }
        }
        String encoded = out.toString();
        return ".".equals(encoded) || "..".equals(encoded) ? encoded.replace(".", "%2E") : encoded;
    }

    private static List<String> strings(Object value) {
        List<String> out = new ArrayList<>();
        for (Object item : asList(value)) {
            if (item != null) {
                out.add(item.toString());
            }
        }
        return out;
    }

    private static double decimalOrZero(Object value) {
        return value instanceof Number n ? n.doubleValue() : 0.0;
    }

    /** 權杖標頭（backend 有設才有）：空 map＝沒設。 */
    private Map<String, String> writeToken() {
        return endpoints.sddWriteToken().map(token -> Map.of(TOKEN_HEADER, token)).orElse(Map.of());
    }

    /** SelfImproving 寫入權杖標頭（與 SDD 權杖是兩個獨立的值）：空 map＝沒設。 */
    private Map<String, String> siWriteToken() {
        return endpoints.siWriteToken().map(token -> Map.of(TOKEN_HEADER, token)).orElse(Map.of());
    }

    private static SddFsmState.HumanPending humanPendingOf(Object value) {
        Map<String, Object> map = asMap(value);
        List<Map<String, Object>> items = objects(map.get("items"));
        return new SddFsmState.HumanPending(map.get("count") instanceof Number n ? n.intValue() : items.size(), items);
    }

    private static SddFsmState.RetryHistory retryHistoryOf(Object value) {
        Map<String, Object> map = asMap(value);
        Map<String, Object> last = map.get("last") instanceof Map<?, ?> ? asMap(map.get("last")) : null;
        return new SddFsmState.RetryHistory(map.get("count") instanceof Number n ? n.intValue() : 0, last);
    }

    /** 清單裡的物件項（原樣）；不是物件的項目略過。 */
    private static List<Map<String, Object>> objects(Object value) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (Object item : asList(value)) {
            if (item instanceof Map<?, ?>) {
                out.add(asMap(item));
            }
        }
        return out;
    }

    /** 2xx 但本文不是預期的形狀（契約 §1.7.1：{@code bridge_error}）：與 Bridge 回非 2xx 同為上游錯誤，不是例外 500。 */
    private static UpstreamException malformed(String what) {
        return new UpstreamException.Failure("Bridge 的 " + what + " 回應不是預期的形狀", Map.of("bridgeStatus", 200));
    }

    /**
     * 健康探測（契約 §3.1；v1.4 預設路徑 {@code /health/deep}）：<b>只看 HTTP 狀態碼</b>——2xx 為成功；503 {@code degraded}（引擎自檢未通過）、
     * 其他非 2xx、連線失敗、逾時一律為失敗。回應本文完全不讀：深度探針 200 回應裡的 {@code checks.sdd.ok=false} 只是資訊
     * （主控裁決 Q4：{@code sdd} 檢查不影響 HTTP 狀態，所以與 AutoClaude 批次無關的 SDD 目錄問題不會拉低 Agent 可用率）。
     */
    @Override
    public BridgeHealth health() {
        try {
            int status = client(HEALTH_READ_TIMEOUT, traceId()).get()
                    .uri(endpoints.autoclaudeBase() + endpoints.healthPath())
                    .exchange((request, response) -> response.getStatusCode().value());
            return new BridgeHealth(status >= 200 && status < 300, status);
        } catch (RuntimeException e) {
            LOG.debug("Bridge 健康探測失敗：{}", e.toString());
            return new BridgeHealth(false, 0);
        }
    }

    // ── W3-B2：runs 系列（契約 §3.1；逾時與重試照呼叫總表）──────────────────────────────────────────

    @Override
    public RunStarted startRun(StartRunRequest request) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("run_id", request.runId().toString());
        body.put("project", request.project());
        body.put("execution_path", request.executionPath());
        body.put("playbook", request.playbook());
        body.put("config_overrides", request.configOverrides());
        body.put("env", request.env());
        body.put("fresh", request.fresh());
        Map<String, String> auth = Map.of();
        Duration readTimeout = START_READ_TIMEOUT;
        if (request.sdd() != null) {
            // 帶 sdd 的請求會觸發 FSM 寫入（談判、委派）：須附權杖，讀取逾時放寬到 90 秒（含最多三次 CLI 子行程）
            auth = writeToken();
            if (auth.isEmpty()) {
                throw new ServiceUnavailableException("backend 沒有設定 SDD 寫入權杖（BRIDGE_SDD_WRITE_TOKEN），SDD 批次已停用",
                        ErrorReasons.SDD_WRITE_DISABLED);
            }
            readTimeout = START_SDD_READ_TIMEOUT;
            body.put("sdd", sddBlockOf(request.sdd()));
        }
        Map<String, Object> doc = postJson(runsBase() + "/autoclaude/runs", Map.of(), body, readTimeout, auth);
        List<ExecutionWarning> warnings = new ArrayList<>();
        for (Object item : asList(doc.get("warnings"))) {
            Map<String, Object> warning = asMap(item);
            if (text(warning.get("code")) != null) {
                warnings.add(new ExecutionWarning(text(warning.get("code")), null, text(warning.get("detail"))));
            }
        }
        return new RunStarted(text(doc.get("run_id")), statusOf(doc.get("status")),
                doc.get("pid") instanceof Number n ? n.intValue() : null, text(doc.get("workspace")),
                text(doc.get("bridge_instance")), warnings);
    }

    /** {@code sdd} 區塊的線上形狀（snake_case；沒有 {@code spec_file} 則省略該鍵）。 */
    private static Map<String, Object> sddBlockOf(SddBlock block) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("spec_dir", block.specDir());
        if (block.specFile() != null && !block.specFile().isBlank()) {
            out.put("spec_file", block.specFile());
        }
        out.put("fsm_project", block.fsmProject());
        out.put("root", block.root());
        out.put("approver", block.approver());
        return out;
    }

    @Override
    public BridgeStatus pauseRun(UUID runId) {
        return statusOf(postJson(runsBase() + "/autoclaude/runs/" + runId + ":pause", Map.of(), PAUSE_READ_TIMEOUT)
                .get("status"));
    }

    @Override
    public BridgeStatus resumeRun(UUID runId, Map<String, String> env) {
        Map<String, Object> body = env == null || env.isEmpty() ? Map.of() : Map.of("env", env);
        // console-api 不記錄批次是否為 SDD，所以有設權杖就一律附（Bridge 只對 SDD run 驗；D-115-18）
        return statusOf(postJson(runsBase() + "/autoclaude/runs/" + runId + ":resume", Map.of(), body,
                RESUME_READ_TIMEOUT, writeToken()).get("status"));
    }

    @Override
    public BridgeStatus stopRun(UUID runId) {
        return statusOf(postJson(runsBase() + "/autoclaude/runs/" + runId + ":stop", Map.of(), STOP_READ_TIMEOUT)
                .get("status"));
    }

    @Override
    public void restoreRun(UUID runId, UUID checkpointId, Map<String, String> env) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("checkpoint_id", checkpointId.toString());
        if (env != null && !env.isEmpty()) {
            body.put("env", env);
        }
        postJson(runsBase() + "/autoclaude/runs/" + runId + "/restore", Map.of(), body, RESTORE_READ_TIMEOUT,
                writeToken());
    }

    @Override
    public RunSnapshot getRun(UUID runId) {
        Map<String, Object> doc = asMap(getJson(runsBase() + "/autoclaude/runs/" + runId, GET_READ_TIMEOUT));
        return new RunSnapshot(text(doc.get("run_id")), statusOf(doc.get("status")),
                BridgeText.withoutPid(text(doc.get("reason"))),
                intOrNull(doc.get("pid")), text(doc.get("started_at")), text(doc.get("completed_at")),
                intOrNull(doc.get("exit_code")), text(doc.get("current_step")), intOrNull(doc.get("current_step_number")),
                intOrZero(doc.get("attempt")), intOrZero(doc.get("completed_steps")), intOrZero(doc.get("total_steps")),
                doc.get("tokens_used") instanceof Number n ? n.longValue() : 0L, intOrZero(doc.get("last_event_seq")),
                text(doc.get("project")), text(doc.get("execution_path")), text(doc.get("bridge_instance")),
                resourcesOf(doc.get("resources")));
    }

    /**
     * {@code RunStateOut.resources}（契約 §3.1.2）：{@code cpu_percent／rss_bytes／process_count／sampled_at} 四個欄位都在且型別正確才採用，
     * 值<b>原樣</b>帶出（不重算、不四捨五入、不夾範圍）。Bridge 回 null、回應缺這個鍵（舊版 Bridge）、不是物件或欄位不齊一律回 null——
     * 資源取樣只是顯示用的輔助資料，寧可沒有，也不讓它拖垮整個詳情回應，更不猜測缺的欄位。
     */
    static ResourceUsage resourcesOf(Object value) {
        if (!(value instanceof Map<?, ?> map)) {
            return null;
        }
        if (map.get("cpu_percent") instanceof Number cpu && map.get("rss_bytes") instanceof Number rss
                && map.get("process_count") instanceof Number processes && map.get("sampled_at") instanceof String at
                && !at.isBlank()) {
            return new ResourceUsage(cpu.doubleValue(), rss.longValue(), processes.intValue(), at);
        }
        LOG.debug("Bridge 的 resources 欄位不齊或型別不符，視為沒有資料");
        return null;
    }

    @Override
    public List<BridgeEvent> listEvents(UUID runId, int after, int limit) {
        Object doc = getJson(runsBase() + "/autoclaude/runs/" + runId + "/events?after=" + after + "&limit=" + limit,
                EVENTS_READ_TIMEOUT);
        List<BridgeEvent> events = new ArrayList<>();
        for (Object item : asList(doc)) {
            Map<String, Object> map = new LinkedHashMap<>(asMap(item));
            String event = text(map.remove("event"));
            events.add(eventOf(event, map, null));
        }
        return events;
    }

    @Override
    public void streamEvents(UUID runId, int afterSeq, Duration idleTimeout, Consumer<BridgeEvent> handler) {
        HttpClient http = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(STREAM_CONNECT_TIMEOUT).build();
        HttpRequest request = HttpRequest.newBuilder(URI.create(runsBase() + "/autoclaude/runs/" + runId
                + "/stream?after=" + afterSeq)).header("Accept", "text/event-stream").header(TRACE_HEADER, traceId())
                .GET().build();
        IdleWatchdog watchdog = new IdleWatchdog(Thread.currentThread(), idleTimeout);
        try {
            watchdog.arm();
            HttpResponse<Stream<String>> response = http.send(request, HttpResponse.BodyHandlers.ofLines());
            if (response.statusCode() != 200) {
                try (Stream<String> body = response.body()) {
                    handle(HttpStatusCode.valueOf(response.statusCode()), String.join("\n", body.toList()));
                }
                throw new UpstreamException.Failure("Bridge 事件串流回了非預期的狀態 " + response.statusCode(),
                        Map.of("bridgeStatus", response.statusCode()));
            }
            try (Stream<String> lines = response.body()) {
                SseFrameParser parser = new SseFrameParser(handler);
                for (Iterator<String> it = lines.iterator(); it.hasNext();) {
                    watchdog.arm();
                    parser.feed(it.next());
                }
            }
        } catch (InterruptedException e) {
            throw streamInterrupted(watchdog, e);
        } catch (UncheckedIOException e) {
            throw watchdog.fired() || e.getCause() instanceof InterruptedIOException
                    ? streamInterrupted(watchdog, e) : translateIo(e.getCause());
        } catch (IOException e) {
            throw watchdog.fired() ? streamInterrupted(watchdog, e) : translateIo(e);
        } finally {
            watchdog.disarm();
        }
    }

    /** 看門狗逾時（不論 JDK 把中斷包成 {@code InterruptedException}、{@code InterruptedIOException} 或一般 {@code IOException}）＝閒置逾時。 */
    private static UpstreamException streamInterrupted(IdleWatchdog watchdog, Exception cause) {
        if (watchdog.fired()) {
            return new UpstreamException.TimedOut("Engine Bridge 事件串流閒置逾時");
        }
        Thread.currentThread().interrupt();
        return new UpstreamException.Unavailable("Engine Bridge 事件串流被中斷：" + cause.getClass().getSimpleName());
    }

    private static UpstreamException translateIo(Throwable e) {
        for (Throwable t = e; t != null; t = t.getCause()) {
            if (t instanceof HttpTimeoutException || t instanceof SocketTimeoutException) {
                return new UpstreamException.TimedOut("Engine Bridge 逾時：" + t.getClass().getSimpleName());
            }
        }
        return new UpstreamException.Unavailable("與 Engine Bridge 通訊失敗：" + e.getClass().getSimpleName());
    }

    private String runsBase() {
        return endpoints.autoclaudeBase();
    }

    private static BridgeEvent eventOf(String event, Map<String, Object> data, Integer fallbackSeq) {
        int seq = data.get("seq") instanceof Number n ? n.intValue() : fallbackSeq == null ? 0 : fallbackSeq;
        for (String key : FREE_TEXT_KEYS) {
            if (data.get(key) instanceof String value) {
                data.put(key, BridgeText.withoutPid(value));
            }
        }
        return new BridgeEvent(seq, text(data.get("ts")), event == null ? "" : event, data);
    }

    private static BridgeStatus statusOf(Object value) {
        return BridgeStatus.parse(text(value)).orElseThrow(() -> new UpstreamException.Failure(
                "Bridge 回了無法辨識的狀態：" + value, Map.of("bridgeStatus", 200)));
    }

    private static Integer intOrNull(Object value) {
        return value instanceof Number n ? Integer.valueOf(n.intValue()) : null;
    }

    private static int intOrZero(Object value) {
        return value instanceof Number n ? n.intValue() : 0;
    }

    /** GET＋JSON 解析（物件或陣列）；連線失敗與讀取逾時重試 2 次（200ms 退避，契約 §3.1），4xx／5xx 不重試。 */
    private Object getJson(String url, Duration readTimeout) {
        return getJson(url, Map.of(), readTimeout, GET_RETRIES);
    }

    /**
     * 同上，重試次數由呼叫端決定（引擎狀態查詢不重試：契約 §3.1，{@code retries=0}），且 {@code urlTemplate} 可帶 URI 變數
     * （{@code {project}}、{@code {root}}）：變數值嚴格 percent-encode，所以 CJK、空白、{@code :} 與路徑分隔符都能安全定址。
     */
    private Object getJson(String urlTemplate, Map<String, Object> variables, Duration readTimeout, int retries) {
        return getJson(rest -> rest.get().uri(urlTemplate, variables), readTimeout, retries);
    }

    /**
     * 上面兩個的共同核心：{@code request} 決定請求的目標（範本加變數，或已編碼好的 {@link URI}）；重試與錯誤分流相同。
     * 重試行為不變：連線失敗與讀取逾時重試 {@code retries} 次，4xx／5xx 不重試。
     */
    private Object getJson(Function<RestClient, RestClient.RequestHeadersSpec<?>> request, Duration readTimeout,
                           int retries) {
        String trace = traceId();
        // 至少嘗試一次；最後一次失敗（連線失敗或讀取逾時）就把它丟出去，其餘錯誤（4xx／5xx）在 handle 內直接丟出、不重試
        for (int attempt = 0;; attempt++) {
            if (attempt > 0) {
                try {
                    Thread.sleep(GET_RETRY_BACKOFF_MS);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    throw new UpstreamException.Unavailable("等待重試時被中斷");
                }
            }
            UpstreamException failure;
            try {
                return request.apply(client(readTimeout, trace)).exchange((req, response) -> {
                    HttpStatusCode status = response.getStatusCode();
                    String body = readBody(response.getBody());
                    if (status.is2xxSuccessful()) {
                        return parseAny(body);
                    }
                    handle(status, body);
                    return null;
                });
            } catch (ResourceAccessException e) {
                failure = translate(e);
            } catch (UpstreamException.Unavailable | UpstreamException.TimedOut e) {
                failure = e;
            }
            if (attempt >= retries) {
                throw failure;
            }
        }
    }

    private static Object parseAny(String body) {
        try {
            return JSON.readValue(body, Object.class);
        } catch (JacksonException e) {
            throw new UpstreamException.Failure("Bridge 回了無法解析的成功本文", Map.of("bridgeStatus", 200));
        }
    }

    /** SSE 閒置看門狗：每收到一行（含 keep-alive 註解）就重新計時；逾時中斷讀取執行緒（Bridge 每 15 秒送 keep-alive）。 */
    private static final class IdleWatchdog {

        private final Thread reader;
        private final Duration idleTimeout;
        private final AtomicBoolean fired = new AtomicBoolean(false);
        private final AtomicReference<ScheduledFuture<?>> pending = new AtomicReference<>();

        IdleWatchdog(Thread reader, Duration idleTimeout) {
            this.reader = reader;
            this.idleTimeout = idleTimeout;
        }

        void arm() {
            ScheduledFuture<?> next = WATCHDOG.schedule(() -> {
                fired.set(true);
                reader.interrupt();
            }, idleTimeout.toMillis(), TimeUnit.MILLISECONDS);
            ScheduledFuture<?> previous = pending.getAndSet(next);
            if (previous != null) {
                previous.cancel(false);
            }
        }

        boolean fired() {
            return fired.get();
        }

        void disarm() {
            ScheduledFuture<?> previous = pending.getAndSet(null);
            if (previous != null) {
                previous.cancel(false);
            }
            if (fired.get()) {
                Thread.interrupted();
            }
        }
    }

    /** 把 SSE 文字行組回事件（{@code event:}、{@code data:}，空行結尾）；註解行與 {@code retry:} 忽略。 */
    private static final class SseFrameParser {

        private final Consumer<BridgeEvent> handler;
        private String event;
        private String id;
        private final StringBuilder data = new StringBuilder();

        SseFrameParser(Consumer<BridgeEvent> handler) {
            this.handler = handler;
        }

        void feed(String line) {
            if (line.isEmpty()) {
                dispatch();
            } else if (line.startsWith(":")) {
                return;
            } else if (line.startsWith("event:")) {
                event = line.substring(6).strip();
            } else if (line.startsWith("id:")) {
                id = line.substring(3).strip();
            } else if (line.startsWith("data:")) {
                if (!data.isEmpty()) {
                    data.append('\n');
                }
                data.append(line.substring(5).stripLeading());
            }
        }

        private void dispatch() {
            String name = event;
            String payload = data.toString();
            String frameId = id;
            event = null;
            id = null;
            data.setLength(0);
            if (name == null || payload.isEmpty()) {
                return;
            }
            Map<String, Object> map;
            try {
                map = new LinkedHashMap<>(asMap(JSON.readValue(payload, Object.class)));
            } catch (JacksonException e) {
                LOG.warn("略過無法解析的 Bridge 事件本文：{}", payload.length() > 200 ? payload.substring(0, 200) : payload);
                return;
            }
            Integer fallback = null;
            if (frameId != null && frameId.matches("[0-9]+")) {
                fallback = Integer.valueOf(frameId);
            }
            map.remove("event");
            handler.accept(eventOf(name, map, fallback));
        }
    }

    // ── 內部 ──────────────────────────────────────────────────────────────────

    /** 本次呼叫要帶的 traceId：目前執行緒 MDC 的值；沒有（背景工作）就新產一個 UUID。 */
    private static String traceId() {
        String current = MDC.get(TRACE_MDC_KEY);
        return current == null || current.isBlank() ? UUID.randomUUID().toString() : current;
    }

    private RestClient client(Duration readTimeout, String traceId) {
        RestClient.Builder copy = builder.clone();
        ClientHttpRequestFactory factory = factories.create(CONNECT_TIMEOUT, readTimeout);
        if (factory != null) {
            copy.requestFactory(factory);
        }
        copy.defaultHeader(TRACE_HEADER, traceId);
        return copy.build();
    }

    private Map<String, Object> postJson(String url, Object body, Duration readTimeout) {
        return postJson(url, Map.of(), body, readTimeout, Map.of());
    }

    /**
     * POST＋JSON：{@code urlTemplate} 可帶 URI 變數（嚴格 percent-encode）；{@code headers} 是額外標頭（目前只有 {@value #TOKEN_HEADER}）。
     * 🔴 標頭值（權杖）只放進請求，不進日誌、例外訊息或錯誤封包。
     */
    private Map<String, Object> postJson(String urlTemplate, Map<String, Object> variables, Object body,
                                         Duration readTimeout, Map<String, String> headers) {
        String payload = JSON.writeValueAsString(body);
        try {
            return client(readTimeout, traceId()).post().uri(urlTemplate, variables)
                    .headers(h -> headers.forEach(h::set)).contentType(MediaType.APPLICATION_JSON).body(payload)
                    .exchange((request, response) -> handle(response.getStatusCode(), readBody(response.getBody())));
        } catch (ResourceAccessException e) {
            throw translate(e);
        }
    }

    /**
     * POST 一份<b>原樣</b>的 JSON 文字（SelfImproving 稽核檔與預檢本文）：位元組＝字串的 UTF-8，不經 Jackson 重新序列化——稽核 JSON 是
     * {@code audit_sha256} 與 HMAC 的對象，多一個空白或換個鍵序都會讓主機端 CLI 以 AUDIT-MAC-MISMATCH 拒收。{@code uri} 是已編碼好的完整網址
     * （不交給範本引擎，同 {@link #siExport}）。🔴 標頭值（權杖）只放進請求，不進日誌、例外訊息或錯誤封包。
     */
    private Map<String, Object> postRaw(URI uri, String payload, Duration readTimeout, Map<String, String> headers) {
        try {
            return client(readTimeout, traceId()).post().uri(uri).headers(h -> headers.forEach(h::set))
                    .contentType(MediaType.APPLICATION_JSON).body(payload.getBytes(StandardCharsets.UTF_8))
                    .exchange((request, response) -> handle(response.getStatusCode(), readBody(response.getBody())));
        } catch (ResourceAccessException e) {
            throw translate(e);
        }
    }

    private static Map<String, Object> handle(HttpStatusCode status, String body) {
        if (status.is2xxSuccessful()) {
            return parseObject(body, "Bridge 回了無法解析的成功本文");
        }
        Map<String, Object> error = parseErrorBody(body);
        String reason = text(error.get("reason"));
        // 503 sdd_write_disabled 是「明確拒絕」（權杖沒設＝這個動詞停用），與 4xx 同走 BridgeRejectedException，由用例轉成 503；其餘 5xx 才是故障
        boolean writeDisabled = status.value() == 503
                && (SDD_WRITE_DISABLED.equals(reason) || SI_WRITE_DISABLED.equals(reason));
        // 503 si_unavailable 同理：SelfImproving 資料面不可用是 Bridge 明確回報的狀態（帶 cause 與 detail），不是上游故障
        boolean siUnavailable = status.value() == 503 && SI_UNAVAILABLE.equals(reason);
        if (status.is4xxClientError() || writeDisabled || siUnavailable) {
            List<Map<String, Object>> violations = new ArrayList<>();
            for (Object item : asList(error.get("violations"))) {
                violations.add(asMap(item));
            }
            throw new BridgeRejectedException(status.value(), reason == null ? "" : reason, text(error.get("gate")),
                    detailText(error.get("detail")), violations, error);
        }
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("bridgeStatus", status.value());
        if (reason != null && !reason.isEmpty()) {
            details.put("bridgeReason", reason);
        }
        throw new UpstreamException.Failure("Bridge 回了非預期的錯誤（HTTP " + status.value()
                + (reason == null || reason.isEmpty() ? "" : "，" + reason) + "）", details);
    }

    /**
     * 連線階段的失敗（拒絕、DNS、連線逾時）→ {@code Unavailable}，<b>確定沒有送達</b>；讀取逾時 → {@code TimedOut}（請求已送出）；
     * 其餘通訊失敗（送出後連線被重設、提前 EOF…）→ {@code Unavailable} 並標 {@link UpstreamException.Unavailable#deliveryUncertain()}：
     * Bridge 可能已處理請求（SelfImproving 寫入據此決定保留或補償刪除稽核列，TCS-SelfImprovingDecide-P2b W11）。
     */
    private static UpstreamException translate(ResourceAccessException e) {
        for (Throwable t = e; t != null; t = t.getCause()) {
            if (t instanceof HttpConnectTimeoutException || t instanceof ConnectException
                    || t instanceof UnknownHostException) {
                return new UpstreamException.Unavailable("無法連線到 Engine Bridge：" + t.getClass().getSimpleName());
            }
            if (t instanceof HttpTimeoutException || t instanceof SocketTimeoutException) {
                return new UpstreamException.TimedOut("Engine Bridge 逾時：" + t.getClass().getSimpleName());
            }
        }
        return new UpstreamException.Unavailable("與 Engine Bridge 通訊失敗：" + e.getClass().getSimpleName(), true, Map.of());
    }

    private static String readBody(InputStream stream) throws IOException {
        byte[] bytes = stream.readNBytes(MAX_BODY_BYTES);
        return new String(bytes, StandardCharsets.UTF_8);
    }

    private static Map<String, Object> parseObject(String body, String failure) {
        try {
            return JSON.readValue(body, OBJECT);
        } catch (JacksonException e) {
            throw new UpstreamException.Failure(failure, Map.of("bridgeStatus", 200));
        }
    }

    /** 錯誤本文解析失敗不應遮蔽真正的狀態碼：退回空物件。 */
    private static Map<String, Object> parseErrorBody(String body) {
        try {
            return body == null || body.isBlank() ? Map.of() : JSON.readValue(body, OBJECT);
        } catch (JacksonException e) {
            return Map.of();
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }

    private static List<?> asList(Object value) {
        return value instanceof List<?> list ? list : List.of();
    }

    private static String text(Object value) {
        return value == null ? null : value.toString();
    }

    /**
     * Bridge 錯誤封包的 {@code detail}：字串原樣；物件（{@code fsm_state_conflict}、{@code spec_digest_changed} 的 {@code detail} 是物件，
     * 契約 §6.8.6 靜默處 #8）轉成一行 {@code k=v; k=v}——完整物件另由 {@code BridgeRejectedException.detailObject()} 取。
     */
    private static String detailText(Object detail) {
        if (detail instanceof Map<?, ?> map) {
            return map.entrySet().stream().map(e -> e.getKey() + "=" + e.getValue()).collect(Collectors.joining("; "));
        }
        return text(detail);
    }
}
