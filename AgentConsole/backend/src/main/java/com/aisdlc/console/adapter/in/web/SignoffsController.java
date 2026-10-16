package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.PendingSignoffsResponse;
import com.aisdlc.console.application.port.in.SignoffQueueUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** 待審批清單端點（API-SGN-05／US-E-07；契約 §1.8；D-18）。VIEWER 以上可讀（落在 {@code GET /api/v1/**} 的既有規則）。 */
@RestController
@RequestMapping("/api/v1/signoffs")
@Tag(name = "BRD/PRD 匯入", description = "Phase 3；API-IMP／API-SGN")
public class SignoffsController {

    private final SignoffQueueUseCase queue;

    public SignoffsController(SignoffQueueUseCase queue) {
        this.queue = queue;
    }

    @GetMapping("/pending")
    @Operation(operationId = "getPendingSignoffs", summary = "待簽核的草案清單（跨專案；v1.4 補充端點，D-18）",
            description = "列出待 signoff 的草案：專案、目標、任務與待審批的匯入記錄四種，判準與通知摘要的 pendingSignoffs 完全相同"
                    + "（PROJECT：signed_off=false 且未軟刪；GOAL／TASK：另要求所屬專案（與目標）未軟刪；IMPORT：PARSED／REVIEWING 且未 signoff），"
                    + "計數與清單的述詞由同一處產生，不變量：counts.total 恆等於 GET /notifications/summary 的 pendingSignoffs。"
                    + "排序 created_at 升冪（同值以 id 升冪）；limit 只截斷 items（預設 50、上限 200），不影響 counts。"
                    + "IMPORT 項的 projectId／projectName／parentId 為 null（匯入記錄在 confirm 之前還沒有專案）。"
                    + "供儀表板「待人工審批」卡；取代前端用專案與目標 API 另組的近似清單（完整性審查 I-05）。")
    public ApiResult<PendingSignoffsResponse> pending(
            @Parameter(description = "清單最多回幾筆（預設 50，範圍 1～200）；不影響 counts",
                    schema = @Schema(type = "integer", format = "int32", minimum = "1", maximum = "200", defaultValue = "50"))
            @RequestParam(defaultValue = "50") int limit) {
        return ApiResult.ok(PendingSignoffsResponse.from(queue.pending(limit)));
    }
}
