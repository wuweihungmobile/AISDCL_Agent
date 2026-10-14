package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.CreateTaskRequest;
import com.aisdlc.console.adapter.in.web.dto.SignoffRequest;
import com.aisdlc.console.adapter.in.web.dto.TaskDetailResponse;
import com.aisdlc.console.adapter.in.web.dto.TaskResponse;
import com.aisdlc.console.adapter.in.web.dto.TaskSummaryResponse;
import com.aisdlc.console.adapter.in.web.dto.UpdateTaskRequest;
import com.aisdlc.console.application.port.in.ManageTaskUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

/** 任務管理端點（PRD §7.1.3、§7.1.4.1 的任務 signoff）。讀取：任何已登入角色；寫入：OPERATOR／ADMIN。 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "任務管理")
public class TaskController {

    private final ManageTaskUseCase tasks;

    public TaskController(ManageTaskUseCase tasks) {
        this.tasks = tasks;
    }

    @PostMapping("/goals/{goalId}/tasks")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "建立任務", description = "NFR-SEC-03：evaluatorCommand 命中黑名單字元、expectedOutputRegex 不可編譯皆回 400")
    public ApiResult<TaskResponse> create(@PathVariable UUID goalId, @Valid @RequestBody CreateTaskRequest request) {
        return ApiResult.created(TaskResponse.from(tasks.create(goalId, request.toDomain())));
    }

    @GetMapping("/goals/{goalId}/tasks")
    @Operation(summary = "查詢任務列表", description = "依 sortOrder 排序")
    public ApiResult<List<TaskSummaryResponse>> list(@PathVariable UUID goalId) {
        return ApiResult.ok(tasks.list(goalId).stream().map(TaskSummaryResponse::from).toList());
    }

    @GetMapping("/tasks/{id}")
    @Operation(summary = "查詢任務詳情", description = "含最近一次執行日誌與執行歷史（Phase 2 歷史為空清單）")
    public ApiResult<TaskDetailResponse> get(@PathVariable UUID id) {
        return ApiResult.ok(TaskDetailResponse.from(tasks.get(id)));
    }

    @PutMapping("/tasks/{id}")
    @Operation(summary = "更新任務", description = "可改名稱、說明、通過標準、maxRetries、evaluatorCommand、expectedOutputRegex、passCriteriaSpec")
    public ApiResult<TaskResponse> update(@PathVariable UUID id, @Valid @RequestBody UpdateTaskRequest request) {
        return ApiResult.ok(TaskResponse.from(tasks.update(id, request.toDomain())));
    }

    @DeleteMapping("/tasks/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(summary = "刪除任務（軟刪除）", description = "RUNNING 狀態的任務回 409")
    public void delete(@PathVariable UUID id) {
        tasks.delete(id);
    }

    @PostMapping("/tasks/{id}/retry")
    @Operation(summary = "手動重試任務", description = "只允許 FAILED／ESCALATED：retryCount+1、狀態轉 QUEUED；其他狀態回 409")
    public ApiResult<TaskResponse> retry(@PathVariable UUID id) {
        return ApiResult.ok(TaskResponse.from(tasks.retry(id)));
    }

    @PostMapping("/tasks/{id}/signoff")
    @Operation(summary = "人工 signoff 任務草案", description = "approver 必填、非空白；缺漏回 400；已 signoff 回 409")
    public ApiResult<TaskResponse> signoff(@PathVariable UUID id, @Valid @RequestBody SignoffRequest request) {
        return ApiResult.ok(TaskResponse.from(tasks.signoff(id, request.approver())));
    }
}
