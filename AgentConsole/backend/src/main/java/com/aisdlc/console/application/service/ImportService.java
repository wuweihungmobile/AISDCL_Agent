package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ImportUseCase;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectCounts;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectView;
import com.aisdlc.console.application.port.in.PageResult;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.DocumentTextExtractor;
import com.aisdlc.console.application.port.out.DocumentTextExtractor.ExtractionException;
import com.aisdlc.console.application.port.out.GoalRepository;
import com.aisdlc.console.application.port.out.ImportRecordRepository;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.TaskRepository;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.PayloadTooLargeException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UnsupportedFormatException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.model.goal.Goal;
import com.aisdlc.console.domain.model.goal.NewGoal;
import com.aisdlc.console.domain.model.imports.GateError;
import com.aisdlc.console.domain.model.imports.ImportRecord;
import com.aisdlc.console.domain.model.imports.ImportSourceType;
import com.aisdlc.console.domain.model.imports.ParseOptions;
import com.aisdlc.console.domain.model.imports.ParseWarning;
import com.aisdlc.console.domain.model.imports.ParsedResult;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedGoal;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedProject;
import com.aisdlc.console.domain.model.imports.ParsedResult.ParsedTask;
import com.aisdlc.console.domain.model.project.NewProject;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.task.NewTask;
import com.aisdlc.console.domain.model.task.Task;
import com.aisdlc.console.domain.service.FieldRules;
import com.aisdlc.console.domain.service.GoalKeyOrder;
import com.aisdlc.console.domain.service.ParsedResultValidator;
import com.aisdlc.console.domain.service.PassCriteriaSanitizer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Supplier;

/**
 * BRD/PRD 匯入用例（PRD §5.2；契約 §1.1、§3.3）。
 *
 * <p>交易邊界（刻意不是類別層級的 {@code @Transactional}）：{@code parse} 與 {@code signoff} 會呼叫 Bridge／LLM
 * （秒到分鐘級），絕不佔著資料庫交易；它們以 {@link TransactionTemplate} 把「宣告 PARSING」「寫回結果」「寫回失敗」
 * 各切成短交易。尤其<b>失敗必須先提交狀態（退回 UPLOADED、寫 lastParseErrors）再丟例外</b>——例外若在同一交易內
 * 丟出會讓狀態一併回滾，記錄就卡在 PARSING。
 *
 * <p>🔴 人工 signoff 硬閘：signoff 只批准、不落庫（ADR-001 D12）；{@code confirm} 要求已 signoff，並在<b>單一交易</b>內
 * 建立專案／目標／任務（全部 signedOff=true，signedOffBy／At 承襲匯入記錄），任何一步失敗整個交易回滾。
 */
@Service
public class ImportService implements ImportUseCase {

    private static final Logger LOG = LoggerFactory.getLogger(ImportService.class);

    static final int MAX_FILE_BYTES = 10 * 1024 * 1024;
    static final int MAX_TEXT_CHARS = 2_000_000;
    static final int MAX_NAME_CHARS = 500;
    static final int MAX_PAGE_SIZE = 100;
    private static final List<String> ALLOWED_EXTENSIONS = List.of(".md", ".pdf", ".docx");
    private static final byte[] PDF_MAGIC = {'%', 'P', 'D', 'F', '-'};
    private static final byte[] ZIP_MAGIC = {'P', 'K', 3, 4};

    private final ImportRecordRepository records;
    private final DocumentTextExtractor extractor;
    private final ImportParser parser;
    private final ParsedResultValidator validator;
    private final ProjectRepository projects;
    private final GoalRepository goals;
    private final TaskRepository tasks;
    private final AgentBridge bridge;
    private final AuditTrail audit;
    private final Clock clock;
    private final TransactionTemplate tx;

    public ImportService(ImportRecordRepository records, DocumentTextExtractor extractor, ImportParser parser,
                         ProjectRepository projects, GoalRepository goals, TaskRepository tasks,
                         AgentBridge bridge, AuditTrail audit, Clock clock, TransactionTemplate tx,
                         @Value("${console.import.max-steps:24}") int maxSteps) {
        this.records = records;
        this.extractor = extractor;
        this.parser = parser;
        this.validator = new ParsedResultValidator(maxSteps);
        this.projects = projects;
        this.goals = goals;
        this.tasks = tasks;
        this.bridge = bridge;
        this.audit = audit;
        this.clock = clock;
        this.tx = tx;
    }

    // ── 建立（upload／text）────────────────────────────────────────────────────

    @Override
    @Transactional
    public ImportRecord upload(String fileName, byte[] content) {
        if (content == null || content.length == 0) {
            throw ValidationException.of("file", "檔案是空的", ErrorReasons.FILE_EMPTY, Map.of());
        }
        String name = basename(fileName);
        String extension = extensionOf(name);
        if (!ALLOWED_EXTENSIONS.contains(extension)) {
            throw new UnsupportedFormatException("不支援的檔案類型：" + (extension.isEmpty() ? "（無副檔名）" : extension)
                    + "；只支援 .md／.pdf／.docx", ErrorReasons.FILE_TYPE_UNSUPPORTED,
                    Map.of("extension", extension, "allowed", ALLOWED_EXTENSIONS));
        }
        if (content.length > MAX_FILE_BYTES) {
            throw new PayloadTooLargeException("檔案大小 " + content.length + " bytes 超過 10MB 上限",
                    ErrorReasons.FILE_TOO_LARGE, Map.of("limitBytes", MAX_FILE_BYTES));
        }
        ImportSourceType type;
        String text;
        switch (extension) {
            case ".md" -> {
                type = ImportSourceType.MARKDOWN;
                text = decodeUtf8(content);
            }
            case ".pdf" -> {
                type = ImportSourceType.PDF;
                requireMagic(content, PDF_MAGIC, extension);
                text = extract(() -> extractor.extractPdf(content));
            }
            default -> {
                type = ImportSourceType.DOCX;
                requireMagic(content, ZIP_MAGIC, extension);
                text = extract(() -> extractor.extractDocx(content));
            }
        }
        if (text.isBlank()) {
            throw new UnprocessableException("無法從檔案擷取文字（內容全為空白；掃描檔需先做 OCR）",
                    ErrorReasons.FILE_NO_TEXT, Map.of());
        }
        // 上傳的唯一大小上限是 10MB 檔案（契約 §1.1.1）；2,000,000 字元只限制「貼上純文字」（§1.1.2）。
        ImportRecord record = ImportRecord.create(type, text, clip(name, MAX_NAME_CHARS), clock.instant());
        records.save(record);
        audit.note("import.upload", "import", record.id().toString());
        return record;
    }

    @Override
    @Transactional
    public ImportRecord createFromText(String content, String sourceFileName, ImportSourceType sourceType) {
        ImportSourceType type = sourceType == null ? ImportSourceType.PLAIN_TEXT : sourceType;
        Violations v = new Violations();
        if (type != ImportSourceType.PLAIN_TEXT && type != ImportSourceType.MARKDOWN) {
            v.add("sourceType", "sourceType 只能是 PLAIN_TEXT 或 MARKDOWN（PDF／DOCX 只能由 upload 產生）");
        }
        if (content == null || content.isBlank()) {
            v.add("content", "內容不可為空");
        } else if (content.length() > MAX_TEXT_CHARS) {
            v.add("content", "內容長度不可超過 " + MAX_TEXT_CHARS + " 字元");
        }
        if (sourceFileName != null && sourceFileName.length() > MAX_NAME_CHARS) {
            v.add("sourceFileName", "來源名稱長度不可超過 " + MAX_NAME_CHARS + " 字元");
        }
        v.throwIfAny();
        String name = sourceFileName == null || sourceFileName.isBlank() ? null : sourceFileName.strip();
        ImportRecord record = ImportRecord.create(type, content, name, clock.instant());
        records.save(record);
        audit.note("import.text", "import", record.id().toString());
        return record;
    }

    // ── 查詢 ──────────────────────────────────────────────────────────────────

    @Override
    @Transactional(readOnly = true)
    public PageResult<ImportRecord> list(ListQuery query) {
        Violations v = new Violations();
        if (query.page() < 0) {
            v.add("page", "page 不可為負數");
        }
        if (query.size() < 1 || query.size() > MAX_PAGE_SIZE) {
            v.add("size", "size 必須介於 1 到 " + MAX_PAGE_SIZE);
        }
        v.throwIfAny();
        return records.search(query);
    }

    @Override
    @Transactional(readOnly = true)
    public ImportRecord get(UUID id) {
        return load(id, false);
    }

    // ── parse ────────────────────────────────────────────────────────────────

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public ParseOutcome parse(UUID id, ParseOptions options) {
        ParseOptions checked = checkOptions(options);
        ImportRecord claimed = tx.execute(status -> {
            ImportRecord record = load(id, true);
            record.beginParse(checked);      // 同一交易內把本次請求的選項原樣存下（C-10；不論之後成敗）
            return records.save(record);
        });
        audit.note("import.parse", "import", id.toString());
        try {
            ImportParser.Draft draft = parser.parse(claimed, checked);
            List<GateError> gates = validator.validate(draft.result());
            if (!gates.isEmpty()) {
                throw ImportParser.gateRejected(draft.result().path(), gates);
            }
            ImportRecord done = tx.execute(status -> {
                ImportRecord record = load(id, true);
                record.completeParse(draft.result(), draft.warnings());
                return records.save(record);
            });
            return new ParseOutcome(done, draft.warnings());
        } catch (RuntimeException failure) {
            // 失敗一律先提交「退回 UPLOADED」（僅被有界閘拒絕時另存 lastParseErrors），再丟原例外。
            List<GateError> stored = failure instanceof UnprocessableException unprocessable
                    && !unprocessable.gateErrors().isEmpty() ? unprocessable.gateErrors() : null;
            recordParseFailure(id, stored, failure);
            throw failure;
        }
    }

    private void recordParseFailure(UUID id, List<GateError> gateErrors, RuntimeException original) {
        try {
            tx.executeWithoutResult(status -> {
                ImportRecord record = load(id, true);
                record.failParse(gateErrors);
                records.save(record);
            });
        } catch (RuntimeException secondary) {
            LOG.error("解析失敗後無法把匯入記錄 {} 退回 UPLOADED（它會卡在 PARSING，直到下次啟動復原）", id, secondary);
            original.addSuppressed(secondary);
        }
    }

    private static ParseOptions checkOptions(ParseOptions options) {
        Violations v = new Violations();
        String path = FieldRules.executionPath(v, "executionPath", options.executionPath());
        Integer autonomy = FieldRules.autonomyLevel(v, "autonomyLevel", options.autonomyLevel(),
                ImportParser.DEFAULT_AUTONOMY);
        if (options.additionalPrompt() != null && options.additionalPrompt().length() > 4000) {
            v.add("additionalPrompt", "補充說明長度不可超過 4000 字元");
        }
        if (options.specDir() != null && options.specDir().length() > 500) {
            v.add("specDir", "specDir 長度不可超過 500 字元");
        }
        v.throwIfAny();
        return new ParseOptions(path, autonomy, options.additionalPrompt(), options.specDir());
    }

    // ── PUT result ───────────────────────────────────────────────────────────

    @Override
    @Transactional
    public ParseOutcome editResult(UUID id, ParsedResult edited) {
        ImportRecord record = load(id, true);
        record.requireEditAllowed();
        ParsedResult tree = renumber(edited);
        sanitize(tree);
        List<GateError> gates = validator.validate(tree);
        if (!gates.isEmpty()) {
            throw ImportParser.gateRejected(record.parsePath(), gates);
        }
        // 提示只取決於三層樹（伺服器欄位不影響），所以先算再存：重算後的值覆寫記錄的 warnings（C-10），回應與重開記錄所見一致
        List<ParseWarning> warnings = placeholderWarnings(tree);
        record.editResult(tree, warnings);
        records.save(record);
        audit.note("import.result", "import", id.toString());
        return new ParseOutcome(record, warnings);
    }

    /** 陣列順序即排序：目標與任務的 sortOrder 由伺服器重編為 0 起連續整數（請求帶的值忽略）。 */
    private static ParsedResult renumber(ParsedResult edited) {
        List<ParsedGoal> goals = new ArrayList<>();
        List<ParsedGoal> rawGoals = edited.goals() == null ? List.of() : edited.goals();
        for (int i = 0; i < rawGoals.size(); i++) {
            ParsedGoal g = rawGoals.get(i);
            List<ParsedTask> tasks = new ArrayList<>();
            List<ParsedTask> rawTasks = g.tasks() == null ? List.of() : g.tasks();
            for (int j = 0; j < rawTasks.size(); j++) {
                ParsedTask t = rawTasks.get(j);
                tasks.add(new ParsedTask(t.name(), t.description(), t.passCriteria(), j, t.estimatedTokens(),
                        t.evaluatorCommand(), t.expectedOutputRegex(), t.passCriteriaSpec(), t.maxRetries()));
            }
            goals.add(new ParsedGoal(g.key(), g.name(), g.description(), g.passCriteria(), i,
                    g.dependsOn() == null ? List.of() : g.dependsOn(), tasks));
        }
        return ParsedResult.tree(edited.project(), goals);
    }

    /** NFR-SEC-03：evaluatorCommand 不得含禁用字元、expectedOutputRegex 須可編譯（與 Phase 2 任務建立同規則，400）。 */
    private static void sanitize(ParsedResult tree) {
        for (int i = 0; i < tree.goals().size(); i++) {
            List<ParsedTask> tasks = tree.goals().get(i).tasks();
            for (int j = 0; j < tasks.size(); j++) {
                String base = "parsedResult.goals[" + i + "].tasks[" + j + "]";
                PassCriteriaSanitizer.requireSafeCommand(base + ".evaluatorCommand", tasks.get(j).evaluatorCommand());
                PassCriteriaSanitizer.requireCompilableRegex(base + ".expectedOutputRegex",
                        tasks.get(j).expectedOutputRegex());
            }
        }
    }

    private static List<ParseWarning> placeholderWarnings(ParsedResult tree) {
        List<ParseWarning> warnings = new ArrayList<>();
        if (tree == null) {
            return warnings;
        }
        if (ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT.equals(tree.project().passCriteria())) {
            warnings.add(new ParseWarning(ParseWarning.PASSCRITERIA_PLACEHOLDER,
                    "專案的通過標準仍是佔位字串，請於 signoff 前補齊", "project"));
        }
        for (int i = 0; i < tree.goals().size(); i++) {
            ParsedGoal goal = tree.goals().get(i);
            if (ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT.equals(goal.passCriteria())) {
                warnings.add(new ParseWarning(ParseWarning.PASSCRITERIA_PLACEHOLDER,
                        "目標「" + goal.name() + "」的通過標準仍是佔位字串，請於 signoff 前補齊", "goals[" + i + "]"));
            }
            for (int j = 0; j < goal.tasks().size(); j++) {
                if (ParseWarning.PASSCRITERIA_PLACEHOLDER_TEXT.equals(goal.tasks().get(j).passCriteria())) {
                    warnings.add(new ParseWarning(ParseWarning.PASSCRITERIA_PLACEHOLDER,
                            "任務「" + goal.tasks().get(j).name() + "」的通過標準仍是佔位字串，請於 signoff 前補齊",
                            "goals[" + i + "].tasks[" + j + "]"));
                }
            }
        }
        return warnings;
    }

    // ── signoff ──────────────────────────────────────────────────────────────

    /** 🔴 人工 signoff：先驗狀態、再對路徑 C 的每個 draft 呼叫 Bridge {@code :approve}（任一失敗不改任何狀態），最後才簽。 */
    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public ImportRecord signoff(UUID id, String approver) {
        if (approver == null || approver.isBlank()) {
            throw ValidationException.of("approver", "approver 不可為空（人工 signoff 不可匿名）");
        }
        String who = approver.strip();
        ImportRecord before = tx.execute(status -> {
            ImportRecord record = load(id, false);
            record.requireSignoffAllowed();
            return record;
        });
        List<String> draftIds = before.parsedResult() == null || before.parsedResult().draftIds() == null
                ? List.of() : before.parsedResult().draftIds();
        for (String draftId : draftIds) {
            approveDraft(draftId, who);
        }
        ImportRecord signed = tx.execute(status -> {
            ImportRecord record = load(id, true);
            record.signoff(who, clock.instant());
            return records.save(record);
        });
        audit.note("import.signoff", "import", id.toString());
        return signed;
    }

    private void approveDraft(String draftId, String approver) {
        try {
            bridge.approveDraft(draftId, approver);
        } catch (BridgeRejectedException e) {
            if (e.status() == 409 && "already_signed_off".equals(e.reason())) {
                return;                        // 冪等：已簽署過視為成功
            }
            if (e.status() == 404 && "draft_not_found".equals(e.reason())) {
                throw new ConflictException("Bridge 上找不到草案 " + draftId + "（工作區可能已被清除），請重新解析",
                        ErrorReasons.DRAFT_EXPIRED, Map.of("draftId", draftId));
            }
            throw new UpstreamException.Failure("Bridge 批准草案時回了非預期的錯誤（HTTP " + e.status() + "）",
                    Map.of("bridgeStatus", e.status(), "bridgeReason", e.reason()));
        }
    }

    // ── confirm ──────────────────────────────────────────────────────────────

    @Override
    @Transactional
    public ProjectView confirm(UUID id, String actor) {
        ImportRecord record = load(id, true);
        record.requireConfirmAllowed();
        ParsedResult tree = record.parsedResult();
        List<GateError> gates = validator.validate(tree);
        if (!gates.isEmpty()) {
            throw ImportParser.gateRejected(record.parsePath(), gates);
        }
        Instant now = clock.instant();
        String approver = record.signedOffBy();
        Instant approvedAt = record.signedOffAt();

        ParsedProject p = tree.project();
        Project project = withPath("parsedResult.project", () -> Project.create(
                new NewProject(p.name(), p.executionPath(), p.passCriteria(), p.description(), p.autonomyLevel(),
                        false), actor, now));
        project.inheritSignoff(approver, approvedAt);
        projects.save(project);

        // 依賴在前建立（goal_dependencies 有外鍵）；sortOrder 取自陣列位置，與建立順序無關
        Map<String, UUID> idByKey = new HashMap<>();
        int taskCount = 0;
        for (int index : GoalKeyOrder.dependencyFirstIndexes(tree.goals())) {
            ParsedGoal g = tree.goals().get(index);
            String goalPath = "parsedResult.goals[" + index + "]";
            List<UUID> dependsOn = new ArrayList<>();
            for (String key : g.dependsOn() == null ? List.<String>of() : g.dependsOn()) {
                dependsOn.add(idByKey.get(key));
            }
            Goal goal = withPath(goalPath, () -> Goal.create(project.id(),
                    new NewGoal(g.name(), g.description(), g.passCriteria(), dependsOn, false), g.sortOrder(), now));
            goal.inheritSignoff(approver, approvedAt);
            goals.save(goal);
            idByKey.put(g.key(), goal.id());
            for (int j = 0; j < g.tasks().size(); j++) {
                ParsedTask t = g.tasks().get(j);
                Task task = withPath(goalPath + ".tasks[" + j + "]", () -> Task.create(goal.id(),
                        new NewTask(t.name(), t.description(), t.passCriteria(), t.evaluatorCommand(),
                                t.expectedOutputRegex(), t.passCriteriaSpec() == null || t.passCriteriaSpec().isEmpty()
                                        ? null : JsonStrings.toJson(t.passCriteriaSpec()), t.estimatedTokens(),
                                t.maxRetries(), false), t.sortOrder(), now));
                task.inheritSignoff(approver, approvedAt);
                tasks.save(task);
                taskCount++;
            }
        }
        record.markImported(project.id());
        records.save(record);
        audit.note("import.confirm", "import", id.toString());
        return new ProjectView(project, new ProjectCounts(tree.goals().size(), taskCount, 0));
    }

    /** 落庫前複驗不過：把 domain 的欄位名補上 {@code parsedResult.goals[i].tasks[j].} 前綴（契約 §1.1.6）。 */
    private static <T> T withPath(String path, Supplier<T> action) {
        try {
            return action.get();
        } catch (ValidationException e) {
            List<Violation> prefixed = e.violations().stream()
                    .map(v -> new Violation(path + "." + v.field(), v.message())).toList();
            throw new ValidationException(e.getMessage(), e.reason(), prefixed, e.details());
        }
    }

    // ── reject ───────────────────────────────────────────────────────────────

    @Override
    @Transactional
    public ImportRecord reject(UUID id) {
        ImportRecord record = load(id, true);
        record.reject();
        records.save(record);
        audit.note("import.reject", "import", id.toString());
        return record;
    }

    // ── 共用 ─────────────────────────────────────────────────────────────────

    private ImportRecord load(UUID id, boolean forUpdate) {
        Optional<ImportRecord> found = forUpdate ? records.findByIdForUpdate(id) : records.findById(id);
        return found.orElseThrow(() -> NotFoundException.of("匯入記錄", id));
    }

    private static String basename(String fileName) {
        if (fileName == null) {
            return "";
        }
        String name = fileName.strip();
        int cut = Math.max(name.lastIndexOf('/'), name.lastIndexOf('\\'));
        return cut >= 0 ? name.substring(cut + 1) : name;
    }

    private static String extensionOf(String name) {
        int dot = name.lastIndexOf('.');
        return dot < 0 ? "" : name.substring(dot).toLowerCase(Locale.ROOT);
    }

    private static void requireMagic(byte[] content, byte[] magic, String extension) {
        boolean matches = content.length >= magic.length;
        for (int i = 0; matches && i < magic.length; i++) {
            matches = content[i] == magic[i];
        }
        if (!matches) {
            throw new UnprocessableException("檔案內容與副檔名 " + extension + " 不符", ErrorReasons.FILE_CONTENT_MISMATCH,
                    Map.of("extension", extension));
        }
    }

    /** 嚴格 UTF-8 解碼（容許 BOM）；任何非法位元組序列都拒絕，不做靜默替換。 */
    private static String decodeUtf8(byte[] content) {
        try {
            String text = StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(content)).toString();
            return text.startsWith("﻿") ? text.substring(1) : text;
        } catch (CharacterCodingException e) {
            throw new UnprocessableException("檔案不是有效的 UTF-8 文字（.md 須為 UTF-8）", ErrorReasons.FILE_NOT_UTF8,
                    Map.of());
        }
    }

    private static String extract(Supplier<String> extraction) {
        try {
            return extraction.get();
        } catch (ExtractionException e) {
            if (e.kind() == ExtractionException.Kind.ENCRYPTED) {
                throw new UnprocessableException("PDF 已加密，無法擷取文字", ErrorReasons.PDF_ENCRYPTED, Map.of());
            }
            throw new UnprocessableException("檔案已損毀，無法讀取", ErrorReasons.FILE_CORRUPT, Map.of());
        }
    }

    private static String clip(String value, int max) {
        return value.length() <= max ? value : value.substring(0, max);
    }
}
