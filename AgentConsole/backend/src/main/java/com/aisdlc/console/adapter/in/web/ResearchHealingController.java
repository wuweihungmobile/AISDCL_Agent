package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.application.port.in.ResearchHealingUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/** 自癒歷史（API-RP-27；PKG-API-P2）：JDBC 唯讀加記憶體快取，零 Bridge 請求；VIEWER 以上可讀。 */
@RestController
@RequestMapping("/api/v1/research/projects/{id}")
@Tag(name = "研發工作流（ResearchToPRD）")
public class ResearchHealingController {

    private final ResearchHealingUseCase healing;

    public ResearchHealingController(ResearchHealingUseCase healing) {
        this.healing = healing;
    }

    @GetMapping("/healing")
    @Operation(operationId = "getResearchHealing", summary = "自癒歷史（API-RP-27；VIEWER 以上）",
            description = "資料庫視圖 v_research_healing_attempts 的唯讀投影：每列 attempt（同任務內序號）、狀態、excerpt（error_message 先遮蔽再取尾端 300 字元）、resolved、escalated、"
                    + "specChangeForbidden。attribution 與 patchResult 引擎未提供，恆為 null。maxRetries 取系統參數 agent.maxRetries。logSyncedThrough 與 logLag 來自"
                    + "最近一次成功的 Bridge 同步（記憶體快取，重啟即空；無紀錄＝null 與 0）。專案不存在＝404 research_not_found；未綁 Console 專案＝200 空列。")
    public ApiResult<ResearchHealingUseCase.Healing> healing(@Parameter(description = "研究專案 id（UUID）") @PathVariable UUID id) {
        return ApiResult.ok(healing.healing(id));
    }
}
