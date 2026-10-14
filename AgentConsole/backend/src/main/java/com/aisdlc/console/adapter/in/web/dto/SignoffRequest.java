package com.aisdlc.console.adapter.in.web.dto;

import jakarta.validation.constraints.NotBlank;

/** signoff 請求（PRD §7.1.4.1）：approver 必填、非空白、不可匿名，缺漏回 400。 */
public record SignoffRequest(
        @NotBlank(message = "approver 不可為空（人工 signoff 不可匿名）") String approver) {
}
