package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchDecompositionReadPort;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.application.port.out.ResearchScrReadPort;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Decomposition;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.service.ResearchFlowPolicy;
import org.springframework.stereotype.Component;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/**
 * 內環 run 啟動的研究專案前置守衛（D-102；PRD AC-R2P-14-4、AC-R2P-14-5、AC-R2P-14-7）：<b>僅當 {@code research_projects.console_project_id = :projectId} 命中</b>才生效，
 * 非研究專案零影響（也不呼叫 Bridge；回歸 AT-961-11-E-2）。檢查序固定（先中者定案）：<ol>
 *   <li>有 {@code OPEN} 的 SCR → 409 {@code scr_open}（內環唯讀）；</li>
 *   <li>拆解 stale（狀態 STALE，或其 PRD 摘要與現行凍結摘要不符）→ 409 {@code decomposition_stale}（{@code details.expected_sha256}、{@code actual_sha256}）；</li>
 *   <li>內環鍵沒有 Stage-2 凍結（讀內環鍵 FSM 視圖的 {@code frozen_stages}，不取 DB 旗標、不維護第二份狀態）→ 409 {@code fsm_state_conflict}；
 *       讀不到視圖＝無法確認 TCS 已凍結，同樣拒絕（fail-closed）。</li>
 * </ol>
 * 既有的 {@code UNSIGNED_DRAFT} 斷言在本守衛之前、不變。execute、resume、restore 三個入口共用這一個守衛（FR-15-2：不另開第二套執行控制）。
 */
@Component
public class ResearchExecutionGuard {

    private static final Set<String> STALE_STATUSES = Set.of("STALE", "REJECTED");

    private final ResearchProjectReadPort researchProjects;
    private final ResearchScrReadPort scrs;
    private final ResearchDecompositionReadPort decompositions;
    private final ProjectRepository consoleProjects;
    private final ResearchBridge bridge;

    ResearchExecutionGuard(ResearchProjectReadPort researchProjects, ResearchScrReadPort scrs, ResearchDecompositionReadPort decompositions,
                           ProjectRepository consoleProjects, ResearchBridge bridge) {
        this.researchProjects = researchProjects;
        this.scrs = scrs;
        this.decompositions = decompositions;
        this.consoleProjects = consoleProjects;
        this.bridge = bridge;
    }

    /** 啟動前檢查；通過＝靜默返回，不通過丟 409。 */
    public void check(UUID consoleProjectId) {
        Optional<UUID> bound = researchProjects.researchIdOfConsoleProject(consoleProjectId);
        if (bound.isEmpty()) {
            return;
        }
        UUID researchId = bound.get();
        if (scrs.hasOpen(researchId)) {
            throw new ConflictException("規格變更請求進行中，內環唯讀，不能啟動執行", ErrorReasons.RESEARCH_SCR_OPEN, Map.of("research_id", researchId.toString()));
        }
        Optional<Decomposition> decomposition = decompositions.effective(researchId);
        if (decomposition.isPresent()) {
            Optional<String> frozen = decompositions.frozenPrdSha256(researchId);
            Decomposition d = decomposition.get();
            boolean mismatch = frozen.isPresent() && d.prdSha256() != null && !frozen.get().equals(d.prdSha256());
            if (STALE_STATUSES.contains(d.status()) || mismatch) {
                Map<String, Object> details = new LinkedHashMap<>();
                details.put("research_id", researchId.toString());
                frozen.ifPresent(sha -> details.put("expected_sha256", sha));
                if (d.prdSha256() != null) {
                    details.put("actual_sha256", d.prdSha256());
                }
                throw new ConflictException("拆解綁定的 PRD 摘要已過期，請重新拆解並再簽核", ErrorReasons.RESEARCH_DECOMPOSITION_STALE, details);
            }
        }
        requireStage2Frozen(consoleProjectId, researchId);
    }

    private void requireStage2Frozen(UUID consoleProjectId, UUID researchId) {
        Project project = consoleProjects.findById(consoleProjectId).orElse(null);
        if (project == null) {
            return;
        }
        String current = null;
        boolean frozen = false;
        String cause = null;
        try {
            var state = bridge.fsm(project.effectiveSddProject(), project.executionPath()).state();
            current = state.currentState();
            frozen = ResearchFlowPolicy.stage2Frozen(state.frozenStages());
        } catch (RuntimeException e) {
            cause = e instanceof DomainException domain ? domain.reason() : e.getClass().getSimpleName();
        }
        if (!frozen) {
            Map<String, Object> details = new LinkedHashMap<>();
            details.put("research_id", researchId.toString());
            if (current != null) {
                details.put("current_state", current);
            }
            details.put("expected", "內環鍵已凍結 " + ResearchFlowPolicy.STAGE2);
            if (cause != null) {
                details.put("cause", "fsm_unreadable:" + cause);
            }
            throw new ConflictException("測試契約（TCS）尚未凍結，內環不能啟動執行", ErrorReasons.RESEARCH_FSM_STATE_CONFLICT, details);
        }
    }
}
