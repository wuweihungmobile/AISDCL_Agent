package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.SiKeyNames;
import com.aisdlc.console.adapter.in.web.dto.research.AllowlistEntryDto;
import com.aisdlc.console.adapter.in.web.dto.research.ApproveResultDto;
import com.aisdlc.console.adapter.in.web.dto.research.CapabilitiesDto;
import com.aisdlc.console.adapter.in.web.dto.research.EvidenceMatrixDto;
import com.aisdlc.console.adapter.in.web.dto.research.PrdVersionDto;
import com.aisdlc.console.adapter.in.web.dto.research.RecordsAuditDto;
import com.aisdlc.console.adapter.in.web.dto.research.ReconcileResultDto;
import com.aisdlc.console.adapter.in.web.dto.research.ReinitResultDto;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchAllowlistPatchRequest;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchAllowlistRequest;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchApproveRequest;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchCreateRequest;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchEventPage;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchFsmViewDto;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchProjectDetail;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchProjectSummary;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchReinitRequest;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchReturnRequest;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchSavePrdRequest;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchStageRequest;
import com.aisdlc.console.adapter.in.web.dto.research.ResearchWatchSourceRequest;
import com.aisdlc.console.adapter.in.web.dto.research.ReturnResultDto;
import com.aisdlc.console.adapter.in.web.dto.research.ReviewRoundDto;
import com.aisdlc.console.adapter.in.web.dto.research.SourceDto;
import com.aisdlc.console.adapter.in.web.dto.research.StageStartedDto;
import com.aisdlc.console.adapter.in.web.dto.research.WatchSourceDto;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.application.port.in.ResearchQueryUseCase;
import com.aisdlc.console.application.port.in.ResearchRegistryUseCase;
import com.aisdlc.console.domain.model.auth.Role;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 研發工作流（ResearchToPRD P0）的 REST 端點（API 契約 API_Contract_ResearchToPRD §1.1；TCS-ResearchToPRD-P0 D5）：研究專案、事件、來源與證據、PRD 版本、
 * 審查輪、FSM 視圖、記錄完整率、allowlist 與全部寫入動作。<b>console-api 對 {@code console.research_*} 零寫入</b>：GET 走 JDBC 唯讀（唯有能力探針、allowlist、FSM
 * 視圖轉 Bridge 的唯讀端點）；寫入只經 Bridge、恰一次呼叫、不重試（{@code ResearchCommandService}），成功後自 DB 重讀。
 *
 * <p>權限：GET＝VIEWER 以上（無有效 JWT＝401）；{@code POST}／{@code PUT}／{@code PATCH} 預設＝OPERATOR 以上（{@code SecurityConfig} 通用規則）；
 * <b>僅 ADMIN</b>：{@code approve}、{@code return}、{@code POST /allowlist}、{@code PATCH /allowlist/{id}}（{@code SecurityConfig} 逐條規則，置於通用規則之前；
 * VIEWER、OPERATOR＝403 {@code ACCESS_DENIED}）；<b>換世代</b>（{@code reinit} 帶 {@code generation:"next"}）同樣僅 ADMIN，由 {@code ResearchCommandService}
 * 於服務層入口檢查（OPERATOR＝403 {@code research_write_forbidden}）。失敗一律沒有 {@code data}。沒有任何 DELETE 對映。
 *
 * <p>共通失敗序（契約 §0.2，先中者定案）：401→403→503 {@code research_write_disabled}（寫入端點）→400／422 輸入閘→404 {@code research_not_found}→409 端點專屬
 * →502／504（{@code bridge_unreachable}／{@code bridge_timeout}）。
 */
@RestController
@RequestMapping("/api/v1/research")
@Tag(name = "研發工作流（ResearchToPRD）", description = "研究→證據→PRD→四方審查→Gate 0 的 P0 端點（API-RP-01～13、18～22）；契約檔 API_Contract_ResearchToPRD.md")
public class ResearchController {

    private static final String WRITE_FLOW = "失敗序：研究寫入權杖未設（503 research_write_disabled）→ 輸入閘（422 invalid_request；details.violations[{field,rule,message}] 一次全列，"
            + "errors[] 同內容）→ 專案不存在（404 research_not_found）→ 恰一次 Bridge 呼叫（連線 2 秒、讀取 30 秒、不重試；Bridge 的 409／422／503 reason 逐字透傳，"
            + "連線失敗 502 bridge_unreachable、讀取逾時 504 bridge_timeout）。操作人（approver、decided_by、author、requested_by、added_by…）一律取 JWT subject，"
            + "請求本文沒有這些欄位。";

    private final ResearchQueryUseCase query;
    private final ResearchCommandUseCase command;
    private final ResearchRegistryUseCase registry;

    public ResearchController(ResearchQueryUseCase query, ResearchCommandUseCase command, ResearchRegistryUseCase registry) {
        this.query = query;
        this.command = command;
        this.registry = registry;
    }

    // ── 唯讀（VIEWER 以上）──────────────────────────────────────────────────────────────

    @GetMapping("/capabilities")
    @Operation(operationId = "getResearchCapabilities", summary = "研究面能力探針（API-RP-01）",
            description = "轉 Bridge GET /research/capabilities 的 camelCase 投影，快取 30 秒（只快取成功回應）。無 BRIDGE_DB_DSN 時仍 200、db=false"
                    + "（這是「研究端點無 DSN 一律 503」的唯一例外）；mode=mock-only 時 UI 停用「啟動深研」（伺服器端不拒絕）。VIEWER 以上可讀。")
    public ApiResult<CapabilitiesDto> capabilities() {
        return ApiResult.ok(CapabilitiesDto.from(query.capabilities()));
    }

    @GetMapping("/projects")
    @Operation(operationId = "listResearchProjects", summary = "研究專案清單（API-RP-02）",
            description = "回陣列（不分頁），更新時間新到舊。預設只回未封存的專案；archived=true 回已封存的那一份。JDBC 唯讀。VIEWER 以上可讀。")
    public ApiResult<List<ResearchProjectSummary>> projects(
            @Parameter(description = "true＝只回已封存的專案（預設 false＝只回未封存）") @RequestParam(defaultValue = "false") boolean archived) {
        return ApiResult.ok(query.projects(archived).stream().map(ResearchProjectSummary::from).toList());
    }

    @GetMapping("/projects/{id}")
    @Operation(operationId = "getResearchProject", summary = "研究專案詳情與流程脊（API-RP-04）",
            description = "專案列、五個計數、PRD head 版號、最新已完成的審查輪與流程脊 flow（固定五步；effective 由 ResearchFlowPolicy 計算、不落 DB："
                    + "步驟 1～3 與 TCS 相態原樣取 DB 游標）。已封存的專案仍可讀。不存在＝404 research_not_found。VIEWER 以上可讀。")
    public ApiResult<ResearchProjectDetail> project(@Parameter(description = "研究專案 id（UUID）") @PathVariable UUID id) {
        return ApiResult.ok(ResearchProjectDetail.from(query.detail(id)));
    }

    @GetMapping("/projects/{id}/events")
    @Operation(operationId = "listResearchEvents", summary = "研究事件帳（REST 回補；API-RP-05）",
            description = "append-only 事件帳 seq > afterSeq 的前 limit 筆（依 seq 遞增；limit 預設 100、上限 500，超過夾到 500）。回 {items, nextSeq, truncated}："
                    + "truncated 為真時以 nextSeq 續抓。SSE 斷線後客戶端先以本端點回補再接串流。不存在＝404 research_not_found。VIEWER 以上可讀。")
    public ApiResult<ResearchEventPage> events(
            @PathVariable UUID id,
            @Parameter(description = "游標（選填；整數 ≥0，預設 0）：只回 seq 嚴格大於它的事件", schema = @Schema(type = "integer", format = "int64", minimum = "0"))
            @RequestParam(required = false) Long afterSeq,
            @Parameter(description = "頁大小（選填；整數 ≥1，預設 100，上限 500）", schema = @Schema(type = "integer", format = "int32", minimum = "1", maximum = "500"))
            @RequestParam(required = false) Integer limit) {
        return ApiResult.ok(ResearchEventPage.from(query.events(id, afterSeq, limit)));
    }

    @GetMapping("/projects/{id}/sources")
    @Operation(operationId = "listResearchSources", summary = "研究來源與抓取紀錄（API-RP-07）",
            description = "全部來源（依 sourceNo），每筆帶它的抓取紀錄（依抓取時間遞增；含失敗與被拒者）。T3 來源只當搜尋線索（clueOnly）。VIEWER 以上可讀。")
    public ApiResult<List<SourceDto>> sources(@PathVariable UUID id) {
        return ApiResult.ok(query.sources(id).stream().map(SourceDto::from).toList());
    }

    @GetMapping("/projects/{id}/evidence")
    @Operation(operationId = "listResearchEvidence", summary = "證據矩陣（API-RP-07）",
            description = "一個矩陣版本（預設最新版）：items 取自 research_evidence_items；counterEvidence、honestBounds、searchLog 取自 EVIDENCE_ITEMS 產物全文"
                    + "（D-43）。尚無任何矩陣版本（剛建立、尚未研究）回 200 的空矩陣（matrixVersion＝0）；指定的 matrixVersion 不存在＝404 research_not_found。VIEWER 以上可讀。")
    public ApiResult<EvidenceMatrixDto> evidence(
            @PathVariable UUID id,
            @Parameter(description = "矩陣版本（選填；整數 ≥1，預設最新版）", schema = @Schema(type = "integer", format = "int32", minimum = "1"))
            @RequestParam(required = false) Integer matrixVersion) {
        return ApiResult.ok(EvidenceMatrixDto.from(query.evidence(id, matrixVersion)));
    }

    @GetMapping("/projects/{id}/prd/versions")
    @Operation(operationId = "listPrdVersions", summary = "PRD 版本清單（API-RP-08）",
            description = "依 versionNo 遞增；清單不含全文（content 只有單筆端點回）。VIEWER 以上可讀。")
    public ApiResult<List<PrdVersionDto>> prdVersions(@PathVariable UUID id) {
        return ApiResult.ok(query.prdVersions(id).stream().map(PrdVersionDto::withoutContent).toList());
    }

    @GetMapping("/projects/{id}/prd/versions/{n}")
    @Operation(operationId = "getPrdVersion", summary = "單一 PRD 版本（含全文；API-RP-08）",
            description = "n＝versionNo（整數）。含 content 全文（工作室編輯器與 Diff 用）。版本不存在＝404 research_not_found。VIEWER 以上可讀。")
    public ApiResult<PrdVersionDto> prdVersion(@PathVariable UUID id, @Parameter(description = "PRD 版號 versionNo（整數 ≥1）") @PathVariable int n) {
        return ApiResult.ok(PrdVersionDto.from(query.prdVersion(id, n)));
    }

    @GetMapping("/projects/{id}/review-rounds")
    @Operation(operationId = "listReviewRounds", summary = "四方審查輪清單（API-RP-10）",
            description = "依 roundNo 遞增，各帶四維分數與缺陷。只有已完成評估的輪才有列（D-57）：進行中、被取消、中斷或輸出無效的審查沒有輪列，"
                    + "進行中的狀態由 stage run 與 research.run 事件表達。VIEWER 以上可讀。")
    public ApiResult<List<ReviewRoundDto>> reviewRounds(@PathVariable UUID id) {
        return ApiResult.ok(query.rounds(id).stream().map(ReviewRoundDto::from).toList());
    }

    @GetMapping("/projects/{id}/review-rounds/{n}")
    @Operation(operationId = "getReviewRound", summary = "單一審查輪（API-RP-10）",
            description = "n＝roundNo。指向沒有列的輪（進行中、被取消、輸出無效）＝404 research_not_found（D-57）。VIEWER 以上可讀。")
    public ApiResult<ReviewRoundDto> reviewRound(@PathVariable UUID id, @Parameter(description = "輪號 roundNo（整數 ≥1）") @PathVariable int n) {
        return ApiResult.ok(ReviewRoundDto.from(query.round(id, n)));
    }

    @GetMapping("/projects/{id}/fsm")
    @Operation(operationId = "getResearchFsm", summary = "外環 FSM 視圖（API-RP-13）",
            description = "轉 Bridge GET /sdd/fsm/{外環鍵}?root=<工作區>（唯讀，連線 2 秒、讀取 3 秒、不重試）：既有 SddFsmState 全部欄位原樣（最外層 camelCase、巢狀內容保留 "
                    + "snake_case 鍵），retryHistory 多 gates（SCG_VALIDATION、PR_REVIEW、RTM_VERIFY 各 {currentCount, entries}），另加 humanReturnCount（目前 fsm_generation "
                    + "內 Gate 0 人工退回的筆數，console-api 讀 DB 計得）。VIEWER 以上可讀。")
    public ApiResult<ResearchFsmViewDto> fsm(@PathVariable UUID id) {
        return ApiResult.ok(ResearchFsmViewDto.from(query.fsm(id)));
    }

    @GetMapping("/projects/{id}/records/audit")
    @Operation(operationId = "getResearchRecordsAudit", summary = "入庫完整率（API-RP-19）",
            description = "R1～R14 各類記錄的筆數（PRD §5.1.8）與 missing（筆數為 0 且不屬 R10 自癒嘗試、R12 SCR 者）。JDBC 唯讀。VIEWER 以上可讀。")
    public ApiResult<RecordsAuditDto> recordsAudit(@PathVariable UUID id) {
        return ApiResult.ok(RecordsAuditDto.from(query.recordsAudit(id)));
    }

    @GetMapping("/allowlist")
    @Operation(operationId = "listResearchAllowlist", summary = "研究來源 allowlist（API-RP-22）",
            description = "有效清單的條目：環境變數基底（source=ENV；沒有 id 與 layer）加 ADMIN 新增的條目（source=ADMIN）。轉 Bridge GET /research/allowlist。"
                    + "VIEWER 以上可讀。")
    public ApiResult<List<AllowlistEntryDto>> allowlist() {
        return ApiResult.ok(query.allowlist().stream().map(AllowlistEntryDto::from).toList());
    }

    @GetMapping("/watch-sources")
    @Operation(operationId = "listResearchWatchSources", summary = "自我進化追蹤來源清單（API-RP-29；研究來源單一化）",
            description = "研究來源設定的第二層（網址層）：全部追蹤來源（含已停用；依 slug 位元組序）。hostAllowed＝host 是否仍在當前有效網域清單（停用網域後追蹤來源列不動，"
                    + "只是 hostAllowed 轉假）。轉 Bridge GET /research/watch-sources。VIEWER 以上可讀。")
    public ApiResult<List<WatchSourceDto>> watchSources() {
        return ApiResult.ok(registry.watchSources().stream().map(WatchSourceDto::from).toList());
    }

    @PostMapping("/watch-sources")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(operationId = "addResearchWatchSource", summary = "新增自我進化追蹤來源（API-RP-29；僅 ADMIN）",
            description = "本文 {slug, url, kind, extract, layer, expand?}（expand 缺省或 null＝無；物件須恰含 mode、prefix、max）；本文含任何其他鍵（含 addedBy）＝400 unknown_field。"
                    + "輸入閘（400，errors[] 一次全列；規則名 invalid_slug｜invalid_url｜invalid_kind｜invalid_layer｜invalid_extract｜invalid_expand）先於 Bridge；url 原樣判定、"
                    + "不做任何正規化（大寫 host、顯式 :443、IP 字面一律拒絕，請自行改寫後重送）。單一閘：host 須在當前有效網域清單，否則 422 host_not_allowed（details.host）；"
                    + "同 slug 已存在（含已停用者；slug 永不重用）＝409 watch_source_exists（details.slug）；假設寫入成功後的登記快照超過 24576 位元組＝422 registry_too_large（零寫入）。"
                    + "成功 201 回條目，並以 AuditTrail 標註（audit_log 的 entity_type=research_watch_source、entity_id＝slug；不寫 research_events：全域資源）。新增後不會自動生效——"
                    + "須再呼叫 POST /api/v1/si/research-registry/sync 把登記簽成稽核檔、待自我進化入帳。" + WRITE_FLOW,
            requestBody = @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
                    content = @Content(schema = @Schema(implementation = ResearchWatchSourceRequest.class))))
    public ApiResult<WatchSourceDto> addWatchSource(@RequestBody Map<String, Object> request, Authentication authentication) {
        return ApiResult.created(WatchSourceDto.from(registry.addWatchSource(caller(authentication), request)));
    }

    @PatchMapping("/watch-sources/{slug}")
    @Operation(operationId = "updateResearchWatchSource", summary = "停用／重新啟用追蹤來源（API-RP-29；僅 ADMIN）",
            description = "只准改 enabled（不可刪除；slug 永不重用）：本文含 enabled 以外的任何鍵＝422 invalid_request、條目不變。停用人取 JWT subject；重新啟用清空停用欄，"
                    + "且 host 須仍在當前有效網域清單（否則 422 host_not_allowed）。slug 不存在＝404 research_not_found（details.slug）。成功 200 回條目，並以 AuditTrail 標註"
                    + "（entity_type=research_watch_source）。" + WRITE_FLOW,
            requestBody = @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
                    content = @Content(schema = @Schema(implementation = ResearchAllowlistPatchRequest.class))))
    public ApiResult<WatchSourceDto> updateWatchSource(@Parameter(description = "追蹤來源 slug") @PathVariable String slug,
                                                       @RequestBody Map<String, Object> body, Authentication authentication) {
        return ApiResult.ok(WatchSourceDto.from(registry.patchWatchSource(caller(authentication), slug, body)));
    }

    // ── 寫入（OPERATOR 以上；ADMIN 專屬者見各端點）──────────────────────────────────────────

    @PostMapping("/projects")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(operationId = "createResearchProject", summary = "建立研究專案（API-RP-03；OPERATOR 以上）",
            description = "輸入閘（400 invalid_request；errors[] 與 details.violations[{field,rule,message}] 一次全列；industry 為真而 Web 層未啟用＝400 layer_unavailable）→ "
                    + "配 id → Bridge POST /research/projects（Bridge 先在單一交易寫專案列、事件 seq=1、ISSUE_SCOPE 產物，再建工作區與外環 FSM 鍵）→ 自 DB 重讀。"
                    + "201 回 ResearchProjectDetail（flowStep=topic、flowPhase=INGESTED）；slug 已被未封存專案使用＝409 slug_in_use；檔案或建鍵失敗＝專案列照建、"
                    + "flowStatus=FAILED 且 flowDetail=init_failed:<步驟>（以 reinit 補建）。" + WRITE_FLOW)
    public ApiResult<ResearchProjectDetail> create(@RequestBody ResearchCreateRequest request, Authentication authentication) {
        return ApiResult.created(ResearchProjectDetail.from(command.create(caller(authentication), request.toInput())));
    }

    @PutMapping("/projects/{id}/prd")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(operationId = "savePrdVersion", summary = "存 PRD 新版（人工編輯；API-RP-09；OPERATOR 以上）",
            description = "樂觀鎖：baseVersion 須是目前 head 版號（否則 409 prd_version_conflict，details.headVersion）；content ≤1 MiB、UTF-8、無 NUL。成功 201 回新版本"
                    + "（authorKind=HUMAN、author＝JWT subject；不含 content），flowPhase 回 DRAFTING（人改過須重審）。Gate 0 之後＝409 spec_frozen。" + WRITE_FLOW)
    public ApiResult<PrdVersionDto> savePrd(@PathVariable UUID id, @RequestBody ResearchSavePrdRequest request, Authentication authentication) {
        return ApiResult.created(PrdVersionDto.withoutContent(command.savePrd(caller(authentication), id, request.toInput())));
    }

    @PostMapping("/projects/{id}/stages/{stage}")
    @ResponseStatus(HttpStatus.ACCEPTED)
    @Operation(operationId = "startResearchStage", summary = "啟動階段（API-RP-11；OPERATOR 以上）",
            description = "stage＝research｜draft｜review｜revise｜iterate｜tcs-draft（tcs-draft 自 P1 起可用；前置：分流成功、已有拆解、內環鍵已採納基線）；本文選填 {auto, note, afterEscalation}。前置條件由 Bridge 驗，"
                    + "未滿足＝409 stage_conflict（details.unmet 逐條列出 rule 與說明）／fsm_state_conflict／escalated／spec_frozen；同專案已有進行中的 stage 或全站並行上限"
                    + "＝409 stage_conflict（不排隊、不重試）；DB 阻塞＝503 db_blocked。not_implemented（Bridge 端點本體尚未實作時回 502）自 P1 起 Bridge 無觸發者，保留供 P2 骨架（D-111）。成功 202 回 {stageRunId, flowPhase, flowStatus}；"
                    + "進度看 SSE research.run 與 research.step。" + WRITE_FLOW)
    public ApiResult<StageStartedDto> startStage(
            @PathVariable UUID id,
            @Parameter(description = "階段", schema = @Schema(allowableValues = {"research", "draft", "review", "revise", "iterate", "tcs-draft"}))
            @PathVariable String stage,
            @RequestBody(required = false) ResearchStageRequest request, Authentication authentication) {
        ResearchStageRequest body = request == null ? new ResearchStageRequest(null, null, null) : request;
        Map<String, Object> started = command.startStage(caller(authentication), id, stage, body.toInput());
        return new ApiResult<>(HttpStatus.ACCEPTED.value(), "success", StageStartedDto.from(started), OffsetDateTime.now(), MDC.get("traceId"));
    }

    @PostMapping("/projects/{id}/approve")
    @Operation(operationId = "approveResearchBaseline", summary = "Gate 0：核准 PRD 並凍結基線（API-RP-12；僅 ADMIN）",
            description = "本文 {prdVersion（整數）, expectedDigests（至少一鍵）, reason?}；approver 取 JWT subject（本文型別沒有 approver 欄，多帶的被忽略）。"
                    + "expectedDigests 只比對送來的鍵（D-72）：一個鍵都沒送＝422 missing_digests（盲核；由輸入閘回、零 Bridge 請求）；其餘檔案的摘要由 Bridge 於凍結當下自工作區計算並記入凍結記錄。"
                    + "Bridge 檢查序：權杖→prdVersion 為 head 且有通過的審查輪（409 review_not_passed）→送來的摘要與現檔逐鍵比對（422 digest_mismatch，"
                    + "details.files[{key,expected,current}]）→FSM 現態為 HUMAN_PENDING 且無 ESCALATION（409 fsm_state_conflict／escalated）→有重試史才先走 "
                    + "SPEC_REGRESSION_CHECK→spec-frozen。成功 200 回 {gateDecisionId, stage, specDocDigests, fsmState}；非冪等：第二次＝409 fsm_state_conflict。" + WRITE_FLOW)
    public ApiResult<ApproveResultDto> approve(@PathVariable UUID id, @RequestBody ResearchApproveRequest request, Authentication authentication) {
        return ApiResult.ok(ApproveResultDto.from(command.approve(caller(authentication), id, request.toInput())));
    }

    @PostMapping("/projects/{id}/return")
    @Operation(operationId = "returnResearchPrd", summary = "退回修改（API-RP-21；僅 ADMIN）",
            description = "本文 {reason}（必填，1～500 字）。Bridge 呼叫 gate SCG_VALIDATION FAIL：FSM 維持 HUMAN_PENDING、retry_count＋1（與自動 FAIL 共用 3 次預算，第 3 次＝ESCALATION）；"
                    + "PRD 回可編輯，之後的重審 triggerKind=POST_HUMAN。成功 200 回 {gateDecisionId, fsmRetryCount, escalated}。" + WRITE_FLOW)
    public ApiResult<ReturnResultDto> returnPrd(@PathVariable UUID id, @RequestBody ResearchReturnRequest request, Authentication authentication) {
        return ApiResult.ok(ReturnResultDto.from(command.returnPrd(caller(authentication), id, request.reason())));
    }

    @PostMapping("/projects/{id}/cancel")
    @Operation(operationId = "cancelResearchStage", summary = "取消進行中的 stage（API-RP-18；OPERATOR 以上）",
            description = "停止進行中的 stage run（被取消的審查 run 不寫審查輪列、不佔 round_no；D-57）；沒有進行中的 stage＝冪等。200 回開放物件（Bridge 本文的 camelCase 轉換；"
                    + "前端不讀內容）。" + WRITE_FLOW)
    public ApiResult<Map<String, Object>> cancel(@PathVariable UUID id, Authentication authentication) {
        return ApiResult.ok(open(command.action(caller(authentication), id, "cancel")));
    }

    @PostMapping("/projects/{id}/reconcile")
    @Operation(operationId = "reconcileResearch", summary = "對帳（API-RP-18；OPERATOR 以上）",
            description = "只報告、不修復：回 {consistent, checks[{name, status(ok｜drift｜NOT_EVALUABLE｜pending_correction), drift?}]}，結果追加 research_events（research.reconcile）。" + WRITE_FLOW)
    public ApiResult<ReconcileResultDto> reconcile(@PathVariable UUID id, Authentication authentication) {
        return ApiResult.ok(ReconcileResultDto.from(command.action(caller(authentication), id, "reconcile")));
    }

    @PostMapping("/projects/{id}/archive")
    @Operation(operationId = "archiveResearchProject", summary = "封存研究專案（軟刪除；API-RP-18；OPERATOR 以上）",
            description = "軟刪除：封存後預設清單不含該專案（archived=true 可見），30 天內可 restore。有進行中的 stage＝409 stage_conflict。200 回開放物件。" + WRITE_FLOW)
    public ApiResult<Map<String, Object>> archive(@PathVariable UUID id, Authentication authentication) {
        return ApiResult.ok(open(command.action(caller(authentication), id, "archive")));
    }

    @PostMapping("/projects/{id}/restore")
    @Operation(operationId = "restoreResearchProject", summary = "復原已封存的研究專案（API-RP-18；OPERATOR 以上）",
            description = "把已封存的專案移回預設清單。200 回開放物件。" + WRITE_FLOW)
    public ApiResult<Map<String, Object>> restore(@PathVariable UUID id, Authentication authentication) {
        return ApiResult.ok(open(command.action(caller(authentication), id, "restore")));
    }

    @PostMapping("/projects/{id}/reinit")
    @Operation(operationId = "reinitResearchProject", summary = "重試初始化／換世代（API-RP-20；OPERATOR 以上，換世代僅 ADMIN）",
            description = "本文可省略。無 generation＝重試（冪等；flowStatus=FAILED 時可呼叫：初始化失敗〔flowDetail 以 init_failed: 起頭〕補建缺的目錄、檔案與外環鍵，"
                    + "stage 失敗或取消〔flowDetail 為失敗原因或 cancelled〕以 FSM 重衍生狀態、清掉失敗標記，D-81；其餘＝409 stage_conflict，"
                    + "details.flowStatus／flowDetail，零寫入）。generation=next＝換世代（D-60）：放棄這一把外環鍵、另開新世代鍵取得全新 3 次預算；"
                    + "reason 必填（1～500 字；缺、空白、超長＝422 invalid_request）；FSM 現態須為 ESCALATION*（否則 409 fsm_state_conflict，details.current_state）。"
                    + "角色：換世代僅 ADMIN——VIEWER＝403 ACCESS_DENIED（授權鏈）、OPERATOR＝403 research_write_forbidden（服務層入口，Bridge 請求數 0）。"
                    + "200 回 {flow, fsmProject?, fsmGeneration?, gateDecisionId?}（後三者只有換世代有）。" + WRITE_FLOW)
    public ApiResult<ReinitResultDto> reinit(@PathVariable UUID id, @RequestBody(required = false) ResearchReinitRequest request,
                                             Authentication authentication) {
        ResearchReinitRequest body = request == null ? new ResearchReinitRequest(null, null) : request;
        return ApiResult.ok(ReinitResultDto.from(command.reinit(caller(authentication), id, body.toInput())));
    }

    @PostMapping("/allowlist")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(operationId = "addResearchAllowlistEntry", summary = "新增 allowlist 條目（API-RP-22；僅 ADMIN）",
            description = "本文 {listKind, host, layer, purpose, tosNote, minIntervalSeconds, tosAcknowledged}；minIntervalSeconds 建立時決定、建立後不可改。"
                    + "Reddit 網域（reddit.com、*.reddit.com、redd.it）須 tosAcknowledged=true（否則 422 terms_ack_required）；同 listKind 與 host 已有條目＝409 allowlist_exists。"
                    + "成功 201 回條目，並以 AuditTrail 標註（audit_log 的 entity_type=research_allowlist、entity_id＝條目 id；不寫 research_events：allowlist 是全域資源，D-52、D-62(1)）。"
                    + WRITE_FLOW)
    public ApiResult<AllowlistEntryDto> addAllowlistEntry(@RequestBody ResearchAllowlistRequest request, Authentication authentication) {
        return ApiResult.created(AllowlistEntryDto.from(command.addAllowlistEntry(caller(authentication), request.toInput())));
    }

    @PatchMapping("/allowlist/{id}")
    @Operation(operationId = "updateResearchAllowlistEntry", summary = "停用／啟用 allowlist 條目（API-RP-22；僅 ADMIN）",
            description = "只准改 enabled（不可刪除條目）：本文含 enabled 以外的任何鍵（含 minIntervalSeconds）＝422 invalid_request、條目不變。停用人取 JWT subject。"
                    + "條目不存在＝404 research_not_found。成功 200 回條目，並以 AuditTrail 標註（entity_type=research_allowlist）。" + WRITE_FLOW,
            requestBody = @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
                    content = @Content(schema = @Schema(implementation = ResearchAllowlistPatchRequest.class))))
    public ApiResult<AllowlistEntryDto> updateAllowlistEntry(@Parameter(description = "條目 id（UUID）") @PathVariable String id,
                                                             @RequestBody Map<String, Object> body, Authentication authentication) {
        return ApiResult.ok(AllowlistEntryDto.from(command.patchAllowlistEntry(caller(authentication), id, body)));
    }

    // ── 內部 ──────────────────────────────────────────────────────────────────────────────

    private static Caller caller(Authentication authentication) {
        boolean admin = authentication != null && authentication.getAuthorities().stream().map(GrantedAuthority::getAuthority)
                .anyMatch(("ROLE_" + Role.ADMIN.name())::equals);
        return new Caller(authentication == null ? null : authentication.getName(), admin);
    }

    /** Bridge 的開放物件本文（取消、封存、復原）→ 鍵轉 camelCase 的物件（值不動；前端不讀內容）。 */
    @SuppressWarnings("unchecked")
    private static Map<String, Object> open(Map<String, Object> body) {
        return (Map<String, Object>) SiKeyNames.camelKeys(body);
    }
}
