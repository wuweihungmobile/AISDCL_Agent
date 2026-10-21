package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.SiExportResponse;
import com.aisdlc.console.application.port.in.SiMirrorUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * SelfImproving 的唯讀鏡像（TCS-SelfImprovingMirror-P1b R7、R9、R10；PRD AC-SI-32-1～32-4）：六個 {@code GET}，<b>沒有任何非 GET 對映</b>
 * （P1b 零寫入；{@code @RequestMapping} 不帶 {@code method}，ArchUnit 鎖住）。權限沿 {@code SecurityConfig} 既有規則：無有效 JWT＝401、
 * VIEWER 以上可讀；非 GET 對 VIEWER＝403（被安全層擋下）、對 OPERATOR／ADMIN＝405（沒有對映）。
 *
 * <p>回應的 {@code data} 是 Bridge 的 export 物件原樣轉遞（欄名只經 snake_case→camelCase，值不動）；backend 不重算、不快取、不補欄。
 * 各 kind 的 {@code items} 欄位形狀見契約後繼檔 {@code API_Contract_SelfImproving_P1b.md §1.7}（端點總表為同檔 §1.0）。
 * 失敗一律<b>沒有 {@code data}</b>（不回空表、不回部分資料）：503 {@code si_unavailable}（details 帶 Bridge 的 {@code cause} 與
 * {@code detail}）、404 {@code si_not_found}（details 帶 {@code id}）、422（Bridge 的 {@code invalid_request}）、502／504。
 */
@RestController
@RequestMapping("/api/v1/si")
@Tag(name = "自我進化（SelfImproving）", description = "P1b 唯讀鏡像；API-SI-01～06（契約後繼檔 API_Contract_SelfImproving_P1b）")
public class SiController {

    private static final String SINCE = "游標（選填；整數 ≥0）：只回「ID 的數字部分」嚴格大於它的項目；取自上一頁回應的 nextSince。不合 → 400";
    private static final String LIMIT = "頁大小（選填；整數 ≥1）：不合 → 400；超過根層協定參數檔的上限時，CLI 失敗而回 503 si_unavailable（cause=nonzero_rc）";

    private final SiMirrorUseCase si;

    public SiController(SiMirrorUseCase si) {
        this.si = si;
    }

    @GetMapping("/status")
    @Operation(operationId = "getSiStatus", summary = "SelfImproving 狀態摘要（唯讀；P1b）",
            description = "Bridge GET /si/status（根層 si export --kind status）的原樣轉遞：啟動事件偵測、開啟中的運轉、待決提案、冷卻、"
                    + "暫停、各項「量不到」（NOT-EVALUABLE）。不分頁、不收任何查詢參數。每個請求恰一次 Bridge 呼叫（連線 2 秒、讀取 20 秒、不重試），"
                    + "不快取；失敗沒有 data（503 si_unavailable 帶 details.cause 與 details.detail）。VIEWER 以上可讀。")
    public ApiResult<SiExportResponse> status() {
        return ApiResult.ok(SiExportResponse.from(si.status()));
    }

    @GetMapping("/observations")
    @Operation(operationId = "getSiObservations", summary = "SelfImproving 觀察帳本（唯讀；P1b）",
            description = "Bridge GET /si/observations 的原樣轉遞：帳本逐列（九欄、marksKv、line）；無法解析的壞列以 {line, raw, valid:false} 出現，"
                    + "problems 逐項說明。游標分頁：truncated 為 true 時以 nextSince 取下一頁。失敗沒有 data。VIEWER 以上可讀。")
    public ApiResult<SiExportResponse> observations(
            @Parameter(description = SINCE, schema = @Schema(type = "integer", format = "int32", minimum = "0"))
            @RequestParam(required = false) Integer since,
            @Parameter(description = LIMIT, schema = @Schema(type = "integer", format = "int32", minimum = "1"))
            @RequestParam(required = false) Integer limit) {
        return ApiResult.ok(SiExportResponse.from(si.observations(since, limit)));
    }

    @GetMapping("/events")
    @Operation(operationId = "getSiEvents", summary = "SelfImproving 事件帳本（唯讀；P1b）",
            description = "Bridge GET /si/events 的原樣轉遞：事件帳本逐行（多型事件，鍵依 kind 而異，原樣轉 camelCase）。"
                    + "游標分頁同 observations。失敗沒有 data。VIEWER 以上可讀。")
    public ApiResult<SiExportResponse> events(
            @Parameter(description = SINCE, schema = @Schema(type = "integer", format = "int32", minimum = "0"))
            @RequestParam(required = false) Integer since,
            @Parameter(description = LIMIT, schema = @Schema(type = "integer", format = "int32", minimum = "1"))
            @RequestParam(required = false) Integer limit) {
        return ApiResult.ok(SiExportResponse.from(si.events(since, limit)));
    }

    @GetMapping("/proposals")
    @Operation(operationId = "getSiProposals", summary = "SelfImproving 提案清單（唯讀；P1b）",
            description = "Bridge GET /si/proposals 的原樣轉遞：每筆含狀態、route、digest、verdict、cooldown 與卡面 card 字串"
                    + "（逐位元組等於 si card 的輸出，量不到時為 null 並於 ne 說明）。游標分頁同 observations。失敗沒有 data。VIEWER 以上可讀。")
    public ApiResult<SiExportResponse> proposals(
            @Parameter(description = SINCE, schema = @Schema(type = "integer", format = "int32", minimum = "0"))
            @RequestParam(required = false) Integer since,
            @Parameter(description = LIMIT, schema = @Schema(type = "integer", format = "int32", minimum = "1"))
            @RequestParam(required = false) Integer limit) {
        return ApiResult.ok(SiExportResponse.from(si.proposals(since, limit)));
    }

    @GetMapping("/proposals/{id}")
    @Operation(operationId = "getSiProposal", summary = "SelfImproving 單筆提案（唯讀；P1b）",
            description = "Bridge GET /si/proposals/{id} 的原樣轉遞（items 恰一筆）。id 原樣嚴格 percent-encode 成單一路徑段後交給 Bridge；"
                    + "格式（PROP-SI-<三位以上數字>）的單一真相在 Bridge：不合 → 422（details.bridgeReason=invalid_request）。"
                    + "格式合法而查無 → 404（reason si_not_found，details.id；「404 的 reason 省略」慣例的第二個例外）。不收任何查詢參數。VIEWER 以上可讀。")
    public ApiResult<SiExportResponse> proposal(
            @Parameter(description = "提案 ID（例：PROP-SI-004）") @PathVariable String id) {
        return ApiResult.ok(SiExportResponse.from(si.proposal(id)));
    }

    @GetMapping("/runs")
    @Operation(operationId = "getSiRuns", summary = "SelfImproving 運轉（唯讀；P1b）",
            description = "Bridge GET /si/runs 的原樣轉遞：運轉的開關事件序號、觸發、研究事件、提案結果（outcome）。"
                    + "游標分頁同 observations。失敗沒有 data。VIEWER 以上可讀。")
    public ApiResult<SiExportResponse> runs(
            @Parameter(description = SINCE, schema = @Schema(type = "integer", format = "int32", minimum = "0"))
            @RequestParam(required = false) Integer since,
            @Parameter(description = LIMIT, schema = @Schema(type = "integer", format = "int32", minimum = "1"))
            @RequestParam(required = false) Integer limit) {
        return ApiResult.ok(SiExportResponse.from(si.runs(since, limit)));
    }
}
