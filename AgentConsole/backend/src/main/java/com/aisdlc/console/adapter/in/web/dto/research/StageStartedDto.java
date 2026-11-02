package com.aisdlc.console.adapter.in.web.dto.research;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

/**
 * 階段已啟動（契約 API-RP-11 的 202）：Bridge 回 {@code {stage_run_id, engine_run_id, flow:{step,phase,status}}}，這裡只取契約的三欄。進度由 SSE 的
 * {@code research.run}（stage、roundNo、attempt、stageRunId、engineRunId、status）事件與 {@code research.step} 游標事件取得。
 */
@Schema(name = "ResearchStageStarted", description = "階段已啟動（202）：stage run id 與啟動後的流程相態")
public record StageStartedDto(
        @NotNull String stageRunId,
        @NotNull String flowPhase,
        @NotNull @Schema(description = "IDLE｜RUNNING｜WAITING_HUMAN｜BLOCKED｜ESCALATED｜FAILED｜CANCELLED｜COMPLETED") String flowStatus) {

    public static StageStartedDto from(Map<String, Object> body) {
        Map<String, Object> flow = Iso.map(body.get("flow"));
        return new StageStartedDto(Iso.text(body.get("stage_run_id"), ""), Iso.text(flow.get("phase"), ""), Iso.text(flow.get("status"), ""));
    }
}
