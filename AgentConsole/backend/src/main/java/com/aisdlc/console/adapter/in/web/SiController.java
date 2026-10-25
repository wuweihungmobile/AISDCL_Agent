package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.SiCloseRequest;
import com.aisdlc.console.adapter.in.web.dto.SiConsoleWritesResponse;
import com.aisdlc.console.adapter.in.web.dto.SiDecideRequest;
import com.aisdlc.console.adapter.in.web.dto.SiExportResponse;
import com.aisdlc.console.adapter.in.web.dto.SiObservationRequest;
import com.aisdlc.console.adapter.in.web.dto.SiValidationResponse;
import com.aisdlc.console.adapter.in.web.dto.SiWriteReceiptResponse;
import com.aisdlc.console.application.port.in.SiMirrorUseCase;
import com.aisdlc.console.application.port.in.SiReconcileUseCase;
import com.aisdlc.console.application.port.in.SiWriteUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;

/**
 * SelfImproving 的端點：P1b 的六個唯讀鏡像 {@code GET}（TCS-SelfImprovingMirror-P1b R7、R9、R10；PRD AC-SI-32-1～32-4）加 P2b 的寫入載體——
 * 四個 {@code POST}（決定、新增觀察、關閉觀察、預檢）與一個對帳讀面 {@code GET /console-writes}（TCS-SelfImprovingDecide-P2b W10、W11、W14；
 * PRD AC-SI-33、AC-SI-35）。<b>Console 不寫帳本</b>：四個 POST 只簽稽核 JSON、寫 Console 自己的稽核列、經 Bridge 落稽核檔，由主機端根層 CLI 入帳。
 * <b>沒有任何 PUT、PATCH、DELETE 對映</b>（{@code @RequestMapping} 不帶 {@code method}，ArchUnit 鎖住）。
 *
 * <p>權限：GET＝VIEWER 以上（無有效 JWT＝401）；<b>四個 POST＝僅 ADMIN</b>（{@code SecurityConfig}：VIEWER／OPERATOR＝403 {@code ACCESS_DENIED}），
 * 帳號另須在 {@code console.si.deciders} 名單內（403 {@code si_write_forbidden}）；PUT／PATCH／DELETE 對 VIEWER＝403、對 OPERATOR／ADMIN＝405（沒有對映）。
 * 閘門序（POST）：401→403 ACCESS_DENIED→403 si_write_forbidden→503 si_write_disabled→422 invalid_request→執行。
 *
 * <p>GET 回應的 {@code data} 是 Bridge 的 export 物件原樣轉遞（欄名只經 snake_case→camelCase，值不動）；backend 不重算、不快取、不補欄。
 * 各 kind 的 {@code items} 欄位形狀見契約後繼檔 {@code API_Contract_SelfImproving_P1b.md §1.7}（端點總表為同檔 §1.0）。
 * 失敗一律<b>沒有 {@code data}</b>（不回空表、不回部分資料）：503 {@code si_unavailable}（details 帶 Bridge 的 {@code cause} 與
 * {@code detail}）、404 {@code si_not_found}（details 帶 {@code id}）、422（Bridge 的 {@code invalid_request}）、502／504。
 */
@RestController
@RequestMapping("/api/v1/si")
@Tag(name = "自我進化（SelfImproving）", description = "P1b 唯讀鏡像 API-SI-01～06（契約後繼檔 API_Contract_SelfImproving_P1b）；"
        + "P2b 寫入載體（決定、新增與關閉觀察、預檢、對帳；契約後繼檔 API_Contract_SelfImproving_P2b）")
public class SiController {

    private static final String SINCE = "游標（選填；整數 ≥0）：只回「ID 的數字部分」嚴格大於它的項目；取自上一頁回應的 nextSince。不合 → 400";
    private static final String LIMIT = "頁大小（選填；整數 ≥1）：不合 → 400；超過根層協定參數檔的上限時，CLI 失敗而回 503 si_unavailable（cause=nonzero_rc）";
    private static final String WRITE_FLOW = "驗證順序固定：角色（僅 ADMIN；否則 403 ACCESS_DENIED）→ 帳號須在 console.si.deciders（403 si_write_forbidden）→ "
            + "寫入面啟用（503 si_write_disabled；details.cause＝audit_key_unset｜bridge_token_unset）→ 輸入閘（422 invalid_request；"
            + "details.violations[{field,message}] 一次全列）→ 簽章、寫 Console 稽核列、單次 Bridge 呼叫（連線 2 秒／讀取 20 秒、不重試）。"
            + "Bridge 明確拒絕或確定未落檔時補償刪除稽核列；結果不明（504、送出後連線重設的 502、2xx 本文無法解析的 502）時保留該列並在 "
            + "details.outcomeUnknown 標明。重送一律新 auditRef。201 的意思是稽核檔已落地、待入帳（由主機端根層 CLI 以 --carrier console 驗簽入帳），不是已入帳。";

    private final SiMirrorUseCase si;
    private final SiWriteUseCase write;
    private final SiReconcileUseCase reconcile;

    public SiController(SiMirrorUseCase si, SiWriteUseCase write, SiReconcileUseCase reconcile) {
        this.si = si;
        this.write = write;
        this.reconcile = reconcile;
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

    // ── P2b：寫入載體（僅 ADMIN；Console 不寫帳本，只落經簽章的稽核檔）──────────────────────────────────

    @PostMapping("/proposals/{id}/decide")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(operationId = "postSiDecide", summary = "對待決提案或暫停的運轉下決定（P2b；僅 ADMIN）",
            description = "九種動詞（approve、reject、return、promote、decline-promote、rollback、unblock、resume、ack-handoff；沒有批次核准）；"
                    + "路徑 id 為 PROP 號（resume 為 RUN 號）。各動詞必填與禁止的欄位見 SiDecideRequest；多帶或缺帶一律 422。" + WRITE_FLOW)
    public ApiResult<SiWriteReceiptResponse> decide(@Parameter(description = "提案 ID（例：PROP-SI-004）；resume 為運轉 ID（例：RUN-SI-001）")
                                                    @PathVariable String id, @RequestBody SiDecideRequest request,
                                                    Principal principal) {
        return ApiResult.created(SiWriteReceiptResponse.from(write.decide(principal.getName(), id, request.toInput())));
    }

    @PostMapping("/observations")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(operationId = "postSiObservation", summary = "新增觀察列（P2b；僅 ADMIN）",
            description = "新增一列處置為 open 的觀察；corrects 帶被更正列的 OBS 號時產生 rel=corrects 標記。建議先呼叫 observations/validate 預檢。"
                    + WRITE_FLOW)
    public ApiResult<SiWriteReceiptResponse> addObservation(@RequestBody SiObservationRequest request, Principal principal) {
        return ApiResult.created(SiWriteReceiptResponse.from(write.addObservation(principal.getName(), request.toInput())));
    }

    @PostMapping("/observations/{id}/close")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(operationId = "postSiObservationClose", summary = "關閉處置為 open 的觀察列（P2b；僅 ADMIN）",
            description = "把處置為 open 的觀察列一次關成七個終值之一（沒有 open）；路徑 id 為 OBS 號。是否存在、是否仍為 open 由根層 CLI 入帳時判"
                    + "（不成立＝入帳被拒，稽核檔與 Console 稽核列原地不動，持續顯示待入帳）。" + WRITE_FLOW)
    public ApiResult<SiWriteReceiptResponse> closeObservation(@Parameter(description = "觀察列 ID（例：OBS-SI-005）") @PathVariable String id,
                                                              @RequestBody SiCloseRequest request, Principal principal) {
        return ApiResult.created(SiWriteReceiptResponse.from(write.closeObservation(principal.getName(), id, request.toInput())));
    }

    @PostMapping("/observations/validate")
    @Operation(operationId = "postSiObservationValidate", summary = "新增觀察列的唯讀預檢（P2b；僅 ADMIN）",
            description = "根層 obs-add --dry-run：回預覽列、位元組數與根層的拒收原因（ok=false 仍是 200）。不取 auditRef、不簽章、不寫 Console 稽核列、不落檔、"
                    + "不寫帳本。與新增觀察同一關（授權、停用、輸入閘）；Bridge 回 503 si_unavailable 時原因逐字轉出。" + WRITE_FLOW)
    public ApiResult<SiValidationResponse> validateObservation(@RequestBody SiObservationRequest request, Principal principal) {
        return ApiResult.ok(SiValidationResponse.from(write.validateObservation(principal.getName(), request.toInput())));
    }

    // ── P2b：對帳讀面 ───────────────────────────────────────────────────────────────────────────

    @GetMapping("/console-writes")
    @Operation(operationId = "getSiConsoleWrites", summary = "Console 稽核列與 SelfImproving 帳本的對帳（P2b；VIEWER 以上可讀）",
            description = "回 Console 自己的稽核列（時間新到舊；不含 body 與 mac）與每列是否已入帳（ingested）、帳本中 carrier 為 console 而本表沒有對應列的項（orphans，"
                    + "紅色警示來源）。對帳在 backend 一次全量做：以 Bridge 的 observations 與 events 各自 limit=500 迴圈取頁（上限各 20 頁）。"
                    + "讀路徑唯一的副作用是把 obs-add 列的 subjectId（NULL）依帳本新列號回填（冪等）；Bridge 永遠只被呼叫 GET。量不到（Bridge 失敗、逾時、"
                    + "頁數超限）＝reconcile.status 為 NOT-EVALUABLE（reason：si_unavailable、bridge_unreachable、bridge_timeout、scan_cap_exceeded），"
                    + "items 照回、ingested 與 orphans 為 null——不回空陣列、不冒充無待入帳。")
    public ApiResult<SiConsoleWritesResponse> consoleWrites(
            @Parameter(description = "回傳的稽核列數（選填；整數 1～500，預設 100）：不合 → 400",
                    schema = @Schema(type = "integer", format = "int32", minimum = "1", maximum = "500", defaultValue = "100"))
            @RequestParam(required = false) Integer limit) {
        return ApiResult.ok(SiConsoleWritesResponse.from(reconcile.consoleWrites(limit)));
    }
}
