package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.DecomposeRequest;
import com.aisdlc.console.application.port.out.AgentBridge.DecomposeResult;
import com.aisdlc.console.application.port.out.AgentBridge.DraftStep;
import com.aisdlc.console.application.port.out.AgentBridge.SddCompileResult;
import com.aisdlc.console.application.port.out.AgentBridge.SddCompileWarning;
import com.aisdlc.console.application.port.out.AgentBridge.SddTask;
import com.aisdlc.console.application.port.out.LlmClient;
import com.aisdlc.console.application.port.out.LlmClient.LlmException;
import com.aisdlc.console.application.port.out.LlmClient.LlmRequest;
import com.aisdlc.console.application.port.out.LlmClient.LlmResult;
import com.aisdlc.console.application.service.SettingsReader.ModelSettings;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.model.imports.GateError;
import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.domain.model.imports.ImportSourceType;
import com.aisdlc.console.domain.model.imports.ParseOptions;
import com.aisdlc.console.domain.model.imports.ParsePath;
import com.aisdlc.console.domain.model.imports.ParseWarning;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedProject;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedTask;
import com.aisdlc.console.domain.service.OutboundUrlPolicy;
import com.aisdlc.console.domain.service.OutboundUrlPolicy.Rejected;
import com.aisdlc.console.domain.service.ParsedResultValidator;
import com.aisdlc.console.domain.service.PassCriteriaSanitizer;
import com.aisdlc.console.domain.service.SpecPaths;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * 匯入解析的三條路徑與選擇規則（契約 §3.3；PRD §0.4／§5.2）。本類別只負責「把來源變成三層草稿樹」；
 * 有界閘由呼叫端（{@link ImportService}）對<b>任何路徑</b>的結果一律重新套用（不信任上游，不截斷不修剪）。
 *
 * <p>路徑選擇（依序，先符合者勝）：
 * <ol>
 *   <li>明示 {@code specDir} → 路徑 A（任何 Bridge 失敗都報錯，含 {@code spec_not_found}）；</li>
 *   <li>探測 {@code executionPath}：{@code POST /sdd/compile}——200 → 路徑 A；422 {@code spec_not_found}／
 *       {@code sanitization_failed} → 視為沒有規格；其餘 422（規格存在但被拒）→ <b>fail-closed</b>
 *       回 422 {@code SDD 規格檢查未通過}，不退回 LLM 瞎猜（PRD §0.4 的凍結硬閘）；Bridge 不可達／逾時／5xx → 略過路徑 A；</li>
 *   <li>路徑 C：{@code sourceType=PLAIN_TEXT} 且全文 &lt; 2,000 字元且沒有 Markdown 標題行 → 視為高階目標；</li>
 *   <li>路徑 B：其餘全部（OpenAI 相容 chat completions）。</li>
 * </ol>
 * 所有路徑共通：{@code parsedResult.project.executionPath} 與 {@code autonomyLevel} 一律取自 {@link ParseOptions}。
 */
@Component
class ImportParser {

    private static final Logger LOG = LoggerFactory.getLogger(ImportParser.class);

    static final int HIGH_LEVEL_GOAL_MAX_CHARS = 2_000;
    static final int GOALS_PER_SDD_BATCH = 24;
    static final int DEFAULT_AUTONOMY = 3;
    private static final Pattern MARKDOWN_HEADING = Pattern.compile("(?m)^ {0,3}#{1,6}[ \\t]");
    private static final Set<String> SPEC_ABSENT_REASONS = Set.of("spec_not_found", "sanitization_failed");
    private static final Duration DECOMPOSE_EXTRA_READ_TIMEOUT = Duration.ofSeconds(15);

    /** 系統訊息（契約 §3.3.3 逐字）。 */
    static final String SYSTEM_MESSAGE = """
            你是一位資深的軟體架構師。只輸出一個 JSON 物件，不要輸出任何其他文字，也不要使用 Markdown 程式碼框。
            JSON 結構：
            {
              "project": { "name": "string", "executionPath": "string（建議）", "passCriteria": "string（Markdown）", "description": "string（Markdown）" },
              "goals": [
                { "key": "g1", "name": "string", "description": "string（Markdown）", "passCriteria": "string（Markdown）",
                  "sortOrder": 0, "dependsOn": ["其他目標的 key；沒有則為空陣列"],
                  "tasks": [ { "name": "string", "description": "string（Markdown，不可為空）", "passCriteria": "string（Markdown）", "sortOrder": 0, "estimatedTokens": 0 } ] }
              ]
            }
            限制：最多 24 個目標、每個目標最多 24 個任務；key 在整份輸出內唯一；dependsOn 只能引用其他目標的 key 且不得成環；每個任務的 description 都必須有實質內容。""";

    /** 解析結果＝草稿樹（含伺服器欄位）＋非阻擋提示。 */
    record Draft(ParsedResult result, List<ParseWarning> warnings) {
    }

    private final AgentBridge bridge;
    private final LlmClient llm;
    private final SettingsReader settings;
    private final OutboundUrlPolicy policy;
    private final int maxPromptChars;

    ImportParser(AgentBridge bridge, LlmClient llm, SettingsReader settings, OutboundUrlPolicy policy,
                 @Value("${console.import.max-prompt-chars:120000}") int maxPromptChars) {
        this.bridge = bridge;
        this.llm = llm;
        this.settings = settings;
        this.policy = policy;
        this.maxPromptChars = maxPromptChars;
    }

    // ── 路徑選擇 ──────────────────────────────────────────────────────────────

    Draft parse(ImportRecord record, ParseOptions options) {
        int autonomy = options.autonomyLevel() == null ? DEFAULT_AUTONOMY : options.autonomyLevel();
        String specDir = options.specDir() == null || options.specDir().isBlank() ? null : options.specDir().strip();
        if (specDir != null) {
            return fromSdd(compileOrReject(specDir, options.specFile(), options.sddProject()), options, autonomy);
        }
        SddCompileResult probed = probeSpec(options.executionPath(), options.sddProject());
        if (probed != null) {
            return fromSdd(probed, options, autonomy);
        }
        if (isHighLevelGoal(record)) {
            return fromDecompose(record, options, autonomy);
        }
        return fromLlm(record, options, autonomy);
    }

    /** 路徑 C 的判準：純文字、全文 &lt; 2,000 字元、沒有 Markdown 標題行（{@code ^[ ]{0,3}#{1,6}[ \t]}）。 */
    static boolean isHighLevelGoal(ImportRecord record) {
        if (record.sourceType() != ImportSourceType.PLAIN_TEXT) {
            return false;
        }
        String content = record.sourceContent().strip();
        return content.length() < HIGH_LEVEL_GOAL_MAX_CHARS && !MARKDOWN_HEADING.matcher(content).find();
    }

    // ── 路徑 A：規格驅動 ──────────────────────────────────────────────────────

    /** 明示 specDir：任何失敗都報錯（含 {@code spec_not_found}；凍結後內容已變更的 409 也是拒絕）。 */
    private SddCompileResult compileOrReject(String specDir, String specFile, String sddProject) {
        try {
            return bridge.sddCompile(specDir, specFile, sddProject);
        } catch (BridgeRejectedException e) {
            if (e.status() == 422 || isDigestChanged(e)) {
                throw specRejected(e);
            }
            throw new UpstreamException.Failure("Bridge 編譯規格時回了非預期的錯誤（HTTP " + e.status() + "）",
                    Map.of("bridgeStatus", e.status(), "bridgeReason", e.reason()));
        }
    }

    /**
     * 探測 executionPath：回 null＝沒有規格（改走 C／B）。探測模式只送 {@code spec_dir}（與已知時的 {@code fsm_project}），不送
     * {@code spec_file}（契約 §3.3.2 v1.5 補充第 1 點）。
     *
     * <p>🔴 <b>fail-closed</b>（契約 §3.3.2 第 9 點；ADR-016 §6.3）：規格存在但被拒＝拒絕，不退回 LLM 瞎猜——除了 422
     * {@code spec_not_frozen}／{@code spec_tainted}…，<b>凍結後內容已變更的 409 {@code spec_digest_changed} 也必須明確拒絕</b>。
     * 此前「非 422 的 4xx 一律略過路徑 A」會把這個 409 靜默降級成 LLM 草稿（fail-open）。
     */
    private SddCompileResult probeSpec(String executionPath, String sddProject) {
        try {
            return bridge.sddCompile(executionPath, null, sddProject);
        } catch (BridgeRejectedException e) {
            if (e.status() == 422 && SPEC_ABSENT_REASONS.contains(e.reason())) {
                return null;
            }
            if (e.status() == 422 || isDigestChanged(e)) {
                throw specRejected(e);       // 規格存在但被拒：fail-closed
            }
            LOG.warn("探測 SDD 規格時 Bridge 回了非預期的 HTTP {}（{}），略過路徑 A", e.status(), e.reason());
            return null;
        } catch (UpstreamException e) {
            LOG.warn("探測 SDD 規格時無法與 Bridge 通訊（{}），略過路徑 A", e.reason());
            return null;
        }
    }

    /** 凍結後內容已變更（Bridge 409 {@code spec_digest_changed}；ADR-016 §6.2）：與 {@code spec_not_frozen} 一樣是「規格存在但被拒」。 */
    private static boolean isDigestChanged(BridgeRejectedException e) {
        return e.status() == 409 && "spec_digest_changed".equals(e.reason());
    }

    private static UnprocessableException specRejected(BridgeRejectedException e) {
        String detail = e.detail() != null && !e.detail().isBlank() ? e.detail() : describeViolations(e);
        String reason = e.reason().isEmpty() ? "unknown" : e.reason();
        return new UnprocessableException("SDD 規格檢查未通過（" + reason + "）：" + detail,
                ErrorReasons.SDD_SPEC_REJECTED, List.of(),
                List.of(new Violation("specDir", "SDD 規格檢查未通過（" + reason + "）：" + detail)),
                Map.of("bridgeReason", reason, "detail", detail));
    }

    private static String describeViolations(BridgeRejectedException e) {
        List<String> messages = new ArrayList<>();
        for (Map<String, Object> violation : e.violations()) {
            Object message = violation.get("message");
            if (message != null) {
                messages.add(message.toString());
            }
        }
        return messages.isEmpty() ? "Bridge 拒絕了這個規格目錄" : String.join("；", messages);
    }

    private Draft fromSdd(SddCompileResult compiled, ParseOptions options, int autonomy) {
        if (compiled.tasks() == null || compiled.tasks().isEmpty()) {
            throw new UnprocessableException("SDD 規格檢查未通過：規格編譯後沒有任何任務",
                    ErrorReasons.SDD_SPEC_REJECTED, List.of(),
                    List.of(new Violation("specDir", "規格編譯後沒有任何任務")),
                    Map.of("bridgeReason", "no_tasks", "detail", "規格編譯後沒有任何任務"));
        }
        String scenario = compiled.scenario() == null || compiled.scenario().isBlank()
                ? lastSegment(options.executionPath()) : compiled.scenario().strip();
        String digest = compiled.digest() == null ? "" : compiled.digest();
        String description = "由凍結 SDD 規格匯入（" + nullToEmpty(compiled.specPath()) + "；digest "
                + digest.substring(0, Math.min(12, digest.length())) + "）";
        ParsedProject project = new ParsedProject(clip(scenario, 200), options.executionPath(),
                "規格「" + scenario + "」的全部合約驗收通過", description, autonomy);
        List<SddTask> all = compiled.tasks();
        int batches = (all.size() + GOALS_PER_SDD_BATCH - 1) / GOALS_PER_SDD_BATCH;
        List<ParseWarning> warnings = new ArrayList<>(sddLevelWarnings(compiled));
        List<ParsedGoal> goals = new ArrayList<>();
        for (int k = 0; k < batches; k++) {
            List<SddTask> chunk = all.subList(k * GOALS_PER_SDD_BATCH, Math.min(all.size(),
                    (k + 1) * GOALS_PER_SDD_BATCH));
            List<ParsedTask> tasks = new ArrayList<>();
            for (int j = 0; j < chunk.size(); j++) {
                tasks.add(sddTask(chunk.get(j), digest, j, "goals[" + k + "].tasks[" + j + "]", warnings));
            }
            String name = batches == 1 ? scenario : scenario + "（第 " + (k + 1) + " 批）";
            goals.add(new ParsedGoal("g" + (k + 1), clip(name, 200), description,
                    "全部 " + chunk.size() + " 個合約的驗收標準通過", k,
                    k == 0 ? List.of() : List.of("g" + k), tasks));
        }
        // v1.5 的四個伺服器擁有欄位（契約 §3.3.2 第 5 點）：只有路徑 A 才有值，confirm 才回填（parse／預覽不回填）
        String specPath = blankToNull(compiled.specPath());
        ParsedResult result = new ParsedResult(project, goals, ParsePath.SDD, null, null, null, null, digest,
                blankToNull(compiled.specFormatVersion()), blankToNull(compiled.fsmProject()),
                specPath == null ? null : SpecPaths.parentOf(specPath), specPath);
        return new Draft(result, warnings);
    }

    /**
     * 路徑 A 的規格層級提示（黃色、不阻擋；契約 §3.3.2 第 6 點）：{@code at_unmapped}（規格<b>宣告位置</b>出現、卻沒編成步驟的 AT；已編成的
     * AT 照常產出任務）、{@code frozen_digest_absent}（凍結時沒有記錄內容摘要，無法偵測凍結後改檔）、{@code state_dir_not_ignored}
     * （Bridge 回報專案根的 {@code build/reports/fsm/} 未被 git 忽略；原樣轉入）。
     */
    private static List<ParseWarning> sddLevelWarnings(SddCompileResult compiled) {
        List<ParseWarning> warnings = new ArrayList<>();
        if (!compiled.unmappedAtIds().isEmpty()) {
            warnings.add(new ParseWarning(ParseWarning.AT_UNMAPPED,
                    "規格出現但未編成步驟的 AT：" + String.join("、", compiled.unmappedAtIds()), "specDir"));
        }
        if ("absent".equals(compiled.frozenDigest())) {
            warnings.add(new ParseWarning(ParseWarning.FROZEN_DIGEST_ABSENT,
                    "規格凍結時沒有記錄內容摘要（舊狀態檔），無法偵測凍結後改檔", "specDir"));
        }
        for (SddCompileWarning warning : compiled.warnings()) {
            if (ParseWarning.STATE_DIR_NOT_IGNORED.equals(warning.code())) {
                warnings.add(new ParseWarning(ParseWarning.STATE_DIR_NOT_IGNORED, nullToEmpty(warning.detail()),
                        "executionPath"));
            }
        }
        return warnings;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.strip();
    }

    private static ParsedTask sddTask(SddTask task, String digest, int sortOrder, String where,
                                      List<ParseWarning> warnings) {
        String regex = task.expectedOutputRegex();
        if (regex != null && !regex.isBlank() && !compilable(regex)) {
            warnings.add(new ParseWarning(ParseWarning.REGEX_DROPPED,
                    "規格合約 " + task.stepId() + " 的 expected_output_regex 無法編譯，已清空", where));
            regex = null;
        }
        String command = safeCommand(task.evaluatorCommand(), task.stepId(), where, warnings);
        String passCriteria = regex != null && !regex.isBlank() ? "輸出符合 " + regex
                : "規格合約 " + task.stepId() + " 的驗收標準";
        Map<String, Object> spec = new LinkedHashMap<>();
        spec.put("source", "sdd");
        spec.put("specDigest", digest);
        spec.put("stepId", task.stepId());
        spec.put("weakRegex", task.weakRegex());
        if (task.maintainContext() != null) {
            spec.put("maintainContext", task.maintainContext());       // G-08：跨 AC 脈絡隔離；Bridge 沒給就不放這個鍵
        }
        // G-08：SCG-4 型 5、SCG-5 型 2 的重試上限不再丟成 null（落庫取預設 3）；Bridge 沒給仍是 null
        return new ParsedTask(clip(task.name(), 200), task.prompt(), passCriteria, sortOrder, null, command,
                regex == null || regex.isBlank() ? null : regex, spec, task.maxRetries());
    }

    // ── 路徑 C：高階目標 → Bridge decompose ────────────────────────────────────

    private Draft fromDecompose(ImportRecord record, ParseOptions options, int autonomy) {
        ModelSettings model = settings.modelSettings();
        String goal = record.sourceContent().strip();
        String project = firstLine(goal);
        Map<String, Object> minimax = null;
        if (!model.apiKey().isEmpty()) {
            minimax = new LinkedHashMap<>();
            minimax.put("base_url", model.apiUrl());
            minimax.put("model", model.name());
            minimax.put("timeout_seconds", model.timeoutSeconds());
        }
        DecomposeResult decomposed;
        try {
            decomposed = bridge.decompose(new DecomposeRequest(goal,
                    options.additionalPrompt() == null ? "" : options.additionalPrompt(), project,
                    ParsedResultValidator.HARD_MAX_STEPS, minimax),
                    Duration.ofSeconds(model.timeoutSeconds()).plus(DECOMPOSE_EXTRA_READ_TIMEOUT));
        } catch (BridgeRejectedException e) {
            throw decomposeRejected(e);
        }
        List<ParseWarning> warnings = new ArrayList<>();
        List<ParsedTask> tasks = new ArrayList<>();
        List<DraftStep> steps = decomposed.steps() == null ? List.of() : decomposed.steps();
        if (steps.isEmpty()) {
            // 契約 §3.3.5：Bridge 回報無步驟（no_steps）＝brain_failed；一個沒有任務的目標連 PUT result 都過不了結構檢查。
            throw gateRejected(ParsePath.DECOMPOSE, List.of(new GateError(GateError.BRAIN_FAILED,
                    "Bridge 拆解後沒有任何步驟（no_steps）", null)));
        }
        for (int j = 0; j < steps.size(); j++) {
            DraftStep step = steps.get(j);
            String where = "goals[0].tasks[" + j + "]";
            String command = safeCommand(step.evaluatorCommand(), step.stepId(), where, warnings);
            String passCriteria;
            if (command != null) {
                passCriteria = "評估指令通過";
            } else {
                passCriteria = ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT;
                warnings.add(new ParseWarning(ParseWarning.PASSCRITERIA_PLACEHOLDER,
                        "任務「" + nullToEmpty(step.name()) + "」沒有可用的通過標準，已填入佔位字串，請於 signoff 前補齊", where));
            }
            Map<String, Object> spec = new LinkedHashMap<>();
            spec.put("source", "decompose");
            spec.put("stepId", step.stepId());
            spec.put("draftId", decomposed.draftId());
            tasks.add(new ParsedTask(step.name() == null || step.name().isBlank() ? nullToEmpty(step.stepId())
                    : clip(step.name(), 200), step.prompt(), passCriteria, j, null, command, null, spec, null));
        }
        String reasoning = decomposed.reasoning() == null ? "" : decomposed.reasoning();
        ParsedProject parsedProject = new ParsedProject(clip(project, 200), options.executionPath(), goal,
                reasoning.isBlank() ? "由高階目標自動拆解" : reasoning, autonomy);
        ParsedGoal parsedGoal = new ParsedGoal("g1", clip(project, 200), reasoning, "拆解出的全部步驟依序完成", 0,
                List.of(), tasks);
        ParsedResult result = new ParsedResult(parsedProject, List.of(parsedGoal), ParsePath.DECOMPOSE, null, null,
                reasoning, List.of(decomposed.draftId()), null);
        return new Draft(result, warnings);
    }

    /** Bridge decompose 的 4xx：帶 gate 的 422 轉成有界閘違規；其餘 422 為「引擎拒絕此請求」；非 422 是 Bridge 錯誤。 */
    private static RuntimeException decomposeRejected(BridgeRejectedException e) {
        if (e.status() == 422 && e.gate() != null && !e.gate().isBlank()) {
            String detail = e.detail() != null && !e.detail().isBlank() ? e.detail()
                    : "Bridge 拒絕了拆解請求（" + e.reason() + "）";
            return gateRejected(ParsePath.DECOMPOSE, List.of(new GateError(e.gate(), detail, null)));
        }
        if (e.status() == 422) {
            if ("invalid_request".equals(e.reason())) {
                LOG.error("Bridge 以 invalid_request 拒絕 decompose 請求：Console 組出的請求不符契約（缺陷）：{}", e.body());
            }
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("bridgeReason", e.reason().isEmpty() ? "unknown" : e.reason());
            details.put("violations", e.violations());
            return new UnprocessableException("引擎拒絕此請求（" + e.reason() + "）", ErrorReasons.BRIDGE_REJECTED,
                    details);
        }
        return new UpstreamException.Failure("Bridge 拆解時回了非預期的錯誤（HTTP " + e.status() + "）",
                Map.of("bridgeStatus", e.status(), "bridgeReason", e.reason()));
    }

    // ── 路徑 B：自由文件 → OpenAI 相容 chat completions ─────────────────────────

    private Draft fromLlm(ImportRecord record, ParseOptions options, int autonomy) {
        ModelSettings model = settings.modelSettings();
        if (model.apiKey().isEmpty()) {
            throw gateRejected(ParsePath.LLM, List.of(new GateError(GateError.BRAIN_UNSUPPORTED,
                    "尚未設定 model.apiKey（系統參數），無法呼叫模型解析文件", null)));
        }
        try {
            policy.checkStatic(model.apiUrl());
        } catch (Rejected rejected) {
            throw gateRejected(ParsePath.LLM, List.of(new GateError(GateError.BRAIN_UNSUPPORTED,
                    "模型位址未通過 SSRF／allowlist 檢查（" + rejected.violation().code() + "）", null)));
        }
        String userMessage = userMessage(autonomy, options.additionalPrompt(), record.sourceContent());
        int total = SYSTEM_MESSAGE.length() + userMessage.length();
        if (total > maxPromptChars) {
            throw gateRejected(ParsePath.LLM, List.of(new GateError(GateError.PROMPT_TOO_LONG,
                    "文件過長：" + total + " 字元，上限 " + maxPromptChars, "sourceContent")));
        }
        LlmResult generated;
        try {
            generated = llm.generate(new LlmRequest(model.apiUrl(), model.apiKey(), model.name(), SYSTEM_MESSAGE,
                    userMessage, model.temperature(), model.topP(), model.maxTokensPerRequest(),
                    model.timeoutSeconds()));
        } catch (LlmException e) {
            String gate = e.kind() == LlmException.Kind.UNSUPPORTED ? GateError.BRAIN_UNSUPPORTED
                    : GateError.BRAIN_FAILED;
            throw gateRejected(ParsePath.LLM, List.of(new GateError(gate, e.detail(), null)));
        }
        List<ParseWarning> warnings = new ArrayList<>();
        ParsedResult tree = normalizeLlmDraft(generated.draft(), record, options, autonomy, warnings);
        String aiModel = generated.model() != null && !generated.model().isBlank() ? generated.model() : model.name();
        ParsedResult result = new ParsedResult(tree.project(), tree.goals(), ParsePath.LLM, aiModel,
                generated.tokenUsed(), null, null, null);
        return new Draft(result, warnings);
    }

    /** 使用者訊息＝PRD §5.2.4 的輸入 Prompt 樣板逐字，代入自治等級、補充說明與文件內容（逐段組裝，不做字串取代）。 */
    static String userMessage(int autonomyLevel, String additionalPrompt, String documentContent) {
        String additional = additionalPrompt == null || additionalPrompt.isBlank() ? "（無）" : additionalPrompt;
        return "你是一位資深的軟體架構師。請分析以下需求文件，並將其拆解為三層結構：\n\n"
                + "1. **專案 (Project)**：整體專案名稱、執行路徑建議、通過標準、說明描述\n"
                + "2. **目標 (Goal)**：專案下的主要里程碑或功能模組，含說明描述與通過標準\n"
                + "3. **任務 (Task)**：目標下的具體可執行開發任務，含說明描述與通過標準\n\n"
                + "自治等級: " + autonomyLevel + "\n"
                + "補充說明: " + additional + "\n\n"
                + "---\n需求文件內容:\n" + documentContent + "\n---\n\n"
                + "請以 JSON 格式輸出結果。";
    }

    /**
     * 模型輸出 → 三層樹（契約 §3.3.3）：目標缺 key 依序補 g1、g2…；{@code project.executionPath} 與
     * {@code autonomyLevel} 以 ParseOptions 為準（模型建議丟棄）；任務／目標的 passCriteria 空白填佔位字串並加警告；
     * {@code sortOrder} 一律依陣列順序重編。任務的 name／description 保持原樣（空白交給 {@code empty_prompt} 閘）。
     */
    private static ParsedResult normalizeLlmDraft(ParsedResult draft, ImportRecord record, ParseOptions options,
                                                  int autonomy, List<ParseWarning> warnings) {
        ParsedProject p = draft.project();
        String name = p.name() == null || p.name().isBlank() ? fallbackProjectName(record) : clip(p.name().strip(), 200);
        String projectCriteria = p.passCriteria();
        if (projectCriteria == null || projectCriteria.isBlank()) {
            projectCriteria = ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT;
            warnings.add(new ParseWarning(ParseWarning.PASSCRITERIA_PLACEHOLDER,
                    "專案沒有通過標準，已填入佔位字串，請於 signoff 前補齊", "project"));
        }
        ParsedProject project = new ParsedProject(name, options.executionPath(), projectCriteria, p.description(),
                autonomy);
        List<ParsedGoal> goals = new ArrayList<>();
        List<ParsedGoal> rawGoals = draft.goals() == null ? List.of() : draft.goals();
        for (int i = 0; i < rawGoals.size(); i++) {
            ParsedGoal g = rawGoals.get(i);
            String key = g.key() == null || g.key().isBlank() ? "g" + (i + 1) : g.key().strip();
            String goalCriteria = g.passCriteria();
            if (goalCriteria == null || goalCriteria.isBlank()) {
                goalCriteria = ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT;
                warnings.add(new ParseWarning(ParseWarning.PASSCRITERIA_PLACEHOLDER,
                        "目標「" + nullToEmpty(g.name()) + "」沒有通過標準，已填入佔位字串，請於 signoff 前補齊", "goals[" + i + "]"));
            }
            List<ParsedTask> tasks = new ArrayList<>();
            List<ParsedTask> rawTasks = g.tasks() == null ? List.of() : g.tasks();
            for (int j = 0; j < rawTasks.size(); j++) {
                ParsedTask t = rawTasks.get(j);
                String taskCriteria = t.passCriteria();
                if (taskCriteria == null || taskCriteria.isBlank()) {
                    taskCriteria = ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT;
                    warnings.add(new ParseWarning(ParseWarning.PASSCRITERIA_PLACEHOLDER,
                            "任務「" + nullToEmpty(t.name()) + "」沒有通過標準，已填入佔位字串，請於 signoff 前補齊",
                            "goals[" + i + "].tasks[" + j + "]"));
                }
                tasks.add(new ParsedTask(t.name(), t.description(), taskCriteria, j, t.estimatedTokens(), null, null,
                        null, null));
            }
            goals.add(new ParsedGoal(key, g.name() == null || g.name().isBlank() ? "目標 " + (i + 1) : g.name().strip(),
                    g.description(), goalCriteria, i, g.dependsOn() == null ? List.of() : g.dependsOn(), tasks));
        }
        return ParsedResult.tree(project, goals);
    }

    // ── 共用 ──────────────────────────────────────────────────────────────────

    /** 有界閘拒絕的 422（契約 §1.1.3）：{@code errors[]} 一次列出全部違規，details＝{@code {path}}。 */
    static UnprocessableException gateRejected(ParsePath path, List<GateError> errors) {
        return new UnprocessableException("解析結果未通過有界閘（" + errors.size() + " 項）：" + errors.get(0).detail(),
                ErrorReasons.IMPORT_GATE_REJECTED, errors, List.of(),
                Map.of("path", path == null ? "UNKNOWN" : path.name()));
    }

    private static String safeCommand(String command, String stepId, String where, List<ParseWarning> warnings) {
        if (command == null || command.isBlank()) {
            return null;
        }
        boolean unsafe = !PassCriteriaSanitizer.violationsOf(command).isEmpty()
                || command.chars().anyMatch(Character::isISOControl);
        if (unsafe) {
            warnings.add(new ParseWarning(ParseWarning.EVALUATOR_COMMAND_DROPPED,
                    "步驟 " + stepId + " 的評估指令含禁用字元，已清空（NFR-SEC-03）", where));
            return null;
        }
        return command.strip();
    }

    private static boolean compilable(String regex) {
        try {
            Pattern.compile(regex);
            return true;
        } catch (PatternSyntaxException e) {
            return false;
        }
    }

    private static String fallbackProjectName(ImportRecord record) {
        String file = record.sourceFileName();
        if (file != null && !file.isBlank()) {
            int dot = file.lastIndexOf('.');
            return clip(dot > 0 ? file.substring(0, dot) : file, 200);
        }
        return "匯入專案";
    }

    private static String firstLine(String content) {
        String first = content.lines().map(String::strip).filter(line -> !line.isEmpty()).findFirst().orElse("");
        return first.isEmpty() ? "decomposed-goal" : clip(first, 60);
    }

    private static String lastSegment(String path) {
        String trimmed = path.replaceAll("[\\\\/]+$", "");
        int cut = Math.max(trimmed.lastIndexOf('/'), trimmed.lastIndexOf('\\'));
        String last = cut >= 0 ? trimmed.substring(cut + 1) : trimmed;
        return last.isBlank() ? "SDD 規格" : last;
    }

    private static String clip(String value, int max) {
        return value == null ? "" : value.length() <= max ? value : value.substring(0, max);
    }

    private static String nullToEmpty(String value) {
        return value == null ? "" : value;
    }
}
