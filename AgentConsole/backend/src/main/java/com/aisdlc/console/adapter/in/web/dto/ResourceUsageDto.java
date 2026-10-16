package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.execution.ResourceUsage;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * 引擎行程樹的資源取樣（契約 §1.2.3、§3.1.2；D-12；US-M-10）：Bridge {@code RunStateOut.resources} 的投影，值原樣帶出。
 * 不含 pid、命令列與環境變數；「沒有資料」不用本物件表達，而是 {@code BridgeInfo.resources} 為 null（或缺席）。
 */
@Schema(name = "ResourceUsage", description = "引擎行程樹的資源取樣（v1.3，D-12；Bridge RunStateOut.resources 的投影，規格見契約 §3.1.2）："
        + "Bridge 背景每 5 秒以 psutil 取樣一次，請求路徑只回最近一筆；不含 pid、命令列與環境變數")
public record ResourceUsageDto(
        @NotNull @Schema(minimum = "0", maximum = "100", description = "整機正規化的 CPU 百分比＝行程樹各行程 cpu_percent 總和 ÷ 邏輯核心數，"
                + "小數 1 位；取樣器第一筆可為 0.0") double cpuPercent,
        @NotNull @Schema(minimum = "0", description = "行程樹各行程 RSS 的總和（bytes）") long memoryBytes,
        @NotNull @Schema(minimum = "1", description = "取樣當下仍存活的行程數（含引擎根行程）") int processCount,
        @NotNull @Schema(type = "string", format = "date-time",
                description = "取樣時間（ISO-8601 含 offset；Bridge 一律 UTC，值原樣帶出）") String sampledAt) {

    public static ResourceUsageDto from(ResourceUsage usage) {
        return usage == null ? null
                : new ResourceUsageDto(usage.cpuPercent(), usage.memoryBytes(), usage.processCount(), usage.sampledAt());
    }
}
