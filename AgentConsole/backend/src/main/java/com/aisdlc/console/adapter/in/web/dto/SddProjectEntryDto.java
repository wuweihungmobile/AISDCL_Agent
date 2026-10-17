package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.engine.SddProjectEntry;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/** FSM 專案清單的一筆（Bridge {@code GET /sdd/fsm} 的 {@code projects[]} 投影，鍵轉 camelCase；契約 §1.7.1；D-16）。 */
@Schema(name = "SddProjectEntry", description = "FSM 專案清單的一筆（v1.4，D-16）。project 就是 GET /engines/sdd?project= 吃的鍵，每一筆都點得進去")
public record SddProjectEntryDto(
        @NotNull @Schema(description = "檔名 FSM-STATE-<project>.yaml 中的專案名（淨化後的標準鍵；v1.5 起值域＝Bridge 淨化鏡像 fsm_component() 的輸出域："
                + "非空、NFC、≤ 80、不含禁用字元與控制字元、不以 . 結尾，可含 CJK、空白、括號）", maxLength = 80) String project,
        @NotNull @Schema(description = "檔名（FSM-STATE-<project>.yaml）") String source,
        @NotNull @Schema(description = "檔內 fsm_state.current_state；缺則 null", nullable = true) String currentState,
        @NotNull @Schema(description = "檔內 fsm_state.updated_at（ISO-8601 字串，原樣、不轉型）；缺則 null", nullable = true)
        String updatedAt) {

    public static SddProjectEntryDto from(SddProjectEntry entry) {
        return new SddProjectEntryDto(entry.project(), entry.source(), entry.currentState(), entry.updatedAt());
    }
}
