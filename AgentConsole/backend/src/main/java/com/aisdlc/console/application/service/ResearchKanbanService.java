package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase;
import com.aisdlc.console.application.port.in.ResearchDecompositionUseCase;
import com.aisdlc.console.application.port.in.ResearchKanbanUseCase;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchHealingReadPort;
import com.aisdlc.console.application.port.out.ResearchKanbanReadPort;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.application.port.out.ResearchScrReadPort;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.model.execution.ExecutionRtm;
import com.aisdlc.console.domain.model.execution.ReviewDecision;
import com.aisdlc.console.domain.model.execution.ReviewKind;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.research.ResearchP2Views.HealingFacts;
import com.aisdlc.console.domain.model.research.ResearchP2Views.TaskCounts;
import com.aisdlc.console.domain.model.research.ResearchViews;
import com.aisdlc.console.domain.service.ResearchFlowPolicy;
import com.aisdlc.console.domain.service.ReviewGatePolicy;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/**
 * 看板投影（API-RP-26）。唯讀：只有 JDBC 讀與 Bridge 的 FSM 讀取（{@code bridge.fsm}），沒有任何 Bridge 寫入請求；完成判定與來源端點共用同一份計算。
 * 檢查：專案不存在 404；未綁 Console 專案時各欄取空值（沒有 run、沒有任務）。
 */
@Service
public class ResearchKanbanService implements ResearchKanbanUseCase {

    private static final Set<String> RELEASE_STATES = Set.of("RELEASE_READY", "RELEASE");
    private static final int GATES_PER_KIND = 5;

    private final ResearchProjectReadPort researchProjects;
    private final ResearchScrReadPort scrs;
    private final ResearchDecompositionUseCase decompositions;
    private final ResearchHealingReadPort healing;
    private final ResearchKanbanReadPort kanban;
    private final ProjectRepository consoleProjects;
    private final ResearchBridge bridge;
    private final ExecutionQueryUseCase executions;
    private final SettingsReader settings;
    private final Clock clock;

    @SuppressWarnings("java:S107")
    ResearchKanbanService(ResearchProjectReadPort researchProjects, ResearchScrReadPort scrs, ResearchDecompositionUseCase decompositions,
                          ResearchHealingReadPort healing, ResearchKanbanReadPort kanban, ProjectRepository consoleProjects, ResearchBridge bridge,
                          ExecutionQueryUseCase executions, SettingsReader settings, Clock clock) {
        this.researchProjects = researchProjects;
        this.scrs = scrs;
        this.decompositions = decompositions;
        this.healing = healing;
        this.kanban = kanban;
        this.consoleProjects = consoleProjects;
        this.bridge = bridge;
        this.executions = executions;
        this.settings = settings;
        this.clock = clock;
    }

    @Override
    public Kanban kanban(UUID researchId) {
        ResearchViews.Project research = researchProjects.findById(researchId)
                .orElseThrow(() -> new NotFoundException("研究專案不存在：" + researchId, ErrorReasons.RESEARCH_NOT_FOUND, Map.of()));
        UUID consoleId = research.consoleProjectId();
        Optional<Project> console = consoleId == null ? Optional.empty() : consoleProjects.findById(consoleId);
        Optional<UUID> latestRun = consoleId == null ? Optional.empty() : kanban.latestRunId(consoleId);

        // Bridge 讀取：內環鍵的 FSM 視圖；任何失敗＝不可達／不可讀，FSM 衍生欄一律 unknown
        String fsmState = null;
        boolean stage2Frozen = false;
        boolean reachable = console.isEmpty();
        if (console.isPresent()) {
            try {
                var state = bridge.fsm(console.get().effectiveSddProject(), console.get().executionPath()).state();
                fsmState = state.currentState();
                stage2Frozen = ResearchFlowPolicy.stage2Frozen(state.frozenStages());
                reachable = true;
            } catch (RuntimeException e) {
                reachable = false;
            }
        }
        boolean unknown = console.isPresent() && !reachable;

        var decomposition = decompositions.current(researchId);
        Decompose decompose = decomposition.map(v -> new Decompose("SIGNED_OFF".equals(v.decomposition().status()) && !v.stale(),
                v.decomposition().status(), v.decomposition().tasksCount(), v.stale())).orElse(new Decompose(false, "NONE", 0, false));

        TaskCounts counts = consoleId == null ? new TaskCounts(0, 0, 0, 0, 0, 0, 0) : kanban.taskCounts(consoleId);
        HealingFacts facts = consoleId == null ? new HealingFacts(0, 0) : healing.facts(consoleId);
        int maxRetries = settings.intValue("agent", "maxRetries");

        Tcs tcs = unknown ? new Tcs(false, null, null, null, Boolean.TRUE)
                : new Tcs(consoleId != null && stage2Frozen, consoleId == null ? null : stage2Frozen, null, fsmState, null);
        Implement implement = new Implement(counts.done(), fsmState, unknown ? Boolean.TRUE : null,
                new Tasks(counts.total(), counts.running(), counts.completed(), counts.skipped(), counts.failed(), counts.escalated(), counts.retrying()));
        Healing healingColumn = new Healing(facts.retryingSteps() == 0 && facts.escalatedTasks() == 0, facts.retryingSteps(), facts.escalatedTasks(), maxRetries);
        Regression regression = regression(latestRun, fsmState, unknown);

        List<PendingReview> pending = consoleId == null ? List.of() : kanban.pendingReviews(consoleId).stream()
                .map(r -> new PendingReview(r.reviewId(), r.runId(), r.kind(), r.taskId(), r.reason(), r.createdAt(), allowed(r.kind(), r.taskId() != null))).toList();
        List<Gate> gates = kanban.gateDecisions(researchId, GATES_PER_KIND).stream()
                .map(g -> new Gate(g.gate(), g.decision(), g.decidedBy(), g.decidedAt(), g.fsmStateAfter(), g.reason())).toList();

        OffsetDateTime snapshotAt = null;
        if (!reachable) {
            snapshotAt = latest(research.updatedAt(), consoleId == null ? null : kanban.latestEventAt(consoleId).orElse(null),
                    kanban.latestDecisionAt(researchId).orElse(null));
        }
        return new Kanban(researchId, consoleId, latestRun.orElse(null), OffsetDateTime.now(clock), reachable, snapshotAt, !reachable, scrs.hasOpen(researchId),
                new Columns(decompose, tcs, implement, healingColumn, regression), pending, gates);
    }

    private Regression regression(Optional<UUID> latestRun, String fsmState, boolean unknown) {
        Rtm rtm = null;
        if (latestRun.isPresent()) {
            try {
                ExecutionRtm source = executions.rtm(latestRun.get());
                rtm = new Rtm(latestRun.get(), source.at().passed(), source.at().total(), source.ac().covered(), source.ac().total(), source.ac().pct(),
                        source.fullyCovered(), true);
            } catch (RuntimeException e) {
                rtm = null;      // 404（rtm_not_found／run_not_found）或 Bridge 失敗：無追溯報告，rtmAvailable＝false
            }
        }
        boolean release = fsmState != null && RELEASE_STATES.contains(fsmState);
        boolean done = rtm != null && rtm.acPct() == 100.0 && rtm.fullyCovered() && release;
        return new Regression(done, fsmState, unknown ? null : (Boolean) release, unknown ? Boolean.TRUE : null, rtm != null, rtm);
    }

    private static List<String> allowed(String kind, boolean hasTask) {
        List<String> out = new ArrayList<>();
        for (ReviewDecision decision : ReviewGatePolicy.allowedDecisions(ReviewKind.valueOf(kind), hasTask)) {
            out.add(decision.name());
        }
        return out;
    }

    private static OffsetDateTime latest(OffsetDateTime... times) {
        OffsetDateTime best = null;
        for (OffsetDateTime time : times) {
            if (time != null && (best == null || time.isAfter(best))) {
                best = time;
            }
        }
        return best;
    }
}
