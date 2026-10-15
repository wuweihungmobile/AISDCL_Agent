package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.CreateProjectRequest;
import com.aisdlc.console.adapter.in.web.dto.PageData;
import com.aisdlc.console.adapter.in.web.dto.ProjectDetailResponse;
import com.aisdlc.console.adapter.in.web.dto.ProjectResponse;
import com.aisdlc.console.adapter.in.web.dto.ProjectSummaryResponse;
import com.aisdlc.console.adapter.in.web.dto.SignoffRequest;
import com.aisdlc.console.adapter.in.web.dto.UpdateProjectRequest;
import com.aisdlc.console.application.port.in.ManageProjectUseCase;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.ListQuery;
import com.aisdlc.console.application.port.in.ManageProjectUseCase.SortField;
import com.aisdlc.console.domain.exception.ErrorReasons;
import com.aisdlc.console.domain.exception.ForbiddenException;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.model.auth.Role;
import com.aisdlc.console.domain.model.project.ProjectStatus;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.util.Locale;
import java.util.UUID;

/** 專案管理端點（PRD §7.1.1、§7.1.4.1 的專案 signoff）。讀取：任何已登入角色；寫入：OPERATOR／ADMIN。 */
@RestController
@RequestMapping("/api/v1/projects")
@Tag(name = "專案管理")
public class ProjectController {

    private final ManageProjectUseCase projects;

    public ProjectController(ManageProjectUseCase projects) {
        this.projects = projects;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "建立專案", description = "狀態預設 DRAFT；手動建立 signedOff=true，draft=true 時為 false")
    public ApiResult<ProjectResponse> create(@Valid @RequestBody CreateProjectRequest request, Principal principal) {
        return ApiResult.created(ProjectResponse.from(projects.create(request.toDomain(), principal.getName())));
    }

    @GetMapping
    @Operation(summary = "查詢專案列表",
            description = "分頁、名稱模糊搜尋、狀態篩選、排序；預設排除已軟刪除。deleted=true 改為「只列軟刪除的專案」（OPERATOR 以上，"
                    + "VIEWER 回 403 ACCESS_DENIED；列表項帶 deletedAt；保留期已過的專案仍會列出，按復原才會得到 409 restore_window_expired；"
                    + "v1.2，C-3）")
    public ApiResult<PageData<ProjectSummaryResponse>> list(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @Parameter(description = "名稱模糊搜尋（不分大小寫）") @RequestParam(required = false) String q,
            @RequestParam(required = false) ProjectStatus status,
            @Parameter(description = "排序：欄位[,asc|desc]，欄位可為 name／status／createdAt／updatedAt；預設 updatedAt,desc")
            @RequestParam(defaultValue = "updatedAt,desc") String sort,
            @Parameter(description = "true＝只列軟刪除的專案（OPERATOR 以上）；false／省略＝只列未軟刪除者")
            @RequestParam(defaultValue = "false") boolean deleted,
            Authentication authentication) {
        requireOperatorToSeeDeleted(deleted, authentication);
        String[] parts = sort.split(",", 2);
        SortField field = parseSortField(parts[0]);
        boolean ascending = parseDirection(parts.length > 1 ? parts[1] : "asc");
        ListQuery query = new ListQuery(q, status, deleted, field, ascending, page, size);
        return ApiResult.ok(PageData.of(projects.list(query), ProjectSummaryResponse::from));
    }

    @GetMapping("/{id}")
    @Operation(summary = "查詢專案詳情", description = "含目標摘要清單（每個目標的任務數與已完成數）")
    public ApiResult<ProjectDetailResponse> get(@PathVariable UUID id) {
        return ApiResult.ok(ProjectDetailResponse.from(projects.get(id)));
    }

    @PutMapping("/{id}")
    @Operation(summary = "更新專案", description = "EXECUTING 狀態只准改 name／description，其他欄位有變更回 409")
    public ApiResult<ProjectResponse> update(@PathVariable UUID id, @Valid @RequestBody UpdateProjectRequest request) {
        return ApiResult.ok(ProjectResponse.from(projects.update(id, request.toDomain())));
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(summary = "刪除專案（軟刪除）", description = "is_deleted=true、status=ARCHIVED，連帶軟刪目標與任務；EXECUTING 回 409")
    public void delete(@PathVariable UUID id) {
        projects.delete(id);
    }

    @PostMapping("/{id}/restore")
    @Operation(summary = "復原軟刪除的專案（v1.2 補充端點）",
            description = "復原專案與同一次刪除連帶軟刪的目標／任務（以相同的 deleted_at 辨識；單獨先刪除的目標／任務不回來）；專案 status "
                    + "還原為刪除前的狀態（升級前就已軟刪者：未 signoff → DRAFT、已 signoff → READY）。前置：專案已軟刪除，且 deleted_at 在"
                    + "保留期內（console.retention.soft-delete-days，預設 30 天；與清除排程是否開啟無關）。找不到該 id（含已被清除）→ 404；"
                    + "未被刪除 → 409 project_not_deleted；已逾保留期 → 409 restore_window_expired。寫 audit（project.restore）")
    public ApiResult<ProjectDetailResponse> restore(@PathVariable UUID id) {
        return ApiResult.ok(ProjectDetailResponse.from(projects.restore(id)));
    }

    @PostMapping("/{id}/signoff")
    @Operation(summary = "人工 signoff 專案草案", description = "approver 必填、非空白；缺漏回 400；已 signoff 回 409")
    public ApiResult<ProjectResponse> signoff(@PathVariable UUID id, @Valid @RequestBody SignoffRequest request) {
        return ApiResult.ok(ProjectResponse.from(projects.signoff(id, request.approver())));
    }

    /**
     * {@code deleted=true} 只准 OPERATOR 以上（契約 §1.6.2）：VIEWER 回 403 {@code ACCESS_DENIED}（與安全層的角色不足同一個 reason）。
     * 路徑層級的 RBAC 對 GET 一律放行 VIEWER，所以這個角色限制只能在這裡檢查（與 {@code reveal=true} 同型）。
     */
    private static void requireOperatorToSeeDeleted(boolean deleted, Authentication authentication) {
        if (!deleted) {
            return;
        }
        boolean allowed = authentication != null && authentication.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .anyMatch(a -> ("ROLE_" + Role.OPERATOR.name()).equals(a) || ("ROLE_" + Role.ADMIN.name()).equals(a));
        if (!allowed) {
            throw new ForbiddenException("權限不足：檢視已刪除的專案需要 OPERATOR 以上的角色", ErrorReasons.ACCESS_DENIED);
        }
    }

    private static SortField parseSortField(String raw) {
        return switch (raw.strip().toLowerCase(Locale.ROOT)) {
            case "name" -> SortField.NAME;
            case "status" -> SortField.STATUS;
            case "createdat" -> SortField.CREATED_AT;
            case "updatedat" -> SortField.UPDATED_AT;
            default -> throw ValidationException.of("sort", "sort 欄位只能是 name、status、createdAt、updatedAt");
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
