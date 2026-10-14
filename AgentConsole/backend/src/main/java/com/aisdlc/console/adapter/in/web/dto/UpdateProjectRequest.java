package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.project.ProjectStatus;
import com.aisdlc.console.domain.model.project.ProjectUpdate;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;

/**
 * 更新專案請求；所有欄位選填，未提供（null）＝不變更。EXECUTING 狀態只准改 name／description，
 * 其他欄位有變更回 409（附 reason）。
 */
public record UpdateProjectRequest(
        @Size(max = 200, message = "名稱長度不可超過 200 字元") String name,
        @Size(max = 500, message = "執行路徑長度不可超過 500 字元") String executionPath,
        String passCriteria,
        @Schema(description = "給空白字串＝清除說明") String description,
        @Min(value = 1, message = "自治等級必須介於 1 到 10") @Max(value = 10, message = "自治等級必須介於 1 到 10")
        Integer autonomyLevel,
        @Schema(description = "手動狀態轉移的目標，本版只開放 DRAFT／READY；其餘狀態由執行引擎事件驅動，要求其他值回 409")
        ProjectStatus status) {

    public ProjectUpdate toDomain() {
        return new ProjectUpdate(name, executionPath, passCriteria, description, autonomyLevel, status);
    }
}
