package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ManageProjectUseCase;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.ProjectDetailView;
import com.aisdlc.console.application.port.in.SddGovernanceUseCase;
import com.aisdlc.console.application.port.out.AgentBridge;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AgentBridge.SddFreeze;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.RuntimeSettings;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.model.engine.SddFsmState;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.service.SddBindingRules;
import com.aisdlc.console.domain.service.SddFreezeRules;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.util.Objects;
import java.util.UUID;

/**
 * SDD 治理用例（契約 §1.10.2 核准凍結、§1.10.7 編輯 FSM 專案）。
 *
 * <p>核准凍結是 Console 對 FSM 唯一的寫入動詞（ADR-016）。<b>交易邊界</b>：它會呼叫 Bridge（秒級），所以刻意不是 {@code @Transactional}——
 * 唯一的資料庫寫入（綁定的寫回）是獨立的短交易，而且<b>先於</b> Bridge 的寫入呼叫（衝突要在任何 FSM 寫入之前發現，免得 FSM 已被寫入才發現兩個
 * Console 專案認領同一個 FSM 專案）；第 6 項之後失敗不回滾它（鍵確實有狀態檔，綁定本身是對的）。
 */
@Service
public class SddGovernanceService implements SddGovernanceUseCase {

    private final ProjectRepository projects;
    private final AgentBridge bridge;
    private final RuntimeSettings settings;
    private final AuditTrail audit;
    private final Clock clock;
    private final TransactionTemplate tx;
    private final ManageProjectUseCase manageProjects;

    public SddGovernanceService(ProjectRepository projects, AgentBridge bridge, RuntimeSettings settings,
                                AuditTrail audit, Clock clock, TransactionTemplate tx,
                                ManageProjectUseCase manageProjects) {
        this.projects = projects;
        this.bridge = bridge;
        this.settings = settings;
        this.audit = audit;
        this.clock = clock;
        this.tx = tx;
        this.manageProjects = manageProjects;
    }

    @Override
    public SddFsmState freeze(UUID projectId, FreezeRequest request, String approver) {
        // 1 專案存在（404 先於 400）
        Project project = projects.findById(projectId).orElseThrow(() -> NotFoundException.of("專案", projectId));
        // 2 請求驗證（400）：格式、長度、與專案已綁定規格檔的一致性
        Violations violations = new Violations();
        SddFreezeRules.Checked checked = SddFreezeRules.check(violations, request.reason(), request.stage(),
                request.docs(), request.expectedDigests(), project.executionPath(), project.sddSpecFile());
        violations.throwIfAny();
        audit.note("project.sdd.freeze", "project", projectId.toString());
        // 3 寫入權杖（503）：沒有設定＝SDD 寫入面整個停用，不發出任何 Bridge 呼叫
        if (!settings.sddWriteTokenConfigured()) {
            throw new ServiceUnavailableException("SDD 寫入面停用：backend 沒有設定寫入權杖（BRIDGE_SDD_WRITE_TOKEN），無法核准凍結",
                    ErrorReasons.SDD_WRITE_DISABLED);
        }
        // 4 唯讀取標準鍵：Backend 不淨化，把有效值（可以是原名）原樣交給 Bridge，由它回淨化後的 fsm_project
        String effective = project.effectiveSddProject();
        SddFsmState current;
        try {
            current = bridge.sddFsm(effective, project.executionPath());
        } catch (BridgeRejectedException e) {
            throw BridgeErrors.forSddWrite(e, effective);
        }
        String key = current.fsmProject() != null && !current.fsmProject().isBlank() ? current.fsmProject() : effective;
        // 5 綁定唯一性與寫回（獨立短交易，先於 Bridge 寫入）
        bindOnFirstUse(projectId, key);
        // 6 Bridge :freeze（approver 一律取 JWT subject；失敗不回滾第 5 項）
        try {
            return bridge.sddFreeze(key, new SddFreeze(project.executionPath(), checked.stage(), checked.docs(),
                    approver, checked.reason(), checked.expectedDigests()));
        } catch (BridgeRejectedException e) {
            throw BridgeErrors.forSddWrite(e, key);
        }
    }

    /** 以標準鍵查綁定唯一性；通過後專案的 {@code sddProject} 為 NULL 時寫入它（使用者輸入的值不覆寫）。 */
    private void bindOnFirstUse(UUID projectId, String key) {
        tx.executeWithoutResult(status -> {
            Project locked = projects.findByIdForUpdate(projectId)
                    .orElseThrow(() -> NotFoundException.of("專案", projectId));
            SddBindings.requireFree(projects, locked.executionPath(), key, locked.id());
            if (locked.sddProject() == null && locked.rebindSddProject(key, clock.instant())) {
                projects.save(locked);
            }
        });
    }

    @Override
    @Transactional
    public ProjectDetailView bind(UUID projectId, String sddProject) {
        Project project = projects.findByIdForUpdate(projectId)
                .orElseThrow(() -> NotFoundException.of("專案", projectId));
        Violations violations = new Violations();
        String next = SddBindingRules.storedProject(violations, "sddProject", sddProject);
        violations.throwIfAny();
        if (!Objects.equals(next, project.sddProject())) {
            SddBindings.requireFree(projects, project.executionPath(), next, project.id());
            project.rebindSddProject(next, clock.instant());
            projects.save(project);
            audit.note("project.sdd.bind", "project", projectId.toString());
        }
        return manageProjects.get(projectId);
    }
}
