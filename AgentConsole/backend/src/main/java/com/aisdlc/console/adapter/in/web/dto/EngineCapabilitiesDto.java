package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.execution.EngineCapabilities;
import com.aisdlc.console.domain.model.execution.EngineCapabilityState;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * 該批次 spawn 時 Console「實際送進引擎」的能力狀態（契約 §1.2.1、§3.4.2；D-11）。兩個欄位描述的是「Console 送進引擎的、與引擎
 * 因此會做的」，不是使用者的設定。{@code ExecutionRunResponse}／{@code ExecutionRunDetailResponse} 才帶它，批次列表項沒有。
 */
@Schema(name = "EngineCapabilities", description = "v1.3（D-11）：該批次 spawn 時 Console 實際送進引擎的能力狀態（契約 §3.4.2 決策表）。"
        + "autoMutation 對映引擎鍵 minimax.enable_kernel_brain（Brain 逐步校正：失敗步驟尚有重試次數時先由 Brain 改寫 prompt 再重試，"
        + "Brain 呼叫失敗則該步驟直接升級；實務上只有 prompt 改寫，不含步驟變異）；selfEvolution：引擎沒有演化開關，"
        + "有金鑰就是 ENABLED，與旗標和等級都無關（失敗型 ESCALATION 時由 Brain 產生演化「提案」，只寫引擎日誌，不套用、不重載）；"
        + "沒有金鑰時，有人要求（agent.enableSelfEvolution 或等級 ≥ 7）為 UNAVAILABLE_NO_API_KEY，否則 OFF")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record EngineCapabilitiesDto(
        @NotNull @Schema(description = "ENABLED＝已送進引擎且引擎會做；OFF＝沒有人要求（或有金鑰且明確送 enable_kernel_brain=false）；"
                + "UNAVAILABLE_NO_API_KEY＝有人要求但 Console 沒有金鑰可送（不送 minimax.*，批次照常執行，只是沒有 Brain）")
        EngineCapabilityState autoMutation,
        @NotNull @Schema(description = "同 autoMutation 的值域；有金鑰恆為 ENABLED（語意是「只產生演化提案、不套用」）")
        EngineCapabilityState selfEvolution) {

    /** null（V10 之前建立的批次）→ null，欄位缺席。 */
    public static EngineCapabilitiesDto from(EngineCapabilities capabilities) {
        return capabilities == null ? null
                : new EngineCapabilitiesDto(capabilities.autoMutation(), capabilities.selfEvolution());
    }
}
