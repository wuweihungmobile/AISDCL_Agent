package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase;
import com.aisdlc.console.application.port.in.ResearchQueryUseCase;
import com.aisdlc.console.application.port.in.ResearchQueryUseCase.ProjectDetail;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.application.port.out.ResearchReviewReadPort;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.model.research.ResearchViews.PrdVersion;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;

/**
 * 研究到規格的寫入用例（API 契約 §1.1 的全部 POST／PUT／PATCH；ADR-003 D4）。console-api <b>對 {@code console.research_*} 零寫入</b>：每個動作依契約 §0.2 的
 * 失敗序——<b>研究寫入權杖未設（503）→ 輸入閘（400／422）→ 專案存在（404）→ 恰一次 Bridge 呼叫（不重試；409／502／504 由 Bridge 或連線決定）</b>——再以 JDBC 唯讀
 * 取回結果。{@code approver}、{@code decided_by}、{@code author}、{@code requested_by}、{@code created_by}、{@code actor}、{@code added_by}、{@code disabled_by}
 * 一律取 JWT subject（{@link Caller#subject()}）：請求本文型別沒有這些欄位。
 *
 * <p>角色：{@code SecurityConfig} 的 matcher 管通用規則與逐條 ADMIN 規則；<b>換世代</b>（{@link #reinit} 帶 {@code generation}）同一路徑的兩種模式無法由 matcher 分流，
 * 所以服務層入口檢查（先於任何 Bridge 呼叫與權杖檢查）：非 ADMIN＝403 {@code research_write_forbidden}（D-64；VIEWER 在更早的授權鏈就被擋成 {@code ACCESS_DENIED}）。
 * 每個動作用 {@link AuditTrail#note} 標註目前請求（{@code audit_log} 的 {@code entity_type}、{@code entity_id}；日誌行的 {@code action}、{@code entity}）。
 */
@Service
public class ResearchCommandService implements ResearchCommandUseCase {

    private final ResearchBridge bridge;
    private final ResearchProjectReadPort projects;
    private final ResearchReviewReadPort reviews;
    private final ResearchQueryUseCase query;
    private final AuditTrail audit;

    ResearchCommandService(ResearchBridge bridge, ResearchProjectReadPort projects, ResearchReviewReadPort reviews, ResearchQueryUseCase query,
                           AuditTrail audit) {
        this.bridge = bridge;
        this.projects = projects;
        this.reviews = reviews;
        this.query = query;
        this.audit = audit;
    }

    @Override
    public ProjectDetail create(Caller caller, CreateInput input) {
        requireWriteEnabled();
        ResearchInputGates.CreateBody gated = ResearchInputGates.create(input, query::webLayerEnabled);
        UUID id = UUID.randomUUID();
        audit.note("research.create", "research", id.toString());
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("research_id", id.toString());
        body.put("slug", gated.slug());
        body.put("title", gated.title());
        body.put("topic", gated.topic());
        body.put("scope", gated.scope());
        body.put("depth_level", gated.depthLevel());
        body.put("created_by", caller.subject());
        call(() -> bridge.createProject(body));
        return reread(id, 201);
    }

    @Override
    public Map<String, Object> startStage(Caller caller, UUID id, String stage, StageInput input) {
        requireWriteEnabled();
        ResearchInputGates.stage(stage);
        requireProject(id);
        audit.note("research.stage", "research", id.toString(), Map.of("stage", stage));
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("auto", Boolean.TRUE.equals(input.auto()));
        if (input.note() != null && !input.note().isBlank()) {
            body.put("note", input.note().strip());
        }
        body.put("requested_by", caller.subject());
        body.put("after_escalation", Boolean.TRUE.equals(input.afterEscalation()));
        return call(() -> bridge.startStage(id, stage, body));
    }

    @Override
    public PrdVersion savePrd(Caller caller, UUID id, SavePrdInput input) {
        requireWriteEnabled();
        String summary = ResearchInputGates.savePrd(input);
        requireProject(id);
        audit.note("research.prd.save", "research", id.toString());
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("base_version", input.baseVersion());
        body.put("content", input.content());
        body.put("change_summary", summary);
        body.put("author", caller.subject());
        Map<String, Object> saved = call(() -> bridge.savePrd(id, body));
        int versionNo = saved.get("version_no") instanceof Number n ? n.intValue() : -1;
        return reviews.prdVersion(id, versionNo)
                .map(ResearchCommandService::withoutContent)
                .orElseThrow(() -> new UpstreamException.Failure("Bridge 回成功，但資料庫查無新的 PRD 版本 " + versionNo, Map.of("bridgeStatus", 201)));
    }

    @Override
    public Map<String, Object> approve(Caller caller, UUID id, ApproveInput input) {
        requireWriteEnabled();
        String reason = ResearchInputGates.approve(input);
        requireProject(id);
        audit.note("research.approve", "research", id.toString());
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("prd_version", input.prdVersion());
        body.put("expected_digests", input.expectedDigests());
        body.put("approver", caller.subject());
        if (reason != null) {
            body.put("reason", reason);
        }
        return call(() -> bridge.approve(id, body));
    }

    @Override
    public Map<String, Object> returnPrd(Caller caller, UUID id, String reason) {
        requireWriteEnabled();
        String checked = ResearchInputGates.requiredReason(reason);
        requireProject(id);
        audit.note("research.return", "research", id.toString());
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("approver", caller.subject());
        body.put("reason", checked);
        return call(() -> bridge.returnPrd(id, body));
    }

    @Override
    public Map<String, Object> action(Caller caller, UUID id, String verb) {
        requireWriteEnabled();
        requireProject(id);
        audit.note("research." + verb, "research", id.toString());
        Map<String, Object> body = new LinkedHashMap<>();
        if (!"reconcile".equals(verb)) {
            body.put("actor", caller.subject());
        }
        return call(() -> bridge.action(id, verb, body));
    }

    @Override
    public ReinitResult reinit(Caller caller, UUID id, ReinitInput input) {
        if (input.generation() != null && !caller.admin()) {
            // D-64：換世代僅 ADMIN；matcher 無法依請求本文分流，所以在服務層入口擋（先於權杖檢查與任何 Bridge 呼叫；Bridge 請求數 0）
            throw new ForbiddenException("換世代（generation=next）僅限 ADMIN", ErrorReasons.RESEARCH_WRITE_FORBIDDEN);
        }
        requireWriteEnabled();
        String reason = ResearchInputGates.reinit(input);
        requireProject(id);
        audit.note("research.reinit", "research", id.toString());
        Map<String, Object> body = new LinkedHashMap<>();
        if (input.generation() != null) {
            body.put("generation", input.generation());
            body.put("reason", reason);
            body.put("decided_by", caller.subject());
        }
        Map<String, Object> result = call(() -> bridge.reinit(id, body));
        ProjectDetail project = reread(id, 200);
        return new ReinitResult(project, result.get("fsm_project") == null ? null : result.get("fsm_project").toString(),
                result.get("fsm_generation") instanceof Number n ? Integer.valueOf(n.intValue()) : null,
                result.get("gate_decision_id") == null ? null : result.get("gate_decision_id").toString());
    }

    @Override
    public Map<String, Object> addAllowlistEntry(Caller caller, AllowlistInput input) {
        requireWriteEnabled();
        ResearchInputGates.allowlistEntry(input);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("list_kind", input.listKind());
        body.put("host", input.host());
        body.put("layer", input.layer());
        body.put("purpose", input.purpose() == null ? "" : input.purpose());
        body.put("tos_note", input.tosNote() == null ? "" : input.tosNote());
        if (input.minIntervalSeconds() != null) {
            body.put("min_interval_seconds", input.minIntervalSeconds());
        }
        body.put("tos_acknowledged", Boolean.TRUE.equals(input.tosAcknowledged()));
        body.put("added_by", caller.subject());
        Map<String, Object> entry = call(() -> bridge.addAllowlistEntry(body));
        // D-62(1)：Bridge 寫表並回應成功、條目 id 已知後才標註（V6 audit_log 的 entity_type／entity_id；不新增欄位、不寫 research_events）
        audit.note("research.allowlist", "research_allowlist", String.valueOf(entry.get("id")));
        return entry;
    }

    @Override
    public Map<String, Object> patchAllowlistEntry(Caller caller, String entryId, Map<String, Object> patch) {
        requireWriteEnabled();
        boolean enabled = ResearchInputGates.allowlistPatch(patch);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("enabled", enabled);
        body.put("disabled_by", caller.subject());
        Map<String, Object> entry = call(() -> bridge.patchAllowlistEntry(entryId, body));
        audit.note("research.allowlist", "research_allowlist", entry.get("id") == null ? entryId : entry.get("id").toString());
        return entry;
    }

    /** 契約 §0.2 第 3 列：backend 沒設研究寫入權杖＝整個寫入面停用，一個請求都不發。 */
    private void requireWriteEnabled() {
        if (!bridge.writeEnabled()) {
            throw new ServiceUnavailableException("backend 沒有設定研究寫入權杖（BRIDGE_RESEARCH_WRITE_TOKEN），研究寫入面已停用",
                    ErrorReasons.RESEARCH_WRITE_DISABLED, Map.of("cause", "bridge_token_unset"));
        }
    }

    private void requireProject(UUID id) {
        if (!projects.exists(id)) {
            throw new NotFoundException("研究專案不存在：" + id, ErrorReasons.RESEARCH_NOT_FOUND, Map.of());
        }
    }

    /** 恰一次 Bridge 呼叫；Bridge 的 4xx 與明確拒絕的 503 轉成 Console 的領域例外（reason 逐字）。 */
    private <T> T call(Supplier<T> action) {
        try {
            return action.get();
        } catch (BridgeRejectedException e) {
            throw ResearchBridgeErrors.map(e);
        }
    }

    /** Bridge 回成功後自 DB 重讀；資料庫查無＝Bridge 說謊或寫入沒落地，當作上游故障（不回 404：請求本身沒有錯）。 */
    private ProjectDetail reread(UUID id, int bridgeStatus) {
        try {
            return query.detail(id);
        } catch (NotFoundException e) {
            throw new UpstreamException.Failure("Bridge 回成功，但資料庫查無研究專案 " + id, Map.of("bridgeStatus", bridgeStatus));
        }
    }

    private static PrdVersion withoutContent(PrdVersion v) {
        return new PrdVersion(v.versionNo(), v.semver(), v.kind(), v.authorKind(), v.author(), v.parentVersionNo(), v.sha256(), v.bytes(),
                v.evidenceRefs(), v.changeSummary(), v.createdAt(), null);
    }
}
