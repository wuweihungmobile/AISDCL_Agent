package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.ResourceUsage;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Engine Bridge 的出站埠（契約 §3.1 呼叫總表；Bridge 只有 console-api 以服務身分呼叫，內網、無認證）。
 *
 * <p>本棒（W3-B1）只放匯入需要的四個方法：{@code decompose}、{@code approveDraft}、{@code sddCompile}、{@code health}；
 * 第二棒（W3-B2）在<b>同一介面</b>補 runs 系列（{@code startRun}、{@code pauseRun}…，方法名照契約 §3.1 最後一欄）。
 *
 * <p>錯誤約定：連線失敗 → {@code UpstreamException.Unavailable}（502）；讀取逾時 → {@code UpstreamException.TimedOut}
 * （504）；Bridge 回 5xx → {@code UpstreamException.Failure}（502，details 帶 bridgeStatus／bridgeReason）；
 * Bridge 回 4xx → {@link BridgeRejectedException}（由用例依端點語意對映成 409／422…，契約 §3.2）。
 */
public interface AgentBridge {

    /**
     * 路徑 C 的拆解請求（{@code POST /autoclaude/decompose}）。
     *
     * @param minimaxOverrides {@code config_overrides.minimax}（base_url／model／timeout_seconds）；沒有金鑰時為 null
     */
    record DecomposeRequest(String goal, String context, String project, int maxSteps,
                            Map<String, Object> minimaxOverrides) {
    }

    /** Bridge decompose 回傳的步驟（{@code playbook.tasks[]}；已是拓撲序，不含依賴資訊）。 */
    record DraftStep(String stepId, String name, String prompt, String evaluatorCommand) {
    }

    record DecomposeResult(String draftId, String reasoning, List<DraftStep> steps) {
    }

    /**
     * {@code /sdd/compile} 回傳的任務（{@code SddToPlaybookAdapter.compile_tasks} 的 PlaybookTask）。
     *
     * @param weakRegex Bridge 的 {@code weak_regex}：規格的驗收 regex 被判定為太弱
     */
    record SddTask(String stepId, String name, String prompt, String expectedOutputRegex, String evaluatorCommand,
                   boolean weakRegex) {
    }

    record SddCompileResult(String scenario, String specPath, String digest, List<SddTask> tasks) {
    }

    /** 健康探測結果（{@code GET {autoclaude.healthCheckPath}}）；B2 的探測環與通知摘要使用。 */
    record BridgeHealth(boolean ok, int httpStatus) {
    }

    /** Bridge 回了 4xx：帶回它的錯誤封包欄位（{@code {code,reason,gate?,detail?,violations?,…}}）。 */
    final class BridgeRejectedException extends RuntimeException {

        private static final long serialVersionUID = 1L;

        private final int status;
        private final String reason;
        private final String gate;
        private final String detail;
        private final transient List<Map<String, Object>> violations;
        private final transient Map<String, Object> body;

        public BridgeRejectedException(int status, String reason, String gate, String detail,
                                       List<Map<String, Object>> violations, Map<String, Object> body) {
            super("Bridge 回應 " + status + " " + reason);
            this.status = status;
            this.reason = reason;
            this.gate = gate;
            this.detail = detail;
            this.violations = violations == null ? List.of() : List.copyOf(violations);
            this.body = body == null ? Map.of() : Map.copyOf(body);
        }

        public int status() {
            return status;
        }

        /** Bridge 的 {@code reason}（例：{@code spec_not_found}、{@code draft_not_found}）；沒有則為空字串。 */
        public String reason() {
            return reason;
        }

        /** 有界閘名稱（decompose 的 422）；沒有則為 null。 */
        public String gate() {
            return gate;
        }

        public String detail() {
            return detail;
        }

        public List<Map<String, Object>> violations() {
            return violations;
        }

        /** 完整的 Bridge 錯誤本文（轉成 details 時逐項原樣帶出）。 */
        public Map<String, Object> body() {
            return body;
        }
    }

    /**
     * 路徑 C：{@code POST /autoclaude/decompose}。
     *
     * @param readTimeout 讀取逾時（契約 §3.1：{@code model.timeout}＋15 秒）
     */
    DecomposeResult decompose(DecomposeRequest request, Duration readTimeout);

    /** signoff 路徑 C：{@code POST /autoclaude/decompose/{draft_id}:approve}；Bridge 的 409 {@code already_signed_off} 由呼叫端視為成功。 */
    void approveDraft(String draftId, String approver);

    /** 路徑 A：{@code POST /sdd/compile {spec_dir}}。 */
    SddCompileResult sddCompile(String specDir);

    /** 健康探測（不丟例外：連不上就是 {@code ok=false}）。 */
    BridgeHealth health();

    // ── W3-B2：runs 系列（契約 §3.1 呼叫總表；方法名照最後一欄）──────────────────────────────────────

    /**
     * {@code POST /autoclaude/runs} 的請求（Bridge 的 {@code RunCreateIn}，{@code extra=forbid}）。
     *
     * @param playbook        {@code PlaybookIn} 的 JSON 形狀（{@code PlaybookBuilder.Playbook#toMap()}）
     * @param configOverrides 頂層鍵限 Bridge 白名單；機密一律走 {@code env}
     */
    record StartRunRequest(UUID runId, String project, String executionPath, Map<String, Object> playbook,
                           Map<String, Object> configOverrides, Map<String, String> env, boolean fresh) {
    }

    /** {@code POST /autoclaude/runs} 的 201 回應。 */
    record RunStarted(String runId, BridgeStatus status, Integer pid, String workspace, String bridgeInstance) {
    }

    /**
     * {@code GET /autoclaude/runs/{id}} 的快照（{@code RunStateOut}）。時間欄位保留 Bridge 的原字串（UTC，{@code +00:00}）。
     *
     * @param resources 引擎行程樹的資源取樣（v1.3，D-12；契約 §3.1.2）；Bridge 回 null、回應缺這個鍵（舊版 Bridge）或欄位不齊時為 null
     */
    record RunSnapshot(String runId, BridgeStatus status, String reason, Integer pid, String startedAt,
                       String completedAt, Integer exitCode, String currentStep, Integer currentStepNumber,
                       int attempt, int completedSteps, int totalSteps, long tokensUsed, int lastEventSeq,
                       String project, String executionPath, String bridgeInstance, ResourceUsage resources) {
    }

    /**
     * Bridge 的一則事件（SSE 與 {@code GET …/events} 共用的形狀）：{@code event} 是事件名
     * （{@code log／status／step／token／alert／review-request}），{@code data} 是扁平的欄位封包
     * （含 {@code seq}、{@code ts}，已去掉 {@code event} 鍵——REST 重播由介面卡自行取出並移除，契約 §2.7）。
     */
    record BridgeEvent(int seq, String ts, String event, Map<String, Object> data) {

        public BridgeEvent {
            data = data == null ? Map.of() : Map.copyOf(data);
        }

        public String text(String key) {
            Object value = data.get(key);
            return value == null ? null : value.toString();
        }

        public Integer integer(String key) {
            return data.get(key) instanceof Number n ? Integer.valueOf(n.intValue()) : null;
        }

        public Long longValue(String key) {
            return data.get(key) instanceof Number n ? Long.valueOf(n.longValue()) : null;
        }

        public Double decimal(String key) {
            return data.get(key) instanceof Number n ? Double.valueOf(n.doubleValue()) : null;
        }
    }

    /** {@code GET …/checkpoints} 的一筆（{@code CheckpointOut}；沒有 {@code completedSteps}，Console 以 DB 為準）。 */
    record BridgeCheckpoint(String checkpointId, String name, String createdAt, int stepIdx, String stepId,
                            boolean automatic) {
    }

    /** {@code POST /autoclaude/runs}（201）；非冪等，失敗即由呼叫端補償。 */
    RunStarted startRun(StartRunRequest request);

    /** {@code :pause}（202）：只收 RUNNING；PAUSING 時冪等。回 Bridge 的新狀態（通常 PAUSING）。 */
    BridgeStatus pauseRun(UUID runId);

    /** {@code :resume}（202）：只收 PAUSED；body 可帶 {@code env}（Bridge 重啟後請求層 env 會遺失）。 */
    BridgeStatus resumeRun(UUID runId, Map<String, String> env);

    /** {@code :stop}（202）：收 RUNNING／PAUSING／PAUSED；PAUSED 者即時收尾為 CANCELLED。 */
    BridgeStatus stopRun(UUID runId);

    /** {@code POST …/restore {checkpoint_id}}（202）：收 PAUSED 與三個終態。 */
    void restoreRun(UUID runId, UUID checkpointId, Map<String, String> env);

    /** {@code GET /autoclaude/runs/{id}}：Bridge 不認得該 run 時丟 {@link BridgeRejectedException}（404 {@code run_not_found}）。 */
    RunSnapshot getRun(UUID runId);

    /** {@code GET …/events?after=&limit=}（裸陣列；已正規化成與 SSE 相同形狀的 {@link BridgeEvent}）。 */
    List<BridgeEvent> listEvents(UUID runId, int after, int limit);

    /** {@code GET …/checkpoints}（審核 RETRY 找 {@code step_idx} 快照時使用；契約的 checkpoints 端點以 DB 為準）。 */
    List<BridgeCheckpoint> listCheckpoints(UUID runId);

    /**
     * 開事件串流（{@code GET …/stream?after=<last_seq>}）並對每則事件呼叫 {@code handler}，<b>阻塞</b>到串流結束
     * （正常結束＝伺服器關閉連線）；閒置超過 {@code idleTimeout}（Bridge 每 15 秒送 keep-alive，契約 §3.1 取 45 秒）、
     * 連線失敗、{@code handler} 丟例外都以例外離開，由呼叫端決定退避重連。
     * Bridge 不認得該 run（404）丟 {@link BridgeRejectedException}。
     */
    void streamEvents(UUID runId, int afterSeq, Duration idleTimeout, java.util.function.Consumer<BridgeEvent> handler);
}
