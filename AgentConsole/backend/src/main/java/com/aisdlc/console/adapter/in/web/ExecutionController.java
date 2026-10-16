package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.CheckpointResponse;
import com.aisdlc.console.adapter.in.web.dto.DagResponse;
import com.aisdlc.console.adapter.in.web.dto.ExecutionRunDetailResponse;
import com.aisdlc.console.adapter.in.web.dto.ExecutionRunResponse;
import com.aisdlc.console.adapter.in.web.dto.ExecutionRunSummaryResponse;
import com.aisdlc.console.adapter.in.web.dto.ExecutionStepResponse;
import com.aisdlc.console.adapter.in.web.dto.PageData;
import com.aisdlc.console.adapter.in.web.dto.ReviewRequestBody;
import com.aisdlc.console.adapter.in.web.dto.StartExecutionRequest;
import com.aisdlc.console.application.port.in.ExecuteProjectUseCase;
import com.aisdlc.console.application.port.in.ExecutionControlUseCase;
import com.aisdlc.console.application.port.in.ExecutionQueryUseCase;
import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.RunListQuery;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.execution.RunStatus;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.headers.Header;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

/**
 * 專案執行端點（Phase 4；契約 §1.2）。讀取：任何已登入角色；寫入（execute／pause／resume／cancel／restore／review）：
 * OPERATOR／ADMIN（由 SecurityConfig 的「GET 之外一律 OPERATOR 以上」規則保證）。
 *
 * <p>控制類端點的回應是 {@code ExecutionRunResponse} 快照（呼叫 Bridge 成功後立刻再讀一次）；審核回 204，
 * 另開後續批次時 id 放在回應標頭 {@code X-Follow-Up-Run-Id}。
 */
@RestController
@Tag(name = "專案執行", description = "Phase 4；API-EXE／API-AUT／API-DAG")
public class ExecutionController {

    static final String FOLLOW_UP_HEADER = "X-Follow-Up-Run-Id";

    private final ExecuteProjectUseCase execute;
    private final ExecutionControlUseCase control;
    private final ExecutionQueryUseCase query;

    public ExecutionController(ExecuteProjectUseCase execute, ExecutionControlUseCase control,
                               ExecutionQueryUseCase query) {
        this.execute = execute;
        this.control = control;
        this.query = query;
    }

    @PostMapping("/api/v1/projects/{projectId}/execute")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "啟動專案執行",
            description = "後端二次硬校驗（前端按鈕禁用只是體驗）。驗證順序固定：404 專案 → 400 欄位驗證 → 409 專案正在執行中 → "
                    + "409 專案狀態不允許執行 → 409 未經人工審批的草案不可執行 → 400 範圍 id 不屬於此專案 → 409 範圍問題 → "
                    + "409 目標依賴成環 → 422 物化失敗 → Bridge（409 鎖／422／502／504，並補償刪除剛建的 run 列）。"
                    + "成功：建立 execution_runs（run_number 同專案遞增）→ Bridge POST /autoclaude/runs → 專案 EXECUTING、"
                    + "範圍內任務 QUEUED、啟動事件消費者。v1.3：依自治等級（≥ 6 要求自動突變、≥ 7 要求自演化）與旗標物化引擎設定，"
                    + "回應的 engineCapabilities 如實標示「實際送進引擎的」能力（沒有 model.apiKey 不報錯，回 UNAVAILABLE_NO_API_KEY）")
    public ApiResult<ExecutionRunResponse> execute(@PathVariable UUID projectId,
                                                   @RequestBody StartExecutionRequest request, Principal principal) {
        return ApiResult.created(ExecutionRunResponse.from(
                execute.execute(projectId, request.toCommand(), principal.getName())));
    }

    @GetMapping("/api/v1/projects/{projectId}/executions")
    @Operation(summary = "列出專案執行批次（補充端點，ADR-001 G-16）",
            description = "分頁；預設 startedAt,desc。每列帶批次比較所需的 Token／時間／成功率（US-M-06），"
                    + "供執行頁挑選目前批次與監控頁「執行批次」下拉")
    public ApiResult<PageData<ExecutionRunSummaryResponse>> list(
            @PathVariable UUID projectId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) RunStatus status,
            @Parameter(description = "欄位[,asc|desc]；欄位限 startedAt／runNumber；預設 startedAt,desc")
            @RequestParam(defaultValue = "startedAt,desc") String sort) {
        String[] parts = sort.split(",", 2);
        boolean byRunNumber = parseSortField(parts[0]);
        boolean ascending = parseDirection(parts.length > 1 ? parts[1] : "asc");
        return ApiResult.ok(PageData.of(
                query.list(projectId, new RunListQuery(status, byRunNumber, ascending, page, size)),
                ExecutionRunSummaryResponse::from));
    }

    @GetMapping("/api/v1/executions/{runId}")
    @Operation(summary = "查詢執行狀態",
            description = "合併 DB 列與 Bridge GET /autoclaude/runs/{id}。Bridge 不可達時仍回 200，bridge.connected=false，"
                    + "進度欄位退回 DB 衍生值（currentStep 缺席），不回 5xx。pendingReviews 只含 PENDING。"
                    + "v1.3：engineCapabilities（讀自 DB，建立時凍結）與 bridge.resources（引擎行程樹的資源取樣，值原樣來自同一次 Bridge 快照；"
                    + "行程不存活、Bridge 不可達或不認得該批次時缺席）")
    public ApiResult<ExecutionRunDetailResponse> get(@PathVariable UUID runId) {
        return ApiResult.ok(ExecutionRunDetailResponse.from(query.get(runId)));
    }

    @PostMapping("/api/v1/executions/{runId}/pause")
    @Operation(summary = "暫停執行（下一個步驟邊界生效）",
            description = "Bridge :pause（只收 RUNNING；PAUSING 時冪等）。回應的 bridgeStatus 為 PAUSING，status 仍是 RUNNING，"
                    + "直到 SSE 送出 status-change（PAUSED）。已在最後一步時暫停來不及，run 照常 COMPLETED")
    public ApiResult<ExecutionRunResponse> pause(@PathVariable UUID runId, Principal principal) {
        return ApiResult.ok(ExecutionRunResponse.from(control.pause(runId, principal.getName())));
    }

    @PostMapping("/api/v1/executions/{runId}/resume")
    @Operation(summary = "恢復執行（PAUSED 同進度接續）",
            description = "Bridge :resume（只收 PAUSED）。後端先重驗範圍內 Goal／Task 皆 signedOff"
                    + "（否則 409「未經人工審批的草案不可執行」）。回應 bridgeStatus=RUNNING")
    public ApiResult<ExecutionRunResponse> resume(@PathVariable UUID runId, Principal principal) {
        return ApiResult.ok(ExecutionRunResponse.from(control.resume(runId, principal.getName())));
    }

    @PostMapping("/api/v1/executions/{runId}/cancel")
    @Operation(summary = "取消執行（stop）",
            description = "Bridge :stop（RUNNING／PAUSING／PAUSED 可收）。回應 bridgeStatus=CANCELLING；終態 CANCELLED 由 SSE 通知。"
                    + "取消後範圍內 RUNNING／QUEUED 任務轉 CANCELLED（系統重設，US-E-06），專案回 READY")
    public ApiResult<ExecutionRunResponse> cancel(@PathVariable UUID runId, Principal principal) {
        return ApiResult.ok(ExecutionRunResponse.from(control.cancel(runId, principal.getName())));
    }

    @GetMapping("/api/v1/executions/{runId}/steps")
    @Operation(summary = "分頁查詢執行步驟（亦為 SSE 斷線的 REST 回補）",
            description = "資料列由 Bridge 寫入 execution_steps（每個 step 事件一列）。stepNumber 等於該 step 事件的 Bridge seq"
                    + "（與 SSE id: 同一個序號空間），所以 afterSeq 直接對 SSE 的 Last-Event-ID 整數部分。"
                    + "依 stepNumber 升冪；afterSeq 為嚴格大於。預設 size=50、上限 200")
    public ApiResult<PageData<ExecutionStepResponse>> steps(
            @PathVariable UUID runId,
            @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "每頁筆數（1～200）",
                    schema = @Schema(type = "integer", format = "int32", minimum = "1", maximum = "200",
                            defaultValue = "50"))
            @RequestParam(defaultValue = "50") int size,
            @Parameter(description = "只回傳 stepNumber（＝事件 seq）大於此值的列（嚴格大於）",
                    schema = @Schema(type = "integer", format = "int32", minimum = "0"))
            @RequestParam(defaultValue = "0") int afterSeq) {
        return ApiResult.ok(PageData.of(query.steps(runId, afterSeq, page, size), ExecutionStepResponse::from));
    }

    @GetMapping("/api/v1/executions/{runId}/dag")
    @Operation(summary = "查詢 DAG 圖",
            description = "節點與邊在建立批次時凍結於 execution_runs.dag；每個節點的 status 於讀取時疊加目標／任務的現況"
                    + "（歷史批次也是現況，見 statusAsOf）")
    public ApiResult<DagResponse> dag(@PathVariable UUID runId) {
        return ApiResult.ok(DagResponse.from(query.dag(runId)));
    }

    @GetMapping("/api/v1/executions/{runId}/checkpoints")
    @Operation(summary = "查詢可用斷點列表",
            description = "由 console.checkpoints 讀取（Bridge 於每個步驟完成時自行記錄歷史快照，append-only），依建立時間舊→新。"
                    + "不含 stateSnapshot 本體；stepIdx／stepId 取自快照內的 step_idx／step_id（＝還原後下一個要跑的步驟）")
    public ApiResult<List<CheckpointResponse>> checkpoints(@PathVariable UUID runId) {
        return ApiResult.ok(query.checkpoints(runId).stream().map(CheckpointResponse::from).toList());
    }

    @PostMapping("/api/v1/executions/{runId}/restore/{checkpointId}")
    @Operation(summary = "從指定歷史 checkpoint 還原並續跑",
            description = "Bridge POST /autoclaude/runs/{id}/restore（接受 PAUSED 與終態 COMPLETED／FAILED／CANCELLED；終態已放的鎖須重新取得，"
                    + "可能 409）。還原點之後的任務與目標由後端「系統重設」；專案回 EXECUTING。後端先重驗範圍內 signedOff。"
                    + "restore 沿用該 run 建立時的 playbook；只允許對專案最新的批次 restore（否則 409「只能還原專案最新的執行批次」）")
    public ApiResult<ExecutionRunResponse> restore(@PathVariable UUID runId, @PathVariable UUID checkpointId,
                                                   Principal principal) {
        return ApiResult.ok(ExecutionRunResponse.from(control.restore(runId, checkpointId, principal.getName())));
    }

    @PostMapping("/api/v1/executions/{runId}/review/{stepId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @ApiResponse(responseCode = "204", description = "已處理（無內容）",
            headers = @Header(name = FOLLOW_UP_HEADER, description = "後續批次 id（僅 SKIP／無還原點的 RETRY 會出現）",
                    schema = @Schema(type = "string", format = "uuid")))
    @Operation(summary = "審核執行結果（通過／拒絕／重試／跳過）",
            description = "路徑的 {stepId} 是 review_requests.id（UUID），不是 playbook 的 step_id。審核人取自 JWT subject。"
                    + "可用的決定由審核項的 allowedDecisions 決定；不在其內 → 409「此審核項不允許該決定」。成功 204。"
                    + "SKIP（以及找不到還原點的 RETRY）會另開後續批次（follow-up run），其 id 放在回應標頭 X-Follow-Up-Run-Id")
    public void review(@PathVariable UUID runId, @PathVariable("stepId") UUID reviewId,
                       @Valid @RequestBody ReviewRequestBody body, Principal principal,
                       HttpServletResponse response) {
        control.review(runId, reviewId, body.decision(), body.comment(), principal.getName())
                .ifPresent(followUp -> response.setHeader(FOLLOW_UP_HEADER, followUp.toString()));
    }

    /** 回 true＝依 runNumber 排序；false＝依 startedAt。 */
    private static boolean parseSortField(String raw) {
        return switch (raw.strip().toLowerCase(Locale.ROOT)) {
            case "startedat" -> false;
            case "runnumber" -> true;
            default -> throw ValidationException.of("sort", "sort 欄位只能是 startedAt、runNumber");
        };
    }

    private static boolean parseDirection(String raw) {
        return switch (raw.strip().toLowerCase(Locale.ROOT)) {
            case "asc" -> true;
            case "desc" -> false;
            default -> throw ValidationException.of("sort", "sort 方向只能是 asc 或 desc");
        };
    }
}
