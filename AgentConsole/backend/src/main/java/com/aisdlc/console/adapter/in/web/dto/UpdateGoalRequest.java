package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.goal.GoalUpdate;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;

import java.util.List;
import java.util.UUID;

/** 更新目標請求；所有欄位選填，未提供（null）＝不變更。 */
public record UpdateGoalRequest(
        @Size(max = 200, message = "名稱長度不可超過 200 字元") String name,
        @Schema(description = "給空白字串＝清除說明") String description,
        String passCriteria,
        @Min(value = 0, message = "排序順序不可為負數") Integer sortOrder,
        @Schema(description = "null＝不變；空陣列＝清除全部依賴；有值＝整組取代（Kahn 防環：成環回 400，reason＝依賴成環）")
        List<UUID> dependsOn) {

    public GoalUpdate toDomain() {
        return new GoalUpdate(name, description, passCriteria, sortOrder, dependsOn);
    }
}
