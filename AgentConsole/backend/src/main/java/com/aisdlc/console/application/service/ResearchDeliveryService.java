package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.application.port.in.ResearchDeliveryUseCase;
import com.aisdlc.console.application.port.in.ResearchGateUseCase;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchDeliveryReadPort;
import com.aisdlc.console.application.port.out.ResearchKanbanReadPort;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.application.port.out.ResearchScrReadPort;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.model.execution.ExecutionRtm;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.research.ResearchP2Views.DeliveryRow;
import com.aisdlc.console.domain.model.research.ResearchViews;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.regex.Pattern;

/**
 * 交付（API-RP-17／28）。Tag／PR 的檢查序：寫入權杖未設 503 → 輸入閘 422 → 專案不存在 404 → 服務層前置 409（{@code unmet[]}；零 Bridge 請求）→ Bridge 恰一次。
 * console-api 對 {@code research_*} 零寫入；部署能力（容器模式）由 Bridge 判定並以 422 {@code route_unsupported_in_deployment} 回，這裡不猜。
 */
@Service
public class ResearchDeliveryService implements ResearchDeliveryUseCase {

    /** tagName 正規式：與 Bridge {@code gitops.SEMVER_PATTERN} 同一字面（兩端各持一份，由 AT-962-19-3 對拍）；長度上限另見 {@link #TAG_NAME_MAX}。 */
    public static final String TAG_NAME_PATTERN = "^v?(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\\+[0-9A-Za-z.-]+)?$";
    public static final int TAG_NAME_MAX = 64;
    public static final int TAG_MESSAGE_MAX = 200;
    static final String TRACE_REL = "03_execution/traceability_matrix.json";
    private static final Pattern TAG_NAME = Pattern.compile(TAG_NAME_PATTERN);
    private static final Set<String> RELEASE_STATES = Set.of("RELEASE_READY", "RELEASE");

    private final ResearchBridge bridge;
    private final ResearchProjectReadPort researchProjects;
    private final ResearchDeliveryReadPort deliveries;
    private final ResearchScrReadPort scrs;
    private final ResearchKanbanReadPort kanban;
    private final ProjectRepository consoleProjects;
    private final ExecutionQueryUseCase executions;
    private final ResearchGithubTokenSource githubToken;
    private final AuditTrail audit;

    @SuppressWarnings("java:S107")
    ResearchDeliveryService(ResearchBridge bridge, ResearchProjectReadPort researchProjects, ResearchDeliveryReadPort deliveries, ResearchScrReadPort scrs,
                            ResearchKanbanReadPort kanban, ProjectRepository consoleProjects, ExecutionQueryUseCase executions,
                            ResearchGithubTokenSource githubToken, AuditTrail audit) {
        this.bridge = bridge;
        this.researchProjects = researchProjects;
        this.deliveries = deliveries;
        this.scrs = scrs;
        this.kanban = kanban;
        this.consoleProjects = consoleProjects;
        this.executions = executions;
        this.githubToken = githubToken;
        this.audit = audit;
    }

    @Override
    public Overview overview(UUID researchId) {
        ResearchViews.Project research = require(researchId);
        List<DeliveryRow> rows = deliveries.deliveries(researchId);
        Snapshot snapshot = rows.stream().filter(d -> "RELEASE_TAG".equals(d.kind()) && "CREATED".equals(d.status()) && d.snapshotSha256() != null)
                .reduce((first, second) -> second).map(d -> new Snapshot(TRACE_REL, d.snapshotSha256().strip())).orElse(null);
        boolean container = false;
        try {
            container = "mock-only".equals(String.valueOf(bridge.capabilities().get("mode")));
        } catch (RuntimeException e) {
            container = false;
        }
        UUID consoleId = research.consoleProjectId();
        String state = consoleId == null ? null : fsmState(consoleId).orElse(null);
        Optional<ExecutionRtm> rtm = consoleId == null ? Optional.empty() : kanban.latestRunId(consoleId).flatMap(this::rtm);
        Preconditions pre = new Preconditions(state != null && RELEASE_STATES.contains(state), rtm.isPresent() && fullRtm(rtm.get()),
                scrs.hasOpen(researchId), null, null);
        return new Overview(rows.stream().map(d -> new Delivery(d.kind(), d.ref(), d.commitSha(), d.url(), d.rtmReportRef(), d.fsmStateAfter(), d.status(),
                d.createdBy(), d.createdAt(), d.snapshotSha256() == null ? null : d.snapshotSha256().strip())).toList(), snapshot,
                deliveries.projectRoot(researchId).orElse(null), container, pre);
    }

    @Override
    public Traceability traceability(UUID researchId) {
        ResearchViews.Project research = require(researchId);
        Map<String, Object> body = new LinkedHashMap<>();
        if (research.consoleProjectId() != null) {
            kanban.latestRunId(research.consoleProjectId()).ifPresent(run -> body.put("run_id", run.toString()));
        }
        return trace(call(() -> bridge.traceabilityPreview(researchId, body)));
    }

    /** Bridge 的追溯表本文（鍵本來就是 camelCase；gherkinSummary 為 {given,when,then} 物件、source 為字串陣列）→ 型別。 */
    private static Traceability trace(Map<String, Object> body) {
        List<TraceRow> rows = new ArrayList<>();
        if (body.get("rows") instanceof List<?> items) {
            for (Object item : items) {
                Map<?, ?> row = item instanceof Map<?, ?> m ? m : Map.of();
                Map<?, ?> g = row.get("gherkinSummary") instanceof Map<?, ?> m ? m : Map.of();
                List<String> source = new ArrayList<>();
                if (row.get("source") instanceof List<?> s) {
                    s.forEach(x -> source.add(String.valueOf(x)));
                }
                rows.add(new TraceRow(text(row.get("ac")), text(row.get("userStory")), new Gherkin(text(g.get("given")), text(g.get("when")), text(g.get("then"))),
                        text(row.get("unitStatus")), text(row.get("e2eStatus")), text(row.get("lastRunAt")), List.copyOf(source)));
            }
        }
        Map<?, ?> t = body.get("totals") instanceof Map<?, ?> m ? m : Map.of();
        TraceTotals totals = new TraceTotals(num(t.get("acTotal")), num(t.get("covered")), num(t.get("uncovered")), num(t.get("frTotal")));
        TraceRtm rtm = null;
        if (body.get("rtm") instanceof Map<?, ?> r) {
            rtm = new TraceRtm(text(r.get("runId")), Boolean.TRUE.equals(r.get("fullyCovered")), r.get("acPct") instanceof Number n ? n.doubleValue() : null, true);
        }
        return new Traceability(List.copyOf(rows), totals, rtm, text(body.get("generatedAt")));
    }

    /** Bridge 的交付列（snake_case；偶有 camelCase 的快照鍵）→ {@link Delivery}。 */
    private static Delivery delivery(Object raw) {
        Map<?, ?> d = raw instanceof Map<?, ?> m ? m : Map.of();
        return new Delivery(text(d.get("kind")), text(d.get("ref")), text(d.get("commit_sha")), text(d.get("url")), text(d.get("rtm_report_ref")),
                text(d.get("fsm_state_after")), text(d.get("status")), text(d.get("created_by")), parseTime(d.get("created_at")), text(d.get("snapshot_sha256")));
    }

    private static java.time.OffsetDateTime parseTime(Object value) {
        try {
            return value == null ? null : java.time.OffsetDateTime.parse(value.toString());
        } catch (java.time.format.DateTimeParseException e) {
            return null;
        }
    }

    private static String text(Object value) {
        return value == null ? null : value.toString();
    }

    private static int num(Object value) {
        return value instanceof Number n ? n.intValue() : 0;
    }

    @Override
    public TagResult tag(Caller caller, UUID researchId, TagInput input) {
        requireWriteEnabled();
        validateTag(input);
        ResearchViews.Project research = require(researchId);
        List<String> unmet = new ArrayList<>();
        UUID consoleId = research.consoleProjectId();
        if (consoleId == null) {
            unmet.add("no_console_project");
        } else {
            Optional<String> state = fsmState(consoleId);
            if (state.isEmpty() || !"RELEASE_READY".equals(state.get())) {
                unmet.add("not_release_ready");
            }
            Optional<ExecutionRtm> rtm = kanban.latestRunId(consoleId).flatMap(this::rtm);
            if (rtm.isEmpty() || !fullRtm(rtm.get())) {
                unmet.add("rtm_below_100");
            }
        }
        if (scrs.hasOpen(researchId)) {
            unmet.add("scr_open");
        }
        if (!unmet.isEmpty()) {
            throw new ConflictException("交付前置條件不成立（" + String.join("、", unmet) + "）", ErrorReasons.RESEARCH_FSM_STATE_CONFLICT, Map.of("unmet", unmet));
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("tag_name", input.tagName());
        body.put("message", input.message());
        body.put("push", Boolean.TRUE.equals(input.push()));
        body.put("create_github_release", false);
        body.put("approver", caller.subject());
        body.put("requested_by", caller.subject());
        audit.note("research.delivery.tag", "research", researchId.toString());
        Map<String, Object> made = call(() -> bridge.tag(researchId, body));
        Map<?, ?> snap = made.get("snapshot") instanceof Map<?, ?> m ? m : Map.of();
        Map<?, ?> flow = made.get("flow") instanceof Map<?, ?> m ? m : Map.of();
        return new TagResult(delivery(made.get("delivery")), snap.isEmpty() ? null : new Snapshot(text(snap.get("relPath")), text(snap.get("sha256"))),
                new ResearchGateUseCase.FlowCursor(text(flow.get("step")), text(flow.get("phase")), text(flow.get("status")), text(flow.get("detail"))),
                text(made.get("fsmState")));
    }

    @Override
    public PrResult pr(Caller caller, UUID researchId, PrInput input) {
        requireWriteEnabled();
        ResearchRouteGates.Check check = new ResearchRouteGates.Check();
        if (!Boolean.TRUE.equals(input.bodyPreviewAck())) {
            check.add("bodyPreviewAck", "preview_ack_required", "須勾選已預覽 PR 內文（bodyPreviewAck 為 true）");
        }
        if (!check.violations.isEmpty()) {
            throw check.unprocessable();
        }
        require(researchId);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("branch", input.branch());
        body.put("body_preview_ack", true);
        githubToken.token().ifPresent(token -> body.put("github_token", token));
        body.put("approver", caller.subject());
        body.put("requested_by", caller.subject());
        audit.note("research.delivery.pr", "research", researchId.toString());
        Map<String, Object> made = call(() -> bridge.pr(researchId, body));
        return new PrResult(delivery(made.get("delivery")), Boolean.TRUE.equals(made.get("created")));
    }

    private void validateTag(TagInput input) {
        ResearchRouteGates.Check check = new ResearchRouteGates.Check();
        String name = input.tagName();
        if (name == null || name.length() > TAG_NAME_MAX || !TAG_NAME.matcher(name).matches()) {
            check.add("tagName", "not_semver", "tagName 須為 semver（至多 " + TAG_NAME_MAX + " 字）");
        }
        if (input.message() != null && input.message().length() > TAG_MESSAGE_MAX) {
            check.add("message", "message_too_long", "message 至多 " + TAG_MESSAGE_MAX + " 字");
        }
        if (Boolean.TRUE.equals(input.createGithubRelease())) {
            check.add("createGithubRelease", "release_not_supported", "P2 不建立 GitHub Release");
        }
        if (!check.violations.isEmpty()) {
            throw check.unprocessable();
        }
    }

    private Optional<String> fsmState(UUID consoleProjectId) {
        Optional<Project> project = consoleProjects.findById(consoleProjectId);
        if (project.isEmpty()) {
            return Optional.empty();
        }
        try {
            return Optional.ofNullable(bridge.fsm(project.get().effectiveSddProject(), project.get().executionPath()).state().currentState());
        } catch (RuntimeException e) {
            return Optional.empty();
        }
    }

    private Optional<ExecutionRtm> rtm(UUID runId) {
        try {
            return Optional.of(executions.rtm(runId));
        } catch (RuntimeException e) {
            return Optional.empty();
        }
    }

    private static boolean fullRtm(ExecutionRtm rtm) {
        return rtm.fullyCovered() && rtm.ac().pct() == 100.0;
    }

    private void requireWriteEnabled() {
        if (!bridge.writeEnabled()) {
            throw new ServiceUnavailableException("backend 沒有設定研究寫入權杖（BRIDGE_RESEARCH_WRITE_TOKEN），研究寫入面已停用",
                    ErrorReasons.RESEARCH_WRITE_DISABLED, Map.of("cause", "bridge_token_unset"));
        }
    }

    private ResearchViews.Project require(UUID id) {
        return researchProjects.findById(id).orElseThrow(() -> new NotFoundException("研究專案不存在：" + id, ErrorReasons.RESEARCH_NOT_FOUND, Map.of()));
    }

    private static <T> T call(Supplier<T> action) {
        try {
            return action.get();
        } catch (BridgeRejectedException e) {
            throw ResearchBridgeErrors.map(e);
        }
    }
}
