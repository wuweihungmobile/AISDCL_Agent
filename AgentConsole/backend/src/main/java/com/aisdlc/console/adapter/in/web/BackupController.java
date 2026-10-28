package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.BackupJobAcceptedResponse;
import com.aisdlc.console.adapter.in.web.dto.BackupJobPageResponse;
import com.aisdlc.console.adapter.in.web.dto.BackupJobResponse;
import com.aisdlc.console.adapter.in.web.dto.BackupOverviewResponse;
import com.aisdlc.console.application.port.in.BackupJobUseCase;
import com.aisdlc.console.application.port.in.BackupQueryUseCase;
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
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.Map;

/**
 * 系統管理／資料庫備份的端點（TCS-SysAdminBackup-20261027 §C3；API-BK-01～04）：三個唯讀 {@code GET}（總覽、工作紀錄、單筆工作）加一個僅 ADMIN 的
 * {@code POST}（手動觸發）。<b>保留與排程沒有任何可寫面</b>：本類別恰三個 {@code @GetMapping}、一個 {@code @PostMapping}，沒有 PUT、PATCH、DELETE
 * （ArchUnit 鎖住）；備份的排程與保留策略住 sidecar 的 crontab 與 pgBackRest 設定，Console 只讀、只顯示。
 *
 * <p>權限：GET＝VIEWER 以上（無有效 JWT＝401）；POST＝僅 ADMIN（{@code SecurityConfig}：OPERATOR、VIEWER＝403 {@code ACCESS_DENIED}）。
 * 輸出尾段與觸發者只給 ADMIN。POST 的成功與被拒（401、403、409、422）都由 {@code AuditLoggingFilter} 在 {@code console.audit_log} 留一列；GET 不留列。
 * 失敗一律<b>沒有 {@code data}</b>（不回空表、不回部分資料）。
 */
@RestController
@RequestMapping("/api/v1/sysadmin")
@Tag(name = "系統管理（資料庫備份）", description = "備份清單與狀態（唯讀）、手動觸發全備／增備／驗證（僅 ADMIN）、工作紀錄；契約檔 API_Contract_SysAdminBackup.md")
public class BackupController {

    private final BackupQueryUseCase query;
    private final BackupJobUseCase trigger;

    public BackupController(BackupQueryUseCase query, BackupJobUseCase trigger) {
        this.query = query;
        this.trigger = trigger;
    }

    @GetMapping("/backups")
    @Operation(operationId = "getBackupOverview", summary = "備份總覽（唯讀；系統管理／資料庫備份）",
            description = "備份清單、四張最近狀態卡（全備、增備、離站 pg_dump、驗證）、排程與保留、各 repo 狀態、WAL 歸檔健康與進行中的工作。"
                    + "每個請求讀 sidecar 匯出的 8 個控制面檔案（不快取）。🔴 fail-loud：控制面未設定（control.reason=not_configured）、匯出檔不可讀"
                    + "（export_unreadable）、格式版本不符（schema_mismatch）時仍回 200，但所有資料區塊為 null（不是空陣列或 0）；runner_offline（心跳逾 30 秒）時"
                    + "資料照回但 canTrigger=false。個別來源失敗（info／logical 的 ok:false、cron 解析不了、資料庫讀取失敗）只降級該區塊並加 control.warnings。"
                    + "時間一律 UTC 帶 Z；排程時區取自 schedule.json。輸出尾段與觸發者僅 ADMIN。VIEWER 以上可讀。")
    public ApiResult<BackupOverviewResponse> overview(Authentication authentication) {
        return ApiResult.ok(BackupOverviewResponse.from(query.overview(isAdmin(authentication))));
    }

    @GetMapping("/backups/jobs")
    @Operation(operationId = "getBackupJobs", summary = "備份工作紀錄（唯讀；Console 發起的手動工作）",
            description = "requested_at 嚴格新到舊；排程工作不在此表（看總覽的狀態卡）。limit 預設 20、1～100；before 為 ISO-8601 時間（嚴格小於 requested_at）；"
                    + "參數非法 → 422 invalid_request（details.violations[{field,message}]）。回 {items, nextBefore}。requestedBy、detail 僅 ADMIN。"
                    + "控制面未設定或資料庫讀取失敗 → 503 backup_control_unavailable。VIEWER 以上可讀。")
    public ApiResult<BackupJobPageResponse> jobs(
            @Parameter(description = "頁大小（選填；整數 1～100，預設 20）；不合 → 422 invalid_request",
                    schema = @Schema(type = "integer", format = "int32", minimum = "1", maximum = "100"))
            @RequestParam(required = false) String limit,
            @Parameter(description = "游標（選填；ISO-8601 時間）：只回 requested_at 嚴格早於它的工作；取自上一頁的 nextBefore；不合 → 422 invalid_request")
            @RequestParam(required = false) String before,
            Authentication authentication) {
        return ApiResult.ok(BackupJobPageResponse.from(query.jobs(limit, before, isAdmin(authentication))));
    }

    @GetMapping("/backups/jobs/{id}")
    @Operation(operationId = "getBackupJob", summary = "單筆備份工作（唯讀）",
            description = "查無或 id 不是 UUID → 404 backup_job_not_found（不是 500、不是 422）。detail（已遮罩、最後 ≤2000 字元）與 requestedBy 僅 ADMIN。"
                    + "控制面未設定或資料庫讀取失敗 → 503 backup_control_unavailable。VIEWER 以上可讀。")
    public ApiResult<BackupJobResponse> job(@Parameter(description = "工作 id（UUID）") @PathVariable String id,
                                            Authentication authentication) {
        return ApiResult.ok(BackupJobResponse.from(query.job(id, isAdmin(authentication))));
    }

    @PostMapping("/backups/jobs")
    @ResponseStatus(HttpStatus.ACCEPTED)
    @Operation(operationId = "postBackupJob", summary = "手動觸發備份（全備、增備、驗證；僅 ADMIN）",
            description = "body {type:\"full|diff|verify\", confirm:true}。驗證順序固定：角色（僅 ADMIN；否則 403 ACCESS_DENIED）→ 本文不是 JSON 物件"
                    + "（400 MALFORMED_REQUEST_BODY）→ type 缺、非字串或不合（422 invalid_request；details.violations）→ confirm 不是 JSON 布林 true"
                    + "（400 backup_confirm_required）→ 控制面不可用（503 backup_control_unavailable：目錄未設、心跳過期、匯出不可讀、資料庫讀取失敗）→ "
                    + "已有 QUEUED 或 RUNNING（409 backup_job_in_progress）→ 頻率上限（409 backup_too_frequent；full 86400 秒、diff 3600 秒、verify 不設；"
                    + "details.type、details.nextAllowedAt）→ 建列並寫請求檔；寫檔失敗該列補償為 FAILED（control_write_failed）並回 503。任一前序失敗都零列、零檔。"
                    + "成功 202：工作已排入佇列（QUEUED），多餘的鍵忽略、id 由伺服器產生。",
            requestBody = @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
                    content = @Content(schema = @Schema(type = "object", example = "{\"type\":\"full\",\"confirm\":true}",
                            description = "{type: full|diff|verify, confirm: true（JSON 布林）}"))))
    public ApiResult<BackupJobAcceptedResponse> trigger(@RequestBody Map<String, Object> body, Authentication authentication) {
        BackupJobAcceptedResponse accepted = BackupJobAcceptedResponse.from(trigger.trigger(authentication.getName(), body));
        return new ApiResult<>(HttpStatus.ACCEPTED.value(), "success", accepted, OffsetDateTime.now(), MDC.get("traceId"));
    }

    private static boolean isAdmin(Authentication authentication) {
        return authentication != null && authentication.getAuthorities().stream().map(GrantedAuthority::getAuthority)
                .anyMatch(("ROLE_" + Role.ADMIN.name())::equals);
    }
}
