package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.application.port.in.ResearchScrUseCase;
import com.aisdlc.console.application.port.out.AgentBridge.BridgeRejectedException;
import com.aisdlc.console.application.port.out.AuditTrail;
import com.aisdlc.console.application.port.out.ExecutionRunRepository;
import com.aisdlc.console.application.port.out.ResearchBridge;
import com.aisdlc.console.application.port.out.ResearchProjectReadPort;
import com.aisdlc.console.application.port.out.ResearchScrReadPort;
import com.aisdlc.console.domain.exception.DomainException;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.NotFoundException;
import com.aisdlc.console.domain.exception.ServiceUnavailableException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.research.ResearchRouteViews.Scr;
import com.aisdlc.console.domain.model.research.ResearchViews;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;

/**
 * 規格變更請求用例（API-RP-15；PRD FR-R2P-19；D-103、D-104）。console-api 對 {@code console.research_scr} 零寫入：<b>發起</b>＝輸入閘（400，零 Bridge 請求）→ 專案存在（404）→
 * 先停進行中的 run（既有 stop 用例 {@link ExecutionControlService#cancel}；{@code HEALING_FAILED} 不停：它不碰內環，只產生指令）→ 恰一次 Bridge {@code :scr}（不重試）；
 * <b>套用重試</b>＝Bridge {@code :scr-apply}。Bridge 的 409 {@code scr_open}／{@code scr_limit}／{@code fsm_state_conflict} 與 422 {@code violations[]} 逐字透傳。
 * {@code requested_by}、{@code approver} 一律取 JWT subject。
 */
@Service
public class ResearchScrService implements ResearchScrUseCase {

    private static final Logger LOG = LoggerFactory.getLogger(ResearchScrService.class);
    /** SCR 理由上限（與 Bridge 的 {@code SCR_REASON_MAX} 同值；獨立常數）。 */
    public static final int SCR_REASON_MAX = 500;
    /** evidenceUrl 長度上限（與 V21 CHECK 及 Bridge 同值）。 */
    static final int EVIDENCE_URL_MAX = 500;
    public static final int AFFECTED_SECTION_MAX = 200;
    public static final int AFFECTED_SECTIONS_MAX_ITEMS = 20;
    public static final Set<String> KINDS = Set.of("MINOR", "MAJOR");
    public static final Set<String> SOURCE_KINDS = Set.of("HUMAN", "REVIEW_FINDING", "SCG4", "HEALING_FAILED");
    /** 理由分類：PRD 的中文五分類 → DB 碼（TCS §5.1；請求亦可直接給 DB 碼）。 */
    static final Map<String, String> REASON_CLASSES = Map.of("PRD 缺漏證據", "EVIDENCE", "AC 模糊", "AC_VAGUE", "需求變更", "REQ_CHANGE",
            "技術不可行", "INFEASIBLE", "其他", "OTHER");
    private static final String HEALING_FAILED = "HEALING_FAILED";

    private final ResearchBridge bridge;
    private final ResearchProjectReadPort researchProjects;
    private final ResearchScrReadPort scrs;
    private final ExecutionRunRepository runs;
    private final ExecutionControlService control;
    private final AuditTrail audit;

    ResearchScrService(ResearchBridge bridge, ResearchProjectReadPort researchProjects, ResearchScrReadPort scrs, ExecutionRunRepository runs,
                       ExecutionControlService control, AuditTrail audit) {
        this.bridge = bridge;
        this.researchProjects = researchProjects;
        this.scrs = scrs;
        this.runs = runs;
        this.control = control;
        this.audit = audit;
    }

    @Override
    public Map<String, Object> open(Caller caller, UUID researchId, ScrInput input) {
        requireWriteEnabled();
        Map<String, Object> body = gate(input);
        ResearchViews.Project research = require(researchId);
        audit.note("research.scr", "research", researchId.toString());
        if (!HEALING_FAILED.equals(input.sourceKind()) && research.consoleProjectId() != null) {
            stopActiveRun(research.consoleProjectId());
        }
        body.put("requested_by", caller.subject());
        return call(() -> bridge.openScr(researchId, body));
    }

    @Override
    public List<Scr> list(UUID researchId) {
        require(researchId);
        return scrs.list(researchId);
    }

    @Override
    public Map<String, Object> apply(Caller caller, UUID researchId, int scrNo) {
        requireWriteEnabled();
        if (scrNo < 1) {
            throw ValidationException.of("scrNo", "scrNo 須為 1 以上的整數");
        }
        require(researchId);
        audit.note("research.scr.apply", "research", researchId.toString(), Map.of("scrNo", scrNo));
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("scr_no", scrNo);
        body.put("approver", caller.subject());
        return call(() -> bridge.applyScr(researchId, body));
    }

    /** D-103：console-api 在呼叫 Bridge 之前先停進行中的 run（既有 stop 用例）；停不了（狀態剛好已變）不擋 SCR——內環唯讀由 Bridge 與執行前置守衛保證。 */
    private void stopActiveRun(UUID consoleProjectId) {
        runs.findInProgressRunId(consoleProjectId).ifPresent(runId -> {
            try {
                control.cancel(runId);
            } catch (DomainException e) {
                LOG.warn("SCR 發起：停止進行中的批次 {} 失敗（{}），仍繼續呼叫 Bridge", runId, e.reason());
            }
        });
    }

    /** 驗請求並轉成 Bridge 的 snake_case 本文（不含 requested_by）。違規回 400（{@code errors[]} 加 {@code details.violations}）。 */
    static Map<String, Object> gate(ScrInput in) {
        ResearchRouteGates.Check check = new ResearchRouteGates.Check();
        if (in.kind() == null || !KINDS.contains(in.kind())) {
            check.add("kind", in.kind() == null ? "required" : "invalid_value", "kind 須為 MINOR 或 MAJOR");
        }
        if (in.sourceKind() == null || !SOURCE_KINDS.contains(in.sourceKind())) {
            check.add("sourceKind", in.sourceKind() == null ? "required" : "invalid_value",
                    "sourceKind 須為 " + String.join("、", new java.util.TreeSet<>(SOURCE_KINDS)) + " 之一");
        }
        String reason = in.reason() == null ? null : in.reason().strip();
        if (reason == null || reason.isEmpty()) {
            check.add("reason", "required", "reason 為必填（1～" + SCR_REASON_MAX + " 字）");
        } else if (reason.codePointCount(0, reason.length()) > SCR_REASON_MAX) {
            check.add("reason", "max_length", "reason 不可超過 " + SCR_REASON_MAX + " 字");
        }
        String reasonClass = null;
        if (in.reasonClass() != null) {
            reasonClass = REASON_CLASSES.containsKey(in.reasonClass()) ? REASON_CLASSES.get(in.reasonClass())
                    : REASON_CLASSES.containsValue(in.reasonClass()) ? in.reasonClass() : null;
            if (reasonClass == null) {
                check.add("reasonClass", "invalid_value", "reasonClass 須為 " + String.join("、", REASON_CLASSES.keySet()) + " 之一");
            }
        }
        List<String> sections = new ArrayList<>();
        if (in.affectedSections() != null) {
            if (in.affectedSections().size() > AFFECTED_SECTIONS_MAX_ITEMS) {
                check.add("affectedSections", "max_items", "affectedSections 至多 " + AFFECTED_SECTIONS_MAX_ITEMS + " 項");
            }
            for (int i = 0; i < in.affectedSections().size(); i++) {
                String item = in.affectedSections().get(i);
                if (item == null || item.isBlank()) {
                    check.add("affectedSections[" + i + "]", "required", "affectedSections 的項目不可為空白");
                } else if (item.codePointCount(0, item.length()) > AFFECTED_SECTION_MAX) {
                    check.add("affectedSections[" + i + "]", "max_length", "affectedSections 的項目不可超過 " + AFFECTED_SECTION_MAX + " 字");
                } else {
                    sections.add(item.strip());
                }
            }
        }
        String evidenceUrl = in.evidenceUrl() == null || in.evidenceUrl().isEmpty() ? null : in.evidenceUrl();
        if (evidenceUrl != null && !evidenceUrl.startsWith("https://")) {
            check.add("evidenceUrl", "not_https", "evidenceUrl 須以 https:// 開頭");
        } else if (evidenceUrl != null && evidenceUrl.length() > EVIDENCE_URL_MAX) {
            check.add("evidenceUrl", "too_long", "evidenceUrl 不可超過 " + EVIDENCE_URL_MAX + " 字元");
        }
        if (!check.violations.isEmpty()) {
            // evidenceUrl 的違規依 D-142 ⚖P2-11 為 422；其餘欄位維持 P1 既有的 400
            throw check.violations.stream().anyMatch(v -> "evidenceUrl".equals(v.field())) ? check.unprocessable() : check.validation();
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("kind", in.kind());
        body.put("source_kind", in.sourceKind());
        body.put("reason", reason);
        if (reasonClass != null) {
            body.put("reason_class", reasonClass);
        }
        body.put("affected_sections", sections);
        if (evidenceUrl != null) {
            body.put("evidence_url", evidenceUrl);
        }
        return body;
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
