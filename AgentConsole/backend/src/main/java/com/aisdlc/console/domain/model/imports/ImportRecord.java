package com.aisdlc.console.domain.model.imports;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ValidationException;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 匯入記錄聚合（PRD §5.2；契約 §1.1；純 Java）。
 *
 * <p>狀態機與動作可用性表（✗ 一律 409 {@code 匯入記錄狀態不允許此操作}，details＝{@code {action,status}}）：
 * <pre>
 *            parse        PUT result   signoff   confirm        reject
 * UPLOADED     ✓             ✗           ✗         ✗              ✓
 * PARSING    ✗(解析中)       ✗           ✗         ✗              ✗
 * PARSED     ✓(未signoff)    ✓           ✓       ✓(需已signoff)    ✓
 * REVIEWING  ✓(未signoff)    ✓(撤銷)     ✓       ✓(需已signoff)    ✓
 * IMPORTED/REJECTED ✗        ✗           ✗      ✗(IMPORTED→已匯入)  ✗
 * </pre>
 * 🔴 人工 signoff 硬閘：編輯會撤銷既有 signoff；confirm 要求已 signoff。
 * 失敗的 parse 不寫 {@code parsedResult}／{@code parsePath}（AR-07）；只有被有界閘拒絕時才寫 {@code lastParseErrors}。
 */
public final class ImportRecord {

    public static final String ACTION_PARSE = "parse";
    public static final String ACTION_EDIT_RESULT = "editResult";
    public static final String ACTION_SIGNOFF = "signoff";
    public static final String ACTION_CONFIRM = "confirm";
    public static final String ACTION_REJECT = "reject";

    private final UUID id;
    private final ImportSourceType sourceType;
    private final String sourceContent;
    private final String sourceFileName;
    private ParsedResult parsedResult;
    private ParsePath parsePath;
    private String aiModel;
    private Long tokenUsed;
    private ImportStatus status;
    private boolean signedOff;
    private String signedOffBy;
    private Instant signedOffAt;
    private UUID projectId;
    private final Instant createdAt;
    private List<GateError> lastParseErrors;

    @SuppressWarnings("java:S107")
    private ImportRecord(UUID id, ImportSourceType sourceType, String sourceContent, String sourceFileName,
                         ParsedResult parsedResult, ParsePath parsePath, String aiModel, Long tokenUsed,
                         ImportStatus status, boolean signedOff, String signedOffBy, Instant signedOffAt,
                         UUID projectId, Instant createdAt, List<GateError> lastParseErrors) {
        this.id = id;
        this.sourceType = sourceType;
        this.sourceContent = sourceContent;
        this.sourceFileName = sourceFileName;
        this.parsedResult = parsedResult;
        this.parsePath = parsePath;
        this.aiModel = aiModel;
        this.tokenUsed = tokenUsed;
        this.status = status;
        this.signedOff = signedOff;
        this.signedOffBy = signedOffBy;
        this.signedOffAt = signedOffAt;
        this.projectId = projectId;
        this.createdAt = createdAt;
        this.lastParseErrors = lastParseErrors;
    }

    /** 建立新記錄：UPLOADED、未 signoff。內容與檔名的長度／空白檢查由呼叫端（用例）負責。 */
    public static ImportRecord create(ImportSourceType sourceType, String content, String fileName, Instant now) {
        return new ImportRecord(UUID.randomUUID(), sourceType, content, fileName, null, null, null, null,
                ImportStatus.UPLOADED, false, null, null, null, now, null);
    }

    /** 由持久層資料還原。 */
    @SuppressWarnings("java:S107")
    public static ImportRecord restore(UUID id, ImportSourceType sourceType, String sourceContent,
                                       String sourceFileName, ParsedResult parsedResult, ParsePath parsePath,
                                       String aiModel, Long tokenUsed, ImportStatus status, boolean signedOff,
                                       String signedOffBy, Instant signedOffAt, UUID projectId, Instant createdAt,
                                       List<GateError> lastParseErrors) {
        return new ImportRecord(id, sourceType, sourceContent, sourceFileName, parsedResult, parsePath, aiModel,
                tokenUsed, status, signedOff, signedOffBy, signedOffAt, projectId, createdAt,
                lastParseErrors == null ? null : List.copyOf(lastParseErrors));
    }

    // ── parse ────────────────────────────────────────────────────────────────

    /**
     * 前置檢查順序固定：IMPORTED／REJECTED → 狀態不允許；PARSING → 解析中；已 signoff → 不可重新解析。
     * 通過後轉 PARSING 並清空 {@code lastParseErrors}（契約 §1.1.3）。
     */
    public void beginParse() {
        if (status.terminal()) {
            throw stateNotAllowed(ACTION_PARSE);
        }
        if (status == ImportStatus.PARSING) {
            throw new ConflictException("這筆匯入記錄正在解析中，請稍候再試", ErrorReasons.IMPORT_PARSING,
                    Map.of("status", ImportStatus.PARSING.name()));
        }
        if (signedOff) {
            throw new ConflictException("已 signoff 的草案不可重新解析；請先編輯以撤銷 signoff 或放棄後重新匯入",
                    ErrorReasons.IMPORT_SIGNED_OFF_NO_REPARSE,
                    Map.of("signedOffBy", String.valueOf(signedOffBy), "signedOffAt", String.valueOf(signedOffAt)));
        }
        status = ImportStatus.PARSING;
        lastParseErrors = null;
    }

    /** 解析成功：PARSED、未 signoff；寫入樹與伺服器欄位，清空最近一次閘違規。 */
    public void completeParse(ParsedResult result) {
        requireStatus(ImportStatus.PARSING, ACTION_PARSE);
        parsedResult = result;
        parsePath = result.path();
        aiModel = result.aiModel();
        tokenUsed = result.tokenUsed();
        status = ImportStatus.PARSED;
        signedOff = false;
        signedOffBy = null;
        signedOffAt = null;
        lastParseErrors = null;
    }

    /**
     * 解析失敗：一律退回 UPLOADED。保留先前成功解析的 {@code parsedResult}（使用者的編輯不因一次失敗的重解析而消失）；
     * 僅「被有界閘拒絕」時（{@code gateErrors} 非 null）寫入 {@code lastParseErrors}。
     */
    public void failParse(List<GateError> gateErrors) {
        requireStatus(ImportStatus.PARSING, ACTION_PARSE);
        status = ImportStatus.UPLOADED;
        lastParseErrors = gateErrors == null ? null : List.copyOf(gateErrors);
    }

    // ── PUT result ───────────────────────────────────────────────────────────

    /** 編輯的前置檢查（僅 PARSED／REVIEWING）；用例先檢查狀態（409），再做消毒（400）與有界閘（422）。 */
    public void requireEditAllowed() {
        if (!status.hasDraft()) {
            throw stateNotAllowed(ACTION_EDIT_RESULT);
        }
    }

    /** 編輯：僅 PARSED／REVIEWING；成功後 REVIEWING，<b>撤銷既有 signoff</b>；伺服器欄位沿用庫內值。 */
    public void editResult(ParsedResult edited) {
        requireEditAllowed();
        parsedResult = parsedResult == null ? edited : edited.withServerFieldsOf(parsedResult);
        status = ImportStatus.REVIEWING;
        signedOff = false;
        signedOffBy = null;
        signedOffAt = null;
    }

    // ── signoff ──────────────────────────────────────────────────────────────

    /** signoff 的前置檢查（狀態須為 PARSED／REVIEWING 且尚未 signoff）；不改任何狀態。 */
    public void requireSignoffAllowed() {
        if (!status.hasDraft()) {
            throw stateNotAllowed(ACTION_SIGNOFF);
        }
        if (signedOff) {
            throw alreadySignedOff();
        }
    }

    /** 人工 signoff：approver 不可為空白；只批准、不落庫（落庫由 confirm 負責，ADR-001 D12）。 */
    public void signoff(String approver, Instant now) {
        if (approver == null || approver.isBlank()) {
            throw ValidationException.of("approver", "approver 不可為空（人工 signoff 不可匿名）");
        }
        requireSignoffAllowed();
        signedOff = true;
        signedOffBy = approver.strip();
        signedOffAt = now;
    }

    // ── confirm ──────────────────────────────────────────────────────────────

    /** confirm 的前置檢查：IMPORTED→已匯入；非 PARSED／REVIEWING→狀態不允許；未 signoff→草案尚未 signoff。 */
    public void requireConfirmAllowed() {
        if (status == ImportStatus.IMPORTED) {
            throw new ConflictException("這筆匯入記錄已經確認匯入過了", ErrorReasons.ALREADY_IMPORTED,
                    Map.of("projectId", String.valueOf(projectId)));
        }
        if (!status.hasDraft()) {
            throw stateNotAllowed(ACTION_CONFIRM);
        }
        if (!signedOff) {
            throw new ConflictException("草案尚未經人工 signoff，不可確認匯入", ErrorReasons.IMPORT_NOT_SIGNED_OFF,
                    Map.of("status", status.name(), "signedOff", false));
        }
    }

    /** 落庫成功：IMPORTED 並回填 projectId。 */
    public void markImported(UUID newProjectId) {
        requireConfirmAllowed();
        projectId = newProjectId;
        status = ImportStatus.IMPORTED;
    }

    // ── reject ───────────────────────────────────────────────────────────────

    /** 放棄：任何非終態且非 PARSING 的記錄 → REJECTED（不呼叫 Bridge）。 */
    public void reject() {
        if (status.terminal() || status == ImportStatus.PARSING) {
            throw stateNotAllowed(ACTION_REJECT);
        }
        status = ImportStatus.REJECTED;
    }

    // ── 共用 ─────────────────────────────────────────────────────────────────

    private void requireStatus(ImportStatus expected, String action) {
        if (status != expected) {
            throw stateNotAllowed(action);
        }
    }

    private ConflictException stateNotAllowed(String action) {
        return new ConflictException("匯入記錄目前狀態為 " + status + "，不允許執行 " + action,
                ErrorReasons.IMPORT_STATE_NOT_ALLOWED, Map.of("action", action, "status", status.name()));
    }

    private ConflictException alreadySignedOff() {
        return new ConflictException("匯入草案已完成 signoff，不可重複簽核", ErrorReasons.ALREADY_SIGNED_OFF,
                Map.of("signedOffBy", String.valueOf(signedOffBy), "signedOffAt", String.valueOf(signedOffAt)));
    }

    public UUID id() {
        return id;
    }

    public ImportSourceType sourceType() {
        return sourceType;
    }

    public String sourceContent() {
        return sourceContent;
    }

    public String sourceFileName() {
        return sourceFileName;
    }

    public ParsedResult parsedResult() {
        return parsedResult;
    }

    public ParsePath parsePath() {
        return parsePath;
    }

    public String aiModel() {
        return aiModel;
    }

    public Long tokenUsed() {
        return tokenUsed;
    }

    public ImportStatus status() {
        return status;
    }

    public boolean signedOff() {
        return signedOff;
    }

    public String signedOffBy() {
        return signedOffBy;
    }

    public Instant signedOffAt() {
        return signedOffAt;
    }

    public UUID projectId() {
        return projectId;
    }

    public Instant createdAt() {
        return createdAt;
    }

    /** 最近一次 parse 被有界閘拒絕的原因；沒有則為 null。 */
    public List<GateError> lastParseErrors() {
        return lastParseErrors;
    }
}
