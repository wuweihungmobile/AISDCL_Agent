package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.EditParsedResultRequest;
import com.aisdlc.console.adapter.in.web.dto.ImportRecordDetailResponse;
import com.aisdlc.console.adapter.in.web.dto.ImportRecordResponse;
import com.aisdlc.console.adapter.in.web.dto.PageData;
import com.aisdlc.console.adapter.in.web.dto.ParseOptionsRequest;
import com.aisdlc.console.adapter.in.web.dto.ParseResultResponse;
import com.aisdlc.console.adapter.in.web.dto.ProjectResponse;
import com.aisdlc.console.adapter.in.web.dto.SignoffRequest;
import com.aisdlc.console.adapter.in.web.dto.TextImportRequest;
import com.aisdlc.console.application.port.in.ImportUseCase;
import com.aisdlc.console.application.port.in.ImportUseCase.ListQuery;
import com.aisdlc.console.application.port.in.ImportUseCase.SortField;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.UnprocessableException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.imports.ImportStatus;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.security.Principal;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

/**
 * BRD/PRD 匯入端點（Phase 3；PRD §7.1.4；契約 §1.1）。讀取：任何已登入角色；寫入（upload／text／parse／result／
 * signoff／confirm／reject）：OPERATOR／ADMIN（由 SecurityConfig 的「GET 之外一律 OPERATOR 以上」規則保證）。
 */
@RestController
@RequestMapping("/api/v1/import")
@Tag(name = "BRD/PRD 匯入", description = "Phase 3；API-IMP／API-SGN")
public class ImportController {

    private final ImportUseCase imports;

    public ImportController(ImportUseCase imports) {
        this.imports = imports;
    }

    @GetMapping
    @Operation(summary = "查詢匯入歷史（分頁）",
            description = "列表不含 sourceContent、parsedResult（用 GET /api/v1/import/{id} 取詳情）。預設依 createdAt 由新到舊")
    public ApiResult<PageData<ImportRecordResponse>> list(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) ImportStatus status,
            @Parameter(description = "來源檔名模糊搜尋（不分大小寫；萬用字元視為字面）") @RequestParam(required = false) String q,
            @Parameter(description = "欄位[,asc|desc]；欄位限 createdAt／status；預設 createdAt,desc")
            @RequestParam(defaultValue = "createdAt,desc") String sort) {
        String[] parts = sort.split(",", 2);
        SortField field = parseSortField(parts[0]);
        boolean ascending = parseDirection(parts.length > 1 ? parts[1] : "asc");
        return ApiResult.ok(PageData.of(imports.list(new ListQuery(q, status, field, ascending, page, size)),
                ImportRecordResponse::from));
    }

    @PostMapping(path = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @ResponseStatus(HttpStatus.CREATED)
    @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true)
    @Operation(summary = "上傳 BRD/PRD 檔案",
            description = "副檔名限 .md／.pdf／.docx（不分大小寫）、大小 ≤ 10MB；後端擷取純文字存入 sourceContent。"
                    + "經 nginx 時 /api/v1/import/ 須設 client_max_body_size 11m（契約 §0.7）")
    public ApiResult<ImportRecordResponse> upload(@RequestPart("file") MultipartFile file) {
        byte[] content;
        try {
            content = file.getBytes();
        } catch (IOException e) {
            throw new UnprocessableException("檔案已損毀，無法讀取", ErrorReasons.FILE_CORRUPT, Map.of());
        }
        return ApiResult.created(ImportRecordResponse.from(imports.upload(file.getOriginalFilename(), content)));
    }

    @PostMapping("/text")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "貼上純文字建立匯入記錄",
            description = "sourceType 只接受 PLAIN_TEXT（預設）與 MARKDOWN；路徑判斷（高階目標 vs 結構化文件）在 parse 階段")
    public ApiResult<ImportRecordResponse> importText(@Valid @RequestBody TextImportRequest request) {
        return ApiResult.created(ImportRecordResponse.from(
                imports.createFromText(request.content(), request.sourceFileName(), request.sourceType())));
    }

    @GetMapping("/{id}")
    @Operation(summary = "查詢匯入記錄詳情（補充端點）",
            description = "含 sourceContent 與 parsedResult；parsedResult 在第一次成功解析前為 null")
    public ApiResult<ImportRecordDetailResponse> get(@PathVariable UUID id) {
        return ApiResult.ok(ImportRecordDetailResponse.from(imports.get(id)));
    }

    @PostMapping("/{id}/parse")
    @Operation(summary = "觸發 AI 解析（三條路徑擇一）",
            description = "同步呼叫。路徑 A（SDD 規格）> C（高階目標，Bridge decompose）> B（OpenAI 相容 LLM）；"
                    + "三道有界閘與 prompt_too_long 任一不過 → 422（記錄退回 UPLOADED），不截斷不修剪")
    public ApiResult<ParseResultResponse> parse(@PathVariable UUID id,
                                                @Valid @RequestBody ParseOptionsRequest request) {
        return ApiResult.ok(ParseResultResponse.from(imports.parse(id, request.toDomain())));
    }

    @PutMapping("/{id}/result")
    @Operation(summary = "編輯解析結果（重新過有界閘）",
            description = "以整棵樹覆寫 project 與 goals（陣列順序即排序）；成功後 status=REVIEWING，編輯會撤銷既有 signoff")
    public ApiResult<ParseResultResponse> editResult(@PathVariable UUID id,
                                                     @Valid @RequestBody EditParsedResultRequest request) {
        return ApiResult.ok(ParseResultResponse.from(imports.editResult(id, request.parsedResult().toDomain())));
    }

    @PostMapping("/{id}/signoff")
    @Operation(summary = "🔴 人工 signoff 匯入草案（只批准，不落庫）",
            description = "approver 必填、非空白（不可匿名）；路徑 C 對每個 draftId 呼叫 Bridge :approve；已 signoff 回 409")
    public ApiResult<ImportRecordResponse> signoff(@PathVariable UUID id, @Valid @RequestBody SignoffRequest request) {
        return ApiResult.ok(ImportRecordResponse.from(imports.signoff(id, request.approver())));
    }

    @PostMapping("/{id}/confirm")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "確認匯入（單一交易建立專案／目標／任務）",
            description = "要求 signedOff=true，否則 409；全部 signedOff=true、signedOffBy／At 承襲匯入記錄")
    public ApiResult<ProjectResponse> confirm(@PathVariable UUID id, Principal principal) {
        return ApiResult.created(ProjectResponse.from(imports.confirm(id, principal.getName())));
    }

    @PostMapping("/{id}/reject")
    @Operation(summary = "放棄匯入（補充端點）", description = "status 轉 REJECTED；已 IMPORTED／REJECTED 或解析中回 409")
    public ApiResult<ImportRecordResponse> reject(@PathVariable UUID id) {
        return ApiResult.ok(ImportRecordResponse.from(imports.reject(id)));
    }

    private static SortField parseSortField(String raw) {
        return switch (raw.strip().toLowerCase(Locale.ROOT)) {
            case "createdat" -> SortField.CREATED_AT;
            case "status" -> SortField.STATUS;
            default -> throw ValidationException.of("sort", "sort 欄位只能是 createdAt、status");
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
