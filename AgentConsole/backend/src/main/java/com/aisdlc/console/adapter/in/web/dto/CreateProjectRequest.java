package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.project.NewProject;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** 建立專案請求（PRD §5.1.1）。 */
public record CreateProjectRequest(
        @NotBlank(message = "名稱不能為空") @Size(max = 200, message = "名稱長度不可超過 200 字元") String name,
        @NotBlank(message = "執行路徑不能為空") @Size(max = 500, message = "執行路徑長度不可超過 500 字元")
        @Schema(description = "專案執行路徑，必須是絕對路徑（POSIX 或 Windows）") String executionPath,
        @NotBlank(message = "通過標準不能為空") String passCriteria,
        String description,
        @Min(value = 1, message = "自治等級必須介於 1 到 10") @Max(value = 10, message = "自治等級必須介於 1 到 10")
        @Schema(description = "自治等級 1～10，預設 3") Integer autonomyLevel,
        @Schema(description = "true＝草案（signedOff=false，需另外 signoff）；預設 false＝手動建立（signedOff=true）")
        Boolean draft) {

    public NewProject toDomain() {
        return new NewProject(name, executionPath, passCriteria, description, autonomyLevel, Boolean.TRUE.equals(draft));
    }
}
