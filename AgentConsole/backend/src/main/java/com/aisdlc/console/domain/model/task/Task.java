package com.aisdlc.console.domain.model.task;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.service.FieldRules;
import com.aisdlc.console.domain.service.PassCriteriaSanitizer;
import com.aisdlc.console.domain.service.StateMachines;

import java.time.Instant;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * 任務聚合（PRD §5.1.3；純 Java）。
 *
 * <p>不變式：evaluatorCommand 不得含黑名單字元、expectedOutputRegex 必須可編譯（NFR-SEC-03，建立與更新都套用）；
 * 狀態轉移走 {@link #transitionTo(TaskStatus, Instant)}（附錄 B.3）；RUNNING 的任務不可刪除；
 * retry 只允許 FAILED／ESCALATED。
 */
public final class Task {

    public static final int DEFAULT_MAX_RETRIES = 3;

    private final UUID id;
    private final UUID goalId;
    private String name;
    private String description;
    private String passCriteria;
    private String evaluatorCommand;
    private String expectedOutputRegex;
    private String passCriteriaSpec;
    private int sortOrder;
    private TaskStatus status;
    private Long estimatedTokens;
    private Long actualTokens;
    private int retryCount;
    private int maxRetries;
    private String assignedAgent;
    private String executionLog;
    private boolean signedOff;
    private String signedOffBy;
    private Instant signedOffAt;
    private boolean deleted;
    private final Instant createdAt;
    private Instant updatedAt;
    private Instant startedAt;
    private Instant completedAt;

    @SuppressWarnings("java:S107")
    private Task(UUID id, UUID goalId, String name, String description, String passCriteria,
                 String evaluatorCommand, String expectedOutputRegex, String passCriteriaSpec, int sortOrder,
                 TaskStatus status, Long estimatedTokens, Long actualTokens, int retryCount, int maxRetries,
                 String assignedAgent, String executionLog, boolean signedOff, String signedOffBy,
                 Instant signedOffAt, boolean deleted, Instant createdAt, Instant updatedAt, Instant startedAt,
                 Instant completedAt) {
        this.id = id;
        this.goalId = goalId;
        this.name = name;
        this.description = description;
        this.passCriteria = passCriteria;
        this.evaluatorCommand = evaluatorCommand;
        this.expectedOutputRegex = expectedOutputRegex;
        this.passCriteriaSpec = passCriteriaSpec;
        this.sortOrder = sortOrder;
        this.status = status;
        this.estimatedTokens = estimatedTokens;
        this.actualTokens = actualTokens;
        this.retryCount = retryCount;
        this.maxRetries = maxRetries;
        this.assignedAgent = assignedAgent;
        this.executionLog = executionLog;
        this.signedOff = signedOff;
        this.signedOffBy = signedOffBy;
        this.signedOffAt = signedOffAt;
        this.deleted = deleted;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.startedAt = startedAt;
        this.completedAt = completedAt;
    }

    /** 建立新任務（狀態 PENDING、retryCount 0；sortOrder 由 application 層算出「排末」後傳入）。 */
    public static Task create(UUID goalId, NewTask spec, int sortOrder, Instant now) {
        Violations v = new Violations();
        String name = FieldRules.requiredText(v, "name", "名稱", spec.name(), 200);
        String passCriteria = FieldRules.requiredMarkdown(v, "passCriteria", "通過標準", spec.passCriteria());
        String command = FieldRules.optionalText(v, "evaluatorCommand", "驗證命令", spec.evaluatorCommand(), 1000);
        String regex = FieldRules.optionalText(v, "expectedOutputRegex", "期望輸出正規表示式",
                spec.expectedOutputRegex(), 1000);
        int maxRetries = spec.maxRetries() == null ? DEFAULT_MAX_RETRIES : spec.maxRetries();
        if (maxRetries < 0) {
            v.add("maxRetries", "最大重試次數不可為負數");
        }
        if (spec.estimatedTokens() != null && spec.estimatedTokens() < 0) {
            v.add("estimatedTokens", "預估 Token 不可為負數");
        }
        v.throwIfAny();
        PassCriteriaSanitizer.requireSafeCommand("evaluatorCommand", command);
        PassCriteriaSanitizer.requireCompilableRegex("expectedOutputRegex", regex);
        return new Task(UUID.randomUUID(), goalId, name, FieldRules.optionalMarkdown(spec.description()),
                passCriteria, command, regex, FieldRules.optionalMarkdown(spec.passCriteriaSpec()), sortOrder,
                TaskStatus.PENDING, spec.estimatedTokens(), null, 0, maxRetries, null, null, !spec.draft(),
                null, null, false, now, now, null, null);
    }

    /** 由持久層資料還原。 */
    @SuppressWarnings("java:S107")
    public static Task restore(UUID id, UUID goalId, String name, String description, String passCriteria,
                               String evaluatorCommand, String expectedOutputRegex, String passCriteriaSpec,
                               int sortOrder, TaskStatus status, Long estimatedTokens, Long actualTokens,
                               int retryCount, int maxRetries, String assignedAgent, String executionLog,
                               boolean signedOff, String signedOffBy, Instant signedOffAt, boolean deleted,
                               Instant createdAt, Instant updatedAt, Instant startedAt, Instant completedAt) {
        return new Task(id, goalId, name, description, passCriteria, evaluatorCommand, expectedOutputRegex,
                passCriteriaSpec, sortOrder, status, estimatedTokens, actualTokens, retryCount, maxRetries,
                assignedAgent, executionLog, signedOff, signedOffBy, signedOffAt, deleted, createdAt, updatedAt,
                startedAt, completedAt);
    }

    /** 套用更新（null 欄位不變；evaluator／regex／spec 給空白＝清除）；NFR-SEC-03 消毒同建立。 */
    public void update(TaskUpdate update, Instant now) {
        Violations v = new Violations();
        String newName = name;
        if (update.name() != null) {
            newName = FieldRules.requiredText(v, "name", "名稱", update.name(), 200);
        }
        String newCriteria = passCriteria;
        if (update.passCriteria() != null) {
            newCriteria = FieldRules.requiredMarkdown(v, "passCriteria", "通過標準", update.passCriteria());
        }
        String newCommand = evaluatorCommand;
        if (update.evaluatorCommand() != null) {
            newCommand = FieldRules.optionalText(v, "evaluatorCommand", "驗證命令", update.evaluatorCommand(), 1000);
        }
        String newRegex = expectedOutputRegex;
        if (update.expectedOutputRegex() != null) {
            newRegex = FieldRules.optionalText(v, "expectedOutputRegex", "期望輸出正規表示式",
                    update.expectedOutputRegex(), 1000);
        }
        if (update.maxRetries() != null && update.maxRetries() < 0) {
            v.add("maxRetries", "最大重試次數不可為負數");
        }
        if (update.sortOrder() != null && update.sortOrder() < 0) {
            v.add("sortOrder", "排序順序不可為負數");
        }
        if (update.estimatedTokens() != null && update.estimatedTokens() < 0) {
            v.add("estimatedTokens", "預估 Token 不可為負數");
        }
        v.throwIfAny();
        PassCriteriaSanitizer.requireSafeCommand("evaluatorCommand", newCommand);
        PassCriteriaSanitizer.requireCompilableRegex("expectedOutputRegex", newRegex);

        String newDescription = update.description() == null ? description
                : FieldRules.optionalMarkdown(update.description());
        String newSpec = update.passCriteriaSpec() == null ? passCriteriaSpec
                : FieldRules.optionalMarkdown(update.passCriteriaSpec());
        int newMaxRetries = update.maxRetries() == null ? maxRetries : update.maxRetries();
        int newSortOrder = update.sortOrder() == null ? sortOrder : update.sortOrder();
        Long newEstimated = update.estimatedTokens() == null ? estimatedTokens : update.estimatedTokens();

        boolean changed = !Objects.equals(newName, name)
                || !Objects.equals(newDescription, description)
                || !Objects.equals(newCriteria, passCriteria)
                || !Objects.equals(newCommand, evaluatorCommand)
                || !Objects.equals(newRegex, expectedOutputRegex)
                || !Objects.equals(newSpec, passCriteriaSpec)
                || newMaxRetries != maxRetries
                || newSortOrder != sortOrder
                || !Objects.equals(newEstimated, estimatedTokens);
        name = newName;
        description = newDescription;
        passCriteria = newCriteria;
        evaluatorCommand = newCommand;
        expectedOutputRegex = newRegex;
        passCriteriaSpec = newSpec;
        maxRetries = newMaxRetries;
        sortOrder = newSortOrder;
        estimatedTokens = newEstimated;
        if (changed) {
            updatedAt = now;
        }
    }

    /** 狀態轉移（附錄 B.3）；非法轉移丟 409。 */
    public void transitionTo(TaskStatus target, Instant now) {
        StateMachines.requireTransition(status, target);
        status = target;
        updatedAt = now;
    }

    /** 手動重試：只允許 FAILED／ESCALATED；retryCount+1、狀態轉 QUEUED（US-T-06）。 */
    public void retry(Instant now) {
        if (status != TaskStatus.FAILED && status != TaskStatus.ESCALATED) {
            throw new ConflictException("只有 FAILED 或 ESCALATED 的任務可以重試", "目前狀態不可重試",
                    Map.of("status", status.name()));
        }
        transitionTo(TaskStatus.QUEUED, now);
        retryCount++;
    }

    /** 人工 signoff：approver 不可為空白、不可重複。 */
    public void signoff(String approver, Instant now) {
        if (approver == null || approver.isBlank()) {
            throw ValidationException.of("approver", "approver 不可為空（人工 signoff 不可匿名）");
        }
        if (signedOff) {
            throw new ConflictException("任務已完成 signoff，不可重複簽核", "已 signoff",
                    Map.of("signedOffBy", String.valueOf(signedOffBy), "signedOffAt", String.valueOf(signedOffAt)));
        }
        signedOff = true;
        signedOffBy = approver.strip();
        signedOffAt = now;
        updatedAt = now;
    }

    /** 匯入確認落庫專用：{@code signedOff=true}，{@code signedOffBy／At} 承襲匯入記錄（契約 §1.1.6）。 */
    public void inheritSignoff(String approver, Instant at) {
        signedOff = true;
        signedOffBy = approver;
        signedOffAt = at;
    }

    /** 軟刪除：RUNNING 的任務不可直接刪除（US-T-04，409）。 */
    public void softDelete(Instant now) {
        if (status == TaskStatus.RUNNING) {
            throw new ConflictException("執行中的任務不可刪除", "RUNNING 狀態的任務不可刪除",
                    Map.of("status", status.name()));
        }
        deleted = true;
        updatedAt = now;
    }

    public UUID id() {
        return id;
    }

    public UUID goalId() {
        return goalId;
    }

    public String name() {
        return name;
    }

    public String description() {
        return description;
    }

    public String passCriteria() {
        return passCriteria;
    }

    public String evaluatorCommand() {
        return evaluatorCommand;
    }

    public String expectedOutputRegex() {
        return expectedOutputRegex;
    }

    public String passCriteriaSpec() {
        return passCriteriaSpec;
    }

    public int sortOrder() {
        return sortOrder;
    }

    public TaskStatus status() {
        return status;
    }

    public Long estimatedTokens() {
        return estimatedTokens;
    }

    public Long actualTokens() {
        return actualTokens;
    }

    public int retryCount() {
        return retryCount;
    }

    public int maxRetries() {
        return maxRetries;
    }

    public String assignedAgent() {
        return assignedAgent;
    }

    public String executionLog() {
        return executionLog;
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

    public boolean deleted() {
        return deleted;
    }

    public Instant createdAt() {
        return createdAt;
    }

    public Instant updatedAt() {
        return updatedAt;
    }

    public Instant startedAt() {
        return startedAt;
    }

    public Instant completedAt() {
        return completedAt;
    }
}
