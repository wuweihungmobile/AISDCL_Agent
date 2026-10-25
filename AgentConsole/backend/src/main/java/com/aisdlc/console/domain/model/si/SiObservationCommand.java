package com.aisdlc.console.domain.model.si;

/**
 * 通過輸入閘的新增觀察命令（TCS-SelfImprovingDecide-P2b W12、表 M-O；obs-add 與 validate 共用）：字串欄已 trim、不含豎線與控制字元。
 * 刻意沒有 {@code marks_extra}：Console 只產生 {@code corrects} 對應的 {@code rel=corrects:<ID>} 標記。
 *
 * @param exposure 守衛面才有（a｜b｜c｜無）；其餘為 {@code null}
 * @param corrects 被更正的 OBS 號；沒有為 {@code null}
 */
public record SiObservationCommand(String context, String symptom, String evidence, String category, String severity,
                                   String face, String exposure, boolean externalDerived, String corrects) {
}
