package com.aisdlc.console.application.port.in;

import com.aisdlc.console.application.port.in.ResearchQueryUseCase.ProjectDetail;
import com.aisdlc.console.domain.model.research.ResearchViews.PrdVersion;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 研究到規格的寫入用例（API 契約 §1.1 的全部 POST／PUT／PATCH；ADR-003 D4）。console-api <b>對 {@code console.research_*} 零寫入</b>：每個動作只做輸入閘、角色檢查、
 * 稽核標註，再<b>恰一次</b>呼叫 Bridge（不重試），成功後以 JDBC 唯讀取回結果。角色：一般寫入為 OPERATOR 以上（{@code SecurityConfig} 通用規則）；
 * Gate 0 核准／退回與 allowlist 新增／停用僅 ADMIN（{@code SecurityConfig} 逐條規則）；<b>換世代</b>（{@link #reinit} 帶 {@code generation:"next"}）僅 ADMIN，
 * 但 matcher 無法依請求本文分流，所以檢查在服務層入口（OPERATOR＝403 {@code research_write_forbidden}；D-64）。{@code approver}、{@code decided_by}、
 * {@code author} 一律取 JWT subject（{@link Caller#subject()}），請求本文沒有這些欄位。
 */
public interface ResearchCommandUseCase {

    /** 呼叫者：JWT subject 與是否 ADMIN（角色取自 JWT，不取自請求本文）。 */
    record Caller(String subject, boolean admin) {
    }

    /** {@code scope.layers} 的四個布林（可為 null＝請求沒給）。 */
    record Layers(Boolean academic, Boolean industry, Boolean oss, Boolean community) {
    }

    /** 建立請求的 scope（欄位可為 null＝請求沒給，預設值由 Bridge 補）。 */
    record Scope(Layers layers, String techStack, List<String> inScope, List<String> outOfScope, Integer recencyYears,
                 List<String> applicabilityAxes) {
    }

    /** {@code POST /research/projects} 的輸入（輸入閘之前的原樣值；欄位可為 null＝請求沒給）。 */
    record CreateInput(String slug, String title, String topic, Scope scope, String depthLevel, String targetScopeHint) {
    }

    /** {@code POST …/stages/{stage}} 的選填本文。 */
    record StageInput(Boolean auto, String note, Boolean afterEscalation) {
    }

    /** {@code PUT …/prd}：{@code baseVersion} 須是目前 head 版號（樂觀鎖）。 */
    record SavePrdInput(Integer baseVersion, String content, String changeSummary) {
    }

    /** {@code POST …/approve}：{@code prdVersion} 為整數 versionNo；{@code expectedDigests} 鍵為相對 POSIX 路徑、值為 {@code sha256:<64hex>}。 */
    record ApproveInput(Integer prdVersion, Map<String, String> expectedDigests, String reason) {
    }

    /** {@code POST …/reinit}：無 {@code generation}＝重試初始化；{@code "next"}＝換世代（{@code reason} 必填 1～500 字）。 */
    record ReinitInput(String generation, String reason) {
    }

    /** {@code POST /research/allowlist} 的輸入。 */
    record AllowlistInput(String listKind, String host, String layer, String purpose, String tosNote, Integer minIntervalSeconds,
                          Boolean tosAcknowledged) {
    }

    /** 換世代／重試初始化的結果：{@code project} 為成功後自 DB 重讀的詳情（取其 {@code flow}）；其餘三欄取自 Bridge 回應（重試初始化時為 null）。 */
    record ReinitResult(ProjectDetail project, String fsmProject, Integer fsmGeneration, String gateDecisionId) {
    }

    /** 建立：成功回自 DB 重讀的詳情（{@code flowStep=topic}、{@code flowPhase=INGESTED}）。 */
    ProjectDetail create(Caller caller, CreateInput input);

    /** 啟動階段：回 Bridge 的 202 本文（snake_case：{@code stage_run_id}、{@code engine_run_id}、{@code flow}）。 */
    Map<String, Object> startStage(Caller caller, UUID id, String stage, StageInput input);

    /** 存 PRD 新版：成功回自 DB 重讀的新版本（不含 {@code content}）。 */
    PrdVersion savePrd(Caller caller, UUID id, SavePrdInput input);

    Map<String, Object> approve(Caller caller, UUID id, ApproveInput input);

    Map<String, Object> returnPrd(Caller caller, UUID id, String reason);

    /** {@code verb}：{@code cancel}｜{@code reconcile}｜{@code archive}｜{@code restore}。 */
    Map<String, Object> action(Caller caller, UUID id, String verb);

    ReinitResult reinit(Caller caller, UUID id, ReinitInput input);

    /** 新增 allowlist 條目（僅 ADMIN）：成功後以 {@code AuditTrail.note("research.allowlist", "research_allowlist", <條目 id>)} 標註（D-62(1)）。 */
    Map<String, Object> addAllowlistEntry(Caller caller, AllowlistInput input);

    /** 停用／啟用 allowlist 條目（僅 ADMIN）：{@code body} 只准 {@code enabled} 一鍵（其餘鍵＝422 {@code invalid_request}）；成功後同上標註。 */
    Map<String, Object> patchAllowlistEntry(Caller caller, String entryId, Map<String, Object> body);
}
