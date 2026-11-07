package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ImportUseCase;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.application.port.in.ResearchDecompositionUseCase;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ImportRecordRepository;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchDecompositionReadPort;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.domain.model.imports.ImportSourceType;
import com.aisdlc.console.domain.model.imports.ParseOptions;
import com.aisdlc.console.domain.model.imports.ParsePath;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedProject;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedTask;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Decomposition;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.ImportRef;
import com.aisdlc.console.domain.model.research.ResearchViews;
import com.aisdlc.console.domain.service.DecompositionCoverage;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;

/**
 * 拆解用例（API-RP-16；D-94、D-113、D-120、D-121）。<b>觸發</b>＝恰一次 Bridge {@code :decompose}（同步、讀逾時 330 秒、不重試）；<b>讀取</b>＝JDBC 唯讀（有效拆解、覆蓋、豁免、stale）；
 * <b>簽核</b>（OPERATOR 以上）：<ol>
 *   <li>輸入閘（approver＝JWT subject，空白＝400；豁免格式 400）→ 專案存在（404）→ 前置：已分流、有拆解、狀態可簽、未 stale（409）；</li>
 *   <li>覆蓋判定（{@link DecompositionCoverage}）：未覆蓋清單扣掉有理由的豁免後非空＝422 {@code invalid_request}（{@code violations[{field:coverage,rule:uncovered_ac}]}），零落庫、零 Bridge 請求；</li>
 *   <li><b>先走既有 import／signoff 路徑</b>（不走 HTTP 迴圈）：以拆解 artifact 建一筆路徑 C 的匯入記錄（{@code targetProjectId}＝已分流的 Console 專案）→ {@link ImportUseCase#signoff}
 *       → {@link ImportUseCase#confirm}（目標與任務併入該專案、全部 signedOff）→ 專案層 signoff（承襲同一個人工簽核）；</li>
 *   <li>呼 Bridge {@code :decomposition-signoff {decomposition_id, import_record_id, imported_tasks_count, console_project_id, approver, waivers}}：一次寫 {@code SIGNED_OFF} 與 {@code import_record_id}。</li>
 * </ol>
 * 誠實劃界：第 3 步與第 4 步之間沒有跨系統交易（匯入落庫已 commit 而 Bridge 呼叫失敗＝正式專案已有目標任務但拆解列仍是 DRAFTED；呼叫者重試簽核會因匯入記錄已是新的而再建一筆，
 * 目標任務重複的處置見交卷〈誠實劃界〉）。
 */
@Service
public class ResearchDecompositionService implements ResearchDecompositionUseCase {

    public static final int WAIVER_REASON_MAX = 500;
    public static final int WAIVERS_MAX_ITEMS = 500;
    private static final Set<String> SIGNABLE = Set.of("DRAFTED", "SCG_PASSED", "FROZEN");
    private static final String PLACEHOLDER_CRITERIA = "依拆解草稿；完成條件由任務描述定義";

    private final ResearchBridge bridge;
    private final ResearchProjectReadPort researchProjects;
    private final ResearchDecompositionReadPort decompositions;
    private final ProjectRepository consoleProjects;
    private final ImportRecordRepository importRecords;
    private final ImportUseCase imports;
    private final AuditTrail audit;
    private final Clock clock;
    private final TransactionTemplate tx;

    @SuppressWarnings("java:S107")
    ResearchDecompositionService(ResearchBridge bridge, ResearchProjectReadPort researchProjects, ResearchDecompositionReadPort decompositions,
                                 ProjectRepository consoleProjects, ImportRecordRepository importRecords, ImportUseCase imports, AuditTrail audit,
                                 Clock clock, TransactionTemplate tx) {
        this.bridge = bridge;
        this.researchProjects = researchProjects;
        this.decompositions = decompositions;
        this.consoleProjects = consoleProjects;
        this.importRecords = importRecords;
        this.imports = imports;
        this.audit = audit;
        this.clock = clock;
        this.tx = tx;
    }

    @Override
    public Optional<View> current(UUID researchId) {
        require(researchId);
        Optional<String> frozen = decompositions.frozenPrdSha256(researchId);
        return decompositions.effective(researchId).map(d -> view(d, frozen.orElse(null)));
    }

    @Override
    public Map<String, Object> trigger(Caller caller, UUID researchId, List<String> usIds) {
        requireWriteEnabled();
        require(researchId);
        audit.note("research.decomposition", "research", researchId.toString());
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("requested_by", caller.subject());
        if (usIds != null && !usIds.isEmpty()) {
            body.put("scope", Map.of("us_ids", List.copyOf(usIds)));
        }
        return call(() -> bridge.decompose(researchId, body));
    }

    @Override
    public View signoff(Caller caller, UUID researchId, List<WaiverInput> waivers) {
        requireWriteEnabled();
        String approver = caller.subject();
        if (approver == null || approver.isBlank()) {
            throw ValidationException.of("approver", "憑證沒有帳號名（JWT subject），無法簽核（人工簽核不可匿名）");
        }
        List<DecompositionCoverage.Waiver> checkedWaivers = checkWaivers(waivers);
        ResearchViews.Project research = require(researchId);
        audit.note("research.decomposition.signoff", "research", researchId.toString());
        UUID consoleProjectId = research.consoleProjectId();
        if (consoleProjectId == null) {
            throw new ConflictException("這個研究專案尚未分流，沒有可簽核的拆解", ErrorReasons.RESEARCH_FSM_STATE_CONFLICT, Map.of("cause", "not_routed"));
        }
        Decomposition decomposition = decompositions.effective(researchId).orElseThrow(() -> new ConflictException("這個研究專案尚未拆解",
                ErrorReasons.RESEARCH_FSM_STATE_CONFLICT, Map.of("cause", "no_decomposition")));
        Optional<String> frozen = decompositions.frozenPrdSha256(researchId);
        if (isStale(decomposition, frozen.orElse(null))) {
            throw stale(decomposition, frozen.orElse(null));
        }
        if (!SIGNABLE.contains(decomposition.status())) {
            throw new ConflictException("拆解目前的狀態不允許簽核（" + decomposition.status() + "）", ErrorReasons.RESEARCH_FSM_STATE_CONFLICT,
                    Map.of("status", decomposition.status(), "decomposition_id", decomposition.id().toString()));
        }
        DecompositionCoverage.Result coverage = DecompositionCoverage.of(decomposition.content());
        List<String> missing = DecompositionCoverage.stillUncovered(coverage, checkedWaivers);
        if (!missing.isEmpty()) {
            throw uncovered(missing);
        }
        Project console = consoleProjects.findById(consoleProjectId).orElseThrow(() -> NotFoundException.of("專案", consoleProjectId));
        UUID importRecordId = importThroughExistingPath(decomposition, console, approver);
        signoffProject(consoleProjectId, approver);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("decomposition_id", decomposition.id().toString());
        body.put("import_record_id", importRecordId.toString());
        body.put("console_project_id", consoleProjectId.toString());
        // D-143(3)：匯入落成的正式 tasks 數（與 confirm 匯入的是同一棵 parsedTree），Bridge 記進簽核版 artifact，AT-961-10-6 斷言與 tasks_count 相等
        body.put("imported_tasks_count", importedTasksCount(decomposition, console));
        body.put("approver", approver);
        List<Map<String, Object>> waiverBody = new ArrayList<>();
        for (DecompositionCoverage.Waiver waiver : checkedWaivers) {
            waiverBody.add(Map.of("ac", waiver.ac(), "reason", waiver.reason()));
        }
        body.put("waivers", waiverBody);
        call(() -> bridge.decompositionSignoff(researchId, body));
        return decompositions.effective(researchId).map(d -> view(d, decompositions.frozenPrdSha256(researchId).orElse(null)))
                .orElseThrow(() -> new UpstreamException.Failure("Bridge 回成功，但資料庫查無拆解", Map.of("bridgeStatus", 200)));
    }

    // ── 既有 import／signoff 路徑 ────────────────────────────────────────────────────────

    /**
     * 以拆解 artifact 建路徑 C 的匯入記錄，經既有 signoff 與 confirm（併入 Console 專案）落為正式目標與任務；回匯入記錄 id。
     * <b>冪等（D-133）</b>：匯入記錄的 {@code source_file_name} 記 {@code research-decomposition:<拆解 id>}、{@code parse_options.targetProjectId} 記 Console 專案，
     * 簽核前先以這兩個既有欄位查——已 IMPORTED 的直接重用（不建第二筆、不重複目標任務）；停在 signoff 或 confirm 之前的（先前失敗）從中斷處續做。
     * 這使「匯入成功但 Bridge :decomposition-signoff 失敗」之後重試簽核，匯入記錄數與目標任務數都不增。
     */
    private UUID importThroughExistingPath(Decomposition decomposition, Project console, String approver) {
        Optional<ImportRef> existing = decompositions.importRecordOf(console.id(), decomposition.id());
        if (existing.isPresent()) {
            ImportRef ref = existing.get();
            if ("IMPORTED".equals(ref.status())) {
                return ref.id();
            }
            if ("PARSED".equals(ref.status()) || "REVIEWING".equals(ref.status())) {
                if (!ref.signedOff()) {
                    imports.signoff(ref.id(), approver);
                }
                imports.confirm(ref.id(), approver);
                return ref.id();
            }
        }
        ParsedResult tree = parsedTree(decomposition, console);
        ParseOptions options = new ParseOptions(console.executionPath(), console.autonomyLevel(), null, null, null, console.effectiveSddProject(), console.id());
        UUID recordId = tx.execute(status -> {
            ImportRecord record = ImportRecord.create(ImportSourceType.PLAIN_TEXT, "研發工作流拆解 " + decomposition.id(),
                    "research-decomposition:" + decomposition.id(), clock.instant());
            record.beginParse(options);
            record.completeParse(tree, List.of());
            importRecords.save(record);
            return record.id();
        });
        imports.signoff(recordId, approver);
        imports.confirm(recordId, approver);
        return recordId;
    }

    /** 匯入落成的正式 tasks 數：confirm 把 parsedTree 的每個 task 併入專案，故以同一棵樹計（冪等重用既有匯入記錄時同樣成立）。 */
    private static int importedTasksCount(Decomposition decomposition, Project console) {
        int total = 0;
        for (ParsedGoal goal : parsedTree(decomposition, console).goals()) {
            total += goal.tasks().size();
        }
        return total;
    }

    @SuppressWarnings("unchecked")
    private static ParsedResult parsedTree(Decomposition decomposition, Project console) {
        Map<String, Object> content = decomposition.content() == null ? Map.of() : decomposition.content();
        List<ParsedGoal> goals = new ArrayList<>();
        int goalIndex = 0;
        for (Object rawGoal : content.get("goals") instanceof List<?> list ? list : List.of()) {
            Map<String, Object> goal = rawGoal instanceof Map<?, ?> m ? (Map<String, Object>) m : Map.of();
            String key = text(goal.get("goal_id"), "G-" + (goalIndex + 1));
            String criteria = text(goal.get("pass_criteria"), PLACEHOLDER_CRITERIA);
            List<ParsedTask> tasks = new ArrayList<>();
            int taskIndex = 0;
            for (Object rawTask : goal.get("tasks") instanceof List<?> list ? list : List.of()) {
                Map<String, Object> task = rawTask instanceof Map<?, ?> m ? (Map<String, Object>) m : Map.of();
                String name = text(task.get("name"), "任務 " + (taskIndex + 1));
                Map<String, Object> spec = new LinkedHashMap<>();
                spec.put("source", "research_decomposition");
                spec.put("taskId", text(task.get("task_id"), ""));
                spec.put("coversAc", task.get("covers_ac") instanceof List<?> acs ? acs : List.of());
                String evaluator = task.get("evaluator_command") == null ? null : task.get("evaluator_command").toString();
                tasks.add(new ParsedTask(name, text(task.get("prompt"), name), "完成：" + name, taskIndex,
                        task.get("estimated_tokens") instanceof Number n ? Long.valueOf(n.longValue()) : null, evaluator, null, spec, null));
                taskIndex++;
            }
            List<String> dependsOn = new ArrayList<>();
            for (Object dep : goal.get("depends_on") instanceof List<?> list ? list : List.of()) {
                dependsOn.add(String.valueOf(dep));
            }
            goals.add(new ParsedGoal(key, text(goal.get("name"), key), "", criteria, goalIndex, dependsOn, tasks));
            goalIndex++;
        }
        ParsedProject project = new ParsedProject(console.name(), console.executionPath(), console.passCriteria(), console.description(),
                console.autonomyLevel());
        return new ParsedResult(project, goals, ParsePath.DECOMPOSE, null, null, null, List.of(), null);
    }

    private void signoffProject(UUID consoleProjectId, String approver) {
        tx.executeWithoutResult(status -> consoleProjects.findByIdForUpdate(consoleProjectId).ifPresent(project -> {
            if (!project.signedOff()) {
                project.inheritSignoff(approver, clock.instant());
                consoleProjects.save(project);
            }
        }));
    }

    // ── 讀模型與判定 ─────────────────────────────────────────────────────────────────────

    private View view(Decomposition d, String frozenSha) {
        DecompositionCoverage.Result coverage = DecompositionCoverage.of(d.content());
        List<DecompositionCoverage.Waiver> waivers = new ArrayList<>();
        List<Map<String, Object>> goals = new ArrayList<>();
        Map<String, Object> content = d.content() == null ? Map.of() : d.content();
        if (content.get("waivers") instanceof List<?> items) {
            for (Object item : items) {
                if (item instanceof Map<?, ?> m) {
                    waivers.add(new DecompositionCoverage.Waiver(text(m.get("ac"), ""), text(m.get("reason"), "")));
                }
            }
        }
        if (content.get("goals") instanceof List<?> items) {
            for (Object item : items) {
                if (item instanceof Map<?, ?> m) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> goal = (Map<String, Object>) m;
                    goals.add(goal);
                }
            }
        }
        return new View(d, coverage, List.copyOf(waivers), List.copyOf(goals), isStale(d, frozenSha));
    }

    private static boolean isStale(Decomposition d, String frozenSha) {
        return "STALE".equals(d.status()) || (frozenSha != null && d.prdSha256() != null && !frozenSha.equals(d.prdSha256()));
    }

    private static ConflictException stale(Decomposition d, String frozenSha) {
        Map<String, Object> details = new LinkedHashMap<>();
        details.put("decomposition_id", d.id().toString());
        if (frozenSha != null) {
            details.put("expected_sha256", frozenSha);
        }
        if (d.prdSha256() != null) {
            details.put("actual_sha256", d.prdSha256());
        }
        return new ConflictException("拆解綁定的 PRD 摘要已過期，請重新拆解並再簽核", ErrorReasons.RESEARCH_DECOMPOSITION_STALE, details);
    }

    private static UnprocessableException uncovered(List<String> missing) {
        List<Violation> violations = new ArrayList<>();
        List<Map<String, Object>> items = new ArrayList<>();
        for (String ac : missing) {
            String message = ac + " 未被任何 task 的 covers_ac 涵蓋，且沒有人工豁免理由";
            violations.add(new Violation("coverage", message));
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("field", "coverage");
            item.put("rule", "uncovered_ac");
            item.put("message", message);
            item.put("ac", ac);
            items.add(item);
        }
        return new UnprocessableException("拆解仍有 " + missing.size() + " 個 AC 未覆蓋且沒有豁免理由，不能簽核", ErrorReasons.RESEARCH_INVALID_REQUEST, List.of(),
                violations, Map.of("violations", items, "uncovered", List.copyOf(missing)));
    }

    private static List<DecompositionCoverage.Waiver> checkWaivers(List<WaiverInput> waivers) {
        if (waivers == null) {
            return List.of();
        }
        ResearchRouteGates.Check check = new ResearchRouteGates.Check();
        List<DecompositionCoverage.Waiver> out = new ArrayList<>();
        if (waivers.size() > WAIVERS_MAX_ITEMS) {
            check.add("waivers", "max_items", "waivers 至多 " + WAIVERS_MAX_ITEMS + " 項");
        }
        for (int i = 0; i < waivers.size(); i++) {
            WaiverInput waiver = waivers.get(i);
            String ac = waiver == null || waiver.ac() == null ? "" : waiver.ac().strip();
            String reason = waiver == null || waiver.reason() == null ? "" : waiver.reason().strip();
            if (ac.isEmpty()) {
                check.add("waivers[" + i + "].ac", "required", "豁免的 AC 編號為必填");
            }
            if (reason.isEmpty() || reason.codePointCount(0, reason.length()) > WAIVER_REASON_MAX) {
                check.add("waivers[" + i + "].reason", "invalid_length", "豁免理由須為 1～" + WAIVER_REASON_MAX + " 字");
            }
            out.add(new DecompositionCoverage.Waiver(ac, reason));
        }
        if (!check.violations.isEmpty()) {
            throw check.validation();
        }
        return List.copyOf(out);
    }

    private static String text(Object value, String fallback) {
        return value == null || value.toString().isBlank() ? fallback : value.toString();
    }

    private void requireWriteEnabled() {
        if (!bridge.writeEnabled()) {
            throw new ServiceUnavailableException("backend 沒有設定研究寫入權杖（BRIDGE_RESEARCH_WRITE_TOKEN），研究寫入面已停用",
                    ErrorReasons.RESEARCH_WRITE_DISABLED, Map.of("cause", "bridge_token_unset"));
        }
    }

    private ResearchViews.Project require(UUID id) {
        return researchProjects.findById(id).orElseThrow(() -> new NotFoundException("研究專案不存在：" + id, ErrorReasons.RESEARCH_NOT_FOUND, Map.of()));
    }

    private static <T> T call(Supplier<T> action) {
        try {
            return action.get();
        } catch (BridgeRejectedException e) {
            throw ResearchBridgeErrors.map(e);
        }
    }
}
