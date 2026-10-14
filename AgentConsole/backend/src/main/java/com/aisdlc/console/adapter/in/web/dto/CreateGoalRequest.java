package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.goal.NewGoal;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.util.List;
import java.util.UUID;

/** 建立目標請求（PRD §5.1.2）；專案 id 取自路徑。 */
public record CreateGoalRequest(
        @NotBlank(message = "名稱不能為空") @Size(max = 200, message = "名稱長度不可超過 200 字元") String name,
        String description,
        @NotBlank(message = "通過標準不能為空") String passCriteria,
        @Schema(description = "前置依賴目標 id；須為同一專案內、未刪除的目標；成環／自依賴／跨專案回 400") List<UUID> dependsOn,
        @Schema(description = "true＝草案（signedOff=false）；預設 false＝手動建立（signedOff=true）") Boolean draft) {

    public NewGoal toDomain() {
        return new NewGoal(name, description, passCriteria, dependsOn, Boolean.TRUE.equals(draft));
    }
}
