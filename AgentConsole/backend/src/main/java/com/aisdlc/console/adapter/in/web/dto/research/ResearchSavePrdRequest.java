package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.SavePrdInput;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

/** 存 PRD 新版（契約 API-RP-09）：樂觀鎖 {@code baseVersion}（須是目前 head 版號，否則 409 {@code prd_version_conflict}）；作者一律取 JWT subject。 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "ResearchSavePrdRequest", description = "存 PRD 新版：baseVersion（目前 head）、content（≤1 MiB、UTF-8、無 NUL）、changeSummary")
public record ResearchSavePrdRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, minimum = "0", description = "目前 head 版號（尚無版本為 0）") Integer baseVersion,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "PRD 全文（Markdown）") String content,
        @Schema(maxLength = 500) String changeSummary) {

    public SavePrdInput toInput() {
        return new SavePrdInput(baseVersion, content, changeSummary);
    }
}
