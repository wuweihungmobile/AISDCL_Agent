package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.SiKeyNames;
import com.aisdlc.console.adapter.in.web.dto.research.DecompositionDto;
import com.aisdlc.console.adapter.in.web.dto.research.DecompositionSignoffRequest;
import com.aisdlc.console.adapter.in.web.dto.research.DecompositionTriggerRequest;
import com.aisdlc.console.adapter.in.web.dto.research.RouteConfirmRequest;
import com.aisdlc.console.adapter.in.web.dto.research.RouteDecisionDto;
import com.aisdlc.console.adapter.in.web.dto.research.RoutePreviewRequest;
import com.aisdlc.console.adapter.in.web.dto.research.RoutePreviewResult;
import com.aisdlc.console.adapter.in.web.dto.research.ScrDto;
import com.aisdlc.console.adapter.in.web.dto.research.ScrOpenRequest;
import com.aisdlc.console.application.port.in.ResearchCommandUseCase.Caller;
import com.aisdlc.console.application.port.in.ResearchDecompositionUseCase;
import com.aisdlc.console.application.port.in.ResearchRouteUseCase;
import com.aisdlc.console.application.port.in.ResearchScrUseCase;
import com.aisdlc.console.domain.model.auth.Role;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * 研發工作流 P1 的 REST 端點：分流（API-RP-14）、規格變更請求（API-RP-15）、任務拆解（API-RP-16）（API 契約 API_Contract_ResearchToPRD §1.1；PKG-API-P1）。獨立於
 * {@link ResearchController}（縮小單檔爆炸面）。<b>console-api 對 {@code console.research_*} 零寫入</b>：GET 走 JDBC 唯讀；寫入只經 Bridge、恰一次呼叫、不重試
 * （分流確認與拆解觸發的讀逾時 330 秒，其餘 30 秒）；console-api 只寫自己的 {@code projects} 列與 {@code audit_log}。
 *
 * <p>權限：GET＝VIEWER 以上；POST 預設 OPERATOR 以上；<b>僅 ADMIN</b>：{@code POST …/route}、{@code POST …/scr/{scrNo}/apply}（{@code SecurityConfig} 逐條規則，
 * 置於通用規則之前）。approver、requestedBy 一律取 JWT subject，請求本文沒有這些欄位。失敗序同 {@link ResearchController}（401→403→503→400／422→404→409→502／504）。
 */
@RestController
@RequestMapping("/api/v1/research/projects/{id}")
@Tag(name = "研發工作流（ResearchToPRD）", description = "研究→證據→PRD→四方審查→Gate 0 的 P0 端點，與 P1 的分流、規格變更請求與任務拆解端點（API-RP-14～16）；契約檔 API_Contract_ResearchToPRD.md")
public class ResearchRouteController {

    private static final String WRITE_FLOW = "失敗序：研究寫入權杖未設（503 research_write_disabled）→ 輸入閘（400／422 invalid_request；details.violations[{field,rule,message}] 一次全列，"
            + "errors[] 同內容）→ 專案不存在（404 research_not_found）→ Bridge 恰一次呼叫（連線 2 秒、讀取 30 秒〔分流確認與拆解觸發 330 秒〕、不重試；Bridge 的 409／422 reason 與 details 逐字透傳，"
            + "連線失敗 502 bridge_unreachable、讀取逾時 504 bridge_timeout）。操作人（approver、requestedBy）一律取 JWT subject，請求本文沒有這些欄位。";

    private final ResearchRouteUseCase route;
    private final ResearchScrUseCase scr;
    private final ResearchDecompositionUseCase decomposition;

    public ResearchRouteController(ResearchRouteUseCase route, ResearchScrUseCase scr, ResearchDecompositionUseCase decomposition) {
        this.route = route;
        this.scr = scr;
        this.decomposition = decomposition;
    }

    // ── 分流（API-RP-14）──────────────────────────────────────────────────────────────────

    @PostMapping("/route/preview")
    @Operation(operationId = "previewResearchRoute", summary = "分流預演（API-RP-14；OPERATOR 以上；零副作用）",
            description = "本文＝軌道 A（targetModule、branchName、baseRef）或軌道 B（projectName、stackTemplate、repoName、owner、visibility、createGithub、ci、dockerCompose）；"
                    + "分流與 PRD target_scope 不同須附 scopeDiffersReason（缺＝422 invalid_request，規則 scope_differs_reason_required）。回與確認共用的動作清單（動作、目標、"
                    + "是否觸及外部系統）、Bridge 導出的 executionPath／implFsmProject／implStateDir 與警示。前後 git 狀態、目標目錄與資料庫（所有 research_* 表與 projects）皆不變（D-108）；"
                    + "部署不支援回 422 route_unsupported_in_deployment（details.missing[]）。" + WRITE_FLOW)
    public ApiResult<RoutePreviewResult> preview(@Parameter(description = "研究專案 id（UUID）") @PathVariable UUID id, @RequestBody RoutePreviewRequest request,
                                                 Authentication authentication) {
        return ApiResult.ok(RoutePreviewResult.from(route.preview(caller(authentication), id, request.toInput())));
    }

    @PostMapping("/route")
    @Operation(operationId = "routeResearchProject", summary = "確認分流並同步執行（API-RP-14；僅 ADMIN）",
            description = "步驟：輸入閘與 route_conflict 預檢（409，零 Bridge 請求）→ Bridge 預演取得導出路徑 → 先建 Console projects 列（DRAFT、signed_off=false、sdd_project＝內環鍵；"
                    + "短交易先 commit）→ Bridge :route（同步，D-105；讀取逾時 330 秒）。成功 200 回 RouteDecisionDto（含 publishedDocs 與步驟）；失敗（502 route_step_failed、逾時、不可達、Bridge 拒絕）"
                    + "＝projects 列標 ARCHIVED（不刪列）＋稽核＋通知 Bridge :route-compensated，不自動 git clean、stash、刪目錄。approver 取 JWT subject；GitHub token 取後端設定鍵 "
                    + "research.github_token，僅軌道 B 且 createGithub=true 時放進該次 Bridge 請求，不入任何回應、日誌與稽核。" + WRITE_FLOW)
    public ApiResult<RouteDecisionDto> confirm(@PathVariable UUID id, @RequestBody RouteConfirmRequest request, Authentication authentication) {
        return ApiResult.ok(RouteDecisionDto.from(route.confirm(caller(authentication), id, request.toInput())));
    }

    @GetMapping("/route")
    @Operation(operationId = "getResearchRoute", summary = "最新一筆分流（含步驟；API-RP-14）",
            description = "JDBC 唯讀。尚無分流回 200 且 data 為 null（D-106，不是 404）。研究專案不存在＝404 research_not_found。VIEWER 以上可讀。")
    public ApiResult<RouteDecisionDto> getRoute(@PathVariable UUID id) {
        return ApiResult.ok(route.current(id).map(RouteDecisionDto::from).orElse(null));
    }

    // ── 規格變更請求（API-RP-15）──────────────────────────────────────────────────────────

    @PostMapping("/scr")
    @ResponseStatus(HttpStatus.ACCEPTED)
    @Operation(operationId = "openResearchScr", summary = "發起規格變更請求（API-RP-15；OPERATOR 以上）",
            description = "本文 {kind（MINOR｜MAJOR）, sourceKind（HUMAN｜REVIEW_FINDING｜SCG4｜HEALING_FAILED）, reason（1～500 字）, reasonClass?, affectedSections?}。"
                    + "console-api 先停進行中的 run（既有 stop 用例；HEALING_FAILED 例外：只產生恢復指令）再呼 Bridge :scr；同一研究專案的 MINOR 至多 2 次（第 3 次 409 scr_limit）。"
                    + "202 回 Bridge 本文（camelCase）：MINOR＝{scrNo, status}、MAJOR＝{scrNo, successorResearchId}、HEALING_FAILED＝{scrNo, recovery{target, powershell, posix}}。" + WRITE_FLOW)
    public ApiResult<Map<String, Object>> openScr(@PathVariable UUID id, @RequestBody ScrOpenRequest request, Authentication authentication) {
        return new ApiResult<>(HttpStatus.ACCEPTED.value(), "success", open(scr.open(caller(authentication), id, request.toInput())), OffsetDateTime.now(),
                MDC.get("traceId"));
    }

    @GetMapping("/scr")
    @Operation(operationId = "listResearchScr", summary = "規格變更請求清單（API-RP-15）",
            description = "依 scrNo 遞增；JDBC 唯讀。研究專案不存在＝404 research_not_found。VIEWER 以上可讀。")
    public ApiResult<List<ScrDto>> listScr(@PathVariable UUID id) {
        return ApiResult.ok(scr.list(id).stream().map(ScrDto::from).toList());
    }

    @PostMapping("/scr/{scrNo}/apply")
    @Operation(operationId = "applyResearchScr", summary = "套用 MINOR SCR 的內環收尾（API-RP-15；僅 ADMIN）",
            description = "MINOR SCR 於 Gate-0-SCR<k> 核准後的內環收尾序列失敗或阻塞時，ADMIN 以本端點重試（Bridge :scr-apply）。200 回 Bridge 本文（camelCase）："
                    + "{scrNo, status（APPLIED｜BLOCKED）, implFsmActions[], flow}。SCR 非 APPROVED 或內環現態不在矩陣內＝409 fsm_state_conflict。" + WRITE_FLOW)
    public ApiResult<Map<String, Object>> applyScr(@PathVariable UUID id, @Parameter(description = "SCR 序號（整數 ≥1）") @PathVariable int scrNo,
                                                   Authentication authentication) {
        return ApiResult.ok(open(scr.apply(caller(authentication), id, scrNo)));
    }

    // ── 拆解（API-RP-16）──────────────────────────────────────────────────────────────────

    @GetMapping("/decomposition")
    @Operation(operationId = "getResearchDecomposition", summary = "有效拆解（API-RP-16）",
            description = "有效拆解＝已簽核且 PRD 摘要仍符合凍結摘要的最新一筆，否則最新一筆（含 DRAFTED、STALE）。回覆蓋對映（total、covered、uncovered[]；取 Bridge 寫入的內容，"
                    + "console-api 不重算）、豁免、stale 旗標與 TCS 發佈資訊。尚無拆解回 200 且 data 為 null（D-120）。JDBC 唯讀。VIEWER 以上可讀。")
    public ApiResult<DecompositionDto> getDecomposition(@PathVariable UUID id) {
        return ApiResult.ok(decomposition.current(id).map(DecompositionDto::from).orElse(null));
    }

    @PostMapping("/decomposition")
    @Operation(operationId = "triggerResearchDecomposition", summary = "觸發任務拆解（API-RP-16；OPERATOR 以上）",
            description = "本文可省略；選填 scope.usIds（只拆指定的 US）。Bridge :decompose 同步執行（逐 US 呼叫既有拆解服務，covers_ac 由呼叫綁定的 AC 確定性賦值；讀取逾時 330 秒、不重試）。"
                    + "200 回 Bridge 本文（camelCase）：{decompositionId, status（DRAFTED）, tasksCount, coverage{total, covered, uncovered[]}}；有界閘（步驟 ≤24、無環、prompt 非空）不過＝"
                    + "422 invalid_request（details.violations[].rule），不截斷。" + WRITE_FLOW)
    public ApiResult<Map<String, Object>> triggerDecomposition(@PathVariable UUID id, @RequestBody(required = false) DecompositionTriggerRequest request,
                                                               Authentication authentication) {
        List<String> usIds = request == null ? null : request.usIds();
        return ApiResult.ok(open(decomposition.trigger(caller(authentication), id, usIds)));
    }

    @PostMapping("/decomposition/signoff")
    @Operation(operationId = "signoffResearchDecomposition", summary = "簽核拆解（API-RP-16；OPERATOR 以上）",
            description = "本文可省略；選填 waivers[{ac, reason}]。approver 取 JWT subject（憑證無帳號名＝400；本文帶 approver 被忽略）。先走既有 import／signoff 路徑把拆解落為正式專案的目標與任務"
                    + "（全部 signedOff；專案層一併簽核），再呼 Bridge :decomposition-signoff（一次寫 SIGNED_OFF 與 import_record_id，D-113）。覆蓋未清零且無豁免＝"
                    + "422 invalid_request（violations[{field:coverage, rule:uncovered_ac}]）；PRD 摘要已變＝409 decomposition_stale。200 回簽核後的有效拆解。" + WRITE_FLOW)
    public ApiResult<DecompositionDto> signoffDecomposition(@PathVariable UUID id, @RequestBody(required = false) DecompositionSignoffRequest request,
                                                            Authentication authentication) {
        return ApiResult.ok(DecompositionDto.from(decomposition.signoff(caller(authentication), id, request == null ? null : request.toInput())));
    }

    // ── 內部 ──────────────────────────────────────────────────────────────────────────────

    private static Caller caller(Authentication authentication) {
        boolean admin = authentication != null && authentication.getAuthorities().stream().map(GrantedAuthority::getAuthority)
                .anyMatch(("ROLE_" + Role.ADMIN.name())::equals);
        return new Caller(authentication == null ? null : authentication.getName(), admin);
    }

    /** Bridge 的本文（snake_case）→ 鍵轉 camelCase 的物件（值不動）。 */
    @SuppressWarnings("unchecked")
    private static Map<String, Object> open(Map<String, Object> body) {
        return (Map<String, Object>) SiKeyNames.camelKeys(body);
    }
}
