package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.engine.SddFsmState;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

/**
 * 重試歷史（契約 §1.7.1、§3.1.3；D-16）。現行 FSM-STATE 的 {@code retry_history} 是以重試閘為鍵的映射：{@code count}＝各閘 {@code history}
 * 筆數的總和；{@code last}＝全部筆中 {@code date} 最晚者（原樣，另加 {@code gate} 欄＝所屬的閘名）；沒有任何一筆為 {@code count=0}、{@code last=null}。
 */
@Schema(name = "SddRetryHistory", description = "重試歷史（v1.4，D-16）：count＝各閘 history 筆數的總和；last＝全部筆中 date 最晚者"
        + "（原樣，另加 gate 欄＝所屬的重試閘名）；沒有任何一筆為 {count: 0, last: null}")
public record SddRetryHistoryDto(
        @NotNull @Schema(minimum = "0") int count,
        @NotNull @Schema(description = "最近一筆（原樣再加 gate 欄）；沒有為 null", nullable = true) Map<String, Object> last) {

    public static SddRetryHistoryDto from(SddFsmState.RetryHistory history) {
        return new SddRetryHistoryDto(history.count(), history.last());
    }
}
