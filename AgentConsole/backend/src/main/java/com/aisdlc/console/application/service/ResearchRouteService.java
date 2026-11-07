package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.application.port.in.ResearchRouteUseCase;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ProjectRepository;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.application.port.out.ResearchRouteReadPort;
import com.aisdlc.console.domain.exception.ConflictException;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ResearchBridgeException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.UpstreamException;
import com.aisdlc.console.domain.exception.Violation;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.model.project.NewProject;
import com.aisdlc.console.domain.model.project.Project;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Route;
import com.aisdlc.console.domain.model.research.ResearchViews;
import com.aisdlc.console.domain.service.FieldRules;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Clock;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;

/**
 * 分流用例（API-RP-14；契約 §1.4；IFACE §3.3；D-105、D-106、D-108、D-112）。<b>交易邊界</b>（AC-R2P-11-8）：確認會同步呼叫 Bridge（最長 300 秒），所以刻意不是
 * {@code @Transactional}——<ol>
 *   <li>輸入閘（400／422）與 {@code route_conflict} 預檢（409）先於一切寫入，零 Bridge 請求（D-108）；</li>
 *   <li>呼 Bridge 預演取得 {@code execution_path}、{@code impl_fsm_project}（Bridge 是路徑的唯一導出者）；</li>
 *   <li><b>先建</b> {@code projects} 列（DRAFT、{@code signed_off=false}、{@code sdd_project}＝內環鍵；V12 唯一索引防重綁；<b>一個短交易 commit，先於 Bridge 呼叫</b>——
 *       Bridge 失敗不回滾它，靠補償）；重試（最新分流為 FAILED 且其 Console 專案仍在同路徑同鍵）沿用既有列；</li>
 *   <li>呼 Bridge {@code :route}（同步、讀逾時 330 秒）；成功由 <b>Bridge</b> 回填 {@code research_projects.console_project_id}（console-api 不寫研究表）；</li>
 *   <li>任何失敗（502 {@code route_step_failed}、逾時、不可達、Bridge 拒絕）：{@code projects} 列軟刪除標 {@code ARCHIVED}（不刪列；同時釋放 V12 綁定，讓補償後的新分流可重綁）
 *       ＋稽核標註 {@code research.route.compensate}＋（取得到 {@code route_id} 時）呼 Bridge {@code :route-compensated}（Bridge 驗該列為 FAILED 才寫 COMPENSATED，
 *       否則回 409 {@code route_conflict}——console-api 只記錄、不重試、不隱瞞）。<b>不自動 git clean、stash、刪目錄</b>。</li>
 * </ol>
 */
@Service
public class ResearchRouteService implements ResearchRouteUseCase {

    private static final Logger LOG = LoggerFactory.getLogger(ResearchRouteService.class);
    /** 補償理由上限（獨立常數，與 Bridge 的 {@code COMPENSATE_REASON_MAX} 同值）。 */
    static final int COMPENSATE_REASON_MAX = 500;
    private static final Set<String> COMPENSABLE_ROUTE_STATUSES = Set.of("FAILED", "RUNNING", "PENDING");

    private final ResearchBridge bridge;
    private final ResearchProjectReadPort researchProjects;
    private final ResearchRouteReadPort routes;
    private final ProjectRepository consoleProjects;
    private final ResearchGithubTokenSource githubToken;
    private final AuditTrail audit;
    private final Clock clock;
    private final TransactionTemplate tx;

    @SuppressWarnings("java:S107")
    ResearchRouteService(ResearchBridge bridge, ResearchProjectReadPort researchProjects, ResearchRouteReadPort routes, ProjectRepository consoleProjects,
                         ResearchGithubTokenSource githubToken, AuditTrail audit, Clock clock, TransactionTemplate tx) {
        this.bridge = bridge;
        this.researchProjects = researchProjects;
        this.routes = routes;
        this.consoleProjects = consoleProjects;
        this.githubToken = githubToken;
        this.audit = audit;
        this.clock = clock;
        this.tx = tx;
    }

    @Override
    public Map<String, Object> preview(Caller caller, UUID researchId, RouteInput input) {
        requireWriteEnabled();
        ResearchViews.Project research = require(researchId);
        Map<String, Object> body = ResearchRouteGates.bridgeBody(input, research.targetScope());
        audit.note("research.route.preview", "research", researchId.toString());
        return call(() -> bridge.routePreview(researchId, body));
    }

    @Override
    public Route confirm(Caller caller, UUID researchId, RouteInput input) {
        requireWriteEnabled();
        ResearchViews.Project research = require(researchId);
        Map<String, Object> request = ResearchRouteGates.bridgeBody(input, research.targetScope());
        routes.active(researchId).ifPresent(active -> {
            throw new ConflictException("這個研究專案已有進行中或已完成的分流", ErrorReasons.RESEARCH_ROUTE_CONFLICT,
                    Map.of("route_id", active.id().toString(), "status", active.status()));
        });
        audit.note("research.route", "research", researchId.toString());
        Map<String, Object> preview = call(() -> bridge.routePreview(researchId, request));
        String executionPath = text(preview.get("execution_path"));
        String implKey = text(preview.get("impl_fsm_project"));
        requireSafeExecutionPath(executionPath);
        Route failed = routes.latest(researchId).filter(route -> "FAILED".equals(route.status())).orElse(null);
        UUID consoleProjectId = prepareConsoleProject(caller, research, executionPath, implKey, failed);

        Map<String, Object> body = new LinkedHashMap<>(request);
        body.put("console_project_id", consoleProjectId.toString());
        body.put("approver", caller.subject());
        if (Boolean.TRUE.equals(input.retry())) {
            body.put("retry", true);
        }
        if ("B".equals(input.track()) && Boolean.TRUE.equals(input.createGithub())) {
            githubToken.token().ifPresent(token -> body.put("github_token", token));
        }
        try {
            call(() -> bridge.route(researchId, body));
        } catch (RuntimeException failure) {
            compensate(caller, researchId, consoleProjectId, failure);
            throw failure;
        }
        return routes.latest(researchId).filter(route -> "SUCCEEDED".equals(route.status()))
                .orElseThrow(() -> new UpstreamException.Failure("Bridge 回成功，但資料庫查無成功的分流", Map.of("bridgeStatus", 200)));
    }

    @Override
    public Optional<Route> current(UUID researchId) {
        require(researchId);
        return routes.latest(researchId);
    }

    // ── 先建 projects 列與補償 ───────────────────────────────────────────────────────────

    /** 第 3 步：先建 Console 專案列（一個短交易 commit）；重試沿用同一列。回專案 id。 */
    private UUID prepareConsoleProject(Caller caller, ResearchViews.Project research, String executionPath, String implKey, Route failed) {
        UUID id = tx.execute(status -> {
            if (failed != null && failed.consoleProjectId() != null) {
                Optional<Project> existing = consoleProjects.findById(failed.consoleProjectId());
                if (existing.isPresent() && executionPath.equals(existing.get().executionPath()) && java.util.Objects.equals(implKey, existing.get().sddProject())) {
                    return existing.get().id();
                }
            }
            String name = (research.rpNo() + " " + research.title());
            NewProject spec = new NewProject(name.length() > 200 ? name.substring(0, 200) : name, executionPath,
                    "待拆解簽核後定義（由研發工作流 " + research.rpNo() + " 分流建立；草案，簽核前禁止執行）。",
                    "研發工作流 " + research.rpNo() + "（" + research.slug() + "）分流產生的內環專案。", null, true, implKey, null, null);
            Project created = Project.create(spec, caller.subject(), clock.instant());
            SddBindings.requireFree(consoleProjects, created.executionPath(), created.sddProject(), created.id());
            consoleProjects.save(created);
            return created.id();
        });
        return id;
    }

    /** 失敗補償到安全態（AC-R2P-11-8）：專案列標 ARCHIVED（軟刪除，不刪列）、稽核標註、通知 Bridge；全程不碰檔案與 git。 */
    private void compensate(Caller caller, UUID researchId, UUID consoleProjectId, RuntimeException cause) {
        String label = causeLabel(cause);
        try {
            tx.executeWithoutResult(status -> consoleProjects.findByIdForUpdate(consoleProjectId).ifPresent(project -> {
                if (!project.deleted()) {
                    project.softDelete(clock.instant());
                    consoleProjects.save(project);
                }
            }));
        } catch (RuntimeException e) {
            LOG.error("分流補償：無法把 Console 專案 {} 標為 ARCHIVED（研究專案 {}）", consoleProjectId, researchId, e);
        }
        audit.note("research.route.compensate", "project", consoleProjectId.toString(),
                Map.of("research_id", researchId.toString(), "cause", label));
        UUID routeId = compensableRouteId(researchId, consoleProjectId, cause);
        if (routeId == null) {
            return;
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("route_id", routeId.toString());
        String reason = "console-api 補償：分流失敗（" + label + "），Console 專案列已標為 ARCHIVED";
        body.put("reason", reason.length() > COMPENSATE_REASON_MAX ? reason.substring(0, COMPENSATE_REASON_MAX) : reason);
        body.put("requested_by", caller.subject());
        try {
            bridge.routeCompensated(researchId, body);
        } catch (RuntimeException e) {
            // 例：逾時但 Bridge 仍 RUNNING＝409 route_conflict；不重試、不隱瞞（原失敗照樣回給呼叫者）
            LOG.warn("分流補償通知 Bridge 未被接受（research={}, route={}）：{}", researchId, routeId, e.getMessage());
        }
    }

    private UUID compensableRouteId(UUID researchId, UUID consoleProjectId, RuntimeException cause) {
        if (cause instanceof DomainException domain && domain.details().get("route_id") != null) {
            try {
                return UUID.fromString(domain.details().get("route_id").toString());
            } catch (IllegalArgumentException ignored) {
                // 落到最新分流列的查找
            }
        }
        return routes.latest(researchId).filter(route -> consoleProjectId.equals(route.consoleProjectId()))
                .filter(route -> COMPENSABLE_ROUTE_STATUSES.contains(route.status())).map(Route::id).orElse(null);
    }

    private static String causeLabel(RuntimeException cause) {
        if (cause instanceof ResearchBridgeException e) {
            return e.reason();
        }
        return cause instanceof DomainException e && e.reason() != null ? e.reason() : cause.getClass().getSimpleName();
    }

    // ── 共用 ─────────────────────────────────────────────────────────────────────────────

    /** Bridge 導出的執行路徑須是安全的絕對路徑（同專案建立的 {@code FieldRules.executionPath}），否則 422 {@code sanitization_failed}、零 projects 寫入。 */
    private static void requireSafeExecutionPath(String path) {
        Violations v = new Violations();
        String checked = path == null ? null : FieldRules.executionPath(v, "executionPath", path);
        if (checked == null || !v.isEmpty() || path.contains("..")) {
            throw new UnprocessableException("分流的執行路徑沒有通過安全檢查", ErrorReasons.RESEARCH_SANITIZATION_FAILED,
                    List.of(), List.of(new Violation("executionPath", "執行路徑必須是不含 .. 的絕對路徑")), Map.of());
        }
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

    private static String text(Object value) {
        return value == null ? null : value.toString();
    }
}
