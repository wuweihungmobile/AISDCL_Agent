package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.application.port.in.ResearchKanbanUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/**
 * 看板投影（API-RP-26；PKG-API-P2）。<b>唯讀、零寫入、零 Bridge 寫入請求</b>；沒有任何 execute／pause／resume／cancel／stop／restore／review 路徑片段
 * （既有執行控制端點不重造，由 {@code ResearchKanbanRouteInventoryTest} 鎖住）。VIEWER 以上可讀。
 */
@RestController
@RequestMapping("/api/v1/research/projects/{id}")
@Tag(name = "研發工作流（ResearchToPRD）")
public class ResearchKanbanController {

    private final ResearchKanbanUseCase kanban;

    public ResearchKanbanController(ResearchKanbanUseCase kanban) {
        this.kanban = kanban;
    }

    @GetMapping("/kanban")
    @Operation(operationId = "getResearchKanban", summary = "研究專案看板投影（API-RP-26；VIEWER 以上；唯讀）",
            description = "console-api 聚合五欄（Task 拆解、測試規格產生、程式碼實作、自癒修復、回歸驗收）加待審清單與內環閘決定（SCG4、SCG5、SCG6 各最近 5 筆，decidedAt 新到舊）。"
                    + "各欄完成判定與來源端點共用同一份計算。Bridge 不可達：200、bridgeReachable＝false、stale＝true、FSM 衍生欄為 null 並帶 unknown＝true，"
                    + "任務計數、拆解、待審與決定取資料庫即時值，snapshotAt＝專案更新時間、最新事件與最新決定三者的最大值。研究專案不存在＝404 research_not_found。")
    public ApiResult<ResearchKanbanUseCase.Kanban> kanban(@Parameter(description = "研究專案 id（UUID）") @PathVariable UUID id) {
        return ApiResult.ok(kanban.kanban(id));
    }
}
