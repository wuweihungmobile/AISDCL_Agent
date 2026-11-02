package com.aisdlc.console.adapter.in.web.dto.research;

import com.aisdlc.console.application.port.in.ResearchQueryUseCase.RecordsAudit;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

import java.util.List;

/**
 * 入庫完整率（契約 §1.3 {@code RecordsAuditDto}；API-RP-19）：R1～R14 各類記錄（PRD §5.1.8）的筆數，與 {@code missing}＝筆數為 0 且該類不屬「允許為 0」
 * （R10 自癒嘗試、R12 SCR）者。P0 尚無 V19 的表，R7、R8、R10、R11、R12 的筆數恆為 0（所以 Gate 0 時點的 {@code missing} 恰為 R7、R8、R11）。
 */
@Schema(name = "RecordsAuditDto", description = "R1～R14 各類記錄的筆數與缺漏類別（missing＝筆數為 0 且不屬 R10、R12）")
public record RecordsAuditDto(
        @NotNull @Schema(description = "恰 14 項：R1～R14") List<ClassDto> classes,
        @NotNull List<String> missing) {

    /** 一類記錄。 */
    @Schema(name = "RecordsAuditClassDto")
    public record ClassDto(@NotNull String id, @NotNull String name, @NotNull int count) {
    }

    public static RecordsAuditDto from(RecordsAudit audit) {
        return new RecordsAuditDto(audit.classes().stream().map(c -> new ClassDto(c.id(), c.name(), c.count())).toList(), audit.missing());
    }
}
