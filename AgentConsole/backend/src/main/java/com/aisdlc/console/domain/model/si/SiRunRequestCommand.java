package com.aisdlc.console.domain.model.si;

/**
 * 通過輸入閘的立即啟動請求命令（TCS-SelfImprovingSchedule W-S7、表 M-R）。
 *
 * @param note 選填備註（已去前後空白）；{@code null}＝稽核 body 不含該鍵
 */
public record SiRunRequestCommand(String note) {
}
