package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.engine.SddProjectEntry;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/** FSM 專案清單的一筆（Bridge {@code GET /sdd/fsm} 的 {@code projects[]} 投影，鍵轉 camelCase；契約 §1.7.1；D-16）。 */
@Schema(name = "SddProjectEntry", description = "FSM 專案清單的一筆（v1.4，D-16）。project 就是 GET /engines/sdd?project= 吃的鍵，每一筆都點得進去")
public record SddProjectEntryDto(
        @NotNull @Schema(description = "檔名 FSM-STATE-<project>.yaml 中的專案名", pattern = "^[A-Za-z0-9._-]{1,128}$") String project,
        @NotNull @Schema(description = "檔名（FSM-STATE-<project>.yaml）") String source,
        @NotNull @Schema(description = "檔內 fsm_state.current_state；缺則 null", nullable = true) String currentState,
        @NotNull @Schema(description = "檔內 fsm_state.updated_at（ISO-8601 字串，原樣、不轉型）；缺則 null", nullable = true)
        String updatedAt) {

    public static SddProjectEntryDto from(SddProjectEntry entry) {
        return new SddProjectEntryDto(entry.project(), entry.source(), entry.currentState(), entry.updatedAt());
    }
}
