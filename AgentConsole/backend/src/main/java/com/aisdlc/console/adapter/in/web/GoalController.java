package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.CreateGoalRequest;
import com.aisdlc.console.adapter.in.web.dto.GoalDetailResponse;
import com.aisdlc.console.adapter.in.web.dto.GoalResponse;
import com.aisdlc.console.adapter.in.web.dto.GoalSummaryResponse;
import com.aisdlc.console.adapter.in.web.dto.ReorderRequest;
import com.aisdlc.console.adapter.in.web.dto.SignoffRequest;
import com.aisdlc.console.adapter.in.web.dto.UpdateGoalRequest;
import com.aisdlc.console.application.port.in.ManageGoalUseCase;
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

/** 目標管理端點（PRD §7.1.2、§7.1.4.1 的目標 signoff）。讀取：任何已登入角色；寫入：OPERATOR／ADMIN。 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "目標管理")
public class GoalController {

    private final ManageGoalUseCase goals;

    public GoalController(ManageGoalUseCase goals) {
        this.goals = goals;
    }

    @PostMapping("/projects/{projectId}/goals")
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "建立目標", description = "dependsOn 以 Kahn 試算防環；成環／自依賴／跨專案回 400")
    public ApiResult<GoalResponse> create(@PathVariable UUID projectId, @Valid @RequestBody CreateGoalRequest request) {
        return ApiResult.created(GoalResponse.from(goals.create(projectId, request.toDomain())));
    }

    @GetMapping("/projects/{projectId}/goals")
    @Operation(summary = "查詢目標列表", description = "依 sortOrder 排序；含任務數、已完成數與完成比例（只算未軟刪）")
    public ApiResult<List<GoalSummaryResponse>> list(@PathVariable UUID projectId) {
        return ApiResult.ok(goals.list(projectId).stream().map(GoalSummaryResponse::from).toList());
    }

    @GetMapping("/goals/{id}")
    @Operation(summary = "查詢目標詳情", description = "含依賴目標 id 與任務標題清單")
    public ApiResult<GoalDetailResponse> get(@PathVariable UUID id) {
        return ApiResult.ok(GoalDetailResponse.from(goals.get(id)));
    }

    @PutMapping("/goals/{id}")
    @Operation(summary = "更新目標", description = "dependsOn：null＝不變、空陣列＝清除、有值＝整組取代（Kahn 防環）")
    public ApiResult<GoalResponse> update(@PathVariable UUID id, @Valid @RequestBody UpdateGoalRequest request) {
        return ApiResult.ok(GoalResponse.from(goals.update(id, request.toDomain())));
    }

    @DeleteMapping("/goals/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(summary = "刪除目標（軟刪除）",
            description = "連帶軟刪其下任務；所屬專案有進行中批次（INITIALIZING／RUNNING／PAUSED）回 409 reason=project_executing"
                    + "（details＝{projectId, runId}；v1.2，C-8）；其次，含 RUNNING 任務回 409")
    public void delete(@PathVariable UUID id) {
        goals.delete(id);
    }

    @PutMapping("/goals/reorder")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Operation(summary = "調整目標順序", description = "orderedGoalIds 須恰好是專案下全部（未刪除）目標，依新順序重寫 sortOrder")
    public void reorder(@Valid @RequestBody ReorderRequest request) {
        goals.reorder(request.projectId(), request.orderedGoalIds());
    }

    @PostMapping("/goals/{id}/signoff")
    @Operation(summary = "人工 signoff 目標草案", description = "approver 必填、非空白；缺漏回 400；已 signoff 回 409")
    public ApiResult<GoalResponse> signoff(@PathVariable UUID id, @Valid @RequestBody SignoffRequest request) {
        return ApiResult.ok(GoalResponse.from(goals.signoff(id, request.approver())));
    }
}
