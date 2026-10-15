package com.aisdlc.console.domain.model.goal;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.service.FieldRules;
import com.aisdlc.console.domain.service.StateMachines;

import java.time.Instant;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;

/**
 * 目標聚合（PRD §5.1.2；純 Java）。
 *
 * <p>{@code dependsOn} 是聚合內的前置依賴 id 集合（資料層為 goal_dependencies 關聯表）。本類別只守
 * 「不可依賴自己」；成環（需整張專案圖）與跨專案由 application 層用 DagService 與專案內目標清單把關。
 */
public final class Goal {

    private final UUID id;
    private final UUID projectId;
    private String name;
    private String description;
    private String passCriteria;
    private int sortOrder;
    private GoalStatus status;
    private Set<UUID> dependsOn;
    private boolean signedOff;
    private String signedOffBy;
    private Instant signedOffAt;
    private boolean deleted;
    private final Instant createdAt;
    private Instant updatedAt;

    private Goal(UUID id, UUID projectId, String name, String description, String passCriteria, int sortOrder,
                 GoalStatus status, Set<UUID> dependsOn, boolean signedOff, String signedOffBy,
                 Instant signedOffAt, boolean deleted, Instant createdAt, Instant updatedAt) {
        this.id = id;
        this.projectId = projectId;
        this.name = name;
        this.description = description;
        this.passCriteria = passCriteria;
        this.sortOrder = sortOrder;
        this.status = status;
        this.dependsOn = dependsOn;
        this.signedOff = signedOff;
        this.signedOffBy = signedOffBy;
        this.signedOffAt = signedOffAt;
        this.deleted = deleted;
        this.createdAt = createdAt;
        this.updatedAt = updatedAt;
    }

    /** 建立新目標（狀態 PENDING；sortOrder 由 application 層算出「排末」後傳入）。 */
    public static Goal create(UUID projectId, NewGoal spec, int sortOrder, Instant now) {
        Violations v = new Violations();
        String name = FieldRules.requiredText(v, "name", "名稱", spec.name(), 200);
        String passCriteria = FieldRules.requiredMarkdown(v, "passCriteria", "通過標準", spec.passCriteria());
        v.throwIfAny();
        UUID id = UUID.randomUUID();
        Set<UUID> deps = normalizeDependencies(id, spec.dependsOn());
        return new Goal(id, projectId, name, FieldRules.optionalMarkdown(spec.description()), passCriteria,
                sortOrder, GoalStatus.PENDING, deps, !spec.draft(), null, null, false, now, now);
    }

    /** 由持久層資料還原。 */
    public static Goal restore(UUID id, UUID projectId, String name, String description, String passCriteria,
                               int sortOrder, GoalStatus status, Collection<UUID> dependsOn, boolean signedOff,
                               String signedOffBy, Instant signedOffAt, boolean deleted, Instant createdAt,
                               Instant updatedAt) {
        return new Goal(id, projectId, name, description, passCriteria, sortOrder, status,
                new LinkedHashSet<>(dependsOn), signedOff, signedOffBy, signedOffAt, deleted, createdAt,
                updatedAt);
    }

    /** 套用更新（null 欄位不變）。 */
    public void update(GoalUpdate update, Instant now) {
        Violations v = new Violations();
        String newName = name;
        if (update.name() != null) {
            newName = FieldRules.requiredText(v, "name", "名稱", update.name(), 200);
        }
        String newCriteria = passCriteria;
        if (update.passCriteria() != null) {
            newCriteria = FieldRules.requiredMarkdown(v, "passCriteria", "通過標準", update.passCriteria());
        }
        if (update.sortOrder() != null && update.sortOrder() < 0) {
            v.add("sortOrder", "排序順序不可為負數");
        }
        v.throwIfAny();
        Set<UUID> newDeps = update.dependsOn() == null ? dependsOn : normalizeDependencies(id, update.dependsOn());
        String newDescription = update.description() == null ? description
                : FieldRules.optionalMarkdown(update.description());
        int newSortOrder = update.sortOrder() == null ? sortOrder : update.sortOrder();

        boolean changed = !Objects.equals(newName, name)
                || !Objects.equals(newCriteria, passCriteria)
                || !Objects.equals(newDescription, description)
                || newSortOrder != sortOrder
                || !newDeps.equals(dependsOn);
        name = newName;
        passCriteria = newCriteria;
        description = newDescription;
        sortOrder = newSortOrder;
        dependsOn = newDeps;
        if (changed) {
            updatedAt = now;
        }
    }

    /** 重排用：只改 sortOrder。 */
    public void moveTo(int newSortOrder, Instant now) {
        if (newSortOrder != sortOrder) {
            sortOrder = newSortOrder;
            updatedAt = now;
        }
    }

    /** 狀態轉移（附錄 B.2）；非法轉移丟 409。 */
    public void transitionTo(GoalStatus target, Instant now) {
        StateMachines.requireTransition(status, target);
        status = target;
        updatedAt = now;
    }

    /**
     * 系統重設（契約 §3.5.3 的 R-goal 推導與人工判定）：直接設定狀態、不經 {@link StateMachines}
     * （附錄 B.2 沒有 {@code FAILED→IN_PROGRESS}、{@code COMPLETED→任何}）；手動 API 仍完全遵守附錄 B。
     * 狀態沒變時不動 {@code updatedAt}。
     */
    public void systemSetStatus(GoalStatus target, Instant now) {
        if (status != target) {
            status = target;
            updatedAt = now;
        }
    }

    /** 人工 signoff：approver 不可為空白、不可重複。 */
    public void signoff(String approver, Instant now) {
        if (approver == null || approver.isBlank()) {
            throw ValidationException.of("approver", "approver 不可為空（人工 signoff 不可匿名）");
        }
        if (signedOff) {
            throw new ConflictException("目標已完成 signoff，不可重複簽核", "已 signoff",
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

    /** 軟刪除（deleted=true）；連帶任務由 application 層處理。 */
    public void softDelete(Instant now) {
        deleted = true;
        updatedAt = now;
    }

    private static Set<UUID> normalizeDependencies(UUID selfId, Collection<UUID> requested) {
        Set<UUID> deps = new LinkedHashSet<>();
        if (requested != null) {
            for (UUID dependency : requested) {
                if (dependency == null) {
                    throw ValidationException.of("dependsOn", "dependsOn 不可包含空值");
                }
                if (dependency.equals(selfId)) {
                    throw ValidationException.of("dependsOn", "目標不可依賴自己", "自依賴",
                            Map.of("goalId", selfId.toString()));
                }
                deps.add(dependency);
            }
        }
        return deps;
    }

    public UUID id() {
        return id;
    }

    public UUID projectId() {
        return projectId;
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

    public int sortOrder() {
        return sortOrder;
    }

    public GoalStatus status() {
        return status;
    }

    /** 前置依賴 id（唯讀快照，保留加入順序）。 */
    public Set<UUID> dependsOn() {
        return Collections.unmodifiableSet(dependsOn);
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
}
