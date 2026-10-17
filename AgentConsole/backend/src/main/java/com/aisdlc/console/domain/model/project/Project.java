package com.aisdlc.console.domain.model.project;

import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.service.FieldRules;
import com.aisdlc.console.domain.service.SddBindingRules;
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
 * 名稱與說明；signoff 不可匿名且不可重複；軟刪除＝{@code deleted=true} 且 {@code status=ARCHIVED}，並記下
 * {@code deletedAt} 與刪除前的狀態（{@code statusBeforeDelete}，V9／C-3），讓保留期內可以 {@link #recover 復原}。
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
    private Instant deletedAt;
    private ProjectStatus statusBeforeDelete;
    private String sddProject;
    private String sddSpecDir;
    private String sddSpecFile;

    @SuppressWarnings("java:S107")
    private Project(UUID id, String name, String executionPath, String passCriteria, String description,
                    ProjectStatus status, int autonomyLevel, boolean signedOff, String signedOffBy,
                    Instant signedOffAt, boolean deleted, Instant createdAt, Instant updatedAt,
                    String createdBy, Instant deletedAt, ProjectStatus statusBeforeDelete, String sddProject,
                    String sddSpecDir, String sddSpecFile) {
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
        this.deletedAt = deletedAt;
        this.statusBeforeDelete = statusBeforeDelete;
        this.sddProject = sddProject;
        this.sddSpecDir = sddSpecDir;
        this.sddSpecFile = sddSpecFile;
    }

    /**
     * 建立新專案：狀態 DRAFT；手動建立（非草案）預設已 signoff，草案則 signedOff=false。{@link NewProject} 的 SDD 綁定三欄只有路徑 A
     * 的 confirm 會帶（契約 §0.5 V12 寫入規則②：{@code POST／PUT /projects} 的請求不收這三欄）。
     */
    public static Project create(NewProject spec, String createdBy, Instant now) {
        Violations v = new Violations();
        String name = FieldRules.requiredText(v, "name", "名稱", spec.name(), 200);
        String path = FieldRules.executionPath(v, "executionPath", spec.executionPath());
        String passCriteria = FieldRules.requiredMarkdown(v, "passCriteria", "通過標準", spec.passCriteria());
        Integer autonomy = FieldRules.autonomyLevel(v, "autonomyLevel", spec.autonomyLevel(),
                DEFAULT_AUTONOMY_LEVEL);
        String sddProject = SddBindingRules.storedProject(v, "sddProject", spec.sddProject());
        String sddSpecDir = SddBindingRules.storedPath(v, "sddSpecDir", spec.sddSpecDir());
        String sddSpecFile = SddBindingRules.storedPath(v, "sddSpecFile", spec.sddSpecFile());
        v.throwIfAny();
        return new Project(UUID.randomUUID(), name, path, passCriteria,
                FieldRules.optionalMarkdown(spec.description()), ProjectStatus.DRAFT, autonomy,
                !spec.draft(), null, null, false, now, now, createdBy, null, null, sddProject, sddSpecDir,
                sddSpecFile);
    }

    /** 由持久層資料還原（不做驗證、不產生新 id）。 */
    @SuppressWarnings("java:S107")
    public static Project restore(UUID id, String name, String executionPath, String passCriteria,
                                  String description, ProjectStatus status, int autonomyLevel,
                                  boolean signedOff, String signedOffBy, Instant signedOffAt,
                                  boolean deleted, Instant createdAt, Instant updatedAt, String createdBy,
                                  Instant deletedAt, ProjectStatus statusBeforeDelete, String sddProject,
                                  String sddSpecDir, String sddSpecFile) {
        return new Project(id, name, executionPath, passCriteria, description, status, autonomyLevel,
                signedOff, signedOffBy, signedOffAt, deleted, createdAt, updatedAt, createdBy, deletedAt,
                statusBeforeDelete, sddProject, sddSpecDir, sddSpecFile);
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

    /**
     * 系統重設（契約 §3.5.3）：執行事件造成的專案狀態變化，直接設定、不經 {@link StateMachines}
     * （附錄 B.1 沒有 {@code COMPLETED→EXECUTING}；手動 API 仍完全遵守附錄 B）。狀態沒變時不動 {@code updatedAt}。
     */
    public void systemSetStatus(ProjectStatus target, Instant now) {
        if (status != target) {
            status = target;
            updatedAt = now;
        }
    }

    /**
     * execute 成功後進入 EXECUTING：{@code DRAFT／FAILED} 先內部轉 {@code READY} 再轉 {@code EXECUTING}（兩步都合法）；
     * {@code READY} 直接轉；{@code COMPLETED} 屬系統重設（補了新任務後可再跑，契約 D-31）。
     */
    public void startExecuting(Instant now) {
        if (status == ProjectStatus.EXECUTING) {
            return;
        }
        if (status == ProjectStatus.DRAFT || status == ProjectStatus.FAILED) {
            transitionTo(ProjectStatus.READY, now);
        }
        if (StateMachines.canTransition(status, ProjectStatus.EXECUTING)) {
            transitionTo(ProjectStatus.EXECUTING, now);
        } else {
            systemSetStatus(ProjectStatus.EXECUTING, now);
        }
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

    /**
     * 匯入確認落庫專用（契約 §1.1.6）：專案／目標／任務一律 {@code signedOff=true}，
     * {@code signedOffBy／At} 承襲匯入記錄上那一次人工 signoff（人工審批已發生在匯入記錄上，不是落庫時才簽）。
     */
    public void inheritSignoff(String approver, Instant at) {
        signedOff = true;
        signedOffBy = approver;
        signedOffAt = at;
    }

    /**
     * 軟刪除：status=ARCHIVED 且 deleted=true；EXECUTING 不可刪除（409）。同時記下 {@code deletedAt}（保留期與復原的起點）
     * 與刪除前的狀態（復原時還原；契約 §0.5 V9）。呼叫端須把<b>同一個</b> {@code now} 傳給連帶軟刪的目標與任務——
     * 復原靠「目標／任務的 deleted_at 等於專案的」辨識同一次刪除連帶軟刪的列。
     */
    public void softDelete(Instant now) {
        if (status == ProjectStatus.EXECUTING) {
            throw new ConflictException("專案執行中，不可刪除", "EXECUTING 狀態的專案不可刪除",
                    Map.of("status", status.name()));
        }
        ProjectStatus before = status;
        transitionTo(ProjectStatus.ARCHIVED, now);
        deleted = true;
        deletedAt = now;
        statusBeforeDelete = before;
    }

    /**
     * 復原軟刪除（契約 §1.6.1，C-3）：{@code deleted=false}、{@code deletedAt}／{@code statusBeforeDelete} 清空、狀態還原為刪除前的值；
     * 升級前就已軟刪（沒有 {@code statusBeforeDelete}）者：未 signoff → DRAFT、已 signoff → READY。這是系統層的還原，直接設定狀態、
     * 不經 {@link StateMachines}（附錄 B.1 的 ARCHIVED 是終點，沒有任何出邊；手動 API 仍完全遵守附錄 B）。
     * 前置條件（確實被軟刪、仍在保留期內）由用例檢查。
     */
    public void recover(Instant now) {
        status = statusBeforeDelete != null ? statusBeforeDelete : signedOff ? ProjectStatus.READY : ProjectStatus.DRAFT;
        deleted = false;
        deletedAt = null;
        statusBeforeDelete = null;
        updatedAt = now;
    }

    // ── SDD 綁定（契約 §1.10.5、§0.5 V12；Console 專案是錨）──────────────────────────────

    /**
     * 有效 FSM 專案（契約 §1.10.5）：{@code sddProject} 有值取它，否則取<b>專案名</b>。<b>Backend 不自行淨化</b>（淨化鏡像只有 Bridge 有）：
     * 一律把「有效值（可以是原名）」交給 Bridge，由 Bridge 回應帶淨化後的標準鍵。
     */
    public String effectiveSddProject() {
        return sddProject == null || sddProject.isBlank() ? name : sddProject;
    }

    /**
     * 改寫 FSM 專案鍵（{@code null}＝清除，回到「用預設」）：第一次使用時寫回標準鍵，或使用者在 {@code PUT /projects/{id}/sdd-binding}
     * 輸入的值。值先經 {@link SddBindingRules#storedProject} 驗長度。
     *
     * @return 值有變才 true（只有真的改了才動 {@code updatedAt}；相同值＝冪等）
     */
    public boolean rebindSddProject(String value, Instant now) {
        Violations v = new Violations();
        String next = SddBindingRules.storedProject(v, "sddProject", value);
        v.throwIfAny();
        if (Objects.equals(next, sddProject)) {
            return false;
        }
        sddProject = next;
        updatedAt = now;
        return true;
    }

    /**
     * 路徑 A 的 confirm 回填規格綁定（冪等更新；契約 §1.10.8）：{@code sddSpecDir}＝編譯回應 {@code spec_path} 的父目錄、
     * {@code sddSpecFile}＝{@code spec_path}（皆絕對路徑）。null 的參數不動該欄位。
     *
     * @return 任一欄位有變才 true
     */
    public boolean bindSddSpec(String specDir, String specFile, Instant now) {
        Violations v = new Violations();
        String dir = SddBindingRules.storedPath(v, "sddSpecDir", specDir);
        String file = SddBindingRules.storedPath(v, "sddSpecFile", specFile);
        v.throwIfAny();
        boolean changed = false;
        if (dir != null && !dir.equals(sddSpecDir)) {
            sddSpecDir = dir;
            changed = true;
        }
        if (file != null && !file.equals(sddSpecFile)) {
            sddSpecFile = file;
            changed = true;
        }
        if (changed) {
            updatedAt = now;
        }
        return changed;
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

    /** 軟刪除當下的時間；未被軟刪除為 null。 */
    public Instant deletedAt() {
        return deletedAt;
    }

    /** 軟刪除前的狀態；未被軟刪除、或升級前就已軟刪者為 null。 */
    public ProjectStatus statusBeforeDelete() {
        return statusBeforeDelete;
    }

    /** FSM 專案鍵（V12，≤ 100 字元）；null＝「用預設」（專案名）。 */
    public String sddProject() {
        return sddProject;
    }

    /** 規格檔所在目錄（V12；絕對路徑）；尚未用路徑 A 匯入規格為 null。 */
    public String sddSpecDir() {
        return sddSpecDir;
    }

    /** 規格檔（V12；絕對路徑）；尚未用路徑 A 匯入規格為 null。 */
    public String sddSpecFile() {
        return sddSpecFile;
    }
}
