package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.AlertResponse;
import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.LogEntryResponse;
import com.aisdlc.console.adapter.in.web.dto.PageData;
import com.aisdlc.console.adapter.in.web.dto.ProjectMetricsResponse;
import com.aisdlc.console.adapter.in.web.dto.TaskTrendPoint;
import com.aisdlc.console.adapter.in.web.dto.TokenTrendPoint;
import com.aisdlc.console.application.port.in.MonitorUseCase;
import com.aisdlc.console.application.port.in.MonitorUseCase.LogQuery;
import com.aisdlc.console.application.port.in.MonitorUseCase.Query;
import com.aisdlc.console.application.port.in.MonitorUseCase.Report;
import com.aisdlc.console.domain.exception.ValidationException;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.headers.Header;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

/**
 * 專案監控端點（Phase 5；契約 §1.3）。讀取：任何已登入角色；確認告警：OPERATOR／ADMIN。資料全來自 DB（不呼叫 Bridge）。
 *
 * <p>共通查詢參數：{@code runId}（必須屬於該專案，否則 404）、{@code from}／{@code to}（ISO-8601 帶 offset；預設 {@code to}＝現在、
 * {@code from}＝{@code to}−24 小時；{@code from} 必須早於 {@code to}、視窗 ≤ 366 天，否則 400「時間範圍不合法」）。
 * 輪詢間隔不得小於 {@code monitor.refreshIntervalMs}（預設與最小值皆 10 秒）。
 */
@RestController
@RequestMapping("/api/v1/monitor")
@Tag(name = "專案監控", description = "Phase 5；API-MON／API-ALR／API-NTF")
public class MonitorController {

    private static final String RUN_ID_DOC = "只看此執行批次（必須屬於該專案，否則 404）；省略＝專案全部批次";
    private static final String FROM_DOC = "視窗起點（ISO-8601 帶 offset）；預設 to 之前 24 小時";
    private static final String TO_DOC = "視窗終點（ISO-8601 帶 offset）；預設現在。from 必須早於 to，否則 400";
    private static final String BUCKET_DOC = "分桶粒度；預設視窗 ≤ 48 小時用 HOUR，否則 DAY";

    private final MonitorUseCase monitor;

    public MonitorController(MonitorUseCase monitor) {
        this.monitor = monitor;
    }

    @GetMapping("/projects/{projectId}/metrics")
    @Operation(summary = "查詢專案指標（PRD 八項 KPI＋設計稿所需欄位）",
            description = "百分比一律 0～100 並四捨五入到小數 1 位；平均值四捨五入到小數 2 位。previousValue／delta 是與「緊鄰前一個等長視窗」"
                    + "的比較，無法計算時為 null（UI 顯示「—」）。公式見 Markdown 契約 §3.8。預設視窗：to＝現在、from＝to−24h")
    public ApiResult<ProjectMetricsResponse> metrics(
            @PathVariable UUID projectId,
            @Parameter(description = RUN_ID_DOC) @RequestParam(required = false) UUID runId,
            @Parameter(description = FROM_DOC, schema = @Schema(type = "string", format = "date-time"))
            @RequestParam(required = false) String from,
            @Parameter(description = TO_DOC, schema = @Schema(type = "string", format = "date-time"))
            @RequestParam(required = false) String to) {
        return ApiResult.ok(ProjectMetricsResponse.from(monitor.metrics(query(projectId, runId, from, to, null))));
    }

    @GetMapping("/projects/{projectId}/token-trend")
    @Operation(summary = "Token 使用趨勢（含預算線）",
            description = "依 bucket 分桶（預設：視窗 ≤ 48 小時用 HOUR，否則 DAY）；資料來源 console.run_token_samples（由 Bridge token 事件寫入）。"
                    + "沒有資料的桶不補零（前端自行補）。budget 為該桶所屬批次的 tokenBudget（多批次時取桶內最新批次；無預算為 null）")
    public ApiResult<List<TokenTrendPoint>> tokenTrend(
            @PathVariable UUID projectId,
            @Parameter(description = RUN_ID_DOC) @RequestParam(required = false) UUID runId,
            @Parameter(description = FROM_DOC, schema = @Schema(type = "string", format = "date-time"))
            @RequestParam(required = false) String from,
            @Parameter(description = TO_DOC, schema = @Schema(type = "string", format = "date-time"))
            @RequestParam(required = false) String to,
            @Parameter(description = BUCKET_DOC, schema = @Schema(type = "string", allowableValues = {"HOUR", "DAY"}))
            @RequestParam(required = false) String bucket) {
        return ApiResult.ok(monitor.tokenTrend(query(projectId, runId, from, to, bucket)).stream()
                .map(TokenTrendPoint::from).toList());
    }

    @GetMapping("/projects/{projectId}/task-trend")
    @Operation(summary = "任務執行趨勢（依步驟事件分桶）",
            description = "資料來源 console.execution_steps（STARTED／COMPLETED／FAILED／RETRYING 各自計數）。成功／失敗比率由 completed 與 failed 推得。"
                    + "只回 List<TaskTrendPoint>（PRD §7.1.6），不含事件清單：事件時間軸改用 GET /api/v1/executions/{runId}/steps（主控裁決）")
    public ApiResult<List<TaskTrendPoint>> taskTrend(
            @PathVariable UUID projectId,
            @Parameter(description = RUN_ID_DOC) @RequestParam(required = false) UUID runId,
            @Parameter(description = FROM_DOC, schema = @Schema(type = "string", format = "date-time"))
            @RequestParam(required = false) String from,
            @Parameter(description = TO_DOC, schema = @Schema(type = "string", format = "date-time"))
            @RequestParam(required = false) String to,
            @Parameter(description = BUCKET_DOC, schema = @Schema(type = "string", allowableValues = {"HOUR", "DAY"}))
            @RequestParam(required = false) String bucket) {
        return ApiResult.ok(monitor.taskTrend(query(projectId, runId, from, to, bucket)).stream()
                .map(TaskTrendPoint::from).toList());
    }

    @GetMapping("/projects/{projectId}/alerts")
    @Operation(summary = "查詢告警",
            description = "由新到舊；PRD 回傳 List<AlertResponse>（不分頁），以 limit（預設 50，上限 200）截斷")
    public ApiResult<List<AlertResponse>> alerts(
            @PathVariable UUID projectId,
            @Parameter(description = RUN_ID_DOC) @RequestParam(required = false) UUID runId,
            @Parameter(description = "true＝只看已確認；false＝只看未確認；省略＝全部") @RequestParam(required = false) Boolean acknowledged,
            @Parameter(schema = @Schema(type = "integer", format = "int32", minimum = "1", maximum = "200",
                    defaultValue = "50")) @RequestParam(defaultValue = "50") int limit) {
        return ApiResult.ok(monitor.alerts(projectId, runId, acknowledged, limit).stream().map(AlertResponse::from)
                .toList());
    }

    @PostMapping("/alerts/{alertId}/acknowledge")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(summary = "確認告警",
            description = "寫入 acknowledged／By／At。冪等：已確認的告警再次確認仍回 204，且不改寫第一次的確認人與時間。"
                    + "確認後同一規則＋對象可再產生新告警")
    public void acknowledge(@PathVariable UUID alertId, Principal principal) {
        monitor.acknowledge(alertId, principal.getName());
    }

    @GetMapping("/projects/{projectId}/logs")
    @Operation(summary = "查詢結構化日誌",
            description = "日誌由 execution_steps、批次生命週期（execution_runs）、alerts、review_requests 衍生，不含引擎原始 stdout"
                    + "（原始行只在 SSE log 事件，來源 ENGINE）。等級對映：FAILED／CRITICAL→ERROR；RETRYING／WARNING／CANCELLED→WARN；其餘 INFO。"
                    + "預設 order=desc（新到舊）")
    public ApiResult<PageData<LogEntryResponse>> logs(
            @PathVariable UUID projectId,
            @Parameter(description = RUN_ID_DOC) @RequestParam(required = false) UUID runId,
            @Parameter(description = FROM_DOC, schema = @Schema(type = "string", format = "date-time"))
            @RequestParam(required = false) String from,
            @Parameter(description = TO_DOC, schema = @Schema(type = "string", format = "date-time"))
            @RequestParam(required = false) String to,
            @Parameter(schema = @Schema(type = "string", allowableValues = {"ALL", "INFO", "WARN", "ERROR"},
                    defaultValue = "ALL"))
            @RequestParam(defaultValue = "ALL") String level,
            @RequestParam(required = false) UUID taskId,
            @Parameter(description = "訊息關鍵字（不分大小寫；萬用字元視為字面）",
                    schema = @Schema(type = "string", maxLength = 200))
            @RequestParam(required = false) String q,
            @Parameter(schema = @Schema(type = "string", allowableValues = {"asc", "desc"}, defaultValue = "desc"))
            @RequestParam(defaultValue = "desc") String order,
            @RequestParam(defaultValue = "0") int page,
            @Parameter(schema = @Schema(type = "integer", format = "int32", minimum = "1", maximum = "200",
                    defaultValue = "50")) @RequestParam(defaultValue = "50") int size) {
        boolean ascending = switch (order.strip().toLowerCase(Locale.ROOT)) {
            case "asc" -> true;
            case "desc" -> false;
            default -> throw ValidationException.of("order", "order 只能是 asc 或 desc");
        };
        LogQuery logQuery = new LogQuery(query(projectId, runId, from, to, null), level, taskId, q, ascending, page,
                size);
        return ApiResult.ok(PageData.of(monitor.logs(logQuery), LogEntryResponse::from));
    }

    @GetMapping("/projects/{projectId}/report")
    @ApiResponse(responseCode = "200", description = "報表檔案",
            headers = @Header(name = "Content-Disposition",
                    description = "attachment; filename=\"monitor-report-<projectId 前 8 碼>-<yyyyMMdd-HHmm>.csv\"",
                    schema = @Schema(type = "string")),
            content = {
                    @Content(mediaType = "text/csv", schema = @Schema(type = "string")),
                    @Content(mediaType = "application/pdf", schema = @Schema(type = "string", format = "binary"))})
    @Operation(summary = "匯出監控報表（CSV 必做；PDF 標 W5）",
            description = "不包 ApiResult 封包，直接回檔案並帶 Content-Disposition: attachment。呼叫端須送 Accept: text/csv（或 */*）。"
                    + "CSV：UTF-8 含 BOM、CRLF、RFC 4180 引號；多個區段以 #section,<名稱> 行分隔（summary／runs／tasks／alerts），"
                    + "格式見 Markdown 契約 §1.3.7。format=pdf 在 W5 之前回 501（reason「PDF 報表尚未提供（W5）」）")
    public ResponseEntity<byte[]> report(
            @PathVariable UUID projectId,
            @Parameter(schema = @Schema(type = "string", allowableValues = {"csv", "pdf"}, defaultValue = "csv"))
            @RequestParam(defaultValue = "csv") String format,
            @Parameter(description = RUN_ID_DOC) @RequestParam(required = false) UUID runId,
            @Parameter(description = FROM_DOC, schema = @Schema(type = "string", format = "date-time"))
            @RequestParam(required = false) String from,
            @Parameter(description = TO_DOC, schema = @Schema(type = "string", format = "date-time"))
            @RequestParam(required = false) String to) {
        Report report = monitor.report(query(projectId, runId, from, to, null), format);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        ContentDisposition.attachment().filename(report.filename()).build().toString())
                .contentType(MediaType.parseMediaType(report.contentType()))
                .body(report.content());
    }

    private static Query query(UUID projectId, UUID runId, String from, String to, String bucket) {
        return new Query(projectId, runId, TimeParams.parse("from", from), TimeParams.parse("to", to), bucket);
    }
}
