package com.aisdlc.console.application.port.out;

import com.aisdlc.console.domain.model.engine.SddFsmList;
import com.aisdlc.console.domain.model.engine.SddFsmState;
import com.aisdlc.console.domain.model.engine.SddVersion;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.aisdlc.console.domain.model.execution.ExecutionRtm;
import com.aisdlc.console.domain.model.execution.ExecutionWarning;
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
     * @param weakRegex       Bridge 的 {@code weak_regex}：規格的驗收 regex 被判定為太弱
     * @param maxRetries      Bridge 的 {@code max_retries}（SCG-4 型 5、SCG-5 型 2；G-08）；Bridge 沒給為 null（落庫取預設 3）
     * @param maintainContext Bridge 的 {@code maintain_context}（跨 AC 脈絡隔離；G-08）；Bridge 沒給為 null（不放進 {@code passCriteriaSpec}）
     * @param specDigest      Bridge 的 {@code spec_digest}（逐任務；與規格層級的 {@code digest} 相同）；沒給為 null
     */
    record SddTask(String stepId, String name, String prompt, String expectedOutputRegex, String evaluatorCommand,
                   boolean weakRegex, Integer maxRetries, Boolean maintainContext, String specDigest) {

        /** v1.4 的六欄（沒有 G-08 補齊的欄位）。 */
        public SddTask(String stepId, String name, String prompt, String expectedOutputRegex,
                       String evaluatorCommand, boolean weakRegex) {
            this(stepId, name, prompt, expectedOutputRegex, evaluatorCommand, weakRegex, null, null, null);
        }
    }

    /** {@code /sdd/compile} 回應的 {@code warnings[]}（{@code {code, detail}}；目前只有 {@code state_dir_not_ignored}）。 */
    record SddCompileWarning(String code, String detail) {
    }

    /**
     * {@code POST /sdd/compile} 的回應（契約 §3.1.4 (e)、§3.3.2）。
     *
     * @param specPath          實際採用的規格檔的<b>絕對路徑</b>（Console 用它填 {@code sddSpecFile}、用它的父目錄填 {@code sddSpecDir}）
     * @param specFile          實際採用的規格檔，相對 {@code spec_dir} 的 POSIX 路徑；舊版 Bridge 缺鍵為 null
     * @param fsmProject        通過凍結閘的狀態檔的<b>標準鍵</b>（Console 用它寫回 {@code sddProject}）；舊版 Bridge 缺鍵為 null
     * @param frozenDigest      {@code verified}（狀態檔有摘要且與現檔吻合）或 {@code absent}（沒有任何階段帶摘要）；舊版缺鍵為 null
     * @param specFormatVersion 規格格式版本（只顯示與稽核，不閘控）
     * @param unmappedAtIds     規格<b>宣告位置</b>出現、卻沒被編成 step 的 AT 字樣（正向；與 RTM 的逆向 {@code unmappedAtIds} 是兩個不同層的欄位）；
     *                          缺則空
     */
    record SddCompileResult(String scenario, String specPath, String digest, List<SddTask> tasks, String specFile,
                            String fsmProject, String frozenDigest, String specFormatVersion,
                            List<String> unmappedAtIds, List<SddCompileWarning> warnings) {

        public SddCompileResult {
            unmappedAtIds = unmappedAtIds == null ? List.of() : List.copyOf(unmappedAtIds);
            warnings = warnings == null ? List.of() : List.copyOf(warnings);
        }

        /** v1.4 的四欄（沒有 v1.5 的選檔、標準鍵、摘要狀態與出聲資訊）。 */
        public SddCompileResult(String scenario, String specPath, String digest, List<SddTask> tasks) {
            this(scenario, specPath, digest, tasks, null, null, null, null, List.of(), List.of());
        }
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

        /**
         * Bridge 的 {@code detail} 是<b>物件</b>時的完整內容（{@code fsm_state_conflict}：{@code current_state}、{@code expected_state?}、
         * {@code run_id?}、{@code run_status?}、{@code reason?}；{@code spec_digest_changed}：{@code pair}、{@code doc}、各摘要；契約 §6.8.6 #8）；
         * {@code detail} 是字串或缺席時為空。Backend 一律只讀 {@code detail}，不依賴封包頂層的同名過渡欄位。
         */
        @SuppressWarnings("unchecked")
        public Map<String, Object> detailObject() {
            return body.get("detail") instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
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

    /**
     * 路徑 A：{@code POST /sdd/compile {spec_dir, spec_file?, fsm_project?}}（契約 §3.1.4 (e)）。{@code specFile}（相對 {@code specDir}
     * 的 POSIX 路徑，或其下的絕對路徑）與 {@code fsmProject}（FSM 專案名的有效值，<b>原樣</b>送出——Backend 不淨化，Bridge 淨化後在回應帶標準鍵）
     * 為 null 時省略該鍵。匯入探測模式只送 {@code specDir}（與已知時的 {@code fsmProject}），不送 {@code specFile}。
     */
    SddCompileResult sddCompile(String specDir, String specFile, String fsmProject);

    /** 健康探測（不丟例外：連不上就是 {@code ok=false}）。 */
    BridgeHealth health();

    // ── W3-B2：runs 系列（契約 §3.1 呼叫總表；方法名照最後一欄）──────────────────────────────────────

    /**
     * {@code POST /autoclaude/runs} 的頂層選填 {@code sdd} 區塊（契約 §1.10.6、§3.1.6；與 {@code playbook} 同層）：範圍內任務全為 SDD 來源時才送。
     * 帶它的請求會觸發 FSM 寫入（談判、委派），所以<b>必須附 {@code X-Bridge-Token}</b>（由出站介面卡依設定附上，這裡不放權杖）。
     *
     * @param specDir    規格目錄（絕對路徑；專案的 {@code sddSpecDir}）
     * @param specFile   規格檔（絕對路徑；專案的 {@code sddSpecFile}）；沒有則省略
     * @param fsmProject <b>有效 FSM 專案</b>（原名或標準鍵皆可，Bridge 一律先淨化）
     * @param root       專案根（專案的 {@code executionPath}）
     * @param approver   簽核人（1～100 字元；Backend 永遠送具名人，ADR-016 §5.2 C-1）
     */
    record SddBlock(String specDir, String specFile, String fsmProject, String root, String approver) {
    }

    /**
     * {@code POST /autoclaude/runs} 的請求（Bridge 的 {@code RunCreateIn}，{@code extra=forbid}）。
     *
     * @param playbook        {@code PlaybookIn} 的 JSON 形狀（{@code PlaybookBuilder.Playbook#toMap()}）
     * @param configOverrides 頂層鍵限 Bridge 白名單；機密一律走 {@code env}
     * @param sdd             SDD 批次的治理區塊；非 SDD 批次為 null（不送這個鍵，行為與 v1.4 完全相同）
     */
    record StartRunRequest(UUID runId, String project, String executionPath, Map<String, Object> playbook,
                           Map<String, Object> configOverrides, Map<String, String> env, boolean fresh,
                           SddBlock sdd) {

        /** 非 SDD 批次（沒有 {@code sdd} 區塊）。 */
        public StartRunRequest(UUID runId, String project, String executionPath, Map<String, Object> playbook,
                               Map<String, Object> configOverrides, Map<String, String> env, boolean fresh) {
            this(runId, project, executionPath, playbook, configOverrides, env, fresh, null);
        }
    }

    /**
     * {@code POST /autoclaude/runs} 的 201 回應。
     *
     * @param warnings Bridge 回的選填 {@code warnings[]}（放行但值得出聲的事，目前只有 {@code sdd_frozen_digest_absent}；
     *                 {@code {code, detail}} 轉成沒有 {@code cause} 的 {@link ExecutionWarning}）；沒有或舊版 Bridge 為空
     */
    record RunStarted(String runId, BridgeStatus status, Integer pid, String workspace, String bridgeInstance,
                      List<ExecutionWarning> warnings) {

        public RunStarted {
            warnings = warnings == null ? List.of() : List.copyOf(warnings);
        }

        public RunStarted(String runId, BridgeStatus status, Integer pid, String workspace, String bridgeInstance) {
            this(runId, status, pid, workspace, bridgeInstance, List.of());
        }
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

    /** {@code POST /autoclaude/runs}（201）；非冪等，失敗即由呼叫端補償。 */
    RunStarted startRun(StartRunRequest request);

    /** {@code :pause}（202）：只收 RUNNING；PAUSING 時冪等。回 Bridge 的新狀態（通常 PAUSING）。 */
    BridgeStatus pauseRun(UUID runId);

    /**
     * {@code :resume}（202）：只收 PAUSED；body 可帶 {@code env}（Bridge 重啟後請求層 env 會遺失）。🔴 讀取逾時 30 秒（v1.5：SDD run 可能多一次
     * {@code delegate-enter}）；backend 有設寫入權杖時<b>一律附 {@code X-Bridge-Token}</b>（console-api 不記錄批次是否為 SDD，Bridge 只對 SDD run 驗，D-115-18）。
     */
    BridgeStatus resumeRun(UUID runId, Map<String, String> env);

    /** {@code :stop}（202）：收 RUNNING／PAUSING／PAUSED；PAUSED 者即時收尾為 CANCELLED。 */
    BridgeStatus stopRun(UUID runId);

    /** {@code POST …/restore {checkpoint_id}}（202）：收 PAUSED 與三個終態。讀取逾時 30 秒、權杖規則同 {@link #resumeRun}。 */
    void restoreRun(UUID runId, UUID checkpointId, Map<String, String> env);

    /** {@code GET /autoclaude/runs/{id}}：Bridge 不認得該 run 時丟 {@link BridgeRejectedException}（404 {@code run_not_found}）。 */
    RunSnapshot getRun(UUID runId);

    /** {@code GET …/events?after=&limit=}（裸陣列；已正規化成與 SSE 相同形狀的 {@link BridgeEvent}）。 */
    List<BridgeEvent> listEvents(UUID runId, int after, int limit);

    /**
     * 開事件串流（{@code GET …/stream?after=<last_seq>}）並對每則事件呼叫 {@code handler}，<b>阻塞</b>到串流結束
     * （正常結束＝伺服器關閉連線）；閒置超過 {@code idleTimeout}（Bridge 每 15 秒送 keep-alive，契約 §3.1 取 45 秒）、
     * 連線失敗、{@code handler} 丟例外都以例外離開，由呼叫端決定退避重連。
     * Bridge 不認得該 run（404）丟 {@link BridgeRejectedException}。
     */
    void streamEvents(UUID runId, int afterSeq, Duration idleTimeout, java.util.function.Consumer<BridgeEvent> handler);

    // ── v1.4（D-16）：AISDLC_SDD 引擎狀態（只讀；契約 §3.1 呼叫總表三列、§3.1.3）──────────────────────────
    // 三個呼叫都是唯讀（console-api 不寫 SDD 目錄、不寫任何 FSM-STATE 檔，ADR-001 D22），連線 2 秒／讀取 3 秒、<b>不重試</b>。
    // 錯誤約定同本介面其餘方法：連線失敗 → UpstreamException.Unavailable；讀取逾時 → UpstreamException.TimedOut；
    // 5xx（含 503 sdd_unavailable，details.bridgeReason）或 2xx 但本文不是預期的形狀 → UpstreamException.Failure；4xx → BridgeRejectedException。

    /** {@code GET /sdd/version}：{@code SDD_ROOT} 無效 → 503 {@code sdd_unavailable}。 */
    SddVersion sddVersion();

    /**
     * {@code GET /sdd/fsm[?root=]}：FSM 專案清單（目錄不存在＝200 空清單，不是錯誤）；{@code SDD_ROOT} 無效 → 503 {@code sdd_unavailable}。
     *
     * @param root v1.5 選填：專案根（絕對路徑；狀態目錄＝{@code <root>/build/reports/fsm}）；null＝v1.4 行為（讀 Bridge 預設的狀態目錄）。
     *             不合 allowlist 或不存在 → 422 {@code sanitization_failed}（{@link BridgeRejectedException}）
     */
    SddFsmList sddFsmList(String root);

    /**
     * {@code GET /sdd/fsm/{project}[?root=]}：404 {@code fsm_not_found}（找不到狀態檔）、422 {@code fsm_state_unreadable}（YAML 壞掉、
     * 不是 UTF-8、缺 {@code fsm_state} 根節點）、422 {@code sanitization_failed}（{@code root} 不合）以 {@link BridgeRejectedException} 丟出。
     *
     * <p>🔴 {@code project} 是 FSM 專案名的<b>有效值（可以是原名）</b>：Backend <b>不淨化</b>，本方法只負責把它 percent-encode 進路徑段
     * （Bridge 的淨化鏡像把原名與標準鍵視為等價）。含 {@code /} 的原名不可由 URL 定址（契約 §3.1.7 第 11 點），Bridge 回沒有 reason 的 404。
     */
    SddFsmState sddFsm(String project, String root);

    /**
     * {@code POST /sdd/fsm/{project}:freeze}（契約 §3.1.4 (d)；唯一的 FSM 寫入動詞）：附 {@code X-Bridge-Token}，讀取逾時 40 秒、不重試
     * （非冪等：第二次回 409）。成功回凍結後的 FSM 狀態（與 {@link #sddFsm} 同形；Bridge 另帶的 {@code stage}／{@code spec_doc_digests} 不轉發）。
     * backend 沒有設定權杖時<b>不發出請求</b>、直接丟 503 {@code sdd_write_disabled}（呼叫端本來就該先檢查）。
     * 失敗：503 {@code sdd_write_disabled}／403 {@code sdd_write_forbidden}／404／409／422 以 {@link BridgeRejectedException} 丟出；5xx、
     * 連線失敗、逾時照 {@code UpstreamException}。
     */
    SddFsmState sddFreeze(String project, SddFreeze request);

    /**
     * {@code POST /sdd/fsm/{project}:freeze} 的請求本文（Bridge 的 {@code SddFreezeIn}，{@code extra=forbid}）。
     *
     * @param root            專案根（專案的 {@code executionPath}）
     * @param stage           選填；省略＝Bridge 用 {@code Stage-<n>}
     * @param docs            相對 {@code root} 的 POSIX 路徑，1～20 項，須含至少一份 TCS
     * @param approver        一律取 JWT subject（不可由 client 指定；Bridge 要求 1～100 字元且不含 {@code ;}）
     * @param reason          去前後空白後 1～500 字元
     * @param expectedDigests 選填：核准人當時看到的摘要（鍵須都在 {@code docs} 內）；null 或空＝不比對
     */
    record SddFreeze(String root, String stage, List<String> docs, String approver, String reason,
                     Map<String, String> expectedDigests) {
    }

    /**
     * {@code GET /autoclaude/runs/{id}/rtm}（契約 §1.10.3、§3.1.4 (f)；G-05；唯讀、不需權杖）：連線 2 秒／讀取 3 秒、不重試。
     * 批次不存在 → 404 {@code run_not_found}；沒有報告 → 404 {@code rtm_not_found}；報告壞掉 → 422 {@code rtm_unreadable}
     * （皆為 {@link BridgeRejectedException}，由呼叫端依端點語意轉譯）。
     */
    ExecutionRtm getRunRtm(UUID runId);
}
