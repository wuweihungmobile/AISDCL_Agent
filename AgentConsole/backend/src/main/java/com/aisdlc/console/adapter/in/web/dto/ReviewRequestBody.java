package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.execution.ReviewDecision;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** 審核請求（契約 §1.2.11）：{@code {"decision":"APPROVE|REJECT|RETRY|SKIP","comment":"≤2000 字元（選填）"}}。 */
@Schema(name = "ReviewRequest")
public record ReviewRequestBody(
        @NotNull ReviewDecision decision,
        @Size(max = 2000) String comment) {
}
