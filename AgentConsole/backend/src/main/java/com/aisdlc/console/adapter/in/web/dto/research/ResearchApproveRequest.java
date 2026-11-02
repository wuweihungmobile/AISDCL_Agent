package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchCommandUseCase.ApproveInput;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import io.swagger.v3.oas.annotations.media.Schema;

import java.util.Map;

/**
 * Gate 0 核准的請求本文（契約 API-RP-12；僅 ADMIN）。<b>本文型別沒有 approver 欄</b>：核准人一律取 JWT subject，多帶的欄位（含 {@code approver}）被忽略
 * （先例 {@code SddFreezeRequest}）。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
@Schema(name = "ResearchApproveRequest", description = "核准 PRD（Gate 0）：prdVersion（head 版號）、expectedDigests（核准人當時看到的檔案摘要）、reason")
public record ResearchApproveRequest(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, minimum = "1", description = "要核准的 PRD 版號（整數 versionNo；須為 head 且有通過的審查輪）") Integer prdVersion,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "相對 POSIX 路徑 → sha256:<64 位小寫十六進位>；須涵蓋 head PRD、00_research/evidence_matrix.md、"
                + "00_research/issue_scope.json、01_specs/adr_draft.md") Map<String, String> expectedDigests,
        @Schema(maxLength = 500, description = "核准理由（選填；有的話 1～500 字）") String reason) {

    public ApproveInput toInput() {
        return new ApproveInput(prdVersion, expectedDigests, reason);
    }
}
