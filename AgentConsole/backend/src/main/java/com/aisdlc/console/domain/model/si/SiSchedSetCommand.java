package com.aisdlc.console.domain.model.si;

/**
 * 通過輸入閘的排程設定命令（TCS-SelfImprovingSchedule W-S7、表 M-S；根層 PRD §9.2〈P4 增補〉）。
 *
 * @param enabled       啟用（true）或停用（false）；停用時 {@code periodMinutes} 仍必備
 * @param periodMinutes 週期（分鐘）；界（取自 {@code status.schedule}）已在序 5′ 驗過
 * @param reason        選填理由（已去前後空白）；{@code null}＝稽核 body 不含該鍵
 */
public record SiSchedSetCommand(boolean enabled, int periodMinutes, String reason) {
}
