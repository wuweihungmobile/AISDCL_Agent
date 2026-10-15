package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.imports.ImportSourceType;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** 貼上純文字建立匯入記錄（契約 §1.1.2）。 */
public record TextImportRequest(
        @NotBlank(message = "內容不可為空") @Size(max = 2_000_000, message = "內容長度不可超過 2000000 字元")
        @Schema(description = "需求文字（支援 Markdown）；不可全為空白") String content,
        @Size(max = 500, message = "來源名稱長度不可超過 500 字元")
        @Schema(description = "選填的來源名稱（例：來自剪貼簿）") String sourceFileName,
        @Schema(description = "PLAIN_TEXT（預設）或 MARKDOWN；PDF／DOCX 只能由 upload 產生（其他值 400）",
                allowableValues = {"PLAIN_TEXT", "MARKDOWN"}) ImportSourceType sourceType) {
}
