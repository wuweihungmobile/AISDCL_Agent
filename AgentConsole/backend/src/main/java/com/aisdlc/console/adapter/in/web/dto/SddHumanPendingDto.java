package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.engine.SddFsmState;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;
import java.util.Map;

/**
 * 待人工確認（契約 §1.7.1、§3.1.3；D-16）。現行 FSM-STATE 的 {@code human_pending_tracking} 是<b>單一映射</b>：{@code entered_at} 有值 →
 * {@code count=1}、{@code items=[該映射原樣]}；否則 0 與空陣列；所以 {@code count} 實務上只會是 0 或 1。{@code items} 的內容原樣
 * （保留 snake_case 鍵）。
 */
@Schema(name = "SddHumanPending", description = "待人工確認（v1.4，D-16）：entered_at 有值 → count=1、items=[該映射原樣]；否則 count=0、items=[]；"
        + "若來源是 list，count＝筆數、items＝尾 5 筆原樣。count 實務上只會是 0 或 1。items 的內容原樣＝FSM 檔寫什麼就是什麼（保留 snake_case 鍵）")
public record SddHumanPendingDto(
        @NotNull @Schema(minimum = "0") int count,
        @NotNull @ArraySchema(maxItems = 5, arraySchema = @Schema(description = "原樣的項目（最多 5 筆）"))
        List<Map<String, Object>> items) {

    public static SddHumanPendingDto from(SddFsmState.HumanPending pending) {
        return new SddHumanPendingDto(pending.count(), pending.items());
    }
}
