package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.ProjectDetailResponse;
import com.aisdlc.console.adapter.in.web.dto.SddBindingRequest;
import com.aisdlc.console.adapter.in.web.dto.SddFreezeRequest;
import com.aisdlc.console.adapter.in.web.dto.SddFsmStateDto;
import com.aisdlc.console.application.port.in.SddGovernanceUseCase;
import com.aisdlc.console.domain.exception.ValidationException;
import com.aisdlc.console.domain.exception.Violations;
import com.aisdlc.console.domain.service.SddBindingRules;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.util.Map;
import java.util.UUID;

/**
 * SDD 治理端點（v1.5；契約 §1.10.2、§1.10.7；API-SGN-06、API-PRJ-08）：核准凍結與編輯專案的 FSM 專案。寫入端點：OPERATOR／ADMIN
 * （落在非 GET 的既有規則；VIEWER → 403 {@code ACCESS_DENIED}）。
 */
@RestController
@RequestMapping("/api/v1/projects")
@Tag(name = "專案管理")
public class SddGovernanceController {

    private final SddGovernanceUseCase governance;

    public SddGovernanceController(SddGovernanceUseCase governance) {
        this.governance = governance;
    }

    @PostMapping("/{id}/sdd/freeze")
    @Operation(operationId = "freezeProjectSddSpec", summary = "核准凍結 SDD 規格（人工閘；v1.5，D-115-03）",
            description = "PRD §0.4 把 Console 的 signoff 對映 FSM 的 HUMAN_PENDING：本端點是 Console 對 FSM 唯一的寫入動詞，HUMAN_PENDING→SPEC_FROZEN，"
                    + "帶 approver（一律取 JWT subject，不可由 client 指定）、理由與文件摘要。驗證順序固定：專案存在（404）→ 請求驗證（400）→ "
                    + "backend 沒有設定寫入權杖（503 sdd_write_disabled）→ 唯讀取標準鍵（Bridge GET /sdd/fsm/{project}?root=）→ 綁定唯一性與寫回"
                    + "（409 sdd_binding_conflict；獨立短交易、先於 Bridge 寫入）→ Bridge POST /sdd/fsm/{project}:freeze（帶 X-Bridge-Token，"
                    + "讀取逾時 40 秒、不重試）。Bridge 失敗對映：fsm_state_conflict→409 sdd_fsm_state_conflict；fsm_not_found→409 sdd_fsm_not_found；"
                    + "spec_digest_changed→409 sdd_spec_digest_changed；422→引擎拒絕此請求；503 sdd_write_disabled→503；403 sdd_write_forbidden→"
                    + "502（設定缺陷）。非冪等：第二次呼叫（FSM 已不在 HUMAN_PENDING）→ 409 sdd_fsm_state_conflict。寫 audit（project.sdd.freeze）。"
                    + "成功 200：凍結後的 FSM 狀態（與 GET /engines/sdd 的 fsm 同形）。")
    public ApiResult<SddFsmStateDto> freeze(@PathVariable UUID id, @RequestBody SddFreezeRequest request,
                                            Principal principal) {
        return ApiResult.ok(SddFsmStateDto.from(governance.freeze(id, request.toDomain(), principal.getName())));
    }

    @PutMapping("/{id}/sdd-binding")
    @Operation(operationId = "updateProjectSddBinding", summary = "編輯專案的 FSM 專案（改綁；v1.5，D-115-14）",
            description = "存入去前後空白後的值（非 null 時 1～100 字元、不含控制字元；null＝清除，回到「用預設」＝專案名；鍵缺席 → 400），"
                    + "不檢查狀態檔是否存在、不呼叫 Bridge；先檢查唯一性（同 executionPath 已有未刪除專案以同一個 sddProject 綁定 → 409 "
                    + "sdd_binding_conflict）；相同值再送＝冪等（200，不寫稽核）。改綁不搬移 FSM 狀態檔，也不影響進行中的批次。"
                    + "寫 audit（project.sdd.bind）。",
            requestBody = @io.swagger.v3.oas.annotations.parameters.RequestBody(required = true,
                    content = @Content(schema = @Schema(implementation = SddBindingRequest.class))))
    public ApiResult<ProjectDetailResponse> updateBinding(@PathVariable UUID id, @RequestBody Map<String, Object> body) {
        if (body == null || !body.containsKey("sddProject")) {
            throw ValidationException.of("sddProject", "sddProject 為必填（要清除綁定請傳 null）");
        }
        Object value = body.get("sddProject");
        if (value != null && !(value instanceof String)) {
            throw ValidationException.of("sddProject", "sddProject 必須是字串或 null");
        }
        // 契約 §1.10.7 的 400 列是 Bean Validation：請求本文的格式問題（空白、過長、控制字元）先於資源查找（404）；
        // 用例仍會再驗一次同一條規則（冪等），所以直接呼叫用例的人也守得住。
        Violations violations = new Violations();
        String stored = SddBindingRules.storedProject(violations, "sddProject", (String) value);
        violations.throwIfAny();
        return ApiResult.ok(ProjectDetailResponse.from(governance.bind(id, stored)));
    }
}
