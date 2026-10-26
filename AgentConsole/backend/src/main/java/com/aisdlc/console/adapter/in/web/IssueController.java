package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.IssueExportResponse;
import com.aisdlc.console.adapter.in.web.dto.IssuePriorityRequest;
import com.aisdlc.console.adapter.in.web.dto.IssuePriorityResponse;
import com.aisdlc.console.application.port.in.IssuePriorityUseCase;
import com.aisdlc.console.application.port.in.IssueQueryUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.util.Map;

/**
 * 議題中心的端點（TCS-IssueCenter-20261027 §C4；API-IC-01～04）：兩個唯讀 {@code GET}（議題清單、單筆）加兩個僅 ADMIN 的優先順序寫入
 * （{@code PUT}、{@code DELETE}）。<b>Console 不寫帳本</b>：議題的歸類、排序、中文對照全在根層（Bridge 原樣轉遞），本類別只多加 Console 自有的優先順序。
 * 名稱不符 {@code Si*Controller}，所以不受 SelfImproving 那組「七個 GET、四個 POST、沒有 PUT／DELETE」的計數鎖；本類別是議題中心<b>唯一</b>帶 PUT、DELETE
 * 映射的類別，各恰一個（ArchUnit 鎖住）。
 *
 * <p>權限：GET＝VIEWER 以上（無有效 JWT＝401）；PUT、DELETE＝僅 ADMIN（{@code SecurityConfig}：OPERATOR、VIEWER＝403 {@code ACCESS_DENIED}），
 * 兩者都不要求 {@code console.si.deciders} 名單（優先順序不是帳本決定）。寫入端點的成功與被拒、失敗都由 {@code AuditLoggingFilter} 在
 * {@code console.audit_log} 留一列。GET 回應的 {@code data} 是 Bridge 的匯出物件原樣轉遞（欄名只經 snake_case→camelCase，值不動）；
 * 失敗一律<b>沒有 {@code data}</b>（不回空表、不回部分資料）。
 */
@RestController
@RequestMapping("/api/v1/issues")
@Tag(name = "議題中心（Issue Center）", description = "議題清單與單筆（唯讀，Bridge 原樣轉遞＋Console 自有的優先順序）；優先順序的設定與清除（僅 ADMIN；"
        + "契約檔 API_Contract_IssueCenter.md）")
public class IssueController {

    private static final String UPSTREAM = "失敗一律沒有 data：Bridge 的 503 si_unavailable→503（details.cause、details.detail 逐字）、連線失敗或 Bridge 的其他 5xx→502、"
            + "讀取逾時（20 秒、不重試）→504；順位表讀取失敗→5xx。";

    private final IssueQueryUseCase query;
    private final IssuePriorityUseCase priority;

    public IssueController(IssueQueryUseCase query, IssuePriorityUseCase priority) {
        this.query = query;
        this.priority = priority;
    }

    @GetMapping
    @Operation(operationId = "getIssues", summary = "議題清單（唯讀；議題中心）",
            description = "Bridge GET /si/issues（根層 si export --kind issues）的原樣轉遞，每筆另有 Console 自有的 priority、priorityNote"
                    + "（僅 rankable 為真且有順位列才有值，其餘 null）。回應含 legend（狀態、結果、來源、嚴重度的中文與說明）與 summary（整本帳的計數，"
                    + "不受篩選、游標影響）。status、source 是中文篩選別名（逗號取聯集、兩者取交集），原樣轉給根層判（含空字串；不認得的值＝503 si_unavailable，"
                    + "不是 422）。每個請求恰一次 Bridge 呼叫與一次順位表讀取（連線 2 秒、讀取 20 秒、不重試），不快取。" + UPSTREAM + "VIEWER 以上可讀。")
    public ApiResult<IssueExportResponse> issues(
            @Parameter(description = "狀態篩選（選填；七個狀態名或分頁名「待處理」，逗號分隔）。值以 64 字元、不以 - 起頭、不含控制字元為限，不合 → 422（引擎拒絕此請求）")
            @RequestParam(required = false) String status,
            @Parameter(description = "來源篩選（選填；四個來源名，逗號分隔）。規則同 status")
            @RequestParam(required = false) String source,
            @Parameter(description = "游標（選填；整數 ≥0）：只回游標嚴格大於它的項目；取自上一頁回應的 nextSince。不合 → 400（不觸及 Bridge）",
                    schema = @Schema(type = "integer", format = "int32", minimum = "0"))
            @RequestParam(required = false) Integer since,
            @Parameter(description = "頁大小（選填；整數 ≥1）：不合 → 400；超過根層協定參數檔的上限時，CLI 失敗而回 503 si_unavailable（cause=nonzero_rc）",
                    schema = @Schema(type = "integer", format = "int32", minimum = "1"))
            @RequestParam(required = false) Integer limit) {
        return ApiResult.ok(IssueExportResponse.from(query.list(since, limit, status, source)));
    }

    @GetMapping("/{id}")
    @Operation(operationId = "getIssue", summary = "單筆議題（唯讀；議題中心）",
            description = "Bridge GET /si/issues/{id} 的原樣轉遞（items 恰一筆，含 raw、timeline、links 與 priority、priorityNote；沒有 legend、summary）。"
                    + "id 原樣嚴格 percent-encode 成單一路徑段後交給 Bridge；格式（OBS-SI-<三位以上數字>、PROP-SI-<三位以上數字>、DEF-<數字>-<數字>）的"
                    + "單一真相在 Bridge：不合 → 422（details.bridgeReason=invalid_request）。格式合法而查無 → 404（reason si_not_found，訊息「查無此議題」，"
                    + "details.id）。不收查詢參數。" + UPSTREAM + "VIEWER 以上可讀。")
    public ApiResult<IssueExportResponse> issue(@Parameter(description = "議題編號（例：PROP-SI-004）") @PathVariable String id) {
        return ApiResult.ok(IssueExportResponse.from(query.one(id)));
    }

    @PutMapping("/{id}/priority")
    @Operation(operationId = "putIssuePriority", summary = "設定議題的優先順序（議題中心；僅 ADMIN）",
            description = "設定或更新該議題的順位與備註（Console 自有資料；不寫帳本，也不要求 console.si.deciders 名單）。驗證順序固定：角色（僅 ADMIN；否則 403 "
                    + "ACCESS_DENIED）→ 本文不是 JSON 物件（400 MALFORMED_REQUEST_BODY）→ 輸入閘（422 invalid_request；details.violations[{field,message}] "
                    + "一次全列，Bridge 零呼叫）→ 取該議題（Bridge 失敗 503／502／504；查無 404 si_not_found）→ 議題狀態不可排（409 issue_not_rankable；"
                    + "details.id、details.status）→ UPSERT。任一前序失敗都零寫入。成功 200：寫入的那一列。後者生效（setBy、setAt 為後者）。",
            requestBody = @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
                    content = @Content(schema = @Schema(implementation = IssuePriorityRequest.class))))
    public ApiResult<IssuePriorityResponse> putPriority(@Parameter(description = "議題編號（例：PROP-SI-004）") @PathVariable String id,
                                                        @RequestBody Map<String, Object> body, Principal principal) {
        return ApiResult.ok(IssuePriorityResponse.from(priority.set(principal.getName(), id, body)));
    }

    @DeleteMapping("/{id}/priority")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(operationId = "deleteIssuePriority", summary = "清除議題的優先順序（議題中心；僅 ADMIN）",
            description = "刪除該議題的順位列。冪等：列不存在也是 204。不呼叫 Bridge，所以議題已結案或已不存在時仍清得掉遺留的列。驗證順序固定：角色（僅 ADMIN；否則 403 "
                    + "ACCESS_DENIED）→ id 格式（422 invalid_request）→ 刪除。沒有本文。")
    public void deletePriority(@Parameter(description = "議題編號（例：PROP-SI-004）") @PathVariable String id) {
        priority.clear(id);
    }
}
