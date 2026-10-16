package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.application.port.in.ExecutionQueryUseCase.BridgeInfoView;
import com.aisdlc.console.domain.model.execution.BridgeStatus;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;

/** Engine Bridge 的連線資訊（契約 §1.2.3）：不外露 pid 與 lock key。 */
@Schema(name = "BridgeInfo")
@JsonInclude(JsonInclude.Include.NON_NULL)
public record BridgeInfoDto(
        @NotNull @Schema(description = "Bridge 是否可達（網路層）；false 時進度欄位為 DB 衍生值") boolean connected,
        @Schema(description = "Bridge 實例識別（bridge_instance）；不含 pid、lock key") String instance,
        BridgeStatus status,
        @Schema(description = "Bridge 可達但回 404 run_not_found 時為 false（workspace 已清除）") Boolean runKnown,
        @NotNull Instant checkedAt,
        @Schema(description = "v1.3（D-12；US-M-10）：引擎行程樹的資源取樣（Bridge GET /autoclaude/runs/{id} 回應的 resources，規格見契約 §3.1.2）。"
                + "引擎行程不存活（尚未啟動、暫停中、終態）、還沒有第一筆樣本、最近一筆樣本已超過 15 秒、Bridge 不可達（connected=false）、"
                + "runKnown=false，或 Bridge 的回應沒有這個鍵（舊版 Bridge）時為 null 或缺席。"
                + "只有 GET /executions/{runId}（ExecutionRunDetailResponse.bridge）帶 bridge 物件；pause／resume／cancel／restore 的快照沒有")
        ResourceUsageDto resources) {

    public static BridgeInfoDto from(BridgeInfoView v) {
        return new BridgeInfoDto(v.connected(), v.instance(), v.status(), v.runKnown(), v.checkedAt(),
                ResourceUsageDto.from(v.resources()));
    }
}
