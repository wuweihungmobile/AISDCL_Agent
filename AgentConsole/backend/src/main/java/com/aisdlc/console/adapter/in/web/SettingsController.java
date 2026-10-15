package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.ConfigHistoryResponse;
import com.aisdlc.console.adapter.in.web.dto.ConfigResponse;
import com.aisdlc.console.adapter.in.web.dto.ConnectionTestResponse;
import com.aisdlc.console.adapter.in.web.dto.ImportSettingsResponse;
import com.aisdlc.console.adapter.in.web.dto.PageData;
import com.aisdlc.console.adapter.in.web.dto.SettingsExportDocument;
import com.aisdlc.console.adapter.in.web.dto.TestConnectionRequest;
import com.aisdlc.console.adapter.in.web.dto.TokenGuardRequest;
import com.aisdlc.console.adapter.in.web.dto.UpdateConfigRequest;
import com.aisdlc.console.application.port.in.SettingsUseCase;
import com.aisdlc.console.application.port.in.SettingsUseCase.ConfigView;
import com.aisdlc.console.application.port.in.SettingsUseCase.ExportedSettings;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.model.auth.Role;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.CacheControl;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.security.Principal;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 系統參數端點（Phase 6；PRD §7.1.8；契約 §1.5）。讀取：任何已登入角色（加密值遮罩）；
 * 寫入、重置、匯出入、測試連線：僅 ADMIN（SecurityConfig 對 {@code /api/v1/settings/**} 的非 GET 一律要求 ADMIN）；
 * {@code reveal=true} 揭露加密明文僅 ADMIN（這裡檢查，非 ADMIN 回 403 專屬 reason）。
 */
@RestController
@RequestMapping("/api/v1/settings")
@Tag(name = "系統參數", description = "Phase 6；API-SET／NFR-SEC-04／NFR-SEC-05")
public class SettingsController {

    private static final DateTimeFormatter FILE_DATE = DateTimeFormatter.ofPattern("yyyyMMdd").withZone(ZoneOffset.UTC);

    private final SettingsUseCase settings;

    public SettingsController(SettingsUseCase settings) {
        this.settings = settings;
    }

    @GetMapping
    @Operation(summary = "查詢所有參數（依分類）",
            description = "六個分類：model／agent／execution／monitor／autoclaude／sdd。加密值一律 ••••••••，並附 hasValue；"
                    + "reveal=true 僅 ADMIN（其他角色 403），每次揭露寫審計")
    public ApiResult<Map<String, List<ConfigResponse>>> listAll(
            @Parameter(description = "true＝揭露加密值明文（僅 ADMIN）") @RequestParam(defaultValue = "false") boolean reveal,
            Authentication authentication) {
        requireAdminToReveal(reveal, authentication);
        Map<String, List<ConfigResponse>> byCategory = new LinkedHashMap<>();
        settings.listAll(reveal).forEach((category, views) -> byCategory.put(category, toResponses(views)));
        return ApiResult.ok(byCategory);
    }

    @GetMapping("/history")
    @Operation(summary = "查詢參數修改歷史（分頁）",
            description = "由新到舊。加密參數的 oldValue／newValue 一律遮罩；單獨給 key（沒有 category）回 400")
    public ApiResult<PageData<ConfigHistoryResponse>> history(
            @RequestParam(required = false) String category,
            @Parameter(description = "需與 category 併用（單獨給 key 回 400）") @RequestParam(required = false) String key,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ApiResult.ok(PageData.of(settings.history(category, key, page, size), ConfigHistoryResponse::from));
    }

    @PostMapping("/export")
    @Operation(summary = "匯出設定（JSON 檔）",
            description = "不包 ApiResult 封包，直接回檔案；加密參數的 value 一律輸出佔位字串 <encrypted>（匯入時略過）")
    public ResponseEntity<SettingsExportDocument> export() {
        ExportedSettings exported = settings.export();
        String filename = "aisdlc-settings-" + FILE_DATE.format(exported.exportedAt()) + ".json";
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .cacheControl(CacheControl.noStore())
                .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.attachment().filename(filename).build()
                        .toString())
                .body(SettingsExportDocument.from(exported));
    }

    @PostMapping(path = "/import", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true)
    @Operation(summary = "匯入設定（JSON 檔）",
            description = "multipart 欄位 file（≤ 1MB、version=1）。逐筆驗證，通過者在同一交易套用並寫歷史；<encrypted> 佔位值略過；"
                    + "token_guard 兩鍵以合併後的最終值做 halt > compact 跨鍵校驗。經 nginx 時須有 client_max_body_size 2m（契約 §0.7）")
    public ApiResult<ImportSettingsResponse> importSettings(@RequestPart("file") MultipartFile file,
                                                            Principal principal) {
        return ApiResult.ok(ImportSettingsResponse.from(
                settings.importSettings(SettingsFileReader.read(file), principal.getName())));
    }

    @PostMapping("/test-connection")
    @Operation(summary = "測試模型連線（SEC-04）",
            description = "預設測試已儲存的 model.apiUrl／apiKey；body（選填）可帶尚未儲存的值。對完整端點原樣送一則 1-token 的 POST ping；"
                    + "連線釘死在已驗證的 IP、不跟 redirect。SSRF／allowlist 檢查未過 → 422；網路層結果 → 200＋success=false")
    public ApiResult<ConnectionTestResponse> testConnection(@Valid @RequestBody(required = false)
                                                            TestConnectionRequest request, Principal principal) {
        return ApiResult.ok(ConnectionTestResponse.from(settings.testConnection(
                request == null ? null : request.toDomain(), principal.getName())));
    }

    @PutMapping("/execution/token-guard")
    @Operation(summary = "原子更新 token_guard 群組（NFR-SEC-05）",
            description = "compactThresholdPct 與 haltThresholdPct 一併提交，同一交易內跨鍵校驗 halt > compact；"
                    + "不滿足 → 400（reason 逐字：halt_threshold_pct 必須大於 compact_threshold_pct）；任何失敗都不改任何一個鍵")
    public ApiResult<List<ConfigResponse>> updateTokenGuard(@Valid @RequestBody TokenGuardRequest request,
                                                            Principal principal) {
        return ApiResult.ok(toResponses(settings.updateTokenGuard(request.compactThresholdPct(),
                request.haltThresholdPct(), principal.getName())));
    }

    @GetMapping("/{category}")
    @Operation(summary = "查詢特定分類參數", description = "同 GET /api/v1/settings 的遮罩與 reveal 規則；分類不存在 → 404")
    public ApiResult<List<ConfigResponse>> listCategory(
            @CategoryParam @PathVariable String category,
            @Parameter(description = "true＝揭露加密值明文（僅 ADMIN）") @RequestParam(defaultValue = "false") boolean reveal,
            Authentication authentication) {
        requireAdminToReveal(reveal, authentication);
        return ApiResult.ok(toResponses(settings.listCategory(category, reveal)));
    }

    @PostMapping("/{category}/reset")
    @Operation(summary = "重置整個分類為預設值（補充端點）",
            description = "同一交易內逐鍵重置並各寫歷史；加密鍵預設略過（要連同重置須 confirm=true）；"
                    + "token_guard 以重置後的最終值做跨鍵校驗，不滿足 → 400 且整批不套用")
    public ApiResult<List<ConfigResponse>> resetCategory(
            @CategoryParam @PathVariable String category,
            @Parameter(description = "涉及加密參數的重置須明確帶 true") @RequestParam(defaultValue = "false") boolean confirm,
            Principal principal) {
        return ApiResult.ok(toResponses(settings.resetCategory(category, confirm, principal.getName())));
    }

    @PutMapping("/{category}/{key}")
    @Operation(summary = "更新單一參數",
            description = "驗證順序：404 鍵不存在 → 400 型別／validationRule／範圍／SEC-04 allowlist（model.apiUrl）→ "
                    + "400 token_guard 單鍵跨鍵校驗（讀對端鍵現值）→ 409 敏感參數未帶 confirm=true")
    public ApiResult<ConfigResponse> update(@CategoryParam @PathVariable String category, @PathVariable String key,
                                            @Valid @RequestBody UpdateConfigRequest request, Principal principal) {
        return ApiResult.ok(ConfigResponse.from(settings.update(category, key, request.value(),
                request.confirmed(), principal.getName())));
    }

    @PostMapping("/{category}/{key}/reset")
    @Operation(summary = "重置單一參數為預設值",
            description = "寫歷史。token_guard 單鍵重置後若違反 halt > compact → 400；加密鍵需 confirm=true，否則 409")
    public ApiResult<ConfigResponse> reset(
            @CategoryParam @PathVariable String category, @PathVariable String key,
            @Parameter(description = "涉及加密參數的重置須明確帶 true") @RequestParam(defaultValue = "false") boolean confirm,
            Principal principal) {
        return ApiResult.ok(ConfigResponse.from(settings.reset(category, key, confirm, principal.getName())));
    }

    private static List<ConfigResponse> toResponses(List<ConfigView> views) {
        return views.stream().map(ConfigResponse::from).toList();
    }

    /** {@code reveal=true} 只准 ADMIN（契約 §1.5.1）：其他角色 403，reason 為專屬常數。 */
    private static void requireAdminToReveal(boolean reveal, Authentication authentication) {
        if (!reveal) {
            return;
        }
        boolean admin = authentication != null && authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority).anyMatch(("ROLE_" + Role.ADMIN.name())::equals);
        if (!admin) {
            throw new ForbiddenException("僅 ADMIN 可揭露敏感參數", ErrorReasons.REVEAL_ADMIN_ONLY);
        }
    }
}
