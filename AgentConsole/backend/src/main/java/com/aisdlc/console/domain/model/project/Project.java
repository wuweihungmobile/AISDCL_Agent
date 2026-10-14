package com.aisdlc.console.domain.model.project;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.service.FieldRules;
import com.aisdlc.console.domain.service.StateMachines;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * 專案聚合根（PRD §5.1.1；純 Java，不依賴 Spring／JPA）。
 *
 * <p>不變式：狀態轉移只能經由 {@link #transitionTo(ProjectStatus, Instant)}（附錄 B.1）；EXECUTING 時只准改
 * 名稱與說明；signoff 不可匿名且不可重複；軟刪除＝{@code deleted=true} 且 {@code status=ARCHIVED}。
 */
public final class Project {

    public static final int DEFAULT_AUTONOMY_LEVEL = 3;

    private final UUID id;
    private String name;
    private String executionPath;
    private String passCriteria;
    private String description;
    private ProjectStatus status;
    private int autonomyLevel;
    private boolean signedOff;
    private String signedOffBy;
    private Instant signedOffAt;
    private boolean deleted;
    private final Instant createdAt;
    private Instant updatedAt;
    private final String createdBy;

    private Project(UUID id, String name, String executionPath, String passCriteria, String description,
                    ProjectStatus status, int autonomyLevel, boolean signedOff, String signedOffBy,
                    Instant signedOffAt, boolean deleted, Instant createdAt, Instant updatedAt,
                    String createdBy) {
        this.id = id;
        this.name = name;
        this.executionPath = executionPath;
        this.passCriteria = passCriteria;
        this.description = description;
        this.status = status;
        this.autonomyLevel = autonomyLevel;
        this.signedOff = signedOff;
        this.signedOffBy = signedOffBy;
        this.signedOffAt = signedOffAt;
        this.deleted = deleted;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
        this.createdBy = createdBy;
    }

    /** 建立新專案：狀態 DRAFT；手動建立（非草案）預設已 signoff，草案則 signedOff=false。 */
    public static Project create(NewProject spec, String createdBy, Instant now) {
        Violations v = new Violations();
        String name = FieldRules.requiredText(v, "name", "名稱", spec.name(), 200);
        String path = FieldRules.executionPath(v, "executionPath", spec.executionPath());
        String passCriteria = FieldRules.requiredMarkdown(v, "passCriteria", "通過標準", spec.passCriteria());
        Integer autonomy = FieldRules.autonomyLevel(v, "autonomyLevel", spec.autonomyLevel(),
                DEFAULT_AUTONOMY_LEVEL);
        v.throwIfAny();
        return new Project(UUID.randomUUID(), name, path, passCriteria,
                FieldRules.optionalMarkdown(spec.description()), ProjectStatus.DRAFT, autonomy,
                !spec.draft(), null, null, false, now, now, createdBy);
    }

    /** 由持久層資料還原（不做驗證、不產生新 id）。 */
    public static Project restore(UUID id, String name, String executionPath, String passCriteria,
                                  String description, ProjectStatus status, int autonomyLevel,
                                  boolean signedOff, String signedOffBy, Instant signedOffAt,
                                  boolean deleted, Instant createdAt, Instant updatedAt, String createdBy) {
        return new Project(id, name, executionPath, passCriteria, description, status, autonomyLevel,
                signedOff, signedOffBy, signedOffAt, deleted, createdAt, updatedAt, createdBy);
    }

    /**
     * 套用更新（null 欄位不變）。EXECUTING 時只准改 name／description，其餘欄位「值有變更」即 409。
     * 先完整驗證（含狀態轉移是否合法）再一次套用，驗證失敗不會留下半套修改。
     */
    public void update(ProjectUpdate update, Instant now) {
        if (status == ProjectStatus.EXECUTING) {
            rejectRestrictedChangesWhileExecuting(update);
        }
        Violations v = new Violations();
        String newName = name;
        if (update.name() != null) {
            newName = FieldRules.requiredText(v, "name", "名稱", update.name(), 200);
        }
        String newPath = executionPath;
        if (update.executionPath() != null) {
            newPath = FieldRules.executionPath(v, "executionPath", update.executionPath());
        }
        String newCriteria = passCriteria;
        if (update.passCriteria() != null) {
            newCriteria = FieldRules.requiredMarkdown(v, "passCriteria", "通過標準", update.passCriteria());
        }
        Integer newAutonomy = autonomyLevel;
        if (update.autonomyLevel() != null) {
            newAutonomy = FieldRules.autonomyLevel(v, "autonomyLevel", update.autonomyLevel(), autonomyLevel);
        }
        v.throwIfAny();
        ProjectStatus target = update.status() != null && update.status() != status ? update.status() : null;
        if (target != null) {
            StateMachines.requireTransition(status, target);
        }
        String newDescription = update.description() == null ? description
                : FieldRules.optionalMarkdown(update.description());

        boolean changed = !Objects.equals(newName, name)
                || !Objects.equals(newPath, executionPath)
                || !Objects.equals(newCriteria, passCriteria)
                || !Objects.equals(newDescription, description)
                || newAutonomy != autonomyLevel;
        name = newName;
        executionPath = newPath;
        passCriteria = newCriteria;
        description = newDescription;
        autonomyLevel = newAutonomy;
        if (changed) {
            updatedAt = now;
        }
        if (target != null) {
            transitionTo(target, now);
        }
    }

    private void rejectRestrictedChangesWhileExecuting(ProjectUpdate update) {
        List<String> blocked = new ArrayList<>();
        if (update.executionPath() != null && !update.executionPath().strip().equals(executionPath)) {
            blocked.add("executionPath");
        }
        if (update.passCriteria() != null && !update.passCriteria().equals(passCriteria)) {
            blocked.add("passCriteria");
        }
        if (update.autonomyLevel() != null && update.autonomyLevel() != autonomyLevel) {
            blocked.add("autonomyLevel");
        }
        if (update.status() != null && update.status() != status) {
            blocked.add("status");
        }
        if (!blocked.isEmpty()) {
            throw new ConflictException("專案執行中，僅可修改名稱與說明",
                    "EXECUTING 狀態只准修改 name／description", Map.of("fields", blocked));
        }
    }

    /** 狀態轉移（附錄 B.1）；非法轉移丟 409。 */
    public void transitionTo(ProjectStatus target, Instant now) {
        StateMachines.requireTransition(status, target);
        status = target;
        updatedAt = now;
    }

    /** 人工 signoff：approver 不可為空白（不可匿名）、不可重複 signoff。 */
    public void signoff(String approver, Instant now) {
        if (approver == null || approver.isBlank()) {
            throw ValidationException.of("approver", "approver 不可為空（人工 signoff 不可匿名）");
        }
        if (signedOff) {
            throw new ConflictException("專案已完成 signoff，不可重複簽核", "已 signoff",
                    Map.of("signedOffBy", String.valueOf(signedOffBy), "signedOffAt", String.valueOf(signedOffAt)));
        }
        signedOff = true;
        signedOffBy = approver.strip();
        signedOffAt = now;
        updatedAt = now;
    }

    /** 軟刪除：status=ARCHIVED 且 deleted=true；EXECUTING 不可刪除（409）。 */
    public void softDelete(Instant now) {
        if (status == ProjectStatus.EXECUTING) {
            throw new ConflictException("專案執行中，不可刪除", "EXECUTING 狀態的專案不可刪除",
                    Map.of("status", status.name()));
        }
        transitionTo(ProjectStatus.ARCHIVED, now);
        deleted = true;
    }

    public UUID id() {
        return id;
    }

    public String name() {
        return name;
    }

    public String executionPath() {
        return executionPath;
    }

    public String passCriteria() {
        return passCriteria;
    }

    public String description() {
        return description;
    }

    public ProjectStatus status() {
        return status;
    }

    public int autonomyLevel() {
        return autonomyLevel;
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

    public String createdBy() {
        return createdBy;
    }
}
