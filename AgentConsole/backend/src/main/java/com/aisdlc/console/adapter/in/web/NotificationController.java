package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.NotificationSummaryResponse;
import com.aisdlc.console.application.port.in.NotificationUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 通知與待辦計數端點（API-NTF-01；契約 §1.4.1）。任何已登入角色可讀。 */
@RestController
@RequestMapping("/api/v1/notifications")
@Tag(name = "專案監控", description = "Phase 5；API-MON／API-ALR／API-NTF")
public class NotificationController {

    private final NotificationUseCase notifications;

    public NotificationController(NotificationUseCase notifications) {
        this.notifications = notifications;
    }

    @GetMapping("/summary")
    @Operation(summary = "通知與待辦計數（補充端點，ADR-001 G-17）",
            description = "供頂列通知鈴與 signoff 佇列徽章。pendingSignoffs＝專案、目標、任務三表中未 signoff 且未軟刪的列數"
                    + "＋待審批的匯入記錄數；輪詢間隔不得小於 monitor.refreshIntervalMs（預設與最小 10 秒）")
    public ApiResult<NotificationSummaryResponse> summary() {
        return ApiResult.ok(NotificationSummaryResponse.from(notifications.summary()));
    }
}
