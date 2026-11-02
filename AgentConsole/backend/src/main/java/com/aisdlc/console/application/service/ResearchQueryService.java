package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ResearchQueryUseCase;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchBridge.ResearchFsm;
import com.aisdlc.console.application.port.out.ResearchEvidenceReadPort;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.application.port.out.ResearchReviewReadPort;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.research.ResearchViews.EventPage;
import com.aisdlc.console.domain.model.research.ResearchViews.Matrix;
import com.aisdlc.console.domain.model.research.ResearchViews.PrdVersion;
import com.aisdlc.console.domain.model.research.ResearchViews.Project;
import com.aisdlc.console.domain.model.research.ResearchViews.RecordClass;
import com.aisdlc.console.domain.model.research.ResearchViews.Round;
import com.aisdlc.console.domain.model.research.ResearchViews.RunFact;
import com.aisdlc.console.domain.model.research.ResearchViews.Source;
import com.aisdlc.console.domain.service.ResearchFlowPolicy;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

/**
 * 研究到規格的讀取用例（API 契約 §1.1 的全部 GET；ADR-003 D4）：研究專案、事件、來源與證據、PRD 版本、審查輪、記錄完整率都是 JDBC <b>唯讀</b>
 * {@code console.research_*}（Bridge 是唯一寫入者）；只有能力探針、allowlist 與 FSM 視圖轉 Bridge 的唯讀端點。{@code {id}} 不存在一律
 * 404 {@code research_not_found}（含已封存者仍可讀：封存是軟刪除）。
 *
 * <p>能力探針快取 30 秒（API-RP-01）：只快取成功的回應；{@link #webLayerEnabled()} 共用同一份快取，探針取不到（Bridge 不可達等）回 empty，
 * 由建立請求的入口閘<b>放行</b>、交給 Bridge 自己判（只擋「確定知道 Web 層未啟用」的請求）。
 */
@Service
public class ResearchQueryService implements ResearchQueryUseCase {

    /** 能力探針的快取秒數（契約 API-RP-01）。 */
    static final Duration CAPABILITIES_TTL = Duration.ofSeconds(30);
    static final int DEFAULT_EVENT_LIMIT = 100;
    static final int MAX_EVENT_LIMIT = 500;
    /** 允許筆數為 0 的記錄類別：R10 自癒嘗試、R12 SCR（契約 API-RP-19）。 */
    private static final Set<String> MAY_BE_EMPTY = Set.of("R10", "R12");

    private final ResearchProjectReadPort projects;
    private final ResearchEvidenceReadPort evidence;
    private final ResearchReviewReadPort reviews;
    private final ResearchBridge bridge;
    private final Clock clock;
    private final AtomicReference<CachedCapabilities> capabilities = new AtomicReference<>();

    ResearchQueryService(ResearchProjectReadPort projects, ResearchEvidenceReadPort evidence, ResearchReviewReadPort reviews,
                         ResearchBridge bridge, Clock clock) {
        this.projects = projects;
        this.evidence = evidence;
        this.reviews = reviews;
        this.bridge = bridge;
        this.clock = clock;
    }

    private record CachedCapabilities(Map<String, Object> body, Instant at) {
    }

    @Override
    public List<Project> projects(boolean archived) {
        return projects.findAll(archived);
    }

    @Override
    public ProjectDetail detail(UUID id) {
        Project project = require(id);
        RunFact run = project.consoleProjectId() == null ? null : projects.latestRun(project.consoleProjectId()).orElse(null);
        ResearchFlowPolicy.Research cursor = new ResearchFlowPolicy.Research(project.flowStep(), project.flowPhase(), project.flowStatus(),
                project.flowDetail());
        ResearchFlowPolicy.ConsoleProject bound = project.consoleProjectId() == null ? null
                : new ResearchFlowPolicy.ConsoleProject(project.consoleProjectId());
        // P0 沒有內環 FSM 視圖（P1 分流後才有）：傳 null，ResearchFlowPolicy 只靠游標與最新 run 衍生
        ResearchFlowPolicy.Flow flow = ResearchFlowPolicy.flow(id, cursor, bound, run, null);
        var head = projects.headPrdVersion(id);
        return new ProjectDetail(project, projects.counts(id), head.isPresent() ? Integer.valueOf((int) head.getAsLong()) : null,
                projects.lastReview(id).orElse(null), flow);
    }

    @Override
    public EventPage events(UUID id, Long afterSeq, Integer limit) {
        require(id);
        if (afterSeq != null && afterSeq < 0) {
            throw ValidationException.of("afterSeq", "afterSeq 須為 0 以上的整數");
        }
        if (limit != null && limit < 1) {
            throw ValidationException.of("limit", "limit 須為 1 以上的整數");
        }
        int bounded = limit == null ? DEFAULT_EVENT_LIMIT : Math.min(limit, MAX_EVENT_LIMIT);
        return projects.events(id, afterSeq == null ? 0L : afterSeq, bounded);
    }

    @Override
    public List<Source> sources(UUID id) {
        require(id);
        return evidence.sources(id);
    }

    @Override
    public Matrix evidence(UUID id, Integer matrixVersion) {
        Project project = require(id);
        if (matrixVersion != null && matrixVersion < 1) {
            throw ValidationException.of("matrixVersion", "matrixVersion 須為 1 以上的整數");
        }
        Optional<Matrix> matrix = evidence.matrix(id, matrixVersion);
        if (matrix.isPresent()) {
            return matrix.get();
        }
        if (matrixVersion != null) {
            throw notFound("證據矩陣版本 " + matrixVersion + " 不存在");
        }
        // 預設（最新版）而尚無任何矩陣版本＝剛建立、尚未研究：回空矩陣（版本 0），讓證據頁顯示「尚無證據」而不是錯誤
        return new Matrix(0, project.scopeRev(), "", List.of(), null);
    }

    @Override
    public List<PrdVersion> prdVersions(UUID id) {
        require(id);
        return reviews.prdVersions(id);
    }

    @Override
    public PrdVersion prdVersion(UUID id, int versionNo) {
        require(id);
        return reviews.prdVersion(id, versionNo).orElseThrow(() -> notFound("PRD 版本 " + versionNo + " 不存在"));
    }

    @Override
    public List<Round> rounds(UUID id) {
        require(id);
        return reviews.rounds(id);
    }

    @Override
    public Round round(UUID id, int roundNo) {
        require(id);
        // 進行中、取消、無效輸出的審查沒有輪列（D-57）：指向它們的 {n} 一律 404
        return reviews.round(id, roundNo).orElseThrow(() -> notFound("審查輪 " + roundNo + " 不存在（沒有已完成的輪列）"));
    }

    @Override
    public FsmView fsm(UUID id) {
        Project project = require(id);
        ResearchFsm fsm;
        try {
            fsm = bridge.fsm(project.fsmProject(), project.workspacePath());
        } catch (BridgeRejectedException e) {
            throw ResearchBridgeErrors.map(e);
        }
        return new FsmView(fsm, projects.humanReturnCount(id, project.fsmProject()));
    }

    @Override
    public RecordsAudit recordsAudit(UUID id) {
        require(id);
        List<RecordClass> classes = projects.recordClasses(id);
        List<String> missing = new ArrayList<>();
        for (RecordClass recordClass : classes) {
            if (recordClass.count() == 0 && !MAY_BE_EMPTY.contains(recordClass.id())) {
                missing.add(recordClass.id());
            }
        }
        return new RecordsAudit(classes, List.copyOf(missing));
    }

    /** 立即丟棄能力探針的快取（下一次呼叫重新問 Bridge）：維運改了 Bridge 位址或設定之後、以及整合測試切換 Bridge 旋鈕之間使用。 */
    public void invalidateCapabilities() {
        capabilities.set(null);
    }

    @Override
    public Map<String, Object> capabilities() {
        Instant now = clock.instant();
        CachedCapabilities cached = capabilities.get();
        if (cached != null && Duration.between(cached.at(), now).compareTo(CAPABILITIES_TTL) < 0) {
            return cached.body();
        }
        Map<String, Object> fresh;
        try {
            fresh = bridge.capabilities();
        } catch (BridgeRejectedException e) {
            throw ResearchBridgeErrors.map(e);
        }
        capabilities.set(new CachedCapabilities(fresh, now));
        return fresh;
    }

    @Override
    public List<Map<String, Object>> allowlist() {
        Map<String, Object> body;
        try {
            body = bridge.allowlist();
        } catch (BridgeRejectedException e) {
            throw ResearchBridgeErrors.map(e);
        }
        List<Map<String, Object>> entries = new ArrayList<>();
        if (body.get("items") instanceof List<?> items) {
            for (Object item : items) {
                if (item instanceof Map<?, ?> entry) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> typed = (Map<String, Object>) entry;
                    entries.add(typed);
                }
            }
        }
        return List.copyOf(entries);
    }

    @Override
    public Optional<Boolean> webLayerEnabled() {
        try {
            return capabilities().get("web_layer_enabled") instanceof Boolean enabled ? Optional.of(enabled) : Optional.empty();
        } catch (RuntimeException e) {
            return Optional.empty();
        }
    }

    private Project require(UUID id) {
        return projects.findById(id).orElseThrow(() -> notFound("研究專案不存在：" + id));
    }

    private static NotFoundException notFound(String message) {
        return new NotFoundException(message, ErrorReasons.RESEARCH_NOT_FOUND, Map.of());
    }
}
