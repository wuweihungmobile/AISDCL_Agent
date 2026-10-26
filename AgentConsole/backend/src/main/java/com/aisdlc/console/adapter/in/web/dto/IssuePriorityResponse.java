package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.issue.IssuePriority;
import io.swagger.v3.oas.annotations.media.Schema;

import java.time.OffsetDateTime;

/** {@code PUT /api/v1/issues/{id}/priority} 的 {@code data}（TCS-IssueCenter-20261027 §C4.3）：寫入的那一列。 */
@Schema(name = "IssuePriority", description = "議題的優先順序（Console 自有；一個議題最多一列）")
public record IssuePriorityResponse(
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "議題編號") String id,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, minimum = "1", maximum = "9999", description = "順位（1 最先）") int rank,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, maxLength = 200, description = "備註（可為空字串）") String note,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "設定者（JWT 帳號）") String setBy,
        @Schema(requiredMode = Schema.RequiredMode.REQUIRED, description = "設定時間（伺服器時間，ISO-8601 帶 offset）") OffsetDateTime setAt) {

    public static IssuePriorityResponse from(IssuePriority row) {
        return new IssuePriorityResponse(row.issueId(), row.rank(), row.note(), row.setBy(), row.setAt());
    }
}
