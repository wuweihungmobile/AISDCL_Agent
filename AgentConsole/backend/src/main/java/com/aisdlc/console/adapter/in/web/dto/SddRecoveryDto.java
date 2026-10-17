package com.aisdlc.console.adapter.in.web.dto;

import com.aisdlc.console.domain.model.engine.SddFsmState;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;

/**
 * ESCALATION 的恢復指令（v1.5；契約 §1.10.4；ADR-XPLAT-016 §5.3 的模板，由 Bridge 組字）。Console 原樣顯示，不提供恢復動作，
 * 也不得自行組字或猜測目標：恢復只有人、留在 SDD session。只含路徑與指令模板（理由欄位留 {@code <人工原因>} 佔位），不含任何機密。
 */
@Schema(name = "SddRecovery", description = "ESCALATION 的恢復指令（v1.5）：Bridge 組字的 resume-from-escalation 指令（含 <人工原因> 佔位）；"
        + "Console 原樣顯示，不提供恢復動作。不含任何機密")
public record SddRecoveryDto(
        @NotNull @Schema(description = "建議的 resume-from-escalation --to（SPEC_DRAFTING／IMPLEMENTATION／PR_REVIEW；委派失敗＝IMPLEMENTATION）")
        String target,
        @NotNull @Schema(description = "PowerShell 形態的完整指令（含 <人工原因> 佔位）") String powershell,
        @NotNull @Schema(description = "bash／zsh 形態的完整指令（含 <人工原因> 佔位）") String posix) {

    /** null（非 ESCALATION 狀態、或 Bridge 無法判定目標而省略）→ null。 */
    public static SddRecoveryDto from(SddFsmState.Recovery recovery) {
        return recovery == null ? null : new SddRecoveryDto(recovery.target(), recovery.powershell(), recovery.posix());
    }
}
