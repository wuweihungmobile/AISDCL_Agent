package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.signoff.PendingSignoffCounts;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/** 四種草案各自的待簽核數與總和（契約 §1.8.1；D-18）。{@code total} 恆等於 {@code GET /notifications/summary} 的 {@code pendingSignoffs}。 */
@Schema(name = "PendingSignoffCounts", description = "四種草案各自的待簽核數與總和（v1.4，D-18）。total 恆等於 GET /notifications/summary 的 "
        + "pendingSignoffs（同一組述詞、同一判準；limit 不影響本物件）")
public record PendingSignoffCountsDto(
        @NotNull @Schema(minimum = "0") int projects,
        @NotNull @Schema(minimum = "0") int goals,
        @NotNull @Schema(minimum = "0") int tasks,
        @NotNull @Schema(minimum = "0") int imports,
        @NotNull @Schema(minimum = "0", description = "四者之和") int total) {

    public static PendingSignoffCountsDto from(PendingSignoffCounts counts) {
        return new PendingSignoffCountsDto(counts.projects(), counts.goals(), counts.tasks(), counts.imports(),
                counts.total());
    }
}
