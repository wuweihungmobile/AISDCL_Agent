package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.application.port.in.ResearchGateUseCase;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchKanbanReadPort;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.application.port.out.ResearchScrReadPort;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.model.execution.ExecutionRtm;
import com.aisdlc.console.domain.model.research.ResearchP2Views.TaskCounts;
import com.aisdlc.console.domain.model.research.ResearchViews;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/**
 * 內環閘登錄（API-RP-23）。檢查序：寫入權杖未設 503 → 輸入閘 422 → 專案不存在 404 → 未綁 Console 專案 409（{@code unmet:[no_console_project]}）→
 * OPEN SCR 409 {@code scr_open} → 服務層前置 409（PR_REVIEW、RTM_VERIFY；零 Bridge 請求）→ Bridge {@code :gates} 恰一次。
 * {@code decisionId} 由本層產生（即 Bridge 決定列主鍵，重送冪等；D-148 BR-5）；approver 與 requestedBy 一律取 JWT subject；{@code escalated} 由 Bridge 回傳值如實帶出。
 */
@Service
public class ResearchGateService implements ResearchGateUseCase {

    static final int REASON_MAX = 500;
    static final int REPORT_REF_MAX = 300;
    private static final Set<String> GATES = Set.of("PR_REVIEW", "RTM_VERIFY", "RELEASE_READY");

    private final ResearchBridge bridge;
    private final ResearchProjectReadPort researchProjects;
    private final ResearchScrReadPort scrs;
    private final ResearchKanbanReadPort kanban;
    private final ExecutionQueryUseCase executions;
    private final AuditTrail audit;

    @SuppressWarnings("java:S107")
    ResearchGateService(ResearchBridge bridge, ResearchProjectReadPort researchProjects, ResearchScrReadPort scrs, ResearchKanbanReadPort kanban,
                        ExecutionQueryUseCase executions, AuditTrail audit) {
        this.bridge = bridge;
        this.researchProjects = researchProjects;
        this.scrs = scrs;
        this.kanban = kanban;
        this.executions = executions;
        this.audit = audit;
    }

    @Override
    public GateResult register(Caller caller, UUID researchId, GateInput input) {
        if (!bridge.writeEnabled()) {
            throw new ServiceUnavailableException("backend 沒有設定研究寫入權杖（BRIDGE_RESEARCH_WRITE_TOKEN），研究寫入面已停用",
                    ErrorReasons.RESEARCH_WRITE_DISABLED, Map.of("cause", "bridge_token_unset"));
        }
        validate(input);
        ResearchViews.Project research = researchProjects.findById(researchId)
                .orElseThrow(() -> new NotFoundException("研究專案不存在：" + researchId, ErrorReasons.RESEARCH_NOT_FOUND, Map.of()));
        if (research.consoleProjectId() == null) {
            throw conflict(List.of("no_console_project"));
        }
        if (scrs.hasOpen(researchId)) {
            throw new ConflictException("規格變更請求進行中，內環唯讀，不能登錄閘決定", ErrorReasons.RESEARCH_SCR_OPEN, Map.of("research_id", researchId.toString()));
        }
        UUID consoleId = research.consoleProjectId();
        Optional<UUID> run = kanban.latestRunId(consoleId);
        requirePreconditions(input.gate(), consoleId, run);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("decision_id", UUID.randomUUID().toString());
        body.put("gate", input.gate());
        body.put("result", input.result());
        body.put("reason", input.reason() == null ? "" : input.reason());
        body.put("review_report_ref", input.reviewReportRef());
        body.put("reviewer_independent", Boolean.TRUE.equals(input.reviewerIndependent()));
        body.put("approver", caller.subject());
        body.put("run_id", run.map(UUID::toString).orElse(null));
        body.put("requested_by", caller.subject());
        audit.note("research.gates", "research", researchId.toString());
        try {
            return result(bridge.gates(researchId, body));
        } catch (BridgeRejectedException e) {
            throw ResearchBridgeErrors.map(e);
        }
    }

    /** Bridge 本文（snake_case）→ 強型別結果；Bridge 偶以框架閘名（SCG4／5／6）回 gate，對映回 API 名。 */
    private static GateResult result(Map<String, Object> body) {
        Map<?, ?> flow = body.get("flow") instanceof Map<?, ?> m ? m : Map.of();
        String next = body.get("next_state") == null ? null : body.get("next_state").toString();
        return new GateResult(String.valueOf(body.get("gate_decision_id")), gateOf(String.valueOf(body.get("gate"))), String.valueOf(body.get("result")).equals("FAIL") ? Result.FAIL : Result.PASS,
                body.get("fsm_state_before") == null ? null : body.get("fsm_state_before").toString(), next, Boolean.TRUE.equals(body.get("escalated")),
                new FlowCursor(text(flow.get("step")), text(flow.get("phase")), text(flow.get("status")), text(flow.get("detail"))),
                body.get("replayed") instanceof Boolean replayed ? replayed : null);
    }

    private static Gate gateOf(String name) {
        return switch (name) {
            case "SCG4" -> Gate.PR_REVIEW;
            case "SCG5" -> Gate.RTM_VERIFY;
            case "SCG6" -> Gate.RELEASE_READY;
            default -> Gate.valueOf(name);
        };
    }

    private static String text(Object value) {
        return value == null ? null : value.toString();
    }

    private static void validate(GateInput input) {
        ResearchRouteGates.Check check = new ResearchRouteGates.Check();
        String gate = input.gate();
        if (gate == null || !GATES.contains(gate)) {
            check.add("gate", "invalid_gate", "gate 須為 PR_REVIEW｜RTM_VERIFY｜RELEASE_READY");
        }
        String result = input.result();
        if (!"PASS".equals(result) && !"FAIL".equals(result)) {
            check.add("result", "invalid_result", "result 須為 PASS｜FAIL");
        }
        String reason = input.reason();
        if ("FAIL".equals(result) && (reason == null || reason.isBlank())) {
            check.add("reason", "reason_required", "FAIL 必須附理由");
        }
        if (reason != null && reason.length() > REASON_MAX) {
            check.add("reason", "reason_too_long", "reason 至多 " + REASON_MAX + " 字");
        }
        if (input.reviewReportRef() != null && input.reviewReportRef().length() > REPORT_REF_MAX) {
            check.add("reviewReportRef", "report_ref_too_long", "reviewReportRef 至多 " + REPORT_REF_MAX + " 字");
        }
        if ("RELEASE_READY".equals(gate) && "PASS".equals(result)) {
            check.add("result", "release_pass_via_tag", "RELEASE_READY 的 PASS 只經建立 Release Tag（POST …/delivery/tag）達成");
        }
        if ("PR_REVIEW".equals(gate) && !Boolean.TRUE.equals(input.reviewerIndependent())) {
            check.add("reviewerIndependent", "reviewer_independence_required", "PR_REVIEW 須聲明審查者獨立（reviewerIndependent 為 true）");
        }
        if (!check.violations.isEmpty()) {
            throw check.unprocessable();
        }
    }

    private void requirePreconditions(String gate, UUID consoleId, Optional<UUID> run) {
        if ("RELEASE_READY".equals(gate)) {
            return;
        }
        List<String> unmet = new ArrayList<>();
        Optional<ExecutionRtm> rtm = run.flatMap(this::rtm);
        if ("PR_REVIEW".equals(gate)) {
            TaskCounts counts = kanban.taskCounts(consoleId);
            if (run.isEmpty() || !counts.done()) {
                unmet.add("tasks_incomplete");
            }
            if (rtm.isPresent() && !rtm.get().fullyCovered()) {
                unmet.add("rtm_below_100");
            }
        } else if (rtm.isPresent() && rtm.get().ac().pct() != 100.0) {
            unmet.add("rtm_below_100");
        }
        if (rtm.isEmpty()) {
            unmet.add("rtm_unavailable");
        }
        if (!unmet.isEmpty()) {
            throw conflict(unmet);
        }
    }

    private Optional<ExecutionRtm> rtm(UUID runId) {
        try {
            return Optional.of(executions.rtm(runId));
        } catch (RuntimeException e) {
            return Optional.empty();
        }
    }

    private static ConflictException conflict(List<String> unmet) {
        return new ConflictException("內環閘登錄的前置條件不成立（" + String.join("、", unmet) + "）", ErrorReasons.RESEARCH_FSM_STATE_CONFLICT,
                Map.of("unmet", unmet));
    }
}
