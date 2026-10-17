package com.aisdlc.console.adapter.in.web;

import com.aisdlc.console.adapter.in.web.dto.ApiResult;
import com.aisdlc.console.adapter.in.web.dto.SddEngineStatusResponse;
import com.aisdlc.console.application.port.in.SddEngineUseCase;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.UUID;

/** 引擎狀態端點（API-ENG-01、API-ENG-02；契約 §1.7、§1.10.4；D-16）：目前只有 AISDLC_SDD。VIEWER 以上可讀（落在 {@code GET /api/v1/**} 的既有規則）。 */
@RestController
@RequestMapping("/api/v1/engines")
@Tag(name = "專案監控", description = "Phase 5；API-MON／API-ALR／API-NTF")
public class EnginesController {

    private final SddEngineUseCase sdd;

    public EnginesController(SddEngineUseCase sdd) {
        this.sdd = sdd;
    }

    @GetMapping("/sdd")
    @Operation(operationId = "getSddEngineStatus", summary = "AISDLC_SDD 引擎狀態（只讀；v1.4 補充端點，D-16）",
            description = "Console 對 FSM 狀態的唯一消費點（監控頁「AISDLC_SDD 引擎」卡；PRD §0.3：FSM-STATE 是 Console 對 SDD 的遙測來源）。"
                    + "依序呼叫 Bridge 的 GET /sdd/version、GET /sdd/fsm，帶了 project 時再呼叫 GET /sdd/fsm/{project}；三者全是唯讀，"
                    + "console-api 不寫 SDD 目錄、不寫任何 FSM-STATE 檔（ADR-001 D22）。每個呼叫 2 秒／3 秒逾時、不重試、失敗即短路。"
                    + "引擎不可用也回 200（沿用「Bridge 不可達回 200」的慣例）：available=false 並以 reason 說明"
                    + "（bridge_unreachable／sdd_unavailable／bridge_error）；帶了 project 而找不到或讀不動時 available 仍為 true、"
                    + "fsm=null、reason 為 fsm_not_found／fsm_state_unreadable。reason 是回應欄位，不是 ApiError.reason。"
                    + "project 省略 → fsm=null（不帶 reason），由前端依 projects 選一個再帶 project 重取。"
                    + "FSM 狀態檔只在 SDD runtime 執行時才變動，前端 30 秒輪詢一次，不走 SSE（ADR-001 D22）。"
                    + "build/reports/ 被 git 忽略，乾淨 clone 沒有 FSM 狀態檔：available=true、projects=[] 是正常狀態。"
                    + "Bridge 清單裡讀不動的檔名（errors[]）只記日誌，不轉發。"
                    + "v1.5（D-115-02、D-115-14）：新增選填 projectId——帶了就讀「該專案」的 FSM（root＝專案的 executionPath；專案不存在或已軟刪除 → 404，"
                    + "不是 UUID → 400）；project 省略時預設取該專案的有效 FSM 專案（sddProject 有值取它，否則專案名；Backend 不淨化，值原樣交給 Bridge）。"
                    + "fsm 新增 phase／escalationHistory／escalationProvenance／fsmProject／recovery（皆選填，舊版 Bridge 缺鍵時補預設）；"
                    + "reason 新增 sdd_root_rejected（projectId 的專案根被 Bridge 拒絕：仍回 200、available=true、projects=[]、fsm=null）。")
    public ApiResult<SddEngineStatusResponse> sddEngine(
            @Parameter(description = "選填（v1.5）。帶了＝以該 Console 專案的 executionPath 為 root 讀它的 FSM；專案不存在或已軟刪除 → 404，不是 UUID → 400。"
                    + "省略＝v1.4 行為（讀 Bridge 預設的狀態目錄）", schema = @Schema(type = "string", format = "uuid"))
            @RequestParam(required = false) UUID projectId,
            @Parameter(description = "FSM 專案名的有效值（可以是原名；v1.5 起 Console 不淨化，只驗長度與控制字元，由 Bridge 的淨化鏡像處理）；"
                    + "1～200 字元、不含控制字元，不合 → 400。省略 → 沒有 projectId 時 fsm=null；帶了 projectId 時取該專案的有效 FSM 專案",
                    schema = @Schema(type = "string", minLength = 1, maxLength = 200, pattern = "^[^\\x00-\\x1f\\x7f]{1,200}$"))
            @RequestParam(required = false) String project) {
        return ApiResult.ok(SddEngineStatusResponse.from(sdd.status(project, projectId)));
    }
}
