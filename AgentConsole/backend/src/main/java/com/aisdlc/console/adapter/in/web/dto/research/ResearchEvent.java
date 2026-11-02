package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.domain.model.research.ResearchViews.Event;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

/**
 * 研究事件（契約 §1.3 {@code ResearchEvent}；{@code console.research_events} 一列，append-only，{@code seq} 每專案單調＝SSE 的 {@code id}）。
 * REST（{@code GET …/events}）與 SSE（{@code GET /stream/research/{id}}）共用這個形狀；{@code payload} 的鍵是 Bridge 寫入的原樣（依 eventType 而異）。
 */
@Schema(name = "ResearchEvent", description = "研究事件（append-only 事件帳的一列；SSE 的 data 與 REST 事件頁共用）")
public record ResearchEvent(
        @NotNull @Schema(description = "每專案單調遞增的序號＝SSE id", format = "int64") long seq,
        @NotNull @Schema(description = "research.step｜run｜source｜evidence｜prd｜review｜review_invalid｜defect｜gate｜reconcile｜route｜scr｜delivery｜alert")
        String eventType,
        @NotNull String step,
        @NotNull @Schema(description = "JWT subject 或 bridge") String actor,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String refKind,
        @Schema(nullable = true, requiredMode = Schema.RequiredMode.REQUIRED) String refId,
        @NotNull Map<String, Object> payload,
        @NotNull String occurredAt) {

    public static ResearchEvent from(Event event) {
        return new ResearchEvent(event.seq(), event.eventType(), event.step(), event.actor(), event.refKind(),
                event.refId() == null ? null : event.refId().toString(), event.payload(), Iso.of(event.occurredAt()));
    }
}
